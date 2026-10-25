# Interfejs w przeglądarce

## Uruchomienie

```powershell
.\.venv\Scripts\adresplan.exe serve
```

Otwórz `http://127.0.0.1:8000`. Terminal pokazuje adres i ścieżkę bazy; `Ctrl+C` zatrzymuje serwer. Inny port lub plik bazy:

```powershell
.\.venv\Scripts\adresplan.exe serve --database data/projekty.sqlite3 --port 8080
```

Aplikacja jest przeznaczona na jeden komputer: nasłuchuje tylko na `127.0.0.1` i nie ma kont użytkowników. Wszystkie skrypty i style są w pakiecie, więc po instalacji nie potrzebuje Internetu.

## Język

Przełącznik **PL / EN** w górnym pasku zmienia język stron, komunikatów i raportów. Wybór jest zapamiętywany w ciasteczku. Bez wyboru aplikacja używa polskiego, chyba że przeglądarka jako pierwszy język podaje inny niż polski — wtedy angielskiego. Język nie wpływa na dane projektu.

## Praca z projektem

1. Na stronie Projekty utwórz projekt (nazwa, pula IPv4, decyzja o IPv6) albo zaimportuj plik JSON.
2. W edytorze dodaj lokalizacje, budynki i segmenty. W tabeli ustaw hosty, VLAN i rolę; rozwinięcie wiersza pokazuje dalsze ustawienia i przypięcia.
3. Zmiany zapisują się po 300 ms. Komunikat „Zapisano · wersja N” potwierdza zapis.
4. Wynik pod tabelą pokazuje przydziały, bramy, zakresy statyczne i DHCP oraz IPv6. Komunikat o błędzie ma przycisk „Przejdź do pola”.
5. **Zamroź adresy** przypina bieżący plan. **Podgląd i eksport** pokazuje i pobiera raporty oraz konfigurację urządzeń.

Dodatkowe narzędzia:

- **Tryb podglądu** — „Najpierw pokaż skutki” pozwala zobaczyć zmiany adresów przed zapisem i zatwierdzić je jednym przyciskiem.
- **Szablony** — gotowe zestawy sieci i własne wzorce budynków lub całych lokalizacji; kilka oddziałów naraz dodasz z listy nazw.
- **Blokady** — lista podsieci już zajętych w istniejącej sieci; planer je omija.
- **Historia** — każda zmiana tworzy wersję; wersje można porównać i przywrócić.
- **Diagram** — hierarchia adresacji jako obraz SVG do pobrania.
- **Druk / PDF** — raport do wydruku albo zapisu jako PDF z przeglądarki.
- **Kalkulator** — VLSM według liczby urządzeń, informacje o adresie i równy podział sieci. Wynik VLSM można zamienić w projekt.

Skróty: Enter i Shift+Enter przechodzą między polami, Ctrl+D duplikuje wiersz, kliknięcie CIDR kopiuje go do schowka. Motyw jasny, ciemny lub systemowy wybierzesz w górnym pasku.

## Błędy i edycja w dwóch kartach

- Błędna wartość pola (np. CIDR z bitami hosta albo VLAN 5000) nie jest zapisywana. Formularz zachowuje wpisane dane i wskazuje pole.
- Poprawne dane, które się nie mieszczą, są zapisywane, a wynik dostaje oznaczenie **PLAN NIEKOMPLETNY**. Takiego planu nie da się zamrozić.
- Jeśli projekt zmienił się w innej karcie, zapis zostaje odrzucony zamiast nadpisać cudze zmiany. Wczytaj aktualną wersję i wprowadź zmiany ponownie.

## Baza danych i kopie zapasowe

Ścieżka bazy: opcja `--database`, potem zmienna `ADRESPLAN_DB`, a domyślnie folder danych użytkownika:

| System | Domyślne miejsce |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AddressPlan\adresplan.sqlite3` |
| Linux | `~/.local/share/AddressPlan/adresplan.sqlite3` (lub `$XDG_DATA_HOME`) |
| macOS | `~/Library/Application Support/AddressPlan/adresplan.sqlite3` |

Baza przechowuje projekty, pełną historię i bibliotekę szablonów. Kopię jednego projektu zrobisz eksportem JSON. Kopię wszystkiego pobierzesz przyciskiem na stronie głównej (`/library/backup.sqlite3`). Aby ją odtworzyć, uruchom `serve --database ŚCIEŻKA_DO_KOPII`.

## API

Lokalne API korzysta z tych samych obliczeń co interfejs i CLI. `{key}` to klucz projektu w bazie.

| Żądanie | Wynik |
| --- | --- |
| `GET /api/session` | Token do żądań POST i PUT |
| `GET /api/projects` | Lista projektów z wersjami |
| `GET /api/projects/{key}/plan` | Projekt i wynik w formacie JSON; wersja w nagłówku `X-Project-Revision` |
| `PUT /api/projects/{key}` | Zapis projektu; wymaga nagłówka `If-Match` z numerem wersji |
| `GET /api/projects/{key}/export.{format}` | Plik: `csv`, `md`, `json`, `xlsx`, `docx`, `cisco`, `mikrotik`; opcjonalnie `?profile=brief` |
| `GET /api/projects/{key}/history` | Lista wersji |
| `GET /api/projects/{key}/history/{n}` | Zapisana wersja n jako JSON |
| `GET /api/projects/{key}/diagram.svg` | Diagram SVG |
| `POST /api/calc` | Kalkulator: `text`, opcjonalnie `count` albo `new_prefix` i `limit` |

Żądania zmieniające dane wymagają nagłówka `X-CSRF-Token`. Brak `If-Match` daje odpowiedź 428, konflikt wersji 409, błędne dane 422. Eksport niekompletnego planu zwraca 200 z nagłówkiem `X-Plan-Complete: false`.

## Zabezpieczenia

Serwer przyjmuje tylko adresy localhost, sprawdza nagłówek Origin i token formularza, nie włącza CORS i wysyła restrykcyjną politykę CSP. Szablony automatycznie cytują dane użytkownika. To ochrona przed atakami z innych stron w przeglądarce, a nie system kont — aplikacja nie jest przygotowana do publicznego hostingu. Opcja `--host 0.0.0.0` służy wyłącznie do uruchomienia w kontenerze.
