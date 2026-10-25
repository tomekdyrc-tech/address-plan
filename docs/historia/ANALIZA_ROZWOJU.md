# Analiza aplikacji i propozycje rozwoju

Data: 16.10.2026. Podstawa: bieżący kod źródłowy po poprawkach interfejsu i wyboru IPv6, modele danych, szablony, historia, zapis i eksporty. To propozycja dalszych prac, nie zatwierdzony zakres wdrożenia.

## Stan po wdrożeniu poprawek 1–3

Wdrożono: podział IPv6 dla wielu lokalizacji i jawne dopasowanie, zawieszanie IPv6 z zachowaniem konfiguracji oraz czytelne komunikaty. Opisy ograniczeń poniżej dokumentują stan stwierdzony podczas analizy; szczegóły wykonania są w changelogu. Następnie wdrożono uzgodnione siedem usprawnień: filtry, bibliotekę szablonów, backup, podgląd skutków, projekt z kalkulatora, wyjaśnienia i raporty. Instrukcja: `USPRAWNIENIA.md`. Pozostałe pomysły, takie jak import tabel CSV, stany wdrożenia i mapa pul, nadal są propozycjami.

## Ocena

Aplikacja ma działający rdzeń planowania, historię i kilka formatów dokumentacji. Kolejne prace powinny przede wszystkim skrócić drogę od opisu sieci do czytelnego, stabilnego planu. Dodawanie kolejnych narzędzi bez uporządkowania tej drogi zwiększyłoby złożoność obsługi.

## Potwierdzone ograniczenia i niespójności

### 1. Domyślne IPv6 nie mieści dwóch lokalizacji

Włączenie IPv6 generuje ULA /48. Domyślne ustawienie lokalizacji to również /48, budynku /56, infrastruktury /56 (`core/models.py`). W jednej puli /48 mieści się jedna lokalizacja /48.

Sprawdzono bez zapisywania bazy: projekt IPv4 /16 + ULA /48 i dwa oddziały utworzone z zestawu podstawowego. Wynik: 10 przydziałów IPv4, 5 przydziałów IPv6, błąd `v6_insufficient_space`. Druga lokalizacja nie otrzymuje pełnej adresacji IPv6. Jest to zgodne z regułami alokatora, ale domyślne ustawienia nie pasują do nowego przepływu kopiowania oddziałów.

Propozycja: przed planowaniem IPv6 zapytać o docelową liczbę lokalizacji i budynków, pokazać proponowaną hierarchię oraz jej pojemność. Dla nowych planów można np. zaproponować /52 na lokalizację wewnątrz /48, zachowując /56 na budynki i infrastrukturę. Konkretny podział musi uwzględnić zapas i liczbę budynków. Przy wdrożonym, zamrożonym planie wymagana jest jawna decyzja przed zmianą hierarchii.

### 2. Wyłączenie IPv6 usuwa bieżącą konfigurację

`web/forms.py` usuwa prefiks, przypięcia i blokady IPv6. Historia pozwala wrócić do wcześniejszego projektu, ale przywraca również ówczesne dane IPv4.

Propozycja: osobny zapisany stan „IPv6 aktywne”. Wyłączenie zatrzymuje alokację i ukrywa pola, zachowując konfigurację. Osobne działanie „Usuń konfigurację IPv6” służy do jej wyczyszczenia. Ponowne włączenie waliduje zachowane dane względem aktualnej struktury. To wymaga aktualizacji modelu i kontrolowanej migracji danych.

### 3. Komunikaty interfejsu pochodzą z formatu konsolowego

`web/app.py` używa `format_finding`, które dołącza poziom, kod diagnostyczny, ID i szczegóły. Długie identyfikatory i komunikaty informacyjne utrudniają znalezienie rzeczywistego problemu.

Propozycja: widoczny komunikat „Oddział Gdańsk → Pracownicy: za mała pula na 80 urządzeń”, obok działanie „Przejdź do pola”. Kody, ID i szczegóły w rozwijanym panelu. Domyślnie pokazywać błędy i ostrzeżenia, a informacje o poprawnych przydziałach zwinąć.

### 4. Źródła i paczki mają tę samą wersję mimo różnic

Źródła nadal deklarują 1.1.0, natomiast wcześniejsze artefakty w `dist` nie zawierają ostatnich zmian. Główna instrukcja i dokument odbioru odnoszą się jeszcze do wcześniejszych 700 testów.

Propozycja: przed publikacją nadać aktualizacji jednoznaczną wersję, zsynchronizować instrukcje i zrzuty oraz ponownie zbudować i sprawdzić paczki. Napis w navbarze powinien wskazywać rzeczywiście zainstalowane wydanie.

## Zalecane ulepszenia

| Priorytet | Zmiana | Oczekiwany efekt |
| --- | --- | --- |
| Wysoki | Widok tylko wybranej lokalizacji lub budynku; wyszukiwanie po nazwie, VLAN i CIDR | Kilkanaście oddziałów nie wymaga przewijania całej tabeli. Filtrowanie nie może usuwać ani zmieniać niewidocznych elementów przy zapisie. |
| Wysoki | Biblioteka szablonów z edycją nazwy, podglądem, aktualizacją wzorca i usuwaniem z możliwością odzyskania | Szablony stają się narzędziem wielokrotnej pracy, a nie rosnącą listą kopii. Zmiana wzorca nie zmienia istniejących projektów. |
| Wysoki | Kopia całej biblioteki z interfejsu | Jeden plik obejmuje projekty, historię i szablony. Obecny JSON pojedynczego projektu nie jest taką kopią. Kopia działającej bazy powinna używać mechanizmu backupu SQLite. |
| Wysoki | Podgląd zmiany przydziałów przed zatwierdzeniem większej przebudowy | Administrator widzi, które sieci zmienią CIDR i czy trzeba przeadresować urządzenia. Historia już daje podstawę do porównania, ale dopiero po zapisie. |
| Średni | „Utwórz projekt z wyniku” w kalkulatorze VLSM | Jedna lista urządzeń przechodzi do dalszej dokumentacji bez ponownego wpisywania. Trzeba jawnie ustalić zapas i bramy, ponieważ kalkulator i edytor mają inne założenia. |
| Średni | Podgląd wyliczenia dla segmentu | Np. „20 urządzeń + 25% zapasu + 1 brama = 26 adresów; wybrano /27, pojemność 30”. Użytkownik rozumie, skąd bierze się wynik. |
| Średni | Metryka projektu i profile eksportu | Autor, organizacja, opis, data, status; raport skrócony dla odbiorcy i szczegółowy dla administratora. Kod diagnostyczny nie musi trafiać na pierwszą stronę dokumentacji. |
| Średni | Import tabeli segmentów CSV z mapowaniem kolumn i podglądem | Dane przygotowane w arkuszu nie wymagają ręcznego przepisywania. Błędne wiersze są wskazywane przed zapisem. |
| Średni | Stany „Roboczy” i „Wdrożony” | Jasne rozróżnienie planowania i utrzymania. Wdrożenie wiąże się z kompletnym planem, zamrożeniem adresów i zapamiętaną wersją dokumentacji. |
| Późniejszy | Widok zajętości puli jako bloków | Łatwiej zauważyć, gdzie jest zapas i dlaczego duża nowa podsieć nie mieści się mimo wolnych adresów. Wizualizacja musi rozróżniać poziomy hierarchii i nie sumować rodziców z dziećmi. |

## Proponowana kolejność

1. Poprawić domyślną hierarchię IPv6 dla wielu oddziałów, zachowanie konfiguracji po wyłączeniu oraz komunikaty.
2. Wprowadzić widok wybranego obiektu i zarządzanie szablonami.
3. Dodać kopię całej biblioteki oraz podgląd zmian adresacji przed zastosowaniem.
4. Połączyć kalkulator z projektem i ulepszyć końcową dokumentację.
5. Uporządkować wersję, instrukcje i paczki przed publikacją na GitHubie.

To może być podział kolejnego wydania na etapy; nie jest deklaracją realizacji wszystkich funkcji naraz.

## Technologie i zakres

Obecne Python/FastAPI, Jinja2/HTMX i SQLite wystarczą do proponowanych usprawnień. Najważniejsza praca dotyczy modelu danych, migracji, formularzy i sprawdzenia scenariuszy administratora. Zmiana frameworka nie rozwiąże tych problemów.

Generowanie konfiguracji routerów, aktywne skanowanie i pełna ewidencja pojedynczych adresów rozszerzyłyby aplikację o osobne obszary odpowiedzialności. Na obecnym etapie większy zwrot da dopracowanie planera i dokumentacji.

## Zakres tej analizy

Przejrzano kod i dokumentację oraz wykonano kontrolowany przykład dwóch lokalizacji IPv6 w pamięci. Nie zmieniono działania aplikacji ani danych użytkownika. Nie był to pełny audyt bezpieczeństwa ani ponowny przebieg wszystkich testów. Propozycje funkcji wymagają wdrożenia i osobnej weryfikacji.
