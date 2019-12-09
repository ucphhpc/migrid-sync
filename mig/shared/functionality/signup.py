#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# signup - general sign up entry point backend
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

    migoid_url, migcert_url, extoid_url, extcert_url = '', '', '', ''
    if configuration.migserver_https_mig_oid_url:
        migoid_url = os.path.join(configuration.migserver_https_sid_url,
                                  'cgi-sid', 'reqoid.py')
    if configuration.migserver_https_mig_cert_url:
        migcert_url = os.path.join(configuration.migserver_https_sid_url,
                                   'cgi-sid', 'reqcert.py')
    # NOTE: external users go through auth URL to sign up
    if configuration.migserver_https_ext_oid_url:
        extoid_url = os.path.join(configuration.migserver_https_ext_oid_url,
                                  'wsgi-bin', 'autocreate.py')
    if configuration.migserver_https_ext_cert_url:
        extcert_url = os.path.join(configuration.migserver_https_ext_cert_url,
                                   'wsgi-bin', 'extcert.py')
    valid_topics = {'migoid': {'url': migoid_url},
                    'migcert': {'url': migcert_url},
                    'extoid': {'url': extoid_url},
                    'extcert': {'url': extcert_url},
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
        show = [i.lower() for i in accepted['show']]
    show = [i for i in show if i in valid_show and valid_show[i]['url']]
    if not show:
        logger.info('%s showing default topics' % op_name)
        show = defaults['show']

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s account sign up' % configuration.short_title
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.migtools.js"></script>
    '''
    add_init = ''
    add_ready = '''
        var action = "sign up", oid_title, oid_url, tag_prefix;
        oid_title = "%s";
        oid_url = "%s";
        tag_prefix = "extoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oid_title = "%s";
        var oid_url = "%s";
        tag_prefix = "migoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
''' % (configuration.user_ext_oid_title, configuration.user_ext_oid_provider,
       configuration.user_mig_oid_title, configuration.user_mig_oid_provider)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    title_entry['skipmenu'] = True
    # header_entry = {'object_type': 'header', 'text'
    #                : 'Welcome to the %s account sign up page' % \
    #                configuration.short_title}
    # output_objects.append(header_entry)

    html = """
    <h2>Signup for %s</h2>
<p>
Before you can use this site you need a user account. You can sign up for one
here as described below.
</p>
""" % configuration.short_title
    if configuration.user_openid_providers and 'extoid' in show or \
            'migoid' in show:
        html += """<h2>OpenID Login</h2>
The simplest sign up method is to use an existing OpenID login if you have one.
"""
        for method in show:
            if method == 'migoid':
                html += """
<p>
%(migoid_title)s users can sign up for an account with OpenID access here.
</p>
<div id='migoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<!-- NOTE: we can't request field here as there is no account yet! -->
<input id='migoid_button' type='submit' value='%(migoid_title)s User OpenID Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a registration page where
you need to enter your details to get both an OpenID account <em>and</em> an
account on %(short_title)s with that OpenID login associated.
</p>
"""
            if method == 'extoid':
                html += """
<p>
%(extoid_title)s users can sign up for an account here using their existing
OpenID credentials.
</p>
<div id='extoid_status'>
<!-- OpenID status updated by AJAX call -->
</div>
<div id='extoid_debug'>
<!-- OpenID debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,country,state,role' />
<input id='extoid_button' type='submit' value='%(extoid_title)s User OpenID Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a login page where you
need to enter your credentials and accept that your identity is used for
%(short_title)s OpenID login.
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
        for method in show:
            if method == 'migcert':
                html += """
<p>
You can sign up for an account with an associated x509 user certificate here.
</p>
<div class='form_container'>
<form method='get' action='%(migcert_url)s'>
<input id='reqcert_button' type='submit' value='%(migcert_title)s User Certificate Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a registration page where
you need to enter your details to get both a user certificate <em>and</em> an
account on %(short_title)s with that user certificate associated for login.
</p>
"""
            if method == 'extcert':
                html += """
<p>
%(extcert_title)s users can sign up for an %(short_title)s account here using
their existing x509 user certificate.
</p>
<div class='form_container'>
<form method='get' action='%(extcert_url)s'>
<input id='extcert_button' type='submit' value='%(extcert_title)s User Certificate Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a registration page where
the fields will mostly be pre-filled based on your certificate. You just need
to accept that your certificate is used for %(short_title)s login.
</p>

"""
        html += """
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
