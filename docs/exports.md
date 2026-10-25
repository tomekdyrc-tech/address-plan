# Eksporty

Każdy eksport liczy plan od nowa z danych projektu. Wynik zapisany wcześniej w pliku nigdy nie jest źródłem adresów. Raporty powstają w języku wybranym w interfejsie albo opcją `--lang` w [CLI](cli.md).

| Format | Do czego służy |
| --- | --- |
| Markdown | Czytelny raport, np. do repozytorium na GitHubie |
| CSV | Tabela segmentów do arkusza |
| XLSX | Raport w Excelu z kilkoma arkuszami |
| DOCX | Raport w Wordzie, gotowy do druku |
| JSON | Kopia projektu do ponownego importu |
| Cisco IOS, MikroTik | Konfiguracja startowa bramy w każdym budynku |
| SVG | Diagram hierarchii (z widoku Diagram w przeglądarce) |

Plan niekompletny też można wyeksportować. Dokument ma wtedy wyraźny status, zawiera udane przydziały i listę błędów, a CLI kończy się kodem 1.

Pliki są zapisywane bezpiecznie: najpierw powstaje plik tymczasowy, a dopiero potem zastępuje docelowy. Raport CSV lub Markdown nie może nadpisać źródłowego pliku JSON.

## Markdown

Zawiera status, założenia i ustawienia, lokalizacje i budynki, dla każdego budynku tabele segmentów z adresacją IPv4 i IPv6, infrastrukturę IPv6, wykorzystanie pul, wolne bloki i pełną walidację. Nazwy wpisane przez użytkownika są cytowane, więc nie zepsują tabeli ani nie wstawią HTML.

Przykłady: [raport sieci AV](../examples/exports/church-av.md), [raport T4](../examples/exports/t4-hierarchy.md).

## CSV

Jeden wiersz na segment, z nazwą lokalizacji i budynku. Kolumny obejmują VLAN, rolę, liczby hostów, adresację IPv4 (CIDR, maska, brama, zakresy statyczny i DHCP, broadcast), IPv6 (CIDR, brama, tryb RA, końce łącza, reverse DNS), uwagi i komunikaty walidacji.

Plik ma separator `;`, kodowanie UTF-8 z BOM i wszystkie pola w cudzysłowach. Tekst zaczynający się od `=`, `+`, `-` lub `@` dostaje apostrof na początku, żeby arkusz nie potraktował go jak formuły. CSV jest dokumentacją, nie służy do importu.

## XLSX i DOCX

XLSX ma arkusze Plan, Podsumowanie, Wolne bloki i Walidacja, a przy blokadach także arkusz Blokady. Wszystkie komórki są tekstem: długie adresy IPv6 nie są zaokrąglane, a formuły nie są wykonywane. Nagłówki są zamrożone i mają filtry.

DOCX to raport A4 w poziomie: założenia, ustawienia, tabele IPv4 i IPv6 dla każdego budynku, infrastruktura, wolne bloki i walidacja. Strony są numerowane.

Oba formaty mają profil **skrócony** (same przydziały dla odbiorcy) i **szczegółowy** (dla administratora). Pliki Office wymagają w CLI opcji `-o`.

## JSON

Ten sam format co `plan --json`: pełne dane projektu i świeżo obliczony wynik (`schema_version` 3). To jedyny format do ponownego importu i do przechowywania zamrożonych adresów. Szczegóły: [format JSON](json-format.md).

## Konfiguracja Cisco IOS i MikroTik

Generator tworzy szkic konfiguracji bramy dla każdego budynku:

- dla segmentu z numerem VLAN: VLAN i interfejs VLAN z adresem bramy,
- dla sieci LAN: serwer DHCP z zakresem z planu (adresy bram i statyczne są wyłączone z puli),
- dla loopbacków: interfejs loopback z adresem /32,
- dla IPv6: adres bramy, ogłaszanie prefiksu, a przy DHCPv6 odpowiednie flagi RA.

Program nie zna fizycznych portów urządzenia. Dlatego łącza P2P i segmenty bez VLAN-u są wypisane jako zakomentowane szablony z miejscem `<INTERFACE>` do uzupełnienia. W MikroTiku interfejsy VLAN powstają na interfejsie `bridge`.

Cała konfiguracja jest w ASCII (np. „Dźwięk” → `Dzwiek`). Nazwy z projektu są zamieniane na bezpieczne identyfikatory, a opisy na jedną linię, więc tekst wpisany przez użytkownika nie może dodać własnego polecenia.

To punkt wyjścia, nie gotowa konfiguracja produkcyjna. Przed wgraniem sprawdź nazwy interfejsów, trunki, zabezpieczenia i ustawienia DHCP.

```powershell
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f cisco -o output/brama.txt
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f mikrotik -o output/brama.rsc
```
