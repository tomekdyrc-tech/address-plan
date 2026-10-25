"""Strict JSON input models; the network planner remains independent of Pydantic."""

from __future__ import annotations

from ipaddress import IPv4Network, IPv6Address, IPv6Network
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    StrictStr,
)
from pydantic_core import PydanticCustomError

from adresplan.core.models import (
    BlockedSubnet,
    GatewayPosition,
    IPv6GatewayMode,
    IPv6Infrastructure,
    IPv6Kind,
    IPv6RAMode,
    IPv6SubnetStrategy,
    Node,
    NodeKind,
    Project,
    ProjectSettings,
    Segment,
    SegmentRole,
)

SCHEMA_VERSION = 3


def _nonblank(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("blank_string", "Wartość nie może być pusta.")
    return value


def _utf8_text(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise PydanticCustomError(
            "invalid_utf8_text", "Tekst zawiera nieprawidłowy znak Unicode."
        ) from error
    return value


def _v4_network(value: object) -> IPv4Network:
    if isinstance(value, IPv4Network):
        return value
    if not isinstance(value, str) or "/" not in value:
        raise PydanticCustomError("cidr_v4", "Podaj sieć IPv4 z prefiksem, np. 10.0.0.0/24.")
    try:
        return IPv4Network(value, strict=True)
    except ValueError as error:
        raise PydanticCustomError(
            "cidr_v4", "Nieprawidłowa sieć IPv4 lub ustawione bity hosta."
        ) from error


def _v6_network(value: object) -> IPv6Network:
    if isinstance(value, IPv6Network) and value.network_address.scope_id is None:
        return value
    if not isinstance(value, str) or "/" not in value or "%" in value:
        raise PydanticCustomError("cidr_v6", "Podaj sieć IPv6 z prefiksem, np. 2001:db8::/48.")
    try:
        return IPv6Network(value, strict=True)
    except ValueError as error:
        raise PydanticCustomError(
            "cidr_v6", "Nieprawidłowa sieć IPv6 lub ustawione bity hosta."
        ) from error


def _v6_address(value: object) -> IPv6Address:
    if isinstance(value, IPv6Address) and value.scope_id is None:
        return value
    if isinstance(value, str) and "%" not in value:
        try:
            return IPv6Address(value)
        except ValueError:
            pass
    raise PydanticCustomError("address_v6", "Podaj adres IPv6 bez identyfikatora interfejsu.")


Text: TypeAlias = Annotated[StrictStr, AfterValidator(_utf8_text)]
Nonblank: TypeAlias = Annotated[Text, AfterValidator(_nonblank), Field(min_length=1)]
Nonnegative: TypeAlias = Annotated[StrictInt, Field(ge=0)]
GatewayCount: TypeAlias = Annotated[StrictInt, Field(ge=0, le=3)]
V4CIDR: TypeAlias = Annotated[IPv4Network, BeforeValidator(_v4_network)]
V6CIDR: TypeAlias = Annotated[IPv6Network, BeforeValidator(_v6_network)]
V6Address: TypeAlias = Annotated[IPv6Address, BeforeValidator(_v6_address)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)


class SettingsInput(InputModel):
    growth_pct: Nonnegative = 25
    gateway: GatewayPosition = GatewayPosition.FIRST
    gateway_addrs: GatewayCount = 1
    p2p_prefix: Annotated[StrictInt, Field(ge=30, le=31)] = 31
    v6_site_prefix: Annotated[StrictInt, Field(ge=0, le=60, multiple_of=4)] = 48
    v6_building_prefix: Annotated[StrictInt, Field(ge=52, le=60, multiple_of=4)] = 56
    v6_infra_prefix: Annotated[StrictInt, Field(ge=0, le=60, multiple_of=4)] = 56
    v6_growth_pct: Nonnegative = 100
    v6_subnet_strategy: IPv6SubnetStrategy = IPv6SubnetStrategy.SEQUENTIAL
    v6_gateway_mode: IPv6GatewayMode = IPv6GatewayMode.GLOBAL
    v6_link_local_gateway: V6Address = IPv6Address("fe80::1")
    v6_ra_mode: IPv6RAMode = IPv6RAMode.SLAAC


class NodeInput(InputModel):
    id: Nonblank
    name: Nonblank
    parent_id: Nonblank | None = None
    sort_order: Nonnegative = 0
    pinned_v4: V4CIDR | None = None
    pinned_v6: V6CIDR | None = None
    notes: Text = ""


class SiteInput(NodeInput):
    kind: Literal["site"]


class BuildingInput(NodeInput):
    kind: Literal["building"]


class SegmentInput(NodeInput):
    kind: Literal["segment"]
    role: SegmentRole = SegmentRole.LAN
    hosts: Nonnegative = 0
    growth_pct: Nonnegative | None = None
    gateway: GatewayPosition | None = None
    gateway_addrs: GatewayCount | None = None
    static_count: Nonnegative = 0
    vlan_id: Annotated[StrictInt, Field(ge=1, le=4094)] | None = None
    v6_enabled: StrictBool = True
    ra_mode: IPv6RAMode | None = None


TreeInput: TypeAlias = Annotated[
    SiteInput | BuildingInput | SegmentInput, Field(discriminator="kind")
]


class InfrastructureInput(InputModel):
    site_id: Nonblank
    network: V6CIDR
    reserved_pool: V6CIDR
    p2p_pool: V6CIDR
    loopback_pool: V6CIDR


class BlockedSubnetInput(InputModel):
    network: V4CIDR | V6CIDR
    parent_id: Nonblank | None = None
    note: Text = ""


class ProjectInput(InputModel):
    id: Nonblank
    name: Nonblank
    author: Text = ""
    organization: Text = ""
    description: Text = ""
    document_date: Text = ""
    v4_pool: V4CIDR
    nodes: list[TreeInput] = Field(default_factory=list)
    settings: SettingsInput = Field(default_factory=SettingsInput)
    v6_prefix: V6CIDR | None = None
    v6_active: StrictBool = True
    v6_kind: IPv6Kind = IPv6Kind.DOCUMENTATION
    pinned_v6_infrastructure: list[InfrastructureInput] = Field(default_factory=list)
    blocked_subnets: list[BlockedSubnetInput] = Field(default_factory=list)

    def to_core(self) -> Project:
        nodes: list[Node] = []
        for node in self.nodes:
            values = node.model_dump(mode="python", exclude={"kind"})
            nodes.append(
                Segment(**values)
                if isinstance(node, SegmentInput)
                else Node(kind=NodeKind(node.kind), **values)
            )
        return Project(
            id=self.id,
            name=self.name,
            author=self.author,
            organization=self.organization,
            description=self.description,
            document_date=self.document_date,
            v4_pool=self.v4_pool,
            nodes=tuple(nodes),
            settings=ProjectSettings(**self.settings.model_dump(mode="python")),
            v6_prefix=self.v6_prefix,
            v6_active=self.v6_active,
            v6_kind=self.v6_kind,
            pinned_v6_infrastructure=tuple(
                IPv6Infrastructure(**pin.model_dump(mode="python"))
                for pin in self.pinned_v6_infrastructure
            ),
            blocked_subnets=tuple(
                BlockedSubnet(**block.model_dump(mode="python")) for block in self.blocked_subnets
            ),
        )


class DocumentInput(InputModel):
    schema_version: Annotated[StrictInt, Field(ge=1, le=SCHEMA_VERSION)]
    project: ProjectInput
    plan: dict[StrictStr, JsonValue] | None = Field(
        default=None,
        description="Wynik poglądowy. Import ignoruje jego zawartość i przelicza projekt od nowa.",
    )


def project_json_schema() -> dict[str, object]:
    """Generate the versioned public schema from the actual import models."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:adresplan:project:3",
        **DocumentInput.model_json_schema(),
    }
