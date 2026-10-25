"""Reference T5, alternate layouts, LAN numbering and IPv6 pin behavior."""

from dataclasses import replace
from ipaddress import IPv6Address, IPv6Network

import pytest

from adresplan.core.models import (
    IPv6GatewayMode,
    IPv6Kind,
    IPv6PoolKind,
    IPv6RAMode,
    IPv6SubnetStrategy,
    Node,
    NodeKind,
    Segment,
    SegmentRole,
)
from adresplan.core.plan import build_plan
from adresplan.core.plan4 import build_plan_v4
from adresplan.core.plan6 import build_plan_v6


def vlan_project(project):
    values = [10, 20, 99, 30, 40, 50, 60]
    return replace(
        project,
        settings=replace(
            project.settings, v6_subnet_strategy=IPv6SubnetStrategy.VLAN_DECIMAL_AS_HEX
        ),
        nodes=tuple(
            replace(n, vlan_id=values[n.sort_order])
            if isinstance(n, Segment) and n.role in (SegmentRole.LAN, SegmentRole.MGMT)
            else n
            for n in project.nodes
        ),
    )


def test_t5_exact_hierarchy_and_infrastructure(t5_project) -> None:
    plan = build_plan(t5_project)
    assert plan.is_complete
    actual = {a.node_id: str(a.network) for a in plan.v6_allocations}
    assert {key: actual[key] for key in ["site", "a", "b", "c", "link0", "link1", "loop"]} == {
        "site": "2001:db8:abcd::/48",
        "a": "2001:db8:abcd:100::/56",
        "b": "2001:db8:abcd:200::/56",
        "c": "2001:db8:abcd:300::/56",
        "link0": "2001:db8:abcd:1::/127",
        "link1": "2001:db8:abcd:1::2/127",
        "loop": "2001:db8:abcd:2::/128",
    }
    assert [actual[f"a{i}"] for i in range(7)] == [
        f"2001:db8:abcd:{0x100 + i:x}::/64" for i in range(7)
    ]
    pools = plan.v6_infrastructure[0]
    assert str(pools.network) == "2001:db8:abcd::/56"
    assert str(pools.reserved_pool) == "2001:db8:abcd::/64"
    assert str(pools.p2p_pool) == "2001:db8:abcd:1::/64"
    assert str(pools.loopback_pool) == "2001:db8:abcd:2::/64"
    info = {i.node_id: i for i in plan.v6_segments}
    assert info["a0"].gateway == IPv6Address("2001:db8:abcd:100::1")
    assert info["a0"].ra_mode is IPv6RAMode.SLAAC
    assert info["a0"].compressed == "2001:db8:abcd:100::/64"
    assert info["a0"].exploded == "2001:0db8:abcd:0100:0000:0000:0000:0000/64"
    assert info["link0"].endpoints == (
        IPv6Address("2001:db8:abcd:1::"),
        IPv6Address("2001:db8:abcd:1::1"),
    )
    assert info["loop"].endpoints == (IPv6Address("2001:db8:abcd:2::"),)
    assert info["link0"].gateway is None and info["link0"].reverse_zone is None
    v4 = build_plan_v4(t5_project)
    assert plan.v4_allocations == v4.v4_allocations and plan.v4_reservations == v4.v4_reservations
    assert plan.v6_allocations == build_plan_v6(t5_project).v6_allocations


def test_input_order_does_not_change_the_plan(t5_project) -> None:
    assert build_plan(t5_project) == build_plan(
        replace(t5_project, nodes=tuple(reversed(t5_project.nodes)))
    )


def test_t5_vlan_digits_as_hex(t5_project) -> None:
    plan = build_plan(vlan_project(t5_project))
    assert plan.is_complete
    actual = {a.node_id: str(a.network) for a in plan.v6_allocations}
    assert (actual["a0"], actual["a1"], actual["a2"]) == (
        "2001:db8:abcd:110::/64",
        "2001:db8:abcd:120::/64",
        "2001:db8:abcd:199::/64",
    )


def test_vlan_110_is_an_error_in_slash_56_and_works_in_slash_52(t5_project) -> None:
    data = vlan_project(t5_project)
    data = replace(
        data, nodes=tuple(replace(n, vlan_id=110) if n.id == "a0" else n for n in data.nodes)
    )
    plan = build_plan(data)
    assert not plan.is_complete
    assert any(
        f.code == "v6_vlan_offset_outside_building" and f.node_id == "a0" for f in plan.findings
    )
    assert next(a.network for a in plan.v6_allocations if a.node_id == "a").prefixlen == 56
    bigger = build_plan(replace(data, settings=replace(data.settings, v6_building_prefix=52)))
    assert bigger.is_complete
    assert next(a.network for a in bigger.v6_allocations if a.node_id == "a0") == IPv6Network(
        "2001:db8:abcd:1110::/64"
    )


@pytest.mark.parametrize("value", [None, 0, 1000, 4094, True])
def test_vlan_strategy_requires_supported_vlan_ids(t5_project, value) -> None:
    data = vlan_project(t5_project)
    data = replace(
        data, nodes=tuple(replace(n, vlan_id=value) if n.id == "a0" else n for n in data.nodes)
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == "v6_vlan_required_1_999" for f in plan.findings)


def test_duplicate_vlan_offsets_collide_within_a_building(t5_project) -> None:
    data = vlan_project(t5_project)
    data = replace(
        data, nodes=tuple(replace(n, vlan_id=10) if n.id == "a1" else n for n in data.nodes)
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == "v6_subnet_collision" for f in plan.findings)


def test_link_local_gateway_and_ra_mode_override(t5_project) -> None:
    data = replace(
        t5_project,
        settings=replace(t5_project.settings, v6_gateway_mode=IPv6GatewayMode.LINK_LOCAL),
        nodes=tuple(
            replace(n, ra_mode=IPv6RAMode.DHCPV6) if n.id == "a0" else n for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    infos = {i.node_id: i for i in plan.v6_segments}
    assert (
        infos["a0"].gateway == IPv6Address("fe80::1") and infos["a0"].ra_mode is IPv6RAMode.DHCPV6
    )
    assert infos["a1"].ra_mode is IPv6RAMode.SLAAC


def test_small_slash_56_project_uses_explicit_slash_60_layout(t5_project) -> None:
    data = replace(
        t5_project,
        v6_prefix=IPv6Network("2001:db8:abcd::/56"),
        settings=replace(
            t5_project.settings, v6_site_prefix=56, v6_infra_prefix=60, v6_building_prefix=60
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    actual = {a.node_id: str(a.network) for a in plan.v6_allocations}
    assert actual["a"] == "2001:db8:abcd:10::/60" and actual["a0"] == "2001:db8:abcd:10::/64"
    assert str(plan.v6_infrastructure[0].network) == "2001:db8:abcd::/60"


def test_two_sites_need_more_than_one_slash_48(t5_project) -> None:
    extra = (
        Node(id="site2", name="Site2", kind=NodeKind.SITE, sort_order=1),
        Node(id="building2", name="Building2", kind=NodeKind.BUILDING, parent_id="site2"),
        Segment(id="segment2", name="Segment2", parent_id="building2", hosts=10),
    )
    data = replace(t5_project, nodes=(*t5_project.nodes, *extra))
    plan = build_plan(data)
    assert not plan.is_complete
    assert any(f.code == "v6_insufficient_space" and f.node_id == "site2" for f in plan.findings)
    larger = build_plan(replace(data, v6_prefix=IPv6Network("2001:db8:abc0::/44")))
    assert larger.is_complete
    assert [str(a.network) for a in larger.v6_allocations if a.node_id in ("site", "site2")] == [
        "2001:db8:abc0::/48",
        "2001:db8:abc1::/48",
    ]


def test_disabled_segment_keeps_ipv4_but_gets_no_ipv6(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(replace(n, v6_enabled=False) if n.id == "a0" else n for n in t5_project.nodes),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert "a0" in {a.node_id for a in plan.v4_allocations}
    assert "a0" not in {a.node_id for a in plan.v6_allocations}


def test_disabled_project_has_no_ipv6_outputs(t5_project) -> None:
    plan = build_plan(replace(t5_project, v6_prefix=None))
    assert (
        plan.is_complete
        and not plan.v6_allocations
        and not plan.v6_infrastructure
        and not plan.v6_metrics
    )
    all_disabled = replace(
        t5_project,
        nodes=tuple(
            replace(n, v6_enabled=False) if isinstance(n, Segment) else n for n in t5_project.nodes
        ),
    )
    plan = build_plan(all_disabled)
    assert plan.is_complete and not plan.v6_allocations
    assert len(plan.v6_metrics) == 1 and plan.v6_metrics[0].kind is IPv6PoolKind.PROJECT


@pytest.mark.parametrize(
    ("prefix", "kind"), [("fd12:3456:789a::/48", IPv6Kind.ULA), ("2001:1234::/48", IPv6Kind.GUA)]
)
def test_ula_and_gua_projects(prefix, kind, t5_project) -> None:
    assert build_plan(replace(t5_project, v6_prefix=IPv6Network(prefix), v6_kind=kind)).is_complete


def test_pinned_lan_anchors_building_without_entering_infrastructure(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(
            replace(n, pinned_v6=IPv6Network("2001:db8:abcd:500::/64")) if n.id == "a0" else n
            for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    addresses = {a.node_id: a.network for a in plan.v6_allocations}
    assert addresses["a"] == IPv6Network("2001:db8:abcd:500::/56")
    assert addresses["a0"] == IPv6Network("2001:db8:abcd:500::/64")


def test_lan_pin_cannot_occupy_reserved_infrastructure(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(
            replace(n, pinned_v6=IPv6Network("2001:db8:abcd:1::/64")) if n.id == "a0" else n
            for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == "v6_subnet_collision" for f in plan.findings)


def test_far_lan_pins_grow_the_building_to_a_common_nibble_block(t5_project) -> None:
    pins = {
        "a0": IPv6Network("2001:db8:abcd:1100::/64"),
        "a1": IPv6Network("2001:db8:abcd:1200::/64"),
    }
    data = replace(
        t5_project,
        nodes=tuple(
            replace(n, pinned_v6=pins[n.id]) if n.id in pins else n for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert next(a.network for a in plan.v6_allocations if a.node_id == "a") == IPv6Network(
        "2001:db8:abcd:1000::/52"
    )


def test_site_anchor_can_be_derived_from_its_descendants(t5_project) -> None:
    data = replace(
        t5_project,
        v6_prefix=IPv6Network("2001:db8:abc0::/44"),
        nodes=tuple(
            replace(n, pinned_v6=IPv6Network("2001:db8:abc5:100::/64")) if n.id == "a0" else n
            for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert next(a.network for a in plan.v6_allocations if a.node_id == "site") == IPv6Network(
        "2001:db8:abc5::/48"
    )


def test_pins_cannot_silently_expand_a_site_beyond_its_configured_size(t5_project) -> None:
    pins = {
        "a0": IPv6Network("2001:db8:abc5:100::/64"),
        "b0": IPv6Network("2001:db8:abc6:100::/64"),
    }
    data = replace(
        t5_project,
        v6_prefix=IPv6Network("2001:db8:abc0::/44"),
        nodes=tuple(
            replace(n, pinned_v6=pins[n.id]) if n.id in pins else n for n in t5_project.nodes
        ),
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == "v6_site_anchor_span" for f in plan.findings)


def test_small_pool_with_default_large_layout_is_an_error_not_implicit_reconfiguration(
    t5_project,
) -> None:
    plan = build_plan(replace(t5_project, v6_prefix=IPv6Network("2001:db8:abcd::/56")))
    assert not plan.is_complete and any(f.code == "invalid_v6_settings" for f in plan.findings)


def test_large_address_spaces_are_never_eagerly_expanded(t5_project, monkeypatch) -> None:
    original = IPv6Network.subnets

    def forbidden(*args, **kwargs):
        raise AssertionError("host enumeration or randomness is forbidden in core")

    def bounded(self, *args, **kwargs):
        for i, network in enumerate(original(self, *args, **kwargs)):
            if i >= 256:
                raise AssertionError("unbounded subnet enumeration")
            yield network

    monkeypatch.setattr(IPv6Network, "hosts", forbidden)
    monkeypatch.setattr(IPv6Network, "subnets", bounded)
    monkeypatch.setattr("secrets.token_bytes", forbidden)
    assert build_plan(t5_project).is_complete
    assert build_plan(t5_project) == build_plan(t5_project)


def test_infrastructure_only_site_does_not_need_an_unused_building_block(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(n for n in t5_project.nodes if n.id in ("site", "a", "link0", "link1", "loop")),
        v6_prefix=IPv6Network("2001:db8:abcd::/60"),
        settings=replace(
            t5_project.settings, v6_site_prefix=60, v6_infra_prefix=60, v6_building_prefix=60
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert "a" not in {a.node_id for a in plan.v6_allocations}
    assert {i.node_id for i in plan.v6_segments} == {"link0", "link1", "loop"}


def test_pinned_empty_site_is_a_deliberate_reservation(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=(Node(id="site", name="Site", kind=NodeKind.SITE, pinned_v6=t5_project.v6_prefix),),
    )
    plan = build_plan(data)
    assert plan.is_complete and len(plan.v6_infrastructure) == 1
    assert len(plan.v6_allocations) == 1 and not plan.v6_segments
