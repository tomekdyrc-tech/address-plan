"""Address changes between the saved project and an uncommitted plan."""

from adresplan.core.models import Node, Project
from adresplan.core.plan import build_plan


def allocation_impact(before: Project, after: Project) -> list[dict[str, str]]:
    old, new = build_plan(before), build_plan(after)
    nodes = {n.id: n for p in (before, after) for n in p.nodes}
    names = {}
    for key, node in nodes.items():
        parts, seen = [], set()
        current: Node | None = node
        while current is not None and current.id not in seen:
            seen.add(current.id)
            parts.append(current.name)
            current = nodes.get(current.parent_id or "")
        names[key] = " → ".join(reversed(parts))
    rows = []
    for family, left, right in (
        ("IPv4", old.v4_allocations, new.v4_allocations),
        ("IPv6", old.v6_allocations, new.v6_allocations),
    ):
        a = {n.node_id: str(n.network) for n in left}
        b = {n.node_id: str(n.network) for n in right}
        for key in sorted(a.keys() | b.keys()):
            if a.get(key) != b.get(key):
                rows.append(
                    {
                        "name": names.get(key, "Element"),
                        "family": family,
                        "before": a.get(key, "—"),
                        "after": b.get(key, "—"),
                    }
                )
    return rows
