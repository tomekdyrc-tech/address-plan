"""Project list, creation, import and the live editor with its save endpoint."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.datastructures import FormData, UploadFile

from adresplan.application.impact import allocation_impact
from adresplan.application.ipv6_setup import fit_ipv6_hierarchy
from adresplan.application.project_json import MAX_JSON_BYTES, ProjectJSONError, loads_project
from adresplan.application.templates import (
    apply_site_template,
    apply_template,
    building_template,
    site_template,
    starter_templates,
)
from adresplan.application.ula import generate_ula
from adresplan.core.freeze import freeze
from adresplan.core.models import IPv6Kind, Project
from adresplan.core.plan import build_plan
from adresplan.i18n import tr
from adresplan.store.sqlite import (
    RevisionConflict,
    StoredProject,
    duplicate_project,
    input_document,
    template_name,
)
from adresplan.web.forms import anchor, edited_project, revision
from adresplan.web.state import WebState

# History entry recorded for each editor action; plain edits use the default.
SAVE_REASONS = {
    "freeze": "Zamrożenie adresów",
    "unpin": "Usunięcie przypięć",
    "block-add": "Dodanie blokad",
    "template-apply": "Budynek z szablonu",
    "site-template-apply": "Lokalizacje z szablonu",
    "ipv6-toggle": "Zmiana użycia IPv6",
    "ipv6-fit": "Dopasowanie hierarchii IPv6",
}


def new_project_document(form: FormData) -> tuple[dict[str, Any], str]:
    project_id, site_id, building_id = (uuid4().hex for _ in range(3))
    document: dict[str, Any] = {
        "schema_version": 1,
        "project": {
            "id": project_id,
            "name": str(form.get("name", tr("Nowy projekt"))),
            "v4_pool": str(form.get("v4_pool", "10.0.0.0/16")),
            "nodes": [
                {
                    "id": site_id,
                    "name": str(form.get("site_name", tr("Lokalizacja 1"))),
                    "kind": "site",
                },
                {
                    "id": building_id,
                    "name": str(form.get("building_name", tr("Budynek 1"))),
                    "kind": "building",
                    "parent_id": site_id,
                },
            ],
        },
    }
    return document, site_id


def router(web: WebState) -> APIRouter:
    routes = APIRouter()
    store = web.store

    @routes.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        return web.page(
            request,
            "home.html",
            {
                "projects": store.list(),
                "building_templates": web.template_catalog(),
                "starters": starter_templates(),
            },
        )

    @routes.post("/projects/new")
    async def new_project(request: Request) -> Response:
        form = await web.form_input(request)
        document, site_id = new_project_document(form)
        choice = str(form.get("start_template", ""))
        if choice:
            kind, _, template_key = choice.partition("|")
            recipe = web.selected_template(template_key, kind)
            document["project"]["nodes"] = (
                document["project"]["nodes"][:1] if kind == "building" else []
            )
            project = loads_project(json.dumps(document)).project
            if kind == "site":
                project = apply_site_template(
                    project, recipe, str(form.get("site_name", tr("Lokalizacja 1")))
                )
            else:
                project = apply_template(
                    project, recipe, site_id, str(form.get("building_name", tr("Budynek 1")))
                )
        else:
            project = loads_project(json.dumps(document)).project
        project = edited_project(project, {"ipv6_usage": str(form.get("ipv6_usage", "no"))})
        saved = store.create(project)
        return RedirectResponse(f"/p/{saved.key}", 303)

    @routes.post("/projects/import")
    async def import_project(request: Request) -> Response:
        form = await web.form_input(request)
        upload = form.get("file")
        try:
            if not isinstance(upload, UploadFile):
                raise HTTPException(422, tr("Wybierz plik JSON."))
            raw = await upload.read(MAX_JSON_BYTES + 1)
        finally:
            await form.close()
        saved = store.create(loads_project(raw).project)
        return RedirectResponse(f"/p/{saved.key}", 303)

    @routes.post("/p/{key}/duplicate")
    async def duplicate(key: str, request: Request) -> Response:
        await web.form_input(request)
        saved = store.create(duplicate_project(store.get(key).project))
        return RedirectResponse(f"/p/{saved.key}", 303)

    @routes.get("/p/{key}", response_class=HTMLResponse)
    async def editor(key: str, request: Request) -> Response:
        return web.page(request, "editor.html", web.editor_context(store.get(key)))

    def save_error(request: Request, key: str, saved: StoredProject, error: Exception) -> Response:
        details: dict[str, Any] = {"message": str(error), "key": key, "project": saved.project}
        if isinstance(error, ProjectJSONError):
            details["message"] = tr("Popraw wskazane pola. Ostatni zapis pozostał bez zmian.")
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
        return web.page(
            request,
            "save-error.html",
            details,
            409 if isinstance(error, RevisionConflict) else 422,
        )

    def apply_templates(project: Project, form: FormData, action: str) -> Project:
        if action == "template-apply":
            recipe = web.selected_template(str(form.get("template_key", "")), "building")
            project = apply_template(
                project,
                recipe,
                str(form.get("template_site", "")),
                str(form.get("template_building_name", "")) or recipe["building"]["name"],
            )
        if action == "site-template-apply":
            recipe = web.selected_template(str(form.get("site_template_key", "")), "site")
            project = apply_site_template(project, recipe, str(form.get("template_site_names", "")))
        return project

    @routes.post("/p/{key}/save", response_class=HTMLResponse)
    async def save(key: str, request: Request) -> Response:
        form = await web.form_input(request)
        saved = store.get(key)
        template_saved = None
        had_ipv6 = saved.project.uses_ipv6
        reviewing = form.get("planning_mode") == "review"
        baseline = saved.project
        try:
            expected = revision(form)
            if saved.revision != expected:
                raise RevisionConflict(
                    tr("Projekt zmienił się w innej karcie. Wczytaj aktualną wersję.")
                )
            base = baseline
            if form.get("draft_document"):
                if not reviewing:
                    raise HTTPException(
                        422,
                        tr(
                            "Zatwierdź albo odrzuć podgląd przed powrotem do automatycznego zapisu."
                        ),
                    )
                base = loads_project(str(form["draft_document"])).project
                if base.id != baseline.id:
                    raise HTTPException(422, tr("Podgląd należy do innego projektu."))
            project = edited_project(base, form)
            action = str(form.get("action", "save"))
            if action == "ula" and form.get("ipv6_usage") != "no":
                project = replace(project, v6_prefix=generate_ula(), v6_kind=IPv6Kind.ULA)
            if action == "ipv6-fit":
                project = fit_ipv6_hierarchy(project)
            if action == "freeze":
                plan = build_plan(project)
                if not plan.is_complete:
                    return web.page(
                        request,
                        "results.html",
                        {
                            **web.editor_context(replace(saved, project=project)),
                            "message": tr(
                                "Nie można zamrozić niekompletnego planu. Popraw błędy i zapisz."
                            ),
                        },
                        422,
                    )
                project = freeze(project, plan)
            if action.startswith(("template-save:", "site-template-save:")):
                if reviewing:
                    raise HTTPException(
                        422, tr("Najpierw zatwierdź podgląd projektu, potem zapisz wzorzec.")
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
                project = apply_templates(project, form, action)
                reason = SAVE_REASONS.get(action, "Edycja projektu")
                saved = (
                    replace(saved, project=project)
                    if reviewing
                    else store.save(key, project, expected, reason)
                )
        except (ProjectJSONError, RevisionConflict) as error:
            return save_error(request, key, saved, error)
        if request.headers.get("HX-Request") != "true" and not reviewing:
            return RedirectResponse(f"/p/{key}", 303)
        structural = action not in ("save", "") or had_ipv6 != saved.project.uses_ipv6
        response = web.page(
            request,
            "workspace.html" if structural else "results.html",
            {
                **web.editor_context(saved),
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

    @routes.post("/p/{key}/apply-preview")
    async def apply_preview(request: Request, key: str) -> Response:
        form = await web.form_input(request)
        project = loads_project(str(form.get("draft_document", ""))).project
        store.save(key, project, revision(form), "Zatwierdzenie podglądu zmian")
        return RedirectResponse(f"/p/{key}", 303)

    return routes
