"""Tree validation, stable identity and model behavior."""

from dataclasses import FrozenInstanceError, replace
from ipaddress import IPv4Network

import pytest

from adresplan.core.models import (
    Finding,
    FindingLevel,
    Node,
    NodeKind,
    Plan,
    Project,
    Segment,
    node_sort_key,
)
from adresplan.core.structure import validate_structure


def project(*nodes: Node) -> Project:
    return Project(id="p", name="Project", v4_pool=IPv4Network("10.0.0.0/16"), nodes=nodes)


def test_valid_tree_is_not_required_to_be_in_parent_first_order() -> None:
    segment = Segment(id="s", name="S", parent_id="b", hosts=10)
    building = Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="site")
    site = Node(id="site", name="Site", kind=NodeKind.SITE)
    data = project(segment, building, site)
    assert validate_structure(data) == ()
    assert validate_structure(replace(data, nodes=tuple(reversed(data.nodes)))) == ()


def test_empty_project_is_structurally_valid() -> None:
    assert validate_structure(project()) == ()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("id", " ", "empty_project_id"),
        ("name", " ", "empty_project_name"),
    ],
)
def test_required_project_identity(field: str, value: str, code: str) -> None:
    assert validate_structure(replace(project(), **{field: value}))[0].code == code


@pytest.mark.parametrize(
    ("node", "code"),
    [
        (Node(id=" ", name="S", kind=NodeKind.SITE), "empty_node_id"),
        (Node(id="s", name=" ", kind=NodeKind.SITE), "empty_node_name"),
        (Node(id="s", name="S", kind=NodeKind.SITE, sort_order=-1), "negative_sort_order"),
        (Node(id="s", name="S", kind=NodeKind.SITE, parent_id="b"), "site_has_parent"),
        (Node(id="b", name="B", kind=NodeKind.BUILDING), "missing_parent"),
        (Node(id="s", name="S", kind=NodeKind.SEGMENT), "segment_data_missing"),
    ],
)
def test_malformed_nodes_are_findings(node: Node, code: str) -> None:
    assert code in {f.code for f in validate_structure(project(node))}


def test_duplicate_ids_make_parent_reference_ambiguous() -> None:
    site = Node(id="site", name="A", kind=NodeKind.SITE)
    building = Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="site")
    findings = validate_structure(project(site, replace(site, name="Other"), building))
    assert {f.code for f in findings} == {"duplicate_node_id", "missing_parent"}


def test_segment_cannot_be_attached_directly_to_site() -> None:
    findings = validate_structure(
        project(
            Node(id="site", name="Site", kind=NodeKind.SITE),
            Segment(id="s", name="S", parent_id="site"),
        )
    )
    assert [f.code for f in findings] == ["invalid_parent_kind"]


def test_parent_cycles_are_bounded_and_reported() -> None:
    data = project(
        Node(id="a", name="A", kind=NodeKind.BUILDING, parent_id="b"),
        Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="a"),
    )
    findings = validate_structure(data)
    assert sum(f.code == "parent_cycle" for f in findings) == 2
    assert findings == validate_structure(replace(data, nodes=tuple(reversed(data.nodes))))


def test_self_cycle_is_reported() -> None:
    findings = validate_structure(
        project(Node(id="a", name="A", kind=NodeKind.SITE, parent_id="a"))
    )
    assert "parent_cycle" in {f.code for f in findings}


def test_sorting_uses_order_name_then_id_without_replacing_ids() -> None:
    nodes = [
        Node(id="b", name="Same", kind=NodeKind.SITE),
        Node(id="a", name="Same", kind=NodeKind.SITE),
    ]
    assert [node.id for node in sorted(nodes, key=node_sort_key)] == ["a", "b"]
    renamed = replace(nodes[0], name="New")
    assert renamed.id == nodes[0].id
    with pytest.raises(FrozenInstanceError):
        nodes[0].name = "Changed"


def test_plan_completeness_depends_on_errors_not_warnings() -> None:
    plan = Plan(project_id="p", findings=(Finding(code="warning", level=FindingLevel.WARNING),))
    assert plan.is_complete
    assert not replace(plan, findings=(Finding(code="failure"),)).is_complete
