"""Deterministic, family-preserving best-fit allocation on a list of free CIDRs."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import replace
from ipaddress import collapse_addresses

from adresplan.core.models import (
    Allocation,
    AllocationRequest,
    AllocationResult,
    DetailValue,
    Finding,
    NetworkT,
)


def _request_key(request: AllocationRequest[NetworkT]) -> tuple[int, int, str, str]:
    prefix = request.prefix if isinstance(request.prefix, int) else -1
    return prefix, request.sort_order, request.name, request.node_id


def _valid_prefix(prefix: int, max_prefixlen: int) -> bool:
    return isinstance(prefix, int) and not isinstance(prefix, bool) and 0 <= prefix <= max_prefixlen


def _claim(free: list[NetworkT], container: NetworkT, taken: NetworkT) -> None:
    free.remove(container)
    if container != taken:
        free.extend(container.address_exclude(taken))


def _run(
    pool: NetworkT,
    requests: tuple[AllocationRequest[NetworkT], ...],
    excluded: tuple[NetworkT, ...] = (),
) -> AllocationResult[NetworkT]:
    """Allocate once, without recursively calculating capacity suggestions."""
    free: list[NetworkT] = [pool]
    allocations: list[Allocation[NetworkT]] = []
    findings: list[Finding] = []
    valid_exclusions = []
    for network in excluded:
        if network.version != pool.version or not network.subnet_of(pool):
            findings.append(
                Finding(code="blocked_outside_pool", details=(("network", str(network)),))
            )
        else:
            valid_exclusions.append(network)
    for network in collapse_addresses(valid_exclusions):
        reserved_container = next(block for block in free if network.subnet_of(block))
        _claim(free, reserved_container, network)
    valid: list[AllocationRequest[NetworkT]] = []
    counts = Counter(request.node_id for request in requests)
    for node_id in sorted(counts):
        if counts[node_id] > 1:
            findings.append(Finding(code="duplicate_request_id", node_id=node_id))
    for request in requests:
        if counts[request.node_id] > 1:
            continue
        if not request.node_id.strip():
            findings.append(Finding(code="empty_request_id", node_id=request.node_id))
            continue
        if not _valid_prefix(request.prefix, pool.max_prefixlen):
            findings.append(Finding(code="invalid_prefix", node_id=request.node_id))
            continue
        valid.append(request)

    # Pins are removed before automatic requests, regardless of their size or order.
    for request in valid:
        pinned = request.pinned
        if pinned is None:
            continue
        code: str | None = None
        if pinned.version != pool.version:
            code = "pinned_family_mismatch"
        elif pinned.prefixlen > request.prefix:
            code = "pinned_too_small"
        elif not pinned.subnet_of(pool):
            code = "pinned_outside_pool"
        if code is not None:
            findings.append(Finding(code=code, node_id=request.node_id))
            continue
        container = next((block for block in free if pinned.subnet_of(block)), None)
        if container is None:
            code = (
                "pinned_blocked"
                if any(pinned.overlaps(n) for n in valid_exclusions)
                else "pinned_overlap"
            )
            findings.append(Finding(code=code, node_id=request.node_id))
            continue
        _claim(free, container, pinned)
        allocations.append(Allocation(node_id=request.node_id, network=pinned))

    for request in valid:
        if request.pinned is not None:
            continue
        candidates = [block for block in free if block.prefixlen <= request.prefix]
        if not candidates:
            largest = min((block.prefixlen for block in free), default=None)
            findings.append(
                Finding(
                    code="insufficient_space",
                    node_id=request.node_id,
                    details=(
                        ("requested_prefix", request.prefix),
                        ("free_addresses", sum(block.num_addresses for block in free)),
                        ("largest_free_prefix", largest),
                    ),
                )
            )
            continue
        best = min(candidates, key=lambda block: (-block.prefixlen, int(block.network_address)))
        taken = (
            best
            if best.prefixlen == request.prefix
            else next(best.subnets(new_prefix=request.prefix))
        )
        _claim(free, best, taken)
        allocations.append(Allocation(node_id=request.node_id, network=taken))

    return AllocationResult(
        allocations=tuple(
            sorted(allocations, key=lambda a: (int(a.network.network_address), a.node_id))
        ),
        free_blocks=tuple(sorted(free, key=lambda block: int(block.network_address))),
        findings=tuple(findings),
    )


def allocate(
    pool: NetworkT,
    requests: Iterable[AllocationRequest[NetworkT]],
    *,
    excluded: tuple[NetworkT, ...] = (),
) -> AllocationResult[NetworkT]:
    """Allocate IPv4 or IPv6 requests, collect errors, and never mutate input.

    Larger blocks come first; ties use sort_order, name and persistent ID. An invalid
    pin is reported and never silently replaced by an automatic allocation. Capacity
    suggestions simulate the same allocator on bounded supernets without moving pins.
    """
    ordered = tuple(sorted(requests, key=_request_key))
    result = _run(pool, ordered, excluded)
    if not any(f.code == "insufficient_space" for f in result.findings):
        return result

    total = sum(
        request.pinned.num_addresses
        if request.pinned is not None
        else 2 ** (pool.max_prefixlen - request.prefix)
        for request in ordered
        if _valid_prefix(request.prefix, pool.max_prefixlen)
    )
    lower_bound = pool.max_prefixlen - (total - 1).bit_length() if total else pool.max_prefixlen
    suggested: int | None = None
    if lower_bound >= 0 and all(f.code == "insufficient_space" for f in result.findings):
        for prefix in range(min(pool.prefixlen - 1, lower_bound), -1, -1):
            if _run(pool.supernet(new_prefix=prefix), ordered, excluded).is_complete:
                suggested = prefix
                break

    enriched: list[Finding] = []
    finding: Finding
    for finding in result.findings:
        if finding.code == "insufficient_space":
            details: tuple[tuple[str, DetailValue], ...] = (
                *finding.details,
                ("required_addresses", total),
                ("capacity_lower_bound_prefix", lower_bound if lower_bound >= 0 else None),
                ("suggested_pool_prefix", suggested),
            )
            enriched.append(replace(finding, details=details))
        else:
            enriched.append(finding)
    return AllocationResult(
        allocations=result.allocations,
        free_blocks=result.free_blocks,
        findings=tuple(enriched),
    )
