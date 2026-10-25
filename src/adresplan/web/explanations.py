"""Explain the same sizing calculation that the allocator uses."""

from adresplan.core.models import GatewayPosition, Project, Segment, SegmentRole
from adresplan.core.sizing import grown_host_count, size_segment_v4


def explain_segment(project: Project, segment: Segment) -> str:
    try:
        size = size_segment_v4(segment, project.settings)
    except ValueError:
        return "Popraw zapotrzebowanie i ustawienia segmentu, aby zobaczyć wyliczenie."
    if segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK):
        return (
            f"Stałe zapotrzebowanie: {size.usable_needed} adresów; "
            f"wymagany prefiks /{size.prefix}. "
            "Zapas i brama nie są doliczane."
        )
    growth = project.settings.growth_pct if segment.growth_pct is None else segment.growth_pct
    reserve = grown_host_count(segment.hosts, growth) - segment.hosts
    gateway = project.settings.gateway if segment.gateway is None else segment.gateway
    gateways = segment.gateway_addrs
    if gateways is None:
        gateways = 0 if gateway is GatewayPosition.NONE else project.settings.gateway_addrs
    capacity = 2 ** (32 - size.prefix) - 2
    return (
        f"{segment.hosts} urządzeń + {reserve} zapasu ({growth}%) + {gateways} adresów bram "
        f"+ {segment.static_count} dodatkowych adresów statycznych "
        f"= {size.usable_needed} potrzebnych adresów. "
        f"Minimum: /{size.prefix}, pojemność {capacity}. "
        "Przypięty większy blok może mieć dodatkowy zapas."
    )
