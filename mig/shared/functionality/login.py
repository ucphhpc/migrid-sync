#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# login - general login method selection backend
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

"""Back end to let users choose between login with certificate or OpenID"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import keyword_all
from shared.functional import validate_input
from shared.init import initialize_main_variables, find_entry

def get_valid_topics(configuration):
    """Get a map of valid show topics and their associated helper URLs"""
    valid_topics = {
        'kitoid': {'url': configuration.migserver_https_oid_url},
        'migoid': {'url': configuration.migserver_https_oid_url},
        'migcert': {'url': configuration.migserver_https_cert_url},
        'extcert': {'url': configuration.migserver_https_cert_url},
        }
    return valid_topics

def signature(configuration):
    """Signature of the main function"""

    defaults = {'show': configuration.site_login_methods,
                'modauthopenid.error': [''],
                'modauthopenid.referrer': ['']}
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
    openid_error = ', '.join(accepted['modauthopenid.error'])

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s login selector' % configuration.short_title
    # TODO: move ping to shared location for signup and login
    # TODO: wrap openid ping in function and split up for each oid
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.migtools.js"></script>
<script type="text/javascript">
    $(document).ready(function() {
        var action = "login", oid_title, oid_url, tag_prefix;
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
                    : 'Welcome to the %s login selector page' % \
                    configuration.short_title}
    output_objects.append(header_entry)

    html = ""
    if openid_error:
        err_txt, report_txt = '', ''
        if 'no_idp_found' in openid_error:
            err_txt += "OpenID server did not respond!"
            report_txt += """It appears the requested OpenID login service is
offline"""
        else:
            err_txt += "OpenID server error!"
            report_txt += """It appears there's a problem with the requested
OpenID login service"""
        report_txt += """, so you cannot currently use it for login to %s.<br />
Please report the problem to your OpenID identity provider.
""" % configuration.short_title
        html += """<h2>OpenID Login to %s Failed!</h2>
<div class='errortext'>
%s (error code(s): %s)
</div>
<div class='warningtext'>
%s
</div>
""" % (configuration.short_title, err_txt, openid_error, report_txt)
    html += """<h2>Login to %s</h2>
<p>
There are multiple login methods as described below.
</p>
""" % configuration.short_title
    if configuration.user_openid_providers and 'kitoid' in show or \
           'migoid' in show:
        html += """<h2>OpenID</h2>
The simplest login method is to use an existing OpenID login if you have one.
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
<input id='kitoid_button' type='submit' value='Login with KU OpenID' />
</form>
</div>
"""
        if 'migoid' in show:
            html += """
<p>
If you already have a MiG OpenID account here you can login to the account
using the local MiG OpenID server.
<div id='migoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<input id='migoid_button' type='submit' value='Login with MiG OpenID' />
</form>
</p>
</div>
"""
            
        html += """
<p>
When you click the Login with OpenID button you will be taken to a login
page, where you need to provide your credentials and accept that your identity
is used for login with this site.
</p>
"""

    if 'migcert' in show or 'extcert' in show:
        html += """
<h2>Client Certificate</h2>
<p>
We provide high security access control with client certificates, like the ones
you may know from digital signature providers.
</p>
"""
        html += """
<p>
If you have an x509 user certificate associated with your account you can login
using it here.
Depending on your certificate installation you may be prompted for a password.
</p>
<div class='form_container'>
<form method='get' action='%(extcert_url)s'>
<input id='reqcert_button' type='submit' value='Login with Your User Certificate' />
</form>
</div>
"""
        html += """
"""
    var_map = {'kitoid_url': valid_show['kitoid']['url'],
               'migoid_url':valid_show['migoid']['url'],
               'extcert_url': valid_show['extcert']['url'],
               }
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    return (output_objects, returnvalues.OK)
