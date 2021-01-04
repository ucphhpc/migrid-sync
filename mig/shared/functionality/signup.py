#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# signup - general sign up entry point backend
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Back end to let users sign up for account with certificate, OpenID 2.0 or
OpenID Connect."""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.defaults import keyword_all, csrf_field, keyword_auto
from mig.shared.functional import validate_input
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry


def get_valid_topics(configuration):
    """Get a map of valid show topics and their associated helper URLs"""

    migoid_url, migoidc_url, migcert_url = '', '', ''
    extoid_url, extoidc_url, extcert_url = '', '', ''
    if configuration.migserver_https_mig_oid_url:
        migoid_url = os.path.join(configuration.migserver_https_sid_url,
                                  'cgi-sid', 'reqoid.py')
    if configuration.migserver_https_mig_oidc_url:
        migoidc_url = os.path.join(configuration.migserver_https_sid_url,
                                   'cgi-sid', 'reqoid.py')
    if configuration.migserver_https_mig_cert_url:
        migcert_url = os.path.join(configuration.migserver_https_sid_url,
                                   'cgi-sid', 'reqcert.py')
    # NOTE: external users go through auth URL to sign up
    if configuration.migserver_https_ext_oid_url:
        extoid_url = os.path.join(configuration.migserver_https_ext_oid_url,
                                  'wsgi-bin', 'autocreate.py')
    if configuration.migserver_https_ext_oidc_url:
        extoidc_url = os.path.join(configuration.migserver_https_ext_oidc_url,
                                   'wsgi-bin', 'autocreate.py')
    if configuration.migserver_https_ext_cert_url:
        extcert_url = os.path.join(configuration.migserver_https_ext_cert_url,
                                   'wsgi-bin', 'extcert.py')
    valid_topics = {'migoid': {'url': migoid_url},
                    'migoidc': {'url': migoidc_url},
                    'migcert': {'url': migcert_url},
                    'extoid': {'url': extoid_url},
                    'extoidc': {'url': extoidc_url},
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
                                                 defaults, output_objects,
                                                 allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    valid_show = get_valid_topics(configuration)
    if keyword_all in accepted['show']:
        show = valid_show.keys()
    else:
        show = list(set([i.lower() for i in accepted['show']]))
    show = [i for i in show if i in valid_show and valid_show[i]['url']]
    if not show:
        logger.info('%s showing default topics' % op_name)
        show = defaults['show']

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s account sign up' % configuration.short_title
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>
    '''
    add_init = ''
    add_ready = '''
        var action = "sign up", oid_title, oid_url, tag_prefix;
        oid_title = "%s";
        oid_url = "%s";
        tag_prefix = "extoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        oidc_url = "%s";
        tag_prefix = "extoidc_";
        check_oid_available(action, oid_title, oidc_url, tag_prefix);
        oid_title = "%s";
        var oid_url = "%s";
        tag_prefix = "migoid_";
        check_oid_available(action, oid_title, oid_url, tag_prefix);
        var oidc_url = "%s";
        tag_prefix = "migoidc_";
        check_oid_available(action, oid_title, oidc_url, tag_prefix);
''' % (configuration.user_ext_oid_title, configuration.user_ext_oid_provider,
       configuration.user_ext_oidc_provider, configuration.user_mig_oid_title,
       configuration.user_mig_oid_provider,
       configuration.user_mig_oidc_provider)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    title_entry['skipmenu'] = True
    # NOTE: keep empty header for narrow page layout
    header_entry = {'object_type': 'header', 'text':
                    # 'Welcome to the %s account sign up page' % \
                    # configuration.short_title
                    ''}
    output_objects.append(header_entry)

    # POST helpers for autocreate
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'autocreate'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    html = """
    <h2>Signup for %s</h2>
<p>
Before you can use this site you need a user account. You can sign up for one
here as described below.
</p>
""" % configuration.short_title
    if configuration.user_openid_providers and \
        ('extoid' in show or 'migoid' in show) or \
        configuration.user_openidconnect_providers and \
            ('extoidc' in show or 'migoidc' in show):
        html += """<h2>OpenID Login</h2>
<p>
The simplest sign up method is to use an existing OpenID 2.0 or OpenID Connect
login if you have one.
</p>
"""
        for method in show:
            if method == 'migoid':
                html += """
<p>
%(migoid_title)s users can sign up for an account with OpenID 2.0 access here.
</p>
<div id='migoid_status'>
<!-- OpenID 2.0 status updated by AJAX call -->
</div>
<div id='migoid_debug'>
<!-- OpenID 2.0 debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoid_url)s'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<!-- NOTE: we can't request field here as there is no account yet! -->
<input id='migoid_button' type='submit' value='%(migoid_title)s User OpenID 2.0 Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a registration page where
you need to enter your details to get both an OpenID account <em>and</em> an
account on %(short_title)s with that OpenID login associated.
</p>
"""
        for method in show:
            if method == 'migoidc':
                html += """
<p>
%(migoid_title)s users can sign up for an account with OpenID Connect access here.
</p>
<div id='migoidc_status'>
<!-- OpenID Connect status updated by AJAX call -->
</div>
<div id='migoidc_debug'>
<!-- OpenID Connect debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(migoidc_url)s'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<!-- NOTE: we can't request field here as there is no account yet! -->
<input id='migoidc_button' type='submit' value='%(migoid_title)s User OpenID Connect Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a registration page where
you need to enter your details to get both an OpenID Connect account <em>and</em> an
account on %(short_title)s with that OpenID Connect login associated.
</p>
"""
            if method == 'extoid':
                html += """
<p>
%(extoid_title)s users can sign up for an account here using their existing
OpenID 2.0 credentials.
</p>
<div id='extoid_status'>
<!-- OpenID 2.0 status updated by AJAX call -->
</div>
<div id='extoid_debug'>
<!-- OpenID 2.0 debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoid_url)s'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type='hidden' name='openid.ns' value='http://specs.openid.net/auth/2.0' />
<input type='hidden' name='openid.ns.sreg' value='http://openid.net/extensions/sreg/1.1' />
<input type='hidden' name='openid.sreg.required' value='nickname,fullname,email,o,ou,country,state,role' />
<input id='extoid_button' type='submit' value='%(extoid_title)s User OpenID 2.0 Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a login page where you
need to enter your credentials and accept that your identity is used for
%(short_title)s OpenID 2.0 login.
</p>
"""
            if method == 'extoidc':
                html += """
<p>
%(extoid_title)s users can sign up for an account here using their existing
OpenID Connect credentials.
</p>
<div id='extoidc_status'>
<!-- OpenID Connect status updated by AJAX call -->
</div>
<div id='extoidc_debug'>
<!-- OpenID Connect debug updated by AJAX call -->
</div>
<div class='form_container'>
<form method='post' action='%(extoidc_url)s'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input id='extoidc_button' type='submit' value='%(extoid_title)s User OpenID Connect Signup' />
</form>
</div>
<p>
When you click the Signup button you will be taken to a login page where you
need to enter your credentials and accept that your identity is used for
%(short_title)s OpenID Connect login.
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

    var_map = {'migoid_url': valid_show['migoid']['url'],
               'migoidc_url': valid_show['migoidc']['url'],
               'migoid_title': configuration.user_mig_oid_title,
               'extoid_url': valid_show['extoid']['url'],
               'extoidc_url': valid_show['extoidc']['url'],
               'extoid_title': configuration.user_ext_oid_title,
               'migcert_url': valid_show['migcert']['url'],
               'migcert_title': configuration.user_mig_cert_title,
               'extcert_url': valid_show['extcert']['url'],
               'extcert_title': configuration.user_ext_cert_title,
               'short_title': configuration.short_title}
    var_map.update(fill_helpers)
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    if set(configuration.site_signup_methods) != set(show):
        output_objects.append({'object_type': 'link',
                               'destination': 'signup.py',
                               'class': 'infolink iconspace',
                               'title': 'View all sign up methods',
                               'text': 'View all sign up methods'})
    return (output_objects, returnvalues.OK)
