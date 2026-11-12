[![GitHub release](https://img.shields.io/github/release/FMainz/IPFire-API?include_prereleases=&sort=semver&color=blue)](https://github.com/FMainz/IPFire-API/releases/)
![Letzter Commit](https://img.shields.io/github/last-commit/FMainz/IPFire-API)
[![Lizenz: GPL-3.0-only](https://img.shields.io/badge/License-GPL--3.0--only-blue.svg)](https://github.com/FMainz/IPFire-API/blob/main/LICENSE)
![API-Downloads](https://img.shields.io/github/downloads/FMainz/IPFire-API/total?style=flat-square&color=red&label=API-Downloads)
[![Stars](https://img.shields.io/github/stars/FMainz/IPFire-API)](https://github.com/FMainz/IPFire-API/stargazers)
# IPFire-API

Diese Dokumentation ist auf 🇩🇪 Deutsch und 🇬🇧 [Englisch](README.md) verfügbar.

IPFire-API ist eine Schnittstelle für IPFire, die ausgewählte System-, Netzwerk-, Dienst-, Add-on-, USV-, Traffic- und Internetverbindungsdaten im JSON-Format bereitstellt. Außerdem bietet sie authentifizierte Steuerungsmöglichkeiten: Die RED-Verbindung kann online oder offline geschaltet, die Installation verfügbarer Updates aus der Ferne gestartet und ein Neustart angefordert werden, wenn IPFire ihn als erforderlich meldet.

Die API wurde ursprünglich für die Home-Assistant-Integration [HA-IPFire](https://github.com/FMainz/HA-IPFire) entwickelt und wird inzwischen als separates Projekt gepflegt, damit auch andere Integrationen und Clients sie nutzen können.

Die Installation zusätzlicher Software auf einer Firewall ist immer mit einem gewissen Risiko verbunden, auch bei dieser API. Wenn du die API nicht benötigst, solltest du sie nicht installieren.

## Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Installation](#installation)
- [API-Zugriff](#api-zugriff)
  - [Verbindungssteuerung](#verbindungssteuerung)
  - [Update-Installation](#update-installation)
  - [Neustart](#neustart)
  - [Backup-Management](#backup-management)
  - [Systemparameter](#systemparameter)
    - [CPU](#cpu)
    - [Arbeitsspeicher](#arbeitsspeicher)
    - [Festplatte](#festplatte)
    - [SMART](#smart)
  - [Netzwerk](#netzwerk)
    - [VLANs](#vlans)
    - [Nachbartabelle](#nachbartabelle)
    - [Routingtabellen](#routingtabellen)
  - [DHCP-Leases](#dhcp-leases)
  - [Dienste](#dienste)
  - [Add-ons](#add-ons)
    - [USV](#usv)
  - [Zertifikate](#zertifikate)
  - [Updates](#updates)
- [Sicherheit](#sicherheit)
- [Lizenz](#lizenz)

## Funktionen

- Informationen zu System, CPU, Arbeitsspeicher, Festplatte, SMART, USV und Zertifikaten
- Status der Netzwerkschnittstellen und IPFire-Dienste
- Status unterstützter Add-ons
- Verfügbare IPFire-Core- und Paket-Updates sowie authentifizierter Start des Pakfire-Upgrade
- Authentifizierter Neustart des Routers, wenn IPFire ihn als erforderlich meldet
- System- und Add-on-Backups aus der Ferne erstellen, auflisten, herunterladen und löschen; ISO-Backup-Erstellung starten
- Traffic-Zähler der RED-Schnittstelle
- Status und Details der Internetverbindung
- Verbinden und Trennen über IPFires natives `redctrl`
- JSON-Antworten mit API-Version und Script-Revision

## Installation

Kopiere `cgi-bin/api.cgi` in das CGI-Verzeichnis des IPFire-Webservers:

```text
/srv/web/ipfire/cgi-bin/api.cgi
```

Setze Eigentümer und Ausführungsrechte:

```sh
chown root:root /srv/web/ipfire/cgi-bin/api.cgi
chmod 755 /srv/web/ipfire/cgi-bin/api.cgi
```

Das CGI verwendet die bestehende Authentifizierung der IPFire-Weboberfläche. Das Script richtet keine separaten API-Zugangsdaten ein.

## API-Zugriff

Die API ist unter folgender Adresse erreichbar:

```text
https://<ipfire-host>:444/cgi-bin/api.cgi
```

Eine authentifizierte `GET`-Anfrage liefert die aktuellen Daten als JSON. Die Antwort verwendet API-Version `1`, gibt die Revision des `api.cgi`-Scripts unter `api_revision` aus und enthält die Bereiche `system`, `network`, `dhcp`, `updates`, `services`, `ups`, `traffic`, `connection` und `certificates`. `api_version` bezeichnet die Version der JSON-Schnittstelle; `api_revision` entspricht der Script-Version im Dateikopf. Der Bereich `addons` wird nur ausgegeben, wenn unterstützte Add-ons mit Diensten installiert sind. Nicht verfügbare Messwerte werden als `null` ausgegeben. Nicht erkannte Add-on- und Dienststatus erscheinen als `false`. Die Backup-Verzeichnisse werden nur durchsucht, wenn die Anfrage `?backup=1` enthält; dann wird auch `backups` ausgegeben.

Alle authentifizierten `POST`-Aktionen benötigen den Header `X-IPFire-API: 1`. Aus Gründen der Abwärtskompatibilität wird auch der bisherige Header `X-HA-IPFire-API: 1` akzeptiert.

### Verbindungssteuerung

Verbindungsaktionen verwenden authentifizierte `POST`-Anfragen mit einem Formularkörper und dem Header `X-IPFire-API: 1`.
Als Beispiel der Aufruf zum Verbindungsaufbau mittels `curl`:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=connect' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Zum Trennen der Verbindung ersetze `action=connect` durch `action=disconnect`. `curl` fragt das Passwort der Weboberfläche interaktiv ab. Ersetze die Platzhalter durch den Benutzernamen der Weboberfläche und den Hostnamen von IPFire. Bei einem selbstsignierten IPFire-Zertifikat muss `curl` diesem Zertifikat vertrauen, zum Beispiel mit `--cacert /pfad/zum/ipfire-zertifikat.pem`.

Das CGI ruft IPFires natives `/usr/local/bin/redctrl` auf. `connect` baut die Verbindung auf oder verbindet sie neu; `disconnect` trennt sie. Andere Methoden, fehlende Header und nicht unterstützte Aktionen werden abgewiesen.

### Update-Installation

Eine authentifizierte `POST`-Anfrage mit dem Header `X-IPFire-API: 1` kann die Installation aller von Pakfire aktuell gelisteten Updates starten.
Beispielumsetzung mittels `curl`:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=upgrade' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Die API startet denselben nicht interaktiven Pakfire-Upgrade-Prozess wie die IPFire-Weboberfläche. Die Anfrage kehrt sofort mit `result: "accepted"` zurück. Den Status `running`, `completed` oder `failed` liefert danach `updates.operation` in den `GET`-Antworten. Die API weist die Anfrage zurück, wenn keine Updates verfügbar sind oder bereits ein von der API gestartetes Upgrade läuft. Es werden immer alle verfügbaren Updates gemeinsam installiert; einzelne Pakete lassen sich damit nicht auswählen. **Sende diese Anfrage nur, wenn du bereit bist, alle derzeit von Pakfire gelisteten Updates zu installieren.**

Das Objekt `updates.operation` ist in jeder `GET`-Antwort enthalten. Der folgende Aufruf gibt die vollständige JSON-Antwort aus; der Status des Vorgangs steht unter `updates.operation`:

```sh
curl --user '<webgui-benutzer>' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Wenn `jq` installiert ist, lässt sich die Antwort filtern, sodass nur `updates.operation` ausgegeben wird. Unter Debian Trixie ist `jq` im [gleichnamigen Paket](https://packages.debian.org/de/trixie/jq) enthalten und kann mit `sudo apt install jq` installiert werden:

```sh
curl --user '<webgui-benutzer>' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi' \
  | jq '.updates.operation'
```

### Neustart

Eine authentifizierte `POST`-Anfrage mit `action=reboot` fordert IPFire zum Neustart auf. Die API akzeptiert diese Aktion nur, wenn `/var/run/need_reboot` vorhanden ist, und verwendet IPFires nativen Helfer `/usr/local/bin/ipfirereboot`. Der Router startet kurz nach der API-Antwort `result: "accepted"` neu. Die Verbindung zu Home Assistant wird unterbrochen, bis IPFire wieder erreichbar ist.

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=reboot' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

### Backup-Management

Das Objekt `backups` wird nur bei einer authentifizierten `GET`-Anfrage mit `?backup=1` ausgegeben. So werden die Backup-Verzeichnisse bei regulären API-Abfragen nicht durchsucht. Es enthält ein Array `system` mit vollständigen System-Backups (`.ipf`) aus `/var/ipfire/backup`, das Neueste zuerst. Jeder Eintrag enthält den Dateinamen, die Dateigröße in Byte und den Änderungszeitpunkt als Unix-Zeitstempel. `addons_available` führt die Add-ons auf, für die IPFire eine Backup-Funktion bereitstellt, auch wenn noch keine Sicherungsdatei vorhanden ist. Wenn Add-on-Backup-Dateien unter `/var/ipfire/backup/addons/backup` vorhanden sind, wird zusätzlich das Array `addons` mit Dateiinformationen und Add-on-Namen ausgegeben. Add-on-Backups enthalten Konfigurationsdateien, nicht die installierten Add-on-Pakete. Ein leeres Array `system` bedeutet, dass keine System-Backups vorhanden sind; `null` bedeutet, dass das System-Backup-Verzeichnis nicht gelesen werden konnte. Das Objekt `operation` zeigt den letzten über die API gestarteten Erstellungs-, Lösch- oder ISO-Erstellungsvorgang an. IPFire erstellt ISOs mit seiner nativen Backup-Methode lokal auf dem Router. Die [offizielle IPFire-Backup-Dokumentation](https://www.ipfire.org/docs/configuration/system/backup) beschreibt keinen HTTP/API-Zugriff zum Auflisten oder Herunterladen der erzeugten ISO-Dateien. Verwende `https://<ipfire-host>:444/cgi-bin/api.cgi?backup=1`, um Backups aufzulisten oder `backups.operation` abzufragen.

Zum Erstellen eines System-Backups sende eine authentifizierte `POST`-Anfrage mit `action=create_backup`, `type=system` und `logs=include` oder `logs=exclude`. Die API startet den Vorgang im Hintergrund und antwortet mit `result: "accepted"`. Frage anschließend `backups.operation` in `GET`-Antworten mit `?backup=1` ab, bis der Status `completed` oder `failed` lautet. Das Einbeziehen der Logs kann deutlich länger dauern. Beispiel ohne Logs:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=create_backup' \
  --data-urlencode 'type=system' \
  --data-urlencode 'logs=exclude' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Für ein Add-on-Konfigurations-Backup verwende `type=addon` und den Paketnamen des Add-ons:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=create_backup' \
  --data-urlencode 'type=addon' \
  --data-urlencode 'addon=wio' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Für ein angepasstes Installations-ISO mit dem aktuellen System-Backup verwende `type=iso`. IPFire lädt das Basis-ISO bei Bedarf aus dem Internet herunter. Die Erstellung kann lange dauern und benötigt eine Internetverbindung sowie ausreichend freien Speicherplatz. Frage `backups.operation` über `GET ...?backup=1` ab. Der Status bleibt `running`, bis IPFire die ISO-Erstellung abgeschlossen hat:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=create_backup' \
  --data-urlencode 'type=iso' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Zum Herunterladen eines gelisteten Backups sende eine authentifizierte `POST`-Anfrage mit `action=download_backup`, dem passenden `type` (`system` oder `addon`) und dem exakten `filename`. Die Antwort enthält direkt die Datei; mit `curl --output` wird sie gespeichert:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=download_backup' \
  --data-urlencode 'type=system' \
  --data-urlencode 'filename=2026-11-12-1200.ipf' \
  --output '2026-11-12-1200.ipf' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

Zum Löschen eines gelisteten Backups sende eine authentifizierte `POST`-Anfrage mit `action=delete_backup`, dem passenden `type` (`system` oder `addon`) und dem exakten `filename`. Bei Erfolg gibt die API JSON mit `result: "ok"` zurück; `backups.operation` zeigt anschließend den abgeschlossenen Löschvorgang samt Typ und Dateiname an. Das Löschen ist endgültig; prüfe Typ und Dateiname vor dem Senden der Anfrage:

```sh
curl --user '<webgui-benutzer>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=delete_backup' \
  --data-urlencode 'type=system' \
  --data-urlencode 'filename=2026-11-08-1724.ipf' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

### Systemparameter

Der Abschnitt `system` stellt folgende Informationen bereit:

| Parameter | Beschreibung |
| --- | --- |
| `version` | IPFire-Version |
| `pakfire_version` | Pakfire-Version |
| `kernel_version` | Linux-Kernel-Version |
| `architecture` | Systemarchitektur |
| `cpu_model` | CPU-Modell |
| `cpu_count` | Anzahl der CPU-Kerne |
| `model` | Systemmodell |
| `vendor` | Systemhersteller |
| `virtual` | Gibt an, ob das System virtualisiert ist |
| `core_update` | Gibt an, ob ein Core-Update verfügbar ist |
| `package_updates` | Anzahl der verfügbaren Paket-Updates |
| `reboot_required` | Gibt an, ob IPFire nach einem Update einen Neustart als erforderlich markiert hat |
| `uptime` | Betriebszeit des Systems in Sekunden |

#### CPU

| Parameter | Beschreibung |
| --- | --- |
| `total` | Kumulierte CPU-Gesamtzeit |
| `idle` | Kumulierte CPU-Leerlaufzeit |

#### Arbeitsspeicher

| Parameter | Beschreibung |
| --- | --- |
| `total` | Gesamter physischer Arbeitsspeicher in Byte |
| `available` | Verfügbarer Arbeitsspeicher in Byte |
| `free` | Freier Arbeitsspeicher in Byte |
| `buffers` | Für Puffer verwendeter Arbeitsspeicher in Byte |
| `cached` | Für den Cache verwendeter Arbeitsspeicher in Byte |

#### Festplatte

Die Speicherplatzinformationen des Root-Dateisystems werden unter `disk.root` bereitgestellt.

| Parameter | Beschreibung |
| --- | --- |
| `total` | Gesamter Speicherplatz in Byte |
| `used` | Belegter Speicherplatz in Byte |
| `available` | Verfügbarer Speicherplatz in Byte |
| `use_percent` | Festplattenauslastung in Prozent |

Die I/O-Statistiken für das Gerät `sda` werden unter `disk.sda` bereitgestellt.

| Parameter | Beschreibung |
| --- | --- |
| `reads` | Anzahl abgeschlossener Lesevorgänge |
| `sectors_read` | Anzahl gelesener Sektoren |
| `writes` | Anzahl abgeschlossener Schreibvorgänge |
| `sectors_written` | Anzahl geschriebener Sektoren |
| `io_in_progress` | Anzahl der aktuell laufenden I/O-Vorgänge |
| `io_time` | Für I/O-Vorgänge aufgewendete Zeit |

#### SMART

SMART-Informationen werden für die Systemfestplatte bereitgestellt. Das Ergebnis wird eine Stunde zwischengespeichert, damit die Festplatte nicht bei jeder API-Anfrage erneut abgefragt wird. Nach Ablauf des Caches aktualisiert die nächste API-Anfrage die Daten. Es gibt keine Aktualisierung im Hintergrund; ohne weitere Anfrage bleiben die angezeigten Werte daher unverändert.

| Parameter | Beschreibung |
| --- | --- |
| `power_on_hours` | Betriebsstunden der Festplatte |
| `remaining_lifetime` | Verbleibende Lebensdauer der Festplatte in Prozent |
| `health` | SMART-Gesundheitsstatus |
| `errors` | Anzahl der SMART-Fehler |
| `uncorrectable_errors` | Anzahl nicht korrigierbarer Fehler |
| `power_cycles` | Anzahl der Einschaltzyklen |
| `temperature` | Festplattentemperatur |

### Netzwerk

Der Abschnitt `network` meldet die konfigurierten IPFire-Netzwerkzonen und Informationen zu den zugeordneten Geräten. Die booleschen Zonenwerte zeigen an, ob eine Zone im IPFire-Hardwareprofil vorhanden ist. Sie geben nicht den aktuellen physischen Linkstatus an.

| Parameter | Beschreibung |
| --- | --- |
| `blue` | Gibt an, ob die BLUE-Zone im Hardwareprofil vorhanden ist |
| `green` | Gibt an, ob die GREEN-Zone im Hardwareprofil vorhanden ist |
| `orange` | Gibt an, ob die ORANGE-Zone im Hardwareprofil vorhanden ist |
| `red` | Gibt an, ob die RED-Zone im Hardwareprofil vorhanden ist |

Die Werte sind boolesch:

* `true` – die Zone ist vorhanden
* `false` – die Zone ist nicht vorhanden

Das Objekt `interfaces` enthält für jede konfigurierte Zone Daten aus den IPFire-Schnittstelleneinstellungen, den Linux-Schnittstellenzählern und von `ethtool`:

| Parameter | Beschreibung |
| --- | --- |
| `device` | Der Linux-Netzwerkname des der Zone zugeordneten Geräts |
| `rx_bytes` | Kumulierte Anzahl der von der Schnittstelle empfangenen Bytes |
| `tx_bytes` | Kumulierte Anzahl der von der Schnittstelle gesendeten Bytes |
| `driver` | Name des Netzwerktreibers |
| `driver_version` | Von `ethtool` gemeldete Treiberversion |
| `firmware_version` | Von `ethtool` gemeldete Firmwareversion |
| `supported_link_modes` | Vom Gerät und Treiber unterstützte Verbindungsmodi |
| `max_supported_speed_mbps` | Höchste Geschwindigkeit der unterstützten Verbindungsmodi |
| `advertised_link_modes` | Für die automatische Aushandlung angebotene Verbindungsmodi |
| `link_partner_advertised_link_modes` | Von der Gegenstelle angebotene Modi, falls gemeldet |
| `supports_auto_negotiation` | Gibt an, ob das Gerät automatische Aushandlung unterstützt |
| `auto_negotiation` | Gibt an, ob automatische Aushandlung aktiviert ist |
| `speed_mbps` | Aktuell ausgehandelte Verbindungsgeschwindigkeit in Mbit/s |
| `duplex` | Aktuell ausgehandelter Duplexmodus |
| `link_detected` | Gibt an, ob ein physischer Link erkannt wird |

`rx_bytes` und `tx_bytes` sind kumulative Zähler aus `/sys/class/net/<device>/statistics/`. Clients können durch den Vergleich aufeinanderfolgender Werte die Übertragungsrate berechnen. Der Eintrag einer Zone ist `null`, wenn kein zugeordnetes Gerät vorhanden ist. Existiert das Gerät, aber es besteht kein physischer Link, können unterstützte und angebotene Modi trotzdem verfügbar sein; `speed_mbps` und `duplex` sind dann `null`.

#### VLANs

Das optionale Array `vlans` listet die über IPFires Zonenkonfiguration eingerichteten VLANs auf. Sind keine VLANs konfiguriert, wird das Feld nicht ausgegeben. Jeder Eintrag enthält:

| Parameter | Beschreibung |
| --- | --- |
| `zone` | IPFire-Zone, die das VLAN verwendet |
| `vlan_id` | Konfigurierte VLAN-Kennung |
| `parent_device` | Übergeordnetes Netzwerkgerät, sofern es anhand der konfigurierten Eltern-MAC-Adresse gefunden wird |
| `parent_mac_address` | Von IPFire gespeicherte MAC-Adresse des Eltern-Geräts |
| `zone_device` | Der Zone zugeordnetes Netzwerkgerät |
| `zone_interface_present` | Gibt an, ob das Zonengerät derzeit unter Linux vorhanden ist |
| `mac_address` | Für die VLAN-Schnittstelle konfigurierte MAC-Adresse |

Die API liest diese Angaben aus IPFires Konfigurationsdatei `/var/ipfire/ethernet/vlans`. VLANs, die außerhalb der IPFire-Zonenkonfiguration angelegt wurden, werden hier nicht aufgeführt.

#### Nachbartabelle

Das Array `neighbors` entspricht IPFires Ausgabe von `ip neigh show` und enthält Adresse, Gerät, Link-Layer-Adresse (falls verfügbar) und Neighbor-Status.

#### Routingtabellen

Das Array `routes` enthält die Hauptroutingtabelle. Gibt es Einträge in Routingtabelle 220, werden sie im optionalen Array `ipsec_routes` ausgegeben. Ist diese Tabelle leer, fehlt das Feld vollständig.

### DHCP-Leases

Das Array `dhcp.leases` wird aus `/var/state/dhcp/dhcpd.leases` gelesen, derselben Lease-Datenbank, die auch die IPFire-Weboberfläche verwendet. Es enthält den jeweils letzten Eintrag pro IP-Adresse, einschließlich abgelaufener Leases, mit IP-Adresse, MAC-Adresse, Hostname, Ablaufzeit und Status (aktiv oder abgelaufen). Ein Lease ohne Ablaufzeit wird mit `expires_never: true` gekennzeichnet. Kann die Lease-Datei nicht gelesen werden, ist `dhcp.leases` gleich `null`. Ob der DHCP-Server läuft, steht weiterhin unter `services.dhcp`.

### Dienste

Der Abschnitt `services` stellt den aktuellen Status der von IPFire verwalteten Dienste bereit.

| Parameter | Beschreibung |
| --- | --- |
| `dhcp` | Status des DHCP-Servers |
| `web_server` | Status des IPFire-Webservers |
| `cron` | Status des Cron-Dienstes |
| `dns_resolver` | Status des DNS-Resolvers |
| `logging` | Status des Logging-Dienstes |
| `ntp` | Status des NTP-Dienstes |
| `ssh` | Status des SSH-Dienstes |
| `vpn` | Status des VPN-Dienstes |
| `web_proxy` | Status des Web-Proxy-Dienstes |
| `ips` | Status des Intrusion Prevention Systems (IPS) |
| `ovpn_roadwarrior` | Status des OpenVPN-Roadwarrior-Dienstes |
| `lldp` | Status des LLDP-Dienstes |
| `dbus` | Status des D-Bus-Dienstes |

Die Werte sind boolesch:

* `true` – der Dienst läuft
* `false` – der Dienst läuft nicht

### Add-ons

Der Abschnitt `addons` wird nur ausgegeben, wenn unterstützte IPFire-Add-ons mit Diensten installiert sind. Er stellt deren aktuellen Status bereit. Sind keine solchen Add-ons installiert, fehlt der Abschnitt vollständig. Der Bereich ist für weitere Add-on-Schnittstellen vorgesehen. Beiträge sollten das Add-on, die Quelle des Status und relevante IPFire-Versionsannahmen dokumentieren.

Das folgende Beispiel zeigt, wie der Status eines Add-ons dargestellt wird:

| Parameter | Beschreibung |
| --- | --- |
| `transmission.running` | Gibt an, ob das Transmission-Add-on läuft |

Der Wert ist boolesch:

* `true` – das Add-on läuft
* `false` – das Add-on läuft nicht

Transmission dient hier nur als Beispiel. Der Abschnitt `addons` kann auch Statusinformationen zu anderen unterstützten Add-ons bereitstellen.

#### USV

Das Objekt `ups.apcupsd` wird nur ausgegeben, wenn das optionale IPFire-Add-on `apcupsd` installiert ist. Die Daten werden über den Befehl `apcaccess status` ausgelesen. Kann der Befehl keinen Statusbericht liefern, lautet `status` `unavailable` und die Messwerte sind `null`.

| Parameter | Beschreibung |
| --- | --- |
| `status` | Von apcupsd gemeldeter USV-Status, zum Beispiel `ONLINE`, `ONBATT` oder `COMMLOST` |
| `battery_charge_percent` | Batterieladung in Prozent (`BCHARGE`) |
| `runtime_minutes` | Geschätzte verbleibende Laufzeit in Minuten (`TIMELEFT`) |
| `load_percent` | Aktuelle USV-Last in Prozent (`LOADPCT`) |
| `model` | Von apcupsd gemeldetes USV-Modell |
| `ups_name` | Konfigurierter Name der USV |

Welche Werte verfügbar sind, hängt von USV und Treiber ab. Die Daten konnten noch nicht mit jeder unterstützten USV geprüft werden.

### Zertifikate

Der Abschnitt `certificates` liefert Informationen zum Zertifikat, das Apache für die IPFire-Weboberfläche auf Port `444` ausgibt, sowie zu den von IPFire verwalteten OpenVPN-Clientzertifikaten. Die API liest das Apache-Zertifikat lokal über TLS aus. Das Ablaufdatum entspricht damit dem tatsächlich aktiven Zertifikat, auch wenn es von einem externen Werkzeug wie einem ACME-Client verwaltet wird. OpenVPN-Einträge werden aus der Zertifikatsdatenbank von IPFire gelesen; das OpenVPN-Serverzertifikat wird aus der Clientliste ausgeschlossen.

| Parameter | Beschreibung |
| --- | --- |
| `apache.status` | `valid`, `expired` oder `unavailable` |
| `apache.subject` | Zertifikatsinhaber |
| `apache.issuer` | Zertifikatsaussteller |
| `apache.not_before` | Beginn der Gültigkeit laut OpenSSL |
| `apache.not_after` | Ablaufdatum in UTC im ISO-8601-Format |
| `apache.remaining.years` | Verbleibende volle Kalenderjahre |
| `apache.remaining.months` | Zusätzlich verbleibende volle Kalendermonate |
| `apache.remaining.days` | Zusätzlich verbleibende Kalendertage |
| `apache.remaining_days` | Insgesamt verbleibende volle Tage |

Kann das Apache-Zertifikat nicht ausgelesen werden, lautet `status` `unavailable` und die Zertifikatsdetails sind `null`. Bei einem abgelaufenen Zertifikat stehen die verbleibenden Zähler auf null.

OpenVPN-Clientzertifikate werden als Array unter `openvpn.clients` ausgegeben. Jeder Eintrag enthält:

| Parameter | Beschreibung |
| --- | --- |
| `common_name` | Common Name des Zertifikats |
| `serial` | Seriennummer des Zertifikats |
| `status` | `valid`, `expired`, `revoked` oder `unknown` |
| `not_after` | Ablaufdatum in UTC im ISO-8601-Format |
| `remaining.years` | Verbleibende volle Kalenderjahre |
| `remaining.months` | Zusätzlich verbleibende volle Kalendermonate |
| `remaining.days` | Zusätzlich verbleibende Kalendertage |
| `remaining_days` | Insgesamt verbleibende volle Tage |

Ein leeres Array bedeutet, dass keine OpenVPN-Clientzertifikate vorhanden sind. Kann die OpenVPN-Zertifikatsdatenbank oder das Serverzertifikat nicht gelesen werden, ist `openvpn.clients` gleich `null`.

### Updates

Der Abschnitt `system` enthält weiterhin die bisherige Update-Übersicht. Der Bereich `updates` listet die einzelnen Core- und Paket-Updates auf und meldet den Status eines über die API gestarteten Upgrades. Die Liste basiert auf den lokal gespeicherten Pakfire-Paketinformationen. Falls diese veraltet sein könnten, aktualisiere sie zuerst in der Pakfire-Seite von IPFire. Eine `GET`-Anfrage der API aktualisiert sie nicht selbst.

| Parameter | Beschreibung |
| --- | --- |
| `core_update` | Gibt an, ob ein IPFire-Core-Update verfügbar ist |
| `package_updates` | Anzahl der verfügbaren Paket-Updates |
| `reboot_required` | Gibt an, ob IPFire nach einem Update einen Neustart als erforderlich markiert hat |

Die Werte `core_update` und `reboot_required` sind boolesch:

* `true` – ein Core-Update ist verfügbar
* `false` – kein Core-Update ist verfügbar

`package_updates` enthält die Anzahl der verfügbaren Paket-Updates. `reboot_required` gibt an, ob die Datei `/var/run/need_reboot` vorhanden ist.

`updates.available` ist ein Array der anstehenden Updates. Es wird aus der lokalen Core-Liste, Paketliste und den Metadaten der installierten Pakete von Pakfire gebildet. Core-Einträge enthalten `type`, `name`, `version`, `installed_release` und `available_release`. Paket-Einträge enthalten `type`, `name`, `installed_version`, `available_version`, `installed_release` und `available_release`. Gibt es keine anstehenden Updates, ist das Array leer. `null` bedeutet, dass die benötigten lokalen Pakfire-Daten nicht gelesen oder verarbeitet werden konnten. Eine `GET`-Anfrage aktualisiert diese Listen nicht.

`updates.operation` enthält `status`, `started_at`, `finished_at`, `exit_code` und gegebenenfalls `error`. Die Zeitangaben sind Unix-Zeitstempel in Sekunden. Der Status lautet vor einem API-gestarteten Upgrade `idle`, währenddessen `running` und danach `completed` oder `failed`. Der temporäre Vorgangsstatus und das Update-Protokoll liegen unter `/tmp/ipfire-api` und werden bei einem Neustart von IPFire gelöscht.

## Sicherheit

Lass diesen API-Zugang hinter der authentifizierten IPFire-Weboberfläche. Mache ihn nicht für nicht vertrauenswürdige Netzwerke erreichbar. System- und Add-on-Backups sowie angepasste Installations-ISOs enthalten sensible Konfigurationsdaten; schütze heruntergeladene Dateien entsprechend. Das Löschen eines Backups ist endgültig. `POST`-Anfragen können den Status der Internetverbindung ändern, IPFire-Updates installieren, Backups erstellen, herunterladen oder löschen oder den Router bei erforderlichem Neustart neu starten.

### Unterstützung

Wenn dir IPFire-API weiterhilft, kannst du die Weiterentwicklung auf Ko-fi unterstützen:

[![FMainz auf Ko-fi unterstützen](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/fmainz)

## Lizenz

IPFire-API steht ausschließlich unter der GNU General Public License Version 3. Siehe [LICENSE](LICENSE).
