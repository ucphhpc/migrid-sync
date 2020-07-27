#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# randomscheduler - [insert a few words of module description on this line]
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

"""Random Scheduler"""

import random

from scheduler import Scheduler


class RandomScheduler(Scheduler):

    """Random scheduler"""

    def __init__(self, logger, config):
        Scheduler.__init__(self, logger, config)
        self.name = 'RandomScheduler'

    # Override dummy general scheduling algorithm

    def schedule(self, resource_conf, must_match={}):
        """Random Scheduler
        Find the jobs that fit resource and choose one of
        them at random.
        All jobs are filtered against must_match first so that only
        jobs that match all attribute values there are considered
        for scheduling.
        """

        # Mark jobs not suitable for execution at resource

        self.filter_jobs(resource_conf)

        qlen = self.job_queue.queue_length()
        if qlen == 0:
            self.logger.info('schedule: no jobs in queue')
            return None

        self.logger.info('schedule: %d job(s) in queue', qlen)

        fit_list = []

        for i in range(0, qlen):
            job = self.job_queue.get_job(i)

            # Ignore job which don't match the filter requirements

            for (key, val) in must_match.items():
                if key not in job or val != job[key]:
                    continue
            self.logger.debug('Schedule treating job %d: %s', i,
                              job['JOB_ID'])
            if 'GO' == job['SCHEDULE_HINT']\
                 and resource_conf['RESOURCE_ID']\
                 in job['SCHEDULE_TARGETS']:
                self.logger.debug('schedule: found suitable job %s',
                                  job['JOB_ID'])
                self.logger.debug('Resource: %s',
                                  resource_conf['RESOURCE_ID'])
                fit_list.append((i, job))
            else:
                self.logger.debug('schedule: job %s marked %s',
                                  job['JOB_ID'], job['SCHEDULE_HINT'])

        if len(fit_list) == 0:
            self.logger.info('schedule: found no suitable job for %s',
                             resource_conf['RESOURCE_ID'])
            return None

        random_index = random.randint(0, len(fit_list) - 1)
        self.logger.debug('schedule: randomly selected index %d',
                          random_index)
        (i, job) = fit_list[random_index]

        job['EXEC_RESOURCE'] = resource_conf['RESOURCE_ID']
        self.job_queue.dequeue_job(i)
        self.update_history(job, resource_conf)

        self.logger.info('schedule: randomly selected job: %s',
                         job['JOB_ID'])

        # just return last job while testing

        return job


