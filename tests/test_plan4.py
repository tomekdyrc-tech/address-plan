"""Exact T4 hierarchy, anchored parents, partial plans and per-level accounting."""

from dataclasses import replace
from fractions import Fraction
from ipaddress import IPv4Network
from itertools import combinations

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
from adresplan.core.plan4 import build_plan_v4


def small_project(*segments: Segment, building_pin: str | None = None) -> Project:
    return Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/16"),
        settings=ProjectSettings(growth_pct=0, gateway=GatewayPosition.NONE, gateway_addrs=0),
        nodes=(
            Node(id="site", name="Site", kind=NodeKind.SITE),
            Node(
                id="b",
                name="B",
                kind=NodeKind.BUILDING,
                parent_id="site",
                pinned_v4=IPv4Network(building_pin) if building_pin else None,
            ),
            *(replace(s, parent_id="b") for s in segments),
        ),
    )


def test_t4_exact_addresses_and_free_blocks(t4_project) -> None:
    plan = build_plan(t4_project)
    assert plan.is_complete
    assert {a.node_id: str(a.network) for a in plan.v4_allocations} == {
        "site": "10.20.0.0/20",
        "a": "10.20.0.0/23",
        "b": "10.20.2.0/24",
        "c": "10.20.3.0/27",
        "a_wifi": "10.20.0.0/24",
        "a_office": "10.20.1.0/26",
        "a_voip": "10.20.1.64/26",
        "a_training": "10.20.1.128/27",
        "a_cameras": "10.20.1.160/27",
        "a_servers": "10.20.1.192/28",
        "a_mgmt": "10.20.1.208/28",
        "a_link1": "10.20.1.224/31",
        "a_link2": "10.20.1.226/31",
        "a_loop": "10.20.1.228/32",
        "b_hall": "10.20.2.0/25",
        "b_office": "10.20.2.128/26",
        "b_av": "10.20.2.192/27",
        "c_residence": "10.20.3.0/27",
    }
    assert [str(f.network) for f in plan.free_blocks if f.parent_id == "site"] == [
        "10.20.3.32/27",
        "10.20.3.64/26",
        "10.20.3.128/25",
        "10.20.4.0/22",
        "10.20.8.0/21",
    ]
    metrics = {m.parent_id: m for m in plan.v4_metrics}
    assert (metrics["site"].allocated_addresses, metrics["site"].free_addresses) == (800, 3296)
    assert metrics["site"].continuity == Fraction(64, 103)
    assert metrics["a"].free_addresses == 27 and metrics["b"].free_addresses == 32
    assert metrics["c"].continuity is None and metrics[None].free_addresses == 0
    assert sum(r.network.num_addresses for r in plan.v4_reservations) == 741
    assert sum(f.network.num_addresses for f in plan.free_blocks) == 3355
    assert build_plan_v4(t4_project) == plan


def test_t4_is_deterministic_after_reordering_input(t4_project) -> None:
    assert build_plan(t4_project) == build_plan(
        replace(t4_project, nodes=tuple(reversed(t4_project.nodes)))
    )


def test_t4_without_fixed_site_uses_minimum_slash_22(t4_project) -> None:
    data = replace(
        t4_project,
        nodes=tuple(replace(n, pinned_v4=None) if n.id == "site" else n for n in t4_project.nodes),
    )
    assert (
        next(a.network for a in build_plan(data).v4_allocations if a.node_id == "site").prefixlen
        == 22
    )


def test_all_immediate_child_partitions_are_complete(t4_project) -> None:
    plan = build_plan(t4_project)
    nodes = {n.id: n for n in t4_project.nodes}
    for metric in plan.v4_metrics:
        children = [
            a.network for a in plan.v4_allocations if nodes[a.node_id].parent_id == metric.parent_id
        ]
        free = [f.network for f in plan.free_blocks if f.parent_id == metric.parent_id]
        assert all(not a.overlaps(b) for a, b in combinations(children + free, 2))
        assert all(n.subnet_of(metric.network) for n in children + free)
        assert sum(n.num_addresses for n in children + free) == metric.network.num_addresses


def test_pinned_leaf_anchors_unpinned_building_and_site() -> None:
    data = small_project(
        Segment(id="pinned", name="Pinned", hosts=100, pinned_v4=IPv4Network("10.0.200.0/24")),
        Segment(id="auto", name="Auto", hosts=100),
    )
    plan = build_plan(data)
    assert plan.is_complete
    actual = {a.node_id: str(a.network) for a in plan.v4_allocations}
    assert actual["site"] == actual["b"] == "10.0.200.0/23"
    assert actual["pinned"] == "10.0.200.0/24" and actual["auto"] == "10.0.201.0/25"


def test_far_apart_pins_require_their_common_cover_not_just_sum() -> None:
    data = small_project(
        Segment(id="one", name="One", hosts=1, pinned_v4=IPv4Network("10.0.0.0/30")),
        Segment(id="two", name="Two", hosts=1, pinned_v4=IPv4Network("10.0.0.252/30")),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert next(a.network for a in plan.v4_allocations if a.node_id == "b") == IPv4Network(
        "10.0.0.0/24"
    )


def test_simulation_grows_anchored_block_to_overcome_fragmentation() -> None:
    data = small_project(
        Segment(
            id="one", name="One", role=SegmentRole.LOOPBACK, pinned_v4=IPv4Network("10.0.0.0/32")
        ),
        Segment(
            id="two", name="Two", role=SegmentRole.LOOPBACK, pinned_v4=IPv4Network("10.0.0.128/32")
        ),
        Segment(id="auto", name="Auto", hosts=100),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert next(a.network for a in plan.v4_allocations if a.node_id == "b") == IPv4Network(
        "10.0.0.0/23"
    )
    assert next(a.network for a in plan.v4_allocations if a.node_id == "auto") == IPv4Network(
        "10.0.1.0/25"
    )


def test_explicit_parent_does_not_grow_when_children_do_not_fit() -> None:
    data = small_project(
        Segment(id="one", name="One", hosts=30),
        Segment(id="two", name="Two", hosts=30),
        building_pin="10.0.0.0/27",
    )
    plan = build_plan(data)
    assert not plan.is_complete
    assert next(a.network for a in plan.v4_allocations if a.node_id == "b") == IPv4Network(
        "10.0.0.0/27"
    )
    assert any(f.code == "insufficient_space" and f.node_id == "two" for f in plan.findings)


def test_child_pin_outside_explicit_parent_is_not_moved() -> None:
    data = small_project(
        Segment(id="one", name="One", hosts=10, pinned_v4=IPv4Network("10.0.1.0/28")),
        building_pin="10.0.0.0/24",
    )
    plan = build_plan(data)
    assert not plan.is_complete
    assert any(f.code == "pinned_outside_pool" and f.node_id == "one" for f in plan.findings)
    assert "one" not in {a.node_id for a in plan.v4_allocations}


def test_bad_segment_does_not_prevent_independent_segment_from_allocating() -> None:
    plan = build_plan(
        small_project(Segment(id="bad", name="Bad", hosts=0), Segment(id="ok", name="OK", hosts=10))
    )
    assert not plan.is_complete
    assert any(
        f.code == "invalid_segment_requirements" and f.node_id == "bad" for f in plan.findings
    )
    assert "ok" in {a.node_id for a in plan.v4_allocations}


def test_empty_project_and_empty_unpinned_nodes_do_not_allocate_phantom_blocks() -> None:
    for data in [small_project(), replace(small_project(), nodes=())]:
        plan = build_plan(data)
        assert plan.is_complete and plan.v4_allocations == ()
        assert len(plan.free_blocks) == 1 and plan.free_blocks[0].network == data.v4_pool


def test_pinned_empty_parent_reserves_its_whole_block() -> None:
    plan = build_plan(small_project(building_pin="10.0.4.0/24"))
    assert plan.is_complete
    assert any(f.parent_id == "b" and str(f.network) == "10.0.4.0/24" for f in plan.free_blocks)


def test_infrastructure_oversized_pin_is_a_reported_error() -> None:
    plan = build_plan(
        small_project(
            Segment(
                id="loop",
                name="Loop",
                role=SegmentRole.LOOPBACK,
                pinned_v4=IPv4Network("10.0.0.0/31"),
            )
        )
    )
    assert not plan.is_complete
    assert any(f.code == "invalid_reservations" for f in plan.findings)


def test_interleaved_pins_in_sibling_buildings_report_summary_block_conflict() -> None:
    data = small_project(
        Segment(
            id="one", name="One", role=SegmentRole.LOOPBACK, pinned_v4=IPv4Network("10.0.0.0/32")
        ),
        Segment(
            id="two", name="Two", role=SegmentRole.LOOPBACK, pinned_v4=IPv4Network("10.0.0.64/32")
        ),
    )
    data = replace(
        data,
        nodes=(
            *data.nodes,
            Node(id="other", name="Other", kind=NodeKind.BUILDING, parent_id="site"),
            Segment(
                id="interleaved",
                name="Interleaved",
                parent_id="other",
                role=SegmentRole.LOOPBACK,
                pinned_v4=IPv4Network("10.0.0.32/32"),
            ),
        ),
    )
    plan = build_plan(data)
    assert not plan.is_complete
    assert any(f.code == "hierarchy_anchor_overlap" and f.node_id == "other" for f in plan.findings)
    assert "interleaved" not in {a.node_id for a in plan.v4_allocations}


def test_pins_inside_project_cannot_force_an_ancestor_outside_project() -> None:
    data = replace(
        small_project(
            Segment(
                id="pin",
                name="Pin",
                role=SegmentRole.LOOPBACK,
                pinned_v4=IPv4Network("10.0.0.0/32"),
            ),
            Segment(id="auto", name="Auto", hosts=10),
        ),
        v4_pool=IPv4Network("10.0.0.0/30"),
    )
    plan = build_plan(data)
    assert not plan.is_complete
    assert any(f.code == "hierarchy_anchor_outside_parent" for f in plan.findings)


def test_overlapping_pinned_segments_are_reported() -> None:
    plan = build_plan(
        small_project(
            Segment(id="a", name="A", hosts=1, pinned_v4=IPv4Network("10.0.0.0/29")),
            Segment(id="b2", name="B", hosts=1, pinned_v4=IPv4Network("10.0.0.4/30")),
        )
    )
    assert not plan.is_complete and any(f.code == "pinned_overlap" for f in plan.findings)


def test_pinned_segment_that_is_too_small_is_not_automatically_replaced() -> None:
    plan = build_plan(
        small_project(
            Segment(id="bad", name="Bad", hosts=100, pinned_v4=IPv4Network("10.0.0.0/30")),
            Segment(id="ok", name="OK", hosts=10),
        )
    )
    assert any(f.code == "pinned_too_small" and f.node_id == "bad" for f in plan.findings)
    assert "bad" not in {a.node_id for a in plan.v4_allocations}
    assert "ok" in {a.node_id for a in plan.v4_allocations}


def test_bad_tree_is_returned_as_a_partial_plan_without_recursing() -> None:
    data = small_project(Segment(id="s", name="S", hosts=10))
    data = replace(
        data, nodes=tuple(replace(n, parent_id="b") if n.id == "b" else n for n in data.nodes)
    )
    plan = build_plan(data)
    assert not plan.is_complete and not plan.v4_allocations
    assert any(f.code == "parent_cycle" for f in plan.findings)
