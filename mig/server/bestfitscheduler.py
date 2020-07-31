#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# bestfitscheduler - [insert a few words of module description on this line]
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

"""Best Fit Scheduler"""
from __future__ import absolute_import

from mig.server.scheduler import Scheduler


class BestFitScheduler(Scheduler):

    def __init__(self, logger, config):
        Scheduler.__init__(self, logger, config)
        self.name = 'BestFitScheduler'

    def fitness(self, job, resource_conf):

        # Dictionary with mapping from job attribute to fit multiplier.
        # The higher the fit multiplier, the more the total fitness will be
        # affected by fitting that particular attribute.

        priority_list = {
            'CPUCOUNT': 100,
            'NODECOUNT': 100,
            'CPUTIME': 60,
            'MEMORY': 30,
            'DISK': 10,
        }
        job_fitness = 0.0

        for attr in priority_list.keys():
            prio_mult = priority_list[attr]
            try:
                job_val = float(job[attr])
                res_val = float(resource_conf[attr])
            except:
                self.logger.error(
                    'fitness: float conversion for %s failed!', attr)
                continue

            if res_val == 0.0:

                # We already know that job fits so both must be 0, which is a
                # perfect fit. However a rate of 0/0 causes a ZeroDivisionError.

                fit_rate = 1.0
            else:
                fit_rate = job_val / res_val

            self.logger.debug('fitness: %s %f %d', attr, fit_rate,
                              prio_mult)
            job_fitness += fit_rate * prio_mult

        # Ordinary resources should avoid sandbox jobs unless there are no
        # other suitable jobs around

        if resource_conf.get('SANDBOX', False) != job.get('SANDBOX', False):
            job_fitness *= 0.0001

        self.logger.debug('fitness: %f', job_fitness)
        return job_fitness

    # Override dummy general scheduling algorithm

    def schedule(self, resource_conf, must_match={}):
        """Best Fit Scheduler:
        Find all the jobs that can run on the resource and select the one that
        fits 'best' i.e. fills out most of the available resources.
        The fitness function above is used to decide a fitness score for a job.
        All jobs are filtered against must_match first so that only
        jobs that match all attribute values there are considered
        for scheduling.
        """

        self.logger.debug('schedule: %s', self.name)

        # Mark jobs not suitable for execution at resource

        self.filter_jobs(resource_conf)

        qlen = self.job_queue.queue_length()
        if qlen == 0:

            # Actually we should never get here from grid_script, but anyway...

            self.logger.info('schedule: no jobs in queue')
            return None

        self.logger.info('schedule: %d job(s) in queue', qlen)

        best_job = None
        best_fitness = 0.0

        for i in range(0, qlen):
            job = self.job_queue.get_job(i)

            # Ignore job which don't match the filter requirements

            for (key, val) in must_match.items():
                if key not in job or val != job[key]:
                    continue

            # self.logger.debug("schedule treating job %d: %s", i, job['JOB_ID'])

            if 'GO' == job['SCHEDULE_HINT']\
                    and resource_conf['RESOURCE_ID']\
                    in job['SCHEDULE_TARGETS']:

                # self.logger.debug("schedule: found suitable job")

                job_fitness = self.fitness(job, resource_conf)

                # self.logger.info("schedule: job fitness: %s %f" % \
                #                 (job['JOB_ID'], job_fitness))

                if job_fitness > best_fitness:
                    best_job = job
                    best_i = i
                    best_fitness = job_fitness
            else:

                    # self.logger.info("schedule: new best fit: %s %f" % \
                    #                 (job['JOB_ID'], job_fitness))
                # self.logger.info("schedule: job %s marked %s" % \
                #                  (job["JOB_ID"], job["SCHEDULE_HINT"]))

                pass

        if not best_job:

            # No job was found that can be executed on the resource

            self.logger.info('schedule: found no suitable job for %s',
                             resource_conf['RESOURCE_ID'])
            return None

        self.logger.info('schedule: found best job: %s' % best_job)
        best_job['EXEC_RESOURCE'] = resource_conf['RESOURCE_ID']
        self.job_queue.dequeue_job(best_i)
        self.update_history(best_job, resource_conf)

        # self.ShowHistory()

        self.logger.info('schedule: returning best job: %s %d %f'
                         % (best_job['JOB_ID'], best_i, best_fitness))
        return best_job
