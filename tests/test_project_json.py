"""JSON is an input boundary, never a source of trusted computed allocations."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from importlib.resources import files
from ipaddress import IPv4Network, IPv6Address
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from adresplan.application.project_json import (
    MAX_JSON_BYTES,
    ProjectJSONError,
    dumps_project,
    load_project,
    loads_project,
    save_project,
)
from adresplan.application.schemas import (
    ProjectInput,
    SettingsInput,
    project_json_schema,
)
from adresplan.core.freeze import freeze
from adresplan.core.models import (
    GatewayPosition,
    IPv6GatewayMode,
    IPv6RAMode,
    IPv6SubnetStrategy,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
)
from adresplan.core.plan import build_plan
from adresplan.export.json_ import dumps_project as export_json

ROOT = Path(__file__).resolve().parents[1]


def minimal_document() -> dict:
    return {
        "schema_version": 1,
        "project": {
            "id": "av",
            "name": "Sieć AV — próba",
            "v4_pool": "10.42.0.0/20",
            "v6_prefix": "2001:db8:42::/48",
            "nodes": [
                {"id": "s", "name": "Zbór", "kind": "site"},
                {"id": "b", "name": "Sala", "kind": "building", "parent_id": "s"},
                {
                    "id": "av",
                    "name": "Dźwięk",
                    "kind": "segment",
                    "parent_id": "b",
                    "hosts": 10,
                },
            ],
        },
    }


def import_dict(document: dict):
    return loads_project(json.dumps(document, ensure_ascii=True))


@pytest.mark.parametrize("fixture", ["t4_project", "t5_project"])
def test_round_trip_preserves_every_field_and_plan(fixture: str, request) -> None:
    project = request.getfixturevalue(fixture)
    source_plan = build_plan(project)
    text = dumps_project(project)
    state = loads_project(text)
    assert state.project == project
    assert state.plan == source_plan
    assert dumps_project(state.project) == text
    result = json.loads(text)
    assert result["schema_version"] == 3
    assert result["plan"]["is_complete"] is True
    assert result["plan"]["project_id"] == project.id


def test_segment_subclass_data_and_all_settings_survive(t5_project: Project) -> None:
    project = replace(
        t5_project,
        name="Żółć / projekt\npróba",
        settings=ProjectSettings(
            growth_pct=7,
            gateway=GatewayPosition.LAST,
            gateway_addrs=3,
            p2p_prefix=30,
            v6_site_prefix=48,
            v6_building_prefix=56,
            v6_infra_prefix=60,
            v6_growth_pct=125,
            v6_subnet_strategy=IPv6SubnetStrategy.SEQUENTIAL,
            v6_gateway_mode=IPv6GatewayMode.LINK_LOCAL,
            v6_link_local_gateway=IPv6Address("fe80::abcd"),
            v6_ra_mode=IPv6RAMode.DHCPV6,
        ),
        nodes=tuple(
            replace(
                n,
                hosts=23,
                growth_pct=31,
                gateway=GatewayPosition.LAST,
                gateway_addrs=2,
                static_count=8,
                vlan_id=123,
                ra_mode=IPv6RAMode.SLAAC,
                notes="Mikser, kamera, obraz — Łódź",
                sort_order=99,
            )
            if n.id == "a0"
            else replace(n, v6_enabled=False)
            if n.id == "a1"
            else n
            for n in t5_project.nodes
        ),
    )
    assert build_plan(project).is_complete
    state = loads_project(dumps_project(project))
    assert state.project == project
    assert state.plan == build_plan(project)
    assert state.project.settings == project.settings
    assert isinstance(state.project.nodes[2], Segment)
    segment = state.project.nodes[2]
    original = project.nodes[2]
    assert {f.name: getattr(segment, f.name) for f in fields(Segment)} == {
        f.name: getattr(original, f.name) for f in fields(Segment)
    }


def test_defaults_match_core_and_export_materializes_them() -> None:
    state = import_dict(minimal_document())
    assert state.project.settings == ProjectSettings()
    assert SettingsInput().model_dump() == {
        f.name: getattr(ProjectSettings(), f.name) for f in fields(ProjectSettings)
    }
    segment = state.project.nodes[2]
    assert segment == Segment(id="av", name="Dźwięk", parent_id="b", hosts=10)
    dumped = json.loads(dumps_project(state.project))["project"]
    assert set(dumped) == {f.name for f in fields(Project)}
    assert set(dumped["nodes"][2]) == {f.name for f in fields(Segment)}
    assert set(dumped["nodes"][0]) == {f.name for f in fields(Node)}
    assert set(dumped["settings"]) == {f.name for f in fields(ProjectSettings)}


def test_frozen_round_trip_retains_pins_and_future_expansion(t5_project: Project) -> None:
    before = build_plan(t5_project)
    frozen = freeze(t5_project, before)
    restored = loads_project(dumps_project(frozen))
    assert restored.project == frozen
    assert restored.plan == before
    assert restored.project.pinned_v6_infrastructure == before.v6_infrastructure
    extended = replace(
        restored.project,
        nodes=(*restored.project.nodes, Segment(id="new", name="Nowy", parent_id="a", hosts=1)),
    )
    after = loads_project(dumps_project(extended)).plan
    assert after.is_complete
    for old, current in (
        (before.v4_allocations, after.v4_allocations),
        (before.v6_allocations, after.v6_allocations),
    ):
        lookup = {a.node_id: a.network for a in current}
        assert all(lookup[a.node_id] == a.network for a in old)
    assert after.v6_infrastructure == before.v6_infrastructure


@pytest.mark.parametrize(
    "snapshot",
    [
        {},
        {"is_complete": False},
        {
            "project_id": "forged",
            "is_complete": True,
            "v4_allocations": [{"node_id": "av", "network": "192.0.2.0/24"}],
            "v6_infrastructure": "not even the output shape",
            "future_field": [1, "test", None],
        },
    ],
)
def test_saved_result_is_ignored_and_recomputed(snapshot: dict) -> None:
    document = minimal_document()
    expected = import_dict(document)
    document["plan"] = snapshot
    assert import_dict(document) == expected


def test_editing_project_in_export_recomputes_the_old_snapshot() -> None:
    state = import_dict(minimal_document())
    document = json.loads(dumps_project(state.project))
    document["project"]["nodes"][2]["hosts"] = 200
    updated = import_dict(document)
    assert updated.plan != state.plan
    assert updated.plan == build_plan(updated.project)
    assert updated.plan.is_complete


def test_incomplete_plan_can_be_saved_imported_and_diagnosed(t4_project: Project) -> None:
    project = replace(t4_project, v4_pool=IPv4Network("10.20.0.0/24"))
    expected = build_plan(project)
    assert not expected.is_complete
    text = dumps_project(project)
    assert json.loads(text)["plan"]["is_complete"] is False
    restored = loads_project(text)
    assert restored.plan == expected
    assert restored.project == project
    assert restored.plan.findings


@pytest.mark.parametrize(
    ("prefix", "kind"),
    [("2001:db8:42::/48", "doc"), ("fd12:3456:789a::/48", "ula"), ("2001:4860::/48", "gua")],
)
def test_ipv6_kind_and_vlan_strategy_survive_import(prefix: str, kind: str) -> None:
    document = minimal_document()
    project = document["project"]
    project.update(v6_prefix=prefix, v6_kind=kind)
    project["settings"] = {"v6_subnet_strategy": "vlan_decimal_as_hex"}
    project["nodes"][2]["vlan_id"] = 10
    state = import_dict(document)
    assert state.plan.is_complete
    assert loads_project(dumps_project(state.project)) == state


def test_valid_types_with_inconsistent_network_settings_return_findings() -> None:
    document = minimal_document()
    document["project"]["settings"] = {"v6_site_prefix": 60, "v6_infra_prefix": 56}
    state = import_dict(document)
    assert not state.plan.is_complete
    assert any(f.code == "invalid_v6_settings" for f in state.plan.findings)
    assert loads_project(dumps_project(state.project)) == state


def test_infrastructure_and_pin_fields_are_validated(t5_project: Project) -> None:
    frozen = freeze(t5_project, build_plan(t5_project))
    document = json.loads(dumps_project(frozen))
    document["project"]["pinned_v6_infrastructure"][0]["p2p_pool"] = "10.0.0.0/24"
    document["project"]["nodes"][2]["pinned_v4"] = "2001:db8::/64"
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert {i.path for i in raised.value.issues} == {
        ("project", "pinned_v6_infrastructure", 0, "p2p_pool"),
        ("project", "nodes", 2, "pinned_v4"),
    }


def test_explicit_optional_nulls_and_out_of_order_nodes_preserve_ids() -> None:
    document = minimal_document()
    document["project"]["v6_prefix"] = None
    segment = document["project"]["nodes"][2]
    segment.update(
        growth_pct=None,
        gateway=None,
        gateway_addrs=None,
        vlan_id=None,
        ra_mode=None,
        pinned_v4=None,
        pinned_v6=None,
    )
    document["project"]["nodes"].reverse()
    state = import_dict(document)
    assert state.plan.is_complete
    assert tuple(n.id for n in state.project.nodes) == ("av", "b", "s")
    assert state.project.v6_prefix is None
    assert not state.plan.v6_allocations
    assert loads_project(dumps_project(state.project)) == state


@pytest.mark.parametrize("version", [None, True, False, "1", 1.0, 0, -1, 4, 999])
def test_invalid_or_future_schema_version_is_rejected(version: object) -> None:
    document = minimal_document()
    document["schema_version"] = version
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert raised.value.issues[0].path == ("schema_version",)
    assert raised.value.issues[0].code == "unsupported_schema_version"


def test_missing_version_is_not_guessed() -> None:
    document = minimal_document()
    del document["schema_version"]
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert raised.value.issues[0].code == "missing"


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        (("project", "nodes", 2, "hosts"), "10", "int_type"),
        (("project", "nodes", 2, "hosts"), True, "int_type"),
        (("project", "nodes", 2, "hosts"), 10.0, "int_type"),
        (("project", "nodes", 2, "hosts"), -1, "greater_than_equal"),
        (("project", "nodes", 2, "v6_enabled"), 1, "bool_type"),
        (("project", "nodes", 2, "v6_enabled"), "false", "bool_type"),
        (("project", "nodes", 2, "growth_pct"), -1, "greater_than_equal"),
        (("project", "nodes", 2, "gateway_addrs"), 4, "less_than_equal"),
        (("project", "nodes", 2, "static_count"), -1, "greater_than_equal"),
        (("project", "nodes", 2, "vlan_id"), 0, "greater_than_equal"),
        (("project", "nodes", 2, "vlan_id"), 4095, "less_than_equal"),
        (("project", "nodes", 2, "role"), "router", "enum"),
        (("project", "nodes", 2, "name"), 123, "string_type"),
        (("project", "nodes", 2, "name"), "   ", "blank_string"),
        (("project", "nodes", 2, "name"), "\ud800", "invalid_utf8_text"),
        (("project", "nodes", 2, "notes"), "\udfff", "invalid_utf8_text"),
        (("project", "nodes", 2, "sort_order"), -1, "greater_than_equal"),
        (("project", "nodes", 2, "host"), 10, "extra_forbidden"),
        (("project", "v4_pool"), "10.42.0.1/24", "cidr_v4"),
        (("project", "v4_pool"), "2001:db8::/48", "cidr_v4"),
        (("project", "v4_pool"), "10.42.0.0", "cidr_v4"),
        (("project", "v4_pool"), 174325760, "cidr_v4"),
        (("project", "v6_prefix"), "2001:db8::1/64", "cidr_v6"),
        (("project", "v6_prefix"), "10.0.0.0/8", "cidr_v6"),
        (("project", "v6_prefix"), "fe80::%eth0/64", "cidr_v6"),
        (("project", "name"), "", "blank_string"),
        (("project", "id"), "\t", "blank_string"),
        (("project", "setting"), {}, "extra_forbidden"),
        (("plan",), [], "dict_type"),
        (("surprise",), 1, "extra_forbidden"),
    ],
)
def test_bad_input_has_precise_paths_and_stable_codes(path, value, code: str) -> None:
    document = minimal_document()
    current = document
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert any(i.path == path and i.code == code for i in raised.value.issues)
    assert "https://errors.pydantic" not in str(raised.value)
    if "nodes" in path:
        assert "project.nodes[2]" in str(raised.value)
        assert ".segment." not in str(raised.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("growth_pct", "25"),
        ("growth_pct", -1),
        ("growth_pct", True),
        ("p2p_prefix", 32),
        ("p2p_prefix", 30.0),
        ("gateway", "middle"),
        ("gateway_addrs", 4),
        ("v6_building_prefix", 54),
        ("v6_site_prefix", 49),
        ("v6_infra_prefix", 64),
        ("v6_growth_pct", -1),
        ("v6_ra_mode", "magic"),
        ("v6_gateway_mode", "none"),
        ("v6_subnet_strategy", "random"),
        ("v6_link_local_gateway", 1),
        ("v6_link_local_gateway", "fe80::1%eth0"),
        ("v6_link_local_gateway", "10.0.0.1"),
        ("typo", 25),
    ],
)
def test_settings_are_validated_before_calling_the_planner(field: str, value: object) -> None:
    document = minimal_document()
    document["project"]["settings"] = {field: value}
    with patch("adresplan.application.project_json.build_plan") as planner:
        with pytest.raises(ProjectJSONError) as raised:
            import_dict(document)
        planner.assert_not_called()
    assert raised.value.issues[0].path == ("project", "settings", field)


@pytest.mark.parametrize(
    ("index", "field", "value", "code"),
    [
        (0, "parent_id", "b", "site_has_parent"),
        (1, "parent_id", "missing", "missing_parent"),
        (2, "parent_id", "s", "invalid_parent_kind"),
        (2, "parent_id", "av", "parent_cycle"),
        (2, "id", "b", "duplicate_node_id"),
    ],
)
def test_invalid_tree_is_rejected(index: int, field: str, value: str, code: str) -> None:
    document = minimal_document()
    document["project"]["nodes"][index][field] = value
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert any(i.code == code for i in raised.value.issues)
    assert all(i.path[:2] == ("project", "nodes") for i in raised.value.issues)


@pytest.mark.parametrize("kind", ["router", 1, None])
def test_unknown_node_kind_does_not_become_a_default_segment(kind: object) -> None:
    document = minimal_document()
    document["project"]["nodes"][2]["kind"] = kind
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert raised.value.issues[0].code == "union_tag_invalid"


def test_missing_kind_and_role_fields_on_a_building_are_errors() -> None:
    document = minimal_document()
    del document["project"]["nodes"][2]["kind"]
    document["project"]["nodes"][1]["hosts"] = 10
    with pytest.raises(ProjectJSONError) as raised:
        import_dict(document)
    assert {i.code for i in raised.value.issues} == {"union_tag_not_found", "extra_forbidden"}


@pytest.mark.parametrize("text", ["", "{", '{"schema_version":1,}', "{} {}", "null", "[]", "1"])
def test_malformed_or_nonobject_document_is_rejected(text: str) -> None:
    with pytest.raises(ProjectJSONError):
        loads_project(text)


@pytest.mark.parametrize(
    "text",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"project":{"id":"a","id":"b"}}',
        '{"plan":{"id":"a","id":"b"}}',
    ],
)
def test_duplicate_keys_are_rejected_even_in_ignored_snapshot(text: str) -> None:
    with pytest.raises(ProjectJSONError) as raised:
        loads_project(text)
    assert raised.value.issues[0].code == "duplicate_json_key"


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
def test_nonfinite_numbers_are_not_json(number: str) -> None:
    text = json.dumps(minimal_document())[:-1] + ', "plan":{"bad":' + number + "}}"
    with pytest.raises(ProjectJSONError) as raised:
        loads_project(text)
    assert raised.value.issues[0].code == "invalid_json_number"


def test_bom_is_supported_and_output_is_utf8_without_bom() -> None:
    document = minimal_document()
    raw = json.dumps(document, ensure_ascii=False).encode("utf-8")
    assert loads_project(b"\xef\xbb\xbf" + raw) == loads_project(raw)
    assert loads_project("\ufeff" + raw.decode("utf-8")) == loads_project(raw)
    text = dumps_project(loads_project(raw).project)
    assert "Dźwięk" in text
    assert not text.startswith("\ufeff")
    assert text.endswith("\n")


@pytest.mark.parametrize("data", [b"\xff\xfe", "\ud800"])
def test_invalid_utf8_is_reported(data) -> None:
    with pytest.raises(ProjectJSONError) as raised:
        loads_project(data)
    assert raised.value.issues[0].code == "invalid_utf8"


def test_size_limit_applies_to_string_file_and_export(tmp_path: Path) -> None:
    raw = b" " * (MAX_JSON_BYTES + 1)
    file = tmp_path / "too-big.json"
    file.write_bytes(raw)
    for operation in (
        lambda: loads_project(raw),
        lambda: loads_project(raw.decode()),
        lambda: load_project(file),
    ):
        with pytest.raises(ProjectJSONError) as raised:
            operation()
        assert raised.value.issues[0].code == "json_too_large"
    project = import_dict(minimal_document()).project
    too_large = replace(project, name="x" * MAX_JSON_BYTES)
    with pytest.raises(ProjectJSONError) as raised:
        dumps_project(too_large)
    assert raised.value.issues[0].code == "json_too_large"


def test_deep_json_is_a_boundary_error() -> None:
    with pytest.raises(ProjectJSONError) as raised:
        loads_project("[" * 2000 + "0" + "]" * 2000)
    assert raised.value.issues[0].code in {"invalid_json", "model_type"}


def test_file_round_trip_and_atomic_replacement(tmp_path: Path, t5_project: Project) -> None:
    target = tmp_path / "próba.json"
    target.write_bytes(b"previous content")
    save_project(target, t5_project)
    assert load_project(str(target)).project == t5_project
    assert target.read_bytes() == dumps_project(t5_project).encode("utf-8")
    assert list(tmp_path.iterdir()) == [target]


def test_replace_failure_keeps_previous_file_and_cleans_temporary(
    tmp_path: Path,
    t5_project: Project,
) -> None:
    target = tmp_path / "project.json"
    target.write_bytes(b"previous content")
    with (
        patch("adresplan.application.files.os.replace", side_effect=PermissionError("locked")),
        pytest.raises(ProjectJSONError) as raised,
    ):
        save_project(target, t5_project)
    assert raised.value.issues[0].code == "file_write_error"
    assert target.read_bytes() == b"previous content"
    assert list(tmp_path.iterdir()) == [target]


def test_validation_failure_does_not_touch_existing_file(
    tmp_path: Path, t5_project: Project
) -> None:
    target = tmp_path / "project.json"
    target.write_bytes(b"previous content")
    invalid = replace(t5_project, nodes=(*t5_project.nodes, t5_project.nodes[0]))
    with pytest.raises(ProjectJSONError):
        save_project(target, invalid)
    assert target.read_bytes() == b"previous content"
    assert list(tmp_path.iterdir()) == [target]


def test_file_errors_use_the_same_boundary_error(tmp_path: Path, t5_project: Project) -> None:
    with pytest.raises(ProjectJSONError) as read_error:
        load_project(tmp_path / "missing.json")
    assert read_error.value.issues[0].code == "file_read_error"
    with pytest.raises(ProjectJSONError) as write_error:
        save_project(tmp_path / "missing" / "project.json", t5_project)
    assert write_error.value.issues[0].code == "file_write_error"


def test_plain_node_claiming_to_be_a_segment_is_not_silently_repaired(t5_project: Project) -> None:
    invalid = replace(
        t5_project,
        nodes=(*t5_project.nodes, Node(id="bad", name="Bad", parent_id="a", kind=NodeKind.SEGMENT)),
    )
    with pytest.raises(ProjectJSONError) as raised:
        dumps_project(invalid)
    assert raised.value.issues[0].code == "invalid_project"


def test_schema_is_shipped_and_matches_the_actual_validator() -> None:
    shipped = files("adresplan").joinpath("schemas", "project-v3.schema.json")
    schema = json.loads(shipped.read_text(encoding="utf-8"))
    assert schema == project_json_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["required"] == ["schema_version", "project"]
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["ProjectInput"]["additionalProperties"] is False
    assert set(ProjectInput.model_fields) == {f.name for f in fields(Project)}


def test_export_facade_uses_the_same_format() -> None:
    project = import_dict(minimal_document()).project
    assert export_json(project) == dumps_project(project)


@settings(max_examples=60)
@given(
    hosts=st.integers(min_value=1, max_value=2000),
    static=st.integers(min_value=0, max_value=20),
    growth=st.integers(min_value=0, max_value=150),
    note=st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=60),
)
def test_varied_inputs_round_trip_without_changes(hosts, static, growth, note) -> None:
    document = minimal_document()
    document["project"]["nodes"][2].update(
        hosts=hosts,
        static_count=static,
        growth_pct=growth,
        notes=note,
    )
    original = import_dict(document)
    restored = loads_project(dumps_project(original.project))
    assert restored == original
    assert dumps_project(restored.project) == dumps_project(original.project)
