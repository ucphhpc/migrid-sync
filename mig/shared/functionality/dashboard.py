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

    output_objects.append({'object_type': 'header', 'text'
                          : 'Dashboard'})
    output_objects.append({'object_type': 'sectionheader', 'text' :
                           "Welcome to the Minimum intrusion Grid"})
    welcome_line = "Hi %(SSL_CLIENT_S_DN_CN)s" % os.environ
    output_objects.append({'object_type': 'text', 'text': welcome_line})
    dashboard_info = """
This is your private MiG entry page or your dashboard where you can get a
quick status overview and find pointers to help and documentation.
When you are logged into your MiG page with your user certificate, as you are now,
you can navigate your pages using the menu bar.
""" % os.environ
    output_objects.append({'object_type': 'text', 'text': dashboard_info})

    output_objects.append({'object_type': 'sectionheader', 'text' :
                           'Documentation and Help'})
    online_help = """
MiG includes some online documentation like the
"""
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
In case you still have questions we recommend asking the MiG developer and user
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
                           "MiG Settings"})
    settings_info = """
You can customize your personal MiG interface if you like, by opening the Settings
page from the navigation menu and entering personal preferences. In that way you
can ease file and job handling or even completely redecorate your interface.
"""
    output_objects.append({'object_type': 'text', 'text': settings_info})

    output_objects.append({'object_type': 'sectionheader', 'text' :
                           "Status information"})
    job_dir = os.path.join(configuration.mrsl_files_dir, client_dir)
    job_count = len(os.listdir(job_dir))
    job_info = """
You have submitted a total of %d jobs.
""" % job_count
    output_objects.append({'object_type': 'text', 'text': job_info})
    cert_info = """
Your user certificate expires on %s .
""" % os.environ['SSL_CLIENT_V_END']
    output_objects.append({'object_type': 'text', 'text': cert_info})

    #env_info = """Env %s""" % os.environ
    #output_objects.append({'object_type': 'text', 'text': env_info})

    return (output_objects, returnvalues.OK)


