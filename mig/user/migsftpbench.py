#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migsftpbench - sample paramiko-based sftp client benchmark
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# -- END_HEADER ---
#

"""Sample Paramiko-based sftp client benchmark.

Requires paramiko (http://pypi.python.org/pypi/paramiko) and thus PyCrypto
(http://pypi.python.org/pypi/pycrypto).

Run with:
python migsftpbench.py [MIG_ADDRESS] [MIG_PORT] [MIG_USERNAME] \
           [OPENSSH_ADDRESS] [OPENSSH_PORT] [OPENSSH_USERNAME]

where the optional
MIG_ADDRESS is the FQDN of the MiG native SFTP server (default is dk-io.migrid.org)
MIG_PORT is the port of the MiG native SFTP server (default is 2222)
MIG_USERNAME is the username for the MiG native SFTP server (default is -)
OPENSSH_ADDRESS is the FQDN of the OpenSSH SFTP server (default is dk-io.migrid.org)
OPENSSH_PORT is the port of the OpenSSH SFTP server (default is 22)
OPENSSH_USERNAME is the username for the OpenSSH SFTP server (default is -)

X_USERNAME can e.g be the username displayed on your personal MiG SFTP Setup
page. You will be interactively prompted for it if it is left to default or -
on the command line.

Benchmark sftp upload/download against paramiko and openssh sftp servers.
SSH agent is used for the auth.
"""

from __future__ import print_function

from builtins import input
import os
import subprocess
import sys
import time

import paramiko

migsftp_host = 'dk-io.migrid.org'
migsftp_port = 2222
migsftp_user = '-'
openssh_host = 'dk-io.migrid.org'
openssh_port = 22
openssh_user = '-'
enable_compression = False
bench_sizes = [1, 1024, 16 * 1024, 256 * 1024, 1024 * 1024, 16 * 1024 * 1024,
               256 * 1024 * 1024
               ]
bench_dir = '.upload-cache'
bench_pattern = 'bench-sftp-%s-%d.bin'


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
        bench_fd.write(b'0' * cur_size)
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
        output_order = [action] + list(target)
        for name in target:
            output_order.append(name + ' ratio')
        for field in output_order:
            output[field] = field + ' ' * (18 - len(field))
        for size in bench_sizes:
            output[action] += '\t%db' % size
            for name in target:
                try:
                    ratio = target[name][size] * 1.0 / \
                        target['openssh=openssh'][size]
                except KeyError:
                    ratio = 0.0
                output[name] += '\t%.3fs' % target[name][size]
                output[name + ' ratio'] += '\t%.3f' % ratio
        for field in output_order:
            print(output[field])
        print()


def create_missing_dirs(target):
    """Make sure all local and remote target dirs exist"""
    if not os.path.isdir(bench_dir):
        try:
            os.makedirs(bench_dir)
        except Exception as exc:
            print("Error: mkdir -p %s : %s" % (bench_dir, exc))
            sys.exit(1)
    if target['client'] == 'paramiko':
        ssh_transport = paramiko.SSHClient()
        # For safe and silent operation we try already known host keys
        ssh_transport.load_system_host_keys()
        try:
            ssh_transport.connect(target['hostname'],
                                  port=target['port'],
                                  username=target['username'],
                                  pkey=target['user_key'],
                                  compress=enable_compression)
            sftp = ssh_transport.open_sftp()
        except paramiko.ssh_exception.SSHException as exc:
            if 'known_hosts' in str(exc):
                print("Missing host pub key for requested server %s" %
                      target['hostname'])
                print("You need to provide it or have it in ~/.ssh/known_hosts")
                print(exc)
                sys.exit(1)
            else:
                raise exc
        if not bench_dir in sftp.listdir():
            sftp.mkdir(bench_dir)
        sftp.close()
        ssh_transport.close()
    elif target['client'] == 'openssh':
        batch_path = os.path.join(bench_dir, "mkdir")
        batch_fd = open(batch_path, 'w')
        batch_fd.write('mkdir %s\n' % (bench_dir))
        batch_fd.close()
        sftp_cmd = ['sftp', '-P', "%d" % target['port']]
        sftp_cmd += ['-b', batch_path]
        sftp_cmd += ['%s@%s' % (target['username'],
                                target['hostname'])]
        call = subprocess.Popen(sftp_cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        res = call.wait()


def run_bench(conf, bench_specs):
    """Run bechmark"""
    times = {}
    times['get'] = {}
    times['put'] = {}
    for (name, target) in bench_specs.items():
        times['get'][name] = {}
        times['put'][name] = {}
        if target['key_path']:
            if target['key_path'].find('ed25519') != -1:
                target['user_key'] = paramiko.Ed25519Key.from_private_key_file(
                    target['key_path'])
            else:
                target['user_key'] = paramiko.RSAKey.from_private_key_file(
                    target['key_path'])
        create_missing_dirs(target)
        for size in bench_sizes:
            bench_path = os.path.join(bench_dir, bench_pattern % (name, size))
            # Create file to upload if necessary
            if not os.path.exists(bench_path):
                write_tmp(bench_path, size)
            print("Benchmarking %s sftp upload %db to %s" %
                  (name, size, target['hostname']))
            before = time.time()
            if target['client'] == 'paramiko':
                ssh_transport = paramiko.SSHClient()
                # For safe and silent operation we try already known host keys
                ssh_transport.load_system_host_keys()
                ssh_transport.connect(target['hostname'], target['port'],
                                      username=target['username'],
                                      pkey=target['user_key'],
                                      compress=enable_compression)
                sftp = ssh_transport.open_sftp()
                if not bench_dir in sftp.listdir():
                    sftp.mkdir(bench_dir)
                sftp.put(remotepath=bench_path, localpath=bench_path)
                sftp.close()
                ssh_transport.close()
            elif target['client'] == 'openssh':
                batch_path = bench_path.replace("bench-", "put-bench-")
                batch_fd = open(batch_path, 'w')
                batch_fd.write('put %s %s\n' % (bench_path, bench_path))
                batch_fd.close()
                sftp_cmd = ['sftp', '-P', "%d" % target['port']]
                sftp_cmd += ['-b', batch_path]
                sftp_cmd += ['%s@%s' % (target['username'],
                                        target['hostname'])]
                call = subprocess.Popen(sftp_cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                res = call.wait()
                if not res == 0:
                    print("ERROR: sftp returned %d:\n%s" %
                          (res, call.stdout.read()))
            after = time.time()
            times['put'][name][size] = after - before
            print("Finished %s sftp upload %db in %fs" %
                  (name, size, times['put'][name][size]))
            print("Benchmarking %s sftp download %db from %s" %
                  (name, size, target['hostname']))
            before = time.time()
            if target['client'] == 'paramiko':
                ssh_transport = paramiko.SSHClient()
                # For safe and silent operation we try already known host keys
                ssh_transport.load_system_host_keys()
                ssh_transport.connect(target['hostname'], target['port'],
                                      username=target['username'],
                                      pkey=target['user_key'],
                                      compress=enable_compression)
                sftp = ssh_transport.open_sftp()
                sftp.get(remotepath=bench_path, localpath=bench_path)
                sftp.close()
                ssh_transport.close()
            elif target['client'] == 'openssh':
                batch_path = bench_path.replace("bench-", "get-bench-")
                batch_fd = open(batch_path, 'w')
                batch_fd.write('get %s %s\n' % (bench_path, bench_path))
                batch_fd.close()
                sftp_cmd = ['sftp', '-P', "%d" % target['port']]
                sftp_cmd += ['-b', batch_path]
                sftp_cmd += ['%s@%s' % (target['username'],
                                        target['hostname'])]
                call = subprocess.Popen(sftp_cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                res = call.wait()
                if not res == 0:
                    print("ERROR: sftp returned %d:\n%s" %
                          (res, call.stdout.read()))
            after = time.time()
            times['get'][name][size] = after - before
            print("Finished %s sftp download %db in %fs" %
                  (name, size, times['get'][name][size]))

    show_results(times, bench_sizes)


if __name__ == '__main__':
    cfg = {}
    paramiko.util.log_to_file('bench-sftp.log')
    bench_hosts = {}
    if sys.argv[1:]:
        migsftp_host = sys.argv[1]
    if sys.argv[2:]:
        migsftp_port = int(sys.argv[2])
    if sys.argv[3:] and sys.argv[3] != '-':
        migsftp_user = sys.argv[3]
    else:
        migsftp_user = input('MiG SFTP Username: ')
    if sys.argv[4:]:
        openssh_host = sys.argv[4]
    if sys.argv[5:]:
        openssh_port = int(sys.argv[5])
    if sys.argv[6:] and sys.argv[6] != '-':
        openssh_user = sys.argv[6]
    else:
        openssh_user = input('OpenSSH Username: ')

    bench_hosts['paramiko=paramiko'] = {
        'client': 'paramiko',
        'hostname': migsftp_host,
        'port': migsftp_port,
        'username': migsftp_user,
        # 'key_path': os.path.expanduser('~/.ssh/id_rsa-nopw'),
        # 'key_path': os.path.expanduser('~/.mig/id_rsa'),
        'key_path': None,
        'user_key': None,
    }
    bench_hosts['openssh=paramiko'] = {
        'client': 'openssh',
        'hostname': migsftp_host,
        'port': migsftp_port,
        'username': migsftp_user,
        # 'key_path': os.path.expanduser('~/.ssh/id_rsa-nopw'),
        # 'key_path': os.path.expanduser('~/.mig/id_rsa'),
        'key_path': None,
        'user_key': None,
    }
    if openssh_host:
        bench_hosts['paramiko=openssh'] = {
            'client': 'paramiko',
            'hostname': openssh_host,
            'port': openssh_port,
            'username': openssh_user,
            # 'key_path': os.path.expanduser('~/.ssh/id_rsa-nopw'),
            # 'key_path': os.path.expanduser('~/.ssh/id_rsa'),
            'key_path': None,
            'user_key': None,
        }
        bench_hosts['openssh=openssh'] = {
            'client': 'openssh',
            'hostname': openssh_host,
            'port': openssh_port,
            'username': openssh_user,
            # 'key_path': os.path.expanduser('~/.ssh/id_rsa-nopw'),
            # 'key_path': os.path.expanduser('~/.ssh/id_rsa'),
            'key_path': None,
            'user_key': None,
        }

    run_bench(cfg, bench_hosts)
