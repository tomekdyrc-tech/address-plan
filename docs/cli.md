# Korzystanie z CLI — część 4B

Stan: 16.10.2026, wersja `1.1.0`. Dostępne są `plan`, `calc`, `freeze`, `export` i `serve`. Eksporty CSV/Markdown/JSON/XLSX/DOCX opisuje [exports.md](exports.md); uruchomienie przeglądarki i SQLite opisuje [web.md](web.md).

## Pierwsze uruchomienie

Polecenia wykonuj w głównym folderze projektu, po instalacji opisanej w README. Nie trzeba aktywować środowiska Pythona.

```powershell
.\.venv\Scripts\adresplan.exe --help
.\.venv\Scripts\adresplan.exe --version
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json
```

Każde polecenie ma własną pomoc, np. `.\.venv\Scripts\adresplan.exe calc --help`. Alternatywna forma uruchomienia to `.\.venv\Scripts\python.exe -m adresplan ...`. Samo uruchomienie bez argumentów pokazuje pomoc.

Wymagana wiedza: podstawy CIDR, masek i VLAN-ów. CLI operuje na plikach JSON; od etapu 5 listę segmentów możesz też zmieniać w interfejsie uruchamianym przez `serve`. Przykład jest syntetyczny i nie opisuje prawdziwej sieci zboru.

## Plan z projektu

```powershell
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json --show-free
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json --verbose
```

Wynik zawiera status kompletności, lokalizacje/budynki/segmenty, VLAN-y i CIDR obu protokołów. Niżej są bramy, zakresy statyczne i DHCP, informacje IPv6, infrastruktura oraz metryki dla każdego poziomu osobno. Przykład AV daje:

| Segment | IPv4 | IPv6 |
| --- | --- | --- |
| Dźwięk | 10.42.0.0/27 | 2001:db8:42:100::/64 |
| Obraz | 10.42.0.32/27 | 2001:db8:42:101::/64 |
| Zarządzanie | 10.42.0.64/28 | 2001:db8:42:102::/64 |

Ostrzeżenie o wykorzystaniu segmentu Dźwięk jest oczekiwane: 20 urządzeń, 25% zapasu i jedna brama wymagają 26 z 30 użytecznych adresów. Plan jest kompletny, więc polecenie kończy się kodem 0.

`--show-free` pokazuje wszystkie wolne bloki wraz z rodzicem i rodzajem puli. Domyślnie widać ich liczbę i metryki. Wolne miejsce budynku, lokalizacji i projektu nie jest jedną sumowaną pulą; te same adresy mogą być opisywane na różnych poziomach hierarchii. Brak przydziału oznaczamy kreską, a niekompletny plan ma widoczny status i kod zakończenia 1.

`--verbose` dodaje komunikaty informacyjne, m.in. o blokach sumarycznych i ciągłości wolnej puli. Bez tej flagi na stderr są tylko błędy i ostrzeżenia.

## Zapis wyniku jako JSON

Najpierw utwórz katalog wyników:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json --output output/plan.json
.\.venv\Scripts\adresplan.exe plan output/plan.json
```

`--output`/`-o` zapisuje pełne dane wejściowe i świeży wynik w formacie z 4A. Katalog docelowy musi istnieć; istniejący plik pod wskazaną ścieżką jest zastępowany atomowo. Projekt źródłowy pozostaje bez zmian, chyba że jawnie podasz tę samą ścieżkę jako wynikową.

```powershell
.\.venv\Scripts\adresplan.exe plan examples/stage4a_project.json --json
```

`--json` wypisuje na stdout wyłącznie dokument JSON, również przy ostrzeżeniach lub niekompletnym planie. Komunikaty trafiają na stderr. Do zapisu pliku używaj `--output`; omija to różnice kodowania przy przekierowaniu wyjścia przez różne wersje PowerShell. Oba strumienie programu używają UTF-8.

Niekompletny plan można zapisać, aby go poprawić; `plan` nadal zwróci kod 1. Przy imporcie program nie ufa zapisanej tabeli `plan`, tylko przelicza dane z `project`. Szczegóły: [format JSON](json-format.md).

## Zamrożenie adresacji

```powershell
.\.venv\Scripts\adresplan.exe freeze examples/stage4a_project.json --output output/zamrozony.json
.\.venv\Scripts\adresplan.exe plan output/zamrozony.json
```

`freeze` wymaga jawnego pliku wynikowego. Zapisuje istniejące przydziały w `pinned_v4`/`pinned_v6` oraz przypięcie całej infrastruktury IPv6. Po dodaniu segmentu dotychczasowe adresy pozostają przypięte; nowy segment musi zmieścić się w wolnym miejscu. Rodzice nie rosną automatycznie po zamrożeniu.

Jeśli plan ma błędy, polecenie zwraca 1 i nie tworzy ani nie zmienia pliku docelowego. Ostrzeżenia nie blokują zamrożenia. Podanie tej samej ścieżki wejścia i wyjścia jest dozwolone jako jawny zapis w miejscu; ponowne zamrożenie tego samego projektu nie zmienia jego treści.

## Kalkulator IPv4

```powershell
.\.venv\Scripts\adresplan.exe calc 192.168.1.10/24
.\.venv\Scripts\adresplan.exe calc 192.168.1.10 255.255.255.0
.\.venv\Scripts\adresplan.exe calc "192.168.1.10 0.0.0.255"
```

Wszystkie trzy zapisy opisują tę samą sieć `192.168.1.0/24`. Kalkulator zachowuje wejściowy adres hosta i wylicza sieć przez `ip_interface(...).network`. W przeciwieństwie do pól sieci projektu, tutaj ustawione bity hosta są normalnym wejściem.

Wynik pokazuje sieć, prefiks, maskę, wildcard, maskę binarną, broadcast, pierwszy/ostatni użyteczny adres, liczbę użytecznych adresów, przynależność całego bloku do RFC 1918 i dane reverse DNS. Zapis `adres/maska` oraz `adres/wildcard` także jest obsługiwany.

- `/31`: dwa końce łącza, oba adresy użyteczne; brak broadcastu.
- `/32`: jeden adres hosta; brak broadcastu.
- Sam adres bez prefiksu: trasa hosta `/32`.
- Pula dokumentacyjna, CGNAT lub loopback nie jest oznaczana jako RFC 1918.

Pojedynczą zwykłą strefę `in-addr.arpa` pokazujemy dla /8, /16 i /24. Dla np. /20 potrzebne są strefy na granicach oktetów; program nie wymyśla jednej nazwy strefy /20. Delegacje bezklasowe są poza zakresem. Nazwa PTR wejściowego adresu jest pokazywana oddzielnie i nie oznacza, że taki rekord istnieje w DNS.

## Kalkulator IPv6

```powershell
.\.venv\Scripts\adresplan.exe calc 2001:db8:abcd::/48
.\.venv\Scripts\adresplan.exe calc 2001:db8:abcd:1234::beef/56
.\.venv\Scripts\adresplan.exe calc fe80::1/64
```

Wynik pokazuje skróconą i rozwiniętą postać adresu oraz sieci, typ adresu i całego bloku, dokładną liczbę adresów, liczbę podsieci /64, strefę `ip6.arpa` i nazwę PTR. Nie pokazuje broadcastu.

Typy to dokumentacyjny, GUA, ULA, link-local, multicast, loopback, nieokreślony, mieszany i inny. Dla szerokiego bloku obejmującego różne kategorie typ bloku jest mieszany, nawet gdy konkretny adres wejściowy ma jeden typ. Rozpoznawanie GUA dotyczy zakresu `2000::/3` z osobnym rozpoznaniem dokumentacyjnego `2001:db8::/32`; nie jest sprawdzaniem routingu w Internecie. Kalkulator rozpoznaje ULA `fc00::/7`; planer projektu nadal wymaga lokalnie nadanej ULA `fd00::/8`.

W /48 jest 65 536 podsieci /64, w /56 jest ich 256, w /127 i /128 — zero. Strefa IPv6 wymaga prefiksu wyrównanego do 4 bitów. Dla /127 program pokazuje brak pojedynczej strefy i osobno nazwę PTR wejściowego adresu. Sam adres IPv6 bez prefiksu jest traktowany jako /128. Zapisy z `%interfejsu` nie są obsługiwane. Kalkulator nie wykonuje zapytań DNS ani żadnych innych operacji sieciowych.

## Podział na podsieci

```powershell
.\.venv\Scripts\adresplan.exe calc 192.168.1.0/24 --split 4
.\.venv\Scripts\adresplan.exe calc 192.168.1.0/24 --new-prefix 26
.\.venv\Scripts\adresplan.exe calc 2001:db8::/48 --new-prefix 64 --limit 4
```

Dwa pierwsze polecenia dają cztery podsieci /26: `.0`, `.64`, `.128`, `.192`. Trzecie ma 65 536 wynikowych /64, ale pokazuje tylko cztery pierwsze.

- `--split N`: N musi być dodatnią potęgą dwójki. Dla 3 program proponuje 4 i kończy się błędem 2, czekając na poprawione polecenie.
- `--new-prefix X`: podaj liczbę bez ukośnika, np. `64`. Prefiks nie może być krótszy od wejściowego ani przekraczać 32/128 dla danej rodziny.
- Wybierz tylko jeden tryb podziału. N=1 lub prefiks równy wejściowemu daje ten sam pojedynczy blok.
- `--limit`: od 1 do 256, domyślnie 256; wymaga włączenia podziału.

Podgląd jest leniwy i ograniczony. Nawet podział `::/0` na /128 nie tworzy listy całej przestrzeni adresów. Liczba wynikowych podsieci jest pokazywana dokładnie, a ograniczenie podglądu jest jawne.

## Błędy i kody zakończenia

| Kod | Znaczenie |
| --- | --- |
| 0 | Sukces; same ostrzeżenia nie blokują wyniku |
| 1 | Niekompletny plan albo odmowa zamrożenia planu z błędami |
| 2 | Błędne argumenty, dane JSON, wejście kalkulatora lub błąd odczytu/zapisu |
| 130 | Przerwanie przez użytkownika podczas wykonywania polecenia |

W PowerShell kod ostatniego programu odczytasz przez `$LASTEXITCODE`. Błąd zawiera polski opis, trwały kod diagnostyczny i — gdy dotyczy węzła — jego ID oraz nazwę. Brak miejsca zawiera dostępne oszacowania pojemności i sugestię prefiksu; program nie zmienia puli automatycznie.

Błąd JSON wskazuje pole, np. `project.nodes[2].hosts`. Typowe pomyłki nie pokazują stosu wywołań Pythona. Tekstowe nazwy i opisy są zabezpieczone przed wstrzyknięciem znaków sterujących terminala; zapis JSON zachowuje ich oryginalną treść.

Źródło zachowania masek, hostów /31 i /32 oraz interfejsów: [dokumentacja Python 3.12 — ipaddress](https://docs.python.org/3.12/library/ipaddress.html). Pomoc i argumenty korzystają z [argparse](https://docs.python.org/3.12/library/argparse.html).
