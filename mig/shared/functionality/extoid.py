#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# extoid - external openid account sign up backend
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Sign up for account with external OpenID back end"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input
from shared.init import initialize_main_variables, find_entry
from shared.safeinput import html_escape


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID account sign up' % configuration.short_title
    title_entry['skipmenu'] = True
    header_entry = {'object_type': 'header', 'text'
                    : 'Welcome to the %s OpenID account sign up page' % \
                    configuration.short_title}
    output_objects.append(header_entry)

    output_objects.append({'object_type': 'html_form', 'text'
                          : """<h2>Simple Login: OpenID</h2>
<p>
Before you can use this site you need a user account. However, it is possible
to sign up with an existing OpenID login.<br />
Thus, if you are a KU user you simply use your usual KU username and password
like you do on KUnet.<br />
When you click the Sign Up with OpenID button you will be taken to a login
page where you need to login and accept that your login is allowed for login
with this site as well.
</p>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<!--
<input type='hidden' name='openid.sreg.required' value='KUID,CN,MAIL,O,OU,ROLE,full_name,country,email,organization,organizational_unit' />
-->
<input type='hidden' name='openid.sreg.required' value='KUID,CN,MAIL,O,OU,ROLE' />
<input id='extoid_button' type='submit' value='Sign Up with OpenID (ALLCAPS attr)' />
</form>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<!--
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,role' />
-->
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,role' />
<input id='extoid_button' type='submit' value='Sign Up with OpenID (OID style attr)' />
</form>
</div>
<div class='form_container'>
<form method='post' action='%(kitoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<!--
<input type='hidden' name='openid.sreg.required' value='KUID,CN,MAIL,O,OU,ROLE,full_name,country,email,organization,organizational_unit' />
-->
<input type='hidden' name='openid.sreg.required' value='KUID,CN,MAIL,O,OU,ROLE' />
<input id='extoid_button' type='submit' value='Sign Up with KIT OpenID (ALLCAPS attr)' />
</form>
</div>
<div class='form_container'>
<form method='post' action='%(kitoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<!--
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,role' />
-->
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email' />
<input id='extoid_button' type='submit' value='Sign Up with KIT OpenID (OID style attr)' />
</form>
</div>
<h2>Advanced Login: Client Certificate</h2>
<p>
Advanced users may choose to use a client certificate for even more secure
access. It is a bit cumbersome to get and install such a client certificate,
so if you want to keep it simple, just go with the OpenID method above
instead. It still provides a solid security solution as long as you follow
the usual good password practice rules.<br />
</p>
<div class='form_container'>
<form method='get' action='%(reqcert_url)s'>
<input id='reqcert_button' type='submit' value='Request a User Certificate' />
</form>
</div>
<p>
If you already have a x509 user certificate that we trust, you can also sign
up with that instead of requesting a new one.
</p>
<div class='form_container'>
<form method='get' action='%(extcert_url)s'>
<input id='extcert_button' type='submit' value='Sign Up With Existing User Certificate' />
</form>
</div>
""" % {'short_title': configuration.short_title,
       'extoid_url': os.path.join(configuration.migserver_https_oid_url,
                                  'wsgi-bin', 'autocreate.py'),
       'kitoid_url': os.path.join(configuration.migserver_https_sid_url,
                                  'wsgi-bin', 'autocreate.py'),
       'reqcert_url': os.path.join(configuration.migserver_https_sid_url,
                                   'cgi-sid', 'reqcert.py'),
       'extcert_url': os.path.join(configuration.migserver_https_cert_url,
                                   'cgi-bin', 'extcert.py'),
       }})

    return (output_objects, returnvalues.OK)


