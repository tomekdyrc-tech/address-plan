"""Template library and full database backup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from adresplan.application.templates import building_template, site_template
from adresplan.i18n import tr
from adresplan.store.sqlite import RevisionConflict
from adresplan.web.forms import revision
from adresplan.web.state import WebState


def router(web: WebState) -> APIRouter:
    routes = APIRouter()
    store = web.store

    @routes.get("/library/backup.sqlite3")
    async def library_backup() -> Response:
        return Response(
            store.backup(),
            media_type="application/vnd.sqlite3",
            headers={"Content-Disposition": 'attachment; filename="address-plan-backup.sqlite3"'},
        )

    @routes.get("/templates", response_class=HTMLResponse)
    async def template_library(request: Request) -> Response:
        return web.page(
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

    @routes.get("/templates/{key}", response_class=HTMLResponse)
    async def template_detail(request: Request, key: str) -> Response:
        return web.page(
            request,
            "template-detail.html",
            {
                "item": store.template_details(key),
                "projects": [store.get(p.key) for p in store.list()],
            },
        )

    @routes.post("/templates/{key}")
    async def template_update(request: Request, key: str) -> Response:
        form = await web.form_input(request)
        expected = revision(form)
        action = str(form.get("action", "rename"))
        if action in ("archive", "restore"):
            store.update_template(key, expected, archived=action == "archive")
        elif action == "replace":
            source = store.get(str(form.get("source_project", "")))
            try:
                source_revision = int(str(form.get("source_revision", "0")))
            except ValueError as error:
                raise HTTPException(422, tr("Nieprawidłowa wersja projektu źródłowego.")) from error
            if source.revision != source_revision:
                raise RevisionConflict(
                    tr("Projekt źródłowy zmienił się. Odśwież podgląd szablonu.")
                )
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
            raise HTTPException(422, tr("Nieznana operacja szablonu."))
        return RedirectResponse(f"/templates/{key}", 303)

    return routes
