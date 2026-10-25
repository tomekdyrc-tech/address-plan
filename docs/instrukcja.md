# Instrukcja szczegółowa — Address Plan (AdresPlan)

Lokalny planer adresacji IPv4 VLSM i IPv6 dla lokalizacji, budynków i VLAN-ów.

Pełny opis funkcji, instalacji, przykładów i sprawdzeń. Krótkie podsumowanie projektu jest w [README](../README.md). Licencja: [MIT](../LICENSE).

## Nowości v1.1

- Historia i porównywanie planów, przywracanie jako nowej wersji.
- Duplikowanie budynków, gotowe zestawy obiektu podstawowego i rozbudowanego i własne szablony budynków oraz całych lokalizacji; wiele oddziałów można dodać z jednej listy nazw.
- Blokady zajętych podsieci IPv4/IPv6, import przez wklejenie listy CIDR.
- Diagram hierarchii adresacji i pobieranie SVG.

[Instrukcja v1.1 i aktualizacji danych](historia/release-v1.1.md) · [Wyniki 700 testów](historia/v1.1-verification.md).

## Usprawnienia pracy

Filtrowanie struktury, zarządzanie szablonami z koszem, pełna kopia biblioteki, podgląd skutków przed zapisem, projekt z kalkulatora VLSM, wyjaśnienia rozmiaru podsieci i dwa profile raportów. [Instrukcja i wynik 746 testów](historia/USPRAWNIENIA.md).

Po tych usprawnieniach wykonano [audyt zapisu i interfejsu](historia/AUDYT-2026-10-16.md): poprawiono pięć usterek; końcowy zestaw obejmuje 750 testów Pythona oraz cztery dodatkowe testy JavaScript.

## Co już działa

- Lokalny interfejs: projekty, import/duplikowanie, drzewo i tabela edycji, plan na żywo, walidacja z linkami, wykorzystanie pul, zamrażanie oraz generator ULA.
- Automatyczny zapis po 300 ms, transakcje SQLite i kontrola wersji chroniąca przed nadpisaniem zmian z drugiej karty.
- Kalkulator z tabelą VLSM według liczby urządzeń, polskimi opisami i osobnymi trybami sprawdzania adresu / równego podziału; podgląd eksportów w przeglądarce. FastAPI/Jinja2/HTMX z zasobami na tym komputerze, bez CDN.
- XLSX z czterema podstawowymi arkuszami i dodatkowym arkuszem blokad, raport DOCX z tabelami budynków oraz widok do druku/PDF.
- Motyw systemowy/jasny/ciemny, Tab/Enter, Ctrl+D w wierszu segmentu lub budynku i kopiowanie CIDR do schowka.
- Obliczanie najmniejszej podsieci LAN/mgmt z zapasem na rozwój, bramami i rezerwą statyczną.
- Obsługa łączy P2P /31 (lub /30) oraz loopbacków /32.
- Alokator best-fit dla obiektów `IPv4Network` i `IPv6Network`: największe potrzeby pierwsze, przypięte bloki przed automatycznymi.
- Walidacja przypięć: rodzina adresów, położenie, pojemność i kolizje.
- Zbieranie błędów bez przerywania pozostałych przydziałów; diagnostyka wolnej przestrzeni i propozycja większej puli.
- Powtarzalny wynik, stabilne identyfikatory, typowane modele i walidacja struktury drzewa.
- Hierarchia lokalizacja → budynek → segment, z jednym blokiem sumarycznym na lokalizację i budynek.
- Wyznaczanie bloków rodziców z uwzględnieniem adresów przypiętych segmentów i fragmentacji wolnego miejsca.
- Zakresy bram, adresów statycznych i DHCP, w tym 1–3 adresy bram oraz wariant bramy na końcu podsieci.
- Walidacja puli IPv4, VLAN-ów, pojemności, kolizji i zawierania podsieci; metryki wykorzystania i ciągłości wolnej puli.
- Hierarchia IPv6, domyślnie lokalizacja /48 → budynki /56 → LAN /64, z zapasem i jawną konfiguracją mniejszych pul.
- Dedykowana infrastruktura IPv6 dla rezerwy /64, łączy /127 i loopbacków /128.
- Numerowanie IPv6 sequential lub cyframi VLAN-u odczytanymi jako hex, walidacja przypięć i kolizji.
- Generator ULA, formy compressed/exploded, strefy ip6.arpa i informacje o bramie/trybie SLAAC lub DHCPv6.
- Czysta funkcja zamrażania obu rodzin i infrastruktury IPv6: kolejne segmenty korzystają z wolnych miejsc bez przesuwania dotychczasowych adresów.
- Testy referencyjne T1–T5 i testy właściwościowe.
- Wersjonowany JSON projektu, ścisła walidacja wejścia i ponowne obliczanie planu przy imporcie.
- Zapis kompletnego projektu i wyniku, w tym zamrożonych adresów obu rodzin i infrastruktury IPv6; atomowa podmiana pliku.
- Schemat JSON dołączony do pakietu, polskie błędy ze ścieżkami do pól i przykład importu/eksportu.
- Polecenia `plan`, `calc`, `freeze`, polska pomoc, diagnostyka i kody zakończenia.
- Kalkulator IPv4/IPv6: maska i wildcard, bity hosta, /31 i /32, reverse DNS, formy IPv6 i liczba /64.
- Leniwy podział przez liczbę podsieci lub docelowy prefiks, z limitem 256 wierszy.
- Eksport CSV z diagnostyką oraz raport Markdown z założeniami, budynkami, wolnymi blokami i walidacją.
- Projekty JSON odpowiadające T1–T5, numeracji VLAN hex, celowym błędom i syntetycznej sieci AV; gotowe przykładowe raporty.

Wspólny planer jest dostępny przez `adresplan.core.plan.build_plan`, zamrażanie przez `adresplan.core.freeze.freeze`, JSON przez `adresplan.application.project_json`, a kalkulator przez `adresplan.core.calc`. CLI, API i interfejs korzystają z tych samych obliczeń.

## Wymagania

- Python 3.11 lub nowszy; środowisko referencyjne: Python 3.12.
- Podstawy CIDR i VLSM do interpretacji wyników.
- Dostęp do Internetu przy pierwszej instalacji zależności. Warstwa JSON używa Pydantic 2; sam rdzeń nadal korzysta wyłącznie z biblioteki standardowej Pythona.

W poleceniach poniżej pracuj w folderze projektu. Jeśli `python --version` pokazuje inną wersję niż oczekiwana, użyj odpowiedniego interpretera, np. `py -3.12` na Windows, jeżeli jest zainstalowany.

## Instalacja na Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\adresplan.exe serve
```

Do korzystania z programu nie potrzebujesz narzędzi programistycznych. Jeśli chcesz uruchamiać testy lub zmieniać kod, zainstaluj środowisko deweloperskie:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
```

Nie trzeba aktywować środowiska ani zmieniać polityki wykonywania skryptów PowerShell.

Linux/macOS: `python3 -m venv .venv`, a w kolejnych poleceniach użyj `.venv/bin/python` zamiast `.\.venv\Scripts\python.exe`.

## Uruchomienie aplikacji

Otwórz **http://127.0.0.1:8000** po wykonaniu `serve`. Terminal pozostaje otwarty; `Ctrl+C` zatrzymuje serwer. Dane pozostają po ponownym uruchomieniu. Domyślna baza Windows: `%LOCALAPPDATA%\AddressPlan\adresplan.sqlite3`.

Możesz utworzyć własny projekt albo wybrać Import i plik `examples/church-av.json` lub `examples/budynek.json`. Edytuj hosty/VLAN-y bez pisania JSON. Zaczekaj na „Zapisano”, następnie obejrzyj wynik pod tabelą. W menu „Podgląd i eksport” pobierzesz raport lub kopię projektu JSON.

Inny plik bazy i port:

```powershell
.\.venv\Scripts\adresplan.exe serve --database data/projekty.sqlite3 --port 8080
```

Parametr `--database` ma pierwszeństwo przed zmienną `ADRESPLAN_DB`. Serwer słucha na `127.0.0.1`; po instalacji nie wymaga Internetu. Pełna instrukcja, kopie danych i API: [interfejs lokalny](web.md).

## Sprawdź przykład VLSM

```powershell
.\.venv\Scripts\python.exe examples/stage1_vlsm.py
```

Przykład T1 zakłada pulę `192.168.10.0/24`, zerowy zapas i brak bram/rezerwacji:

| Segment | Hosty | Przydzielona podsieć | Użyteczne adresy |
| --- | ---: | --- | --- |
| A | 100 | 192.168.10.0/25 | 192.168.10.1–192.168.10.126 |
| B | 50 | 192.168.10.128/26 | 192.168.10.129–192.168.10.190 |
| C | 25 | 192.168.10.192/27 | 192.168.10.193–192.168.10.222 |
| D | 10 | 192.168.10.224/28 | 192.168.10.225–192.168.10.238 |

Wolny pozostaje blok `192.168.10.240/28` (16 adresów).

## Sprawdź hierarchię i zamrażanie

```powershell
.\.venv\Scripts\python.exe examples/stage2_hierarchy.py
```

Przykład T4 pokazuje trzy budynki, wszystkie ich segmenty i wolne bloki. Wynik dla budynków:

| Budynek | Blok | Adresy w segmentach | Wolne wewnątrz budynku |
| --- | --- | ---: | ---: |
| A | 10.20.0.0/23 | 485 | 27 |
| B | 10.20.2.0/24 | 224 | 32 |
| C | 10.20.3.0/27 | 32 | 0 |

Skrypt zamraża plan i dodaje mały segment w budynku A. Nowy przydział to `10.20.1.232/30`, a dotychczasowe adresy pozostają bez zmian. Zamrożone bloki rodziców nie rosną automatycznie: brak miejsca daje błąd i wymaga świadomej zmiany przypięcia. Funkcja odrzuca zamrażanie planu niekompletnego, nieaktualnego albo pochodzącego z innego projektu.

Metryki są liczone oddzielnie dla każdego poziomu. W T4 budynki otrzymują łącznie bloki na 800 adresów, segmenty zajmują 741, wolne poza budynkami wynosi 3296, a wolne wewnątrz budynków 59. Tych poziomów nie sumujemy jako niezależnych alokacji. Metryka ciągłości to największy wolny blok podzielony przez całe wolne miejsce; przy braku wolnego miejsca ma wartość „n/d”.

## Sprawdź IPv6 i zamrażanie obu protokołów

```powershell
.\.venv\Scripts\python.exe examples/stage3_ipv6.py
```

Przykład T5 korzysta z `2001:db8:abcd::/48`:

| Obiekt | Przydział |
| --- | --- |
| Infrastruktura | 2001:db8:abcd::/56 |
| Budynki A, B, C | …:100::/56, …:200::/56, …:300::/56 |
| Pierwsze LAN-y budynku A | …:100::/64 do …:106::/64 |
| Łącza | …:1::/127, …:1::2/127 |
| Loopback | …:2::/128 |

Pierwszy /64 infrastruktury jest rezerwą, drugi pulą łączy, trzeci pulą loopbacków. W /48 mieszczą się 65 536 podsieci /64, w /56 — 256. IPv6 nie przydziela broadcastu.

Strategia `vlan_decimal_as_hex` daje w budynku A: VLAN 10 → `…:110::/64`, VLAN 20 → `…:120::/64`, VLAN 99 → `…:199::/64`. VLAN 110 oznacza offset `0x110` (272), więc w /56 daje błąd; mieści się w /52. Strategia obsługuje VLAN-y 1–999. Włączenie jej wymaga numeru VLAN dla każdego aktywnego LAN/mgmt. Przypięcie sprzeczne z numeracją jest zgłaszane jako błąd i nie jest automatycznie przenoszone.

Pula projektu /48 pomieści jedną lokalizację /48. Dla wielu takich lokalizacji potrzebna jest większa pula. Projekt /56 wymaga świadomego układu, np. lokalizacja /56, infrastruktura /60, budynki /60; ustawienia domyślne nie są zmieniane automatycznie. Wyłączenie IPv6 w segmencie zachowuje jego IPv4. Przed wyłączeniem przypiętego IPv6 należy jawnie usunąć jego przypięcie.

Skrypt zamraża adresy i dodaje LAN `…:107::/64`, łącze `…:1::4/127` oraz loopback `…:2::1/128`. Wypisuje potwierdzenie zachowania dotychczasowych adresów IPv4/IPv6 i pul infrastruktury. Pokazuje także formę rozwiniętą adresu, reverse DNS i nowy prefiks ULA. ULA jest losowana w warstwie aplikacji jako `fd` + 40 bitów Global ID; zapisany prefiks jest wejściem projektu, więc przeliczanie nie losuje go ponownie. [RFC 4193](https://www.rfc-editor.org/rfc/rfc4193.html)

Brama w tabeli to domyślnie adres interfejsu `prefiks::1`; opcja link-local pokazuje `fe80::1`. Tryb SLAAC/DHCPv6 jest informacją dla dokumentacji. W działającej sieci IPv6 host poznaje router domyślny przez Router Advertisement, używając jego adresu link-local. [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html#section-6.3.4)

## Sprawdź zapis i odczyt JSON

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/stage4a_json.py
```

Skrypt wczytuje sztuczny projekt sieci AV z `examples/stage4a_project.json`, wylicza adresację i zapisuje wynik. Następnie wczytuje go ponownie i sprawdza zgodność projektu oraz planu. Powtarza to dla zamrożonych adresów obu rodzin i infrastruktury IPv6. Wyniki znajdziesz w `.tmp/stage4a/project.json` oraz `.tmp/stage4a/project-frozen.json`; kolejne uruchomienie zastępuje te pliki. Parametr `-X utf8` zapewnia poprawne wypisywanie polskich znaków także przy przekierowaniu wyjścia na Windows.

Możesz zmienić `hosts` w pliku przykładowym i uruchomić demonstrację ponownie. Wpisuj liczbę, np. `20`, bez cudzysłowów. Format odróżnia dane wejściowe od migawki wyniku: importer zawsze liczy plan od nowa. Dokumentacja: [format JSON](json-format.md), [odbiór części 4A](historia/stage-4a-verification.md).

## Korzystaj z poleceń terminalowych

```powershell
.\.venv\Scripts\adresplan.exe --help
.\.venv\Scripts\adresplan.exe --version
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json
.\.venv\Scripts\adresplan.exe calc 192.168.1.10/24 --split 4
.\.venv\Scripts\adresplan.exe calc 2001:db8::/48 --new-prefix 64 --limit 4
```

Zapis planu i zamrożenia:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json --output output/plan.json
.\.venv\Scripts\adresplan.exe freeze examples/stage4a_project.json --output output/zamrozony.json
.\.venv\Scripts\adresplan.exe plan output/zamrozony.json
```

`plan --show-free` pokazuje wolne bloki, `plan --json` wypisuje dokument JSON, a `--verbose` dodatkową diagnostykę. Ostrzeżenia i błędy trafiają na stderr, dzięki czemu JSON na stdout pozostaje poprawnym dokumentem. Kody zakończenia: 0 — sukces lub ostrzeżenia; 1 — plan niekompletny; 2 — błędne dane/argumenty lub błąd pliku. `freeze` nie zapisze planu z błędami. Katalog wyjściowy musi istnieć; jawnie wskazany istniejący plik jest zastępowany.

Szczegółowe przykłady, interpretacja wyniku i reguły kalkulatora: [instrukcja CLI](cli.md). Polecenie `serve` otwiera możliwość pracy w przeglądarce.

## Eksport dokumentacji

```powershell
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format csv --output output/plan.csv
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format md --output output/plan.md
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format json --output output/projekt.json
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format xlsx --output output/plan.xlsx
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format docx --output output/plan.docx
```

Najpierw utwórz katalog `output`, jak w przykładzie powyżej. CSV używa średnika i UTF-8 z BOM; Markdown nadaje się do dokumentacji na GitHubie, a JSON do ponownego importu. Bez `--output` dokument trafia na stdout. Plan z błędami jest jawnie oznaczony i daje kod 1. Szczegóły: [eksporty](exports.md).

Możesz od razu przejrzeć [raport AV](../examples/exports/church-av.md), [arkusz AV](../examples/exports/church-av.xlsx), [dokument AV](../examples/exports/church-av.docx), [raport hierarchii T4](../examples/exports/t4-hierarchy.md) i [katalog projektów T1–T5](../examples/README.md). T3 oraz VLAN 110 w /56 celowo pokazują błędy; pozostałe przykłady mają kompletne plany. XLSX/DOCX wymagają `--output`; do ich otwarcia użyj Excela/Worda lub LibreOffice.

## Wygodna praca i druk

Motyw wybierasz w górnym pasku; ustawienie systemowe reaguje na preferencję przeglądarki. Tab przechodzi standardowo między polami, Enter przechodzi do kolejnego widocznego pola, Shift+Enter do poprzedniego. Ctrl+D w wierszu segmentu lub budynku duplikuje go z nowym ID i pustymi przypięciami IPv4/IPv6. Przycisk Duplikuj wykonuje tę samą operację. Numer VLAN pozostaje skopiowany — w razie potrzeby go zmień.

Kliknij CIDR w wyniku, aby skopiować go do schowka. „Druk / PDF” otwiera raport bez edytora; przycisk drukowania uruchamia standardowe okno przeglądarki, w którym można wybrać zapis PDF. Arkusz XLSX jest szeroki i przy wydruku obejmuje kilka stron w poziomie; DOCX i widok druku są wygodniejsze do zwartej dokumentacji.

## Kontener i przygotowanie GitHuba

Opcjonalnie: `docker compose up --build -d`, następnie ten sam adres `http://127.0.0.1:8000`. Baza pozostaje w nazwanym wolumenie. Instrukcje kopii danych, źródeł i licencji: [przygotowanie publikacji](historia/publishing.md). Dockerfile/Compose przygotowano; lokalne środowisko odbioru nie miało Dockera, więc uruchomienie kontenera weryfikuje przygotowany job CI po publikacji.

## Jak liczymy pojemność

Liczba hostów oznacza urządzenia poza osobno rezerwowaną pulą statyczną i bramami. Zapas zaokrąglamy w górę, potem dodajemy bramy i statyczne. Dla LAN uwzględniamy adres sieci i broadcast; najmniejszy blok to /30.

Przykład: 100 hostów + 25% zapasu + 1 brama + 8 statycznych = 134 użyteczne adresy, czyli /24. Ustawienia domyślne LAN: 25% zapasu i jedna brama na początku. P2P/loopback mają osobne reguły i nie dziedziczą bramy ani zapasu hostów.

Operacje sieciowe wykorzystują standardowy moduł `ipaddress`; obliczenia pojemności są całkowitoliczbowe. Nie tworzymy list wszystkich hostów. Błędne przypięcie pozostaje błędem — nie dostaje po cichu innego adresu. Wynik z błędami ma `is_complete=False` i zachowuje poprawne przydziały pozostałych segmentów.

Dla `10.20.1.0/26` i ośmiu adresów statycznych:

| Brama | Adresy bram | Zakres statyczny | Zakres DHCP |
| --- | --- | --- | --- |
| Pierwsza, jeden adres | .1 | .2–.9 | .10–.62 |
| Ostatnia, jeden adres | .62 | .1–.8 | .9–.61 |
| Ostatnia, trzy adresy | .62 (wirtualny), .61, .60 | .1–.8 | .9–.59 |

P2P i loopback nie mają zakresu DHCP ani bramy. Pusty zakres jest reprezentowany jako brak wartości. Duplikat VLAN-u ostrzega w obrębie lokalizacji; ten sam numer w innej lokalizacji jest dozwolony. Pula RFC 1918 jest rozpoznawana jawną listą sieci, a nie przez `is_private`.

## Testy i jakość

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy --strict src/adresplan
```

Testy obejmują pojemność, rozłączność, zawieranie w puli, zachowanie przypięć, deterministyczność oraz sumę alokacji, rezerw i wolnych bloków. Hypothesis korzysta z powtarzalnego profilu do 200 przykładów; dwa pełne testy właściwościowe IPv6 i dwa kalkulatora mają limit 80, a test JSON 60. Sprawdzane są też eksport/import, CSV/Markdown, błędy zapisu i rzeczywiste polecenia CLI. Etap 5 dodaje transakcje i restart SQLite, równoczesne edycje, pełny cykl HTTP, zgodność API/CLI i ochronę lokalnych formularzy. Wyniki bieżącej wersji: [odbiór etapu 5](historia/stage-5-verification.md). mypy sprawdza cały pakiet.

Workflow `.github/workflows/ci.yml` przygotowano dla Linux/Python 3.11 i 3.12 oraz Windows/Python 3.12. Uruchomi się po umieszczeniu repozytorium na GitHubie. Przygotowanie workflow nie oznacza, że zdalny CI już przeszedł.

Zależności narzędzi są utrwalone w `requirements-dev.lock` (bez ścieżek lokalnych). Zakresy wersji w `pyproject.toml` służą późniejszym świadomym aktualizacjom; plik lock jest wspólną podstawą lokalnych sprawdzeń i CI.

## Dokumentacja i kolejne etapy

- [Plan realizacji](historia/PLAN.md) — zakres, etapy i kryteria odbioru.
- [Specyfikacja](historia/SPEC.md) — odpis źródłowego PDF.
- [Historia zmian](../CHANGELOG.md) — aktualizowana po każdym ukończonym etapie.
- [Odbiór etapu 1](historia/stage-1-verification.md) — rzeczywiste wyniki testów i granice wdrożonego zakresu.
- [Odbiór etapu 2](historia/stage-2-verification.md) — hierarchia IPv4, zakresy, zamrażanie i wyniki sprawdzeń.
- [Odbiór etapu 3](historia/stage-3-verification.md) — IPv6, infrastruktura, ULA, reverse DNS i wspólne zamrażanie.
- [Format JSON](json-format.md) — pola, walidacja, schemat i odczyt/zapis.
- [Odbiór części 4A](historia/stage-4a-verification.md) — JSON, zachowanie danych i sprawdzenia.
- [Instrukcja CLI](cli.md) — plan, kalkulator, zamrożenie, parametry i kody zakończenia.
- [Odbiór części 4B](historia/stage-4b-verification.md) — wyniki kalkulatora, podgląd podsieci i testy poleceń.
- [Eksporty](exports.md) — CSV, Markdown, JSON, kodowanie i zachowanie niekompletnych planów.
- [Odbiór części 4C](historia/stage-4c-verification.md) — końcowy odbiór v0.1 i świeżej instalacji.
- [Interfejs lokalny i API](web.md) — uruchomienie, edycja, baza i kopie danych.
- [Odbiór etapu 5](historia/stage-5-verification.md) — SQLite, HTTP i przeglądarka.
- [Odbiór etapu 6](historia/stage-6-verification.md) — Office, wygoda, pakiet i ograniczenia weryfikacji.
- [Architektura](architecture.md) — przepływ danych i reguły utrzymania.
- [Zmiany wersji 1.0](historia/release-v1.0.md) — zakres lokalnego wydania.

Wszystkie sześć etapów implementacji ukończono. [Opis wcześniejszego lokalnego wydania CLI v0.1](historia/release-v0.1.md).
