# Szczegółowa historia zmian — AdresPlan

Pełny dziennik prac z kolejnych etapów. Skrócona wersja: [CHANGELOG.md](../../CHANGELOG.md).

## Po wersji 1.1 (weszło do 1.2.0)

### 2026-10-16 — audyt zapisu, podglądu i szablonów

- Zatwierdzenie podglądu czeka na obliczenia dla ostatniej edycji. Nowe dane, żądanie w toku, opóźniona odpowiedź lub błąd nie pozwalają zatwierdzić starszej propozycji.
- Usunięto blokadę zapisu większych struktur wynikającą z domyślnego limitu 1000 pól formularza. Limit jest nadal skończony (100 000 pól), a ograniczenie rozmiaru żądania pozostaje aktywne. Sprawdzono pełny formularz ze 100 segmentami.
- Automatyczny zapis odświeża nazwy, VLAN-y, CIDR-y i przynależność używane przez filtry oraz opisy wyliczenia wielkości podsieci, zachowując edytowane pola.
- Zmiana użycia IPv6 nie nadpisuje jawnie klikniętej akcji, np. dodania elementu lub zamrożenia adresów.
- Tworzenie i zmiana nazwy szablonu korzystają ze wspólnej walidacji (1–200 znaków). Walidacja następuje przed zapisem projektu, a starsze wzorce z długimi nazwami nadal można aktualizować, przenosić do kosza i przywracać. Błędna nazwa zwraca HTTP 422.
- **750 testów przeszło na Pythonie 3.12.14 i 750 na 3.11.0**, dodatkowo cztery testy stanu JavaScript. Ruff, formatowanie i mypy bez błędów. W przeglądarce potwierdzono odświeżanie danych, blokadę nieaktualnego podglądu i zapis jego ostatniej wersji; konsola bez błędów.
- Zrestartowano serwer użytkownika; wszystkie trzy projekty zachowały nazwy, rewizje i daty zapisu. Raport z pozostałymi zaleceniami: `docs/AUDYT-2026-10-16.md`. Starsze paczki w `dist` nie zostały przebudowane.

### 2026-10-16 — usprawnienia C: kalkulator, wyjaśnienia i dokumentacja

- Kalkulator VLSM potrafi utworzyć projekt z kompletnych wyników. Zachowuje CIDR-y jako przypięcia oraz zerowy dodatkowy zapas i brak osobnej bramy/rezerwy statycznej, aby nie policzyć tych potrzeb drugi raz. Niekompletny VLSM nie tworzy projektu.
- Ustawienia szczegółowe segmentu wyjaśniają liczbę urządzeń, zapas, bramy, dodatkowe adresy statyczne, wymagane minimum prefiksu i pojemność. Wyliczenie korzysta z funkcji silnika; P2P i loopback mają osobny opis.
- Dane dokumentacji: autor, organizacja/inwestor, opis i data. Są zapisywane z projektem, wersjonowane, przenoszone przez JSON i uwzględniane w raportach. Opcjonalne pola rozszerzają bieżący schemat JSON 3; starsze dokumenty otrzymują puste wartości.
- Eksporty MD/XLSX/DOCX i druk/PDF mają profil szczegółowy oraz skrócony. Skrócony pokazuje dane dokumentacji, przydziały i istotne ostrzeżenia; JSON/CSV pozostają pełnym zapisem wejścia lub tabelą segmentów. Tekst w XLSX nadal jest literalny, bez wykonywania formuł.
- Końcowa weryfikacja usprawnień A–C: **746 testów przeszło na Pythonie 3.12.14 i 746 na 3.11.0**, Ruff i mypy bez błędów. Po doprecyzowaniu ścieżek obiektów przeszło dodatkowo 12 testów usprawnień.
- W przeglądarce sprawdzono filtrowanie, edycję i dodanie w podglądzie, zapis jako jednej wersji, odrzucenie podglądu, nazwę/kosz/przywrócenie szablonu, utworzenie projektu z kalkulatora oraz metrykę i skrócony widok druku. Konsola bez błędów. Zrzuty: `docs/screenshots/improvements-preview.jpg`, `docs/screenshots/improvements-report.jpg`.
- Przed aktualizacją lokalnej bazy wykonano i sprawdzono kopię SQLite w `.tmp/before-library-v3-295610334b424e529e96208c34cd9b4d.sqlite3`. Po restarcie serwer i biblioteka odpowiedziały HTTP 200, a lista projektów wraz z ich rewizjami i datami pozostała identyczna.

### 2026-10-16 — usprawnienia B: podgląd skutków przed zapisem

- Można wybrać zapis automatyczny lub najpierw sprawdzić skutki. W drugim trybie edycja i dodawanie elementów przeliczają podgląd bez zapisywania bazy.
- Tabela porównuje zapisane i proponowane CIDR-y obu rodzin, podając pełną ścieżkę obiektu. Zatwierdzenie zapisuje cały podgląd jako jedną wersję; odrzucenie wraca do zapisanego projektu.
- Podgląd jest przechowywany tylko w bieżącej karcie. Zmiana wersji projektu w innej karcie blokuje zatwierdzenie starego podglądu. Projekt o innym ID nie może być podmieniony. Zapisywanie wzorców wymaga wcześniejszego zatwierdzenia podglądu.
- Testy sprawdziły brak zapisów podczas edycji, zachowanie dodanych elementów w kolejnych podglądach, jeden końcowy zapis, konflikt rewizji i odmowę podmiany projektu.

### 2026-10-16 — usprawnienia A: struktura, biblioteka i kopia danych

- Dodano filtrowanie struktury i wyników według lokalizacji/budynku oraz nazwy, VLAN-u i CIDR. Filtry są poza formularzem danych; ukrywanie wierszy nie wyłącza ich pól. Wybór widoku jest zachowywany w sesji przeglądarki.
- Biblioteka szablonów ma podgląd zawartości, zmianę nazwy, aktualizację z zapisanego obiektu i kosz z przywracaniem. Kontrola wersji zabezpiecza przed nadpisaniem z innej karty. Zmiana wzorca nie zmienia wcześniejszych projektów.
- SQLite migruje transakcyjnie z wersji 2 do 3, dodając stan kosza i numer wersji szablonu. Dotychczasowe projekty i historia są zachowane.
- Przycisk pełnej kopii tworzy spójny obraz czynnej bazy mechanizmem SQLite backup: projekty, historia, aktywne i usunięte szablony. Instrukcja pokazuje otwarcie kopii jako osobnej bazy bez nadpisywania obecnej.
- Weryfikacja części: 40 testów biblioteki, migracji i wcześniejszego zapisu przeszło; w tym odtworzenie kopii, konflikty szablonów i przywracanie z kosza. Dalsze usprawnienia są realizowane osobno.

### 2026-10-16 — ukończono poprawki 1, 2 i 3 z analizy

#### 1. IPv6 w wielu lokalizacjach

- Pierwsze włączenie IPv6 z domyślnymi regułami przygotowuje ULA /48 i lokalizacje /52, z budynkami i infrastrukturą /56. Pula pomieści do 16 takich lokalizacji, zależnie od blokad i przypięć.
- Pokazano bieżącą hierarchię i teoretyczną pojemność. Jawny przycisk dopasowania sprawdza warianty podziału według rzeczywistej struktury; obsługuje również wariant lokalizacja /56, budynki/infrastruktura /60 dla większej liczby oddziałów.
- Istniejące hierarchie nie są samoczynnie zmieniane. Przypięcia IPv6 blokują dopasowanie, a IPv4 pozostaje bez zmian. Brak pasującego podziału daje błąd bez częściowego zapisu.

#### 2. Wyłączanie IPv6 z zachowaniem konfiguracji

- Dodano `v6_active` w modelu i JSON. Wyłączenie zawiesza obliczenia IPv6 oraz jego walidację semantyczną, zachowując pulę, reguły, blokady, przypięcia segmentów i infrastruktury.
- Włączenie nie losuje zachowanego prefiksu i ponownie sprawdza konfigurację. Nieaktualne blokady/przypięcia zgłaszają błąd. Zamrażanie podczas zawieszenia nie usuwa zachowanej infrastruktury IPv6.
- Raporty i diagram oznaczają IPv6 jako wyłączone, a zawieszone blokady nie są prezentowane jako czynne. JSON zachowuje całą konfigurację.
- Eksport JSON ma format 3 i dołączony schemat `project-v3.schema.json`; import przyjmuje 1, 2 i 3. Brak nowego pola w starszym pliku zachowuje dotychczasowe działanie IPv6. Historyczne schematy/migawki pozostają zachowane; układ tabel SQLite nadal ma wersję 2.

#### 3. Czytelne komunikaty

- Główne komunikaty pokazują nazwy obiektów w hierarchii i polskie wyjaśnienie. Błędy i ostrzeżenia są widoczne, informacje o planie zwinięte.
- Kody diagnostyczne, identyfikatory i pełne dane pozostają w rozwijanych szczegółach. Przycisk „Przejdź do pola” ustawia kursor oraz otwiera ukryte ustawienia; błędy formularza otrzymały czytelne etykiety pól.
- Wydruk pomija techniczne szczegóły i przyciski przechodzenia do pól. CLI zachowuje dokładny format diagnostyczny.

#### Weryfikacja i zakres

- **734 testy przeszły na Pythonie 3.12.14 i 734 na 3.11.0**. Obejmują 2/16/17 lokalizacji, dopasowanie bez zmiany IPv4, odmowę przy przypięciach, zachowanie konfiguracji po restarcie/JSON, ponowną walidację, zamrażanie podczas zawieszenia, starsze formaty oraz raporty MD/XLSX/DOCX/SVG. Ruff i mypy bez błędów.
- W przeglądarce: projekt z dwoma oddziałami IPv6, zamrożenie, wyłączenie/odświeżenie/włączenie i identyczny prefiks oraz wszystkie CIDR-y. Sprawdzono czytelność komunikatów i ustawienie kursora przez przycisk; brak błędów konsoli. Zrzut: `docs/screenshots/corrections-diagnostics.jpg`.
- Wdrożono wyłącznie trzy zlecone poprawki. Filtrowanie, rozbudowa biblioteki szablonów, backup i inne usprawnienia z analizy czekają na osobne polecenie. Wcześniejsze archiwa `dist` nie obejmują tych zmian.

### 2026-10-16 — analiza dalszego rozwoju

- Ukończono przegląd przepływu planowania, modeli, szablonów, historii, kopii danych, eksportów i spójności wydań. Wnioski i propozycja kolejności prac: `docs/ANALIZA_ROZWOJU.md`.
- Odtworzono w pamięci ograniczenie domyślnego IPv6: dwa oddziały w ULA /48 przy /48 na lokalizację dają `v6_insufficient_space`, mimo poprawnych przydziałów IPv4.
- Wskazano potrzebę zachowania konfiguracji po wyłączeniu IPv6, uproszczenia komunikatów, filtrowania struktury, zarządzania szablonami i pełnej kopii biblioteki.
- Etap obejmował analizę i dokumentację; nie wdrażano proponowanych funkcji ani nie modyfikowano projektów użytkownika.

### 2026-10-16 — świadomy wybór IPv6 i ogólne zestawy obiektów

- Ukończono wybór „Czy planujesz używać IPv6 w tej sieci?” przy tworzeniu projektu i w edytorze. Domyślnie nowy projekt planuje tylko IPv4. Istniejące projekty z prefiksem IPv6 zachowują swoją adresację.
- Dopiero „Tak” przygotowuje prywatny prefiks ULA /48 oraz pokazuje ustawienia, przypięcia segmentów i kolumnę wyników IPv6. Prefiks można zastąpić np. globalnym prefiksem od operatora; zwykły zapis nie generuje go ponownie.
- „Nie” wyłącza planowanie IPv6 po stronie serwera, usuwa bieżący prefiks, przypięcia i blokady IPv6, zachowując przypięcia oraz blokady IPv4. Poprzednia konfiguracja pozostaje w historii. Ukryte wartości IPv6 nie są walidowane ani stosowane, a blokady IPv6 wymagają wcześniejszego włączenia rodziny.
- Dodawanie budynku lub lokalizacji z szablonu nie włącza IPv6 w projekcie IPv4. Zachowano zgodność importów i API — obecność prefiksu nadal określa planowanie IPv6 w danych projektu; schemat pliku i bazy nie zmienia się.
- Zestawy startowe noszą nazwy „Obiekt podstawowy” i „Obiekt rozbudowany”. W rozbudowanym zastąpiono segment „Audio / wideo” ogólnym „Urządzenia i usługi”. Dotychczasowe klucze zestawów zachowano dla zgodności; własne nazwy użytkownika pozostają bez zmian.
- Weryfikacja: **74 testy formularzy, szablonów i interfejsu przeszły**, w tym 5 nowych testów wyboru IPv6, zachowania ULA, czyszczenia rezerwacji, historii i nazw zestawów. Ruff i mypy bez błędów. W przeglądarce sprawdzono tworzenie projektu IPv4, włączenie IPv6, wyłączenie i zachowanie decyzji po odświeżeniu; brak błędów konsoli. Zrzut: `docs/screenshots/ipv6-choice.jpg`.

### 2026-10-16 — łatwiejsze planowanie sieci i kalkulator VLSM

#### Ukończono — nawigacja i tworzenie projektu

- Usunięto plakietkę „SQLite · zapis lokalny”, zwiększono odstęp przy wyborze motywu i dodano `v.` przed wersją.
- Strona startowa i edytor prowadzą przez pulę adresów, strukturę i dokumentację. Przy zakładaniu projektu można nazwać pierwszą lokalizację i budynek oraz zacząć od szablonu.
- Formularz dodawania znajduje się **nad dodanymi elementami**. Liczbę urządzeń i VLAN można podać przed dodaniem segmentu. Pola dopasowują się do wybranego typu elementu.
- Przy wyborze budynku widać też jego lokalizację, co rozróżnia kopie o takich samych nazwach. Poprawiono kontrast przycisków po najechaniu w ciemnym motywie.

#### Ukończono — kalkulator dla użytkownika

- Osobne tryby: VLSM według liczby urządzeń, informacje o adresie, równy podział według liczby podsieci lub prefiksu.
- Edytowalne wiersze nazw i zapotrzebowania, przykładowe sieci, tabela CIDR/masek/zakresów/broadcastu/pojemności/zapasu oraz lista wolnych bloków.
- Czytelne komunikaty po polsku bez flag terminala. Zbyt mała pula daje jawnie oznaczony częściowy wynik i listę nieprzydzielonych sieci.
- VLSM dotyczy zwykłych sieci LAN IPv4: liczba urządzeń obejmuje bramę i własny zapas, kalkulator dodaje sieć i broadcast. Limit 128 sieci; równy podział IPv4/IPv6 pozostaje ograniczony do 256 wierszy podglądu. Dotychczasowe API kalkulatora i CLI zachowują swój zakres.
- Inspiracja układem zadań i tabel: [NetworkCalc](https://networkcalc.com/vlsm-calculator/) i [Subnet Plus](https://subnetplus.com/vlsm-calculator.html). Implementacja używa istniejącego silnika projektu.

#### Ukończono — szablony jako podstawowy sposób przyspieszania pracy

- Dostępne od razu zestawy „Małe biuro” i „Obiekt z realizacją AV”, z podglądem liczby urządzeń i VLAN-ów.
- Biblioteka znajduje się nad strukturą. Własne szablony budynków nadal działają; można też zapisać całą lokalizację z jej budynkami i segmentami.
- Z jednego wzorca można utworzyć 1–50 lokalizacji, wpisując nazwy po jednej w wierszu. Zestaw jest zapisywany jako jedna zmiana projektu; błędne dane nie zapisują części kopii.
- Szablony są dostępne w kolejnych projektach i po restarcie. Kopie mają nowe ID, zachowują VLAN-y i efektywne ustawienia segmentów, bez przypięć i blokad adresowych. Globalne reguły IPv6/P2P pochodzą z projektu docelowego.

#### Weryfikacja

- **718 testów przeszło na Pythonie 3.12.14 i 718 na 3.11.0**; 18 nowych przypadków obejmuje m.in. rozmiary LAN, brak miejsca, walidację, granice podglądu IPv6, zapis/odtwarzanie szablonu lokalizacji, poprawne ID, atomowość i ręczne dodawanie hostów/VLAN.
- Ruff i mypy bez błędów. Testy przeglądarki na osobnej bazie: VLSM i dodanie wiersza, równy podział i błąd dla 3 podsieci, projekt z zestawu biurowego, zapis wzorca, dwie nowe lokalizacje, zachowanie biblioteki po restarcie i dodanie sieci z VLAN-em.
- Zrzut sprawdzonego układu: `docs/screenshots/usability-editor.jpg`. Zmiany są w źródłach; archiwa `dist` z wcześniejszego wydania 1.1 nie były przebudowywane w tym etapie.

### 2026-10-15–16 — v1.1: historia, szablony, zajęte podsieci i diagram

#### Ukończono 1.1A — historia planów

- Transakcyjna migracja SQLite z wersji 1 do 2, zachowująca dotychczasowy projekt i numer rewizji. Zastany zapis staje się początkiem historii; wcześniejszych wersji nie odtwarzamy.
- Migawki wejścia i wyników z datą, przyczyną zapisu i wersją aplikacji. Porównanie korzysta z zapisanych wyników, bez przeliczania dawnych przydziałów.
- Stronicowana historia, porównywanie dowolnych zachowanych wersji, pobranie migawki JSON i przywracanie jako nowej wersji. Kontrola rewizji chroni przed nadpisaniem nowszych zmian. Identyczny autosave nie tworzy pustych wersji.
- Sprawdzono migrację i jej rollback, restart, równoczesne zapisy, niezmienność migawek, przywracanie i blokadę zapisu ze starej karty.

#### Ukończono 1.1B — budynki i szablony

- Duplikowanie budynku wraz z segmentami, nowe ID i poprawne relacje rodziców. Kopia otrzymuje puste przypięcia IPv4/IPv6; blokady pozostają przy oryginale.
- Zapis własnych szablonów budynków w SQLite i ich zastosowanie w dowolnym projekcie/lokalizacji. LAN/mgmt zachowują efektywne reguły zapasu i bram; P2P/loopback zachowują specjalne reguły bez bramy i zapasu.
- VLAN-y są zachowywane, powtórzenia nadal dają ostrzeżenia. Globalne reguły IPv6 i długość P2P pochodzą z projektu docelowego.
- Sprawdzono identyfikatory, przypięcia, role infrastrukturalne, restart biblioteki szablonów oraz tworzenie budynku z szablonu w przeglądarce.

#### Ukończono 1.1C — blokady zajętych podsieci

- Lista blokad IPv4/IPv6 przypisana do projektu, lokalizacji lub budynku; masowe wklejanie CIDR z opcjonalnym opisem po średniku, komentarze # i usuwanie pojedynczej blokady.
- Alokator odejmuje blokady przed przydziałami; nakładające się blokady jednej puli są liczone jako suma zbiorów. Przypięcie kolidujące z blokadą daje błąd, bez zastępczego adresu.
- Dobór bloków nadrzędnych uwzględnia zajęte miejsce. Automatyczna infrastruktura IPv6 omija blokady lokalizacji, zamrożona zgłasza konflikt.
- Metryki zajętości obejmują przydziały i blokady. Blokady są widoczne w JSON, Markdown, DOCX, opcjonalnym arkuszu XLSX i widoku druku. CSV pozostaje tabelą segmentów.
- Eksport JSON w wersji 2; import obsługuje wersje 1 i 2. Zachowano schemat v1 i dodano schemat v2 do pakietu.
- Sprawdzono zachowanie wolnych bloków, pełne wyczerpanie puli, konflikt z freeze, zakresy obu rodzin i test właściwościowy bilansu adresów. W przeglądarce potwierdzono dodanie listy dwóch blokad.

#### Ukończono 1.1D — diagram i wydanie lokalne

- Diagram hierarchii projektu, lokalizacji, budynków, segmentów, infrastruktury IPv6 i zewnętrznych blokad. Kolory błędów/blokad, dopasowanie do okna lub pełny rozmiar, pobieranie samodzielnego SVG.
- SVG nie zawiera skryptów ani zewnętrznych zasobów; teksty są escapowane. Diagram opisuje hierarchię adresacji, nie fizyczną topologię sieci.
- Instrukcja v1.1, opis aktualizacji danych, dokumentacja JSON/API/architektury, zrzuty historii i diagramu oraz syntetyczny przykład `examples/v11-branch.json` z diagramem.
- Wersja pakietu **1.1.0**. Na Pythonie 3.11.0 i 3.12.14 po **700 testów zaliczonych**; Ruff, formatowanie, mypy --strict i pip check bez uwag.
- W przeglądarce sprawdzono autosave, szablony, kopię budynku, blokady, porównanie, wynik przywrócenia wersji 2 jako 5, powiększenie diagramu i rzeczywiste pobranie SVG.
- Wheel zainstalowano jako aktualizację 1.0→1.1 w odizolowanym środowisku bez narzędzi deweloperskich. Spoza źródeł sprawdzono restart, zachowanie historii i szablonów, widoki HTTP, SVG, pięć eksportów HTTP i pięć eksportów CLI.
- Przygotowano wheel, sdist oraz archiwum źródeł `dist/address-plan-1.1.0-source.zip`. Historia aplikacji i rzeczywiste bazy użytkownika nie wchodzą do paczki źródeł.
- **v1.1 ukończono lokalnie 16.10.2026.** Szczegóły i ograniczenia: `docs/v1.1-verification.md`. Nie publikowano repozytorium ani wydania; MIT pozostaje propozycją. Docker i natywny zapis PDF zachowują ograniczenia odbioru opisane po etapie 6.

### 2026-10-14 — Etap 6: dokumenty Office, wygoda i przygotowanie wersji 1.0

#### Dodano

- **6A:** XLSX z arkuszami Plan, Podsumowanie, Wolne bloki i Walidacja; filtry, zamrożone nagłówki/identyfikację, jawne tekstowe typy komórek i czytelny wydruk szerokiej tabeli na kilku stronach.
- DOCX: tytuł, status i założenia, ustawienia projektu, tabele IPv4 i IPv6 per budynek, zakresy, uwagi, infrastruktura, wolne bloki i pełna walidacja. Powtarzane nagłówki, niedzielone wiersze i stopka z numerem strony.
- Oba formaty w CLI, API i menu pobierania. Eksport binarny CLI wymaga `--output`; zapisy pozostają atomowe. Wyniki częściowe zachowują diagnostykę i kod zakończenia 1.
- Literalny zapis tekstów i adresów w XLSX, bez formuł, aktywnych hiperłączy i utraty dokładności dużych liczników IPv6. Przekroczenie 32767 znaków komórki daje komunikat zamiast cichego obcięcia.
- **6B:** widok druku/PDF, motyw systemowy/jasny/ciemny, Enter/Shift+Enter, kopiowanie CIDR do schowka oraz duplikowanie segmentu przyciskiem i Ctrl+D. Kopia ma nowe ID oraz puste przypięcia obu rodzin.
- **6C:** cztery przykładowe dokumenty Office, zrzuty ekranu, instrukcje, opis architektury, opis wersji 1.0 i przygotowania publikacji.
- Dockerfile bez roota, Compose z trwałym wolumenem i portem komputera ograniczonym do localhost, jawne `serve --host 0.0.0.0` dla kontenera oraz job CI sprawdzający kontener i dane po restarcie.
- Skrypt pakujący źródła według jawnej listy plików, `.gitattributes` i propozycję MIT do decyzji autora. Bazy, środowiska, cache, prywatne eksporty i lokalne narzędzia nie trafiają do paczki publikacyjnej.
- 24 pozycje testowe Office: ponowne otwarcie, zgodność danych, teksty specjalne, częściowe/puste plany, limit komórki, atomowy zapis, CLI/HTTP, widok druku i kopia segmentu.

#### Poprawiono

- Ctrl+D faktycznie przekazuje operację duplikowania do HTMX, zamiast wykonywać zwykły zapis formularza.
- Usunięto odziedziczone linie tytułów DOCX, poprawiono powiązanie opisów z tabelami, podział wierszy i odstęp od stopki.
- Wykluczono katalogi tymczasowych narzędzi i środowisk z Ruff; obsługa wyboru rodzica nie dodaje kolejnych słuchaczy przy każdym odświeżeniu wyniku.

#### Weryfikacja i stan

- Lokalna wersja pakietu **1.0.0**; format JSON i schemat SQLite pozostają w wersji 1.
- Windows / Python 3.11.0 i 3.12.14: po **672 zaliczone testy**; dodatkowy odbiór 111 testów Office/HTTP/CLI po korektach składu. Ruff, formatowanie, mypy --strict dla 35 plików i pip check bez uwag.
- Raporty XLSX i DOCX otwarto ponownie programowo. DOCX AV/T4 wyrenderowano do 11 i 6 stron, skontrolowano układ; arkusze sprawdzono również przez wydruk LibreOffice do PDF.
- Przeglądarka: Enter, jasny/ciemny motyw, Ctrl+D na zamrożonym źródle, puste przypięcie kopii, schowek, widok raportu i rzeczywiste pobranie poprawnego XLSX. Import pliku w tej kontroli nie uzyskał zgody — użyto nowego projektu utworzonego formularzem, bez obchodzenia odmowy.
- Zbudowano wheel/sdist i sprawdzono czystą instalację poza źródłami, bez narzędzi deweloperskich: restart z zachowaniem danych, strony/druk, lokalne zasoby, pięć eksportów HTTP i dziesięć eksportów CLI dla planu poprawnego/częściowego.
- YAML Compose/CI został sparsowany i sprawdzony. **Dockera nie uruchomiono lokalnie** — silnik nie jest zainstalowany. Zapis PDF z natywnego okna przeglądarki nie został automatycznie potwierdzony; druk raportów Office został sprawdzony.
- **Cały etap 6 i sześć etapów implementacji ukończono.** Niczego nie opublikowano, zdalnego CI nie uruchamiano. MIT pozostaje wyraźnie oznaczoną propozycją, nie wybraną licencją. Szczegóły: `docs/stage-6-verification.md`.

### 2026-10-14 — Etap 5: SQLite i lokalny interfejs w przeglądarce

#### Dodano

- Polecenie `serve`, lokalny serwer FastAPI/Jinja2/HTMX i polski interfejs: lista projektów, tworzenie, import JSON, duplikowanie, drzewo i tabela edycji.
- Automatyczne przeliczanie i zapis po 300 ms, wynik IPv4/IPv6 z rezerwacjami, linki walidacji do wierszy, wykorzystanie pul, wolne bloki i infrastruktura IPv6.
- Zamrażanie adresów, czyszczenie przypięć, generator ULA, kalkulator i podgląd/pobieranie CSV, Markdown i JSON.
- SQLite z transakcjami, wersją schematu i zapisem wyłącznie danych wejściowych; domyślny plik w katalogu danych użytkownika, opcje `--database` i `ADRESPLAN_DB`.
- Kontrolę wersji projektu: równoczesny zapis starej karty daje konflikt, a zwykła odpowiedź przeliczenia zachowuje edytowane pola i fokus. Operacje zmiany struktury chwilowo blokują formularz.
- API planu, kalkulatora, eksportów, listy i aktualizacji projektu. Wynik JSON jest zgodny z CLI i ponownie wyliczany z wejścia.
- Ograniczenie serwera do `127.0.0.1`, kontrolę Host/Origin, tokeny formularzy/API, autoescape i CSP. HTMX 2.0.11 z licencją oraz CSS/JS są dołączone lokalnie do paczki.
- 31 pozycji testowych dotyczących SQLite, restartu, izolacji, równoczesnego zapisu, formularzy, API, eksportów, niepoprawnego wejścia i polecenia `serve`; instrukcję interfejsu/API i raport odbioru.

#### Poprawiono

- Rozróżnienie pustej wartości „dziedzicz bramę” od jawnego „bez bramy” podczas zapisu formularza.
- Zamykanie plików importu również po błędzie, bez pozostawiania tymczasowych uchwytów.
- Błędne wartości pozostają w formularzu, a ostatni poprawny zapis w bazie nie jest zastępowany. Niekompletne plany mają jawny status i nie mogą zostać zamrożone.

#### Weryfikacja i stan

- Wersja pakietu `0.2.0.dev1`; JSON `schema_version=1`, SQLite `user_version=1`.
- Windows / Python 3.11.0 i 3.12.14: po **648 zaliczonych testów**. Ruff, formatowanie i mypy --strict dla 34 plików bez uwag; `pip check` bez konfliktów.
- Kontrola rzeczywistej przeglądarki: tworzenie/dodawanie, zapis bez przeładowania, ostatnia z szybkich zmian, walidacja i link do wiersza, ULA, freeze, konflikt dwóch kart, kalkulator i podgląd raportu. Zasoby interfejsu pochodzą z lokalnego `/static`.
- Wheel/sdist zbudowano; zwykłą instalację wheel sprawdzono poza źródłami, bez pytest/httpx2. Serwer zachował projekt i przypięcia po restarcie; strony, zasoby, trzy eksporty, API kalkulatora i CLI działają.
- **Etap 5 ukończony.** Etap 6 (XLSX/DOCX, druk, motywy i przygotowanie publikacji) pozostaje nierozpoczęty. Niczego nie opublikowano; zdalnego CI nie uruchamiano.

### 2026-10-14 — Część 4C: eksporty i ukończenie CLI v0.1

#### Dodano

- Polecenie `export PROJEKT.json --format csv|md|json`, zapis plikowy albo sam dokument na stdout; diagnostykę na stderr i kod 1 dla planów niekompletnych.
- CSV: segmenty, hierarchia, VLAN/rola, hosty z zapasem, IPv4, maski, bramy, zakresy, broadcast, IPv6, RA, końce łączy i uwagi; jawny status i diagnostykę.
- Raport Markdown: założenia i ustawienia, lokalizacje/budynki i przypięcia, tabele per budynek, infrastruktura IPv6, metryki, wolne bloki i pełną walidację.
- Cytowanie CSV, UTF-8 z BOM dla plików CSV, neutralizację tekstu przypominającego formuły oraz bezpieczne cytowanie Markdown/HTML w nazwach i uwagach.
- Osiem projektów JSON: T1–T5, wariant VLAN hex, celowy błąd VLAN 110 i syntetyczną sieć AV; `examples/budynek.json` odpowiada T4. Dotychczasowy przykład 4A zachowano.
- Cztery raporty AV/T4 do przejrzenia i wersjonowania; test zgodności ich treści z aktualnym eksporterem.
- Instrukcję eksportów, katalog przykładów, opis lokalnego wydania v0.1 i raport końcowego odbioru.
- 62 pozycje testowe: pola i zakresy eksportów, błędy/teksty specjalne, pliki, przykłady i rzeczywiste polecenia CLI.

#### Zmieniono

- Wersja pakietu: `0.1.0`. Format JSON pozostaje `schema_version=1`; brak nowych zależności uruchomieniowych.
- Wspólne przygotowanie zwalidowanego, świeżego planu i atomowy zapis dla wszystkich formatów. Reguły rdzenia i przydziały pozostają zgodne z T1–T5.
- README ma prostą instalację dla użytkownika oraz osobne polecenia narzędzi deweloperskich.

#### Weryfikacja i stan

- Windows / Python 3.11.0 i 3.12.14: po **617 zaliczonych testów**, Ruff i mypy --strict dla 29 plików bez uwag, `pip check` bez konfliktów.
- Wheel/sdist `0.1.0` zbudowano. Zwykła instalacja wheel w świeżym środowisku przeszła kontrolę spoza repozytorium: wszystkie cztery polecenia, osiem projektów, 24 eksporty, UTF-8/BOM, schema, kalkulator, zamrożenie/rozbudowa oraz kody 0/1/2.
- Niekompletne plany zachowują udane przydziały i diagnostykę w eksporcie; nie można ich zamrozić. Nieudany zapis nie obcina poprzedniego pliku.
- **Cały etap 4 ukończony; lokalne wydanie CLI v0.1 gotowe.** Etapu 5 (SQLite i interfejs przeglądarkowy) nie rozpoczęto.
- Niczego nie opublikowano na GitHubie/PyPI; zdalnego CI nie uruchamiano. Licencja pozostaje do wyboru przez autora przed publikacją.

### 2026-10-14 — Część 4B: polecenia terminalowe i kalkulator

#### Dodano

- `plan PROJEKT.json`: hierarchia i adresy IPv4/IPv6, rezerwacje, infrastruktura oraz metryki; opcje `--show-free`, `--verbose`, `--json` i `--output`.
- `calc`: wejście z bitami hosta, prefiksem, maską lub wildcard; IPv4 /31 i /32, jawne RFC 1918, reverse DNS; IPv6 compressed/exploded, typ adresu/bloku i liczba podsieci /64.
- Podział przez `--split N` albo `--new-prefix X`, z leniwym podglądem do 256 wierszy. Dla N=3 komunikat proponuje 4, bez automatycznej zmiany wejścia.
- `freeze PROJEKT.json --output WYNIK.json`: zamrożenie obu rodzin i infrastruktury; odmowa zmiany pliku docelowego przy błędnym planie.
- Polską pomoc, diagnostykę z kodem i identyfikatorem węzła, UTF-8 oraz oddzielne stdout/stderr.
- Kody zakończenia: 0 — sukces/ostrzeżenia, 1 — niekompletny plan, 2 — błędne wejście/argumenty lub błąd pliku.
- Zabezpieczenie prezentowanych nazw przed znakami sterującymi terminala; dane źródłowe w JSON pozostają zachowane.
- 128 pozycji testowych, w tym prawdziwe wywołania CLI i dwa testy właściwościowe po maksymalnie 80 przykładów; instrukcję CLI i raport odbioru.

#### Weryfikacja i stan

- Wersja deweloperska: `0.1.0.dev5`. Format JSON nadal `schema_version=1`; brak nowych zależności uruchomieniowych.
- Windows / Python 3.11.0 i 3.12.14: po 555 zaliczonych testów; Ruff i mypy --strict dla 24 plików bez uwag, brak konfliktów zależności.
- Podział całego IPv6 /0 na /128 pozostaje ograniczony; liczniki są dokładne. Niekompletny plan daje kod 1 i może być zapisany do naprawy, ale nie może być zamrożony.
- Ponowny odczyt zamrożenia i dodanie segmentu zachowuje istniejące IPv4/IPv6 i infrastrukturę. Nieudane zamrożenie pozostawia poprzednią zawartość pliku bez zmian.
- Zbudowano wheel/sdist i sprawdzono zwykłą instalację wheel w osobnym środowisku, poza repozytorium: `plan`, `calc`, `freeze`, UTF-8, T5, schemat JSON i kody zakończenia działają.
- **Ukończono tylko 4B.** Polecenie `export`, CSV/Markdown, komplet przykładów i odbiór v0.1 pozostają w 4C; interfejs w etapie 5.
- Niczego nie opublikowano na GitHubie; zdalnego CI nie uruchamiano.

### 2026-10-14 — Część 4A: JSON projektu i walidacja wejścia

#### Dodano

- Dokument `schema_version=1`: pełne wejście projektu i świeżo wyliczony plan; zapis/odczyt tekstu i plików UTF-8.
- Modele wejścia Pydantic 2 poza core: typy, zakresy, CIDR, enumy, nieznane pola i struktura drzewa; polskie błędy ze ścieżkami pól i stabilnymi kodami.
- Ponowne przeliczanie wyniku przy imporcie — zawartość zapisanej migawki planu nie steruje adresacją.
- Zachowanie ID, kolejności, opisów, wszystkich ustawień segmentów i projektu, przypięć IPv4/IPv6 oraz zamrożonej infrastruktury IPv6.
- Zapis przez plik tymczasowy i atomową podmianę, bez wcześniejszego obcinania poprzedniego pliku.
- Obsługę BOM UTF-8, limit 16 MiB oraz odrzucanie duplikatów kluczy, nieprawidłowych liczb JSON i błędnego kodowania.
- Schemat Draft 2020-12 jako zasób instalowanej paczki, przykład syntetycznej sieci AV i demonstrację `examples/stage4a_json.py`.
- Dokumentację formatu JSON i raport odbioru; podział etapu 4 na części 4A, 4B i 4C.
- 112 pozycji testowych: poprawne i niepoprawne wejście, eksport/import T4/T5, komplet pól podtypów, zamrożenie, błędy zapisu i test właściwościowy 60 wariantów.

#### Zmieniono

- Wersja deweloperska pakietu: `0.1.0.dev4`; numer formatu JSON jest niezależny od wersji aplikacji.
- Zależności uruchomieniowe obejmują Pydantic 2.14.1; wszystkie zależności lokalnych narzędzi i uruchomienia są utrwalone w `requirements-dev.lock`. Rdzeń nadal używa tylko biblioteki standardowej.
- mypy oraz konfiguracja CI sprawdzają cały pakiet, również warstwę JSON i eksporter.

#### Weryfikacja i stan

- Windows / Python 3.11.0 i 3.12.14: po 427 zaliczonych testów; Ruff i mypy --strict dla 22 plików bez uwag; brak konfliktów zależności.
- Eksport → import daje identyczny projekt i plan; po wczytaniu zamrożenia dodanie segmentu zachowuje stare adresy i infrastrukturę.
- Zbudowano wheel/sdist i sprawdzono instalację wheel w nowym środowisku, spoza folderu projektu: schemat jako zasób pakietu, JSON, T5, zamrożenie i dokładne duże liczniki IPv6 działają.
- Poprawny strukturalnie projekt z błędami sieci można zapisać i odczytać wraz z przeliczoną diagnostyką; błędy formatu i drzewa są odrzucane.
- **Ukończono tylko 4A.** Etap 4 pozostaje w trakcie. Nie wdrożono pełnego CLI, kalkulatora, CSV/Markdown ani interfejsu.
- Niczego nie opublikowano na GitHubie; zdalnego CI nie uruchamiano.

### 2026-10-14 — Etap 3: IPv6, infrastruktura i zamrażanie obu protokołów

#### Dodano

- Hierarchiczny planer IPv6 na wspólnym alokatorze: lokalizacje, budynki /56 domyślnie i LAN/mgmt /64.
- Konfigurację większych i mniejszych bloków, zapas w podsieciach /64 oraz uwzględnianie przypiętych segmentów w położeniu przodków.
- Wydzieloną infrastrukturę lokalizacji: rezerwę /64, pulę łączy /127 i pulę loopbacków /128.
- Strategie sequential i VLAN decimal-as-hex z walidacją zakresu, braku VLAN-u, kolizji i konfliktu z przypięciami.
- Generator ULA poza rdzeniem, formy compressed/exploded, strefy ip6.arpa oraz informacje o bramie i trybie SLAAC/DHCPv6.
- Wspólny wynik IPv4/IPv6, metryki i wolne bloki ze wskazaniem rodzaju puli.
- Zamrażanie adresów obu rodzin i pul infrastruktury; kontrolę zachowania istniejących przydziałów przy dodawaniu segmentów.
- Przykład `examples/stage3_ipv6.py` oraz raport `docs/stage-3-verification.md`.
- 112 nowych pozycji testowych; łącznie 315, w tym T5, losowe projekty, przypięcia, brak miejsca, małe pule, ULA, reverse DNS i kontrola leniwej iteracji.

#### Doprecyzowano

- Lokalizacja /48 wymaga większej puli projektu przy wielu lokalizacjach. Pula /56 wymaga jawnego mniejszego układu.
- VLAN 110 oznacza offset 272: błąd w /56 i poprawny przydział w /52; obsługiwane są VLAN-y 1–999.
- Przypięcia sprzeczne z numeracją lub infrastrukturą są błędami, bez automatycznej zmiany istniejących adresów.
- Dotychczasowy test zachowania pól IPv6 otrzymał przypięcie LAN spoza nowo wydzielonej infrastruktury.

#### Weryfikacja

- Windows / Python 3.11.0 i 3.12.14: po 315 zaliczonych testów; mypy --strict dla 13 plików core bez uwag.
- Ruff — lint i formatowanie bez uwag; pip check — bez konfliktów zależności.
- Wektory T1–T5 zgodne; po dodaniu LAN-u, P2P i loopbacka zamrożone adresy IPv4/IPv6 oraz infrastruktura pozostają bez zmian.
- Lokalny T5 obejmujący oba protokoły: 100 przeliczeń, mediana około 7,0 ms i maksimum około 9,8 ms.
- Zbudowano i sprawdzono osobną instalację pakietu `0.1.0.dev3`.

#### Stan projektu

- Etap 3 ukończony; etapu 4 nie rozpoczęto.
- Pełne CLI, kalkulator i import/eksport projektu należą do etapu 4, interfejs w przeglądarce do etapu 5.
- Nie publikowano repozytorium ani wydania; zdalny workflow CI pozostaje przygotowany do uruchomienia po publikacji.

### 2026-10-14 — Etap 2: hierarchia IPv4, rezerwacje i zamrażanie

#### Dodano

- Hierarchiczny planer IPv4: rozmiary liczone od segmentów w górę, przydział bloków od projektu w dół.
- Wyznaczanie położenia przodków z przypiętych segmentów oraz symulację powiększania bloków przy fragmentacji.
- Zakresy użyteczne, 0–3 adresy bram, rezerwę statyczną i DHCP obliczane bez listowania hostów; osobne zachowanie P2P i loopbacków.
- Walidację puli, przypięć, VLAN-ów, kolizji, zawierania i pojemności; ostrzeżenia oraz metryki na każdym poziomie hierarchii.
- Czystą funkcję `freeze(project, plan)`, przypinającą adresy aktualnego, kompletnego planu i zachowującą oryginalne dane wejściowe.
- Odrzucanie zamrażania planów obcych, nieaktualnych i zmodyfikowanych oraz testy braku miejsca bez przesuwania istniejącej adresacji.
- Demonstrację `examples/stage2_hierarchy.py`, dokumentację odbioru etapu 2 i aktualizację README/PLAN.
- 81 dodatkowych pozycji testowych: T4, rezerwacje, walidacja, zamrażanie oraz losowe hierarchie i przypięcia. Łącznie 203 testy.
- Odrzucanie surowych tekstów w polach ról i bram rdzenia, aby nie pomijały reguł opartych na typowanych wartościach enum. Konwersja tekstowego wejścia należy do późniejszej warstwy CLI/web.

#### Doprecyzowano

- Brama na końcu podsieci pozostawia zakres statyczny na początku, a DHCP pomiędzy nimi.
- Kolizje są sprawdzane między rodzeństwem i końcowymi segmentami; prawidłowe zawieranie rodzica i dziecka jest dozwolone.
- Wykorzystanie bloków budynków, segmentów i wolnego miejsca jest liczone osobno, bez podwójnego sumowania.
- Zbyt duża lub kolidująca hierarchia przypięć daje błąd, zamiast automatycznego przesuwania istniejących adresów.

#### Weryfikacja

- Windows / Python 3.11.0 i 3.12.14: po 203 zaliczone testy; mypy --strict dla 10 plików core bez uwag.
- Ruff — lint i formatowanie bez uwag; pip check — brak konfliktów zależności.
- Wektory T1–T4 zgodne; T4: A `10.20.0.0/23`, B `10.20.2.0/24`, C `10.20.3.0/27`.
- T4 na lokalnym Pythonie 3.12: 100 przeliczeń, mediana około 1,4 ms, maksimum około 3,5 ms.
- Przykład po zamrożeniu dodaje `10.20.1.232/30`, zachowując wszystkie wcześniejsze adresy.
- Zbudowano i sprawdzono pakiet instalacyjny wersji deweloperskiej `0.1.0.dev2`.

#### Stan projektu i ograniczenia

- Etap 2 ukończony; etapu 3 nie rozpoczęto.
- Nadal nie ma pełnego planera IPv6, importu projektu/pełnego CLI, eksportów ani interfejsu w przeglądarce.
- Zamrażanie na tym etapie obejmuje IPv4; istniejące ustawienia i przypięcia IPv6 są zachowywane.
- Nie opublikowano repozytorium ani wydania; zdalny workflow CI nie był uruchamiany.

### 2026-10-14 — Etap 1: pakiet, modele i alokator IPv4

#### Dodano

- Pakiet Pythona w układzie `src`, wersję deweloperską `0.1.0.dev1` i entry point `adresplan` z pomocą oraz numerem wersji.
- Typowane modele projektu, ustawień, lokalizacji, budynków, segmentów, alokacji, planu i komunikatów walidacji.
- Walidację struktury drzewa: wymagane identyfikatory i nazwy, duplikaty, rodziców, poziomy oraz cykle.
- Obliczanie wielkości podsieci IPv4 z całkowitoliczbowym zapasem, bramami i rezerwą statyczną; osobne reguły P2P /31 lub /30 i loopback /32.
- Generyczny alokator best-fit dla IPv4 i IPv6, z obsługą przypięć, stabilną kolejnością i zbieraniem błędów bez przerywania pozostałych przydziałów.
- Diagnostykę braku miejsca: zapotrzebowanie, wolne adresy, największy wolny blok i sugestię większej puli sprawdzaną przez symulację.
- 122 testy, w tym dokładne wektory T1–T3, testy właściwościowe dla obu rodzin adresów oraz przypadki graniczne i błędne przypięcia.
- Konfigurację pytest, Hypothesis, Ruff, mypy oraz workflow GitHub Actions dla Linux/Python 3.11 i 3.12 oraz Windows/Python 3.12.
- Utrwalone wersje narzędzi w `requirements-dev.lock`, instrukcję w `README.md`, demonstrację `examples/stage1_vlsm.py` i raport w `docs/stage-1-verification.md`.

#### Poprawiono

- Zgodność konstruktorów generycznych modeli z Pythonem 3.11.0, zachowując niemodyfikowalność rekordów.
- Obsługę niecałkowitych prefiksów i powtarzających się identyfikatorów żądań: są zgłaszane jako błędy, zamiast powodować niekontrolowane przerwanie alokacji.

#### Weryfikacja

- Windows / Python 3.11.0: `pytest` — 122 zaliczone; `mypy --strict src/adresplan/core` — bez uwag.
- Windows / Python 3.12.14: `pytest` — 122 zaliczone; mypy — bez uwag.
- `ruff check .` i `ruff format --check .` — bez uwag; `pip check` — brak konfliktów zależności.
- Zbudowano archiwum źródeł i wheel; sprawdzono instalację wheel w oddzielnym środowisku i działanie poza katalogiem źródeł.
- Przykład T1 zwraca oczekiwane /25, /26, /27, /28 i wolny blok `192.168.10.240/28`.

#### Stan projektu i ograniczenia

- Etap 1 ukończony; etap 2 nie został rozpoczęty.
- Działa alokacja na jednym poziomie; hierarchia sieci, zakresy DHCP/statyczne, zamrażanie projektu, pełny planer IPv6, eksporty i interfejs należą do kolejnych etapów.
- Workflow CI jest przygotowany, ale nie był uruchomiony na GitHubie. Wyniki powyżej pochodzą z lokalnego Windows.
- Nie opublikowano repozytorium ani wydania. Nazwa prezentowana w README: Address Plan (AdresPlan); nazwa pakietu i polecenia: `adresplan`.

### 2026-10-13 — Przygotowanie projektu i dokumentacji

#### Dodano

- Plan realizacji w `PLAN.md`: sześć etapów, technologie, architekturę, zakres wydań v0.1 i v1.0 oraz kryteria odbioru.
- Odpis tekstowy wszystkich dziewięciu stron specyfikacji PDF w `SPEC.md`.
- Zasady przygotowania repozytorium, testowania i publikacji projektu na GitHubie.
- Ten plik historii zmian oraz obowiązek aktualizacji po każdym ukończonym etapie.

#### Doprecyzowano

- Reguły kolizji i zawierania podsieci w hierarchii.
- Znaczenie liczby hostów i rezerwacji adresów.
- Rozmieszczenie rezerwacji przy bramie na końcu podsieci.
- Obsługę przypiętych bloków, zamrażania planu i braku miejsca.
- Podział IPv6 między lokalizacje oraz zachowanie przy mniejszych pulach.
- Zasady reverse DNS, podziału na podsieci i interpretacji metryk oraz testów.

#### Weryfikacja

- Odczytano wszystkie dziewięć stron PDF i sprawdzono kompletność odpisu tekstowego.
- Sprawdzono graniczne przykłady rozmiarów podsieci IPv4 oraz wybrane obliczenia z wektorów T2, T4 i T5.
- Sprawdzono obecność sześciu etapów, siedmiu decyzji technicznych i poprawne zamknięcie bloków tekstowych w dokumentacji.
- Testów aplikacji nie uruchamiano — implementacja jeszcze nie powstała.

#### Stan projektu

- Ukończono przygotowanie planu i dokumentacji.
- Etapy implementacji 1–6 pozostają niewykonane.
- Nie opublikowano kodu ani wydania v0.1/v1.0.

## Zasady aktualizacji

1. Po każdym ukończonym etapie z `PLAN.md` dodaj wpis do sekcji „Niewydane”, nad starszymi wpisami. Nie usuwaj wcześniejszej historii.
2. Nagłówek wpisu ma zawierać rzeczywistą datę ukończenia w formacie `YYYY-MM-DD`, numer etapu i krótki opis.
3. Opisz faktycznie dodane funkcje, zmiany i poprawki. Uwzględnij tylko pasujące kategorie; nie dopisuj pustych sekcji.
4. Podaj wykonane sprawdzenia i ich wynik. Nie oznaczaj niewykonanych testów jako zaliczonych. Istotne ograniczenia opisz wprost.
5. Etap można oznaczyć jako ukończony dopiero po spełnieniu jego kryteriów odbioru i przejściu wymaganych sprawdzeń. Jeśli praca została przerwana, ewentualny wpis ma wyraźnie wskazywać, że etap jest w toku.
6. Wpis ma być czytelny dla osoby odwiedzającej GitHuba: opisywać zachowanie aplikacji i jego znaczenie, bez zapisu całej rozmowy z asystentem.
7. Przy faktycznym wydaniu przenieś dotyczące go wpisy pod nagłówek wersji i daty publikacji. Zachowaj sekcję „Niewydane” dla kolejnych zmian. Planowana wersja nie jest wydaniem.

Przygotowanie dokumentacji opisane powyżej jest historią prac wstępnych, a nie ukończeniem etapu 1.
