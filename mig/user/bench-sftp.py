#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# bench-sftp - sftp benchmark against MiG server openssh and MiG
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Benchmark sft upload/download against paramiko and openssh sftp servers.
SSH agent is used for the auth if no explicit keys are given.
"""

from __future__ import print_function

import os
import sys
import time

import paramiko

local = False
bench_hosts = {}
if local:
    bench_hosts['openssh'] = {
        'hostname': 'localhost',
        'port': 22,
        'username': 'jonas',
        # 'key_path': os.path.expanduser('~/.ssh/id_rsa'),
        'key_path': None,
        'user_key': None,
    }
    bench_hosts['paramiko'] = {
        'hostname': '127.0.0.1',
        'port': 2222,
        'username': 'bardino@nbi.ku.dk',
        # 'key_path': os.path.expanduser('~/.mig/id_rsa'),
        'key_path': None,
        'user_key': None,
    }
else:
    bench_hosts['openssh'] = {
        # 'hostname': 'escistore02.hpc.ku.dk',
        'hostname': 'dk-cert.migrid.org',
        'port': 22,
        'username': 'jones',
        # 'key_path': os.path.expanduser('~/.ssh/id_rsa'),
        'key_path': None,
        'user_key': None,
    }
    bench_hosts['paramiko'] = {
        # 'hostname': 'escistore02.hpc.ku.dk',
        'hostname': 'dk-cert.migrid.org',
        'port': 2222,
        'username': 'bardino@nbi.ku.dk',
        # 'key_path': os.path.expanduser('~/.mig/id_rsa'),
        'key_path': None,
        'user_key': None,
    }

enable_compression = False
#bench_sizes = [1, 1024, 16*1024, 256*1024, 1024*1024, 16*1024*1024, 256*1024*1024, 1024*1024*1024]
#bench_sizes = [1, 1024, 16*1024, 256*1024, 1024*1024, 16*1024*1024, 256*1024*1024]
bench_sizes = [1, 1024, 4*1024, 16*1024, 64*1024, 256*1024, 1024*1024,
               4*1024*1024, 16*1024*1024, 64*1024*1024, 256*1024*1024, 1024*1024*1024]
bench_sizes = [1, 1024, 4*1024, 16*1024, 64*1024, 256*1024, 1024 *
               1024, 4*1024*1024, 16*1024*1024, 64*1024*1024, 256*1024*1024]
#bench_sizes = [1, 1024, 16*1024, 256*1024, 1024*1024, 16*1024*1024]
#bench_sizes = [1, 1024]
bench_pattern = 'bench-sftp-%s-%d.bin'

# Timing results
put_time, get_time = {}, {}


def write_tmp(path, size):
    """Efficiently write dummy tmp file of given size in path"""
    print("Writing %db file for benchmark" % size)
    written = 0
    chunk_size = 1024
    chunks = size // chunk_size
    if chunks * chunk_size != size:
        chunks += 1
    bench_fd = open(path, 'wb')
    while written < size:
        cur_size = min(chunk_size, size - written)
        bench_fd.write('0'*cur_size)
        written += cur_size
    bench_fd.close()
    print("Wrote %db file for benchmark" % written)


def show_results(times, bench_sizes):
    """Pretty print results with ratio"""
    print()
    print("Results:")
    print("========")
    for (action, target) in times.items():
        output = {}
        output_order = [action] + list(target) + ['ratio']
        for field in output_order:
            output[field] = field + ' '*(16-len(field))
        target['ratio'] = {}
        for size in bench_sizes:
            output[action] += '\t%d' % size
            ratio = target['paramiko'][size] * 1.0 / \
                target['openssh'][size]
            target['ratio'][size] = ratio
            for name in target:
                output[name] += '\t%.2f' % target[name][size]
        for field in output_order:
            print(output[field])
        print()


def run_bench(conf, bench_specs):
    """Efficiently write dummy tmp file of given size in path"""
    times = {}
    times['get'] = {}
    times['put'] = {}
    for (name, target) in bench_specs.items():
        if target['key_path']:
            target['user_key'] = paramiko.DSSKey.from_private_key_file(
                target['key_path'])
        times['get'][name] = {}
        times['put'][name] = {}
        for size in bench_sizes:
            bench_path = bench_pattern % (name, size)
            # Create file to upload if necessary
            if not os.path.exists(bench_path):
                write_tmp(bench_path, size)
            print("Benchmarking %s sftp upload %db to %s" %
                  (name, size, target['hostname']))
            before = time.time()
            ssh_transport = paramiko.SSHClient()
            ssh_transport.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_transport.connect(target['hostname'], target['port'],
                                  username=target['username'],
                                  pkey=target['user_key'],
                                  compress=enable_compression)
            sftp = ssh_transport.open_sftp()
            sftp.put(remotepath=bench_path, localpath=bench_path)
            sftp.close()
            ssh_transport.close()
            after = time.time()
            times['put'][name][size] = after - before
            print("Finished %s sftp upload %db in %fs" %
                  (name, size, times['put'][name][size]))
            print("Benchmarking %s sftp download %db from %s" %
                  (name, size, target['hostname']))
            before = time.time()
            ssh_transport = paramiko.SSHClient()
            ssh_transport.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_transport.connect(target['hostname'], target['port'],
                                  username=target['username'],
                                  pkey=target['user_key'],
                                  compress=enable_compression)
            sftp = ssh_transport.open_sftp()
            sftp.get(remotepath=bench_path, localpath=bench_path)
            sftp.close()
            ssh_transport.close()
            after = time.time()
            times['get'][name][size] = after - before
            print("Finished %s sftp download %db in %fs" %
                  (name, size, times['get'][name][size]))

    show_results(times, bench_sizes)


if __name__ == '__main__':
    cfg = {}
    paramiko.util.log_to_file('bench-sftp.log')
    if sys.argv[1:]:
        local = (sys.argv[1].lower()[0] in ('t', 'y', '1'))
    run_bench(cfg, bench_hosts)
