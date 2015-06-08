#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vickreyauctionscheduler - [insert a few words of module description on this line]
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Vicrey Auction Scheduler"""

import random

from scheduler import Scheduler
from shared.conf import get_configuration_object


class VickreyAuctionScheduler(Scheduler):

    """Vickrey Auction scheduler"""

    filtered_jobs = []
    sealed_bids = []

    def __init__(self, logger, config):
        Scheduler.__init__(self, logger, config)
        self.name = 'VickreyAuctionScheduler'
        self.filtered_jobs = []
        self.sealed_bids = []

    def schedule(self, resource_conf):
        """Schedule a job for resource_conf"""

        self.hold_auction(resource_conf)

    def filter_jobs(self, resource_conf={}):
        """Filter jobs with to long execution time """

        res_time = resource_conf['CPUTIME']
        qlen = self.job_queue.queue_length()

        for i in range(qlen):
            job = self.job_queue.get_job(i)

            print job['JOB_ID']

            if job['CPUTIME'] <= res_time:
                self.filtered_jobs.append(job)

    def hold_auction(self, resource_conf):
        """Executes a Vickrey auction"""

        # filter jobs

        self.filter_jobs(resource_conf)

        # Receives sealed bids from jobs

        for job in self.filtered_jobs:

            # print(job)

            # only includes bids equal to or above the reservation price
            # MAXPRICE =  bid, MINPRICE = reservation_price

            if job['MAXPRICE'] >= resource_conf['MINPRICE']:
                self.sealed_bids.append((job['MAXPRICE'], job['JOB_ID'
                        ]))

        # sorting bids

        self.sealed_bids.sort()

        # Extract the highest and second highest bids
        # TODO: can not assume that there are any bids

        if len(self.sealed_bids) <= 0:
            return

        highest = self.sealed_bids.pop()

        if len(self.sealed_bids) > 1:
            second = self.sealed_bids.pop()
        else:
            second = highest

        # debug
        # print highest
        # print second

        winner = dict()

        # determine outcome

        if len(self.sealed_bids) > 1 and highest[0] == second[0]:

            # toss a coin to select a winner
            # below 0,5 highest wins, and above second wins

            if random.random() <= 0.5:
                winner = self.find_winner(highest[1])
            else:
                winner = self.find_winner(second[1])
        else:
            winner = self.find_winner(highest[1])

        # payment and scheduling

        print highest[1]
        print second[1]

        # diff = highest[0] - second[0]

        winner['EXEC_PRICE'] = highest[0]

        # winner["EXEC_RAWDIFF"] = highest[0] - second[0]

        winner['EXEC_RAWDIFF'] = 0
        winner['EXEC_RESOURCE'] = resource_conf['RESOURCE_ID']

        # self.logger.info("schedule: scheduled %s for execution at %s" % \
        #                 (winner['JOB_ID'], resource_conf['RESOURCE_ID']))

        self.job_queue.dequeue_job_by_job_id(winner['JOB_ID'])

        # self.UpdateHistory(winner, resource_conf)

        print winner

        return winner

    def find_winner(self, job_id):
        """Finds the winning job, given a job_id"""

        qlen = self.job_queue.queue_length()

        for i in range(qlen):
            job = self.job_queue.get_job(i)

            if job['JOB_ID'] == job_id:
                return job

        raise Exception('winner %s not found in queue!' % job_id)


# ## MAIN ###

if __name__ == '__main__':
    res = {}
    res['MINPRICE'] = 10
    res['RESOURCE_ID'] = 1
    res['CPUTIME'] = 1000

    job1 = {}
    job1['JOB_ID'] = 1
    job1['MAXPRICE'] = 13
    job1['payment'] = None
    job1['EXEC_RESOURCE'] = None
    job1['CPUTIME'] = 200

    job2 = {}
    job2['JOB_ID'] = 1
    job2['MAXPRICE'] = 15
    job2['payment'] = None
    job2['EXEC_RESOURCE'] = None
    job2['CPUTIME'] = 200

    job3 = {}
    job3['JOB_ID'] = 1
    job3['MAXPRICE'] = 14
    job3['payment'] = None
    job3['EXEC_RESOURCE'] = None
    job3['CPUTIME'] = 200

    job_queue = [job1, job2, job3]

    configuration = get_configuration_object()
    logger = configuration.logger
    auction = VickreyAuctionScheduler(logger, configuration)
    auction.schedule(res)
