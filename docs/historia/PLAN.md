# AdresPlan — plan realizacji i publikacji na GitHubie

Data planu: 13.10.2026. Aktualizacja: 16.10.2026. Status: ukończono etapy 1–6 oraz v1.1, lokalna wersja `1.1.0`. Publikacja i wybór licencji pozostają decyzjami autora.

Podstawa: `12_AdresPlan_specyfikacja.pdf`, wersja 1.0 z 09.10.2026, wszystkie 9 stron. Odpis tekstowy znajduje się w `SPEC.md`. Poniższe decyzje doprecyzowują niejednoznaczne miejsca dokumentu; nie są cytatami z PDF.

## 1. Co budujemy

**Lokalną aplikację dla administratora sieci, która z listy lokalizacji, budynków i VLAN-ów wylicza plan adresacji IPv4 oraz IPv6 i przygotowuje dokumentację.** Kod będzie w publicznym repozytorium GitHub; użytkownik pobierze aplikację i uruchomi ją u siebie.

Przykładowy scenariusz: zbór z salą główną i budynkiem biurowym. Administrator dodaje segmenty Biuro, Goście, AV, Kamery, Zarządzanie oraz łącza routerów. Wpisuje liczbę urządzeń i zapas. Dostaje podsieci, bramy, zakresy statyczne i DHCP, podsumowania budynków oraz ostrzeżenia. Eksportuje plan do dokumentacji. Po wdrożeniu zamraża adresy, żeby dodanie kolejnego VLAN-u nie przesunęło istniejących podsieci.

**GitHub służy do przechowywania kodu i wersji.** FastAPI uruchamia się lokalnie na `127.0.0.1:8000`, a interfejs otwiera się w przeglądarce. GitHub Pages obsługuje strony statyczne, więc nie uruchomi serwera FastAPI ani bazy SQLite. Może później pokazywać opis projektu i zrzuty ekranu. Źródło: [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

Repozytorium ma pokazywać przede wszystkim kompetencje sieciowe: poprawność VLSM, hierarchię adresacji, IPv6, sumaryzację, rezerwacje i weryfikację wyników. Czytelny interfejs pomaga te kompetencje zaprezentować.

## 2. Zakres i wydania

### v0.1 — pierwsze użyteczne wydanie, po etapie 4

- Projekt → lokalizacja → budynek → segment, trwałe identyfikatory i kolejność.
- IPv4: VLSM, hierarchia, przypięte bloki, rezerwacje, walidacja, wolne bloki i metryki.
- IPv6: /64 dla LAN, /127 dla P2P, /128 dla loopbacków, infrastruktura, ULA i reverse DNS.
- Zamrażanie istniejących alokacji, bez przesuwania ich przy kolejnym przeliczeniu.
- Kalkulator IPv4/IPv6 i ograniczony podgląd podziału na podsieci.
- CLI: `plan`, `calc`, `export`, `freeze`; import i eksport JSON, CSV i Markdown.
- Przykłady odpowiadające T1–T5, testy i dokumentacja uruchomienia.

### v1.0 — pełna aplikacja z PDF, po etapie 6

- Wszystko z v0.1.
- SQLite, lista projektów, nowy projekt, duplikowanie projektu, import JSON.
- Polski interfejs: drzewo, tabela edytowana bez przeładowania strony, wynik i walidacja.
- Kalkulator w przeglądarce, zamrożenie planu, kopiowanie CIDR.
- Eksport XLSX i DOCX, podgląd eksportu i widok do druku/PDF przez przeglądarkę.
- Obsługa klawiatury, jasny/ciemny motyw, lokalne zasoby bez CDN.
- Pakiet instalacyjny Pythona, Dockerfile, testy CI i instrukcja publikacji.

### v1.1 — ukończono 16.10.2026

- [x] Historia i porównywanie zapisanych planów, przywracanie jako nowej wersji.
- [x] Szablony i duplikowanie budynków.
- [x] Import listy zajętych podsieci IPv4/IPv6 jako blokad wybranej puli.
- [x] Diagram hierarchii i eksport SVG.
- [x] Migracja SQLite 1→2, import starszego JSON, 700 testów na Pythonie 3.11 i 3.12.

Instrukcja: `docs/release-v1.1.md`. Odbiór: `docs/v1.1-verification.md`.

### Po v1.1

Generowanie konfiguracji urządzeń pozostaje poza zrealizowanym zakresem. Nie dodajemy teraz logowania, skanowania, IPAM, DHCP/DNS ani integracji z routerami.

Wyjątek do tabeli zakresu PDF: strategia IPv6 `vlan_decimal_as_hex` będzie w v0.1, ponieważ szczegółowy etap 3 i test T5 wymagają jej już wtedy, mimo umieszczenia jej w kolumnie „Wersja 2” na stronie 1.

## 3. Technologie i powody wyboru

| Element | Decyzja | Po co |
| --- | --- | --- |
| Język | Python 3.12 jako środowisko referencyjne, minimum 3.11 | Czytelny kod i standardowy moduł sieciowy |
| Obliczenia | `ipaddress`, `dataclasses`, arytmetyka całkowitoliczbowa | Wspólny, niezależny od UI rdzeń |
| Walidacja wejścia | Pydantic v2 w CLI/web/import | Kontrola typów, zakresów i struktury |
| CLI | `argparse` ze standardowej biblioteki | Mało zależności, wystarczy do tego zakresu |
| Serwer | FastAPI + Uvicorn | HTTP/API i lokalny serwer |
| Interfejs | Jinja2 + HTMX + zwykły CSS | Edycja tabeli bez osobnej aplikacji frontendowej i bez npm |
| Zapis | SQLite przez `sqlite3` | Jeden plik; na tym etapie ORM nie daje niezbędnej korzyści |
| Dokumenty | `openpyxl`, `python-docx`, `csv`, `json` | Formatowanie i eksport |
| Sprawdzanie | pytest, Hypothesis, Ruff, mypy | Testy przykładów, losowych przypadków, stylu i typów |
| Instalacja | `venv` + `pip`, plik zależności dla dewelopera | Działa na Windows bez dodatkowego menedżera |
| Automatyzacja | GitHub Actions | Testy uruchamiane po zmianach kodu |
| Kontener | Dockerfile po ukończeniu funkcji | Opcjonalny sposób uruchomienia, nie warunek korzystania |

Nie trzeba znać Reacta, Kubernetes ani administracji serwerem bazodanowym. Wersje bibliotek należy dobrać i sprawdzić podczas etapu 1, utrwalić dla odtwarzalnego środowiska deweloperskiego, a później aktualizować świadomie. Nie wpisujemy tutaj niesprawdzonych numerów najnowszych wydań.

Źródła techniczne: [ipaddress](https://docs.python.org/3.12/library/ipaddress.html), [HTMX](https://htmx.org/docs/), [FastAPI i Uvicorn](https://fastapi.tiangolo.com/deployment/server-workers/), [testowanie Pythona w GitHub Actions](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

## 4. Architektura

```text
Przeglądarka → web (FastAPI/Jinja2/HTMX) ─┐
                                       ├→ application → core
Terminal → CLI ────────────────────────┘       ├→ store (SQLite)
                                              └→ export (pliki)
```

`core` jest jak kalkulator: dostaje dane, zwraca wynik. Nie czyta plików, nie zna HTTP, bazy, losowości ani aktualnej godziny. Dzięki temu CLI, strona i eksport nie wyliczają trzech różnych planów.

Warstwa `application` to mały koordynator przypadków użycia: wczytaj projekt, sprawdź wejście, przelicz, zapisz albo wyeksportuj. To doprecyzowanie struktury PDF, nie osobna usługa.

```text
adresplan/
  README.md                 opis, instalacja, przykład, ograniczenia
  PLAN.md                   ten plan
  SPEC.md                   odpis źródłowego dokumentu
  LICENSE                   po wyborze licencji przez autora
  pyproject.toml            pakiet, zależności, entry point, konfiguracja narzędzi
  requirements-dev.lock     utrwalone zależności środowiska deweloperskiego
  .gitignore
  .github/workflows/ci.yml
  src/adresplan/
    core/
      models.py sizing.py allocator.py plan4.py plan6.py
      reservations.py validate.py calc.py freeze.py
    application/            przypadki użycia i schematy wejściowe
    store/                  zapis wejścia, wersja schematu SQLite
    export/                 csv_.py xlsx.py docx_.py markdown.py json_.py
    web/                    app, templates/, static/htmx.min.js, CSS
    cli.py
  examples/                 syntetyczne projekty i przykładowe eksporty
  tests/                    core, CLI, store, web, eksporty
  docs/                     architektura, model danych, instrukcja, zrzuty
  Dockerfile
```

W bazie przechowujemy bieżące wejście: ustawienia projektu, drzewo, przypięcia, blokady i opisy. Od v1.1 osobno zapisujemy historię wejścia i wyników oraz bibliotekę szablonów. Wynik jest wyliczany przez `build_plan(project) -> Plan`. JSON eksportu zawiera `schema_version`, wejście oraz wynik. Import traktuje wejście jako źródło prawdy i ponownie liczy plan; nie ufa wyliczeniom z pliku.

Modele wymagają m.in. stabilnego `id`, `parent_id`, `kind`, `sort_order`, nazwy, roli segmentu, liczby hostów, zapasu, bram, rezerwacji, VLAN-u, ustawień IPv6 i przypiętych CIDR. `Finding` ma kod, poziom, identyfikator węzła oraz szczegóły błędu; polskie komunikaty powstają na granicy UI/CLI. Plan ma jawny status kompletności i wolne bloki dla każdego poziomu.

## 5. Doprecyzowania przed implementacją

### D1. Zawieranie podsieci to nie kolizja

PDF zabrania nakładania się „dowolnych dwóch alokacji”. Rodzic i dziecko muszą się jednak zawierać: segment `10.20.0.0/24` należy do budynku `10.20.0.0/23`.

Sprawdzamy brak kolizji między rodzeństwem i między końcowymi podsieciami segmentów. Osobno sprawdzamy zawieranie dziecka w rodzicu. Nie sumujemy adresów rodziców i dzieci jako rozłącznych alokacji.

### D2. Co znaczy liczba hostów i rezerwacje

Zachowujemy wzór PDF: `grown_hosts = (hosts * (100 + growth_pct) + 99) // 100`; `usable_needed = grown_hosts + gateway_addrs + static_count`. W tym modelu `hosts` jest liczbą urządzeń poza osobno zarezerwowaną pulą statyczną i bramami. UI musi to wprost wyjaśniać, żeby administrator nie policzył serwerów dwa razy. Zapas jest nieujemnym procentem całkowitym.

Wartość `gateway=none` wymaga `gateway_addrs=0`. Wartość `first/last` wymaga 1–3 adresów bram. LAN bez zapotrzebowania jest błędem. P2P i loopback nie stosują zwykłego wzoru LAN; niedopuszczalne rezerwacje bram/statycznych i niezgodna liczba urządzeń mają dawać czytelny błąd, nie być ignorowane.

### D3. Brama na końcu podsieci

„Statyczne zaraz po bramie” nie działa, gdy brama jest ostatnim użytecznym adresem. Ustalamy: bramy zajmują górny koniec zakresu, statyczne dolny, DHCP środek. Dla `10.20.1.0/26`, jednej bramy `last` i 8 statycznych: brama `.62`, statyczne `.1–.8`, DHCP `.9–.61`. Dla trzech bram rezerwujemy `.60–.62`, z wirtualną bramą `.62`. Przy `first` wirtualna brama jest pierwsza, po niej pozostałe bramy i statyczne. Pusty DHCP reprezentujemy jako brak zakresu, nie odwrócone granice.

### D4. Przypięte bloki i brak miejsca

Przypięcie musi być we właściwej rodzinie, wyrównane, wystarczająco duże i mieścić się w przodkach. Rozmiar rodzica zależy również od położenia przypiętych dzieci: małe segmenty na odległych końcach puli wymagają dużego wspólnego bloku. Wyznaczamy najmniejszego wspólnego przodka CIDR dla przypięć, następnie symulujemy upakowanie reszty. Zwiększanie bloku ma granicę w puli projektu; nie może prowadzić do nieskończonej pętli. Przy nieprzypiętym rodzicu jego kandydackie położenie musi obejmować przypięte dzieci.

Zamrożenie zapisuje istniejące alokacje węzłów i wydzielonej infrastruktury IPv6 jako jawne wejście, atomowo. Wolne wnętrze przypiętego rodzica pozostaje dostępne. Gdy się zapełni, nowy segment dostaje błąd. Zmiana rozmiaru budynku wymaga świadomej edycji przypięcia; automat nie przesuwa istniejącej sieci. Nie zamrażamy niekompletnego planu.

### D5. IPv6 dla kilku lokalizacji i małych pul

PDF opisuje lokalizację /48, ale model ma jedną pulę projektu i wiele lokalizacji. Przyjmujemy jawne `v6_site_prefix`, domyślnie /48, i `/48` dla każdej lokalizacji z większej puli projektu. Projekt /48 może obsłużyć jedną taką lokalizację. Dodanie drugiej daje błąd z sugestią większej puli lub świadomej zmiany podziału; nie próbujemy umieścić dwóch /48 w jednym /48.

Dla puli projektu /56 administrator może wybrać lokalizację /56, budynki /60 i infrastrukturę /60. Ustawienia poziomów muszą się mieścić i pozwalać na LAN /64; domyślny układ /48 → /56 → /64 nie jest bezmyślnie stosowany do każdej puli. Dodajemy `v6_infra_prefix`, domyślnie /56. Pierwszy pasujący blok lokalizacji jest infrastrukturą; pierwszy jego /64 jest zarezerwowany, drugi dla łączy /127, trzeci dla loopbacków /128. Zachowuje to adresy T5.

„Nie mniejszy niż /56” dotyczy rozmiaru bloku, a nie liczby prefiksu. Domyślny budynek dostaje co najmniej 256 podsieci /64: /56 lub większy blok, np. /52. Przy ustawieniu /60 można dać 16 podsieci. Zapas IPv6 liczymy procentowo i wybieramy najmniejszy dozwolony blok, który mieści zapotrzebowanie.

Dokumentacyjny `2001:db8::/32` rozpoznajemy przed ogólnym testem `2000::/3`. Generator ULA losuje 40-bitowy Global ID poza czystym rdzeniem; wygenerowany prefiks zapisujemy do projektu. `build_plan` nie losuje niczego. Źródło konstrukcji ULA: [RFC 4193](https://www.rfc-editor.org/rfc/rfc4193.html).

Doprecyzowanie wdrożenia etapu 3: LAN/mgmt otrzymuje blok z budynku, P2P i loopback korzystają z infrastruktury swojej lokalizacji. `Project.pinned_v6_infrastructure` przechowuje przypięcie całego bloku i trzech wydzielonych /64. Zamrażanie zapisuje je razem z przypięciami obu protokołów. Rozmiar nieprzypiętej lokalizacji jest określony przez `v6_site_prefix`; przypięcia wykraczające poza tę pojemność wymagają świadomej zmiany ustawienia. Przypięcie większego, poprawnego bloku lokalizacji pozostaje dozwolone. Nieprzypięty budynek może urosnąć w granicach /60, /56, /52, aby objąć przypięte LAN-y. Przy istniejących przypięciach wybór wolnych miejsc wykonuje wspólny alokator best-fit.

### D6. Reverse DNS i liczba podsieci

IPv4: pojedynczą zwykłą strefę pokazujemy dla granic /8, /16, /24. Dla np. /20 pokazujemy, że potrzebne są strefy na granicach oktetów; nie udajemy, że /20 ma jedną taką nazwę. Delegacje bezklasowe są poza v1.0. IPv6: nazwa strefy odpowiada długości prefiksu wyrównanego do 4 bitów. Dla /127 i /128 można pokazać dane adresów/PTR, nie obiecywać standardowej delegacji /127.

„Podziel na N równych podsieci” przyjmuje N będące potęgą dwójki. Dla N=3 komunikat proponuje 4 i czeka na zmianę wejścia. Podział musi mieścić się w rodzinie adresów, z limitem podglądu 256 wierszy. Liczba /64 wewnątrz /127 wynosi 0.

### D7. Jak czytać testy i metryki

T1–T3 testują alokator płaski. T4 testuje hierarchię, z pulą projektu i przypiętą lokalizacją `10.20.0.0/20`; bez przypięcia minimalna lokalizacja dla 800 adresów w blokach budynków to /22. T5 testuje IPv6 niezależnie od kolejności zapotrzebowań IPv4.

T2: segmenty zajmują 485 z 1024 adresów; wolne jest 539. T4: końcowe segmenty zajmują 741, bloki budynków 800, a wolne poza budynkami to 3296 z 4096. Dodatkowe 59 adresów jest wolnych wewnątrz budynków. Eksport wolnych bloków podaje poziom i rodzica.

Właściwość `num_addresses - 2 >= usable_needed` dotyczy LAN/mgmt IPv4. /31 ma dwa końce, /32 jeden; IPv6 nie odejmuje broadcastu. Równość „zajęte + wolne = pula” sprawdzamy oddzielnie na każdym poziomie, na rozłącznych blokach. Metryka ciągłości to `largest_free / total_free`; gdy wolne=0, pokazujemy „n/d”. Większy wynik oznacza mniej rozdrobnioną wolną pulę.

Błąd zabronionej puli IPv4 wykrywamy przez przecięcie z zakazanymi zakresami, również jeśli pula obejmuje je tylko częściowo. RFC 1918 sprawdzamy jawną listą trzech sieci. LAN /30 z ponad 2 potrzebnymi adresami jest błędem pojemności; ostrzeżenie nie wystarczy.

## 6. Etapy realizacji — zadania do GitHub Issues

Każdy etap kończy się działającym wynikiem i przejściem sprawdzeń. Po błędzie naprawiamy bieżący etap przed rozpoczęciem kolejnego. Po ukończeniu każdego etapu obowiązkowo aktualizujemy `CHANGELOG.md`: rzeczywista data, numer etapu, wykonane zmiany, wynik sprawdzeń i istotne ograniczenia. Zachowujemy wcześniejsze wpisy i nie przedstawiamy planowanych funkcji jako gotowych. Ukończono checklisty etapów 1–4. Na życzenie użytkownika etap 4 podzielono na 4A/4B/4C, z osobnym wpisem changelog po każdej części; końcowy odbiór 4C zakończył etap 4. Etapów 5–6 nie rozpoczęto.

### Etap 1. Pakiet, modele i alokator IPv4

- [x] `pyproject.toml`, układ `src`, entry point, konfiguracja pytest/Ruff/mypy.
- [x] Typowane modele, walidacja struktury drzewa, stabilne identyfikatory i klucze sortowania.
- [x] Całkowitoliczbowe sizing LAN, osobna obsługa /31, /30 P2P, /32.
- [x] Generyczny alokator best-fit, pinned-first, zbieranie błędów zamiast przerywania.
- [x] T1–T3 oraz testy granic, złej rodziny adresów, niepoprawnych przypięć i deterministyczności.
- [x] CI: Linux Python 3.11/3.12 i Windows Python 3.12; pytest, Ruff i mypy dla core.

Odbiór: adresy i wolne bloki T1/T2 zgodne z PDF; T3 zwraca błąd i minimalne zapotrzebowanie /25. Rdzeń nie importuje web/store/export i nie wykonuje I/O.

Wynik 14.10.2026: 122 testy przeszły na Windows z Pythonem 3.11.0 i 3.12.14; Ruff i mypy --strict dla core bez uwag. Konfiguracja CI jest gotowa, ale zdalne zadania Linux/Windows nie były uruchamiane — repozytorium nie zostało jeszcze opublikowane. Szczegóły: `docs/stage-1-verification.md`.

### Etap 2. Hierarchia IPv4, rezerwacje i zamrażanie

- [x] Rozmiary od liści w górę, alokacja od puli w dół; przypięcia uwzględniają adres i rozmiar.
- [x] Rezerwacje first/last/none, 0–3 bramy, statyczne i DHCP bez listowania hostów.
- [x] Walidacja puli, VLAN-ów, pojemności, relacji dziecko–rodzic oraz metryki.
- [x] Czysta funkcja freeze i testy dodawania segmentu po zamrożeniu.
- [x] T4, przykład /26 z PDF i przypadki z D1–D4/D7.

Odbiór: T4 zgodny co do adresu; kolizja rodzeństwa jest błędem, prawidłowe zawieranie dziecka nie jest; zamrożony plan zachowuje adresy także przy braku miejsca na nowe zapotrzebowanie.

Wynik 14.10.2026: 203 testy przeszły lokalnie na Windows z Pythonem 3.11.0 i 3.12.14. Wektory T1–T4 są zgodne; Ruff i mypy --strict dla 10 plików core bez uwag. Przykład `examples/stage2_hierarchy.py` pokazuje T4 i dodanie segmentu po zamrożeniu. Szczegóły: `docs/stage-2-verification.md`. Etapu 3 nie rozpoczęto.

### Etap 3. IPv6

- [x] Ten sam alokator, poziomy projektu/lokalizacji/budynku, zapas i blok infrastruktury.
- [x] LAN /64, łącza /127, loopbacki /128; przypięcia i brak broadcastu.
- [x] Sequential oraz VLAN jako cyfry hex; walidacja braku VLAN-u, zakresu i kolizji.
- [x] Generator ULA poza core, compressed/exploded, reverse DNS i tryb bramy/RA.
- [x] T5 i testy wielu lokalizacji, konfiguracji /56, wyłączonego IPv6 i zamrażania infrastruktury.

Odbiór: T5 zgodny; VLAN 110 nie mieści się jako offset w /56; /48 ma 65536 podsieci /64, /56 ma 256; brak pełnego rozwijania przestrzeni adresowej.

Wynik 14.10.2026: 315 testów przeszło lokalnie na Windows z Pythonem 3.11.0 i 3.12.14; Ruff i mypy --strict dla 13 plików core bez uwag. Wektory T1–T5 są zgodne. Przykład `examples/stage3_ipv6.py` pokazuje IPv6, strategie numerowania, reverse DNS, ULA oraz zachowanie obu protokołów i infrastruktury po zamrożeniu. Szczegóły: `docs/stage-3-verification.md`. Etapu 4 nie rozpoczęto.

### Etap 4. CLI, kalkulator, JSON i pierwsze wydanie

- [x] Komendy plan/calc/export/freeze; `--help`, zrozumiałe błędy, kod wyjścia niezerowy przy błędnym planie.
- [x] Schemat JSON z wersją, walidacja importu i test eksport → import → identyczny plan.
- [x] Kalkulator maski/prefiksu/wildcard, /31 i /32, IPv6, podział z limitem.
- [x] CSV i Markdown, zestaw syntetycznych przykładów T1–T5 i kościelnej sieci AV.
- [x] README z działającymi poleceniami, instrukcją Windows i wyjaśnieniem wyników.
- [x] Zbudowanie wheel, instalacja w świeżym venv i test CLI poza katalogiem repozytorium.

Odbiór: administrator potrafi wczytać projekt, policzyć adresy, zamrozić je i uzyskać dokumentację. Można oznaczyć lokalny stan jako gotowy do wydania v0.1.

#### Części etapu 4

- [x] **4A — JSON i walidacja:** dane wejściowe, wersja formatu, schemat, zapis/odczyt i zachowanie wyniku oraz przypięć po imporcie.
- [x] **4B — kalkulator i polecenia:** `plan`, `calc`, `freeze`, pomoc i czytelna diagnostyka CLI.
- [x] **4C — eksport i odbiór:** `export`, CSV/Markdown, pełen zestaw przykładów, instrukcja i końcowe sprawdzenie instalowanej aplikacji v0.1.

Wynik części 4A, 14.10.2026: 427 testów przeszło na Windows z Pythonem 3.11.0 i 3.12.14. Ruff i mypy --strict dla całego pakietu bez uwag. Format `schema_version=1` przenosi pełne wejście i świeżą migawkę planu; importer ignoruje migawkę i przelicza wynik. Zapis zachowuje istniejący plik przy błędzie walidacji lub nieudanej podmianie. Przykład `examples/stage4a_json.py` pokazuje sieć AV i odczyt zamrożenia obu rodzin/infrastruktury. Szczegóły: `docs/json-format.md` i `docs/stage-4a-verification.md`. Części 4B/4C nie rozpoczęto; v0.1 nie jest gotowe.

Wynik części 4B, 14.10.2026: 555 testów przeszło na Windows z Pythonem 3.11.0 i 3.12.14. Ruff i mypy --strict dla 24 plików pakietu bez uwag. Polecenia `plan`, `calc`, `freeze` mają polską pomoc i diagnostykę, kody zakończenia oraz obsługę JSON z 4A. Kalkulator przyjmuje bity hosta, maskę/wildcard, IPv4 i IPv6; podział jest leniwy i ograniczony do 256 wierszy. Schemat JSON pozostaje w wersji 1. Instrukcja: `docs/cli.md`; odbiór: `docs/stage-4b-verification.md`. Części 4C nie rozpoczęto; całego etapu 4 nie oznaczamy jako ukończonego.

Wynik części 4C, 14.10.2026: 617 testów przeszło na Windows z Pythonem 3.11.0 i 3.12.14. Ruff i mypy --strict dla 29 plików pakietu bez uwag. Działa `export` do CSV/Markdown/JSON; dołączono osiem nowych projektów i cztery raporty przykładowe. Zbudowano wheel/sdist `0.1.0`, zainstalowano wheel w świeżym środowisku i sprawdzono wszystkie polecenia spoza repozytorium, osiem projektów, 24 eksporty, kody zakończenia i rozbudowę po zamrożeniu. Szczegóły: `docs/stage-4c-verification.md`. **Cały etap 4 ukończony; lokalne CLI v0.1 gotowe.** Repozytorium ani wydania nie opublikowano, zdalnego CI nie uruchamiano; etap 5 pozostaje nierozpoczęty.

### Etap 5. SQLite i interfejs

- [x] SQLite z transakcjami i wersją schematu; zapis jedynie danych wejściowych.
- [x] Ścieżka bazy w katalogu danych użytkownika, możliwość zmiany; nie wewnątrz instalowanego pakietu.
- [x] Lista/nowy/duplikuj/import, edytor drzewa, tabela, walidacja z linkami i wykorzystanie puli.
- [x] FastAPI/Jinja2/HTMX, lokalny JS i CSS, opóźnienie zmian 300 ms.
- [x] Aktualizacje zapisujące dane atomowo i kontrola wersji projektu, żeby stara odpowiedź HTTP nie nadpisała nowszej edycji.
- [x] Przycisk freeze, kalkulator, podgląd eksportu, API plan/calc/export; niekompletny wynik jest wyraźnie oznaczony i zawiera błędy.
- [x] Testy zapisu po restarcie, izolacji projektów, niepoprawnego wejścia i scenariuszy HTTP.
- [x] Kontrola przeglądarki: edycja bez przeładowania, błąd przy właściwym wierszu, brak zapytań do CDN.

Odbiór: użytkownik wykona cały scenariusz bez ręcznej edycji JSON. Domyślny serwer dostępny tylko na localhost; żadnej domyślnej ekspozycji na Internet. Wynik CLI/API/interfejsu dla tego samego wejścia jest zgodny.

Wynik etapu 5, 14.10.2026: **648 testów** na Windows/Python 3.11.0 i 3.12.14; Ruff i mypy --strict dla 34 plików bez uwag. Sprawdzono w przeglądarce tworzenie, dodawanie i edycję bez przeładowania, szybkie zmiany, błędny VLAN/link do wiersza, ULA, zamrożenie, konflikt dwóch kart, kalkulator oraz podgląd eksportu. Wheel uruchomiony spoza źródeł zachował dane po restarcie i udostępnił dokładnie te same zasoby/eksporty. Szczegóły: `docs/stage-5-verification.md`. Etapu 6 nie rozpoczęto.

### Etap 6. Dokumenty, wygoda i przygotowanie v1.0

- [x] XLSX: Plan, Podsumowanie, Wolne bloki, Walidacja; filtr, zamrożone nagłówki, IP jako tekst.
- [x] DOCX: tytuł, założenia, tabele per budynek, wolne bloki i uwagi.
- [x] Test ponownego wczytania XLSX/DOCX oraz wizualne sprawdzenie tabel i wydruku.
- [x] Widok print, motywy, Tab/Enter, Ctrl+D tylko w edytorze, kopiowanie CIDR; kopia wiersza ma nowe ID i wyczyszczone przypięcia, żeby nie powielała podsieci.
- [x] Bezpieczne eksportowanie opisów do arkuszy jako tekstu; treść użytkownika nie staje się formułą ani HTML.
- [x] README, zrzuty ekranu, instrukcja, opis architektury, zmiany wydania, Dockerfile.
- [x] Zasoby statyczne i szablony dołączone do wheel; test aplikacji po czystej instalacji.
- [x] Przegląd publikowanej zawartości i propozycja licencji MIT do wyboru przez autora.

Odbiór: wszystkie obowiązkowe funkcje PDF działają; testy przechodzą; paczka instaluje się na Windows; arkusze i dokumenty są czytelne; źródła są gotowe do publikacji.

Wynik etapu 6, 14.10.2026: **672 testy** na Windows/Python 3.11.0 i 3.12.14, Ruff/mypy bez uwag; raporty Office otwarte ponownie i wyrenderowane, interfejs sprawdzony w przeglądarce, wheel zainstalowany i sprawdzony poza źródłami. Przygotowano Dockerfile/Compose i job CI, lecz lokalnie nie ma silnika Docker; natywnego zapisu PDF z przeglądarki nie potwierdzono automatycznie. MIT jest propozycją do decyzji autora. Niczego nie opublikowano. Szczegóły: `docs/stage-6-verification.md`.

## 7. Jak odbierać pracę bez bycia programistą

Twoja rola: ustalić reguły sieci, sprawdzić adresy i użyteczność, zdecydować o zakresie. Osoba lub asystent piszący kod: implementacja, uruchomienie sprawdzeń, naprawa błędów i dokumentacja. Warto rozumieć własny kod na tyle, żeby wyjaśnić przepływ danych i najważniejsze reguły, nawet jeśli nie napiszesz sam całego UI.

Po każdym etapie żądaj: listy zmienionych funkcji, polecenia uruchomienia, wyniku testów, znanych ograniczeń oraz jednego przykładu do samodzielnego sprawdzenia. Samo „testy na zielono” nie zastępuje kontroli, czy oczekiwane adresy są poprawne.

Praktyczna kontrola końcowa:

1. Wczytaj T4: A=/23, B=/24, C=/27; obejrzyj pojemność i wolne bloki.
2. Sprawdź /26 first i last z 8 statycznymi oraz 1/3 bramami.
3. Spróbuj dodać za duży segment i nakładające się przypięcie — oczekuj komunikatu przy właściwym obiekcie.
4. Zamroź plan, dodaj segment w wolnym miejscu i porównaj stare adresy.
5. Sprawdź T5, VLAN 110 w /56 i brak wystarczającej puli na drugą lokalizację /48.
6. Eksportuj/importuj JSON i porównaj wynik; otwórz XLSX/DOCX i widok druku.
7. Zrestartuj aplikację i sprawdź dane oraz uruchomienie bez dostępu do Internetu po instalacji zależności.

Automatyczne sprawdzenia, dostępne po wdrożeniu etapu 1:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy --strict src/adresplan/core
```

Testy właściwościowe sprawdzają rozłączność, pojemność, wyrównanie, zawieranie, zachowanie przypięć i deterministyczność. Dokładne T1–T5 chronią wynik referencyjny. Test wydajności T4 ma cel <1 s, z podanym środowiskiem pomiaru; nie traktujemy czasu sieciowego CI jako gwarancji na każdym komputerze.

## 8. Uruchomienie i publikacja

Po pobraniu kodu i zainstalowaniu Pythona użytkownik Windows uruchomi aplikację trzema poleceniami. **Polecenia działają od etapu 5.**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\adresplan.exe serve
```

Otworzy `http://127.0.0.1:8000`. Osobna sekcja README poda instalację narzędzi deweloperskich i przykłady CLI. Instalacja wymaga pobrania zależności; po instalacji aplikacja działa lokalnie bez CDN. W kontenerze serwer słucha na `0.0.0.0`, ale mapowanie portu na komputerze powinno być ograniczone do `127.0.0.1`; bazę zapisujemy na trwałym wolumenie.

Przed publikacją na GitHubie:

- [ ] Zatwierdź nazwę repozytorium `address-plan` i licencję; MIT jest propozycją, nie wybraną licencją.
- [ ] `.gitignore` wyklucza venv, bazy SQLite i ich pliki pomocnicze, lokalne eksporty, cache, sekrety i `tmp/`.
- [ ] Repozytorium zawiera tylko sztuczne dane przykładowe; nie prawdziwy plan infrastruktury zboru/firmy.
- [ ] README pokazuje funkcje dostępne w danym wydaniu i zrzut lub eksport.
- [ ] CI przechodzi na czystym środowisku; wheel i interfejs działają po instalacji.
- [ ] Milestones v0.1/v1.0 odpowiadają etapom; Issues opisują konkretne zadania z sekcji 6.
- [ ] Release ma opis zmian, wheel i syntetyczne przykłady; publikacja na PyPI jest opcjonalna później.

Ten plan nie tworzy repozytorium zdalnego ani niczego nie publikuje. Utworzenie repozytorium i wysłanie kodu będą osobnym, konkretnym krokiem po jego przygotowaniu.

## 9. Wiedza do opanowania i realistyczny harmonogram

| Wiedza | Potrzebny poziom | Kiedy |
| --- | --- | --- |
| CIDR, VLSM, sumaryzacja, VLAN | Samodzielnie sprawdzasz przykłady i uzasadniasz podział | Od początku |
| IPv6, /48-/64, SLAAC, P2P, ULA | Rozumiesz pojemność i różnicę względem IPv4 | Przed etapem 3 |
| Python | Czytasz funkcje, typy, dataclasses, wyjątki i testy | Stopniowo w etapach 1–4 |
| Git/GitHub | Commit, diff, branch, issue, release, wynik CI | Przy każdym etapie |
| JSON | Potrafisz odczytać i poprawić przykład projektu | Etap 4 |
| HTTP/HTML | Rozumiesz formularz, request/response, localhost | Etap 5 |
| SQLite i Docker | Podstawy pliku bazy, kopii i kontenera | Etapy 5–6; Docker opcjonalnie |

Szacunek z PDF: rdzeń+CLI 1–2 dni, interfejs i eksporty 3–5 dni. Traktujemy go jako wariant intensywnej pracy doświadczonego wykonawcy, nie termin gwarantowany.

**Plan orientacyjny przy pomocy asystenta i Twojej weryfikacji: 15–25 sesji po 1–2 godziny**, z dodatkowym zapasem na problemy z przypięciami i interfejsem. Etap 1: 2–3 sesje; etap 2: 3–5; etap 3: 3–4; etap 4: 2–3; etap 5: 3–6; etap 6: 2–4. Przy trzech sesjach tygodniowo to około 5–9 tygodni. To mój szacunek, nie wynik benchmarku. Po etapie 2 trzeba go zaktualizować na podstawie faktycznego postępu.

Jeżeli czas się skończy, domykamy v0.1: obliczenia, CLI, przykłady, testy i dokumentacja. To pełny użyteczny produkt pośredni.

## 10. Gotowe polecenie rozpoczęcia implementacji

> Przeczytaj PLAN.md, SPEC.md i źródłowy PDF. Zrealizuj wyłącznie etap 1 z PLAN.md, uwzględniając decyzje D1–D7 w zakresie tego etapu. Przygotuj pakiet, typowane modele, sizing i generyczny alokator, testy T1–T3 oraz CI. Kod, identyfikatory i komentarze pisz po angielsku, komunikaty użytkownika po polsku. Core ma pozostać czysty i korzystać z ipaddress. Uruchom pytest, Ruff i mypy --strict dla core. Napraw błędy przed zakończeniem. Podaj wynik sprawdzeń oraz jeden przykład do ręcznego odbioru. Nie rozpoczynaj etapu 2 i nie publikuj niczego na GitHubie.

Kolejne polecenia mają ten sam schemat: wskazanie jednego etapu, jego kryteriów odbioru i wymaganych testów. Dokumenty źródłowe oraz doprecyzowania z tego planu pozostają wspólną podstawą pracy. Po każdym ukończonym etapie wykonawca aktualizuje `CHANGELOG.md` zgodnie z jego zasadami, również gdy polecenie rozpoczęcia etapu nie powtarza tego obowiązku.
