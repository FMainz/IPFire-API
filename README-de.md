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

## Sicherheit

Lass diesen Endpunkt hinter der authentifizierten IPFire-Weboberfläche. Mache ihn nicht für nicht vertrauenswürdige Netzwerke erreichbar. `POST`-Anfragen können den Status der Internetverbindung ändern.

## Add-ons

Der Bereich `addons` ist für weitere Add-on-Schnittstellen vorgesehen. Beiträge sollten das Add-on, die Quelle des Status und relevante IPFire-Versionsannahmen dokumentieren.

## Lizenz

IPFire-API steht ausschließlich unter der GNU General Public License Version 3. Siehe [LICENSE](LICENSE).
