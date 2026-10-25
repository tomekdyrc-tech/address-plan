"""Freezing must preserve existing addresses and refuse stale or incomplete plans."""

from dataclasses import replace
from ipaddress import IPv6Network

import pytest

from adresplan.core.freeze import freeze
from adresplan.core.models import Finding, Plan, Segment
from adresplan.core.plan import build_plan


def test_freeze_is_pure_and_idempotent(t4_project) -> None:
    plan = build_plan(t4_project)
    frozen = freeze(t4_project, plan)
    allocation_map = {a.node_id: a.network for a in plan.v4_allocations}
    assert all(n.pinned_v4 == allocation_map[n.id] for n in frozen.nodes)
    assert all(n.pinned_v4 is None for n in t4_project.nodes if n.id != "site")
    assert freeze(frozen, build_plan(frozen)) == frozen
    assert build_plan(frozen) == plan


def test_new_segment_uses_free_space_without_moving_any_frozen_address(t4_project) -> None:
    old = build_plan(t4_project)
    frozen = freeze(t4_project, old)
    expanded = replace(
        frozen, nodes=(*frozen.nodes, Segment(id="new", name="New", parent_id="a", hosts=1))
    )
    new = build_plan(expanded)
    assert new.is_complete
    allocations = {a.node_id: a.network for a in new.v4_allocations}
    assert all(allocations[a.node_id] == a.network for a in old.v4_allocations)
    assert str(allocations["new"]) == "10.20.1.232/30"


def test_full_frozen_building_reports_failure_and_preserves_old_allocations(t4_project) -> None:
    old = build_plan(t4_project)
    frozen = freeze(t4_project, old)
    expanded = replace(
        frozen, nodes=(*frozen.nodes, Segment(id="new", name="New", parent_id="b", hosts=60))
    )
    new = build_plan(expanded)
    assert not new.is_complete
    allocations = {a.node_id: a.network for a in new.v4_allocations}
    assert all(allocations[a.node_id] == a.network for a in old.v4_allocations)
    assert "new" not in allocations
    assert any(f.code == "insufficient_space" and f.node_id == "new" for f in new.findings)
    with pytest.raises(ValueError, match="incomplete"):
        freeze(expanded, new)


def test_freeze_rejects_foreign_stale_and_tampered_plans(t4_project) -> None:
    plan = build_plan(t4_project)
    with pytest.raises(ValueError, match="another project"):
        freeze(t4_project, replace(plan, project_id="another"))
    changed = replace(
        t4_project,
        nodes=tuple(replace(n, hosts=300) if n.id == "a_wifi" else n for n in t4_project.nodes),
    )
    with pytest.raises(ValueError, match="does not match"):
        freeze(changed, plan)
    with pytest.raises(ValueError, match="does not match"):
        freeze(t4_project, replace(plan, v4_allocations=plan.v4_allocations[:-1]))
    with pytest.raises(ValueError, match="does not match"):
        freeze(t4_project, Plan(project_id=t4_project.id))


def test_freeze_refuses_errors_but_allows_warnings(t4_project) -> None:
    plan = build_plan(t4_project)
    assert any(f.code == "high_segment_utilization" for f in plan.findings)
    assert freeze(t4_project, plan)
    with pytest.raises(ValueError, match="incomplete"):
        freeze(t4_project, replace(plan, findings=(*plan.findings, Finding(code="error"))))


def test_freeze_preserves_notes_settings_and_existing_ipv6_inputs(t4_project) -> None:
    data = replace(
        t4_project,
        v6_prefix=IPv6Network("2001:db8::/48"),
        nodes=tuple(
            replace(n, notes="Do not lose", pinned_v6=IPv6Network("2001:db8:0:100::/64"))
            if n.id == "a_wifi"
            else n
            for n in t4_project.nodes
        ),
    )
    frozen = freeze(data, build_plan(data))
    node = next(n for n in frozen.nodes if n.id == "a_wifi")
    assert node.notes == "Do not lose" and node.pinned_v6 == IPv6Network("2001:db8:0:100::/64")
    assert frozen.settings == data.settings and frozen.v6_prefix == data.v6_prefix


def test_duplicate_or_overlapping_external_plan_cannot_be_frozen(t4_project) -> None:
    plan = build_plan(t4_project)
    with pytest.raises(ValueError, match="does not match"):
        freeze(
            t4_project,
            replace(plan, v4_allocations=(*plan.v4_allocations, plan.v4_allocations[-1])),
        )
