"""Installed entry point and core dependency boundaries."""

import ast
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from adresplan import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__


def test_module_entry_point_help_and_version() -> None:
    for argument in ("--help", "--version"):
        result = subprocess.run(
            [sys.executable, "-m", "adresplan", argument],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert ("Address Plan" if argument == "--help" else __version__) in result.stdout


def test_core_imports_only_the_standard_library_and_itself() -> None:
    for path in (ROOT / "src" / "adresplan" / "core").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert (
                    module.startswith("adresplan.core")
                    or module.split(".")[0] in sys.stdlib_module_names
                ), (path, module)


def test_example_runs_and_shows_the_reference_addresses() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "stage1_vlsm.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "192.168.10.0/25" in result.stdout
    assert "192.168.10.240/28" in result.stdout


def test_hierarchy_example_runs_and_preserves_frozen_addresses() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "stage2_hierarchy.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert all(
        network in result.stdout for network in ("10.20.0.0/23", "10.20.2.0/24", "10.20.3.0/27")
    )
    assert "Dotychczasowe adresy: bez zmian" in result.stdout


def test_ipv6_example_runs_t5_and_dual_stack_freeze() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "stage3_ipv6.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "2001:db8:abcd:100::/56" in result.stdout
    assert "2001:db8:abcd:120::/64" in result.stdout
    assert "Dotychczasowe adresy IPv4/IPv6: bez zmian" in result.stdout
    assert "Pule infrastruktury: bez zmian" in result.stdout


def test_json_example_runs_and_preserves_input_plan_and_freeze() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "stage4a_json.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Eksport i ponowny import: identyczny projekt i plan" in result.stdout
    assert "Zamrożone IPv4/IPv6 i infrastruktura: zachowane" in result.stdout
    assert "2001:db8:42:100::/64" in result.stdout
