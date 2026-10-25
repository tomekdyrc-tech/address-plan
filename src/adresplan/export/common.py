"""Validated report data shared by tabular and documentation exports."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from ipaddress import IPv4Network, IPv6Network

from adresplan.application.project_json import prepare_project
from adresplan.core.models import (
    AddressRange,
    Finding,
    FindingLevel,
    IPv6SegmentInfo,
    Node,
    Plan,
    Project,
    Segment,
    SegmentReservations,
    SegmentRole,
    node_sort_key,
)
from adresplan.core.sizing import grown_host_count
from adresplan.i18n import tr


def document_details(project: Project) -> tuple[tuple[str, str], ...]:
    return tuple(
        (tr(label), value)
        for label, value in (
            ("Autor", project.author),
            ("Organizacja", project.organization),
            ("Data dokumentacji", project.document_date),
            ("Opis", project.description),
        )
        if value
    )


@dataclass(frozen=True, slots=True)
class SegmentRow:
    site: Node
    building: Node
    segment: Segment
    v4: IPv4Network | None
    v6: IPv6Network | None
    reservation: SegmentReservations | None
    info6: IPv6SegmentInfo | None
    growth_pct: int
    grown_hosts: int
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class Report:
    project: Project
    plan: Plan
    sites: tuple[Node, ...]
    buildings: tuple[Node, ...]
    rows: tuple[SegmentRow, ...]

    @property
    def status(self) -> str:
        return tr("KOMPLETNY") if self.plan.is_complete else tr("NIEKOMPLETNY")


def create_report(project: Project) -> Report:
    state = prepare_project(project)
    project, plan = state.project, state.plan
    children: dict[str | None, list[Node]] = defaultdict(list)
    for node in sorted(project.nodes, key=node_sort_key):
        children[node.parent_id].append(node)
    sites = tuple(children[None])
    buildings = tuple(n for site in sites for n in children[site.id])
    v4 = {a.node_id: a.network for a in plan.v4_allocations}
    v6 = {a.node_id: a.network for a in plan.v6_allocations}
    reservations = {r.node_id: r for r in plan.v4_reservations}
    infos = {r.node_id: r for r in plan.v6_segments}
    by_id = {n.id: n for n in project.nodes}
    rows = []
    for building in buildings:
        site = by_id[building.parent_id or ""]
        for segment in children[building.id]:
            if not isinstance(segment, Segment):
                continue
            infrastructure = segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK)
            growth = segment.growth_pct
            if growth is None:
                growth = 0 if infrastructure else project.settings.growth_pct
            grown = (
                segment.hosts or (2 if segment.role is SegmentRole.P2P else 1)
                if infrastructure
                else grown_host_count(segment.hosts, growth)
            )
            rows.append(
                SegmentRow(
                    site=site,
                    building=building,
                    segment=segment,
                    v4=v4.get(segment.id),
                    v6=v6.get(segment.id),
                    reservation=reservations.get(segment.id),
                    info6=infos.get(segment.id),
                    growth_pct=growth,
                    grown_hosts=grown,
                    findings=tuple(
                        f
                        for f in plan.findings
                        if f.level is not FindingLevel.INFO
                        and f.node_id in (None, site.id, building.id, segment.id)
                    ),
                )
            )
    return Report(project, plan, sites, buildings, tuple(rows))


def ipv6_description(project: Project) -> str:
    if not project.v6_active:
        return tr("Wyłączone (konfiguracja zachowana)") if project.v6_prefix else tr("Wyłączone")
    return str(project.v6_prefix) if project.v6_prefix else "—"


def address_range(value: AddressRange | None) -> str:
    return "" if value is None else f"{value.first}–{value.last}"


def percentage(value: Fraction | None) -> str:
    if value is None:
        return tr("n/d")
    scaled = (value.numerator * 10000 + value.denominator // 2) // value.denominator
    return f"{scaled // 100}.{scaled % 100:02d}%"
