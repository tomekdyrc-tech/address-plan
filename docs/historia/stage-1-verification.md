# Etap 1 — odbiór i weryfikacja

Data: 2026-10-14. Wersja deweloperska: `0.1.0.dev1`.

## Zakres

Ukończono wyłącznie etap 1 z `PLAN.md`: pakiet, typowane modele, walidację struktury, sizing IPv4 i alokator generyczny. Plik `cli.py` zapewnia pomoc i numer wersji; demonstracja to osobny przykład, a nie pełne polecenie planowania z etapu 4.

Rdzeń korzysta wyłącznie ze standardowej biblioteki i własnych modułów. Przyjmuje gotowe obiekty `IPv4Network`/`IPv6Network`, nie odczytuje plików, nie otwiera połączeń, nie losuje i nie zapisuje bazy. Parsowanie surowego wejścia CLI/web z walidacją granic aplikacji powstanie później. Domyślne konstruktory `ipaddress` odrzucają CIDR z ustawionymi bitami hosta.

## Wyniki lokalne

| Sprawdzenie | Wynik |
| --- | --- |
| Windows / Python 3.11.0 / pytest | 122 zaliczone |
| Windows / Python 3.12.14 / pytest | 122 zaliczone |
| mypy --strict dla core, oba interpretery | Bez uwag, 5 plików |
| Ruff — lint i formatowanie | Bez uwag |
| pip check, główne środowisko | Brak konfliktów zależności |
| Budowa sdist i wheel | Powodzenie |
| Instalacja wheel w osobnym venv, poza katalogiem źródeł | Import rdzenia, przydział i entry point działają |

Hypothesis ma limit 200 przykładów na test właściwościowy, stały profil i wyłączoną bazę lokalnych przykładów. Liczba 122 oznacza pozycje testowe pytest, a nie 122 losowania Hypothesis.

Zdalnego CI nie uruchamiano. Przygotowano workflow dla Ubuntu/Python 3.11 i 3.12 oraz Windows/Python 3.12. Nie stwierdzamy na tej podstawie lokalnego wykonania testów na Linuksie.

## Kontrola sieciowa

- **T1:** 100, 50, 25, 10 hostów w `192.168.10.0/24` daje kolejno `.0/25`, `.128/26`, `.192/27`, `.224/28`; wolne `.240/28`.
- **T2:** wszystkie 10 przydziałów zgodne z dokumentem, w tym P2P /31 i loopback /32; 485 adresów przydzielonych i 539 wolnych w /22.
- **T3:** X i Y otrzymują /27; Z nie mieści się w /26, zwraca błąd z zapotrzebowaniem 80 adresów i sugestią /25.
- **Właściwości:** rozłączność alokacji i wolnych bloków, zawieranie w puli, wyrównanie, zachowanie całkowitego rozmiaru puli, deterministyczność i zachowanie istniejących przypięć po dodaniu nowych żądań.
- **Przypadki błędne:** za małe lub nakładające się przypięcia, przypięcia poza pulą lub w złej rodzinie, zły prefiks, duplikaty ID, niespójne rezerwacje i brak miejsca.
- **Fragmentacja:** gdy dwa przypięte /32 uniemożliwiają przydział /25 w /24, sugestia uwzględnia rzeczywistą symulację, a nie tylko sumę wolnych adresów.

Diagnostyka wolnej przestrzeni w komunikacie braku miejsca opisuje stan w chwili nieudanego przydziału. Algorytm dalej próbuje przydzielać mniejsze żądania. Niepoprawny pin nie jest automatycznie przesuwany. Wynik z błędami ma `is_complete=False`.

## Jak odtworzyć główne sprawdzenia

Po instalacji opisanej w README, w PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy --strict src/adresplan/core
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m build --no-isolation
.\.venv\Scripts\python.exe examples/stage1_vlsm.py
```

W lokalnym środowisku Codex narzędzia instalowano do katalogów projektu. Budowa archiwum wymagała wykonania poza ograniczeniem sandboxa blokującym dostęp do tymczasowo rozpakowanych plików. Nie zmieniano reguł projektu ani algorytmu w celu obejścia testów.

## Granica etapu

Model `Plan` i pola IPv6 przygotowano do dalszej pracy, ale funkcja budowania hierarchicznego planu, rezerwacje zakresów, zamrażanie projektu, baza, eksport i interfejs nie zostały zaimplementowane. Test odtwarzania przypięć dotyczy alokatora, nie przyszłego przycisku zamrażania.
