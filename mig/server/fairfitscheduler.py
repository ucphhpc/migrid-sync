#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fairfitscheduler - a modified best-fit scheduler to include job age
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Fair Fit Scheduler: reuses best-fit scheduler but increases job fitness
with an absolute and a relative waiting-time bonus to counter inherent
starvation tendencies of pure best-fit scheduling.
"""
from __future__ import absolute_import
from __future__ import division

import time

from mig.server.bestfitscheduler import BestFitScheduler


class FairFitScheduler(BestFitScheduler):

    """Fair Fit Scheduler:
    This is a Best Fit Scheduler modified to include job age in the
    fitness function. In that way we compensate somewhat for the
    potential problem with jobs being starved due to bad fitness.
    THIS ADDED 'FAIRNESS' IS CLEARLY WORKING AGAINST FREE MARKET
    FORCES!
    The level of fairness is strictly bound to the age_mult value below.

    """

    # Multiply the queued waiting time by this priority constant and add the
    # resulting value to the job fitness to balance waiting time with best
    # fit and to counter starvation in general. A bonus based on the ratio
    # between queued and job wallclock time is additionally included to
    # slightly favor shorter jobs more over time.
    # With the current best fit max fitness value of 300 an age_mult value of
    # 0.01 means that any job waiting 30000 seconds (approx 8 hours) will
    # always be in front of even a perfectly fitting job submitted just now.
    # Due to the added relative wait time ratio bonus the jobs requesting
    # shorter time will reach that tipping point a bit sooner.

    age_mult = 0.01

    def __init__(self, logger, config):
        BestFitScheduler.__init__(self, logger, config)
        self.name = 'FairFitScheduler'

    def fitness(self, job, resource_conf):

        # Simply call fitness function from super class and add
        # absolute and relative queue time fitness bonus afterwards

        job_fitness = BestFitScheduler.fitness(self, job, resource_conf)
        self.logger.debug('fitness: %f without time bonus', job_fitness)

        queue_time = time.mktime(time.gmtime()) - \
            time.mktime(job['QUEUED_TIMESTAMP'])
        job_time = int(job.get('CPUTIME', 60))

        # Force rel_bonus between 0 and 1 to avoid very short job "gaming"

        rel_bonus = 10.0 / max(job_time, 10)

        # Always apply a mix of absolute and relative aging

        job_fitness += self.age_mult * queue_time * (1 + rel_bonus)
        self.logger.debug('fitness: %f with queue / job time %f / %f (%f)',
                          job_fitness, queue_time, job_time, rel_bonus)

        return job_fitness
