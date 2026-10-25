# Wiersz poleceń (CLI)

Polecenie `adresplan` ma pięć podpoleceń: `plan`, `calc`, `freeze`, `export` i `serve`. Każde ma własną pomoc, np. `adresplan calc --help`. Przykłady zakładają Windows i instalację z [przewodnika](instrukcja.md); na Linuksie i macOS użyj `.venv/bin/adresplan`.

```powershell
.\.venv\Scripts\adresplan.exe --help
.\.venv\Scripts\adresplan.exe --version
```

## Język

Komunikaty, pomoc i raporty są domyślnie po polsku. Wersję angielską włączysz opcją `--lang en` (w dowolnym miejscu polecenia) albo zmienną środowiskową `ADRESPLAN_LANG=en`:

```powershell
.\.venv\Scripts\adresplan.exe --lang en plan examples/church-av.json
```

## plan — oblicz plan z pliku projektu

```powershell
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json
```

Wynik pokazuje status, drzewo lokalizacji, budynków i segmentów z VLAN-ami i adresami obu protokołów, a niżej bramy, zakresy statyczne i DHCP, informacje IPv6 i wykorzystanie pul. Dla przykładu AV:

| Segment | IPv4 | IPv6 |
| --- | --- | --- |
| Dźwięk | 10.42.0.0/27 | 2001:db8:42:100::/64 |
| Obraz | 10.42.0.32/27 | 2001:db8:42:101::/64 |
| Zarządzanie | 10.42.0.64/28 | 2001:db8:42:102::/64 |

Opcje:

- `--show-free` — lista wszystkich wolnych bloków.
- `--verbose` — także komunikaty informacyjne (domyślnie tylko błędy i ostrzeżenia).
- `--json` — sam dokument JSON na wyjściu; komunikaty idą na stderr.
- `-o PLIK` / `--output PLIK` — zapis projektu z wynikiem do pliku JSON. Folder musi istnieć; istniejący plik jest zastępowany w całości.

Plan z błędami też można zapisać i dalej poprawiać.

## freeze — zamroź adresy

```powershell
.\.venv\Scripts\adresplan.exe freeze examples/stage4a_project.json -o output/zamrozony.json
```

Zapisuje obecne przydziały jako przypięcia (`pinned_v4`, `pinned_v6`) razem z infrastrukturą IPv6. Plik wynikowy jest wymagany. Plan z błędami nie zostanie zamrożony, a plik docelowy pozostanie bez zmian.

## calc — kalkulator podsieci

```powershell
.\.venv\Scripts\adresplan.exe calc 192.168.1.10/24
.\.venv\Scripts\adresplan.exe calc 192.168.1.10 255.255.255.0
.\.venv\Scripts\adresplan.exe calc 2001:db8:abcd::/48
```

Dla IPv4 kalkulator pokazuje sieć, maskę, wildcard, maskę binarną, broadcast, pierwszy i ostatni adres, liczbę adresów, przynależność do RFC 1918 i dane reverse DNS. Przyjmuje zapis z prefiksem, maską albo wildcardem. Sieci /31 mają dwa użyteczne adresy, a /32 jeden; żadna nie ma broadcastu.

Dla IPv6 pokazuje formę skróconą i rozwiniętą, typ adresu (np. GUA, ULA, link-local, dokumentacyjny), liczbę adresów i podsieci /64 oraz strefę `ip6.arpa`. Kalkulator niczego nie wysyła do sieci.

### Podział na równe podsieci

```powershell
.\.venv\Scripts\adresplan.exe calc 192.168.1.0/24 --split 4
.\.venv\Scripts\adresplan.exe calc 192.168.1.0/24 --new-prefix 26
.\.venv\Scripts\adresplan.exe calc 2001:db8::/48 --new-prefix 64 --limit 4
```

- `--split N` — N równych części; N musi być potęgą dwójki (dla 3 program podpowie 4).
- `--new-prefix X` — podsieci o długości /X.
- `--limit` — ile wierszy pokazać (1–256, domyślnie 256).

Liczba wszystkich podsieci jest zawsze podana dokładnie, nawet gdy podgląd jest skrócony.

## export — dokumenty i konfiguracja

```powershell
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f md -o output/plan.md
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f xlsx -o output/plan.xlsx
.\.venv\Scripts\adresplan.exe export examples/church-av.json -f cisco
```

Formaty: `csv`, `md`, `json`, `xlsx`, `docx`, `cisco`, `mikrotik`. Bez `-o` tekst trafia na ekran; Excel i Word wymagają pliku. Opis zawartości: [eksporty](exports.md).

## serve — interfejs w przeglądarce

```powershell
.\.venv\Scripts\adresplan.exe serve --port 8080 --database data/projekty.sqlite3
```

Opcje i działanie interfejsu: [interfejs w przeglądarce](web.md).

## Kody zakończenia

| Kod | Znaczenie |
| --- | --- |
| 0 | Sukces (ostrzeżenia nie blokują wyniku) |
| 1 | Plan niekompletny albo odmowa zamrożenia planu z błędami |
| 2 | Błędne argumenty, dane JSON lub błąd odczytu/zapisu pliku |
| 130 | Przerwanie przez użytkownika |

W PowerShell kod ostatniego polecenia odczytasz z `$LASTEXITCODE`. Komunikat błędu wskazuje pole, np. `project.nodes[2].hosts`, oraz stały kod diagnostyczny. Nazwy z pliku są oczyszczane ze znaków sterujących terminala.
