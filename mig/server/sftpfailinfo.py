#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# sftpfailinfo - grep sftp negotiation log errors and lookup source FQDN
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Grep for sftp negotiation in sftp.log and translate source IP to FQDN"""

import getopt
import multiprocessing
import os
import re
import socket
import sys

from shared.conf import get_configuration_object
from shared.useradm import init_user_adm

def usage(name='sftpfailinfo.py'):
    """Usage help"""

    print """%(doc)s

Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -h                  Show this help
   -v                  Verbose output
   -x TRUSTED_IP       Trust IPs starting with this prefix (multiple allowed)
   -X TRUSTED_DOMAIN   Trust FQDNs ending with this suffix (multiple allowed)
""" % {'doc': __doc__, 'name': name}

def dns_lookup(ip_addr):
    """Reverse DNS lookup with result returned as (ip_addr, fqdn)-tuple if
    address lookup succeeded and (ip_addr, ip_addr) otherwise.
    """
    try:
        fqdn = socket.gethostbyaddr(ip_addr)[0]
    except socket.herror:
        fqdn = ip_addr
    return (ip_addr, fqdn)


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    # Never blacklist localhost IPs
    trust_ip_list = ['127.0.']
    # NOTE: 123.31.32.0/19 in Vietnam maps to 'localhost' - don't trust DNS
    trust_fqdn_list = []
    verbose = False
    opt_args = 'c:hvx:X:'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        elif opt == '-x':
            trust_ip_list.append(val.strip())
        elif opt == '-X':
            trust_fqdn_list.append(val.strip())
        else:
            print 'Error: %s not supported!' % opt
            sys.exit(1)

    if conf_path:
        os.environ['MIG_CONF'] = conf_path
    configuration = get_configuration_object()
    matches = []
    extract_pattern = r"(.+) WARNING client negotiation errors for "
    extract_pattern += r"\('(\d+\.\d+\.\d+\.\d+)', (\d+)\): Incompatible ssh"
    extract_pattern += r" .* \(no acceptable (.*)\)"
    extract_regex = re.compile(extract_pattern)
    sftp_log = configuration.user_sftp_log
    print "Searching for SFTP negotiation errors in %s" % sftp_log
    log_fd = open(sftp_log)
    for line in log_fd:
        if line.find('WARNING client negotiation errors ') != -1:
            matches.append(line)
    log_fd.close()
    print "Found %s matching log lines" % len(matches)
    ip_fail_map = {}
    for line in matches:
        match = extract_regex.match(line)
        if match:
            stamp, source_ip, source_port, err_cond = match.group(1, 2, 3, 4)
            if not source_ip in ip_fail_map:
                ip_fail_map[source_ip] = {'source_ip': source_ip}
            if not err_cond in ip_fail_map[source_ip]:
                ip_fail_map[source_ip][err_cond] = 0
            ip_fail_map[source_ip][err_cond] += 1
            ip_fail_map[source_ip]['last'] = stamp

    print "Reverse DNS lookup %d source IP(s)" % len(ip_fail_map.keys())
    # Reverse DNS lookup is horribly slow with timeout - use multiprocessing
    workers = multiprocessing.Pool(processes=64)
    rdns_results = workers.map(dns_lookup, ip_fail_map.keys())
    fqdn_fail_map = {}
    for (source_ip, source_fqdn) in rdns_results:
        fqdn_fail_map[source_fqdn] = ip_fail_map[source_ip]

    print ""
    print "Full error statistics:"
    print "----------------------"
    sorted_hosts = fqdn_fail_map.keys()
    # Try to sort in a more intuitive way where TLD is considered first
    sorted_hosts.sort(cmp=lambda a, b: cmp(a.split(".")[::-1],
                                           b.split(".")[::-1]))
    show_limit, offender_limit = 8, 32
    for source_fqdn in sorted_hosts:
        err_map = fqdn_fail_map[source_fqdn]
        source_ip = err_map['source_ip']
        last = err_map['last']
        host_stats = "%s (%s): " % (source_fqdn, source_ip)
        host_errs = []
        total = 0
        for (err_cond, err_count) in err_map.items():
            if err_cond in ['source_ip', 'last']:
                continue
            host_errs.append("%s: %d" % (err_cond, err_count))
            total += err_count
        host_stats += ' , '.join(host_errs)
        host_stats += ' , total: %d' % total
        host_stats += ' , last: %s' % last
        # Only display repeated offenders and honor trust
        trust = False
        for trust_prefix in trust_ip_list:
            if source_ip.startswith(trust_prefix):
                trust = True
        for trust_suffix in trust_fqdn_list:
            if source_fqdn.endswith(trust_suffix):
                trust = True
        if trust:
            print host_stats
            print " * You may want to look into these trusted origin failures"
            print ""
            continue
        if total > show_limit:
            print host_stats
            if total > offender_limit:
                print " *  You may want to verify origin and block if fishy:"
                print "\twhois %(source_ip)s|grep 'descr:'" % err_map
                print "\tsudo iptables -A INPUT -s %(source_ip)s/32 -j DROP" \
                      % err_map
            print ""
