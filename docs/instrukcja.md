# Przewodnik użytkownika

Ten przewodnik prowadzi od instalacji do gotowej dokumentacji. Krótkie podsumowanie projektu jest w [README](../README.md).

## Instalacja

Potrzebujesz Pythona 3.11 lub nowszego. Na Windows (PowerShell), w folderze projektu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

Na Linuksie i macOS użyj `python3 -m venv .venv` i ścieżki `.venv/bin/` zamiast `.\.venv\Scripts\`. Nie trzeba aktywować środowiska.

## Uruchomienie

```powershell
.\.venv\Scripts\adresplan.exe serve
```

Otwórz **http://127.0.0.1:8000**. Serwer działa, dopóki terminal jest otwarty; `Ctrl+C` go zatrzymuje. Dane zostają w bazie SQLite na Twoim komputerze. Szczegóły bazy, kopii i API: [interfejs w przeglądarce](web.md).

Przełącznik **PL / EN** w górnym pasku zmienia język interfejsu i raportów. Bez wyboru aplikacja kieruje się językiem przeglądarki.

## Pierwszy plan

1. Na stronie głównej wpisz nazwę projektu i pulę IPv4, np. `10.0.0.0/16`. Zdecyduj, czy planujesz IPv6.
2. Możesz zacząć od gotowego zestawu („Obiekt podstawowy”, „Obiekt rozbudowany”) albo od pustej struktury.
3. W edytorze dodaj lokalizacje, budynki i sieci urządzeń (segmenty). Dla segmentu wpisz liczbę urządzeń i VLAN.
4. Zmiany zapisują się same po chwili. Wynik pod tabelą pokazuje podsieci, bramy, zakresy statyczne i DHCP.
5. Gdy plan jest gotowy, wybierz **Zamroź adresy**. Kolejne zmiany nie przesuną już istniejących sieci.
6. **Podgląd i eksport** pozwala pobrać raport (Markdown, CSV, Excel, Word), kopię projektu (JSON) albo konfigurację startową Cisco lub MikroTik.

Możesz też zaimportować gotowy przykład z folderu [examples](../examples/README.md), np. `examples/church-av.json`.

## Jak liczona jest wielkość podsieci

Liczba hostów to urządzenia bez bram i bez dodatkowych adresów statycznych. Program:

1. dolicza zapas na rozwój (domyślnie 25%, zaokrąglany w górę),
2. dodaje adresy bram i adresy statyczne,
3. dla zwykłej sieci LAN dolicza adres sieci i broadcast,
4. wybiera najmniejszą podsieć, która to pomieści.

Przykład: 100 hostów + 25% zapasu + 1 brama + 8 statycznych = 134 adresy, czyli podsieć /24.

Dla `10.20.1.0/26` z ośmioma adresami statycznymi zakresy wyglądają tak:

| Brama | Adresy bram | Zakres statyczny | Zakres DHCP |
| --- | --- | --- | --- |
| Na początku, jeden adres | .1 | .2–.9 | .10–.62 |
| Na końcu, jeden adres | .62 | .1–.8 | .9–.61 |
| Na końcu, trzy adresy | .62, .61, .60 | .1–.8 | .9–.59 |

Łącza P2P dostają /31 (lub /30), a loopbacki /32. Nie mają bramy, zapasu ani DHCP.

## Przykład VLSM

Pula `192.168.10.0/24`, bez zapasu i bram, cztery sieci:

| Segment | Hosty | Podsieć | Adresy urządzeń |
| --- | ---: | --- | --- |
| A | 100 | 192.168.10.0/25 | 192.168.10.1–192.168.10.126 |
| B | 50 | 192.168.10.128/26 | 192.168.10.129–192.168.10.190 |
| C | 25 | 192.168.10.192/27 | 192.168.10.193–192.168.10.222 |
| D | 10 | 192.168.10.224/28 | 192.168.10.225–192.168.10.238 |

Wolny zostaje blok `192.168.10.240/28`. Przydział zaczyna się od największych potrzeb, a sieci przypięte ręcznie są rozpatrywane przed automatycznymi.

## Hierarchia i IPv6

Adresy są przydzielane hierarchicznie: lokalizacja → budynek → segment. Każdy budynek dostaje jeden blok zbiorczy, co upraszcza trasy.

Domyślny podział IPv6 to lokalizacja /48, budynki /56, sieci LAN /64, łącza /127 i loopbacki /128. Infrastruktura lokalizacji ma trzy pule /64: rezerwę, łącza i loopbacki. Przykład dla `2001:db8:abcd::/48`:

| Obiekt | Przydział |
| --- | --- |
| Infrastruktura | 2001:db8:abcd::/56 |
| Budynki A, B, C | …:100::/56, …:200::/56, …:300::/56 |
| LAN-y budynku A | …:100::/64, …:101::/64, … |
| Łącza | …:1::/127, …:1::2/127 |
| Loopback | …:2::/128 |

Opcja „VLAN jako cyfry hex” wpisuje numer VLAN w adres: VLAN 10 → `…:110::/64`, VLAN 20 → `…:120::/64`. Działa dla VLAN-ów 1–999.

Bez prefiksu od operatora aplikacja może wygenerować prywatny prefiks ULA /48 ([RFC 4193](https://www.rfc-editor.org/rfc/rfc4193.html)). Prefiks jest zapisywany w projekcie, więc ponowne przeliczenie go nie zmienia.

## Zamrażanie

Zamrożenie przypina wszystkie obecne adresy IPv4 i IPv6 oraz infrastrukturę. Nowy segment trafia w wolne miejsce, a istniejące sieci zostają na swoich adresach. Jeśli miejsca zabraknie, program zgłasza błąd zamiast cokolwiek przesuwać. Planu z błędami nie da się zamrozić.

## Praca w terminalu

Te same obliczenia są dostępne z wiersza poleceń:

```powershell
.\.venv\Scripts\adresplan.exe plan examples/church-av.json
.\.venv\Scripts\adresplan.exe calc 192.168.1.0/24 --split 4
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f cisco
```

Opis wszystkich poleceń: [CLI](cli.md). Formaty plików: [eksporty](exports.md) i [format JSON](json-format.md).

## Docker

```powershell
docker compose up --build -d
```

Aplikacja będzie pod tym samym adresem `http://127.0.0.1:8000`. Baza leży w nazwanym wolumenie Dockera.

## Dla programistów

Środowisko deweloperskie i sprawdzenia:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/adresplan
```

Opcjonalne testy JavaScript: `node --test tests/web_state.test.cjs`. Budowę programu opisuje [architektura](architecture.md), a przebieg prac — [historia projektu](historia/README.md).
