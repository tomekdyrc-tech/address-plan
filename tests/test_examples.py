"""The shipped JSON projects reproduce the specification reference vectors."""

from pathlib import Path

import pytest

from adresplan.application.project_json import load_project

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize(
    ("name", "complete"),
    [
        ("t1-vlsm.json", True),
        ("t2-building.json", True),
        ("t3-no-space.json", False),
        ("budynek.json", True),
        ("t5-ipv6.json", True),
        ("t5-vlan-hex.json", True),
        ("t5-vlan-110-error.json", False),
        ("church-av.json", True),
    ],
)
def test_example_status_is_intentional(name: str, complete: bool) -> None:
    assert load_project(EXAMPLES / name).plan.is_complete is complete


def test_t1_t2_t3_addresses_and_free_space() -> None:
    t1 = load_project(EXAMPLES / "t1-vlsm.json").plan
    addresses = {a.node_id: str(a.network) for a in t1.v4_allocations}
    assert [addresses[id] for id in ("A", "B", "C", "D")] == [
        "192.168.10.0/25",
        "192.168.10.128/26",
        "192.168.10.192/27",
        "192.168.10.224/28",
    ]
    assert [str(b.network) for b in t1.free_blocks if b.parent_id == "building"] == [
        "192.168.10.240/28"
    ]
    t2 = load_project(EXAMPLES / "t2-building.json").plan
    addresses = {a.node_id: str(a.network) for a in t2.v4_allocations}
    assert [addresses[f"a-{i}"] for i in range(10)] == [
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
    assert sum(b.network.num_addresses for b in t2.free_blocks if b.parent_id == "a") == 539
    t3 = load_project(EXAMPLES / "t3-no-space.json").plan
    addresses = {a.node_id: str(a.network) for a in t3.v4_allocations}
    assert addresses["X"] == "192.168.1.0/27" and addresses["Y"] == "192.168.1.32/27"
    assert "Z" not in addresses
    assert any(
        f.code == "insufficient_space" and dict(f.details)["suggested_pool_prefix"] == 25
        for f in t3.findings
    )


def test_t4_t5_and_vlan_hex_reference_addresses() -> None:
    t4 = load_project(EXAMPLES / "budynek.json").plan
    addresses = {a.node_id: str(a.network) for a in t4.v4_allocations}
    assert [addresses[id] for id in ("a", "b", "c")] == [
        "10.20.0.0/23",
        "10.20.2.0/24",
        "10.20.3.0/27",
    ]
    t5 = load_project(EXAMPLES / "t5-ipv6.json").plan
    addresses = {a.node_id: str(a.network) for a in t5.v6_allocations}
    assert [addresses[id] for id in ("a", "b", "c")] == [
        "2001:db8:abcd:100::/56",
        "2001:db8:abcd:200::/56",
        "2001:db8:abcd:300::/56",
    ]
    assert addresses["link0"] == "2001:db8:abcd:1::/127"
    assert addresses["loop"] == "2001:db8:abcd:2::/128"
    hex5 = load_project(EXAMPLES / "t5-vlan-hex.json").plan
    addresses = {a.node_id: str(a.network) for a in hex5.v6_allocations}
    assert [addresses[id] for id in ("a0", "a1", "a2")] == [
        "2001:db8:abcd:110::/64",
        "2001:db8:abcd:120::/64",
        "2001:db8:abcd:199::/64",
    ]
    bad = load_project(EXAMPLES / "t5-vlan-110-error.json").plan
    assert any(f.code == "v6_vlan_offset_outside_building" for f in bad.findings)
