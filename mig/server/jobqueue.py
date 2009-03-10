#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobqueue - [insert a few words of module description on this line]
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

"""MiG server job queue"""


def print_job(job_dict, detail=['JOB_ID']):

    # Keyword all prints all values

    if detail == ['ALL']:
        for attr in job_dict.keys():
            print '\t%s: %s' % (attr, job_dict[attr])
    else:

        for attr in detail:
            if job_dict.has_key(attr):
                print '\t%s: %s' % (attr, job_dict[attr])
            else:
                print '\t%s: UNSET' % attr


class JobQueue:

    """Simple job queue implemantation using a list"""

    # TODO: change to better data structure - perhaps circular buffer
    # or real linked list.
    # -Must support ability to inspect a job without dequeueing it
    # -Must support virtually unlimited queue length
    # Built-in Queue class does *not* support inspection!

    queue = None
    logger = None

    def __init__(self, logger):
        """Init"""

        self.queue = []
        self.logger = logger
        self.logger.info('initialised queue')

    def show_queue(self, detail=['JOB_ID']):
        """Print queue contents"""

        print 'Queue:'
        if self.queue_length() > 0:
            for j in self.queue:
                print_job(j, detail)
        else:
            print '\t-Empty-'

    def queue_length(self):
        """Count number of jobs in queue"""

        return len(self.queue)

    def enqueue_job(self, job, index):
        """Insert job at index in queue list"""

        if self.queue_length() >= index:

            # check if a job with that job_id is in the queue to avoid multiple occurences

            try:
                for queue_job in self.queue:
                    if queue_job['JOB_ID'] == job['JOB_ID']:
                        self.logger.error('enqueue_job called with a job already in the queue! Skipping enqueue_job for job_id %s!'
                                 % job['JOB_ID'])
                        return False
            except Exception, exc:
                self.logger.error('enqueue_job exception when checking if specified job already is in the queue: %s'
                                   % exc)

            # job must be wrapped

            self.queue[index:index] = [job]

            # self.logger.info("NEW JOB! after enqueue len is %d", self.queue_length())

            return True
        else:
            self.logger.error("NEW JOB! failed to enqueue job - index %d \
            out of range! (qlen %d)"
                              , index, self.queue_length())
        return False

    def get_job(self, index):
        """Find and return job found at index in queue list"""

        job = None
        if self.queue_length() > index:
            job = self.queue[index]
        else:
            self.logger.error("get_job: Failed to get job - index %d \
            out of range! (qlen %d)"
                              , index, self.queue_length())
        return job

    def get_job_by_id(self, jobid):
        """Find and return job with jobid"""

        job = None
        if self.queue_length() > 0:
            for j in self.queue:
                if j['JOB_ID'] == jobid:
                    job = j
                    break
        else:
            self.logger.error('get_job_by_id: Queue empty.')

        if not job:
            self.logger.error('get_job_by_id: Failed to get job - jobid: %s '
                               % jobid)
        return job

    def dequeue_job(self, index):
        """Dequeue and return job found at index in queue list"""

        job = None
        if self.queue_length() > index:
            job = self.queue[index]
            self.queue[index:index + 1] = []
        else:
            self.logger.error("dequeue_job: Failed to dequeue job - index %d \
            out of range! (qlen %d)"
                              , index, self.queue_length())
        return job

    def dequeue_job_by_id(self, jobid):
        """Dequeue and return job with id: 'jobid'"""

        job = None
        index = 0
        if self.queue_length() > 0:
            for j in self.queue:
                if j['JOB_ID'] == jobid:
                    job = self.queue[index]
                    self.dequeue_job(index)
                    break
                index += 1
        else:
            self.logger.error('dequeue_job_by_id: Queue empty.')

        if not job:
            self.logger.error('dequeue_job_by_id: Failed to dequeue job - jobid: %s '
                               % jobid)
        return job


