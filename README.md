# IPFire-API

[Deutsch](README-de.md)

IPFire-API is a CGI-based API extension for IPFire. It exposes selected system, network, service, add-on, traffic, and internet connection information as JSON, and supports controlling the RED internet connection. The project's goal is to provide a broad range of useful information and features.

The project is based on the [HA-IPFire Home Assistant integration](https://github.com/FMainz/HA-IPFire). By developing it separately, the goal is to create a general-purpose API that provides integrations and other clients with the same open, standardized interface.

## Features

- System, CPU, memory, disk, SMART, network, and service information
- Status information for supported add-ons
- RED traffic counters
- Internet connection state and details
- Connect and disconnect actions through IPFire's native `redctrl`
- JSON responses with an API version field

## Installation

Copy `cgi-bin/api.cgi` to the IPFire web server's CGI directory:

```text
/srv/web/ipfire/cgi-bin/api.cgi
```

Set the owner and executable permissions:

```sh
chown root:root /srv/web/ipfire/cgi-bin/api.cgi
chmod 755 /srv/web/ipfire/cgi-bin/api.cgi
```

The CGI uses IPFire's existing web interface authentication. No separate API credentials are configured by this script.

## Endpoint

The endpoint is:

```text
https://<ipfire-host>:444/cgi-bin/api.cgi
```

An authenticated `GET` request returns the current data as JSON. The response uses API version `1` and includes `system`, `network`, `services`, `addons`, `traffic`, and `connection` sections. Unavailable measurements are returned as `null` where applicable; unavailable add-on and service states are reported as `false`.

### Connection control

Connection actions use authenticated `POST` requests with a form body and the `X-IPFire-API: 1` header:

```text
action=connect
```

or:

```text
action=disconnect
```

The CGI invokes IPFire's native `/usr/local/bin/redctrl` command. A `connect` action starts or restarts the connection; `disconnect` stops it. Other methods, missing headers, and unsupported actions are rejected.

For compatibility with existing clients, the CGI also accepts the legacy `X-HA-IPFire-API: 1` header.

## Security

Keep this endpoint behind IPFire's authenticated web interface. Do not expose it to untrusted networks. `POST` requests can change the internet connection state.

## Add-ons

The `addons` response section is intended to grow as add-on integrations are added. Contributions should document the add-on, its status source, and any IPFire version assumptions.

## License

IPFire-API is licensed under the GNU General Public License version 3 only. See [LICENSE](LICENSE).
