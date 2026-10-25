# v0.1 — lokalne wydanie CLI

Wersja pakietu: `0.1.0`. Etapy 1–4 obejmują gotowy rdzeń IPv4/IPv6 i obsługę terminalową: `plan`, `calc`, `freeze`, `export`. Interfejs w przeglądarce nie jest częścią tego wydania.

## Scenariusz użytkownika

Po pobraniu źródeł i instalacji Pythona 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\adresplan.exe plan examples/church-av.json
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\adresplan.exe freeze examples/church-av.json --output output/zamrozony.json
.\.venv\Scripts\adresplan.exe export output/zamrozony.json --format md --output output/plan.md
.\.venv\Scripts\adresplan.exe export output/zamrozony.json --format csv --output output/plan.csv
```

To lokalna aplikacja. Instalacja zależności wymaga Internetu; polecenia nie konfigurują ani nie skanują urządzeń sieciowych. Dane projektu edytujesz w JSON. Po zamrożeniu dopisane segmenty korzystają z wolnych miejsc, bez przesuwania wcześniejszych adresów. Brak miejsca daje błąd i wymaga świadomej zmiany projektu.

## Paczki

- `dist/adresplan-0.1.0-py3-none-any.whl` — paczka do instalacji.
- `dist/adresplan-0.1.0.tar.gz` — archiwum źródeł z przykładami, testami i dokumentacją.

Wheel zawiera moduły programu, znacznik typów i schemat JSON. Przykłady i instrukcje są w repozytorium/sdist, nie wewnątrz zainstalowanego modułu. Instalując sam wheel, wskazujesz własny plik projektu lub osobno pobrany przykład. Folder `dist` jest lokalnym wynikiem budowania i nie trafia do zwykłych commitów.

## Granice wydania

- Sprawdzane lokalnie na Windows / Python 3.11 i 3.12. Konfiguracja CI dla Linux/Windows jest przygotowana; wynik zdalnego CI będzie dostępny dopiero po publikacji.
- Dane: JSON, CSV, Markdown. Bez SQLite, interfejsu webowego, XLSX i DOCX.
- Projekty z błędami można zapisać i dokumentować, ale nie zamrażać.
- Publikacja na GitHubie/PyPI nie została wykonana. Nazwa repozytorium i licencja pozostają do zatwierdzenia przez autora przed publikacją.

Wyniki odbioru i instalacji: [stage-4c-verification.md](stage-4c-verification.md). Zmiany: [CHANGELOG.md](../../CHANGELOG.md).
