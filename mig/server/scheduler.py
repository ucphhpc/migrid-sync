#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# scheduler - base scheduler class used by all schedulers
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

"""General Scheduler framework"""

import calendar
import fnmatch
import re
import time

# Exponential delay penalty

from math import exp, floor

import shared.safeeval as safeeval
from jobqueue import print_job
from shared.resource import anon_resource_id
from shared.vgrid import vgrid_access_match, validated_vgrid_list


class Scheduler:

    """Base scheduler class to inherit from"""

    name = 'Scheduler'

    # Associated job queues

    job_queue = None
    done_queue = None

    # Associated logger

    logger = None

    # Associated configuration

    conf = None

    # Job history (last x jobs handled by scheduler)

    history = None

    # Maximum number of history entries

    history_backlog = 100

    # TODO: change all times to hours or minutes instead of seconds
    # unit length in seconds - thus 3600 is one hour

    unit_length = 3600

    # List of dictionaries representing the associated users.

    users = None
    user_backlog = 100

    # List of dictionaries representing the known resources.
    # Each dictionary contains details like load, min_price and price multiplier

    resources = None
    res_backlog = 100

    # minimum seconds to keep cache entries after LAST_SEEN (one week)

    cache_ttl = ((60 * 60) * 24) * 7

    # List of dictionaries representing the known servers.

    servers = None

    # List of dictionaries representing the status of peer servers.
    # This is used for directing job migration

    peers = None

    # High and Low watermarks for resource load - 0.25 means that 25% of resource
    # jobrequests are given a job (average)

    lo_load = 0.45

    # hi_load can similarly be set to represent 85% load

    hi_load = 0.85

    target_load = 0.75

    # Resource min prices are multiplied by a price multiplier to get current
    # price.
    # Obviously this value should always be >= 1.0 to honor min prices.
    # When the resources are heavily loaded (load > high watermark)
    # the multiplier should keep increasing.
    # Similarly the multiplier should keep decreasing under low load
    # The multipliers are adjusted in steps of multiply_delta

    multiply_delta = 0.001

    # Pure integer or float expressions can contain numbers and a dot

    float_expr = '^[0-9.]+$'
    float_re = re.compile(float_expr)

    # Simple price expressions can contain numbers, parenthesis and
    # simple arithmetic operators

    simple_expr = '^[0-9.()+*/-]+$'
    simple_re = re.compile(simple_expr)

    illegal_price = -42.0
    reschedule_interval = 1800
    __schedule_fields = {
        'SCHEDULE_TIMESTAMP': None,
        'SCHEDULE_HINT': None,
        'EXPECTED_DELAY': None,
        'SCHEDULE_TARGETS': [],
        'EXEC_PRICE': None,
        'EXEC_DIFF': None,
        'EXEC_RAWDIFF': None,
        }

    def __init__(self, logger, config):
        self.conf = config
        self.logger = logger
        self.logger.debug('initialised scheduler with job expire after %d secs'
                           % self.conf.expire_after)

        # Init dynamic structures here to avoid sharing between objects

        self.history = []
        self.users = {}
        self.resources = {}
        self.servers = {}
        self.peers = config.peers
        self.update_local_server()

    def _clone_dict(self, dictionary):
        """ Clone contents of dictionary """

    # TODO: Find out if a built-in method exists for this operation

        clone = {}
        for key in dictionary.keys():
            clone[key] = dictionary[key]
        return clone

    def _clone_job(self, job):
        return self._clone_dict(job)

    def attach_job_queue(self, job_queue):

        # Bind supplied job_queue to this scheduler

        self.job_queue = job_queue
        self.update_local_server()

    def attach_done_queue(self, done_queue):

        # Bind supplied done_queue to this scheduler

        self.done_queue = done_queue
        self.update_local_server()

    def set_cache(self, cache):

        # Bind supplied cache to this scheduler and expire old entries

        (self.servers, self.resources, self.users) = cache
        for entities in (self.servers, self.resources, self.users):
            self.expire_entitites(entities)
        self.update_local_server()

    def get_cache(self):

        # Extract cache from this scheduler

        return (self.servers, self.resources, self.users)

    def server_migrate_cost(self, server_id):
        server_conf = {'SERVER_ID': server_id}
        server = self.find_server(server_conf)
        cost = float(server['MIGRATE_COST'])
        return cost

    def resource_migrate_cost(self, resource_conf):
        server_id = resource_conf['SERVER']
        cost = self.server_migrate_cost(server_id)
        return cost

    def user_migrate_cost(self, user_conf):
        server_id = user_conf['SERVER']
        cost = self.server_migrate_cost(server_id)
        return cost

    def server_distance(self, server_id):
        server = {'SERVER_ID': server_id}
        server = self.find_server(server)
        dist = int(server['DISTANCE'])
        return dist

    def resource_distance(self, resource_conf):
        server_id = resource_conf['SERVER']

        dist = self.server_distance(server_id)
        return dist

    def user_distance(self, user_conf):
        server_id = user_conf['SERVER']
        dist = self.server_distance(server_id)
        return dist

    def server_direction(self, server_id):
        server = {'SERVER_ID': server_id}
        server = self.find_server(server)
        direction = server['MIGRATE_DIRECTION']
        return direction

    def resource_direction(self, resource_conf):
        server_id = resource_conf['SERVER']
        direction = self.server_direction(server_id)
        return direction

    def user_direction(self, user_conf):
        server_id = user_conf['SERVER']
        direction = self.server_direction(server_id)
        return direction

    def updated_data(self, cur_entity, new_entity):

        # Check if new_entity contains new data

        if not cur_entity:

            # No existing data for entity

            return True
        try:
            cur_timestamp = float(cur_entity['LAST_SEEN'])
            new_timestamp = float(new_entity['LAST_SEEN'])
        except:
            self.logger.warning('updated_data: failed to get timestamp! %s %s'
                                 % (cur_entity, new_entity))
            return False

        if cur_timestamp >= new_timestamp:
            return False

        self.logger.debug('found new data for entity (%f, %f)'
                           % (cur_timestamp, new_timestamp))
        return True

    def outdated_data(self, entity, expire_after):

        # Check if entity contains outdated data

        try:
            timestamp = float(entity['LAST_SEEN'])
        except:
            self.logger.warning('outdated_data: failed to get timestamp! %s'
                                 % entity)
            return True

        now = time.time()

        if timestamp + expire_after < now:
            return True
        elif timestamp > now:
            self.logger.warning('found time in the future! (%f, %f) %s'
                                 % (timestamp, now, entity))

        # self.logger.info("found valid data for entity (%f, %f)" % \
        #                 (timestamp, now))

        return False

    def relevant_update(self, cur_server, new_server):

        # Never update with outdated data

        if self.outdated_data(new_server, self.conf.expire_peer):
            self.logger.debug('ignoring stale information for %s'
                               % new_server['SERVER_ID'])
            return False
        elif not self.updated_data(cur_server, new_server):
            self.logger.debug('ignoring stale information for %s'
                               % new_server['SERVER_ID'])
            return False

        # Don't try to extract migrate costs if no existing server data

        if not cur_server:
            self.logger.info('found new server %s'
                              % new_server['SERVER_ID'])
            return True

        # Make sure this path has same or cheaper cost

        try:
            cur_cost = self.server_migrate_cost(cur_server['SERVER_ID'])
            new_cost = float(new_server['MIGRATE_COST'])
        except Exception, exc:
            self.logger.warning('relevant_update: get migrate cost failed! %s %s (%s)'
                                 % (cur_server, new_server, exc))
            return False

        if cur_cost < new_cost:
            self.logger.info('ignoring expensive path to %s'
                              % new_server['SERVER_ID'])
            return False

        self.logger.info('found same or cheaper path to %s (%f, %f)'
                          % (new_server['SERVER_ID'], cur_cost,
                         new_cost))
        return True

    def update_local_server(self):

        # Update local status
        # TODO: use "repr" instead of "str"?
        # ... even though it gives wrong lowest order values

        server = {}
        server['SERVER_ID'] = self.conf.mig_server_id
        server['FQDN'] = self.conf.server_fqdn
        if self.job_queue:
            server['QUEUED'] = str(self.job_queue.queue_length())
        else:
            server['QUEUED'] = str(0)
        server['LO_LOAD'] = str(self.lo_load)
        server['HI_LOAD'] = str(self.hi_load)
        server['TARGET_LOAD'] = str(self.target_load)
        server['EXPIRE_AFTER'] = str(self.conf.expire_after)
        server['DISTANCE'] = str(0)
        server['MIGRATE_COST'] = str(0.0)
        server['LAST_SEEN'] = repr(time.time())
        server['TYPE'] = 'server'
        return self.update_servers(server)

    def expire_entitites(self, entities):
        """Expire entities not seen for a long while"""

        for (entity_id, entity) in entities.items():
            if self.outdated_data(entity, self.cache_ttl):
                self.logger.info('Dropping stale cache data for %s'
                                  % entity_id)
                del entities[entity_id]
            else:
                self.logger.info('Keeping cache data for %s'
                                  % entity_id)

    def find_server(self, server_conf):

        # Find server with server_conf in server 'list'

        server_id = server_conf['SERVER_ID']

        # self.logger.debug("Findserver: %s" % server_id)

        server = {}
        if self.servers.has_key(server_id):
            server = self.servers[server_id]
        return server

    def update_servers(self, server_conf):

        # Update and return local stats for
        # server_conf

        inc_list = server_conf.keys()

        server = self.find_server(server_conf)
        if server:

            # self.logger.debug("update_servers: %s already in servers list" % server["SERVER_ID"])
            # Truncate conf options to catch changes

            for attr in inc_list:
                server[attr] = server_conf[attr]

            return server

        server = {}

        # Truncate conf options to catch changes

        for attr in inc_list:
            server[attr] = server_conf[attr]

        server_id = server['SERVER_ID']
        self.servers[server_id] = server
        return server

    def update_seen(self, entity):

        # Update entity timestamp

        now = time.time()
        if entity.has_key('QUEUED'):
            server = self.find_server(entity)
            server['FIRST_SEEN'] = server.get('FIRST_SEEN', now)
            server['LAST_SEEN'] = now
            server['TYPE'] = 'server'
        elif entity.has_key('USER_ID'):
            user = self.find_user(entity)
            user['FIRST_SEEN'] = user.get('FIRST_SEEN', now)
            user['LAST_SEEN'] = now
            user['SERVER'] = self.conf.mig_server_id
            user['TYPE'] = 'user'
        elif entity.has_key('CPUCOUNT'):
            resource = self.find_resource(entity)
            resource['FIRST_SEEN'] = resource.get('FIRST_SEEN', now)
            resource['LAST_SEEN'] = now
            resource['SERVER'] = self.conf.mig_server_id
            resource['TYPE'] = 'resource'
            resource['LAST_LOAD'] = resource['LOAD']

            # Always set last scheduling to 0 here and
            # only update if actually scheduling
            # something for this resource

            resource['SCHED_HIST'].pop(0)
            resource['SCHED_HIST'].append(0)
            resource['PRICE_HIST'].pop(0)
            resource['PRICE_HIST'].append(0.0)
            resource['DIFF_HIST'].pop(0)
            resource['DIFF_HIST'].append(0.0)
        else:
            self.logger.error('update_seen: unknown type: %s, %s'
                               % entity)

    def find_owner(self, job):

        # Find id of job owner

        owner = None
        if job.has_key('OWNER'):
            owner = job['OWNER']
        return owner

    def find_user(self, user_conf):

        # Find user with user_conf in user 'list'

        user_id = user_conf['USER_ID']

        # self.logger.debug("find_user: %s" % user_id)

        user = {}
        if self.users.has_key(user_id):
            user = self.users[user_id]
        return user

    def update_users(self, user_conf):

        # Update and return local stats for
        # user_conf

        inc_list = user_conf.keys()
        fill_in = False

        user = self.find_user(user_conf)
        if not user:
            fill_in = True

        # Truncate conf options to catch changes

        for attr in inc_list:
            user[attr] = user_conf[attr]

        # insert in case this is a new remote user

        user_id = user['USER_ID']
        self.users[user_id] = user

        if not fill_in:
            return user

        user['QUEUE_HIST'] = []

        # TODO: sched hist is difficult to maintain since jobs get scheduled concurrently
        # at different servers (vector clocks or similar are needed to allow correct SCHED_HIST p2p information)

        user['SCHED_HIST'] = []
        user['DONE_HIST'] = []
        while len(user['QUEUE_HIST']) < self.user_backlog:
            user['QUEUE_HIST'].append({})
            user['SCHED_HIST'].append({})
            user['DONE_HIST'].append({})
        user['QUEUE_CNT'] = 0
        user['SCHED_CNT'] = 0
        user['DONE_CNT'] = 0

        user_id = user['USER_ID']
        self.users[user_id] = user
        return user

    def find_resource(self, resource_conf):

        # Find resource with resource_conf in resource list

        res_id = resource_conf['RESOURCE_ID']

        # self.logger.debug("find_resource: %s" % res_id)

        res = {}
        if self.resources.has_key(res_id):
            res = self.resources[res_id]
        return res

    def update_resources(self, resource_conf):

        # Update and return local stats for resource_conf.
        # min_price is kept as expression to allow remote calculation
        #  for jobs with specific RE requirements
        # cur_price is the current min_price without REs

        inc_list = resource_conf.keys()
        fill_in = False

        res = self.find_resource(resource_conf)
        if not res:
            fill_in = True

        # Truncate to catch changes and existing attributes

        for attr in inc_list:
            res[attr] = resource_conf[attr]

        if fill_in:

            # Add a new local resource
            # self.logger.debug("update_resources: adding %s to resource list" % res_id)

            res['LOAD'] = 0.0
            res['LAST_LOAD'] = 0.0
            res['EXPECTED_DELAY'] = 0.0
            res['LOAD_MULTIPLY'] = 1.0
            res['CUR_PRICE'] = self.get_min_price(resource_conf, [])
            res['SCHED_HIST'] = []
            res['PRICE_HIST'] = []
            res['DIFF_HIST'] = []
            res['DONE_HIST'] = []
            while len(res['SCHED_HIST']) < self.res_backlog:
                res['SCHED_HIST'].append(0)
                res['PRICE_HIST'].append(0.0)
                res['DIFF_HIST'].append(0.0)
                res['DONE_HIST'].append(0)
            res['SCHED_CNT'] = 0
            res['DONE_CNT'] = 0

        # insert in case this is a new remote resource

        res_id = res['RESOURCE_ID']
        self.resources[res_id] = res
        return res

    # TODO: handle disappearing server-links somewhere
    # TODO: handle moved entities (detection: newer timestamp and different "SERVER")
    # TODO: make sure we follow vector clock update strategies...
    #       should we store all recent data with timestamp vector clocks even for
    #       non cheapest paths? monitoring and quick recovery on failing paths...

    def update_peer_status(
        self,
        peer_id,
        peer_servers,
        peer_resources,
        peer_users,
        ):

        # For each server dictionary that contains updated data update
        # connected users and resources if newer information is available

        for (server_id, server) in peer_servers.items():
            cur_conf = {'SERVER_ID': server_id}
            cur_server = self.find_server(cur_conf)

            # Include first hop in costs

            dist = int(server['DISTANCE']) + 1
            server['DISTANCE'] = str(dist)
            cost = float(server['MIGRATE_COST'])\
                 + float(self.peers[peer_id]['migrate_cost'])
            server['MIGRATE_COST'] = str(cost)
            server['MIGRATE_DIRECTION'] = peer_id

            # Update information if new server or if timestamp is
            # newer than current timestamp and path is same or cheaper

            if not self.relevant_update(cur_server, server):
                self.logger.info("update_peer_status: don't update %s"
                                  % server_id)
                self.remove_peer_resources(server_id, peer_resources)
                self.remove_peer_users(server_id, peer_users)
                continue

            self.logger.info('update_peer_status: update %s'
                              % server_id)

            # Update is relevant

            self.update_servers(server)

            # Prune users/resources no longer in peer_users/resources

            self.prune_peer_resources(server_id, peer_resources)
            self.prune_peer_users(server_id, peer_users)

            # Update users/resources from peer

            self.update_peer_resources(server_id, peer_resources)
            self.update_peer_users(server_id, peer_users)

        # update_peer_resources and update_peer_users removes all
        # resources and users bound to the server from
        # peer_resources/peer_users.
        # So any remaining entries at this point are unbound.

        if peer_users:
            self.logger.warning('Unbound user(s) from peer! %s'
                                 % peer_users)
        if peer_resources:
            self.logger.warning('Unbound resource(s) from peer! %s'
                                 % peer_resources)

        return True

    def prune_peer_resources(self, server_id, resources):

        # Remove resources that haven't been seen for a while at remote server
        # and thus has been expired there.
        # In that way information about dead resources propagates.

        for (cur_id, cur_res) in self.resources.items():
            if cur_res['SERVER'] != server_id:
                continue
            if not cur_id in resources.keys():

                # Remove resource from local list

                self.logger.info('prune_peer_resources: remove %s'
                                  % cur_id)
                del self.resources[cur_id]

    def prune_peer_users(self, server_id, users):

        # Same as function above just for users...

        for (cur_id, cur_user) in self.users.items():
            if cur_user['SERVER'] != server_id:
                continue
            if not cur_id in users.keys():

                # Remove user from local list

                self.logger.info('prune_peer_users: remove %s' % cur_id)
                del self.users[cur_id]

    def update_peer_resources(self, server_id, resources):
        for (res_id, res) in resources.items():

            # Ignore resources connected to other servers.
            # We still get data from non-peers since this
            # function gets called for all published
            # servers as long as they have relevant data.

            if res['SERVER'] != server_id:
                self.logger.info('update_peer_resources: ignore %s'
                                  % res_id)
                continue

            # Update if newer timestamp

            cur_conf = {'RESOURCE_ID': res_id}
            cur_res = self.find_resource(cur_conf)
            if self.updated_data(cur_res, res):

                # self.logger.info("update_peer_resources: update data for %s" % res_id)

                self.update_resources(res)
            else:

                # self.logger.info("update_peer_resources: ignore old data for %s" % res_id)

                pass

            # Remove resource from list to avoid further treatment
            # config.logger.debug("update_peer_resources: done with %s" % res_id)

            del resources[res_id]

    def update_peer_users(self, server_id, users):
        for (user_id, user) in users.items():

            # ignore users connected to other servers

            if user['SERVER'] != server_id:

                # self.logger.info("update_peer_users: ignore %s" % user_id)

                continue

            # Update if newer timestamp

            cur_conf = {'USER_ID': user_id}
            cur_user = self.find_user(cur_conf)
            if self.updated_data(cur_user, user):
                self.update_users(user)

            # Remove user from list to avoid further treatment
            # config.logger.debug("update_peer_users: done with %s" % user_id)

            del users[user_id]

    def remove_peer_resources(self, server_id, resources):
        for (res_id, res) in resources.items():

            # ignore resources connected to other servers

            if res['SERVER'] != server_id:

                # self.logger.debug("remove_peer_resources: ignore %s" % res_id)

                continue

            # Remove resource from list to avoid further treatment
            # self.logger.info("remove_peer_resources: remove %s from %s" % (res_id, server_id))

            del resources[res_id]

    def remove_peer_users(self, server_id, users):
        for (user_id, user) in users.items():

            # ignore users connected to other servers

            if user['SERVER'] != server_id:

                # self.logger.debug("remove_peer_users: ignore %s" % user_id)

                continue

            # Remove user from list to avoid further treatment
            # self.logger.info("remove_peer_users: remove %s from %s" % (user_id, server_id))

            del users[user_id]

    def remove_stale_data(self):

        # Remove data related to stale servers.
        #
        # If a local user/resource dies or moves the server removes it
        # from the next published status. So in time it will be removed
        # automatically from other servers too by ordinary pruning.
        #
        # If a server is no longer available we will notice here and
        # cascade the removal of all entities that are marked as
        # connected to that server.

        for (server_id, server) in self.servers.items():

            # self.logger.info("remove_stale_data: checking %s" % server_id)

            if self.outdated_data(server, self.conf.expire_peer):
                self.logger.info('Dropping stale data for %s'
                                  % server_id)
                del self.servers[server_id]
                self.remove_peer_resources(server_id, self.resources)
                self.remove_peer_users(server_id, self.users)
            else:

                # self.logger.info("Keeping data for %s" % server_id)

                pass

    def update_price(self, resource_conf):

        # Update resource price to fit current supply and demand

        res_dict = self.find_resource(resource_conf)
        if not res_dict:
            print 'Error: resource not found! %s' % resource_conf
            return False
        res_id = res_dict['RESOURCE_ID']

        # min_price = res_dict["MINPRICE"]

        sched_hist = res_dict['SCHED_HIST']
        price_hist = res_dict['PRICE_HIST']
        diff_hist = res_dict['DIFF_HIST']
        res_dict['LOAD'] = (1.0 * sched_hist.count(1))\
             / self.res_backlog

        # load = res_dict["LOAD"]

        short_len = 10
        short_load = (1.0 * sched_hist[self.res_backlog
                       - short_len:self.res_backlog].count(1))\
             / short_len
        mult = res_dict['LOAD_MULTIPLY']

        cur_sched = sched_hist[self.res_backlog - 1]
        cur_price = price_hist[self.res_backlog - 1]
        cur_diff = diff_hist[self.res_backlog - 1]

        # Drastic fall back if short_len requests in a row failed.
        # This should help adapt to sudden price drops.
        # Note that this reduction is repeated for every following failed
        # request, so the 0.9 multiplier is not insignificant!

        if short_load == 0.0 and mult > 1.0:
            res_dict['LOAD_MULTIPLY'] = 1 + 0.9 * (mult - 1)
            mult = res_dict['LOAD_MULTIPLY']
            self.logger.info('update_price: Fallback! multiplier decreased to %f'
                              % mult)

        if cur_sched == 0:

            # Didn't get a job so price should fall

            res_dict['LOAD_MULTIPLY'] -= self.multiply_delta
            res_dict['LOAD_MULTIPLY'] = max(mult, 1.0)
        elif cur_price == 0.0:

            # Got a free job - ignore

            pass
        elif cur_diff > 0.0:

            # Got a job so price should rise.
            # Careful not to rise more than cur_diff, though.
            # price_rise = new_price - cur_price =
            #  (mult + delta) * base_price - mult * base_price =
            #  delta * base_price = delta * cur_price / mult

            price_rise = (self.multiply_delta * cur_price) / mult
            if cur_diff >= price_rise:

                # still somewhat below expected maxprice

                res_dict['LOAD_MULTIPLY'] += self.multiply_delta
            else:

                # Close to maxprice: scale delta so that
                # cur_diff = prise_rise = delta * cur_price / mult
                # Round off delta to avoid precision issues

                prec = 1e16
                delta = floor(((prec * cur_diff) * mult) / cur_price)
                res_dict['LOAD_MULTIPLY'] += delta / prec

        # Updated multiplier automatically gets included from unitprice

        res_dict['CUR_PRICE'] = self.get_min_price(resource_conf, [])

        # self.logger.debug("update_price: %s, %s %f %f" % \
        #                 (res_id, min_price, load, load_multiply))

        return True

    def show_history(self):
        print 'History:'
        for job in self.history:
            print_job(job)

    def get_min_price(self, resource_conf, job_re):

        # Calculate current value of MINPRICE function for resource

        res_re = resource_conf['RUNTIMEENVIRONMENT']

        utc_time = time.gmtime()
        res_replace_map = {
            'hour': repr(utc_time.tm_hour),
            'wday': repr(utc_time.tm_wday),
            'yday': repr(utc_time.tm_yday),
            'date': repr(utc_time.tm_mday),
            'month': repr(utc_time.tm_mon),
            'year': repr(utc_time.tm_year),
            }

        # Replace required REs with 1 and rest with 0
        # print res_re

        for (re_name, re_list) in res_re:
            if re_name in job_re:

                # self.logger.debug("get_min_price: charging for RE: %s" % re_name)

                res_replace_map[re_name] = repr(1)
            else:

                # self.logger.debug("get_min_price: not charging for RE: %s" % re_name)

                res_replace_map[re_name] = repr(0)

        return self.unit_price(resource_conf, res_replace_map)

    def get_max_price(self, job):

        # Calculate current value of MAXPRICE function for job

        exec_delay = time.mktime(time.gmtime())\
             - time.mktime(job['RECEIVED_TIMESTAMP'])
        job_replace_map = {'exec_delay': repr(exec_delay)}
        return self.eval_price(job['MAXPRICE'], job_replace_map)

    def eval_price(self, price_string, replace_map):

        # Parse the price_string with replacements specified in replace_map
        # dictionary

        # The substitution and safe evaluation can be a real CPU hog.
        # Try to make the common case (simple price) fast by avoiding
        # substitution and safe evaluation if possible.

        expr = price_string

        # self.logger.debug("eval_price: %s %s" % (price_string, replace_map))

        if self.float_re.match(expr):

            # No need to evaluate expression at all before float()

            eval_func = None
            eval_price = expr
        elif self.simple_re.match(expr):

            # Need to do simple evaluation

            eval_func = safeeval.expr_eval
        else:
            for key in replace_map.keys():

                # self.logger.debug("%s : %s %s" % (price_string, key,
                #                 replace_map[key]))

                expr = expr.replace(key, replace_map[key])

                # self.logger.debug("%s" % expr)

            if self.simple_re.match(expr):

                # No more unknown parts - simple evaluation

                eval_func = safeeval.expr_eval
            else:

                # Still unknown contents - math evaluation

                eval_func = safeeval.math_expr_eval

        if eval_func:
            try:
                eval_price = eval_func(expr)
            except ValueError, err:
                self.logger.error('eval_price: illegal price expression: %s!'
                                   % price_string)
                self.logger.error('%s' % err)
                return self.illegal_price
            except Exception, err:
                self.logger.error('eval_price: evaluation of %s caused exception!'
                                   % price_string)
                self.logger.debug('%s' % err)
                return self.illegal_price

        # Make sure that price is actually a floating point number and not,
        # say, a list or something else we can't use as a price

        try:
            eval_price = float(eval_price)
        except TypeError:
            self.logger.error('eval_price: conversion of %s to float failed!'
                               % eval_price)
            return self.illegal_price

        # Treat negative price function values as zero cost

        if eval_price < 0.0:
            eval_price = 0.0

        return eval_price

    def update_history(self, job, resource_conf):

        # only called if job was scheduled

        job['EXECUTE_TIMESTAMP'] = time.gmtime()

        if len(self.history) >= self.history_backlog:
            del self.history[0]

        # Clone job to avoid problems with original

        hist_job = self._clone_job(job)
        self.history.append(hist_job)

        # self.logger.debug("update_history: %s added to history" % job["JOB_ID"])

        owner = self.find_owner(job)
        user_conf = {'USER_ID': owner}
        user = self.find_user(user_conf)
        if user:
            user['SCHED_HIST'].pop(0)

            # Clone job to avoid problems with original

            sched_job = self._clone_job(job)
            user['SCHED_HIST'].append(sched_job)
            user['SCHED_CNT'] += 1
        else:

            # Unfortunately we can't update schedule hist consistently for migrated jobs!
            # self.logger.debug("update_history: scheduled migrated job")

            pass

        res = self.find_resource(resource_conf)

        # Mark scheduling as succesful (always defaults to 0 if empty)

        res['SCHED_HIST'][self.res_backlog - 1] = 1
        res['SCHED_CNT'] += 1
        res['PRICE_HIST'][self.res_backlog - 1] = job['EXEC_PRICE']
        res['DIFF_HIST'][self.res_backlog - 1] = job['EXEC_RAWDIFF']

    def unit_price(self, resource_conf, replace_map):

        # Calculate the price of one MiG unit at the specified resource.
        # Extract the MINPRICE for the current time and apply the effect of
        # the current load to get the actual unit price.
        # self.logger.debug("unit_price: MINPRICE: %s" % \
        #                 resource_conf["MINPRICE"])

        res_id = resource_conf['RESOURCE_ID']

        if resource_conf.has_key('MINPRICE'):
            min_price = self.eval_price(resource_conf['MINPRICE'],
                    replace_map)
        else:
            min_price = 0.0
            self.logger.warning('unit_price: no MINPRICE for %s, using %f'
                                 % (res_id, min_price))
            self.logger.warning('unit_price: %s' % resource_conf)

        if min_price == self.illegal_price:
            self.logger.error("unit_price: failed to evaluate '%s'"
                               % resource_conf['MINPRICE'])

            # Set to something big to avoid free resource because of typos
            # ... Admin will probably notice no jobs and debug!
            # TODO: can we notify admin somehow? mark resource as broken?
            # we could add a price verification tool... or even include
            # check in reload

            min_price = 1000000000.0

        res = self.find_resource(resource_conf)
        load_multiply = 1.0

        # unit_price is called before the resource is in resources map

        if res:
            load_multiply = float(res['LOAD_MULTIPLY'])
        unit_price = min_price * load_multiply
        return unit_price

    def current_prices(self, job, res):

        # Returns a tuple with current job maxprice and resource price for
        # executing the job now.
        # If price is broken we just ignore it and leave job to expire.

        attr = 'MAXPRICE'
        try:
            cpucount = int(job['CPUCOUNT'])
            nodecount = int(job['NODECOUNT'])
            cputime = int(job['CPUTIME'])
        except:
            self.logger.error('current_prices: integer conversion in cpu_secs for %s failed!'
                               % job)

            # Make sure job_price - res_price is negative for now

            return (self.illegal_price, 0.0)

        cpu_secs = (cpucount * nodecount) * cputime
        units = cpu_secs / self.unit_length
        if cpu_secs % self.unit_length != 0:
            units += 1

        # Job prices are decided as current price times the job extent
        # since we must decide price now to be able to move payment to
        # temporary account.
        # Additionally fairness demands the price decision here.

        unit_price = self.get_min_price(res, job['RUNTIMEENVIRONMENT'])
        res_price = units * unit_price
        job_price = self.get_max_price(job)

        # self.logger.debug("current_prices: job %s, price %d, units %d" % \
        #                                (job["JOB_ID"], job_price, units))

        if job_price == self.illegal_price:
            self.logger.error("current_prices: job %s: failed to evaluate '%s'"
                               % (job['JOB_ID'], job[attr]))
        elif job_price < res_price:

            # self.logger.debug("current_prices: %s of job %s does not fit resource (%s,%s)" % (attr, job["JOB_ID"], job_price, res_price))

            pass
        else:

            # self.logger.debug("current_prices: %s of job %s fits resource (%s,%s)" % (attr, job["JOB_ID"], job_price, res_price))

            pass

        return (job_price, res_price)

    def job_fits_resource(self, job, res):

        # self.logger.info("scheduler examines job_id %s" % job["JOB_ID"])

        res_id = res['RESOURCE_ID']
        public_id = res_id
        if res.get('ANONYMOUS', True):
            public_id = anon_resource_id(public_id)
            
        # TODO: switch FORCEDDESTINATION jobs to use new RESOURCE field
        if job.has_key('FORCEDDESTINATION'):
            unique_resource_name = res['RESOURCE_ID']
            job_forced_dict = job['FORCEDDESTINATION']
            if job_forced_dict['UNIQUE_RESOURCE_NAME']\
                 == unique_resource_name:

                # self.logger.info("jobs forceddestination matches this resource (%s)" % unique_resource_name)

                return True
            else:

                # self.logger.info("jobs forceddestination does not match this resource (job: %s, res: %s)" % (job_forced_dict["UNIQUE_RESOURCE_NAME"], unique_resource_name))

                return False

        if job.get('RESOURCE', []):
            res_match = False
            for job_dest in job['RESOURCE']:
                if fnmatch.fnmatch(public_id, job_dest):
                    res_match = True
                    break
            if not res_match:
                return False

        checklist = ['NODECOUNT', 'CPUCOUNT', 'CPUTIME', 'DISK',
                     'MEMORY']

        # print "going to check if resource and jobs match (keywords %s)" % checklist

        for attr in job.keys():
            if attr == 'ARCHITECTURE':
                if job[attr] and job[attr] != res[attr]:

                    # self.logger.info("job_fits_resource: %s of job does not fit resource (%s,%s)" % (attr, job[attr], res[attr]))

                    return False
            if attr == 'JOBTYPE':

                # Backwards compatibility - batch only

                if not res.has_key(attr):
                    res[attr] = 'batch'

                # keyword to match all

                if 'all' == res[attr]:
                    continue

                # batch is a subset of bulk

                if 'bulk' == res[attr] and job[attr] == 'batch':
                    continue

                if job[attr] != res[attr]:
                    self.logger.info('job_fits_resource: %s of job does not fit resource (%s, %s)'
                             % (attr, job[attr], res[attr]))
                    return False
            if attr == 'SANDBOX':

                # self.logger.info("SANDBOX")
                # hack to ensure that a resource has a sandbox keyword

                if not res.has_key(attr):
                    res[attr] = False

                # do not schedule non-sandbox jobs on a sandbox resource

                if not job[attr] and res[attr]:

                    # job is not allowed to run in a sandbox resource
                    self.logger.info("job is not allowed to run on a sandbox resource")
                    return False

                # sandbox jobs on non-sandbox resources are ok, however

                # self.logger.info("SANDBOX DONE")

            if attr == 'PLATFORM':

                # Default value for PLATFORM is the empty string

                if not res.has_key('PLATFORM'):
                    res[attr] = ''

                if job[attr].upper() != res[attr].upper():

                    # Platforms don't match
                    # self.logger.info("Job has PLATFORM: (%s), doesn't match resource PLATFORM: (%s)" % (job[attr], res[attr]))

                    return False

            if attr not in checklist:
                continue

            # Simple ">" test for attributes in checklist

            try:
                if int(job[attr]) > int(res[attr]):

                    # self.logger.info("job_fits_resource: %s of job does not fit resource (%s,%s)" % (attr, job[attr], res[attr]))
                    # print "job_fits_resource: %s of job does not fit resource (%s,%s)" % (attr, job[attr], res[attr])

                    return False
            except Exception, exc:
                self.logger.error('job_fits_resource: %s check for %s vs %s failed! (%s, %s). Exception: %s'
                                   % (
                    attr,
                    job,
                    res,
                    job[attr],
                    res[attr],
                    exc,
                    ))
                return False

        # RUNTIMEENVIRONMENT checks - compare lists
        # REs look like [('POVRAY3.6', []), ('HKTEST', [('bla', 'bla2'), ('blaa', 'bla3')]), ('LOCALDISK', [])]
        # print "going to check that runtimeenvironments of job and resource match"

        for jre in job['RUNTIMEENVIRONMENT']:
            found = False
            for rre in res['RUNTIMEENVIRONMENT']:
                (res_name, res_val) = rre
                if jre == res_name:
                    found = True
                    break

            # found must be True, otherwise the job
            # cannot be executed on this resource

            if not found:

                # self.logger.info("RE %s from job not found in resource RE list: %s" % (jre, res["RUNTIMEENVIRONMENT"]))

                return False

        # Check VGRID
        # Force old jobs with VGRID string value to list form

        job['VGRID'] = validated_vgrid_list(self.conf, job)
        (match, job_vgrid, res_vgrid) = vgrid_access_match(
            self.conf, job['USER_CERT'], job, res_id.split('_')[0], res)
        self.logger.info('scheduler: res and job vgrid match: %s %s' % \
                         (res_vgrid, job_vgrid))
        res_name = job_name = 'Unknown'
        try:
            res_name = res['RESOURCE_ID']
            job_name = job['JOB_ID']
        except Exception, err:
            self.logger.error('scheduler: res or job name error: %s (%s) (%s)'
                              % (err, res, job))
        if match:
            job['RESOURCE_VGRID'] = res_vgrid
        else:

            # self.logger.info("Matching VGRID lists: %s (%s) vs %s (%s)" % \
            #                 (res["VGRID"], res_name, job["VGRID"], job_name))

            job['RESOURCE_VGRID'] = 'No_suitable_VGrid_found'

            # self.logger.info("Incompatible VGRID lists: %s (%s) vs %s (%s)" % \
            #                 (res["VGRID"], res_name, job["VGRID"], job_name))

            return False

        # self.logger.info("end job_fits_resource")

        return True

    def expire_jobs(self):
        """Traverse queue and remove jobs that are
        expired, i.e. jobs that have been queued for
        too long.
        Note: jobs only need to be *started* within
        expire_after time units after QUEUED_TIMESTAMP!
        They're not required to actually finish within
        that period.
        """

        expired = []

        # Expiry is disabled if set to 0 or negative

        if self.conf.expire_after <= 0:
            return expired

        qlen = self.job_queue.queue_length()

        # self.logger.debug("expire_jobs: qlen %d" % qlen)

        # Expire from back of queue to avoid index changes on removal

        for i in range(qlen - 1, -1, -1):
            job = self.job_queue.get_job(i)

            # self.logger.debug("expire_jobs treating job %d of %d:" % \
            #                 (i+1, qlen))

            queued_time = time.mktime(time.gmtime())\
                 - time.mktime(job['QUEUED_TIMESTAMP'])
            if queued_time > self.conf.expire_after:
                self.logger.info('expire_jobs: removing expired job %s (%f, %f)'
                                  % (job['JOB_ID'], queued_time,
                                 self.conf.expire_after))
                self.job_queue.dequeue_job(i)
                expired.append(job)

        if expired:
            self.logger.info('expire_jobs: expired %d job(s)'
                              % len(expired))

        return expired

    def filter_jobs(self, resource_conf={}):
        """Filter jobs in queue as part of job migration planning"""

        # schedule_filter includes fitness filter

        self.schedule_filter(resource_conf)

    def thrashing_penalty(self, job, res):
        """Penalize already migrated jobs to avoid thrashing"""

        # Make sure legacy jobs don't fail

        if not job.has_key('MIGRATE_COUNT'):
            job['MIGRATE_COUNT'] = str(0)

        migrate_count = int(job['MIGRATE_COUNT'])
        dist = self.resource_distance(res)

        # simple linear penalty so far

        return 2.0 * (migrate_count + dist)

    def migrate_penalty(self, job, res):
        dist = self.resource_distance(res)
        if dist == 0:
            return 0.0

        # TODO: extract sum of real file sizes - dummy value so far

        size = 1.0
        migrate_cost = self.resource_migrate_cost(res)
        thrashing_cost = self.thrashing_penalty(job, res)

        return size * migrate_cost + thrashing_cost

    def delay_penalty(self, job, res):
        """Delay penalty only kicks in as delay nears time to live (ttl).
        Before that happens it must be exact zero to avoid denying free
        jobs to run on free resources.
        """

        scale = 0.00005

        # NOTE: using ttl rather than expire_after unbalances prices!
        # (e.g. test-scenarios/asymmetric/4-8-16_free-vs-nonfree.input)
        # ttl = expire_after - (now - queued_timestamp)
        # queued_time = time.mktime(time.gmtime()) - time.mktime(job["QUEUED_TIMESTAMP"])
        # TODO: needs conversion when time base is changed
        # ttl = self.expire_after - queued_time
        # expire_factor = 16.0 / ttl

        if self.conf.expire_after < 60:
            expire_factor = 0.0
        else:
            expire_factor = 16.0 / self.conf.expire_after

        delay = float(res['EXPECTED_DELAY'])
        delay_penalty = scale * (exp(delay * expire_factor) - 1)

        # self.logger.debug("delay_penalty: %s : %f" % (delay, delay_penalty))

        if delay_penalty < 0.001:
            delay_penalty = 0.0

        # print "%f %f %f %f" % (queued_time, ttl, delay, delay_penalty)

        return delay_penalty

    def best_resource(self, job, request_res):
        """Generate list of suitable targets to make
        selection and probability approximation easier.
        """

        if request_res:
            request_id = request_res['RESOURCE_ID']
        else:
            request_id = ''
        local_resources = []
        remote_resources = []
        job_id = job['JOB_ID']

        # self.logger.debug("best_resource: inspecting job %s" % job_id)

        for (res_id, res) in self.resources.items():

            # self.logger.info("test job %s against %s" % (job_id, res_id))

            res_dist = self.resource_distance(res)

            # self.logger.info("%s is %d away" % (res_id, res_dist))

            # Note: We do'nt know future CPUTIME of other resources, but just
            # keep last requested time as a qualified guess

            if not self.job_fits_resource(job, res):

                # self.logger.info("best_resource: job %s does not fit %s" % (job_id, res_id))

                continue

            # self.logger.info("job %s fits %s" % (job_id, res_id))

            # Check if price is acceptable

            (job_price, res_price) = self.current_prices(job, res)
            raw_diff = job_price - res_price

            if res_dist > 0:
                migrate_penalty = self.migrate_penalty(job, res)
                price_diff = raw_diff - migrate_penalty

            delay_penalty = self.delay_penalty(job, res)
            price_diff = raw_diff - delay_penalty

            if price_diff < 0.0:

                # self.logger.info("ignoring %s (%.16e, %e, %e)" % \
                #                 (res_id, res_price,
                #                  job_price, delay_penalty))

                continue

            res['JOB_PRICE'] = res_price
            res['RAW_DIFF'] = raw_diff
            res['PRICE_DIFF'] = price_diff

            if res_dist > 0:
                remote_resources.append(res)
            else:
                local_resources.append(res)

        # Select the best resource for job in fit_resources list

        best = {
            'id': None,
            'res': None,
            'diff': None,
            'dist': None,
            'price': None,
            'raw': None,
            'equiv': None,
            }

        # Local resources are tested first

        for res in local_resources + remote_resources:
            res_id = res['RESOURCE_ID']
            res_dist = self.resource_distance(res)
            res_price = res['JOB_PRICE']
            price_diff = res['PRICE_DIFF']
            res_raw = res['RAW_DIFF']

            # self.logger.debug("job %s: pricediff %f on %s" % \
            #                   (job_id, price_diff, res_id))

            # previous loop assures that price_diffs are non-negative
            # Prefer shortest migration path to minimize  delay

            if not best['res'] or price_diff > best['diff']\
                 or price_diff == best['diff'] and res_dist\
                 < best['dist']:

                # self.logger.info("%s offers a better price (%f) for %s" % \
                # ........ (res_id, res_price, job_id))

                best = {
                    'id': res_id,
                    'res': res,
                    'diff': price_diff,
                    'dist': res_dist,
                    'price': res_price,
                    'raw': res_raw,
                    'equiv': [],
                    }
            elif price_diff == best['diff'] and res_dist == best['dist'
                    ]:

                # Append alternatives with same price

                best['equiv'].append(res_id)

        # if best["id"]:
            # self.logger.info("best price on %s before filter %s (%s, %s)" %\
            #                 (best["id"], best["price"], best["diff"],
            #                  best["raw"]))

        # Filter out expensive resources from possible targets
        # TODO: make percentage a config value
        # Allow 5% higher price if scheduled now
        # Note: percent issue with free resources

        best_local = []
        for res in local_resources:
            if best['price'] * 1.05 >= res['JOB_PRICE']:
                best_local.append(res)
        best_remote = []
        for res in remote_resources:
            if best['price'] * 1.05 >= res['JOB_PRICE']:
                best_remote.append(res)

        # print "best_local: %s" % best_local

        fit_count = len(best_local) + len(best_remote)
        schedule_chance = None
        if not request_res:

            # Filtering without a requesting resource

            pass
        elif request_res in best_local:

            # Prefer requesting resource if it is reasonably close to
            # or better than the rest

            res = request_res
            res_id = res['RESOURCE_ID']
            res_dist = 0
            res_price = res['JOB_PRICE']
            price_diff = res['PRICE_DIFF']
            res_raw = res['RAW_DIFF']

            # Scheduling chance estimate based on #local resources

            if fit_count == 1 or best['res'] == res:

                # No other suitable/better resource

                schedule_chance = 1.0
            else:

                # self.logger.debug("requesting resource %s offers a reasonable or better (%f) price (%f) for %s" % (res_id, schedule_chance, res_price, job_id))
                # Worse but still reasonable offer
                # TODO: should this be delay dependent?

                schedule_chance = 1.0 / fit_count

            equiv = best['equiv']
            best = {
                'id': res_id,
                'res': res,
                'diff': price_diff,
                'dist': res_dist,
                'price': res_price,
                'raw': res_raw,
                'equiv': equiv,
                }
        elif best['res'] and self.job_fits_resource(job, request_res):

            # Jobs that fit but are two far back in the queue should
            # still be considered to avoid receiving even more jobs...

            schedule_chance = 0.1 / fit_count

        if schedule_chance:

            # Update delay expectation

            request_res['EXPECTED_DELAY'] += schedule_chance\
                 * float(job['CPUTIME'])

            # self.logger.info("requesting resource %s updated expected delay to (%d)" % (res_id, request_res.get("EXPECTED_DELAY", -1)))

        # self.logger.info("returning best resource %s (%s, %s)" % (best["id"], best["price"], request_res.get("JOB_PRICE", None)))

        return best

    def fill_schedule(self, job):
        """Fill in any missing scheduling fields in job"""

        for (field, default) in self.__schedule_fields.items():
            job[field] = job.get(field, default)
        return job

    def copy_schedule(self, src, dst):
        """Copy schedule fields from src to dst job"""

        for field in self.__schedule_fields.keys():
            if src.has_key(field):
                dst[field] = src[field]
        return dst

    def clear_schedule(self, job):
        """Remove any scheduling fields from job - used e.g. after time outs"""

        for field in self.__schedule_fields.keys():
            if job.has_key(field):
                del job[field]
        return job

    def schedule_filter(self, resource_conf={}):
        """Filter all local jobs and mark any jobs for
        migration if they are better fit for being
        executed somewhere else.
        It is likely that we need to filter regularly even
        when no local resource requests a job.
        That is, we need to support the case where
        resource_conf is not set.

        TODO: run filter once in a while even if no
        jobrequests! otherwise jobs can get stuck at an
        idle server.

        mark all jobs that can be executed cheaper at a remote
        resource for migration.
        """

        self.logger.info('running schedule filter on queue (%s)'
                          % resource_conf)
        local_jobs = self.job_queue.queue_length()

        # Find current resource once and for all

        if resource_conf:
            request_res = self.find_resource(resource_conf)
            request_id = request_res['RESOURCE_ID']
            request_res['EXPECTED_DELAY'] = 0.0
        else:

            # Use dummy if no requesting resource

            request_res = {}
            request_id = ''

        # Use previously collected resource statuses for price directed
        # migration

        now = time.time()
        first_request = request_res.get('FIRST_SEEN', now)

        for i in range(local_jobs):
            best = None
            job = self.job_queue.get_job(i)
            job_id = job['JOB_ID']

            # Fill any missing fields for e.g. new jobs

            self.fill_schedule(job)

            # backwards compatible timestamp extraction (was float before)

            last_scheduled = job['SCHEDULE_TIMESTAMP']
            if not last_scheduled or isinstance(last_scheduled, float):
                last_scheduled = time.gmtime(0)
            schedule_time = calendar.timegm(last_scheduled)
            schedule_age = now - schedule_time

            # skip (re)schedule if each of these apply:
            # -resource was included in last scheduling
            # -we recently scheduled job

            if schedule_time > first_request and job['SCHEDULE_HINT']\
                 and schedule_age < self.reschedule_interval:

                # self.logger.info("cached schedule %s for %s" % \
                #                 (job["SCHEDULE_HINT"], job_id))

                continue

            # Reset schedule

            self.clear_schedule(job)
            self.fill_schedule(job)

            # Get a dictionary with details about best resource(s)

            best = self.best_resource(job, request_res)

            # Now mark job to use best resource

            job['SCHEDULE_TIMESTAMP'] = time.gmtime()
            if not best['res']:

                # self.logger.info("no resource offers a suitable price for %s (%s)" % \
                #                 (job_id, best))

                job['SCHEDULE_HINT'] = 'STAY'
                continue
            elif job['STATUS'] == 'FROZEN':

                # self.logger.debug("hold frozen job %s" % job_id)
                
                job['SCHEDULE_HINT'] = 'STAY'
                continue

            # Found best resource if we got this far

            if best['dist'] > 0:
                server = self.resource_direction(best['res'])

                # self.logger.debug("remote resource %s at %s offers the best price %f for %s" % (best_id, server, best_price, job_id))

                job['SCHEDULE_HINT'] = 'MIGRATE' + ' ' + server
            else:

                # self.logger.debug("local resource %s offers the best pricediff (%f) for %s (delay %f, equivs %s)" % \
                #                 (best["id"], best["diff"], job_id,
                #                  best["res"]["EXPECTED_DELAY"],
                #                  best["equiv"]))

                job['SCHEDULE_HINT'] = 'GO'

            job['SCHEDULE_TARGETS'] = [best['id']] + best['equiv']
            job['EXPECTED_DELAY'] = best['res']['EXPECTED_DELAY']
            job['EXEC_PRICE'] = best['price']
            job['EXEC_DIFF'] = best['diff']
            job['EXEC_RAWDIFF'] = best['raw']

        return True

    def returned_job(self, job):
        """Update user stats if job is back with owner"""

        owner = self.find_owner(job)
        user_conf = {'USER_ID': owner}
        user = self.find_user(user_conf)
        if user and self.user_distance(user) == 0:

            # local user - mark job done

            user['DONE_HIST'].pop(0)
            user['DONE_HIST'].append(job)
            user['DONE_CNT'] += 1

            # Make sure we catch missing scheduling information (migrated jobs)

            user['SCHED_CNT'] = max(user['SCHED_CNT'], user['DONE_CNT'])
            return True

        return False

    def finished_job(self, res_id, job):
        """Resource finished executing job:
        Any transport of job is handled independently
        in servercomm.
        """

        # Enqueue job for later handling

        qlen = self.done_queue.queue_length()
        self.done_queue.enqueue_job(job, qlen)

        resource_conf = {'RESOURCE_ID': res_id}
        res = self.find_resource(resource_conf)
        if not res:
            self.logger.error('finished_job: unknown resource %s'
                               % res_id)
            return 0

        res['DONE_HIST'].pop(0)
        res['DONE_HIST'].append(job)
        res['DONE_CNT'] += 1
        return res['DONE_CNT']

    def remaining_slot(self, job_list, resource_conf):
        """Return a resource conf where the sum of resources required
        by the jobs in job_list is subtracted from the resources
        available in resource_conf.
        """

        # First copy resource_conf

        res_conf = {}
        for (key, val) in resource_conf.items():
            res_conf[key] = val

        # Now subtract job resources requested

        for job in job_list:
            for key in ['MEMORY', 'DISK', 'NODECOUNT', 'CPUCOUNT']:
                res_conf[key] = '%s' % (int(res_conf[key])
                         - int(job[key]))
        return res_conf

    def backfill(self, best_job, resource_conf):
        """Return a list of jobs that can be used as backfill when
        running best_job on resource with resource_conf.
        That is jobs that fit within the total amount of resources,
        are allowed for bulk scheduling and belong to the same user.
        """

        backfill_list = []
        self.logger.info('backfill best: %(JOB_ID)s (%(JOBTYPE)s)'
                          % best_job)
        if 'bulk' != best_job['JOBTYPE']:
            return backfill_list
        while True:
            remaining = self.remaining_slot([best_job] + backfill_list,
                    resource_conf)
            self.logger.info('backfill remaining: %(CPUCOUNT)s %(NODECOUNT)s'
                              % remaining)
            next_job = self.schedule(remaining, must_match={'USER_CERT'
                    : best_job['USER_CERT'], 'JOBTYPE': 'bulk'})
            if not next_job:
                break
            self.logger.info('backfill next: %(JOB_ID)s (%(JOBTYPE)s)'
                              % next_job)
            backfill_list.append(next_job)
        return backfill_list

    def schedule(self, resource_conf, must_match={}):
        """This is a dummy scheduler to be subclassed"""

        err_str = \
            "schedule: You're not supposed to use this base class schedule() method directly! Please use one of the subclasses or create your own function to overload schedule()."
        self.logger.error(err_str)
        print err_str
        return None


