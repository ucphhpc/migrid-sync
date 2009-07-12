#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssslogin - SSS welcome and login backend
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

"""This script is the welcome site for sandbox users"""

import sys

from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues

default_language = 'english'


def signature():
    """Signature of the main function"""

    defaults = {'language': [default_language]}
    return ['html_form', defaults]


html = {}
html['maintenance'] = \
    """
Sorry we are currently down for maintenance, we'll be back shortly
"""

html['english'] = \
    """
<form action='sssadmin.py' method='POST'>

<table class='sandboxlogintext'>
<tr><td><a href='ssslogin.py?language=danish'>P&aring; dansk</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Welcome to the MiG-SSS download site. By downloading and installing this software, your computer will be participating in solving scientific problems whenever the screen saver is on. All you have to do is log in below, download the sandbox, and follow the instructions during the install procedure.<td><tr>

<tr><td><h3>Why Login?</h3></td></tr>
<tr><td>Please note that we do not store any personal information. All you need is a login name which is solely used for identifying sandboxes so that you can keep track of how many jobs your PC has solved while it was idle.  </td></tr>
<tr><td></td></tr>

<tr><td><h3>What About Security?</h3></td></tr>
<tr><td>The applications that will be running on your PC when you leave it in screen saver mode are all executed in a so-called 'sandbox'. A sandbox provides a secure execution environment, in which untrusted programs can run. Programs running in the sandbox can neither compromise nor gain access to your PC.</td></tr>

<tr><td><h3>Sandbox monitor</h3></td></tr>
<tr><td>After logging in you will be presented with a list of statistics for your own sandboxes. In case you want to compare your donations to those from other sandbox resource owners, you can take a look at the <a href='sssmonitor.py'>overall sandbox monitor</a>.</td></tr>

<tr><td><h3>More Questions?</h3></td></tr>
<tr><td>Please check the <a href='sssfaq.py?language=english'>FAQ</a>, or send us an email.</td></tr>
</table>
<br>
<table class='sandboxlogin'>
<TR><TD align='' colspan=''>Choose a user name:</TD>
<TD><input type='TEXT' name='username' size='10'></TD></TR>

<TR><TD align='' colspan=''>Choose a password:</TD>
<TD><input type='PASSWORD' name='password' size='10'></TD></TR>

<TR><TD>I'm a new user</TD><TD align='left' colspan='1'><input type='checkbox' name='newuser'></TD></TR>

<TR><TD align='center' colspan='2'><input type='SUBMIT' value='Send'></TD></TR>


</table></form>
"""

html['danish'] = \
    """
<form action='sssadmin.py' method='POST'>

<table class='sandboxlogintext'>
<tr><td><a href='ssslogin.py?language=english'>In English</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Velkommen til MiG-SSS. Ved at downloade og installere denne software vil din PC, n&aring;r den er i screen saver mode, donere den ubrugte CPU-tid til at bidrage med at l&oslash;se videnskabelige problemer. Det eneste, der kr&aelig;ves er, at man logger ind nedenfor, downloader softwaren og f&oslash;lger installationsproceduren.<td><tr>

<tr><td><h3>Brugernavn</h3></td></tr>
<tr><td>Der gemmes ikke nogen former for personlig information. Der skal blot v&aelig;lges et brugernavn, som udelukkende bruges til at identificere individuelle bidragsydere, s&aring; man kan f&oslash;lge med i hvor mange jobs ens PC har afviklet mens den har v&aelig;ret i screen saver mode.<td></tr>

<tr><td><h3>Hvad med sikkerhed?</h3></td></tr>
<tr><td>De programmer der kommer til at k&oslash;re n&aring;r din PC er i screen saver mode, vil alle blive afviklet i en s&aring;kaldt 'sandkasse'. En sandkasse stiller et sikkert milj&oslash; tilr&aring;dighed, hvori det er sikkert at k&oslash;re ukendte programmer. Programmer k&oslash;rende i sandkassen kan hverken kompromittere eller f&aring; tilgang til din PC.</td></tr>

<tr><td><h3>Installationsvejledning</h3></td></tr>
<tr><td>Programmet findes b&aring;de i en version til Windows XP og Linux. Windowsbrugere downloader en installationsfil, som g&oslash;r installationen meget simpel. En trin-for-trin guide kan findes her: <a href='http://www.migrid.org/MiG/MiG/Mig_danish/MiG-SSS installationsprocedure'>Installationsguide til Windows</a><td></tr>

<tr><td><h3>Job monitor</h3></td></tr>
<tr><td>N&aring;r du logger ind f&aring;r du en oversigt over jobs k&oslash;rt p&aring; dine sandkasse resurser. Hvis du gerne vil sammenligne med andres sandkasse donationer, kan du se p&aring; den <a href='sssmonitor.py'>samlede sandkasse monitor</a>.</td></tr>

<tr><td><h3>Flere sp&oslash;rgsm&aring;l?</h3></td></tr>
<tr><td>Check om det skulle findes i <a href='sssfaq.py?language=danish'>FAQ'en</a>, ellers send os en email.</td></tr>
</table>

<br>
<table class='sandboxlogin'>
<TR><TD align='' colspan=''>V&aelig;lg et brugernavn:</TD>
<TD><input type='TEXT' name='username' size='10'></TD></TR>

<TR><TD align='' colspan=''>V&aelig;lg et password:</TD>
<TD><input type='PASSWORD' name='password' size='10'></TD></TR>

<TR><TD>Jeg er ny bruger</TD><TD align='left' colspan='1'><input type='checkbox' name='newuser'></TD></TR>

<TR><TD align='center' colspan='2'><input type='SUBMIT' value='Send'></TD></TR>


</table></form>
"""


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_menu=client_id)
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Screen Saver Sandbox'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    language = accepted['language'][-1]

    if not language in html.keys():
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported language: %s, defaulting to %s'
                               % (language, default_language)})
        language = default_language

        # print "<a href='ssslogin.py'>Default language</a>"
        # sys.exit(1)

    output_objects.append({'object_type': 'html_form', 'text'
                          : html[language]})
    return (output_objects, returnvalues.OK)


