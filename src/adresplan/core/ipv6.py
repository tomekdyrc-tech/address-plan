"""Pure IPv6 sizing, addressing and reverse-DNS helpers."""

from ipaddress import IPv6Address, IPv6Network

from adresplan.core.models import IPv6Kind
from adresplan.core.sizing import grown_host_count

BUILDING_PREFIXES = (60, 56, 52)
DOCUMENTATION = IPv6Network("2001:db8::/32")
ULA = IPv6Network("fd00::/8")
GUA = IPv6Network("2000::/3")
SUBNET64_SIZE = IPv6Network("::/64").num_addresses


def classify_prefix(network: IPv6Network) -> IPv6Kind:
    for prefix, kind in [
        (DOCUMENTATION, IPv6Kind.DOCUMENTATION),
        (ULA, IPv6Kind.ULA),
        (GUA, IPv6Kind.GUA),
    ]:
        if network.subnet_of(prefix):
            return kind
    raise ValueError("planning requires a GUA, locally assigned ULA or documentation prefix")


def count_subnets64(network: IPv6Network) -> int:
    return network.num_addresses // SUBNET64_SIZE


def reverse_zone(network: IPv6Network) -> str:
    """Return a nibble-aligned ip6.arpa zone, not a fictitious /127 delegation."""
    if network.prefixlen % 4:
        raise ValueError("reverse zones require a prefix aligned to four bits")
    return ".".join(
        network.network_address.reverse_pointer.split(".")[32 - network.prefixlen // 4 :]
    )


def ula_from_global_id(global_id: bytes) -> IPv6Network:
    """Build fd + 40 Global ID bits + 80 zero bits, without accessing randomness."""
    if not isinstance(global_id, bytes) or len(global_id) != 5:
        raise ValueError("ULA Global ID must contain exactly five bytes")
    return IPv6Network((IPv6Address(b"\xfd" + global_id + bytes(10)), 48))


def building_prefix(segment_count: int, minimum_prefix: int, growth_pct: int) -> int:
    needed = grown_host_count(segment_count, growth_pct)
    if (
        not isinstance(minimum_prefix, int)
        or isinstance(minimum_prefix, bool)
        or minimum_prefix not in BUILDING_PREFIXES
    ):
        raise ValueError("building prefix must be 52, 56 or 60")
    for prefix in BUILDING_PREFIXES:
        if prefix <= minimum_prefix and count_subnets64(IPv6Network((0, prefix))) >= needed:
            return prefix
    raise ValueError("building requires more /64 subnets than a /52 can hold")


def subnet64_at(network: IPv6Network, offset: int) -> IPv6Network:
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset < count_subnets64(network)
    ):
        raise ValueError("/64 subnet offset is outside its parent")
    address = IPv6Address(int(network.network_address) + offset * SUBNET64_SIZE)
    return IPv6Network((address, 64))
