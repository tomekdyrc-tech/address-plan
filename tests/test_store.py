"""Persistence, isolation and concurrent edit contracts."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from adresplan.application.project_json import ProjectJSONError, load_project
from adresplan.store.sqlite import (
    MissingProject,
    ProjectStore,
    RevisionConflict,
    StoreError,
    database_path,
    duplicate_project,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def store(tmp_path):
    return ProjectStore(tmp_path / "nested" / "projects.sqlite3")


def test_restart_input_only_and_isolation(store):
    project = load_project(EXAMPLES / "church-av.json").project
    first = store.create(project)
    second = store.create(project)
    store.save(first.key, replace(project, name="Zmieniony"), 1)
    restarted = ProjectStore(store.path)
    assert restarted.get(first.key).revision == 2
    assert restarted.get(second.key).project == project
    assert restarted.list()[0].name == "Zmieniony"
    with sqlite3.connect(store.path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 3
        document = json.loads(db.execute("SELECT document FROM projects LIMIT 1").fetchone()[0])
    assert set(document) == {"schema_version", "project"}


def test_optimistic_lock_is_transactional(store):
    project = load_project(EXAMPLES / "budynek.json").project
    saved = store.create(project)

    def update(name):
        try:
            return store.save(saved.key, replace(project, name=name), 1).project.name
        except RevisionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ["A", "B"]))
    assert results.count("conflict") == 1
    assert store.get(saved.key).revision == 2
    assert store.get(saved.key).project.name in results


def test_bad_inputs_and_identity_do_not_write(store):
    project = load_project(EXAMPLES / "budynek.json").project
    saved = store.create(project)
    with pytest.raises(ProjectJSONError):
        store.save(saved.key, replace(project, name=""), 1)
    with pytest.raises(StoreError):
        store.save(saved.key, replace(project, id="other"), 1)
    assert store.get(saved.key) == saved
    with pytest.raises(MissingProject):
        store.get("missing")
    with pytest.raises(MissingProject):
        store.save("missing", project, 1)


@pytest.mark.parametrize("version", [0, 1, 2])
def test_unknown_database_is_preserved(tmp_path, version):
    path = tmp_path / "foreign.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (value TEXT)")
        db.execute(f"PRAGMA user_version={version}")
    before = path.read_bytes()
    with pytest.raises(StoreError):
        ProjectStore(path)
    assert path.read_bytes() == before


def test_duplicate_remaps_ids_and_preserves_frozen_addresses():
    from adresplan.core.freeze import freeze
    from adresplan.core.plan import build_plan

    source = load_project(EXAMPLES / "church-av.json").project
    frozen = freeze(source, build_plan(source))
    copied = duplicate_project(frozen)
    assert copied.id != source.id
    assert not {n.id for n in copied.nodes} & {n.id for n in source.nodes}
    assert [n.pinned_v4 for n in copied.nodes] == [n.pinned_v4 for n in frozen.nodes]
    assert build_plan(copied).is_complete
    assert {p.site_id for p in copied.pinned_v6_infrastructure} <= {n.id for n in copied.nodes}


def test_database_override_and_default(monkeypatch, tmp_path):
    monkeypatch.setenv("ADRESPLAN_DB", str(tmp_path / "environment.db"))
    assert database_path() == tmp_path / "environment.db"
    assert database_path(tmp_path / "argument.db") == tmp_path / "argument.db"
    monkeypatch.delenv("ADRESPLAN_DB")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert database_path().name == "adresplan.sqlite3"
    assert "src" not in database_path().parts
