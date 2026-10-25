# Format projektu JSON

Plik JSON to przenośna kopia projektu. Eksport zapisuje wersję formatu 3; import przyjmuje też wersje 1 i 2. Pełny schemat (JSON Schema 2020-12) jest w [`src/adresplan/schemas/project-v3.schema.json`](../src/adresplan/schemas/project-v3.schema.json).

```json
{
  "schema_version": 3,
  "project": { "id": "demo", "name": "Biuro", "v4_pool": "10.0.0.0/16", "nodes": [] },
  "plan": { "...": "wynik poglądowy" }
}
```

**Źródłem prawdy jest `project`.** Obiekt `plan` jest tylko podglądem: import go ignoruje i zawsze liczy wynik od nowa. Żeby zachować adres, ustaw przypięcie (`pinned_v4`, `pinned_v6`) albo zamroź projekt.

## Projekt

| Pole | Opis |
| --- | --- |
| `id`, `name`, `v4_pool` | Wymagane. `id` to stały identyfikator, którego import nie zmienia |
| `nodes` | Lista lokalizacji, budynków i segmentów |
| `settings` | Reguły planowania; eksport zapisuje je zawsze w całości |
| `v6_prefix`, `v6_kind` | Pula IPv6 i jej rodzaj: `doc`, `ula` albo `gua` |
| `v6_active` | `false` wstrzymuje planowanie IPv6, ale zachowuje jego ustawienia |
| `blocked_subnets` | Zajęte podsieci: `network`, `parent_id` (`null` = cały projekt), `note` |
| `pinned_v6_infrastructure` | Zamrożone pule infrastruktury IPv6 lokalizacji |
| `author`, `organization`, `description`, `document_date` | Opcjonalne dane do dokumentacji |

Sieci zapisuje się z prefiksem, np. `10.42.0.0/20` albo `2001:db8:42::/48`. Ustawione bity hosta (`10.42.0.1/24`) są błędem — program nie poprawia ich po cichu.

## Węzły

Każdy węzeł ma `id`, `name` i `kind`:

- `site` — lokalizacja, bez rodzica,
- `building` — budynek; `parent_id` wskazuje lokalizację,
- `segment` — sieć urządzeń; `parent_id` wskazuje budynek.

Wspólne pola opcjonalne: `sort_order`, `pinned_v4`, `pinned_v6`, `notes`. Segment ma dodatkowo:

| Pole | Domyślnie | Wartości |
| --- | --- | --- |
| `role` | `lan` | `lan`, `mgmt`, `p2p`, `loopback` |
| `hosts` | `0` | liczba urządzeń bez bram i adresów statycznych |
| `growth_pct` | z projektu | zapas w procentach |
| `gateway` | z projektu | `first`, `last`, `none` |
| `gateway_addrs` | z projektu | 0–3 |
| `static_count` | `0` | dodatkowe adresy statyczne |
| `vlan_id` | brak | 1–4094 |
| `v6_enabled` | `true` | czy segment dostaje IPv6 |
| `ra_mode` | z projektu | `slaac`, `dhcpv6` |

## Ustawienia domyślne

Zapas 25%, brama na początku podsieci, jeden adres bramy, łącza P2P /31. IPv6: lokalizacja /48, budynek /56, infrastruktura /56, zapas 100%, kolejne podsieci, brama globalna (`fe80::1` w trybie link-local), tryb SLAAC.

## Walidacja

Są dwa poziomy kontroli:

1. **Format** — brak wymaganych pól, literówki w nazwach pól, złe typy, błędne CIDR, powtórzone identyfikatory albo cykle w drzewie. Plik zostaje odrzucony z komunikatem i ścieżką, np. `project.nodes[2].hosts`.
2. **Plan** — dane są poprawne, ale np. brakuje miejsca albo przypięcia kolidują. Projekt wczytuje się normalnie, a wynik ma `is_complete: false` i listę błędów.

Liczby muszą być liczbami: `"20"`, `20.0` i `true` nie zastąpią `20`. Plik musi być w UTF-8 i mieć najwyżej 16 MiB. Powtórzone klucze, `NaN` i `Infinity` są odrzucane.

## Wynik

Obiekt `plan` zawiera przydziały IPv4 i IPv6, rezerwacje (bramy, zakresy statyczne i DHCP), informacje IPv6, infrastrukturę, wolne bloki, metryki wykorzystania, diagnostykę oraz `is_complete`. Liczby adresów są dokładnymi liczbami całkowitymi; dla IPv6 bywają większe, niż dokładnie obsłuży typ `Number` w JavaScripcie.

Eksport jest powtarzalny: ten sam projekt daje ten sam plik, bez dat i losowych identyfikatorów.

## Użycie w Pythonie

```python
from adresplan.application.project_json import dumps_project, load_project, save_project

state = load_project("examples/church-av.json")  # ProjectState(project, plan)
print(state.plan.is_complete)
save_project("kopia.json", state.project)
```

`save_project` najpierw sprawdza projekt, potem zapisuje plik tymczasowy i dopiero wtedy zastępuje docelowy, więc błąd nie uszkodzi istniejącego pliku.
