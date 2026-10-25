"""Polish messages for diagnostics, calculator errors and labels shared by all outputs."""

from adresplan.core.calc import IPv6AddressKind
from adresplan.core.models import FindingLevel, IPv6PoolKind, NodeKind

CALC_MESSAGES = {
    "invalid_address": (
        "Podaj poprawny adres IPv4/IPv6 z prefiksem albo adres IPv4 i "
        "maskę/wildcard. Bez %interfejsu."
    ),
    "choose_one_split_mode": "Wybierz jeden sposób podziału: --split albo --new-prefix.",
    "invalid_preview_limit": "Limit podglądu musi być liczbą całkowitą od 1 do 256.",
    "invalid_subnet_count": "Liczba podsieci musi być dodatnią liczbą całkowitą.",
    "subnet_count_not_power_of_two": "Liczba równych podsieci musi być potęgą dwójki.",
    "invalid_subnet_prefix": (
        "Docelowy prefiks nie może być krótszy od wejściowego ani przekraczać"
        " /32 (IPv4) lub /128 (IPv6)."
    ),
}
NODE_KINDS = {
    NodeKind.SITE: "lokalizacja",
    NodeKind.BUILDING: "budynek",
    NodeKind.SEGMENT: "segment",
}
V6_ADDRESS_KINDS = {
    IPv6AddressKind.DOCUMENTATION: "dokumentacyjny",
    IPv6AddressKind.ULA: "ULA",
    IPv6AddressKind.GUA: "GUA",
    IPv6AddressKind.LINK_LOCAL: "link-local",
    IPv6AddressKind.MULTICAST: "multicast",
    IPv6AddressKind.LOOPBACK: "loopback",
    IPv6AddressKind.UNSPECIFIED: "nieokreślony (::)",
    IPv6AddressKind.MIXED: "mieszany zakres",
    IPv6AddressKind.OTHER: "inny / poza rozpoznawanymi zakresami",
}
POOL_KINDS = {
    IPv6PoolKind.PROJECT: "projekt",
    IPv6PoolKind.SITE: "lokalizacja",
    IPv6PoolKind.BUILDING: "budynek",
    IPv6PoolKind.INFRASTRUCTURE: "infrastruktura",
    IPv6PoolKind.P2P: "łącza",
    IPv6PoolKind.LOOPBACK: "loopbacki",
}
LEVEL_LABELS = {
    FindingLevel.ERROR: "BŁĄD",
    FindingLevel.WARNING: "OSTRZEŻENIE",
    FindingLevel.INFO: "INFO",
}

FINDING_MESSAGES = {
    "invalid_blocked_subnet": "Nieprawidłowa blokada zajętej podsieci.",
    "blocked_outside_pool": "Zablokowana podsieć wykracza poza pulę rodzica.",
    "v6_blocked_outside_pool": "Zablokowana podsieć IPv6 wykracza poza pulę rodzica.",
    "pinned_blocked": "Przypięta podsieć przecina zablokowany zakres IPv4.",
    "v6_pinned_blocked": "Przypięta podsieć przecina zablokowany zakres IPv6.",
    "duplicate_request_id": "Powtórzony identyfikator zapotrzebowania.",
    "empty_request_id": "Brakuje identyfikatora zapotrzebowania.",
    "invalid_prefix": "Nieprawidłowa długość prefiksu.",
    "pinned_family_mismatch": "Przypięta sieć ma niewłaściwą rodzinę adresów.",
    "pinned_too_small": "Przypięty blok jest za mały dla zapotrzebowania.",
    "pinned_outside_pool": "Przypięta sieć wykracza poza pulę rodzica.",
    "pinned_overlap": "Przypięta sieć koliduje z innym przydziałem.",
    "insufficient_space": "Brak miejsca na wymaganą podsieć.",
    "invalid_segment_requirements": "Nieprawidłowe zapotrzebowanie segmentu.",
    "hierarchy_capacity_exceeded": "Zapotrzebowanie hierarchii przekracza pojemność IPv4.",
    "hierarchy_anchor_overlap": "Bloki wymagane przez przypięte dzieci kolidują ze sobą.",
    "hierarchy_anchor_outside_parent": (
        "Blok wymagany przez przypięte dzieci nie mieści się w rodzicu."
    ),
    "pool_fragmentation": "Wolne miejsce w puli i jego ciągłość.",
    "summary_route": "Blok sumaryczny rodzica.",
    "invalid_reservations": "Nie można wyznaczyć rezerwacji w segmencie.",
    "high_segment_utilization": "Zapotrzebowanie przekracza 85% pojemności segmentu.",
    "invalid_v4_pool": "Nieprawidłowa pula IPv4.",
    "forbidden_v4_pool": "Pula przecina zabroniony zakres IPv4.",
    "cgnat_pool": "Pula przecina zakres CGNAT; nie jest to RFC 1918.",
    "non_rfc1918_pool": "Pula nie mieści się w prywatnych zakresach RFC 1918.",
    "pinned_outside_project": "Przypięta sieć wykracza poza pulę projektu.",
    "invalid_vlan_id": "VLAN musi mieć numer od 1 do 4094.",
    "user_traffic_vlan_1": "Ruch użytkowników korzysta z VLAN 1.",
    "duplicate_vlan_id": "Numer VLAN powtarza się w tej lokalizacji.",
    "plan_project_mismatch": "Wynik należy do innego projektu.",
    "unknown_allocation_node": "Przydział wskazuje nieznany węzeł.",
    "duplicate_allocation_node": "Węzeł ma więcej niż jeden przydział.",
    "allocation_family_mismatch": "Przydział ma niewłaściwą rodzinę adresów.",
    "allocation_parent_missing": "Brakuje przydziału rodzica.",
    "allocation_outside_parent": "Przydział nie mieści się w rodzicu.",
    "pinned_allocation_changed": "Przydział różni się od przypiętej sieci.",
    "invalid_segment_allocation": "Przydział segmentu nie spełnia jego wymagań.",
    "missing_segment_allocation": "Segment nie otrzymał przydziału.",
    "allocation_overlap": "Podsieci kolidują ze sobą.",
    "empty_project_id": "Brakuje identyfikatora projektu.",
    "empty_project_name": "Brakuje nazwy projektu.",
    "empty_node_id": "Brakuje identyfikatora węzła.",
    "empty_node_name": "Brakuje nazwy węzła.",
    "duplicate_node_id": "Identyfikator węzła powtarza się.",
    "negative_sort_order": "Kolejność nie może być ujemna.",
    "segment_data_missing": "Brakuje danych segmentu.",
    "site_has_parent": "Lokalizacja nie może mieć rodzica.",
    "missing_parent": "Nie znaleziono rodzica węzła.",
    "invalid_parent_kind": "Budynek musi należeć do lokalizacji, a segment do budynku.",
    "parent_cycle": "Relacje rodziców tworzą cykl.",
    "v6_pool_missing": "Przypięto IPv6 bez ustawienia puli projektu.",
    "invalid_v6_pool": "Nieprawidłowa pula IPv6.",
    "unsupported_v6_pool": (
        "Planer wymaga puli GUA, lokalnie nadanej ULA fd00::/8 albo dokumentacyjnej."
    ),
    "v6_kind_mismatch": "Rodzaj puli IPv6 nie odpowiada jej adresowi.",
    "invalid_v6_settings": (
        "Niespójne ustawienia IPv6; sprawdź prefiksy poziomów i bramę link-local."
    ),
    "invalid_v6_segment_settings": "Nieprawidłowe ustawienia IPv6 segmentu.",
    "v6_disabled_with_pin": "Segment ma przypięte IPv6, mimo że IPv6 jest wyłączone.",
    "v6_pin_family_mismatch": "Przypięcie IPv6 ma inną rodzinę adresów.",
    "v6_pin_outside_project": "Przypięcie IPv6 wykracza poza pulę projektu.",
    "invalid_v6_pin_prefix": "Przypięcie IPv6 ma prefiks niezgodny z rolą węzła.",
    "duplicate_v6_infrastructure_pin": "Powtórzone przypięcie infrastruktury lokalizacji.",
    "invalid_v6_infrastructure_pin": (
        "Nieprawidłowe przypięcie infrastruktury lub jej trzech pul /64."
    ),
    "unexpected_v6_allocations": "Plan zawiera IPv6, choć projekt nie ma puli IPv6.",
    "v6_site_anchor_span": "Przypięte dzieci nie mieszczą się w skonfigurowanym bloku lokalizacji.",
    "v6_building_anchor_span": (
        "Przypięte LAN-y wymagają większego bloku budynku niż dozwolone /52."
    ),
    "v6_building_capacity": "Zapotrzebowanie na /64 przekracza dozwolony rozmiar budynku.",
    "v6_building_pin_too_small": "Przypięty blok budynku IPv6 jest za mały.",
    "v6_vlan_required_1_999": "Numeracja IPv6 cyframi hex wymaga VLAN-u od 1 do 999.",
    "v6_vlan_offset_outside_building": (
        "Offset VLAN-u odczytany jako hex nie mieści się w budynku IPv6."
    ),
    "v6_vlan_pin_mismatch": "Przypięty LAN IPv6 nie odpowiada numeracji VLAN jako hex.",
    "v6_pin_outside_parent": "Przypięcie IPv6 nie mieści się w rodzicu.",
    "v6_subnet_collision": "Przypięte podsieci IPv6 kolidują ze sobą.",
    "v6_unknown_infrastructure_site": "Infrastruktura wskazuje nieznaną lokalizację.",
    "v6_duplicate_infrastructure": "Lokalizacja ma powtórzoną infrastrukturę IPv6.",
    "v6_infrastructure_family_mismatch": "Pule infrastruktury mają nieprawidłową rodzinę adresów.",
    "v6_invalid_segment_allocation": "Podsieć IPv6 nie odpowiada roli segmentu.",
    "v6_invalid_building_capacity": "Budynek IPv6 nie mieści wymaganego zapasu /64.",
    "v6_invalid_site_allocation": "Przydział IPv6 lokalizacji ma nieprawidłowy rozmiar.",
    "v6_infrastructure_missing": "Brakuje wydzielonej infrastruktury IPv6 lokalizacji.",
    "v6_infrastructure_outside_site": "Infrastruktura IPv6 nie mieści się w lokalizacji.",
    "v6_pinned_infrastructure_changed": "Pule infrastruktury różnią się od zamrożonych.",
    "v6_building_infrastructure_overlap": "Blok budynku nachodzi na infrastrukturę IPv6.",
}
REASONS = {
    "a LAN segment must need at least one usable address": (
        "LAN/mgmt wymaga co najmniej jednego użytecznego adresu."
    ),
    "gateway=none requires gateway_addrs=0": "Brama none wymaga gateway_addrs=0.",
    "gateway=first/last requires between one and three addresses": (
        "Brama first/last wymaga od 1 do 3 adresów."
    ),
    "infrastructure roles cannot apply host growth": "P2P i loopback nie stosują zapasu hostów.",
    "infrastructure roles cannot have a gateway": "P2P i loopback nie mają bramy.",
    "infrastructure roles cannot reserve gateway or static addresses": (
        "P2P i loopback nie rezerwują bram ani puli statycznej."
    ),
    "usable address requirement exceeds IPv4 capacity": (
        "Zapotrzebowanie przekracza całą przestrzeń IPv4."
    ),
    "network has insufficient usable addresses": "W podsieci brakuje użytecznych adresów.",
    "network is too small for segment requirements": (
        "Podsieć jest za mała dla zapotrzebowania segmentu."
    ),
    "P2P links require a /30 or /31 network": "Łącze P2P wymaga /30 albo /31.",
    "loopbacks require a /32 network": "Loopback IPv4 wymaga /32.",
    "p2p requires 2 endpoints or hosts=0 (unspecified)": (
        "P2P wymaga hosts=2 albo hosts=0 (liczba domyślna)."
    ),
    "loopback requires 1 endpoints or hosts=0 (unspecified)": (
        "Loopback wymaga hosts=1 albo hosts=0 (liczba domyślna)."
    ),
    "a blocked subnet must fit in the project pool of the same family": (
        "Blokada musi mieścić się w puli projektu tej samej rodziny."
    ),
    "a blocked subnet must belong to the project, a site or a building": (
        "Blokadę przypisz do projektu, lokalizacji albo budynku."
    ),
    "building requires more /64 subnets than a /52 can hold": (
        "Zapas i liczba LAN-ów wymagają więcej /64 niż mieści /52."
    ),
}
DETAIL_LABELS = {
    "range": "zakres",
    "network": "sieć",
    "parent_id": "rodzic",
    "site_id": "lokalizacja",
    "vlan_id": "VLAN",
    "count": "liczba",
    "other_node_id": "drugi węzeł",
    "requested_prefix": "wymagany prefiks",
    "required_prefix": "wymagany prefiks",
    "free_addresses": "wolne adresy",
    "largest_free_prefix": "największy wolny prefiks",
    "required_addresses": "wymagane adresy",
    "required_usable": "wymagane użyteczne",
    "usable_capacity": "pojemność użyteczna",
    "usable_needed": "wymagane użyteczne",
    "capacity_lower_bound_prefix": "dolne oszacowanie prefiksu",
    "suggested_pool_prefix": "sugerowany prefiks puli",
    "pool_kind": "rodzaj puli",
    "actual_kind": "rozpoznany rodzaj",
    "continuity": "ciągłość",
}
