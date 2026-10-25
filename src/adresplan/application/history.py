"""Compare persisted inputs and historical results without recalculating old plans."""

import re
from dataclasses import dataclass
from typing import Any

from adresplan.i18n import tr

_LABELS = {
    "nodes": "Element",
    "name": "Nazwa",
    "author": "Autor dokumentacji",
    "organization": "Organizacja",
    "description": "Opis projektu",
    "document_date": "Data dokumentacji",
    "hosts": "Liczba hostów",
    "vlan_id": "VLAN",
    "parent_id": "Element nadrzędny",
    "kind": "Typ",
    "role": "Rola",
    "id": "Identyfikator",
    "sort_order": "Kolejność",
    "notes": "Uwagi",
    "growth_pct": "Zapas (%)",
    "gateway": "Brama",
    "gateway_addrs": "Liczba adresów bram",
    "static_count": "Adresy statyczne",
    "v4_pool": "Pula IPv4",
    "v6_prefix": "Pula IPv6",
    "v6_kind": "Rodzaj IPv6",
    "v6_active": "Planowanie IPv6 aktywne",
    "v6_enabled": "IPv6 włączone",
    "settings": "Reguły projektu",
    "pinned_v4": "Przypięcie IPv4",
    "pinned_v6": "Przypięcie IPv6",
    "v4_allocations": "Przydziały IPv4",
    "v6_allocations": "Przydziały IPv6",
    "v4_reservations": "Zakresy IPv4",
    "v6_segments": "Parametry IPv6",
    "v6_infrastructure": "Infrastruktura IPv6",
    "free_blocks": "Wolne bloki",
    "blocked_subnets": "Zajęte podsieci",
    "v4_metrics": "Wykorzystanie IPv4",
    "v6_metrics": "Wykorzystanie IPv6",
    "findings": "Komunikaty walidacji",
    "network": "Podsieć",
    "is_complete": "Plan kompletny",
    "usable_needed": "Potrzebne adresy",
    "first_usable": "Pierwszy adres hosta",
    "last_usable": "Ostatni adres hosta",
    "gateway_addresses": "Adresy bram",
    "static_range": "Zakres statyczny",
    "dhcp_range": "Zakres DHCP",
    "first": "Początek",
    "last": "Koniec",
    "ra_mode": "Tryb RA",
    "reverse_zone": "Strefa reverse DNS",
    "endpoints": "Końce łącza",
}


# Reasons are stored in Polish in the database and translated when displayed.
HISTORY_REASONS = frozenset(
    (
        "Utworzenie projektu",
        "Edycja projektu",
        "Początek historii po aktualizacji",
        "Zatwierdzenie podglądu zmian",
        "Zamrożenie adresów",
        "Usunięcie przypięć",
        "Dodanie blokad",
        "Budynek z szablonu",
        "Lokalizacje z szablonu",
        "Zmiana użycia IPv6",
        "Dopasowanie hierarchii IPv6",
    )
)
_RESTORE_REASON = re.compile(r"Przywrócenie wersji (\d+)")


def reason_label(reason: str) -> str:
    restored = _RESTORE_REASON.fullmatch(reason)
    if restored:
        return tr("Przywrócenie wersji {number}", number=restored[1])
    return tr(reason) if reason in HISTORY_REASONS else reason


def field_label(path: str) -> str:
    return " · ".join(tr(_LABELS[part]) if part in _LABELS else part for part in path.split("."))


@dataclass(frozen=True, slots=True)
class Change:
    area: str
    element: str
    field: str
    before: str
    after: str


def _text(value: Any) -> str:
    import json

    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[Change]:
    changes: list[Change] = []
    names = {
        n["id"]: n["name"] for snapshot in (before, after) for n in snapshot["project"]["nodes"]
    }

    def compare(area: str, element: str, left: Any, right: Any, path: str = "") -> None:
        if left == right:
            return
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                compare(area, element, left.get(key), right.get(key), f"{path}.{key}".lstrip("."))
        else:
            changes.append(Change(area, element, path, _text(left), _text(right)))

    for area, key in ((tr("Dane wejściowe"), "project"), (tr("Wynik planowania"), "plan")):
        left, right = before.get(key, {}), after.get(key, {})
        for field in sorted(left.keys() | right.keys()):
            old, new = left.get(field), right.get(field)
            identity = (
                "id"
                if field == "nodes"
                else "site_id"
                if field == "v6_infrastructure"
                else "node_id"
            )
            if (
                field
                in (
                    "nodes",
                    "v4_allocations",
                    "v6_allocations",
                    "v4_reservations",
                    "v6_segments",
                    "v6_infrastructure",
                )
                and isinstance(old, list)
                and isinstance(new, list)
                and all(isinstance(item, dict) and identity in item for item in [*old, *new])
            ):
                old_by_id = {item[identity]: item for item in old}
                new_by_id = {item[identity]: item for item in new}
                for node_id in sorted(old_by_id.keys() | new_by_id.keys()):
                    label = names.get(node_id, node_id)
                    compare(area, label, old_by_id.get(node_id), new_by_id.get(node_id), field)
            else:
                compare(area, tr("Projekt"), old, new, field)
    return changes
