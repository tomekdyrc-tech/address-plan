"""Starting configurations for Cisco IOS and MikroTik RouterOS."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Network
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from adresplan.application.exporting import export_document
from adresplan.application.project_json import load_project
from adresplan.cli import main
from adresplan.core.models import (
    GatewayPosition,
    IPv6GatewayMode,
    IPv6RAMode,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
    SegmentRole,
)
from adresplan.core.plan import build_plan
from adresplan.export.config import dumps_config
from adresplan.web.app import create_app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def church() -> Project:
    return load_project(EXAMPLES / "church-av.json").project


def _reservation(project: Project, name: str):
    node = next(n for n in project.nodes if n.name == name)
    plan = build_plan(project)
    return next(r for r in plan.v4_reservations if r.node_id == node.id)


def test_cisco_creates_vlan_interfaces_dhcp_and_loopbacks(church) -> None:
    config = dumps_config(church, "cisco")
    staff = _reservation(church, "Stanowiska biurowe")
    gateway, dhcp = staff.gateway_addresses[0], staff.dhcp_range
    assert dhcp is not None
    assert "ipv6 unicast-routing" in config
    assert "vlan 70\n name Stanowiska-biurowe\n!\ninterface Vlan70\n" in config
    assert f" ip address {gateway} {staff.network.netmask}\n" in config
    assert f"ip dhcp excluded-address {staff.first_usable} {gateway}\n" in config
    assert f" network {staff.network.network_address} {staff.network.netmask}\n" in config
    assert f" default-router {gateway}\n" in config
    assert "interface Loopback0\n description Loopback routera\n" in config
    assert "! interface <INTERFACE>\n! description Lacze router-biuro\n" in config
    assert "ip dhcp pool VLAN60" not in config  # management networks stay static
    assert config.endswith("!\nend\n")


def test_mikrotik_uses_vlan_interfaces_on_the_bridge(church) -> None:
    config = dumps_config(church, "mikrotik")
    staff = _reservation(church, "Stanowiska biurowe")
    assert staff.dhcp_range is not None
    assert (
        "/interface vlan add name=vlan70-Stanowiska-biurowe vlan-id=70 interface=bridge"
        ' comment="Stanowiska biurowe"' in config
    )
    assert (
        f"/ip pool add name=pool-vlan70-Stanowiska-biurow"
        f" ranges={staff.dhcp_range.first}-{staff.dhcp_range.last}" in config
    )
    assert f"gateway={staff.gateway_addresses[0]}" in config
    assert '/interface bridge add name=lo0 comment="Loopback routera"' in config
    assert "# /ip address add address=10.42.2.32/31 interface=<INTERFACE>" in config


@pytest.mark.parametrize("vendor", ["cisco", "mikrotik"])
def test_user_text_cannot_inject_commands(vendor) -> None:
    hostile = 'Evil" \n/system reset-configuration $x \\\nend'
    project = Project(
        id="p",
        name=hostile,
        v4_pool=IPv4Network("10.0.0.0/24"),
        nodes=(
            Node(id="s", name=hostile, kind=NodeKind.SITE),
            Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="s"),
            Segment(id="lan", name=hostile, parent_id="b", hosts=10, vlan_id=10),
        ),
    )
    config = dumps_config(project, vendor)
    assert config.isascii()
    commands = [line for line in config.splitlines() if not line.startswith(("!", "#"))]
    assert not any(line.lstrip().startswith(("/system", "end")) for line in commands[:-1])
    if vendor == "mikrotik":
        assert 'comment="Evil\\" /system reset-configuration \\$x \\\\ end"' in config
    else:
        assert ' description Evil" /system reset-configuration $x \\ end\n' in config


def test_incomplete_plan_is_marked_and_skipped_segments_listed() -> None:
    project = load_project(EXAMPLES / "t3-no-space.json").project
    config = dumps_config(project, "cisco")
    assert "PLAN NIEKOMPLETNY" in config
    assert "brak przydzialu IPv4 - pominieto." in config


def test_link_local_gateway_and_dhcpv6() -> None:
    settings = ProjectSettings(
        v6_gateway_mode=IPv6GatewayMode.LINK_LOCAL, v6_ra_mode=IPv6RAMode.DHCPV6
    )
    project = Project(
        id="p",
        name="P",
        v4_pool=IPv4Network("10.0.0.0/24"),
        v6_prefix=IPv6Network("2001:db8::/48"),
        settings=settings,
        nodes=(
            Node(id="s", name="S", kind=NodeKind.SITE),
            Node(id="b", name="B", kind=NodeKind.BUILDING, parent_id="s"),
            Segment(id="lan", name="LAN", parent_id="b", hosts=10, vlan_id=10),
            Segment(id="lo", name="Lo", parent_id="b", role=SegmentRole.LOOPBACK),
        ),
    )
    cisco = dumps_config(project, "cisco")
    assert " ipv6 address fe80::1 link-local\n" in cisco
    assert " ipv6 nd managed-config-flag\n" in cisco
    mikrotik = dumps_config(project, "mikrotik")
    assert "/ipv6 nd add interface=vlan10-LAN managed-address-configuration=yes" in mikrotik
    assert "/ipv6 address add address=fe80::1/64 interface=vlan10-LAN" in mikrotik
    no_gateway = replace(
        project, settings=replace(settings, gateway=GatewayPosition.NONE, gateway_addrs=0)
    )
    config = dumps_config(no_gateway, "cisco")
    assert config.count("interface Vlan10") == 1
    assert "Plan nie przewiduje bramy w tej podsieci." in config
    assert "ip dhcp pool" not in config


def test_config_is_available_from_cli_and_web(tmp_path, capsys) -> None:
    source = EXAMPLES / "church-av.json"
    assert main(["export", str(source), "-f", "mikrotik"]) == 0
    assert capsys.readouterr().out == export_document(load_project(source).project, "mikrotik")
    app = create_app(tmp_path / "web.sqlite3")
    with TestClient(app, base_url="http://localhost") as client:
        token = client.get("/api/session").json()["csrf_token"]
        client.headers["X-CSRF-Token"] = token
        response = client.post(
            "/projects/import",
            files={"file": ("input.json", source.read_bytes())},
            follow_redirects=False,
        )
        key = response.headers["location"].rsplit("/", 1)[1]
        download = client.get(f"/api/projects/{key}/export.cisco")
        assert download.headers["content-type"].startswith("text/plain")
        assert f'address-plan-{key}-cisco-ios.txt"' in download.headers["content-disposition"]
        assert "interface Vlan10" in download.text
        preview = client.get(f"/p/{key}/export?format=mikrotik").text
        assert "MikroTik" in preview and "/interface vlan add" in preview
