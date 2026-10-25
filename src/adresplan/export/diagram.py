"""Standalone SVG address hierarchy with escaped text and no external resources."""

import html
import re
from collections import defaultdict
from dataclasses import dataclass

from adresplan.core.models import FindingLevel, NodeKind, Project, node_sort_key
from adresplan.export.common import create_report, ipv6_description
from adresplan.i18n import tr


@dataclass(frozen=True)
class _Card:
    key: str
    parent: str | None
    name: str
    detail: str
    v4: str
    v6: str
    color: str = "#246675"


def _escape(value: str) -> str:
    return html.escape(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]", "�", value), quote=True)


def dumps_svg(project: Project) -> str:
    report = create_report(project)
    plan = report.plan
    v4 = {a.node_id: str(a.network) for a in plan.v4_allocations}
    v6 = {a.node_id: str(a.network) for a in plan.v6_allocations}
    errors = {f.node_id for f in plan.findings if f.level is FindingLevel.ERROR}
    cards = [
        _Card(
            "root",
            None,
            project.name,
            report.status,
            str(project.v4_pool),
            ipv6_description(project),
            "#173b49",
        )
    ]
    kinds = {
        NodeKind.SITE: tr("Lokalizacja"),
        NodeKind.BUILDING: tr("Budynek"),
        NodeKind.SEGMENT: tr("Segment"),
    }
    for node in sorted(project.nodes, key=node_sort_key):
        cards.append(
            _Card(
                "n:" + node.id,
                "n:" + node.parent_id if node.parent_id else "root",
                node.name,
                kinds[node.kind] + (" · " + tr("BŁĄD") if node.id in errors else ""),
                v4.get(node.id, "—"),
                v6.get(node.id, "—"),
                "#b42338" if node.id in errors else "#246675",
            )
        )
    for i, block in enumerate(project.active_blocked_subnets):
        cards.append(
            _Card(
                f"block:{i}",
                "n:" + block.parent_id if block.parent_id else "root",
                block.note or tr("Zajęta podsieć"),
                tr("Blokada zewnętrzna"),
                str(block.network) if block.network.version == 4 else "—",
                str(block.network) if block.network.version == 6 else "—",
                "#985c19",
            )
        )
    for pool in plan.v6_infrastructure:
        cards.append(
            _Card(
                "infra:" + pool.site_id,
                "n:" + pool.site_id,
                tr("Infrastruktura IPv6"),
                tr("Rezerwa · P2P · loopback"),
                "—",
                str(pool.network),
            )
        )
    children: dict[str | None, list[_Card]] = defaultdict(list)
    for card in cards:
        children[card.parent].append(card)
    positions: dict[str, tuple[int, float]] = {}
    row = 0

    def place(card: _Card, depth: int) -> float:
        nonlocal row
        descendants = children[card.key]
        if descendants:
            ys = [place(child, depth + 1) for child in descendants]
            y = (ys[0] + ys[-1]) / 2
        else:
            y = 72.0 + row * 132
            row += 1
        positions[card.key] = (24 + depth * 390, y)
        return y

    place(cards[0], 0)
    width = max(x for x, _ in positions.values()) + 374
    height = max(y for _, y in positions.values()) + 140
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{_escape(tr("Plan adresacji: {name}", name=project.name))}</title>',
        '<desc id="desc">'
        + _escape(
            tr(
                "Hierarchia adresacji, nie fizyczna topologia połączeń. "
                "Czerwone karty oznaczają błędy, brązowe — zajęte podsieci. "
                "Brak CIDR oznaczono kreską."
            )
        )
        + "</desc>",
        f'<rect width="{width}" height="{height}" fill="#f3f7f8"/>',
        '<text x="24" y="32" font-family="sans-serif" font-size="20" fill="#173b49">'
        f"Address Plan · {_escape(report.status)}</text>",
    ]
    for card in cards[1:]:
        if card.key not in positions or card.parent not in positions:
            continue
        x, y = positions[card.key]
        px, py = positions[card.parent]
        svg.append(
            f'<path d="M {px + 350} {py + 50} H {x - 20} V {y + 50} H {x}" '
            'fill="none" stroke="#8cabb5" stroke-width="2"/>'
        )
    for card in cards:
        if card.key not in positions:
            continue
        x, y = positions[card.key]
        title = " · ".join((card.name, card.detail, card.v4, card.v6))
        svg.append(f"<g><title>{_escape(title)}</title>")
        svg.append(
            f'<rect x="{x}" y="{y}" width="350" height="104" rx="10" '
            f'fill="white" stroke="{card.color}" stroke-width="2"/>'
        )
        for offset, text, size in (
            (22, card.detail, 12),
            (44, card.name, 16),
            (68, "IPv4: " + card.v4, 13),
            (88, "IPv6: " + card.v6, 13),
        ):
            short = text if offset >= 68 or len(text) <= 38 else text[:35] + "…"
            if offset >= 68 and len(text) > 40:
                size = 10
            svg.append(
                f'<text x="{x + 14}" y="{y + offset}" font-family="sans-serif" '
                f'font-size="{size}" fill="{card.color}">{_escape(short)}</text>'
            )
        svg.append("</g>")
    return "\n".join([*svg, "</svg>"])
