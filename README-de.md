# IPFire-API

[English](README.md)

IPFire-API ist eine CGI-basierte API-Erweiterung für IPFire. Sie stellt ausgewählte System-, Netzwerk-, Dienst-, Add-on-, Traffic- und Verbindungsinformationen als JSON bereit und kann die RED-Internetverbindung steuern. Das Ziel des Projekt ist es, viele sinnvolle Informationen und Funktionen zur Verfügung zu stellen.

Grundstock des Projekts ist die Home-Assistant-Integration [HA-IPFire](https://github.com/FMainz/HA-IPFire). Mit der separaten Entwicklung soll eine allgemeingültige API geschaffen werden, die Integrationen und anderen Clients die selbe offene standadisierte Schnittstelle zur Verfügung stellt.

## Funktionen

- Informationen zu System, CPU, Arbeitsspeicher, Festplatte und SMART
- Status der Netzwerkschnittstellen und IPFire-Dienste
- Status unterstützter Add-ons
- Traffic-Zähler der RED-Schnittstelle
- Status und Details der Internetverbindung
- Verbinden und Trennen über IPFires natives `redctrl`
- JSON-Antworten mit API-Versionsfeld

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

## Endpunkt

Der Endpunkt lautet:

```text
https://<ipfire-host>:444/cgi-bin/api.cgi
```

Eine authentifizierte `GET`-Anfrage liefert die aktuellen Daten als JSON. Die Antwort verwendet API-Version `1` und enthält die Bereiche `system`, `network`, `services`, `addons`, `traffic` und `connection`. Nicht verfügbare Messwerte werden, sofern zutreffend, als `null` ausgegeben. Nicht erkannte Add-on- und Dienststatus erscheinen als `false`.

### Verbindungssteuerung

Verbindungsaktionen verwenden authentifizierte `POST`-Anfragen mit einem Formularkörper und dem Header `X-IPFire-API: 1`:

```text
action=connect
```

oder:

```text
action=disconnect
```

Das CGI ruft IPFires natives `/usr/local/bin/redctrl` auf. `connect` baut die Verbindung auf oder verbindet sie neu; `disconnect` trennt sie. Andere Methoden, fehlende Header und nicht unterstützte Aktionen werden abgewiesen.

Für bestehende Clients akzeptiert das CGI außerdem weiterhin den bisherigen Header `X-HA-IPFire-API: 1`.

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

SMART-Informationen werden für die Systemfestplatte bereitgestellt.

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

Der Abschnitt `network` stellt den aktuellen Status der IPFire-Netzwerkschnittstellen bereit.

| Parameter | Beschreibung |
| --- | --- |
| `blue` | Status der BLUE-Netzwerkschnittstelle |
| `green` | Status der GREEN-Netzwerkschnittstelle |
| `orange` | Status der ORANGE-Netzwerkschnittstelle |
| `red` | Status der RED-Netzwerkschnittstelle |

Die Werte sind boolesch:

* `true` – die Schnittstelle ist aktiv
* `false` – die Schnittstelle ist inaktiv

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

Der Abschnitt `addons` stellt den aktuellen Status unterstützter IPFire-Add-ons bereit.

Das folgende Beispiel zeigt, wie der Status eines Add-ons dargestellt wird:

| Parameter | Beschreibung |
| --- | --- |
| `transmission.running` | Gibt an, ob das Transmission-Add-on läuft |

Der Wert ist boolesch:

* `true` – das Add-on läuft
* `false` – das Add-on läuft nicht

Transmission dient hier nur als Beispiel. Der Abschnitt `addons` kann auch Statusinformationen zu anderen unterstützten Add-ons bereitstellen.

### Updates

Der Abschnitt `system` stellt Informationen über verfügbare IPFire-Updates bereit.

| Parameter | Beschreibung |
| --- | --- |
| `core_update` | Gibt an, ob ein IPFire-Core-Update verfügbar ist |
| `package_updates` | Anzahl der verfügbaren Paket-Updates |

Der Wert `core_update` ist boolesch:

* `true` – ein Core-Update ist verfügbar
* `false` – kein Core-Update ist verfügbar

`package_updates` enthält die Anzahl der verfügbaren Paket-Updates.

## Sicherheit

Lass diesen Endpunkt hinter der authentifizierten IPFire-Weboberfläche. Mache ihn nicht für nicht vertrauenswürdige Netzwerke erreichbar. `POST`-Anfragen können den Status der Internetverbindung ändern.

## Add-ons

Der Bereich `addons` ist für weitere Add-on-Schnittstellen vorgesehen. Beiträge sollten das Add-on, die Quelle des Status und relevante IPFire-Versionsannahmen dokumentieren.

## Lizenz

IPFire-API steht ausschließlich unter der GNU General Public License Version 3. Siehe [LICENSE](LICENSE).
