# IPFire-API

[Deutsch](README-de.md)

IPFire-API is a CGI-based API extension for IPFire. It exposes selected system, network, service, add-on, UPS, traffic, and internet connection information as JSON, and supports controlling the RED internet connection. The project's goal is to provide a broad range of useful information and features.

The project is based on the [HA-IPFire Home Assistant integration](https://github.com/FMainz/HA-IPFire). By developing it separately, the goal is to create a general-purpose API that provides integrations and other clients with the same open, standardized interface.

## Features

- System, CPU, memory, disk, SMART, network, service, UPS, and certificate information
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

An authenticated `GET` request returns the current data as JSON. The response uses API version `1` and includes `system`, `network`, `dhcp`, `services`, `ups`, `traffic`, `connection`, and `certificates` sections. The `addons` section is included only when supported add-ons with services are installed. Unavailable measurements are returned as `null` where applicable; unavailable add-on and service states are reported as `false`.

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
| `reboot_required` | Whether IPFire has marked a reboot as required after an update |
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

SMART information is provided for the system disk. The result is cached for one hour so the disk is not queried on every API request. After the cache expires, the next API request refreshes the data; there is no background refresh, so the values remain unchanged until another request is made.

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

The `network` section reports configured IPFire network zones and information about their assigned devices. Zone booleans indicate whether the zone is present in IPFire's hardware profile; they do not indicate the current physical link state.

| Parameter | Description |
| --- | --- |
| `blue` | Whether the BLUE zone is present in the hardware profile |
| `green` | Whether the GREEN zone is present in the hardware profile |
| `orange` | Whether the ORANGE zone is present in the hardware profile |
| `red` | Whether the RED zone is present in the hardware profile |

Values are boolean:

* `true` – the zone is present
* `false` – the zone is not present

The `interfaces` object contains data for each configured zone, read from IPFire's interface settings, the Linux interface counters, and `ethtool`:

| Parameter | Description |
| --- | --- |
| `device` | Linux network device assigned to the zone |
| `rx_bytes` | Cumulative number of bytes received by the interface |
| `tx_bytes` | Cumulative number of bytes transmitted by the interface |
| `driver` | Network driver name |
| `driver_version` | Driver version reported by `ethtool` |
| `firmware_version` | Firmware version reported by `ethtool` |
| `supported_link_modes` | Link modes supported by the device and driver |
| `max_supported_speed_mbps` | Highest speed found in the supported link modes |
| `advertised_link_modes` | Link modes currently advertised for autonegotiation |
| `link_partner_advertised_link_modes` | Link modes advertised by the connected partner, if reported |
| `supports_auto_negotiation` | Whether the device supports autonegotiation |
| `auto_negotiation` | Whether autonegotiation is currently enabled |
| `speed_mbps` | Currently negotiated link speed in Mbps |
| `duplex` | Currently negotiated duplex mode |
| `link_detected` | Whether a physical link is detected |

`rx_bytes` and `tx_bytes` are cumulative counters read from `/sys/class/net/<device>/statistics/`; clients can calculate rates by comparing successive readings. An interface entry is `null` when no assigned device is present. If the device exists but has no physical link, its supported and advertised modes may still be available while `speed_mbps` and `duplex` are `null`.

#### Neighbors

The `neighbors` array mirrors IPFire's `ip neigh show` output and includes address, device, link-layer address (when available), and neighbor state.

#### Routes

The `routes` array contains the main routing table. If IPFire has entries in routing table 220, they are included in the optional `ipsec_routes` array; this field is omitted when that table is empty.

### DHCP leases

The `dhcp.leases` array is read from `/var/state/dhcp/dhcpd.leases`, the lease database used by IPFire's web interface. It includes the latest record for each IP address, including expired leases, with its IP address, MAC address, hostname, expiry time, and active or expired status. A lease with no expiry is marked with `expires_never: true`. If the lease file cannot be read, `dhcp.leases` is `null`. The DHCP server's running state remains available under `services.dhcp`.

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

The `addons` section is included only when supported IPFire add-ons with services are installed. It provides their current status. If no such add-ons are installed, the section is omitted entirely. For example, an add-on status is represented as:

| Parameter | Description |
| --- | --- |
| `transmission.running` | Whether the Transmission add-on is running |

Values are boolean: `true` means the add-on is running; `false` means it is not running. Transmission is an example; the section can provide status information for other supported add-ons.

### UPS

The `ups.apcupsd` object is included only when the optional IPFire `apcupsd` add-on is installed. It reports data using the add-on's `apcaccess status` command. If the command cannot return a status report, `status` is `unavailable` and measurements are `null`.

| Parameter | Description |
| --- | --- |
| `status` | UPS state reported by apcupsd, such as `ONLINE`, `ONBATT`, or `COMMLOST` |
| `battery_charge_percent` | Battery charge in percent (`BCHARGE`) |
| `runtime_minutes` | Estimated remaining runtime in minutes (`TIMELEFT`) |
| `load_percent` | Current UPS load in percent (`LOADPCT`) |
| `model` | UPS model reported by apcupsd |
| `ups_name` | Configured UPS name |

The values depend on the UPS and driver and have not been verified against every supported device.

### Certificates

The `certificates` section reports the certificate Apache presents for the IPFire web interface on port `444`, and OpenVPN client certificates recorded by IPFire. The API reads Apache's certificate over the local TLS connection, so the reported expiry reflects the active certificate, including certificates managed by external tools such as ACME clients. OpenVPN client entries are read from IPFire's certificate database; the OpenVPN server certificate is excluded from that list.

| Parameter | Description |
| --- | --- |
| `apache.status` | `valid`, `expired`, or `unavailable` |
| `apache.subject` | Certificate subject |
| `apache.issuer` | Certificate issuer |
| `apache.not_before` | Start of validity, as reported by OpenSSL |
| `apache.not_after` | Expiry date in UTC using ISO 8601 format |
| `apache.remaining.years` | Whole calendar years remaining |
| `apache.remaining.months` | Additional whole calendar months remaining |
| `apache.remaining.days` | Additional calendar days remaining |
| `apache.remaining_days` | Total whole days remaining |

If Apache's certificate cannot be read, `status` is `unavailable` and certificate details are `null`. When the certificate has expired, the remaining counters are zero.

OpenVPN client certificates are returned as an array under `openvpn.clients`. Each entry includes:

| Parameter | Description |
| --- | --- |
| `common_name` | Certificate common name |
| `serial` | Certificate serial number |
| `status` | `valid`, `expired`, `revoked`, or `unknown` |
| `not_after` | Expiry date in UTC using ISO 8601 format |
| `remaining.years` | Whole calendar years remaining |
| `remaining.months` | Additional whole calendar months remaining |
| `remaining.days` | Additional calendar days remaining |
| `remaining_days` | Total whole days remaining |

An empty array means that no OpenVPN client certificates are present. If the OpenVPN certificate database or server certificate cannot be read, `openvpn.clients` is `null`.

### Updates

The `system` section also provides information about available IPFire updates.

| Parameter | Description |
| --- | --- |
| `core_update` | Whether an IPFire core update is available |
| `package_updates` | Number of available package updates |
| `reboot_required` | Whether IPFire has marked a reboot as required after an update |

`core_update` and `reboot_required` are boolean. `package_updates` is the number of available package updates. `reboot_required` reflects whether `/var/run/need_reboot` exists.

## Security

Keep this endpoint behind IPFire's authenticated web interface. Do not expose it to untrusted networks. `POST` requests can change the internet connection state.

## Add-ons

The `addons` response section is intended to grow as add-on integrations are added. Contributions should document the add-on, its status source, and any IPFire version assumptions.

## License

IPFire-API is licensed under the GNU General Public License version 3 only. See [LICENSE](LICENSE).
