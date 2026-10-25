"""CLI integration: usable output, real exit statuses, and safe freeze writes."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from adresplan.application.console import format_finding, format_plan
from adresplan.application.project_json import load_project, loads_project, save_project
from adresplan.core.models import Finding, FindingLevel, IPv6SubnetStrategy, Project, Segment
from adresplan.core.plan import build_plan

ROOT = Path(__file__).resolve().parents[1]
AV = ROOT / "examples/stage4a_project.json"


def run_cli(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "adresplan", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
        env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "ascii"},
    )


@pytest.mark.parametrize(
    "command",
    [
        (),
        ("--help",),
        ("plan", "--help"),
        ("calc", "--help"),
        ("freeze", "--help"),
        ("export", "--help"),
    ],
)
def test_help_is_polish_and_exits_successfully(command) -> None:
    result = run_cli(*command)
    assert result.returncode == 0
    assert "Użycie:" in result.stdout
    assert "Pokaż pomoc" in result.stdout
    assert not result.stderr
    assert "usage:" not in result.stdout and "options:" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ("unknown",),
        ("plan",),
        ("calc",),
        ("freeze", str(AV)),
        ("plan", str(AV), "--typo"),
        ("plan", str(AV), "--j"),
        ("calc", "10.0.0.0/24", "--split", "2", "--new-prefix", "25"),
        ("calc", "10.0.0.0/24", "--split", "abc"),
        ("calc", "10.0.0.0/24", "--new-prefix"),
    ],
)
def test_argument_errors_return_two_without_traceback(arguments) -> None:
    result = run_cli(*arguments)
    assert result.returncode == 2
    assert "Błąd argumentów" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ("192.168.1.10/24",),
        ("192.168.1.10", "255.255.255.0"),
        ("192.168.1.10", "0.0.0.255"),
        ("192.168.1.10 0.0.0.255",),
    ],
)
def test_calc_accepts_all_documented_ipv4_forms(arguments) -> None:
    result = run_cli("calc", *arguments, "--split", "4")
    assert result.returncode == 0, result.stderr
    assert "Sieć: 192.168.1.0/24" in result.stdout
    assert "Wildcard: 0.0.0.255" in result.stdout
    assert "Liczba użytecznych: 254" in result.stdout
    assert "192.168.1.192/26" in result.stdout
    assert not result.stderr


def test_calc_ipv6_shows_bounded_split_and_no_broadcast() -> None:
    result = run_cli("calc", "2001:db8::/48", "--new-prefix", "64", "--limit", "2")
    assert result.returncode == 0
    assert "65536 podsieci; pokazano 2" in result.stdout
    assert "2001:db8:0:1::/64" in result.stdout
    assert "2001:db8:0:2::/64" not in result.stdout
    assert "Broadcast" not in result.stdout
    assert "Typ adresu: dokumentacyjny" in result.stdout


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("10.0.0.1/31",), "Liczba użytecznych: 2"),
        (("10.0.0.1/32",), "Liczba użytecznych: 1"),
        (("2001:db8::1/127",), "prefiks niewyrównany do 4 bitów"),
        (("192.168.1.10/20",), "brak jednej zwykłej strefy"),
    ],
)
def test_calculator_edge_cases_are_explained(arguments, expected) -> None:
    result = run_cli("calc", *arguments)
    assert result.returncode == 0
    assert expected in result.stdout


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("bad",), "invalid_address"),
        (("10.0.0.0/24", "--split", "3"), "podaj --split 4"),
        (("10.0.0.0/24", "--split", "0"), "invalid_subnet_count"),
        (("10.0.0.0/24", "--new-prefix", "23"), "invalid_subnet_prefix"),
        (("10.0.0.0/24", "--split", "512"), "invalid_subnet_prefix"),
        (("::/0", "--new-prefix", "128", "--limit", "257"), "invalid_preview_limit"),
        (("::/0", "--new-prefix", "128", "--limit", "0"), "invalid_preview_limit"),
        (("::/0", "--limit", "2"), "--limit wymaga podziału"),
        (("::/0", "--limit", "256"), "--limit wymaga podziału"),
    ],
)
def test_bad_calculations_return_two_without_partial_output(arguments, expected) -> None:
    result = run_cli("calc", *arguments)
    assert result.returncode == 2
    assert expected in result.stderr
    assert not result.stdout
    assert "Traceback" not in result.stderr


def test_plan_displays_hierarchy_ranges_metrics_and_warning() -> None:
    result = run_cli("plan", str(AV))
    assert result.returncode == 0
    for expected in (
        "KOMPLETNY",
        "Dźwięk",
        "10.42.0.0/27",
        "2001:db8:42:100::/64",
        "DHCP",
        "Infrastruktura IPv6",
        "Metryki IPv4",
        "Metryki IPv6",
    ):
        assert expected in result.stdout
    assert "OSTRZEŻENIE [high_segment_utilization] [audio: Dźwięk]" in result.stderr
    assert "INFO" not in result.stderr


def test_plan_free_blocks_and_verbose_diagnostics_are_explicit() -> None:
    result = run_cli("plan", str(AV), "--show-free", "--verbose")
    assert result.returncode == 0
    assert "Wolny CIDR" in result.stdout
    assert "INFO [summary_route]" in result.stderr
    assert "Blok sumaryczny" in result.stderr


def test_plan_json_stdout_is_clean_reimportable_and_matches_saved_file(tmp_path: Path) -> None:
    output = tmp_path / "wynik próby.json"
    result = run_cli("plan", str(AV), "--json", "--output", str(output), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    state = loads_project(result.stdout)
    assert state == load_project(AV)
    assert output.read_bytes() == result.stdout.encode("utf-8")
    assert "Zapisano JSON" in result.stderr
    assert "OSTRZEŻENIE" not in result.stdout


def test_bad_project_input_and_read_errors_are_polish(tmp_path: Path) -> None:
    missing = run_cli("plan", str(tmp_path / "missing.json"))
    assert missing.returncode == 2 and "file_read_error" in missing.stderr
    invalid = tmp_path / "invalid.json"
    data = json.loads(AV.read_text(encoding="utf-8"))
    data["project"]["nodes"][2]["hosts"] = "20"
    invalid.write_text(json.dumps(data), encoding="utf-8")
    result = run_cli("plan", str(invalid))
    assert result.returncode == 2
    assert "project.nodes[2].hosts" in result.stderr and "liczba całkowita" in result.stderr
    assert "Traceback" not in result.stderr


def test_incomplete_plan_returns_one_and_can_be_saved_for_repair(
    tmp_path: Path, t4_project: Project
) -> None:
    project = replace(
        t4_project,
        nodes=tuple(replace(n, hosts=5000) if n.id == "a_wifi" else n for n in t4_project.nodes),
    )
    source, target = tmp_path / "source.json", tmp_path / "partial.json"
    save_project(source, project)
    result = run_cli("plan", str(source), "--json", "-o", str(target))
    assert result.returncode == 1
    assert not json.loads(result.stdout)["plan"]["is_complete"]
    assert load_project(target).project == project
    assert "Brak miejsca" in result.stderr
    assert "sugerowany prefiks puli: /" in result.stderr
    assert "a_wifi" in result.stderr or "site" in result.stderr


def test_freeze_reloads_all_pins_and_allows_future_expansion(
    tmp_path: Path, t5_project: Project
) -> None:
    source, target = tmp_path / "source.json", tmp_path / "frozen.json"
    save_project(source, t5_project)
    original = source.read_bytes()
    result = run_cli("freeze", str(source), "-o", str(target), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Zamrożono" in result.stdout
    assert source.read_bytes() == original
    frozen = load_project(target)
    plan = build_plan(t5_project)
    assert frozen.plan == plan
    assert frozen.project.pinned_v6_infrastructure == plan.v6_infrastructure
    assert all(n.pinned_v4 is not None and n.pinned_v6 is not None for n in frozen.project.nodes)
    extended = replace(
        frozen.project,
        nodes=(*frozen.project.nodes, Segment(id="new", name="Nowy", parent_id="a", hosts=1)),
    )
    after = build_plan(extended)
    assert after.is_complete
    for old, new in (
        (plan.v4_allocations, after.v4_allocations),
        (plan.v6_allocations, after.v6_allocations),
    ):
        lookup = {a.node_id: a.network for a in new}
        assert all(lookup[a.node_id] == a.network for a in old)


def test_freeze_refuses_incomplete_plan_without_touching_target(
    tmp_path: Path, t5_project: Project
) -> None:
    invalid = replace(
        t5_project,
        settings=replace(
            t5_project.settings, v6_subnet_strategy=IPv6SubnetStrategy.VLAN_DECIMAL_AS_HEX
        ),
    )
    source, target = tmp_path / "source.json", tmp_path / "frozen.json"
    save_project(source, invalid)
    target.write_bytes(b"previous content")
    result = run_cli("freeze", str(source), "--output", str(target))
    assert result.returncode == 1
    assert "Nie można zamrozić" in result.stderr
    assert "VLAN-u od 1 do 999" in result.stderr
    assert target.read_bytes() == b"previous content"
    assert not result.stdout


def test_explicit_in_place_freeze_is_valid_and_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "project.json"
    save_project(target, load_project(AV).project)
    assert run_cli("freeze", str(target), "-o", str(target)).returncode == 0
    once = target.read_bytes()
    assert run_cli("freeze", str(target), "-o", str(target)).returncode == 0
    assert target.read_bytes() == once


def test_output_write_errors_return_two_without_traceback(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "out.json"
    for command in ("plan", "freeze"):
        result = run_cli(command, str(AV), "-o", str(target))
        assert result.returncode == 2
        assert "file_write_error" in result.stderr
        assert "Traceback" not in result.stderr
        assert not target.exists()


def test_user_text_cannot_inject_terminal_control_sequences(tmp_path: Path) -> None:
    state = load_project(AV)
    project = replace(
        state.project,
        name="Próba\n\x1b[31m",
        nodes=tuple(
            replace(n, name="Dźwięk\t\x1b[2J") if n.id == "audio" else n
            for n in state.project.nodes
        ),
    )
    target = tmp_path / "controls.json"
    save_project(target, project)
    result = run_cli("plan", str(target))
    assert result.returncode == 0
    assert "\\n\\x1b[31m" in result.stdout
    assert "\x1b" not in result.stdout + result.stderr
    assert "\\t\\x1b[2J" in result.stderr


def test_empty_plan_and_unknown_finding_have_usable_output() -> None:
    project = replace(load_project(AV).project, nodes=())
    assert "Status: KOMPLETNY" in format_plan(project, build_plan(project), show_free=True)
    finding = Finding(code="future_code", level=FindingLevel.WARNING, node_id="unknown")
    assert "OSTRZEŻENIE [future_code] [unknown]" in format_finding(finding, project)


def test_bad_segment_requirements_are_explained_in_polish(tmp_path: Path) -> None:
    # Use JSON strings at the input boundary; core receives a typed enum.
    raw = json.loads(AV.read_text(encoding="utf-8"))
    raw["project"]["nodes"][2].update(hosts=0, gateway="none", gateway_addrs=0)
    source = tmp_path / "bad-lan.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    result = run_cli("plan", str(source))
    assert result.returncode == 1
    assert "co najmniej jednego użytecznego adresu" in result.stderr
    assert "must need" not in result.stderr


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_export_stdout_contains_the_selected_document(format: str) -> None:
    import csv
    from io import StringIO

    result = run_cli("export", str(AV), "--format", format)
    assert result.returncode == 0, result.stderr
    assert "Zapisano eksport" not in result.stdout
    assert "OSTRZEŻENIE [high_segment_utilization]" in result.stderr
    if format == "json":
        assert loads_project(result.stdout) == load_project(AV)
    elif format == "csv":
        rows = list(csv.DictReader(StringIO(result.stdout), delimiter=";"))
        assert len(rows) == 3
        assert rows[0]["Segment"] == "Dźwięk"
    else:
        assert result.stdout.startswith("# Plan adresacji")
        assert "## Wolne bloki" in result.stdout


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_export_to_file_has_expected_bytes_and_no_document_on_stdout(
    format, tmp_path: Path
) -> None:
    from adresplan.application.exporting import export_document

    target = tmp_path / f"próba.{format}"
    result = run_cli("export", str(AV), "-f", format, "-o", str(target), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert not result.stdout
    assert "Zapisano eksport" in result.stderr
    expected = export_document(load_project(AV).project, format)
    assert target.read_bytes() == expected.encode("utf-8-sig" if format == "csv" else "utf-8")


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_export_incomplete_plan_is_marked_and_returns_one(format, tmp_path: Path) -> None:
    source = ROOT / "examples/t3-no-space.json"
    target = tmp_path / f"partial.{format}"
    result = run_cli("export", str(source), "-f", format, "-o", str(target))
    assert result.returncode == 1
    assert target.exists() and "insufficient_space" in result.stderr
    text = target.read_text(encoding="utf-8-sig")
    assert '"is_complete": false' in text if format == "json" else "NIEKOMPLETNY" in text


@pytest.mark.parametrize("arguments", [(), ("-f", "xlsx"), ("--format",), ("--form", "csv")])
def test_export_bad_or_missing_format_is_argument_error(arguments) -> None:
    result = run_cli("export", str(AV), *arguments)
    assert result.returncode == 2
    assert "Błąd argumentów" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("format", ["csv", "md"])
def test_document_export_does_not_overwrite_the_source_project(format, tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(AV.read_bytes())
    original = source.read_bytes()
    result = run_cli("export", str(source), "-f", format, "-o", str(source))
    assert result.returncode == 2
    assert "innego pliku" in result.stderr
    assert source.read_bytes() == original


def test_json_export_can_explicitly_update_its_own_input(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(AV.read_bytes())
    expected = load_project(source)
    result = run_cli("export", str(source), "-f", "json", "-o", str(source))
    assert result.returncode == 0
    assert load_project(source) == expected


@pytest.mark.parametrize("format", ["csv", "md", "json"])
def test_export_file_errors_do_not_truncate_old_document(format, tmp_path: Path) -> None:
    target = tmp_path / f"old.{format}"
    target.write_bytes(b"previous document")
    source = tmp_path / "bad.json"
    source.write_text("{broken", encoding="utf-8")
    result = run_cli("export", str(source), "-f", format, "-o", str(target))
    assert result.returncode == 2
    assert target.read_bytes() == b"previous document"
    result = run_cli("export", str(AV), "-f", format, "-o", str(tmp_path / "missing" / "plan"))
    assert result.returncode == 2 and "file_write_error" in result.stderr
