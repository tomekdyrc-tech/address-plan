"""Calculate endpoint, gateway, static and DHCP ranges without enumerating hosts."""

from ipaddress import IPv4Address, IPv4Network

from adresplan.core.models import (
    AddressRange,
    GatewayPosition,
    ProjectSettings,
    Segment,
    SegmentReservations,
    SegmentRole,
)
from adresplan.core.sizing import size_segment_v4


def _address_range(first: int, last: int) -> AddressRange | None:
    return AddressRange(first=IPv4Address(first), last=IPv4Address(last)) if first <= last else None


def reserve_segment_v4(
    segment: Segment, settings: ProjectSettings, network: IPv4Network
) -> SegmentReservations:
    """The first gateway in the returned tuple is the virtual/default gateway."""
    size = size_segment_v4(segment, settings)
    if not isinstance(network, IPv4Network):
        raise ValueError("IPv4 reservations require an IPv4 network")
    if network.prefixlen > size.prefix:
        raise ValueError("network is too small for segment requirements")

    if segment.role is SegmentRole.LOOPBACK and network.prefixlen != 32:
        raise ValueError("loopbacks require a /32 network")
    if segment.role is SegmentRole.P2P and network.prefixlen not in (30, 31):
        raise ValueError("P2P links require a /30 or /31 network")
    first = int(network.network_address) + (1 if network.prefixlen <= 30 else 0)
    last = int(network.broadcast_address) - (1 if network.prefixlen <= 30 else 0)
    capacity = last - first + 1
    if capacity < size.usable_needed:
        raise ValueError("network has insufficient usable addresses")

    if segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK):
        return SegmentReservations(
            node_id=segment.id,
            network=network,
            usable_needed=size.usable_needed,
            first_usable=IPv4Address(first),
            last_usable=IPv4Address(last),
        )

    gateway = settings.gateway if segment.gateway is None else segment.gateway
    count = segment.gateway_addrs
    if count is None:
        count = 0 if gateway is GatewayPosition.NONE else settings.gateway_addrs
    gateways: tuple[IPv4Address, ...] = ()
    if gateway is GatewayPosition.FIRST:
        gateways = tuple(IPv4Address(first + offset) for offset in range(count))
        first += count
    elif gateway is GatewayPosition.LAST:
        gateways = tuple(IPv4Address(last - offset) for offset in range(count))
        last -= count
    static = _address_range(first, first + segment.static_count - 1)
    first += segment.static_count
    return SegmentReservations(
        node_id=segment.id,
        network=network,
        usable_needed=size.usable_needed,
        first_usable=IPv4Address(int(network.network_address) + 1),
        last_usable=IPv4Address(int(network.broadcast_address) - 1),
        gateway_addresses=gateways,
        static_range=static,
        dhcp_range=_address_range(first, last),
    )
