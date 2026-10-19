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

### System parameters

The `system` section provides the following information:

| Parameter | Description |
| --- | --- |
| `version` | IPFire version |
| `pakfire_version` | Pakfire version |
| `kernel_version` | Linux kernel version |
| `architecture` | System architecture |
| `cpu_model` | CPU model |
| `cpu_count` | Number of CPU cores |
| `model` | System model |
| `vendor` | System vendor |
| `virtual` | Whether the system is virtualized |
| `core_update` | Whether an IPFire core update is available |
| `package_updates` | Number of available package updates |
| `uptime` | System uptime in seconds |

#### CPU

| Parameter | Description |
| --- | --- |
| `total` | Accumulated CPU time |
| `idle` | Accumulated CPU idle time |

#### Memory

| Parameter | Description |
| --- | --- |
| `total` | Total physical memory in bytes |
| `available` | Available memory in bytes |
| `free` | Free memory in bytes |
| `buffers` | Memory used for buffers in bytes |
| `cached` | Memory used for cache in bytes |

#### Disk

Root filesystem space information is provided under `disk.root`.

| Parameter | Description |
| --- | --- |
| `total` | Total disk space in bytes |
| `used` | Used disk space in bytes |
| `available` | Available disk space in bytes |
| `use_percent` | Disk usage in percent |

I/O statistics for the `sda` device are provided under `disk.sda`.

| Parameter | Description |
| --- | --- |
| `reads` | Number of completed read operations |
| `sectors_read` | Number of sectors read |
| `writes` | Number of completed write operations |
| `sectors_written` | Number of sectors written |
| `io_in_progress` | Number of I/O operations currently in progress |
| `io_time` | Time spent performing I/O operations |

#### SMART

SMART information is provided for the system disk.

| Parameter | Description |
| --- | --- |
| `power_on_hours` | Disk power-on hours |
| `remaining_lifetime` | Remaining disk lifetime in percent |
| `health` | SMART health status |
| `errors` | SMART error count |
| `uncorrectable_errors` | Number of uncorrectable errors |
| `power_cycles` | Number of power cycles |
| `temperature` | Disk temperature |

### Network

The `network` section provides the current state of the IPFire network interfaces.

| Parameter | Description |
| --- | --- |
| `blue` | State of the BLUE network interface |
| `green` | State of the GREEN network interface |
| `orange` | State of the ORANGE network interface |
| `red` | State of the RED network interface |

Values are boolean:

* `true` – the interface is active
* `false` – the interface is inactive

### Services

The `services` section provides the current status of services managed by IPFire.

| Parameter | Description |
| --- | --- |
| `dhcp` | DHCP server status |
| `web_server` | IPFire web server status |
| `cron` | Cron service status |
| `dns_resolver` | DNS resolver status |
| `logging` | Logging service status |
| `ntp` | NTP service status |
| `ssh` | SSH service status |
| `vpn` | VPN service status |
| `web_proxy` | Web proxy status |
| `ips` | Intrusion Prevention System (IPS) status |
| `ovpn_roadwarrior` | OpenVPN Roadwarrior status |
| `lldp` | LLDP service status |
| `dbus` | D-Bus service status |

Values are boolean:

* `true` – the service is running
* `false` – the service is not running

### Add-ons

The `addons` section provides the current status of supported IPFire add-ons. For example, an add-on status is represented as:

| Parameter | Description |
| --- | --- |
| `transmission.running` | Whether the Transmission add-on is running |

Values are boolean: `true` means the add-on is running; `false` means it is not running. Transmission is an example; the section can provide status information for other supported add-ons.

### Updates

The `system` section also provides information about available IPFire updates.

| Parameter | Description |
| --- | --- |
| `core_update` | Whether an IPFire core update is available |
| `package_updates` | Number of available package updates |

`core_update` is boolean. `package_updates` is the number of available package updates.

## Security

Keep this endpoint behind IPFire's authenticated web interface. Do not expose it to untrusted networks. `POST` requests can change the internet connection state.

## Add-ons

The `addons` response section is intended to grow as add-on integrations are added. Contributions should document the add-on, its status source, and any IPFire version assumptions.

## License

IPFire-API is licensed under the GNU General Public License version 3 only. See [LICENSE](LICENSE).
