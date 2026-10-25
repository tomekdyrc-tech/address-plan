"""Demonstrate T5, VLAN numbering, reverse DNS, ULA and dual-stack freeze."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Network

from adresplan.application.ula import generate_ula
from adresplan.core.freeze import freeze
from adresplan.core.ipv6 import count_subnets64
from adresplan.core.models import (
    IPv6SubnetStrategy,
    Node,
    NodeKind,
    Project,
    Segment,
    SegmentRole,
)
from adresplan.core.plan import build_plan


def sample_project() -> Project:
    nodes: list[Node] = [Node(id="site", name="Lokalizacja", kind=NodeKind.SITE)]
    for order, building in enumerate(["a", "b", "c"]):
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
                id=f"{building}{i}", name=f"LAN {i + 1}", parent_id=building, hosts=10, sort_order=i
            )
            for i in range(7)
        )
    nodes.extend(
        [
            Segment(id="link0", name="Link 1", parent_id="a", role=SegmentRole.P2P, sort_order=10),
            Segment(id="link1", name="Link 2", parent_id="a", role=SegmentRole.P2P, sort_order=11),
            Segment(
                id="loop", name="Loopback", parent_id="a", role=SegmentRole.LOOPBACK, sort_order=12
            ),
        ]
    )
    return Project(
        id="t5",
        name="Przyklad T5",
        nodes=tuple(nodes),
        v4_pool=IPv4Network("10.0.0.0/16"),
        v6_prefix=IPv6Network("2001:db8:abcd::/48"),
    )


def main() -> None:
    project = sample_project()
    plan = build_plan(project)
    names = {n.id: n.name for n in project.nodes}
    print("T5: projekt IPv4 + IPv6; strategia sequential")
    for allocation in plan.v6_allocations:
        print(f"{allocation.node_id:<8} {names[allocation.node_id]:<16} {allocation.network}")
    pools = plan.v6_infrastructure[0]
    print(f"\nInfrastruktura: {pools.network}")
    print(
        f"Rezerwa: {pools.reserved_pool}; lacza: {pools.p2p_pool}; loopbacki: {pools.loopback_pool}"
    )
    info = next(i for i in plan.v6_segments if i.node_id == "a0")
    print(f"\nLAN 1, brama: {info.gateway}; RA: {info.ra_mode.value}")
    print(f"Forma skrocona: {info.compressed}")
    print(f"Forma rozwinieta: {info.exploded}")
    print(f"Strefa reverse DNS: {info.reverse_zone}")
    print(
        f"Liczba /64: w /48 = {count_subnets64(project.v6_prefix)}, "
        f"w /56 = {count_subnets64(pools.network)}"
    )

    vlans = [10, 20, 99, 30, 40, 50, 60]
    numbered = replace(
        project,
        settings=replace(
            project.settings, v6_subnet_strategy=IPv6SubnetStrategy.VLAN_DECIMAL_AS_HEX
        ),
        nodes=tuple(
            replace(n, vlan_id=vlans[n.sort_order])
            if isinstance(n, Segment) and n.role is SegmentRole.LAN
            else n
            for n in project.nodes
        ),
    )
    addresses = {a.node_id: a.network for a in build_plan(numbered).v6_allocations}
    print("\nStrategia VLAN jako cyfry hex:")
    for i, vlan in enumerate(vlans[:3]):
        print(f"VLAN {vlan}: {addresses[f'a{i}']}")

    frozen = freeze(project, plan)
    extended = replace(
        frozen,
        nodes=(
            *frozen.nodes,
            Segment(id="new-lan", name="Nowy LAN", parent_id="a", hosts=1),
            Segment(id="new-link", name="Nowe lacze", parent_id="a", role=SegmentRole.P2P),
            Segment(id="new-loop", name="Nowy loopback", parent_id="a", role=SegmentRole.LOOPBACK),
        ),
    )
    after = build_plan(extended)
    unchanged = True
    for before, current in [
        (plan.v4_allocations, after.v4_allocations),
        (plan.v6_allocations, after.v6_allocations),
    ]:
        allocated = {a.node_id: a.network for a in current}
        unchanged = unchanged and all(allocated[a.node_id] == a.network for a in before)
    print("\nPo zamrozeniu i dodaniu trzech segmentow:")
    for a in after.v6_allocations:
        if a.node_id.startswith("new-"):
            print(f"{a.node_id}: {a.network}")
    print("Dotychczasowe adresy IPv4/IPv6:", "bez zmian" if unchanged else "ZMIENIONE")
    print(
        "Pule infrastruktury:",
        "bez zmian" if after.v6_infrastructure == plan.v6_infrastructure else "ZMIENIONE",
    )
    print("Nowy prefiks ULA:", generate_ula())
    print("Wynik:", "poprawny" if after.is_complete else "z bledami")


if __name__ == "__main__":
    main()
