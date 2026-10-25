# Eksport dokumentacji — v0.1

Wersja v0.1 obsługuje CSV, Markdown i JSON. Każdy eksport waliduje wejście i liczy świeży plan wspólnym rdzeniem. Zapisana wcześniej migawka `plan` nie jest źródłem przydziałów. Pliki można tworzyć z projektu zwykłego albo zamrożonego.

## Polecenia

Z głównego folderu projektu:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format csv --output output/plan.csv
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format md --output output/plan.md
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format json --output output/projekt.json
```

Skróty: `-f` oznacza `--format`, `-o` oznacza `--output`. Format jest wymagany, a rozszerzenie pliku nie zmienia wybranego formatu. Bez `--output` sam dokument trafia na stdout. Potwierdzenie zapisu i diagnostyka trafiają na stderr. `--verbose` dodaje komunikaty informacyjne.

Katalog docelowy musi istnieć. Zapis wykorzystuje plik tymczasowy w tym samym katalogu i atomową podmianę. Jawnie wskazany istniejący plik jest zastępowany po przygotowaniu pełnego dokumentu. CSV/Markdown nie mogą nadpisać źródłowego projektu pod tą samą ścieżką. JSON można jawnie zaktualizować w miejscu.

Kod 0 oznacza sukces lub same ostrzeżenia. Kod 1 oznacza wyeksportowany plan niekompletny; dokument zawiera status, udane przydziały i diagnostykę. Błąd wejścia lub zapisu daje kod 2. Niekompletny plan można dokumentować i poprawiać, ale nie można go zamrozić.

## CSV

CSV to tabela segmentów, z nazwą lokalizacji i budynku w każdym wierszu. Zawiera:

- identyfikatory, nazwę projektu, status kompletności oraz liczbę błędów i ostrzeżeń;
- segment, VLAN, rolę, hosty wejściowe, efektywny zapas i hosty z zapasem;
- IPv4 CIDR, maskę, wymagane użyteczne adresy, bramy, zakres użyteczny, statyczny, DHCP i broadcast;
- IPv6 CIDR, bramę, tryb RA, końce P2P/loopbacków i reverse DNS;
- uwagi segmentu, budynku i lokalizacji oraz błędy/ostrzeżenia dotyczące segmentu lub jego przodków.

Kolumna `IPv6 CIDR` obejmuje /64, /127 i /128, zgodnie z rolą segmentu. P2P i loopback nie mają bram ani DHCP. Dla /31 i /32 kolumna broadcast pozostaje pusta. Brak przydziału w niekompletnym planie daje puste pola adresowe, ale sam segment nadal ma wiersz. Projekt bez segmentów ma jeden wiersz typu `projekt`, żeby zachować status i diagnostykę.

Plik używa średnika, wszystkich pól w cudzysłowach, końców wierszy CRLF i UTF-8 z BOM. Na stdout BOM nie jest dodawany. Moduł `csv` obsługuje średniki, cudzysłowy i nowe linie w danych. Przy ręcznym imporcie do arkusza wybierz separator `;`, UTF-8 i tekst dla kolumn adresowych. XLSX zapisuje tekstowe typy komórek bez potrzeby ręcznego importu.

Tekst zaczynający się od `=`, `+`, `-` lub `@` — również po białych znakach/BOM — dostaje apostrof na początku komórki, aby ograniczyć interpretowanie tekstu jako formuły w arkuszu. Dotyczy to także pól zaczynających się od tabulatora lub nowej linii. Jest to świadoma zmiana prezentacji CSV; oryginał pozostaje w JSON. CSV nie służy do ponownego importu projektu.

CSV przedstawia segmenty; pełne podsumowania, wolne bloki i wszystkie komunikaty znajdziesz w Markdown lub JSON.

## Markdown

Raport do repozytorium zawiera:

1. Nazwę projektu, status, liczbę błędów i ostrzeżeń.
2. Założenia, pule, wszystkie ustawienia projektu i wyjaśnienie liczenia hostów.
3. Lokalizacje i budynki, ich bloki sumaryczne, przypięcia i uwagi.
4. Osobno dla każdego budynku: zapotrzebowanie segmentów, IPv4 z rezerwacjami oraz IPv6.
5. Infrastrukturę IPv6 z trzema wydzielonymi pulami /64.
6. Metryki, każdy poziom osobno, z dokładnymi całkowitymi licznikami adresów.
7. Wszystkie wolne bloki z rodzicem i rodzajem puli.
8. Pełną walidację z poziomem, kodem, ID węzła i polskim opisem.

Nazwy i uwagi są tekstem: znaki Markdown są cytowane, surowy HTML jest kodowany, a nowe linie w komórkach zamieniane na `<br>`. Użytkownik nie może wprowadzić nowego wiersza tabeli ani nagłówka przez treść nazwy. Brak wartości jest oznaczony kreską. Metryki rodziców i dzieci nie są dodawane do jednego wyniku.

Przykładowy [raport sieci AV](../examples/exports/church-av.md) i [raport T4](../examples/exports/t4-hierarchy.md) są częścią repozytorium. Markdown można przeglądać na GitHubie. Od wersji 1.0 dostępne są również DOCX i widok do druku/PDF.

## JSON

`export --format json` używa tego samego formatu co `plan --json` i `plan --output`. Zawiera `schema_version=2`, pełne wejście i świeży wynik. Nie ma drugiej implementacji formatu. To właściwy format do zachowania projektu, przypięć i infrastruktury. Szczegóły: [json-format.md](json-format.md).

Eksport nie zmienia wejścia, nie losuje ULA i nie dodaje dat ani identyfikatorów. Dla tego samego wejścia i wersji algorytmu treść jest powtarzalna.

Techniczne źródła: [Python csv](https://docs.python.org/3.12/library/csv.html), [tabele GitHub Flavored Markdown](https://github.github.com/gfm/#tables-extension-).

## XLSX i DOCX

`export --format xlsx --output plan.xlsx` oraz `export --format docx --output plan.docx` zapisują binarne dokumenty. `--output` jest wymagane, żeby zawartość ZIP nie trafiła przypadkiem do terminala. Kody zakończenia 0/1/2 i atomowy zapis zachowują dotychczasowe znaczenie.

XLSX: Plan, Podsumowanie, Wolne bloki i Walidacja; tytuł/status, filtry, zamrożone nagłówki i identyfikacja, szerokości, zawijanie, powtarzane nagłówki wydruku. Plan zawiera pola CSV, z lokalizacją/budynkiem/segmentem na początku. Wszystkie komórki są tekstowe: zachowują dokładne IPv6 i nie wykonują formuł. Wydruk szerokiej tabeli zachowuje skalę 100% i może wymagać kilku stron w poziomie. Treści ponad limit komórki XLSX są odrzucane z komunikatem, bez cichego obcinania.

DOCX: A4 poziomo, tytuł i założenia, ustawienia, tabele IPv4 i IPv6 dla każdego budynku, uwagi, infrastruktura, wolne bloki i walidacja. Powtarzane nagłówki, niedzielone zwykłe wiersze i numerowane strony ułatwiają czytanie długich raportów. Lista wolnych bloków IPv6 może zajmować wiele stron — pokazuje pełny wynik, bez wyliczania pojedynczych hostów.

Daty kontenera ZIP/Office mogą się różnić między zapisami. Powtarzalność dotyczy danych raportu; nie wymaga identyczności binarnej DOCX/XLSX. Do powtarzalnego porównywania źródeł używaj JSON, CSV lub Markdown.

## Blokady i diagram v1.1

JSON, Markdown i DOCX zawierają listę blokad; XLSX dodaje arkusz Blokady, gdy lista nie jest pusta. Metryki zajętości uwzględniają także blokady. CSV nadal przedstawia segmenty, bez osobnych wierszy zewnętrznych blokad. Diagram SVG pobiera się z widoku Diagram w przeglądarce; to samodzielny plik bez zewnętrznych zasobów i skryptów.
