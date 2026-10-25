"""Scoped external reservations; only CIDR arithmetic, never address enumeration."""

from ipaddress import IPv4Network, IPv6Network

from adresplan.core.models import Finding, NodeKind, Project


def blocked_v4(project: Project, parent_id: str | None) -> tuple[IPv4Network, ...]:
    return tuple(
        b.network
        for b in project.blocked_subnets
        if b.parent_id == parent_id and isinstance(b.network, IPv4Network)
    )


def blocked_v6(project: Project, parent_id: str | None) -> tuple[IPv6Network, ...]:
    return tuple(
        b.network
        for b in project.blocked_subnets
        if b.parent_id == parent_id and isinstance(b.network, IPv6Network)
    )


def validate_blocks(project: Project, family: int) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    nodes = {n.id: n for n in project.nodes}
    pool = project.v4_pool if family == 4 else project.v6_prefix
    for block in project.blocked_subnets:
        if block.network.version != family:
            continue
        reason = ""
        if (
            pool is None
            or block.network.version != pool.version
            or int(block.network.network_address) < int(pool.network_address)
            or int(block.network.broadcast_address) > int(pool.broadcast_address)
        ):
            reason = "Blokada musi mieścić się w puli projektu tej samej rodziny."
        elif block.parent_id is not None and (
            block.parent_id not in nodes or nodes[block.parent_id].kind is NodeKind.SEGMENT
        ):
            reason = "Blokadę przypisz do projektu, lokalizacji albo budynku."
        if reason:
            findings.append(
                Finding(
                    code="invalid_blocked_subnet",
                    node_id=block.parent_id,
                    details=(("network", str(block.network)), ("reason", reason)),
                )
            )
    return tuple(findings)
