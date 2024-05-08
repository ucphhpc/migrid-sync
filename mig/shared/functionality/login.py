#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# login - general login method selection backend
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""Back end to let users choose between login with certificate, OpenID 2.0 or
OpenID Connect.
"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import verify_local_url
from mig.shared.defaults import keyword_all
from mig.shared.functional import validate_input
from mig.shared.init import initialize_main_variables, find_entry


def get_valid_topics(configuration):
    """Get a map of valid show topics and their associated helper URLs"""
    valid_topics = {
        'migcert': {'url': configuration.migserver_https_mig_cert_url},
        'migoid': {'url': configuration.migserver_https_mig_oid_url},
        'migoidc': {'url': configuration.migserver_https_mig_oidc_url},
        'extcert': {'url': configuration.migserver_https_ext_cert_url},
        'extoid': {'url': configuration.migserver_https_ext_oid_url},
        'extoidc': {'url': configuration.migserver_https_ext_oidc_url}
    }
    return valid_topics


def signature(configuration):
    """Signature of the main function"""

    defaults = {'show': configuration.site_login_methods,
                'modauthopenid.error': [''],
                'modauthopenid.referrer': [''],
                'redirect_url': ['']}
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
        show = list(valid_show)
    else:
        show = [i.lower() for i in accepted['show']]
    show = [i for i in show if i in valid_show and valid_show[i]['url']]
    if not show:
        logger.info('%s showing default topics' % op_name)
        show = defaults['show']
    openid_error = ', '.join(accepted['modauthopenid.error'])
    # OpenID server errors may return here with redirect url set
    redirect_url = accepted['redirect_url'][-1]

    if not verify_local_url(configuration, redirect_url):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''The requested redirect_url is not a valid local destination'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s login selector' % configuration.short_title
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>
    '''
    add_init = ''
    add_ready = '''
        var action = "login", oid_title, oid_url, tag_prefix;
        oid_title = "%s";
        oid_url = "%s";
        tag_prefix = "extoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oidc_title = "%s";
        oidc_url = "%s";
        tag_prefix = "extoidc_";
        check_oidc_available(action, oidc_title, oidc_url, tag_prefix);
        oid_title = "%s";
        var oid_url = "%s";
        tag_prefix = "migoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oidc_title = "%s";
        var oidc_url = "%s";
        tag_prefix = "migoidc_";
        check_oidc_available(action, oidc_title, oidc_url, tag_prefix);
''' % (configuration.user_ext_oid_title, configuration.user_ext_oid_provider,
       configuration.user_ext_oidc_title, configuration.user_ext_oidc_provider,
       configuration.user_mig_oid_title, configuration.user_mig_oid_provider,
       configuration.user_mig_oidc_title, configuration.user_mig_oidc_provider)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    title_entry['skipmenu'] = True
    # NOTE: keep empty header for narrow page layout
    header_entry = {'object_type': 'header', 'text':
                    # 'Welcome to the %s login selector page' % \
                    #  configuration.short_title
                    ''}
    output_objects.append(header_entry)

    html = ""
    if openid_error:
        err_txt, report_txt = '', ''
        report_fail = """, so you cannot currently use it for login to %s.
<br />
Please report the problem to your OpenID identity provider.
""" % configuration.short_title
        if redirect_url:
            report_fail += """<br />The error happened on access to %s ."""  \
                           % redirect_url

        if 'no_idp_found' in openid_error:
            err_txt += "OpenID server did not respond!"
            report_txt += """It appears the requested OpenID login service is
offline""" + report_fail
        elif 'canceled' in openid_error:
            err_txt += "OpenID login canceled!"
            report_txt += """You have to either enter your OpenID login and
accept that it is used for %s login or choose another one of the login methods
below.""" % configuration.short_title
        else:
            err_txt += "OpenID server error!"
            report_txt += """It appears there's a problem with the requested
OpenID login service""" + report_fail

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
    if configuration.user_openid_providers and 'extoid' in show or 'migoid' in show or \
            configuration.user_openidconnect_providers and 'extoidc' in show or 'migoidc' in show:
        html += """<h2>OpenID</h2>
<p>
The simplest login method is to use an existing OpenID 2.0 or OpenID Connect
login if you have one.
</p>
"""

        for method in show:
            if method == 'migoid':
                html += """
<p>
%(migoid_title)s users can login to %(short_title)s using the associated
OpenID 2.0 server.
</p>
<div id='migoid_status'>
<!-- OpenID 2.0 status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID 2.0 debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<input id='migoid_button' type='submit' value='%(migoid_title)s User OpenID 2.0 Login' />
</form>
</div>
"""
            if method == 'migoidc':
                html += """
<p>
%(migoidc_title)s users can login to %(short_title)s using the associated
OpenID Connect server.
</p>
<div id='migoidc_status'>
<!-- OpenID Connect status updated by AJAX call -->
</div>
<div id='migoidc_debug'>
<!-- OpenID Connect debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoidc_url)s'>
<input id='migoidc_button' type='submit' value='%(migoidc_title)s User OpenID Connect Login' />
</form>
</div>
"""
            if method == 'extoid':
                html += """
<p>
%(extoid_title)s users can login to %(short_title)s using the associated
OpenID 2.0 server.
</p>
<div id='extoid_status'>
<!-- OpenID 2.0 status updated by AJAX call -->
</div>
<div id='extoid_debug'>
<!-- OpenID 2.0 debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input id='extoid_button' type='submit' value='%(extoid_title)s User OpenID 2.0 Login' />
</form>
</div>
"""
            if method == 'extoidc':
                html += """
<p>
%(extoidc_title)s users can login to %(short_title)s using the associated
OpenID Connect server.
</p>
<div id='extoidc_status'>
<!-- OpenID Connect status updated by AJAX call -->
</div>
<div id='extoidc_debug'>
<!-- OpenID Connect debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoidc_url)s'>
<input id='extoidc_button' type='submit' value='%(extoidc_title)s User OpenID Connect Login' />
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
               'migoidc_url': valid_show['migoidc']['url'],
               'migoid_title': configuration.user_mig_oid_title,
               'migoidc_title': configuration.user_mig_oidc_title,
               'extoid_url': valid_show['extoid']['url'],
               'extoidc_url': valid_show['extoidc']['url'],
               'extoid_title': configuration.user_ext_oid_title,
               'extoidc_title': configuration.user_ext_oidc_title,
               'migcert_url': valid_show['migcert']['url'],
               'migcert_title': configuration.user_mig_cert_title,
               'extcert_url': valid_show['extcert']['url'],
               'extcert_title': configuration.user_ext_cert_title,
               'short_title': configuration.short_title}
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    return (output_objects, returnvalues.OK)
