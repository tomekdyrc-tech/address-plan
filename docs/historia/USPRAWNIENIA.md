# Usprawnienia pracy z planem

Stan: 16.10.2026, kod lokalny po poprawkach IPv6. Wdrożono siedem usprawnień z uzgodnionej listy. Nie wymagają nowych bibliotek.

## Widok struktury

Nad edytorem wybierz lokalizację lub budynek albo wyszukaj nazwę, VLAN i fragment CIDR. Filtr działa na tabeli edycji oraz przydziałach. „Pokaż całą strukturę” przywraca widok. Ukryte elementy zachowują dane i nadal są zapisywane; filtry nie wywołują zapisu projektu. Wybór widoku jest zachowywany w sesji karty dla danego projektu.

## Biblioteka szablonów

W navbarze wybierz **Szablony**. W podglądzie wzorca możesz zmienić nazwę, zobaczyć segmenty i zapotrzebowanie, zastąpić zawartość obiektem zapisanym w projekcie oraz przenieść wzorzec do kosza. Z kosza można przywrócić szablon. Aktualizacja nie zmienia projektów utworzonych wcześniej. Stara karta nie nadpisze nowszej wersji wzorca.

## Pełna kopia danych

Na stronie Projektów wybierz **Pobierz pełną kopię zapasową**. Kopia obejmuje projekty, wszystkie wersje historii i szablony, także kosz. Jest spójną migawką SQLite wykonaną podczas pracy aplikacji.

Aby sprawdzić lub odtworzyć pobraną kopię, zatrzymaj serwer i uruchom:

```powershell
.\.venv\Scripts\adresplan.exe serve --database 'C:\ścieżka\address-plan-backup.sqlite3'
```

Program użyje tej bazy; poprzedni plik pozostaje zachowany. Kopia może zawierać dane dokumentacji i historyczne plany, dlatego przechowuj ją razem ze swoją dokumentacją. Eksport JSON pojedynczego projektu nadal nie obejmuje biblioteki ani całej historii.

## Podgląd zmian przed zapisem

W sekcji **Widok struktury → Zapisywanie zmian** wybierz **Najpierw pokaż skutki — zatwierdzę sam**. Możesz zmieniać pola, dodawać elementy i stosować szablony. Baza pozostaje bez zmian. Tabela podglądu pokazuje zapisane i proponowane CIDR-y, włącznie z dodanymi i usuniętymi przydziałami.

- **Zatwierdź wszystkie zmiany** zapisuje podgląd jako jedną wersję projektu.
- **Odrzuć podgląd** wczytuje dotychczasowy zapis.
- Niezatwierdzony podgląd istnieje tylko w tej karcie; nie jest automatyczną kopią zapasową. Przy opuszczaniu karty działa ostrzeżenie o niezapisanych zmianach.
- Zmiana projektu w innej karcie blokuje zatwierdzenie starej wersji. Najpierw uzgodnij zmiany z aktualnym zapisem.
- Wzorzec można zapisać po zatwierdzeniu podglądu. Wrócenie do automatycznego zapisu wymaga wcześniejszego zatwierdzenia albo odrzucenia.

## Z kalkulatora do projektu

W trybie VLSM rozwiń **Przenieś wynik do dokumentacji**, nazwij projekt i wybierz **Utwórz projekt z wyniku VLSM**. Aplikacja ponownie obliczy dane formularza; nie korzysta z nieaktualnej tabeli widocznej wcześniej.

CIDR-y są zachowane jako przypięcia segmentów. Zapas procentowy to 0%, a osobna rezerwacja bram i adresów statycznych jest wyłączona, zgodnie z założeniami kalkulatora. Liczba urządzeń w kalkulatorze już obejmowała planowaną bramę i własny zapas. W edytorze możesz świadomie zmienić te reguły, uwzględniając pojemność przypiętych podsieci. Częściowy wynik VLSM nie tworzy projektu.

## Skąd taki rozmiar podsieci?

W ustawieniach szczegółowych segmentu zobaczysz np. `20 urządzeń + 5 zapasu (25%) + 1 adres bramy + 0 dodatkowych statycznych = 26 potrzebnych adresów; minimum /27, pojemność 30`. Opis pochodzi z tych samych reguł co alokator. Większy przypięty blok może mieć dodatkową pojemność. P2P i loopback nie dostają zapasu ani bram LAN.

## Dane i zakres dokumentacji

W edytorze rozwiń **Dane dokumentacji**: autor, organizacja, opis i data. Pola są opcjonalne i trafiają do projektu JSON oraz raportów.

W **Podgląd i eksport** wybierz raport szczegółowy dla administratora albo skrócony dla odbiorcy. Wariant skrócony obejmuje przydziały, metrykę i istotne ostrzeżenia; pomija techniczne zestawienia silnika. Działa dla Markdown, Worda, Excela i widoku Druk/PDF. JSON zachowuje komplet danych wejściowych, a CSV swoją tabelę segmentów niezależnie od wyboru profilu.

## Aktualizacja i sprawdzenie

SQLite migruje transakcyjnie z wersji 2 do 3. Dodawane są stan kosza oraz numer wersji szablonu. Projekty i ich historia zostają zachowane. Bieżący JSON ma format 3, a import nadal obsługuje 1 i 2. Starsza aplikacja nie otworzy bazy po migracji do 3; do powrotu służy kopia sprzed aktualizacji.

746 testów zaliczono na Pythonie 3.11.0 i 3.12.14. Sprawdzono odtworzenie pełnej kopii, migrację biblioteki, kosz, konflikty rewizji, podgląd wieloetapowej edycji, jeden zapis po zatwierdzeniu, przenoszenie VLSM, wyliczenia oraz raporty z literalnymi tekstami. W przeglądarce sprawdzono również podstawowy przebieg pracy; nowe raporty Office ponownie otwarto programowo, bez osobnego renderowania ich przez Word/Excel.

Zmiany są w źródłach. Wcześniejsze paczki `dist` nie były w tym etapie przebudowywane.
