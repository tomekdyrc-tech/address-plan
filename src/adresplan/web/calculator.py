"""Human-facing calculator views built on the shared, bounded allocator."""

import json
from ipaddress import IPv4Network
from typing import Any
from uuid import uuid4

from starlette.datastructures import FormData

from adresplan.application.console import calculation_error
from adresplan.application.project_json import loads_project
from adresplan.core.allocator import allocate
from adresplan.core.calc import CalculationError, calculate, preview_subnets
from adresplan.core.models import AllocationRequest, Project


def calculator_context(form: FormData) -> dict[str, Any]:
    result = calculate(str(form.get("text", "")))
    mode = str(form.get("mode", "legacy"))
    rows: list[dict[str, Any]] = []
    context: dict[str, Any] = {"result": result, "rows": rows, "mode": mode}
    if mode == "vlsm":
        if not isinstance(result.network, IPv4Network):
            raise ValueError(
                "Plan według liczby urządzeń obsługuje IPv4. Dla IPv6 wybierz równy podział."
            )
        names, counts = form.getlist("subnet_name"), form.getlist("subnet_hosts")
        if len(names) != len(counts) or not 1 <= len(names) <= 128:
            raise ValueError("Dodaj od 1 do 128 sieci i podaj liczbę urządzeń dla każdej.")
        requests = []
        wanted = {}
        for index, (name, count) in enumerate(zip(names, counts, strict=True)):
            label = str(name).strip()
            if not label or len(label) > 100:
                raise ValueError("Każda sieć potrzebuje nazwy (do 100 znaków).")
            try:
                hosts = int(str(count))
            except ValueError as error:
                raise ValueError(f"{label}: wpisz całkowitą liczbę urządzeń.") from error
            if not 1 <= hosts <= 2**32 - 2:
                raise ValueError(f"{label}: liczba urządzeń musi wynosić od 1 do 4294967294.")
            prefix = 32 - (hosts + 1).bit_length()
            key = str(index)
            wanted[key] = (label, hosts)
            requests.append(AllocationRequest[IPv4Network](node_id=key, name=label, prefix=prefix))
        plan = allocate(result.network, requests)
        for allocation in plan.allocations:
            name, hosts = wanted[allocation.node_id]
            subnet = calculate(str(allocation.network))
            rows.append({"name": name, "hosts": hosts, "subnet": subnet})
        context["free_blocks"] = plan.free_blocks
        context["unallocated"] = [
            wanted[f.node_id][0] for f in plan.findings if f.node_id in wanted
        ]
        context["requested_hosts"] = sum(h for _, h in wanted.values())
    elif mode in ("count", "prefix", "legacy"):
        split_count = form.get("count") if mode != "prefix" else None
        prefix_value = form.get("new_prefix") if mode != "count" else None
        if mode != "legacy" or split_count or prefix_value:
            try:
                preview = preview_subnets(
                    result.network,
                    count=int(str(split_count)) if split_count else None,
                    new_prefix=int(str(prefix_value)) if prefix_value else None,
                    limit=int(str(form.get("limit", "32"))),
                )
            except CalculationError:
                raise
            except ValueError as error:
                raise ValueError("Wpisz całkowitą liczbę podsieci lub długość prefiksu.") from error
            context["preview"] = preview
            rows.extend(
                {"name": str(i + 1), "subnet": calculate(str(n))}
                for i, n in enumerate(preview.subnets)
            )
    elif mode != "inspect":
        raise ValueError("Wybierz sposób obliczenia.")
    return context


def friendly_error(error: ValueError) -> str:
    if not isinstance(error, CalculationError):
        return str(error)
    if error.code == "choose_one_split_mode":
        return (
            "Wybierz podział według liczby podsieci albo długości prefiksu "
            "i uzupełnij odpowiednie pole."
        )
    if error.code == "subnet_count_not_power_of_two":
        return (
            "Równe podsieci tworzymy w liczbie 2, 4, 8, 16 itd. "
            f"Wpisz {error.suggested_count} lub wybierz VLSM dla sieci o różnych rozmiarach."
        )
    return calculation_error(error)


def project_from_calculation(context: dict[str, Any], name: str) -> Project:
    if context["mode"] != "vlsm" or context.get("unallocated") or not context["rows"]:
        raise ValueError("Utwórz najpierw kompletny plan VLSM IPv4, aby przenieść go do projektu.")
    site, building = uuid4().hex, uuid4().hex
    document = {
        "schema_version": 3,
        "project": {
            "id": uuid4().hex,
            "name": name.strip() or "Plan z kalkulatora",
            "v4_pool": str(context["result"].network),
            "v6_active": False,
            "settings": {"growth_pct": 0, "gateway": "none", "gateway_addrs": 0},
            "nodes": [
                {"id": site, "kind": "site", "name": "Lokalizacja 1"},
                {"id": building, "kind": "building", "name": "Budynek 1", "parent_id": site},
                *[
                    {
                        "id": uuid4().hex,
                        "kind": "segment",
                        "name": r["name"],
                        "parent_id": building,
                        "hosts": r["hosts"],
                        "pinned_v4": str(r["subnet"].network),
                        "v6_enabled": False,
                    }
                    for r in context["rows"]
                ],
            ],
        },
    }
    return loads_project(json.dumps(document, ensure_ascii=False)).project
