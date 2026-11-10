[![GitHub release](https://img.shields.io/github/release/FMainz/IPFire-API?include_prereleases=&sort=semver&color=blue)](https://github.com/FMainz/IPFire-API/releases/)
![last commit](https://img.shields.io/github/last-commit/FMainz/IPFire-API)
[![License: GPL-3.0-only](https://img.shields.io/badge/License-GPL--3.0--only-blue.svg)](https://github.com/FMainz/IPFire-API/blob/main/LICENSE)
![API downloads](https://img.shields.io/github/downloads/FMainz/IPFire-API/total?style=flat-square&color=red&label=API%20downloads)
[![stars](https://img.shields.io/github/stars/FMainz/IPFire-API)](https://github.com/FMainz/IPFire-API/stargazers)
# IPFire-API

This documentation is available in 🇬🇧 English and 🇩🇪 [German](README-de.md).

IPFire-API is an interface for IPFire that returns selected system, network, service, add-on, UPS, traffic, and internet connection information in JSON format. It also provides authenticated controls to bring the RED connection online or offline, start the installation of available updates remotely, and request a router reboot when IPFire reports that one is required.

The API was originally developed for the [HA-IPFire Home Assistant integration](https://github.com/FMainz/HA-IPFire) and is now maintained as a separate project, so other integrations and clients can use it as well.

Installing additional software on a firewall always carries some risk, including this API. If you do not need the API, you should not install it.

## Contents

- [Features](#features)
- [Installation](#installation)
- [Endpoint](#endpoint)
  - [Connection control](#connection-control)
  - [Update installation](#update-installation)
  - [Reboot](#reboot)
  - [System parameters](#system-parameters)
    - [CPU](#cpu)
    - [Memory](#memory)
    - [Disk](#disk)
    - [SMART](#smart)
  - [Network](#network)
    - [VLANs](#vlans)
    - [Neighbors](#neighbors)
    - [Routes](#routes)
  - [DHCP leases](#dhcp-leases)
  - [Services](#services)
  - [Add-ons](#add-ons)
    - [UPS](#ups)
  - [Certificates](#certificates)
  - [Updates](#updates)
- [Security](#security)
- [License](#license)

## Features

- System, CPU, memory, disk, SMART, network, service, UPS, and certificate information
- Status information for supported add-ons
- Available IPFire core and package updates, with an authenticated action to start the Pakfire upgrade
- Authenticated router reboot action when IPFire reports that a reboot is required
- RED traffic counters
- Internet connection state and details
- Connect and disconnect actions through IPFire's native `redctrl`
- JSON responses with API version and script revision fields

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

An authenticated `GET` request returns the current data as JSON. The response uses API version `1`, reports the `api.cgi` script revision in `api_revision`, and includes `system`, `network`, `dhcp`, `updates`, `services`, `ups`, `traffic`, `connection`, and `certificates` sections. The `api_version` describes the JSON interface; `api_revision` is the script version from the file header. The `addons` section is included only when supported add-ons with services are installed. Unavailable measurements are returned as `null` where applicable; unavailable add-on and service states are reported as `false`.

All authenticated `POST` actions require the `X-IPFire-API: 1` header. For compatibility with existing clients, the legacy `X-HA-IPFire-API: 1` header is also accepted.

### Connection control

Connection actions use authenticated `POST` requests with a form body and the `X-IPFire-API: 1` header.
The following example uses `curl` to establish the connection:

```sh
curl --user '<webgui-user>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=connect' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

To disconnect, use `action=disconnect` instead. `curl` prompts for the WebGUI password. Replace the placeholders with the WebGUI username and IPFire host name. If IPFire uses a self-signed certificate, configure `curl` to trust that certificate, for example with `--cacert /path/to/ipfire-certificate.pem`.

The CGI invokes IPFire's native `/usr/local/bin/redctrl` command. A `connect` action starts or restarts the connection; `disconnect` stops it. Other methods, missing headers, and unsupported actions are rejected.

### Update installation

An authenticated `POST` request with the `X-IPFire-API: 1` header can start the installation of all updates currently listed by Pakfire.
Example using `curl`:

```sh
curl --user '<webgui-user>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=upgrade' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

The API starts the same non-interactive Pakfire upgrade used by the IPFire web interface. The request returns immediately with `result: "accepted"`; poll the `updates.operation` object in `GET` responses to see whether the run is `running`, `completed`, or `failed`. The API rejects the request if no updates are available or another API-started upgrade is running. This action installs the full update set; it does not install individual packages selectively. **Only run this request when you are ready to install all updates currently listed by Pakfire.**

The `updates.operation` object is included in every `GET` response. The following command prints the full JSON response; the operation status is in `updates.operation`:

```sh
curl --user '<webgui-user>' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

If `jq` is installed, you can filter the response to display only `updates.operation`. On Debian Trixie, `jq` is available in the [package of the same name](https://packages.debian.org/trixie/jq) and can be installed with `sudo apt install jq`:

```sh
curl --user '<webgui-user>' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi' \
  | jq '.updates.operation'
```

### Reboot

An authenticated `POST` request with `action=reboot` asks IPFire to restart. The API accepts this action only while `/var/run/need_reboot` exists and uses IPFire's native `/usr/local/bin/ipfirereboot` helper. The router restarts shortly after the API returns `result: "accepted"`; the connection to Home Assistant will be interrupted until IPFire is available again.

```sh
curl --user '<webgui-user>' \
  --header 'X-IPFire-API: 1' \
  --data-urlencode 'action=reboot' \
  'https://<ipfire-host>:444/cgi-bin/api.cgi'
```

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

#### VLANs

The optional `vlans` array lists VLANs configured through IPFire's zone configuration. It is omitted when no VLANs are configured. Each entry contains:

| Parameter | Description |
| --- | --- |
| `zone` | IPFire zone using the VLAN |
| `vlan_id` | Configured VLAN identifier |
| `parent_device` | Parent network device, if it can be matched to the configured parent MAC address |
| `parent_mac_address` | Parent MAC address recorded by IPFire |
| `zone_device` | Network device assigned to the zone |
| `zone_interface_present` | Whether the zone device currently exists in Linux |
| `mac_address` | MAC address configured for the VLAN interface |

The API reads this information from IPFire's `/var/ipfire/ethernet/vlans` settings file. VLANs created outside IPFire's zone configuration are not listed here.

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

The `addons` section is included only when supported IPFire add-ons with services are installed. It provides their current status. If no such add-ons are installed, the section is omitted entirely. This section is intended to grow as add-on integrations are added. Contributions should document the add-on, its status source, and any IPFire version assumptions. For example, an add-on status is represented as:

| Parameter | Description |
| --- | --- |
| `transmission.running` | Whether the Transmission add-on is running |

Values are boolean: `true` means the add-on is running; `false` means it is not running. Transmission is an example; the section can provide status information for other supported add-ons.

#### UPS

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

The `system` section provides the existing update summary. The `updates` section lists the individual core and package updates and reports the status of an API-started upgrade. The list uses the local Pakfire package metadata; refresh the package lists in IPFire's Pakfire page first if they may be out of date. The API does not refresh them as part of a `GET` request.

| Parameter | Description |
| --- | --- |
| `core_update` | Whether an IPFire core update is available |
| `package_updates` | Number of available package updates |
| `reboot_required` | Whether IPFire has marked a reboot as required after an update |

`core_update` and `reboot_required` are boolean. `package_updates` is the number of available package updates. `reboot_required` reflects whether `/var/run/need_reboot` exists.

`updates.available` is an array of pending updates, built from Pakfire's local core list, package list, and installed package metadata. Core entries contain `type`, `name`, `version`, `installed_release`, and `available_release`. Package entries contain `type`, `name`, `installed_version`, `available_version`, `installed_release`, and `available_release`. It is an empty array when no updates are pending and `null` if the required local Pakfire data cannot be read or parsed. The API does not refresh these lists during a `GET` request.

`updates.operation` contains `status`, `started_at`, `finished_at`, `exit_code`, and, when relevant, `error`. The timestamps are Unix timestamps in seconds. The status is `idle` before an API-started upgrade, `running` during it, then `completed` or `failed`. Temporary operation state and the update log are kept under `/tmp/ipfire-api` and are cleared when IPFire reboots.

## Security

Keep this endpoint behind IPFire's authenticated web interface. Do not expose it to untrusted networks. `POST` requests can change the internet connection state, install IPFire updates, or reboot the router when required.

### Support

If you find IPFire-API useful, you can support its ongoing development on Ko-fi:

[![Support FMainz on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/fmainz)

## License

IPFire-API is licensed under the GNU General Public License version 3 only. See [LICENSE](LICENSE).
