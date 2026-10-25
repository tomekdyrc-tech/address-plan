# Address Plan - konfiguracja startowa: Syntetyczna siec AV i biura
# Status planu: KOMPLETNY. Pula IPv4: 10.42.0.0/20.
# Szkic do przegladu przed wdrozeniem: sprawdz nazwy interfejsow, trunki VLAN, DHCP i zabezpieczenia urzadzenia.
# Segmenty bez VLAN-u i lacza P2P sa zakomentowane; uzupelnij <INTERFACE>.
# Interfejsy VLAN powstaja na interfejsie bridge; dopasuj go do trunku.
#
# ===== Lokalizacja zboru / Sala glowna =====
/interface vlan add name=vlan10-Dzwiek vlan-id=10 interface=bridge comment="Dzwiek"
/ip address add address=10.42.0.193/27 interface=vlan10-Dzwiek comment="Dzwiek"
/ipv6 address add address=2001:db8:42:100::1/64 advertise=yes interface=vlan10-Dzwiek comment="Dzwiek"
/ip pool add name=pool-vlan10-Dzwiek ranges=10.42.0.198-10.42.0.222
/ip dhcp-server add name=dhcp-vlan10-Dzwiek address-pool=pool-vlan10-Dzwiek interface=vlan10-Dzwiek
/ip dhcp-server network add address=10.42.0.192/27 gateway=10.42.0.193 comment="Dzwiek"
/interface vlan add name=vlan20-Obraz vlan-id=20 interface=bridge comment="Obraz"
/ip address add address=10.42.0.225/27 interface=vlan20-Obraz comment="Obraz"
/ipv6 address add address=2001:db8:42:101::1/64 advertise=yes interface=vlan20-Obraz comment="Obraz"
/ip pool add name=pool-vlan20-Obraz ranges=10.42.0.226-10.42.0.254
/ip dhcp-server add name=dhcp-vlan20-Obraz address-pool=pool-vlan20-Obraz interface=vlan20-Obraz
/ip dhcp-server network add address=10.42.0.224/27 gateway=10.42.0.225 comment="Obraz"
/interface vlan add name=vlan30-Prezentacja vlan-id=30 interface=bridge comment="Prezentacja"
/ip address add address=10.42.1.1/28 interface=vlan30-Prezentacja comment="Prezentacja"
/ipv6 address add address=2001:db8:42:102::1/64 advertise=yes interface=vlan30-Prezentacja comment="Prezentacja"
/ip pool add name=pool-vlan30-Prezentacja ranges=10.42.1.2-10.42.1.14
/ip dhcp-server add name=dhcp-vlan30-Prezentacja address-pool=pool-vlan30-Prezentacja interface=vlan30-Prezentacja
/ip dhcp-server network add address=10.42.1.0/28 gateway=10.42.1.1 comment="Prezentacja"
/interface vlan add name=vlan40-Monitoring vlan-id=40 interface=bridge comment="Monitoring"
/ip address add address=10.42.0.190/26 interface=vlan40-Monitoring comment="Monitoring"
/ipv6 address add address=2001:db8:42:103::1/64 advertise=yes interface=vlan40-Monitoring comment="Monitoring"
/ip pool add name=pool-vlan40-Monitoring ranges=10.42.0.133-10.42.0.189
/ip dhcp-server add name=dhcp-vlan40-Monitoring address-pool=pool-vlan40-Monitoring interface=vlan40-Monitoring
/ip dhcp-server network add address=10.42.0.128/26 gateway=10.42.0.190 comment="Monitoring"
/interface vlan add name=vlan50-Goscie vlan-id=50 interface=bridge comment="Goscie"
/ip address add address=10.42.0.1/25 interface=vlan50-Goscie comment="Goscie"
/ipv6 address add address=2001:db8:42:104::1/64 advertise=yes interface=vlan50-Goscie comment="Goscie"
/ip pool add name=pool-vlan50-Goscie ranges=10.42.0.2-10.42.0.126
/ip dhcp-server add name=dhcp-vlan50-Goscie address-pool=pool-vlan50-Goscie interface=vlan50-Goscie
/ip dhcp-server network add address=10.42.0.0/25 gateway=10.42.0.1 comment="Goscie"
/interface vlan add name=vlan60-Zarzadzanie vlan-id=60 interface=bridge comment="Zarzadzanie"
/ip address add address=10.42.1.17/28 interface=vlan60-Zarzadzanie comment="Zarzadzanie"
/ipv6 address add address=2001:db8:42:105::1/64 advertise=yes interface=vlan60-Zarzadzanie comment="Zarzadzanie"
#
# ===== Lokalizacja zboru / Biuro =====
# Lacze P2P Lacze router-biuro: przypisz interfejs fizyczny.
# /ip address add address=10.42.2.32/31 interface=<INTERFACE> comment="Lacze router-biuro"
# /ipv6 address add address=2001:db8:42:1::/127 advertise=no interface=<INTERFACE> comment="Lacze router-biuro"
/interface bridge add name=lo0 comment="Loopback routera"
/ip address add address=10.42.2.34/32 interface=lo0 comment="Loopback routera"
/ipv6 address add address=2001:db8:42:2::/128 advertise=no interface=lo0 comment="Loopback routera"
/interface vlan add name=vlan70-Stanowiska-biurowe vlan-id=70 interface=bridge comment="Stanowiska biurowe"
/ip address add address=10.42.2.1/27 interface=vlan70-Stanowiska-biurowe comment="Stanowiska biurowe"
/ipv6 address add address=2001:db8:42:200::1/64 advertise=yes interface=vlan70-Stanowiska-biurowe comment="Stanowiska biurowe"
/ip pool add name=pool-vlan70-Stanowiska-biurow ranges=10.42.2.2-10.42.2.30
/ip dhcp-server add name=dhcp-vlan70-Stanowiska-biurow address-pool=pool-vlan70-Stanowiska-biurow interface=vlan70-Stanowiska-biurowe
/ip dhcp-server network add address=10.42.2.0/27 gateway=10.42.2.1 comment="Stanowiska biurowe"
