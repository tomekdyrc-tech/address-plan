"""Local FastAPI application; all computations use the shared application/core APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from adresplan import __version__
from adresplan.application.project_json import MAX_JSON_BYTES, ProjectJSONError
from adresplan.i18n import parse_language, preferred_language, set_language, tr
from adresplan.store.sqlite import (
    MissingProject,
    ProjectStore,
    RevisionConflict,
    StoreError,
    TemplateNameError,
    database_path,
)
from adresplan.web.routes import api, calc, exports, history, library, preferences, projects
from adresplan.web.routes.preferences import LANGUAGE_COOKIE
from adresplan.web.state import WEB_ROOT, WebState

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)


def create_app(database: Path | None = None) -> FastAPI:
    app = FastAPI(title="Address Plan", version=__version__, docs_url=None, redoc_url=None)
    web = WebState(ProjectStore(database_path(database)))
    app.state.store = web.store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: Any) -> Response:
        set_language(
            parse_language(request.cookies.get(LANGUAGE_COOKIE))
            or preferred_language(request.headers.get("accept-language"))
        )
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
                return JSONResponse(
                    {"detail": tr("Odrzucono żądanie z innej strony.")}, status_code=403
                )
            length = request.headers.get("content-length", "0")
            if not length.isdecimal() or int(length) > MAX_JSON_BYTES + 1024 * 1024:
                return JSONResponse(
                    {"detail": tr("Plik lub żądanie jest zbyt duże.")}, status_code=413
                )
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

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
        return web.page(request, "error.html", {"message": str(error)}, status)

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
        return web.page(request, "error.html", {"message": str(error)}, 422)

    for group in (projects, library, history, exports, calc, api, preferences):
        app.include_router(group.router(web))
    return app
