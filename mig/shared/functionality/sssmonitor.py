#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sssmonitor - Global SSS monitor back end
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

import datetime

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input
from shared.gridstat import GridStat
from shared.sandbox import load_sandbox_db

# sandbox db has the format: {username: (password, [list_of_resources])}

PW, RESOURCES = 0, 1


def signature():
    """Signature of the main function"""

    defaults = {'show_all': [''], 'sort': [''], 'group_by': ['']}
    return ['sandboxinfos', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_menu=client_id)

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    show_all = accepted['show_all'][-1].lower()
    sort = accepted['sort'][-1]
    group_by = accepted['group_by'][-1].lower()

    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Screen Saver Sandbox Monitor'})

    # Load the user file

    try:
        userdb = load_sandbox_db(configuration)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not read file with sandbox info! (%s)'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Load statistics objects

    grid_stat = GridStat(configuration, logger)
    grid_stat.update()

    sandboxinfos = []

    # loop through all users

    total_jobs = 0
    for username in userdb:
        resources_jobs = {}

        jobs_per_resource = 0
        jobs_per_user = 0

        resources_walltime = {}
        walltime_per_resource = datetime.timedelta(0)
        walltime_per_user = datetime.timedelta(0)

        # loop through all resources of each user

        for resource in userdb[username][RESOURCES]:

            # now find number of jobs successfully executed by resource

            jobs_per_resource = \
                grid_stat.get_value(grid_stat.RESOURCE_TOTAL, resource,
                                    'FINISHED')
            jobs_per_user += jobs_per_resource
            n = {resource: jobs_per_resource}
            resources_jobs.update(n)

            walltime_per_resource = \
                grid_stat.get_value(grid_stat.RESOURCE_TOTAL, resource,
                                    'USED_WALLTIME')

            if walltime_per_resource != 0:
                if not walltime_per_user:
                    walltime_per_user = walltime_per_resource
                else:
                    walltime_per_user += walltime_per_resource

            n = {resource: walltime_per_resource}
            resources_walltime.update(n)

        if group_by == 'users' and (jobs_per_user > 0 or show_all
                                     == 'true'):
            sandboxinfo = {'object_type': 'sandboxinfo'}
            sandboxinfo['username'] = username
            sandboxinfo['resource'] = len(userdb[username][RESOURCES])
            sandboxinfo['jobs'] = jobs_per_user
            sandboxinfo['walltime'] = walltime_per_user
            sandboxinfos.append(sandboxinfo)
        elif jobs_per_user > 0 or show_all == 'true':
            for res in resources_jobs.keys():
                if resources_jobs[res] > 0 or show_all == 'true':
                    sandboxinfo = {'object_type': 'sandboxinfo'}
                    sandboxinfo['username'] = username
                    sandboxinfo['resource'] = res
                    sandboxinfo['jobs'] = resources_jobs[res]
                    sandboxinfo['walltime'] = resources_walltime[res]
                    sandboxinfos.append(sandboxinfo)

        total_jobs += jobs_per_user

    if 'username' == sort:

        # sort by owner: case insensitive

        sandboxinfos.sort(cmp=lambda a, b: cmp(a['username'].lower(),
                          b['username'].lower()))
    elif 'resource' == sort:

        # sort by numerical resource ID

        if group_by == 'users':
            sandboxinfos.sort(cmp=lambda a, b: cmp(int(b['resource']),
                              int(a['resource'])))
        else:

            sandboxinfos.sort(cmp=lambda a, b: cmp(int(a['resource'
                              ].lower().replace('sandbox.', '')),
                              int(b['resource'
                              ].lower().replace('sandbox.', ''))))
    elif 'jobs' == sort:

        # sort by most jobs done

        sandboxinfos.sort(reverse=True)
    elif 'walltime' == sort:

        # sort by most walltime

        sandboxinfos.sort(cmp=lambda a, b: cmp(a['walltime'].days
                           * 86400 + a['walltime'].seconds, b['walltime'
                          ].days * 86400 + b['walltime'].seconds),
                          reverse=True)
    else:

        # do not sort

        pass

    # Sort

    output_objects.append({'object_type': 'verbatim', 'text'
                          : 'Sort by: '})
    
    link_list = []
    for name in ('username', 'resource', 'jobs', 'walltime'):
        link_list.append({'object_type': 'link', 'destination'
                         : '?sort=%s&group_by=%s' % (name, group_by),
                         'text': '%s' % name.capitalize()})

    output_objects.append({'object_type': 'multilinkline', 'links'
                          : link_list})

    # Group

    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'verbatim', 'text': 'Show: '})

    link_list = []
    for name in ('resources', 'users'):
        link_list.append({'object_type': 'link', 'destination'
                         : '?sort=%s&group_by=%s' % (sort, name), 'text'
                         : '%s' % name.capitalize()})

    output_objects.append({'object_type': 'multilinkline', 'links'
                          : link_list})
    # Time stamp

    now = datetime.datetime.now()
    output_objects.append({'object_type': 'text', 'text'
                          : 'Updated on %s' % now})
    output_objects.append({'object_type': 'text', 'text': ''})

    
    # Actual stats

    output_objects.append({'object_type': 'sandboxinfos', 'sandboxinfos'
                          : sandboxinfos})
    output_objects.append({'object_type': 'text', 'text'
                          : 'Total jobs run by sandboxes: %s'
                           % total_jobs})
    return (output_objects, returnvalues.OK)
