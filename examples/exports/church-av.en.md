# Address plan — Syntetyczna sieć AV i biura

**Status: COMPLETE. Errors: 0; warnings: 3.**

An incomplete result contains only successful allocations. A missing CIDR means no allocation; diagnostics are at the end of the report.

## Assumptions

| Parameter | Value |
| --- | --- |
| Project ID | church-av |
| IPv4 pool | 10.42.0.0/20 |
| IPv6 prefix | 2001:db8:42::/48 |
| IPv6 kind | doc |

The host count does not include separately reserved gateways or the static pool. Growth is rounded up. P2P and loopback have fixed endpoint counts. IPv6 has no broadcast. The IPv6 gateway address and RA mode are documentation only.

| Project setting | Value |
| --- | --- |
| growth\_pct | 25 |
| gateway | first |
| gateway\_addrs | 1 |
| p2p\_prefix | 31 |
| v6\_site\_prefix | 48 |
| v6\_building\_prefix | 56 |
| v6\_infra\_prefix | 56 |
| v6\_growth\_pct | 100 |
| v6\_subnet\_strategy | sequential |
| v6\_gateway\_mode | global |
| v6\_link\_local\_gateway | fe80::1 |
| v6\_ra\_mode | slaac |

## Sites and buildings

| Kind | ID | Name | Parent | IPv4 | IPv6 | Pinned IPv4 | Pinned IPv6 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| site | site | Lokalizacja zboru | — | 10.42.0.0/22 | 2001:db8:42::/48 | — | — | Dane wyłącznie przykładowe. Nie opisują rzeczywistej infrastruktury. |
| building | hall | Sala główna | site | 10.42.0.0/23 | 2001:db8:42:100::/56 | — | — | — |
| building | office | Biuro | site | 10.42.2.0/26 | 2001:db8:42:200::/56 | — | — | — |

## Lokalizacja zboru / Sala główna

Building ID: hall. IPv4 block: 10.42.0.0/23; IPv6: 2001:db8:42:100::/56.

### Segments and requirements

| ID | Segment | VLAN | Role | Input hosts | Growth % | Hosts with growth | Static | IPv6 enabled | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| audio | Dźwięk | 10 | lan | 20 | 25 | 25 | 4 | yes | Mikser i stageboxy; rezerwa statyczna liczona osobno. |
| video | Obraz | 20 | lan | 16 | 25 | 20 | 0 | yes | Kamery transmisji i stanowisko realizacji. |
| presentation | Prezentacja | 30 | lan | 8 | 25 | 10 | 0 | yes | — |
| cameras | Monitoring | 40 | lan | 24 | 25 | 30 | 4 | yes | — |
| guests | Goście | 50 | lan | 80 | 25 | 100 | 0 | yes | — |
| mgmt | Zarządzanie | 60 | mgmt | 10 | 25 | 13 | 0 | yes | — |

### IPv4

| ID | CIDR | Mask | Usable addresses | Needed / capacity | Gateways | Static | DHCP | Broadcast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| audio | 10.42.0.192/27 | 255.255.255.224 | 10.42.0.193–10.42.0.222 | 30 / 30 | 10.42.0.193 | 10.42.0.194–10.42.0.197 | 10.42.0.198–10.42.0.222 | 10.42.0.223 |
| video | 10.42.0.224/27 | 255.255.255.224 | 10.42.0.225–10.42.0.254 | 21 / 30 | 10.42.0.225 | — | 10.42.0.226–10.42.0.254 | 10.42.0.255 |
| presentation | 10.42.1.0/28 | 255.255.255.240 | 10.42.1.1–10.42.1.14 | 11 / 14 | 10.42.1.1 | — | 10.42.1.2–10.42.1.14 | 10.42.1.15 |
| cameras | 10.42.0.128/26 | 255.255.255.192 | 10.42.0.129–10.42.0.190 | 35 / 62 | 10.42.0.190 | 10.42.0.129–10.42.0.132 | 10.42.0.133–10.42.0.189 | 10.42.0.191 |
| guests | 10.42.0.0/25 | 255.255.255.128 | 10.42.0.1–10.42.0.126 | 101 / 126 | 10.42.0.1 | — | 10.42.0.2–10.42.0.126 | 10.42.0.127 |
| mgmt | 10.42.1.16/28 | 255.255.255.240 | 10.42.1.17–10.42.1.30 | 14 / 14 | 10.42.1.17 | — | 10.42.1.18–10.42.1.30 | 10.42.1.31 |

### IPv6

| ID | CIDR | Gateway | RA | Link endpoints / loopback | Reverse DNS |
| --- | --- | --- | --- | --- | --- |
| audio | 2001:db8:42:100::/64 | 2001:db8:42:100::1 | slaac | — | 0.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |
| video | 2001:db8:42:101::/64 | 2001:db8:42:101::1 | slaac | — | 1.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |
| presentation | 2001:db8:42:102::/64 | 2001:db8:42:102::1 | slaac | — | 2.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |
| cameras | 2001:db8:42:103::/64 | 2001:db8:42:103::1 | slaac | — | 3.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |
| guests | 2001:db8:42:104::/64 | 2001:db8:42:104::1 | slaac | — | 4.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |
| mgmt | 2001:db8:42:105::/64 | 2001:db8:42:105::1 | slaac | — | 5.0.1.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |

## Lokalizacja zboru / Biuro

Building ID: office. IPv4 block: 10.42.2.0/26; IPv6: 2001:db8:42:200::/56.

### Segments and requirements

| ID | Segment | VLAN | Role | Input hosts | Growth % | Hosts with growth | Static | IPv6 enabled | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| link | Łącze router–biuro | — | p2p | 0 | 0 | 2 | 0 | yes | — |
| loop | Loopback routera | — | loopback | 0 | 0 | 1 | 0 | yes | — |
| staff | Stanowiska biurowe | 70 | lan | 20 | 25 | 25 | 0 | yes | — |

### IPv4

| ID | CIDR | Mask | Usable addresses | Needed / capacity | Gateways | Static | DHCP | Broadcast |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| link | 10.42.2.32/31 | 255.255.255.254 | 10.42.2.32–10.42.2.33 | 2 / 2 | — | — | — | — |
| loop | 10.42.2.34/32 | 255.255.255.255 | 10.42.2.34–10.42.2.34 | 1 / 1 | — | — | — | — |
| staff | 10.42.2.0/27 | 255.255.255.224 | 10.42.2.1–10.42.2.30 | 26 / 30 | 10.42.2.1 | — | 10.42.2.2–10.42.2.30 | 10.42.2.31 |

### IPv6

| ID | CIDR | Gateway | RA | Link endpoints / loopback | Reverse DNS |
| --- | --- | --- | --- | --- | --- |
| link | 2001:db8:42:1::/127 | — | — | 2001:db8:42:1::, 2001:db8:42:1::1 | — |
| loop | 2001:db8:42:2::/128 | — | — | 2001:db8:42:2:: | — |
| staff | 2001:db8:42:200::/64 | 2001:db8:42:200::1 | slaac | — | 0.0.2.0.2.4.0.0.8.b.d.0.1.0.0.2.ip6.arpa |

## IPv6 infrastructure

| Site ID | Block | Reserve | Link pool /127 | Loopback pool /128 |
| --- | --- | --- | --- | --- |
| site | 2001:db8:42::/56 | 2001:db8:42::/64 | 2001:db8:42:1::/64 | 2001:db8:42:2::/64 |

## Utilization summary

Each level is counted separately. Do not add up parent and child allocations as separate blocks. Continuity = largest free block / all free space; with no free space it is n/a.

| Family | Parent ID | Pool kind | Network | Used addresses | Free addresses | Largest free block | Utilization | Continuity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IPv4 | project | hierarchy | 10.42.0.0/20 | 1024 | 3072 | 10.42.8.0/21 | 25.00% | 66.67% |
| IPv4 | site | hierarchy | 10.42.0.0/22 | 576 | 448 | 10.42.3.0/24 | 56.25% | 57.14% |
| IPv4 | hall | hierarchy | 10.42.0.0/23 | 288 | 224 | 10.42.1.128/25 | 56.25% | 57.14% |
| IPv4 | office | hierarchy | 10.42.2.0/26 | 35 | 29 | 10.42.2.48/28 | 54.69% | 55.17% |

| Family | Parent ID | Pool kind | Network | Used addresses | Free addresses | Largest free block | Utilization | Continuity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IPv6 | project | project | 2001:db8:42::/48 | 1208925819614629174706176 | 0 | — | 100.00% | n/a |
| IPv6 | site | site | 2001:db8:42::/48 | 14167099448608935641088 | 1194758720166020239065088 | 2001:db8:42:8000::/49 | 1.17% | 50.59% |
| IPv6 | site | infrastructure | 2001:db8:42::/56 | 55340232221128654848 | 4667026250648516558848 | 2001:db8:42:80::/57 | 1.17% | 50.59% |
| IPv6 | site | p2p | 2001:db8:42:1::/64 | 2 | 18446744073709551614 | 2001:db8:42:1:8000::/65 | 0.00% | 50.00% |
| IPv6 | site | loopback | 2001:db8:42:2::/64 | 1 | 18446744073709551615 | 2001:db8:42:2:8000::/65 | 0.00% | 50.00% |
| IPv6 | hall | building | 2001:db8:42:100::/56 | 110680464442257309696 | 4611686018427387904000 | 2001:db8:42:180::/57 | 2.34% | 51.20% |
| IPv6 | office | building | 2001:db8:42:200::/56 | 18446744073709551616 | 4703919738795935662080 | 2001:db8:42:280::/57 | 0.39% | 50.20% |

## Free blocks

| Family | Parent ID | Pool kind | Free CIDR | Address count |
| --- | --- | --- | --- | --- |
| IPv4 | project | hierarchy | 10.42.4.0/22 | 1024 |
| IPv4 | project | hierarchy | 10.42.8.0/21 | 2048 |
| IPv4 | site | hierarchy | 10.42.2.64/26 | 64 |
| IPv4 | site | hierarchy | 10.42.2.128/25 | 128 |
| IPv4 | site | hierarchy | 10.42.3.0/24 | 256 |
| IPv4 | hall | hierarchy | 10.42.1.32/27 | 32 |
| IPv4 | hall | hierarchy | 10.42.1.64/26 | 64 |
| IPv4 | hall | hierarchy | 10.42.1.128/25 | 128 |
| IPv4 | office | hierarchy | 10.42.2.35/32 | 1 |
| IPv4 | office | hierarchy | 10.42.2.36/30 | 4 |
| IPv4 | office | hierarchy | 10.42.2.40/29 | 8 |
| IPv4 | office | hierarchy | 10.42.2.48/28 | 16 |
| IPv6 | site | site | 2001:db8:42:300::/56 | 4722366482869645213696 |
| IPv6 | site | site | 2001:db8:42:400::/54 | 18889465931478580854784 |
| IPv6 | site | site | 2001:db8:42:800::/53 | 37778931862957161709568 |
| IPv6 | site | site | 2001:db8:42:1000::/52 | 75557863725914323419136 |
| IPv6 | site | site | 2001:db8:42:2000::/51 | 151115727451828646838272 |
| IPv6 | site | site | 2001:db8:42:4000::/50 | 302231454903657293676544 |
| IPv6 | site | site | 2001:db8:42:8000::/49 | 604462909807314587353088 |
| IPv6 | site | infrastructure | 2001:db8:42:3::/64 | 18446744073709551616 |
| IPv6 | site | infrastructure | 2001:db8:42:4::/62 | 73786976294838206464 |
| IPv6 | site | infrastructure | 2001:db8:42:8::/61 | 147573952589676412928 |
| IPv6 | site | infrastructure | 2001:db8:42:10::/60 | 295147905179352825856 |
| IPv6 | site | infrastructure | 2001:db8:42:20::/59 | 590295810358705651712 |
| IPv6 | site | infrastructure | 2001:db8:42:40::/58 | 1180591620717411303424 |
| IPv6 | site | infrastructure | 2001:db8:42:80::/57 | 2361183241434822606848 |
| IPv6 | site | p2p | 2001:db8:42:1::2/127 | 2 |
| IPv6 | site | p2p | 2001:db8:42:1::4/126 | 4 |
| IPv6 | site | p2p | 2001:db8:42:1::8/125 | 8 |
| IPv6 | site | p2p | 2001:db8:42:1::10/124 | 16 |
| IPv6 | site | p2p | 2001:db8:42:1::20/123 | 32 |
| IPv6 | site | p2p | 2001:db8:42:1::40/122 | 64 |
| IPv6 | site | p2p | 2001:db8:42:1::80/121 | 128 |
| IPv6 | site | p2p | 2001:db8:42:1::100/120 | 256 |
| IPv6 | site | p2p | 2001:db8:42:1::200/119 | 512 |
| IPv6 | site | p2p | 2001:db8:42:1::400/118 | 1024 |
| IPv6 | site | p2p | 2001:db8:42:1::800/117 | 2048 |
| IPv6 | site | p2p | 2001:db8:42:1::1000/116 | 4096 |
| IPv6 | site | p2p | 2001:db8:42:1::2000/115 | 8192 |
| IPv6 | site | p2p | 2001:db8:42:1::4000/114 | 16384 |
| IPv6 | site | p2p | 2001:db8:42:1::8000/113 | 32768 |
| IPv6 | site | p2p | 2001:db8:42:1::1:0/112 | 65536 |
| IPv6 | site | p2p | 2001:db8:42:1::2:0/111 | 131072 |
| IPv6 | site | p2p | 2001:db8:42:1::4:0/110 | 262144 |
| IPv6 | site | p2p | 2001:db8:42:1::8:0/109 | 524288 |
| IPv6 | site | p2p | 2001:db8:42:1::10:0/108 | 1048576 |
| IPv6 | site | p2p | 2001:db8:42:1::20:0/107 | 2097152 |
| IPv6 | site | p2p | 2001:db8:42:1::40:0/106 | 4194304 |
| IPv6 | site | p2p | 2001:db8:42:1::80:0/105 | 8388608 |
| IPv6 | site | p2p | 2001:db8:42:1::100:0/104 | 16777216 |
| IPv6 | site | p2p | 2001:db8:42:1::200:0/103 | 33554432 |
| IPv6 | site | p2p | 2001:db8:42:1::400:0/102 | 67108864 |
| IPv6 | site | p2p | 2001:db8:42:1::800:0/101 | 134217728 |
| IPv6 | site | p2p | 2001:db8:42:1::1000:0/100 | 268435456 |
| IPv6 | site | p2p | 2001:db8:42:1::2000:0/99 | 536870912 |
| IPv6 | site | p2p | 2001:db8:42:1::4000:0/98 | 1073741824 |
| IPv6 | site | p2p | 2001:db8:42:1::8000:0/97 | 2147483648 |
| IPv6 | site | p2p | 2001:db8:42:1:0:1::/96 | 4294967296 |
| IPv6 | site | p2p | 2001:db8:42:1:0:2::/95 | 8589934592 |
| IPv6 | site | p2p | 2001:db8:42:1:0:4::/94 | 17179869184 |
| IPv6 | site | p2p | 2001:db8:42:1:0:8::/93 | 34359738368 |
| IPv6 | site | p2p | 2001:db8:42:1:0:10::/92 | 68719476736 |
| IPv6 | site | p2p | 2001:db8:42:1:0:20::/91 | 137438953472 |
| IPv6 | site | p2p | 2001:db8:42:1:0:40::/90 | 274877906944 |
| IPv6 | site | p2p | 2001:db8:42:1:0:80::/89 | 549755813888 |
| IPv6 | site | p2p | 2001:db8:42:1:0:100::/88 | 1099511627776 |
| IPv6 | site | p2p | 2001:db8:42:1:0:200::/87 | 2199023255552 |
| IPv6 | site | p2p | 2001:db8:42:1:0:400::/86 | 4398046511104 |
| IPv6 | site | p2p | 2001:db8:42:1:0:800::/85 | 8796093022208 |
| IPv6 | site | p2p | 2001:db8:42:1:0:1000::/84 | 17592186044416 |
| IPv6 | site | p2p | 2001:db8:42:1:0:2000::/83 | 35184372088832 |
| IPv6 | site | p2p | 2001:db8:42:1:0:4000::/82 | 70368744177664 |
| IPv6 | site | p2p | 2001:db8:42:1:0:8000::/81 | 140737488355328 |
| IPv6 | site | p2p | 2001:db8:42:1:1::/80 | 281474976710656 |
| IPv6 | site | p2p | 2001:db8:42:1:2::/79 | 562949953421312 |
| IPv6 | site | p2p | 2001:db8:42:1:4::/78 | 1125899906842624 |
| IPv6 | site | p2p | 2001:db8:42:1:8::/77 | 2251799813685248 |
| IPv6 | site | p2p | 2001:db8:42:1:10::/76 | 4503599627370496 |
| IPv6 | site | p2p | 2001:db8:42:1:20::/75 | 9007199254740992 |
| IPv6 | site | p2p | 2001:db8:42:1:40::/74 | 18014398509481984 |
| IPv6 | site | p2p | 2001:db8:42:1:80::/73 | 36028797018963968 |
| IPv6 | site | p2p | 2001:db8:42:1:100::/72 | 72057594037927936 |
| IPv6 | site | p2p | 2001:db8:42:1:200::/71 | 144115188075855872 |
| IPv6 | site | p2p | 2001:db8:42:1:400::/70 | 288230376151711744 |
| IPv6 | site | p2p | 2001:db8:42:1:800::/69 | 576460752303423488 |
| IPv6 | site | p2p | 2001:db8:42:1:1000::/68 | 1152921504606846976 |
| IPv6 | site | p2p | 2001:db8:42:1:2000::/67 | 2305843009213693952 |
| IPv6 | site | p2p | 2001:db8:42:1:4000::/66 | 4611686018427387904 |
| IPv6 | site | p2p | 2001:db8:42:1:8000::/65 | 9223372036854775808 |
| IPv6 | site | loopback | 2001:db8:42:2::1/128 | 1 |
| IPv6 | site | loopback | 2001:db8:42:2::2/127 | 2 |
| IPv6 | site | loopback | 2001:db8:42:2::4/126 | 4 |
| IPv6 | site | loopback | 2001:db8:42:2::8/125 | 8 |
| IPv6 | site | loopback | 2001:db8:42:2::10/124 | 16 |
| IPv6 | site | loopback | 2001:db8:42:2::20/123 | 32 |
| IPv6 | site | loopback | 2001:db8:42:2::40/122 | 64 |
| IPv6 | site | loopback | 2001:db8:42:2::80/121 | 128 |
| IPv6 | site | loopback | 2001:db8:42:2::100/120 | 256 |
| IPv6 | site | loopback | 2001:db8:42:2::200/119 | 512 |
| IPv6 | site | loopback | 2001:db8:42:2::400/118 | 1024 |
| IPv6 | site | loopback | 2001:db8:42:2::800/117 | 2048 |
| IPv6 | site | loopback | 2001:db8:42:2::1000/116 | 4096 |
| IPv6 | site | loopback | 2001:db8:42:2::2000/115 | 8192 |
| IPv6 | site | loopback | 2001:db8:42:2::4000/114 | 16384 |
| IPv6 | site | loopback | 2001:db8:42:2::8000/113 | 32768 |
| IPv6 | site | loopback | 2001:db8:42:2::1:0/112 | 65536 |
| IPv6 | site | loopback | 2001:db8:42:2::2:0/111 | 131072 |
| IPv6 | site | loopback | 2001:db8:42:2::4:0/110 | 262144 |
| IPv6 | site | loopback | 2001:db8:42:2::8:0/109 | 524288 |
| IPv6 | site | loopback | 2001:db8:42:2::10:0/108 | 1048576 |
| IPv6 | site | loopback | 2001:db8:42:2::20:0/107 | 2097152 |
| IPv6 | site | loopback | 2001:db8:42:2::40:0/106 | 4194304 |
| IPv6 | site | loopback | 2001:db8:42:2::80:0/105 | 8388608 |
| IPv6 | site | loopback | 2001:db8:42:2::100:0/104 | 16777216 |
| IPv6 | site | loopback | 2001:db8:42:2::200:0/103 | 33554432 |
| IPv6 | site | loopback | 2001:db8:42:2::400:0/102 | 67108864 |
| IPv6 | site | loopback | 2001:db8:42:2::800:0/101 | 134217728 |
| IPv6 | site | loopback | 2001:db8:42:2::1000:0/100 | 268435456 |
| IPv6 | site | loopback | 2001:db8:42:2::2000:0/99 | 536870912 |
| IPv6 | site | loopback | 2001:db8:42:2::4000:0/98 | 1073741824 |
| IPv6 | site | loopback | 2001:db8:42:2::8000:0/97 | 2147483648 |
| IPv6 | site | loopback | 2001:db8:42:2:0:1::/96 | 4294967296 |
| IPv6 | site | loopback | 2001:db8:42:2:0:2::/95 | 8589934592 |
| IPv6 | site | loopback | 2001:db8:42:2:0:4::/94 | 17179869184 |
| IPv6 | site | loopback | 2001:db8:42:2:0:8::/93 | 34359738368 |
| IPv6 | site | loopback | 2001:db8:42:2:0:10::/92 | 68719476736 |
| IPv6 | site | loopback | 2001:db8:42:2:0:20::/91 | 137438953472 |
| IPv6 | site | loopback | 2001:db8:42:2:0:40::/90 | 274877906944 |
| IPv6 | site | loopback | 2001:db8:42:2:0:80::/89 | 549755813888 |
| IPv6 | site | loopback | 2001:db8:42:2:0:100::/88 | 1099511627776 |
| IPv6 | site | loopback | 2001:db8:42:2:0:200::/87 | 2199023255552 |
| IPv6 | site | loopback | 2001:db8:42:2:0:400::/86 | 4398046511104 |
| IPv6 | site | loopback | 2001:db8:42:2:0:800::/85 | 8796093022208 |
| IPv6 | site | loopback | 2001:db8:42:2:0:1000::/84 | 17592186044416 |
| IPv6 | site | loopback | 2001:db8:42:2:0:2000::/83 | 35184372088832 |
| IPv6 | site | loopback | 2001:db8:42:2:0:4000::/82 | 70368744177664 |
| IPv6 | site | loopback | 2001:db8:42:2:0:8000::/81 | 140737488355328 |
| IPv6 | site | loopback | 2001:db8:42:2:1::/80 | 281474976710656 |
| IPv6 | site | loopback | 2001:db8:42:2:2::/79 | 562949953421312 |
| IPv6 | site | loopback | 2001:db8:42:2:4::/78 | 1125899906842624 |
| IPv6 | site | loopback | 2001:db8:42:2:8::/77 | 2251799813685248 |
| IPv6 | site | loopback | 2001:db8:42:2:10::/76 | 4503599627370496 |
| IPv6 | site | loopback | 2001:db8:42:2:20::/75 | 9007199254740992 |
| IPv6 | site | loopback | 2001:db8:42:2:40::/74 | 18014398509481984 |
| IPv6 | site | loopback | 2001:db8:42:2:80::/73 | 36028797018963968 |
| IPv6 | site | loopback | 2001:db8:42:2:100::/72 | 72057594037927936 |
| IPv6 | site | loopback | 2001:db8:42:2:200::/71 | 144115188075855872 |
| IPv6 | site | loopback | 2001:db8:42:2:400::/70 | 288230376151711744 |
| IPv6 | site | loopback | 2001:db8:42:2:800::/69 | 576460752303423488 |
| IPv6 | site | loopback | 2001:db8:42:2:1000::/68 | 1152921504606846976 |
| IPv6 | site | loopback | 2001:db8:42:2:2000::/67 | 2305843009213693952 |
| IPv6 | site | loopback | 2001:db8:42:2:4000::/66 | 4611686018427387904 |
| IPv6 | site | loopback | 2001:db8:42:2:8000::/65 | 9223372036854775808 |
| IPv6 | hall | building | 2001:db8:42:106::/63 | 36893488147419103232 |
| IPv6 | hall | building | 2001:db8:42:108::/61 | 147573952589676412928 |
| IPv6 | hall | building | 2001:db8:42:110::/60 | 295147905179352825856 |
| IPv6 | hall | building | 2001:db8:42:120::/59 | 590295810358705651712 |
| IPv6 | hall | building | 2001:db8:42:140::/58 | 1180591620717411303424 |
| IPv6 | hall | building | 2001:db8:42:180::/57 | 2361183241434822606848 |
| IPv6 | office | building | 2001:db8:42:201::/64 | 18446744073709551616 |
| IPv6 | office | building | 2001:db8:42:202::/63 | 36893488147419103232 |
| IPv6 | office | building | 2001:db8:42:204::/62 | 73786976294838206464 |
| IPv6 | office | building | 2001:db8:42:208::/61 | 147573952589676412928 |
| IPv6 | office | building | 2001:db8:42:210::/60 | 295147905179352825856 |
| IPv6 | office | building | 2001:db8:42:220::/59 | 590295810358705651712 |
| IPv6 | office | building | 2001:db8:42:240::/58 | 1180591620717411303424 |
| IPv6 | office | building | 2001:db8:42:280::/57 | 2361183241434822606848 |

## Validation

| Level | Code | Node ID | Description |
| --- | --- | --- | --- |
| Information | pool\_fragmentation | — | INFO \[pool\_fragmentation\] \[project\]: Free space in the pool and its continuity. free addresses: 3072; largest free prefix: /21; continuity: 2/3 |
| Information | summary\_route | site | INFO \[summary\_route\] \[site: Lokalizacja zboru\]: Summary block of the parent. network: 10.42.0.0/22 |
| Information | pool\_fragmentation | site | INFO \[pool\_fragmentation\] \[site: Lokalizacja zboru\]: Free space in the pool and its continuity. free addresses: 448; largest free prefix: /24; continuity: 4/7 |
| Information | summary\_route | hall | INFO \[summary\_route\] \[hall: Sala główna\]: Summary block of the parent. network: 10.42.0.0/23 |
| Information | pool\_fragmentation | hall | INFO \[pool\_fragmentation\] \[hall: Sala główna\]: Free space in the pool and its continuity. free addresses: 224; largest free prefix: /25; continuity: 4/7 |
| Warning | high\_segment\_utilization | audio | WARNING \[high\_segment\_utilization\] \[audio: Dźwięk\]: The demand exceeds 85% of the segment capacity. required usable: 30; usable capacity: 30 |
| Warning | high\_segment\_utilization | mgmt | WARNING \[high\_segment\_utilization\] \[mgmt: Zarządzanie\]: The demand exceeds 85% of the segment capacity. required usable: 14; usable capacity: 14 |
| Information | summary\_route | office | INFO \[summary\_route\] \[office: Biuro\]: Summary block of the parent. network: 10.42.2.0/26 |
| Information | pool\_fragmentation | office | INFO \[pool\_fragmentation\] \[office: Biuro\]: Free space in the pool and its continuity. free addresses: 29; largest free prefix: /28; continuity: 16/29 |
| Warning | high\_segment\_utilization | staff | WARNING \[high\_segment\_utilization\] \[staff: Stanowiska biurowe\]: The demand exceeds 85% of the segment capacity. required usable: 26; usable capacity: 30 |

The report was calculated from the project input data. To keep addresses when expanding, save a frozen JSON project with the freeze command. CSV and Markdown are documentation; use JSON to import again.
