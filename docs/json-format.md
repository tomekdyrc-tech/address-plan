# Format projektu JSON — wersja 3 (import również wersji 1 i 2)

Stan: 16.10.2026, aplikacja 1.1.0. Format jest dostępny w bibliotece, przykładzie `examples/stage4a_json.py` oraz poleceniach `plan`, `freeze` i `export --format json`. Przykłady obsługi własnego pliku: [instrukcja CLI](cli.md).

## Najpierw uruchom przykład

Z głównego folderu projektu, w PowerShell:

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/stage4a_json.py
```

Wejście to `examples/stage4a_project.json`, zawierające wyłącznie sztuczne dane sieci AV. Skrypt zapisuje dwa pliki w ignorowanym przez Git folderze `.tmp/stage4a/`:

- `project.json` — dane wejściowe i aktualny wynik;
- `project-frozen.json` — projekt z przypiętymi adresami IPv4/IPv6 i infrastrukturą IPv6, razem z wynikiem.

Skrypt porównuje projekt i plan po ponownym wczytaniu. Kończy się błędem, jeśli cokolwiek się zmieniło. Możesz zmienić np. `hosts` w pliku przykładowym i ponownie uruchomić demonstrację. Kolejne uruchomienie zastępuje poprzednie pliki wynikowe; nie zmienia wejścia.

## Koperta dokumentu

| Pole | Wymagane | Znaczenie |
| --- | --- | --- |
| `schema_version` | Tak | Liczba całkowita `1`, `2` lub `3`; eksport zapisuje `3`; nie tekst `"1"`, nie `true` |
| `project` | Tak | Dane wejściowe projektu |
| `plan` | Nie | Obiekt z wyliczonym wynikiem lub `null`; import ignoruje zawartość tego obiektu |

`schema_version` jest wersją formatu danych, niezależną od wersji aplikacji, obecnie `1.1.0`. Brak wersji i nieobsługiwane wersje są odrzucane. Import wersji 1 stosuje pustą listę blokad.

**Źródłem prawdy jest `project`.** Zmiana przydziału w `plan` nie przypina podsieci. Aby zachować adres, ustaw `pinned_v4`/`pinned_v6` w odpowiednim węźle albo skorzystaj z zamrażania. Po imporcie wynik jest zawsze obliczany ponownie ze wszystkich danych wejściowych. Nie jest odtwarzany z zapisanej tabeli.

## Dane projektu

Wymagane są `id`, `name` i `v4_pool`. `id` jest trwałym identyfikatorem, nie nazwą wyświetlaną. Import nigdy go nie losuje ani nie zmienia. Identyfikatory węzłów muszą być unikalne w projekcie.

| Pole | Domyślnie / znaczenie |
| --- | --- |
| `nodes` | Pusta tablica; kolejność elementów jest zachowywana |
| `settings` | Domyślne ustawienia planera z etapów 1–3 |
| `v6_prefix` | `null`, czyli brak puli IPv6 |
| `v6_active` | `true` dla zgodności starszych plików; `false` zawiesza planowanie IPv6 i zachowuje jego konfigurację |
| `v6_kind` | `doc`; dopuszczalne: `doc`, `ula`, `gua` |
| `pinned_v6_infrastructure` | Pusta tablica; zamrożone pule infrastruktury lokalizacji |

Sieci są tekstem z prefiksem, np. `10.42.0.0/20`, `2001:db8:42::/48`. Parser korzysta z `ipaddress` i nie zeruje po cichu bitów hosta: `10.42.0.1/24` jest błędem. Adresy innej rodziny i numeryczne reprezentacje adresów są odrzucane. Zapis IPv6 jest normalizowany do formy skróconej. Projekt zachowuje wartości sieci; nie zachowuje alternatywnego formatowania tekstu wejściowego.

## Drzewo: lokalizacja → budynek → segment

Każdy węzeł ma `id`, `name` i `kind`. Dopuszczalne rodzaje:

- `site` — lokalizacja, bez rodzica;
- `building` — budynek, z `parent_id` wskazującym lokalizację;
- `segment` — segment, z `parent_id` wskazującym budynek.

Wspólne pola opcjonalne: `sort_order=0`, `pinned_v4=null`, `pinned_v6=null`, `notes=""`. Identyfikatory i nazwy nie mogą być puste ani złożone wyłącznie z białych znaków. Import nie przycina nazw i opisów. Rodzic może występować później w tablicy; ważny jest identyfikator, a nie pozycja.

Segment ma dodatkowo:

| Pole | Domyślnie | Reguła wejścia |
| --- | --- | --- |
| `role` | `lan` | `lan`, `mgmt`, `p2p`, `loopback` |
| `hosts` | `0` | Nieujemna liczba całkowita |
| `growth_pct` | `null` | Nieujemna liczba całkowita albo dziedziczenie |
| `gateway` | `null` | `first`, `last`, `none` albo dziedziczenie |
| `gateway_addrs` | `null` | Liczba całkowita 0–3 albo dziedziczenie |
| `static_count` | `0` | Nieujemna liczba całkowita |
| `vlan_id` | `null` | Liczba całkowita 1–4094 albo brak VLAN-u |
| `v6_enabled` | `true` | Wartość logiczna JSON |
| `ra_mode` | `null` | `slaac`, `dhcpv6` albo dziedziczenie |

Pole `hosts` oznacza urządzenia poza osobno rezerwowaną pulą statyczną i bramami. Reguły zależne od roli oraz wzajemna zgodność ustawień są sprawdzane przez istniejący planer. LAN z zerowym zapotrzebowaniem, VLAN 110 w numeracji hex w budynku /56 albo za mała pula nie stają się poprawne tylko dlatego, że da się je zapisać w JSON-ie.

## Ustawienia i zamrożenie

Eksport zapisuje wszystkie ustawienia jawnie, także domyślne: zapas hostów 25%, bramę `first`, jeden adres bramy, P2P /31; IPv6: lokalizację /48, budynek /56, infrastrukturę /56, zapas 100%, numerację `sequential`, bramę `global`, adres link-local `fe80::1` i tryb `slaac`.

Pełna lista pól i dopuszczalnych wartości znajduje się w `src/adresplan/schemas/project-v3.schema.json`. Pola prefiksów lokalizacji i infrastruktury IPv6 muszą być wielokrotnością 4 do /60. Budynki dopuszczają /52, /56 i /60. Relacje pomiędzy nimi i pulą projektu sprawdza planer; nie zmienia ich automatycznie przy imporcie.

Zamrożony projekt zawiera przypięcia w węzłach i tablicę `pinned_v6_infrastructure`. Każdy jej wpis ma `site_id`, `network`, `reserved_pool`, `p2p_pool`, `loopback_pool`. Zachowywane są wszystkie te pola. Wczytanie takiego projektu nie przydziela infrastruktury od nowa. Import sam w sobie nie zamraża projektu.

ULA jest zapisywana jako konkretne `v6_prefix` i `v6_kind="ula"`. Import ani eksport nie losuje nowego prefiksu.

## Walidacja i błędy

Są dwa poziomy kontroli:

1. **Format i struktura:** brak wymaganych pól, literówki w nazwach pól, nieprawidłowe typy/liczby/CIDR, duplikaty identyfikatorów, brak rodzica i cykle powodują `ProjectJSONError`. Błąd ma stabilny kod, polski komunikat i ścieżkę, np. `project.nodes[2].hosts`. Indeksy tablic zaczynają się od zera.
2. **Plan sieci:** poprawne typy i drzewo mogą nadal oznaczać brak miejsca, kolizję przypięć lub niespójne ustawienia. Import zwraca projekt oraz plan z diagnostyką i `is_complete=false`. Taki projekt można zapisać i dalej poprawiać. Zamrożenie wymaga kompletnego planu.

Liczby muszą być liczbami: `"20"`, `20.0` i `true` nie zastępują całkowitego `20`. Pola logiczne przyjmują `true`/`false`, bez cudzysłowów. Nieznane pola wejścia są błędem; zapobiega to pomijaniu literówek, np. `host` zamiast `hosts`. Zawartość opcjonalnego obiektu `plan` może mieć starszy kształt, ponieważ nie jest używana do obliczeń.

Wejście musi być poprawnym JSON-em UTF-8, opcjonalnie z BOM, o rozmiarze do 16 MiB. Brak komentarzy i przecinków na końcu list. Powtórzone klucze, NaN, Infinity, przepełnienie liczb zmiennoprzecinkowych oraz nieprawidłowe znaki Unicode w danych projektu są odrzucane. Eksport używa UTF-8 bez BOM i końców linii LF.

## Co zawiera wynik

Eksport `plan` zawiera wszystkie pola rekordu rdzenia `Plan` oraz `is_complete`: alokacje obu protokołów, wolne bloki z poziomem/rodzicem, diagnostykę, rezerwacje IPv4, metryki obu rodzin, infrastrukturę IPv6 i informacje o segmentach IPv6. Sieci i adresy są tekstem, a enumy swoimi wartościami, np. `warning`.

Liczby adresów są zapisywane jako dokładne całkowite liczby JSON. W IPv6 przekraczają zakres dokładnych liczb całkowitych zwykłego JavaScript `Number`; zewnętrzny odbiorca musi uwzględniać tę cechę. Python zachowuje je dokładnie. Właściwości wyliczane pomocniczo, np. `utilization`, nie są osobnymi polami migawki — dostępne są dane potrzebne do ich obliczenia.

Eksport jest deterministyczny dla tego samego projektu i wersji algorytmu: nie dodaje daty, losowych identyfikatorów ani nowej ULA. Ponowny import nie gwarantuje identycznego wyniku po przyszłej zmianie algorytmu; przypięcia pozostają jawnym wejściem i ograniczeniem planera.

## API biblioteki i zapis pliku

W `adresplan.application.project_json` dostępne są:

| Funkcja | Wynik |
| --- | --- |
| `loads_project(text_or_bytes)` | `ProjectState(project, plan)` |
| `load_project(path)` | To samo, z pliku |
| `dumps_project(project)` | Tekst JSON z nowo przeliczonym planem |
| `save_project(path, project)` | Walidacja i zapis pliku |

Eksporter udostępnia te same funkcje zapisu przez `adresplan.export.json_`. Nie ma drugiej implementacji formatu. Żadna z tych funkcji nie przyjmuje gotowego planu do zapisania jako prawdy.

Zapis najpierw waliduje projekt i tworzy pełną treść, potem zapisuje plik tymczasowy w tym samym katalogu i zastępuje plik docelowy. Nie ucina wcześniej istniejącego pliku. Testy sprawdzają zachowanie poprzedniej zawartości przy błędzie walidacji i przy zablokowanej podmianie. Katalog docelowy musi istnieć. Kolejny udany zapis pod tę samą ścieżkę zastępuje poprzedni plik.

Schemat Draft 2020-12 jest generowany z modeli Pydantic i dołączany do wheel. Test porównuje go z aktualnymi modelami. Schemat opisuje kształt wejścia; reguły zależne od innych pól i topologii są sprawdzane dodatkowo przez aplikację i rdzeń. Dokumentacja użytych mechanizmów: [typy ścisłe](https://docs.pydantic.dev/latest/concepts/strict_mode/), [modele rozróżniane polem rodzaju](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators), [generowanie JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/).

## Blokady od v1.1

Opcjonalne `project.blocked_subnets` jest listą obiektów: `{"network": "10.0.8.0/24", "parent_id": null, "note": "Kamery"}`. `network` przyjmuje ścisły CIDR IPv4 lub IPv6; `parent_id` wskazuje lokalizację/budynek, a `null` oznacza pulę projektu. Domyślnie lista jest pusta. Schemat v1 pozostaje dołączony jako historyczny, a aktualny walidator opisuje `project-v3.schema.json`. Historia i szablony są przechowywane w SQLite, poza eksportem pojedynczego projektu.

## Stan IPv6 w wersji 3

`v6_active=false` wyłącza obliczenia IPv6, zachowując `v6_prefix`, ustawienia, przypięcia węzłów, infrastrukturę i blokady. JSON przechowuje także konfigurację zawieszoną. Ponowne włączenie waliduje ją według aktualnej struktury. Raporty oznaczają rodzinę jako wyłączoną i nie pokazują zawieszonych blokad jako czynnych.

Import wersji 1/2 bez tego pola stosuje `true`, dzięki czemu dotychczasowa pula IPv6 nadal działa. Bez puli IPv6 przydziały nie powstają. Nowy projekt w interfejsie bez zgody na IPv6 zapisuje `false`. Starszy program obsługujący tylko format 2 nie odczyta eksportu 3. Schematy wersji 1 i 2 pozostają dołączone jako historyczne; bieżący to `project-v3.schema.json`. Bieżące tabele SQLite mają wersję 3 (biblioteka szablonów z koszem); dokumenty są normalizowane przy zapisie, a historyczne migawki zachowują swój format.

Opcjonalne pola dokumentacji projektu: `author`, `organization`, `description`, `document_date` (tekst; domyślnie puste). Są zachowywane w JSON i historii, ale nie zmieniają obliczeń adresacji.
