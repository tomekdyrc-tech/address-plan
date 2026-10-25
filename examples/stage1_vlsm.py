"""Run reference vector T1 directly against the pure core."""

from ipaddress import IPv4Network

from adresplan.core.allocator import allocate
from adresplan.core.models import AllocationRequest
from adresplan.core.sizing import prefix_for_usable


def main() -> None:
    entries = [("A", 100), ("B", 50), ("C", 25), ("D", 10)]
    requests = [
        AllocationRequest[IPv4Network](
            node_id=name, name=name, prefix=prefix_for_usable(hosts), sort_order=order
        )
        for order, (name, hosts) in enumerate(entries)
    ]
    result = allocate(IPv4Network("192.168.10.0/24"), requests)
    print("T1: 192.168.10.0/24; zapas=0%, bramy=0, statyczne=0")
    print(f"{'Segment':<10} {'Hosty':>6}  {'Podsiec':<22} Zakres uzyteczny")
    host_counts = dict(entries)
    for allocation in result.allocations:
        network = allocation.network
        print(
            f"{allocation.node_id:<10} {host_counts[allocation.node_id]:>6}  "
            f"{str(network):<22} {network[1]} - {network[-2]}"
        )
    print("Wolne:", ", ".join(map(str, result.free_blocks)))
    print("Wynik:", "poprawny" if result.is_complete else "z bledami")


if __name__ == "__main__":
    main()
