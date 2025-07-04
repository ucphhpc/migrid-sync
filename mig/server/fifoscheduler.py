#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fifoscheduler - [insert a few words of module description on this line]
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

"""Strict FIFO Scheduler"""
from __future__ import absolute_import

from builtins import range
from mig.server.scheduler import Scheduler


class FIFOScheduler(Scheduler):

    """Strict FIFO Scheduler"""

    def __init__(self, logger, config):
        Scheduler.__init__(self, logger, config)
        self.name = 'FIFOScheduler'

    def schedule(self, resource_conf, must_match={}):
        """Find the next job to run on the resource
        This is a strict FIFO scheduler.
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

        for i in range(1):
            job = self.job_queue.get_job(i)

            # Ignore job which don't match the filter requirements

            for (key, val) in must_match.items():
                if key not in job or val != job[key]:
                    continue
            self.logger.debug('schedule treating job %d: %s' % (i,
                                                                job['JOB_ID']))
            if 'GO' == job['SCHEDULE_HINT']\
                    and resource_conf['RESOURCE_ID']\
                    in job['SCHEDULE_TARGETS']:
                job['EXEC_RESOURCE'] = resource_conf['RESOURCE_ID']
                self.logger.info('schedule: scheduled %s for execution at %s'
                                 % (job['JOB_ID'],
                                     resource_conf['RESOURCE_ID']))
                self.job_queue.dequeue_job(0)
                self.update_history(job, resource_conf)
                return job
            else:
                self.logger.debug('Schedule: job %s marked %s'
                                  % (job['JOB_ID'], job['SCHEDULE_HINT'
                                                        ]))

        # No job was found that can be executed on the resource

        self.logger.info('Schedule: found no suitable job for %s'
                         % resource_conf['HOSTURL'])
        return None
