#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssslogin - SSS welcome and login backend
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

from shared import returnvalues
from shared.defaults import csrf_field
from shared.functional import validate_input
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.init import initialize_main_variables

default_language = 'english'


def signature():
    """Signature of the main function"""

    defaults = {'language': [default_language]}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    output_objects.append({'object_type': 'header', 'text'
                          : '%s Screen Saver Sandbox' % \
                            configuration.short_title
                            })
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    language = accepted['language'][-1]

    if not configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'text', 'text':
                               '''Sandbox resources are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    if not language in ("maintenance", "english", "danish"):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported language: %s, defaulting to %s'
                               % (language, default_language)})
        language = default_language

        # print "<a href='ssslogin.py'>Default language</a>"
        # sys.exit(1)

    html = {}
    html['maintenance'] = """
Sorry we are currently down for maintenance, we'll be back shortly
"""

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'site': configuration.short_title, 'form_method': form_method,
                    'csrf_field': csrf_field, 'csrf_limit': csrf_limit}
    target_op = 'sssadmin'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    html['english'] = """
<form method='%(form_method)s' action='%(target_op)s.py'> 
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />

<table class='sandboxlogintext'>
<tr><td><a class='danishlink iconspace' href='ssslogin.py?language=danish'>P&aring; dansk</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Welcome to the %(site)s-SSS download site. By downloading and installing this software, your computer will be participating in solving scientific problems whenever the screen saver is on. All you have to do is log in below, download the sandbox, and follow the instructions during the install procedure.</td></tr>

<tr><td><h3>Why Login?</h3></td></tr>
<tr><td>Please note that we do not store any personal information. All you need is a login name which is solely used for identifying sandboxes so that you can keep track of how many jobs your PC has solved while it was idle.  </td></tr>
<tr><td></td></tr>

<tr><td><h3>What About Security?</h3></td></tr>
<tr><td>The applications that will be running on your PC when you leave it in screen saver mode are all executed in a so-called 'sandbox'. A sandbox provides a secure execution environment, in which untrusted programs can run. Programs running in the sandbox can neither compromise nor gain access to your PC.</td></tr>

<tr><td><h3>Sandbox monitor</h3></td></tr>
<tr><td>After logging in you will be presented with a list of statistics for your own sandboxes. In case you want to compare your donations to those from other sandbox resource owners, you can take a look at the <a class='monitorlink iconspace' href='sssmonitor.py'>overall sandbox monitor</a>.</td></tr>

<tr><td><h3>More Questions?</h3></td></tr>
<tr><td>Please check the <a class='infolink iconspace' href='sssfaq.py?language=english'>FAQ</a>, or send us an email.</td></tr>
</table>
<br />
<table class='sandboxlogin'>
<tr>
<td class='righttext'>Choose a user name:</td>
<td class='lefttext'><input type='text' name='username' size='10' /></td>
</tr>
<tr>
<td class='righttext'>Choose a password:</td>
<td class='lefttext'><input type='password' name='password' size='10' /></td>
</tr>
<tr>
<td class='righttext'>I'm a new user</td>
<td class='lefttext'><input type='checkbox' name='newuser' /></td>
</tr>
<tr>
<td class='centertext' colspan='2'><input type='submit' value='Send' /></td>
</tr>


</table></form>
""" % fill_helpers

    html['danish'] = """
<form method='%(form_method)s' action='%(target_op)s.py'> 
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />

<table class='sandboxlogintext'>
<tr><td><a class='englishlink iconspace' href='ssslogin.py?language=english'>In English</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Velkommen til %(site)s-SSS. Ved at downloade og installere denne software vil din PC, n&aring;r den er i screen saver mode, donere den ubrugte CPU-tid til at bidrage med at l&oslash;se videnskabelige problemer. Det eneste, der kr&aelig;ves er, at man logger ind nedenfor, downloader softwaren og f&oslash;lger installationsproceduren.<td><tr>

<tr><td><h3>Brugernavn</h3></td></tr>
<tr><td>Der gemmes ikke nogen former for personlig information. Der skal blot v&aelig;lges et brugernavn, som udelukkende bruges til at identificere individuelle bidragsydere, s&aring; man kan f&oslash;lge med i hvor mange jobs ens PC har afviklet mens den har v&aelig;ret i screen saver mode.<td></tr>

<tr><td><h3>Hvad med sikkerhed?</h3></td></tr>
<tr><td>De programmer der kommer til at k&oslash;re n&aring;r din PC er i screen saver mode, vil alle blive afviklet i en s&aring;kaldt 'sandkasse'. En sandkasse stiller et sikkert milj&oslash; tilr&aring;dighed, hvori det er sikkert at k&oslash;re ukendte programmer. Programmer k&oslash;rende i sandkassen kan hverken kompromittere eller f&aring; tilgang til din PC.</td></tr>

<tr><td><h3>Installationsvejledning</h3></td></tr>
<tr><td>Programmet findes b&aring;de i en version til Windows XP og Linux. Windowsbrugere downloader en installationsfil, som g&oslash;r installationen meget simpel. En trin-for-trin guide kan findes her: <a class='infolink iconspace' href='http://www.migrid.org/MiG/MiG/Mig_danish/MiG-SSS installationsprocedure'>Installationsguide til Windows</a><td></tr>

<tr><td><h3>Job monitor</h3></td></tr>
<tr><td>N&aring;r du logger ind f&aring;r du en oversigt over jobs k&oslash;rt p&aring; dine sandkasse resurser. Hvis du gerne vil sammenligne med andres sandkasse donationer, kan du se p&aring; den <a class='monitorlink iconspace' href='sssmonitor.py'>samlede sandkasse monitor</a>.</td></tr>

<tr><td><h3>Flere sp&oslash;rgsm&aring;l?</h3></td></tr>
<tr><td>Check om det skulle findes i <a class='infolink iconspace' href='sssfaq.py?language=danish'>FAQ'en</a>, ellers send os en email.</td></tr>
</table>

<br />
<table class='sandboxlogin'>
<tr><td align='center' colspan='1'>V&aelig;lg et brugernavn:</td>
<td><input type='text' name='username' size='10' /></td></tr>

<tr><td align='center' colspan='1'>V&aelig;lg et password:</td>
<td><input type='password' name='password' size='10' /></td></tr>

<tr><td>Jeg er ny bruger</td><td align='left' colspan='1'><input type='checkbox' name='newuser' /></td></tr>

<tr><td align='center' colspan='2'><input type='submit' value='Send' /></td></tr>


</table></form>
""" % fill_helpers

    output_objects.append({'object_type': 'html_form', 'text': html[language]})
    return (output_objects, returnvalues.OK)


