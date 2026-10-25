# Plan adresacji — Przyklad T4

**Status: KOMPLETNY. Błędy: 0; ostrzeżenia: 4.**

Wynik niekompletny zawiera tylko udane przydziały. Brak CIDR oznacza brak przydziału; diagnostyka jest na końcu raportu.

## Założenia

| Parametr | Wartość |
| --- | --- |
| Projekt ID | demo-t4 |
| Pula IPv4 | 10.20.0.0/20 |
| Prefiks IPv6 | — |
| Rodzaj IPv6 | doc |

Liczba hostów nie obejmuje osobno rezerwowanych bram ani puli statycznej. Zapas zaokrąglamy w górę. P2P i loopback mają stałe liczby końców. W IPv6 brak broadcastu. Adres bramy IPv6 i tryb RA są informacją dokumentacyjną.

| Ustawienie projektu | Wartość |
| --- | --- |
| growth\_pct | 0 |
| gateway | none |
| gateway\_addrs | 0 |
| p2p\_prefix | 31 |
| v6\_site\_prefix | 48 |
| v6\_building\_prefix | 56 |
| v6\_infra\_prefix | 56 |
| v6\_growth\_pct | 100 |
| v6\_subnet\_strategy | sequential |
| v6\_gateway\_mode | global |
| v6\_link\_local\_gateway | fe80::1 |
| v6\_ra\_mode | slaac |

## Lokalizacje i budynki

| Rodzaj | ID | Nazwa | Rodzic | IPv4 | IPv6 | Przypięte IPv4 | Przypięte IPv6 | Uwagi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lokalizacja | site | Lokalizacja | — | 10.20.0.0/20 | — | 10.20.0.0/20 | — | — |
| budynek | a | Budynek A | site | 10.20.0.0/23 | — | — | — | — |
| budynek | b | Budynek B | site | 10.20.2.0/24 | — | — | — | — |
| budynek | c | Budynek C | site | 10.20.3.0/27 | — | — | — | — |

## Lokalizacja / Budynek A

Budynek ID: a. Blok IPv4: 10.20.0.0/23; IPv6: —.

### Segmenty i zapotrzebowanie

| ID | Segment | VLAN | Rola | Hosty wejściowe | Zapas % | Hosty z zapasem | Statyczne | IPv6 włączone | Uwagi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a-0 | WiFi-goscie | — | lan | 200 | 0 | 200 | 0 | tak | — |
| a-1 | Biuro | — | lan | 60 | 0 | 60 | 0 | tak | — |
| a-2 | VoIP | — | lan | 45 | 0 | 45 | 0 | tak | — |
| a-3 | Szkolenia | — | lan | 28 | 0 | 28 | 0 | tak | — |
| a-4 | Kamery | — | lan | 20 | 0 | 20 | 0 | tak | — |
| a-5 | Serwery | — | lan | 12 | 0 | 12 | 0 | tak | — |
| a-6 | Zarzadzanie | — | mgmt | 10 | 0 | 10 | 0 | tak | — |
| a-7 | Link-R1-SW1 | — | p2p | 0 | 0 | 2 | 0 | tak | — |
| a-8 | Link-R1-SW2 | — | p2p | 0 | 0 | 2 | 0 | tak | — |
| a-9 | Loopback-R1 | — | loopback | 0 | 0 | 1 | 0 | tak | — |

### IPv4

| ID | CIDR | Maska | Użyteczne adresy | Potrzebne / pojemność | Bramy | Statyczne | DHCP | Broadcast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a-0 | 10.20.0.0/24 | 255.255.255.0 | 10.20.0.1–10.20.0.254 | 200 / 254 | — | — | 10.20.0.1–10.20.0.254 | 10.20.0.255 |
| a-1 | 10.20.1.0/26 | 255.255.255.192 | 10.20.1.1–10.20.1.62 | 60 / 62 | — | — | 10.20.1.1–10.20.1.62 | 10.20.1.63 |
| a-2 | 10.20.1.64/26 | 255.255.255.192 | 10.20.1.65–10.20.1.126 | 45 / 62 | — | — | 10.20.1.65–10.20.1.126 | 10.20.1.127 |
| a-3 | 10.20.1.128/27 | 255.255.255.224 | 10.20.1.129–10.20.1.158 | 28 / 30 | — | — | 10.20.1.129–10.20.1.158 | 10.20.1.159 |
| a-4 | 10.20.1.160/27 | 255.255.255.224 | 10.20.1.161–10.20.1.190 | 20 / 30 | — | — | 10.20.1.161–10.20.1.190 | 10.20.1.191 |
| a-5 | 10.20.1.192/28 | 255.255.255.240 | 10.20.1.193–10.20.1.206 | 12 / 14 | — | — | 10.20.1.193–10.20.1.206 | 10.20.1.207 |
| a-6 | 10.20.1.208/28 | 255.255.255.240 | 10.20.1.209–10.20.1.222 | 10 / 14 | — | — | 10.20.1.209–10.20.1.222 | 10.20.1.223 |
| a-7 | 10.20.1.224/31 | 255.255.255.254 | 10.20.1.224–10.20.1.225 | 2 / 2 | — | — | — | — |
| a-8 | 10.20.1.226/31 | 255.255.255.254 | 10.20.1.226–10.20.1.227 | 2 / 2 | — | — | — | — |
| a-9 | 10.20.1.228/32 | 255.255.255.255 | 10.20.1.228–10.20.1.228 | 1 / 1 | — | — | — | — |

### IPv6

| ID | CIDR | Brama | RA | Końce łącza / loopback | Reverse DNS |
| --- | --- | --- | --- | --- | --- |
| a-0 | — | — | — | — | — |
| a-1 | — | — | — | — | — |
| a-2 | — | — | — | — | — |
| a-3 | — | — | — | — | — |
| a-4 | — | — | — | — | — |
| a-5 | — | — | — | — | — |
| a-6 | — | — | — | — | — |
| a-7 | — | — | — | — | — |
| a-8 | — | — | — | — | — |
| a-9 | — | — | — | — | — |

## Lokalizacja / Budynek B

Budynek ID: b. Blok IPv4: 10.20.2.0/24; IPv6: —.

### Segmenty i zapotrzebowanie

| ID | Segment | VLAN | Rola | Hosty wejściowe | Zapas % | Hosty z zapasem | Statyczne | IPv6 włączone | Uwagi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b-0 | Sala | — | lan | 100 | 0 | 100 | 0 | tak | — |
| b-1 | Biuro | — | lan | 40 | 0 | 40 | 0 | tak | — |
| b-2 | AV | — | lan | 20 | 0 | 20 | 0 | tak | — |

### IPv4

| ID | CIDR | Maska | Użyteczne adresy | Potrzebne / pojemność | Bramy | Statyczne | DHCP | Broadcast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b-0 | 10.20.2.0/25 | 255.255.255.128 | 10.20.2.1–10.20.2.126 | 100 / 126 | — | — | 10.20.2.1–10.20.2.126 | 10.20.2.127 |
| b-1 | 10.20.2.128/26 | 255.255.255.192 | 10.20.2.129–10.20.2.190 | 40 / 62 | — | — | 10.20.2.129–10.20.2.190 | 10.20.2.191 |
| b-2 | 10.20.2.192/27 | 255.255.255.224 | 10.20.2.193–10.20.2.222 | 20 / 30 | — | — | 10.20.2.193–10.20.2.222 | 10.20.2.223 |

### IPv6

| ID | CIDR | Brama | RA | Końce łącza / loopback | Reverse DNS |
| --- | --- | --- | --- | --- | --- |
| b-0 | — | — | — | — | — |
| b-1 | — | — | — | — | — |
| b-2 | — | — | — | — | — |

## Lokalizacja / Budynek C

Budynek ID: c. Blok IPv4: 10.20.3.0/27; IPv6: —.

### Segmenty i zapotrzebowanie

| ID | Segment | VLAN | Rola | Hosty wejściowe | Zapas % | Hosty z zapasem | Statyczne | IPv6 włączone | Uwagi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c-0 | Plebania | — | lan | 30 | 0 | 30 | 0 | tak | — |

### IPv4

| ID | CIDR | Maska | Użyteczne adresy | Potrzebne / pojemność | Bramy | Statyczne | DHCP | Broadcast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c-0 | 10.20.3.0/27 | 255.255.255.224 | 10.20.3.1–10.20.3.30 | 30 / 30 | — | — | 10.20.3.1–10.20.3.30 | 10.20.3.31 |

### IPv6

| ID | CIDR | Brama | RA | Końce łącza / loopback | Reverse DNS |
| --- | --- | --- | --- | --- | --- |
| c-0 | — | — | — | — | — |

## Infrastruktura IPv6

| Lokalizacja ID | Blok | Rezerwa | Pula łączy /127 | Pula loopbacków /128 |
| --- | --- | --- | --- | --- |

## Podsumowanie wykorzystania

Każdy poziom jest liczony osobno. Nie sumuj przydziałów rodziców i ich dzieci jako rozłącznych bloków. Ciągłość = największy wolny blok / całe wolne miejsce; przy braku wolnego miejsca ma wartość n/d.

| Rodzina | Rodzic ID | Rodzaj puli | Sieć | Zajęte adresy | Wolne adresy | Największy wolny blok | Wykorzystanie | Ciągłość |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IPv4 | projekt | hierarchia | 10.20.0.0/20 | 4096 | 0 | — | 100.00% | n/d |
| IPv4 | site | hierarchia | 10.20.0.0/20 | 800 | 3296 | 10.20.8.0/21 | 19.53% | 62.14% |
| IPv4 | a | hierarchia | 10.20.0.0/23 | 485 | 27 | 10.20.1.240/28 | 94.73% | 59.26% |
| IPv4 | b | hierarchia | 10.20.2.0/24 | 224 | 32 | 10.20.2.224/27 | 87.50% | 100.00% |
| IPv4 | c | hierarchia | 10.20.3.0/27 | 32 | 0 | — | 100.00% | n/d |

| Rodzina | Rodzic ID | Rodzaj puli | Sieć | Zajęte adresy | Wolne adresy | Największy wolny blok | Wykorzystanie | Ciągłość |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Wolne bloki

| Rodzina | Rodzic ID | Rodzaj puli | Wolny CIDR | Liczba adresów |
| --- | --- | --- | --- | --- |
| IPv4 | site | hierarchia | 10.20.3.32/27 | 32 |
| IPv4 | site | hierarchia | 10.20.3.64/26 | 64 |
| IPv4 | site | hierarchia | 10.20.3.128/25 | 128 |
| IPv4 | site | hierarchia | 10.20.4.0/22 | 1024 |
| IPv4 | site | hierarchia | 10.20.8.0/21 | 2048 |
| IPv4 | a | hierarchia | 10.20.1.229/32 | 1 |
| IPv4 | a | hierarchia | 10.20.1.230/31 | 2 |
| IPv4 | a | hierarchia | 10.20.1.232/29 | 8 |
| IPv4 | a | hierarchia | 10.20.1.240/28 | 16 |
| IPv4 | b | hierarchia | 10.20.2.224/27 | 32 |

## Walidacja

| Poziom | Kod | Węzeł ID | Opis |
| --- | --- | --- | --- |
| Informacja | pool\_fragmentation | — | INFO \[pool\_fragmentation\] \[projekt\]: Wolne miejsce w puli i jego ciągłość. wolne adresy: 0; największy wolny prefiks: n/d; ciągłość: n/d |
| Informacja | summary\_route | site | INFO \[summary\_route\] \[site: Lokalizacja\]: Blok sumaryczny rodzica. sieć: 10.20.0.0/20 |
| Informacja | pool\_fragmentation | site | INFO \[pool\_fragmentation\] \[site: Lokalizacja\]: Wolne miejsce w puli i jego ciągłość. wolne adresy: 3296; największy wolny prefiks: /21; ciągłość: 64/103 |
| Informacja | summary\_route | a | INFO \[summary\_route\] \[a: Budynek A\]: Blok sumaryczny rodzica. sieć: 10.20.0.0/23 |
| Informacja | pool\_fragmentation | a | INFO \[pool\_fragmentation\] \[a: Budynek A\]: Wolne miejsce w puli i jego ciągłość. wolne adresy: 27; największy wolny prefiks: /28; ciągłość: 16/27 |
| Ostrzeżenie | high\_segment\_utilization | a-1 | OSTRZEŻENIE \[high\_segment\_utilization\] \[a-1: Biuro\]: Zapotrzebowanie przekracza 85% pojemności segmentu. wymagane użyteczne: 60; pojemność użyteczna: 62 |
| Ostrzeżenie | high\_segment\_utilization | a-3 | OSTRZEŻENIE \[high\_segment\_utilization\] \[a-3: Szkolenia\]: Zapotrzebowanie przekracza 85% pojemności segmentu. wymagane użyteczne: 28; pojemność użyteczna: 30 |
| Ostrzeżenie | high\_segment\_utilization | a-5 | OSTRZEŻENIE \[high\_segment\_utilization\] \[a-5: Serwery\]: Zapotrzebowanie przekracza 85% pojemności segmentu. wymagane użyteczne: 12; pojemność użyteczna: 14 |
| Informacja | summary\_route | b | INFO \[summary\_route\] \[b: Budynek B\]: Blok sumaryczny rodzica. sieć: 10.20.2.0/24 |
| Informacja | pool\_fragmentation | b | INFO \[pool\_fragmentation\] \[b: Budynek B\]: Wolne miejsce w puli i jego ciągłość. wolne adresy: 32; największy wolny prefiks: /27; ciągłość: 1 |
| Informacja | summary\_route | c | INFO \[summary\_route\] \[c: Budynek C\]: Blok sumaryczny rodzica. sieć: 10.20.3.0/27 |
| Informacja | pool\_fragmentation | c | INFO \[pool\_fragmentation\] \[c: Budynek C\]: Wolne miejsce w puli i jego ciągłość. wolne adresy: 0; największy wolny prefiks: n/d; ciągłość: n/d |
| Ostrzeżenie | high\_segment\_utilization | c-0 | OSTRZEŻENIE \[high\_segment\_utilization\] \[c-0: Plebania\]: Zapotrzebowanie przekracza 85% pojemności segmentu. wymagane użyteczne: 30; pojemność użyteczna: 30 |

Raport obliczono z danych wejściowych projektu. Aby zachować adresy przy rozbudowie, zapisz zamrożony projekt JSON poleceniem freeze. CSV i Markdown są dokumentacją; do ponownego importu służy JSON.
