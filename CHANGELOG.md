# Historia zmian

Skrót najważniejszych zmian. Pełny dziennik prac z każdego etapu: [szczegółowa historia](docs/historia/CHANGELOG-szczegolowy.md).

## 1.2.0 — 2026-10-25

- Wersja angielska interfejsu, komunikatów, CLI (`--lang en`) i wszystkich raportów; przełącznik PL / EN w aplikacji.
- Generator konfiguracji startowej Cisco IOS i MikroTik RouterOS (VLAN, brama, DHCP, loopbacki, IPv6).
- Tryb podglądu zmian przed zapisem, biblioteka szablonów z koszem i pełna kopia zapasowa bazy.
- IPv6 w wielu lokalizacjach, wyłączanie IPv6 z zachowaniem ustawień, czytelniejsze komunikaty błędów.
- Projekt z wyniku kalkulatora VLSM i skrócony profil raportów.
- Porządki w kodzie: interfejs WWW podzielony na moduły tras, komunikaty w osobnym module.
- Zaktualizowane zależności, uproszczona dokumentacja, licencja MIT.

## 1.1.0 — 2026-10-16

- Historia planów: porównywanie wersji i przywracanie.
- Szablony budynków i lokalizacji, duplikowanie budynków, dodawanie wielu oddziałów naraz.
- Blokady zajętych podsieci IPv4 i IPv6, import listy CIDR.
- Diagram hierarchii adresacji z pobieraniem SVG.

## 1.0.0 — 2026-10-14

- Lokalny interfejs w przeglądarce (FastAPI, HTMX) z zapisem w SQLite i ochroną przed nadpisaniem zmian z innej karty.
- Raporty XLSX i DOCX, widok do druku i PDF, jasny i ciemny motyw.
- Obraz Dockera i CI w GitHub Actions.

## 0.1.0 — 2026-10-14

- Planer VLSM IPv4 z hierarchią lokalizacja → budynek → segment, bramami, zakresami statycznymi i DHCP.
- Plan IPv6 z infrastrukturą, generator ULA i zamrażanie adresów.
- Format JSON z walidacją, CLI (`plan`, `calc`, `freeze`, `export`), eksport CSV i Markdown.
