# Odbiór etapu 6

Data: 14.10.2026. Lokalna wersja 1.0.0. Ukończono 6A, 6B i 6C; nie utworzono zdalnego repozytorium ani publicznego wydania.

## Funkcje

XLSX obejmuje cztery wymagane arkusze, filtr, zamrożone nagłówki i identyfikację, powtarzane nagłówki wydruku oraz pełny wynik z walidacją. Wszystkie wartości są tekstowe — dotyczy to również treści zaczynających się od znaków formuł, komunikatów błędów i dokładnych liczników IPv6. Limit 32767 znaków komórki jest kontrolowany, bez cichego obcinania.

DOCX obejmuje tytuł i status, założenia i ustawienia, tabelę IPv4 i IPv6 każdego budynku, rezerwacje, uwagi, infrastrukturę, wolne bloki i walidację. Wiersze nie dzielą się między stronami, nagłówki są powtarzane, a stopka zawiera status i numer strony. Oba formaty działają w CLI i API, a zapis plików jest atomowy. Format binarny wymaga pliku docelowego CLI.

Interfejs ma motywy Systemowy/Jasny/Ciemny, standardowy Tab, Enter/Shift+Enter w edytorze, Ctrl+D/przycisk Duplikuj dla segmentu, kopiowanie CIDR i osobny widok druku. Kopia ma nowe ID i puste przypięcia, bez modyfikacji źródła. VLAN jest zachowany, więc użytkownik może zobaczyć ostrzeżenie o powtórzeniu.

Dodano dokumentację architektury, instrukcję użytkownika/publikacji, zrzuty, cztery pliki Office AV/T4, opis lokalnego wydania, Dockerfile/Compose i job CI. Skrypt tworzy paczkę źródeł według jawnej listy. MIT pozostaje propozycją w `LICENSE-MIT.proposed.txt`; nie wybrano aktywnej licencji.

## Testy

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.11.0 | 672 testy zaliczone |
| Windows / Python 3.12.14 | 672 testy zaliczone |
| Odbiór Office/HTTP/CLI po poprawkach składu | 111 testów zaliczonych |
| Ruff i formatowanie | Bez uwag |
| mypy --strict | Bez uwag, 35 plików pakietu |
| pip check | Bez konfliktów, oba środowiska i czysta instalacja |

24 nowe pozycje testowe obejmują ponowne otwarcie raportów, dokładną zgodność wierszy XLSX z wejściem, adresy i uwagi w DOCX, Unicode/kontrolne znaki XML, teksty przypominające formuły, brak makr i hiperłączy, częściowe/puste plany, odmowę błędnych danych, limit komórki, brak uszkodzenia wcześniejszego pliku, prawdziwe CLI i HTTP oraz duplikowanie zamrożonego segmentu.

Istniejące testy T1–T5, właściwości, kalkulatora, JSON, CSV/Markdown, SQLite i konfliktów zapisu pozostały zaliczone. Dane binarne Office mogą mieć różne czasy ZIP; sprawdzamy zawartość i typy, nie wymagamy identycznych bajtów kolejnych zapisów.

## Kontrola dokumentów

Przykłady AV i T4 wygenerowano przez funkcje pakietu, otwarto ponownie bibliotekami `openpyxl` i `python-docx`, następnie wyrenderowano LibreOffice 26.2.6. Było to narzędzie QA rozpakowane wyłącznie w `.tmp`, bez globalnej instalacji i bez zależności aplikacji od tego programu.

DOCX renderowano kanonicznym `render_docx.py`. Poprawiono odziedziczone linie tytułów, połączenie opisu z początkiem tabeli, niedzielenie wierszy i odległość od stopki. Końcowy AV ma 11 stron, T4 6 stron. Obejrzano zestawienia stron i szczegóły tabel, w tym IPv6 oraz końcową walidację. Duża liczba stron AV wynika z pełnej listy wolnych bloków infrastruktury IPv6.

XLSX również przekonwertowano do PDF w Calc i sprawdzono układ oraz nagłówki. Szeroki Plan drukuje się w skali 100% z powtarzanymi kolumnami lokalizacji/budynku/segmentu, zamiast zmniejszać 32 kolumny do jednej nieczytelnej strony. Pozostałe arkusze dopasowują szerokość do strony. Zapisane arkusze mają filtr i zamrożenie, a źródła tekstowe nie stają się formułami.

## Kontrola przeglądarki

Na localhost utworzono projekt formularzem i segment LAN. Sprawdzono Enter przenoszący fokus z hostów do VLAN-u, ciemny/jasny motyw i zachowanie wyboru między stronami, freeze oraz Ctrl+D. W pierwszej próbie skrót wysyłał zwykły zapis przez `requestSubmit`; poprawiono go na kliknięcie właściwego przycisku HTMX. Ponowna kontrola pokazała nowe ID i puste przypięcie kopii, przy zachowanym adresie źródła. Po wyczyszczeniu przypięć oba segmenty otrzymały rozłączne `/26` w rodzicu `/25`.

Kliknięcie CIDR zapisało `10.0.0.0/25` do schowka, co potwierdzono odczytem i komunikatem. Widok druku zawiera raport bez edytora, z rozwiniętymi metrykami i wolnymi blokami. Wywołanie natywnego okna drukowania zablokowało sterowanie kartą; nie potwierdzono zapisu PDF do pliku w tej przeglądarce. Tymczasową kartę zamknięto. To ograniczenie automatycznego odbioru okna przeglądarki, nie deklaracja udanego wydruku HTML.

Menu XLSX zostało otwarte i plik pobrano rzeczywiście przez przeglądarkę. Potwierdzono, że pobrany plik jest poprawnym XLSX. Zrzuty jasnego/ciemnego edytora, widoku raportu i eksportu zapisano w dokumentacji.

Próba importu pliku przez przeglądarkę nie uzyskała zgody użytkownika. Nie ponawiano jej ani nie zastosowano obejścia. Kontrolę UI wykonano na nowych danych wpisanych w formularzu. Nie wpływa to na wcześniejsze testy importu etapu 5 ani testy granic HTTP wykonywane w izolowanym TestClient.

## Pakiet i źródła

Zbudowano wheel/sdist 1.0.0. Sprawdzono zgodność wszystkich źródeł pakietu, szablonów i zasobów z wheel. Świeża `.venv-release-10` zawiera tylko zależności uruchomieniowe; nie zawiera pytest ani httpx2. Z katalogu poza projektem, w izolowanym trybie Pythona, uruchomiono serwer z `site-packages` i bazą utworzoną podczas kontroli UI.

Po restarcie przetrwały cztery elementy projektu. Przez rzeczywiste HTTP sprawdzono strony, widok druku, zasoby i pięć eksportów. Przez CLI wykonano dziesięć eksportów: pięć formatów dla poprawnego AV i częściowego T3, z poprawnymi kodami 0/1. Arkusze i dokumenty z instalacji otworzyły się ponownie.

Paczka źródeł zawiera wyłącznie wskazane katalogi i rozszerzenia. Sprawdzono brak baz, środowisk, cache, źródłowego PDF i wzorców typowych kluczy prywatnych/tokenów. Przykłady są syntetyczne. Licencja MIT jest plikiem propozycji z miejscem na autora; aktywny LICENSE i deklaracja licencji pakietu nie zostały dodane.

Compose i workflow CI zostały sparsowane parserem YAML; potwierdzono mapowanie localhost i trwały wolumen. Dockerfile pracuje bez roota, ma healthcheck i jawny nasłuch kontenera. **Silnika Docker brak na komputerze odbioru**, więc nie deklarujemy lokalnego zaliczenia obrazu. Przygotowany job CI wykona budowę i restart po rzeczywistej publikacji na GitHubie. Zdalnego CI jeszcze nie uruchomiono.

## Ręczny odbiór użytkownika

Uruchom `adresplan serve`, dodaj własny segment albo importuj przykład T4. Sprawdź A=`10.20.0.0/23`, B=`10.20.2.0/24`, C=`10.20.3.0/27`. Pobierz XLSX/DOCX, obejrzyj arkusze i tabele. Wybierz motyw, skopiuj CIDR i wypróbuj Ctrl+D w wierszu segmentu. W widoku Druk/PDF wybierz zapis PDF w swojej przeglądarce. Przed publikacją wybierz licencję i autora praw.
