"""Compose independent IPv4 and IPv6 calculations into one deterministic plan."""

from dataclasses import replace

from adresplan.core.models import Plan, Project
from adresplan.core.plan4 import build_plan_v4
from adresplan.core.plan6 import build_plan_v6


def build_plan(project: Project) -> Plan:
    v4 = build_plan_v4(project)
    v6 = build_plan_v6(project)
    return replace(
        v4,
        v6_allocations=v6.v6_allocations,
        free_blocks=(*v4.free_blocks, *v6.free_blocks),
        findings=tuple(dict.fromkeys((*v4.findings, *v6.findings))),
        v6_infrastructure=v6.v6_infrastructure,
        v6_segments=v6.v6_segments,
        v6_metrics=v6.v6_metrics,
    )
