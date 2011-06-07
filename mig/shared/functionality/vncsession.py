#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vncsession - Start a new VNC session
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

"""Start a new vnc session"""

import os
import socket

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.livedisplaysfunctions import get_users_display_dict, \
    get_dict_from_display_number, set_user_display_active, \
    set_user_display_inactive
from shared.vncfunctions import create_vnc_password


def signature():
    """Signature of the main function"""

    defaults = {
        'width': ['800'],
        'height': ['600'],
        'depth': ['16'],
        'desktopname': ['X11'],
        }
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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

    width = accepted['width'][-1]
    height = accepted['height'][-1]
    depth = accepted['depth'][-1]
    desktopname = accepted['desktopname'][-1]

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    status = returnvalues.OK

    script = \
        """
    <script type="text/javascript">
      function endVNC () {
      if (!window.XMLHttpRequest)
        var httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
      else
        var httpRequest = new XMLHttpRequest();
      try {
        httpRequest.open('POST', 'vncstop.py', '');
        httpRequest.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        httpRequest.send('');
	}
	catch (e) 
	{
	  alert(e);
	  return e;
        }
      }
      </script>
    """

    # ## TODO: Include something like the following for support for interactive jobrequests!
    # ===============================================================================
    #    function submitjob(request) {
    #    if (!window.XMLHttpRequest)
    #     var httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
    #    else
    #      var httpRequest = new XMLHttpRequest();
    #      try {
    #        httpRequest.open('POST', 'textarea.py', '');
    #        httpRequest.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    #        httpRequest.send(request);
    #      }
    #      catch (e) {
    #        alert(e);
    #        return e;
    #      }
    #      if (httpRequest.status == 200)
    #        return httpRequest.responseText;
    #      else
    #        return httpRequest.status + " " + httpRequest.statusText;
    #    }
    # ##############################################################333
    # ....FOLLOWING IS A SAMPLE TAKEN FROM: dsl.gymer.dk (thx. for sharing gymer)
    # ....function submitkey() {
    # ....        var form = document.getElementById("submitkeyform");
    # ....        var res = submitjob("action=submitkey"+"&key="+form.key.value );
    # ....        document.getElementById("subcontent").innerHTML = res;
    # ....}
    # ===============================================================================

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s Interactive Session' % configuration.short_title
    title_entry['javascript'] = script
    title_entry['bodyfunctions'] = 'onUnLoad="endVNC()"'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Session for: %s' % client_id})

    error = ''

    # Find available port/display.
    # TODO: Seperate port and display no... Check /tmp/.X11-lock/ for available dispays
    # ....and make bind check for available ports! Display might be in use without
    # ....using a port and vice-versa!
    # TODO: baseVNCport and VNC_port_count should be read from configuration

    passwdfile = ''
    password = ''

    valid_display_found = False
    (stat, msg) = get_users_display_dict(client_id, configuration,
            logger)
    if stat == False:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting dictionary of live displays %s'
                               % msg})
        status = returnvalues.CLIENT_ERROR
        return (output_objects, status)
    if stat == -1:
        logger.info('did not find a display number for %s' % client_id)
        baseVNCport = 8087
        VNC_port_count = 15
        display_number = 1
        start_display = 5

        for i in range(start_display, VNC_port_count + start_display):
            free_display_found = False
            try:
                S = socket.socket()
                S.bind(('', baseVNCport + i))
                display_number = i
                vnc_port = baseVNCport + display_number
                free_display_found = True
            except Exception, exc:
                error = exc
            S.close()
            S = None

            if free_display_found:

                # verify display is free or steal it? verify for now

                (disp_numb_stat, disp_numb_ret) = \
                    get_dict_from_display_number(i, configuration,
                        logger)
                if disp_numb_stat == False:
                    output_objects.append({'object_type': 'error_text',
                            'text'
                            : 'Error getting dictionary for display %s'
                             % disp_numb_ret})
                    status = returnvalues.CLIENT_ERROR
                    return (output_objects, status)
                if disp_numb_ret != -1:

                    # display is registered as being in use, but the display seems to be available.

                    continue
                else:

                    # display is available

                    (passstat, passmsg) = create_vnc_password()
                    if passstat == False:
                        output_objects.append({'object_type'
                                : 'error_text', 'text': passmsg})
                        status = returnvalues.CLIENT_ERROR
                        logger.error('%s' % passmsg)
                        return (output_objects, status)

                    (password, passwdfile) = passmsg

                    valid_display_found = True
                    (stat, msg) = set_user_display_active(
                        client_id,
                        display_number,
                        vnc_port,
                        password,
                        configuration,
                        logger,
                        )
                    if not stat:
                        output_objects.append({'object_type'
                                : 'error_text', 'text'
                                : 'could not set user display active: %s'
                                 % msg})
                        status = returnvalues.CLIENT_ERROR
                        return (output_objects, status)
                    break
    else:
        display_number = stat
        vnc_port = msg['vnc_port']
        password = msg['password']
        valid_display_found = True

        logger.info('user %s has display %s' % (client_id,
                    display_number))

    if not valid_display_found:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Display unavailable. Click back and try again later.'
                              })
        status = returnvalues.CLIENT_ERROR
        logger.error('No available ports for vnc: %s' % error)
        return (output_objects, status)
    display = ':' + repr(display_number)
    logger.debug('VNC: Found port = %d' % vnc_port)

    # Run launch and record the process ID.

    vnclogfile = base_dir + '.vncserver.log'
    launch = \
        'Xvnc -rfbport %i -SecurityTypes VncAuth -AlwaysShared -DisconnectClients=0 -BlacklistTimeout=0'\
         % vnc_port

    # launch = "Xvnc4 -rfbport %i -SecurityTypes VncAuth -NeverShared -DisconnectClients=0" % (vnc_port)

    launch += ' -geometry %sx%s -depth %s' % (width, height, depth)
    launch += ' -PasswordFile %s' % passwdfile
    launch += ' -desktop "%s" %s' % (desktopname, display)

    launch += ' & >>%s 2>>%s.stderr' % (vnclogfile, vnclogfile)

    pidfile = '%s.vnc_port%s.Xvnc4.pid' % (base_dir, vnc_port)
    launch += ' & echo $! > %s' % pidfile

    logger.info('VNC Launch: %s' % launch)
    result = os.system(launch) >> 8

    if result != 0:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'VNC-server could not start. Read ".vncserver.log" log file in your home dir for specifications.'
                              })
        status = returnvalues.CLIENT_ERROR
        logger.error('VNC-server could not start! Result = %d' % result)
        (stat, ret) = set_user_display_inactive(client_id,
                display_number, configuration, logger)
        if not stat:
            logger.error('%s' % ret)

        return (output_objects, status)

    if not os.path.exists(pidfile):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'PID file of VNC server not found!'})
        status = returnvalues.CLIENT_ERROR
        (stat, ret) = set_user_display_inactive(client_id,
                display_number, configuration, logger)
        if not stat:
            logger.error('%s' % ret)
            return (output_objects, status)

        html = \
            '''Opening embedded vnc applet here:<br />
<b>This will only work if your browser includes a java plugin!</b><br />
<applet code="vncviewer" archive="vncviewer.jar" codebase="%s/vnc/" width="%s" height="%s">
<param name="port" value="%s">
<param name="password" value="%s">
</applet>
<br />
VNC port: %s<br />
Display number: %s<p>
'''\
             % (
            configuration.migserver_http_url,
            repr(int(width) + 50),
            repr(int(height) + 50),
            repr(vnc_port),
            password,
            vnc_port,
            display_number,
            )
    output_objects.append({'object_type': 'html_form', 'text': html})

    # TODO: remove temp passwdfile. This should be done when the display has been left.
    # It can't be removed now, since Xvnc reads the password when clients connects again.

    return (output_objects, status)


