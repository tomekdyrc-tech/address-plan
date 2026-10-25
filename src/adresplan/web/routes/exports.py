"""Export previews, downloads and the print view."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from adresplan.application.exporting import (
    ExportFormat,
    ReportProfile,
    export_bytes,
    export_document,
)
from adresplan.core.plan import build_plan
from adresplan.web.state import WebState

MEDIA_TYPES = {
    "csv": "text/csv",
    "md": "text/markdown",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "cisco": "text/plain",
    "mikrotik": "text/plain",
}
FORMAT_LABELS = {
    "md": "MD",
    "csv": "CSV",
    "json": "JSON",
    "xlsx": "XLSX",
    "docx": "DOCX",
    "cisco": "Cisco IOS",
    "mikrotik": "MikroTik",
}
# Device configurations are plain text; give them a name an editor opens directly.
FILE_NAMES = {"cisco": "{key}-cisco-ios.txt", "mikrotik": "{key}-mikrotik.rsc"}


def router(web: WebState) -> APIRouter:
    routes = APIRouter()
    store = web.store

    @routes.get("/p/{key}/print", response_class=HTMLResponse)
    async def print_preview(
        key: str, request: Request, profile: ReportProfile = "full"
    ) -> Response:
        from adresplan.export.brief import brief_data

        saved = store.get(key)
        return web.page(
            request,
            "print.html",
            {
                **web.editor_context(saved),
                "profile": profile,
                "brief": brief_data(saved.project) if profile == "brief" else None,
            },
        )

    @routes.get("/p/{key}/export", response_class=HTMLResponse)
    async def export_preview(
        key: str, request: Request, format: ExportFormat = "md", profile: ReportProfile = "full"
    ) -> Response:
        saved = store.get(key)
        return web.page(
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
                "format_labels": FORMAT_LABELS,
            },
        )

    @routes.get("/api/projects/{key}/export.{format}")
    async def api_export(
        key: str, format: ExportFormat, profile: ReportProfile = "full"
    ) -> Response:
        saved = store.get(key)
        content = export_bytes(saved.project, format, profile)
        filename = FILE_NAMES.get(format, "{key}.{format}").format(key=key, format=format)
        return Response(
            content,
            media_type=MEDIA_TYPES[format],
            headers={
                "Content-Disposition": f'attachment; filename="address-plan-{filename}"',
                "X-Plan-Complete": str(build_plan(saved.project).is_complete).lower(),
            },
        )

    return routes
