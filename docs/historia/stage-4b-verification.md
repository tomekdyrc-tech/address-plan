# Odbiór części 4B — CLI i kalkulator

Data: 14.10.2026. Wersja deweloperska: `0.1.0.dev5`. **Ukończono 4B; cały etap 4 nadal trwa.**

## Zakres

- `plan PROJEKT.json`: tabela hierarchii i CIDR obu rodzin, rezerwacje IPv4, informacje/infrastruktura IPv6 i metryki osobno na każdym poziomie.
- `plan --show-free`, `--verbose`, `--json`, `--output`: wolne bloki, dodatkowa diagnostyka, poprawny JSON na stdout oraz atomowy zapis przez mechanizm 4A.
- `freeze PROJEKT.json --output WYNIK.json`: przypięcia obu rodzin i infrastruktury; odmowa zapisu planu z błędami.
- `calc`: prefiks, maska, wildcard, obsługa bitów hosta, /31 i /32, RFC 1918, reverse DNS; formy/typy IPv6 i liczba /64.
- Podział przez `--split N` albo `--new-prefix X`; leniwy podgląd 1–256 wierszy.
- Polska pomoc i diagnostyka, UTF-8, podział stdout/stderr oraz kody zakończenia 0/1/2.

Kalkulator to czysty moduł `core/calc.py`, bez I/O i nowych zależności. Polska prezentacja jest w warstwie aplikacji. Nie zmieniono algorytmów przydziału ani formatu JSON `schema_version=1`.

## Wyniki lokalne

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.12.14 | 555 testów zaliczonych, około 39,6 s |
| Windows / Python 3.11.0 | 555 testów zaliczonych, około 39,3 s |
| Nowe pozycje testowe | 128 względem 427 po części 4A |
| Ruff lint i formatowanie | Bez uwag |
| mypy `--strict src/adresplan` | Bez uwag, 24 pliki; oba interpretery |
| `pip check` | Bez konfliktów zależności; oba środowiska |

Dwa nowe testy właściwościowe wykonują do 80 powtarzalnych przykładów każdy: zakresy użyteczne IPv4 oraz poprawność i ograniczenie podziałów IPv6. Testy CLI wywołują prawdziwy podproces, sprawdzają oddzielnie stdout, stderr i kod zakończenia. Wymuszają początkowo kodowanie ASCII, aby sprawdzić ustawienie UTF-8 przez program. Czasy są pomiarem lokalnym; pełne zestawy obu interpreterów uruchomiono równolegle.

Testy plikowe używały lokalnych katalogów `--basetemp=.tmp/pytest-4b-py312` i `.tmp/pytest-4b-py311`, aby ominąć ograniczenia systemowego katalogu tymczasowego w piaskownicy. Nie jest to wymaganie aplikacji.

## Instalowana paczka

Zbudowano wheel i sdist `0.1.0.dev5`. Wheel zainstalowano zwykłym, nieedytowalnym trybem w osobnym środowisku z zależnościami z 4A (`.venv-smoke4a`), zastępując poprzednią wersję. Pakiet nie korzystał z katalogu `src`.

Kontrola z katalogu `C:/Users/Tomek`, poza repozytorium, przez izolowany Python `-I` i zainstalowany `adresplan.exe` potwierdziła:

- wersję `0.1.0.dev5`, pomoc wszystkich trzech poleceń i dostępność schematu JSON;
- `plan --json` zgodny z odczytanym projektem AV, przy oddzielnych ostrzeżeniach;
- maskę/wildcard, /31, /32 oraz ograniczony podział całego IPv6 /0 na /128;
- błąd 2 i sugestię 4 dla `--split 3`;
- zamrożenie T5, ponowny odczyt i dodanie segmentu bez przesunięcia starych adresów ani infrastruktury;
- kod 1 dla niekompletnego planu i pozostawienie poprzedniego pliku przy odmowie zamrożenia;
- polskie UTF-8 mimo początkowego ustawienia ASCII w środowisku procesu.

To kontrola paczki deweloperskiej, nie końcowy odbiór v0.1. W 4C trzeba jeszcze sprawdzić kompletne CLI wraz z poleceniem `export` i instalację końcowego wydania w świeżym środowisku.

## Najważniejsze przypadki odbioru

| Przypadek | Wynik |
| --- | --- |
| Host/prefiks, maska i wildcard IPv4 | Ta sama poprawna sieć i zakres |
| `/31`, `/32`, `/0` i maksymalne adresy IPv4 | Poprawne granice, bez listowania hostów |
| RFC 1918 kontra CGNAT, dokumentacyjne, loopback i link-local | Jawna klasyfikacja trzech prywatnych zakresów |
| IPv4 /20 i IPv6 /127 | Bez fikcyjnej pojedynczej strefy reverse; PTR osobno |
| IPv6 GUA/ULA/doc/link-local/multicast/loopback/nieokreślony/inny | Rozpoznane; szerokie bloki mogą mieć typ mieszany |
| /48, /56, /127, /128 IPv6 | Odpowiednio 65536, 256, 0, 0 podsieci /64 |
| Podział przez N i przez prefiks | Zgodne, uporządkowane wyniki |
| N=3 | Błąd 2 i sugestia 4, bez częściowego wyniku |
| Podział całego IPv6 /0 na /128 | Dokładny licznik i ograniczony podgląd |
| Błędna maska, prefiks, limit, sprzeczne opcje i literówki | Błąd 2, polska pomoc, brak traceback |
| Plan AV | Oczekiwane adresy, ostrzeżenie o wykorzystaniu, kod 0 |
| `plan --json --output` z ostrzeżeniami | Poprawny JSON na stdout i identyczny plik; komunikaty na stderr |
| Niekompletny plan | Kod 1, diagnostyka i możliwość zapisania projektu do naprawy |
| Zamrożenie T5 i dodanie segmentu po odczycie | Stare IPv4/IPv6 i infrastruktura zachowane |
| Odmowa zamrożenia | Poprzedni plik docelowy nietknięty |
| Jawne zamrożenie w tym samym pliku | Poprawne i idempotentne |
| Błąd odczytu/zapisu i zły typ pola JSON | Kod 2 i ścieżka/kod błędu |
| Znaki sterujące w nazwach użytkownika | Bez wykonywania sekwencji terminala; oryginał pozostaje w JSON |

## Ręczna kontrola

```powershell
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json
.\.venv\Scripts\adresplan.exe calc 192.168.1.10 0.0.0.255 --split 4
.\.venv\Scripts\adresplan.exe calc 2001:db8::/48 --new-prefix 64 --limit 4
```

Pierwszy kalkulator daje sieć `192.168.1.0/24`, 254 użyteczne adresy i cztery /26. Drugi pokazuje dokładnie 65536 wynikowych /64, ale tylko cztery wiersze podglądu. Instrukcja zapisu i zamrożenia: [cli.md](../cli.md).

## Granice ukończonego zakresu

Nie rozpoczęto 4C: polecenia `export`, CSV/Markdown, pełnego zestawu przykładów i odbioru wydania v0.1. Interfejs webowy i SQLite pozostają w etapie 5. Nie publikowano repozytorium ani wydania; zdalny CI nie był uruchamiany.
