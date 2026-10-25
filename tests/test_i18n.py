"""English interface and reports: complete catalogue, no Polish left in English output."""

import ast
import contextlib
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adresplan import i18n
from adresplan.application import history, messages, project_json
from adresplan.application.exporting import export_bytes, export_document
from adresplan.cli import main
from adresplan.export.csv_ import CSV_COLUMNS
from adresplan.i18n import tr, use_language
from adresplan.web import forms
from adresplan.web.app import create_app
from adresplan.web.routes.projects import SAVE_REASONS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "adresplan"
EXAMPLES = ROOT / "examples"
POLISH = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


def literal_ids() -> set[str]:
    """Every literal passed to tr()/tr_all() in Python code and Jinja templates."""
    found: set[str] = set()
    for path in SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("tr", "tr_all")
            ):
                found.update(
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                )
    for path in (SOURCE / "web" / "templates").glob("*.html"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"""\btr\((?:"((?:[^"\\]|\\.)*)"|'([^']*)')""", text):
            found.add(json.loads(f'"{match[1]}"') if match[1] is not None else match[2])
    return found


def catalogue_ids() -> set[str]:
    """Polish ids kept in tables and translated where they are displayed."""
    ids = set(literal_ids())
    for table in (
        messages.CALC_MESSAGES,
        messages.FINDING_MESSAGES,
        messages.REASONS,
        messages.DETAIL_LABELS,
        messages.NODE_KINDS,
        messages.V6_ADDRESS_KINDS,
        messages.POOL_KINDS,
        messages.LEVEL_LABELS,
        project_json._MESSAGES,
        project_json._STRUCTURE_MESSAGES,
        history._LABELS,
        SAVE_REASONS,
    ):
        ids.update(table.values())
    ids.update(history.HISTORY_REASONS)
    ids.update(CSV_COLUMNS)
    for field in (
        *forms.DOCUMENT_FIELDS,
        *forms.PROJECT_FIELDS,
        *forms.SETTINGS_FIELDS,
        *forms.NODE_FIELDS,
        *forms.SEGMENT_FIELDS,
    ):
        ids.add(field.label)
        ids.update(label for _, label in field.choices)
    return ids


def test_every_message_id_has_an_english_translation() -> None:
    missing = sorted(catalogue_ids() - i18n.catalog().keys())
    assert missing == []


def test_catalogue_entries_are_english_and_keep_placeholders() -> None:
    catalogue = i18n.catalog()
    for polish, english in catalogue.items():
        assert english.strip(), polish
        assert set(re.findall(r"{(\w+)}", polish)) == set(re.findall(r"{(\w+)}", english)), polish
        assert not POLISH.search(english), english


def test_history_reasons_cover_editor_actions() -> None:
    assert set(SAVE_REASONS.values()) <= history.HISTORY_REASONS


def test_tr_formats_values_and_follows_the_active_language() -> None:
    assert tr("Pokazano {shown}", shown=3) == "Pokazano 3"
    with use_language("en"):
        assert tr("Pokazano {shown}", shown=3) == "Shown: 3"
    assert i18n.language() == "pl"


@pytest.mark.parametrize(
    ("header", "expected"),
    [(None, "pl"), ("pl-PL,pl;q=0.9,en;q=0.8", "pl"), ("en-US,en;q=0.9", "en"), ("de", "en")],
)
def test_browser_language_preference(header, expected) -> None:
    assert i18n.preferred_language(header) == expected


@pytest.fixture
def english(tmp_path):
    app = create_app(tmp_path / "web.sqlite3")
    with TestClient(app, base_url="http://localhost") as client:
        token = client.get("/api/session").json()["csrf_token"]
        client.headers["X-CSRF-Token"] = token
        client.cookies.set("lang", "en")
        i18n.missing.clear()
        yield client, app.state.store, token


def _key(response) -> str:
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[1]


def _save(client, key, store, **data):
    payload = {"revision": str(store.get(key).revision), **data}
    return client.post(f"/p/{key}/save", data=payload, headers={"HX-Request": "true"})


def _english_project(client, store) -> str:
    key = _key(
        client.post(
            "/projects/new",
            data={"ipv6_usage": "yes", "start_template": "building|starter:office"},
            follow_redirects=False,
        )
    )
    project = store.get(key).project
    site = next(n for n in project.nodes if n.kind == "site")
    building = next(n for n in project.nodes if n.kind == "building")
    _save(
        client,
        key,
        store,
        action="add",
        new_kind="segment",
        new_name="Cameras",
        new_parent=building.id,
        new_hosts="40",
        new_vlan="40",
    )
    _save(
        client,
        key,
        store,
        action="add",
        new_kind="building",
        new_name="Warehouse",
        new_parent=site.id,
    )
    _save(client, key, store, action="block-add", blocked_networks="10.0.200.0/24; Old CCTV")
    _save(client, key, store, action=f"template-save:{building.id}", template_name="Office")
    _save(client, key, store, action=f"site-template-save:{site.id}", template_name="Branch")
    _save(
        client,
        key,
        store,
        action="template-apply",
        template_key="starter:av",
        template_site=site.id,
        template_building_name="Hall",
    )
    _save(client, key, store, action=f"duplicate:{building.id}")
    _save(client, key, store, action="ipv6-fit")
    _save(client, key, store, action="freeze")
    _save(client, key, store, action="unpin")
    _save(client, key, store, action="save", planning_mode="review", **{"p.name": "Head office"})
    return key


def _visit_project(client, key) -> list[str]:
    pages = [
        client.get(f"/p/{key}").text,
        client.get(f"/p/{key}/history").text,
        client.get(f"/p/{key}/history?before=1&after=2").text,
        client.get(f"/p/{key}/diagram").text,
        client.get(f"/api/projects/{key}/diagram.svg").text,
    ]
    for profile in ("full", "brief"):
        pages.append(client.get(f"/p/{key}/print?profile={profile}").text)
        for extension in ("md", "csv", "json", "xlsx", "docx", "cisco", "mikrotik"):
            pages.append(client.get(f"/p/{key}/export?format={extension}&profile={profile}").text)
            content = client.get(f"/api/projects/{key}/export.{extension}?profile={profile}")
            assert content.status_code == 200
            if extension in ("xlsx", "docx"):
                with zipfile.ZipFile(io.BytesIO(content.content)) as archive:
                    pages.extend(
                        archive.read(name).decode("utf-8")
                        for name in archive.namelist()
                        if name.endswith(".xml")
                    )
            elif extension != "json":
                pages.append(content.text)
    return pages


def test_english_pages_and_reports_are_complete(english) -> None:
    client, store, token = english
    pages = [client.get(path).text for path in ("/", "/calc", "/templates")]
    key = _english_project(client, store)
    pages.extend(_visit_project(client, key))
    for item in store.templates():
        pages.append(client.get(f"/templates/{item['key']}").text)
    pages.append(client.get("/templates").text)
    for calc in (
        {
            "mode": "vlsm",
            "text": "192.168.1.0/24",
            "subnet_name": ["Staff", "Guests"],
            "subnet_hosts": ["50", "25"],
        },
        {
            "mode": "vlsm",
            "text": "192.168.1.0/28",
            "subnet_name": ["Staff"],
            "subnet_hosts": ["50"],
        },
        {"mode": "inspect", "text": "192.168.1.10/31"},
        {"mode": "inspect", "text": "2001:db8::1/64"},
        {"mode": "count", "text": "10.0.0.0/24", "count": "4", "limit": "2"},
        {"mode": "prefix", "text": "2001:db8::/48", "new_prefix": "64", "limit": "4"},
    ):
        response = client.post("/calc", data=calc)
        assert response.status_code == 200, response.text
        pages.append(response.text)
    assert not i18n.missing, sorted(i18n.missing)
    for page in pages:
        assert not POLISH.search(page), (
            POLISH.search(page)
            and page[max(0, POLISH.search(page).start() - 120) : POLISH.search(page).start() + 60]
        )


def test_english_messages_for_errors_and_examples(english) -> None:
    client, store, _ = english
    for example in sorted(EXAMPLES.glob("*.json")):
        response = client.post(
            "/projects/import",
            files={"file": ("input.json", example.read_bytes())},
            follow_redirects=False,
        )
        if response.status_code == 303:
            _visit_project(client, _key(response))
    key = _english_project(client, store)
    _save(client, key, store, **{"p.v4_pool": "10.0.0.1/16"})
    _save(client, key, store, action="block-add", blocked_networks="# only a comment")
    client.post(f"/p/{key}/save", data={"revision": "1"}, headers={"HX-Request": "true"})
    for calc in (
        {"mode": "vlsm", "text": "2001:db8::/48", "subnet_name": ["A"], "subnet_hosts": ["5"]},
        {"mode": "count", "text": "10.0.0.0/24", "count": "3"},
        {"mode": "prefix", "text": "10.0.0.0/24"},
        {"mode": "inspect", "text": "not an address"},
        {"mode": "vlsm", "text": "10.0.0.0/24", "subnet_name": [""], "subnet_hosts": ["x"]},
    ):
        assert client.post("/calc", data=calc).status_code == 422
    client.post("/api/calc", json={"text": "10.0.0.0/24", "count": 3})
    client.post("/projects/import", files={"file": ("bad.json", b'{"schema_version": 9}')})
    client.post("/projects/import", files={"file": ("bad.json", b"{,")})
    client.get("/p/missing-project")
    assert not i18n.missing, sorted(i18n.missing)


def test_language_switch_sets_cookie_and_stays_on_site(english) -> None:
    client, _, token = english
    client.cookies.clear()
    response = client.post(
        "/language", data={"csrf": token, "lang": "en", "next": "/calc"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/calc"
    assert "lang=en" in response.headers["set-cookie"]
    page = client.get("/calc").text
    assert '<html lang="en">' in page and "Subnet and VLSM calculator" in page
    unsafe = client.post(
        "/language",
        data={"csrf": token, "lang": "pl", "next": "//example.com"},
        follow_redirects=False,
    )
    assert unsafe.headers["location"] == "/"
    assert "Kalkulator podsieci" in client.get("/calc").text
    browser = TestClient(client.app, base_url="http://localhost")
    assert '<html lang="en">' in browser.get("/", headers={"Accept-Language": "en-GB"}).text


def _run(*arguments: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(arguments))
        except SystemExit as exit_:
            code = int(exit_.code or 0)
    return code, out.getvalue(), err.getvalue()


def test_cli_speaks_english_with_lang_option(tmp_path, monkeypatch) -> None:
    i18n.missing.clear()
    outputs = []
    for command in ((), ("plan",), ("calc",), ("freeze",), ("export",), ("serve",)):
        code, out, _ = _run("--lang", "en", *command, "--help")
        assert code == 0
        outputs.append(out)
    assert "usage:" in outputs[0] and "Commands" in outputs[0]
    for example in sorted(EXAMPLES.glob("*.json")):
        outputs.extend(_run("plan", str(example), "--show-free", "--verbose", "--lang=en")[1:])
        target = tmp_path / f"{example.stem}.md"
        outputs.extend(
            _run("--lang", "en", "export", str(example), "-f", "md", "-o", str(target))[1:]
        )
        outputs.extend(
            _run("--lang", "en", "freeze", str(example), "-o", str(tmp_path / "f.json"))[1:]
        )
    for calc in (
        ("10.0.0.10/24", "--split", "4"),
        ("2001:db8::/48", "--new-prefix", "52"),
        ("10.0.0.0/24", "--split", "3"),
        ("bad",),
        ("10.0.0.1/32",),
    ):
        outputs.extend(_run("--lang", "en", "calc", *calc)[1:])
    outputs.extend(_run("--lang", "en", "export", "missing.json", "-f", "xlsx")[1:])
    outputs.extend(_run("--lang", "en", "plan")[1:])
    monkeypatch.setenv("ADRESPLAN_LANG", "en")
    outputs.extend(_run("calc", "192.168.0.0/16")[1:])
    assert "Network: 192.168.0.0/16" in outputs[-2]
    assert not i18n.missing, sorted(i18n.missing)
    # Example projects carry Polish user data; only application text must be English.
    names: set[str] = set()
    for example in EXAMPLES.glob("*.json"):
        project = json.loads(example.read_text("utf-8"))["project"]
        names.update([project["name"], *(n["name"] for n in project["nodes"])])
        names.update(n.get("notes", "") for n in project["nodes"])
        names.update(b.get("note", "") for b in project.get("blocked_subnets", []))
    for output in outputs:
        for name in sorted(names - {""}, key=len, reverse=True):
            output = output.replace(name, "")
        assert not POLISH.search(output), output[:400]


def test_english_exports_from_the_library(t5_project) -> None:
    i18n.missing.clear()
    with use_language("en"):
        markdown = export_document(t5_project, "md")
        workbook = export_bytes(t5_project, "xlsx")
    assert "# Address plan" in markdown and "## Validation" in markdown
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        assert 'name="Summary"' in archive.read("xl/workbook.xml").decode()
    assert not i18n.missing, sorted(i18n.missing)
