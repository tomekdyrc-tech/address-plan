"""Dual-stack freeze and infrastructure pin persistence."""

from dataclasses import replace
from ipaddress import IPv6Network

import pytest

from adresplan.core.freeze import freeze
from adresplan.core.models import IPv6SubnetStrategy, Node, NodeKind, Segment, SegmentRole
from adresplan.core.plan import build_plan


def test_dual_stack_freeze_is_pure_idempotent_and_pins_infrastructure(t5_project) -> None:
    before = build_plan(t5_project)
    frozen = freeze(t5_project, before)
    expected = {a.node_id: a.network for a in before.v6_allocations}
    assert all(n.pinned_v6 == expected[n.id] for n in frozen.nodes)
    assert frozen.pinned_v6_infrastructure == before.v6_infrastructure
    assert t5_project.pinned_v6_infrastructure == () and all(
        n.pinned_v6 is None for n in t5_project.nodes
    )
    assert build_plan(frozen) == before
    assert freeze(frozen, build_plan(frozen)) == frozen


def test_adding_lan_link_and_loopback_preserves_all_addresses_in_both_families(t5_project) -> None:
    before = build_plan(t5_project)
    frozen = freeze(t5_project, before)
    extended = replace(
        frozen,
        nodes=(
            *frozen.nodes,
            Segment(id="new-lan", name="New LAN", parent_id="a", hosts=1),
            Segment(id="new-link", name="New link", parent_id="a", role=SegmentRole.P2P),
            Segment(id="new-loop", name="New loop", parent_id="a", role=SegmentRole.LOOPBACK),
        ),
    )
    after = build_plan(extended)
    assert after.is_complete
    for old, new in [
        (before.v4_allocations, after.v4_allocations),
        (before.v6_allocations, after.v6_allocations),
    ]:
        assigned = {a.node_id: a.network for a in new}
        assert all(assigned[a.node_id] == a.network for a in old)
    assert after.v6_infrastructure == before.v6_infrastructure
    assigned = {a.node_id: str(a.network) for a in after.v6_allocations}
    assert assigned["new-lan"] == "2001:db8:abcd:107::/64"
    assert assigned["new-link"] == "2001:db8:abcd:1::4/127"
    assert assigned["new-loop"] == "2001:db8:abcd:2::1/128"


def test_infrastructure_size_change_cannot_silently_move_frozen_pools(t5_project) -> None:
    frozen = freeze(t5_project, build_plan(t5_project))
    changed = replace(frozen, settings=replace(frozen.settings, v6_infra_prefix=52))
    plan = build_plan(changed)
    assert not plan.is_complete and any(
        f.code == "invalid_v6_infrastructure_pin" for f in plan.findings
    )
    with pytest.raises(ValueError):
        freeze(changed, plan)


def test_changed_frozen_pool_does_not_readdress_pinned_endpoints(t5_project) -> None:
    frozen = freeze(t5_project, build_plan(t5_project))
    pools = frozen.pinned_v6_infrastructure[0]
    changed = replace(
        frozen,
        pinned_v6_infrastructure=(
            replace(pools, p2p_pool=pools.loopback_pool, loopback_pool=pools.p2p_pool),
        ),
    )
    plan = build_plan(changed)
    assert not plan.is_complete and any(f.code == "v6_pin_outside_parent" for f in plan.findings)
    assert "link0" not in {a.node_id for a in plan.v6_allocations}


def test_vlan_strategy_change_reports_mismatching_pins_instead_of_moving_them(t5_project) -> None:
    before = build_plan(t5_project)
    frozen = freeze(t5_project, before)
    changed = replace(
        frozen,
        settings=replace(
            frozen.settings, v6_subnet_strategy=IPv6SubnetStrategy.VLAN_DECIMAL_AS_HEX
        ),
        nodes=tuple(
            replace(n, vlan_id=n.sort_order + 1)
            if isinstance(n, Segment) and n.role is SegmentRole.LAN
            else n
            for n in frozen.nodes
        ),
    )
    plan = build_plan(changed)
    assert not plan.is_complete and any(f.code == "v6_vlan_pin_mismatch" for f in plan.findings)
    old = {a.node_id: a.network for a in before.v6_allocations}
    assert all(a.network == old[a.node_id] for a in plan.v6_allocations)


def test_new_site_does_not_move_existing_frozen_site_when_pool_is_full(t5_project) -> None:
    before = build_plan(t5_project)
    frozen = freeze(t5_project, before)
    extended = replace(
        frozen,
        nodes=(
            *frozen.nodes,
            Node(id="site2", name="Site2", kind=NodeKind.SITE),
            Node(id="building2", name="Building2", kind=NodeKind.BUILDING, parent_id="site2"),
            Segment(id="new", name="New", parent_id="building2", hosts=1),
        ),
    )
    plan = build_plan(extended)
    assert not plan.is_complete and any(f.code == "v6_insufficient_space" for f in plan.findings)
    assigned = {a.node_id: a.network for a in plan.v6_allocations}
    assert all(assigned[a.node_id] == a.network for a in before.v6_allocations)


def test_foreign_incomplete_and_tampered_ipv6_plans_cannot_be_frozen(t5_project) -> None:
    plan = build_plan(t5_project)
    with pytest.raises(ValueError):
        freeze(t5_project, replace(plan, v6_allocations=plan.v6_allocations[:-1]))
    with pytest.raises(ValueError):
        freeze(t5_project, replace(plan, v6_infrastructure=()))
    changed = replace(t5_project, v6_prefix=IPv6Network("2001:db8:abce::/48"))
    with pytest.raises(ValueError):
        freeze(changed, plan)
