"""IPv4 input and allocation validation with explicit address-space rules."""

from collections import defaultdict
from ipaddress import IPv4Network
from itertools import combinations
from typing import TypeGuard

from adresplan.core.models import (
    Finding,
    FindingLevel,
    NodeKind,
    Plan,
    Project,
    Segment,
    SegmentRole,
    node_sort_key,
)
from adresplan.core.reservations import reserve_segment_v4

RFC1918 = (IPv4Network("10.0.0.0/8"), IPv4Network("172.16.0.0/12"), IPv4Network("192.168.0.0/16"))
CGNAT = IPv4Network("100.64.0.0/10")
FORBIDDEN_POOLS = (
    IPv4Network("127.0.0.0/8"),
    IPv4Network("169.254.0.0/16"),
    IPv4Network("224.0.0.0/4"),
    IPv4Network("240.0.0.0/4"),
)


def _is_v4_network(network: object) -> TypeGuard[IPv4Network]:
    return isinstance(network, IPv4Network)


def is_rfc1918(network: IPv4Network) -> bool:
    return any(network.subnet_of(private) for private in RFC1918)


def validate_project_v4(project: Project) -> tuple[Finding, ...]:
    """Validate pool, pins and VLANs after the tree structure has been checked."""
    if not _is_v4_network(project.v4_pool):
        return (Finding(code="invalid_v4_pool"),)
    findings: list[Finding] = []
    for forbidden in FORBIDDEN_POOLS:
        if project.v4_pool.overlaps(forbidden):
            findings.append(Finding(code="forbidden_v4_pool", details=(("range", str(forbidden)),)))
    if project.v4_pool.overlaps(CGNAT):
        findings.append(Finding(code="cgnat_pool", level=FindingLevel.WARNING))
    elif not is_rfc1918(project.v4_pool):
        findings.append(Finding(code="non_rfc1918_pool", level=FindingLevel.WARNING))

    nodes = {node.id: node for node in project.nodes}
    vlans: dict[tuple[str, int], list[str]] = defaultdict(list)
    for node in sorted(project.nodes, key=node_sort_key):
        if node.pinned_v4 is not None:
            if not _is_v4_network(node.pinned_v4):
                findings.append(Finding(code="pinned_family_mismatch", node_id=node.id))
            elif not node.pinned_v4.subnet_of(project.v4_pool):
                findings.append(Finding(code="pinned_outside_project", node_id=node.id))
        if not isinstance(node, Segment) or node.vlan_id is None:
            continue
        if (
            isinstance(node.vlan_id, bool)
            or not isinstance(node.vlan_id, int)
            or not 1 <= node.vlan_id <= 4094
        ):
            findings.append(Finding(code="invalid_vlan_id", node_id=node.id))
            continue
        if node.vlan_id == 1 and node.role is SegmentRole.LAN:
            findings.append(
                Finding(code="user_traffic_vlan_1", level=FindingLevel.INFO, node_id=node.id)
            )
        parent = nodes.get(node.parent_id or "")
        if parent is not None and parent.parent_id is not None:
            vlans[(parent.parent_id, node.vlan_id)].append(node.id)
    for (site_id, vlan), ids in sorted(vlans.items()):
        if len(ids) > 1:
            for node_id in ids:
                findings.append(
                    Finding(
                        code="duplicate_vlan_id",
                        level=FindingLevel.WARNING,
                        node_id=node_id,
                        details=(("site_id", site_id), ("vlan_id", vlan), ("count", len(ids))),
                    )
                )
    return tuple(findings)


def validate_plan_v4(project: Project, plan: Plan) -> tuple[Finding, ...]:
    """Allow ancestor containment, but reject sibling and endpoint collisions."""
    if not _is_v4_network(project.v4_pool):
        return (Finding(code="invalid_v4_pool"),)
    findings: list[Finding] = []
    if plan.project_id != project.id:
        findings.append(Finding(code="plan_project_mismatch"))
    nodes = {node.id: node for node in project.nodes}
    allocations: dict[str, IPv4Network] = {}
    for allocation in plan.v4_allocations:
        if allocation.node_id not in nodes:
            findings.append(Finding(code="unknown_allocation_node", node_id=allocation.node_id))
        elif allocation.node_id in allocations:
            findings.append(Finding(code="duplicate_allocation_node", node_id=allocation.node_id))
        elif not _is_v4_network(allocation.network):
            findings.append(Finding(code="allocation_family_mismatch", node_id=allocation.node_id))
        else:
            allocations[allocation.node_id] = allocation.network
    peers: dict[str | None, list[str]] = defaultdict(list)
    leaves: list[str] = []
    existing_errors = {f.node_id for f in plan.findings if f.level is FindingLevel.ERROR}
    for node_id in sorted(allocations):
        node = nodes[node_id]
        network = allocations[node_id]
        parent = (
            project.v4_pool if node.kind is NodeKind.SITE else allocations.get(node.parent_id or "")
        )
        if parent is None:
            findings.append(Finding(code="allocation_parent_missing", node_id=node_id))
        elif not network.subnet_of(parent):
            findings.append(Finding(code="allocation_outside_parent", node_id=node_id))
        if node.pinned_v4 is not None and network != node.pinned_v4:
            findings.append(Finding(code="pinned_allocation_changed", node_id=node_id))
        peers[node.parent_id].append(node_id)
        if isinstance(node, Segment):
            leaves.append(node_id)
            if node_id not in existing_errors:
                try:
                    reserve_segment_v4(node, project.settings, network)
                except ValueError as error:
                    findings.append(
                        Finding(
                            code="invalid_segment_allocation",
                            node_id=node_id,
                            details=(("reason", str(error)),),
                        )
                    )

    existing_errors.update(f.node_id for f in findings if f.level is FindingLevel.ERROR)
    for node in sorted(project.nodes, key=node_sort_key):
        if not isinstance(node, Segment) or node.id in allocations:
            continue
        ancestor: str | None = node.id
        visited: set[str] = set()
        while ancestor is not None and ancestor in nodes and ancestor not in visited:
            if ancestor in existing_errors:
                break
            visited.add(ancestor)
            ancestor = nodes[ancestor].parent_id
        else:
            findings.append(Finding(code="missing_segment_allocation", node_id=node.id))

    checked: set[tuple[str, str]] = set()
    for group in (*peers.values(), leaves):
        for first, second in combinations(sorted(group), 2):
            if (first, second) in checked:
                continue
            checked.add((first, second))
            if allocations[first].overlaps(allocations[second]):
                findings.append(
                    Finding(
                        code="allocation_overlap",
                        node_id=second,
                        details=(("other_node_id", first),),
                    )
                )
    return tuple(findings)
