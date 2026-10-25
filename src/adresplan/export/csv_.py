"""Segment CSV with explicit completeness and spreadsheet-safe text cells."""

import csv
from collections.abc import Iterator
from io import StringIO

from adresplan.application.console import format_finding
from adresplan.core.models import FindingLevel, Project
from adresplan.export.common import address_range, create_report

CSV_COLUMNS = (
    "Typ wiersza",
    "Projekt ID",
    "Projekt",
    "Status planu",
    "Błędy",
    "Ostrzeżenia",
    "Lokalizacja",
    "Budynek",
    "Segment ID",
    "Segment",
    "VLAN",
    "Rola",
    "Hosty (wejście)",
    "Zapas [%]",
    "Hosty (z zapasem)",
    "Wymagane użyteczne IPv4",
    "IPv4 CIDR",
    "Maska",
    "Brama",
    "Zakres użyteczny IPv4",
    "Zakres statyczny",
    "Zakres DHCP",
    "Broadcast",
    "IPv6 CIDR",
    "Brama IPv6",
    "Tryb RA",
    "Końce IPv6",
    "Reverse DNS IPv6",
    "Uwagi",
    "Uwagi budynku",
    "Uwagi lokalizacji",
    "Walidacja",
)


def spreadsheet_text(value: str) -> str:
    """Prefix potentially executable text, including leading whitespace/control chars."""
    first = next((c for c in value if not c.isspace() and c != "\ufeff"), "")
    return (
        "'" + value
        if (first in ("=", "+", "-", "@") or value.startswith(("\t", "\r", "\n")))
        else value
    )


def report_records(project: Project) -> Iterator[dict[str, str]]:
    report = create_report(project)
    base = {
        "Typ wiersza": "segment",
        "Projekt ID": project.id,
        "Projekt": project.name,
        "Status planu": report.status,
        "Błędy": str(sum(f.level is FindingLevel.ERROR for f in report.plan.findings)),
        "Ostrzeżenia": str(sum(f.level is FindingLevel.WARNING for f in report.plan.findings)),
    }
    for row in report.rows:
        segment, reservation, info = row.segment, row.reservation, row.info6
        data = {
            **base,
            "Lokalizacja": row.site.name,
            "Budynek": row.building.name,
            "Segment ID": segment.id,
            "Segment": segment.name,
            "VLAN": str(segment.vlan_id) if segment.vlan_id is not None else "",
            "Rola": segment.role.value,
            "Hosty (wejście)": str(segment.hosts),
            "Zapas [%]": str(row.growth_pct),
            "Hosty (z zapasem)": str(row.grown_hosts),
            "Wymagane użyteczne IPv4": str(reservation.usable_needed) if reservation else "",
            "IPv4 CIDR": str(row.v4) if row.v4 else "",
            "Maska": str(row.v4.netmask) if row.v4 else "",
            "Brama": ", ".join(str(a) for a in reservation.gateway_addresses)
            if reservation
            else "",
            "Zakres użyteczny IPv4": f"{reservation.first_usable}–{reservation.last_usable}"
            if reservation
            else "",
            "Zakres statyczny": address_range(reservation.static_range) if reservation else "",
            "Zakres DHCP": address_range(reservation.dhcp_range) if reservation else "",
            "Broadcast": str(row.v4.broadcast_address) if row.v4 and row.v4.prefixlen < 31 else "",
            "IPv6 CIDR": str(row.v6) if row.v6 else "",
            "Brama IPv6": str(info.gateway) if info and info.gateway else "",
            "Tryb RA": info.ra_mode.value if info and info.ra_mode else "",
            "Końce IPv6": ", ".join(str(a) for a in info.endpoints) if info else "",
            "Reverse DNS IPv6": info.reverse_zone or "" if info else "",
            "Uwagi": segment.notes,
            "Uwagi budynku": row.building.notes,
            "Uwagi lokalizacji": row.site.notes,
            "Walidacja": "\n".join(format_finding(f, project) for f in row.findings),
        }
        yield data
    if not report.rows:
        yield {
            **base,
            "Typ wiersza": "projekt",
            "Walidacja": "\n".join(
                format_finding(f, project)
                for f in report.plan.findings
                if f.level is not FindingLevel.INFO
            ),
        }


def dumps_csv(project: Project) -> str:
    stream = StringIO(newline="")
    writer = csv.DictWriter(
        stream, fieldnames=CSV_COLUMNS, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n"
    )
    writer.writeheader()
    for data in report_records(project):
        writer.writerow({key: spreadsheet_text(value) for key, value in data.items()})
    return stream.getvalue()
