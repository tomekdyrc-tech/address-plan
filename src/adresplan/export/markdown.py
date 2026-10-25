"""Deterministic GitHub Markdown report with escaped user-provided text."""

import html
from collections.abc import Iterable
from dataclasses import fields

from adresplan.application.console import format_finding
from adresplan.core.models import FindingLevel, Project
from adresplan.export.common import (
    address_range,
    create_report,
    document_details,
    ipv6_description,
    percentage,
)
from adresplan.i18n import tr, tr_all


def markdown_text(value: object) -> str:
    text = "—" if value is None or value == "" else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(
        f"\\x{ord(c):02x}" if (ord(c) < 32 and c != "\n") or 127 <= ord(c) <= 159 else c
        for c in text
    )
    text = html.escape(text, quote=False).replace("\\", "\\\\")
    for character in ("|", "`", "*", "_", "[", "]", "~"):
        text = text.replace(character, "\\" + character)
    return text.replace("\n", "<br>")


def _table(headers: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> str:
    values = [
        "| " + " | ".join(markdown_text(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    values.extend("| " + " | ".join(markdown_text(c) for c in row) + " |" for row in rows)
    return "\n".join(values)


def dumps_markdown(project: Project) -> str:
    report = create_report(project)
    plan = report.plan
    v4 = {a.node_id: a.network for a in plan.v4_allocations}
    v6 = {a.node_id: a.network for a in plan.v6_allocations}
    errors = sum(f.level is FindingLevel.ERROR for f in plan.findings)
    warnings = sum(f.level is FindingLevel.WARNING for f in plan.findings)
    sections = [
        "# " + tr("Plan adresacji — {name}", name=markdown_text(project.name)),
        "**"
        + tr(
            "Status: {status}. Błędy: {errors}; ostrzeżenia: {warnings}.",
            status=report.status,
            errors=errors,
            warnings=warnings,
        )
        + "**",
        tr(
            "Wynik niekompletny zawiera tylko udane przydziały. Brak CIDR oznacza brak przydziału; "
            "diagnostyka jest na końcu raportu."
        ),
        "## " + tr("Założenia"),
        _table(
            tr_all("Parametr", "Wartość"),
            (
                (tr("Projekt ID"), project.id),
                (tr("Pula IPv4"), project.v4_pool),
                (tr("Prefiks IPv6"), ipv6_description(project)),
                (tr("Rodzaj IPv6"), project.v6_kind.value),
            ),
        ),
        tr(
            "Liczba hostów nie obejmuje osobno rezerwowanych bram ani puli statycznej. "
            "Zapas zaokrąglamy w górę. P2P i loopback mają stałe liczby końców. "
            "W IPv6 brak broadcastu. Adres bramy IPv6 i tryb RA są informacją dokumentacyjną."
        ),
        _table(
            tr_all("Ustawienie projektu", "Wartość"),
            ((f.name, getattr(project.settings, f.name)) for f in fields(project.settings)),
        ),
        "## " + tr("Lokalizacje i budynki"),
        _table(
            tr_all(
                "Rodzaj",
                "ID",
                "Nazwa",
                "Rodzic",
                "IPv4",
                "IPv6",
                "Przypięte IPv4",
                "Przypięte IPv6",
                "Uwagi",
            ),
            (
                (
                    tr("lokalizacja") if n.parent_id is None else tr("budynek"),
                    n.id,
                    n.name,
                    n.parent_id,
                    v4.get(n.id),
                    v6.get(n.id),
                    n.pinned_v4,
                    n.pinned_v6,
                    n.notes,
                )
                for n in (*report.sites, *report.buildings)
            ),
        ),
    ]
    if document_details(project):
        sections.insert(2, _table(tr_all("Dokumentacja", "Wartość"), document_details(project)))
    if project.active_blocked_subnets:
        sections += [
            "## " + tr("Zajęte podsieci — blokady"),
            _table(
                tr_all("Rodzic ID", "CIDR", "Opis"),
                (
                    (b.parent_id or tr("projekt"), b.network, b.note)
                    for b in project.active_blocked_subnets
                ),
            ),
            tr(
                "Zajęte adresy w metrykach obejmują przydziały i blokady; nakładające się blokady "
                "tej samej puli są liczone tylko raz."
            ),
        ]
    if not report.rows:
        sections.append(tr("Projekt nie zawiera segmentów."))
    for building in report.buildings:
        site = next(s for s in report.sites if s.id == building.parent_id)
        rows = tuple(r for r in report.rows if r.building.id == building.id)
        sections += [
            f"## {markdown_text(site.name)} / {markdown_text(building.name)}",
            tr(
                "Budynek ID: {id}. Blok IPv4: {v4}; IPv6: {v6}.",
                id=markdown_text(building.id),
                v4=markdown_text(v4.get(building.id)),
                v6=markdown_text(v6.get(building.id)),
            ),
            "### " + tr("Segmenty i zapotrzebowanie"),
            _table(
                tr_all(
                    "ID",
                    "Segment",
                    "VLAN",
                    "Rola",
                    "Hosty wejściowe",
                    "Zapas %",
                    "Hosty z zapasem",
                    "Statyczne",
                    "IPv6 włączone",
                    "Uwagi",
                ),
                (
                    (
                        r.segment.id,
                        r.segment.name,
                        r.segment.vlan_id,
                        r.segment.role.value,
                        r.segment.hosts,
                        r.growth_pct,
                        r.grown_hosts,
                        r.segment.static_count,
                        tr("tak") if r.segment.v6_enabled else tr("nie"),
                        r.segment.notes,
                    )
                    for r in rows
                ),
            ),
            "### IPv4",
            _table(
                tr_all(
                    "ID",
                    "CIDR",
                    "Maska",
                    "Użyteczne adresy",
                    "Potrzebne / pojemność",
                    "Bramy",
                    "Statyczne",
                    "DHCP",
                    "Broadcast",
                ),
                (
                    (
                        r.segment.id,
                        r.v4,
                        r.v4.netmask if r.v4 else None,
                        f"{r.reservation.first_usable}–{r.reservation.last_usable}"
                        if r.reservation
                        else None,
                        f"{r.reservation.usable_needed} / {r.reservation.usable_capacity}"
                        if r.reservation
                        else None,
                        ", ".join(map(str, r.reservation.gateway_addresses))
                        if r.reservation
                        else None,
                        address_range(r.reservation.static_range) if r.reservation else None,
                        address_range(r.reservation.dhcp_range) if r.reservation else None,
                        r.v4.broadcast_address if r.v4 and r.v4.prefixlen < 31 else None,
                    )
                    for r in rows
                ),
            ),
            "### IPv6",
            _table(
                tr_all("ID", "CIDR", "Brama", "RA", "Końce łącza / loopback", "Reverse DNS"),
                (
                    (
                        r.segment.id,
                        r.v6,
                        r.info6.gateway if r.info6 else None,
                        r.info6.ra_mode.value if r.info6 and r.info6.ra_mode else None,
                        ", ".join(map(str, r.info6.endpoints)) if r.info6 else None,
                        r.info6.reverse_zone if r.info6 else None,
                    )
                    for r in rows
                ),
            ),
        ]
    sections += [
        "## " + tr("Infrastruktura IPv6"),
        _table(
            tr_all("Lokalizacja ID", "Blok", "Rezerwa", "Pula łączy /127", "Pula loopbacków /128"),
            (
                (p.site_id, p.network, p.reserved_pool, p.p2p_pool, p.loopback_pool)
                for p in plan.v6_infrastructure
            ),
        ),
        "## " + tr("Podsumowanie wykorzystania"),
        tr(
            "Każdy poziom jest liczony osobno. Nie sumuj przydziałów rodziców i ich dzieci jako "
            "rozłącznych bloków. Ciągłość = największy wolny blok / całe wolne miejsce; "
            "przy braku wolnego miejsca ma wartość n/d."
        ),
        _table(
            tr_all(
                "Rodzina",
                "Rodzic ID",
                "Rodzaj puli",
                "Sieć",
                "Zajęte adresy",
                "Wolne adresy",
                "Największy wolny blok",
                "Wykorzystanie",
                "Ciągłość",
            ),
            (
                (
                    "IPv4",
                    m.parent_id if m.parent_id is not None else tr("projekt"),
                    tr("hierarchia"),
                    m.network,
                    m.allocated_addresses,
                    m.free_addresses,
                    m.largest_free_block,
                    percentage(m.utilization),
                    percentage(m.continuity),
                )
                for m in plan.v4_metrics
            ),
        ),
        _table(
            tr_all(
                "Rodzina",
                "Rodzic ID",
                "Rodzaj puli",
                "Sieć",
                "Zajęte adresy",
                "Wolne adresy",
                "Największy wolny blok",
                "Wykorzystanie",
                "Ciągłość",
            ),
            (
                (
                    "IPv6",
                    m.parent_id if m.parent_id is not None else tr("projekt"),
                    m.kind.value,
                    m.network,
                    m.allocated_addresses,
                    m.free_addresses,
                    m.largest_free_block,
                    percentage(m.utilization),
                    percentage(m.continuity),
                )
                for m in plan.v6_metrics
            ),
        ),
        "## " + tr("Wolne bloki"),
        _table(
            tr_all("Rodzina", "Rodzic ID", "Rodzaj puli", "Wolny CIDR", "Liczba adresów"),
            (
                (
                    f"IPv{b.network.version}",
                    b.parent_id if b.parent_id is not None else tr("projekt"),
                    b.pool_kind.value if b.pool_kind is not None else tr("hierarchia"),
                    b.network,
                    b.network.num_addresses,
                )
                for b in plan.free_blocks
            ),
        ),
        "## " + tr("Walidacja"),
        _table(
            tr_all("Poziom", "Kod", "Węzeł ID", "Opis"),
            (
                (
                    tr(
                        {
                            FindingLevel.ERROR: "Błąd",
                            FindingLevel.WARNING: "Ostrzeżenie",
                            FindingLevel.INFO: "Informacja",
                        }[f.level]
                    ),
                    f.code,
                    f.node_id,
                    format_finding(f, project),
                )
                for f in plan.findings
            ),
        ),
        tr(
            "Raport obliczono z danych wejściowych projektu. Aby zachować adresy przy rozbudowie, "
            "zapisz zamrożony projekt JSON poleceniem freeze. CSV i Markdown są dokumentacją; "
            "do ponownego importu służy JSON."
        ),
    ]
    return "\n\n".join(sections) + "\n"
