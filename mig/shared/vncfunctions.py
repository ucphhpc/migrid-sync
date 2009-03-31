#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vncfunctions - [insert a few words of module description on this line]
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
import socket
import popen2
import tempfile

from shared.html import get_cgi_html_header, get_cgi_html_footer, \
    html_add
from shared.cgishared import init_cgi_script_with_cert
from shared.livedisplaysfunctions import get_users_display_dict, \
    get_dict_from_display_number, set_user_display_active, \
    set_user_display_inactive, set_user_display_inactive


def create_vnc_password():

    # Create vnc password

    password = ''
    try:
        import random
        import base64
        rand = random.Random()
        for i in range(8):
            tal = rand.randint(32, 255)
            password += chr(tal)
        password = base64.encodestring(password)[:8]
        (filehandle, passwdfile) = tempfile.mkstemp(dir='/tmp',
                text=False)
        os.close(filehandle)
        (sdout, sdin) = popen2.popen2('vncpasswd %s' % passwdfile)
        sdin.write(password + '\n')
        sdin.flush()
        sdin.write(password + '\n')
        sdin.flush()
        return (True, (password, passwdfile))
    except Exception, e:
        return (False, 'Error creating vnc password (%s)' % e)


def main(
    logger,
    configuration,
    cert_name_no_spaces,
    o,
    ):

    # ## MAIN ###
    # (logger, configuration, cert_name_no_spaces, o) = init_cgi_script_with_cert()
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep
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

    o.client_html(get_cgi_html_header(title='MiG Interactive Session',
                  scripts=script, header='Session for: %s'
                   % cert_name_no_spaces,
                  bodyfunctions='onUnLoad="endVNC()"'))

    error = ''

    # Find available port/display.
    # TODO: Seperate port and display no... Check /tmp/.X11-lock/ for available dispays
    # ....and make bind check for available ports! Display might be in use without
    # ....using a port and vice-versa!
    # TODO: baseVNCport and VNC_port_count should be read from configuration

    passwdfile = ''
    password = ''

    valid_display_found = False
    (stat, msg) = get_users_display_dict(cert_name_no_spaces,
            configuration, logger)
    if stat == False:
        o.out('Error getting dictionary of live displays %s' % msg)
        o.reply_and_exit(o.ERROR)
    if stat == -1:
        logger.info('did not find a display number for %s'
                     % cert_name_no_spaces)
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
            except Exception, e:
                error = e
            S.close()
            S = None

            if free_display_found:

        # verify display is free or steal it? verify for now

                (disp_numb_stat, disp_numb_ret) = \
                    get_dict_from_display_number(i, configuration,
                        logger)
                if disp_numb_stat == False:
                    o.out('Error getting dictionary for display %s'
                           % disp_numb_ret)
                    o.reply_and_exit(o.ERROR)
                if disp_numb_ret != -1:

            # display is registered as being in use, but the display seems to be available.

                    continue
                else:

            # display is available

                    (passstat, passmsg) = create_vnc_password()
                    if passstat == False:
                        o.client_html('<p>%s</p>' % passmsg)
                        logger.error('%s' % passmsg)
                        o.reply_and_exit(o.ERROR)
                    (password, passwdfile) = passmsg

                    valid_display_found = True
                    (stat, msg) = set_user_display_active(
                        cert_name_no_spaces,
                        display_number,
                        vnc_port,
                        password,
                        configuration,
                        logger,
                        )
                    if not stat:
                        o.out('could not set user display active: %s'
                               % msg)
                        o.reply_and_exit(o.ERROR)
                    break
    else:
        display_number = stat
        vnc_port = msg['vnc_port']
        password = msg['password']
        valid_display_found = True

        logger.info('user %s has display %s' % (cert_name_no_spaces,
                    display_number))

    if not valid_display_found:
        o.client_html('Display unavailable. Click back and try again later.<br>'
                      )
        o.client_html(get_cgi_html_footer("<p><a href='../'>Back to main page</a>"
                      ))
        logger.error('No available ports for vnc: %s' % error)
        o.reply_and_exit(o.ERROR)
    display = ':' + repr(display_number)
    logger.debug('VNC: Found port = %d' % vnc_port)

    # Read all incomming variables:

    fs = cgi.FieldStorage()
    width = fs.getfirst('width', '800')
    height = fs.getfirst('height', '600')
    depth = fs.getfirst('depth', '16')
    desktop = fs.getfirst('desktopname', 'X11')

    test = width.isdigit() and height.isdigit() and depth.isdigit()
    if not test:
        o.client_html('Incorrect paramters! Please press back and enter correct values.'
                      )
        logger.error('Parameters incorrectly specified by user.')
        o.reply_and_exit(o.ERROR)

    # Run launch and record the process ID.

    vnclogfile = base_dir + '.vncserver.log'
    launch = \
        'Xvnc -rfbport %i -SecurityTypes VncAuth -AlwaysShared -DisconnectClients=0 -BlacklistTimeout=0'\
         % vnc_port

    # launch = "Xvnc4 -rfbport %i -SecurityTypes VncAuth -NeverShared -DisconnectClients=0" % (vnc_port)

    launch += ' -geometry %sx%s -depth %s' % (width, height, depth)
    launch += ' -PasswordFile %s' % passwdfile
    launch += ' -desktop "%s" %s' % (desktop, display)

    launch += ' & >>%s 2>>%s.stderr' % (vnclogfile, vnclogfile)

    pidfile = '%s.vnc_port%s.Xvnc4.pid' % (base_dir, vnc_port)
    launch += ' & echo $! > %s' % pidfile

    logger.info('VNC Launch: %s' % launch)
    result = os.system(launch) >> 8

    if result != 0:
        o.client_html('VNC-server could not start. Read ".vncserver.log" log file in your home dir for specifications.'
                      )
        logger.error('VNC-server could not start! Result = %d' % result)
        (stat, ret) = set_user_display_inactive(cert_name_no_spaces,
                display_number, configuration, logger)
        if not stat:
            logger.error('%s' % ret)

        o.reply_and_exit(o.ERROR)

    if not os.path.exists(pidfile):
        o.client_html('PID file of VNC server not found!')
        (stat, ret) = set_user_display_inactive(cert_name_no_spaces,
                display_number, configuration, logger)
        if not stat:
            logger.error('%s' % ret)
            o.reply_and_exit(o.ERROR)

    o.client_html('Opening embedded vnc applet here.<br><b>This will only work if your browser includes a java plugin!</b>'
                  )
    o.client_html('<APPLET CODE="vncviewer" ARCHIVE="vncviewer.jar" CODEBASE="%s/vgrid/"'
                   % configuration.migserver_http_url)
    o.client_html('WIDTH=' + repr(int(width) + 50) + ' HEIGHT='
                   + repr(int(height) + 50) + '>')
    o.client_html('<param name="PORT" value=' + repr(vnc_port) + '>')
    o.client_html('<param name="PASSWORD" value="%s" >' % password)
    o.client_html('</APPLET>')
    o.client_html('<br>')

    status = o.OK

    # TODO: remove temp passwdfile. This should be done when the display has been left.
    # It can't be removed now, since Xvnc reads the password when clients connects again.

    o.client_html(get_cgi_html_footer("VNC port: %s<BR>Display number: %s<p><a href='../'>Back to main page</a>"
                   % (vnc_port, display_number)))
    o.reply_and_exit(status)


