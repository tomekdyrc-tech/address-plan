"""HTTP workflows exercise the same input, calculation and export boundaries as the CLI."""

import json
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from adresplan.application.exporting import export_document
from adresplan.application.project_json import dumps_project, load_project, loads_project
from adresplan.core.models import NodeKind, Segment
from adresplan.core.plan import build_plan
from adresplan.web.app import create_app
from adresplan.web.forms import anchor

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
        self.select = None
        self.in_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.in_form = attrs.get("id") == "project-form"
        if not self.in_form:
            return
        if tag == "input" and "name" in attrs:
            self.values[attrs["name"]] = attrs.get("value", "")
        if tag == "select":
            self.select = attrs["name"]
        if (
            tag == "option"
            and self.select
            and (self.select not in self.values or "selected" in attrs)
        ):
            self.values[self.select] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None
        if tag == "form":
            self.in_form = False


@pytest.fixture
def web(tmp_path):
    app = create_app(tmp_path / "web.sqlite3")
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["X-CSRF-Token"] = client.get("/api/session").json()["csrf_token"]
        yield client, app.state.store


def form(client, key):
    parser = FormParser()
    parser.feed(client.get(f"/p/{key}").text)
    return parser.values


def post(client, key, data):
    return client.post(f"/p/{key}/save", data=data, headers={"HX-Request": "true"})


@pytest.mark.parametrize(
    "example",
    [
        "t1-vlsm",
        "t2-building",
        "t3-no-space",
        "budynek",
        "t5-ipv6",
        "t5-vlan-hex",
        "t5-vlan-110-error",
        "church-av",
    ],
)
def test_import_plan_and_export_match_cli(web, example):
    client, store = web
    raw = (EXAMPLES / f"{example}.json").read_bytes()
    response = client.post(
        "/projects/import", files={"file": ("input.json", raw)}, follow_redirects=False
    )
    assert response.status_code == 303
    key = response.headers["location"].rsplit("/", 1)[1]
    project = store.get(key).project
    page = client.get(f"/p/{key}")
    assert page.status_code == 200
    result = client.get(f"/api/projects/{key}/plan")
    assert result.json() == json.loads(dumps_project(project))
    assert result.headers["X-Project-Revision"] == "1"
    for extension in ("csv", "md", "json"):
        output = client.get(f"/api/projects/{key}/export.{extension}")
        expected = export_document(project, extension)
        assert output.text == ("\ufeff" if extension == "csv" else "") + expected
        assert output.headers["X-Plan-Complete"] == str(build_plan(project).is_complete).lower()
        assert client.get(f"/p/{key}/export?format={extension}").status_code == 200


def test_create_add_edit_freeze_restart_duplicate_delete(web):
    client, store = web
    response = client.post(
        "/projects/new", data={"name": "Sieć AV", "v4_pool": "10.42.0.0/16"}, follow_redirects=False
    )
    key = response.headers["location"].rsplit("/", 1)[1]
    values = form(client, key)
    building = next(n for n in store.get(key).project.nodes if n.kind == NodeKind.BUILDING)
    values.update(action="add", new_kind="segment", new_name="Audio", new_parent=building.id)
    response = post(client, key, values)
    assert response.status_code == 200
    assert response.headers["HX-Retarget"] == "#workspace"
    values = form(client, key)
    values.update(
        {
            "n2.hosts": "42",
            "n2.vlan_id": "10",
            "p.v6_prefix": "2001:db8:42::/48",
            "ipv6_usage": "yes",
        }
    )
    response = post(client, key, values)
    assert response.status_code == 200
    assert response.headers["HX-Retarget"] == "#workspace"
    assert store.get(key).project.nodes[-1].hosts == 42
    values = form(client, key)
    values["action"] = "freeze"
    assert post(client, key, values).status_code == 200
    frozen = store.get(key).project
    assert all(n.pinned_v4 and n.pinned_v6 for n in frozen.nodes)
    assert frozen.pinned_v6_infrastructure
    # A new app instance reads the current input from the same database.
    restarted = create_app(store.path)
    assert restarted.state.store.get(key).project == frozen
    response = client.post(f"/p/{key}/duplicate", follow_redirects=False)
    other_key = response.headers["location"].rsplit("/", 1)[1]
    assert other_key != key
    assert len(client.get("/api/projects").json()) == 2
    values = form(client, key)
    values["action"] = "delete:" + building.id
    assert post(client, key, values).status_code == 200
    assert len(store.get(key).project.nodes) == 1
    assert len(store.get(other_key).project.nodes) == 3


def test_all_fields_roundtrip_and_invalid_field_preserves_database(web):
    client, store = web
    saved = store.create(load_project(EXAMPLES / "church-av.json").project)
    values = form(client, saved.key)
    assert post(client, saved.key, values).status_code == 200
    assert store.get(saved.key).project == saved.project
    index = next(i for i, n in enumerate(saved.project.nodes) if isinstance(n, Segment))
    values["revision"] = str(store.get(saved.key).revision)
    values[f"n{index}.hosts"] = "not-an-integer"
    response = post(client, saved.key, values)
    assert response.status_code == 422
    assert "Zmiany nie zostały zapisane" in response.text
    assert f'href="#{anchor(saved.project.nodes[index].id)}"' in response.text
    assert store.get(saved.key).revision == 1  # unchanged form did not create a revision
    assert store.get(saved.key).project == saved.project


def test_domain_error_saves_partial_and_prevents_freeze(web):
    client, store = web
    saved = store.create(load_project(EXAMPLES / "church-av.json").project)
    values = form(client, saved.key)
    index = next(i for i, n in enumerate(saved.project.nodes) if isinstance(n, Segment))
    values[f"n{index}.hosts"] = "99999999"
    response = post(client, saved.key, values)
    assert response.status_code == 200
    assert "PLAN NIEKOMPLETNY" in response.text
    assert f'href="#{anchor(saved.project.nodes[index].id)}"' in response.text
    values = form(client, saved.key)
    values["action"] = "freeze"
    assert post(client, saved.key, values).status_code == 422
    assert store.get(saved.key).revision == 2


def test_stale_form_and_api_cannot_overwrite(web):
    client, store = web
    saved = store.create(load_project(EXAMPLES / "budynek.json").project)
    values = form(client, saved.key)
    values["p.name"] = "Pierwsza karta"
    assert post(client, saved.key, values).status_code == 200
    values["p.name"] = "Stara karta"
    assert post(client, saved.key, values).status_code == 409
    assert store.get(saved.key).project.name == "Pierwsza karta"
    raw = dumps_project(replace(saved.project, name="API"))
    url = f"/api/projects/{saved.key}"
    assert client.put(url, content=raw).status_code == 428
    assert client.put(url, content=raw, headers={"If-Match": "1"}).status_code == 409
    assert client.put(url, content=raw, headers={"If-Match": "2"}).status_code == 200
    assert store.get(saved.key).project.name == "API"


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"text": "192.168.1.10/24", "count": 4}, 200),
        ({"text": "2001:db8::/0", "new_prefix": 128, "limit": 2}, 200),
        ({"text": "10.0.0.0/24", "count": 3}, 422),
        ({"text": "bad"}, 422),
        ({"text": "10/8", "limit": 999}, 422),
        ({"text": "10.0.0.0/8", "count": True}, 422),
    ],
)
def test_calculator_api(web, payload, expected):
    client, _ = web
    response = client.post("/api/calc", json=payload)
    assert response.status_code == expected
    if expected == 200 and "new_prefix" in payload:
        assert response.json()["preview"]["is_truncated"]
        assert len(response.json()["preview"]["subnets"]) == 2


def test_calculator_form(web):
    client, _ = web
    assert client.get("/calc").status_code == 200
    response = client.post("/calc", data={"text": "192.168.1.10/24", "count": "4"})
    assert response.status_code == 200 and "192.168.1.0/26" in response.text
    assert client.post("/calc", data={"text": "bad"}).status_code == 422


def test_local_security_escaping_and_bad_import(web):
    client, store = web
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert (
        client.post("/projects/new", headers={"Origin": "http://evil.example"}).status_code == 403
    )
    assert client.post("/projects/new", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert (
        client.post("/projects/new", headers={"Origin": "http://localhost:9000"}).status_code == 403
    )
    assert client.post("/projects/import", files={"file": ("x.json", b"{bad}")}).status_code == 422
    assert client.get("/api/projects/missing/plan").status_code == 404
    assert client.get("/p/missing").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/static/htmx.min.js").status_code == 200
    project = load_project(EXAMPLES / "budynek.json").project
    saved = store.create(replace(project, name='<script>alert("x")</script>'))
    response = client.get(f"/p/{saved.key}")
    assert "<script>alert" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    document = client.get(f"/api/projects/{saved.key}/plan").text
    assert loads_project(document).project.name == saved.project.name


def test_ula_unpin_and_bad_hierarchy_are_atomic(web):
    client, store = web
    saved = store.create(load_project(EXAMPLES / "church-av.json").project)
    values = form(client, saved.key)
    values["action"] = "ula"
    assert post(client, saved.key, values).status_code == 200
    project = store.get(saved.key).project
    assert str(project.v6_prefix).startswith("fd") and project.v6_prefix.prefixlen == 48
    assert project.v6_kind == "ula" and build_plan(project).is_complete
    values = form(client, saved.key)
    values["action"] = "freeze"
    assert post(client, saved.key, values).status_code == 200
    values = form(client, saved.key)
    values["action"] = "unpin"
    assert post(client, saved.key, values).status_code == 200
    project = store.get(saved.key).project
    assert not project.pinned_v6_infrastructure
    assert all(n.pinned_v4 is None and n.pinned_v6 is None for n in project.nodes)
    values = form(client, saved.key)
    values["n1.parent_id"] = "missing"
    assert post(client, saved.key, values).status_code == 422
    assert store.get(saved.key).revision == 4
    assert store.get(saved.key).project == project


def test_non_ascii_csrf_is_rejected_without_server_error(web):
    client, _ = web
    client.headers.pop("X-CSRF-Token")
    assert client.post("/projects/new", data={"csrf": "żółć"}).status_code == 403


def test_serve_binds_localhost_and_validates_port(tmp_path, monkeypatch):
    from adresplan.cli import main

    calls = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    assert main(["serve", "--database", str(tmp_path / "app.db"), "--port", "8765"]) == 0
    assert calls == [{"host": "127.0.0.1", "port": 8765, "log_level": "info"}]
    with pytest.raises(SystemExit) as error:
        main(["serve", "--port", "65536"])
    assert error.value.code == 2
