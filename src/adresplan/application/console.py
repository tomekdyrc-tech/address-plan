"""Polish plain-text presentation shared by CLI command handlers."""

from collections.abc import Iterable
from fractions import Fraction

from adresplan.core.calc import (
    CalculationError,
    IPv4Calculation,
    IPv6AddressKind,
    IPv6Calculation,
    SubnetPreview,
)
from adresplan.core.models import (
    AddressRange,
    Finding,
    FindingLevel,
    IPv6PoolKind,
    Node,
    NodeKind,
    Plan,
    Project,
    Segment,
    node_sort_key,
)

CALC_MESSAGES = {
    "invalid_address": (
        "Podaj poprawny adres IPv4/IPv6 z prefiksem albo adres IPv4 i "
        "maskę/wildcard. Bez %interfejsu."
    ),
    "choose_one_split_mode": "Wybierz jeden sposób podziału: --split albo --new-prefix.",
    "invalid_preview_limit": "Limit podglądu musi być liczbą całkowitą od 1 do 256.",
    "invalid_subnet_count": "Liczba podsieci musi być dodatnią liczbą całkowitą.",
    "subnet_count_not_power_of_two": "Liczba równych podsieci musi być potęgą dwójki.",
    "invalid_subnet_prefix": (
        "Docelowy prefiks nie może być krótszy od wejściowego ani przekraczać"
        " /32 (IPv4) lub /128 (IPv6)."
    ),
}
_KINDS = {NodeKind.SITE: "lokalizacja", NodeKind.BUILDING: "budynek", NodeKind.SEGMENT: "segment"}
_V6_KINDS = {
    IPv6AddressKind.DOCUMENTATION: "dokumentacyjny",
    IPv6AddressKind.ULA: "ULA",
    IPv6AddressKind.GUA: "GUA",
    IPv6AddressKind.LINK_LOCAL: "link-local",
    IPv6AddressKind.MULTICAST: "multicast",
    IPv6AddressKind.LOOPBACK: "loopback",
    IPv6AddressKind.UNSPECIFIED: "nieokreślony (::)",
    IPv6AddressKind.MIXED: "mieszany zakres",
    IPv6AddressKind.OTHER: "inny / poza rozpoznawanymi zakresami",
}
_POOL_KINDS = {
    IPv6PoolKind.PROJECT: "projekt",
    IPv6PoolKind.SITE: "lokalizacja",
    IPv6PoolKind.BUILDING: "budynek",
    IPv6PoolKind.INFRASTRUCTURE: "infrastruktura",
    IPv6PoolKind.P2P: "łącza",
    IPv6PoolKind.LOOPBACK: "loopbacki",
}
_LEVELS = {
    FindingLevel.ERROR: "BŁĄD",
    FindingLevel.WARNING: "OSTRZEŻENIE",
    FindingLevel.INFO: "INFO",
}

FINDING_MESSAGES = {
    "invalid_blocked_subnet": "Nieprawidłowa blokada zajętej podsieci.",
    "blocked_outside_pool": "Zablokowana podsieć wykracza poza pulę rodzica.",
    "v6_blocked_outside_pool": "Zablokowana podsieć IPv6 wykracza poza pulę rodzica.",
    "pinned_blocked": "Przypięta podsieć przecina zablokowany zakres IPv4.",
    "v6_pinned_blocked": "Przypięta podsieć przecina zablokowany zakres IPv6.",
    "duplicate_request_id": "Powtórzony identyfikator zapotrzebowania.",
    "empty_request_id": "Brakuje identyfikatora zapotrzebowania.",
    "invalid_prefix": "Nieprawidłowa długość prefiksu.",
    "pinned_family_mismatch": "Przypięta sieć ma niewłaściwą rodzinę adresów.",
    "pinned_too_small": "Przypięty blok jest za mały dla zapotrzebowania.",
    "pinned_outside_pool": "Przypięta sieć wykracza poza pulę rodzica.",
    "pinned_overlap": "Przypięta sieć koliduje z innym przydziałem.",
    "insufficient_space": "Brak miejsca na wymaganą podsieć.",
    "invalid_segment_requirements": "Nieprawidłowe zapotrzebowanie segmentu.",
    "hierarchy_capacity_exceeded": "Zapotrzebowanie hierarchii przekracza pojemność IPv4.",
    "hierarchy_anchor_overlap": "Bloki wymagane przez przypięte dzieci kolidują ze sobą.",
    "hierarchy_anchor_outside_parent": (
        "Blok wymagany przez przypięte dzieci nie mieści się w rodzicu."
    ),
    "pool_fragmentation": "Wolne miejsce w puli i jego ciągłość.",
    "summary_route": "Blok sumaryczny rodzica.",
    "invalid_reservations": "Nie można wyznaczyć rezerwacji w segmencie.",
    "high_segment_utilization": "Zapotrzebowanie przekracza 85% pojemności segmentu.",
    "invalid_v4_pool": "Nieprawidłowa pula IPv4.",
    "forbidden_v4_pool": "Pula przecina zabroniony zakres IPv4.",
    "cgnat_pool": "Pula przecina zakres CGNAT; nie jest to RFC 1918.",
    "non_rfc1918_pool": "Pula nie mieści się w prywatnych zakresach RFC 1918.",
    "pinned_outside_project": "Przypięta sieć wykracza poza pulę projektu.",
    "invalid_vlan_id": "VLAN musi mieć numer od 1 do 4094.",
    "user_traffic_vlan_1": "Ruch użytkowników korzysta z VLAN 1.",
    "duplicate_vlan_id": "Numer VLAN powtarza się w tej lokalizacji.",
    "plan_project_mismatch": "Wynik należy do innego projektu.",
    "unknown_allocation_node": "Przydział wskazuje nieznany węzeł.",
    "duplicate_allocation_node": "Węzeł ma więcej niż jeden przydział.",
    "allocation_family_mismatch": "Przydział ma niewłaściwą rodzinę adresów.",
    "allocation_parent_missing": "Brakuje przydziału rodzica.",
    "allocation_outside_parent": "Przydział nie mieści się w rodzicu.",
    "pinned_allocation_changed": "Przydział różni się od przypiętej sieci.",
    "invalid_segment_allocation": "Przydział segmentu nie spełnia jego wymagań.",
    "missing_segment_allocation": "Segment nie otrzymał przydziału.",
    "allocation_overlap": "Podsieci kolidują ze sobą.",
    "empty_project_id": "Brakuje identyfikatora projektu.",
    "empty_project_name": "Brakuje nazwy projektu.",
    "empty_node_id": "Brakuje identyfikatora węzła.",
    "empty_node_name": "Brakuje nazwy węzła.",
    "duplicate_node_id": "Identyfikator węzła powtarza się.",
    "negative_sort_order": "Kolejność nie może być ujemna.",
    "segment_data_missing": "Brakuje danych segmentu.",
    "site_has_parent": "Lokalizacja nie może mieć rodzica.",
    "missing_parent": "Nie znaleziono rodzica węzła.",
    "invalid_parent_kind": "Budynek musi należeć do lokalizacji, a segment do budynku.",
    "parent_cycle": "Relacje rodziców tworzą cykl.",
    "v6_pool_missing": "Przypięto IPv6 bez ustawienia puli projektu.",
    "invalid_v6_pool": "Nieprawidłowa pula IPv6.",
    "unsupported_v6_pool": (
        "Planer wymaga puli GUA, lokalnie nadanej ULA fd00::/8 albo dokumentacyjnej."
    ),
    "v6_kind_mismatch": "Rodzaj puli IPv6 nie odpowiada jej adresowi.",
    "invalid_v6_settings": (
        "Niespójne ustawienia IPv6; sprawdź prefiksy poziomów i bramę link-local."
    ),
    "invalid_v6_segment_settings": "Nieprawidłowe ustawienia IPv6 segmentu.",
    "v6_disabled_with_pin": "Segment ma przypięte IPv6, mimo że IPv6 jest wyłączone.",
    "v6_pin_family_mismatch": "Przypięcie IPv6 ma inną rodzinę adresów.",
    "v6_pin_outside_project": "Przypięcie IPv6 wykracza poza pulę projektu.",
    "invalid_v6_pin_prefix": "Przypięcie IPv6 ma prefiks niezgodny z rolą węzła.",
    "duplicate_v6_infrastructure_pin": "Powtórzone przypięcie infrastruktury lokalizacji.",
    "invalid_v6_infrastructure_pin": (
        "Nieprawidłowe przypięcie infrastruktury lub jej trzech pul /64."
    ),
    "unexpected_v6_allocations": "Plan zawiera IPv6, choć projekt nie ma puli IPv6.",
    "v6_site_anchor_span": "Przypięte dzieci nie mieszczą się w skonfigurowanym bloku lokalizacji.",
    "v6_building_anchor_span": (
        "Przypięte LAN-y wymagają większego bloku budynku niż dozwolone /52."
    ),
    "v6_building_capacity": "Zapotrzebowanie na /64 przekracza dozwolony rozmiar budynku.",
    "v6_building_pin_too_small": "Przypięty blok budynku IPv6 jest za mały.",
    "v6_vlan_required_1_999": "Numeracja IPv6 cyframi hex wymaga VLAN-u od 1 do 999.",
    "v6_vlan_offset_outside_building": (
        "Offset VLAN-u odczytany jako hex nie mieści się w budynku IPv6."
    ),
    "v6_vlan_pin_mismatch": "Przypięty LAN IPv6 nie odpowiada numeracji VLAN jako hex.",
    "v6_pin_outside_parent": "Przypięcie IPv6 nie mieści się w rodzicu.",
    "v6_subnet_collision": "Przypięte podsieci IPv6 kolidują ze sobą.",
    "v6_unknown_infrastructure_site": "Infrastruktura wskazuje nieznaną lokalizację.",
    "v6_duplicate_infrastructure": "Lokalizacja ma powtórzoną infrastrukturę IPv6.",
    "v6_infrastructure_family_mismatch": "Pule infrastruktury mają nieprawidłową rodzinę adresów.",
    "v6_invalid_segment_allocation": "Podsieć IPv6 nie odpowiada roli segmentu.",
    "v6_invalid_building_capacity": "Budynek IPv6 nie mieści wymaganego zapasu /64.",
    "v6_invalid_site_allocation": "Przydział IPv6 lokalizacji ma nieprawidłowy rozmiar.",
    "v6_infrastructure_missing": "Brakuje wydzielonej infrastruktury IPv6 lokalizacji.",
    "v6_infrastructure_outside_site": "Infrastruktura IPv6 nie mieści się w lokalizacji.",
    "v6_pinned_infrastructure_changed": "Pule infrastruktury różnią się od zamrożonych.",
    "v6_building_infrastructure_overlap": "Blok budynku nachodzi na infrastrukturę IPv6.",
}
_REASONS = {
    "a LAN segment must need at least one usable address": (
        "LAN/mgmt wymaga co najmniej jednego użytecznego adresu."
    ),
    "gateway=none requires gateway_addrs=0": "Brama none wymaga gateway_addrs=0.",
    "gateway=first/last requires between one and three addresses": (
        "Brama first/last wymaga od 1 do 3 adresów."
    ),
    "infrastructure roles cannot apply host growth": "P2P i loopback nie stosują zapasu hostów.",
    "infrastructure roles cannot have a gateway": "P2P i loopback nie mają bramy.",
    "infrastructure roles cannot reserve gateway or static addresses": (
        "P2P i loopback nie rezerwują bram ani puli statycznej."
    ),
    "usable address requirement exceeds IPv4 capacity": (
        "Zapotrzebowanie przekracza całą przestrzeń IPv4."
    ),
    "network has insufficient usable addresses": "W podsieci brakuje użytecznych adresów.",
    "network is too small for segment requirements": (
        "Podsieć jest za mała dla zapotrzebowania segmentu."
    ),
    "P2P links require a /30 or /31 network": "Łącze P2P wymaga /30 albo /31.",
    "loopbacks require a /32 network": "Loopback IPv4 wymaga /32.",
    "p2p requires 2 endpoints or hosts=0 (unspecified)": (
        "P2P wymaga hosts=2 albo hosts=0 (liczba domyślna)."
    ),
    "loopback requires 1 endpoints or hosts=0 (unspecified)": (
        "Loopback wymaga hosts=1 albo hosts=0 (liczba domyślna)."
    ),
    "building requires more /64 subnets than a /52 can hold": (
        "Zapas i liczba LAN-ów wymagają więcej /64 niż mieści /52."
    ),
}
_DETAIL_LABELS = {
    "range": "zakres",
    "network": "sieć",
    "parent_id": "rodzic",
    "site_id": "lokalizacja",
    "vlan_id": "VLAN",
    "count": "liczba",
    "other_node_id": "drugi węzeł",
    "requested_prefix": "wymagany prefiks",
    "required_prefix": "wymagany prefiks",
    "free_addresses": "wolne adresy",
    "largest_free_prefix": "największy wolny prefiks",
    "required_addresses": "wymagane adresy",
    "required_usable": "wymagane użyteczne",
    "usable_capacity": "pojemność użyteczna",
    "usable_needed": "wymagane użyteczne",
    "capacity_lower_bound_prefix": "dolne oszacowanie prefiksu",
    "suggested_pool_prefix": "sugerowany prefiks puli",
    "pool_kind": "rodzaj puli",
    "actual_kind": "rozpoznany rodzaj",
    "continuity": "ciągłość",
}


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
        return "n/d"
    scaled = (value.numerator * 10000 + value.denominator // 2) // value.denominator
    return f"{scaled // 100}.{scaled % 100:02d}%"


def _range(value: AddressRange | None) -> str:
    return "—" if value is None else f"{value.first}–{value.last}"


def calculation_error(error: CalculationError) -> str:
    message = CALC_MESSAGES.get(error.code, "Nie można obliczyć wyniku.")
    if error.suggested_count is not None:
        message += (
            f" Najbliższa większa liczba to {error.suggested_count}; "
            f"podaj --split {error.suggested_count}."
        )
    return message


def format_calculation(
    result: IPv4Calculation | IPv6Calculation, preview: SubnetPreview | None = None
) -> str:
    lines = [
        f"Adres wejściowy: {result.address}/{result.network.prefixlen}",
        f"Sieć: {result.network}",
    ]
    if isinstance(result, IPv4Calculation):
        broadcast = str(result.broadcast) if result.broadcast is not None else "brak (/31 lub /32)"
        lines.extend(
            [
                f"Prefiks: /{result.network.prefixlen}",
                f"Maska: {result.netmask}",
                f"Wildcard: {result.wildcard}",
                f"Maska binarnie: {result.binary_mask}",
                f"Broadcast: {broadcast}",
                f"Pierwszy użyteczny: {result.first_usable}",
                f"Ostatni użyteczny: {result.last_usable}",
                f"Liczba użytecznych: {result.usable_count}",
                f"RFC 1918: {'tak' if result.rfc1918 else 'nie'}",
            ]
        )
        if result.reverse_zone is None:
            lines.append(
                "Strefa reverse DNS: brak jednej zwykłej strefy dla tego prefiksu; "
                "obsługiwane granice /8, /16, /24. Delegacje bezklasowe poza zakresem."
            )
    else:
        lines.extend(
            [
                f"Adres skrócony: {result.address.compressed}",
                f"Adres rozwinięty: {result.address.exploded}",
                f"Sieć skrócona: {result.compressed}",
                f"Sieć rozwinięta: {result.exploded}",
                f"Typ adresu: {_V6_KINDS[result.address_kind]}",
                f"Typ bloku: {_V6_KINDS[result.network_kind]}",
                f"Liczba adresów: {result.network.num_addresses}",
                f"Liczba podsieci /64: {result.subnets64}",
            ]
        )
        if result.reverse_zone is None:
            lines.append(
                "Strefa reverse DNS: prefiks niewyrównany do 4 bitów; "
                "brak pojedynczej strefy ip6.arpa dla tego bloku."
            )
    if result.reverse_zone is not None:
        lines.append(f"Strefa reverse DNS: {result.reverse_zone}")
    lines.append(f"Nazwa PTR adresu wejściowego: {result.reverse_pointer}")
    if preview is not None:
        lines.append(
            f"\nPodział na /{preview.new_prefix}: {preview.total_count} podsieci; "
            f"pokazano {len(preview.subnets)}."
        )
        lines.extend(str(network) for network in preview.subnets)
        if preview.is_truncated:
            lines.append("Podgląd ograniczony; pozostałych podsieci nie rozwinięto.")
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
    lines = [
        f"Projekt: {safe_text(project.name)} [{safe_text(project.id)}]",
        f"Status: {'KOMPLETNY' if plan.is_complete else 'NIEKOMPLETNY — zawiera błędy'}",
        f"Pula IPv4: {project.v4_pool}; IPv6: {project.v6_prefix or 'wyłączone'}",
        "",
        _table(
            ("ID", "Nazwa", "Rodzaj", "Rodzic", "VLAN", "IPv4", "IPv6"),
            (
                (
                    n.id,
                    n.name,
                    _KINDS[n.kind],
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
            "\nRezerwacje IPv4:",
            _table(
                ("ID", "Użyteczne", "Potrzebne", "Bramy", "Statyczne", "DHCP"),
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
            "\nInformacje IPv6:",
            _table(
                ("ID", "Brama", "Tryb RA", "Końce łącza / loopback"),
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
            "\nInfrastruktura IPv6:",
            _table(
                ("Lokalizacja", "Blok", "Rezerwa", "Łącza", "Loopbacki"),
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
            "\nMetryki IPv4 (osobno na każdym poziomie):",
            _table(
                ("Rodzic", "Pula", "Zajęte", "Wolne", "Wykorzystanie", "Ciągłość"),
                (
                    (
                        m.parent_id if m.parent_id is not None else "projekt",
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
            "\nMetryki IPv6 (osobno na każdym poziomie):",
            _table(
                ("Rodzic", "Rodzaj", "Pula", "Zajęte", "Wolne", "Wykorzystanie", "Ciągłość"),
                (
                    (
                        m.parent_id if m.parent_id is not None else "projekt",
                        _POOL_KINDS[m.kind],
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
    lines.append(f"\nWolne bloki: {len(plan.free_blocks)}. Pełna lista: --show-free lub --json.")
    if show_free:
        lines.append(
            _table(
                ("Rodzic", "Rodzaj puli", "Wolny CIDR"),
                (
                    (
                        b.parent_id if b.parent_id is not None else "projekt",
                        _POOL_KINDS[b.pool_kind] if b.pool_kind is not None else "IPv4",
                        str(b.network),
                    )
                    for b in plan.free_blocks
                ),
            )
        )
    errors = sum(f.level is FindingLevel.ERROR for f in plan.findings)
    warnings = sum(f.level is FindingLevel.WARNING for f in plan.findings)
    lines.append(f"Diagnostyka: błędy={errors}, ostrzeżenia={warnings}.")
    return "\n".join(lines)


def format_finding(finding: Finding, project: Project) -> str:
    message = FINDING_MESSAGES.get(finding.code)
    if message is None and finding.code.startswith("v6_"):
        base = FINDING_MESSAGES.get(finding.code[3:])
        message = "IPv6: " + base if base is not None else None
    message = message or "Naruszona reguła planowania; szczegóły identyfikuje kod diagnostyczny."
    node = next((n for n in project.nodes if n.id == finding.node_id), None)
    context = (
        f" [{safe_text(finding.node_id)}: {safe_text(node.name)}]"
        if node
        else f" [{safe_text(finding.node_id)}]"
        if finding.node_id is not None
        else " [projekt]"
    )
    details = []
    for key, value in finding.details:
        if key == "reason":
            if isinstance(value, str) and value in _REASONS:
                details.append(_REASONS[value])
            continue
        label = _DETAIL_LABELS.get(key, key)
        display = "n/d" if value is None else str(value)
        if key.endswith("prefix") and isinstance(value, int):
            display = f"/{value}"
        if key == "pool_kind" and isinstance(value, str):
            display = next((_POOL_KINDS[k] for k in _POOL_KINDS if k.value == value), value)
        details.append(f"{label}: {safe_text(display)}")
    suffix = " " + "; ".join(details) if details else ""
    return f"{_LEVELS[finding.level]} [{finding.code}]{context}: {message}{suffix}"
