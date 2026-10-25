# Odbiór etapu 5 — SQLite i interfejs

Data: 14.10.2026. Wersja `0.2.0.dev1`. Ukończono wyłącznie etap 5; etap 6 nie został rozpoczęty.

## Zakres

SQLite przechowuje dane wejściowe, wersję projektu i czas zapisu. Każdy wynik powstaje przez wspólny planer używany w CLI. Klucz zapisu jest oddzielony od identyfikatorów importowanych danych. Zapis jest transakcją z kontrolą oczekiwanej wersji; obcy/nowszy schemat nie zostaje nadpisany.

Interfejs ma projekty (nowy/import/duplikuj), drzewo i tabelę, parametry globalne i indywidualne, plan na żywo, walidację z linkami, metryki i wolne bloki, freeze/czyszczenie przypięć, generator ULA, kalkulator oraz podgląd i pobieranie JSON/CSV/Markdown. FastAPI/Jinja2/HTMX korzystają z lokalnych zasobów. Polecenie `serve` wiąże `127.0.0.1`.

## Testy automatyczne

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.11.0 | 648 testów, 47,04 s |
| Windows / Python 3.12.14 | 648 testów, 46,70 s |
| Ruff / formatowanie | Bez uwag |
| mypy --strict | Bez uwag, 34 pliki pakietu |
| pip check | Bez konfliktów w obu środowiskach deweloperskich i czystej instalacji |

Do poprzednich 617 testów doszło 31 pozycji. Sprawdzono:

- Odtworzenie projektu po ponownym otwarciu SQLite, brak wyniku w rekordzie bazy, izolację dwóch importów i kopii.
- Jednoczesne zapisy z dwóch wątków: jeden zapis i jeden konflikt; wersja rośnie dokładnie raz.
- Zachowanie pliku obcej bazy oraz odmowę niepoprawnych danych i zmiany ID projektu.
- Utworzenie, dodanie segmentu, edycję, IPv6, freeze, ponowne utworzenie aplikacji, duplikowanie i usunięcie poddrzewa.
- Zachowanie wszystkich pól formularza podczas zwykłego zapisu, ścieżkę/link błędnego pola, brak modyfikacji bazy przy 422.
- Zapis częściowego planu, odmowę freeze, konflikt formularza i API, warunek `If-Match`.
- Generator ULA, czyszczenie przypięć, odmowę niepoprawnej hierarchii i brak błędu serwera dla niepoprawnego tokenu Unicode.
- Import ośmiu projektów T1–T5/AV i dokładną zgodność dokumentu API z JSON oraz wszystkich trzech eksportów z CLI, również przy częściowych wynikach.
- Kalkulator IPv4/IPv6, błędne dane i podział; IPv6 /0 na /128 nadal ograniczony do limitu podglądu.
- Kontrolę Host/Origin/tokenów, escapowanie HTML, lokalne zasoby i brak dokumentacji korzystającej z CDN.
- Komendę `serve`, związanie tylko localhost i zakres portu.

Polecenia: `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy --strict src/adresplan`, `python -m pip check`. Lokalne testy HTTP wymagały uruchomienia poza piaskownicą narzędzia: Windows blokował pomocnicze gniazdo pętli asyncio. Nie pominięto testów ani ostrzeżeń.

## Rzeczywista przeglądarka

W przeglądarce wbudowanej w Codex, pod `127.0.0.1:8765`, wykonano:

1. Nowy projekt i dodanie segmentu Dźwięk bez ręcznej edycji JSON.
2. Hosty 40, VLAN 10: plan `/26`. Seria szybkich zmian 70 → 80 → 90: ostatnia wartość 90 pozostaje w formularzu i planie `/25`, z poprawną wersją zapisu.
3. Zbyt duże zapotrzebowanie: jawny wynik częściowy i link do lokalizacji, której blok nie mieści się w puli.
4. VLAN 5000: brak zapisu, wartości pozostają w edytorze, link przewija i wyróżnia dokładny wiersz segmentu. Przywrócenie VLAN 10 zapisuje ponownie.
5. Wygenerowanie ULA, aktualizacja IPv6 i zamrożenie obu rodzin wraz z infrastrukturą.
6. Dwie karty tego samego projektu: po zapisie w pierwszej próba ze starej wersji drugiej daje konflikt i nie nadpisuje danych.
7. Podgląd Markdown oraz kalkulator `192.168.1.10/24`, podział na cztery `/26`: `.0`, `.64`, `.128`, `.192`.
8. Restart serwera z instalacji wheel i ponowne otwarcie projektu: zachowane dane i zamrożone adresy.

Obejrzano zrzuty edytora, błędu z wyróżnionym wierszem i podglądu eksportu. Szablon odwołuje się do trzech lokalnych zasobów `/static/app.css`, `/static/htmx.min.js`, `/static/app.js`; zasoby pobrano poprawnie. CSP dopuszcza skrypty i połączenia tylko z własnego źródła. Nie dodano zależności od CDN/fontów/usług zewnętrznych.

## Paczka i czysta instalacja

Zbudowano wheel i sdist `0.2.0.dev1`. Wszystkie źródła web, szablony, statyczne pliki oraz licencja HTMX są w wheel i odpowiadają bajtowo plikom roboczym. Sdist zawiera licencję HTMX. Zależności mają aktualny plik lock.

Wheel zainstalowano zwyczajnie w osobnym środowisku `.venv-release-02`, wyłącznie z zależnościami uruchomieniowymi. Brak pytest i httpx2 potwierdzono. Z katalogu poza projektem, w trybie izolowanym Pythona, uruchomiono prawdziwy serwer przez `serve`. Zaimportowany moduł pochodził z `site-packages`.

Sprawdzono przez HTTP strony, zachowanie danych po restarcie, identyczność zasobów z paczki, trzy eksporty i ich statusy, API kalkulatora z tokenem, a przez CLI wersję, plan T5 i kalkulator. Pierwszy skrypt kontrolny wymagał korekty porównania nagłówka HTTP (nazwy nagłówków są niewrażliwe na wielkość liter); po poprawce wszystkie eksporty przeszły odbiór. Tymczasowe serwery podglądu zatrzymano po kontroli.

## Ręczny odbiór

Uruchom `adresplan serve`, otwórz `http://127.0.0.1:8000` i importuj `examples/budynek.json`. W wyniku T4 sprawdź: A=`10.20.0.0/23`, B=`10.20.2.0/24`, C=`10.20.3.0/27`. Edytuj hosty segmentu, zaczekaj na „Zapisano”, obejrzyj wynik i pobierz JSON. Zatrzymaj i uruchom aplikację ponownie — projekt nadal będzie na liście.

## Granice

Brak XLSX/DOCX, specjalnego wydruku, motywów i dodatkowych skrótów etapu 6. Kontrola przeglądarki objęła układ desktopowy; nie jest audytem wszystkich przeglądarek i urządzeń. Domyślna ścieżka danych jest testowana bez zapisywania rzeczywistych danych użytkownika do AppData; kontrolne bazy znajdują się w ignorowanym `.tmp`. Aplikacja nie ma kont ani uwierzytelniania do udostępniania w sieci. Niczego nie opublikowano na GitHubie/PyPI; zdalnego CI nie uruchamiano.
