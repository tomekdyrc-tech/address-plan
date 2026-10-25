"""Starting gateway configuration (Cisco IOS, MikroTik RouterOS) generated from a fresh plan.

The output is a draft to review before use: one gateway per building, a VLAN interface per
segment with a VLAN ID, DHCP for LAN segments, and loopbacks. Physical interfaces are unknown,
so routed segments without a VLAN and P2P links are emitted as commented templates.
User text never reaches a command unescaped: names become slugs and descriptions one line.
"""

import re
import unicodedata
from collections.abc import Callable, Iterator
from ipaddress import IPv4Address
from typing import Literal, TypeAlias

from adresplan.core.models import IPv6RAMode, Project, SegmentRole
from adresplan.export.common import Report, SegmentRow, create_report
from adresplan.i18n import tr

ConfigVendor: TypeAlias = Literal["cisco", "mikrotik"]
INTERFACE_PLACEHOLDER = "<INTERFACE>"


def _line(value: object, limit: int = 200) -> str:
    """One printable line: controls and newlines become spaces, never a second command."""
    text = "".join(" " if unicodedata.category(c)[0] == "C" else c for c in str(value))
    return " ".join(text.split())[:limit]


# Letters and punctuation without an ASCII decomposition; the rest is handled by NFKD.
_ASCII = str.maketrans({"ł": "l", "Ł": "L", "—": "-", "–": "-", "„": '"', "”": '"', "→": "->"})


def _ascii(value: str) -> str:
    """Device consoles and older firmware expect ASCII: Dźwięk -> Dzwiek, Łącze -> Lacze."""
    text = unicodedata.normalize("NFKD", value.translate(_ASCII))
    return text.encode("ascii", "ignore").decode()


def _slug(value: str, limit: int) -> str:
    """ASCII name safe for VLAN, pool and interface names."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", _ascii(value)).strip("-")
    return slug[:limit].strip("-") or "segment"


def _quoted(value: object) -> str:
    """RouterOS string literal; backslash, quote and $ cannot end it or expand variables."""
    text = _line(value).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    return f'"{text}"'


def _gateway(row: SegmentRow) -> IPv4Address | None:
    reservation = row.reservation
    return (
        reservation.gateway_addresses[0] if reservation and reservation.gateway_addresses else None
    )


def _routed(row: SegmentRow) -> bool:
    """A VLAN interface can be generated; otherwise the block needs a physical interface."""
    return row.segment.role is not SegmentRole.P2P and row.segment.vlan_id is not None


def _serves_dhcp(row: SegmentRow) -> bool:
    return (
        row.segment.role is SegmentRole.LAN
        and _gateway(row) is not None
        and row.reservation is not None
        and row.reservation.dhcp_range is not None
    )


def _excluded(row: SegmentRow) -> Iterator[tuple[IPv4Address, IPv4Address]]:
    """Usable addresses outside the DHCP range: gateways and the static pool."""
    reservation = row.reservation
    if reservation is None or reservation.dhcp_range is None:
        return
    first, last = reservation.dhcp_range.first, reservation.dhcp_range.last
    if reservation.first_usable < first:
        yield reservation.first_usable, IPv4Address(int(first) - 1)
    if last < reservation.last_usable:
        yield IPv4Address(int(last) + 1), reservation.last_usable


def _manual_reason(row: SegmentRow) -> str:
    name = _line(row.segment.name)
    if row.segment.role is SegmentRole.P2P:
        return tr("Łącze P2P {name}: przypisz interfejs fizyczny.", name=name)
    return tr("{name}: brak VLAN-u — przypisz interfejs routowany.", name=name)


def _commented(lines: list[str], mark: str) -> list[str]:
    return [f"{mark}{text}" if text.startswith(" ") else f"{mark} {text}" for text in lines]


def _header(report: Report, mark: str) -> list[str]:
    project = report.project
    lines = [
        tr("Address Plan — konfiguracja startowa: {name}", name=_line(project.name)),
        tr(
            "Status planu: {status}. Pula IPv4: {pool}.", status=report.status, pool=project.v4_pool
        ),
        tr(
            "Szkic do przeglądu przed wdrożeniem: sprawdź nazwy interfejsów, trunki VLAN, "
            "DHCP i zabezpieczenia urządzenia."
        ),
        tr(
            "Segmenty bez VLAN-u i łącza P2P są zakomentowane; uzupełnij {placeholder}.",
            placeholder=INTERFACE_PLACEHOLDER,
        ),
    ]
    if not report.plan.is_complete:
        lines.append(
            tr("PLAN NIEKOMPLETNY — pominięto segmenty bez przydziału. Popraw błędy w planie.")
        )
    return [f"{mark} {line}" for line in lines]


def _render(
    report: Report,
    mark: str,
    segment: Callable[[SegmentRow, int], list[str]],
    prologue: list[str],
    epilogue: list[str],
) -> str:
    lines = [*_header(report, mark), *prologue]
    for building in report.buildings:
        rows = [r for r in report.rows if r.building.id == building.id]
        if not rows:
            continue
        lines += [mark, f"{mark} ===== {_line(rows[0].site.name)} / {_line(building.name)} ====="]
        loopbacks = 0
        for row in rows:
            if row.v4 is None:
                name = _line(row.segment.name)
                lines.append(
                    f"{mark} " + tr("{name}: brak przydziału IPv4 — pominięto.", name=name)
                )
                continue
            lines += segment(row, loopbacks)
            loopbacks += row.segment.role is SegmentRole.LOOPBACK
    return "\n".join([*lines, *epilogue]) + "\n"


def _cisco_ipv6(row: SegmentRow) -> list[str]:
    info, network = row.info6, row.v6
    if network is None:
        return []
    if row.segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK) or info is None:
        return [f" ipv6 address {network}"]
    if info.gateway is None:
        lines = [f" ipv6 address {network}"]
    elif info.gateway.is_link_local:
        lines = [" ipv6 enable", f" ipv6 address {info.gateway} link-local"]
        lines.append(f" ipv6 nd prefix {network}")
    else:
        lines = [f" ipv6 address {info.gateway}/{network.prefixlen}"]
    if info.ra_mode is IPv6RAMode.DHCPV6:
        lines += [" ipv6 nd managed-config-flag", " ipv6 nd other-config-flag"]
        lines.append(" ! " + tr("Serwer lub relay DHCPv6 skonfiguruj osobno."))
    return lines


def _cisco_segment(row: SegmentRow, loopback: int) -> list[str]:
    segment, v4, reservation = row.segment, row.v4, row.reservation
    assert v4 is not None
    name, gateway = _line(segment.name), _gateway(row)
    if segment.role is SegmentRole.LOOPBACK:
        return [
            f"interface Loopback{loopback}",
            f" description {name}",
            f" ip address {v4.network_address} {v4.netmask}",
            *_cisco_ipv6(row),
            "!",
        ]
    interface = f"Vlan{segment.vlan_id}" if _routed(row) else INTERFACE_PLACEHOLDER
    block = [f"interface {interface}", f" description {name}"]
    if segment.role is SegmentRole.P2P:
        block.append(f" ip address {v4.network_address} {v4.netmask}")
    elif gateway is not None:
        block.append(f" ip address {gateway} {v4.netmask}")
    else:
        block.append(" ! " + tr("Plan nie przewiduje bramy w tej podsieci."))
    if reservation is not None and len(reservation.gateway_addresses) > 1:
        extra = ", ".join(map(str, reservation.gateway_addresses[1:]))
        block.append(
            " ! " + tr("Dodatkowe adresy bram (np. HSRP/VRRP): {addresses}", addresses=extra)
        )
    block += [*_cisco_ipv6(row), " no shutdown"]
    if _routed(row):
        lines = [f"vlan {segment.vlan_id}", f" name {_slug(segment.name, 32)}", "!", *block, "!"]
    else:
        lines = [f"! {_manual_reason(row)}", *_commented(block, "!"), "!"]
    if _serves_dhcp(row):
        pool = (
            f"VLAN{segment.vlan_id}-{_slug(segment.name, 24)}"
            if segment.vlan_id
            else _slug(segment.name, 32)
        )
        dhcp = [f"ip dhcp excluded-address {first} {last}" for first, last in _excluded(row)]
        dhcp += [
            f"ip dhcp pool {pool}",
            f" network {v4.network_address} {v4.netmask}",
            f" default-router {gateway}",
        ]
        lines += [*(dhcp if _routed(row) else _commented(dhcp, "!")), "!"]
    return lines


def _mikrotik_ipv6(row: SegmentRow, interface: str, comment: str) -> list[str]:
    info, network = row.info6, row.v6
    if network is None:
        return []
    end = f"interface={interface} comment={comment}"
    if row.segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK) or info is None:
        return [f"/ipv6 address add address={network} advertise=no {end}"]
    if info.gateway is not None and info.gateway.is_link_local:
        lines = [
            f"/ipv6 address add address={info.gateway}/64 {end}",
            f"/ipv6 nd prefix add prefix={network} interface={interface}",
        ]
    else:
        address = f"{info.gateway}/{network.prefixlen}" if info.gateway else str(network)
        lines = [f"/ipv6 address add address={address} advertise=yes {end}"]
    if info.ra_mode is IPv6RAMode.DHCPV6:
        lines.append(
            f"/ipv6 nd add interface={interface} managed-address-configuration=yes"
            " other-configuration=yes"
        )
    return lines


def _mikrotik_segment(row: SegmentRow, loopback: int) -> list[str]:
    segment, v4, reservation = row.segment, row.v4, row.reservation
    assert v4 is not None
    comment, gateway = _quoted(segment.name), _gateway(row)
    if segment.role is SegmentRole.LOOPBACK:
        interface = f"lo{loopback}"
        return [
            f"/interface bridge add name={interface} comment={comment}",
            f"/ip address add address={v4} interface={interface} comment={comment}",
            *_mikrotik_ipv6(row, interface, comment),
        ]
    routed = _routed(row)
    interface = (
        f"vlan{segment.vlan_id}-{_slug(segment.name, 20)}" if routed else INTERFACE_PLACEHOLDER
    )
    end = f"interface={interface} comment={comment}"
    block = (
        [
            f"/interface vlan add name={interface} vlan-id={segment.vlan_id} interface=bridge"
            f" comment={comment}"
        ]
        if routed
        else []
    )
    if segment.role is SegmentRole.P2P:
        block.append(f"/ip address add address={v4.network_address}/{v4.prefixlen} {end}")
    elif gateway is not None:
        block.append(f"/ip address add address={gateway}/{v4.prefixlen} {end}")
    block += _mikrotik_ipv6(row, interface, comment)
    if _serves_dhcp(row):
        assert reservation is not None and reservation.dhcp_range is not None
        pool = _slug(interface if routed else segment.name, 24)
        block += [
            f"/ip pool add name=pool-{pool}"
            f" ranges={reservation.dhcp_range.first}-{reservation.dhcp_range.last}",
            f"/ip dhcp-server add name=dhcp-{pool} address-pool=pool-{pool} interface={interface}",
            f"/ip dhcp-server network add address={v4} gateway={gateway} comment={comment}",
        ]
    return block if routed else [f"# {_manual_reason(row)}", *_commented(block, "#")]


def dumps_config(project: Project, vendor: ConfigVendor) -> str:
    """Whole configuration as ASCII text, comments included."""
    report = create_report(project)
    if vendor == "cisco":
        uses_ipv6 = any(row.v6 is not None for row in report.rows)
        prologue = ["!", "ipv6 unicast-routing"] if uses_ipv6 else []
        return _ascii(_render(report, "!", _cisco_segment, prologue, ["!", "end"]))
    note = tr("Interfejsy VLAN powstają na interfejsie bridge; dopasuj go do trunku.")
    return _ascii(_render(report, "#", _mikrotik_segment, [f"# {note}"], []))
