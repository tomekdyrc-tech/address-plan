# Odbiór części 4C i lokalnego wydania v0.1

Data: 14.10.2026. Wersja pakietu: `0.1.0`. **Etap 4 ukończony; etapu 5 nie rozpoczęto.**

## Wynik

Administrator może wczytać projekt JSON, policzyć adresację, sprawdzić podsieci w kalkulatorze, zamrozić istniejące przydziały i otrzymać dokumentację CSV/Markdown albo przenośny projekt JSON. Nie wymaga to pisania kodu Pythona. Do edycji danych przed etapem 5 potrzebna jest podstawowa znajomość JSON.

Dodano polecenie `export`, eksportery CSV i Markdown oraz wspólne przygotowanie świeżego planu i atomowy zapis plików. Istniejący JSON korzysta z tego samego mechanizmu zapisu. Nie zmieniono algorytmów alokacji ani formatu `schema_version=1`.

## Testy i narzędzia

| Sprawdzenie | Rzeczywisty wynik lokalny |
| --- | --- |
| Windows / Python 3.12.14 | 617 testów zaliczonych, około 49,5 s |
| Windows / Python 3.11.0 | 617 testów zaliczonych, około 49,4 s |
| Nowe pozycje po 4B | 62 względem 555 |
| Ruff lint i formatowanie | Bez uwag |
| mypy `--strict src/adresplan` | Bez uwag, 29 plików, oba interpretery |
| `pip check` | Bez konfliktów w środowiskach deweloperskich i świeżej instalacji |

Pełne zestawy testów obu interpreterów uruchomiono równolegle; czas nie jest gwarancją na innych komputerach. Testy plikowe w piaskownicy używały `--basetemp` w `.tmp/`. Test atomowego zapisu z 4A zaktualizowano do wspólnej implementacji `application/files.py`; nadal sprawdza pozostawienie starej treści i usunięcie pliku tymczasowego po nieudanej podmianie.

Nowe sprawdzenia obejmują dokładne pola CSV, zapas i rezerwacje, bramę last, /31 i /32, IPv6 /64-/127-/128, końce łączy, RA i reverse DNS, cytowanie CSV, tekst przypominający formuły, ucieczki Markdown/HTML, raporty niekompletne i puste, deterministyczność, błędy zapisu oraz rzeczywiste wywołania `export`.

## Przykłady i raporty

Dodano osiem projektów JSON: T1, T2, T3, T4 (`budynek.json`), T5 sequential, T5 VLAN hex, celowy błąd VLAN 110 w /56 oraz syntetyczną sieć AV i biura. Dawny mały przykład z 4A nadal działa. T3 i błąd VLAN 110 celowo zwracają 1. Pozostałe przykłady mają kompletne plany; ostrzeżenia są dopuszczalne.

- T1: zgodne cztery przydziały i wolny /28.
- T2: zgodne wszystkie dziesięć podsieci, 485 adresów zajętych i 539 wolnych wewnątrz przypiętego budynku.
- T3: X i Y otrzymują /27, Z nie otrzymuje adresu; diagnoza sugeruje /25.
- T4: A=/23, B=/24, C=/27, zgodnie z PDF.
- T5: budynki i infrastruktura zgodne; VLAN 10/20/99 daje odpowiednio `…:110::/64`, `…:120::/64`, `…:199::/64`.
- AV i T4: po jednym raporcie CSV i Markdown w `examples/exports`; testy porównują pliki z bieżącym eksportem bajt po bajcie.

CSV zawiera status każdego wiersza i zachowuje segment bez przydziału. Markdown zawiera założenia, ustawienia, rodziców i przypięcia, tabele per budynek, infrastrukturę, metryki, wolne bloki i pełną walidację. Brak wartości nie staje się zmyślonym adresem. Liczniki IPv6 pozostają dokładnymi liczbami całkowitymi.

## Świeża instalacja poza repozytorium

Zbudowano `adresplan-0.1.0-py3-none-any.whl` i `adresplan-0.1.0.tar.gz`. Utworzono nowe, puste środowisko `.venv-release-01` na Pythonie 3.12.14. Zainstalowano wheel w zwykłym, nieedytowalnym trybie, z zależnościami ograniczonymi przez `requirements-dev.lock`. Środowisko zawiera zależności uruchomieniowe, bez pytest i narzędzi deweloperskich.

Kontrolę uruchomiono z `C:/Users/Tomek`, poza repozytorium, przez Python `-I` i zainstalowany `adresplan.exe`. Sprawdzono ścieżkę importu w `.venv-release-01`, wersję `0.1.0` i schemat JSON dołączony jako zasób pakietu.

Przeszły:

- pomoc wszystkich czterech poleceń i `--version`;
- `plan --json` dla ośmiu nowych projektów, z porównaniem wyniku do ponownego odczytu;
- 24 eksporty plikowe: osiem projektów × CSV/Markdown/JSON, z oczekiwanymi kodami 0 lub 1;
- poprawna liczba rekordów CSV, statusy, BOM i separator; odczyt wszystkich wyeksportowanych JSON-ów;
- zgodność bajtów dokumentu na stdout i w pliku: dla CSV jedyną dodatkową częścią pliku jest BOM;
- polskie UTF-8 mimo początkowo wymuszonego ASCII w środowisku podprocesu;
- kalkulator maski/wildcard, podział /24 na cztery /26 oraz ograniczony podział IPv6 /0 na /128;
- kod 2 i sugestia poprawienia `--split 3`;
- zamrożenie T5, odczyt, dodanie LAN-u i brak przesunięcia wcześniejszych IPv4/IPv6 oraz infrastruktury;
- odmowa zamrożenia T3 i zachowanie poprzedniej treści pliku docelowego.

Końcowe archiwa sprawdzono pod kątem zgodności kodu i schematu z folderem `src`, a sdist również pod kątem aktualnej dokumentacji, testów, JSON-ów i przykładowych eksportów. Zmiany dokumentacji po kontroli instalacji nie zmieniają kodu programu.

## Status publikacji i kolejny etap

To lokalnie przygotowane wydanie CLI v0.1. Nie publikowano GitHub/PyPI, nie uruchamiano zdalnego CI i nie wybrano licencji za autora. Konfiguracja CI jest gotowa do późniejszego uruchomienia. Dostępne instrukcje: [wydanie v0.1](release-v0.1.md), [CLI](../cli.md), [eksporty](../exports.md), [przykłady](../../examples/README.md).

Etap 5 — SQLite i polski interfejs w przeglądarce — pozostaje nierozpoczęty. XLSX/DOCX i końcowe szlify należą do etapu 6.
