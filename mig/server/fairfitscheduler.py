#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fairfitscheduler - [insert a few words of module description on this line]
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

"""Fair Fit Scheduler"""

import time

from bestfitscheduler import BestFitScheduler


class FairFitScheduler(BestFitScheduler):
    """Fair Fit Scheduler:
    This is a Best Fit Scheduler modified to include job age in the
    fitness function. In that way we compensate somewhat for the
    potential problem with jobs being starved due to bad fitness.
    THIS ADDED 'FAIRNESS' IS CLEARLY WORKING AGAINST FREE MARKET
    FORCES!
    The level of fairness is strictly bound to the age_mult and
    expire_mult values below.

    """
    # If expiry is disabled at the MiG server:
    # Multiply the time (in *seconds*) the job has been waiting in
    # queue by this priority multiplier.
    age_mult = 0.01

    # If expiry is enabled at the MiG server:
    # Multiply the risk of job expiry (in percent) by this multiplier
    expire_mult = 50

    #---
    # Please note that age_mult and expire_mult should be decided in
    # relation to priorities in BestFit fitness function.
    # However age_mult should be rather small since waiting a few
    # minutes or even hours should not result in decisive fitness
    # changes
    #---
    
    def __init__(self, logger, config):
        BestFitScheduler.__init__(self, logger, config)
        self.name = "FairFitScheduler"

    def fitness(self, job, resource_conf):
        # Simply call fitness function from super class and add
        # queued time fitness value afterwards
        job_fitness = BestFitScheduler.fitness(self, job, resource_conf)
        self.logger.debug("fitness: %f without queue time", job_fitness)

        queue_time = time.mktime(time.gmtime()) - \
                     time.mktime(job['QUEUED_TIMESTAMP'])

        expire_after = self.conf.expire_after
        if expire_after == 0:
            # No risk of expiry so we use pure aging
            job_fitness += queue_time * self.age_mult
            self.logger.debug("fitness: %f with queue time %f",
                             job_fitness, queue_time)
        else:
            # Aging relies on risk of job expiry
            expire_risk = 1 - \
                          (abs(expire_after - queue_time) / expire_after)
            job_fitness += expire_risk * self.expire_mult

            #self.logger.level = 10
            self.logger.debug("fitness: %f with expire risk %f",
                             job_fitness, expire_risk)
            #self.logger.level = 20

        return job_fitness
