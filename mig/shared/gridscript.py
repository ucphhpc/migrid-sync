#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gridscript - main script helper functions
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
import time

import shared.fileio as io
from shared.base import client_id_dir
from shared.fileio import send_message_to_grid_script
from shared.job import output_dir
from shared.notification import notify_user_thread
try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

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

    # Load and add current logger

    queue = io.unpickle(path, logger)
    if not queue:
        # unpickle not successful
        return None
    else:
        queue.logger = logger
        return queue


def save_schedule_cache(cache, path, logger):
    """Save schedule cache to path for quick loading later"""

    return io.pickle(cache, path, logger)


def load_schedule_cache(path, logger):
    """Load schedule cache from path"""

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
    last_start_file = os.path.join(configuration.mig_system_files,
                                   'grid_script_laststart')
    if os.path.exists(last_start_file):
        last_start = os.path.getmtime(last_start_file)

    check_mrsl_files_start_time = time.time()

    for (root, dirs, files) in os.walk(configuration.mrsl_files_dir):

        # skip all dot dirs - they are from repos etc and _not_ jobs

        if root.find(os.sep + '.') != -1:
            continue

        # skip all dirs without any recent changes

        if only_new and os.path.getmtime(root) < last_start:
            logger.info('check mRSL files: skipping unchanged dir: %s' % root)
            continue
        
        logger.info('check mRSL files: inspecting %d files in %s' % \
                    (len(files), root))
        file_count = 0
        for name in files:
            filename = os.path.join(root, name)
            file_count += 1
            if file_count % 1000 == 0:
                logger.info('check mRSL files: %d files in %s checked' % \
                            (file_count, root))
            if os.path.getmtime(filename) < last_start:
                if only_new:
                    #logger.debug('skipping treated mrsl file: %s'
                    #             % filename)
                    continue
                logger.info('parsing possibly outdated mrsl file: %s'
                             % filename)

            job_dict = io.unpickle(filename, logger)
            if not job_dict:
                logger.error('could not open and unpickle: %s' % filename)
                continue

            if job_dict['STATUS'] == 'PARSE':

                # parse is ok, since mRSL file exists
                # tell 'grid_script' and let grid_script put it into the queue

                logger.info('Found a file with PARSE status: %s'
                             % job_dict['JOB_ID'])
                job_id = job_dict['JOB_ID']
                client_id = job_dict['USER_CERT']
                client_dir = client_id_dir(client_id)
                message = 'USERJOBFILE %s/%s\n' % (client_dir, job_id)
                if not send_message_to_grid_script(message, logger,
                        configuration):
                    print 'Fatal error: Could not write to grid stdin'
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
                # logger.debug('Job in %s is already treated' % filename)
                continue

    # update last_start_file access times. Note the timestamp is not "now" but
    # when check_mrsl_files was called to avoid loosing any jobs being parsed
    # at the same time as this function is running.

    logger.info('setting time of last_start_file %s to %s'
                 % (last_start_file, check_mrsl_files_start_time))
    io.touch(last_start_file, check_mrsl_files_start_time)


def remove_jobrequest_pending_files(configuration):
    for (root, dirs, files) in os.walk(configuration.resource_home):
        for name in files:

            # skip all dot dirs - they are from repos etc and _not_ jobs

            if root.find(os.sep + '.') != -1:
                continue
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
        symlink1 = os.path.join(configuration.webserver_home, sessionid)

        # logger.info("trying to remove: %s" % symlink1)

        os.remove(symlink1)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    try:
        symlink2 = os.path.join(configuration.webserver_home, iosessionid)

        # logger.info("trying to remove: %s" % symlink2)

        os.remove(symlink2)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    try:
        symlink3 = os.path.join(configuration.sessid_to_mrsl_link_home,
                                sessionid + '.mRSL')

        # logger.info("trying to remove: %s" % symlink3)

        os.remove(symlink3)
    except Exception, err:
        logger.error('error removing symlink during server_clean_up %s'
                      % err)
        success = False

    # Remove X.job and X.sendoutputfiles and source created during job script generation

    try:
        joblink = os.path.join(configuration.webserver_home, sessionid + '.job')
        jobfile = os.path.realpath(joblink)
        os.remove(joblink)
        os.remove(jobfile)
    except Exception, err:
        logger.error('error removing %s %s' % (jobfile, err))
        success = False
    try:
        getupdatefileslink = os.path.join(configuration.webserver_home,
                                           sessionid + '.getupdatefiles')
        getupdatefilesfile = os.path.realpath(getupdatefileslink)
        os.remove(getupdatefileslink)
        os.remove(getupdatefilesfile)
    except Exception, err:
        logger.error('error removing %s %s' % (getupdatefilesfile,
                     err))
        success = False
    try:
        sendoutputfileslink = os.path.join(configuration.webserver_home,
                                           sessionid + '.sendoutputfiles')
        sendoutputfilesfile = os.path.realpath(sendoutputfileslink)
        os.remove(sendoutputfileslink)
        os.remove(sendoutputfilesfile)
    except Exception, err:
        logger.error('error removing %s %s' % (sendoutputfilesfile,
                     err))
        success = False

    try:
        sendupdatefileslink = os.path.join(configuration.webserver_home,
                                           sessionid + '.sendupdatefiles')
        sendupdatefilesfile = os.path.realpath(sendupdatefileslink)
        os.remove(sendupdatefileslink)
        os.remove(sendupdatefilesfile)
    except Exception, err:
        logger.error('error removing %s %s' % (sendupdatefilesfile,
                     err))
        success = False
    try:
        last_live_update_file = os.path.join(configuration.mig_system_files,
                                             job_id + '.last_live_update')
        if os.path.isfile(last_live_update_file):
            os.remove(last_live_update_file)
    except Exception, err:
        logger.error('error removing %s %s' % (last_live_update_file,
                     err))
        success = False

    # Empty jobs should have all their status files deleted
    # Clean up may happen before any files are uploaded so ignore
    # missing files, however.

    if job_id.find(configuration.empty_job_name) != -1:
        empty_prefix = os.path.join(configuration.user_home,
                                    configuration.empty_job_name,
                                    output_dir, job_id)
        for name in ['.status', '.io-status', '.stdout', '.stderr']:
            status_path = os.path.realpath(os.path.join(empty_prefix,
                                                        job_id + name))
            if os.path.exists(status_path):
                try:
                    os.remove(status_path)
                except Exception, err:
                    logger.error('could not remove %s during server_clean_up %s'
                                  % (status_path, err))
        if os.path.exists(empty_prefix):
            try:
                os.rmdir(empty_prefix)
            except Exception, err:
                logger.error('could not remove %s during server_clean_up %s'
                             % (empty_prefix, err))

    # Only sandboxes create this link, so we don't fail if it does not exists.

    sandboxgetinputfileslink = os.path.join(configuration.webserver_home,
                                            localjobname + '.getinputfiles')
    if os.path.islink(sandboxgetinputfileslink):
        try:
            os.remove(sandboxgetinputfileslink)
        except Exception, err:
            logger.info('could not remove %s during server_clean_up %s'
                         % (sandboxgetinputfileslink, err))

    # Only oneclick sandboxes create this link, so we don't fail if it does not exists.

    oneclickexelink = os.path.join(configuration.webserver_home, sessionid + '.jvm')
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

        client_dir = client_id_dir(job_dict['USER_CERT'])

        # Remove job result files, if they have arrived as the result is not valid
        # This can happen with sandboxes as they can't be stopped serverside

        status_prefix = os.path.join(configuration.user_home, client_dir,
                                     job_dict['JOB_ID'])
        io.delete_file(status_prefix + '.status', logger)
        io.delete_file(status_prefix + '.stdout', logger)
        io.delete_file(status_prefix + '.stderr', logger)

        # Generate execution history

        if not job_dict.has_key('EXECUTION_HISTORY'):
            job_dict['EXECUTION_HISTORY'] = []

        history_dict = {
            'QUEUED_TIMESTAMP': job_dict['QUEUED_TIMESTAMP'],
            'EXECUTING_TIMESTAMP': job_dict['EXECUTING_TIMESTAMP'],
            'FAILED_TIMESTAMP': failed_timestamp,
            'FAILED_MESSAGE': failed_msg,
            'UNIQUE_RESOURCE_NAME': job_dict['UNIQUE_RESOURCE_NAME'],
            'RESOURCE_VGRID': job_dict.get('RESOURCE_VGRID', ''),
            'PUBLICNAME': job_dict.get('PUBLICNAME', 'HIDDEN'),
            }

        job_dict['EXECUTION_HISTORY'].append(history_dict)

        # Retry if retries left

        job_dict['RETRY_COUNT'] = job_dict.get('RETRY_COUNT', 0) + 1

        unique_resource_name = job_dict['UNIQUE_RESOURCE_NAME']

        mrsl_file = os.path.join(configuration.mrsl_files_dir,
                                 client_dir, job_dict['JOB_ID']
                                  + '.mRSL')
        job_retries = job_dict.get('RETRIES', configuration.job_retries)
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
            if job_dict.has_key('PUBLICNAME'):
                del job_dict['PUBLICNAME']
            if job_dict.has_key('RESOURCE_VGRID'):
                del job_dict['RESOURCE_VGRID']

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
            notify_user_thread(
                job_dict,
                configuration.myfiles_py_location,
                'FAILED',
                logger,
                False,
                configuration,
                )

def arc_job_status(
    job_dict,
    configuration,
    logger
    ):
    """Retrieve status information for a job submitted to ARC.
       Status is returned as a string. In case of failure, returns 
       'UNKNOWN' and logs the error."""
    
    logger.debug('Checking ARC job status for %s' % job_dict['JOB_ID'])

    userdir = os.path.join(configuration.user_home, \
                           client_id_dir(job_dict['USER_CERT']))
    try:
        jobinfo = {'status':'UNKNOWN(TO FINISH)'}
        session = arc.Ui(userdir)
        jobinfo = session.jobStatus(job_dict['EXE'])
    except arc.ARCWrapperError, err:
        logger.error('Error during ARC status retrieval: %s'\
                     % err.what())
        pass
    except arc.NoProxyError, err:
        logger.error('Error during ARC status retrieval: %s'\
                     % err.what())
        pass
    except Exception, err:
        logger.error('Error during ARC status retrieval: %s'\
                     % err.__str__())
        pass
    return jobinfo['status']

def clean_arc_job(
    job_dict, 
    status,
    msg,
    configuration,
    logger,
    kill = True,
    timestamp = None
    ):
    """Cleaning remainder of an executed ARC job:
        - delete from ARC (and possibly kill the job, parameter)
        - delete two symbolic links (user dir and mrsl file)
        - write status and timestamp into mrsl 
    """


    logger.debug('Cleanup for ARC job %s, status %s' % (job_dict['JOB_ID'],status))

    if not status in ['FINISHED', 'CANCELED', 'FAILED']:
        logger.error('inconsistent cleanup request: %s for job %s' % \
                     (status, job_dict))
        return

    # done by the caller...
    # executing_queue.dequeue_job_by_id(job_dict['JOB_ID'])

    if not timestamp:
        timestamp = time.gmtime()
    client_dir = client_id_dir(job_dict['USER_CERT'])

    # clean up in ARC
    try:
        userdir = os.path.join(configuration.user_home, client_dir)
        arcsession = arc.Ui(userdir)
    except Exception, err:
        logger.error('Error cleaning up ARC job: %s' % err)
        logger.debug('Job was: %s' % job_dict)
    else:
        # cancel catches, clean always succeeds
        if kill:
            killed = arcsession.cancel(job_dict['EXE'])
            if not killed:
                arcsession.clean(job_dict['EXE'])
        else:
            arcsession.clean(job_dict['EXE'])

    # Clean up associated server files of the job

    if 'SESSIONID' in job_dict:
        sessionid = job_dict['SESSIONID']
        symlinks = [os.path.join(configuration.webserver_home,
                                 sessionid)
                    , os.path.join(configuration.sessid_to_mrsl_link_home,
                                   sessionid + '.mRSL')]
        for link in symlinks:
            try: 
                os.remove(link)
            except Exception, err:
                logger.error('Could not remove link %s: %s' % (link, err))


    job_dict['STATUS'] = status
    job_dict[ status + '_TIMESTAMP' ] = timestamp

    if not status == 'FINISHED':
        # Generate execution history

        if not job_dict.has_key('EXECUTION_HISTORY'):
            job_dict['EXECUTION_HISTORY'] = []

        history_dict = {
            'QUEUED_TIMESTAMP': job_dict['QUEUED_TIMESTAMP'],
            'EXECUTING_TIMESTAMP': job_dict['EXECUTING_TIMESTAMP'],
            status + '_TIMESTAMP': timestamp,
            status + '_MESSAGE': msg,
            'UNIQUE_RESOURCE_NAME': job_dict['UNIQUE_RESOURCE_NAME'],
        }

        job_dict['EXECUTION_HISTORY'].append(history_dict)

    # save into mrsl

    mrsl_file = os.path.join(configuration.mrsl_files_dir,
                                 client_dir, 
                                 job_dict['JOB_ID'] + '.mRSL')
    io.pickle(job_dict, mrsl_file, logger)

    return
