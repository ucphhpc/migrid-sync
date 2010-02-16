#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# dashboard - Dashboard entry page backend
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

# See all_docs dictionary below for information about adding
# documentation topics.

"""Dashboard used as entry page"""

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables
from shared.useradm import client_id_dir
from shared.vgridaccess import user_allowed_resources
from shared.usercache import refresh_disk_stats, refresh_job_stats, \
     format_bytes, OWN, VGRID, JOBS, FILES, DIRECTORIES, BYTES, PARSE, \
     QUEUED, EXECUTING, FINISHED, RETRY, CANCELED, EXPIRED, FAILED


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    output_objects.append({'object_type': 'header', 'text'
                          : 'Dashboard'})
    output_objects.append({'object_type': 'sectionheader', 'text' :
                           "Welcome to the %s" % \
                           configuration.site_title})
    welcome_line = "Hi %(SSL_CLIENT_S_DN_CN)s" % os.environ
    output_objects.append({'object_type': 'text', 'text': welcome_line})
    dashboard_info = """
This is your private entry page or your dashboard where you can get a
quick status overview and find pointers to help and documentation.
When you are logged in with your user certificate, as you are now,
you can navigate your pages using the menu on the left.
""" % os.environ
    output_objects.append({'object_type': 'text', 'text': dashboard_info})

    # Only include external documentation in full mode
    if configuration.dashboardui == "full":
        output_objects.append({'object_type': 'sectionheader', 'text' :
                               'Documentation and Help'})
        online_help = """
%s includes some online documentation like the
""" % configuration.site_title
        output_objects.append({'object_type': 'text', 'text': online_help})
        output_objects.append({'object_type': 'link', 'destination': 'docs.py',
                               'text': 'On-demand documentation '})
        project_info = """
but additional background information and tutorials are available on the
"""
        output_objects.append({'object_type': 'text', 'text': project_info})
        output_objects.append({'object_type': 'link', 'destination':
                               'http://code.google.com/p/migrid/',
                               'text': 'Project page'})
        intro_info = """
The Getting Started guide there is a good starting point for new
users, and the wiki pages should answer the most common questions.
"""
        output_objects.append({'object_type': 'text', 'text': intro_info})
        support_info = """
In case you still have questions we recommend asking the developer and user
community online through the
"""
        output_objects.append({'object_type': 'text', 'text': support_info})
        output_objects.append({'object_type': 'link', 'destination':
                               'http://groups.google.com/group/migrid',
                               'text': 'Community page'})
        support_guide = """
in that way you get the quickest possible answer and other users can find
the answer there as well in the future.
"""
        output_objects.append({'object_type': 'text', 'text': support_guide})

        
        output_objects.append({'object_type': 'sectionheader', 'text' :
                               "Personal Settings"})
        settings_info = """
You can customize your personal pages if you like, by opening the Settings
page from the navigation menu and entering personal preferences. In that way you
can ease file and job handling or even completely redecorate your interface.
"""
        output_objects.append({'object_type': 'text', 'text': settings_info})

    output_objects.append({'object_type': 'sectionheader', 'text' :
                           "Status information"})
    job_dir = os.path.join(configuration.mrsl_files_dir, client_dir)
    job_stats = refresh_job_stats(configuration, client_id)
    total_jobs = {'total': sum(job_stats[JOBS].values()),
                  'parse': job_stats[JOBS][PARSE],
                  'queued': job_stats[JOBS][QUEUED],
                  'executing': job_stats[JOBS][EXECUTING],
                  'finished': job_stats[JOBS][FINISHED],
                  'retry': job_stats[JOBS][RETRY],
                  'canceled': job_stats[JOBS][CANCELED],
                  'expired': job_stats[JOBS][EXPIRED],
                  'failed': job_stats[JOBS][FAILED],
                  }
    job_info = """
You have submitted a total of %(total)d jobs:
%(parse)d parse, %(queued)d queued, %(executing)d executing, %(finished)d finished, %(retry)s retry,
%(canceled)d canceled, %(expired)d expired and %(failed)d failed.
""" % total_jobs
    output_objects.append({'object_type': 'text', 'text': job_info})
    resource_count = len(user_allowed_resources(configuration, client_id))
    resource_info = """
%d resources allow execution of your jobs.
""" % resource_count
    output_objects.append({'object_type': 'text', 'text': resource_info})
    disk_stats = refresh_disk_stats(configuration, client_id)
    total_disk = {'own_files': disk_stats[OWN][FILES],
                 'own_directories': disk_stats[OWN][DIRECTORIES],
                 'own_megabytes': format_bytes(disk_stats[OWN][BYTES], 'mega'),
                 'vgrid_files': disk_stats[VGRID][FILES],
                 'vgrid_directories': disk_stats[VGRID][DIRECTORIES],
                 'vgrid_megabytes': format_bytes(disk_stats[VGRID][BYTES], 'mega')
                  }
    disk_info = """
Your own %(own_files)d files and %(own_directories)d directories take up %(own_megabytes).1f MB in total
and you additionally share %(vgrid_files)d files and %(vgrid_directories)d directories of
%(vgrid_megabytes).1f MB in total.
""" % total_disk
    output_objects.append({'object_type': 'text', 'text': disk_info})
    cert_info = """
Your user certificate expires on %s .
""" % os.environ['SSL_CLIENT_V_END']
    output_objects.append({'object_type': 'text', 'text': cert_info})

    #env_info = """Env %s""" % os.environ
    #output_objects.append({'object_type': 'text', 'text': env_info})

    return (output_objects, returnvalues.OK)


