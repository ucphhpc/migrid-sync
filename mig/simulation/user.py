#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# user - [insert a few words of module description on this line]
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
# User class used for simulating users that randomly submit jobs
#

from builtins import object
import random


class User(object):

    id = ''
    submit_prob = None
    logger = None
    server = None
    maxprice = None
    length = 2
    jobs = 0

    def __init__(
        self,
        id,
        logger,
        prob,
        price,
        server,
        vgrid,
        ):

        self.id = id
        self.logger = logger
        self.submit_prob = prob
        self.maxprice = price
        self.server = server
        self.vgrid = vgrid

    def submit_job(self, step):
        self.logger.info('%s submitting job with maxprice %s to %s in step %d'
                         , self.id, self.maxprice, self.server.id, step)
        name = '%s' % self.id
        self.server.submit(name, self.length, self.maxprice, self.vgrid)
        self.jobs += 1

    def sleep(self):
        self.logger.debug('%s sleeping', self.id)

    def simulate(self, timestep):

        # Randomly submit a job during given timestep

        rand = random.random()
        qlen = self.server.job_queue.queue_length()

        if rand <= self.submit_prob and qlen < 200:
            self.submit_job(timestep)
        else:
            self.sleep()


