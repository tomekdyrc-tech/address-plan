"""Demonstrate the T4 hierarchy, usable ranges and freeze behavior."""

from dataclasses import replace
from ipaddress import IPv4Network

from adresplan.core.freeze import freeze
from adresplan.core.models import (
    AddressRange,
    GatewayPosition,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
    SegmentRole,
)
from adresplan.core.plan import build_plan


def sample_project() -> Project:
    nodes: list[Node] = [
        Node(
            id="site", name="Lokalizacja", kind=NodeKind.SITE, pinned_v4=IPv4Network("10.20.0.0/20")
        )
    ]
    entries = {
        "a": [
            ("WiFi-goscie", 200, SegmentRole.LAN),
            ("Biuro", 60, SegmentRole.LAN),
            ("VoIP", 45, SegmentRole.LAN),
            ("Szkolenia", 28, SegmentRole.LAN),
            ("Kamery", 20, SegmentRole.LAN),
            ("Serwery", 12, SegmentRole.LAN),
            ("Zarzadzanie", 10, SegmentRole.MGMT),
            ("Link-R1-SW1", 0, SegmentRole.P2P),
            ("Link-R1-SW2", 0, SegmentRole.P2P),
            ("Loopback-R1", 0, SegmentRole.LOOPBACK),
        ],
        "b": [
            ("Sala", 100, SegmentRole.LAN),
            ("Biuro", 40, SegmentRole.LAN),
            ("AV", 20, SegmentRole.LAN),
        ],
        "c": [("Plebania", 30, SegmentRole.LAN)],
    }
    for order, (building, segments) in enumerate(entries.items()):
        nodes.append(
            Node(
                id=building,
                name=f"Budynek {building.upper()}",
                kind=NodeKind.BUILDING,
                parent_id="site",
                sort_order=order,
            )
        )
        nodes.extend(
            Segment(
                id=f"{building}-{index}",
                name=name,
                parent_id=building,
                hosts=hosts,
                role=role,
                sort_order=index,
            )
            for index, (name, hosts, role) in enumerate(segments)
        )
    return Project(
        id="demo-t4",
        name="Przyklad T4",
        v4_pool=IPv4Network("10.20.0.0/20"),
        nodes=tuple(nodes),
        settings=ProjectSettings(growth_pct=0, gateway=GatewayPosition.NONE, gateway_addrs=0),
    )


def format_range(value: AddressRange | None) -> str:
    return f"{value.first} - {value.last}" if value else "n/d"


def main() -> None:
    project = sample_project()
    plan = build_plan(project)
    names = {node.id: node.name for node in project.nodes}
    print("T4: hierarchia IPv4; zapas=0%, bramy=0, statyczne=0")
    for allocation in plan.v4_allocations:
        print(f"{names[allocation.node_id]:<22} {allocation.network}")
    print("\nWykorzystanie w blokach budynkow:")
    for metrics in plan.v4_metrics:
        if metrics.parent_id in ("a", "b", "c"):
            print(
                f"{names[metrics.parent_id]}: "
                f"{metrics.allocated_addresses}/{metrics.network.num_addresses}, "
                f"wolne {metrics.free_addresses}"
            )
    print("\nWolne bloki poza budynkami:")
    for free in plan.free_blocks:
        if free.parent_id == "site":
            print(free.network)
    reservation = next(r for r in plan.v4_reservations if r.node_id == "b-2")
    print(f"\nZakres DHCP segmentu AV: {format_range(reservation.dhcp_range)}")
    frozen = freeze(project, plan)
    extended = replace(
        frozen,
        nodes=(*frozen.nodes, Segment(id="new", name="Nowy segment", parent_id="a", hosts=1)),
    )
    after = build_plan(extended)
    addresses = {a.node_id: a.network for a in after.v4_allocations}
    unchanged = all(addresses[a.node_id] == a.network for a in plan.v4_allocations)
    print(f"Nowy segment po zamrozeniu: {addresses.get('new', 'brak miejsca')}")
    print("Dotychczasowe adresy:", "bez zmian" if unchanged else "ZMIENIONE")
    print("Wynik:", "poprawny" if after.is_complete else "z bledami")


if __name__ == "__main__":
    main()
