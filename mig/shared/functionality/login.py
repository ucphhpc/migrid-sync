#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# login - general login method selection backend
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
        'migcert': {'url': configuration.migserver_https_mig_cert_url},
        'migoid': {'url': configuration.migserver_https_mig_oid_url},
        'extcert': {'url': configuration.migserver_https_ext_cert_url},
        'extoid': {'url': configuration.migserver_https_ext_oid_url},
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
        show = [i.lower() for i in accepted['show']]
    show = [i for i in show if i in valid_show and valid_show[i]['url']]
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
        oid_title = "%s";
        oid_url = "%s";
        tag_prefix = "extoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oid_title = "%s";
        var oid_url = "%s";
        tag_prefix = "migoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
    });
</script>
''' % (configuration.user_ext_oid_title, configuration.user_ext_oid_provider, 
       configuration.user_mig_oid_title, configuration.user_mig_oid_provider)
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
    if configuration.user_openid_providers and 'extoid' in show or 'migoid' in show:
        html += """<h2>OpenID</h2>
<p>
The simplest login method is to use an existing OpenID login if you have one.
</p>
"""
            
        for method in show:
            if method == 'migoid':
                html += """
<p>
%(migoid_title)s users can login to %(short_title)s using the associated
OpenID server.
</p>
<div id='migoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<input id='migoid_button' type='submit' value='%(migoid_title)s User OpenID Login' />
</form>
</div>
"""
            if method == 'extoid':
                html += """
<p>
%(extoid_title)s users can login to %(short_title)s using the associated
OpenID server.
</p>
<div id='extoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='extoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input id='extoid_button' type='submit' value='%(extoid_title)s User OpenID Login' />
</form>
</div>
"""
            
        html += """
<p>
When you click the OpenID Login button you will be taken to a login page, where
you need to provide your credentials and accept that your identity is used for
login on %(short_title)s.
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
        for method in show:
            if method == 'migcert':
                html += """<p>
%(migcert_title)s users with an associated x509 certificate can use it for
login here.
</p>
<div class='form_container'>
<form method='get' action='%(migcert_url)s'>
<input id='reqcert_button' type='submit' value='%(migcert_title)s User Certificate Login' />
</form>
</div>
"""
            if method == 'extcert':
                html += """<p>
%(extcert_title)s users with an associated x509 certificate can use it for
login here.
</p>
<div class='form_container'>
<form method='get' action='%(extcert_url)s'>
<input id='reqcert_button' type='submit' value='%(extcert_title)s User Certificate Login' />
</form>
</div>
"""
        html += """
<p>
Depending on your certificate installation you may be prompted for a password
to use the certificate.
</p>
"""
    var_map = {'migoid_url': valid_show['migoid']['url'],
               'migoid_title': configuration.user_mig_oid_title,
               'extoid_url': valid_show['extoid']['url'],
               'extoid_title': configuration.user_ext_oid_title,
               'migcert_url': valid_show['migcert']['url'],
               'migcert_title': configuration.user_mig_cert_title,
               'extcert_url': valid_show['extcert']['url'],
               'extcert_title': configuration.user_ext_cert_title,
               'short_title': configuration.short_title}
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    return (output_objects, returnvalues.OK)
