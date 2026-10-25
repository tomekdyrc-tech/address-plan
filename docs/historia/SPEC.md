# AdresPlan — odpis tekstowy specyfikacji

Źródło: `12_AdresPlan_specyfikacja.pdf`, wersja 1.0 z 09.10.2026.

Ten plik jest odpisem tekstu ze wszystkich 9 stron, ułatwiającym pracę nad kodem. Układ tabel i łamanie wierszy pochodzą z ekstrakcji PDF; w razie wątpliwości należy sprawdzić oryginalny dokument. Doprecyzowania i plan realizacji znajdują się w `PLAN.md`, zwłaszcza w decyzjach D1–D7. Poniżej zachowano oryginalne wymagania, również te wymagające doprecyzowania.


## Strona 1

```text
AdresPlan
Planer adresacji IPv4 (VLSM) i IPv6 dla budynków, lokalizacji i VLAN-ów. Specyfikacja
do wklejenia w Codex.
Wersja dokumentu
1.0, 09.10.2026
Typ aplikacji
Lokalna aplikacja webowa (FastAPI + HTMX) z rdzeniem w czystym Pythonie i CLI
Wymagana wiedza
CIDR, VLSM, sumaryzacja, podstawy IPv6 (/48, /56, /64, SLAAC), VLAN, Python 3.11+,
podstawy HTTP/HTML
Szacowany czas
Rdzeń + CLI: 1-2 dni. Pełny interfejs i eksporty: 3-5 dni
Zależność od innych
Brak. Rdzeń da się potem użyć w projekcie 11 (trener podsieci)
1. Cel i kontekst
Narzędzie dla administratora małej lub średniej sieci (zbór, szkoła, biuro z kilkoma budynkami), które z listy
segmentów (VLAN-ów) i liczby urządzeń produkuje kompletny, zweryfikowany plan adresacji IPv4 i IPv6
oraz gotową dokumentację. Ma być wygodne: edytowalna tabela, przeliczanie na żywo, walidacja w trakcie
wpisywania, kalkulator podsieci pod ręką.
Czym to nie jest: nie jest to IPAM (NetBox, phpIPAM) śledzący pojedyncze adresy hostów, ani serwer
DHCP/DNS, ani skaner sieci (to projekt 13). Wartość leży w planowaniu i dokumentowaniu, nie w zarządzaniu
operacyjnym.
Zasady pracy z Codexem
Pracuj etapami z rozdziału 11. Po każdym etapie uruchom testy i nie przechodź dalej na czerwonym.
Kod, identyfikatory i komentarze po angielsku, interfejs użytkownika po polsku. Cała logika sieciowa
wyłącznie przez moduł ipaddress ze standardowej biblioteki, bez ręcznego parsowania łańcuchów i bez
własnych operacji bitowych tam, gdzie ipaddress je ma. Moduł core jest czysty: bez I/O, bez bazy, bez
importów z web, store i export.
2. Zakres
Obszar
MVP (obowiązkowe)
Wersja 2 (jeśli zostanie dostęp)
Struktura
Projekt, Lokalizacja, Budynek, Segment (drzewo 3
poziomów)
Szablony projektów, duplikowanie
budynku
IPv4
VLSM z hierarchiczną sumaryzacją, przypinanie bloków,
rezerwacje (brama, statyczne, DHCP)
Import istniejących, zajętych podsieci
jako blokady
IPv6
Plan /48 -> /56 -> /64, łącza /127, loopbacki /128,
generator ULA, strefy ip6.arpa
Strategia podsieci z numerem VLAN w
adresie
Kontrola
Walidacja błędów i ostrzeżeń, metryki wykorzystania i
fragmentacji, tryb Zamroź plan
Diff między wersjami planu, historia
zmian
Narzędzia
Kalkulator podsieci IPv4/IPv6
Generator konfiguracji (Cisco IOS,
MikroTik)
Wyjście
CSV, XLSX, DOCX, Markdown, JSON (eksport i import),
widok do druku
Diagram Mermaid/Graphviz
Poza zakresem
Logowanie użytkowników, śledzenie adresów hostów,
DHCP/DNS, skanowanie, integracje z urządzeniami
```


## Strona 2

```text
3. Stack technologiczny
Warstwa
Wybór
Uzasadnienie
Język
Python 3.12 (minimum 3.11)
ipaddress w stdlib robi większość pracy
sieciowej
Rdzeń
dataclasses + stdlib, walidacja wejścia w
pydantic v2 na granicy (web/CLI)
Czysty, szybko testowalny
Web
FastAPI + Jinja2 + HTMX (plik JS dołączony lokalnie,
bez CDN)
Edycja inline bez npm i bundlera
Baza
SQLite (SQLAlchemy 2.x lub sqlite3)
Jeden plik, zero konfiguracji
Eksport
openpyxl, python-docx, csv ze stdlib
Stabilne, bez zależności systemowych
Testy
pytest, hypothesis
Testy właściwościowe świetnie pasują do
alokatora
Jakość
ruff, mypy --strict dla core
Wyłapuje błędy typów w arytmetyce adresów
Uruchomienie
uv lub venv, opcjonalnie Dockerfile
adresplan serve i gotowe
Dlaczego nie Streamlit: wystarczy do prototypu, ale edycja drzewa z tabelą inline jest w nim uciążliwa.
HTMX daje szybki, stały interfejs bez budowania frontendu.
4. Struktura repozytorium
adresplan/
  pyproject.toml
  README.md
  src/adresplan/
    core/
      models.py         # Project, Node, Segment, Allocation, Plan, Finding
      sizing.py         # prefix_for_usable, next_pow2, nibble helpers
      allocator.py      # generic free-list allocator (IPv4Network | IPv6Network)
      plan4.py          # hierarchical IPv4 plan
      plan6.py          # hierarchical IPv6 plan
      reservations.py   # gateway / static / DHCP ranges (integer arithmetic)
      validate.py       # errors and warnings
      calc.py           # subnet calculator
    store/              # SQLite repository
    export/             # csv_.py xlsx.py docx_.py markdown.py json_.py
    web/                # FastAPI app, templates/, static/htmx.min.js
    cli.py              # adresplan plan|calc|serve|export
  tests/
    test_sizing.py test_allocator.py test_plan4.py test_plan6.py
    test_validate.py test_calc.py test_exports.py test_properties.py
5. Model danych
Zasada nadrzędna: w bazie trzymasz wyłącznie dane wejściowe. Plan to czysta funkcja
build_plan(project) -> Plan, deterministyczna: te same dane dają ten sam wynik, zawsze. Dzięki temu nie
ma rozjazdu między bazą a wyliczeniami. Jedyny wyjątek to bloki przypięte (pinned_*), które są świadomą
decyzją użytkownika.
Pole
Typ
Opis
Project.v4_pool
CIDR
Główna pula IPv4, np. 10.20.0.0/16. Odrzuć host bits (strict=True),
UI proponuje poprawkę
Project.v6_prefix
CIDR lub null
Np. 2001:db8:abcd::/48. Pole v6_kind: gua, ula, doc
Project.settings
JSON
Domyślne: growth_pct=25, gateway=first, p2p_prefix=31,
v6_building_prefix=56, v6_growth_pct=100,
v6_subnet_strategy=sequential
Node.kind
enum
site, building, segment
Node.parent_id, sort_order
int
Drzewo i kolejność wyświetlania (kolejność wpływa tylko na remisy)
Segment.role
enum
lan, p2p, loopback, mgmt
Segment.vlan_id
1-4094 lub null
Unikalny w obrębie lokalizacji (ostrzeżenie przy duplikacie)
AdresPlan - specyfikacja projektu 12
strona 2 / 9
```


## Strona 3

```text
Pole
Typ
Opis
Segment.hosts
int >= 0
Liczba urządzeń końcowych bez bramy
Segment.growth_pct
int
Zapas na rozwój, domyślnie z ustawień projektu
Segment.gateway
first / last / none
Pozycja bramy; gateway_addrs 0-3 (3 = HSRP/VRRP: wirtualny + dwa
routery)
Segment.static_count
int
Ile adresów po bramie zarezerwować na urządzenia statyczne
*.pinned_v4, *.pinned_v6
CIDR lub null
Ręcznie przypięty blok (segment, budynek lub lokalizacja)
Segment.v6_enabled
bool
Czy segment dostaje /64
Node.notes
text
Wolny opis, trafia do eksportu
6. Algorytmy IPv4
6.1 Rozmiar segmentu
Dla segmentu typu lan i mgmt:
usable_needed = ceil(hosts * (1 + growth_pct/100)) + gateway_addrs + static_count
prefix        = 32 - (usable_needed + 1).bit_length()     # == 32 - ceil(log2(usable_needed + 2))
Używaj bit_length() zamiast math.log2: arytmetyka całkowitoliczbowa, brak błędów zmiennoprzecinkowych
przy potęgach dwójki. Dwa dodatkowe adresy to adres sieci i broadcast. Minimalny blok dla lan to /30 (przy
usable_needed = 0 zgłoś błąd walidacji). Rola p2p daje /31 (RFC 3021; opcja p2p_prefix=30 dla starego
sprzętu), rola loopback daje /32.
usable_neede
d
1-2
3-6
7-14
15-30
31-62
63-126
127-254
255-510
Prefiks
/30
/29
/28
/27
/26
/25
/24
/23
6.2 Alokator (jeden, generyczny dla IPv4 i IPv6)
Napisz jedną implementację działającą na IPv4Network i IPv6Network (obie mają address_exclude, subnet_of,
overlaps), parametryzowaną rodziną adresów. Algorytm best-fit na liście wolnych bloków:
def allocate(pool, requests, pinned):
    free = [pool]
    for p in pinned:                      # 1. pinned first; must be inside pool, no overlap
        host = next(f for f in free if p.subnet_of(f))        # else -> Finding(error)
        free.remove(host)
        free.extend(host.address_exclude(p) if host != p else [])
    for r in sorted(requests, key=lambda r: (r.prefix, r.sort_order, r.name)):
        cands = [f for f in free if f.prefixlen <= r.prefix]
        if not cands:
            record_error(r, free); continue                   # do not abort, collect all
        best = min(cands, key=lambda n: (-n.prefixlen, int(n.network_address)))
        taken = type(best)((best.network_address, r.prefix))  # first aligned subnet of best
        free.remove(best)
        if best != taken:
            free.extend(best.address_exclude(taken))
        result[r] = taken
    return result, sorted(free, key=lambda n: int(n.network_address))
•
Best-fit (najmniejszy pasujący wolny blok, remis: najniższy adres) ogranicza fragmentację lepiej niż
first-fit.
•
address_exclude zwraca generator, nie posortowaną listę, a rzuca ValueError, gdy argument nie jest
podsiecią. Materializuj wynik i sortuj tylko do wyświetlania.
•
Determinizm: sortowanie stabilne z jawnym kluczem. Żadnej zależności od kolejności iteracji zbiorów.
•
Błąd braku miejsca ma być użyteczny: ile adresów potrzeba łącznie, ile jest wolnych, największy wolny
blok, oraz sugestia minimalnej puli (np. "potrzebujesz co najmniej /23").
AdresPlan - specyfikacja projektu 12
strona 3 / 9
```


## Strona 4

```text
6.3 Hierarchia: lokalizacja, budynek, segment
Dwie fazy, od dołu do góry i od góry w dół:
•
Faza 1 (rozmiary): blok budynku = next_pow2(suma rozmiarów bloków segmentów). To działa, bo bloki o
rozmiarach będących potęgami dwójki, ułożone malejąco, upakowują się bez luk (każde przesunięcie jest
wielokrotnością rozmiaru kolejnego bloku). Analogicznie dla lokalizacji z budynków.
•
Faza 2 (adresy): alokuj lokalizacje z puli projektu, budynki z bloku lokalizacji, segmenty z bloku
budynku, tym samym alokatorem. Dzięki temu każdy budynek to jedna trasa sumaryczna w routingu.
•
Gdy w budynku są przypięte segmenty, wzór z fazy 1 nie wystarcza. Rozmiar ustal próbą: zacznij od
next_pow2(suma) i zwiększaj blok, aż symulowana alokacja się powiedzie.
6.4 Rezerwacje wewnątrz segmentu
Dla prefix <= 30: pierwszy użyteczny adres to int(network_address)+1, ostatni to int(broadcast_address)-1.
Nigdy nie wywołuj list(net.hosts()) na dużym bloku (/8 to 16 mln obiektów). Licz na liczbach całkowitych
i konwertuj ip_address(n) tylko dla wyświetlanych adresów.
•
Brama: pierwszy lub ostatni użyteczny (wg ustawienia), przy gateway_addrs=3 kolejne adresy to routery
HSRP/VRRP.
•
Zakres statyczny: static_count adresów zaraz po adresach bramy.
•
Zakres DHCP: reszta aż do ostatniego użytecznego (minus brama, jeśli last).
•
/31 i /32: brak bramy i DHCP, w eksporcie wpisz "n/d".
Przykład: 10.20.1.0/26, brama first, 8 adresów statycznych: brama .1, statyczne .2-.9, DHCP .10-.62 (53
adresy).
6.5 Walidacja
Poziom
Reguła
Błąd
Nakładanie się dowolnych dwóch alokacji; alokacja poza blokiem nadrzędnym; przypięty blok
niewyrównany lub poza pulą; brak miejsca w puli; nieprawidłowy CIDR (host bits, ValueError przy
strict=True); segment z usable_needed = 0; pula w zakresach 127/8, 169.254/16, 224/4, 240/4
Ostrzeżenie
Pula spoza RFC 1918 (10/8, 172.16/12, 192.168/16); pula w 100.64.0.0/10 (CGNAT); duplikat VLAN ID
w lokalizacji; wykorzystanie segmentu powyżej 85% po zapasie; /30 dla segmentu z więcej niż 2
hostami
Info
VLAN 1 użyty dla ruchu użytkowników; fragmentacja: największy wolny blok / suma wolnych; sugestia
sumaryzacji
Pułapka: is_private w Pythonie
ip_network(...).is_private zwraca True także dla 127.0.0.0/8, 169.254.0.0/16 i dokumentacyjnego
192.0.2.0/24, a dla 100.64.0.0/10 zwraca False. Zweryfikowane. Nie używaj is_private do oceny, czy pula
to RFC 1918. Zdefiniuj jawną listę trzech sieci i sprawdzaj subnet_of.
AdresPlan - specyfikacja projektu 12
strona 4 / 9
```


## Strona 5

```text
7. Algorytmy IPv6
Zasada
Szczegół
Typy prefiksów
GUA z 2000::/3 (od dostawcy, zwykle /48 lub /56; RFC 6177 zostawia dostawcom swobodę). ULA
fd00::/8 (RFC 4193). Dokumentacyjny 2001:db8::/32 (RFC 3849) do przykładów i testów
Podsieć LAN
Zawsze /64 (SLAAC wymaga 64-bitowego identyfikatora interfejsu). Nigdy /80 i dłuższe dla
segmentów z użytkownikami
Łącza P2P
/127 (RFC 6164) z dedykowanego /64 przeznaczonego tylko na łącza
Loopbacki
/128 z dedykowanego /64
Hierarchia
Lokalizacja /48 -> blok infrastruktury /56 (pierwszy) -> budynki /56 -> segmenty /64. Granice na
wielokrotnościach 4 bitów (/48, /52, /56, /60, /64): czytelne i wygodne dla delegacji ip6.arpa
Rozmiar budynku
Najmniejszy nibble-wyrównany prefiks z {/60, /56, /52}, który mieści ceil(segmenty * (1 +
v6_growth)) bloków /64, nie mniejszy niż v6_building_prefix (domyślnie /56, bo IPv6 jest
tanie)
Alokator
Ten sam generyczny alokator co dla IPv4, z funkcją rozmiaru zastępującą prefix_for_usable
7.1 Strategie numeru podsieci w budynku
Strategia
Zachowanie
Ograniczenie i walidacja
sequential
(domyślna)
Kolejne /64 wg sort_order: ...:100::/64,
...:101::/64
Brak
vlan_decimal_as_he
x
Cyfry dziesiętne VLAN-u czytane jako hex:
VLAN 20 -> ...:120::/64 w budynku nr 1
Pojemność = 2^(64 - prefiks budynku) - 1.
VLAN 110 to 0x110 = 272, więc w /56 (maks.
255) błąd, w /52 (maks. 4095) OK. Kolizja
dwóch segmentów to błąd. VLAN powyżej 999
nie jest obsługiwany
7.2 Przydatne operacje (zweryfikowane)
# ULA /48 generator (RFC 4193): fd + 40 random bits
rnd = secrets.token_bytes(5)
raw = b"\xfd" + rnd + b"\x00" * 10
ula = ipaddress.IPv6Address(int.from_bytes(raw, "big"))      # fdXX:XXXX:XXXX::/48
# ip6.arpa zone of a /64: reverse_pointer has 32 nibbles, the first 16 are the interface id
rp = net64.network_address.reverse_pointer
zone = ".".join(rp.split(".")[16:])
# 2001:db8:abcd:120::/64 -> 0.2.1.0.d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa
# Lazy iteration only. This killed the process during the spec work (2**63 objects):
#   list(ip_network("2001:db8:abcd:1::/64").subnets(new_prefix=127))
first_two = list(itertools.islice(net.subnets(new_prefix=127), 2))
•
Wyświetlaj obie formy: .compressed i .exploded. W tabelach głównie skompresowaną.
•
IPv6Network.hosts() pomija adres anycast routera podsieci (adres sieci), a dla /127 zwraca oba adresy.
Dla /64 nie wolno go iterować, więc brama to network_address + 1 liczona arytmetycznie.
•
Domyślna brama: ::1 w każdym /64 (ustawienie: link-local fe80::1). Pole informacyjne ra_mode: SLAAC lub
DHCPv6.
•
Dla IPv4 strefa in-addr.arpa ma sens tylko dla granic /8, /16, /24. Pokaż ją dla bloków /24 i większych.
8. Kalkulator podsieci
Strona /calc i polecenie adresplan calc. Wejście: 192.168.1.10/24, 192.168.1.10 255.255.255.0,
2001:db8::/48. Spacja zamieniana na /. ip_network akceptuje zarówno maskę (/255.255.255.0), jak i maskę
odwrotną (/0.0.0.255); oba zweryfikowane. Dla wejścia z bitami hosta użyj ip_interface(...).network
zamiast błędu.
•
IPv4: sieć, broadcast, maska, wildcard, prefiks, pierwszy i ostatni użyteczny, liczba użytecznych, maska
binarnie, czy z RFC 1918 (jawna lista).
AdresPlan - specyfikacja projektu 12
strona 5 / 9
```


## Strona 6

```text
•
IPv6: skompresowany i rozwinięty, typ (GUA, ULA, link-local, dokumentacyjny, multicast), liczba /64 w
bloku (np. /56 daje 256), strefa ip6.arpa.
•
Przycisk "podziel na N podsieci" i "podziel na podsieci /X" (leniwie, z limitem wyświetlania np. 256
wierszy).
9. Interfejs i API
Ścieżka
Zawartość
/
Lista projektów: nowy, duplikuj, import JSON
/p/{id}
Edytor. Lewo: drzewo Lokalizacja > Budynek > Segment. Środek: tabela
edytowalna inline (hx-trigger="change delay:300ms"). Dół: plan na żywo,
pasek wykorzystania puli, lista walidacji z linkami do wierszy
/p/{id}/export
Wybór formatu, podgląd
/calc
Kalkulator
GET /api/projects/{id}/plan
Plan jako JSON (ten sam model co w eksporcie)
POST /api/calc
Kalkulator jako API
GET /api/projects/{id}/export.{
csv,xlsx,docx,md,json}
Eksporty
•
Zamroź plan: przycisk zapisuje bieżące alokacje jako pinned_*. Bez tego dodanie jednego segmentu
może przesunąć adresy w działającej sieci, a to najgorsza cecha planerów. Nowe segmenty trafiają potem
w wolne miejsca.
•
Klawiatura: Tab i Enter przechodzą po komórkach, Ctrl+D duplikuje wiersz. Kliknięcie CIDR kopiuje go do
schowka.
•
Tryb jasny i ciemny przez prefers-color-scheme. Brak zewnętrznych zasobów (CDN, fonty).
•
Widok do druku (@media print), z którego przeglądarka robi PDF.
Układ eksportu
Format
Zawartość
CSV/XLSX
Lokalizacja, Budynek, Segment, VLAN, Rola, Hosty (z zapasem), IPv4 CIDR, Maska, Brama, Zakres
statyczny, Zakres DHCP, Broadcast, IPv6 /64, Uwagi. XLSX: arkusze Plan, Podsumowanie (per
budynek), Wolne bloki, Walidacja; zamrożone nagłówki, autofiltr; adresy zapisane jako tekst
DOCX
Strona tytułowa, założenia (pula, zapas, konwencje), tabela per budynek, wolne bloki, uwagi
Markdown
To samo co DOCX w prostej formie, do repozytorium dokumentacji
JSON
Pełny projekt (dane wejściowe) plus wyliczony plan; import przywraca projekt
10. Wektory testowe (zweryfikowane skryptem
referencyjnym)
Testy używają growth_pct=0, gateway_addrs=0, static_count=0, żeby sprawdzać czysty algorytm. Remisy
rozstrzyga kolejność wejściowa (sort_order).
T1. Podstawowy VLSM
Pula 192.168.10.0/24, hosty 100, 50, 25, 10.
Segment
Hosty
Wynik
Zakres użyteczny
A
100
192.168.10.0/25
.1 - .126
B
50
192.168.10.128/26
.129 - .190
C
25
192.168.10.192/27
.193 - .222
D
10
192.168.10.224/28
.225 - .238
AdresPlan - specyfikacja projektu 12
strona 6 / 9
```


## Strona 7

```text
Segment
Hosty
Wynik
Zakres użyteczny
Wolne
192.168.10.240/28
16 adresów
T2. Budynek z łączami i loopbackiem
Pula 10.20.0.0/22. Wykorzystane 485 z 1024 adresów.
Segment
Wejście
Wynik
WiFi-goscie
200 hostów
10.20.0.0/24
Biuro
60
10.20.1.0/26
VoIP
45
10.20.1.64/26
Szkolenia
28
10.20.1.128/27
Kamery
20
10.20.1.160/27
Serwery
12
10.20.1.192/28
Zarzadzanie
10
10.20.1.208/28
Link-R1-SW1
p2p
10.20.1.224/31
Link-R1-SW2
p2p
10.20.1.226/31
Loopback-R1
loopback
10.20.1.228/32
Wolne bloki
10.20.1.229/32, .230/31, .232/29, .240/28, 10.20.2.0/23
T3. Brak miejsca
Pula 192.168.1.0/26, segmenty X=30, Y=30, Z=10. X dostaje 192.168.1.0/27, Y 192.168.1.32/27, Z (wymaga
/28) nie mieści się: oczekiwany błąd z informacją o braku wolnych bloków i sugestią powiększenia puli, bez
wyjątku i bez przerywania alokacji pozostałych segmentów.
T4. Hierarchia
Lokalizacja 10.20.0.0/20. Budynek A (segmenty z T2) potrzebuje sumy 485 adresów, więc /23. Budynek B
(Sala 100, Biuro 40, AV 20): sumy bloków 128+64+32 = 224, więc /24. Budynek C (Plebania 30): /27.
Budynek
Blok
Segmenty w środku
A
10.20.0.0/23
układ jak w T2 (te same adresy)
B
10.20.2.0/24
Sala 10.20.2.0/25, Biuro 10.20.2.128/26, AV 10.20.2.192/27
C
10.20.3.0/27
Plebania 10.20.3.0/27
Wolne
10.20.3.32/27, 10.20.3.64/26, 10.20.3.128/25, 10.20.4.0/22, 10.20.8.0/21
T5. IPv6
Prefiks 2001:db8:abcd::/48, budynki po /56. Blok infrastruktury (pierwszy): 2001:db8:abcd::/56. Budynek 1:
2001:db8:abcd:100::/56, budynek 2: ...:200::/56, budynek 3: ...:300::/56. W budynku 1 siedem
segmentów LAN sequential: ...:100::/64 ... ...:106::/64. Łącza: 2001:db8:abcd:1::/127,
2001:db8:abcd:1::2/127, itd. z dedykowanego /64. W /48 mieści się 65 536 podsieci /64, w /56 dokładnie 256.
vlan_decimal_as_hex: VLAN 10 -> 2001:db8:abcd:110::/64, VLAN 20 -> ...:120::/64, VLAN 99 -> ...:199::/64
(budynek 1, /56). VLAN 110 w budynku /56 to błąd walidacji (0x110 > 255).
Testy właściwościowe (hypothesis)
•
Dla losowych puli i list segmentów: żadne dwie alokacje się nie nakładają; każda mieści się w puli; każda
jest wyrównana do swojego rozmiaru; każda ma num_addresses - 2 >= usable_needed.
•
Suma alokacji plus wolne bloki równa się rozmiarowi puli.
•
Idempotencja i determinizm: dwa uruchomienia z tymi samymi danymi dają identyczny wynik, także po
permutacji segmentów o różnych rozmiarach.
•
Zamrożony plan plus dodanie segmentu nie zmienia żadnego wcześniejszego adresu.
AdresPlan - specyfikacja projektu 12
strona 7 / 9
```


## Strona 8

```text
•
Eksport JSON, import, ponowne przeliczenie: ten sam plan.
11. Etapy pracy i gotowe prompty
Kolejność jest ustawiona tak, żeby po etapie 4 narzędzie było już użyteczne (CLI), nawet gdyby dostęp
do Codexa skończył się wcześniej. Każdy prompt zaczyna się od wskazania dokumentu jako specyfikacji.
Etap 1: rdzeń IPv4 (cel: testy T1-T3 na zielono)
Przeczytaj SPEC.md. Utwórz szkielet repozytorium z rozdziału 4 (pyproject, ruff, mypy, pytest).
Zaimplementuj core/sizing.py i generyczny core/allocator.py zgodnie z rozdziałami 6.1 i 6.2. Napisz testy
dla wektorów T1, T2 (segmenty płaskie) i T3 oraz testy właściwościowe z rozdziału 10. Nie dotykaj web ani
bazy. Zatrzymaj się, gdy pytest i mypy --strict core przechodzą.
Etap 2: hierarchia, rezerwacje, walidacja (T4)
Zaimplementuj plan4.py (dwie fazy z 6.3, w tym próbę rozmiaru przy przypiętych segmentach),
reservations.py (6.4, wyłącznie arytmetyka całkowitoliczbowa) i validate.py (6.5, z jawną listą RFC 1918
zamiast is_private). Dodaj tryb Zamroź plan jako funkcję czystą freeze(project, plan) -> project. Testy
T4 i przykład rezerwacji z 6.4.
Etap 3: IPv6 (T5)
Zaimplementuj plan6.py na tym samym alokatorze: blok infrastruktury, budynki /56, segmenty /64, łącza
/127, loopbacki /128, obie strategie z 7.1, generator ULA i strefy ip6.arpa z 7.2. Iteruj wyłącznie leniwie
(islice). Dodaj test, że VLAN 110 w budynku /56 daje błąd walidacji.
Etap 4: CLI i JSON (po tym etapie narzędzie jest używalne)
Dodaj cli.py (Typer lub argparse): adresplan plan projekt.json, adresplan calc 10.0.0.0/22, eksport CSV
i Markdown. Zdefiniuj schemat JSON projektu i zapewnij round-trip. Dołącz przykładowy
examples/budynek.json odpowiadający T2 i T4. Dodaj kalkulator z rozdziału 8.
Etap 5: SQLite i interfejs webowy
Dodaj store/ (SQLite, tylko dane wejściowe) i web/ (FastAPI, Jinja2, HTMX lokalnie) zgodnie z rozdziałem 9:
lista projektów, edytor drzewa z edycją inline, plan na żywo, walidacja z linkami do wierszy, kalkulator,
przycisk Zamroź plan. Bez zewnętrznych zasobów. Serwer domyślnie na 127.0.0.1.
Etap 6: eksporty i szlify
Zaimplementuj XLSX (arkusze Plan, Podsumowanie, Wolne bloki, Walidacja), DOCX i Markdown według
układu z rozdziału 9 oraz widok do druku. Dodaj README z przykładem, Dockerfile i test, że wygenerowany
XLSX i DOCX otwierają się bez błędu (openpyxl i python-docx wczytują je z powrotem).
12. Kryteria ukończenia
•
pytest zielony, w tym testy właściwościowe; ruff i mypy --strict na core bez uwag.
•
Wektory T1-T5 odtwarzają się co do adresu.
•
Plan dla projektu z T4 powstaje poniżej sekundy, a edycja komórki w interfejsie odświeża wynik bez
przeładowania strony.
•
Wyeksportowany XLSX i DOCX otwierają się w Excelu i Wordzie, a adresy nie są zamieniane na liczby ani
daty.
•
Dodanie segmentu do zamrożonego planu nie zmienia żadnego istniejącego adresu.
•
README opisuje uruchomienie w trzech poleceniach i zawiera zrzut ekranu lub przykładowy eksport.
AdresPlan - specyfikacja projektu 12
strona 8 / 9
```


## Strona 9

```text
Nie rozszerzaj zakresu bez potrzeby
Jeśli zbliża się koniec dostępu do Codexa, zatrzymaj się po etapie 4 i dopracuj to, co jest. Działające CLI z
eksportem i testami jest warte więcej niż niedokończony interfejs graficzny.
AdresPlan - specyfikacja projektu 12
strona 9 / 9
```
