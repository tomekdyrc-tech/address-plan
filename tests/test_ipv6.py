"""IPv6 arithmetic, ULA generation and reverse-DNS boundaries."""

from ipaddress import IPv6Address, IPv6Network

import pytest
from hypothesis import given
from hypothesis import strategies as st

from adresplan.application.ula import generate_ula
from adresplan.core.ipv6 import (
    building_prefix,
    classify_prefix,
    count_subnets64,
    reverse_zone,
    subnet64_at,
    ula_from_global_id,
)
from adresplan.core.models import IPv6Kind


@pytest.mark.parametrize(
    ("prefix", "count"), [(48, 65536), (56, 256), (60, 16), (64, 1), (127, 0), (128, 0)]
)
def test_count_subnets_without_iterating(prefix, count) -> None:
    assert count_subnets64(IPv6Network((0, prefix))) == count


def test_reverse_zone_matches_the_specification() -> None:
    assert (
        reverse_zone(IPv6Network("2001:db8:abcd:120::/64"))
        == "0.2.1.0.d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa"
    )
    assert reverse_zone(IPv6Network("2001:db8:abcd::/48")) == "d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa"
    assert reverse_zone(IPv6Network("::/0")) == "ip6.arpa"


@pytest.mark.parametrize("prefix", [49, 55, 63, 127])
def test_reverse_zone_rejects_non_nibble_delegations(prefix) -> None:
    with pytest.raises(ValueError):
        reverse_zone(IPv6Network((0, prefix)))


@pytest.mark.parametrize(
    ("network", "kind"),
    [
        ("2001:db8:abcd::/48", IPv6Kind.DOCUMENTATION),
        ("fd12:3456:789a::/48", IPv6Kind.ULA),
        ("2001:1234::/48", IPv6Kind.GUA),
    ],
)
def test_prefix_classification_checks_documentation_before_gua(network, kind) -> None:
    assert classify_prefix(IPv6Network(network)) is kind


@pytest.mark.parametrize("network", ["fe80::/64", "ff00::/8", "::/128", "::1/128", "fc00::/8"])
def test_unsupported_project_prefix_types(network) -> None:
    with pytest.raises(ValueError):
        classify_prefix(IPv6Network(network))


@pytest.mark.parametrize(
    ("count", "minimum", "growth", "prefix"),
    [
        (7, 56, 100, 56),
        (7, 60, 100, 60),
        (9, 60, 100, 56),
        (128, 56, 100, 56),
        (129, 56, 100, 52),
        (1, 52, 100, 52),
        (0, 60, 0, 60),
        (4096, 52, 0, 52),
    ],
)
def test_building_capacity_uses_growth_and_minimum_block_size(
    count, minimum, growth, prefix
) -> None:
    assert building_prefix(count, minimum, growth) == prefix


@pytest.mark.parametrize(
    ("count", "minimum", "growth"),
    [(-1, 56, 0), (1, 64, 0), (1, True, 0), (1, 56, -1), (4097, 52, 0), (1, 56.0, 0)],
)
def test_invalid_building_sizes(count, minimum, growth) -> None:
    with pytest.raises(ValueError):
        building_prefix(count, minimum, growth)


def test_subnet_offset_handles_more_than_eight_bits() -> None:
    assert subnet64_at(IPv6Network("2001:db8:abcd:100::/56"), 0x20) == IPv6Network(
        "2001:db8:abcd:120::/64"
    )
    assert subnet64_at(IPv6Network("2001:db8:abcd:1000::/52"), 0x110) == IPv6Network(
        "2001:db8:abcd:1110::/64"
    )


@pytest.mark.parametrize("offset", [-1, 256, True, 1.5])
def test_subnet_offset_rejects_outside_or_non_integer_input(offset) -> None:
    with pytest.raises(ValueError):
        subnet64_at(IPv6Network("2001:db8::/56"), offset)


def test_ula_matches_fd_plus_exactly_forty_random_bits(monkeypatch) -> None:
    calls = []

    def fixed_bytes(length):
        calls.append(length)
        return bytes.fromhex("123456789a")

    monkeypatch.setattr("adresplan.application.ula.secrets.token_bytes", fixed_bytes)
    assert generate_ula() == IPv6Network("fd12:3456:789a::/48")
    assert calls == [5]
    assert ula_from_global_id(bytes(5)) == IPv6Network("fd00::/48")


@pytest.mark.parametrize("value", [b"", bytes(4), bytes(6), "12345", 12345])
def test_invalid_global_id_length_or_type(value) -> None:
    with pytest.raises(ValueError):
        ula_from_global_id(value)


@given(st.binary(min_size=5, max_size=5))
def test_ula_preserves_the_global_id_without_host_bits(value) -> None:
    network = ula_from_global_id(value)
    assert network.prefixlen == 48 and network.network_address.packed[:6] == b"\xfd" + value
    assert network.network_address.packed[6:] == bytes(10)
    assert network.subnet_of(IPv6Network("fd00::/8"))


@given(st.integers(0, 255))
def test_subnet_offset_stays_aligned_and_inside_parent(offset) -> None:
    pool = IPv6Network("2001:db8:abcd:100::/56")
    child = subnet64_at(pool, offset)
    assert child.prefixlen == 64 and child.subnet_of(pool)
    assert int(child.network_address) - int(pool.network_address) == offset * 2**64
    assert IPv6Address(child.network_address.packed) == child.network_address
