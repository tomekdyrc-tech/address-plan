"""Pure subnet calculations and bounded, lazy subnet previews."""

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_interface,
)
from itertools import islice

from adresplan.core.ipv6 import count_subnets64, reverse_zone
from adresplan.core.models import Network
from adresplan.core.sizing import next_pow2
from adresplan.core.validate import is_rfc1918

MAX_PREVIEW_ROWS = 256


class CalculationError(ValueError):
    """Stable error codes; the CLI/web boundary supplies translated messages."""

    def __init__(self, code: str, *, suggested_count: int | None = None) -> None:
        self.code = code
        self.suggested_count = suggested_count
        super().__init__(code)


class IPv6AddressKind(StrEnum):
    DOCUMENTATION = "doc"
    ULA = "ula"
    GUA = "gua"
    LINK_LOCAL = "link_local"
    MULTICAST = "multicast"
    LOOPBACK = "loopback"
    UNSPECIFIED = "unspecified"
    MIXED = "mixed"
    OTHER = "other"


_V6_RANGES = (
    (IPv6Network("::/128"), IPv6AddressKind.UNSPECIFIED),
    (IPv6Network("::1/128"), IPv6AddressKind.LOOPBACK),
    (IPv6Network("2001:db8::/32"), IPv6AddressKind.DOCUMENTATION),
    (IPv6Network("fc00::/7"), IPv6AddressKind.ULA),
    (IPv6Network("fe80::/10"), IPv6AddressKind.LINK_LOCAL),
    (IPv6Network("ff00::/8"), IPv6AddressKind.MULTICAST),
    (IPv6Network("2000::/3"), IPv6AddressKind.GUA),
)


def _classify_v6(network: IPv6Network) -> IPv6AddressKind:
    for block, kind in _V6_RANGES:
        if network.subnet_of(block):
            if kind is IPv6AddressKind.GUA and network.overlaps(IPv6Network("2001:db8::/32")):
                return IPv6AddressKind.MIXED
            return kind
    return (
        IPv6AddressKind.MIXED
        if any(network.overlaps(block) for block, _ in _V6_RANGES)
        else IPv6AddressKind.OTHER
    )


@dataclass(frozen=True, slots=True)
class IPv4Calculation:
    address: IPv4Address
    network: IPv4Network
    broadcast: IPv4Address | None
    netmask: IPv4Address
    wildcard: IPv4Address
    first_usable: IPv4Address
    last_usable: IPv4Address
    usable_count: int
    binary_mask: str
    rfc1918: bool
    reverse_zone: str | None
    reverse_pointer: str


@dataclass(frozen=True, slots=True)
class IPv6Calculation:
    address: IPv6Address
    network: IPv6Network
    compressed: str
    exploded: str
    address_kind: IPv6AddressKind
    network_kind: IPv6AddressKind
    subnets64: int
    reverse_zone: str | None
    reverse_pointer: str


@dataclass(frozen=True, slots=True)
class SubnetPreview:
    network: Network
    new_prefix: int
    total_count: int
    subnets: tuple[Network, ...]

    @property
    def is_truncated(self) -> bool:
        return len(self.subnets) < self.total_count


def calculate(text: str) -> IPv4Calculation | IPv6Calculation:
    """Accept a host/prefix, address + netmask/hostmask, or a single host address."""
    parts = text.split()
    if not 1 <= len(parts) <= 2 or "%" in text:
        raise CalculationError("invalid_address")
    normalized = parts[0] if len(parts) == 1 else "/".join(parts)
    try:
        interface = ip_interface(normalized)
    except ValueError as error:
        raise CalculationError("invalid_address") from error
    if isinstance(interface, IPv4Interface):
        network = interface.network
        ordinary = network.prefixlen < 31
        binary = format(network.netmask, "b")
        zone = None
        if network.prefixlen in (8, 16, 24):
            zone = ".".join(
                network.network_address.reverse_pointer.split(".")[4 - network.prefixlen // 8 :]
            )
        return IPv4Calculation(
            address=interface.ip,
            network=network,
            broadcast=network.broadcast_address if ordinary else None,
            netmask=network.netmask,
            wildcard=network.hostmask,
            first_usable=network[1] if ordinary else network[0],
            last_usable=network[-2] if ordinary else network[-1],
            usable_count=network.num_addresses - 2 if ordinary else network.num_addresses,
            binary_mask=".".join(binary[i : i + 8] for i in range(0, 32, 8)),
            rfc1918=is_rfc1918(network),
            reverse_zone=zone,
            reverse_pointer=interface.ip.reverse_pointer,
        )
    network6 = interface.network
    return IPv6Calculation(
        address=interface.ip,
        network=network6,
        compressed=network6.compressed,
        exploded=network6.exploded,
        address_kind=_classify_v6(IPv6Network((interface.ip, 128))),
        network_kind=_classify_v6(network6),
        subnets64=count_subnets64(network6),
        reverse_zone=reverse_zone(network6) if network6.prefixlen % 4 == 0 else None,
        reverse_pointer=interface.ip.reverse_pointer,
    )


def preview_subnets(
    network: Network,
    *,
    count: int | None = None,
    new_prefix: int | None = None,
    limit: int = MAX_PREVIEW_ROWS,
) -> SubnetPreview:
    """Materialize at most 256 CIDRs, even for an IPv6 /0 split into /128s."""
    if (count is None) == (new_prefix is None):
        raise CalculationError("choose_one_split_mode")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PREVIEW_ROWS:
        raise CalculationError("invalid_preview_limit")
    if count is not None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise CalculationError("invalid_subnet_count")
        suggestion = next_pow2(count)
        if suggestion != count:
            raise CalculationError("subnet_count_not_power_of_two", suggested_count=suggestion)
        new_prefix = network.prefixlen + count.bit_length() - 1
    if (
        isinstance(new_prefix, bool)
        or not isinstance(new_prefix, int)
        or not network.prefixlen <= new_prefix <= network.max_prefixlen
    ):
        raise CalculationError("invalid_subnet_prefix")
    total = 2 ** (new_prefix - network.prefixlen)
    return SubnetPreview(
        network=network,
        new_prefix=new_prefix,
        total_count=total,
        subnets=tuple(islice(network.subnets(new_prefix=new_prefix), limit)),
    )
