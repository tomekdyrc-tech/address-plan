"""Exact flat-allocation reference vectors T1-T3 from the source specification."""

from ipaddress import IPv4Network

from adresplan.core.allocator import allocate
from adresplan.core.models import (
    AllocationRequest,
    GatewayPosition,
    ProjectSettings,
    Segment,
    SegmentRole,
)
from adresplan.core.sizing import size_segment_v4


def request(
    name: str, hosts: int, order: int, role: SegmentRole = SegmentRole.LAN
) -> AllocationRequest[IPv4Network]:
    segment = Segment(
        id=name,
        name=name,
        hosts=hosts,
        role=role,
        growth_pct=0,
        gateway=GatewayPosition.NONE,
        gateway_addrs=0,
    )
    size = size_segment_v4(segment, ProjectSettings())
    return AllocationRequest(node_id=name, name=name, prefix=size.prefix, sort_order=order)


def test_t1_basic_vlsm() -> None:
    result = allocate(
        IPv4Network("192.168.10.0/24"),
        [
            request(name, hosts, order)
            for order, (name, hosts) in enumerate([("A", 100), ("B", 50), ("C", 25), ("D", 10)])
        ],
    )
    assert result.is_complete
    assert [(a.node_id, str(a.network)) for a in result.allocations] == [
        ("A", "192.168.10.0/25"),
        ("B", "192.168.10.128/26"),
        ("C", "192.168.10.192/27"),
        ("D", "192.168.10.224/28"),
    ]
    assert [str(n) for n in result.free_blocks] == ["192.168.10.240/28"]
    assert [(str(a.network[1]), str(a.network[-2])) for a in result.allocations] == [
        ("192.168.10.1", "192.168.10.126"),
        ("192.168.10.129", "192.168.10.190"),
        ("192.168.10.193", "192.168.10.222"),
        ("192.168.10.225", "192.168.10.238"),
    ]


def test_t2_building_flat_segments() -> None:
    entries = [
        ("WiFi-goscie", 200, SegmentRole.LAN),
        ("Biuro", 60, SegmentRole.LAN),
        ("VoIP", 45, SegmentRole.LAN),
        ("Szkolenia", 28, SegmentRole.LAN),
        ("Kamery", 20, SegmentRole.LAN),
        ("Serwery", 12, SegmentRole.LAN),
        ("Zarzadzanie", 10, SegmentRole.MGMT),
        ("Link-R1-SW1", 0, SegmentRole.P2P),
        ("Link-R1-SW2", 0, SegmentRole.P2P),
        ("Loopback-R1", 0, SegmentRole.LOOPBACK),
    ]
    pool = IPv4Network("10.20.0.0/22")
    result = allocate(pool, [request(n, h, i, r) for i, (n, h, r) in enumerate(entries)])
    assert result.is_complete
    assert [str(a.network) for a in result.allocations] == [
        "10.20.0.0/24",
        "10.20.1.0/26",
        "10.20.1.64/26",
        "10.20.1.128/27",
        "10.20.1.160/27",
        "10.20.1.192/28",
        "10.20.1.208/28",
        "10.20.1.224/31",
        "10.20.1.226/31",
        "10.20.1.228/32",
    ]
    assert [str(n) for n in result.free_blocks] == [
        "10.20.1.229/32",
        "10.20.1.230/31",
        "10.20.1.232/29",
        "10.20.1.240/28",
        "10.20.2.0/23",
    ]
    assert sum(a.network.num_addresses for a in result.allocations) == 485
    assert sum(n.num_addresses for n in result.free_blocks) == pool.num_addresses - 485 == 539


def test_t3_no_space_is_a_finding_with_a_useful_suggestion() -> None:
    result = allocate(
        IPv4Network("192.168.1.0/26"),
        [request("X", 30, 0), request("Y", 30, 1), request("Z", 10, 2)],
    )
    assert not result.is_complete
    assert [(a.node_id, str(a.network)) for a in result.allocations] == [
        ("X", "192.168.1.0/27"),
        ("Y", "192.168.1.32/27"),
    ]
    assert result.free_blocks == ()
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert (finding.code, finding.node_id) == ("insufficient_space", "Z")
    assert dict(finding.details) == {
        "requested_prefix": 28,
        "free_addresses": 0,
        "largest_free_prefix": None,
        "required_addresses": 80,
        "capacity_lower_bound_prefix": 25,
        "suggested_pool_prefix": 25,
    }
