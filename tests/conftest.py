"""Reproducible property checks without persistent local state."""

from ipaddress import IPv4Network, IPv6Network

import pytest
from hypothesis import settings

from adresplan.core.models import (
    GatewayPosition,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
    SegmentRole,
)

settings.register_profile(
    "adresplan", max_examples=200, derandomize=True, database=None, deadline=None
)
settings.load_profile("adresplan")


@pytest.fixture
def t4_project() -> Project:
    nodes: list[Node] = [
        Node(
            id="site", name="Lokalizacja", kind=NodeKind.SITE, pinned_v4=IPv4Network("10.20.0.0/20")
        ),
        *(
            Node(
                id=b,
                name=f"Budynek {b.upper()}",
                kind=NodeKind.BUILDING,
                parent_id="site",
                sort_order=i,
            )
            for i, b in enumerate(["a", "b", "c"])
        ),
    ]
    entries = [
        ("a", "wifi", 200, SegmentRole.LAN),
        ("a", "office", 60, SegmentRole.LAN),
        ("a", "voip", 45, SegmentRole.LAN),
        ("a", "training", 28, SegmentRole.LAN),
        ("a", "cameras", 20, SegmentRole.LAN),
        ("a", "servers", 12, SegmentRole.LAN),
        ("a", "mgmt", 10, SegmentRole.MGMT),
        ("a", "link1", 0, SegmentRole.P2P),
        ("a", "link2", 0, SegmentRole.P2P),
        ("a", "loop", 0, SegmentRole.LOOPBACK),
        ("b", "hall", 100, SegmentRole.LAN),
        ("b", "office", 40, SegmentRole.LAN),
        ("b", "av", 20, SegmentRole.LAN),
        ("c", "residence", 30, SegmentRole.LAN),
    ]
    nodes.extend(
        Segment(id=f"{b}_{name}", name=name, parent_id=b, hosts=hosts, role=role, sort_order=i)
        for i, (b, name, hosts, role) in enumerate(entries)
    )
    return Project(
        id="t4",
        name="T4",
        v4_pool=IPv4Network("10.20.0.0/20"),
        nodes=tuple(nodes),
        settings=ProjectSettings(growth_pct=0, gateway=GatewayPosition.NONE, gateway_addrs=0),
    )


@pytest.fixture
def t5_project() -> Project:
    nodes: list[Node] = [Node(id="site", name="Site", kind=NodeKind.SITE)]
    for order, building in enumerate(["a", "b", "c"]):
        nodes.append(
            Node(
                id=building,
                name=building,
                kind=NodeKind.BUILDING,
                parent_id="site",
                sort_order=order,
            )
        )
        nodes.extend(
            Segment(id=f"{building}{i}", name=f"LAN{i}", parent_id=building, hosts=10, sort_order=i)
            for i in range(7)
        )
    nodes.extend(
        [
            Segment(id="link0", name="Link0", parent_id="a", role=SegmentRole.P2P, sort_order=10),
            Segment(id="link1", name="Link1", parent_id="a", role=SegmentRole.P2P, sort_order=11),
            Segment(
                id="loop", name="Loop", parent_id="a", role=SegmentRole.LOOPBACK, sort_order=12
            ),
        ]
    )
    return Project(
        id="t5",
        name="T5",
        v4_pool=IPv4Network("10.0.0.0/16"),
        nodes=tuple(nodes),
        v6_prefix=IPv6Network("2001:db8:abcd::/48"),
    )
