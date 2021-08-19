#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# maxthroughputscheduler - [insert a few words of module description on this line]
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

"""Max Throughput Scheduler"""
from __future__ import absolute_import

from builtins import range
from mig.server.scheduler import Scheduler


class MaxThroughputScheduler(Scheduler):

    def __init__(self, logger, expire_after):
        Scheduler.__init__(self, logger, expire_after)
        self.name = 'MaxThrougputScheduler'

    def schedule(self, resource_conf, must_match={}):
        """Max Throughput Scheduler:
        Find the jobs that can be run on the resource and select
        the shortest one unless concurrent jobs can be found that
        allow higher throughput.
        Scheduling history will probably be necessary to detect
        the latter.

        Please note that this may end up as a multidimensional
        version of the 0-1 knapsack problem. Furthermore we may
        run into trouble since we can only schedule on job at a
        time and the next slot may very well be different: we
        need info about past and future timeslots!

        For now we always select the shortest job in the hope that
        it will reduce the time before we get a new timeslot.

        All jobs are filtered against must_match first so that only
        jobs that match all attribute values there are considered
        for scheduling.
        """

        self.logger.debug('schedule: %s' % self.name)

        qlen = self.job_queue.queue_length()
        if qlen == 0:
            self.logger.info('schedule: no jobs in queue')
            return None

        self.logger.info('schedule: %d job(s) in queue' % qlen)

        # First gather all jobs that fits resource to minimize
        # search space

        fit_list = []

        for i in range(0, qlen):
            job = self.job_queue.get_job(i)

            # Ignore job which don't match the filter requirements

            for (key, val) in must_match.items():
                if key not in job or val != job[key]:
                    continue
            self.logger.debug('Schedule treating job %d: %s' % (i,
                                                                job['JOB_ID']))
            if self.job_fits_resource(job, resource_conf):
                self.logger.debug('schedule: found suitable job')
                fit_list.append((i, job))

        if len(fit_list) == 0:

            # No job was found that can be executed on the resource

            self.logger.info('schedule: found no suitable job for %s'
                             % resource_conf['HOSTURL'])
            return None

        best_job = None
        best_fitness = -1
        best_i = -1
        for (i, job) in fit_list:
            self.logger.debug('schedule: %s' % job['JOB_ID'])
            job_fitness = int(job['CPUTIME'])
            if job_fitness < best_fitness or best_fitness < 0:
                best_job = job
                best_i = i
                best_fitness = job_fitness

        self.job_queue.dequeue_job(best_i)
        self.update_history(job, resource_conf)

        self.logger.info('schedule: returning best job: %s %d %f'
                         % (best_job['JOB_ID'], best_i, best_fitness))
        return best_job
