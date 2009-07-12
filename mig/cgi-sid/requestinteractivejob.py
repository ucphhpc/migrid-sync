#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# requestinteractivejob - [insert a few words of module description on this line]
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

import cgi
import os
import sys
import fcntl
import time

from shared.ssh import execute_on_resource, copy_file_to_exe
from shared.conf import get_resource_configuration, get_resource_exe
from shared.livedisplaysfunctions import get_users_display_number
from shared.validstring import valid_dir_input
from shared.cgishared import init_cgiscript_possibly_with_cert
from shared.findtype import is_resource
from shared.fileio import unpickle

# ## Main ###

(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

if str(os.getenv('REQUEST_METHOD')) != 'GET':
    o.out('Please use HTTP GET')
    o.reply_and_exit(o.ERROR)

# Make sure that we're actually called by an authenticated resource!

if str(os.getenv('HTTPS')) != 'on':
    o.out('Please use HTTPS with session id for authenticating job requests!'
          )
    o.reply_and_exit(o.ERROR)
logger.info('REQUESTINTERACTIVEJOB CALLED')

# TODO: add session ID check here

remote_ip = str(os.getenv('REMOTE_ADDR'))

fieldstorage = cgi.FieldStorage()

jobid = fieldstorage.getfirst('jobid', '')
exe_name = fieldstorage.getfirst('exe', '')
unique_resource_name = fieldstorage.getfirst('unique_resource_name', '')
localjobname = fieldstorage.getfirst('localjobname', '')
sessionid = fieldstorage.getfirst('sessionid', '')

o.out('interactivejob request from %s %s %s %s' % (remote_ip, exe_name,
      unique_resource_name, jobid))

# Please note that base_dir must end in slash to avoid access to other
# resource dirs when own name is a prefix of another resource name

base_dir = os.path.abspath(configuration.resource_home + os.sep
                            + unique_resource_name) + os.sep

# No owner check here so we need to specifically check for illegal
# directory traversals

if not valid_dir_input(configuration.resource_home,
                       unique_resource_name):

    # out of bounds - rogue resource!?!?

    o.out('invalid unique_resource_name! %s' % unique_resource_name)
    o.internal('requestinteractivejob called with illegal parameter(s) in what appears to be an illegal directory traversal attempt!: unique_resource_name %s, exe_name %s, client_id %s'
                % (unique_resource_name, exe_name, client_id))
    o.reply_and_exit(o.CLIENT_ERROR)

if exe_name == '':
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

# Check that resource address matches request source
# TODO: get real ip and enable this check
# remote_ip = str(os.getenv("REMOTE_ADDR"))
# resource_ip = "0.0.0.0"
# if remote_ip != resource_ip:
#    print "Warning: job request not sent from expected resource address!"
#    logger.warning("job request not issued from address of resource! (%s != %s)", remote_ip, resource_ip)

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

if not is_resource(unique_resource_name, configuration.resource_home):
    o.out('requestinteractivejob error! Your unique_resource_name is not recognized as a MiG resource!'
          )
    o.reply_and_exit(o.ERROR)

(status, resource_config) = \
    get_resource_configuration(configuration.resource_home,
                               unique_resource_name, logger)
if not status:
    o.out("No resouce_config for: '" + unique_resource_name + "'\n")
    o.reply_and_exit(o.ERROR)

logger.info('getting exe')
(status, exe) = get_resource_exe(resource_config, exe_name, logger)
if not status:
    o.out("No EXE config for: '" + unique_resource_name + "' EXE: '"
           + exe_name + "'")
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
logger.info('ENV TEST: %s' % str(os.getenv('DISPLAY')))

# copy .interactivejob to exe:

local_filename = configuration.mig_system_files + jobid\
     + '.interactivejob'
dest_filename = jobid + '.interactivejob'
(copy_status, copy_msg) = copy_file_to_exe(local_filename,
        dest_filename, resource_config, exe_name, logger)
if not copy_status:
    o.out(copy_msg)
    o.reply_and_exit(o.ERROR)
logger.info('%s copied to resource %s  exe %s' % (local_filename,
            unique_resource_name, exe_name))

# TODO: does this work with execute_on_exe() instead of manual ssh?
# execute .interactive on exe

ssh_command = \
    'ssh -X %s@%s \\"cd %s; mv -f %s job-dir_%s; cd job-dir_%s; chmod +x %s; bash -c \'./%s\'\\"'\
     % (
    exe['execution_user'],
    exe['execution_node'],
    exe['execution_dir'],
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
            False, resource_config, logger)
except Exception, e:
    logger.error('Exception executing remote SSH from requestinteractivejob.py: %s '
                  % e)
    o.reply_and_exit(o.ERROR)

if exit_code != 0:
    logger.error('Error executing interactive job script on resource: %s command: %s exit code: %s'
                  % (unique_resource_name, executed_command, exit_code))
    o.reply_and_exit(o.ERROR)

o.out('requestinteractivejob OK. The job was started on the resource: %s exe: %s remote addr: %s'
       % (unique_resource_name, exe, os.getenv('REMOTE_ADDR')))
o.reply_and_exit(o.OK)
