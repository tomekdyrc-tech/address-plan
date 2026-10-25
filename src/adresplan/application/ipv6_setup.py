"""Explicit IPv6 hierarchy adjustment, refusing to relocate pinned networks."""

from dataclasses import replace

from adresplan.application.project_json import InputIssue, ProjectJSONError
from adresplan.core.models import Project
from adresplan.core.plan6 import build_plan_v6
from adresplan.i18n import tr


def fit_ipv6_hierarchy(project: Project) -> Project:
    if not project.uses_ipv6:
        raise ProjectJSONError(
            (InputIssue((), "ipv6_inactive", tr("Najpierw włącz planowanie IPv6.")),)
        )
    if project.pinned_v6_infrastructure or any(n.pinned_v6 is not None for n in project.nodes):
        raise ProjectJSONError(
            (
                InputIssue(
                    (),
                    "ipv6_pinned",
                    tr(
                        "Podział IPv6 zawiera przypięte adresy. Nie zmieniono hierarchii. "
                        "Sprawdź przypięcia przed zmianą reguł."
                    ),
                ),
            )
        )
    assert project.v6_prefix is not None
    # Prefer generous buildings, then smaller buildings and more sites.
    for site, building, infrastructure in ((52, 56, 56), (52, 60, 60), (56, 60, 60), (48, 52, 52)):
        if project.v6_prefix.prefixlen > site:
            continue
        candidate = replace(
            project,
            settings=replace(
                project.settings,
                v6_site_prefix=site,
                v6_building_prefix=building,
                v6_infra_prefix=infrastructure,
            ),
        )
        if build_plan_v6(candidate).is_complete:
            return candidate
    raise ProjectJSONError(
        (
            InputIssue(
                (),
                "ipv6_capacity",
                tr(
                    "Nie znaleziono podziału pasującego do puli, struktury i blokad. "
                    "Sprawdź pulę oraz ustawienia planowania IPv6."
                ),
            ),
        )
    )
