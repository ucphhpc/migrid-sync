#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# simulation - simulate distributed servers exchanging jobs
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""MiG simulation of a setup with a number of resources, users and servers"""

# import pychecker.checker

from __future__ import print_function
from __future__ import absolute_import

import getopt
import ConfigParser
import logging
import math
import random
import os
import sys
import time

from mig.simulation.user import User
from mig.simulation.resource import Resource
from mig.simulation.server import Server
from mig.shared.configuration import Configuration


def usage():
    print('Usage:', sys.argv[0], '[OPTIONS] SETUP')
    print('OPTIONS:')
    print('\t-h/--help')
    print('\t-d/--debug loglevel')
    print("\t\twhere loglevel is in 'logging.(DEBUG|INFO|WARN|ERROR)'")
    print('\t-e/--expire seconds')
    print('\t-f/--frequency statusfrequency')
    print('\t-l/--log logfile')
    print('\t-m/--migratecost cost')
    print('\t-r/--random seed')
    print('\t-s/--steps timesteps')
    print('\t-t/--topology layout')
    print("\t\twhere layout is in '(linear|ring|full|mesh|cube|star)'")
    print('SETUP:')
    print("\t'#SERVERS:#RESOURCES:#USERS' string")
    print('\t\tor')
    print('\tConfigParser formatted scenario description file')


def server_to_dict(server, migrate_cost):

    # Generate a dictionary that is suitable for use in peers

    server_dict = {}
    server_dict['fqdn'] = server.id
    server_dict['obj'] = server
    server_dict['migrate_cost'] = migrate_cost

    return server_dict


def set_peers(servers, topology, migrate_cost):

    # Fill in peer dictionaries according to topology.
    # Don't insert server objects directly into peers - use dicts instead

    index = 0
    server_cnt = len(servers)
    server_names = servers.keys()
    server_list = servers.values()

    print('Using', topology, 'topology')

    if topology == 'ring':
        for server in server_list:
            prev = (index - 1) % server_cnt
            next = (index + 1) % server_cnt
            if prev != index:
                server.peers[server_names[prev]] = \
                    server_to_dict(server_list[prev], migrate_cost)
            if prev != next and next != index:
                server.peers[server_names[next]] = \
                    server_to_dict(server_list[next], migrate_cost)
            index += 1
    elif topology == 'linear':
        for server in server_list:
            prev = max(index - 1, 0)
            next = min(index + 1, server_cnt - 1)
            if prev != index:
                server.peers[server_names[prev]] = \
                    server_to_dict(server_list[prev], migrate_cost)
            if prev != next and next != index:
                server.peers[server_names[next]] = \
                    server_to_dict(server_list[next], migrate_cost)
            index += 1
    elif topology == 'star':
        server_name = servers.keys()[0]
        server = servers[server_name]
        for (peer_name, peer) in servers.items():
            if server_name != peer_name:
                server.peers[peer_name] = server_to_dict(peer,
                                                         migrate_cost)
                peer.peers[server_name] = server_to_dict(server,
                                                         migrate_cost)
    elif topology == 'mesh':

        # fill a square from left to right, top to bottom:
        # -start in topmost left corner and fill in to the right until the end
        # of the row is reached. Then continue from left in the next row.

        x = math.ceil(math.pow(server_cnt, 0.5))
        y = int(math.ceil(server_cnt * 1.0 / x))
        x = int(x)

        # row = ""

        for server in server_list:
            i = index % x
            j = index // x
            above = (j - 1) * x + i
            below = (j + 1) * x + i
            left = (j * x + i) - 1
            right = j * x + i + 1

            # if i == 0:
            #    print row
            #    row = ""
            # row = row + " " + server.id

            if j - 1 >= 0:
                (peer_name, peer) = (server_names[above],
                                     server_list[above])
                server.peers[peer_name] = server_to_dict(peer,
                                                         migrate_cost)
            if j + 1 < y and below < server_cnt:
                (peer_name, peer) = (server_names[below],
                                     server_list[below])
                server.peers[peer_name] = server_to_dict(peer,
                                                         migrate_cost)
            if i - 1 >= 0:
                (peer_name, peer) = (server_names[left],
                                     server_list[left])
                server.peers[peer_name] = server_to_dict(peer,
                                                         migrate_cost)
            if i + 1 < x and right < server_cnt:
                (peer_name, peer) = (server_names[right],
                                     server_list[right])
                server.peers[peer_name] = server_to_dict(peer,
                                                         migrate_cost)

            index += 1
    elif topology == 'full':

        # print row
        # elif topology == "cube":

        for (server_name, server) in servers.items():
            for (peer_name, peer) in servers.items():
                if server_name != peer_name:
                    server.peers[peer_name] = server_to_dict(peer,
                                                             migrate_cost)
    else:
        print('Unsupported topology:', topology)

    for server in servers.values():
        print(server.id, 'peers', server.peers.keys())


def show_status(level):
    for server in servers.values():
        qlen = server.job_queue.queue_length()
        print('%s: queued %d, migrated %d, returned %d' % (server.id,
                                                           qlen, server.migrated_jobs, server.returned_jobs))
        (avg_dist, avg_price, avg_paid, avg_diff, avg_load) = (0.0,
                                                               0.0, 0.0, 0.0, 0.0)
        (avg_done, avg_empty, avg_requests, avg_delay) = (0.0, 0.0,
                                                          0.0, 0.0)
        cnt = 0
        print(' res fqdn:\tdist\tload\tprice\tpaid\tdiff\tjobs\tdelay')
        for (res_fqdn, resource_conf) in server.resources.items():
            dist = server.scheduler.resource_distance(resource_conf)
            if level == 'local' and dist > 0:
                continue

            # print resource_conf

            avg_dist += float(dist)
            load = resource_conf['LOAD']
            avg_load += load
            cur_price = resource_conf['CUR_PRICE']
            avg_price += cur_price
            prices = resource_conf['PRICE_HIST']
            cur_paid = prices[len(prices) - 1]
            avg_paid += cur_paid
            price_diffs = resource_conf['DIFF_HIST']
            cur_diff = price_diffs[len(price_diffs) - 1]
            avg_diff += cur_diff
            done = resources[res_fqdn].jobs_done
            avg_done += 1.0 * done
            empty = resources[res_fqdn].jobs_empty
            avg_empty += 1.0 * empty
            requests = done + empty
            avg_requests += 1.0 * requests
            delay = resource_conf['EXPECTED_DELAY']
            avg_delay += delay
            print('  %s:\t%s\t%.3f\t%.2f\t%.2f\t%.2f\t%d/%d\t%.2f' % (
                res_fqdn,
                dist,
                load,
                cur_price,
                cur_paid,
                cur_diff,
                done,
                requests,
                delay,
            ))
            cnt += 1
        cnt = max(1, cnt)
        avg_dist /= cnt
        avg_load /= cnt
        avg_price /= cnt
        avg_paid /= cnt
        avg_diff /= cnt
        avg_done /= cnt
        avg_empty /= cnt
        avg_requests /= cnt
        avg_delay /= cnt
        print(' average:\t%.1f\t%.3f\t%.2f\t%.2f\t%.2f\t%.0f/%.0f\t%.2f'
              % (
                  avg_dist,
                  avg_load,
                  avg_price,
                  avg_paid,
                  avg_diff,
                  avg_done,
                  avg_requests,
                  avg_delay,
              ))

        print(' user ID:\tjobs\tprice\tdiff\tlast/min/avg/max paid\tlast/min/avg/max delay\tlast/min/avg/max dist')
        for (user_id, user_conf) in server.users.items():
            dist = server.scheduler.user_distance(user_conf)
            if level == 'local' and dist > 0:
                continue
            queue_jobs = user_conf['QUEUE_HIST']
            queue_total = len(queue_jobs)
            empty_cnt = queue_jobs.count({})
            jobs_queued = queue_total - empty_cnt
            queue_cnt = user_conf['QUEUE_CNT']
            done_jobs = user_conf['DONE_HIST']
            done_total = len(done_jobs)
            empty_cnt = done_jobs.count({})
            jobs_done = done_total - empty_cnt
            done_cnt = user_conf['DONE_CNT']

            if jobs_done > 0:
                last_done = done_jobs[done_total - 1]
                last_execute = time.mktime(last_done['EXECUTE_TIMESTAMP'
                                                     ])
                last_received = \
                    time.mktime(last_done['RECEIVED_TIMESTAMP'])
                last_paid = last_done['EXEC_PRICE']
                last_diff = last_done['EXEC_RAWDIFF']
                last_dist = int(last_done['MIGRATE_COUNT'])
            else:
                last_done = None
                last_execute = 0.0
                last_received = 0.0
                last_paid = 0.0
                last_diff = 0.0
                last_dist = 0

            last_delay = last_execute - last_received
            last_price = last_paid + last_diff

            (min_paid, avg_paid, max_paid) = (0.0, 0.0, 0.0)
            (min_delay, avg_delay, max_delay) = (0.0, 0.0, 0.0)
            (min_dist, avg_dist, max_dist) = (0.0, 0.0, 0.0)

            if jobs_done > 0:
                real_jobs = 0
                for job in done_jobs:

                    # Skip empty entries

                    if not job:
                        continue

                    real_jobs += 1

                    if real_jobs == 1:

                        # Init using first real job

                        job_paid = job['EXEC_PRICE']
                        job_execute = \
                            time.mktime(job['EXECUTE_TIMESTAMP'])
                        job_received = \
                            time.mktime(job['RECEIVED_TIMESTAMP'])
                        job_delay = job_execute - job_received
                        job_dist = int(job['MIGRATE_COUNT'])
                        min_paid = avg_paid = max_paid = job_paid
                        min_delay = avg_delay = max_delay = job_delay
                        min_dist = avg_dist = max_dist = job_dist
                        continue

                    # print job

                    job_paid = job['EXEC_PRICE']
                    job_execute = time.mktime(job['EXECUTE_TIMESTAMP'])
                    job_received = time.mktime(job['RECEIVED_TIMESTAMP'
                                                   ])
                    job_delay = job_execute - job_received
                    job_dist = int(job['MIGRATE_COUNT'])

                    avg_paid += job_paid
                    avg_delay += job_delay
                    avg_dist += job_dist
                    min_paid = min(job_paid, min_paid)
                    min_delay = min(job_delay, min_delay)
                    min_dist = min(job_dist, min_dist)
                    max_paid = max(job_paid, max_paid)
                    max_delay = max(job_delay, max_delay)
                    max_dist = max(job_dist, max_dist)

                avg_paid /= jobs_done
                avg_delay /= jobs_done
                avg_dist /= jobs_done

            print('  %s:\t%d/%d\t%.2f\t%.2f\t%.2f/%.2f/%.2f/%.2f\t%d/%d/%.2f/%d\t\t%d/%d/%.2f/%d'
                  % (
                      user_id,
                      done_cnt,
                      queue_cnt,
                      last_price,
                      last_diff,
                      last_paid,
                      min_paid,
                      avg_paid,
                      max_paid,
                      last_delay,
                      min_delay,
                      avg_delay,
                      max_delay,
                      last_dist,
                      min_dist,
                      avg_dist,
                      max_dist,
                  ))
            cnt += 1


# ## Main ###

server_cnt = 1
resource_cnt = 1
user_cnt = 1

timesteps = 100
status_freq = 20
topology = 'ring'
migrate_cost = '1.0'
seed = None

logginglevel = 'logging.INFO'

# logginglevel = "logging.WARN"

log_name = 'simulation.log'

input_name = ''
override_steps = None
override_freq = None
override_top = None
override_expire = None
override_migrate = None
override_seed = None

servers = {}
resources = {}
users = {}

# Parse command line

try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'hd:e:f:l:m:r:s:t:', [
        'help',
        'debug=',
        'expire=',
        'frequency=',
        'log=',
        'migratecost=',
        'random=',
        'steps=',
        'topology=',
    ])
except getopt.GetoptError as e:
    print('Error: ' + e.msg)
    usage()
    sys.exit(1)

for (opt, val) in opts:
    if opt in ('-h', '--help'):
        usage()
        sys.exit(0)
    elif opt in ('-d', '--debug'):
        logginglevel = val
    elif opt in ('-e', '--expire'):
        try:
            override_expire = int(val)
        except ValueError as e:
            print('Error: invalid expire argument %s - expected integer'
                  % val)
            print(e)
            sys.exit(1)
    elif opt in ('-f', '--frequency'):
        try:
            override_freq = int(val)
        except ValueError as e:
            print('Error: invalid frequency argument %s - expected integer'
                  % val)
            print(e)
            sys.exit(1)
    elif opt in ('-l', '--log'):
        log_name = val
    elif opt in ('-m', '--migratecost'):
        override_migrate = val
    elif opt in ('-r', '--random'):
        override_seed = val
    elif opt in ('-s', '--steps'):
        try:
            override_steps = int(val)
        except ValueError as e:
            print('Error: invalid steps argument %s - expected integer'
                  % val)
            print(e)
            sys.exit(1)
    elif opt in ('-t', '--topology'):
        override_top = val
    else:
        print('Error: unknown option: %s' % opt)
        sys.exit(1)

logfile = os.path.expanduser(log_name)
logger = logging.getLogger('simulation_logger')
hdlr = logging.FileHandler(logfile)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)

logger.setLevel(eval(logginglevel))

logger.info(' --- Setting up simulation --- ')

if len(args) != 1:
    usage()
    sys.exit(1)

arg = args[0]
if arg.count(':') == 2:
    vals = []
    parts = arg.split(':')
    for cnt in parts:
        try:
            val = int(cnt)
            vals.append(val)
        except ValueError as e:
            print('Error: invalid argument %s - expected integer' % cnt)
            print(e)
            sys.exit(1)

    server_cnt = vals[0]
    resource_cnt = vals[1]
    user_cnt = vals[2]
    entity_cnt = server_cnt + resource_cnt + user_cnt

    if override_seed:
        seed = override_seed
    if override_steps:
        timesteps = override_steps
    if override_freq:
        status_freq = override_freq
    if override_top:
        topology = override_top
    if override_migrate:
        migrate_cost = override_migrate

    try:
        print(timesteps)
        timesteps = int(timesteps)
        expire = timesteps
        status_freq = int(status_freq)
    except ValueError as e:
        print('Error: invalid argument %s - expected integer' % timesteps)
        print(e)
        sys.exit(1)

    if override_expire:
        expire = override_expire

    for i in range(server_cnt):
        name = 'server-%d' % i

        # Dummy conf to allow use of conf.attributes
        # Use own conf for each server to avoid sharing

        config = Configuration('MiGserver.conf')
        config.expire_after = expire
        config.mig_server_id = name

        # Override any peers read from peer conf

        config.peers = {}
        servers[name] = Server(name, logger, config)

    for i in range(resource_cnt):
        name = 'resource-%d' % i
        index = random.randint(0, server_cnt - 1)
        server = servers.values()[index]
        logger.info('setting up %s connected to %s', name, server.id)
        resources[name] = Resource(
            name,
            logger,
            0.8,
            "%s" % (42.0 + i / 3.0),
            server,
            [''],
        )

    for i in range(user_cnt):
        name = 'user-%d' % i
        index = random.randint(0, server_cnt - 1)
        server = servers.values()[index]
        logger.info('setting up %s connected to %s', name, server.id)
        users[name] = User(
            name,
            logger,
            0.3,
            "%s" % (56.5 + i),
            server,
            [''],
        )
else:

    input_name = arg
    input_path = os.path.expanduser(input_name)
    if not os.path.isfile(input_path):
        print('Error: input file %s not found!' % input_name)
        sys.exit(1)
    input_files = [input_path]
    scenario = ConfigParser.ConfigParser()

    # Set up a minimum of default options

    general = 'general'
    scenario.add_section(general)
    defaults = {
        'topology': topology,
        'timesteps': "%d" % timesteps,
        'status_frequency': "%s" % status_freq,
        'expire': "%s" % timesteps,
        'migrate_cost': "%s" % migrate_cost,
        'seed': "%s" % seed,
    }
    for (opt, val) in defaults.items():
        scenario.set(general, opt, val)

    scenario.read(input_files)

    # command line values overrides config value

    if override_seed:
        scenario.set(general, 'seed', "%s" % override_seed)
    if override_steps:
        scenario.set(general, 'timesteps', "%s" % override_steps)
    if override_freq:
        scenario.set(general, 'status_frequency', "%s" % (override_freq))
    if override_top:
        scenario.set(general, 'topology', override_top)
    if override_migrate:
        scenario.set(general, 'migrate_cost', override_migrate)

    # read out possibly updated values

    for opt in defaults.keys():
        defaults[opt] = scenario.get(general, opt)

    topology = defaults['topology']
    migrate_cost = defaults['migrate_cost']
    print('topology', topology)
    try:
        timesteps = int(defaults['timesteps'])
        expire = timesteps
        seed = eval(defaults['seed'])
        status_freq = int(defaults['status_frequency'])
    except ValueError as e:
        print('Error: invalid argument %s - expected integer' % defaults)
        print(e)
        sys.exit(1)

    if override_expire:
        expire = override_expire

    scenario.set(general, 'expire', expire)

    (server_cnt, user_cnt, resource_cnt) = (0, 0, 0)
    server_confs = {}
    resource_confs = {}
    user_confs = {}

    for fqdn in scenario.sections():
        if fqdn == general:
            continue
        entity = {'fqdn': fqdn, 'type': ''}
        for opt in scenario.options(fqdn):
            entity[opt] = scenario.get(fqdn, opt)

        if entity['type'] == 'server':
            server_cnt += 1
            server_confs[fqdn] = entity
        elif entity['type'] == 'resource':
            resource_cnt += 1
            resource_confs[fqdn] = entity
        elif entity['type'] == 'user':
            user_cnt += 1
            user_confs[fqdn] = entity
        else:
            print('Error: entity %s lacks type!' % fqdn)
            sys.exit(1)

    entity_cnt = server_cnt + resource_cnt + user_cnt

    for (name, conf) in server_confs.items():

        # Dummy conf to allow use of conf.attributes
        # Use own conf for each server to avoid sharing

        config = Configuration('dummy.conf')
        config.expire_after = expire
        config.mig_server_id = name

        # Override any peers read from peer conf

        config.peers = {}
        servers[name] = Server(name, logger, config)

    for (name, conf) in resource_confs.items():
        server_fqdn = conf['server']
        server = servers[server_fqdn]
        prob = float(conf['request_probability'])
        minprice = conf['minprice']
        logger.info('setting up %s connected to %s', name, server.id)
        resources[name] = Resource(
            name,
            logger,
            prob,
            minprice,
            server,
            [''],
        )

    for (name, conf) in user_confs.items():
        server_fqdn = conf['server']
        server = servers[server_fqdn]
        prob = float(conf['submit_probability'])
        maxprice = conf['maxprice']
        logger.info('setting up %s connected to %s', name, server.id)
        users[name] = User(
            name,
            logger,
            prob,
            maxprice,
            server,
            [''],
        )

set_peers(servers, topology, migrate_cost)

logger.info('Starting simulation')

start = time.time()

print('Seeding random with: %s' % seed)
random.seed(seed)
for step in range(timesteps):
    logger.info('step %d', step)
    entities = servers.values() + resources.values() + users.values()
    remain = len(entities)
    while remain > 0:
        index = random.randint(0, remain - 1)
        entity = entities[index]
        entities[index:index + 1] = []
        entity.simulate(step)
        remain = len(entities)

    if step % status_freq == 0:
        print('step', step)
        show_status('local')

end = time.time()

logger.info(' --- End of simulation --- ')

runtime = end - start

print('Final state after %d steps' % timesteps)
show_status('all')

print('Actual runtime %3.2f s' % runtime)

sys.exit(0)
