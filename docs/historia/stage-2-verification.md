# Etap 2 — odbiór i weryfikacja

Data: 2026-10-14. Wersja deweloperska: `0.1.0.dev2`.

## Zakres

Ukończono hierarchiczny planer IPv4, rezerwacje bram/statycznych/DHCP, walidację sieciową, metryki oraz czystą funkcję zamrażania. Publiczne funkcje to `adresplan.core.plan.build_plan(project)` i `adresplan.core.freeze.freeze(project, plan)`. Cały rdzeń pozostaje niezależny od plików, bazy, HTTP i losowości.

Etapu 3 nie rozpoczęto. IPv6 jest nadal obsługiwany wyłącznie przez generyczny alokator z etapu 1; dotychczasowe pola wejściowe IPv6 są zachowywane przy zamrażaniu IPv4. Nie ma jeszcze interfejsu w przeglądarce ani importu projektu/pełnych poleceń CLI.

## Weryfikacja lokalna

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.11.0 / pytest | 203 zaliczone |
| Windows / Python 3.12.14 / pytest | 203 zaliczone |
| mypy --strict dla core | Bez uwag, 10 plików |
| Ruff — lint i formatowanie | Bez uwag |
| pip check | Brak konfliktów zależności |
| Przykłady etapów 1 i 2 | Przechodzą jako testy uruchomienia osobnego procesu |
| Archiwum źródeł i wheel | Zbudowane; instalacja wheel sprawdzona w oddzielnym środowisku |

Zdalnego CI nie uruchamiano. Konfiguracja z etapu 1 obejmuje również nowe testy i moduły.

Pomiar T4 na tym komputerze, Windows/Python 3.12.14, 100 przeliczeń: mediana około 1,4 ms, maksimum około 3,5 ms. To pomiar lokalny; nie gwarancja czasu na każdym urządzeniu. Cel poniżej jednej sekundy został spełniony z dużym zapasem.

## Wynik referencyjny T4

| Obiekt | Blok | Przydzielone adresy dzieci | Wolne wewnątrz |
| --- | --- | ---: | ---: |
| Lokalizacja | 10.20.0.0/20 | 800 | 3296 |
| Budynek A | 10.20.0.0/23 | 485 | 27 |
| Budynek B | 10.20.2.0/24 | 224 | 32 |
| Budynek C | 10.20.3.0/27 | 32 | 0 |

Segmenty razem zajmują 741 adresów, a wszystkie wolne bloki 3355. Bloki budynków zajmują 800; różnica 59 to wolne miejsce wewnątrz A i B. Rodzic i dziecko nie są sumowani jako rozłączne alokacje. Zgodność wszystkich adresów segmentów sprawdza test T4.

Lokalizacja z T4 jest jawnie przypięta do /20. Bez tego przypięcia minimalny wyliczony blok lokalizacji wynosi /22.

## Przypięcia i hierarchia

- Rozmiary wynikają z zapotrzebowania dzieci; adresy są przydzielane od puli w dół tym samym alokatorem co w etapie 1.
- Przypięty segment wymusza położenie nieprzypiętych przodków. Najmniejszy wspólny blok przypięć ogranicza minimalny rozmiar rodzica.
- Jeśli sama suma rozmiarów nie wystarcza z powodu fragmentacji, wykonywana jest symulacja i blok rośnie do granicy puli projektu.
- Przeplatające się przypięcia różnych budynków mogą uniemożliwić utworzenie rozłącznych bloków sumarycznych. Plan wtedy zawiera błąd; adresy nie są po cichu przenoszone.
- Jawnie przypięty rodzic nie jest automatycznie powiększany. Puste nieprzypięte węzły nie zajmują fikcyjnych podsieci, a pusty przypięty węzeł rezerwuje swój blok.
- Błędy danych segmentu nie przerywają obliczania poprawnych, niezależnych przydziałów. Niekompletny wynik ma `is_complete=False`.

## Rezerwacje i walidacja

Przykład /26, jedna brama na początku, 8 statycznych: `.1`, `.2–.9`, DHCP `.10–.62` (53 adresy). Brama na końcu: `.62`, statyczne `.1–.8`, DHCP `.9–.61`. Trzy bramy na końcu: wirtualna `.62`, pozostałe `.61/.60`, DHCP kończy się na `.59`. Zakres pusty jest brakiem wartości, a nie zakresem od większego adresu do mniejszego. /31, /32 i legacy P2P /30 nie mają DHCP ani bramy.

Walidacja sprawdza m.in. przecięcia z zabronionymi pulami, jawną listę RFC 1918, CGNAT, zakres i duplikaty VLAN-ów w lokalizacji, pojemność segmentów oraz kolizje rodzeństwa i segmentów. Zawieranie dziecka w rodzicu jest prawidłowe. Ostrzeżenie o wykorzystaniu >85% dotyczy LAN/mgmt, po uwzględnieniu zapasu i rezerwacji; nie ostrzega o naturalnym 100% na P2P/loopbackach.

Wolne bloki i metryki mają `parent_id`; wartość `None` oznacza główną pulę projektu. Ciągłość jest dokładnym ułamkiem: największy wolny blok / wszystkie wolne adresy. Brak wolnego miejsca daje brak wartości. Komunikaty i dane są niezależne od języka UI; ich kody są po angielsku.

## Zamrażanie

`freeze` porównuje plan z bieżącym przeliczeniem projektu, odrzuca plan obcy, nieaktualny, zmodyfikowany lub niekompletny, a następnie zwraca nowy projekt z przypięciami. Nie zmienia oryginalnych danych, identyfikatorów, ustawień, opisów ani pól IPv6. Powtórne zamrożenie jest idempotentne. Ostrzeżenia nie blokują zamrożenia.

Testy obejmują dodanie segmentu do wolnego miejsca, brak miejsca w zamrożonym budynku i zachowanie wszystkich wcześniejszych adresów. Sprawdzane są też losowe drzewa oraz losowo rozmieszczone przypięte loopbacki. Hypothesis korzysta z profilu do 200 przykładów na test właściwościowy.

## Odtworzenie

```powershell
.\.venv\Scripts\python.exe examples/stage2_hierarchy.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy --strict src/adresplan/core
```

Przykład T4 po zamrożeniu dodaje segment `10.20.1.232/30` i wypisuje „Dotychczasowe adresy: bez zmian”.
