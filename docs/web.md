# Interfejs lokalny i API — etap 5

Wersja `1.1.0`, 16.10.2026. Wymagania: Python 3.11+, przeglądarka z JavaScript oraz podstawy CIDR/VLAN/IPv6. Nie musisz edytować kodu ani JSON.

## Uruchomienie

Po instalacji zgodnej z README, z głównego folderu projektu:

```powershell
.\.venv\Scripts\adresplan.exe serve
```

Otwórz `http://127.0.0.1:8000`. Program pokazuje w terminalu adres i rzeczywistą ścieżkę bazy. Terminal pozostaje otwarty; zatrzymanie: `Ctrl+C`. Inny port lub baza:

```powershell
.\.venv\Scripts\adresplan.exe serve --database data/projekty.sqlite3 --port 8080
```

Serwer wiąże wyłącznie `127.0.0.1`. To aplikacja na własny komputer, bez kont użytkowników. Nie konfigurujemy zdalnego hostingu w tym etapie. HTMX 2.0.11, CSS i JavaScript są w pakiecie. Nie ma CDN, zewnętrznych fontów ani wymaganych usług sieciowych.

## Pierwszy plan bez JSON

1. Na stronie Projekty wpisz nazwę i pulę IPv4, np. `10.42.0.0/16`, nazwę pierwszej lokalizacji i budynku. Możesz wybrać obiekt podstawowy, obiekt rozbudowany albo własny szablon.
2. W edytorze formularz „Dodaj do struktury” jest nad listą. Wybierz lokalizację, budynek lub sieć urządzeń (segment). Dla segmentu od razu wpiszesz liczbę urządzeń i VLAN.
3. Dodane elementy pojawiają się poniżej. W tabeli ustaw hosty, VLAN i rolę. Rozwiń ustawienia wiersza, aby zmienić rezerwę statyczną, IPv6, zapas, bramę, przypięcia, kolejność i uwagi. Budynki na listach wyboru są opisane razem z lokalizacją.
4. Na pytanie „Czy planujesz używać IPv6 w tej sieci?” domyślnie wybrane jest „Nie — planuj tylko IPv4”. Wybierz „Tak”, jeżeli IPv6 będzie używane. Aplikacja przygotuje prywatny prefiks ULA /48 i pokaże ustawienia IPv6; możesz wpisać prefiks od operatora. Zwykły zapis nie losuje nowego prefiksu. Ponowne wyłączenie zawiesza IPv6 i zachowuje prefiks, przypięcia oraz blokady do ponownego włączenia. IPv4 działa dalej. Wybór obowiązuje także przy dodawaniu szablonów.
5. Zmiany zapisują się po 300 ms od wpisania lub zmiany pola. Możesz też wybrać Zapisz. Zaczekaj na komunikat „Zapisano”.
6. Wynik pod tabelą pokazuje przydziały, bramy, zakresy statyczne i DHCP oraz IPv6/RA. Rozwiń wykorzystanie pul, wolne bloki i infrastrukturę. Nazwy i walidacja prowadzą do odpowiedniego wiersza.
7. „Zamroź adresy” przypina bieżące IPv4/IPv6 oraz infrastrukturę. Nowe potrzeby muszą zmieścić się w wolnych miejscach przypiętych rodziców. Brak miejsca zgłasza błąd; nie przesuwa istniejących sieci.
8. „Podgląd i eksport” pozwala obejrzeć oraz pobrać CSV, Markdown lub JSON. JSON jest przenośną kopią do importu.

„Wyczyść wszystkie przypięcia” pozwala ponownie swobodnie planować. Usuwanie lokalizacji/budynku obejmuje dzieci, a przycisk pyta o potwierdzenie. Przed większą przebudową warto pobrać JSON. Duplikuj na liście projektów tworzy osobną kopię z nowymi identyfikatorami i zachowaniem adresacji; zmiany w kopii nie zmieniają źródła.

Import JSON zawsze tworzy osobny projekt. Wynik zapisany w pliku nie jest zaufaną podstawą planu — aplikacja przelicza dane wejściowe. T3 i wariant VLAN 110 w /56 w przykładach celowo dają wynik niekompletny.

## Błędy i równoczesna edycja

- Błędny zapis pola, np. CIDR z bitami hosta albo VLAN 5000: odpowiedź 422, baza pozostaje bez zmian, wartości pozostają w edytorze. Popraw wskazane pola.
- Poprawne dane o zbyt dużym zapotrzebowaniu: projekt zostaje zapisany, wynik ma oznaczenie **PLAN NIEKOMPLETNY**, eksport zawiera diagnostykę. Zamrożenie jest wtedy niedostępne i nie zmienia bazy.
- Druga karta zmieniła projekt: odpowiedź 409, bez nadpisania. Skopiuj potrzebne niezapisane wartości, kliknij „wczytaj zapisaną wersję” i zastosuj je do aktualnej wersji.
- Zwykłe przeliczenie wymienia tylko wynik i drzewo, zachowując pola i fokus. HTMX kolejkuje zapisy; nagłówek wersji aktualizuje kolejne żądania, a starsza odpowiedź nie zastępuje nowszego wyniku. Podczas dodawania/usuwania i zamrażania formularz jest chwilowo blokowany, aby wymiana struktury nie zgubiła edycji.
- Przeglądarka ostrzega przed opuszczeniem strony z niezapisanymi zmianami. To uzupełnienie, nie zastępstwo komunikatu „Zapisano”.

## Baza i kopia zapasowa

Kolejność wyboru ścieżki: `--database`, następnie `ADRESPLAN_DB`, następnie katalog danych użytkownika:

| System | Domyślne miejsce |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AddressPlan\adresplan.sqlite3` |
| Linux | `$XDG_DATA_HOME/AddressPlan/adresplan.sqlite3` lub `~/.local/share/AddressPlan/adresplan.sqlite3` |
| macOS | `~/Library/Application Support/AddressPlan/adresplan.sqlite3` |

SQLite przechowuje bieżące zwalidowane wejście, metadane, historię wejścia i wyników oraz szablony. Schemat bazy ma `PRAGMA user_version=3` i automatyczną migrację z 1 lub 2; eksport JSON ma `schema_version=3`, a import przyjmuje także 1 i 2. Obcy lub nowszy schemat nie jest nadpisywany. Każdy zapis jest transakcją; wersja projektu zapobiega utracie równoczesnych zmian.

Najprostsza kopia jednego projektu: eksport JSON. Kopia wszystkich: zatrzymaj aplikację i skopiuj plik SQLite. Odtworzenie: uruchom `serve --database ŚCIEŻKA_DO_KOPII`. Pliki baz i katalog `data` są wykluczone z repozytorium przez `.gitignore`.

## API lokalne

Klucz w URL to klucz zapisu SQLite. Pozostaje oddzielony od identyfikatora wewnątrz importowanego projektu.

| Żądanie | Wynik |
| --- | --- |
| `GET /api/projects` | Lista kluczy, nazw, wersji i czasów zapisu |
| `GET /api/projects/{key}/plan` | Dokładnie ten sam dokument JSON co eksport CLI; wersja w `X-Project-Revision` |
| `POST /api/calc` | JSON z `text`, opcjonalnymi `count` lub `new_prefix`, `limit` 1–256; wynik, ograniczony podgląd i tekst |
| `GET /api/projects/{key}/export.csv` | CSV z BOM, średnikiem i diagnostyką |
| `GET /api/projects/{key}/export.md` | Raport Markdown |
| `GET /api/projects/{key}/export.json` | Przenośny projekt i przeliczony wynik |
| `GET /api/session` | Token formularzy/API dla bieżącego uruchomienia |
| `PUT /api/projects/{key}` | Dokument JSON jak przy imporcie; wymaga `If-Match` z numerem wersji; zwraca nowy dokument i wersję |

Żądania POST/PUT wymagają `X-CSRF-Token` z `/api/session` (formularze mają token automatycznie). Identyfikator istniejącego projektu nie może zostać zmieniony. Brak `If-Match` daje 428, konflikt wersji 409, błędny dokument 422. Eksport częściowy daje HTTP 200 z `X-Plan-Complete: false` i jawnym statusem wewnątrz raportu. Pobranie raportu nie modyfikuje projektu.

Ochrona lokalnej granicy: dozwolony Host localhost/127.0.0.1, weryfikacja Origin i tokenu CSRF, brak CORS, autoescape Jinja2 oraz CSP z zasobami własnymi. Dokumentacja Swagger/Redoc korzystająca z CDN jest wyłączona. Nie jest to uwierzytelnianie ani izolacja od innych programów uruchomionych na tym komputerze.

## Office, druk i skróty

Podgląd eksportu pozwala także pobrać XLSX i DOCX. Dla formatów Office pokazuje tekstową zawartość raportu; rzeczywisty układ widać w pobranym dokumencie. Endpointy `/api/projects/{key}/export.xlsx` i `.docx` zwracają pliki binarne z odpowiednim MIME, nazwą i nagłówkiem kompletności. Niekompletne plany również zachowują diagnostykę w plikach.

XLSX ma arkusze Plan, Podsumowanie, Wolne bloki, Walidacja. Wszystkie wartości są tekstem, w tym CIDR, liczniki IPv6 i treść przypominająca formułę. To raport, a nie drugi kalkulator sieciowy. Komórka dłuższa niż 32767 znaków daje czytelny błąd, zamiast cichego obcięcia. DOCX zawiera tytuł, założenia, tabele per budynek, rezerwacje, IPv6, uwagi, wolne bloki i walidację.

„Druk / PDF” prowadzi do `/p/{key}/print`, gdzie wszystkie szczegóły są rozwinięte. Przycisk uruchamia okno drukowania przeglądarki. Zapis PDF zależy od dostępnych opcji tej przeglądarki; aplikacja nie potrzebuje serwera konwersji ani zainstalowanego Office.

Motyw Systemowy/Jasny/Ciemny wybierasz u góry. Preferencja jest zapisywana lokalnie w przeglądarce. Tab zachowuje standardową nawigację; Enter i Shift+Enter przechodzą między widocznymi polami edytora. Ctrl+D działa w wierszu segmentu lub budynku. Kopia dostaje nowe ID i puste przypięcia obu rodzin; źródło zostaje bez zmian. Kliknięcie CIDR w tabeli wyniku kopiuje adres, a komunikat w stopce potwierdza operację.

Jawne `serve --host 0.0.0.0` dodano dla kontenera. Domyślny zwykły start nadal wiąże tylko `127.0.0.1`.

## Historia, szablony, blokady i diagram (v1.1)

Biblioteka „Przyspiesz pracę szablonem” znajduje się nad strukturą projektu. Gotowe zestawy „Obiekt podstawowy” i „Obiekt rozbudowany” działają od pierwszego uruchomienia. Własny wzorzec zapiszesz przy wierszu budynku lub lokalizacji; opcjonalną nazwę wpiszesz w „Jak zapisać własny wzorzec?”. Wzorzec lokalizacji zawiera wszystkie jej budynki i segmenty. Aby utworzyć kilka oddziałów, wybierz wzorzec i wpisz nazwy po jednej w wierszu (do 50). Zapis obejmuje całą listę jako jedną zmianę.

Szablony są wspólne dla projektów w tej samej bazie i dostępne przy tworzeniu nowego projektu. Kopie dostają nowe identyfikatory i automatyczną adresację; nie przenoszą blokad ani przypięć. VLAN-y są zachowane, a globalne reguły IPv6/P2P wynikają z projektu docelowego. Szablony lokalizacji wymagają tej aktualizacji interfejsu; wcześniejszy pakiet 1.1 w `dist` ich nie obsługuje. Eksport pojedynczego projektu JSON nie zawiera biblioteki szablonów.

Pełna instrukcja: [release-v1.1.md](historia/release-v1.1.md). Widoki: `/p/{key}/history` i `/p/{key}/diagram`. Lista historii: `GET /api/projects/{key}/history?offset=0`; migawka: `GET /api/projects/{key}/history/{revision}`; diagram: `GET /api/projects/{key}/diagram.svg` (z `?download=true` jako załącznik). Przywracanie używa formularza POST z CSRF i oczekiwaną rewizją. Nie ma zmian bazy przez GET.

## Kalkulator bez poleceń terminala

Na stronie Kalkulator wybierz zadanie:

- **VLSM według liczby urządzeń:** podaj pulę IPv4 oraz nazwy i liczby urządzeń w poszczególnych sieciach. W podanej liczbie uwzględnij bramę i planowany zapas. Kalkulator rezerwuje dodatkowo adres sieci i broadcast. Wiersze można dodawać i usuwać, do 128 sieci.
- **Informacje o adresie:** IPv4/IPv6 z prefiksem; dla IPv4 także maska lub wildcard. Wynik zawiera m.in. sieć i dane reverse DNS.
- **Równy podział według liczby:** wybierz 2, 4, 8, 16 itd. podsieci. Inna liczba daje polski komunikat z podpowiedzią.
- **Równy podział według prefiksu:** np. sieć /24 na sieci /26. Podgląd ma maksymalnie 256 wierszy, również dla IPv6.

Tabela VLSM pokazuje CIDR, maskę, zakres, broadcast, pojemność i pozostałe adresy. Poniżej są wolne bloki. Przy braku miejsca wynik jest oznaczony jako częściowy i wymienia nieprzydzielone sieci. Kliknięcie CIDR kopiuje go do schowka. Kalkulator nie zapisuje ani nie zmienia projektu; pełny edytor dodatkowo obsługuje zapas procentowy, rezerwacje, P2P i loopback.

## Poprawki IPv6 i diagnostyki

Pierwsze włączenie IPv6 z domyślnymi regułami tworzy ULA /48, lokalizacje /52 oraz budynki i infrastrukturę /56. Bez blokad i przypięć daje to do 16 lokalizacji. Dotychczasowe pule i hierarchie nie zmieniają się automatycznie. Przycisk „Dopasuj podział IPv6 do lokalizacji” sprawdza pasujący wariant /52–/56 lub /56–/60, uwzględniając aktualne zapotrzebowanie i blokady; zmiana dotyczy IPv6. Operacja odmawia zmiany przy przypiętych adresach IPv6. Przy niepasującym zapotrzebowaniu trzeba świadomie zmienić pulę lub reguły.

„Nie — planuj tylko IPv4” ustawia `v6_active=false`, zachowując konfigurację IPv6. Stan przetrwa restart i eksport/import. Zamrożenie IPv4 podczas zawieszenia nie usuwa zachowanych przypięć IPv6. Po ponownym włączeniu nieprawidłowe przypięcia lub blokady dadzą czytelny błąd, zamiast ich cichego usunięcia.

Komunikaty pokazują ścieżkę lokalizacja → budynek → sieć i polski opis. „Przejdź do pola” otwiera potrzebne ustawienia i ustawia kursor. Kody, ID i pełne dane są pod „Szczegółami technicznymi”; informacje o poprawnym planie są zwinięte. Wydruk pomija techniczne szczegóły oraz przyciski nawigacji do pól.

## Usprawnienia pracy

[Instrukcja filtrów, biblioteki, kopii danych, podglądu zmian i nowych raportów](historia/USPRAWNIENIA.md). Pełna kopia: `GET /library/backup.sqlite3`. Biblioteka: `GET /templates` i `GET/POST /templates/{key}`. Zatwierdzenie podglądu: `POST /p/{key}/apply-preview`, z CSRF, oczekiwaną rewizją i dokumentem projektu. Eksport i druk obsługują `profile=full` lub `profile=brief`.
