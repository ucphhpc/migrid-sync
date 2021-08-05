#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# server - [insert a few words of module description on this line]
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

"""Server class used for simulating servers that handle users
and resources
"""

import time

from mig.server.jobqueue import JobQueue
from mig.server.fairfitscheduler import FairFitScheduler


class Server:

    """Serversimulation"""

    id = ''
    job_queue = None
    scheduler = None
    job_queue = None
    done_queue = None
    users = None
    resources = None
    peers = None
    nextid = 0
    migrated_jobs = 0
    returned_jobs = 0
    conf = None

    def __init__(
        self,
        id,
        logger,
        conf,
    ):

        self.id = id
        self.logger = logger
        self.conf = conf
        self.job_queue = JobQueue(logger)
        self.done_queue = JobQueue(logger)
        self.scheduler = FairFitScheduler(logger, conf)

        # self.scheduler = FirstFitScheduler(logger, conf)

        self.scheduler.attach_job_queue(self.job_queue)
        self.scheduler.attach_done_queue(self.done_queue)
        self.users = self.scheduler.users
        self.resources = self.scheduler.resources
        self.servers = self.scheduler.servers
        self.peers = self.scheduler.peers

    def submit(
        self,
        user_id,
        length,
        maxprice,
        vgrid,
    ):

        self.logger.info('%s received job from %s', self.id, user_id)

        # handle job

        job_id = "%s-%s" % (user_id, self.nextid)
        job = {}
        job['JOB_ID'] = job_id
        self.nextid += 1
        job['OWNER'] = job['USER_CERT'] = user_id
        job['CPUTIME'] = length
        job['MAXPRICE'] = maxprice
        job['CPUCOUNT'] = 1
        job['NODECOUNT'] = 1
        job['MEMORY'] = 1
        job['DISK'] = 1
        job['ARCHITECTURE'] = 'X86'
        job['RUNTIMEENVIRONMENT'] = []
        job['RECEIVED_TIMESTAMP'] = time.gmtime()
        job['QUEUED_TIMESTAMP'] = time.gmtime()
        job['MIGRATE_COUNT'] = "0"
        job['VGRID'] = vgrid

        # Enqueue job

        qlen = self.job_queue.queue_length()
        self.job_queue.enqueue_job(job, qlen)

        # Update user list with this job

        user_conf = {'USER_ID': user_id}

        # This will leave existing users unchanged while new users are created correctly

        user = self.scheduler.update_users(user_conf)
        self.scheduler.update_seen(user)

        # link job to user for continued monitoring

        user['QUEUE_HIST'].pop(0)
        user['QUEUE_HIST'].append(job)
        user['QUEUE_CNT'] += 1

        return True

    def request(
        self,
        res_id,
        length,
        minprice,
        vgrid,
    ):

        res_conf = {'RESOURCE_ID': res_id}
        res = self.scheduler.find_resource(res_conf)
        if not res:

            # create basic configuration

            res['RESOURCE_ID'] = res_id

            # So far unused attributes

            res['CPUCOUNT'] = 1
            res['NODECOUNT'] = 1
            res['MEMORY'] = 1
            res['DISK'] = 1
            res['ARCHITECTURE'] = 'X86'
            res['RUNTIMEENVIRONMENT'] = []

            # UpdateResources need MINPRICE

            res['MINPRICE'] = minprice
            res['CPUTIME'] = length
            res['VGRID'] = vgrid
            res = self.scheduler.update_resources(res)

        # Update/add these in any case

        res['MINPRICE'] = minprice
        res['CPUTIME'] = length

        self.scheduler.update_seen(res)

        # Job price and diff fields are automatically set during scheduling

        job = self.scheduler.schedule(res)

        if job:
            self.logger.info(
                '%s scheduled job %s to %s (%s, %s, %s)',
                self.id,
                job['JOB_ID'],
                res_id,
                res['LOAD'],
                res['CUR_PRICE'],
                res['LOAD_MULTIPLY'],
            )
        else:
            self.logger.info(
                '%s scheduled empty job to %s (%s, %s, %s)',
                self.id,
                res_id,
                res['LOAD'],
                res['CUR_PRICE'],
                res['LOAD_MULTIPLY'],
            )

        self.scheduler.update_price(res)

        return job

    def return_finished(self, res_id, job):

        # Hand back finished job to server

        self.scheduler.finished_job(res_id, job)

    def sleep(self):
        self.logger.debug('%s sleeping')

    def migrate_jobs(self):

        # Migrate all jobs that can be executed cheaper at a remote resource

        local_jobs = self.job_queue.queue_length()
        migrate_count = 0

        if not self.peers.keys():
            return 0

    # Use previously collected resource statuses for price directed migration

        for i in range(local_jobs):

            # queue shrinks as we migrate jobs so i may go out of range

            next_i = i - migrate_count
            job = self.job_queue.get_job(next_i)
            job_id = job['JOB_ID']

            # self.logger.debug("migrate_jobs: inspecting job %s", job_id)

            if 'SCHEDULE_HINT' not in job:

                # self.logger.debug("new job %s not marked yet", job_id)

                pass
            elif job['SCHEDULE_HINT'].startswith('MIGRATE '):
                server = job['SCHEDULE_HINT'].replace('MIGRATE ', '')
                server_conf = self.peers[server]['obj']
                self.logger.info('%s migrating job %s to %s', self.id,
                                 job_id, server)
                success = self.migrate_job(job, server_conf)
                if success:
                    job = self.job_queue.dequeue_job(next_i)
                    migrate_count += 1
                else:
                    self.logger.error(
                        'Migration to %s failed! leaving job %s at index %d', server, job['JOB_ID'], next_i)
            else:

                # self.logger.debug("%s not marked for migration", job_id)

                pass

            # Limit number of migrated jobs to avoid thrashing

            if migrate_count >= self.conf.migrate_limit:
                break

        self.logger.info('%s actually migrated %d jobs', self.id,
                         migrate_count)

        self.migrated_jobs += migrate_count

        return migrate_count

    def migrate_job(self, job, server):
        del job['SCHEDULE_HINT']

    # Add or increment migration counter

        migrate_count = int(job['MIGRATE_COUNT']) + 1
        job['MIGRATE_COUNT'] = "%s" % migrate_count

        qlen = server.job_queue.queue_length()
        server.job_queue.enqueue_job(job, qlen)
        return True

    def return_result(self):

        # Return migrated jobs to source

        done_jobs = self.done_queue.queue_length()
        return_count = 0
        local_count = 0

    # Use previously collected resource statuses for price directed migration

        for i in range(done_jobs):

            # queue shrinks as we migrate jobs so i may go out of range

            next_i = i - (return_count + local_count)
            job = self.done_queue.get_job(next_i)
            job_id = job['JOB_ID']

            # self.logger.info("return_result: inspecting job %s", job_id)

            # Check if job returned to owner

            if self.scheduler.returned_job(job):
                job = self.done_queue.dequeue_job(next_i)

                # don't include local jobs in return counter

                local_count += 1
                continue

            # Otherwise try to pass it on to a closer peer

            # use propagated user migration cost to find shortest
            # path to user

            owner = self.scheduler.find_owner(job)
            user_conf = {'USER_ID': owner}
            user = self.scheduler.find_user(user_conf)

            # We may have treated a job that we don't have local owner
            # information for. If so, just leave job for later return.

            if not user:
                self.logger.info(
                    "return_result: don't know %s - delay return of %s", owner, job_id)
                continue

            peer_id = self.scheduler.user_direction(user)
            peer_dict = self.peers[peer_id]
            peer = peer_dict['obj']

            # found peer - move job there

            if self.return_job(job, peer):
                job = self.done_queue.dequeue_job(next_i)
                return_count += 1
                break

            # Limit number of returned jobs to avoid flooding

            if return_count >= self.conf.migrate_limit:
                break

        self.logger.info('%s actually returned %d local and %d remote jobs',
                         self.id, local_count, return_count)

        self.returned_jobs += return_count

        return return_count

    def return_job(self, job, server):
        qlen = server.done_queue.queue_length()
        server.done_queue.enqueue_job(job, qlen)
        return True

    def refresh_servers(self):
        """
        Update information system in scheduler
        """

        # Update local status
        # self.logger.info("refresh_servers: %s updating local status", self.id)

        self.scheduler.update_local_server()

        # Remove users and resources no longer available with this server
        # self.logger.info("refresh_servers: %s pruning users and resources", self.id)

        self.scheduler.prune_peer_resources(self.id, self.resources)
        self.scheduler.prune_peer_users(self.id, self.users)

        # self.logger.info("refresh_servers: %s removing stale data", self.id)

        self.scheduler.remove_stale_data()

        # Update the server information for all peers.

        for (peer_id, peer_dict) in self.peers.items():

            # self.logger.info("refresh_servers: %s, peer %s", self.id, peer_id)

            peer = peer_dict['obj']
            self.refresh_peer_status(peer)

        return True

    def refresh_peer_status(self, peer):

        # Extract peer status from ConfigParser
        # object, peer.
        # Use contents to update local version of
        # peer status information in scheduler.

        peer_servers = {}
        peer_resources = {}
        peer_users = {}

        for (name, server) in peer.servers.items():

            # self.logger.debug("refresh_peer_status: %s", name)

            peer_servers[name] = self.scheduler._clone_dict(server)

        for (name, resource) in peer.resources.items():

            # self.logger.debug("refresh_peer_status: %s", name)

            peer_resources[name] = self.scheduler._clone_dict(resource)
        for (name, user) in peer.users.items():

            # self.logger.debug("refresh_peer_status: %s", name)

            peer_users[name] = self.scheduler._clone_dict(user)

        self.scheduler.update_peer_status(peer.id, peer_servers,
                                          peer_resources, peer_users)

    def exchange_status(self):

        # migrate every time for now
        # Migrate using previous status and scheduling
        # information.

        self.migrate_jobs()
        self.return_result()

        self.refresh_servers()

        # print self.id, self.resources.keys()

    def simulate(self, timestep):

        # Handle resource and user requests

        # rand = random.random()

        # self.sleep()

        # communicate every time for now

        comm_freq = 1
        if timestep % comm_freq == 0:

            # Update local and remote information

            self.exchange_status()

            # Make sure jobs don't get stuck

            self.scheduler.filter_jobs()
        qlen = self.job_queue.queue_length()
        self.logger.info('%s: %d jobs in queue', self.id, qlen)
