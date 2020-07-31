#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oidresponse - general openid response handler backend
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

"""Back end to handle mainly unexpected error reponses from OpenID services
during signup or login.

It can be used as the target for OpenID handling such OpenID responses by
setting the AuthOpenIDLoginPage variable in Apache like:
AuthOpenIDLoginPage https://${SID_FQDN}:${SID_PORT}/cgi-sid/oidresponse.py
"""
from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.url import openid_basic_logout_url


def signature(configuration):
    """Signature of the main function"""

    defaults = {'modauthopenid.error': REJECT_UNSET,
                'modauthopenid.referrer': [''],
                'redirect_url': ['']}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    defaults = signature(configuration)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    openid_error = ', '.join(accepted['modauthopenid.error'])
    openid_referrer = accepted['modauthopenid.referrer'][-1]
    # OpenID server errors may return here with redirect url set
    redirect_url = accepted['redirect_url'][-1]

    main_url = os.path.join(configuration.migserver_https_sid_url, 'public/')

    client_addr = environ.get('REMOTE_ADDR', '0.0.0.0')
    client_refer = environ.get('HTTP_REFERER', '')

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s OpenID Response Handler' % configuration.short_title
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>
    '''
    add_init = '''
        function delayed_redirect(redir_url, redirmsg_select) {
            setTimeout(function() {
                           $(redirmsg_select).fadeIn(5000);
                       }, 5000);
            setTimeout(function() {
                           location.href=redir_url;
                       }, 15000);
        }
    '''
    add_ready = '''
        var action = "login", oid_title, oid_url, tag_prefix;
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
    # NOTE: keep empty header for narrow page layout
    header_entry = {'object_type': 'header', 'text': ''}
    output_objects.append(header_entry)

    logger.info('oidresponse for %r at %s from %r: %s' % (client_id, client_addr,
                                                          openid_referrer,
                                                          openid_error))
    html = ""
    add_action = '''
<p class="fadein_msg spinner iconspace hidden">
Redirecting to main page in a moment ...
</p>

<script type="text/javascript">
    delayed_redirect("%s", ".fadein_msg");
</script>
''' % main_url
    err_txt, report_txt = '', ''
    report_fail = """, so you cannot currently use it for authentication to %s.
<br />
Please report the problem to your OpenID identity provider if it persists.
""" % configuration.short_title
    if redirect_url:
        report_fail += """<br />The error happened on access to %s ."""  \
            % redirect_url

    if 'no_idp_found' in openid_error:
        err_txt += "OpenID server did not respond!"
        report_txt += """It appears the requested OpenID authentication service
is offline""" + report_fail
    elif 'canceled' in openid_error:
        # Sign up requests after login end here and may need autologout
        if openid_referrer.find('/autocreate.py') != -1:
            logger.info('oidresponse force autologut for %r at %s from %r' %
                        (client_id, client_addr, openid_referrer))
            logger.debug('oidresponse env: %s' % environ)
            err_txt += "OpenID sign up reached an inconsistent login state"
            report_txt += """Sign up to %s only works if you are <em>not</em>
already logged in to the OpenID service.
""" % configuration.short_title
            identity = environ.get('REMOTE_USER', None)
            # NOTE: for cgi-sid we don't have the oid username so use a dummy
            if not identity:
                if configuration.user_mig_oid_provider and \
                        openid_referrer.startswith(
                            configuration.migserver_https_mig_oid_url):
                    identity = configuration.user_mig_oid_provider
                    identity = os.path.join(identity, client_id)
                elif configuration.user_ext_oid_provider and \
                        openid_referrer.startswith(
                            configuration.migserver_https_ext_oid_url):
                    identity = configuration.user_ext_oid_provider
                    identity = os.path.join(identity, client_id)
                else:
                    logger.error(
                        'oidresponse from unexpected ref: %s' % client_refer)

            if identity:
                autologout_url = openid_basic_logout_url(configuration,
                                                         identity,
                                                         main_url)
                add_action = '''
            <p class="fadein_msg spinner iconspace hidden">
            Redirecting through auto-logout to clean up for your next %s sign
            up attempt ...
            </p>
            <script type="text/javascript">
                delayed_redirect("%s", ".fadein_msg");
            </script>
            ''' % (configuration.short_title, autologout_url)

            logger.info('oidresponse for %r at %s from %r with action: %s' %
                        (client_id, client_addr, openid_referrer, add_action))
        else:
            err_txt += "OpenID login canceled!"
            report_txt += """You have to either enter your OpenID login and
accept that it is used for %s login or choose another login method.
""" % configuration.short_title

    else:
        err_txt += "OpenID server error!"
        report_txt += """It appears there's a problem with the requested
OpenID authentication service""" + report_fail

    html += """<h2>OpenID Service Reported an Error</h2>
<div class='errortext'>
%s (error code(s): %s)
</div>
<div class='warningtext'>
%s
</div>
""" % (err_txt, openid_error, report_txt)
    var_map = {'migoid_url': configuration.migserver_https_mig_oid_url,
               'migoid_title': configuration.user_mig_oid_title,
               'extoid_url': configuration.migserver_https_ext_oid_url,
               'extoid_title': configuration.user_ext_oid_title,
               'migcert_url': configuration.migserver_https_mig_cert_url,
               'migcert_title': configuration.user_mig_cert_title,
               'extcert_url': configuration.migserver_https_ext_cert_url,
               'extcert_title': configuration.user_ext_cert_title,
               'short_title': configuration.short_title}
    output_objects.append({'object_type': 'html_form', 'text': html % var_map})
    if add_action:
        output_objects.append({'object_type': 'html_form',
                               'text': add_action})

    return (output_objects, returnvalues.OK)
