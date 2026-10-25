"""Address-space policy, per-site VLANs and independent plan verification."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Network

import pytest

from adresplan.core.models import Allocation, FindingLevel, Node, NodeKind, Plan, Segment
from adresplan.core.plan import build_plan
from adresplan.core.validate import is_rfc1918, validate_plan_v4, validate_project_v4


@pytest.mark.parametrize("cidr", ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "10.1.2.0/24"])
def test_explicit_rfc1918_ranges(cidr) -> None:
    assert is_rfc1918(IPv4Network(cidr))


@pytest.mark.parametrize(
    "cidr", ["127.0.0.0/8", "169.254.0.0/16", "192.0.2.0/24", "100.64.0.0/10", "172.0.0.0/8"]
)
def test_is_private_is_not_used_as_a_substitute_for_rfc1918(cidr) -> None:
    assert not is_rfc1918(IPv4Network(cidr))


@pytest.mark.parametrize(
    "cidr",
    [
        "127.0.0.0/8",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "126.0.0.0/7",
        "169.0.0.0/8",
        "0.0.0.0/0",
    ],
)
def test_forbidden_pools_and_partial_intersections_are_errors(t4_project, cidr) -> None:
    data = replace(t4_project, v4_pool=IPv4Network(cidr), nodes=())
    plan = build_plan(data)
    assert not plan.is_complete and not plan.v4_allocations
    assert any(
        f.code == "forbidden_v4_pool" and f.level is FindingLevel.ERROR for f in plan.findings
    )


@pytest.mark.parametrize(
    ("cidr", "code"), [("192.0.2.0/24", "non_rfc1918_pool"), ("100.64.0.0/10", "cgnat_pool")]
)
def test_non_private_and_cgnat_pools_produce_warnings_not_false_private_labels(
    t4_project, cidr, code
) -> None:
    findings = validate_project_v4(replace(t4_project, v4_pool=IPv4Network(cidr), nodes=()))
    assert any(f.code == code and f.level is FindingLevel.WARNING for f in findings)
    assert not any(f.level is FindingLevel.ERROR for f in findings)


@pytest.mark.parametrize("vlan", [0, 4095, -1, True, "20"])
def test_invalid_vlan_ids_are_errors(t4_project, vlan) -> None:
    data = replace(
        t4_project,
        nodes=tuple(replace(n, vlan_id=vlan) if n.id == "a_wifi" else n for n in t4_project.nodes),
    )
    plan = build_plan(data)
    assert not plan.is_complete and any(f.code == "invalid_vlan_id" for f in plan.findings)


def test_duplicate_vlans_across_buildings_in_one_site_warn(t4_project) -> None:
    data = replace(
        t4_project,
        nodes=tuple(
            replace(n, vlan_id=20) if n.id in ("a_wifi", "b_av") else n for n in t4_project.nodes
        ),
    )
    plan = build_plan(data)
    assert plan.is_complete
    assert {f.node_id for f in plan.findings if f.code == "duplicate_vlan_id"} == {"a_wifi", "b_av"}


def test_same_vlan_in_different_sites_is_allowed(t4_project) -> None:
    data = replace(
        t4_project,
        nodes=(
            *(replace(n, vlan_id=20) if n.id == "a_wifi" else n for n in t4_project.nodes),
            Node(id="other-site", name="Other", kind=NodeKind.SITE),
            Node(id="other-building", name="Other", kind=NodeKind.BUILDING, parent_id="other-site"),
            Segment(id="other", name="Other", parent_id="other-building", hosts=10, vlan_id=20),
        ),
        v4_pool=IPv4Network("10.20.0.0/16"),
    )
    plan = build_plan(data)
    assert plan.is_complete and not any(f.code == "duplicate_vlan_id" for f in plan.findings)


def test_vlan_one_user_traffic_is_info(t4_project) -> None:
    data = replace(
        t4_project,
        nodes=tuple(replace(n, vlan_id=1) if n.id == "a_wifi" else n for n in t4_project.nodes),
    )
    assert any(
        f.code == "user_traffic_vlan_1" and f.level is FindingLevel.INFO
        for f in build_plan(data).findings
    )


def test_parent_child_containment_is_valid_and_sibling_overlap_is_not(t4_project) -> None:
    plan = build_plan(t4_project)
    assert validate_plan_v4(t4_project, plan) == ()
    bad = replace(
        plan,
        v4_allocations=tuple(
            replace(a, network=IPv4Network("10.20.1.0/26")) if a.node_id == "a_voip" else a
            for a in plan.v4_allocations
        ),
    )
    assert any(f.code == "allocation_overlap" for f in validate_plan_v4(t4_project, bad))


def test_wrong_parent_and_too_small_network_are_reported(t4_project) -> None:
    plan = build_plan(t4_project)
    outside = replace(
        plan,
        v4_allocations=tuple(
            replace(a, network=IPv4Network("10.21.0.0/24")) if a.node_id == "a_wifi" else a
            for a in plan.v4_allocations
        ),
    )
    assert any(f.code == "allocation_outside_parent" for f in validate_plan_v4(t4_project, outside))
    small = replace(
        plan,
        v4_allocations=tuple(
            replace(a, network=IPv4Network("10.20.0.0/30")) if a.node_id == "a_wifi" else a
            for a in plan.v4_allocations
        ),
    )
    assert any(f.code == "invalid_segment_allocation" for f in validate_plan_v4(t4_project, small))


def test_foreign_duplicate_unknown_and_missing_parent_allocations(t4_project) -> None:
    plan = build_plan(t4_project)
    bad = replace(
        plan,
        project_id="wrong",
        v4_allocations=(
            *(a for a in plan.v4_allocations if a.node_id != "a"),
            plan.v4_allocations[-1],
            Allocation(node_id="unknown", network=IPv4Network("10.0.0.0/24")),
        ),
    )
    codes = {f.code for f in validate_plan_v4(t4_project, bad)}
    assert {
        "plan_project_mismatch",
        "duplicate_allocation_node",
        "unknown_allocation_node",
        "allocation_parent_missing",
    } <= codes


def test_wrong_family_pool_and_pins_return_findings(t4_project) -> None:
    assert not build_plan(replace(t4_project, v4_pool=IPv6Network("2001:db8::/48"))).is_complete
    for pin, code in [
        (IPv6Network("2001:db8::/64"), "pinned_family_mismatch"),
        (IPv4Network("10.21.0.0/24"), "pinned_outside_project"),
    ]:
        data = replace(
            t4_project,
            nodes=tuple(
                replace(n, pinned_v4=pin) if n.id == "a_wifi" else n for n in t4_project.nodes
            ),
        )
        assert any(f.code == code for f in build_plan(data).findings)


def test_changed_pin_is_detected_by_plan_validator(t4_project) -> None:
    plan = build_plan(t4_project)
    data = replace(
        t4_project,
        nodes=tuple(
            replace(n, pinned_v4=IPv4Network("10.20.1.64/26")) if n.id == "a_office" else n
            for n in t4_project.nodes
        ),
    )
    assert any(f.code == "pinned_allocation_changed" for f in validate_plan_v4(data, plan))


def test_high_utilization_warning_applies_to_lan_not_fixed_infrastructure(t4_project) -> None:
    plan = build_plan(t4_project)
    warned = {f.node_id for f in plan.findings if f.code == "high_segment_utilization"}
    assert "c_residence" in warned
    assert not warned & {"a_link1", "a_link2", "a_loop"}


def test_an_empty_plan_cannot_silently_omit_required_segments(t4_project) -> None:
    findings = validate_plan_v4(t4_project, Plan(project_id=t4_project.id))
    assert {f.node_id for f in findings if f.code == "missing_segment_allocation"} == {
        n.id for n in t4_project.nodes if isinstance(n, Segment)
    }


def test_external_allocation_in_wrong_family_is_a_finding(t4_project) -> None:
    plan = build_plan(t4_project)
    bad = replace(
        plan,
        v4_allocations=tuple(
            replace(a, network=IPv6Network("2001:db8::/64")) if a.node_id == "a_wifi" else a
            for a in plan.v4_allocations
        ),
    )
    assert any(f.code == "allocation_family_mismatch" for f in validate_plan_v4(t4_project, bad))
    assert (
        validate_plan_v4(replace(t4_project, v4_pool=IPv6Network("2001:db8::/48")), plan)[0].code
        == "invalid_v4_pool"
    )
