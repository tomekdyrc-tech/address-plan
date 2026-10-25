"""IPv6 pool, settings, pin and output validation."""

from collections import Counter
from ipaddress import IPv6Address, IPv6Network
from itertools import combinations
from typing import TypeGuard

from adresplan.core.ipv6 import BUILDING_PREFIXES, building_prefix, classify_prefix
from adresplan.core.models import (
    Finding,
    FindingLevel,
    IPv6GatewayMode,
    IPv6Infrastructure,
    IPv6Kind,
    IPv6RAMode,
    IPv6SubnetStrategy,
    NodeKind,
    Plan,
    Project,
    Segment,
    SegmentRole,
    node_sort_key,
)

FATAL_V6_CODES = frozenset({"invalid_v6_pool", "unsupported_v6_pool", "invalid_v6_settings"})
BLOCKED_V6_CODES = frozenset(
    {
        "v6_pin_family_mismatch",
        "v6_pin_outside_project",
        "invalid_v6_pin_prefix",
        "v6_disabled_with_pin",
        "invalid_v6_segment_settings",
        "invalid_v6_infrastructure_pin",
        "duplicate_v6_infrastructure_pin",
    }
)


def is_v6_network(value: object) -> TypeGuard[IPv6Network]:
    return isinstance(value, IPv6Network)


def _nibble_prefix(value: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 60
        and value % 4 == 0
    )


def _valid_segment_settings(enabled: object, role: object, ra_mode: object) -> bool:
    return (
        isinstance(enabled, bool)
        and isinstance(role, SegmentRole)
        and (ra_mode is None or isinstance(ra_mode, IPv6RAMode))
    )


def validate_project_v6(project: Project) -> tuple[Finding, ...]:
    if not project.v6_active:
        return ()
    if project.v6_prefix is None:
        if project.pinned_v6_infrastructure or any(n.pinned_v6 is not None for n in project.nodes):
            return (Finding(code="v6_pool_missing"),)
        return ()
    if not is_v6_network(project.v6_prefix):
        return (Finding(code="invalid_v6_pool"),)
    findings: list[Finding] = []
    try:
        kind = classify_prefix(project.v6_prefix)
    except ValueError:
        return (Finding(code="unsupported_v6_pool"),)
    if not isinstance(project.v6_kind, IPv6Kind) or kind is not project.v6_kind:
        findings.append(Finding(code="v6_kind_mismatch", details=(("actual_kind", kind.value),)))
    settings = project.settings
    valid = (
        _nibble_prefix(settings.v6_site_prefix)
        and _nibble_prefix(settings.v6_infra_prefix)
        and isinstance(settings.v6_building_prefix, int)
        and not isinstance(settings.v6_building_prefix, bool)
        and settings.v6_building_prefix in BUILDING_PREFIXES
        and project.v6_prefix.prefixlen <= settings.v6_site_prefix <= settings.v6_infra_prefix
        and settings.v6_site_prefix <= settings.v6_building_prefix
        and isinstance(settings.v6_growth_pct, int)
        and not isinstance(settings.v6_growth_pct, bool)
        and settings.v6_growth_pct >= 0
        and isinstance(settings.v6_subnet_strategy, IPv6SubnetStrategy)
        and isinstance(settings.v6_gateway_mode, IPv6GatewayMode)
        and isinstance(settings.v6_ra_mode, IPv6RAMode)
        and isinstance(settings.v6_link_local_gateway, IPv6Address)
        and settings.v6_link_local_gateway.is_link_local
    )
    if not valid:
        return (*findings, Finding(code="invalid_v6_settings"))

    nodes = {n.id: n for n in project.nodes}
    for node in sorted(project.nodes, key=node_sort_key):
        pin = node.pinned_v6
        if isinstance(node, Segment):
            if not _valid_segment_settings(node.v6_enabled, node.role, node.ra_mode):
                findings.append(Finding(code="invalid_v6_segment_settings", node_id=node.id))
            if not node.v6_enabled and pin is not None:
                findings.append(Finding(code="v6_disabled_with_pin", node_id=node.id))
        if pin is None:
            continue
        if not is_v6_network(pin):
            findings.append(Finding(code="v6_pin_family_mismatch", node_id=node.id))
            continue
        if not pin.subnet_of(project.v6_prefix):
            findings.append(Finding(code="v6_pin_outside_project", node_id=node.id))
        if isinstance(node, Segment):
            expected = (
                127
                if node.role is SegmentRole.P2P
                else 128
                if node.role is SegmentRole.LOOPBACK
                else 64
            )
            correct = pin.prefixlen == expected
        elif node.kind is NodeKind.BUILDING:
            correct = pin.prefixlen in BUILDING_PREFIXES
        else:
            correct = _nibble_prefix(pin.prefixlen) and pin.prefixlen <= settings.v6_site_prefix
        if not correct:
            findings.append(Finding(code="invalid_v6_pin_prefix", node_id=node.id))

    counts = Counter(p.site_id for p in project.pinned_v6_infrastructure)
    for site_id in sorted(counts):
        if counts[site_id] > 1:
            findings.append(Finding(code="duplicate_v6_infrastructure_pin", node_id=site_id))
    for infra_pin in project.pinned_v6_infrastructure:
        site = nodes.get(infra_pin.site_id)
        if site is None or site.kind is not NodeKind.SITE:
            findings.append(
                Finding(code="invalid_v6_infrastructure_pin", node_id=infra_pin.site_id)
            )
            continue
        pools = (infra_pin.reserved_pool, infra_pin.p2p_pool, infra_pin.loopback_pool)
        valid_pin = (
            is_v6_network(infra_pin.network)
            and _nibble_prefix(infra_pin.network.prefixlen)
            and infra_pin.network.prefixlen <= settings.v6_infra_prefix
            and infra_pin.network.subnet_of(project.v6_prefix)
            and all(
                is_v6_network(p) and p.prefixlen == 64 and p.subnet_of(infra_pin.network)
                for p in pools
            )
            and len(set(pools)) == 3
        )
        if not valid_pin:
            findings.append(
                Finding(code="invalid_v6_infrastructure_pin", node_id=infra_pin.site_id)
            )
    return tuple(findings)


def validate_plan_v6(project: Project, plan: Plan) -> tuple[Finding, ...]:
    """Verify containment using dedicated infrastructure pools for P2P/loopback."""
    if project.v6_prefix is None or not project.v6_active:
        return (
            (Finding(code="unexpected_v6_allocations"),)
            if plan.v6_allocations or plan.v6_infrastructure
            else ()
        )
    if not is_v6_network(project.v6_prefix):
        return (Finding(code="invalid_v6_pool"),)
    findings: list[Finding] = []
    if plan.project_id != project.id:
        findings.append(Finding(code="v6_plan_project_mismatch"))
    nodes = {n.id: n for n in project.nodes}
    allocated: dict[str, IPv6Network] = {}
    for allocation in plan.v6_allocations:
        code = None
        if allocation.node_id not in nodes:
            code = "v6_unknown_allocation_node"
        elif allocation.node_id in allocated:
            code = "v6_duplicate_allocation_node"
        elif not is_v6_network(allocation.network):
            code = "v6_allocation_family_mismatch"
        if code:
            findings.append(Finding(code=code, node_id=allocation.node_id))
        else:
            allocated[allocation.node_id] = allocation.network
    infra: dict[str, IPv6Infrastructure] = {}
    counts = Counter(p.site_id for p in plan.v6_infrastructure)
    for pools in plan.v6_infrastructure:
        children = (pools.reserved_pool, pools.p2p_pool, pools.loopback_pool)
        if pools.site_id not in nodes or nodes[pools.site_id].kind is not NodeKind.SITE:
            findings.append(Finding(code="v6_unknown_infrastructure_site", node_id=pools.site_id))
        elif counts[pools.site_id] > 1:
            findings.append(Finding(code="v6_duplicate_infrastructure", node_id=pools.site_id))
        elif not is_v6_network(pools.network) or not all(is_v6_network(p) for p in children):
            findings.append(
                Finding(code="v6_infrastructure_family_mismatch", node_id=pools.site_id)
            )
        else:
            infra[pools.site_id] = pools
    peers: dict[str | None, list[str]] = {}
    leaves: list[str] = []
    parent: IPv6Network | None
    for node_id, network in sorted(allocated.items()):
        node = nodes[node_id]
        if node.kind is NodeKind.SITE:
            parent = project.v6_prefix
        elif isinstance(node, Segment) and node.role in (SegmentRole.P2P, SegmentRole.LOOPBACK):
            building = nodes.get(node.parent_id or "")
            site_infra = infra.get(building.parent_id or "") if building else None
            parent = (
                (site_infra.p2p_pool if node.role is SegmentRole.P2P else site_infra.loopback_pool)
                if site_infra
                else None
            )
        else:
            parent = allocated.get(node.parent_id or "")
            peers.setdefault(node.parent_id, []).append(node_id)
        if node.kind is NodeKind.SITE:
            peers.setdefault(None, []).append(node_id)
        if parent is None or not network.subnet_of(parent):
            findings.append(Finding(code="v6_allocation_outside_parent", node_id=node_id))
        if node.pinned_v6 is not None and node.pinned_v6 != network:
            findings.append(Finding(code="v6_pinned_allocation_changed", node_id=node_id))
        if isinstance(node, Segment):
            leaves.append(node_id)
            expected = (
                127
                if node.role is SegmentRole.P2P
                else 128
                if node.role is SegmentRole.LOOPBACK
                else 64
            )
            if not node.v6_enabled or network.prefixlen != expected:
                findings.append(Finding(code="v6_invalid_segment_allocation", node_id=node_id))
        elif node.kind is NodeKind.BUILDING:
            count = sum(
                isinstance(n, Segment)
                and n.v6_enabled
                and n.role in (SegmentRole.LAN, SegmentRole.MGMT)
                for n in project.nodes
                if n.parent_id == node_id
            )
            try:
                required = building_prefix(
                    count, project.settings.v6_building_prefix, project.settings.v6_growth_pct
                )
                valid_capacity = (
                    network.prefixlen in BUILDING_PREFIXES and network.prefixlen <= required
                )
            except ValueError:
                valid_capacity = False
            if not valid_capacity:
                findings.append(Finding(code="v6_invalid_building_capacity", node_id=node_id))
        elif network.prefixlen != (
            node.pinned_v6.prefixlen
            if node.pinned_v6 is not None
            else project.settings.v6_site_prefix
        ):
            findings.append(Finding(code="v6_invalid_site_allocation", node_id=node_id))
    for node_id in allocated:
        if nodes[node_id].kind is NodeKind.SITE and node_id not in infra:
            findings.append(Finding(code="v6_infrastructure_missing", node_id=node_id))
    for site_id, pools in sorted(infra.items()):
        parent = allocated.get(site_id)
        children = (pools.reserved_pool, pools.p2p_pool, pools.loopback_pool)
        if parent is None or not pools.network.subnet_of(parent):
            findings.append(Finding(code="v6_infrastructure_outside_site", node_id=site_id))
        if (
            any(not p.subnet_of(pools.network) or p.prefixlen != 64 for p in children)
            or len(set(children)) != 3
        ):
            findings.append(Finding(code="invalid_v6_infrastructure_pin", node_id=site_id))
        expected_infra = next(
            (p for p in project.pinned_v6_infrastructure if p.site_id == site_id), None
        )
        if expected_infra is not None and expected_infra != pools:
            findings.append(Finding(code="v6_pinned_infrastructure_changed", node_id=site_id))
        for node_id in peers.get(site_id, []):
            if allocated[node_id].overlaps(pools.network):
                findings.append(Finding(code="v6_building_infrastructure_overlap", node_id=node_id))
    checked: set[tuple[str, str]] = set()
    for group in (*peers.values(), leaves):
        for first, second in combinations(sorted(group), 2):
            if (first, second) not in checked and allocated[first].overlaps(allocated[second]):
                findings.append(
                    Finding(
                        code="v6_allocation_overlap",
                        node_id=second,
                        details=(("other_node_id", first),),
                    )
                )
            checked.add((first, second))
    errors = {f.node_id for f in (*plan.findings, *findings) if f.level is FindingLevel.ERROR}
    for node in sorted(project.nodes, key=node_sort_key):
        if not isinstance(node, Segment) or not node.v6_enabled or node.id in allocated:
            continue
        ancestor: str | None = node.id
        visited: set[str] = set()
        while ancestor is not None and ancestor in nodes and ancestor not in visited:
            if ancestor in errors:
                break
            visited.add(ancestor)
            ancestor = nodes[ancestor].parent_id
        else:
            findings.append(Finding(code="v6_missing_segment_allocation", node_id=node.id))
    return tuple(findings)
