# Odbiór części 4A — JSON i walidacja

Data: 14.10.2026. Wersja deweloperska: `0.1.0.dev4`. **Część 4A ukończona; cały etap 4 pozostaje w trakcie.**

## Zakres

- Wersjonowany dokument `schema_version=1`, dane projektu i świeżo obliczony plan.
- Ścisłe modele wejścia Pydantic 2 poza rdzeniem; komplet pól projektu, ustawień, węzłów i przypiętej infrastruktury.
- Walidacja typu, zakresu, rodziny adresów i struktury drzewa; polskie błędy ze ścieżkami i stabilnymi kodami.
- Import przelicza plan i nie ufa wynikowi zapisanemu w `plan`.
- Eksport/import zachowuje trwałe ID, kolejność, opisy, ustawienia, przypięcia IPv4/IPv6 i infrastrukturę.
- Zapis UTF-8 przez plik tymczasowy i atomową podmianę; kontrola błędów odczytu/zapisu.
- Schemat JSON dołączony jako zasób pakietu, przykład sieci AV i demonstracja zapisu/odczytu.

Nie wdrożono poleceń `plan`, `calc`, `export`, `freeze`, kalkulatora, eksportów CSV/Markdown ani interfejsu webowego. Wymienione funkcje pozostają odpowiednio w 4B, 4C i etapie 5.

## Wyniki lokalne

Środowisko: Windows, Python 3.11.0 oraz 3.12.14. Pydantic 2.14.1, pydantic-core 2.50.1, zależności utrwalone w `requirements-dev.lock`.

- Python 3.12: **427 testów zaliczonych** w około 14,5 s.
- Python 3.11: **427 testów zaliczonych** w około 15,3 s.
- 112 nowych pozycji testowych względem 315 po etapie 3, w tym test demonstracji oraz 60 powtarzalnych przykładów Hypothesis w jednej pozycji testowej.
- Ruff: lint i formatowanie bez uwag.
- mypy `--strict`: cały pakiet, 22 pliki źródłowe, bez uwag.
- `pip check`: brak konfliktów zależności.
- Zbudowano wheel i sdist `0.1.0.dev4`; zainstalowano wheel wraz z zależnościami w nowym `.venv-smoke4a`.
- Uruchomienie z katalogu nadrzędnego, przez Python `-I`, potwierdziło import z zainstalowanej paczki, dostępność i zgodność schematu, zapis/odczyt przykładu AV, zachowanie zamrożenia i poprawny T5. Liczniki IPv6 większe niż `2**53` pozostały dokładnymi liczbami całkowitymi; sfałszowana migawka wyniku została zignorowana.
- Entry point zainstalowanej paczki zwraca `adresplan 0.1.0.dev4`. Pełnego CLI jeszcze nie ma.

Czasy są lokalnym pomiarem, nie gwarancją na innym komputerze. Zdalny CI nie był uruchamiany; repozytorium nie jest jeszcze opublikowane.

## Najważniejsze przypadki

| Sprawdzenie | Wynik |
| --- | --- |
| T4 i T5: eksport → import → przeliczenie | Identyczny projekt i plan |
| Wszystkie ustawienia i pola podtypu `Segment` | Zachowane, także wartości różne od domyślnych |
| Zamrożony projekt T5 i dodanie nowego LAN-u po imporcie | Dotychczasowe IPv4/IPv6 i infrastruktura zachowane |
| ULA/GUA/doc, numeracja VLAN hex i brak IPv6 | Zachowane |
| Sfałszowany wynik w `plan` | Ignorowany; wynik liczony ze źródłowego projektu |
| Zmiana danych projektu bez zmiany zapisanej migawki | Powstaje nowy, poprawnie przeliczony wynik |
| Poprawna struktura, ale zbyt mała pula/niespójne ustawienia | Projekt dostępny z diagnostyką niekompletnego planu |
| Tekst/float/bool zamiast liczby całkowitej | Odrzucony ze ścieżką pola |
| Duplikaty ID, cykl, brak rodzica, zły typ rodzica | Odrzucone |
| Błędny CIDR, rodzina adresów, bity hosta i scoped IPv6 | Odrzucone |
| Nieznana wersja, literówki, powtórzone klucze, NaN/Infinity | Odrzucone |
| UTF-8 z BOM, polskie opisy, znaki specjalne | Poprawny odczyt; eksport UTF-8 bez BOM |
| Wejście/eksport powyżej 16 MiB | Czytelny błąd |
| Nieudana podmiana istniejącego pliku | Poprzednia zawartość zachowana, plik tymczasowy usunięty |
| Błąd walidacji przed zapisem | Poprzedni plik nietknięty |
| Schemat zapisany w pakiecie | Zgodny z bieżącymi modelami wejścia |

Pierwszy test ujawnił, że zwykła serializacja pola typu `Node` może pominąć pola podtypu `Segment`. Eksport używa serializacji zachowującej podtypy; testy porównują kompletny zestaw pól segmentu i ustawień. To zabezpiecza m.in. hosty, VLAN, rolę, rezerwy i ustawienia IPv6 przed zastąpieniem wartościami domyślnymi przy odczycie.

Testy plikowe w lokalnej piaskownicy używały `--basetemp` wewnątrz `.tmp/`, ponieważ systemowy katalog tymczasowy ma ograniczone uprawnienia. Nie zmienia to zachowania aplikacji.

## Ręczna kontrola

```powershell
.\.venv\Scripts\python.exe -X utf8 examples/stage4a_json.py
```

Oczekiwane segmenty:

| Segment | IPv4 | IPv6 |
| --- | --- | --- |
| Dźwięk | 10.42.0.0/27 | 2001:db8:42:100::/64 |
| Obraz | 10.42.0.32/27 | 2001:db8:42:101::/64 |
| Zarządzanie | 10.42.0.64/28 | 2001:db8:42:102::/64 |

Skrypt potwierdza identyczność projektu i planu oraz zachowanie zamrożenia. Wyniki zapisuje w `.tmp/stage4a/project.json` i `.tmp/stage4a/project-frozen.json`. Dane przykładowe są sztuczne.

Opis formatu i jego granic: [json-format.md](../json-format.md).
