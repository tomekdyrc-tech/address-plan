"""Randomized invariants for the generic free-list allocator."""

from dataclasses import replace
from ipaddress import IPv4Network, IPv6Network
from itertools import combinations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from adresplan.core.allocator import allocate
from adresplan.core.models import AllocationRequest


@pytest.mark.parametrize("family", [4, 6])
@given(
    pool_bits=st.integers(min_value=0, max_value=8),
    sizes=st.lists(st.integers(min_value=0, max_value=8), max_size=18),
)
def test_disjoint_aligned_complete_partition_and_determinism(family, pool_bits, sizes) -> None:
    constructor = IPv4Network if family == 4 else IPv6Network
    bits = 32 if family == 4 else 128
    base = "10.0.0.0" if family == 4 else "2001:db8::"
    pool = constructor(f"{base}/{bits - pool_bits}")
    requests = [
        AllocationRequest(node_id=str(i), name=f"S{i}", prefix=bits - size, sort_order=i)
        for i, size in enumerate(sizes)
    ]
    result = allocate(pool, requests)
    occupied = [a.network for a in result.allocations]
    partition = occupied + list(result.free_blocks)
    assert all(network.subnet_of(pool) for network in partition)
    assert all(not a.overlaps(b) for a, b in combinations(partition, 2))
    assert sum(network.num_addresses for network in partition) == pool.num_addresses
    assert all(int(network.network_address) % network.num_addresses == 0 for network in occupied)
    assert result == allocate(pool, requests) == allocate(pool, reversed(requests))
    assert len(result.allocations) + len(result.findings) == len(requests)


@pytest.mark.parametrize("family", [4, 6])
@given(
    sizes=st.lists(st.integers(min_value=0, max_value=6), max_size=12),
    extra=st.lists(st.integers(min_value=0, max_value=8), max_size=8),
)
def test_pin_replay_preserves_every_previous_address(family, sizes, extra) -> None:
    constructor = IPv4Network if family == 4 else IPv6Network
    bits = 32 if family == 4 else 128
    pool = constructor("10.0.0.0/24" if family == 4 else "2001:db8::/120")
    requests = [
        AllocationRequest(node_id=str(i), name=str(i), prefix=bits - size)
        for i, size in enumerate(sizes)
    ]
    original = allocate(pool, requests)
    assigned = {a.node_id: a.network for a in original.allocations}
    frozen = [replace(r, pinned=assigned[r.node_id]) for r in requests if r.node_id in assigned]
    new = [
        AllocationRequest(node_id=f"new{i}", name=f"new{i}", prefix=bits - size)
        for i, size in enumerate(extra)
    ]
    replayed = allocate(pool, frozen + new)
    actual = {a.node_id: a.network for a in replayed.allocations}
    assert all(actual[node_id] == network for node_id, network in assigned.items())
    assert (
        sum(a.network.num_addresses for a in replayed.allocations)
        + sum(network.num_addresses for network in replayed.free_blocks)
        == pool.num_addresses
    )
