#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_monitor - [insert a few words of module description on this line]
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


"""Creating the MiG monitor page"""

# Henrik Hoey Karlsen

import os
import time
import datetime

from shared.configuration import Configuration
from shared.gridstat import GridStat
from shared.fileio import unpickle
from shared.vgrid import vgrid_list_vgrids


configuration = Configuration("MiGserver.conf")
logger = configuration.logger
# Make sure that the Generic VGrid home used by monitor exists
generic_dir = configuration.vgrid_home + os.sep + "Generic"
if not os.path.isdir(generic_dir):
    try:
        os.makedirs(generic_dir)
    except OSError, ose:
        logger.error("Failed to create Generic VGrid home: %s" % ose)


def create_monitor(vgrid_name):
    """Write monitor HTML file for vgrid_name"""
    html_file = configuration.vgrid_home + "/" + vgrid_name +  "/monitor.html"

    print "starting collecting statistics for VGrid %s" % vgrid_name
    sleep_secs = configuration.sleep_secs
    slackperiod = configuration.slackperiod
    now = time.asctime(time.localtime())

    html_vars = {"sleep_secs":sleep_secs, "vgrid_name":vgrid_name,
                 "logo_url":"/images/logo.jpg", "now":now}

    html = '''<html>
<head>
<meta http-equiv="refresh" content="%(sleep_secs)s">
<title>MiG Monitor, VGrid %(vgrid_name)s</title>
</head>
<body bgcolor="#CCCCCC"><a href="/"><img src="%(logo_url)s" border=0></a><br>
<!-- end of raw header: this line is used by showvgridmonitor -->
This is statistics/monitor details for VGrid %(vgrid_name)s<br>
This page was generated %(now)s<br>
Automatic refresh every %(sleep_secs)s secs.<br>
<br>''' % html_vars

    # loop and get totals
    runtimeenv_dict = {"":0}

    parse_count = 0
    queued_count = 0
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
    disk_requested = 0
    disk_done = 0
    memory_requested = 0
    memory_done = 0
    runtimeenv_dict = {"":0}

    number_of_jobs = 0
    up_count = 0
    down_count = 0
    slack_count = 0
    
    job_assigned = 0
    job_assigned_cpus = 0
    
    gstat = GridStat(configuration, logger)
    
    runtimeenv_dict = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   "RUNTIMEENVIRONMENT", {})
                
    parse_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "PARSE")
    queued_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "QUEUED")
    executing_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                   "EXECUTING")
    failed_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "FAILED")
    retry_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "RETRY")
    canceled_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "CANCELED")
    expired_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "EXPIRED")
    finished_count = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "FINISHED")
    
    nodecount_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                       "NODECOUNT_REQ")
    nodecount_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                  "NODECOUNT_DONE")
    cputime_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                     "CPUTIME_REQ")
    cputime_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                "CPUTIME_DONE")
    disk_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                  "DISK_REQ")
    disk_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(), "DISK_DONE")
    memory_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                    "MEMORY_REQ")
    memory_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                               "MEMORY_DONE")
    cpucount_requested = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                      "CPUCOUNT_REQ")
    cpucount_done = gstat.get_value(gstat.VGRID, vgrid_name.upper(),
                                 "CPUCOUNT_DONE")
    
    number_of_jobs = parse_count
    number_of_jobs += queued_count
    number_of_jobs += expired_count
    number_of_jobs += canceled_count
    number_of_jobs += failed_count
    number_of_jobs += executing_count
    number_of_jobs += finished_count
    number_of_jobs += retry_count

    html_vars = {"parse_count":parse_count, "queued_count":queued_count,
                 "executing_count":executing_count, "failed_count":failed_count,
                 "retry_count":retry_count, "canceled_count":canceled_count,
                 "expired_count":expired_count, "finished_count":finished_count,
                 "number_of_jobs":number_of_jobs,
                 "cpucount_requested":cpucount_requested,
                 "cpucount_done":cpucount_done,
                 "nodecount_requested":nodecount_requested,
                 "nodecount_done":nodecount_done,
                 "cputime_requested":cputime_requested,
                 "cputime_done":cputime_done, "disk_requested":disk_requested,
                 "disk_done":disk_done, "memory_requested":memory_requested,
                 "memory_done":memory_done}
    
    html += """<table border=0><tr><td valign=top>
<table border=1><tr><td><b>State</b></td><td><b>Number of jobs</b></td></tr>
<tr><td>Parse</td><td>%(parse_count)s</td></tr>
<tr><td>Queued</td><td>%(queued_count)s</td></tr>
<tr><td>Executing</td><td>%(executing_count)s</td></tr>
<tr><td>Failed</td><td>%(failed_count)s</td></tr>
<tr><td>Retry</td><td>%(retry_count)s</td></tr>
<tr><td>Canceled</td><td>%(canceled_count)s</td></tr>
<tr><td>Expired</td><td>%(expired_count)s</td></tr>
<tr><td>Finished</td><td>%(finished_count)s</td></tr>
<tr><td>Total</td><td>%(number_of_jobs)s</td></tr>
</table>
</td><td valign=top>
<table border=1>
<tr><td><b>Item</b></td><td><b>Requested</b></td><td><b>Done</b></td></tr>
<tr><td>Cpucount</td><td>%(cpucount_requested)s</td><td>%(cpucount_done)s</td></tr>
<tr><td>Nodecount</td><td>%(nodecount_requested)s</td><td>%(nodecount_done)s</td></tr>
<tr><td>Cputime</td><td>%(cputime_requested)s</td><td>%(cputime_done)s</td></tr>
<tr><td>GB Disk</td><td>%(disk_requested)s</td><td>%(disk_done)s</td></tr>
<tr><td>MB Memory</td><td>%(memory_requested)s</td><td>%(memory_done)s</td></tr>
</table><br>
</td><td valign=top>
<table border=1><tr><td><b>Runtimeenvironment</b></td><td></td></tr>""" % html_vars
        
    if len(runtimeenv_dict.keys()) < 1:
        # No runtimeenv requests
        html += "<tr><td></td><td>-</td></tr>"
    else:
        for entry in runtimeenv_dict.keys():
            if not entry == "":
                html += "<tr><td>" + entry + "</td><td>" + \
                        str(runtimeenv_dict[entry]) + "</td></tr>"
    html += """</table>
</td></tr>
</table><br>
<br>
<hr><br>
<b>Resource job request</b><br>
Listing the last request from each resource<br>
<br>
<table border=1>
<tr><td><b>Resource and last seen</b></td><td><b>Time ago</b></td><td><b>VGrid</b></td><td><b>CPU time</b></td>
<td><b>Node count</b></td><td><b>CPU count</b></td><td><b>GB Disk</b></td>
<td><b>MB Memory</b></td><td><b>Arch</b></td><td><b>Status</b></td>
<td><b>Time</b></td><td><b>Time remaining</b></td></tr>"""

    total_number_of_resources = 0
    total_number_of_cpus = 0
    
    vgrid_name_list = vgrid_name.split("/")
    current_dir = ""

    for vgrid_name_part in vgrid_name_list:
        current_dir += "/" + vgrid_name_part
        print "dir: " + configuration.vgrid_home + current_dir

        for filename in os.listdir(configuration.vgrid_home + current_dir):
            print filename
            if filename.startswith("monitor_last_request_"):
                # read file
                mon_file_name = configuration.vgrid_home + current_dir + "/" + filename
                print "found " + mon_file_name 
                last_request_dict = unpickle(mon_file_name, logger)
                if not last_request_dict:
                    print "could not open and unpickle: " + mon_file_name
                    continue
                
                difference = datetime.datetime.now() - last_request_dict["CREATED_TIME"]
                days = str(difference.days)
                hours = str(difference.seconds / 3600)
                minutes = str((difference.seconds % 3600) / 60)
                seconds = str((difference.seconds % 60) % 60)

                if last_request_dict.has_key("CPUTIME"):
                    cputime = last_request_dict["CPUTIME"]
                elif last_request_dict.has_key("cputime"):
                    cputime = last_request_dict["cputime"]
                else:
                    print "ERROR: last request does not contain cputime field!: %s" % last_request_dict
                    continue
                    
                try:
                    cpusec = int(cputime)
                except ValueError:
                    try:
                        cpusec = int(float(cputime))
                    except ValueError, verr:
                        print "ERROR: failed to parse cputime %s: %s" % \
                              (cputime, verr)

                # Include execution delay guesstimate for strict fill
                # LRMS resources
                try:
                    delay = int(last_request_dict["EXECUTION_DELAY"])
                except KeyError:
                    delay = 0
                except ValueError:
                    delay = 0

                time_remaining = last_request_dict["CREATED_TIME"] + \
                                 datetime.timedelta(seconds=cpusec) + \
                                 datetime.timedelta(seconds=delay) - \
                                 datetime.datetime.now()
                days_rem = str(time_remaining.days)
                hours_rem = str(time_remaining.seconds / 3600)
                minutes_rem = str((time_remaining.seconds % 3600) / 60)
                seconds_rem = str((time_remaining.seconds % 60) % 60)
        
                if time_remaining.days < -7:
                    try:
                        print "removing: %s as we havent seen him for %s days." % \
                              (mon_file_name, abs(time_remaining).days)
                        os.remove(mon_file_name)
                    except Exception, err:
                        print "could not remove: '%s' Error: %s" % \
                              (mon_file_name, str(err))
                    pass
                else:
                    unique_res_name_and_exe_list = filename.split(
                        "monitor_last_request_", 1)
                    html += "<tr><td> " + unique_res_name_and_exe_list[1] + "<br>" + time.asctime((last_request_dict["CREATED_TIME"]).timetuple()) + "</td>"
                    html += "<td>" + days + " days, " + hours + " hours, " + minutes + " min, " + seconds + "secs</td>"
                    html += "<td>" + vgrid_name + "</td>"
                    html += "<td>" + str(last_request_dict["RESOURCE_CONFIG"]["CPUTIME"])+ "</td><td>" + str(last_request_dict["RESOURCE_CONFIG"]["NODECOUNT"]) + "</td><td>" + str(last_request_dict["RESOURCE_CONFIG"]["CPUCOUNT"]) + "</td>"
                    html += "<td>" + str(last_request_dict["RESOURCE_CONFIG"]["DISK"]) + "</td><td>" +str(last_request_dict["RESOURCE_CONFIG"]["MEMORY"])+ "</td><td>" +str(last_request_dict["RESOURCE_CONFIG"]["ARCHITECTURE"]) +"</td>"
                    html += "<td>" + last_request_dict["STATUS"] + "</td><td>" + str(last_request_dict["CPUTIME"]) + "</td>"
                   
                    if (cpusec == 0):
                        html += "<td>-"
                    elif (time_remaining.days < 0):
                        # time_remaining.days < 0 means that we have passed the specified time
                        time_rem_abs = abs(time_remaining)
                        if ((time_rem_abs.days == 0) and (int(time_rem_abs.seconds) < int(slackperiod))):
                            html += "<td>Within slack period (" + str(int(time_rem_abs.seconds)) + "<" + str(int(slackperiod)) + " secs).</td>"
                            slack_count = slack_count + 1
                        else:
                            html += "<td>down?</td>"
                            down_count = down_count + 1
                            # count number of res with jobs assigned
                    else:
                        html += "<td>" + days_rem + " days, " + hours_rem + " hours, " + minutes_rem + " min, " + seconds_rem + "secs</td>"
                        up_count = up_count + 1
                        
                    html += "</tr>"
                    if last_request_dict["STATUS"] == "Job assigned":
                        job_assigned = job_assigned + 1
                        job_assigned_cpus = job_assigned_cpus + (int(last_request_dict["RESOURCE_CONFIG"]["NODECOUNT"]) * int(last_request_dict["RESOURCE_CONFIG"]["CPUCOUNT"]))
                    
                    total_number_of_resources = total_number_of_resources + 1
                    total_number_of_cpus = total_number_of_cpus + (int(last_request_dict["RESOURCE_CONFIG"]["NODECOUNT"]) * int(last_request_dict["RESOURCE_CONFIG"]["CPUCOUNT"]))
 
    html += "</table>" 

    html += "<br><hr><br><b>VGrid Totals</b><br><br>A total of <b>" + str(total_number_of_resources) + "</b> resources (" + str(total_number_of_cpus) + " cpu's) joined this VGrid (" + str(up_count) + " up, " + str(down_count) + " down?, " + str(slack_count) + " slack)<br>"
    html += str(job_assigned) + " resources (" + str(job_assigned_cpus) + " cpu's) seems to be executing a job<br><br>" 
    html += "</body></html>"

    file_handle = open(html_file, "w")
    file_handle.write(html)
    file_handle.close()
    
while True:
    (status, vgrids_list) = vgrid_list_vgrids(configuration)
    # create global statistics ("")
    # vgrids_list.append("")
    print "Updating cache."
    grid_stat = GridStat(configuration, logger)
    grid_stat.update()
    for vgrid_name in vgrids_list:
        print "creating monitor for vgrid: %s" % vgrid_name
        create_monitor(vgrid_name)
    
    print "sleeping for " + str(configuration.sleep_secs) + "seconds"
    time.sleep(float(configuration.sleep_secs))
