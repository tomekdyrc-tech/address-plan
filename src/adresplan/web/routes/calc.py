"""Subnet calculator page and its JSON API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, TypeAdapter

from adresplan.application.console import calculation_error, format_calculation
from adresplan.core.calc import CalculationError, calculate, preview_subnets
from adresplan.i18n import tr
from adresplan.web.calculator import calculator_context, friendly_error, project_from_calculation
from adresplan.web.state import WebState


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


def router(web: WebState) -> APIRouter:
    routes = APIRouter()

    @routes.get("/calc", response_class=HTMLResponse)
    async def calculator(request: Request) -> Response:
        return web.page(request, "calculator.html")

    @routes.post("/calc", response_class=HTMLResponse)
    async def calculate_form(request: Request) -> Response:
        form = await web.form_input(request)
        try:
            result_context = calculator_context(form)
            if form.get("action") == "project":
                project = project_from_calculation(
                    result_context, str(form.get("project_name", tr("Plan z kalkulatora")))
                )
                saved = web.store.create(project)
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
        return web.page(
            request, "calc-result.html", {**result_context, "invalid": status != 200}, status
        )

    @routes.post("/api/calc")
    async def api_calculate(request: Request, data: CalculationInput) -> dict[str, Any]:
        web.api_token(request)
        try:
            return calculation(data)
        except CalculationError as error:
            raise HTTPException(422, calculation_error(error)) from error

    return routes
