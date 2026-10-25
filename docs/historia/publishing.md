# Przygotowanie publikacji na GitHubie

Wersja aplikacji: 1.1.0. To stan lokalny; ten dokument nie oznacza opublikowania wydania ani zaliczenia zdalnego CI.

## Licencja do decyzji autora

MIT pozostaje **propozycją** w `docs/LICENSE-MIT.proposed.txt`. Nie dodano aktywnego pliku LICENSE ani deklaracji licencji pakietu. Przed publikacją autor wybiera licencję i podpis praw autorskich. Po wybraniu MIT przenosi sam właściwy tekst licencji do LICENSE, uzupełnia autora i aktualizuje metadane pakietu. Plik propozycji zawiera wyraźny nagłówek, aby nie sugerować już udzielonej licencji.

MIT pozwala używać, modyfikować i rozpowszechniać kod, także w płatnym i zamkniętym programie, z zachowaniem wymaganej informacji o prawach i licencji. Oryginał: https://opensource.org/license/mit.

## Zawartość do wysłania

Uruchom `python scripts/package_source.py`. Powstanie `dist/address-plan-1.1.0-source.zip`, zawierający kod, testy, przykłady, dokumentację, CI i pliki kontenera. Skrypt używa jawnej listy katalogów i rozszerzeń; pomija środowiska, cache, `.tmp`, bazy, eksporty prywatne, `.env` i lokalne notatki. Źródłowy PDF pozostaje plikiem roboczym poza paczką publikacyjną; odpis SPEC.md opisuje podstawę implementacji.

Przejrzane przykłady są syntetyczne: T1–T5 i przykładowa sieć AV. Nie przedstawiają rzeczywistej infrastruktury zboru lub firmy. Nie dodawaj własnej bazy SQLite do repozytorium. `.gitignore` obejmuje bazy i pliki pomocnicze.

Po wyborze licencji rozpakuj paczkę do pustego folderu i otwórz w nim terminal. Następnie:

```powershell
git init -b main
git add .
git status --short
git commit -m "Prepare Address Plan 1.1"
```

Utworzenie zdalnego repozytorium i push wymagają osobnej decyzji autora. Nazwa sugerowana przez lokalną notatkę użytkownika: **address-plan**. Program i komenda nadal nazywają się `adresplan`. Nie dodano nieistniejącego adresu repozytorium ani plakietki sugerującej udane CI.

## Sprawdzenia przed wydaniem

Zainstaluj zależności z pliku lock i pakiet edytowalny, następnie uruchom pytest, Ruff, mypy i pip check zgodnie z README. `python -m build --no-isolation` tworzy wheel i sdist. Gotowy wheel sprawdź w nowym środowisku, spoza folderu źródeł, a po instalacji otwórz `serve`.

CI zawiera testy na Linux/Python 3.11 i 3.12 oraz Windows/Python 3.12. Osobny job buduje i sprawdza kontener. Zdalne wyniki będą znane po rzeczywistym wysłaniu repozytorium na GitHuba.

## Docker

```powershell
docker compose up --build -d
docker compose logs
docker compose down
```

Otwórz `http://127.0.0.1:8000`. Nazwany wolumen `projects` zachowuje bazę po zatrzymaniu i odtworzeniu kontenera. Nie dodawaj `--volumes` do zatrzymania, jeśli chcesz zachować dane. Proces pracuje jako użytkownik bez uprawnień roota. W kontenerze nasłuchuje na 0.0.0.0, a port komputera jest ograniczony do 127.0.0.1. Kontener nie wymaga LibreOffice — jest ono tylko narzędziem sprawdzania wyglądu podczas rozwoju.
