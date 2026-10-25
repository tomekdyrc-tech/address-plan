"""Hierarchical IPv6 planning with site infrastructure and bounded, lazy allocation."""

from collections import defaultdict
from dataclasses import dataclass, replace
from ipaddress import IPv6Address, IPv6Network, collapse_addresses
from itertools import islice

from adresplan.core.allocator import allocate
from adresplan.core.blocked import blocked_v6, validate_blocks
from adresplan.core.ipv6 import BUILDING_PREFIXES, building_prefix, reverse_zone, subnet64_at
from adresplan.core.models import (
    Allocation,
    AllocationRequest,
    AllocationResult,
    Finding,
    FreeBlock,
    IPv6GatewayMode,
    IPv6Infrastructure,
    IPv6PoolKind,
    IPv6PoolMetrics,
    IPv6SegmentInfo,
    IPv6SubnetStrategy,
    Node,
    Plan,
    Project,
    Segment,
    SegmentRole,
    node_sort_key,
)
from adresplan.core.sizing import grown_host_count
from adresplan.core.structure import validate_structure
from adresplan.core.validate6 import (
    BLOCKED_V6_CODES,
    FATAL_V6_CODES,
    validate_plan_v6,
    validate_project_v6,
)


def _cover(networks: list[IPv6Network]) -> IPv6Network:
    result = networks[0]
    while not all(network.subnet_of(result) for network in networks):
        result = result.supernet()
    return result


def _key(node: Node) -> str:
    return "node:" + node.id


@dataclass(frozen=True, slots=True)
class _Building:
    node: Node
    prefix: int
    anchor: IPv6Network | None
    segments: tuple[Segment, ...]

    def request(self) -> AllocationRequest[IPv6Network]:
        return AllocationRequest(
            node_id=_key(self.node),
            name=self.node.name,
            prefix=self.prefix,
            sort_order=self.node.sort_order,
            pinned=self.anchor,
        )


class _PlannerV6:
    def __init__(self, project: Project, pool: IPv6Network, findings: tuple[Finding, ...]) -> None:
        self.project = project
        self.pool = pool
        self.findings = list(findings)
        self.blocked = {f.node_id for f in findings if f.code in BLOCKED_V6_CODES}
        self.children: dict[str | None, list[Node]] = defaultdict(list)
        for node in sorted(project.nodes, key=node_sort_key):
            self.children[node.parent_id].append(node)
        self.pins = {p.site_id: p for p in project.pinned_v6_infrastructure}
        self.allocations: list[Allocation[IPv6Network]] = []
        self.free: list[FreeBlock] = []
        self.metrics: list[IPv6PoolMetrics] = []
        self.infrastructure: list[IPv6Infrastructure] = []
        self.infos: list[IPv6SegmentInfo] = []

    def segments(self, building: Node) -> tuple[Segment, ...]:
        if building.id in self.blocked:
            return ()
        return tuple(
            n
            for n in self.children[building.id]
            if isinstance(n, Segment) and n.v6_enabled is True and n.id not in self.blocked
        )

    def site_request(self, site: Node) -> AllocationRequest[IPv6Network] | None:
        if site.id in self.blocked:
            return None
        buildings = [b for b in self.children[site.id] if b.id not in self.blocked]
        segments = [s for b in buildings for s in self.segments(b)]
        exclusions = [
            *blocked_v6(self.project, site.id),
            *(n for b in buildings for n in blocked_v6(self.project, b.id)),
        ]
        if not (
            segments
            or site.pinned_v6 is not None
            or site.id in self.pins
            or any(b.pinned_v6 is not None for b in buildings)
            or exclusions
        ):
            return None
        pin = site.pinned_v6
        prefix = pin.prefixlen if pin is not None else self.project.settings.v6_site_prefix
        if pin is None:
            anchors = [n.pinned_v6 for n in (*buildings, *segments) if n.pinned_v6 is not None]
            anchors.extend(exclusions)
            if site.id in self.pins:
                anchors.append(self.pins[site.id].network)
            if anchors:
                cover = _cover(anchors)
                if cover.prefixlen < prefix:
                    self.findings.append(Finding(code="v6_site_anchor_span", node_id=site.id))
                    return None
                pin = cover.supernet(new_prefix=prefix)
        return AllocationRequest(
            node_id=_key(site),
            name=site.name,
            prefix=prefix,
            sort_order=site.sort_order,
            pinned=pin,
        )

    def allocation(
        self,
        pool: IPv6Network,
        parent_id: str | None,
        kind: IPv6PoolKind,
        requests: tuple[AllocationRequest[IPv6Network], ...],
        ids: dict[str, str],
    ) -> AllocationResult[IPv6Network]:
        exclusions = (
            blocked_v6(self.project, parent_id)
            if kind in (IPv6PoolKind.PROJECT, IPv6PoolKind.SITE, IPv6PoolKind.BUILDING)
            else ()
        )
        result = allocate(pool, requests, excluded=exclusions)
        for finding in result.findings:
            code = {
                "pinned_outside_pool": "v6_pin_outside_parent",
                "pinned_overlap": "v6_subnet_collision",
            }.get(finding.code, "v6_" + finding.code)
            self.findings.append(
                replace(
                    finding,
                    code=code,
                    node_id=ids.get(finding.node_id or "", parent_id),
                    details=(*finding.details, ("parent_id", parent_id), ("pool_kind", kind.value)),
                )
            )
        self.free.extend(
            FreeBlock(parent_id=parent_id, network=n, pool_kind=kind) for n in result.free_blocks
        )
        self.metrics.append(
            IPv6PoolMetrics(
                parent_id=parent_id,
                kind=kind,
                network=pool,
                allocated_addresses=pool.num_addresses
                - sum(n.num_addresses for n in result.free_blocks),
                free_addresses=sum(n.num_addresses for n in result.free_blocks),
                largest_free_block=max(
                    result.free_blocks, key=lambda n: n.num_addresses, default=None
                ),
            )
        )
        return result

    def building(self, node: Node) -> _Building | None:
        if node.id in self.blocked:
            return None
        segments = tuple(
            s for s in self.segments(node) if s.role in (SegmentRole.LAN, SegmentRole.MGMT)
        )
        exclusions = tuple(collapse_addresses(blocked_v6(self.project, node.id)))
        if not segments and node.pinned_v6 is None and not exclusions:
            return None
        try:
            reserved_slots = tuple(
                collapse_addresses(
                    n.supernet(new_prefix=64) if n.prefixlen > 64 else n for n in exclusions
                )
            )
            prefix = building_prefix(
                grown_host_count(len(segments), self.project.settings.v6_growth_pct)
                + sum(n.num_addresses // (2**64) for n in reserved_slots),
                self.project.settings.v6_building_prefix,
                0,
            )
        except ValueError as error:
            self.findings.append(
                Finding(
                    code="v6_building_capacity", node_id=node.id, details=(("reason", str(error)),)
                )
            )
            return None
        anchor = node.pinned_v6
        if anchor is not None:
            if anchor.prefixlen > prefix:
                self.findings.append(
                    Finding(
                        code="v6_building_pin_too_small",
                        node_id=node.id,
                        details=(("required_prefix", prefix),),
                    )
                )
            return _Building(node, anchor.prefixlen, anchor, segments)
        anchors = [s.pinned_v6 for s in segments if s.pinned_v6 is not None]
        anchors.extend(exclusions)
        if anchors:
            cover = _cover(anchors)
            fitting = [p for p in BUILDING_PREFIXES if p <= prefix and p <= cover.prefixlen]
            if not fitting:
                self.findings.append(Finding(code="v6_building_anchor_span", node_id=node.id))
                return None
            prefix = fitting[0]
            anchor = cover.supernet(new_prefix=prefix)
        return _Building(node, prefix, anchor, segments)

    def segment_info(self, segment: Segment, network: IPv6Network) -> None:
        self.allocations.append(Allocation(node_id=segment.id, network=network))
        if segment.role in (SegmentRole.LAN, SegmentRole.MGMT):
            settings = self.project.settings
            gateway = (
                IPv6Address(int(network.network_address) + 1)
                if settings.v6_gateway_mode is IPv6GatewayMode.GLOBAL
                else settings.v6_link_local_gateway
            )
            self.infos.append(
                IPv6SegmentInfo(
                    node_id=segment.id,
                    network=network,
                    gateway=gateway,
                    ra_mode=segment.ra_mode if segment.ra_mode is not None else settings.v6_ra_mode,
                    reverse_zone=reverse_zone(network),
                )
            )
        else:
            endpoints: tuple[IPv6Address, ...] = (network.network_address,)
            if segment.role is SegmentRole.P2P:
                endpoints = (*endpoints, IPv6Address(int(network.network_address) + 1))
            self.infos.append(
                IPv6SegmentInfo(node_id=segment.id, network=network, endpoints=endpoints)
            )

    def lan(self, building: _Building, pool: IPv6Network) -> None:
        requests: list[AllocationRequest[IPv6Network]] = []
        ids = {_key(s): s.id for s in building.segments}
        by_key = {_key(s): s for s in building.segments}
        for segment in building.segments:
            pin = segment.pinned_v6
            if self.project.settings.v6_subnet_strategy is IPv6SubnetStrategy.VLAN_DECIMAL_AS_HEX:
                vlan = segment.vlan_id
                if isinstance(vlan, bool) or not isinstance(vlan, int) or not 1 <= vlan <= 999:
                    self.findings.append(Finding(code="v6_vlan_required_1_999", node_id=segment.id))
                    continue
                try:
                    expected = subnet64_at(pool, int(str(vlan), 16))
                except ValueError:
                    self.findings.append(
                        Finding(
                            code="v6_vlan_offset_outside_building",
                            node_id=segment.id,
                            details=(("vlan_id", vlan), ("building_prefix", pool.prefixlen)),
                        )
                    )
                    continue
                if pin is not None and pin != expected:
                    self.findings.append(Finding(code="v6_vlan_pin_mismatch", node_id=segment.id))
                if pin is None:
                    pin = expected
            requests.append(
                AllocationRequest(
                    node_id=_key(segment),
                    name=segment.name,
                    prefix=64,
                    sort_order=segment.sort_order,
                    pinned=pin,
                )
            )
        result = self.allocation(
            pool, building.node.id, IPv6PoolKind.BUILDING, tuple(requests), ids
        )
        for allocation in result.allocations:
            self.segment_info(by_key[allocation.node_id], allocation.network)

    def infra(self, site: Node, pools: IPv6Infrastructure) -> None:
        self.infrastructure.append(pools)
        requests = tuple(
            AllocationRequest[IPv6Network](node_id=key, name=key, prefix=64, pinned=network)
            for key, network in [
                ("reserved", pools.reserved_pool),
                ("p2p", pools.p2p_pool),
                ("loopback", pools.loopback_pool),
            ]
        )
        self.allocation(
            pools.network,
            site.id,
            IPv6PoolKind.INFRASTRUCTURE,
            requests,
            {r.node_id: site.id for r in requests},
        )
        segments = [s for b in self.children[site.id] for s in self.segments(b)]
        for role, pool, kind, prefix in [
            (SegmentRole.P2P, pools.p2p_pool, IPv6PoolKind.P2P, 127),
            (SegmentRole.LOOPBACK, pools.loopback_pool, IPv6PoolKind.LOOPBACK, 128),
        ]:
            by_key = {_key(s): s for s in segments if s.role is role}
            requests = tuple(
                AllocationRequest[IPv6Network](
                    node_id=_key(s),
                    name=s.name,
                    prefix=prefix,
                    sort_order=s.sort_order,
                    pinned=s.pinned_v6,
                )
                for s in by_key.values()
            )
            result = self.allocation(
                pool, site.id, kind, requests, {key: s.id for key, s in by_key.items()}
            )
            for allocation in result.allocations:
                self.segment_info(by_key[allocation.node_id], allocation.network)

    def site(self, site: Node, pool: IPv6Network) -> None:
        if site.id in self.pins:
            pools = self.pins[site.id]
        else:
            trial = allocate(
                pool,
                (
                    AllocationRequest[IPv6Network](
                        node_id="infrastructure",
                        name="Infrastructure",
                        prefix=self.project.settings.v6_infra_prefix,
                    ),
                ),
                excluded=blocked_v6(self.project, site.id),
            )
            if not trial.allocations:
                self.findings.append(Finding(code="v6_insufficient_space", node_id=site.id))
                return
            network = trial.allocations[0].network
            reserved, p2p, loopback = tuple(islice(network.subnets(new_prefix=64), 3))
            pools = IPv6Infrastructure(
                site_id=site.id,
                network=network,
                reserved_pool=reserved,
                p2p_pool=p2p,
                loopback_pool=loopback,
            )
        buildings = tuple(
            b for node in self.children[site.id] if (b := self.building(node)) is not None
        )
        by_key = {_key(b.node): b for b in buildings}
        requests = (
            AllocationRequest[IPv6Network](
                node_id="infrastructure",
                name="Infrastructure",
                prefix=pools.network.prefixlen,
                pinned=pools.network,
            ),
            *(b.request() for b in buildings),
        )
        result = self.allocation(
            pool,
            site.id,
            IPv6PoolKind.SITE,
            requests,
            {"infrastructure": site.id, **{key: b.node.id for key, b in by_key.items()}},
        )
        for allocation in result.allocations:
            if allocation.node_id == "infrastructure":
                self.infra(site, pools)
            else:
                building = by_key[allocation.node_id]
                self.allocations.append(
                    Allocation(node_id=building.node.id, network=allocation.network)
                )
                self.lan(building, allocation.network)

    def build(self) -> Plan:
        by_key = {_key(s): s for s in self.children[None]}
        requests = tuple(r for s in by_key.values() if (r := self.site_request(s)) is not None)
        result = self.allocation(
            self.pool,
            None,
            IPv6PoolKind.PROJECT,
            requests,
            {key: s.id for key, s in by_key.items()},
        )
        for allocation in result.allocations:
            site = by_key[allocation.node_id]
            self.allocations.append(Allocation(node_id=site.id, network=allocation.network))
            self.site(site, allocation.network)
        plan = Plan(
            project_id=self.project.id,
            v6_allocations=tuple(
                sorted(
                    self.allocations,
                    key=lambda a: (int(a.network.network_address), a.network.prefixlen, a.node_id),
                )
            ),
            free_blocks=tuple(self.free),
            findings=tuple(self.findings),
            v6_infrastructure=tuple(self.infrastructure),
            v6_segments=tuple(self.infos),
            v6_metrics=tuple(self.metrics),
        )
        return replace(plan, findings=(*plan.findings, *validate_plan_v6(self.project, plan)))


def build_plan_v6(project: Project) -> Plan:
    if not project.v6_active:
        return Plan(project_id=project.id)
    structure = validate_structure(project)
    if structure:
        return Plan(project_id=project.id, findings=structure)
    findings = validate_project_v6(project)
    block_findings = validate_blocks(project, 6)
    if block_findings:
        return Plan(project_id=project.id, findings=(*findings, *block_findings))
    if project.v6_prefix is None or any(f.code in FATAL_V6_CODES for f in findings):
        return Plan(project_id=project.id, findings=findings)
    return _PlannerV6(project, project.v6_prefix, findings).build()
