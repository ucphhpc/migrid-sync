#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox_admin - sandbox generator and monitor for individual users
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

"""This script allows users to administrate their sandboxes"""

import pickle
import os

from shared.gridstat import GridStat

from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    defaults = {'username': REJECT_UNSET, 'password': REJECT_UNSET,
                'newuser': ['off'], 'vgrid': 'Generic'}
    return ['html_form', defaults]


def print_hd_selection():
    """Returns html section where a user chooses disc space"""

    html = \
        """<TR><TD align='' colspan=''>How much disc space can 
    you allow the sandbox to use?</TD>
    <TD><select name='hd_size'>
    <option value='100'>100 MB</option>
    <option value='1000'>1 GB</option>
    <option value='2000'>2 GB</option>
    </select>
    <input type=hidden name='image_format' value='qcow'>
    </TD></TR>"""
    return html


def print_net_selection():
    """Returns html section where a user chooses max download and upload speed"""

    html = \
        """<TR><TD align='' colspan=''>What is the max download/upload bandwidth in kB/s
    you will allow the sandbox to use?</TD>
    <TD><select name='net_bw'>
    <option value='0'>No limit</option>
    <option value='2048'>2048/1024</option>
    <option value='1024'>1024/512</option>
    <option value='512'>512/256</option>
    <option value='256' selected>256/128</option>
    <option value='128'>128/64</option>
    </select>
    </TD></TR>"""
    return html


def print_mem_selection():
    """Prints html section where a user amount of physical memory"""

    html = \
        """<TR><TD align='' colspan=''>How much physical memory
          does your PC have?</TD>
    <TD><select name='memory'>
    <option value='256'>256 MB</option>
    <option value='512' selected>512 MB</option>
    <option value='1024'>1 GB</option>
    <option value='2048'>2 GB</option>
    <option value='4096'>4 GB</option>
    </select></TD></TR>"""
    return html


def print_os_selection():
    """Prints html section where a user chooses which OS he uses"""

    html = \
        """<TR><TD align='' colspan=''>Which operating system 
          are you using?</TD>
    <TD><select name='operating_system'>
    <option value='win'>Windows XP/Vista</option>
    <option value='linux'>Linux</option>
    </select></TD></TR>"""
    return html


def print_windows_solution_selection():
    """Prints html section where a user chooses whether he wants
    the screensaver or the windows service model"""

    html = \
        """<TR><TD align='' colspan=''>If Windows, do you want 
          the screensaver <break> or the service model? If unsure, choose screensaver</TD>
    <TD><select name='win_solution'>
    <option value='screensaver'>Screensaver</option>
    <option value='service'>Windows Service</option>
    </select></TD></TR>"""
    return html


def count_jobs(resource_name):
    """Counts number of jobs executed by given resource"""

    # gs.update()

    value = gs.get_value(gs.RESOURCE, resource_name, 'FINISHED')
    return value


def show_info(user, vgrid):
    """Shows info for given user and passes any vgrid settings on unchanged"""

    # Resource Monitor Section

    html = \
        """<TABLE border='1' align='center'>
    <TR><TD align='center' colspan='2'>
    <H1>Resource Monitor</H1>
    </TD></TR>
    <TR><TD align='center' colspan='2'>
    <H3>List of resources and number of jobs successfully 
          executed by the resource</H3>
    </TD></TR>"""

    for resource in userdb[user][RESOURCES]:

        # now find number of jobs successfully executed by resource

        jobs = count_jobs(resource)
        html += \
            """<TR><TD align='center'>%s</TD><TD align='center'> %s jobs</TD></TR>"""\
             % (resource, jobs)
    if len(userdb[user][RESOURCES]) == 0:
        html += \
            """<TR><TD align='center'>You haven't downloaded any
              sandbox resources yet</TD></TR>"""
    html += """
    </TABLE>
    <br>"""

    # Download sandbox section

    html += \
        """<form action='sandbox_createimage.py?MiG-SSS.zip' 
          method='POST'>
    <TABLE border='2' align=center>
    <TR><TD align='center' colspan='2'>
    <H1>Download new sandbox</H1>
    </TD></TR>"""

    html += print_hd_selection()
    html += print_mem_selection()
    html += print_net_selection()
    html += print_os_selection()
    html += print_windows_solution_selection()

    html += \
        """<TR><TD>
        <input type='hidden' name='username' value='%s'>
        <input type='hidden' name='vgrid' value='%s'>
</TD></TR>""" % (user, vgrid)
    html += \
        """<TR><TD>Press 'Submit' to download - please note that it 
          may<br> take up to 2 minutes to generate your sandbox</TD>
          <TD align='center'><input type='SUBMIT' value='Submit'>
          </TD></TR>

    </TABLE>
    <br>
    <TABLE align='center'><TR><TD align='center'>If you have 
          any problems, please contact the MiG administrators (%s)
          </TD></TR></TABLE> 
    </form>"""\
         % admin_email.replace('<', '&lt;').replace('>', '&gt;')
    return html


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    username = accepted['username'][-1].strip()
    password = accepted['password'][-1].strip()
    newuser = accepted['newuser'][-1].strip()
    vgrid = accepted['vgrid'][-1].strip()

    PW = 0
    global RESOURCES
    RESOURCES = 1
    sandboxdb_file = configuration.sandbox_home + 'sandbox_users.pkl'

    global userdb

    # Load the user file

    try:
        fd = open(sandboxdb_file, 'rb')
        userdb = pickle.load(fd)
        fd.close()
    except IOError:
        # First time - create empty dict
        userdb = {}
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not read sandbox database! %s'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    global admin_email
    admin_email = configuration.admin_email
    global gs
    gs = GridStat(configuration, logger)

    # If it's a new user, check that the username is free

    if newuser == 'on':
        if userdb.has_key(username):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Username is already taken - please go back and choose another one...'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif len(username) < 3:

            # print "<a href='sandbox_login.py'>Back</a>"

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Please choose a username with 3 or more characters.'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        else:

            # print "<a href='sandbox_login.py'>Back</a>"
            # Create new user with empty resource list

            try:
                fd = open(sandboxdb_file, 'wb')
                newuser = {username: (password, [])}
                userdb.update(newuser)
                pickle.dump(userdb, fd)
                fd.close()
            except Exception, exc:
                output_objects.append({'object_type': 'error_text',
                        'text'
                        : 'Could not save you in the user database! %s'
                         % exc})
                return (output_objects, returnvalues.SYSTEM_ERROR)
            output_objects.append({'object_type': 'html_form', 'text'
                                  : show_info(username, vgrid)})
    else:

    # Otherwise, check that username and password are correct

        if not userdb.has_key(username):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Wrong username - please go back and try again...'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif userdb[username][PW] != password:

            # print "<a href='sandbox_login.py'>Back</a>"....

            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Wrong password - please go back and try again...'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)
        else:

            # print "<a href='sandbox_login.py'>Back</a>"....

            output_objects.append({'object_type': 'html_form', 'text'
                                  : show_info(username, vgrid)})

    return (output_objects, returnvalues.OK)


