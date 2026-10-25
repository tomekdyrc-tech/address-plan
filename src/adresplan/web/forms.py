"""HTML fields translated into the same versioned input as JSON imports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from adresplan.application.project_json import InputIssue, ProjectJSONError, loads_project
from adresplan.application.templates import apply_template, building_template
from adresplan.application.ula import generate_ula
from adresplan.core.models import Project
from adresplan.i18n import tr
from adresplan.store.sqlite import input_document


# Labels and choice names are Polish ids; templates translate them with tr().
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"
    optional: bool = False
    choices: tuple[tuple[str, str], ...] = ()


GATEWAYS = (("first", "Początek"), ("last", "Koniec"), ("none", "Bez bramy"))
RA = (("slaac", "SLAAC"), ("dhcpv6", "DHCPv6"))
DOCUMENT_FIELDS = (
    Field("author", "Autor dokumentacji"),
    Field("organization", "Organizacja / inwestor"),
    Field("description", "Opis projektu"),
    Field("document_date", "Data dokumentacji (RRRR-MM-DD)"),
)
PROJECT_FIELDS = (
    Field("name", "Nazwa projektu"),
    Field("v4_pool", "Pula IPv4"),
    Field("v6_prefix", "Prefiks IPv6", optional=True),
    Field(
        "v6_kind",
        "Rodzaj IPv6",
        choices=(("doc", "Dokumentacyjny"), ("ula", "ULA"), ("gua", "Globalny")),
    ),
)
SETTINGS_FIELDS = (
    Field("growth_pct", "Zapas IPv4 (%)", "number"),
    Field("gateway", "Pozycja bramy", choices=GATEWAYS),
    Field("gateway_addrs", "Adresy bram (0–3)", "number"),
    Field("p2p_prefix", "Prefiks P2P IPv4", choices=(("31", "/31"), ("30", "/30")), kind="number"),
    Field("v6_site_prefix", "Prefiks lokalizacji IPv6", "number"),
    Field("v6_building_prefix", "Prefiks budynku IPv6", "number"),
    Field("v6_infra_prefix", "Prefiks infrastruktury IPv6", "number"),
    Field("v6_growth_pct", "Zapas IPv6 (%)", "number"),
    Field(
        "v6_subnet_strategy",
        "Strategia IPv6",
        choices=(
            ("sequential", "Kolejne podsieci"),
            ("vlan_decimal_as_hex", "VLAN jako cyfry hex"),
        ),
    ),
    Field(
        "v6_gateway_mode",
        "Brama IPv6",
        choices=(("global", "Globalna"), ("link_local", "Link-local")),
    ),
    Field("v6_link_local_gateway", "Adres bramy link-local"),
    Field("v6_ra_mode", "Domyślne RA", choices=RA),
)
NODE_FIELDS = (
    Field("name", "Nazwa"),
    Field("sort_order", "Kolejność", "number"),
    Field("pinned_v4", "Przypięcie IPv4", optional=True),
    Field("pinned_v6", "Przypięcie IPv6", optional=True),
    Field("notes", "Uwagi"),
)
SEGMENT_FIELDS = (
    Field("hosts", "Hosty", "number"),
    Field("vlan_id", "VLAN", "number", optional=True),
    Field(
        "role",
        "Rola",
        choices=(("lan", "LAN"), ("mgmt", "Zarządzanie"), ("p2p", "P2P"), ("loopback", "Loopback")),
    ),
    Field("static_count", "Adresy statyczne", "number"),
    Field(
        "v6_enabled",
        "IPv6 w tej sieci urządzeń",
        "bool",
        choices=(("true", "Włączone"), ("false", "Wyłączone")),
    ),
    Field("growth_pct", "Zapas IPv4 (%)", "number", optional=True),
    Field("gateway", "Pozycja bramy", optional=True, choices=GATEWAYS),
    Field("gateway_addrs", "Adresy bram", "number", optional=True),
    Field("ra_mode", "RA", optional=True, choices=RA),
)


def anchor(node_id: str) -> str:
    return "node-" + hashlib.sha256(node_id.encode()).hexdigest()[:24]


def _value(form: Mapping[str, Any], key: str, field: Field, old: Any) -> Any:
    if key not in form:
        return old
    value = str(form[key]).strip() if field.key != "notes" else str(form[key])
    if value == "" and field.optional:
        return None
    if field.kind == "number":
        try:
            return int(value)
        except ValueError:
            return value  # Central schema supplies the field-specific error.
    if field.kind == "bool":
        return {"true": True, "false": False}.get(value, value)
    return value


def edited_project(project: Project, form: Mapping[str, Any]) -> Project:
    document = input_document(project)
    data = document["project"]
    ipv6_usage = form.get("ipv6_usage")
    if ipv6_usage not in (None, "yes", "no"):
        raise ProjectJSONError(
            (InputIssue((), "ipv6_usage", tr("Wybierz, czy planujesz używać IPv6.")),)
        )
    for field in (*PROJECT_FIELDS, *DOCUMENT_FIELDS):
        if ipv6_usage == "no" and field.key.startswith("v6_"):
            continue
        data[field.key] = _value(form, "p." + field.key, field, data[field.key])
    for field in SETTINGS_FIELDS:
        if ipv6_usage == "no" and field.key.startswith("v6_"):
            continue
        data["settings"][field.key] = _value(
            form, "s." + field.key, field, data["settings"][field.key]
        )
    for index, node in enumerate(data["nodes"]):
        fields = NODE_FIELDS + (SEGMENT_FIELDS if node["kind"] == "segment" else ())
        for field in fields:
            if ipv6_usage == "no" and field.key in ("pinned_v6", "v6_enabled", "ra_mode"):
                continue
            node[field.key] = _value(form, f"n{index}." + field.key, field, node[field.key])
        if node["kind"] != "site":
            node["parent_id"] = str(form.get(f"n{index}.parent_id", node["parent_id"]))
    if ipv6_usage == "no":
        data["v6_active"] = False
    elif ipv6_usage == "yes":
        data["v6_active"] = True
        if not data["v6_prefix"]:
            data["v6_prefix"] = str(generate_ula())
            data["v6_kind"] = "ula"
            # A /48 project must leave room for more than a single /48 site.
            if all(
                data["settings"][k] == v
                for k, v in (
                    ("v6_site_prefix", 48),
                    ("v6_building_prefix", 56),
                    ("v6_infra_prefix", 56),
                )
            ):
                data["settings"]["v6_site_prefix"] = 52
    action = str(form.get("action", "save"))
    if action == "add":
        kind = str(form.get("new_kind", "segment"))
        node = {
            "id": uuid4().hex,
            "kind": kind,
            "name": str(form.get("new_name", tr("Nowy element"))),
            "parent_id": None if kind == "site" else str(form.get("new_parent", "")),
        }
        if kind == "segment":
            node["hosts"] = _value(form, "new_hosts", SEGMENT_FIELDS[0], 10)
            node["vlan_id"] = _value(form, "new_vlan", SEGMENT_FIELDS[1], None)
        data["nodes"].append(node)
    elif action.startswith("delete:"):
        removed = {action.removeprefix("delete:")}
        for _ in data["nodes"]:
            removed.update(n["id"] for n in data["nodes"] if n["parent_id"] in removed)
        data["nodes"] = [n for n in data["nodes"] if n["id"] not in removed]
        data["pinned_v6_infrastructure"] = [
            p for p in data["pinned_v6_infrastructure"] if p["site_id"] not in removed
        ]
        data["blocked_subnets"] = [
            b for b in data["blocked_subnets"] if b["parent_id"] not in removed
        ]
    elif action.startswith("duplicate:"):
        original = action.removeprefix("duplicate:")
        node = next((n for n in data["nodes"] if n["id"] == original), None)
        if node is not None and node["kind"] == "building":
            current = loads_project(json.dumps(document, ensure_ascii=False)).project
            return apply_template(
                current,
                building_template(current, original),
                node["parent_id"],
                node["name"] + " — " + tr("kopia"),
            )
        if node is None or node["kind"] != "segment":
            raise ProjectJSONError(
                (
                    InputIssue(
                        ("nodes",),
                        "duplicate_segment",
                        tr("Wybierz istniejący segment lub budynek do duplikowania."),
                    ),
                )
            )
        copied = {
            **node,
            "id": uuid4().hex,
            "name": node["name"] + " — " + tr("kopia"),
            "pinned_v4": None,
            "pinned_v6": None,
        }
        data["nodes"].insert(data["nodes"].index(node) + 1, copied)
    elif action == "block-add":
        lines = str(form.get("blocked_networks", "")).splitlines()
        added = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            network, _, note = line.partition(";")
            if ipv6_usage == "no" and ":" in network:
                raise ProjectJSONError(
                    (
                        InputIssue(
                            (),
                            "ipv6_disabled",
                            tr("Włącz IPv6 w sekcji Pule i reguły przed dodaniem blokady IPv6."),
                        ),
                    )
                )
            added.append(
                {
                    "network": network.strip(),
                    "note": note.strip(),
                    "parent_id": str(form.get("blocked_parent", "")) or None,
                }
            )
        if not added:
            raise ProjectJSONError(
                (InputIssue((), "blocked_empty", tr("Wpisz przynajmniej jedną podsieć CIDR.")),)
            )
        data["blocked_subnets"].extend(b for b in added if b not in data["blocked_subnets"])
    elif action.startswith("block-delete:"):
        try:
            index = int(action.removeprefix("block-delete:"))
            if index < 0:
                raise ValueError
            del data["blocked_subnets"][index]
        except (ValueError, IndexError) as error:
            raise ProjectJSONError(
                (InputIssue((), "blocked_index", tr("Nie znaleziono blokady.")),)
            ) from error
    elif action == "unpin":
        for node in data["nodes"]:
            node["pinned_v4"] = node["pinned_v6"] = None
        data["pinned_v6_infrastructure"] = []
    return loads_project(json.dumps(document, ensure_ascii=False)).project


def revision(form: Mapping[str, Any]) -> int:
    try:
        value = int(str(form.get("revision", "")))
        if value < 1:
            raise ValueError
        return value
    except ValueError as error:
        raise ProjectJSONError(
            (InputIssue(("revision",), "revision", tr("Brak poprawnej wersji zapisu.")),)
        ) from error
