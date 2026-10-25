"""Immutable input and output records shared by all application boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Generic, TypeAlias, TypeVar

Network: TypeAlias = IPv4Network | IPv6Network
NetworkT = TypeVar("NetworkT", IPv4Network, IPv6Network)
DetailValue: TypeAlias = str | int | None


class NodeKind(StrEnum):
    SITE = "site"
    BUILDING = "building"
    SEGMENT = "segment"


class SegmentRole(StrEnum):
    LAN = "lan"
    MGMT = "mgmt"
    P2P = "p2p"
    LOOPBACK = "loopback"


class GatewayPosition(StrEnum):
    FIRST = "first"
    LAST = "last"
    NONE = "none"


class FindingLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IPv6Kind(StrEnum):
    GUA = "gua"
    ULA = "ula"
    DOCUMENTATION = "doc"


class IPv6SubnetStrategy(StrEnum):
    SEQUENTIAL = "sequential"
    VLAN_DECIMAL_AS_HEX = "vlan_decimal_as_hex"


class IPv6GatewayMode(StrEnum):
    GLOBAL = "global"
    LINK_LOCAL = "link_local"


class IPv6RAMode(StrEnum):
    SLAAC = "slaac"
    DHCPV6 = "dhcpv6"


class IPv6PoolKind(StrEnum):
    PROJECT = "project"
    SITE = "site"
    BUILDING = "building"
    INFRASTRUCTURE = "infrastructure"
    P2P = "p2p"
    LOOPBACK = "loopback"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSettings:
    growth_pct: int = 25
    gateway: GatewayPosition = GatewayPosition.FIRST
    gateway_addrs: int = 1
    p2p_prefix: int = 31
    v6_site_prefix: int = 48
    v6_building_prefix: int = 56
    v6_infra_prefix: int = 56
    v6_growth_pct: int = 100
    v6_subnet_strategy: IPv6SubnetStrategy = IPv6SubnetStrategy.SEQUENTIAL
    v6_gateway_mode: IPv6GatewayMode = IPv6GatewayMode.GLOBAL
    v6_link_local_gateway: IPv6Address = IPv6Address("fe80::1")
    v6_ra_mode: IPv6RAMode = IPv6RAMode.SLAAC


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    """A tree node with an externally assigned, persistent ID (never a generated UUID)."""

    id: str
    name: str
    kind: NodeKind
    parent_id: str | None = None
    sort_order: int = 0
    pinned_v4: IPv4Network | None = None
    pinned_v6: IPv6Network | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class Segment(Node):
    kind: NodeKind = field(default=NodeKind.SEGMENT, init=False)
    role: SegmentRole = SegmentRole.LAN
    hosts: int = 0
    growth_pct: int | None = None
    gateway: GatewayPosition | None = None
    gateway_addrs: int | None = None
    static_count: int = 0
    vlan_id: int | None = None
    v6_enabled: bool = True
    ra_mode: IPv6RAMode | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class IPv6Infrastructure:
    site_id: str
    network: IPv6Network
    reserved_pool: IPv6Network
    p2p_pool: IPv6Network
    loopback_pool: IPv6Network


@dataclass(frozen=True, slots=True, kw_only=True)
class BlockedSubnet:
    network: Network
    parent_id: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class Project:
    id: str
    name: str
    author: str = ""
    organization: str = ""
    description: str = ""
    document_date: str = ""
    v4_pool: IPv4Network
    nodes: tuple[Node, ...] = ()
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    v6_prefix: IPv6Network | None = None
    v6_active: bool = True
    v6_kind: IPv6Kind = IPv6Kind.DOCUMENTATION
    pinned_v6_infrastructure: tuple[IPv6Infrastructure, ...] = ()
    blocked_subnets: tuple[BlockedSubnet, ...] = ()

    @property
    def uses_ipv6(self) -> bool:
        return self.v6_active and self.v6_prefix is not None

    @property
    def active_blocked_subnets(self) -> tuple[BlockedSubnet, ...]:
        return tuple(b for b in self.blocked_subnets if b.network.version == 4 or self.uses_ipv6)


@dataclass(frozen=True, slots=True, kw_only=True)
class Finding:
    """A language-independent finding; presentation layers translate its code."""

    code: str
    level: FindingLevel = FindingLevel.ERROR
    node_id: str | None = None
    details: tuple[tuple[str, DetailValue], ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class SegmentSize:
    prefix: int
    usable_needed: int


@dataclass(frozen=True, kw_only=True)
class AllocationRequest(Generic[NetworkT]):
    node_id: str
    name: str
    prefix: int
    sort_order: int = 0
    pinned: NetworkT | None = None


@dataclass(frozen=True, kw_only=True)
class Allocation(Generic[NetworkT]):
    node_id: str
    network: NetworkT


@dataclass(frozen=True, kw_only=True)
class AllocationResult(Generic[NetworkT]):
    allocations: tuple[Allocation[NetworkT], ...]
    free_blocks: tuple[NetworkT, ...]
    findings: tuple[Finding, ...] = ()

    @property
    def is_complete(self) -> bool:
        return not any(f.level is FindingLevel.ERROR for f in self.findings)


@dataclass(frozen=True, slots=True, kw_only=True)
class FreeBlock:
    parent_id: str | None
    network: Network
    pool_kind: IPv6PoolKind | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AddressRange:
    first: IPv4Address
    last: IPv4Address

    @property
    def count(self) -> int:
        return int(self.last) - int(self.first) + 1


@dataclass(frozen=True, slots=True, kw_only=True)
class SegmentReservations:
    node_id: str
    network: IPv4Network
    usable_needed: int
    first_usable: IPv4Address
    last_usable: IPv4Address
    gateway_addresses: tuple[IPv4Address, ...] = ()
    static_range: AddressRange | None = None
    dhcp_range: AddressRange | None = None

    @property
    def usable_capacity(self) -> int:
        return int(self.last_usable) - int(self.first_usable) + 1

    @property
    def utilization(self) -> Fraction:
        return Fraction(self.usable_needed, self.usable_capacity)


@dataclass(frozen=True, slots=True, kw_only=True)
class PoolMetrics:
    """Immediate children only; parent_id=None identifies the project pool."""

    parent_id: str | None
    network: IPv4Network
    allocated_addresses: int
    free_addresses: int
    largest_free_block: IPv4Network | None

    @property
    def utilization(self) -> Fraction:
        return Fraction(self.allocated_addresses, self.network.num_addresses)

    @property
    def continuity(self) -> Fraction | None:
        if not self.free_addresses or self.largest_free_block is None:
            return None
        return Fraction(self.largest_free_block.num_addresses, self.free_addresses)


@dataclass(frozen=True, slots=True, kw_only=True)
class IPv6PoolMetrics:
    parent_id: str | None
    kind: IPv6PoolKind
    network: IPv6Network
    allocated_addresses: int
    free_addresses: int
    largest_free_block: IPv6Network | None

    @property
    def utilization(self) -> Fraction:
        return Fraction(self.allocated_addresses, self.network.num_addresses)

    @property
    def continuity(self) -> Fraction | None:
        if not self.free_addresses or self.largest_free_block is None:
            return None
        return Fraction(self.largest_free_block.num_addresses, self.free_addresses)


@dataclass(frozen=True, slots=True, kw_only=True)
class IPv6SegmentInfo:
    node_id: str
    network: IPv6Network
    gateway: IPv6Address | None = None
    ra_mode: IPv6RAMode | None = None
    reverse_zone: str | None = None
    endpoints: tuple[IPv6Address, ...] = ()

    @property
    def compressed(self) -> str:
        return self.network.compressed

    @property
    def exploded(self) -> str:
        return self.network.exploded


@dataclass(frozen=True, slots=True, kw_only=True)
class Plan:
    """Computed allocations, ranges, free space and findings, independent of storage."""

    project_id: str
    v4_allocations: tuple[Allocation[IPv4Network], ...] = ()
    v6_allocations: tuple[Allocation[IPv6Network], ...] = ()
    free_blocks: tuple[FreeBlock, ...] = ()
    findings: tuple[Finding, ...] = ()
    v4_reservations: tuple[SegmentReservations, ...] = ()
    v4_metrics: tuple[PoolMetrics, ...] = ()
    v6_infrastructure: tuple[IPv6Infrastructure, ...] = ()
    v6_segments: tuple[IPv6SegmentInfo, ...] = ()
    v6_metrics: tuple[IPv6PoolMetrics, ...] = ()

    @property
    def is_complete(self) -> bool:
        return not any(f.level is FindingLevel.ERROR for f in self.findings)


def node_sort_key(node: Node) -> tuple[int, str, str]:
    """Use the persistent ID to make even identical names/orders deterministic."""
    return node.sort_order, node.name, node.id
