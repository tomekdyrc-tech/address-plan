"""Invalid IPv6 inputs and independent verification of output plans."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Address, IPv6Network

import pytest

from adresplan.core.models import IPv6Kind, Plan, Segment
from adresplan.core.plan import build_plan
from adresplan.core.validate6 import validate_plan_v6


@pytest.mark.parametrize(
    "options",
    [
        {"v6_site_prefix": 49},
        {"v6_site_prefix": True},
        {"v6_site_prefix": 64},
        {"v6_infra_prefix": 64},
        {"v6_infra_prefix": 44},
        {"v6_building_prefix": 64},
        {"v6_growth_pct": -1},
        {"v6_growth_pct": True},
        {"v6_subnet_strategy": "sequential"},
        {"v6_gateway_mode": "global"},
        {"v6_ra_mode": "slaac"},
        {"v6_link_local_gateway": IPv6Address("2001:db8::1")},
    ],
)
def test_invalid_settings_are_errors_without_exceptions(t5_project, options) -> None:
    plan = build_plan(replace(t5_project, settings=replace(t5_project.settings, **options)))
    assert not plan.is_complete and any(f.code == "invalid_v6_settings" for f in plan.findings)


@pytest.mark.parametrize("prefix", ["fe80::/64", "ff00::/8", "::/128", "fc00::/48"])
def test_unsupported_pool_types(t5_project, prefix) -> None:
    plan = build_plan(replace(t5_project, v6_prefix=IPv6Network(prefix)))
    assert not plan.is_complete and any(f.code == "unsupported_v6_pool" for f in plan.findings)


def test_wrong_family_pool_and_inconsistent_kind_are_errors(t5_project) -> None:
    assert any(
        f.code == "invalid_v6_pool"
        for f in build_plan(replace(t5_project, v6_prefix=IPv4Network("10.0.0.0/16"))).findings
    )
    plan = build_plan(replace(t5_project, v6_kind=IPv6Kind.GUA))
    assert not plan.is_complete and any(f.code == "v6_kind_mismatch" for f in plan.findings)


@pytest.mark.parametrize(
    ("node_id", "pin", "code"),
    [
        ("a0", IPv4Network("10.0.0.0/24"), "v6_pin_family_mismatch"),
        ("a0", IPv6Network("2001:db8:abce::/64"), "v6_pin_outside_project"),
        ("a0", IPv6Network("2001:db8:abcd:100::/80"), "invalid_v6_pin_prefix"),
        ("a", IPv6Network("2001:db8:abcd:100::/64"), "invalid_v6_pin_prefix"),
        ("site", IPv6Network("2001:db8:abcd::/52"), "invalid_v6_pin_prefix"),
        ("link0", IPv6Network("2001:db8:abcd:1::/126"), "invalid_v6_pin_prefix"),
        ("loop", IPv6Network("2001:db8:abcd:2::/127"), "invalid_v6_pin_prefix"),
    ],
)
def test_invalid_pins(t5_project, node_id, pin, code) -> None:
    data = replace(
        t5_project,
        nodes=tuple(replace(n, pinned_v6=pin) if n.id == node_id else n for n in t5_project.nodes),
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == code for f in plan.findings)


def test_disabling_pinned_segment_requires_explicit_unpinning(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(
            replace(n, pinned_v6=IPv6Network("2001:db8:abcd:100::/64"), v6_enabled=False)
            if n.id == "a0"
            else n
            for n in t5_project.nodes
        ),
    )
    assert any(f.code == "v6_disabled_with_pin" for f in build_plan(data).findings)
    assert any(
        f.code == "v6_pool_missing" for f in build_plan(replace(data, v6_prefix=None)).findings
    )


def test_pin_in_wrong_infrastructure_subpool_is_not_moved(t5_project) -> None:
    data = replace(
        t5_project,
        nodes=tuple(
            replace(n, pinned_v6=IPv6Network("2001:db8:abcd:3::/127")) if n.id == "link0" else n
            for n in t5_project.nodes
        ),
    )
    assert any(
        f.code == "v6_pin_outside_parent" and f.node_id == "link0"
        for f in build_plan(data).findings
    )


def test_invalid_duplicate_and_foreign_infrastructure_inputs(t5_project) -> None:
    pool = build_plan(t5_project).v6_infrastructure[0]
    for pins in [
        (pool, pool),
        (replace(pool, site_id="unknown"),),
        (replace(pool, p2p_pool=pool.loopback_pool),),
        (replace(pool, p2p_pool=IPv6Network("2001:db8:abcd:400::/64")),),
        (replace(pool, network=IPv4Network("10.0.0.0/24")),),
    ]:
        plan = build_plan(replace(t5_project, pinned_v6_infrastructure=pins))
        assert not plan.is_complete and any(
            f.code in ("invalid_v6_infrastructure_pin", "duplicate_v6_infrastructure_pin")
            for f in plan.findings
        )


def test_missing_segments_and_infrastructure_are_detected(t5_project) -> None:
    empty = validate_plan_v6(t5_project, Plan(project_id=t5_project.id))
    assert {f.node_id for f in empty if f.code == "v6_missing_segment_allocation"} == {
        n.id for n in t5_project.nodes if isinstance(n, Segment)
    }
    plan = build_plan(t5_project)
    assert validate_plan_v6(t5_project, plan) == ()
    assert any(
        f.code == "v6_infrastructure_missing"
        for f in validate_plan_v6(t5_project, replace(plan, v6_infrastructure=()))
    )


def test_collision_and_parent_containment_validation(t5_project) -> None:
    plan = build_plan(t5_project)
    bad = replace(
        plan,
        v6_allocations=tuple(
            replace(a, network=IPv6Network("2001:db8:abcd:100::/64")) if a.node_id == "a1" else a
            for a in plan.v6_allocations
        ),
    )
    assert any(f.code == "v6_allocation_overlap" for f in validate_plan_v6(t5_project, bad))
    outside = replace(
        plan,
        v6_allocations=tuple(
            replace(a, network=IPv6Network("2001:db8:abcd:900::/64")) if a.node_id == "a0" else a
            for a in plan.v6_allocations
        ),
    )
    assert any(
        f.code == "v6_allocation_outside_parent" for f in validate_plan_v6(t5_project, outside)
    )


def test_output_wrong_family_duplicates_and_foreign_project_are_errors(t5_project) -> None:
    plan = build_plan(t5_project)
    bad = replace(
        plan,
        project_id="foreign",
        v6_allocations=tuple(
            replace(a, network=IPv4Network("10.0.0.0/24")) if a.node_id == "a0" else a
            for a in plan.v6_allocations
        ),
    )
    assert {"v6_plan_project_mismatch", "v6_allocation_family_mismatch"} <= {
        f.code for f in validate_plan_v6(t5_project, bad)
    }
    bad = replace(plan, v6_infrastructure=(plan.v6_infrastructure[0],) * 2)
    assert any(f.code == "v6_duplicate_infrastructure" for f in validate_plan_v6(t5_project, bad))
