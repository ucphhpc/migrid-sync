#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gridscript - [insert a few words of module description on this line]
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

"""Main MiG daemon (grid_script) helper functions"""

import os
import pickle
import time

import shared.fileio as io
from shared.notification import notify_user


def clean_grid_stdin(stdin):
    """Deletes all content from the pipe (used when grid-script is
    started). First content in pipe might be lost!!

    """

    while True:
        line = stdin.readline()
        if not line:
            break


def save_queue(queue, path, logger):
    """Save job queue to path for quick loading later"""

    # Don't try to save logger

    queue.logger = None
    return io.pickle(queue, path, logger)


def load_queue(path, logger):
    """Load job queue from path"""

    return io.unpickle(path, logger)


def check_mrsl_files(
    configuration,
    job_queue,
    executing_queue,
    only_new,
    logger,
    ):
    """Check job files on disk in order to initialize job queue after
    (re)start of grid_script.
    """

    # We only check files modified since last start if possible

    last_start = 0
    last_start_file = configuration.mig_system_files\
         + 'grid_script_laststart'
    if os.path.exists(last_start_file):
        last_start = os.path.getmtime(last_start_file)

    check_mrsl_files_start_time = time.time()

    for (root, dirs, files) in os.walk(configuration.mrsl_files_dir):

        # skip all dot dirs - they are from repos etc and _not_ jobs
            
        if root.find(os.sep + '.') != -1:
                continue
        for name in files:
            filename = root + '/' + name
            if os.path.getmtime(filename) < last_start:
                if only_new:
                    logger.info('skipping treated mrsl file: %s'
                                 % filename)
                    continue
                logger.info('parsing possibly outdated mrsl file: %s'
                             % filename)

            try:
                filehandle = open(filename, 'r')
            except Exception, err:
                logger.error('could not open: %s %s' % (filename, err))

            try:
                job_dict = pickle.load(filehandle)
                filehandle.close()
            except Exception, err:
                logger.error('could not open and pickle: %s %s'
                              % (filename, err))
                continue

            if job_dict['STATUS'] == 'PARSE':

                # parse is ok, since mRSL file exists
                # tell 'grid_script' and let grid_script put it into the queue

                logger.info('Found a file with PARSE status: %s'
                             % job_dict['JOB_ID'])
                try:
                    fsock = open(configuration.grid_stdin, 'a')
                    fsock.write('USERJOBFILE ' + job_dict['USER_CERT']
                                 + '/' + job_dict['JOB_ID'] + '\n')
                    fsock.close()
                except Exception, err:
                    print 'Fatal error: Could not write to %s %s'\
                         % (configuration.grid_stdin, err)
            elif job_dict['STATUS'] == 'QUEUED'\
                 and not job_queue.get_job_by_id(job_dict['JOB_ID']):

                # put in job queue

                logger.info('USERJOBFILE: There were %s jobs in the job_queue'
                             % job_queue.queue_length())
                job_queue.enqueue_job(job_dict,
                        job_queue.queue_length())
                logger.info("Now there's %s (QUEUED job %s added)"
                             % (job_queue.queue_length(),
                            job_dict['JOB_ID']))
            elif job_dict['STATUS'] == 'EXECUTING'\
                 and not executing_queue.get_job_by_id(job_dict['JOB_ID'
                    ]):

                # put in executing queue

                logger.info('USERJOBFILE: There were %s jobs in the executing_queue'
                             % executing_queue.queue_length())
                executing_queue.enqueue_job(job_dict,
                        executing_queue.queue_length())
                logger.info("Now there's %s (EXECUTING job %s added)"
                             % (executing_queue.queue_length(),
                            job_dict['JOB_ID']))
            else:
                logger.info('Job in %s is already treated' % filename)

    # update last_start_file access times. Note the timestamp is not "now" but
    # when check_mrsl_files was called to avoid loosing any jobs being parsed
    # at the same time as this function is running.

    logger.info('setting time of last_start_file %s to %s'
                 % (last_start_file, check_mrsl_files_start_time))
    io.touch(last_start_file, check_mrsl_files_start_time)


def remove_jobrequest_pending_files(configuration):
    for (root, dirs, files) in os.walk(configuration.resource_home):
        for name in files:
            if name.startswith('jobrequest_pending.'):

                # remove it

                filename = os.path.join(root, name)
                try:
                    os.remove(filename)
                except Exception, err:
                    print 'could not remove jobrequest_pending file %s %s'\
                         % (filename, err)


def server_cleanup(
    sessionid,
    iosessionid,
    localjobname,
    job_id,
    configuration,
    logger,
    ):
    """Clean up server after finished or timed out job"""

    success = True
    logger.info('server_clean_up start')

    # remove symlinks created in job script generator

    try:
        symlink1 = configuration.webserver_home + sessionid

        # logger.info("trying to remove: " + symlink1)

        os.remove(symlink1)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    try:
        symlink2 = configuration.webserver_home + iosessionid

        # logger.info("trying to remove: " + symlink2)

        os.remove(symlink2)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    try:
        symlink3 = configuration.sessid_to_mrsl_link_home + sessionid\
             + '.mRSL'

        # logger.info("trying to remove: " + symlink3)

        os.remove(symlink3)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    # Remove X.job and X.sendoutputfiles and source created during job script generation

    try:
        joblink = configuration.webserver_home + sessionid + '.job'
        jobfile = os.path.realpath(joblink)
        os.remove(joblink)
        os.remove(jobfile)
    except Exception, err:
        logger.error('error removing %s %s' % (jobfile, err))
        success = False
    try:
        sendoutputfileslink = configuration.webserver_home + sessionid\
             + '.sendoutputfiles'
        sendoutputfilesfile = os.path.realpath(sendoutputfileslink)
        os.remove(sendoutputfileslink)
        os.remove(sendoutputfilesfile)
    except Exception, err:
        logger.error('error removing %s %s' % (sendoutputfilesfile,
                     err))
        success = False

    try:
        sendupdatefileslink = configuration.webserver_home + sessionid\
             + '.sendupdatefiles'
        sendupdatefilesfile = os.path.realpath(sendupdatefileslink)
        os.remove(sendupdatefileslink)
        os.remove(sendupdatefilesfile)
    except Exception, err:
        logger.error('error removing %s %s' % (sendupdatefilesfile,
                     err))
        success = False
    try:
        last_live_update_file = configuration.mig_system_files + os.sep\
             + job_id + '.last_live_update'
        if os.path.isfile(last_live_update_file):
            os.remove(last_live_update_file)
    except Exception, err:
        logger.error('error removing %s %s' % (last_live_update_file,
                     err))
        success = False

    # Empty jobs should have all their status files deleted

    if job_id.find(configuration.empty_job_name) != -1:
        empty_prefix = configuration.user_home + os.sep\
             + configuration.empty_job_name + os.sep + job_id
        for name in ['.status', '.io-status', '.stdout', '.stderr']:
            status_path = os.path.realpath(empty_prefix + name)
            if not os.path.exists(status_path):
                logger.warning('server_cleanup could not find expected file %s'
                                % status_path)
            else:
                try:
                    os.remove(status_path)
                except Exception, err:
                    logger.error('could not remove %s during server_clean_up %s'
                                  % (status_path, err))

    # Only sandboxes create this link, so we don't fail if it does not exists.

    sandboxgetinputfileslink = configuration.webserver_home\
         + localjobname + '.getinputfiles'
    if os.path.islink(sandboxgetinputfileslink):
        try:
            os.remove(sandboxgetinputfileslink)
        except Exception, err:
            logger.info('could not remove %s during server_clean_up %s'
                         % (sandboxgetinputfileslink, err))

    # Only oneclick sandboxes create this link, so we don't fail if it does not exists.

    oneclickexelink = configuration.webserver_home + sessionid + '.jvm'
    if os.path.islink(oneclickexelink):
        try:
            os.remove(oneclickexelink)
        except Exception, err:
            logger.info('could not remove %s during server_clean_up %s'
                         % (oneclickexelink, err))

    return success


def requeue_job(
    job_dict,
    failed_msg,
    job_queue,
    executing_queue,
    configuration,
    logger,
    ):

    if not job_dict:
        msg = 'requeue_job: %s is no longer in executing queue'
        print failed_msg
        logger.info(failed_msg)
    else:
        executing_queue.dequeue_job_by_id(job_dict['JOB_ID'])
        failed_timestamp = time.gmtime()

        # Clean up the server for files assosiated with the executing job

        if not job_dict.has_key('SESSIONID')\
             or not job_dict.has_key('IOSESSIONID')\
             or not server_cleanup(
            job_dict['SESSIONID'],
            job_dict['IOSESSIONID'],
            job_dict['LOCALJOBNAME'],
            job_dict['JOB_ID'],
            configuration,
            logger,
            ):
            logger.error('could not clean up MiG server')
            print 'CLEAN UP FAILED'

        # Remove job result files, if they have arrived as the result is not valid
        # This can happen with sandboxes as they can't be stopped serverside

        io.delete_file(configuration.user_home + job_dict['USER_CERT']
                        + '/' + job_dict['JOB_ID'] + '.status', logger)
        io.delete_file(configuration.user_home + job_dict['USER_CERT']
                        + '/' + job_dict['JOB_ID'] + '.stdout', logger)
        io.delete_file(configuration.user_home + job_dict['USER_CERT']
                        + '/' + job_dict['JOB_ID'] + '.stderr', logger)

        # Generate execution history

        if not job_dict.has_key('EXECUTION_HISTORY'):
            job_dict['EXECUTION_HISTORY'] = []

        history_dict = {
            'QUEUED_TIMESTAMP': job_dict['QUEUED_TIMESTAMP'],
            'EXECUTING_TIMESTAMP': job_dict['EXECUTING_TIMESTAMP'],
            'FAILED_TIMESTAMP': failed_timestamp,
            'FAILED_MESSAGE': failed_msg,
            'UNIQUE_RESOURCE_NAME': job_dict['UNIQUE_RESOURCE_NAME'],
            }

        job_dict['EXECUTION_HISTORY'].append(history_dict)

        # Retry if retries left

        if not job_dict.has_key('RETRY_COUNT'):
            job_dict['RETRY_COUNT'] = 1
        else:
            job_dict['RETRY_COUNT'] += 1

        unique_resource_name = job_dict['UNIQUE_RESOURCE_NAME']

        mrsl_file = configuration.mrsl_files_dir + job_dict['USER_CERT']\
             + '/' + job_dict['JOB_ID'] + '.mRSL'
        job_retries = configuration.job_retries
        if job_dict['RETRY_COUNT'] <= job_retries:
            job_dict['STATUS'] = 'QUEUED'
            job_dict['QUEUED_TIMESTAMP'] = time.gmtime()
            del job_dict['EXECUTING_TIMESTAMP']
            del job_dict['UNIQUE_RESOURCE_NAME']
            del job_dict['EXE']
            del job_dict['RESOURCE_CONFIG']
            del job_dict['LOCALJOBNAME']
            if job_dict.has_key('SESSIONID'):
                del job_dict['SESSIONID']
            if job_dict.has_key('IOSESSIONID'):
                del job_dict['IOSESSIONID']

            io.pickle(job_dict, mrsl_file, logger)

            # Requeue job last in queue for retry later

            job_queue.enqueue_job(job_dict, job_queue.queue_length())

            msg = \
                '%s failed to execute job %s - requeue for retry %d of %d'\
                 % (unique_resource_name, job_dict['JOB_ID'],
                    job_dict['RETRY_COUNT'], job_retries)
            print msg
            logger.info(msg)
        else:

            job_dict['STATUS'] = 'FAILED'
            job_dict['FAILED_TIMESTAMP'] = failed_timestamp
            io.pickle(job_dict, mrsl_file, logger)

            # tell the user the sad news

            msg = 'Gave up on executing job %s after %d retries'\
                 % (job_dict['JOB_ID'], job_retries)
            logger.error(msg)
            print msg
            notify_user(
                job_dict,
                configuration.myfiles_py_location,
                'FAILED',
                logger,
                False,
                configuration.smtp_server,
                configuration,
                )


