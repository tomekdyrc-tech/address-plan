"""JSON API for scripts: session token, project list, reading and saving plans."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from adresplan.application.project_json import MAX_JSON_BYTES, dumps_project, loads_project
from adresplan.i18n import tr
from adresplan.web.state import WebState


def router(web: WebState) -> APIRouter:
    routes = APIRouter()
    store = web.store

    @routes.get("/api/session")
    async def session() -> dict[str, str]:
        return {"csrf_token": web.token}

    @routes.get("/api/projects")
    async def api_list() -> list[dict[str, Any]]:
        return [asdict(summary) for summary in store.list()]

    @routes.get("/api/projects/{key}/plan")
    async def api_plan(key: str) -> Response:
        saved = store.get(key)
        return Response(
            dumps_project(saved.project),
            media_type="application/json",
            headers={"X-Project-Revision": str(saved.revision)},
        )

    @routes.put("/api/projects/{key}")
    async def api_save(key: str, request: Request) -> Response:
        web.api_token(request)
        raw = await request.body()
        if len(raw) > MAX_JSON_BYTES:
            raise HTTPException(413, tr("Zbyt duży projekt."))
        try:
            expected = int(request.headers.get("If-Match", ""))
        except ValueError as error:
            raise HTTPException(428, tr("Wymagana wersja w nagłówku If-Match.")) from error
        saved = store.save(key, loads_project(raw).project, expected)
        return Response(
            dumps_project(saved.project),
            media_type="application/json",
            headers={"X-Project-Revision": str(saved.revision)},
        )

    return routes
