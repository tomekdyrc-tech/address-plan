# Projekty przykładowe

Wszystkie dane są syntetyczne. Pliki mają format `schema_version=1` i zawierają wejście projektu bez zapisanej migawki wyniku. Program oblicza wynik po każdym wczytaniu.

| Plik | Przypadek | Oczekiwany wynik |
| --- | --- | --- |
| `t1-vlsm.json` | T1: 100, 50, 25, 10 hostów | Cztery podsieci w `192.168.10.0/24`, wolne `192.168.10.240/28`; kod 0 |
| `t2-building.json` | T2: LAN-y, dwa łącza i loopback | Segmenty zajmują 485 adresów, wolne 539; kod 0 |
| `t3-no-space.json` | T3: za mała pula /26 | X i Y otrzymują /27, Z nie mieści się; sugestia /25, kod 1 |
| `budynek.json` | T4: trzy budynki | A=`10.20.0.0/23`, B=`10.20.2.0/24`, C=`10.20.3.0/27`; kod 0 |
| `t5-ipv6.json` | T5: sequential IPv6 i dual stack | Budynki `…:100::/56`, `…:200::/56`, `…:300::/56`, osobna infrastruktura; kod 0 |
| `t5-vlan-hex.json` | T5: cyfry VLAN jako hex | VLAN 10 → `…:110::/64`, 20 → `…:120::/64`, 99 → `…:199::/64`; kod 0 |
| `t5-vlan-110-error.json` | Celowy błąd VLAN 110 w /56 | Błąd offsetu `0x110`, brak tego przydziału IPv6; kod 1 |
| `church-av.json` | Sieć AV i biura | Syntetyczne audio, obraz, prezentacja, monitoring, goście, zarządzanie, biuro, P2P i loopback; kod 0 |
| `stage4a_project.json` | Mały przykład z 4A | Trzy segmenty AV, zachowany dla wcześniejszej demonstracji; kod 0 |

Wektory T1–T4 mają zerowy zapas oraz brak bram i rezerwacji statycznych, zgodnie z PDF. T5 i przykłady AV mają własne jawne ustawienia. Ostrzeżenia o wysokim wykorzystaniu segmentu nie zmieniają kodu 0, jeśli nie ma błędów.

T1–T3 badają płaskie przydziały. Format aplikacji wymaga drzewa, dlatego lokalizacja i budynek są w tych plikach przypięte do całej puli. Dzięki temu adresy segmentów i wolne bloki odpowiadają dokładnie płaskim wektorom. W T2 wolne 539 adresów jest wewnątrz przypiętego budynku; nie należy dodawać do tego zajętości rodziców. W T4 lokalizacja jest przypięta do /20, budynki otrzymują minimalne bloki.

Przykłady uruchomienia z głównego folderu repozytorium:

```powershell
.\.venv\Scripts\adresplan.exe plan examples/budynek.json
.\.venv\Scripts\adresplan.exe plan examples/t3-no-space.json
.\.venv\Scripts\adresplan.exe plan examples/t5-vlan-hex.json
.\.venv\Scripts\adresplan.exe export examples/church-av.json --format md
```

T3 i błąd VLAN 110 są celowo niekompletne. Ich eksport działa, wyraźnie oznacza wynik i zwraca 1. Zamrożenie jest wtedy blokowane.

## Przykładowe raporty do przejrzenia

- [Sieć AV — Markdown](exports/church-av.md)
- [Sieć AV — CSV](exports/church-av.csv)
- [Hierarchia T4 — Markdown](exports/t4-hierarchy.md)
- [Hierarchia T4 — CSV](exports/t4-hierarchy.csv)
- [Sieć AV — XLSX](exports/church-av.xlsx)
- [Sieć AV — DOCX](exports/church-av.docx)
- [Hierarchia T4 — XLSX](exports/t4-hierarchy.xlsx)
- [Hierarchia T4 — DOCX](exports/t4-hierarchy.docx)

Raporty są deterministyczne, nie zawierają daty ani ścieżek lokalnych. Testy porównują je bajt po bajcie z eksportem aktualnego planera. Pliki CSV mają UTF-8 z BOM, średnik jako separator i cytowane pola. Pliki JSON są źródłem do ponownego importu; raporty CSV/Markdown służą do czytania i dokumentacji.

## v1.1 — istniejące sieci i rozbudowa

`v11-branch.json` zawiera syntetyczny oddział z dwiema sieciami LAN i trzema blokadami IPv4/IPv6 na poziomie projektu i budynku. Diagram: [v11-branch.svg](exports/v11-branch.svg). Przykład służy do sprawdzenia wolnego miejsca, zamrożenia, duplikowania i porównywania kolejnych zapisów.
