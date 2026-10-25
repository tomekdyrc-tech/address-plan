"""Reference calculations, edge prefixes and bounded subdivision properties."""

from ipaddress import IPv4Address, IPv4Network, IPv6Network, ip_interface
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from adresplan.core.calc import (
    CalculationError,
    IPv4Calculation,
    IPv6AddressKind,
    IPv6Calculation,
    calculate,
    preview_subnets,
)


@pytest.mark.parametrize(
    "text",
    [
        "192.168.1.10/24",
        "192.168.1.10 255.255.255.0",
        "192.168.1.10/255.255.255.0",
        "192.168.1.10 0.0.0.255",
        "192.168.1.10/0.0.0.255",
        "  192.168.1.10\t255.255.255.0  ",
    ],
)
def test_ipv4_accepts_host_bits_prefix_netmask_and_wildcard(text: str) -> None:
    result = calculate(text)
    assert isinstance(result, IPv4Calculation)
    assert result.address == IPv4Address("192.168.1.10")
    assert result.network == IPv4Network("192.168.1.0/24")
    assert result.broadcast == IPv4Address("192.168.1.255")
    assert result.netmask == IPv4Address("255.255.255.0")
    assert result.wildcard == IPv4Address("0.0.0.255")
    assert str(result.first_usable) == "192.168.1.1"
    assert str(result.last_usable) == "192.168.1.254"
    assert result.usable_count == 254
    assert result.binary_mask == "11111111.11111111.11111111.00000000"
    assert result.rfc1918
    assert result.reverse_zone == "1.168.192.in-addr.arpa"
    assert result.reverse_pointer == "10.1.168.192.in-addr.arpa"


@pytest.mark.parametrize(
    ("text", "first", "last", "count", "broadcast"),
    [
        ("10.0.0.1/31", "10.0.0.0", "10.0.0.1", 2, None),
        ("10.0.0.5/32", "10.0.0.5", "10.0.0.5", 1, None),
        ("10.0.0.1/30", "10.0.0.1", "10.0.0.2", 2, "10.0.0.3"),
        ("0.0.0.0/0", "0.0.0.1", "255.255.255.254", 2**32 - 2, "255.255.255.255"),
        ("255.255.255.255/32", "255.255.255.255", "255.255.255.255", 1, None),
    ],
)
def test_ipv4_boundary_prefixes_without_host_enumeration(
    text, first, last, count, broadcast
) -> None:
    with patch.object(IPv4Network, "hosts", side_effect=AssertionError("must not enumerate hosts")):
        result = calculate(text)
    assert isinstance(result, IPv4Calculation)
    assert str(result.first_usable) == first
    assert str(result.last_usable) == last
    assert result.usable_count == count
    assert (str(result.broadcast) if result.broadcast is not None else None) == broadcast


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10.0.0.0/8", True),
        ("172.16.0.0/12", True),
        ("192.168.0.0/16", True),
        ("100.64.0.0/10", False),
        ("192.0.2.0/24", False),
        ("127.0.0.0/8", False),
        ("169.254.0.0/16", False),
        ("172.16.0.0/11", False),
        ("0.0.0.0/0", False),
    ],
)
def test_rfc1918_means_entire_network_in_explicit_private_ranges(text, expected) -> None:
    result = calculate(text)
    assert isinstance(result, IPv4Calculation)
    assert result.rfc1918 is expected


@pytest.mark.parametrize(
    ("text", "zone"),
    [
        ("10.1.2.3/8", "10.in-addr.arpa"),
        ("172.16.1.2/16", "16.172.in-addr.arpa"),
        ("192.168.4.1/24", "4.168.192.in-addr.arpa"),
        ("10.0.0.0/20", None),
        ("10.0.0.0/25", None),
        ("10.0.0.1/32", None),
        ("0.0.0.0/0", None),
    ],
)
def test_ipv4_reverse_dns_does_not_invent_a_zone(text, zone) -> None:
    assert calculate(text).reverse_zone == zone


def test_ipv6_forms_host_bits_and_exact_counts() -> None:
    result = calculate("2001:0db8:abcd:1234::beef/56")
    assert isinstance(result, IPv6Calculation)
    assert str(result.address) == "2001:db8:abcd:1234::beef"
    assert result.compressed == "2001:db8:abcd:1200::/56"
    assert result.exploded == "2001:0db8:abcd:1200:0000:0000:0000:0000/56"
    assert result.subnets64 == 256
    assert result.network.num_addresses == 2**72
    assert result.address_kind is IPv6AddressKind.DOCUMENTATION
    assert result.network_kind is IPv6AddressKind.DOCUMENTATION
    assert result.reverse_zone == "2.1.d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("2001:db8::1/64", IPv6AddressKind.DOCUMENTATION),
        ("2001:4860::1/48", IPv6AddressKind.GUA),
        ("fd12:3456::1/48", IPv6AddressKind.ULA),
        ("fc00::/7", IPv6AddressKind.ULA),
        ("fe80::abcd/64", IPv6AddressKind.LINK_LOCAL),
        ("ff02::1/16", IPv6AddressKind.MULTICAST),
        ("::1", IPv6AddressKind.LOOPBACK),
        ("::", IPv6AddressKind.UNSPECIFIED),
        ("100::1/64", IPv6AddressKind.OTHER),
    ],
)
def test_ipv6_calculator_classifies_more_ranges_than_the_planner(text, kind) -> None:
    result = calculate(text)
    assert isinstance(result, IPv6Calculation)
    assert result.address_kind is kind
    assert result.network_kind is kind


@pytest.mark.parametrize("text", ["2001:db8::/16", "2000::/3", "::/0"])
def test_broad_ipv6_block_has_its_own_classification(text: str) -> None:
    result = calculate(text)
    assert isinstance(result, IPv6Calculation)
    assert result.network_kind is IPv6AddressKind.MIXED


@pytest.mark.parametrize(
    ("prefix", "count", "has_zone"),
    [
        (0, 2**64, True),
        (48, 65536, True),
        (56, 256, True),
        (64, 1, True),
        (65, 0, False),
        (127, 0, False),
        (128, 0, True),
    ],
)
def test_ipv6_subnet64_count_and_nibble_alignment(prefix, count, has_zone) -> None:
    with patch.object(IPv6Network, "hosts", side_effect=AssertionError("must not enumerate hosts")):
        result = calculate(f"2001:db8::1/{prefix}")
    assert isinstance(result, IPv6Calculation)
    assert result.subnets64 == count
    assert (result.reverse_zone is not None) is has_zone


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "not-an-ip",
        "192.168.1.1/33",
        "2001:db8::/129",
        "999.1.1.1/24",
        "192.168.1.1 255.0.255.0",
        "192.168.1.1 0.0.5.255",
        "10.0.0.1/24 extra",
        "10.0.0.1 255.255.255.0 extra",
        "fe80::1%eth0/64",
        "1234",
    ],
)
def test_bad_calculator_input_is_a_stable_error(text: str) -> None:
    with pytest.raises(CalculationError) as raised:
        calculate(text)
    assert raised.value.code == "invalid_address"


def test_single_ipv4_address_is_a_host_route() -> None:
    assert calculate("10.0.0.7").network == IPv4Network("10.0.0.7/32")


@pytest.mark.parametrize(
    ("network", "count", "prefix"),
    [
        ("192.168.1.0/24", 4, 26),
        ("10.0.0.0/31", 2, 32),
        ("2001:db8::/48", 65536, 64),
        ("2001:db8::/127", 2, 128),
        ("::1/128", 1, 128),
    ],
)
def test_two_split_modes_agree(network, count, prefix) -> None:
    pool = calculate(network).network
    by_count = preview_subnets(pool, count=count)
    by_prefix = preview_subnets(pool, new_prefix=prefix)
    assert by_count == by_prefix
    assert by_count.total_count == count
    assert len(by_count.subnets) == min(256, count)
    assert by_count.is_truncated is (count > 256)


def test_three_subnets_suggests_four_without_changing_input() -> None:
    with pytest.raises(CalculationError) as raised:
        preview_subnets(IPv4Network("10.0.0.0/24"), count=3)
    assert raised.value.code == "subnet_count_not_power_of_two"
    assert raised.value.suggested_count == 4


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({}, "choose_one_split_mode"),
        ({"count": 2, "new_prefix": 25}, "choose_one_split_mode"),
        ({"count": 0}, "invalid_subnet_count"),
        ({"count": -1}, "invalid_subnet_count"),
        ({"count": True}, "invalid_subnet_count"),
        ({"count": 2.0}, "invalid_subnet_count"),
        ({"count": 512}, "invalid_subnet_prefix"),
        ({"new_prefix": 23}, "invalid_subnet_prefix"),
        ({"new_prefix": 33}, "invalid_subnet_prefix"),
        ({"new_prefix": True}, "invalid_subnet_prefix"),
        ({"new_prefix": 25.0}, "invalid_subnet_prefix"),
        ({"count": 2, "limit": 0}, "invalid_preview_limit"),
        ({"count": 2, "limit": 257}, "invalid_preview_limit"),
        ({"count": 2, "limit": True}, "invalid_preview_limit"),
    ],
)
def test_invalid_split_arguments_are_rejected(kwargs, code) -> None:
    with pytest.raises(CalculationError) as raised:
        preview_subnets(IPv4Network("10.0.0.0/24"), **kwargs)
    assert raised.value.code == code


@pytest.mark.parametrize("version", [4, 6])
def test_largest_possible_split_stays_bounded(version: int) -> None:
    pool = IPv4Network("0.0.0.0/0") if version == 4 else IPv6Network("::/0")
    result = preview_subnets(pool, new_prefix=pool.max_prefixlen, limit=3)
    assert result.total_count == pool.num_addresses
    assert len(result.subnets) == 3
    assert [int(n.network_address) for n in result.subnets] == [0, 1, 2]


@settings(max_examples=80)
@given(st.ip_addresses(v=4), st.integers(0, 32))
def test_ipv4_ranges_cover_the_correct_usable_space(address, prefix) -> None:
    result = calculate(f"{address}/{prefix}")
    assert isinstance(result, IPv4Calculation)
    assert result.network == ip_interface(f"{address}/{prefix}").network
    assert int(result.last_usable) - int(result.first_usable) + 1 == result.usable_count
    assert result.first_usable in result.network and result.last_usable in result.network
    assert result.usable_count == result.network.num_addresses - (2 if prefix < 31 else 0)


@settings(max_examples=80)
@given(st.ip_addresses(v=6), st.integers(0, 128), st.integers(0, 128), st.integers(1, 10))
def test_ipv6_preview_is_ordered_bounded_and_inside_parent(address, first, second, limit) -> None:
    source, target = sorted((first, second))
    pool = ip_interface(f"{address}/{source}").network
    result = preview_subnets(pool, new_prefix=target, limit=limit)
    assert len(result.subnets) == min(result.total_count, limit)
    assert result.total_count == 2 ** (target - source)
    assert all(n.subnet_of(pool) and n.prefixlen == target for n in result.subnets)
    assert all(
        int(b.network_address) - int(a.network_address) == a.num_addresses
        for a, b in zip(result.subnets, result.subnets[1:], strict=False)
    )
