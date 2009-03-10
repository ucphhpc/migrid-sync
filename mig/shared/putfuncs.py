#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# putfuncs - [insert a few words of module description on this line]
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

"""Functions in this file should only be called from 'put'. If other scripts needs it then move the function to another file.
"""

import os
import time
import re


def template_fits_file(template, filename, allowed_time=3.0):
    """Test if regular expressions in template fits contents of
    filename in a line by line comparison. Please note that an
    empty template matches if filename doesn't exist.
    """

    fit = True

    # Allow comparison to take up to allowed_time seconds

    start_time = time.time()

    try:
        comparelines = open(template, 'r').readlines()
    except Exception, err:

        # print "Failed to read", template

        return False

    try:
        filelines = open(filename, 'r').readlines()
    except Exception, err:

        # print "Failed to read", filename

        if len(comparelines) == 0:

            # No file matches an empty template

            return True
        else:
            return False

    if len(filelines) != len(comparelines):

        # print "line count mismatch between %s and %s", template, filename

        return False

    i = 0

    # print "start time:", start_time

    while i < len(filelines):
        compare_time = time.time() - start_time
        if compare_time > allowed_time:

            # print "Template fit of %s against %s timed out after %d lines (%d seconds)" % (template, filename, i, compare_time)

            fit = False
            break

        line = filelines[i].strip()
        compare = comparelines[i].strip()

        # print line, "?~" , compare

        i += 1

        # os.system("sleep %d" % (i))

        if not re.match(compare, line):

            # print line, "!~" , compare

            fit = False
            break

    # print "Comparison of %s against %s done in %.4f seconds" % (template, filename, compare_time)

    return fit


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
                logger.warning('unsupported verifyfile %s! must end in .{status,stdout,stderr}'
                               , verify)
                job_dict['VERIFIED'] += ' %s: unknown file suffix!'\
                     % verify
                verified = False
                continue

            logger.debug('preparing to do %s check', check)
            if job_dict.has_key('USER_CERT'):
                owner = job_dict['USER_CERT']
            else:
                owner = ''

            logger.debug('owner: %s', owner)
            verifyname = user_home + os.sep + owner + os.sep + verify
            logger.debug('verify using %s', verifyname)
            if not os.path.isfile(verifyname):
                logger.warning('no such verifyfile %s! (%s)', verify,
                               verifyname)
                job_dict['VERIFIED'] += ' %s: %s does not exist!'\
                     % (check, verify)
                verified = False
                continue

            job_id = job_dict['JOB_ID']
            filename = user_home + os.sep + owner + os.sep + job_id\
                 + '.' + check
            logger.debug('Matching %s against %s', verifyname, filename)
            match = template_fits_file(verifyname, filename)
            if match:
                job_dict['VERIFIED'] += ' %s: %s!' % (check, 'OK')
            else:
                job_dict['VERIFIED'] += ' %s: %s!' % (check, 'FAILED')
                verified = False

            logger.info('verified %s against actual results - match: %s'
                        , verify, match)
        if verified:
            job_dict['VERIFIED'] = 'SUCCESS -' + job_dict['VERIFIED']
        else:
            job_dict['VERIFIED'] = 'FAILURE -' + job_dict['VERIFIED']

        job_dict['VERIFIED_TIMESTAMP'] = time.gmtime()
    else:
        logger.info('No verifyfile entries to verify result against')

    logger.info('VERIFIED : %s', job_dict['VERIFIED'])


def migrated_job(filename, cert_name_no_spaces, configuration):

    # returns a tuple (bool status, str msg)

    server_home = configuration.server_home
    mrsl_files_dir = configuration.mrsl_files_dir
    grid_stdin = configuration.grid_stdin

    job_path = server_home + cert_name_no_spaces + '/' + filename

    # unpickle and enqueue received job file

    try:
        job_path_spaces = job_path.replace('\\ ', '\\\\\\ ')
        filehandle = open(job_path_spaces, 'r+')
        job = pickle.load(filehandle)

        # TODO: update any fields to mark migration?

        filehandle.close()
    except:
        return (False,
                'Fatal migration error: loading pickled job failed! '
                 + job_path_spaces)

    job_id = job['JOB_ID']

    # save file with other mRSL files

    mrsl_filename = mrsl_files_dir + cert_name_no_spaces + '/' + job_id\
         + '.mRSL'

    try:
        mrsl_file = open(mrsl_filename, 'w')
        mrsl_file.write(pickle.dumps(job))
        mrsl_file.close()
    except:
        return (False, 'Fatal error: Could not write ' + filename)

    # tell 'grid_script'

    grid_stdin = config.get('GLOBAL', 'grid_stdin')
    try:
        server = open(grid_stdin, 'a')
        server.write('SERVERJOBFILE ' + cert_name_no_spaces + '/'
                      + job_id + '\n')
        server.close()
    except:
        return (False, 'Fatal error: Could not write to %s'
                 % grid_stdin)

    # TODO: do we need to wait for grid_script to ack job reception?
    # ... same question applies to new_job, btw.

    return (True, '%s succesfully migrated.' % job_id)


