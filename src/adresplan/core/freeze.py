"""Turn a verified computed plan into explicit input pins, without I/O."""

from dataclasses import replace

from adresplan.core.models import Plan, Project
from adresplan.core.plan import build_plan


def freeze(project: Project, plan: Plan) -> Project:
    """Freeze both families and IPv6 infrastructure; refuse incomplete or stale plans."""
    if plan.project_id != project.id:
        raise ValueError("plan belongs to another project")
    if not plan.is_complete:
        raise ValueError("cannot freeze an incomplete plan")
    expected = build_plan(project)
    if not expected.is_complete or expected != plan:
        raise ValueError("plan does not match the current project")
    allocations = {allocation.node_id: allocation.network for allocation in plan.v4_allocations}
    allocations6 = {allocation.node_id: allocation.network for allocation in plan.v6_allocations}
    return replace(
        project,
        nodes=tuple(
            replace(
                node,
                pinned_v4=allocations.get(node.id, node.pinned_v4),
                pinned_v6=allocations6.get(node.id, node.pinned_v6),
            )
            for node in project.nodes
        ),
        pinned_v6_infrastructure=(
            plan.v6_infrastructure if project.v6_active else project.pinned_v6_infrastructure
        ),
    )
