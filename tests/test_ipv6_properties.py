"""Randomized whole-space partition and dual-stack freeze invariants."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Network
from itertools import pairwise

from hypothesis import given, settings
from hypothesis import strategies as st

from adresplan.core.freeze import freeze
from adresplan.core.ipv6 import subnet64_at
from adresplan.core.models import Node, NodeKind, Project, Segment, SegmentRole
from adresplan.core.plan import build_plan
from adresplan.core.validate6 import validate_plan_v6


@settings(max_examples=80)
@given(
    site_count=st.integers(1, 3),
    building_count=st.integers(1, 4),
    lan_count=st.integers(1, 5),
    p2p_count=st.integers(0, 3),
    loop_count=st.integers(0, 2),
    minimum=st.sampled_from([56, 60]),
)
def test_partition_and_freeze_of_random_dual_stack_projects(
    site_count, building_count, lan_count, p2p_count, loop_count, minimum
) -> None:
    nodes = []
    for site in range(site_count):
        sid = f"site{site}"
        nodes.append(Node(id=sid, name=sid, kind=NodeKind.SITE, sort_order=site))
        for building in range(building_count):
            bid = f"{sid}-b{building}"
            nodes.append(
                Node(id=bid, name=bid, kind=NodeKind.BUILDING, parent_id=sid, sort_order=building)
            )
            for i in range(lan_count):
                nodes.append(
                    Segment(
                        id=f"{bid}-lan{i}", name=f"LAN{i}", parent_id=bid, hosts=1, sort_order=i
                    )
                )
            for i in range(p2p_count):
                nodes.append(
                    Segment(
                        id=f"{bid}-link{i}",
                        name=f"Link{i}",
                        parent_id=bid,
                        role=SegmentRole.P2P,
                        sort_order=10 + i,
                    )
                )
            for i in range(loop_count):
                nodes.append(
                    Segment(
                        id=f"{bid}-loop{i}",
                        name=f"Loop{i}",
                        parent_id=bid,
                        role=SegmentRole.LOOPBACK,
                        sort_order=20 + i,
                    )
                )
    data = Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/16"),
        v6_prefix=IPv6Network("2001:db8:abc0::/44"),
        nodes=tuple(nodes),
    )
    data = replace(data, settings=replace(data.settings, v6_building_prefix=minimum))
    plan = build_plan(data)
    assert plan.is_complete and validate_plan_v6(data, plan) == ()
    segment_ids = {n.id for n in nodes if isinstance(n, Segment)}
    leaves = [a.network for a in plan.v6_allocations if a.node_id in segment_ids]
    reserved = [p.reserved_pool for p in plan.v6_infrastructure]
    free = [f.network for f in plan.free_blocks if isinstance(f.network, IPv6Network)]
    partition = sorted(leaves + reserved + free, key=lambda n: int(n.network_address))
    assert all(n.subnet_of(data.v6_prefix) for n in partition)
    assert all(int(a.broadcast_address) < int(b.network_address) for a, b in pairwise(partition))
    assert sum(n.num_addresses for n in partition) == data.v6_prefix.num_addresses
    assert all(
        m.allocated_addresses + m.free_addresses == m.network.num_addresses for m in plan.v6_metrics
    )
    assert build_plan(replace(data, nodes=tuple(reversed(data.nodes)))) == plan
    frozen = freeze(data, plan)
    assert build_plan(frozen) == plan and freeze(frozen, build_plan(frozen)) == frozen


@settings(max_examples=80)
@given(offsets=st.lists(st.integers(0, 255), min_size=5, max_size=5, unique=True))
def test_scattered_lan_pins_and_new_segments_preserve_old_addresses(offsets) -> None:
    nodes = [
        Node(id="site", name="Site", kind=NodeKind.SITE),
        Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="site"),
    ]
    block = IPv6Network("2001:db8:abcd:100::/56")
    nodes.extend(
        Segment(
            id=f"s{i}",
            name=f"S{i}",
            parent_id="b",
            hosts=1,
            sort_order=i,
            pinned_v6=subnet64_at(block, offset),
        )
        for i, offset in enumerate(offsets)
    )
    data = Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/16"),
        v6_prefix=IPv6Network("2001:db8:abcd::/48"),
        nodes=tuple(nodes),
    )
    before = build_plan(data)
    assert before.is_complete
    frozen = freeze(data, before)
    extended = replace(
        frozen, nodes=(*frozen.nodes, Segment(id="new", name="New", parent_id="b", hosts=1))
    )
    after = build_plan(extended)
    assert after.is_complete
    for old, current in [
        (before.v4_allocations, after.v4_allocations),
        (before.v6_allocations, after.v6_allocations),
    ]:
        actual = {a.node_id: a.network for a in current}
        assert all(actual[a.node_id] == a.network for a in old)
    assert after.v6_infrastructure == before.v6_infrastructure
