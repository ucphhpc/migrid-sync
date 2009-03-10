#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandboxmonitor - [insert a few words of module description on this line]
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

import os
import sys
import pickle
import getopt
import cgi

from shared.gridstat import GridStat
import shared.cgishared
from shared.conf import get_configuration_object

from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    defaults = {'show_all': ['']}
    return ['sandboxinfos', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    show_all = accepted['show_all'][-1]

    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Screen Saver Sandbox Monitor'})
    sandboxdb_file = configuration.sandbox_home + os.sep\
         + 'sandbox_users.pkl'

    # sandboxdb_file has the format: {username: (password, [list_of_resources])}

    PW = 0
    RESOURCES = 1

    # Load the user file

    try:
        fd = open(sandboxdb_file, 'rb')
        userdb = pickle.load(fd)
        fd.close()
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not read file with sandbox info! (%s)'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Load statistics objects

    gs = GridStat(configuration, logger)
    gs.update()

    sandboxinfos = []

    # loop through all users

    total_jobs = 0
    for username in userdb:
        resources = {}
        jobs_per_resource = 0
        jobs_per_user = 0

        # loop through all resources of each user

        for resource in userdb[username][RESOURCES]:

            # now find number of jobs successfully executed by resource

            jobs_per_resource = gs.get_value(gs.RESOURCE, resource,
                    'FINISHED')
            jobs_per_user += jobs_per_resource
            n = {resource: jobs_per_resource}
            resources.update(n)

        # if level == "basic":
            # print username,":", jobs_per_user, "jobs"
        # else:
            # print "---- ", username, " ----"

        if jobs_per_user > 0 or show_all == 'true':

            # print "<tr><td colspan='2'><h2>%s</h2></td></tr>" % username

            for res in resources.keys():
                if resources[res] > 0 or show_all == 'true':
                    sandboxinfo = {'object_type': 'sandboxinfo'}
                    sandboxinfo['username'] = username
                    sandboxinfo['resource'] = res
                    sandboxinfo['jobs'] = resources[res]

                    # print "<tr><td>%s</td><td>%s jobs</td></tr>" % (res, resources[res])
                    # print res,":", resources[res], "jobs"

                    sandboxinfos.append(sandboxinfo)

        total_jobs += jobs_per_user

        # print "Total jobs run by sandboxes: ", total_jobs, "jobs"............
        # print "<form action='sandbox-monitor.py' method='POST'>"

    output_objects.append({'object_type': 'sandboxinfos', 'sandboxinfos'
                          : sandboxinfos})
    output_objects.append({'object_type': 'text', 'text'
                          : 'Total jobs run by sandboxes: %s'
                           % total_jobs})
    return (output_objects, returnvalues.OK)


    # if show_all=='true':
    #    print "<tr><td align='center'><a href=?show_all=false>Hide empty resources</a></td></tr>"
    # else:
    #    print "<tr><td align='center'><a href=?show_all=true>Show all users and resources</a></td></tr>"
