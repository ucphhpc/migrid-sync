#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userstats - Display some user specific stats
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

"""Display user stats like job states and disk use"""

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables
from shared.usercache import refresh_disk_stats, refresh_job_stats, \
     format_bytes, OWN, VGRID, JOBS, FILES, DIRECTORIES, BYTES, PARSE, \
     QUEUED, EXECUTING, FINISHED, RETRY, CANCELED, EXPIRED, FAILED
from shared.vgridaccess import user_allowed_res_exes


def signature():
    """Signature of the main function"""

    defaults = {
        'stats': ['jobs', 'disk', 'resources', 'certificate'],
        }
    return ['user_stats', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    stats = accepted['stats']

    status = returnvalues.OK

    user_stats = {'object_type': 'user_stats', 'disk': None, 'jobs': None,
                  'resources': None, 'certificate': None}
    if 'disk' in stats:
        disk_stats = refresh_disk_stats(configuration, client_id)
        total_disk = {'own_files': disk_stats[OWN][FILES],
                      'own_directories': disk_stats[OWN][DIRECTORIES],
                      'own_megabytes': format_bytes(disk_stats[OWN][BYTES], 'mega'),
                      'vgrid_files': disk_stats[VGRID][FILES],
                      'vgrid_directories': disk_stats[VGRID][DIRECTORIES],
                      'vgrid_megabytes': format_bytes(disk_stats[VGRID][BYTES], 'mega')
                  }
        user_stats['disk'] = total_disk
    if 'jobs' in stats:
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
        user_stats['jobs'] = total_jobs
    if 'resources' in stats:
        allowed_res = user_allowed_res_exes(configuration, client_id)
        # allowed_res is dictionary of res ID and list of attached exe names
        resource_count = len(allowed_res.keys())
        exe_count = 0
        for exes in allowed_res.values():
            exe_count += len(exes)
        total_res = {'resources': resource_count, 'exes': exe_count}
        user_stats['resources'] = total_res
    if 'certificate' in stats:
        total_cert = {'distinguished_name': os.environ['SSL_CLIENT_S_DN'],
                      'expire': os.environ['SSL_CLIENT_V_END']}
        user_stats['certificate'] = total_cert


    output_objects.append(user_stats)
    
    return (output_objects, status)


