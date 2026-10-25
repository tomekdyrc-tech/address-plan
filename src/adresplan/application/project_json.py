"""Versioned JSON import/export and atomic UTF-8 file storage."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from pydantic import TypeAdapter, ValidationError

from adresplan.application.files import write_atomic
from adresplan.application.schemas import SCHEMA_VERSION, DocumentInput, ProjectInput
from adresplan.core.models import Plan, Project
from adresplan.core.plan import build_plan
from adresplan.core.structure import validate_structure

MAX_JSON_BYTES = 16 * 1024 * 1024
_PROJECT_ADAPTER = TypeAdapter(Project)
_PLAN_ADAPTER = TypeAdapter(Plan)


@dataclass(frozen=True, slots=True)
class InputIssue:
    path: tuple[str | int, ...]
    code: str
    message: str

    @property
    def location(self) -> str:
        result = ""
        for part in self.path:
            result += f"[{part}]" if isinstance(part, int) else f".{part}" if result else part
        return result or "$"


class ProjectJSONError(ValueError):
    """Boundary error with stable codes and Polish text for future CLI/web use."""

    def __init__(self, issues: tuple[InputIssue, ...]) -> None:
        self.issues = issues
        super().__init__("\n".join(f"{i.location}: {i.message}" for i in issues))


@dataclass(frozen=True, slots=True)
class ProjectState:
    project: Project
    plan: Plan


_MESSAGES = {
    "missing": "Brakuje wymaganego pola.",
    "extra_forbidden": "Nieznane pole; sprawdź nazwę i wersję formatu.",
    "int_type": "Wymagana jest liczba całkowita, bez cudzysłowów.",
    "bool_type": "Wymagana jest wartość true albo false.",
    "string_type": "Wymagany jest tekst.",
    "list_type": "Wymagana jest tablica JSON.",
    "dict_type": "Wymagany jest obiekt JSON.",
    "model_type": "Wymagany jest obiekt JSON.",
    "enum": "Niedozwolona wartość; sprawdź listę wartości w schemacie JSON.",
    "literal_error": "Niedozwolona wartość pola.",
    "union_tag_invalid": "Nieznany kind; wybierz site, building albo segment.",
    "union_tag_not_found": "Brakuje kind: site, building albo segment.",
    "greater_than_equal": "Wartość jest mniejsza od dozwolonego minimum.",
    "less_than_equal": "Wartość przekracza dozwolone maksimum.",
    "multiple_of": "Wartość prefiksu musi być wielokrotnością 4.",
    "string_too_short": "Tekst jest za krótki.",
}
_STRUCTURE_MESSAGES = {
    "duplicate_node_id": "Identyfikator węzła występuje więcej niż raz.",
    "site_has_parent": "Lokalizacja nie może mieć rodzica.",
    "missing_parent": "Nie znaleziono rodzica o podanym identyfikatorze.",
    "invalid_parent_kind": "Budynek musi należeć do lokalizacji, a segment do budynku.",
    "parent_cycle": "Relacje rodziców tworzą cykl.",
}


def _fail(code: str, message: str) -> NoReturn:
    raise ProjectJSONError((InputIssue((), code, message),))


def _validation_error(error: ValidationError, *, project_only: bool = False) -> ProjectJSONError:
    issues: list[InputIssue] = []
    for item in error.errors(include_url=False, include_input=False, include_context=False):
        path = item["loc"]
        if project_only:
            path = ("project", *path)
        # Discriminator labels are implementation details, not JSON path components.
        if (
            len(path) > 3
            and path[:2] == ("project", "nodes")
            and isinstance(path[2], int)
            and path[3] in ("site", "building", "segment")
        ):
            path = (*path[:3], *path[4:])
        code = item["type"]
        message = _MESSAGES.get(code, item["msg"])
        if path == ("schema_version",):
            code = "unsupported_schema_version" if code != "missing" else "missing"
            message = (
                f"Wymagana jest schema_version jako liczba całkowita od 1 do {SCHEMA_VERSION}."
            )
        issues.append(InputIssue(path, code, message))
    return ProjectJSONError(tuple(issues))


def _check_structure(project: Project) -> None:
    findings = validate_structure(project)
    if not findings:
        return
    issues: list[InputIssue] = []
    for finding in findings:
        for index, node in enumerate(project.nodes):
            if node.id == finding.node_id:
                field = "id" if finding.code == "duplicate_node_id" else "parent_id"
                issues.append(
                    InputIssue(
                        ("project", "nodes", index, field),
                        finding.code,
                        _STRUCTURE_MESSAGES.get(finding.code, "Nieprawidłowa struktura drzewa."),
                    )
                )
    raise ProjectJSONError(tuple(issues))


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key", f"Powtórzone pole JSON: {key}.")
        result[key] = value
    return result


def _constant(value: str) -> NoReturn:
    _fail("invalid_json_number", f"Wartość {value} nie jest poprawną liczbą JSON.")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _constant(value)
    return number


def loads_project(data: str | bytes) -> ProjectState:
    """Import input only and recompute; a saved plan never supplies allocations."""
    try:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        if len(raw) > MAX_JSON_BYTES:
            _fail("json_too_large", "Plik JSON przekracza limit 16 MiB.")
        text = raw.decode("utf-8-sig")
    except UnicodeError as error:
        raise ProjectJSONError(
            (InputIssue((), "invalid_utf8", "Plik musi używać UTF-8."),)
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_constant,
            parse_float=_finite_float,
        )
    except json.JSONDecodeError as error:
        raise ProjectJSONError(
            (
                InputIssue(
                    (),
                    "invalid_json",
                    f"Błędny JSON: wiersz {error.lineno}, kolumna {error.colno}.",
                ),
            )
        ) from error
    except (RecursionError, ValueError) as error:
        if isinstance(error, ProjectJSONError):
            raise
        raise ProjectJSONError(
            (InputIssue((), "invalid_json", "Nieprawidłowa liczba lub zbyt głęboki JSON."),)
        ) from error
    try:
        document = DocumentInput.model_validate(value)
    except ValidationError as error:
        raise _validation_error(error) from error
    project = document.project.to_core()
    _check_structure(project)
    return ProjectState(project, build_plan(project))


def prepare_project(project: Project) -> ProjectState:
    """Validate typed input once and calculate a fresh result for every exporter."""
    try:
        data = ProjectInput.model_validate(
            _PROJECT_ADAPTER.dump_python(
                project, mode="json", warnings=False, serialize_as_any=True
            )
        )
    except ValidationError as error:
        raise _validation_error(error, project_only=True) from error
    canonical = data.to_core()
    _check_structure(canonical)
    if canonical != project:
        _fail("invalid_project", "Dane projektu nie odpowiadają typowanym modelom wejściowym.")
    return ProjectState(canonical, build_plan(canonical))


def dumps_project(project: Project) -> str:
    """Validate and export the complete input plus a fresh, deterministic snapshot."""
    state = prepare_project(project)
    data = _PROJECT_ADAPTER.dump_python(
        state.project, mode="json", warnings=False, serialize_as_any=True
    )
    plan = state.plan
    snapshot = _PLAN_ADAPTER.dump_python(plan, mode="json")
    snapshot["is_complete"] = plan.is_complete
    text = (
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "project": data,
                "plan": snapshot,
            },
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    )
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise ProjectJSONError(
            (InputIssue((), "invalid_utf8", "Projekt zawiera tekst spoza poprawnego UTF-8."),)
        ) from error
    if size > MAX_JSON_BYTES:
        _fail("json_too_large", "Eksport JSON przekracza limit 16 MiB.")
    return text


def load_project(path: str | Path) -> ProjectState:
    """Read at most the documented limit, including UTF-8 files with a BOM."""
    target = Path(path)
    try:
        with target.open("rb") as stream:
            data = stream.read(MAX_JSON_BYTES + 1)
    except OSError as error:
        raise ProjectJSONError(
            (
                InputIssue(
                    (), "file_read_error", f"Nie można odczytać pliku {target}: {error.strerror}."
                ),
            )
        ) from error
    return loads_project(data)


def save_project(path: str | Path, project: Project) -> None:
    """Replace one file atomically after validation; never truncate the old file first."""
    text = dumps_project(project)
    target = Path(path)
    try:
        write_atomic(target, text.encode("utf-8"))
    except OSError as error:
        raise ProjectJSONError(
            (
                InputIssue(
                    (), "file_write_error", f"Nie można zapisać pliku {target}: {error.strerror}."
                ),
            )
        ) from error
