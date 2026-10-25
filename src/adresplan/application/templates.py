"""Reusable building recipes with fresh IDs and no address-specific reservations."""

import json
from typing import Any
from uuid import uuid4

from adresplan.application.project_json import InputIssue, ProjectJSONError, loads_project
from adresplan.core.models import Project
from adresplan.store.sqlite import input_document


def building_template(project: Project, building_id: str) -> dict[str, Any]:
    data = input_document(project)["project"]
    root = next(
        (n for n in data["nodes"] if n["id"] == building_id and n["kind"] == "building"), None
    )
    if root is None:
        raise ProjectJSONError((InputIssue((), "building", "Wybierz istniejący budynek."),))
    nodes = [dict(root), *(dict(n) for n in data["nodes"] if n["parent_id"] == building_id)]
    for node in nodes:
        node["pinned_v4"] = node["pinned_v6"] = None
        if node["kind"] == "segment" and node["role"] in ("lan", "mgmt"):
            for key in ("growth_pct", "gateway"):
                if node[key] is None:
                    node[key] = data["settings"][key]
            if node["gateway_addrs"] is None:
                node["gateway_addrs"] = (
                    0 if node["gateway"] == "none" else data["settings"]["gateway_addrs"]
                )
            if node["ra_mode"] is None:
                node["ra_mode"] = data["settings"]["v6_ra_mode"]
    return {"building": nodes[0], "segments": nodes[1:]}


def apply_template(project: Project, template: dict[str, Any], site_id: str, name: str) -> Project:
    data = input_document(project)
    target = next((n for n in project.nodes if n.id == site_id and n.kind == "site"), None)
    if target is None:
        raise ProjectJSONError((InputIssue((), "site", "Wybierz lokalizację docelową."),))
    building_id = uuid4().hex
    root = {**template["building"], "id": building_id, "parent_id": site_id, "name": name}
    root["pinned_v4"] = root["pinned_v6"] = None
    data["project"]["nodes"].append(root)
    for original in template["segments"]:
        data["project"]["nodes"].append(
            {
                **original,
                "id": uuid4().hex,
                "parent_id": building_id,
                "pinned_v4": None,
                "pinned_v6": None,
            }
        )
    return loads_project(json.dumps(data, ensure_ascii=False)).project


def site_template(project: Project, site_id: str) -> dict[str, Any]:
    """Capture all buildings in a location without address assignments."""
    site = next((n for n in project.nodes if n.id == site_id and n.kind == "site"), None)
    if site is None:
        raise ProjectJSONError((InputIssue((), "site", "Wybierz istniejącą lokalizację."),))
    return {
        "site": {"name": site.name, "notes": site.notes},
        "buildings": [
            building_template(project, n.id)
            for n in project.nodes
            if n.parent_id == site_id and n.kind == "building"
        ],
    }


def apply_site_template(project: Project, template: dict[str, Any], names: str) -> Project:
    """Create a batch atomically; callers persist only the final validated project."""
    labels = [line.strip() for line in names.splitlines() if line.strip()]
    if not 1 <= len(labels) <= 50:
        raise ProjectJSONError(
            (InputIssue((), "sites", "Podaj od 1 do 50 nazw lokalizacji, po jednej w wierszu."),)
        )
    for label in labels:
        site_id = uuid4().hex
        data = input_document(project)
        data["project"]["nodes"].append(
            {
                "id": site_id,
                "kind": "site",
                "name": label,
                "notes": template["site"].get("notes", ""),
            }
        )
        project = loads_project(json.dumps(data, ensure_ascii=False)).project
        for recipe in template["buildings"]:
            project = apply_template(project, recipe, site_id, recipe["building"]["name"])
    return project


def starter_templates() -> dict[str, dict[str, Any]]:
    """Small editable recipes available before the user has saved a template."""
    recipes = {}
    for key, title, segments in (
        (
            "office",
            "Obiekt podstawowy",
            (("Pracownicy", 20, 10), ("Wi-Fi gościnne", 30, 20), ("Zarządzanie", 5, 99)),
        ),
        (
            "av",
            "Obiekt rozbudowany",
            (
                ("Pracownicy", 10, 10),
                ("Urządzenia i usługi", 30, 20),
                ("Wi-Fi gościnne", 60, 30),
                ("Zarządzanie", 5, 99),
            ),
        ),
    ):
        recipes[key] = {
            "building": {"kind": "building", "name": title},
            "segments": [
                {
                    "kind": "segment",
                    "name": name,
                    "hosts": hosts,
                    "vlan_id": vlan,
                    "role": "mgmt" if vlan == 99 else "lan",
                }
                for name, hosts, vlan in segments
            ],
        }
    return recipes
