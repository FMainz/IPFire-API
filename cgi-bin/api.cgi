#!/usr/bin/perl
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 FMainz
###############################################################################
#                                                                             #
# IPFire API                                                                  #
#                                                                             #
# This CGI provides system, network, service, add-on, traffic, and            #
# connection information from IPFire for integrations and other clients.      #
#                                                                             #
###############################################################################

use strict;
use warnings;

require '/var/ipfire/general-functions.pl';
require "/opt/pakfire/lib/functions.pl";
use JSON::PP;

my $api_version = "1";

# -----------------------------------------------------------------------------
# JSON helper
# -----------------------------------------------------------------------------

sub json_escape {
    my ($value) = @_;

    $value //= '';
    $value =~ s/\\/\\\\/g;
    $value =~ s/"/\\"/g;
    $value =~ s/\r/\\r/g;
    $value =~ s/\n/\\n/g;
    $value =~ s/\t/\\t/g;

    return $value;
}

sub json_string {
    my ($value) = @_;
    return '"' . json_escape($value) . '"';
}

sub read_file {
    my ($path) = @_;

    open(my $fh, '<', $path) or return undef;
    my $value = <$fh>;
    close($fh);

    return undef unless defined $value;
    chomp $value;

    return $value;
}

sub traffic_data {
    my $interface = read_file('/var/ipfire/red/iface');

    return (undef, undef) unless defined $interface;
    return (undef, undef) unless $interface =~ /^[A-Za-z0-9_.:-]+$/;

    my $rx_bytes = read_file("/sys/class/net/$interface/statistics/rx_bytes");
    my $tx_bytes = read_file("/sys/class/net/$interface/statistics/tx_bytes");

    return (undef, undef)
        unless defined $rx_bytes && defined $tx_bytes;

    return (undef, undef)
        unless $rx_bytes =~ /^\d+$/ && $tx_bytes =~ /^\d+$/;

    return (int($rx_bytes), int($tx_bytes));
}

sub system_data {
    open(my $fh, '<', '/etc/system-release') or return ('', 0, 0);

    my $version = <$fh>;
    close($fh);

    chomp($version) if defined $version;

    my %pakfire_status = &Pakfire::status();

    my $core_update =
        (($pakfire_status{'CoreUpdateAvailable'} // '') eq 'yes');

    my $package_updates =
        $pakfire_status{'PakUpdatesAvailable'} // 0;

    $package_updates = 0 unless $package_updates =~ /^\d+$/;
    $package_updates = int($package_updates);

    return (
        defined $version ? $version : '',
        $core_update,
        $package_updates,
    );
}

sub cpu_data {
    open(my $fh, '<', '/proc/stat') or return (undef, undef);

    my @fields;

    while (my $line = <$fh>) {
        if ($line =~ /^cpu\s+(.+)$/) {
            @fields = split(/\s+/, $1);
            last;
        }
    }

    close($fh);

    return (undef, undef) unless @fields >= 8;

    foreach my $value (@fields[0 .. 7]) {
        return (undef, undef) unless $value =~ /^\d+$/;
    }

    # user + nice + system + idle + iowait + irq + softirq + steal
    my $total = 0;
    $total += $_ for @fields[0 .. 7];

    # idle + iowait
    my $idle = $fields[3] + $fields[4];

    return (int($total), int($idle));
}

sub memory_data {
    open(my $fh, '<', '/proc/meminfo') or return ();

    my %memory;

    while (my $line = <$fh>) {
        if ($line =~ /^(MemTotal|MemAvailable|MemFree|Buffers|Cached):\s+(\d+)\s+kB$/) {
            $memory{$1} = int($2) * 1024;
        }
    }

    close($fh);

    return (
        $memory{'MemTotal'},
        $memory{'MemAvailable'},
        $memory{'MemFree'},
        $memory{'Buffers'},
        $memory{'Cached'},
    );
}

sub uptime_data {
    open(my $fh, '<', '/proc/uptime') or return undef;

    my $line = <$fh>;

    close($fh);

    return undef unless defined $line;

    my ($uptime) = split(/\s+/, $line);

    return undef unless defined $uptime;
    return undef unless $uptime =~ /^\d+(?:\.\d+)?$/;

    return int($uptime);
}

sub disk_data {
    open(my $fh, '-|', 'df', '-B1', '/') or return ();

    my $header = <$fh>;
    my $line = <$fh>;

    close($fh);

    return () unless defined $line;

    $line =~ s/^\s+|\s+$//g;

    my @fields = split(/\s+/, $line);

    return () unless @fields >= 6;
    return () unless $fields[1] =~ /^\d+$/;
    return () unless $fields[2] =~ /^\d+$/;
    return () unless $fields[3] =~ /^\d+$/;
    return () unless $fields[4] =~ /^(\d+)%$/;

    my $total = int($fields[1]);
    my $used = int($fields[2]);
    my $available = int($fields[3]);
    my $use_percent = int($1);

    return (
        $total,
        $used,
        $available,
        $use_percent,
    );
}

sub diskstats_data {
    open(my $fh, '<', '/proc/diskstats') or return ();

    while (my $line = <$fh>) {
        $line =~ s/^\s+|\s+$//g;

        my @fields = split(/\s+/, $line);

        next unless @fields >= 14;
        next unless $fields[2] eq 'sda';

        foreach my $value (@fields[3 .. 13]) {
            return () unless $value =~ /^\d+$/;
        }

        return (
            int($fields[3]),   # reads completed
            int($fields[5]),   # sectors read
            int($fields[7]),   # writes completed
            int($fields[9]),   # sectors written
            int($fields[11]),  # I/Os currently in progress
            int($fields[12]),  # time spent doing I/Os
        );
    }

    close($fh);

    return ();
}

sub smart_data {
    my $cache_file = '/tmp/fire-api.cache';
    my $cache_age  = 60 * 60;    # 60 Minuten

    # Cache verwenden, wenn vorhanden, nicht leer und noch aktuell
    if (-f $cache_file && -s $cache_file) {
        my $mtime = (stat($cache_file))[9];

        if (defined $mtime && (time - $mtime) < $cache_age) {
            open(my $fh, '<', $cache_file) or return undef;

            local $/;
            my $data = <$fh>;

            close($fh);

            return $data
                if defined $data && $data =~ /^\s*\{.*\}\s*$/s;
        }
    }

    # SMART-Daten über den von IPFire vorgesehenen Wrapper ermitteln.
    my $output = '';

    if (open(my $fh, '-|', '/usr/local/bin/smartctrl', 'sda')) {
        local $/;
        $output = <$fh> // '';

        close($fh);
    }

    # SMART-Ausgabe muss einen erfolgreichen Health-Test enthalten.
    return undef
        unless $output =~ /SMART overall-health self-assessment test result:\s*PASSED/i;

    my $health = JSON::PP::true;

    # SMART-Attribute aus der tabellarischen Ausgabe auswerten.
    my (
        $temperature,
        $power_on_hours,
        $power_cycles,
        $uncorrectable_errors,
        $remaining_lifetime,
    );

    foreach my $line (split(/\n/, $output)) {
        $line =~ s/^\s+|\s+$//g;

        my @fields = split(/\s+/, $line);

        # SMART-Attributzeilen beginnen mit der Attribut-ID.
        next unless @fields >= 10;
        next unless $fields[0] =~ /^\d+$/;

        my $id  = int($fields[0]);
        my $raw = $fields[-1];

        next unless $raw =~ /^\d+$/;

        if ($id == 9) {
            $power_on_hours = int($raw);
        } elsif ($id == 12) {
            $power_cycles = int($raw);
        } elsif ($id == 160) {
            $uncorrectable_errors = int($raw);
        } elsif ($id == 169) {
            $remaining_lifetime = int($raw);
        } elsif ($id == 194) {
            $temperature = int($raw);
        }
    }

    # Nur vollständige SMART-Daten als gültiges Ergebnis akzeptieren.
    return undef
        unless defined $temperature
            && defined $power_on_hours
            && defined $power_cycles
            && defined $uncorrectable_errors
            && defined $remaining_lifetime;

    # smartctrl liefert in der aktuellen Ausgabe keinen SMART-Error-Log.
    # Daher bleibt errors zunächst 0.
    my $errors = 0;

    my $result = {
        health               => $health,
        temperature          => $temperature,
        power_on_hours       => $power_on_hours,
        power_cycles         => $power_cycles,
        uncorrectable_errors => $uncorrectable_errors,
        errors               => $errors,
        remaining_lifetime   => $remaining_lifetime,
    };

    my $json = encode_json($result);

    # Nur vollständige und erfolgreiche SMART-Daten cachen.
    if (open(my $fh, '>', $cache_file)) {
        print $fh $json;
        close($fh);
    }

    return $json;
}

sub fireinfo_data {
    my $profile_file = '/var/ipfire/fireinfo/profile';

    open(my $fh, '<', $profile_file) or return ();

    local $/;
    my $json = <$fh>;
    close($fh);

    my $data = eval { decode_json($json) };
    return () if $@ || !ref($data);

    my $profile = $data->{'profile'} // {};

    my $cpu = $profile->{'cpu'} // {};
    my $network = $profile->{'network'} // {};
    my $system = $profile->{'system'} // {};

    return (
        $cpu->{'arch'} // '',
        $cpu->{'model_string'} // '',
        int($cpu->{'count'} // 0),

        $system->{'model'} // '',
        $system->{'vendor'} // '',
        $system->{'virtual'} ? 1 : 0,

        $network->{'blue'} ? 1 : 0,
        $network->{'green'} ? 1 : 0,
        $network->{'orange'} ? 1 : 0,
        $network->{'red'} ? 1 : 0,
    );
}

sub services_data {
    my %services = (
        'dhcp' => {
            'process' => 'dhcpd',
        },
        'web_server' => {
            'process' => 'httpd',
        },
        'cron' => {
            'process' => 'fcron',
        },
        'dns_resolver' => {
            'process' => 'kresd',
        },
        'logging' => {
            'process' => 'syslogd',
        },
        'ntp' => {
            'process' => 'ntpd',
        },
        'ssh' => {
            'process' => 'sshd',
        },
        'vpn' => {
            'process' => 'charon',
        },
        'web_proxy' => {
            'process' => 'squid',
        },
        'ips' => {
            'pidfile' => '/var/run/suricata.pid',
        },
        'ovpn_roadwarrior' => {
            'process' => 'openvpn',
            'pidfile' => '/var/run/openvpn-rw.pid',
        },
        'lldp' => {
            'process' => 'lldpd',
        },
        'dbus' => {
            'process' => 'dbus-daemon',
            'pidfile' => '/var/run/dbus/pid',
        },
    );

    my %status;

    foreach my $service (keys %services) {
        my %config = %{ $services{$service} };

        my @pids;

        if (defined $config{'pidfile'}) {
            @pids = &General::read_pids($config{'pidfile'});
        } else {
            @pids = &General::find_pids($config{'process'});
        }

        $status{$service} = scalar(@pids) ? 1 : 0;
    }

    return %status;
}

sub addons_data {
    my %addons;

    my %paklist = &Pakfire::dblist("installed");

    foreach my $pak (sort keys %paklist) {
        my %metadata = &Pakfire::getmetadata($pak, "installed");

        next unless "$metadata{'Services'}";

        foreach my $service (split(/ /, "$metadata{'Services'}")) {
            next unless $service;

            my @status = &General::system_output(
                "/usr/local/bin/addonctrl",
                "$pak",
                "status",
                "$service"
            );

            my $output = join('', @status);

            my $running =
                ($output =~ /is\ running/ && $output !~ /is\ not\ running/);

            $addons{$pak} = {
                'running' => $running ? 1 : 0,
            };
        }
    }

    return %addons;
}

my ($version, $core_update, $package_updates) = system_data();
my ($rx_bytes, $tx_bytes) = traffic_data();
my ($cpu_total, $cpu_idle) = cpu_data();
my $uptime = uptime_data();
my $smart = smart_data();

my ($memory_total,
    $memory_available,
    $memory_free,
    $memory_buffers,
    $memory_cached,
) = memory_data();

my (
    $disk_total,
    $disk_used,
    $disk_available,
    $disk_use_percent,
) = disk_data();

my (
    $disk_reads,
    $disk_sectors_read,
    $disk_writes,
    $disk_sectors_written,
    $disk_io_in_progress,
    $disk_io_time,
) = diskstats_data();

my (
    $architecture,
    $cpu_model,
    $cpu_count,
    $model,
    $vendor,
    $virtual,
    $blue,
    $green,
    $orange,
    $red,
) = fireinfo_data();

my $pakfire_version = &Pakfire::make_version();
my @kernel_version = &General::system_output("uname", "-r");
my $kernel_release = $kernel_version[0] // '';
chomp($kernel_release);

my %services = services_data();
my %addons = addons_data();

# -----------------------------------------------------------------------------
# HTTP response
# -----------------------------------------------------------------------------

print "Content-Type: application/json; charset=utf-8\r\n";
print "Cache-Control: no-store, no-cache, must-revalidate\r\n";
print "Pragma: no-cache\r\n";
print "\r\n";

# The API provides read-only system data and connection control.
my $method = $ENV{'REQUEST_METHOD'} // 'GET';

# -----------------------------------------------------------------------------
# Connection control
# -----------------------------------------------------------------------------
#
# Connection actions require the IPFire web interface authentication and an
# API request header. The legacy HA-IPFire header remains supported.
# The IPFire WebGUI already protects this CGI with HTTP authentication.
#
# Clients may send:
#   X-IPFire-API: 1
#
# HA-IPFire currently sends the legacy header:
#   X-HA-IPFire-API: 1
#
# and a form-encoded POST body:
#   action=connect
#   action=disconnect
#
if ($method eq 'POST') {
    my $api_header = $ENV{'HTTP_X_IPFIRE_API'} // '';
    my $legacy_api_header = $ENV{'HTTP_X_HA_IPFIRE_API'} // '';

    if ($api_header ne '1' && $legacy_api_header ne '1') {
        print '{"api_version":'.$api_version.',"error":"forbidden"}';
        exit 0;
    }

    my $content_length = $ENV{'CONTENT_LENGTH'} // 0;
    my $body = '';

    if ($content_length =~ /^\d+$/ && $content_length > 0) {
        read(STDIN, $body, $content_length);
    }

    my $action = '';
    if ($body =~ /(?:^|&)action=([^&]*)/) {
        $action = $1;
        $action =~ tr/+/ /;
        $action =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
    }

    if ($action ne 'connect' && $action ne 'disconnect') {
        print '{"api_version":'.$api_version.',"error":"invalid_action"}';
        exit 0;
    }

    my $redctrl = '/usr/local/bin/redctrl';

    unless (-x $redctrl) {
        print '{"api_version":'.$api_version.',"error":"redctrl_not_found"}';
        exit 0;
    }

    my $command;

    if ($action eq 'connect') {
        $command = -e "${General::swroot}/red/active"
            ? 'restart'
            : 'start';
    } elsif ($action eq 'disconnect') {
        if (!-e "${General::swroot}/red/active") {
            print '{"api_version":'.$api_version.',"result":"ok"}';
            exit 0;
        }

        $command = 'stop';
    }
    unless (defined $command) {
        print '{"api_version":'.$api_version.',"result":"error","error":"invalid_action"}';
        exit 0;
    }

    my $result;

    {
        open my $null, '>', '/dev/null'
            or die "Cannot open /dev/null: $!";

        local *STDOUT = $null;
        local *STDERR = $null;

        $result = system("$redctrl $command >/dev/null 2>&1");
    }

    if ($result == 0) {
        print '{"api_version":'.$api_version.',"result":"ok"}';
    } else {
        my $exit_code = $result >> 8;
        print '{"api_version":'.$api_version.',"result":"error","error":"redctrl_failed","exit_code":'
            . $exit_code
            . "}";
    }

    exit 0;
}

if ($method ne 'GET') {
    print '{"api_version":'.$api_version.',"error":"method_not_allowed"}';
    exit 0;
}

# -----------------------------------------------------------------------------
# Read IPFire connection information
# -----------------------------------------------------------------------------

my %pppsettings = ();
&General::readhash("${General::swroot}/ppp/settings", \%pppsettings);

my $state = 'disconnected';
my $duration = 0;
my $connected_since = undef;

# IPFire creates /var/ipfire/red/active while the RED connection is active.
# Its modification time is also used by Header::connectionstatus() to display
# the connection age.
my $active_file = "${General::swroot}/red/active";

if (-e $active_file) {
    my @stat = stat($active_file);
    my $mtime = $stat[9];

    if (defined $mtime) {
        $connected_since = int($mtime);
        $duration = time() - $mtime;
        $duration = 0 if $duration < 0;
    }

    $state = 'connected';
} else {
    # Match IPFire's own connectionstatus() logic:
    # keepconnected + running pppd means that the connection is being brought
    # up; otherwise the connection is closed.
    my $keepconnected = "${General::swroot}/red/keepconnected";

    if (-e $keepconnected) {
        my $pppd_running = system("ps -ef | grep -q '[p]ppd'") == 0;
        $state = 'connecting' if $pppd_running;
    }
}

my $profile = $pppsettings{'PROFILENAME'} // '';

my $external_ip = read_file("${General::swroot}/red/local-ipaddress");
my $external_hostname = '';

if ($external_ip ne '') {
    $external_hostname =
        (gethostbyaddr(pack("C4", split(/\./, $external_ip)), 2))[0]
        || '';
}

# -----------------------------------------------------------------------------
# JSON response
# -----------------------------------------------------------------------------

my @json;
push @json, '"api_version":'.$api_version;

push @json, '"system":{'
    . '"version":' . json_string($version)
    . ',"pakfire_version":' . json_string($pakfire_version)
    . ',"kernel_version":' . json_string($kernel_release)
    . ',"architecture":' . json_string($architecture)
    . ',"cpu_model":' . json_string($cpu_model)
    . ',"cpu_count":' . $cpu_count
    . ',"model":' . json_string($model)
    . ',"vendor":' . json_string($vendor)
    . ',"virtual":' . ($virtual ? 'true' : 'false')
    . ',"core_update":' . ($core_update ? 'true' : 'false')
    . ',"package_updates":' . $package_updates
    . ',"uptime":' . (defined $uptime ? $uptime : 'null')
    . ',"cpu":{'
    . '"total":' . (defined $cpu_total ? $cpu_total : 'null')
    . ',"idle":' . (defined $cpu_idle ? $cpu_idle : 'null')
    . '}'
    . ',"memory":{'
    . '"total":' . (defined $memory_total ? $memory_total : 'null')
    . ',"available":' . (defined $memory_available ? $memory_available : 'null')
    . ',"free":' . (defined $memory_free ? $memory_free : 'null')
    . ',"buffers":' . (defined $memory_buffers ? $memory_buffers : 'null')
    . ',"cached":' . (defined $memory_cached ? $memory_cached : 'null')
    . '}'
    . ',"disk":{'
    . '"root":{'
    . '"total":' . (defined $disk_total ? $disk_total : 'null')
    . ',"used":' . (defined $disk_used ? $disk_used : 'null')
    . ',"available":' . (defined $disk_available ? $disk_available : 'null')
    . ',"use_percent":' . (defined $disk_use_percent ? $disk_use_percent : 'null')
    . '}'
    . ',"sda":{'
    . '"reads":' . (defined $disk_reads ? $disk_reads : 'null')
    . ',"sectors_read":' . (defined $disk_sectors_read ? $disk_sectors_read : 'null')
    . ',"writes":' . (defined $disk_writes ? $disk_writes : 'null')
    . ',"sectors_written":' . (defined $disk_sectors_written ? $disk_sectors_written : 'null')
    . ',"io_in_progress":' . (defined $disk_io_in_progress ? $disk_io_in_progress : 'null')
    . ',"io_time":' . (defined $disk_io_time ? $disk_io_time : 'null')
    . '}'
    . '}'
    . ',"smart":' . (defined $smart ? $smart : 'null')
    . '}';

push @json, '"network":{'
    . '"blue":' . ($blue ? 'true' : 'false')
    . ',"green":' . ($green ? 'true' : 'false')
    . ',"orange":' . ($orange ? 'true' : 'false')
    . ',"red":' . ($red ? 'true' : 'false')
    . '}';

push @json, '"services":{'
    . '"dhcp":' . ($services{'dhcp'} ? 'true' : 'false')
    . ',"web_server":' . ($services{'web_server'} ? 'true' : 'false')
    . ',"cron":' . ($services{'cron'} ? 'true' : 'false')
    . ',"dns_resolver":' . ($services{'dns_resolver'} ? 'true' : 'false')
    . ',"logging":' . ($services{'logging'} ? 'true' : 'false')
    . ',"ntp":' . ($services{'ntp'} ? 'true' : 'false')
    . ',"ssh":' . ($services{'ssh'} ? 'true' : 'false')
    . ',"vpn":' . ($services{'vpn'} ? 'true' : 'false')
    . ',"web_proxy":' . ($services{'web_proxy'} ? 'true' : 'false')
    . ',"ips":' . ($services{'ips'} ? 'true' : 'false')
    . ',"ovpn_roadwarrior":' . ($services{'ovpn_roadwarrior'} ? 'true' : 'false')
    . ',"lldp":' . ($services{'lldp'} ? 'true' : 'false')
    . ',"dbus":' . ($services{'dbus'} ? 'true' : 'false')
    . '}';

my @addon_json;

foreach my $addon (sort keys %addons) {
    push @addon_json,
        json_string($addon)
        . ':{'
        . '"running":' . ($addons{$addon}{'running'} ? 'true' : 'false')
        . '}';
}

push @json, '"addons":{' . join(',', @addon_json) . '}';

push @json, '"traffic":{'
    . '"rx_bytes":' . (defined $rx_bytes ? $rx_bytes : 'null')
    . ',"tx_bytes":' . (defined $tx_bytes ? $tx_bytes : 'null')
    . '}';

my @connection;
push @connection, '"state":' . json_string($state);

if (defined $connected_since) {
    push @connection, '"connected_since":' . $connected_since;
    push @connection, '"duration":' . int($duration);
    push @connection, '"duration_text":' . json_string(&General::format_time(int($duration)));
} else {
    push @connection, '"connected_since":null';
    push @connection, '"duration":0';
    push @connection, '"duration_text":""';
}

push @connection, '"profile":' . json_string($profile);
push @connection, '"external_ip":' . json_string($external_ip);
push @connection, '"external_hostname":' . json_string($external_hostname);

push @json, '"connection":{' . join(',', @connection) . '}';

print '{' . join(',', @json) . "}\n";

exit 0;
