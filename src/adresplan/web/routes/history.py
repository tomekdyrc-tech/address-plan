"""Plan history, comparison, restore and the hierarchy diagram."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from adresplan.application.history import compare_snapshots
from adresplan.export.diagram import dumps_svg
from adresplan.web.forms import revision
from adresplan.web.state import WebState


def router(web: WebState) -> APIRouter:
    routes = APIRouter()
    store = web.store

    @routes.get("/p/{key}/history", response_class=HTMLResponse)
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
        return web.page(
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

    @routes.get("/api/projects/{key}/history")
    async def api_history(key: str, offset: int = 0) -> list[dict[str, Any]]:
        return [asdict(entry) for entry in store.history(key, offset=offset)]

    @routes.get("/p/{key}/diagram", response_class=HTMLResponse)
    async def diagram(request: Request, key: str) -> Response:
        return web.page(request, "diagram.html", {"saved": store.get(key)})

    @routes.get("/api/projects/{key}/diagram.svg")
    async def diagram_svg(key: str, download: bool = False) -> Response:
        headers = (
            {"Content-Disposition": f'attachment; filename="address-plan-{key}.svg"'}
            if download
            else {}
        )
        return Response(
            dumps_svg(store.get(key).project), media_type="image/svg+xml", headers=headers
        )

    @routes.get("/api/projects/{key}/history/{number}")
    async def api_snapshot(key: str, number: int) -> Response:
        return Response(
            json.dumps(store.snapshot(key, number), ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="address-plan-{key}-v{number}.json"'
            },
        )

    @routes.post("/p/{key}/history/{number}/restore")
    async def restore(request: Request, key: str, number: int) -> Response:
        form = await web.form_input(request)
        store.restore(key, number, revision(form))
        return RedirectResponse(f"/p/{key}", 303)

    return routes
