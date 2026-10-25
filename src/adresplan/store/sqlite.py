"""Versioned, transactional storage of validated project inputs only."""

from __future__ import annotations

import builtins
import json
import os
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from adresplan import __version__
from adresplan.application.project_json import dumps_project, loads_project
from adresplan.core.models import Project


class StoreError(ValueError):
    """A database cannot be used safely."""


class MissingProject(StoreError):
    """The requested storage key does not exist."""


class RevisionConflict(StoreError):
    """The caller edited an obsolete version."""


class TemplateNameError(StoreError):
    """A template label needs correction by the user."""


def template_name(value: str) -> str:
    label = value.strip()
    if not label or len(label) > 200:
        raise TemplateNameError("Nazwa szablonu musi zawierać od 1 do 200 znaków.")
    return label


@dataclass(frozen=True, slots=True)
class StoredProject:
    key: str
    project: Project
    revision: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    key: str
    name: str
    revision: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class RevisionSummary:
    revision: int
    created_at: str
    reason: str
    app_version: str


def database_path(override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    if value := os.environ.get("ADRESPLAN_DB"):
        return Path(value).expanduser().resolve()
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return root / "AddressPlan" / "adresplan.sqlite3"


def input_document(project: Project) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(dumps_project(project))
    del document["plan"]
    return document


def duplicate_project(project: Project) -> Project:
    ids = {node.id: uuid4().hex for node in project.nodes}
    return replace(
        project,
        id=uuid4().hex,
        name=project.name + " — kopia",
        nodes=tuple(
            replace(node, id=ids[node.id], parent_id=ids.get(node.parent_id or ""))
            for node in project.nodes
        ),
        pinned_v6_infrastructure=tuple(
            replace(pool, site_id=ids[pool.site_id]) for pool in project.pinned_v6_infrastructure
        ),
        blocked_subnets=tuple(
            replace(block, parent_id=ids.get(block.parent_id or ""))
            for block in project.blocked_subnets
        ),
    )


class ProjectStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if tables:
                    raise StoreError("Plik zawiera obcą bazę danych. Wybierz inny plik.")
                connection.execute(
                    "CREATE TABLE projects (key TEXT PRIMARY KEY, name TEXT NOT NULL, "
                    "document TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision > 0), "
                    "updated_at TEXT NOT NULL)"
                )
                connection.execute("PRAGMA user_version=1")
            elif version not in (1, 2, 3):
                raise StoreError("Nieobsługiwana wersja bazy. Użyj odpowiedniej wersji aplikacji.")
            columns = connection.execute("PRAGMA table_info(projects)").fetchall()
            if [row[1] for row in columns] != ["key", "name", "document", "revision", "updated_at"]:
                raise StoreError("Nieprawidłowa struktura bazy projektów.")
            if version in (0, 1):
                connection.execute(
                    "CREATE TABLE revisions (project_key TEXT NOT NULL, revision INTEGER NOT NULL, "
                    "document TEXT NOT NULL, created_at TEXT NOT NULL, reason TEXT NOT NULL, "
                    "app_version TEXT NOT NULL, PRIMARY KEY(project_key, revision))"
                )
                connection.execute(
                    "CREATE TABLE building_templates (key TEXT PRIMARY KEY, name TEXT NOT NULL, "
                    "document TEXT NOT NULL, created_at TEXT NOT NULL)"
                )
                for key, raw, rev, stamp in connection.execute(
                    "SELECT key, document, revision, updated_at FROM projects"
                ).fetchall():
                    snapshot = dumps_project(loads_project(raw).project)
                    connection.execute(
                        "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            key,
                            rev,
                            snapshot,
                            stamp,
                            "Początek historii po aktualizacji",
                            __version__,
                        ),
                    )
                connection.execute("PRAGMA user_version=2")
            if version in (0, 1, 2):
                connection.execute(
                    "ALTER TABLE building_templates ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
                )
                connection.execute(
                    "ALTER TABLE building_templates ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
                )
                connection.execute("PRAGMA user_version=3")
            for table, expected in (
                (
                    "revisions",
                    ["project_key", "revision", "document", "created_at", "reason", "app_version"],
                ),
                (
                    "building_templates",
                    ["key", "name", "document", "created_at", "archived", "revision"],
                ),
            ):
                actual = [r[1] for r in connection.execute(f"PRAGMA table_info({table})")]
                if actual != expected:
                    raise StoreError("Nieprawidłowa struktura historii lub szablonów.")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        except sqlite3.Error as error:
            raise StoreError("Nie udało się odczytać lub zapisać bazy projektów.") from error
        finally:
            connection.close()

    def list(self) -> list[ProjectSummary]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT key, name, revision, updated_at FROM projects ORDER BY updated_at DESC, key"
            ).fetchall()
        return [ProjectSummary(*row) for row in rows]

    def get(self, key: str) -> StoredProject:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT document, revision, updated_at FROM projects WHERE key=?", (key,)
            ).fetchone()
        if row is None:
            raise MissingProject("Nie znaleziono projektu.")
        return StoredProject(key, loads_project(row[0]).project, row[1], row[2])

    def create(self, project: Project) -> StoredProject:
        document = json.dumps(input_document(project), ensure_ascii=False)
        key = uuid4().hex
        now = datetime.now(UTC).isoformat(timespec="microseconds")
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO projects VALUES (?, ?, ?, 1, ?)", (key, project.name, document, now)
            )
            connection.execute(
                "INSERT INTO revisions VALUES (?, 1, ?, ?, ?, ?)",
                (key, dumps_project(project), now, "Utworzenie projektu", __version__),
            )
        return StoredProject(key, project, 1, now)

    def save(
        self, key: str, project: Project, expected_revision: int, reason: str = "Edycja projektu"
    ) -> StoredProject:
        document = json.dumps(input_document(project), ensure_ascii=False)
        now = datetime.now(UTC).isoformat(timespec="microseconds")
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT document, revision FROM projects WHERE key=?", (key,)
            ).fetchone()
            if row is None:
                raise MissingProject("Nie znaleziono projektu.")
            if row[1] != expected_revision:
                raise RevisionConflict(
                    "Projekt zmienił się w innej karcie. Wczytaj aktualną wersję."
                )
            if json.loads(row[0])["project"]["id"] != project.id:
                raise StoreError("Nie można zmienić identyfikatora istniejącego projektu.")
            # Debounced input/change events may submit identical data twice.
            if json.loads(row[0]) == json.loads(document) and not reason.startswith("Przywrócenie"):
                stamp = connection.execute(
                    "SELECT updated_at FROM projects WHERE key=?", (key,)
                ).fetchone()[0]
                return StoredProject(key, project, expected_revision, stamp)
            connection.execute(
                "UPDATE projects SET name=?, document=?, revision=revision+1, updated_at=? "
                "WHERE key=? AND revision=?",
                (project.name, document, now, key, expected_revision),
            )
            connection.execute(
                "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?)",
                (key, expected_revision + 1, dumps_project(project), now, reason, __version__),
            )
        return StoredProject(key, project, expected_revision + 1, now)

    def history(
        self, key: str, *, offset: int = 0, limit: int = 50
    ) -> builtins.list[RevisionSummary]:
        self.get(key)
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT revision, created_at, reason, app_version FROM revisions "
                "WHERE project_key=? ORDER BY revision DESC LIMIT ? OFFSET ?",
                (key, max(1, min(limit, 100)), max(0, offset)),
            ).fetchall()
        return [RevisionSummary(*r) for r in rows]

    def snapshot(self, key: str, revision: int) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT document FROM revisions WHERE project_key=? AND revision=?",
                (key, revision),
            ).fetchone()
        if row is None:
            raise MissingProject("Nie znaleziono tej wersji projektu.")
        result: dict[str, Any] = json.loads(row[0])
        return result

    def restore(self, key: str, target: int, expected_revision: int) -> StoredProject:
        project = loads_project(json.dumps(self.snapshot(key, target))).project
        return self.save(key, project, expected_revision, f"Przywrócenie wersji {target}")

    def templates(self, *, archived: bool = False) -> builtins.list[dict[str, str]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT key, name FROM building_templates WHERE archived=? ORDER BY name, key",
                (int(archived),),
            ).fetchall()
        return [{"key": r[0], "name": r[1]} for r in rows]

    def save_template(self, name: str, document: dict[str, Any]) -> str:
        label = template_name(name)
        key = uuid4().hex
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO building_templates (key,name,document,created_at) VALUES (?, ?, ?, ?)",
                (
                    key,
                    label,
                    json.dumps(document, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return key

    def template(self, key: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT document FROM building_templates WHERE key=? AND archived=0", (key,)
            ).fetchone()
        if row is None:
            raise MissingProject("Nie znaleziono szablonu budynku.")
        result: dict[str, Any] = json.loads(row[0])
        return result

    def template_details(self, key: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT name,document,created_at,archived,revision "
                "FROM building_templates WHERE key=?",
                (key,),
            ).fetchone()
        if row is None:
            raise MissingProject("Nie znaleziono szablonu.")
        return {
            "key": key,
            "name": row[0],
            "document": json.loads(row[1]),
            "created_at": row[2],
            "archived": bool(row[3]),
            "revision": row[4],
        }

    def update_template(
        self,
        key: str,
        expected: int,
        *,
        name: str | None = None,
        document: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> None:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT name,document,archived,revision FROM building_templates WHERE key=?", (key,)
            ).fetchone()
            if row is None:
                raise MissingProject("Nie znaleziono szablonu.")
            if row[3] != expected:
                raise RevisionConflict("Szablon zmienił się w innej karcie. Odśwież bibliotekę.")
            # Old releases accepted longer names. Archiving or replacing their
            # contents must remain possible without forcing a rename first.
            label = row[0] if name is None else template_name(name)
            connection.execute(
                "UPDATE building_templates SET name=?, document=?, archived=?, "
                "revision=revision+1 WHERE key=?",
                (
                    label,
                    row[1] if document is None else json.dumps(document, ensure_ascii=False),
                    row[2] if archived is None else int(archived),
                    key,
                ),
            )

    def backup(self) -> bytes:
        """Consistent snapshot of the live database, including history and templates."""
        with self.connection() as source, closing(sqlite3.connect(":memory:")) as snapshot:
            source.backup(snapshot)
            return snapshot.serialize()
