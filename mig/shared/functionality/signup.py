#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# signup - general sign up entry point backend
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Sign up for account with certificate or OpenID back end"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import keyword_all
from shared.functional import validate_input
from shared.init import initialize_main_variables, find_entry

def get_valid_topics(configuration):
    """Get a map of valid show topics and their associated helper URLs"""
    valid_topics = {
        'kitoid': {'url': os.path.join(configuration.migserver_https_oid_url,
                                       'wsgi-bin', 'autocreate.py')},
        'migoid': {'url': os.path.join(configuration.migserver_https_sid_url,
                                       'wsgi-bin', 'autocreate.py')},
        'migcert': {'url': os.path.join(configuration.migserver_https_sid_url,
                                        'cgi-sid', 'reqcert.py')},
        'extcert': {'url': os.path.join(configuration.migserver_https_cert_url,
                                        'cgi-bin', 'extcert.py')}
        }
    return valid_topics

def signature(configuration):
    """Signature of the main function"""

    defaults = {'show': configuration.site_signup_methods}
    return ['html_form', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    valid_show = get_valid_topics(configuration)
    if keyword_all in accepted['show']:
        show = valid_show.keys()
    else:
        show = [i.lower() for i in accepted['show'] if i.lower() in valid_show]
    if not show:
        logger.info('%s showing default topics' % op_name)
        show = defaults['show']

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s account sign up' % configuration.short_title
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.migtools.js"></script>
<script type="text/javascript">
    $(document).ready(function() {
        var action = "sign up", oid_title, oid_url, tag_prefix;
        oid_title = "KIT";
        oid_url = "https://openid.ku.dk/id/";
        tag_prefix = "kitoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oid_title = "%s";
        var oid_url = "https://%s:%s/openid/id/";
        tag_prefix = "migoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
    });
</script>
''' % (configuration.short_title, configuration.user_openid_show_address,
       configuration.user_openid_show_port)
    title_entry['skipmenu'] = True
    header_entry = {'object_type': 'header', 'text'
                    : 'Welcome to the %s account sign up page' % \
                    configuration.short_title}
    output_objects.append(header_entry)

    html = """<h2>Signup for %s</h2>
<p>
Before you can use this site you need a user account. You can sign up for one
here as described below.
</p>
""" % configuration.short_title
    if configuration.user_openid_providers and 'kitoid' in show or \
           'migoid' in show:
        html += """<h2>OpenID</h2>
The simplest sign up method is to use an existing OpenID login if you have one.
"""
        if 'kitoid' in show:
            html += """
<p>
If you are a KU user, your usual login for KU Net and KU webmail works for
OpenID as well.
</p>
<div id='kitoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='kitoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(kitoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,country,state,role' />
<input id='kitoid_button' type='submit' value='Sign Up with KU OpenID' />
</form>
</div>
"""
        if 'migoid' in show:
            html += """
<p>
If you already have a MiG user certificate and account here you can sign up for
OpenID access to the account using the local MiG OpenID server.
<div id='migoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,country,state,role' />
<input id='migoid_button' type='submit' value='Sign Up with MiG OpenID' />
</form>
</p>
</div>
"""
            
        html += """
<p>
When you click the Sign Up with OpenID button you will be taken to a login
page where you need to enter your credentials and accept that your identity is
used for login with this site as well.
</p>
"""

    if 'migcert' in show or 'extcert' in show:
        html += """
<h2>Client Certificate</h2>
<p>
We provide high security access control with client certificates, like the ones
you may know from digital signature providers. It is a bit cumbersome to get
and install such a client certificate, so if you want to keep it simple and
have other access options, you may want to use those instead.
</p>
"""
        if 'migcert' in show:
            html += """
<p>
You can sign up for an account with an associated x509 user certificate here.
</p>
<div class='form_container'>
<form method='get' action='%(migcert_url)s'>
<input id='reqcert_button' type='submit' value='Sign Up for a User Certificate' />
</form>
</div>
"""
        if 'extcert' in show:
            html += """
<p>
If you already have an x509 user certificate that we trust, you can also sign
up with that instead of requesting a new one.
</p>
<div class='form_container'>
<form method='get' action='%(extcert_url)s'>
<input id='extcert_button' type='submit' value='Sign Up with Existing User Certificate' />
</form>
</div>
"""
        html += """
"""
    var_map = {'kitoid_url': valid_show['kitoid']['url'],
               'migoid_url':valid_show['migoid']['url'],
               'migcert_url': valid_show['migcert']['url'],
               'extcert_url': valid_show['extcert']['url'],
               }
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    return (output_objects, returnvalues.OK)
