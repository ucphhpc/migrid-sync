#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# requestinteractivejob - handle interactive job requests from resources
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""Handle request for an interactive job from a resource"""

import cgi
import fcntl
import os
import sys
import time

from mig.shared.base import valid_dir_input
from mig.shared.cgishared import init_cgiscript_possibly_with_cert
from mig.shared.conf import get_resource_configuration, get_resource_exe
from mig.shared.fileio import unpickle
from mig.shared.findtype import is_resource
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.httpsclient import check_source_ip
from mig.shared.livedisplaysfunctions import get_users_display_number
from mig.shared.scriptinput import fieldstorage_to_dict
from mig.shared.ssh import execute_on_resource, copy_file_to_exe


def signature():
    """Signature of the main function"""

    defaults = {
        'exe': REJECT_UNSET,
        'unique_resource_name': REJECT_UNSET,
        'cputime': ['10000'],
        'nodecount': ['1'],
        'localjobname': [''],
        'sandboxkey': [''],
        'execution_delay': ['0'],
        'exe_pgid': ['0'],
        'sessionid': [''],
        'jobid': [''],
    }
    return ['', defaults]


# TODO: port to new functionality backend structure with standard validation

# ## Main ###

(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

if not configuration.site_enable_live_jobs:
    o.out('Not available on this site!')
    o.reply_and_exit(o.CLIENT_ERROR)

if "%s" % os.getenv('REQUEST_METHOD') != 'GET':
    o.out('Please use HTTP GET')
    o.reply_and_exit(o.ERROR)

# Make sure that we're actually called by an authenticated resource!

if "%s" % os.getenv('HTTPS') != 'on':
    o.out('Please use HTTPS with session id for authenticating job requests!'
          )
    o.reply_and_exit(o.ERROR)


# TODO: add session ID check here

remote_ip = "%s" % os.getenv('REMOTE_ADDR')

fieldstorage = cgi.FieldStorage()
user_arguments_dict = fieldstorage_to_dict(fieldstorage)
defaults = signature()[1]
output_objects = []
# IMPORTANT: validate all input args before doing ANYTHING with them!
(validate_status, accepted) = validate_input(
    user_arguments_dict,
    defaults,
    output_objects,
    allow_rejects=False,
    # NOTE: path cannot use wildcards here
    typecheck_overrides={},
)
if not validate_status:
    logger.error("input validation for %s failed: %s" %
                 (client_id, accepted))
    o.out('Invalid input arguments received!')
    o.reply_and_exit(o.ERROR)

exe = accepted['exe'][-1]
unique_resource_name = accepted['unique_resource_name'][-1]
cputime = accepted['cputime'][-1]
nodecount = accepted['nodecount'][-1]
localjobname = accepted['localjobname'][-1]
#sandboxkey = accepted['sandboxkey'][-1]
execution_delay = accepted['execution_delay'][-1]
#exe_pgid = accepted['exe_pgid'][-1]
sessionid = accepted['sessionid'][-1]
jobid = accepted['jobid'][-1]
o.out("interactive job request from '%s;%s;%s;%s;%s;%s;%s;%s;%s" % (
    remote_ip,
    exe,
    unique_resource_name,
    cputime,
    nodecount,
    localjobname,
    execution_delay,
    jobid,
    sessionid,
))

# Please note that base_dir must end in slash to avoid access to other
# resource dirs when own name is a prefix of another resource name

base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                        unique_resource_name)) + os.sep

# No owner check here so we need to specifically check for illegal
# directory traversals

if not valid_dir_input(configuration.resource_home,
                       unique_resource_name):

    # out of bounds - rogue resource!?!?

    o.out('invalid unique_resource_name! %s' % unique_resource_name)
    o.internal('requestinteractivejob called with illegal parameter(s) in what appears to be an illegal directory traversal attempt!: unique_resource_name %s, exe %s, client_id %s'
               % (unique_resource_name, exe, client_id))
    o.reply_and_exit(o.CLIENT_ERROR)

# Check that resource address matches request source to make DoS harder
try:
    check_source_ip(remote_ip, unique_resource_name)
except ValueError as vae:
    o.out("Warning: interactive job request not sent from expected resource address!")
    o.internal("invalid interactive job request: %s" % vae)
    o.reply_and_exit(o.CLIENT_ERROR)

# TODO: add full session ID check here

if exe == '':
    o.out('requestinteractivejob error! exe was not specified in the query string. Looks like a mis-configured resource!'
          )
    o.reply_and_exit(o.ERROR)

if jobid == '':
    o.out('requestinteractivejob error! jobid was not specified in the query string. Looks like a mis-configured resource!'
          )
    o.reply_and_exit(o.ERROR)

if unique_resource_name == '':
    o.out('requestinteractivejob error! unique_resource_name was not specified in the query string. Looks like a mis-configured resource!'
          )
    o.reply_and_exit(o.ERROR)

if localjobname == '':
    o.out('requestinteractivejob error! localjobname was not specified in the query string. Looks like a mis-configured resource!'
          )
    o.reply_and_exit(o.ERROR)


# TODO: check that the person who submitted the job (where the session ID points) is also the one that submitted the
# received jobid (to avoid a verified user specifies another users job id)

mrslfile = configuration.sessid_to_mrsl_link_home + sessionid + '.mRSL'

mrsldict = unpickle(mrslfile, logger)

if not mrsldict:
    o.out('requestinteractivejob error! Could not open mrsl file')
    o.reply_and_exit(o.ERROR)

job_submitter_client_id = mrsldict['USER_CERT']
o.out('job_submitter_client_id: %s' % job_submitter_client_id)

mrsl_jobid = mrsldict['JOB_ID']
if not jobid == mrsl_jobid:
    o.out('requestinteractivejob error! Wrong job_id specified!')
    o.reply_and_exit(o.ERROR)

# TODO: check the status of the specified job(id) and verify it has not previously been executed.
# The status must be ? (What about RETRY?)

if mrsldict['STATUS'] == 'FINISHED':
    o.out('requestinteractivejob error! Job already executed!')
    o.reply_and_exit(o.ERROR)

if not is_resource(unique_resource_name, configuration):
    o.out('requestinteractivejob error! Your unique_resource_name ' +
          ' is not recognized as a %s resource!' % configuration.short_title
          )
    o.reply_and_exit(o.ERROR)

(status, resource_conf) = \
    get_resource_configuration(configuration.resource_home,
                               unique_resource_name, logger)
if not status:
    o.out("No resouce_conf for: '" + unique_resource_name + "'\n")
    o.reply_and_exit(o.ERROR)

logger.info('getting exe')
(status, exe_conf) = get_resource_exe(resource_conf, exe, logger)
if not status:
    o.out("No EXE config for: '" + unique_resource_name + "' EXE: '"
          + exe + "'")
    o.reply_and_exit(o.ERROR)

# ################################################
# ## SSH to resource and start interactive job ###
# ################################################

# set the correct DISPLAY before calling SSH

display_number = get_users_display_number(job_submitter_client_id,
                                          configuration, logger)

if not display_number:
    o.out('could not find display number for %s in dict'
          % job_submitter_client_id)
    o.reply_and_exit(o.ERROR)

if display_number < 0:
    o.out('could not find valid display number for %s in dict'
          % job_submitter_client_id)
    o.reply_and_exit(o.ERROR)

o.internal('%s has display %s' % (job_submitter_client_id,
                                  display_number))

# os.putenv("DISPLAY", ":%s" % display_number)

os.environ['DISPLAY'] = ':%s' % display_number
logger.info('ENV TEST: %s' % os.getenv('DISPLAY'))

# copy .interactivejob to exe:

local_filename = configuration.mig_system_files + jobid\
    + '.interactivejob'
dest_filename = jobid + '.interactivejob'
(copy_status, copy_msg) = copy_file_to_exe(local_filename,
                                           dest_filename, resource_conf, exe, logger)
if not copy_status:
    o.out(copy_msg)
    o.reply_and_exit(o.ERROR)
logger.info('%s copied to resource %s  exe %s' % (local_filename,
                                                  unique_resource_name, exe))

# TODO: does this work with execute_on_exe() instead of manual ssh?
# execute .interactive on exe

ssh_command = \
    'ssh -X %s@%s \\"cd %s; mv -f %s job-dir_%s; cd job-dir_%s; chmod +x %s; bash -c \'./%s\'\\"'\
    % (
        exe_conf['execution_user'],
        exe_conf['execution_node'],
        exe_conf['execution_dir'],
        dest_filename,
        localjobname,
        localjobname,
        dest_filename,
        dest_filename,
    )
logger.info('execute_on_resource: %s' % ssh_command)
exit_code = -1
try:
    (exit_code, executed_command) = execute_on_resource(ssh_command,
                                                        False, resource_conf, logger)
except Exception as e:
    logger.error('Exception executing remote SSH from requestinteractivejob.py: %s '
                 % e)
    o.reply_and_exit(o.ERROR)

if exit_code != 0:
    logger.error('Error executing interactive job script on resource: %s command: %s exit code: %s'
                 % (unique_resource_name, executed_command, exit_code))
    o.reply_and_exit(o.ERROR)

o.out('requestinteractivejob OK. The job was started on the resource: %s exe: %s remote addr: %s'
      % (unique_resource_name, exe_conf, os.getenv('REMOTE_ADDR')))
o.reply_and_exit(o.OK)
