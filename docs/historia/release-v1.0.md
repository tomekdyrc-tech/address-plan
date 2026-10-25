# Address Plan 1.0

Lokalna wersja 1.0.0 zamyka sześć etapów implementacji. Repozytorium i wydanie nie zostały jeszcze opublikowane. MIT jest przygotowaną propozycją do wyboru przez autora.

Program planuje IPv4 VLSM i IPv6 w hierarchii lokalizacji, budynków i segmentów, sprawdza pojemność, przypięcia, VLAN-y i wolne bloki. Potrafi zamrozić adresację, zachować projekty w SQLite i pracować przez CLI lub lokalny polski interfejs. Dokumentację zapisuje w JSON, CSV, Markdown, XLSX i DOCX.

Nowości względem etapu 5: raporty Office, druk/PDF, motywy, Enter/Shift+Enter, duplikowanie segmentu przyciskiem lub Ctrl+D oraz kopiowanie CIDR. Kopia segmentu ma nowe ID i puste przypięcia; zamrożone źródło nie zmienia się. Dodano dokumentację architektury, zrzuty, pliki kontenera, job CI i pakowanie źródeł bez lokalnych danych.

Pierwsze uruchomienie: zainstaluj pakiet według README, wykonaj `adresplan serve` i otwórz `http://127.0.0.1:8000`. T4 i sieć AV są gotowymi syntetycznymi przykładami. Własne bazy i plany zachowuj poza repozytorium.

Wymagania: Python 3.11+, przeglądarka z JavaScript; do oglądania raportów Word/Excel lub LibreOffice. Docker jest opcjonalny. LibreOffice użyte do kontroli wyglądu nie jest zależnością aplikacji.

Ograniczenia odbioru opisano w `stage-6-verification.md`: kontener wymaga uruchomienia na hoście z Dockerem, a natywne okno drukowania/PDF zależy od przeglądarki. Nie dodano publicznego hostingu ani logowania. Szczegóły zmian znajdują się w CHANGELOG.md.
