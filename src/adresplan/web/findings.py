"""Readable diagnostics for people; internal codes stay in optional details."""

from dataclasses import dataclass

from adresplan.application.console import FINDING_MESSAGES, format_finding
from adresplan.core.models import Finding, Project, Segment
from adresplan.web.forms import (
    DOCUMENT_FIELDS,
    NODE_FIELDS,
    PROJECT_FIELDS,
    SEGMENT_FIELDS,
    SETTINGS_FIELDS,
    anchor,
)


@dataclass(frozen=True)
class WebFinding:
    level: str
    summary: str
    technical: str
    target: str
    field: str


def present_finding(finding: Finding, project: Project) -> WebFinding:
    nodes = {node.id: node for node in project.nodes}
    node = nodes.get(finding.node_id or "")
    path = []
    current = node
    seen = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        path.append(current.name)
        current = nodes.get(current.parent_id or "")
    location = " → ".join(reversed(path)) or project.name
    code = finding.code
    message = FINDING_MESSAGES.get(code)
    if message is None and code.startswith("v6_"):
        base = FINDING_MESSAGES.get(code[3:])
        message = "IPv6: " + base if base else None
    message = message or "Sprawdź reguły planowania tego elementu."
    if code in ("insufficient_space", "missing_segment_allocation"):
        message = "Brak miejsca na podsieć IPv4"
        if isinstance(node, Segment):
            message += f" dla {node.hosts} urządzeń (przed zapasem i bramą)"
        message += ". Zwiększ pulę rodzica albo zmniejsz zapotrzebowanie."
    if code in ("v6_insufficient_space", "v6_missing_segment_allocation"):
        message = (
            "Brak miejsca na podsieć IPv6. Sprawdź rozmiar puli i podział "
            "między lokalizacje oraz budynki."
        )
    if code == "high_segment_utilization":
        message = "Sieć ma mało zapasu — zapotrzebowanie przekracza 85% pojemności podsieci."
    field = "p.v4_pool"
    if code.startswith("v6_") or "v6" in code:
        field = "p.v6_prefix"
    if "settings" in code:
        field = "s.v6_site_prefix" if "v6" in code else "s.growth_pct"
    if node is not None:
        index = next(i for i, n in enumerate(project.nodes) if n.id == node.id)
        key = "hosts" if isinstance(node, Segment) else "name"
        if "pin" in code:
            key = "pinned_v6" if "v6" in code else "pinned_v4"
        elif "vlan" in code:
            key = "vlan_id"
        field = f"n{index}.{key}"
    return WebFinding(
        finding.level.value,
        f"{location}: {message}",
        format_finding(finding, project),
        anchor(node.id) if node else "project-settings",
        field,
    )


def input_label(path: tuple[str | int, ...], project: Project) -> str:
    labels = {
        f.key: f.label
        for f in (
            *PROJECT_FIELDS,
            *DOCUMENT_FIELDS,
            *SETTINGS_FIELDS,
            *NODE_FIELDS,
            *SEGMENT_FIELDS,
        )
    }
    label = labels.get(str(path[-1]), "Dane projektu") if path else "Dane projektu"
    if len(path) > 2 and path[:2] == ("project", "nodes") and isinstance(path[2], int):
        name = project.nodes[path[2]].name if path[2] < len(project.nodes) else "Nowy element"
        return f"{name} → {label}"
    return label
