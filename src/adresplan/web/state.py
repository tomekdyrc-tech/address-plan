"""Shared state and helpers used by every group of routes."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData

from adresplan import __version__
from adresplan.application.history import field_label, reason_label
from adresplan.application.project_json import MAX_JSON_BYTES
from adresplan.application.templates import starter_templates
from adresplan.core.models import Segment
from adresplan.export.common import create_report, ipv6_description
from adresplan.i18n import language, tr
from adresplan.store.sqlite import ProjectStore, StoredProject, input_document
from adresplan.web.explanations import explain_segment
from adresplan.web.findings import input_label, present_finding
from adresplan.web.forms import (
    DOCUMENT_FIELDS,
    NODE_FIELDS,
    PROJECT_FIELDS,
    SEGMENT_FIELDS,
    SETTINGS_FIELDS,
    anchor,
)

WEB_ROOT = Path(__file__).parent


@dataclass
class WebState:
    store: ProjectStore
    token: str = field(default_factory=lambda: secrets.token_hex(32))
    templates: Jinja2Templates = field(
        default_factory=lambda: Jinja2Templates(directory=WEB_ROOT / "templates")
    )

    def __post_init__(self) -> None:
        self.templates.env.globals.update(
            anchor=anchor,
            field_label=field_label,
            input_label=input_label,
            ipv6_description=ipv6_description,
            reason_label=reason_label,
            tr=tr,
        )

    def page(
        self,
        request: Request,
        template: str,
        context: dict[str, Any] | None = None,
        status: int = 200,
    ) -> Response:
        return self.templates.TemplateResponse(
            request,
            template,
            {
                "csrf": self.token,
                "version": __version__,
                "lang": language(),
                "next_path": request.url.path,
                **(context or {}),
            },
            status_code=status,
        )

    async def form_input(self, request: Request) -> FormData:
        # Every segment has many editable fields; 1,000 fields blocks ordinary
        # multi-building projects. Keep a finite limit and the global body cap.
        form = await request.form(max_fields=100_000, max_part_size=MAX_JSON_BYTES)
        supplied = request.headers.get("X-CSRF-Token") or str(form.get("csrf", ""))
        if not secrets.compare_digest(supplied.encode(), self.token.encode()):
            await form.close()
            raise HTTPException(403, tr("Brak tokenu formularza. Odśwież stronę."))
        if request.url.path != "/projects/import":
            await form.close()
        return form

    def api_token(self, request: Request) -> None:
        if not secrets.compare_digest(
            request.headers.get("X-CSRF-Token", "").encode(), self.token.encode()
        ):
            raise HTTPException(403, tr("Brak tokenu sesji."))

    def template_catalog(self) -> list[dict[str, Any]]:
        catalog = []
        for item in self.store.templates():
            recipe = self.store.template(item["key"])
            is_site = "site" in recipe
            buildings = recipe["buildings"] if is_site else [recipe]
            catalog.append(
                {
                    **item,
                    "kind": "site" if is_site else "building",
                    "description": ", ".join(s["name"] for b in buildings for s in b["segments"])
                    or tr("Bez segmentów"),
                }
            )
        return catalog

    def selected_template(self, key: str, kind: str) -> dict[str, Any]:
        if key.startswith("starter:"):
            recipe = starter_templates().get(key.removeprefix("starter:"))
            if recipe is None:
                raise HTTPException(422, tr("Wybierz dostępny szablon."))
        else:
            recipe = self.store.template(key)
        if ("site" in recipe) != (kind == "site"):
            raise HTTPException(422, tr("Wybierz szablon odpowiedniego typu."))
        return recipe

    def editor_context(self, saved: StoredProject) -> dict[str, Any]:
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
            "building_templates": self.template_catalog(),
            "starters": starter_templates(),
            "sites_count": sum(n.kind == "site" for n in project.nodes),
            "v6_site_capacity": (
                2 ** (project.settings.v6_site_prefix - project.v6_prefix.prefixlen)
                if project.v6_prefix
                and project.settings.v6_site_prefix >= project.v6_prefix.prefixlen
                else 0
            ),
        }
