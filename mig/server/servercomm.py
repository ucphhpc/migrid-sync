#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# servercomm - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

#
# Exchange server status data for use by scheduler, pricing, migration, etc
#

from __future__ import print_function
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import range
from io import BytesIO as LegacyStringIO
import os
import sys
import pwd
import time
import configparser

import pycurl

from mig.shared.base import client_id_dir
from mig.shared.fileio import pickle

server_section = 'serverstatus'
http_success = 200


def print_status(status):
    for section in status.sections():
        print('%s:' % section)
        for name in status.options(section):
            print(name, '=', status.get(section, name))

        print('')


def write_status(config, status):

    # Write current server information to WWW accessible file

    # Moved status to wwwuser to avoid mangling with DocumentRoot in apache conf
    # status_dir = config.server_home + config.server_fqdn

    status_dir = config.user_home + config.server_fqdn

    # make sure that path exists

    try:
        os.makedirs(status_dir, mode=0o755)
    except:

        # An exception is thrown if the leaf exists

        pass

    status_path = status_dir + '/' + config.server_fqdn + '.status'

    # TODO: check htaccess here

    try:
        filehandle = open(status_path, 'w')

        for section in status.sections():
            filehandle.write('[%s]\n' % section)
            for name in status.options(section):
                filehandle.write('%s = %s\n' % (name,
                                                status.get(section, name)))
            filehandle.write('\n')

        filehandle.close()
    except Exception as e:
        config.logger.error(
            'Error: failed to write server status to %s (%s)' % (status_path, e))
        return False

    return True


def put_data(
    config,
    filename,
    protocol,
    host,
    port,
    rel_path,
):

    try:
        inputfile = open(filename, 'rb')
    except:
        config.logger.error('Failed to open %s for reading!', filename)
        return (False, 'Invalid filename!')

    # Set size of file to be uploaded.

    size = os.path.getsize(filename)

    if port:
        url = '%s://%s:%s/%s' % (protocol, host, port, rel_path)
    else:
        url = '%s://%s/%s' % (protocol, host, rel_path)

    passphrase = ''
    try:
        pp_file = open(config.passphrase_file, 'r')
        passphrase = pp_file.readline().strip()
        pp_file.close()
    except:
        config.logger.error('Failed to read passphrase from file %s',
                            config.passphrase_file)
        return (-1, 'Failed to read passphrase from file')

    # Store output in memory

    output = LegacyStringIO()

    # Init cURL (not strictly necessary, but for symmetry with cleanup)

    pycurl.global_init(pycurl.GLOBAL_SSL)

    curl = pycurl.Curl()
    # Never use proxy
    curl.setopt(pycurl.PROXY, "")
    curl.setopt(pycurl.HTTPHEADER, ['User-Agent: MiG HTTP PUT'])
    curl.setopt(pycurl.PUT, 1)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, output.write)
    curl.setopt(pycurl.NOSIGNAL, 1)

    # Uncomment to get verbose cURL output including SSL negotiation
    # curl.setopt(curl.VERBOSE, 1)

    # We can not let the server block for very long

    curl.setopt(pycurl.CONNECTTIMEOUT, 5)
    curl.setopt(pycurl.TIMEOUT, 10)

    curl.setopt(pycurl.INFILE, inputfile)
    curl.setopt(pycurl.INFILESIZE, size)

    if protocol == 'https':
        curl.setopt(curl.SSLCERT, config.server_cert)
        curl.setopt(curl.SSLKEY, config.server_key)
        if passphrase:
            curl.setopt(curl.SSLKEYPASSWD, passphrase)

        # Path to CA certificates

        # To use NorduGRID default certificate path set:
        # curl.setopt(curl.CAPATH, "/etc/grid-security/certificates")

        if config.ca_dir:
            curl.setopt(curl.CAPATH, config.ca_dir)
        elif config.ca_file:

            # We use our own demo CA file specified in the configuration for now

            curl.setopt(curl.CAINFO, config.ca_file)

        # Workaround for broken host certificates:
        # ###################################################
        # Do not use this, but fix host cert + CA instead! #
        # ###################################################
        # VERIFYHOST should be 2 (default) unless remote cert can not be
        # verified using CA cert.
        # curl.setopt(curl.SSL_VERIFYHOST,1)
        # Similarly VERIFYPEER will then probably need to be set to 0
        # curl.setopt(curl.SSL_VERIFYPEER,0)

    try:
        curl.perform()
    except pycurl.error as e:

        # pycurl.error is an (errorcode, errormsg) tuple

        config.logger.error('cURL command failed! %s', e[1])
        return (404, 'Error!')

    http_status = curl.getinfo(pycurl.HTTP_CODE)

    # Clean up after cURL

    curl.close()
    pycurl.global_cleanup()

    if http_status == http_success:
        config.logger.info('PUT request succeeded')

        # Go to start of buffer

        output.seek(0)
        msg = output.readlines()
    else:

        # print msg

        config.logger.warning(
            'Server returned HTTP code %d, expected %d', http_status, http_success)

    inputfile.close()
    output.close()

    return (http_status, 'Success!')


def get_data(
    config,
    protocol,
    host,
    port,
    rel_path,
):

    if port:
        url = '%s://%s:%s/%s' % (protocol, host, port, rel_path)
    else:
        url = '%s://%s/%s' % (protocol, host, rel_path)

    passphrase = ''
    try:
        pp_file = open(config.passphrase_file, 'r')
        passphrase = pp_file.readline().strip()
        pp_file.close()
    except:
        config.logger.error('Failed to read passprase from %s',
                            config.passphrase_file)
        return None

    # Store output in memory

    output = LegacyStringIO()

    # Init cURL (not strictly necessary, but for symmetry with cleanup)

    pycurl.global_init(pycurl.GLOBAL_SSL)

    curl = pycurl.Curl()
    # Never use proxy
    curl.setopt(pycurl.PROXY, "")
    curl.setopt(pycurl.HTTPHEADER, ['User-Agent: MiG HTTP GET'])
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, output.write)
    curl.setopt(pycurl.NOSIGNAL, 1)

    # Uncomment to get verbose cURL output including SSL negotiation
    # curl.setopt(curl.VERBOSE, 1)

    # TODO: read timeout values from config?
    # We can not allow the server to block for very long

    curl.setopt(pycurl.CONNECTTIMEOUT, 5)
    curl.setopt(pycurl.TIMEOUT, 10)
    if protocol == 'https':
        curl.setopt(curl.SSLCERT, config.server_cert)
        curl.setopt(curl.SSLKEY, config.server_key)
        if passphrase:
            curl.setopt(curl.SSLKEYPASSWD, passphrase)

        # Path to CA certificates

        # To use NorduGRID default certificate path set:
        # curl.setopt(curl.CAPATH, "/etc/grid-security/certificates")

        if config.ca_dir:
            curl.setopt(curl.CAPATH, config.ca_dir)
        elif config.ca_file:

            # We use our own demo CA file specified in the configuration for now

            curl.setopt(curl.CAINFO, config.ca_file)

        # Workaround for broken host certificates:
        # ###################################################
        # Do not use this, but fix host cert + CA instead! #
        # ###################################################
        # VERIFYHOST should be 2 (default) unless remote cert can not be
        # verified using CA cert.
        # curl.setopt(curl.SSL_VERIFYHOST,1)
        # Similarly VERIFYPEER will then probably need to be set to 0
        # curl.setopt(curl.SSL_VERIFYPEER,0)

    # Clean up after cURL

    try:
        config.logger.info('get_data: fetch %s', url)
        curl.perform()
    except pycurl.error as e:

        # pycurl.error is an (errorcode, errormsg) tuple

        config.logger.error('cURL command failed! %s', e[1])
        return ''

    http_status = curl.getinfo(pycurl.HTTP_CODE)

    curl.close()
    pycurl.global_cleanup()

    server_status = configparser.ConfigParser()

    if http_status == http_success:

        # Go to start of buffer

        output.seek(0)
        try:
            server_status.readfp(output)
        except:
            config.logger.error('Failed to parse server status')
            return None
    else:
        config.logger.error(
            'Server returned HTTP code %d, expected %d', http_status, http_success)
        return None

    output.close()

    return server_status


def section_to_dict(
    conf,
    section,
    section_key,
    opt_conv=None,
):

    # Dump the section contents of a configparser object into a dictionary
    # Bind the section name to section_key int the dictionary
    # Apply opt_conv function to all options if supplied (allows change of case)

    section_dict = {}

    if conf.has_section(section):
        key = section_key
        if opt_conv == 'lower':
            key = section_key.lower()
        elif opt_conv == 'upper':
            key = section_key.upper()
        section_dict[key] = section

        for option in conf.options(section):
            key = option
            if opt_conv == 'lower':
                key = option.lower()
            elif opt_conv == 'upper':
                key = option.upper()
            section_dict[key] = conf.get(section, option)

            # This is a somewhat hack'ish way to get a string representation
            # of a list back to the actual list form.

            if section_dict[key].find('[') != -1:
                list_str = section_dict[key]

                # By setting __builtins__ to the empty dict we avoid trouble:
                # http://mail.python.org/pipermail/python-list/1999-July/008523.html

                section_dict[key] = eval(list_str, {'__builtins__': {}})
    return section_dict


def dict_to_section(conf, input_dict, section_key):
    """
    Dump the contents of a dictionary into a separate section
    configparser object.
    Use the dictionary value of section_key as the session name
    NB: Keys in input_dict are automatically lowercased in the section
    """

    if section_key not in input_dict:
        return False

    section = input_dict[section_key]
    if not conf.has_section(section_key):
        conf.add_section(section)

    for key in input_dict:
        if key != section_key:
            conf.set(section, key, "%s" % input_dict[key])

    return True


def post_data(config, scheduler):
    """
....Build and post a ConfigParser object with all the status
....details.
....Fill out status config object with default sections and
....values
...."""

    server_status = configparser.ConfigParser()

    # write status to config object

    for (server_fqdn, server) in scheduler.servers.items():
        print(server_fqdn)
        dict_to_section(server_status, server, 'SERVER_ID')

    for (res_fqdn, res) in scheduler.resources.items():
        print(res_fqdn)
        dict_to_section(server_status, res, 'RESOURCE_ID')

    for (user_id, user) in scheduler.users.items():
        print(user_id)
        dict_to_section(server_status, user, 'USER_ID')

    # Debug:

    print('\n--- Current Status ---')
    print_status(server_status)
    print('''
--- End of status ---
''')

    status = write_status(config, server_status)
    return status


def refresh_servers(config, scheduler):
    """
....Update information system in scheduler
...."""

    # Update local status

    scheduler.update_local_server()

    # Remove users and resources no longer available with this server

    scheduler.prune_peer_resources(config.mig_server_id,
                                   scheduler.resources)
    scheduler.prune_peer_users(config.mig_server_id, scheduler.users)

    scheduler.remove_stale_data()

    # Update the server information for all peers.

    for (peer_id, peer) in scheduler.peers.items():
        (protocol, server) = (peer['protocol'], peer['fqdn'])
        (port, path) = (peer['port'], peer['rel_path'])
        config.logger.info('refresh_servers: %s', server)
        peer_conf = get_data(config, protocol, server, port, path)
        if peer_conf:
            refresh_peer_status(config, scheduler, peer_id, peer_conf)
        else:
            config.logger.error('Failed to fetch server status for %s',
                                server)
            continue

    return True


def exchange_status(config, scheduler, counter):
    """
....Physically fetch remote status and post local status
...."""

    config.logger.debug('exchange_status: %d', counter)

    # communicate every time for now

    comm_freq = 1

    if counter % comm_freq == 0:

        # Use prevoius peer data for migration
        # since it was used to decide balancing
        # TODO: make sure we balance prices regularly to avoid jobs
        # getting stuck at a server that has no resources coming in

        balance_prices(config, scheduler)

        # BalanceQueues(config, scheduler)
        # Send results back to user

        return_done(config, scheduler)

        # Now update for use in next scheduling

        refresh_servers(config, scheduler)

        # Publish updated status

        post_data(config, scheduler)
    return True


def migrate_job(config, job, peer):
    protocol = 'https'
    port = ''

    server = peer['fqdn']

    # Remove schedule hint from job before migration

    del job['SCHEDULE_HINT']

    # Make sure legacy jobs don't fail

    if 'MIGRATE_COUNT' not in job:
        job['MIGRATE_COUNT'] = "0"

    # Add or increment migration counter

    migrate_count = int(job['MIGRATE_COUNT']) + 1
    job['MIGRATE_COUNT'] = "%s" % migrate_count

    # TODO: only upload if job is not already replicated at
    # remote server
    # TMP!

    steal_job = False

    if not steal_job:

        # upload pickled job to server

        client_dir = client_id_dir(job['USER_CERT'])
        mrsl_filename = config.mrsl_files_dir + client_dir + '/'\
            + job['JOB_ID'] + '.mRSL'
        result = pickle(job, mrsl_filename, config.logger)
        if not result:
            config.logger.error('Aborting migration of job %s (%s)',
                                job['JOB_ID'], result)
            return False

        dest = mrsl_filename

        # TMP!
        # upload_reply = put_data(config, mrsl_filename, protocol, server, port, dest)

        config.logger.warning('Actual migration disabled until fully supported'
                              )
        upload_reply = (-1,
                        'Actual migration disabled until fully supported'
                        )
        if upload_reply[0] != http_success:
            return False

    # migration_msg = ""
    # migration_reply = put_data(config, protocol, server, port, migration_msg)

    return True


def balance_prices(config, scheduler):

    # Find and migrate all jobs that can be executed cheaper at a remote
    # resource

    local_jobs = scheduler.job_queue.queue_length()
    migrate_count = 0

    # Use previously collected resource statuses for price directed migration

    for i in range(local_jobs):

        # queue shrinks as we migrate jobs so i may go out of range

        next_i = i - migrate_count
        job = scheduler.job_queue.get_job(next_i)
        job_id = job['JOB_ID']
        config.logger.debug('balance_prices: inspecting job %s', job_id)

        if 'SCHEDULE_HINT' not in job:
            config.logger.info('new job %s not marked yet', job_id)
        elif job['SCHEDULE_HINT'].startswith('MIGRATE '):
            server = job['SCHEDULE_HINT'].replace('MIGRATE ', '')
            print('peers:', scheduler.peers)
            peer = scheduler.peers[server]
            success = migrate_job(config, job, peer)
            if success:

                # TODO: this is a race!

                job = scheduler.job_queue.dequeue_job(next_i)

                # TODO: physically remove job file, too?

                migrate_count += 1
                break
            else:
                config.logger.error(
                    'Migration to %s failed! leaving job %s at index %d', server, job['JOB_ID'], next_i)
        else:
            config.logger.info('%s not marked for migration', job_id)

        if migrate_count >= config.migrate_limit:
            break

    config.logger.info('Actually migrated %d jobs', migrate_count)

    return migrate_count


def return_done(config, scheduler):
    config.logger.info('return_done: should return %d jobs from done_queue',
                       scheduler.done_queue.queue_length())
    return True


def refresh_peer_status(
    config,
    scheduler,
    peer,
    peer_conf,
):

    # Extract peer status from ConfigParser object, peer_conf.
    # Use contents to update local version of peer status information
    # in scheduler.

    peer_servers = {}
    peer_resources = {}
    peer_users = {}

    for title in peer_conf.sections():
        config.logger.debug('UpdatePeerStatus: %s', title)
        section_type = peer_conf.get(title, 'type')
        if section_type == 'server':
            entity = section_to_dict(peer_conf, title, 'server_id',
                                     'upper')
            peer_servers[title] = entity
        elif section_type == 'resource':
            entity = section_to_dict(peer_conf, title, 'resource_id',
                                     'upper')
            peer_resources[title] = entity
        elif section_type == 'user':
            entity = section_to_dict(peer_conf, title, 'user_id',
                                     'upper')
            peer_users[title] = entity
        else:
            print('UpdatePeerStatus: %s: unknown type: %s' % (title,
                                                              section_type))

    scheduler.UpdatePeerStatus(peer, peer_servers, peer_resources,
                               peer_users)
