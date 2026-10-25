"""Plain-text presentation shared by CLI command handlers, in the active language."""

from collections.abc import Iterable
from fractions import Fraction

from adresplan.application.messages import (
    CALC_MESSAGES,
    DETAIL_LABELS,
    FINDING_MESSAGES,
    LEVEL_LABELS,
    NODE_KINDS,
    POOL_KINDS,
    REASONS,
    V6_ADDRESS_KINDS,
)
from adresplan.core.calc import (
    CalculationError,
    IPv4Calculation,
    IPv6Calculation,
    SubnetPreview,
)
from adresplan.core.models import (
    AddressRange,
    Finding,
    FindingLevel,
    Node,
    Plan,
    Project,
    Segment,
    node_sort_key,
)
from adresplan.i18n import tr, tr_all


def safe_text(value: object) -> str:
    """Keep user-provided names/notes from injecting terminal control sequences."""
    return "".join(
        {"\n": r"\n", "\r": r"\r", "\t": r"\t"}.get(c, f"\\x{ord(c):02x}")
        if ord(c) < 32 or 127 <= ord(c) <= 159
        else c
        for c in str(value)
    )


def _table(headers: tuple[str, ...], rows: Iterable[tuple[str, ...]]) -> str:
    clean = [tuple(safe_text(cell) for cell in row) for row in [headers, *rows]]
    widths = [max(len(row[i]) for row in clean) for i in range(len(headers))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in clean
    )


def _percent(value: Fraction | None) -> str:
    if value is None:
        return tr("n/d")
    scaled = (value.numerator * 10000 + value.denominator // 2) // value.denominator
    return f"{scaled // 100}.{scaled % 100:02d}%"


def _range(value: AddressRange | None) -> str:
    return "—" if value is None else f"{value.first}–{value.last}"


def finding_message(code: str) -> str:
    """Translated description of a diagnostic code, falling back to the IPv4 variant."""
    message = FINDING_MESSAGES.get(code)
    if message is not None:
        return tr(message)
    if code.startswith("v6_") and code[3:] in FINDING_MESSAGES:
        return "IPv6: " + tr(FINDING_MESSAGES[code[3:]])
    return tr("Naruszona reguła planowania; szczegóły identyfikuje kod diagnostyczny.")


def calculation_error(error: CalculationError) -> str:
    message = tr(CALC_MESSAGES.get(error.code, "Nie można obliczyć wyniku."))
    if error.suggested_count is not None:
        message += " " + tr(
            "Najbliższa większa liczba to {count}; podaj --split {count}.",
            count=error.suggested_count,
        )
    return message


def format_calculation(
    result: IPv4Calculation | IPv6Calculation, preview: SubnetPreview | None = None
) -> str:
    lines = [
        tr("Adres wejściowy: {value}", value=f"{result.address}/{result.network.prefixlen}"),
        tr("Sieć: {value}", value=result.network),
    ]
    if isinstance(result, IPv4Calculation):
        broadcast = (
            str(result.broadcast) if result.broadcast is not None else tr("brak (/31 lub /32)")
        )
        lines.extend(
            [
                tr("Prefiks: /{value}", value=result.network.prefixlen),
                tr("Maska: {value}", value=result.netmask),
                tr("Wildcard: {value}", value=result.wildcard),
                tr("Maska binarnie: {value}", value=result.binary_mask),
                tr("Broadcast: {value}", value=broadcast),
                tr("Pierwszy użyteczny: {value}", value=result.first_usable),
                tr("Ostatni użyteczny: {value}", value=result.last_usable),
                tr("Liczba użytecznych: {value}", value=result.usable_count),
                tr("RFC 1918: {value}", value=tr("tak") if result.rfc1918 else tr("nie")),
            ]
        )
        if result.reverse_zone is None:
            lines.append(
                tr(
                    "Strefa reverse DNS: brak jednej zwykłej strefy dla tego prefiksu; "
                    "obsługiwane granice /8, /16, /24. Delegacje bezklasowe poza zakresem."
                )
            )
    else:
        lines.extend(
            [
                tr("Adres skrócony: {value}", value=result.address.compressed),
                tr("Adres rozwinięty: {value}", value=result.address.exploded),
                tr("Sieć skrócona: {value}", value=result.compressed),
                tr("Sieć rozwinięta: {value}", value=result.exploded),
                tr("Typ adresu: {value}", value=tr(V6_ADDRESS_KINDS[result.address_kind])),
                tr("Typ bloku: {value}", value=tr(V6_ADDRESS_KINDS[result.network_kind])),
                tr("Liczba adresów: {value}", value=result.network.num_addresses),
                tr("Liczba podsieci /64: {value}", value=result.subnets64),
            ]
        )
        if result.reverse_zone is None:
            lines.append(
                tr(
                    "Strefa reverse DNS: prefiks niewyrównany do 4 bitów; "
                    "brak pojedynczej strefy ip6.arpa dla tego bloku."
                )
            )
    if result.reverse_zone is not None:
        lines.append(tr("Strefa reverse DNS: {value}", value=result.reverse_zone))
    lines.append(tr("Nazwa PTR adresu wejściowego: {value}", value=result.reverse_pointer))
    if preview is not None:
        lines.append(
            "\n"
            + tr(
                "Podział na /{prefix}: {total} podsieci; pokazano {shown}.",
                prefix=preview.new_prefix,
                total=preview.total_count,
                shown=len(preview.subnets),
            )
        )
        lines.extend(str(network) for network in preview.subnets)
        if preview.is_truncated:
            lines.append(tr("Podgląd ograniczony; pozostałych podsieci nie rozwinięto."))
    return "\n".join(lines)


def _ordered_nodes(project: Project) -> Iterable[Node]:
    def children(parent: str | None) -> Iterable[Node]:
        for node in sorted((n for n in project.nodes if n.parent_id == parent), key=node_sort_key):
            yield node
            yield from children(node.id)

    return children(None)


def format_plan(project: Project, plan: Plan, *, show_free: bool = False) -> str:
    v4 = {a.node_id: str(a.network) for a in plan.v4_allocations}
    v6 = {a.node_id: str(a.network) for a in plan.v6_allocations}
    root = tr("projekt")
    lines = [
        tr("Projekt: {name} [{id}]", name=safe_text(project.name), id=safe_text(project.id)),
        tr(
            "Status: {status}",
            status=tr("KOMPLETNY") if plan.is_complete else tr("NIEKOMPLETNY — zawiera błędy"),
        ),
        tr(
            "Pula IPv4: {v4}; IPv6: {v6}",
            v4=project.v4_pool,
            v6=project.v6_prefix or tr("wyłączone"),
        ),
        "",
        _table(
            tr_all("ID", "Nazwa", "Rodzaj", "Rodzic", "VLAN", "IPv4", "IPv6"),
            (
                (
                    n.id,
                    n.name,
                    tr(NODE_KINDS[n.kind]),
                    n.parent_id or "—",
                    str(n.vlan_id) if isinstance(n, Segment) and n.vlan_id is not None else "—",
                    v4.get(n.id, "—"),
                    v6.get(n.id, "—"),
                )
                for n in _ordered_nodes(project)
            ),
        ),
    ]
    if plan.v4_reservations:
        lines += [
            "\n" + tr("Rezerwacje IPv4:"),
            _table(
                tr_all("ID", "Użyteczne", "Potrzebne", "Bramy", "Statyczne", "DHCP"),
                (
                    (
                        r.node_id,
                        f"{r.first_usable}–{r.last_usable}",
                        str(r.usable_needed),
                        ", ".join(str(a) for a in r.gateway_addresses) or "—",
                        _range(r.static_range),
                        _range(r.dhcp_range),
                    )
                    for r in plan.v4_reservations
                ),
            ),
        ]
    if plan.v6_segments:
        lines += [
            "\n" + tr("Informacje IPv6:"),
            _table(
                tr_all("ID", "Brama", "Tryb RA", "Końce łącza / loopback"),
                (
                    (
                        r.node_id,
                        str(r.gateway) if r.gateway else "—",
                        r.ra_mode.value if r.ra_mode else "—",
                        ", ".join(str(a) for a in r.endpoints) or "—",
                    )
                    for r in plan.v6_segments
                ),
            ),
        ]
    if plan.v6_infrastructure:
        lines += [
            "\n" + tr("Infrastruktura IPv6:"),
            _table(
                tr_all("Lokalizacja", "Blok", "Rezerwa", "Łącza", "Loopbacki"),
                (
                    (
                        p.site_id,
                        str(p.network),
                        str(p.reserved_pool),
                        str(p.p2p_pool),
                        str(p.loopback_pool),
                    )
                    for p in plan.v6_infrastructure
                ),
            ),
        ]
    if plan.v4_metrics:
        lines += [
            "\n" + tr("Metryki IPv4 (osobno na każdym poziomie):"),
            _table(
                tr_all("Rodzic", "Pula", "Zajęte", "Wolne", "Wykorzystanie", "Ciągłość"),
                (
                    (
                        m.parent_id if m.parent_id is not None else root,
                        str(m.network),
                        str(m.allocated_addresses),
                        str(m.free_addresses),
                        _percent(m.utilization),
                        _percent(m.continuity),
                    )
                    for m in plan.v4_metrics
                ),
            ),
        ]
    if plan.v6_metrics:
        lines += [
            "\n" + tr("Metryki IPv6 (osobno na każdym poziomie):"),
            _table(
                tr_all("Rodzic", "Rodzaj", "Pula", "Zajęte", "Wolne", "Wykorzystanie", "Ciągłość"),
                (
                    (
                        m.parent_id if m.parent_id is not None else root,
                        tr(POOL_KINDS[m.kind]),
                        str(m.network),
                        str(m.allocated_addresses),
                        str(m.free_addresses),
                        _percent(m.utilization),
                        _percent(m.continuity),
                    )
                    for m in plan.v6_metrics
                ),
            ),
        ]
    lines.append(
        "\n"
        + tr(
            "Wolne bloki: {count}. Pełna lista: --show-free lub --json.",
            count=len(plan.free_blocks),
        )
    )
    if show_free:
        lines.append(
            _table(
                tr_all("Rodzic", "Rodzaj puli", "Wolny CIDR"),
                (
                    (
                        b.parent_id if b.parent_id is not None else root,
                        tr(POOL_KINDS[b.pool_kind]) if b.pool_kind is not None else "IPv4",
                        str(b.network),
                    )
                    for b in plan.free_blocks
                ),
            )
        )
    errors = sum(f.level is FindingLevel.ERROR for f in plan.findings)
    warnings = sum(f.level is FindingLevel.WARNING for f in plan.findings)
    lines.append(
        tr("Diagnostyka: błędy={errors}, ostrzeżenia={warnings}.", errors=errors, warnings=warnings)
    )
    return "\n".join(lines)


def format_finding(finding: Finding, project: Project) -> str:
    message = finding_message(finding.code)
    node = next((n for n in project.nodes if n.id == finding.node_id), None)
    context = (
        f" [{safe_text(finding.node_id)}: {safe_text(node.name)}]"
        if node
        else f" [{safe_text(finding.node_id)}]"
        if finding.node_id is not None
        else f" [{tr('projekt')}]"
    )
    details = []
    for key, value in finding.details:
        if key == "reason":
            if isinstance(value, str) and value in REASONS:
                details.append(tr(REASONS[value]))
            continue
        label = tr(DETAIL_LABELS[key]) if key in DETAIL_LABELS else key
        display = tr("n/d") if value is None else str(value)
        if key.endswith("prefix") and isinstance(value, int):
            display = f"/{value}"
        if key == "pool_kind" and isinstance(value, str):
            display = next((tr(POOL_KINDS[k]) for k in POOL_KINDS if k.value == value), value)
        details.append(f"{label}: {safe_text(display)}")
    suffix = " " + "; ".join(details) if details else ""
    return f"{tr(LEVEL_LABELS[finding.level])} [{finding.code}]{context}: {message}{suffix}"
