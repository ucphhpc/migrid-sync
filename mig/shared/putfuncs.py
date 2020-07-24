#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# putfuncs - helpers for the put handler
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Functions in this file should only be called from 'put'.
If other scripts needs it then move the function to another file.
"""

import os
import re
import time

from shared.base import client_id_dir
from shared.defaults import job_output_dir
from shared.fileio import send_message_to_grid_script, pickle, unpickle


def template_fits_file(template, filename, allowed_time=3.0):
    """Test if regular expressions in template fits contents of
    filename in a line by line comparison. Please note that an
    empty template matches if filename doesn't exist.
    """

    fit = True
    msg = ''

    # Allow comparison to take up to allowed_time seconds

    start_time = time.time()

    try:
        comparelines = open(template, 'r').readlines()
    except Exception, err:
        msg = "Failed to read template file"
        return (False, msg)

    try:
        filelines = open(filename, 'r').readlines()
    except Exception, err:
        if len(comparelines) == 0:

            # No file matches an empty template

            return (True, msg)
        else:
            msg = "Failed to read file to verify"
            return (False, msg)

    if len(filelines) != len(comparelines):
        msg = "line count mismatch between template and file to verify"
        return (False, msg)

    i = 0

    #print "start time:", start_time

    while i < len(filelines):
        compare_time = time.time() - start_time
        if compare_time > allowed_time:
            msg = "Template fit against file timed out after %d lines (%ds)" \
                  % (i, compare_time)
            fit = False
            break

        line = filelines[i].strip()
        compare = comparelines[i].strip()

        # print line, "?~" , compare

        i += 1
        if not re.match(compare, line):
            # print line, "!~" , compare
            msg = "found mismatch: '%s' vs '%s' (%s)" % (
                line, compare, line == compare)
            fit = False
            break

    #print "Comparison of %s against %s done in %.4f seconds" % (template, filename, compare_time)

    return (fit, msg)


def verify_results(job_dict, logger, configuration):

    # Compares any verifyfiles against actual results and sets VERIFIED_X for each one

    user_home = configuration.user_home

    job_dict['VERIFIED'] = 'NO'
    if job_dict.has_key('VERIFYFILES') and job_dict['VERIFYFILES']:
        verified = True
        job_dict['VERIFIED'] = ''

        for verify in job_dict['VERIFYFILES']:
            logger.debug('verifying %s against actual results', verify)
            if verify.endswith('.status'):
                check = 'status'
            elif verify.endswith('.stdout'):
                check = 'stdout'
            elif verify.endswith('.stderr'):
                check = 'stderr'
            else:
                logger.warning(
                    'unsupported verifyfile %s! must end in .{status,stdout,stderr}', verify)
                job_dict['VERIFIED'] += ' %s: unknown file suffix!'\
                    % verify
                verified = False
                continue

            logger.debug('preparing to do %s check', check)
            client_id = job_dict.get('USER_CERT', '')
            client_dir = client_id_dir(client_id)

            logger.debug('owner: %s', client_id)
            verifyname = os.path.join(user_home, client_dir, verify)
            logger.debug('verify using %s', verifyname)
            if not os.path.isfile(verifyname):
                logger.warning('no such verifyfile %s! (%s)', verify,
                               verifyname)
                job_dict['VERIFIED'] += ' %s: %s does not exist!'\
                    % (check, verify)
                verified = False
                continue

            job_id = job_dict['JOB_ID']
            filename = os.path.join(user_home, client_dir, job_output_dir,
                                    job_id, job_id + '.' + check)
            logger.info('Matching %s against %s', verifyname, filename)
            (match, err) = template_fits_file(verifyname, filename)
            if match:
                job_dict['VERIFIED'] += ' %s: %s' % (check, 'OK')
            else:
                job_dict['VERIFIED'] += ' %s: %s (%s)' % (check, 'FAILED', err)
                verified = False

            logger.info('verified %s against actual results - match: %s (%s)'
                        % (verify, match, err))
        if verified:
            job_dict['VERIFIED'] = 'SUCCESS -' + job_dict['VERIFIED']
        else:
            job_dict['VERIFIED'] = 'FAILURE -' + job_dict['VERIFIED']

        job_dict['VERIFIED_TIMESTAMP'] = time.gmtime()
    else:
        logger.info('No verifyfile entries to verify result against')

    logger.info('VERIFIED : %s', job_dict['VERIFIED'])


def migrated_job(filename, client_id, configuration):
    """returns a tuple (bool status, str msg)"""

    logger = configuration.logger
    client_dir = client_id_dir(client_id)
    job_path = os.path.abspath(os.path.join(configuration.server_home,
                                            client_dir, filename))

    # unpickle and enqueue received job file

    job_path_spaces = job_path.replace('\\ ', '\\\\\\ ')
    job = unpickle(job_path_spaces, configuration.logger)

    # TODO: update any fields to mark migration?

    if not job:
        return (False,
                'Fatal migration error: loading pickled job (%s) failed! ' %
                job_path_spaces)

    job_id = job['JOB_ID']

    # save file with other mRSL files

    mrsl_filename = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                     client_dir, job_id + '.mRSL'))

    if not pickle(job, mrsl_filename, configuration.logger):
        return (False, 'Fatal error: Could not write ' + filename)

    # tell 'grid_script'

    message = 'SERVERJOBFILE ' + client_dir + '/' + job_id + '\n'

    if not send_message_to_grid_script(message, logger, configuration):
        return (False, 'Fatal error: Could not write to grid stdin')

    # TODO: do we need to wait for grid_script to ack job reception?
    # ... same question applies to new_job, btw.

    return (True, '%s succesfully migrated.' % job_id)
