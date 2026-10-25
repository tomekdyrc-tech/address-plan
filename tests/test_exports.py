"""Portable exports preserve network semantics and handle hostile text as data."""

import csv
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from adresplan.application.exporting import export_document, save_document
from adresplan.application.project_json import ProjectJSONError, load_project, loads_project
from adresplan.core.models import GatewayPosition, Project
from adresplan.core.plan import build_plan
from adresplan.export.csv_ import CSV_COLUMNS, dumps_csv
from adresplan.export.markdown import dumps_markdown

ROOT = Path(__file__).resolve().parents[1]


def records(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(text, newline=""), delimiter=";"))


def test_csv_t4_contains_required_columns_and_exact_addresses(t4_project: Project) -> None:
    rows = records(dumps_csv(t4_project))
    assert len(rows) == 14
    assert tuple(rows[0]) == CSV_COLUMNS
    by_id = {r["Segment ID"]: r for r in rows}
    assert by_id["a_wifi"]["IPv4 CIDR"] == "10.20.0.0/24"
    assert by_id["b_av"]["IPv4 CIDR"] == "10.20.2.192/27"
    assert by_id["c_residence"]["IPv4 CIDR"] == "10.20.3.0/27"
    assert by_id["a_wifi"]["Hosty (z zapasem)"] == "200"
    assert by_id["a_wifi"]["Brama"] == ""
    assert by_id["a_wifi"]["Zakres DHCP"] == "10.20.0.1–10.20.0.254"
    assert by_id["a_wifi"]["Maska"] == "255.255.255.0"
    assert by_id["a_wifi"]["Broadcast"] == "10.20.0.255"
    for id, count in [("a_link1", "2"), ("a_link2", "2"), ("a_loop", "1")]:
        assert by_id[id]["Hosty (z zapasem)"] == count
        assert by_id[id]["Brama"] == by_id[id]["Broadcast"] == by_id[id]["Zakres DHCP"] == ""
    assert all(r["Status planu"] == "KOMPLETNY" and r["Błędy"] == "0" for r in rows)


def test_csv_growth_reservations_and_gateway_last() -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    project = replace(
        project,
        nodes=tuple(
            replace(
                n,
                hosts=10,
                growth_pct=50,
                gateway=GatewayPosition.LAST,
                gateway_addrs=3,
                static_count=4,
            )
            if n.id == "audio"
            else n
            for n in project.nodes
        ),
    )
    row = next(r for r in records(dumps_csv(project)) if r["Segment ID"] == "audio")
    assert row["Hosty (wejście)"] == "10" and row["Hosty (z zapasem)"] == "15"
    assert row["Wymagane użyteczne IPv4"] == "22"
    assert row["Brama"] == "10.42.0.30, 10.42.0.29, 10.42.0.28"
    assert row["Zakres statyczny"] == "10.42.0.1–10.42.0.4"
    assert row["Zakres DHCP"] == "10.42.0.5–10.42.0.27"


def test_csv_ipv6_lan_p2p_loopback_and_ra(t5_project: Project) -> None:
    rows = {r["Segment ID"]: r for r in records(dumps_csv(t5_project))}
    assert rows["a0"]["IPv6 CIDR"] == "2001:db8:abcd:100::/64"
    assert rows["a0"]["Brama IPv6"] == "2001:db8:abcd:100::1"
    assert rows["a0"]["Tryb RA"] == "slaac"
    assert rows["a0"]["Reverse DNS IPv6"].endswith("ip6.arpa")
    assert rows["link0"]["IPv6 CIDR"] == "2001:db8:abcd:1::/127"
    assert rows["link0"]["Końce IPv6"] == "2001:db8:abcd:1::, 2001:db8:abcd:1::1"
    assert rows["link0"]["Brama IPv6"] == rows["link0"]["Tryb RA"] == ""
    assert rows["link0"]["Reverse DNS IPv6"] == ""
    assert rows["loop"]["IPv6 CIDR"] == "2001:db8:abcd:2::/128"
    assert rows["loop"]["Końce IPv6"] == "2001:db8:abcd:2::"


@pytest.mark.parametrize(
    "value",
    ["=1+1", "+1+1", "-1+1", "@SUM(1)", "  =1", "\t=1", "\r=1", "\n=1", "\ufeff=1", "\u2003=1"],
)
def test_csv_neutralizes_formula_like_user_text(value: str) -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    project = replace(
        project, name=value, nodes=tuple(replace(n, name=value, notes=value) for n in project.nodes)
    )
    row = records(dumps_csv(project))[0]
    assert all(
        row[key] == "'" + value
        for key in (
            "Projekt",
            "Lokalizacja",
            "Budynek",
            "Segment",
            "Uwagi",
            "Uwagi budynku",
            "Uwagi lokalizacji",
        )
    )
    assert project.name == value


def test_csv_round_trips_delimiters_quotes_polish_text_and_newlines() -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    note = 'Żółć; "mikser"\nDruga linia | [tekst] <tag>'
    project = replace(
        project,
        nodes=tuple(replace(n, notes=note) if n.id == "audio" else n for n in project.nodes),
    )
    text = dumps_csv(project)
    assert text.startswith('"Typ wiersza";')
    assert text.endswith("\r\n")
    assert records(text)[0]["Uwagi"] == note


def test_markdown_report_has_assumptions_buildings_free_blocks_and_validation(
    t4_project: Project,
) -> None:
    text = dumps_markdown(t4_project)
    for fragment in (
        "# Plan adresacji",
        "Status: KOMPLETNY",
        "## Założenia",
        "## Lokalizacja / Budynek A",
        "## Lokalizacja / Budynek B",
        "## Lokalizacja / Budynek C",
        "## Podsumowanie wykorzystania",
        "10.20.0.0/23",
        "10.20.2.0/24",
        "10.20.3.0/27",
        "10.20.8.0/21",
        "## Wolne bloki",
        "## Walidacja",
        "DHCP",
        "Ciągłość",
    ):
        assert fragment in text
    assert text.endswith("\n")


def test_markdown_ipv6_infrastructure_and_scoped_metrics_are_complete(t5_project: Project) -> None:
    text = dumps_markdown(t5_project)
    plan = build_plan(t5_project)
    for pools in plan.v6_infrastructure:
        assert all(
            str(n) in text
            for n in (pools.network, pools.reserved_pool, pools.p2p_pool, pools.loopback_pool)
        )
    assert all(str(a.network) in text for a in (*plan.v4_allocations, *plan.v6_allocations))
    assert all(str(b.network) in text for b in plan.free_blocks)
    assert "1190036353683150593851392" in text
    assert "Nie sumuj" in text


def test_markdown_user_text_cannot_break_tables_or_inject_html_links_or_headings() -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    value = (
        "A|B *bold* `code` [link](https://invalid.test) <script>alert(1)</script>\n# WSTRZYKNIĘTY"
    )
    project = replace(
        project,
        name=value,
        nodes=tuple(
            replace(n, name=value, notes=value) if n.id == "audio" else n for n in project.nodes
        ),
    )
    text = dumps_markdown(project)
    assert "A\\|B \\*bold\\* \\`code\\` \\[link\\]" in text
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert "<br># WSTRZYKNIĘTY" in text and "\n# WSTRZYKNIĘTY" not in text


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_exports_are_deterministic_and_do_not_modify_input(format, t5_project: Project) -> None:
    original = t5_project
    first = export_document(t5_project, format)
    assert first == export_document(t5_project, format)
    assert t5_project == original
    if format == "json":
        assert loads_project(first).project == original


@pytest.mark.parametrize("format", ["csv", "md"])
def test_incomplete_result_includes_unallocated_rows_and_visible_diagnostics(format) -> None:
    project = load_project(ROOT / "examples/t3-no-space.json").project
    text = export_document(project, format)
    if format == "csv":
        rows = records(text)
        assert len(rows) == 3
        assert all(r["Status planu"] == "NIEKOMPLETNY" and r["Błędy"] != "0" for r in rows)
        z = next(r for r in rows if r["Segment ID"] == "Z")
        assert z["IPv4 CIDR"] == ""
        assert "insufficient_space" in z["Walidacja"]
        assert "/25" in z["Walidacja"]
    else:
        assert "Status: NIEKOMPLETNY" in text
        assert "insufficient\\_space" in text
        assert "192.168.1.0/27" in text and "192.168.1.32/27" in text


@pytest.mark.parametrize("format", ["csv", "md"])
def test_empty_project_still_has_project_status(format) -> None:
    project = replace(load_project(ROOT / "examples/stage4a_project.json").project, nodes=())
    text = export_document(project, format)
    assert "KOMPLETNY" in text
    if format == "csv":
        rows = records(text)
        assert len(rows) == 1 and rows[0]["Typ wiersza"] == "projekt"
    else:
        assert "Projekt nie zawiera segmentów" in text


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_export_file_encoding_and_atomic_failure(format, tmp_path: Path) -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    text = export_document(project, format)
    target = tmp_path / f"plan.{format}"
    save_document(target, text, format)
    encoding = "utf-8-sig" if format == "csv" else "utf-8"
    assert target.read_bytes() == text.encode(encoding)
    with (
        patch("adresplan.application.files.os.replace", side_effect=PermissionError("locked")),
        pytest.raises(ProjectJSONError) as raised,
    ):
        save_document(target, "replacement", format)
    assert raised.value.issues[0].code == "file_write_error"
    assert target.read_bytes() == text.encode(encoding)
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_invalid_typed_project_is_not_silently_exported(format) -> None:
    project = load_project(ROOT / "examples/stage4a_project.json").project
    invalid = replace(project, nodes=(*project.nodes, project.nodes[0]))
    with pytest.raises(ProjectJSONError):
        export_document(invalid, format)


@pytest.mark.parametrize("name", ["church-av", "t4-hierarchy"])
def test_committed_sample_exports_match_current_data(name: str) -> None:
    input_name = "church-av.json" if name == "church-av" else "budynek.json"
    project = load_project(ROOT / "examples" / input_name).project
    base = ROOT / "examples/exports"
    assert (base / f"{name}.md").read_bytes() == dumps_markdown(project).encode("utf-8")
    assert (base / f"{name}.csv").read_bytes() == dumps_csv(project).encode("utf-8-sig")
