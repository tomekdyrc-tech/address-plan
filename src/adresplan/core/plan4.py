"""Bottom-up sizing and top-down allocation of a hierarchical IPv4 project."""

from collections import defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction
from ipaddress import IPv4Network, collapse_addresses

from adresplan.core.allocator import allocate
from adresplan.core.blocked import blocked_v4, validate_blocks
from adresplan.core.models import (
    Allocation,
    AllocationRequest,
    Finding,
    FindingLevel,
    FreeBlock,
    Node,
    Plan,
    PoolMetrics,
    Project,
    Segment,
    SegmentReservations,
    SegmentRole,
    node_sort_key,
)
from adresplan.core.reservations import reserve_segment_v4
from adresplan.core.sizing import next_pow2, size_segment_v4
from adresplan.core.structure import validate_structure
from adresplan.core.validate import validate_plan_v4, validate_project_v4


@dataclass(frozen=True, slots=True)
class _Requirement:
    node: Node
    prefix: int
    anchor: IPv4Network | None
    children: tuple["_Requirement", ...] = ()

    @property
    def addresses(self) -> int:
        return IPv4Network((0, self.prefix)).num_addresses

    def request(self) -> AllocationRequest[IPv4Network]:
        return AllocationRequest(
            node_id=self.node.id,
            name=self.node.name,
            prefix=self.prefix,
            sort_order=self.node.sort_order,
            pinned=self.anchor,
        )


def _cover(anchors: list[IPv4Network]) -> IPv4Network:
    """Find a common CIDR ancestor without parsing addresses or using bit masks."""
    result = anchors[0]
    while not all(anchor.subnet_of(result) for anchor in anchors):
        result = result.supernet()
    return result


class _Planner:
    """Private per-call state; no input mutation or state shared between calls."""

    def __init__(self, project: Project, findings: tuple[Finding, ...]) -> None:
        self.project = project
        self.findings = list(findings)
        self.children: dict[str | None, list[Node]] = defaultdict(list)
        for node in sorted(project.nodes, key=node_sort_key):
            self.children[node.parent_id].append(node)
        self.blocked = {
            f.node_id
            for f in findings
            if f.code in ("pinned_family_mismatch", "pinned_outside_project")
        }
        self.allocations: list[Allocation[IPv4Network]] = []
        self.free_blocks: list[FreeBlock] = []
        self.reservations: list[SegmentReservations] = []
        self.metrics: list[PoolMetrics] = []

    def requirement(self, node: Node) -> _Requirement | None:
        if node.id in self.blocked:
            return None
        if isinstance(node, Segment):
            try:
                size = size_segment_v4(node, self.project.settings)
            except ValueError as error:
                self.findings.append(
                    Finding(
                        code="invalid_segment_requirements",
                        node_id=node.id,
                        details=(("reason", str(error)),),
                    )
                )
                return None
            if node.pinned_v4 is not None and node.pinned_v4.prefixlen > size.prefix:
                self.findings.append(Finding(code="pinned_too_small", node_id=node.id))
                return None
            return _Requirement(
                node=node,
                prefix=node.pinned_v4.prefixlen if node.pinned_v4 else size.prefix,
                anchor=node.pinned_v4,
            )

        children = tuple(
            requirement
            for child in self.children[node.id]
            if (requirement := self.requirement(child)) is not None
        )
        # Explicit parent pins are fixed boundaries, including when new children do not fit.
        if node.pinned_v4 is not None:
            return _Requirement(node, node.pinned_v4.prefixlen, node.pinned_v4, children)
        exclusions = tuple(collapse_addresses(blocked_v4(self.project, node.id)))
        if not children and not exclusions:
            return None
        total = sum(child.addresses for child in children) + sum(
            n.num_addresses for n in exclusions
        )
        prefix = 32 - (next_pow2(total).bit_length() - 1)
        if prefix < 0:
            self.findings.append(
                Finding(
                    code="hierarchy_capacity_exceeded",
                    node_id=node.id,
                    details=(("required_addresses", total),),
                )
            )
            return None
        anchors = [child.anchor for child in children if child.anchor is not None] + list(
            exclusions
        )
        if not anchors:
            return _Requirement(node, prefix, None, children)

        cover = _cover(anchors)
        prefix = min(prefix, cover.prefixlen)
        candidate = cover.supernet(new_prefix=prefix)
        while candidate.subnet_of(self.project.v4_pool):
            trial = allocate(
                candidate, (child.request() for child in children), excluded=exclusions
            )
            if trial.is_complete or any(f.code != "insufficient_space" for f in trial.findings):
                break
            if candidate.prefixlen <= self.project.v4_pool.prefixlen:
                break
            candidate = candidate.supernet()
        return _Requirement(node, candidate.prefixlen, candidate, children)

    def allocate_level(
        self, pool: IPv4Network, parent_id: str | None, requirements: tuple[_Requirement, ...]
    ) -> None:
        result = allocate(
            pool,
            (requirement.request() for requirement in requirements),
            excluded=blocked_v4(self.project, parent_id),
        )
        by_id = {requirement.node.id: requirement for requirement in requirements}
        for finding in result.findings:
            code = finding.code
            requirement = by_id.get(finding.node_id or "")
            if requirement is not None and requirement.node.pinned_v4 is None:
                if code == "pinned_overlap":
                    code = "hierarchy_anchor_overlap"
                elif code == "pinned_outside_pool":
                    code = "hierarchy_anchor_outside_parent"
            self.findings.append(
                replace(
                    finding,
                    code=code,
                    node_id=finding.node_id if finding.node_id is not None else parent_id,
                    details=(*finding.details, ("parent_id", parent_id)),
                )
            )
        self.free_blocks.extend(
            FreeBlock(parent_id=parent_id, network=n) for n in result.free_blocks
        )
        metrics = PoolMetrics(
            parent_id=parent_id,
            network=pool,
            allocated_addresses=pool.num_addresses
            - sum(n.num_addresses for n in result.free_blocks),
            free_addresses=sum(n.num_addresses for n in result.free_blocks),
            largest_free_block=max(result.free_blocks, key=lambda n: n.num_addresses, default=None),
        )
        self.metrics.append(metrics)
        self.findings.append(
            Finding(
                code="pool_fragmentation",
                level=FindingLevel.INFO,
                node_id=parent_id,
                details=(
                    ("free_addresses", metrics.free_addresses),
                    (
                        "largest_free_prefix",
                        metrics.largest_free_block.prefixlen
                        if metrics.largest_free_block is not None
                        else None,
                    ),
                    (
                        "continuity",
                        str(metrics.continuity) if metrics.continuity is not None else None,
                    ),
                ),
            )
        )
        for allocation in result.allocations:
            self.allocations.append(allocation)
            requirement = by_id[allocation.node_id]
            if isinstance(requirement.node, Segment):
                self.reserve(requirement.node, allocation.network)
            else:
                self.findings.append(
                    Finding(
                        code="summary_route",
                        level=FindingLevel.INFO,
                        node_id=allocation.node_id,
                        details=(("network", str(allocation.network)),),
                    )
                )
                self.allocate_level(allocation.network, allocation.node_id, requirement.children)

    def reserve(self, segment: Segment, network: IPv4Network) -> None:
        try:
            reservation = reserve_segment_v4(segment, self.project.settings, network)
        except ValueError as error:
            self.findings.append(
                Finding(
                    code="invalid_reservations",
                    node_id=segment.id,
                    details=(("reason", str(error)),),
                )
            )
            return
        self.reservations.append(reservation)
        if segment.role in (
            SegmentRole.LAN,
            SegmentRole.MGMT,
        ) and reservation.utilization > Fraction(85, 100):
            self.findings.append(
                Finding(
                    code="high_segment_utilization",
                    level=FindingLevel.WARNING,
                    node_id=segment.id,
                    details=(
                        ("required_usable", reservation.usable_needed),
                        ("usable_capacity", reservation.usable_capacity),
                    ),
                )
            )

    def build(self) -> Plan:
        roots = tuple(
            requirement
            for node in self.children[None]
            if (requirement := self.requirement(node)) is not None
        )
        self.allocate_level(self.project.v4_pool, None, roots)
        plan = Plan(
            project_id=self.project.id,
            v4_allocations=tuple(
                sorted(
                    self.allocations,
                    key=lambda a: (int(a.network.network_address), a.network.prefixlen, a.node_id),
                )
            ),
            free_blocks=tuple(self.free_blocks),
            findings=tuple(self.findings),
            v4_reservations=tuple(self.reservations),
            v4_metrics=tuple(self.metrics),
        )
        return replace(plan, findings=(*plan.findings, *validate_plan_v4(self.project, plan)))


def build_plan_v4(project: Project) -> Plan:
    """Build the complete IPv4 hierarchy or a partial plan with structured errors."""
    structure_findings = validate_structure(project)
    if structure_findings:
        return Plan(project_id=project.id, findings=structure_findings)
    findings = validate_project_v4(project)
    block_findings = validate_blocks(project, 4)
    if block_findings:
        return Plan(project_id=project.id, findings=(*findings, *block_findings))
    if any(f.code in ("invalid_v4_pool", "forbidden_v4_pool") for f in findings):
        return Plan(project_id=project.id, findings=findings)
    return _Planner(project, findings).build()
