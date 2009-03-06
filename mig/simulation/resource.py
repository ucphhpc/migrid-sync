#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource - [insert a few words of module description on this line]
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
# Resource class used for simulating resources that randomly requests jobs
#

import random


class Resource:
    id = ""
    req_prob = 0.5
    minprice = "0.0"
    logger = None
    server = None
    job = None
    job_timeleft = 0
    jobs_empty = 0
    jobs_done = 0
    length = 2

    def __init__(self, id, logger, prob, price, server, vgrid):
        self.id = id
        self.logger = logger
        self.req_prob = prob
        self.minprice = price
        self.server = server
        self.vgrid = vgrid
    

    def request_job(self, length):
        self.logger.info("%s requesting job with minprice %s from %s",
                         self.id, self.minprice, self.server.id)
        self.job = self.server.request(self.id, length, self.minprice, self.vgrid)
        if self.job:
            self.logger.debug("%s got job %s", self.id, self.job["JOB_ID"])
            self.job_timeleft = int(self.job["CPUTIME"])
        else:
            self.logger.debug("%s got empty job", self.id)
            self.jobs_empty += 1
    

    def sleep(self):
        self.logger.debug("%s sleeping", self.id)
    

    def simulate(self, timestep):
        # Keep requesting jobs for execution:
        # in/output handling is expected to take a bit so job does not start
        # executing in same timestep as it is requested and a new job is not
        # requested immediately after finishing a job
        
        if not self.job:
            # Random delay before taking next job
            rand = random.random()

            if rand <= self.req_prob:
                self.request_job(self.length)
            else:
                self.sleep()
        else:
            self.job_timeleft -= 1

            if self.job_timeleft == 0:
                self.logger.info("%s finished executing job", self.id)
                self.server.return_finished(self.id, self.job)
                self.jobs_done += 1
                self.job = None
            else:
                self.logger.debug("%s still %d left of job execution",
                                 self.id, self.job_timeleft)
