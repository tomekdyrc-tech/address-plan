"""Boundary and role-specific capacity tests."""

from ipaddress import IPv4Network

import pytest
from hypothesis import given
from hypothesis import strategies as st

from adresplan.core.models import GatewayPosition, ProjectSettings, Segment, SegmentRole
from adresplan.core.sizing import grown_host_count, next_pow2, prefix_for_usable, size_segment_v4


@pytest.mark.parametrize(
    ("needed", "prefix"),
    [
        (1, 30),
        (2, 30),
        (3, 29),
        (6, 29),
        (7, 28),
        (14, 28),
        (15, 27),
        (30, 27),
        (31, 26),
        (62, 26),
        (63, 25),
        (126, 25),
        (127, 24),
        (254, 24),
        (255, 23),
        (510, 23),
        (2**32 - 2, 0),
    ],
)
def test_lan_prefix_boundaries(needed: int, prefix: int) -> None:
    assert prefix_for_usable(needed) == prefix


@pytest.mark.parametrize("needed", [0, -1, 2**32 - 1, True, 1.5])
def test_invalid_lan_capacity(needed: int) -> None:
    with pytest.raises(ValueError):
        prefix_for_usable(needed)


@pytest.mark.parametrize(("value", "expected"), [(0, 1), (1, 1), (2, 2), (3, 4), (485, 512)])
def test_next_power_of_two(value: int, expected: int) -> None:
    assert next_pow2(value) == expected


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_next_power_rejects_invalid_input(value: int) -> None:
    with pytest.raises(ValueError):
        next_pow2(value)


@pytest.mark.parametrize(
    ("hosts", "growth", "expected"),
    [(0, 25, 0), (1, 25, 2), (100, 25, 125), (101, 25, 127), (2**60 + 1, 100, 2**61 + 2)],
)
def test_growth_rounding_is_exact(hosts: int, growth: int, expected: int) -> None:
    assert grown_host_count(hosts, growth) == expected


@pytest.mark.parametrize(("hosts", "growth"), [(-1, 0), (1, -1), (True, 0), (1, 0.1)])
def test_growth_rejects_invalid_input(hosts: int, growth: int) -> None:
    with pytest.raises(ValueError):
        grown_host_count(hosts, growth)


def test_lan_inherits_defaults_and_adds_reservations() -> None:
    segment = Segment(id="av", name="AV", hosts=100, static_count=8)
    result = size_segment_v4(segment, ProjectSettings())
    assert result.usable_needed == 125 + 1 + 8
    assert result.prefix == 24


def test_segment_overrides_growth_and_disables_gateway() -> None:
    segment = Segment(id="av", name="AV", hosts=100, growth_pct=0, gateway=GatewayPosition.NONE)
    result = size_segment_v4(segment, ProjectSettings())
    assert result.usable_needed == 100
    assert result.prefix == 25


def test_management_uses_lan_capacity_rules() -> None:
    segment = Segment(id="mgmt", name="Mgmt", role=SegmentRole.MGMT, hosts=6, growth_pct=0)
    assert size_segment_v4(segment, ProjectSettings()).prefix == 28


@pytest.mark.parametrize("gateways", [1, 2, 3])
def test_explicit_gateway_counts(gateways: int) -> None:
    segment = Segment(id="s", name="S", hosts=30, growth_pct=0, gateway_addrs=gateways)
    assert size_segment_v4(segment, ProjectSettings()).usable_needed == 30 + gateways


@pytest.mark.parametrize(
    "segment",
    [
        Segment(id="s", name="S", hosts=-1),
        Segment(id="s", name="S", hosts=1, static_count=-1),
        Segment(id="s", name="S", hosts=1, growth_pct=-1),
        Segment(id="s", name="S", hosts=1, gateway_addrs=-1),
        Segment(id="s", name="S", hosts=1, gateway_addrs=0),
        Segment(id="s", name="S", hosts=1, gateway_addrs=4),
        Segment(id="s", name="S", gateway=GatewayPosition.NONE, gateway_addrs=1),
        Segment(id="s", name="S", gateway=GatewayPosition.NONE),
    ],
)
def test_invalid_segment_requirements(segment: Segment) -> None:
    with pytest.raises(ValueError):
        size_segment_v4(segment, ProjectSettings())


@pytest.mark.parametrize(
    ("role", "prefix", "needed"), [(SegmentRole.P2P, 31, 2), (SegmentRole.LOOPBACK, 32, 1)]
)
def test_infrastructure_does_not_inherit_lan_growth_or_gateway(
    role: SegmentRole, prefix: int, needed: int
) -> None:
    result = size_segment_v4(Segment(id="r", name="R", role=role), ProjectSettings())
    assert (result.prefix, result.usable_needed) == (prefix, needed)


def test_legacy_p2p_uses_slash_30() -> None:
    segment = Segment(id="r", name="R", role=SegmentRole.P2P, hosts=2)
    assert size_segment_v4(segment, ProjectSettings(p2p_prefix=30)).prefix == 30


@pytest.mark.parametrize("role", [SegmentRole.P2P, SegmentRole.LOOPBACK])
@pytest.mark.parametrize(
    "options",
    [
        {"hosts": 3},
        {"static_count": 1},
        {"gateway_addrs": 1},
        {"gateway": GatewayPosition.FIRST},
        {"growth_pct": 25},
    ],
)
def test_infrastructure_rejects_incompatible_options(role: SegmentRole, options: dict) -> None:
    segment = Segment(id="r", name="R", role=role, **options)
    with pytest.raises(ValueError):
        size_segment_v4(segment, ProjectSettings())


def test_invalid_legacy_p2p_prefix() -> None:
    with pytest.raises(ValueError):
        size_segment_v4(
            Segment(id="r", name="R", role=SegmentRole.P2P), ProjectSettings(p2p_prefix=29)
        )


def test_raw_enum_strings_cannot_silently_bypass_role_or_gateway_rules() -> None:
    for options in [
        {"role": "lan"},
        {"role": "p2p"},
        {"gateway": "first"},
        {"gateway": "last"},
        {"gateway": "none"},
    ]:
        with pytest.raises(ValueError):
            size_segment_v4(Segment(id="s", name="S", hosts=1, **options), ProjectSettings())


@given(st.integers(min_value=1, max_value=2**32 - 2))
def test_lan_is_large_enough_and_minimal(needed: int) -> None:
    prefix = prefix_for_usable(needed)
    network = IPv4Network((0, prefix))
    assert network.num_addresses - 2 >= needed
    if prefix < 30:
        assert network.num_addresses // 2 - 2 < needed


@given(st.integers(min_value=0, max_value=2**80), st.integers(min_value=0, max_value=1000))
def test_growth_is_the_integer_ceiling(hosts: int, growth: int) -> None:
    needed = grown_host_count(hosts, growth)
    numerator = hosts * (100 + growth)
    assert needed * 100 >= numerator
    assert (needed - 1) * 100 < numerator
