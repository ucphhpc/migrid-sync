#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_monitor - Monitor page generator
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

"""Creating the MiG monitor page"""
from __future__ import print_function

import datetime
import os
import sys
import time

from shared.conf import get_configuration_object
from shared.defaults import default_vgrid
from shared.fileio import unpickle
from shared.gridstat import GridStat
from shared.html import get_xgi_html_header, get_xgi_html_footer, \
    themed_styles, themed_scripts
from shared.logger import daemon_logger, register_hangup_handler
from shared.output import format_timedelta
from shared.resource import anon_resource_id
from shared.vgridaccess import get_vgrid_map_vgrids

configuration, logger = None, None


def create_monitor(vgrid_name):
    """Write monitor HTML file for vgrid_name"""

    html_file = os.path.join(configuration.vgrid_home, vgrid_name,
                             '%s.html' % configuration.vgrid_monitor)

    print('collecting statistics for VGrid %s' % vgrid_name)
    sleep_secs = configuration.sleep_secs
    slackperiod = configuration.slackperiod
    now = time.asctime(time.localtime())

    html_vars = {
        'sleep_secs': sleep_secs,
        'vgrid_name': vgrid_name,
        'logo_url': '/images/logo.jpg',
        'now': now,
        'short_title': configuration.short_title,
    }

    monitor_meta = '''<meta http-equiv="refresh" content="%(sleep_secs)s" />
''' % html_vars
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
    '''
    add_init = ''
    add_ready = '''
          // table initially sorted by col. 1 (name)
          var sortOrder = [[1,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }
          $("table.monitor").tablesorter({widgets: ["zebra"],
                                          textExtraction: imgTitle,
                                         });
          $("table.monitor").each(function () {
              try {
                  $(this).trigger("sorton", [sortOrder]);
              } catch(err) {
                  /* tablesorter chokes on empty tables - just continue */
              }
          });
    '''
    monitor_js = '''
%s

<script type="text/javascript" >

%s

$(document).ready(function() {
%s
          }
);
</script>
''' % (add_import, add_init, add_ready)

    # User default site style
    style_helpers = themed_styles(configuration)
    script_helpers = themed_scripts(configuration)
    script_helpers['advanced'] += add_import
    script_helpers['init'] += add_init
    script_helpers['ready'] += add_ready
    html = get_xgi_html_header(
        configuration,
        '%(short_title)s Monitor, VGrid %(vgrid_name)s' % html_vars,
        '',
        html=True,
        meta=monitor_meta,
        style_map=style_helpers,
        script_map=script_helpers,
        frame=False,
        menu=False,
        widgets=False,
        userstyle=False,
    )
    html += \
        '''
<!-- end of raw header: this line is used by showvgridmonitor -->
<h1>Statistics/monitor for the %(vgrid_name)s VGrid</h1>
<div class="generatornote smallcontent">
This page was generated %(now)s (automatic refresh every %(sleep_secs)s secs).
</div>
'''\
         % html_vars

    # loop and get totals

    parse_count = 0
    queued_count = 0
    frozen_count = 0
    executing_count = 0
    finished_count = 0
    failed_count = 0
    retry_count = 0
    canceled_count = 0

    cpucount_requested = 0
    cpucount_done = 0
    nodecount_requested = 0
    nodecount_done = 0
    cputime_requested = 0
    cputime_done = 0
    used_walltime = 0
    disk_requested = 0
    disk_done = 0
    memory_requested = 0
    memory_done = 0
    runtimeenv_dict = {'': 0}
    runtimeenv_requested = 0
    runtimeenv_done = 0

    number_of_jobs = 0
    up_count = 0
    down_count = 0
    slack_count = 0

    job_assigned = 0
    job_assigned_cpus = 0

    gstat = GridStat(configuration, logger)

    runtimeenv_dict = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                      'RUNTIMEENVIRONMENT', {})

    parse_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                  'PARSE')
    queued_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   'QUEUED')
    frozen_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   'FROZEN')
    executing_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                      'EXECUTING')
    failed_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   'FAILED')
    retry_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                  'RETRY')
    canceled_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                     'CANCELED')
    expired_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                    'EXPIRED')
    finished_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                     'FINISHED')

    nodecount_requested = gstat.get_value(gstat.VGRID,
                                          vgrid_name.upper(), 'NODECOUNT_REQ')
    nodecount_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                     'NODECOUNT_DONE')
    cputime_requested = gstat.get_value(gstat.VGRID,
                                        vgrid_name.upper(), 'CPUTIME_REQ')
    cputime_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   'CPUTIME_DONE')

    used_walltime = gstat.get_value(gstat.VGRID,
                                    vgrid_name.upper(),
                                    'USED_WALLTIME')

    if (used_walltime == 0):
        used_walltime = datetime.timedelta(0)

    used_walltime = format_timedelta(used_walltime)

    disk_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                     'DISK_REQ')
    disk_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                'DISK_DONE')
    memory_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                       'MEMORY_REQ')
    memory_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                  'MEMORY_DONE')
    cpucount_requested = gstat.get_value(gstat.VGRID,
                                         vgrid_name.upper(), 'CPUCOUNT_REQ')
    cpucount_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                    'CPUCOUNT_DONE')
    runtimeenv_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                           'RUNTIMEENVIRONMENT_REQ')
    runtimeenv_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                      'RUNTIMEENVIRONMENT_DONE')

    number_of_jobs = parse_count
    number_of_jobs += queued_count
    number_of_jobs += frozen_count
    number_of_jobs += expired_count
    number_of_jobs += canceled_count
    number_of_jobs += failed_count
    number_of_jobs += executing_count
    number_of_jobs += finished_count
    number_of_jobs += retry_count

    html_vars = {
        'parse_count': parse_count,
        'queued_count': queued_count,
        'frozen_count': frozen_count,
        'executing_count': executing_count,
        'failed_count': failed_count,
        'retry_count': retry_count,
        'canceled_count': canceled_count,
        'expired_count': expired_count,
        'finished_count': finished_count,
        'number_of_jobs': number_of_jobs,
        'cpucount_requested': cpucount_requested,
        'cpucount_done': cpucount_done,
        'nodecount_requested': nodecount_requested,
        'nodecount_done': nodecount_done,
        'cputime_requested': cputime_requested,
        'cputime_done': cputime_done,
        'used_walltime': used_walltime,
        'disk_requested': disk_requested,
        'disk_done': disk_done,
        'memory_requested': memory_requested,
        'memory_done': memory_done,
        'runtimeenv_requested': runtimeenv_requested,
        'runtimeenv_done': runtimeenv_done,
    }

    html += \
        """<h2>Job Stats</h2><table class=monitorstats><tr><td>
<table class=monitorjobs><tr class=title><td>Job State</td><td>Number of jobs</td></tr>
<tr><td>Parse</td><td>%(parse_count)s</td></tr>
<tr><td>Queued</td><td>%(queued_count)s</td></tr>
<tr><td>Frozen</td><td>%(frozen_count)s</td></tr>
<tr><td>Executing</td><td>%(executing_count)s</td></tr>
<tr><td>Failed</td><td>%(failed_count)s</td></tr>
<tr><td>Retry</td><td>%(retry_count)s</td></tr>
<tr><td>Canceled</td><td>%(canceled_count)s</td></tr>
<tr><td>Expired</td><td>%(expired_count)s</td></tr>
<tr><td>Finished</td><td>%(finished_count)s</td></tr>
<tr><td>Total</td><td>%(number_of_jobs)s</td></tr>
</table>
</td><td>
<table class=monitorresreq>
<tr class=title><td>Requirement</td><td>Requested</td><td>Done</td></tr>
<tr><td>Cpucount</td><td>%(cpucount_requested)s</td><td>%(cpucount_done)s</td></tr>
<tr><td>Nodecount</td><td>%(nodecount_requested)s</td><td>%(nodecount_done)s</td></tr>
<tr><td>Cputime</td><td>%(cputime_requested)s</td><td>%(cputime_done)s</td></tr>
<tr><td>GB Disk</td><td>%(disk_requested)s</td><td>%(disk_done)s</td></tr>
<tr><td>MB Memory</td><td>%(memory_requested)s</td><td>%(memory_done)s</td></tr>
<tr><td>Runtime Envs</td><td>%(runtimeenv_requested)s</td><td>%(runtimeenv_done)s</td></tr>
<tr><td>Used Walltime</td><td colspan='2'>%(used_walltime)s</td></tr>
</table><br />
</td><td>
<div class=monitorruntimeenvdetails>
<table class=monitorruntimeenvdone>
<tr class=title><td>Runtime Envs Done</td><td></td></tr>
"""\
         % html_vars

    if len(runtimeenv_dict.keys()) < 1:

        # No runtimeenv requests

        html += '<tr><td></td><td>-</td></tr>\n'
    else:
        for entry in runtimeenv_dict.keys():
            if not entry == '':
                html += '<tr><td>' + entry + '</td><td>'\
                    + str(runtimeenv_dict[entry]) + '</td></tr>\n'

    total_number_of_exe_resources, total_number_of_store_resources = 0, 0
    total_number_of_exe_cpus, total_number_of_store_gigs = 0, 0

    vgrid_name_list = vgrid_name.split('/')
    current_dir = ''

    exes, stores = '', ''
    for vgrid_name_part in vgrid_name_list:
        current_dir = os.path.join(current_dir, vgrid_name_part)
        abs_mon_dir = os.path.join(configuration.vgrid_home, current_dir)
        # print 'dir: %s' % abs_mon_dir
        # Potential race - just ignore if it disappeared
        try:
            sorted_names = os.listdir(abs_mon_dir)
        except OSError:
            continue
        sorted_names.sort()
        for filename in sorted_names:
            # print filename
            if filename.startswith('monitor_last_request_'):

                # read last request helper file

                mon_file_name = os.path.join(abs_mon_dir, filename)
                print('found ' + mon_file_name)
                last_request_dict = unpickle(mon_file_name, logger)
                if not last_request_dict:
                    print('could not open and unpickle: '\
                        + mon_file_name)
                    continue
                if 'CREATED_TIME' not in last_request_dict:
                    print('skip broken last request dict: '\
                        + mon_file_name)
                    continue

                difference = datetime.datetime.now()\
                    - last_request_dict['CREATED_TIME']
                days = str(difference.days)
                hours = str(difference.seconds / 3600)
                minutes = str((difference.seconds % 3600) / 60)
                seconds = str((difference.seconds % 60) % 60)

                last_timetuple = last_request_dict['CREATED_TIME'].timetuple()

                if 'CPUTIME' in last_request_dict:
                    cputime = last_request_dict['CPUTIME']
                elif 'cputime' in last_request_dict:
                    cputime = last_request_dict['cputime']
                else:
                    print('ERROR: last request does not contain cputime field!: %s'\
                        % last_request_dict)
                    continue

                try:
                    cpusec = int(cputime)
                except ValueError:
                    try:
                        cpusec = int(float(cputime))
                    except ValueError as verr:
                        print('ERROR: failed to parse cputime %s: %s'\
                            % (cputime, verr))

                # Include execution delay guesstimate for strict fill
                # LRMS resources

                try:
                    delay = int(last_request_dict['EXECUTION_DELAY'])
                except KeyError:
                    delay = 0
                except ValueError:
                    delay = 0

                time_remaining = (last_request_dict['CREATED_TIME']
                                  + datetime.timedelta(seconds=cpusec)
                                  + datetime.timedelta(seconds=delay))\
                    - datetime.datetime.now()
                days_rem = str(time_remaining.days)
                hours_rem = str(time_remaining.seconds / 3600)
                minutes_rem = str((time_remaining.seconds % 3600) / 60)
                seconds_rem = str((time_remaining.seconds % 60) % 60)

                if time_remaining.days < -7:
                    try:
                        print('removing: %s as we havent seen him for %s days.'\
                            % (mon_file_name, abs(time_remaining).days))
                        os.remove(mon_file_name)
                    except Exception as err:
                        print("could not remove: '%s' Error: %s"\
                            % (mon_file_name, str(err)))
                    pass
                else:
                    unique_res_name_and_exe_list = \
                        filename.split('monitor_last_request_', 1)
                    if cpusec == 0:
                        resource_status = 'unavailable'
                    elif time_remaining.days < 0:

                        # time_remaining.days < 0 means that we have passed the specified time

                        time_rem_abs = abs(time_remaining)
                        if time_rem_abs.days == 0\
                                and int(time_rem_abs.seconds)\
                                < int(slackperiod):
                            resource_status = 'slack'
                            slack_count = slack_count + 1
                        else:
                            resource_status = 'offline'
                            down_count = down_count + 1
                    else:
                        resource_status = 'online'
                        up_count = up_count + 1

                    exes += '<tr>'
                    exes += \
                        '<td><img src=/images/status-icons/%s.png /></td>'\
                        % resource_status
                    public_id = unique_res_name_and_exe_list[1]
                    if last_request_dict['RESOURCE_CONFIG'].get('ANONYMOUS', True):
                        public_id = anon_resource_id(public_id)
                    public_name = last_request_dict['RESOURCE_CONFIG'].get(
                        'PUBLICNAME', '')
                    resource_parts = public_id.split('_', 2)
                    resource_name = "<a href='viewres.py?unique_resource_name=%s'>%s</a>" % \
                                    (resource_parts[0], resource_parts[0])
                    if public_name:
                        resource_name += "<br />(alias %s)" % public_name
                    else:
                        resource_name += "<br />(no alias)"
                    resource_name += "<br />%s" % resource_parts[1]
                    exes += '<td>%s</td>' % resource_name

                    last_asctime = time.asctime(last_timetuple)
                    last_epoch = time.mktime(last_timetuple)
                    exes += '<td><div class="sortkey">%s</div>%s<br />' %  \
                            (last_epoch, last_asctime)
                    exes += '(%sd %sh %sm %ss ago)</td>' % (days, hours, minutes,
                                                            seconds)
                    exes += '<td>' + vgrid_name + '</td>'
                    runtime_envs = last_request_dict['RESOURCE_CONFIG'
                                                     ]['RUNTIMEENVIRONMENT']
                    runtime_envs.sort()
                    re_list_text = ', '.join([i[0] for i in runtime_envs])
                    exes += '<td title="%s">' % re_list_text \
                        + str(len(runtime_envs)) + '</td>'
                    exes += '<td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['CPUTIME']) + '</td><td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['NODECOUNT']) + '</td><td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['CPUCOUNT']) + '</td><td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['DISK']) + '</td><td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['MEMORY']) + '</td><td>'\
                        + str(last_request_dict['RESOURCE_CONFIG'
                                                ]['ARCHITECTURE']) + '</td>'
                    exes += '<td>' + last_request_dict['STATUS']\
                        + '</td><td>' + str(last_request_dict['CPUTIME'
                                                              ]) + '</td>'

                    exes += '<td class=status_%s>' % resource_status
                    if 'unavailable' == resource_status:
                        exes += '-'
                    elif 'slack' == resource_status:
                        exes += 'Within slack period (%s < %s secs)'\
                            % (time_rem_abs.seconds, slackperiod)
                    elif 'offline' == resource_status:
                        exes += 'down?'
                    else:
                        exes += '%sd, %sh, %sm, %ss'\
                            % (days_rem, hours_rem, minutes_rem,
                                seconds_rem)
                    exes += '</td>'

                    exes += '</tr>\n'
                    if last_request_dict['STATUS'] == 'Job assigned':
                        job_assigned = job_assigned + 1
                        job_assigned_cpus = job_assigned_cpus\
                            + int(last_request_dict['RESOURCE_CONFIG'
                                                    ]['NODECOUNT'])\
                            * int(last_request_dict['RESOURCE_CONFIG'
                                                    ]['CPUCOUNT'])

                    total_number_of_exe_resources += 1
                    total_number_of_exe_cpus += int(
                        last_request_dict['RESOURCE_CONFIG']['NODECOUNT']) \
                        * int(last_request_dict['RESOURCE_CONFIG']['CPUCOUNT'])
            elif filename.startswith('monitor_last_status_'):

                # store must be linked to this vgrid, not only parent vgrid:
                # inheritance only covers access, not automatic participation

                if current_dir != vgrid_name:
                    continue

                # read last resource action status file

                mon_file_name = os.path.join(abs_mon_dir, filename)
                print('found ' + mon_file_name)
                last_status_dict = unpickle(mon_file_name, logger)
                if not last_status_dict:
                    print('could not open and unpickle: '\
                        + mon_file_name)
                    continue
                if 'CREATED_TIME' not in last_status_dict:
                    print('skip broken last request dict: '\
                        + mon_file_name)
                    continue

                difference = datetime.datetime.now()\
                    - last_status_dict['CREATED_TIME']
                days = str(difference.days)
                hours = str(difference.seconds / 3600)
                minutes = str((difference.seconds % 3600) / 60)
                seconds = str((difference.seconds % 60) % 60)

                if last_status_dict['STATUS'] == 'stopped':
                    time_stopped = datetime.datetime.now() - \
                        last_status_dict['CREATED_TIME']
                    if time_stopped.days > 7:
                        try:
                            print('removing: %s as we havent seen him for %s days.'\
                                  % (mon_file_name, abs(time_stopped).days))
                            os.remove(mon_file_name)
                        except Exception as err:
                            print("could not remove: '%s' Error: %s"\
                                  % (mon_file_name, str(err)))
                        continue

                unique_res_name_and_store_list = filename.split(
                    'monitor_last_status_', 1)
                mount_point = last_status_dict.get('MOUNT_POINT', 'UNKNOWN')
                is_live = os.path.ismount(mount_point)

                public_id = unique_res_name_and_store_list[1]
                if last_status_dict['RESOURCE_CONFIG'].get('ANONYMOUS', True):
                    public_id = anon_resource_id(public_id)

                vgrid_link = os.path.join(
                    configuration.vgrid_files_home, vgrid_name, public_id)
                is_linked = (os.path.realpath(vgrid_link) == mount_point)

                total_disk = last_status_dict['RESOURCE_CONFIG']['DISK']
                free_disk, avail_disk, used_disk, used_percent = 0, 0, 0, 0
                gig_bytes = 1.0 * 2**30

                # Fall back status - show last action unless statvfs succeeds

                last_status = last_status_dict['STATUS']
                last_timetuple = last_status_dict['CREATED_TIME'].timetuple()

                # These disk stats are slightly confusing but match 'df'
                # 'available' is the space that can actually be used so it
                # is typically less than 'free'.

                try:
                    disk_stats = os.statvfs(mount_point)
                    total_disk = disk_stats.f_bsize * disk_stats.f_blocks / \
                        gig_bytes
                    avail_disk = disk_stats.f_bsize * disk_stats.f_bavail / \
                        gig_bytes
                    free_disk = disk_stats.f_bsize * disk_stats.f_bfree / \
                        gig_bytes
                    used_disk = total_disk - free_disk
                    used_percent = 100.0 * used_disk / (avail_disk + used_disk)
                    last_status = 'checked'
                    last_timetuple = datetime.datetime.now().timetuple()
                    days, hours, minutes, seconds = 0, 0, 0, 0
                except OSError as ose:
                    print('could not stat mount point %s: %s' % \
                        (mount_point, ose))
                    is_live = False
                if last_status_dict['STATUS'] == 'stopped':
                    resource_status = 'offline'
                    down_count = down_count + 1
                elif last_status_dict['STATUS'] == 'started':
                    if is_live and is_linked:
                        resource_status = 'online'
                        up_count = up_count + 1
                    else:
                        resource_status = 'slack'
                        down_count = down_count + 1
                else:
                    resource_status = 'unknown'

                stores += '<tr>'
                stores += \
                    '<td><img src=/images/status-icons/%s.png /></td>'\
                    % resource_status
                public_name = last_status_dict['RESOURCE_CONFIG'].get(
                    'PUBLICNAME', '')
                resource_parts = public_id.split('_', 2)
                resource_name = "<a href='viewres.py?unique_resource_name=%s'>%s</a>" % \
                                (resource_parts[0], resource_parts[0])
                if public_name:
                    resource_name += "<br />(alias %s)" % public_name
                else:
                    resource_name += "<br />(no alias)"
                resource_name += "<br />%s" % resource_parts[1]
                stores += '<td>%s</td>' % resource_name

                last_asctime = time.asctime(last_timetuple)
                last_epoch = time.mktime(last_timetuple)
                stores += '<td><div class="sortkey">%s</div>%s %s<br />' %  \
                          (last_epoch, last_status, last_asctime)
                stores += '(%sd %sh %sm %ss ago)</td>' % (days, hours, minutes,
                                                          seconds)
                stores += '<td>' + vgrid_name + '</td>'
                stores += '<td>%d</td>' % total_disk
                stores += '<td>%d</td>' % used_disk
                stores += '<td>%d</td>' % avail_disk
                stores += '<td>%d</td>' % used_percent

                stores += '<td class=status_%s>' % resource_status
                stores += resource_status + '</td>'

                stores += '</tr>\n'
                total_number_of_store_resources += 1
                total_number_of_store_gigs += total_disk

    html += """</table>
</div>
</td></tr>

</table>
<h2>Resource Job Requests</h2>
Listing the last request from each resource<br />
<br />
<table class="monitor columnsort">
<thead class="title">
<tr>
  <th class="icon"><!-- Status icon --></th>
  <th>Resource ID, unit</th>
  <th>Last seen</th>
  <th>VGrid</th>
  <th>Runtime envs</th>
  <th>CPU time (s)</th>
  <th>Node count</th>
  <th>CPU count</th>
  <th>Disk (GB)</th>
  <th>Memory (MB)</th>
  <th>Arch</th>
  <th>Status</th>
  <th>Job (s)</th>
  <th>Remaining</th>
</tr>
</thead>
<tbody>
"""
    html += exes
    html += '</tbody>\n</table>\n'

    html += """
<h2>Resource Storage</h2>
Listing the last check for each resource<br />
<br />
<table class="monitor columnsort">
<thead class="title">
<tr>
  <th class="icon"><!-- Status icon --></th>
  <th>Resource ID, unit</th>
  <th>Last Status</th>
  <th>VGrid</th>
  <th>Total Disk (GB)</th>
  <th>Used Disk (GB)</th>
  <th>Available Disk (GB)</th>
  <th>Disk Use %</th>
  <th>Status</th>
</tr>
</thead>
<tbody>
"""
    html += stores
    html += '</tbody>\n</table>\n'

    html += '''
<h2>VGrid Totals</h2>
A total of <b>'''\
         + str(total_number_of_exe_resources) + '</b> exe resources ('\
        + str(total_number_of_exe_cpus) + " cpu's) and <b>"\
        + str(total_number_of_store_resources) + '</b> store resources ('\
        + str(int(total_number_of_store_gigs)) + " GB) joined this VGrid ("\
        + str(up_count) + ' up, ' + str(down_count) + ' down?, '\
        + str(slack_count) + ' slack)<br />'
    html += str(job_assigned) + ' exe resources (' + str(job_assigned_cpus)\
        + """ cpu's) appear to be executing a job<br />
<br />
"""
    html += \
        '<!-- begin raw footer: this line is used by showvgridmonitor -->'
    html += get_xgi_html_footer(configuration, '')

    try:
        file_handle = open(html_file, 'w')
        file_handle.write(html)
        file_handle.close()
    except Exception as exc:
        print('Could not write monitor page %s: %s' % (html_file, exc))


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("monitor", configuration.user_monitor_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    if not configuration.site_enable_jobs:
        err_msg = "Job support is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print("""
Running grid monitor generator.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")

    # Make sure that the default VGrid home used by monitor exists

    default_vgrid_dir = os.path.join(configuration.vgrid_home, default_vgrid)
    if not os.path.isdir(default_vgrid_dir):
        try:
            os.makedirs(default_vgrid_dir)
        except OSError as ose:
            logger.error('Failed to create default VGrid home: %s' % ose)

    keep_running = True
    while keep_running:
        try:
            vgrids_list = get_vgrid_map_vgrids(configuration, caching=True)

            # create global statistics ("")
            # vgrids_list.append("")

            print('Updating cache.')
            grid_stat = GridStat(configuration, logger)
            grid_stat.update()
            for vgrid_name in vgrids_list:
                print('creating monitor for vgrid: %s' % vgrid_name)
                create_monitor(vgrid_name)

            print('sleeping for %s seconds' % configuration.sleep_secs)
            time.sleep(float(configuration.sleep_secs))
        except KeyboardInterrupt:
            keep_running = False
        except Exception as exc:
            print('Caught unexpected exception: %s' % exc)
            time.sleep(10)

    print('Monitor daemon shutting down')
    sys.exit(0)
