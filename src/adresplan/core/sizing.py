"""Size IPv4 segments using integers only; never enumerate host addresses."""

from adresplan.core.models import (
    GatewayPosition,
    ProjectSettings,
    Segment,
    SegmentRole,
    SegmentSize,
)


def _nonnegative_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def next_pow2(value: int) -> int:
    """Return the smallest power of two >= value, with a minimum of one."""
    _nonnegative_integer(value, "value")
    return 1 if value <= 1 else 2 ** (value - 1).bit_length()


def grown_host_count(hosts: int, growth_pct: int) -> int:
    """Round percentage growth up without floating-point arithmetic."""
    _nonnegative_integer(hosts, "hosts")
    _nonnegative_integer(growth_pct, "growth_pct")
    return (hosts * (100 + growth_pct) + 99) // 100


def prefix_for_usable(usable_needed: int) -> int:
    """Return a LAN prefix (/0 through /30), reserving network and broadcast."""
    _nonnegative_integer(usable_needed, "usable_needed")
    if usable_needed == 0:
        raise ValueError("a LAN segment must need at least one usable address")
    if usable_needed > 2**32 - 2:
        raise ValueError("usable address requirement exceeds IPv4 capacity")
    return min(30, 32 - (usable_needed + 1).bit_length())


def size_segment_v4(segment: Segment, settings: ProjectSettings) -> SegmentSize:
    """Resolve input defaults and return the required IPv4 prefix and usable count.

    Unspecified gateway options inherit defaults for LAN/mgmt only. Infrastructure
    roles use fixed endpoint counts and reject explicitly incompatible reservations.
    """
    if not isinstance(segment.role, SegmentRole):
        raise ValueError("unknown segment role")
    if segment.gateway is not None and not isinstance(segment.gateway, GatewayPosition):
        raise ValueError("gateway position must be a GatewayPosition value")
    _nonnegative_integer(segment.hosts, "hosts")
    _nonnegative_integer(segment.static_count, "static_count")
    if segment.growth_pct is not None:
        _nonnegative_integer(segment.growth_pct, "growth_pct")
    if segment.gateway_addrs is not None:
        _nonnegative_integer(segment.gateway_addrs, "gateway_addrs")

    if segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK):
        endpoints = 2 if segment.role is SegmentRole.P2P else 1
        if segment.hosts not in (0, endpoints):
            raise ValueError(
                f"{segment.role} requires {endpoints} endpoints or hosts=0 (unspecified)"
            )
        if segment.static_count or segment.gateway_addrs not in (None, 0):
            raise ValueError("infrastructure roles cannot reserve gateway or static addresses")
        if segment.gateway not in (None, GatewayPosition.NONE):
            raise ValueError("infrastructure roles cannot have a gateway")
        if segment.growth_pct not in (None, 0):
            raise ValueError("infrastructure roles cannot apply host growth")
        if segment.role is SegmentRole.LOOPBACK:
            return SegmentSize(prefix=32, usable_needed=1)
        if settings.p2p_prefix not in (30, 31):
            raise ValueError("p2p_prefix must be 30 or 31")
        return SegmentSize(prefix=settings.p2p_prefix, usable_needed=2)

    growth = settings.growth_pct if segment.growth_pct is None else segment.growth_pct
    gateway = settings.gateway if segment.gateway is None else segment.gateway
    if not isinstance(gateway, GatewayPosition):
        raise ValueError("unknown gateway position")
    gateway_addrs = segment.gateway_addrs
    if gateway_addrs is None:
        gateway_addrs = 0 if gateway is GatewayPosition.NONE else settings.gateway_addrs
    _nonnegative_integer(gateway_addrs, "gateway_addrs")
    if gateway is GatewayPosition.NONE:
        if gateway_addrs != 0:
            raise ValueError("gateway=none requires gateway_addrs=0")
    elif not 1 <= gateway_addrs <= 3:
        raise ValueError("gateway=first/last requires between one and three addresses")
    needed = grown_host_count(segment.hosts, growth) + gateway_addrs + segment.static_count
    return SegmentSize(prefix=prefix_for_usable(needed), usable_needed=needed)
