# Etap 3 — odbiór i weryfikacja

Data: 2026-10-14. Wersja deweloperska: `0.1.0.dev3`.

## Zakres

Ukończono hierarchiczny planer IPv6, numerowanie sequential i VLAN decimal-as-hex, pulę infrastruktury, informacje o bramie/RA, reverse DNS, generator ULA oraz wspólne zamrażanie obu protokołów. `core.plan.build_plan` łączy niezależne wyniki IPv4 i IPv6. `core.plan6.build_plan_v6` pozwala sprawdzić samą część IPv6.

Nie rozpoczęto etapu 4. Nadal nie ma pełnego CLI, importu/eksportu projektu, kalkulatora użytkownika ani interfejsu w przeglądarce. Do sprawdzenia funkcji służy przykład terminalowy `examples/stage3_ipv6.py`.

## Wyniki lokalne

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.11.0 / pytest | 315 zaliczonych |
| Windows / Python 3.12.14 / pytest | 315 zaliczonych |
| mypy --strict dla core | Bez uwag, 13 plików |
| Ruff — lint i formatowanie | Bez uwag |
| pip check | Brak konfliktów zależności |
| Wektory referencyjne | T1–T5 zgodne |
| Pakiet sdist/wheel | Zbudowany i sprawdzony po oddzielnej instalacji |

Zdalnego CI nie uruchamiano; istniejący workflow obejmuje nowe moduły i testy. Dodano 112 pozycji testowych względem etapu 2. Dwa pełne testy właściwościowe IPv6 mają limit 80 przykładów, pozostałe korzystają z profilu do 200. Liczba 315 oznacza pozycje pytest, a nie liczbę losowań.

T5 obejmujący oba protokoły, trzy budynki, po siedem LAN-ów, dwa łącza i loopback: 100 przeliczeń na lokalnym Pythonie 3.12.14 dało medianę około 7,0 ms i maksimum około 9,8 ms. To wynik pomiaru na tym komputerze.

## Dokładny wynik T5

| Obiekt | Przydział |
| --- | --- |
| Lokalizacja | 2001:db8:abcd::/48 |
| Infrastruktura | 2001:db8:abcd::/56 |
| Rezerwa | 2001:db8:abcd::/64 |
| Pula P2P | 2001:db8:abcd:1::/64 |
| Pula loopbacków | 2001:db8:abcd:2::/64 |
| Budynek A | 2001:db8:abcd:100::/56 |
| Budynek B | 2001:db8:abcd:200::/56 |
| Budynek C | 2001:db8:abcd:300::/56 |
| LAN-y A | …:100::/64 do …:106::/64 |
| Łącza | …:1::/127 i …:1::2/127 |
| Loopback | …:2::/128 |

Strategia VLAN w A: 10 → `…:110::/64`, 20 → `…:120::/64`, 99 → `…:199::/64`. VLAN 110 jest offsetem 272 i daje błąd w /56. Po jawnym wybraniu budynków /52 mieści się w bloku A `…:1000::/52`, jako `…:1110::/64`. Zmiana numeracji nie przenosi istniejącego przypięcia; sprzeczność jest błędem.

## Reguły planowania i przypięć

- Lokalizacje mają skonfigurowany prefiks, domyślnie /48. Dwie lokalizacje /48 nie mieszczą się w jednej puli /48. Test większej puli /44 sprawdza rozłączne lokalizacje /48.
- Domyślny budynek ma minimum /56. Przy ustawieniu /60 można używać mniejszych bloków; przy większej liczbie LAN-ów lub przypięciach rozmiar rośnie do /56 albo /52. Zapas jest liczony w podsieciach /64, nie w adresach hostów.
- Pula /56 wymaga jawnego układu, np. lokalizacja /56, infrastruktura /60 i budynki /60. Nieprawidłowa konfiguracja daje błąd, bez automatycznej zmiany ustawień.
- LAN/mgmt otrzymuje dokładnie /64. Łącza otrzymują /127 z puli P2P lokalizacji, loopbacki /128 z osobnej puli. Bloki infrastruktury są oddzielone od budynków.
- Miejsce nieprzypiętych węzłów uwzględnia przypięte dzieci. Przypięcia poza pulą, nieprawidłowe długości prefiksów, złe rodziny adresów i kolizje są błędami.
- IPv6 można wyłączyć w segmencie, pozostawiając jego IPv4. Wyłączenie przypiętego IPv6 wymaga jawnego usunięcia przypięcia.
- Po zamrożeniu przechowywane są przypięcia IPv4, IPv6 i `Project.pinned_v6_infrastructure`. Późniejsza zmiana zapotrzebowania musi mieścić się także w wymaganej rezerwie rozwoju istniejącego bloku.

Pierwsze /64 infrastruktury jest zarezerwowane. Przy sprawdzaniu całego pokrycia puli dodajemy końcowe segmenty, tę rezerwę oraz wszystkie wolne bloki. Rodzice nie są liczeni jako dodatkowe rozłączne przydziały. Metryki i wolne bloki IPv6 mają `pool_kind`, co rozróżnia lokalizację, budynek, infrastrukturę, P2P i loopback nawet przy wspólnym `parent_id`.

## Powtarzalność, pamięć i ULA

Rdzeń nie ma I/O ani źródeł losowości. Wszystkie operacje sieciowe wykorzystują `ipaddress`. Generator w `application.ula` pobiera dokładnie pięć losowych bajtów i przekazuje je czystej funkcji `core.ipv6.ula_from_global_id`. Wynik ma `fd` + 40-bitowy Global ID i prefiks /48. [RFC 4193](https://www.rfc-editor.org/rfc/rfc4193.html)

Testy blokują wywołania `IPv6Network.hosts`, nadmierne rozwijanie iteratorów podsieci oraz losowanie podczas budowania planu. Podpule infrastruktury są wybierane przez `islice(..., 3)`; alokator pobiera pojedynczy pasujący blok, a numer VLAN-u jest zamieniany na offset bez enumerowania /64.

Reverse DNS jest wyznaczany dla prefiksów wyrównanych do czterech bitów. /127 nie jest przedstawiany jako zwykła strefa delegacji; rekordy segmentów infrastruktury zawierają konkretne adresy końców. Obie formy adresu są dostępne przez `IPv6SegmentInfo.compressed` i `.exploded`.

Brama informacyjna LAN to `prefiks::1` lub konfigurowany adres link-local, domyślnie `fe80::1`. SLAAC/DHCPv6 jest metadanymi projektu. Router domyślny w działającej sieci jest odkrywany przez Router Advertisement z adresem link-local routera. [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html#section-6.3.4)

## Zamrażanie i regresja

Testy obejmują niezmienność wejścia, idempotencję, odrzucanie nieaktualnego lub zmodyfikowanego planu, zmianę strategii VLAN, pełną pulę lokalizacji i sprzeczne zmiany infrastruktury. Dodanie LAN-u, łącza i loopbacka po zamrożeniu daje `…:107::/64`, `…:1::4/127`, `…:2::1/128`, zachowując wcześniejsze adresy obu protokołów i pule infrastruktury.

Dotychczasowy test zachowania opisów i pól IPv6 z etapu 2 otrzymał poprawne przypięcie LAN w `…:100::/64`. Stare testowe `…:1::/64` należy teraz do infrastruktury, której etap 2 jeszcze nie obliczał. Cel testu — zachowanie opisów, ustawień i istniejącego poprawnego przypięcia — pozostał bez zmian.

## Odtworzenie

```powershell
.\.venv\Scripts\python.exe examples/stage3_ipv6.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy --strict src/adresplan/core
```
