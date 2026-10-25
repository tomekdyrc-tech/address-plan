"""Explain the same sizing calculation that the allocator uses."""

from adresplan.core.models import GatewayPosition, Project, Segment, SegmentRole
from adresplan.core.sizing import grown_host_count, size_segment_v4
from adresplan.i18n import tr


def explain_segment(project: Project, segment: Segment) -> str:
    try:
        size = size_segment_v4(segment, project.settings)
    except ValueError:
        return tr("Popraw zapotrzebowanie i ustawienia segmentu, aby zobaczyć wyliczenie.")
    if segment.role in (SegmentRole.P2P, SegmentRole.LOOPBACK):
        return tr(
            "Stałe zapotrzebowanie: {needed} adresów; wymagany prefiks /{prefix}. "
            "Zapas i brama nie są doliczane.",
            needed=size.usable_needed,
            prefix=size.prefix,
        )
    growth = project.settings.growth_pct if segment.growth_pct is None else segment.growth_pct
    reserve = grown_host_count(segment.hosts, growth) - segment.hosts
    gateway = project.settings.gateway if segment.gateway is None else segment.gateway
    gateways = segment.gateway_addrs
    if gateways is None:
        gateways = 0 if gateway is GatewayPosition.NONE else project.settings.gateway_addrs
    capacity = 2 ** (32 - size.prefix) - 2
    return tr(
        "{hosts} urządzeń + {reserve} zapasu ({growth}%) + {gateways} adresów bram "
        "+ {static} dodatkowych adresów statycznych = {needed} potrzebnych adresów. "
        "Minimum: /{prefix}, pojemność {capacity}. "
        "Przypięty większy blok może mieć dodatkowy zapas.",
        hosts=segment.hosts,
        reserve=reserve,
        growth=growth,
        gateways=gateways,
        static=segment.static_count,
        needed=size.usable_needed,
        prefix=size.prefix,
        capacity=capacity,
    )
