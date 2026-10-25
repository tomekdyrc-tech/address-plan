"""Whole-tree invariants, independent of reference examples."""

from dataclasses import replace
from ipaddress import IPv4Address, IPv4Network
from itertools import combinations

from hypothesis import given
from hypothesis import strategies as st

from adresplan.core.freeze import freeze
from adresplan.core.models import (
    GatewayPosition,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
    SegmentRole,
)
from adresplan.core.plan import build_plan


@given(
    tree=st.lists(
        st.lists(st.lists(st.integers(1, 60), min_size=1, max_size=4), min_size=1, max_size=3),
        min_size=1,
        max_size=3,
    ),
    growth=st.integers(0, 50),
)
def test_tree_partition_determinism_and_freeze(tree, growth) -> None:
    nodes = []
    for site, buildings in enumerate(tree):
        site_id = f"site{site}"
        nodes.append(Node(id=site_id, name=site_id, kind=NodeKind.SITE, sort_order=site))
        for building, segments in enumerate(buildings):
            building_id = f"{site_id}b{building}"
            nodes.append(
                Node(
                    id=building_id,
                    name=building_id,
                    kind=NodeKind.BUILDING,
                    parent_id=site_id,
                    sort_order=building,
                )
            )
            for number, hosts in enumerate(segments):
                node_id = f"{building_id}s{number}"
                nodes.append(
                    Segment(
                        id=node_id,
                        name=node_id,
                        parent_id=building_id,
                        hosts=hosts,
                        sort_order=number,
                    )
                )
    data = Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/16"),
        nodes=tuple(nodes),
        settings=ProjectSettings(growth_pct=growth, gateway=GatewayPosition.NONE, gateway_addrs=0),
    )
    plan = build_plan(data)
    assert plan.is_complete
    leaf_ids = {n.id for n in nodes if isinstance(n, Segment)}
    leaves = [a.network for a in plan.v4_allocations if a.node_id in leaf_ids]
    all_free = [f.network for f in plan.free_blocks]
    assert len(leaves) == len(leaf_ids)
    assert all(not a.overlaps(b) for a, b in combinations(leaves + all_free, 2))
    assert sum(n.num_addresses for n in leaves + all_free) == data.v4_pool.num_addresses
    assert build_plan(replace(data, nodes=tuple(reversed(data.nodes)))) == plan
    frozen = freeze(data, plan)
    assert build_plan(frozen) == plan
    assert freeze(frozen, build_plan(frozen)) == frozen
    building_id = next(n.id for n in nodes if n.kind is NodeKind.BUILDING)
    extended = replace(
        frozen, nodes=(*frozen.nodes, Segment(id="new", name="New", parent_id=building_id, hosts=1))
    )
    after = build_plan(extended)
    actual = {a.node_id: a.network for a in after.v4_allocations}
    assert all(actual[a.node_id] == a.network for a in plan.v4_allocations)


@given(
    offsets=st.lists(st.integers(0, 255), min_size=1, max_size=6, unique=True),
    hosts=st.integers(1, 100),
)
def test_random_fixed_leaf_addresses_anchor_all_ancestors(offsets, hosts) -> None:
    base = int(IPv4Address("10.0.0.0"))
    nodes = [
        Node(id="site", name="Site", kind=NodeKind.SITE),
        Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="site"),
        *(
            Segment(
                id=f"pin{i}",
                name=f"Pin{i}",
                parent_id="b",
                role=SegmentRole.LOOPBACK,
                pinned_v4=IPv4Network((base + offset, 32)),
            )
            for i, offset in enumerate(offsets)
        ),
        Segment(id="auto", name="Auto", parent_id="b", hosts=hosts),
    ]
    data = Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/16"),
        nodes=tuple(nodes),
        settings=ProjectSettings(growth_pct=0, gateway=GatewayPosition.NONE, gateway_addrs=0),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assigned = {a.node_id: a.network for a in plan.v4_allocations}
    assert all(
        assigned[f"pin{i}"] == IPv4Network((base + offset, 32)) for i, offset in enumerate(offsets)
    )
    assert assigned["b"].subnet_of(assigned["site"])
    assert all(assigned[f"pin{i}"].subnet_of(assigned["b"]) for i in range(len(offsets)))
    assert assigned["auto"].subnet_of(assigned["b"])
