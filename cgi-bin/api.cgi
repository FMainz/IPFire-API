#!/usr/bin/perl
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 FMainz
###############################################################################
#                                                                             #
# IPFire API                                                                  #
#                                                                             #
# This CGI provides system, network, service, add-on, UPS, traffic, and       #
# connection information from IPFire for integrations and other clients.      #
#                                                                             #
###############################################################################

use strict;
use warnings;

require '/var/ipfire/general-functions.pl';
require "/opt/pakfire/lib/functions.pl";
use JSON::PP;
use Time::Local qw(timegm);

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

sub red_traffic_data {
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

sub apache_certificate_data {
    my %result = (
        'status' => 'unavailable',
        'subject' => undef,
        'issuer' => undef,
        'not_before' => undef,
        'not_after' => undef,
        'remaining' => undef,
        'remaining_days' => undef,
    );

    # Query the certificate Apache actually presents on the IPFire WUI port.
    # This also works when the certificate is managed outside IPFire's default
    # certificate paths, for example by an ACME client.
    open(my $fh, '-|',
        'openssl s_client -connect 127.0.0.1:444 -noservername </dev/null'
        . ' 2>/dev/null | openssl x509 -noout -subject -issuer -startdate -enddate'
    ) or return %result;

    my %certificate;
    while (my $line = <$fh>) {
        if ($line =~ /^(subject|issuer|notBefore|notAfter)=(.*)$/) {
            $certificate{$1} = $2;
        }
    }
    close($fh);

    return %result unless defined $certificate{'notAfter'};

    my %months = (
        Jan => 0, Feb => 1, Mar => 2, Apr => 3, May => 4, Jun => 5,
        Jul => 6, Aug => 7, Sep => 8, Oct => 9, Nov => 10, Dec => 11,
    );
    my ($month, $day, $hour, $minute, $second, $year) =
        $certificate{'notAfter'} =~ /^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})\s+GMT$/;

    return %result unless defined $year && exists $months{$month};

    my $expires = eval {
        timegm($second, $minute, $hour, $day, $months{$month}, $year);
    };
    return %result unless defined $expires;

    my $now = time();
    my $not_after = sprintf('%04d-%02d-%02dT%02d:%02d:%02dZ',
        $year, $months{$month} + 1, $day, $hour, $minute, $second);

    $result{'status'} = ($expires > $now) ? 'valid' : 'expired';
    $result{'subject'} = $certificate{'subject'};
    $result{'issuer'} = $certificate{'issuer'};
    $result{'not_before'} = $certificate{'notBefore'};
    $result{'not_after'} = $not_after;

    my ($remaining, $remaining_days) = remaining_time_data($expires);
    $result{'remaining'} = $remaining;
    $result{'remaining_days'} = $remaining_days;

    return %result;
}

sub parse_ca_expiry {
    my ($value) = @_;
    return unless defined $value;

    my ($year, $month, $day, $hour, $minute, $second);
    if ($value =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/) {
        ($year, $month, $day, $hour, $minute, $second) =
            ($1, $2, $3, $4, $5, $6);
    } elsif ($value =~ /^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/) {
        ($year, $month, $day, $hour, $minute, $second) =
            ($1, $2, $3, $4, $5, $6);
        $year += ($year < 50) ? 2000 : 1900;
    } else {
        return;
    }

    my $epoch = eval {
        timegm($second, $minute, $hour, $day, $month - 1, $year);
    };
    return unless defined $epoch;

    return (
        $epoch,
        sprintf('%04d-%02d-%02dT%02d:%02d:%02dZ',
            $year, $month, $day, $hour, $minute, $second),
    );
}

sub remaining_time_data {
    my ($expires) = @_;
    return ({ 'years' => 0, 'months' => 0, 'days' => 0 }, 0)
        unless defined $expires && $expires > time();

    my @now_parts = gmtime(time());
    my @expiry_parts = gmtime($expires);
    my ($day, $month, $year) = @now_parts[3, 4, 5];
    my ($exp_day, $exp_month, $exp_year) = @expiry_parts[3, 4, 5];
    my $years = $exp_year - $year;
    my $remaining_months = $exp_month - $month;
    my $days = $exp_day - $day;

    my $now_time = $now_parts[2] * 3600 + $now_parts[1] * 60 + $now_parts[0];
    my $expiry_time = $expiry_parts[2] * 3600
        + $expiry_parts[1] * 60 + $expiry_parts[0];
    $days-- if $expiry_time < $now_time;

    if ($days < 0) {
        $remaining_months--;
        my $previous_month = ($exp_month + 11) % 12;
        my $previous_year = $exp_year - ($exp_month == 0 ? 1 : 0);
        my @month_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31);
        my $leap = ($previous_year % 4 == 0)
            && (($previous_year % 100 != 0) || ($previous_year % 400 == 0));
        $month_days[1] = 29 if $leap;
        $days += $month_days[$previous_month];
    }
    if ($remaining_months < 0) {
        $years--;
        $remaining_months += 12;
    }

    return (
        {
            'years' => $years,
            'months' => $remaining_months,
            'days' => $days,
        },
        int(($expires - time()) / 86400),
    );
}

sub openvpn_client_certificates_data {
    my $index_file = '/var/ipfire/ovpn/certs/index.txt';
    my $server_cert = '/var/ipfire/ovpn/certs/servercert.pem';

    # The index contains the server certificate as well as any client or
    # site-to-site certificates. Identify the server by serial so it is not
    # reported as a client certificate.
    open(my $serial_fh, '-|', 'openssl', 'x509', '-in', $server_cert, '-noout', '-serial')
        or return undef;
    my $serial_line = <$serial_fh>;
    close($serial_fh);
    return undef unless defined $serial_line && $serial_line =~ /^serial=([0-9A-Fa-f]+)\s*$/;
    my $server_serial = uc($1);
    $server_serial =~ s/^0+//;
    $server_serial = '0' unless length $server_serial;

    open(my $index_fh, '<', $index_file) or return undef;
    my @clients;

    while (my $line = <$index_fh>) {
        chomp $line;
        my @fields = split(/\t/, $line, 6);
        next unless @fields >= 6;

        my $ca_status = $fields[0];
        my $expiry = $fields[1];
        my $serial = $fields[3];
        my $subject = $fields[5];
        next unless defined $serial && defined $subject;
        my $normalized_serial = uc($serial);
        $normalized_serial =~ s/^0+//;
        $normalized_serial = '0' unless length $normalized_serial;
        next if $normalized_serial eq $server_serial;

        my ($common_name) = $subject =~ m{(?:^|/)CN=([^/]+)};
        next unless defined $common_name;
        $common_name =~ s/\\\//\//g;

        my ($expires, $not_after) = parse_ca_expiry($expiry);
        next unless defined $expires;

        my $status = $ca_status eq 'R' ? 'revoked'
            : ($ca_status eq 'E' || $expires <= time()) ? 'expired'
            : $ca_status eq 'V' ? 'valid'
            : 'unknown';
        my ($remaining, $remaining_days) = remaining_time_data($expires);

        push @clients, {
            'common_name' => $common_name,
            'serial' => $serial,
            'status' => $status,
            'not_after' => $not_after,
            'remaining' => $remaining,
            'remaining_days' => $remaining_days,
        };
    }

    close($index_fh);
    return \@clients;
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

sub network_interface_data {
    my ($device) = @_;
    return undef unless defined $device && $device =~ /^[A-Za-z0-9_.:-]+$/;
    return undef unless -e "/sys/class/net/$device";

    my %data = (
        'device' => $device,
        'rx_bytes' => undef,
        'tx_bytes' => undef,
        'driver' => undef,
        'driver_version' => undef,
        'firmware_version' => undef,
        'supported_link_modes' => undef,
        'max_supported_speed_mbps' => undef,
        'advertised_link_modes' => undef,
        'link_partner_advertised_link_modes' => undef,
        'supports_auto_negotiation' => undef,
        'auto_negotiation' => undef,
        'speed_mbps' => undef,
        'duplex' => undef,
        'link_detected' => undef,
    );

    my $rx_bytes = read_file("/sys/class/net/$device/statistics/rx_bytes");
    my $tx_bytes = read_file("/sys/class/net/$device/statistics/tx_bytes");
    $data{'rx_bytes'} = int($rx_bytes)
        if defined $rx_bytes && $rx_bytes =~ /^\d+$/;
    $data{'tx_bytes'} = int($tx_bytes)
        if defined $tx_bytes && $tx_bytes =~ /^\d+$/;

    my %mode_keys = (
        'Supported link modes' => 'supported_link_modes',
        'Advertised link modes' => 'advertised_link_modes',
        'Link partner advertised link modes' => 'link_partner_advertised_link_modes',
    );
    my $current_modes;

    if (open(my $fh, '-|', '/usr/sbin/ethtool', $device)) {
        while (my $line = <$fh>) {
            if ($line =~ /^\s*(Supported link modes|Advertised link modes|Link partner advertised link modes):\s*(.*)$/) {
                $current_modes = $mode_keys{$1};
                $data{$current_modes} = [] unless ref($data{$current_modes}) eq 'ARRAY';
                my @modes = grep { /^\d+base\S+\/(?:Half|Full)$/ } split(/\s+/, $2);
                push @{$data{$current_modes}}, @modes;
                next;
            }

            if (defined $current_modes) {
                my $continuation = $line;
                $continuation =~ s/^\s+|\s+$//g;
                if ($continuation =~ /^\d+base/) {
                    my @modes = grep { /^\d+base\S+\/(?:Half|Full)$/ } split(/\s+/, $continuation);
                    push @{$data{$current_modes}}, @modes;
                    next;
                }
                $current_modes = undef;
            }

            if ($line =~ /^\s*Supports auto-negotiation:\s*(Yes|No)/i) {
                $data{'supports_auto_negotiation'} = lc($1) eq 'yes' ? JSON::PP::true() : JSON::PP::false();
            } elsif ($line =~ /^\s*Auto-negotiation:\s*(on|off)/i) {
                $data{'auto_negotiation'} = lc($1) eq 'on' ? JSON::PP::true() : JSON::PP::false();
            } elsif ($line =~ /^\s*Speed:\s*(\d+)\s*Mb\/s/i) {
                $data{'speed_mbps'} = int($1);
            } elsif ($line =~ /^\s*Duplex:\s*(Half|Full)/i) {
                $data{'duplex'} = lc($1);
            } elsif ($line =~ /^\s*Link detected:\s*(yes|no)/i) {
                $data{'link_detected'} = lc($1) eq 'yes' ? JSON::PP::true() : JSON::PP::false();
            }
        }
        close($fh);
    }

    if (open(my $fh, '-|', '/usr/sbin/ethtool', '-i', $device)) {
        while (my $line = <$fh>) {
            $data{'driver'} = $1 if $line =~ /^driver:\s*(\S+)/;
            $data{'driver_version'} = $1 if $line =~ /^version:\s*(\S+)/;
            if ($line =~ /^firmware-version:\s*(.*?)\s*$/) {
                $data{'firmware_version'} = length($1) ? $1 : undef;
            }
        }
        close($fh);
    }

    if (ref($data{'supported_link_modes'}) eq 'ARRAY') {
        my $max_speed;
        foreach my $mode (@{$data{'supported_link_modes'}}) {
            my ($speed) = $mode =~ /^(\d+)base/;
            $max_speed = $speed if defined $speed && (!defined $max_speed || $speed > $max_speed);
        }
        $data{'max_supported_speed_mbps'} = int($max_speed) if defined $max_speed;
    }

    return \%data;
}

sub network_neighbours_data {
    open(my $fh, '-|', '/sbin/ip', 'neigh', 'show') or return undef;

    my @neighbours;
    my %states = map { $_ => 1 } qw(REACHABLE STALE DELAY PROBE FAILED INCOMPLETE PERMANENT NOARP NONE);

    while (my $line = <$fh>) {
        chomp $line;
        my @fields = split(/\s+/, $line);
        next unless @fields;

        my %entry = (
            'address' => $fields[0],
            'device' => undef,
            'mac_address' => undef,
            'state' => 'unknown',
        );

        for (my $i = 1; $i < @fields; $i++) {
            if ($fields[$i] eq 'dev' && defined $fields[$i + 1]) {
                $entry{'device'} = $fields[++$i];
            } elsif ($fields[$i] eq 'lladdr' && defined $fields[$i + 1]) {
                $entry{'mac_address'} = lc($fields[++$i]);
            } elsif ($states{uc($fields[$i])}) {
                $entry{'state'} = lc($fields[$i]);
            }
        }

        push @neighbours, \%entry;
    }

    close($fh);
    return \@neighbours;
}

sub ip_route_table_data {
    my (@arguments) = @_;
    open(my $fh, '-|', '/sbin/ip', @arguments) or return undef;

    my @routes;
    my %route_types = map { $_ => 1 }
        qw(unicast local broadcast multicast throw unreachable prohibit blackhole nat anycast);

    while (my $line = <$fh>) {
        chomp $line;
        next unless length $line;

        my @fields = split(/\s+/, $line);
        my %route = (
            'type' => 'unicast',
            'destination' => undef,
            'via' => undef,
            'device' => undef,
            'protocol' => undef,
            'scope' => undef,
            'source' => undef,
            'metric' => undef,
            'table' => undef,
            'raw' => $line,
        );

        if (@fields && $route_types{$fields[0]}) {
            $route{'type'} = shift @fields;
        }
        $route{'destination'} = shift @fields if @fields;

        my %keys = (
            'via' => 'via',
            'dev' => 'device',
            'proto' => 'protocol',
            'scope' => 'scope',
            'src' => 'source',
            'metric' => 'metric',
            'table' => 'table',
        );
        for (my $i = 0; $i < @fields; $i++) {
            my $key = $keys{$fields[$i]};
            if (defined $key && defined $fields[$i + 1]) {
                $route{$key} = $fields[++$i];
            }
        }

        $route{'metric'} = 0 + $route{'metric'}
            if defined $route{'metric'} && $route{'metric'} =~ /^\d+$/;
        push @routes, \%route;
    }

    close($fh);
    return \@routes;
}

sub network_interfaces_data {
    my %settings;
    &General::readhash("${General::swroot}/ethernet/settings", \%settings);

    my %interfaces;
    foreach my $zone (qw(red green orange blue)) {
        my $device = $settings{uc($zone) . '_DEV'};
        $interfaces{$zone} = network_interface_data($device);
    }

    return \%interfaces;
}

sub apcupsd_data {
    my @candidates = qw(/usr/sbin/apcaccess /sbin/apcaccess /usr/bin/apcaccess);
    my ($apcaccess) = grep { -x $_ } @candidates;

    # The optional add-on is omitted from the response when it is not installed.
    return undef unless defined $apcaccess;

    my %data = (
        'status' => 'unavailable',
        'battery_charge_percent' => undef,
        'runtime_minutes' => undef,
        'load_percent' => undef,
        'model' => undef,
        'ups_name' => undef,
    );

    if (open(my $fh, '-|', $apcaccess, 'status')) {
        while (my $line = <$fh>) {
            if ($line =~ /^STATUS\s*:\s*(.*?)\s*$/) {
                $data{'status'} = $1;
            } elsif ($line =~ /^BCHARGE\s*:\s*([\d.]+)\s+Percent/i) {
                $data{'battery_charge_percent'} = 0 + $1;
            } elsif ($line =~ /^TIMELEFT\s*:\s*([\d.]+)\s+Minutes/i) {
                $data{'runtime_minutes'} = 0 + $1;
            } elsif ($line =~ /^LOADPCT\s*:\s*([\d.]+)\s+Percent/i) {
                $data{'load_percent'} = 0 + $1;
            } elsif ($line =~ /^MODEL\s*:\s*(.*?)\s*$/) {
                $data{'model'} = $1;
            } elsif ($line =~ /^UPSNAME\s*:\s*(.*?)\s*$/) {
                $data{'ups_name'} = $1;
            }
        }
        close($fh);

        # A status line confirms that apcupsd returned a usable report. If it
        # did not, retain "unavailable" and the null measurements above.
    }

    return \%data;
}

sub dhcp_leases_data {
    my $lease_file = '/var/state/dhcp/dhcpd.leases';
    open(my $fh, '<', $lease_file) or return undef;

    my %leases;
    my $lease;

    while (my $line = <$fh>) {
        if ($line =~ /^\s*lease\s+(\S+)\s*\{/) {
            $lease = {
                'ip_address' => $1,
                'mac_address' => undef,
                'hostname' => undef,
                'expires_at' => undef,
                'expires_never' => JSON::PP::false,
                'status' => 'unknown',
                'expired' => undef,
            };
            next;
        }

        next unless defined $lease;

        if ($line =~ /^\s*ends\s+\d\s+(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})/) {
            my ($year, $month, $day, $hour, $minute, $second) = ($1, $2, $3, $4, $5, $6);
            my $expires = eval {
                timegm($second, $minute, $hour, $day, $month - 1, $year);
            };
            if (defined $expires) {
                $lease->{'expires_at'} = sprintf(
                    '%04d-%02d-%02dT%02d:%02d:%02dZ',
                    $year, $month, $day, $hour, $minute, $second
                );
                my $expired = $expires <= time();
                $lease->{'status'} = $expired ? 'expired' : 'active';
                $lease->{'expired'} = $expired ? JSON::PP::true() : JSON::PP::false();
            }
        } elsif ($line =~ /^\s*ends\s+never/) {
            $lease->{'expires_never'} = JSON::PP::true();
            $lease->{'status'} = 'active';
            $lease->{'expired'} = JSON::PP::false();
        } elsif ($line =~ /^\s*hardware\s+ethernet\s+([0-9a-f:]+);/i) {
            $lease->{'mac_address'} = lc($1);
        } elsif ($line =~ /^\s*client-hostname\s+"((?:\\.|[^"])*)";/) {
            my $hostname = $1;
            $hostname =~ s/\\(["\\])/$1/g;
            $lease->{'hostname'} = $hostname;
        } elsif ($line =~ /^\s*\}\s*$/) {
            # The lease file keeps historical records. The latest record for
            # an address is the one shown by IPFire's current lease list.
            $leases{$lease->{'ip_address'}} = $lease;
            $lease = undef;
        }
    }

    close($fh);
    return [ map { $leases{$_} } sort keys %leases ];
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
my $reboot_required = -e '/var/run/need_reboot' ? 1 : 0;
my ($red_rx_bytes, $red_tx_bytes) = red_traffic_data();
my ($cpu_total, $cpu_idle) = cpu_data();
my $uptime = uptime_data();
my %apache_certificate = apache_certificate_data();
my $openvpn_client_certificates = openvpn_client_certificates_data();
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
my $dhcp_leases = dhcp_leases_data();
my %addons = addons_data();
my $network_interfaces = network_interfaces_data();
my $network_neighbours = network_neighbours_data();
my $network_routes = ip_route_table_data('route', 'show');
my $ipsec_routes = ip_route_table_data('route', 'list', 'table', '220');
my $apcupsd = apcupsd_data();

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

my @apache_certificate_json;
foreach my $key (qw(status subject issuer not_before not_after remaining_days)) {
    my $value = $apache_certificate{$key};
    push @apache_certificate_json,
        json_string($key) . ':'
        . (defined $value
            ? ($key eq 'remaining_days' ? $value : json_string($value))
            : 'null');
}
my $remaining = $apache_certificate{'remaining'};
my $remaining_json = defined $remaining
    ? '{"years":'.$remaining->{'years'}
        . ',"months":'.$remaining->{'months'}
        . ',"days":'.$remaining->{'days'}.'}'
    : 'null';
push @apache_certificate_json, '"remaining":'.$remaining_json;

my $openvpn_clients_json = 'null';
if (defined $openvpn_client_certificates) {
    my @openvpn_clients;
    foreach my $client (@{$openvpn_client_certificates}) {
        push @openvpn_clients,
            '{"common_name":' . json_string($client->{'common_name'})
            . ',"serial":' . json_string($client->{'serial'})
            . ',"status":' . json_string($client->{'status'})
            . ',"not_after":' . json_string($client->{'not_after'})
            . ',"remaining_days":' . $client->{'remaining_days'}
            . ',"remaining":{"years":' . $client->{'remaining'}{'years'}
            . ',"months":' . $client->{'remaining'}{'months'}
            . ',"days":' . $client->{'remaining'}{'days'} . '}}';
    }
    $openvpn_clients_json = '[' . join(',', @openvpn_clients) . ']';
}

push @json, '"certificates":{"apache":{'
    . join(',', @apache_certificate_json)
    . '},"openvpn":{"clients":' . $openvpn_clients_json . '}}';

if (defined $apcupsd) {
    my @apcupsd_fields;
    foreach my $key (qw(status model ups_name)) {
        my $value = $apcupsd->{$key};
        push @apcupsd_fields, json_string($key) . ':'
            . (defined $value ? json_string($value) : 'null');
    }
    foreach my $key (qw(battery_charge_percent runtime_minutes load_percent)) {
        my $value = $apcupsd->{$key};
        push @apcupsd_fields, json_string($key) . ':'
            . (defined $value ? $value : 'null');
    }
    push @json, '"ups":{"apcupsd":{' . join(',', @apcupsd_fields) . '}}';
}

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
    . ',"reboot_required":' . ($reboot_required ? 'true' : 'false')
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

my @network_json = (
    '"blue":' . ($blue ? 'true' : 'false'),
    '"green":' . ($green ? 'true' : 'false'),
    '"orange":' . ($orange ? 'true' : 'false'),
    '"red":' . ($red ? 'true' : 'false'),
    '"interfaces":' . encode_json($network_interfaces),
    '"neighbors":' . (defined $network_neighbours ? encode_json($network_neighbours) : 'null'),
    '"routes":' . (defined $network_routes ? encode_json($network_routes) : 'null'),
);
push @network_json, '"ipsec_routes":' . encode_json($ipsec_routes)
    if defined $ipsec_routes && @{$ipsec_routes};
push @json, '"network":{' . join(',', @network_json) . '}';

push @json, '"dhcp":{"leases":'
    . (defined $dhcp_leases ? encode_json($dhcp_leases) : 'null')
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

push @json, '"addons":{' . join(',', @addon_json) . '}' if @addon_json;

push @json, '"traffic":{'
    . '"rx_bytes":' . (defined $red_rx_bytes ? $red_rx_bytes : 'null')
    . ',"tx_bytes":' . (defined $red_tx_bytes ? $red_tx_bytes : 'null')
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
