"""Local FastAPI application; all computations use the shared application/core APIs."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, replace
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, StrictInt, TypeAdapter
from starlette.datastructures import FormData, UploadFile
from starlette.middleware.trustedhost import TrustedHostMiddleware

from adresplan import __version__
from adresplan.application.console import calculation_error, format_calculation
from adresplan.application.exporting import (
    ExportFormat,
    ReportProfile,
    export_bytes,
    export_document,
)
from adresplan.application.history import compare_snapshots, field_label
from adresplan.application.impact import allocation_impact
from adresplan.application.ipv6_setup import fit_ipv6_hierarchy
from adresplan.application.project_json import (
    MAX_JSON_BYTES,
    ProjectJSONError,
    dumps_project,
    loads_project,
)
from adresplan.application.templates import (
    apply_site_template,
    apply_template,
    building_template,
    site_template,
    starter_templates,
)
from adresplan.application.ula import generate_ula
from adresplan.core.calc import CalculationError, calculate, preview_subnets
from adresplan.core.freeze import freeze
from adresplan.core.models import IPv6Kind, Segment
from adresplan.core.plan import build_plan
from adresplan.export.common import create_report
from adresplan.export.diagram import dumps_svg
from adresplan.store.sqlite import (
    MissingProject,
    ProjectStore,
    RevisionConflict,
    StoredProject,
    StoreError,
    TemplateNameError,
    database_path,
    duplicate_project,
    input_document,
    template_name,
)
from adresplan.web.calculator import calculator_context, friendly_error, project_from_calculation
from adresplan.web.explanations import explain_segment
from adresplan.web.findings import input_label, present_finding
from adresplan.web.forms import (
    DOCUMENT_FIELDS,
    NODE_FIELDS,
    PROJECT_FIELDS,
    SEGMENT_FIELDS,
    SETTINGS_FIELDS,
    anchor,
    edited_project,
    revision,
)

WEB_ROOT = Path(__file__).parent


class CalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    count: StrictInt | None = None
    new_prefix: StrictInt | None = None
    limit: Annotated[StrictInt, Field(ge=1, le=256)] = 256


def calculation(data: CalculationInput) -> dict[str, Any]:
    result = calculate(data.text)
    preview = None
    if data.count is not None or data.new_prefix is not None:
        preview = preview_subnets(
            result.network, count=data.count, new_prefix=data.new_prefix, limit=data.limit
        )
    return {
        "result": TypeAdapter(type(result)).dump_python(result, mode="json"),
        "preview": None
        if preview is None
        else {
            **TypeAdapter(type(preview)).dump_python(preview, mode="json"),
            "is_truncated": preview.is_truncated,
        },
        "text": format_calculation(result, preview),
    }


def create_app(database: Path | None = None) -> FastAPI:
    app = FastAPI(title="Address Plan", version=__version__, docs_url=None, redoc_url=None)
    store = ProjectStore(database_path(database))
    token = secrets.token_hex(32)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=WEB_ROOT / "templates")
    templates.env.globals.update(anchor=anchor, field_label=field_label, input_label=input_label)

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: Any) -> Response:
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
                return JSONResponse(
                    {"detail": "Odrzucono żądanie z innej strony."}, status_code=403
                )
            length = request.headers.get("content-length", "0")
            if not length.isdecimal() or int(length) > MAX_JSON_BYTES + 1024 * 1024:
                return JSONResponse({"detail": "Plik lub żądanie jest zbyt duże."}, status_code=413)
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def page(
        request: Request, template: str, context: dict[str, Any] | None = None, status: int = 200
    ) -> Response:
        return templates.TemplateResponse(
            request,
            template,
            {"csrf": token, "version": __version__, **(context or {})},
            status_code=status,
        )

    async def form_input(request: Request) -> FormData:
        # Every segment has many editable fields; 1,000 fields blocks ordinary
        # multi-building projects. Keep a finite limit and the global body cap.
        form = await request.form(max_fields=100_000, max_part_size=MAX_JSON_BYTES)
        supplied = request.headers.get("X-CSRF-Token") or str(form.get("csrf", ""))
        if not secrets.compare_digest(supplied.encode(), token.encode()):
            await form.close()
            raise HTTPException(403, "Brak tokenu formularza. Odśwież stronę.")
        if request.url.path != "/projects/import":
            await form.close()
        return form

    def api_token(request: Request) -> None:
        if not secrets.compare_digest(
            request.headers.get("X-CSRF-Token", "").encode(), token.encode()
        ):
            raise HTTPException(403, "Brak tokenu sesji.")

    def template_catalog() -> list[dict[str, Any]]:
        catalog = []
        for item in store.templates():
            recipe = store.template(item["key"])
            is_site = "site" in recipe
            buildings = recipe["buildings"] if is_site else [recipe]
            catalog.append(
                {
                    **item,
                    "kind": "site" if is_site else "building",
                    "description": ", ".join(s["name"] for b in buildings for s in b["segments"])
                    or "Bez segmentów",
                }
            )
        return catalog

    def selected_template(key: str, kind: str) -> dict[str, Any]:
        if key.startswith("starter:"):
            recipe = starter_templates().get(key.removeprefix("starter:"))
            if recipe is None:
                raise HTTPException(422, "Wybierz dostępny szablon.")
        else:
            recipe = store.template(key)
        if ("site" in recipe) != (kind == "site"):
            raise HTTPException(422, "Wybierz szablon odpowiedniego typu.")
        return recipe

    def context(saved: StoredProject) -> dict[str, Any]:
        project = saved.project
        report = create_report(project)
        data = input_document(project)["project"]
        messages = [present_finding(f, project) for f in report.plan.findings]
        return {
            "saved": saved,
            "project": project,
            "plan": report.plan,
            "report": report,
            "data": data,
            "project_fields": PROJECT_FIELDS,
            "document_fields": DOCUMENT_FIELDS,
            "explanations": {
                n.id: explain_segment(project, n) for n in project.nodes if isinstance(n, Segment)
            },
            "settings_fields": SETTINGS_FIELDS,
            "node_fields": NODE_FIELDS,
            "segment_fields": SEGMENT_FIELDS,
            "names": {n.id: n.name for n in project.nodes},
            "parents": {n.id: n.parent_id for n in project.nodes},
            "findings": [
                (f, m.summary) for f, m in zip(report.plan.findings, messages, strict=True)
            ],
            "problems": [m for m in messages if m.level != "info"],
            "information": [m for m in messages if m.level == "info"],
            "v4": {a.node_id: a.network for a in report.plan.v4_allocations},
            "v6": {a.node_id: a.network for a in report.plan.v6_allocations},
            "reservations": {r.node_id: r for r in report.plan.v4_reservations},
            "info6": {i.node_id: i for i in report.plan.v6_segments},
            "building_templates": template_catalog(),
            "starters": starter_templates(),
            "sites_count": sum(n.kind == "site" for n in project.nodes),
            "v6_site_capacity": (
                2 ** (project.settings.v6_site_prefix - project.v6_prefix.prefixlen)
                if project.v6_prefix
                and project.settings.v6_site_prefix >= project.v6_prefix.prefixlen
                else 0
            ),
        }

    @app.exception_handler(StoreError)
    async def store_error(request: Request, error: StoreError) -> Response:
        status = (
            404
            if isinstance(error, MissingProject)
            else 409
            if isinstance(error, RevisionConflict)
            else 422
            if isinstance(error, TemplateNameError)
            else 503
        )
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": str(error)}, status_code=status)
        return page(request, "error.html", {"message": str(error)}, status)

    @app.exception_handler(ProjectJSONError)
    async def input_error(request: Request, error: ProjectJSONError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                {
                    "detail": [
                        {"path": i.location, "code": i.code, "message": i.message}
                        for i in error.issues
                    ]
                },
                422,
            )
        return page(request, "error.html", {"message": str(error)}, 422)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        return page(
            request,
            "home.html",
            {
                "projects": store.list(),
                "building_templates": template_catalog(),
                "starters": starter_templates(),
            },
        )

    @app.get("/library/backup.sqlite3")
    async def library_backup() -> Response:
        return Response(
            store.backup(),
            media_type="application/vnd.sqlite3",
            headers={"Content-Disposition": 'attachment; filename="address-plan-backup.sqlite3"'},
        )

    @app.get("/templates", response_class=HTMLResponse)
    async def template_library(request: Request) -> Response:
        return page(
            request,
            "templates-library.html",
            {
                "items": [store.template_details(t["key"]) for t in store.templates()],
                "archived": [
                    store.template_details(t["key"]) for t in store.templates(archived=True)
                ],
                "projects": store.list(),
            },
        )

    @app.get("/templates/{key}", response_class=HTMLResponse)
    async def template_detail(request: Request, key: str) -> Response:
        return page(
            request,
            "template-detail.html",
            {
                "item": store.template_details(key),
                "projects": [store.get(p.key) for p in store.list()],
            },
        )

    @app.post("/templates/{key}")
    async def template_update(request: Request, key: str) -> Response:
        form = await form_input(request)
        expected = revision(form)
        action = str(form.get("action", "rename"))
        if action in ("archive", "restore"):
            store.update_template(key, expected, archived=action == "archive")
        elif action == "replace":
            source = store.get(str(form.get("source_project", "")))
            try:
                source_revision = int(str(form.get("source_revision", "0")))
            except ValueError as error:
                raise HTTPException(422, "Nieprawidłowa wersja projektu źródłowego.") from error
            if source.revision != source_revision:
                raise RevisionConflict("Projekt źródłowy zmienił się. Odśwież podgląd szablonu.")
            original = store.template_details(key)["document"]
            node_id = str(form.get("source_node", ""))
            recipe = (
                site_template(source.project, node_id)
                if "site" in original
                else building_template(source.project, node_id)
            )
            store.update_template(key, expected, document=recipe)
        elif action == "rename":
            store.update_template(key, expected, name=str(form.get("name", "")))
        else:
            raise HTTPException(422, "Nieznana operacja szablonu.")
        return RedirectResponse(f"/templates/{key}", 303)

    @app.post("/projects/new")
    async def new_project(request: Request) -> Response:
        form = await form_input(request)
        project_id, site_id, building_id = (uuid4().hex for _ in range(3))
        document: dict[str, Any] = {
            "schema_version": 1,
            "project": {
                "id": project_id,
                "name": str(form.get("name", "Nowy projekt")),
                "v4_pool": str(form.get("v4_pool", "10.0.0.0/16")),
                "nodes": [
                    {
                        "id": site_id,
                        "name": str(form.get("site_name", "Lokalizacja 1")),
                        "kind": "site",
                    },
                    {
                        "id": building_id,
                        "name": str(form.get("building_name", "Budynek 1")),
                        "kind": "building",
                        "parent_id": site_id,
                    },
                ],
            },
        }
        choice = str(form.get("start_template", ""))
        if choice:
            kind, _, template_key = choice.partition("|")
            recipe = selected_template(template_key, kind)
            document["project"]["nodes"] = (
                document["project"]["nodes"][:1] if kind == "building" else []
            )
            project = loads_project(json.dumps(document)).project
            if kind == "site":
                project = apply_site_template(
                    project, recipe, str(form.get("site_name", "Lokalizacja 1"))
                )
            else:
                project = apply_template(
                    project, recipe, site_id, str(form.get("building_name", "Budynek 1"))
                )
        else:
            project = loads_project(json.dumps(document)).project
        project = edited_project(project, {"ipv6_usage": str(form.get("ipv6_usage", "no"))})
        saved = store.create(project)
        return RedirectResponse(f"/p/{saved.key}", 303)

    @app.post("/projects/import")
    async def import_project(request: Request) -> Response:
        form = await form_input(request)
        upload = form.get("file")
        try:
            if not isinstance(upload, UploadFile):
                raise HTTPException(422, "Wybierz plik JSON.")
            raw = await upload.read(MAX_JSON_BYTES + 1)
        finally:
            await form.close()
        saved = store.create(loads_project(raw).project)
        return RedirectResponse(f"/p/{saved.key}", 303)

    @app.post("/p/{key}/duplicate")
    async def duplicate(key: str, request: Request) -> Response:
        await form_input(request)
        saved = store.create(duplicate_project(store.get(key).project))
        return RedirectResponse(f"/p/{saved.key}", 303)

    @app.get("/p/{key}", response_class=HTMLResponse)
    async def editor(key: str, request: Request) -> Response:
        return page(request, "editor.html", context(store.get(key)))

    @app.get("/p/{key}/print", response_class=HTMLResponse)
    async def print_preview(
        key: str, request: Request, profile: ReportProfile = "full"
    ) -> Response:
        from adresplan.export.brief import brief_data

        saved = store.get(key)
        return page(
            request,
            "print.html",
            {
                **context(saved),
                "profile": profile,
                "brief": brief_data(saved.project) if profile == "brief" else None,
            },
        )

    @app.post("/p/{key}/save", response_class=HTMLResponse)
    async def save(key: str, request: Request) -> Response:
        form = await form_input(request)
        saved = store.get(key)
        template_saved = None
        had_ipv6 = saved.project.uses_ipv6
        reviewing = form.get("planning_mode") == "review"
        baseline = saved.project
        try:
            expected = revision(form)
            if saved.revision != expected:
                raise RevisionConflict(
                    "Projekt zmienił się w innej karcie. Wczytaj aktualną wersję."
                )
            base = baseline
            if form.get("draft_document"):
                if not reviewing:
                    raise HTTPException(
                        422,
                        "Zatwierdź albo odrzuć podgląd przed powrotem do automatycznego zapisu.",
                    )
                base = loads_project(str(form["draft_document"])).project
                if base.id != baseline.id:
                    raise HTTPException(422, "Podgląd należy do innego projektu.")
            project = edited_project(base, form)
            action = str(form.get("action", "save"))
            if action == "ula" and form.get("ipv6_usage") != "no":
                project = replace(project, v6_prefix=generate_ula(), v6_kind=IPv6Kind.ULA)
            if action == "ipv6-fit":
                project = fit_ipv6_hierarchy(project)
            if action == "freeze":
                plan = build_plan(project)
                if not plan.is_complete:
                    return page(
                        request,
                        "results.html",
                        {
                            **context(replace(saved, project=project)),
                            "message": (
                                "Nie można zamrozić niekompletnego planu. Popraw błędy i zapisz."
                            ),
                        },
                        422,
                    )
                project = freeze(project, plan)
            if action.startswith(("template-save:", "site-template-save:")):
                if reviewing:
                    raise HTTPException(
                        422, "Najpierw zatwierdź podgląd projektu, potem zapisz wzorzec."
                    )
                node_id = action.split(":", 1)[1]
                is_site = action.startswith("site-template-save:")
                recipe = (
                    site_template(project, node_id)
                    if is_site
                    else building_template(project, node_id)
                )
                template_saved = template_name(
                    str(form.get("template_name", "")).strip()
                    or recipe["site" if is_site else "building"]["name"]
                )
                # Validate before saving edits; stale pages cannot create templates.
                saved = store.save(key, project, expected)
                store.save_template(template_saved, recipe)
            else:
                if action == "template-apply":
                    recipe = selected_template(str(form.get("template_key", "")), "building")
                    project = apply_template(
                        project,
                        recipe,
                        str(form.get("template_site", "")),
                        str(form.get("template_building_name", "")) or recipe["building"]["name"],
                    )
                if action == "site-template-apply":
                    recipe = selected_template(str(form.get("site_template_key", "")), "site")
                    project = apply_site_template(
                        project, recipe, str(form.get("template_site_names", ""))
                    )
                reason = {
                    "freeze": "Zamrożenie adresów",
                    "unpin": "Usunięcie przypięć",
                    "block-add": "Dodanie blokad",
                    "template-apply": "Budynek z szablonu",
                    "site-template-apply": "Lokalizacje z szablonu",
                    "ipv6-toggle": "Zmiana użycia IPv6",
                    "ipv6-fit": "Dopasowanie hierarchii IPv6",
                }.get(action, "Edycja projektu")
                saved = (
                    replace(saved, project=project)
                    if reviewing
                    else store.save(key, project, expected, reason)
                )
        except (ProjectJSONError, RevisionConflict) as error:
            details: dict[str, Any] = {"message": str(error), "key": key, "project": saved.project}
            if isinstance(error, ProjectJSONError):
                details["message"] = "Popraw wskazane pola. Ostatni zapis pozostał bez zmian."
                details["issues"] = [
                    (
                        anchor(saved.project.nodes[i.path[2]].id)
                        if len(i.path) > 2
                        and i.path[:2] == ("project", "nodes")
                        and isinstance(i.path[2], int)
                        and i.path[2] < len(saved.project.nodes)
                        else "project-settings",
                        i,
                    )
                    for i in error.issues
                ]
            return page(
                request,
                "save-error.html",
                details,
                409 if isinstance(error, RevisionConflict) else 422,
            )
        if request.headers.get("HX-Request") != "true" and not reviewing:
            return RedirectResponse(f"/p/{key}", 303)
        structural = action not in ("save", "") or had_ipv6 != saved.project.uses_ipv6
        response = page(
            request,
            "workspace.html" if structural else "results.html",
            {
                **context(saved),
                "tree_oob": not structural,
                "template_saved": template_saved,
                "reviewing": reviewing,
                "draft_document": json.dumps(input_document(saved.project), ensure_ascii=False)
                if reviewing
                else "",
                "impact": allocation_impact(baseline, saved.project) if reviewing else [],
            },
        )
        response.headers["X-Project-Revision"] = str(saved.revision)
        if reviewing:
            response.headers["X-Plan-Preview"] = "1"
        if structural:
            response.headers["HX-Retarget"] = "#workspace"
            response.headers["HX-Reswap"] = "outerHTML"
        return response

    @app.post("/p/{key}/apply-preview")
    async def apply_preview(request: Request, key: str) -> Response:
        form = await form_input(request)
        project = loads_project(str(form.get("draft_document", ""))).project
        store.save(key, project, revision(form), "Zatwierdzenie podglądu zmian")
        return RedirectResponse(f"/p/{key}", 303)

    @app.get("/p/{key}/history", response_class=HTMLResponse)
    async def history(
        request: Request,
        key: str,
        before: int | None = None,
        after: int | None = None,
        offset: int = 0,
    ) -> Response:
        saved = store.get(key)
        entries = store.history(key, offset=offset)
        newer = saved.revision if after is None else after
        older = (
            before if before is not None else (entries[1].revision if len(entries) > 1 else newer)
        )
        changes = compare_snapshots(store.snapshot(key, older), store.snapshot(key, newer))
        return page(
            request,
            "history.html",
            {
                "saved": saved,
                "entries": entries,
                "changes": changes,
                "before": older,
                "after": newer,
                "offset": max(0, offset),
            },
        )

    @app.get("/api/projects/{key}/history")
    async def api_history(key: str, offset: int = 0) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in store.history(key, offset=offset)]

    @app.get("/p/{key}/diagram", response_class=HTMLResponse)
    async def diagram(request: Request, key: str) -> Response:
        return page(request, "diagram.html", {"saved": store.get(key)})

    @app.get("/api/projects/{key}/diagram.svg")
    async def diagram_svg(key: str, download: bool = False) -> Response:
        headers = (
            {"Content-Disposition": f'attachment; filename="address-plan-{key}.svg"'}
            if download
            else {}
        )
        return Response(
            dumps_svg(store.get(key).project), media_type="image/svg+xml", headers=headers
        )

    @app.get("/api/projects/{key}/history/{number}")
    async def api_snapshot(key: str, number: int) -> Response:
        return Response(
            json.dumps(store.snapshot(key, number), ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="address-plan-{key}-v{number}.json"'
            },
        )

    @app.post("/p/{key}/history/{number}/restore")
    async def restore(request: Request, key: str, number: int) -> Response:
        form = await form_input(request)
        store.restore(key, number, revision(form))
        return RedirectResponse(f"/p/{key}", 303)

    @app.get("/p/{key}/export", response_class=HTMLResponse)
    async def export_preview(
        key: str, request: Request, format: ExportFormat = "md", profile: ReportProfile = "full"
    ) -> Response:
        saved = store.get(key)
        return page(
            request,
            "export.html",
            {
                "saved": saved,
                "format": format,
                "profile": profile,
                "text": export_document(
                    saved.project, "md" if format in ("xlsx", "docx") else format, profile
                ),
                "complete": build_plan(saved.project).is_complete,
            },
        )

    @app.get("/calc", response_class=HTMLResponse)
    async def calculator(request: Request) -> Response:
        return page(request, "calculator.html")

    @app.post("/calc", response_class=HTMLResponse)
    async def calculate_form(request: Request) -> Response:
        form = await form_input(request)
        try:
            result_context = calculator_context(form)
            if form.get("action") == "project":
                project = project_from_calculation(
                    result_context, str(form.get("project_name", "Plan z kalkulatora"))
                )
                saved = store.create(project)
                url = f"/p/{saved.key}"
                return (
                    Response(headers={"HX-Redirect": url})
                    if request.headers.get("HX-Request") == "true"
                    else RedirectResponse(url, 303)
                )
            status = 200
        except ValueError as error:
            result_context = {"error": friendly_error(error)}
            status = 422
        return page(
            request, "calc-result.html", {**result_context, "invalid": status != 200}, status
        )

    @app.get("/api/session")
    async def session() -> dict[str, str]:
        return {"csrf_token": token}

    @app.get("/api/projects")
    async def api_list() -> list[dict[str, Any]]:
        return [asdict(summary) for summary in store.list()]

    @app.get("/api/projects/{key}/plan")
    async def api_plan(key: str) -> Response:
        saved = store.get(key)
        return Response(
            dumps_project(saved.project),
            media_type="application/json",
            headers={"X-Project-Revision": str(saved.revision)},
        )

    @app.put("/api/projects/{key}")
    async def api_save(key: str, request: Request) -> Response:
        api_token(request)
        raw = await request.body()
        if len(raw) > MAX_JSON_BYTES:
            raise HTTPException(413, "Zbyt duży projekt.")
        try:
            expected = int(request.headers.get("If-Match", ""))
        except ValueError as error:
            raise HTTPException(428, "Wymagana wersja w nagłówku If-Match.") from error
        saved = store.save(key, loads_project(raw).project, expected)
        return Response(
            dumps_project(saved.project),
            media_type="application/json",
            headers={"X-Project-Revision": str(saved.revision)},
        )

    @app.post("/api/calc")
    async def api_calculate(request: Request, data: CalculationInput) -> dict[str, Any]:
        api_token(request)
        try:
            return calculation(data)
        except CalculationError as error:
            raise HTTPException(422, calculation_error(error)) from error

    @app.get("/api/projects/{key}/export.{format}")
    async def api_export(
        key: str, format: ExportFormat, profile: ReportProfile = "full"
    ) -> Response:
        saved = store.get(key)
        content = export_bytes(saved.project, format, profile)
        return Response(
            content,
            media_type={
                "csv": "text/csv",
                "md": "text/markdown",
                "json": "application/json",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }[format],
            headers={
                "Content-Disposition": f'attachment; filename="address-plan-{key}.{format}"',
                "X-Plan-Complete": str(build_plan(saved.project).is_complete).lower(),
            },
        )

    return app
