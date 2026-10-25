"""Pins, best fit, diagnostics and family preservation."""

from dataclasses import FrozenInstanceError
from ipaddress import IPv4Network, IPv6Network

import pytest

from adresplan.core.allocator import allocate
from adresplan.core.models import Allocation, AllocationRequest, AllocationResult


def req(node_id: str, prefix: int = 26, **options) -> AllocationRequest[IPv4Network]:
    return AllocationRequest(node_id=node_id, name=node_id, prefix=prefix, **options)


def test_empty_requests_leave_the_pool_free() -> None:
    pool = IPv4Network("10.0.0.0/24")
    result = allocate(pool, [])
    assert result.is_complete and not result.allocations
    assert result.free_blocks == (pool,)


def test_generic_records_support_runtime_type_arguments() -> None:
    network = IPv4Network("10.0.0.0/24")
    allocation = Allocation[IPv4Network](node_id="s", network=network)
    result = AllocationResult[IPv4Network](allocations=(allocation,), free_blocks=())
    assert result.is_complete and result.allocations[0].network == network
    with pytest.raises(FrozenInstanceError):
        allocation.node_id = "changed"


def test_pin_is_claimed_before_larger_automatic_requests() -> None:
    result = allocate(
        IPv4Network("10.0.0.0/24"),
        [req("auto", 25), req("pin", 26, pinned=IPv4Network("10.0.0.128/26"))],
    )
    assert result.is_complete
    assert {a.node_id: str(a.network) for a in result.allocations} == {
        "auto": "10.0.0.0/25",
        "pin": "10.0.0.128/26",
    }


def test_best_fit_uses_smaller_free_block_before_lower_larger_block() -> None:
    result = allocate(
        IPv4Network("10.0.0.0/24"),
        [req("pin", pinned=IPv4Network("10.0.0.128/26")), req("auto")],
    )
    assert next(a.network for a in result.allocations if a.node_id == "auto") == IPv4Network(
        "10.0.0.192/26"
    )


def test_best_fit_tie_uses_lowest_address() -> None:
    result = allocate(
        IPv4Network("10.0.0.0/24"),
        [
            req("p1", 28, pinned=IPv4Network("10.0.0.0/28")),
            req("p2", 28, pinned=IPv4Network("10.0.0.128/28")),
            req("auto", 27),
        ],
    )
    assert next(a.network for a in result.allocations if a.node_id == "auto") == IPv4Network(
        "10.0.0.32/27"
    )


def test_pin_can_use_the_entire_pool_or_be_larger_than_required() -> None:
    pool = IPv4Network("10.0.0.0/24")
    result = allocate(pool, [req("pin", 26, pinned=pool)])
    assert result.is_complete and result.free_blocks == ()
    assert result.allocations[0].network == pool


@pytest.mark.parametrize(
    ("pinned", "code"),
    [
        (IPv4Network("10.0.1.0/26"), "pinned_outside_pool"),
        (IPv4Network("10.0.0.0/27"), "pinned_too_small"),
        (IPv6Network("2001:db8::/64"), "pinned_family_mismatch"),
    ],
)
def test_invalid_pin_does_not_fall_back_to_another_address(pinned, code: str) -> None:
    result = allocate(IPv4Network("10.0.0.0/24"), [req("bad", pinned=pinned), req("ok")])
    assert not result.is_complete
    assert [a.node_id for a in result.allocations] == ["ok"]
    assert result.findings[0].code == code


def test_overlapping_pins_are_reported_without_corrupting_free_space() -> None:
    pool = IPv4Network("10.0.0.0/24")
    result = allocate(
        pool,
        [
            req("a", 25, pinned=IPv4Network("10.0.0.0/25")),
            req("b", pinned=IPv4Network("10.0.0.64/26")),
        ],
    )
    assert [a.node_id for a in result.allocations] == ["a"]
    assert [(f.code, f.node_id) for f in result.findings] == [("pinned_overlap", "b")]
    assert result.free_blocks == (IPv4Network("10.0.0.128/25"),)


def test_duplicate_request_ids_are_rejected_together() -> None:
    result = allocate(IPv4Network("10.0.0.0/24"), [req("same"), req("same"), req("ok")])
    assert [a.node_id for a in result.allocations] == ["ok"]
    assert [f.code for f in result.findings] == ["duplicate_request_id"]


@pytest.mark.parametrize("prefix", [-1, 33, True, 26.5, "26", None])
def test_invalid_prefix_is_reported_and_other_requests_continue(prefix: int) -> None:
    result = allocate(IPv4Network("10.0.0.0/24"), [req("bad", prefix), req("ok")])
    assert [f.code for f in result.findings] == ["invalid_prefix"]
    assert [a.node_id for a in result.allocations] == ["ok"]


def test_empty_id_is_rejected() -> None:
    result = allocate(IPv4Network("10.0.0.0/24"), [req(" ")])
    assert not result.allocations
    assert result.findings[0].code == "empty_request_id"


def test_allocation_continues_after_a_request_does_not_fit() -> None:
    result = allocate(IPv4Network("10.0.0.0/26"), [req("big", 25), req("small", 27)])
    assert [a.node_id for a in result.allocations] == ["small"]
    assert [f.node_id for f in result.findings] == ["big"]


def test_all_failed_requests_produce_findings() -> None:
    result = allocate(IPv4Network("10.0.0.0/32"), [req("a", 31), req("b", 31), req("c", 31)])
    assert [f.node_id for f in result.findings] == ["a", "b", "c"]


def test_fragmentation_suggestion_is_simulated_not_just_summed() -> None:
    result = allocate(
        IPv4Network("10.0.0.0/24"),
        [
            req("p1", 32, pinned=IPv4Network("10.0.0.0/32")),
            req("p2", 32, pinned=IPv4Network("10.0.0.128/32")),
            req("large", 25),
        ],
    )
    details = dict(result.findings[0].details)
    assert details["required_addresses"] == 130
    assert details["free_addresses"] == 254
    assert details["largest_free_prefix"] == 26
    assert details["capacity_lower_bound_prefix"] == 24
    assert details["suggested_pool_prefix"] == 23


def test_request_larger_than_the_entire_family_has_no_suggestion() -> None:
    result = allocate(IPv4Network("0.0.0.0/0"), [req("a", 0), req("b", 0)])
    assert len(result.allocations) == 1
    details = dict(result.findings[0].details)
    assert details["suggested_pool_prefix"] is None
    assert details["capacity_lower_bound_prefix"] is None


def test_identical_order_and_name_are_resolved_by_persistent_id() -> None:
    first = AllocationRequest[IPv4Network](node_id="a", name="same", prefix=26)
    second = AllocationRequest[IPv4Network](node_id="b", name="same", prefix=26)
    pool = IPv4Network("10.0.0.0/24")
    assert allocate(pool, [first, second]) == allocate(pool, [second, first])
    assert allocate(pool, [second, first]).allocations[0].node_id == "a"


def test_input_iterables_and_records_are_not_modified() -> None:
    requests = [req("b"), req("a")]
    saved = requests.copy()
    result = allocate(IPv4Network("10.0.0.0/24"), iter(requests))
    assert requests == saved
    assert result == allocate(IPv4Network("10.0.0.0/24"), requests)
    with pytest.raises(FrozenInstanceError):
        requests[0].prefix = 25


def test_ipv6_preserves_family_and_does_not_enumerate_hosts(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("host enumeration is forbidden")

    monkeypatch.setattr(IPv6Network, "hosts", forbidden)
    pool = IPv6Network("2001:db8::/48")
    requests = [
        AllocationRequest[IPv6Network](node_id="a", name="A", prefix=64),
        AllocationRequest[IPv6Network](node_id="b", name="B", prefix=127),
    ]
    result = allocate(pool, requests)
    assert result.is_complete
    assert [str(a.network) for a in result.allocations] == ["2001:db8::/64", "2001:db8:0:1::/127"]
    assert all(isinstance(a.network, IPv6Network) for a in result.allocations)
    assert (
        sum(a.network.num_addresses for a in result.allocations)
        + sum(block.num_addresses for block in result.free_blocks)
        == pool.num_addresses
    )


def test_invalid_ipv6_pin_is_rejected_in_ipv6_pool() -> None:
    request = AllocationRequest[IPv6Network](
        node_id="s", name="S", prefix=64, pinned=IPv6Network("2001:db9::/64")
    )
    assert (
        allocate(IPv6Network("2001:db8::/48"), [request]).findings[0].code == "pinned_outside_pool"
    )
