"""Interface language chosen by the person using the browser."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from adresplan.i18n import parse_language, tr
from adresplan.web.state import WebState

LANGUAGE_COOKIE = "lang"


def router(web: WebState) -> APIRouter:
    routes = APIRouter()

    @routes.post("/language")
    async def choose_language(request: Request) -> Response:
        form = await web.form_input(request)
        choice = parse_language(str(form.get("lang", "")))
        if choice is None:
            raise HTTPException(422, tr("Wybierz język: pl albo en."))
        target = str(form.get("next", "/"))
        # Only same-site paths; never follow an absolute or protocol-relative URL.
        if not target.startswith("/") or target.startswith("//") or "\\" in target:
            target = "/"
        response = RedirectResponse(target, 303)
        response.set_cookie(
            LANGUAGE_COOKIE, choice, max_age=365 * 24 * 3600, samesite="lax", httponly=True
        )
        return response

    return routes
