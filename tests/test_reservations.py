"""Range boundaries, redundancy, infrastructure and large-address-space behavior."""

from fractions import Fraction
from ipaddress import IPv4Address, IPv4Network
from itertools import combinations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from adresplan.core.models import GatewayPosition, ProjectSettings, Segment, SegmentRole
from adresplan.core.reservations import reserve_segment_v4


def segment(**options) -> Segment:
    return Segment(id="s", name="S", hosts=10, growth_pct=0, **options)


def test_specification_first_gateway_and_eight_static_addresses() -> None:
    result = reserve_segment_v4(
        segment(static_count=8), ProjectSettings(), IPv4Network("10.20.1.0/26")
    )
    assert result.gateway_addresses == (IPv4Address("10.20.1.1"),)
    assert (str(result.static_range.first), str(result.static_range.last)) == (
        "10.20.1.2",
        "10.20.1.9",
    )
    assert (str(result.dhcp_range.first), str(result.dhcp_range.last)) == (
        "10.20.1.10",
        "10.20.1.62",
    )
    assert result.static_range.count == 8 and result.dhcp_range.count == 53
    assert result.usable_capacity == 62 and result.usable_needed == 19
    assert result.utilization == Fraction(19, 62)


@pytest.mark.parametrize("count", [1, 2, 3])
@pytest.mark.parametrize("position", [GatewayPosition.FIRST, GatewayPosition.LAST])
def test_multiple_gateways_and_static_ranges(position: GatewayPosition, count: int) -> None:
    result = reserve_segment_v4(
        segment(gateway=position, gateway_addrs=count, static_count=8),
        ProjectSettings(),
        IPv4Network("10.20.1.0/26"),
    )
    if position is GatewayPosition.FIRST:
        assert [int(a) % 256 for a in result.gateway_addresses] == list(range(1, count + 1))
        assert int(result.static_range.first) % 256 == 1 + count
        assert int(result.dhcp_range.last) % 256 == 62
    else:
        assert [int(a) % 256 for a in result.gateway_addresses] == list(range(62, 62 - count, -1))
        assert int(result.static_range.first) % 256 == 1
        assert int(result.static_range.last) % 256 == 8
        assert int(result.dhcp_range.first) % 256 == 9
        assert int(result.dhcp_range.last) % 256 == 62 - count


def test_no_gateway_uses_bottom_static_range() -> None:
    result = reserve_segment_v4(
        segment(gateway=GatewayPosition.NONE, static_count=8),
        ProjectSettings(),
        IPv4Network("10.20.1.0/26"),
    )
    assert result.gateway_addresses == ()
    assert str(result.static_range.first) == "10.20.1.1"
    assert str(result.dhcp_range.first) == "10.20.1.9"


def test_zero_static_count_is_absent() -> None:
    result = reserve_segment_v4(segment(), ProjectSettings(), IPv4Network("10.0.0.0/28"))
    assert result.static_range is None
    assert result.dhcp_range.count == 13


def test_empty_dhcp_is_absent_instead_of_reversed_range() -> None:
    data = Segment(id="s", name="S", hosts=0, static_count=1, growth_pct=0)
    result = reserve_segment_v4(data, ProjectSettings(), IPv4Network("10.0.0.0/30"))
    assert result.gateway_addresses == (IPv4Address("10.0.0.1"),)
    assert result.static_range.count == 1 and result.dhcp_range is None


@pytest.mark.parametrize(
    ("role", "prefix", "first", "last"),
    [
        (SegmentRole.P2P, 31, "10.0.0.0", "10.0.0.1"),
        (SegmentRole.P2P, 30, "10.0.0.1", "10.0.0.2"),
        (SegmentRole.LOOPBACK, 32, "10.0.0.0", "10.0.0.0"),
    ],
)
def test_infrastructure_ranges_have_no_gateway_or_dhcp(role, prefix, first, last) -> None:
    result = reserve_segment_v4(
        Segment(id="s", name="S", role=role), ProjectSettings(), IPv4Network(f"10.0.0.0/{prefix}")
    )
    assert str(result.first_usable) == first and str(result.last_usable) == last
    assert (
        result.gateway_addresses == () and result.static_range is None and result.dhcp_range is None
    )


@pytest.mark.parametrize(("role", "prefix"), [(SegmentRole.P2P, 29), (SegmentRole.LOOPBACK, 31)])
def test_larger_infrastructure_pins_are_not_silently_treated_as_lan(role, prefix) -> None:
    with pytest.raises(ValueError):
        reserve_segment_v4(
            Segment(id="s", name="S", role=role),
            ProjectSettings(),
            IPv4Network(f"10.0.0.0/{prefix}"),
        )


def test_too_small_lan_is_rejected() -> None:
    with pytest.raises(ValueError):
        reserve_segment_v4(segment(), ProjectSettings(), IPv4Network("10.0.0.0/30"))


def test_large_pool_does_not_enumerate_hosts(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("do not enumerate hosts")

    monkeypatch.setattr(IPv4Network, "hosts", forbidden)
    result = reserve_segment_v4(
        segment(static_count=8), ProjectSettings(), IPv4Network("10.0.0.0/8")
    )
    assert str(result.dhcp_range.last) == "10.255.255.254"
    assert result.dhcp_range.count == 2**24 - 11


@given(
    position=st.sampled_from(list(GatewayPosition)),
    count=st.integers(1, 3),
    static=st.integers(0, 20),
)
def test_gateway_static_and_dhcp_partition_the_usable_range(position, count, static) -> None:
    count = 0 if position is GatewayPosition.NONE else count
    result = reserve_segment_v4(
        segment(gateway=position, gateway_addrs=count, static_count=static),
        ProjectSettings(),
        IPv4Network("10.0.0.0/26"),
    )
    intervals = [(int(a), int(a)) for a in result.gateway_addresses]
    intervals.extend(
        (int(r.first), int(r.last)) for r in [result.static_range, result.dhcp_range] if r
    )
    assert all(b < c or d < a for (a, b), (c, d) in combinations(intervals, 2))
    assert sum(b - a + 1 for a, b in intervals) == result.usable_capacity
    assert min(a for a, b in intervals) == int(result.first_usable)
    assert max(b for a, b in intervals) == int(result.last_usable)
