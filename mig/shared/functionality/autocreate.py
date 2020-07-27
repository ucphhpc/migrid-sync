#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# autocreate - auto create user from signed certificate or openid login
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

# TODO: this backend is horribly KU/UCPH-specific, should move that to conf

"""Automatic sign up back end for external certificates and OpenID logins

   Also see req-/extcertaction.py
   Differences:
     - no e-mail sent: only auto-create functionality or nothing
     - automatic upload of a proxy certificate when provided
     - no special check for KU organisation
     - allows empty fields for things like country, email, and state
"""
from __future__ import absolute_import

import os
import time

from .shared import returnvalues
from .shared.base import client_id_dir, force_utf8, force_unicode, \
    fill_user, distinguished_name_to_user, fill_distinguished_name
from .shared.defaults import user_db_filename, cert_valid_days, \
    oid_valid_days
from .shared.fileio import write_file
from .shared.functional import validate_input, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit
from .shared.httpsclient import extract_client_openid
from .shared.init import initialize_main_variables
from .shared.notification import send_email
from .shared.safeinput import filter_commonname
from .shared.useradm import create_user
from .shared.url import openid_autologout_url

try:
    from .shared import arcwrapper
except Exception as exc:

    # Ignore errors and let it crash if ARC is enabled without the lib

    pass


def signature(login_type):
    """Signature of the main function"""

    if login_type == 'oid':
        defaults = {  # Please note that we only get sreg.required here if user is
                      # already logged in at OpenID provider when signing up so
                      # that we do not get the required attributes
            'openid.ns.sreg': [''],
            'openid.sreg.nickname': [''],
            'openid.sreg.fullname': [''],
            'openid.sreg.o': [''],
            'openid.sreg.ou': [''],
            'openid.sreg.timezone': [''],
            'openid.sreg.short_id': [''],
            'openid.sreg.full_name': [''],
            'openid.sreg.organization': [''],
            'openid.sreg.organizational_unit': [''],
            'openid.sreg.email': [''],
            'openid.sreg.country': ['DK'],
            'openid.sreg.state': [''],
            'openid.sreg.locality': [''],
            'openid.sreg.role': [''],
            'openid.sreg.association': [''],
            'openid.sreg.required': [''],
            'openid.ns': [''],
            'password': [''],
            'comment': ['(Signed up with OpenID and autocreate)'],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
            'authsig': ['']
        }
    elif login_type == 'cert':
        defaults = {
            'cert_id': REJECT_UNSET,
            'cert_name': REJECT_UNSET,
            'org': REJECT_UNSET,
            'email': [''],
            'country': [''],
            'state': [''],
            'role': [''],
            'association': [''],
            'comment': ['(Signed up with certificate and autocreate)'],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
        }
    else:
        raise ValueError('no such login_type: %s' % login_type)
    return ['text', defaults]


def handle_proxy(proxy_string, client_id, config):
    """If ARC-enabled server: store a proxy certificate.
       Arguments: proxy_string - text  extracted from given upload
                  client_id  - DN for user just being created
                  config     - global configuration
    """

    output = []
    client_dir = client_id_dir(client_id)
    proxy_dir = os.path.join(config.user_home, client_dir)
    proxy_path = os.path.join(config.user_home, client_dir,
                              arcwrapper.Ui.proxy_name)

    if not config.arc_clusters:
        output.append({'object_type': 'error_text',
                       'text': 'No ARC support!'})
        return output

    # store the file

    try:
        write_file(proxy_string, proxy_path, config.logger)
        os.chmod(proxy_path, 0o600)
    except Exception as exc:
        output.append({'object_type': 'error_text',
                       'text': 'Proxy file could not be written (%s)!'
                       % str(exc).replace(proxy_dir, '')})
        return output

    # provide information about the uploaded proxy

    try:
        session_ui = arcwrapper.Ui(proxy_dir)
        proxy = session_ui.getProxy()
        if proxy.IsExpired():

            # can rarely happen, constructor will throw exception

            output.append({'object_type': 'warning',
                           'text': 'Proxy certificate is expired.'})
        else:
            output.append({'object_type': 'text', 'text': 'Proxy for %s'
                           % proxy.GetIdentitySN()})
            output.append({'object_type': 'text',
                           'text': 'Proxy certificate will expire on %s (in %s sec.)'
                           % (proxy.Expires(), proxy.getTimeleft())})
    except arcwrapper.NoProxyError as err:

        output.append({'object_type': 'warning',
                       'text': 'No proxy certificate to load: %s'
                       % err.what()})
    return output


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=False)
    logger = configuration.logger
    logger.info('%s: args: %s' % (op_name, user_arguments_dict))
    prefilter_map = {}

    output_objects.append({'object_type': 'header',
                           'text': 'Automatic %s sign up'
                           % configuration.short_title})
    (_, identity) = extract_client_openid(configuration, environ,
                                          lookup_dn=False)
    req_url = environ['SCRIPT_URI']
    if client_id and client_id == identity:
        login_type = 'cert'
        if req_url.startswith(configuration.migserver_https_mig_cert_url):
            base_url = configuration.migserver_https_mig_cert_url
            login_flavor = 'migcert'
        elif req_url.startswith(configuration.migserver_https_ext_cert_url):
            base_url = configuration.migserver_https_ext_cert_url
            login_flavor = 'extcert'
        else:
            logger.warning('no match for cert request URL: %s'
                           % req_url)
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No matching request URL: %s'
                                   % req_url})
            return (output_objects, returnvalues.SYSTEM_ERROR)
    elif identity:
        login_type = 'oid'
        if req_url.startswith(configuration.migserver_https_mig_oid_url):
            base_url = configuration.migserver_https_mig_oid_url
            login_flavor = 'migoid'
        elif req_url.startswith(configuration.migserver_https_ext_oid_url):
            base_url = configuration.migserver_https_ext_oid_url
            login_flavor = 'extoid'
        else:
            logger.warning('no match for oid request URL: %s' % req_url)
            output_objects.append({'object_type': 'error_text',
                                   'text': 'No matching request URL: %s'
                                   % req_url})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        for name in ('openid.sreg.cn', 'openid.sreg.fullname',
                     'openid.sreg.full_name'):
            prefilter_map[name] = filter_commonname
    else:
        logger.error('autocreate without ID rejected for %s' % client_id)
        output_objects.append({'object_type': 'error_text',
                               'text': 'Missing user credentials'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    defaults = signature(login_type)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects, allow_rejects=False,
                                                 prefilter_map=prefilter_map)
    if not validate_status:
        logger.warning('%s from %s got invalid input: %s' %
                       (op_name, client_id, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.debug('Accepted arguments: %s' % accepted)
    # logger.debug('with environ: %s' % environ)

    admin_email = configuration.admin_email
    smtp_server = configuration.smtp_server
    (openid_names, oid_extras) = ([], {})
    tmp_id = 'tmp%s' % time.time()

    logger.info('Received autocreate from %s with ID %s' % (client_id, tmp_id))

    # Extract raw values

    if login_type == 'cert':
        uniq_id = accepted['cert_id'][-1].strip()
        raw_name = accepted['cert_name'][-1].strip()
        country = accepted['country'][-1].strip()
        state = accepted['state'][-1].strip()
        org = accepted['org'][-1].strip()
        org_unit = ''
        role = ','.join([i for i in accepted['role'] if i])
        association = ','.join([i for i in accepted['association']
                                if i])
        locality = ''
        timezone = ''
        email = accepted['email'][-1].strip()
        raw_login = None
    elif login_type == 'oid':
        uniq_id = accepted['openid.sreg.nickname'][-1].strip() \
            or accepted['openid.sreg.short_id'][-1].strip()
        raw_name = accepted['openid.sreg.fullname'][-1].strip() \
            or accepted['openid.sreg.full_name'][-1].strip()
        country = accepted['openid.sreg.country'][-1].strip()
        state = accepted['openid.sreg.state'][-1].strip()
        org = accepted['openid.sreg.o'][-1].strip() \
            or accepted['openid.sreg.organization'][-1].strip()
        org_unit = accepted['openid.sreg.ou'][-1].strip() \
            or accepted['openid.sreg.organizational_unit'][-1].strip()

        # We may receive multiple roles and associations

        role = ','.join([i for i in accepted['openid.sreg.role'] if i])
        association = ','.join([i for i in
                                accepted['openid.sreg.association']
                                if i])
        locality = accepted['openid.sreg.locality'][-1].strip()
        timezone = accepted['openid.sreg.timezone'][-1].strip()

        # We may encounter results without an email, fall back to uniq_id then

        email = accepted['openid.sreg.email'][-1].strip() or uniq_id

    # Fix case of values:
    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)
    # please note that we get utf8 coded bytes here and title() treats such
    # chars as word termination. Temporarily force to unicode.

    try:
        full_name = force_utf8(force_unicode(raw_name).title())
    except Exception:
        logger.warning('could not use unicode form to capitalize full name'
                       )
        full_name = raw_name.title()
    country = country.upper()
    state = state.upper()
    email = email.lower()

    if login_type == 'oid':

        # Remap some oid attributes if on KIT format with faculty in
        # organization and institute in organizational_unit. We can add them
        # as different fields as long as we make sure the x509 fields are
        # preserved.
        # Additionally in the special case with unknown institute (ou=ukendt)
        # we force organization to KU to align with cert policies.
        # We do that to allow autocreate updating existing cert users.

        if org_unit not in ('', 'NA'):
            org_unit = org_unit.upper()
            oid_extras['faculty'] = org
            oid_extras['institute'] = org_unit
            org = org_unit.upper()
            org_unit = 'NA'
            if org == 'UKENDT':
                org = 'KU'
                logger.info('unknown affilition, set organization to %s'
                            % org)

        # Stay on virtual host - extra useful while we test dual OpenID

        base_url = environ.get('REQUEST_URI', base_url).split('?')[0]
        backend = 'home.py'
        if configuration.site_enable_gdp:
            backend = 'gdpman.py'
        elif configuration.site_autolaunch_page:
            backend = os.path.basename(configuration.site_autolaunch_page)
        elif configuration.site_landing_page:
            backend = os.path.basename(configuration.site_landing_page)
        base_url = base_url.replace('autocreate.py', backend)

        raw_login = None
        for oid_provider in configuration.user_openid_providers:
            openid_prefix = oid_provider.rstrip('/') + '/'
            if identity.startswith(openid_prefix):
                raw_login = identity.replace(openid_prefix, '')
                break

    if raw_login:
        openid_names.append(raw_login)
        # TODO: Add additional ext oid provider ID aliases here?

    # we should have the proxy file read...

    proxy_content = accepted['proxy_upload'][-1]

    # keep comment to a single line

    comment = accepted['comment'][-1].replace('\n', '   ')

    # single quotes break command line format - remove

    comment = comment.replace("'", ' ')

    # TODO: improve and enforce full authsig from extoid provider
    authsig_list = accepted.get('authsig', [])
    # if len(authsig_list) != 1:
    #    logger.warning('%s from %s got invalid authsig: %s' %
    #                   (op_name, client_id, authsig_list))

    user_dict = {
        'short_id': uniq_id,
        'full_name': full_name,
        'organization': org,
        'organizational_unit': org_unit,
        'locality': locality,
        'state': state,
        'country': country,
        'email': email,
        'role': role,
        'association': association,
        'timezone': timezone,
        'password': '',
        'comment': '%s: %s' % ('Existing certificate', comment),
        'openid_names': openid_names,
    }
    user_dict.update(oid_extras)

    # We must receive some ID from the provider otherwise we probably hit the
    # already logged in situation and must autologout first

    if not uniq_id and not email:
        if accepted.get('openid.sreg.required', '') and identity:
            logger.warning('autocreate forcing autologut for %s' % client_id)
            output_objects.append({'object_type': 'html_form',
                                   'text': '''<p class="spinner iconleftpad">
Auto log out first to avoid sign up problems ...
</p>'''})
            html = \
                """
            <a id='autologout' href='%s'></a>
            <script type='text/javascript'>
                document.getElementById('autologout').click();
            </script>""" \
                % openid_autologout_url(configuration, identity,
                                        client_id, req_url, user_arguments_dict)
            output_objects.append({'object_type': 'html_form',
                                   'text': html})
        else:
            logger.warning('autocreate without ID refused for %s' % client_id)

        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: Unfortunately external OpenID redirect does not enforce POST
    # Extract helper environments from Apache to verify request authenticity

    redirector = environ.get('HTTP_REFERER', '')
    extoid_prefix = configuration.user_ext_oid_provider.replace('id/', '')
    # TODO: extend redirector check to match the full signup request?
    #       may not work with recent browser policy changes to limit referrer
    #       details on cross site requests.
    # NOTE: redirector check breaks for FF default policy so disabled again!
    if login_flavor == 'extoid' and redirector and \
            not redirector.startswith(extoid_prefix) and \
            not redirector.startswith(configuration.migserver_https_sid_url) \
            and not redirector.startswith(configuration.migserver_http_url):
        logger.error('stray extoid autocreate rejected for %r (ref: %r)' %
                     (client_id, redirector))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting authentic requests through %s OpenID''' %
                               configuration.user_ext_oid_title})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif login_flavor != 'extoid' and not safe_handler(
            configuration, 'post', op_name, client_id,
            get_csrf_limit(configuration), accepted):
        logger.error('unsafe autocreate rejected for %s' % client_id)
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting CSRF-filtered POST requests to prevent unintended updates'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    auth = 'unknown'
    if login_type == 'cert':
        auth = 'extcert'
        # TODO: consider limiting expire to real cert expire if before default?
        user_dict['expire'] = int(time.time() + cert_valid_days * 24
                                  * 60 * 60)
        try:
            distinguished_name_to_user(uniq_id)
            user_dict['distinguished_name'] = uniq_id
        except:
            logger.error('autocreate with bad DN refused for %s' % client_id)
            output_objects.append({'object_type': 'error_text',
                                   'text': '''Illegal Distinguished name:
Please note that the distinguished name must be a valid certificate DN with
multiple "key=val" fields separated by "/".
'''})
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif login_type == 'oid':
        auth = 'extoid'
        user_dict['expire'] = int(time.time() + oid_valid_days * 24
                                  * 60 * 60)
        fill_distinguished_name(user_dict)
        uniq_id = user_dict['distinguished_name']

    # IMPORTANT: do NOT let a user create with ID different from client_id
    if login_type == 'cert' and client_id != uniq_id:
        logger.error('refusing autocreate invalid user for %s: %s' %
                     (client_id, user_dict))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting create matching supplied ID!'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Save auth access method

    user_dict['auth'] = [auth]

    fill_helper = {'short_title': configuration.short_title,
                   'base_url': base_url, 'admin_email': admin_email,
                   'ext_oid_title': configuration.user_ext_oid_title,
                   'front_page_url': configuration.migserver_http_url,
                   'personal_page_url': configuration.migserver_https_ext_oid_url}
    fill_helper.update(user_dict)

    # If server allows automatic addition of users with a CA validated cert
    # we create the user immediately and skip mail

    if login_type == 'cert' and configuration.auto_add_cert_user \
            or login_type == 'oid' and configuration.auto_add_oid_user:
        fill_user(user_dict)

        logger.info('create user: %s' % user_dict)

        # Now all user fields are set and we can begin adding the user

        db_path = os.path.join(configuration.mig_server_home,
                               user_db_filename)
        try:
            create_user(user_dict, configuration.config_file, db_path,
                        ask_renew=False, default_renew=True)
            if configuration.site_enable_griddk \
                    and accepted['proxy_upload'] != ['']:

                # save the file, display expiration date

                proxy_out = handle_proxy(proxy_content, uniq_id,
                                         configuration)
                output_objects.extend(proxy_out)
        except Exception as err:
            logger.error('create failed for %s: %s' % (uniq_id, err))
            output_objects.append({'object_type': 'error_text',
                                   'text': '''Could not create the user account for you:
Please report this problem to the site administrators (%(admin_email)s).'''
                                   % fill_helper})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.info('created user account for %s' % uniq_id)

        email_header = 'Welcome to %s' % configuration.short_title
        email_msg = """Hi and welcome to %(short_title)s!

Your account sign up succeeded and you can now log in to your account using
your usual %(ext_oid_title)s login from
%(front_page_url)s
There you'll also find further information about making the most of
%(short_title)s, including a user guide and answers to Frequently Asked
Questions, plus site status and support information.
You're welcome to contact us with questions or comments using the contact
details there and in the footer of your personal %(short_title)s pages.

Please note that by signing up and using %(short_title)s you also formally
accept the site Terms of Use, which you'll always find in the current form at
%(front_page_url)s/terms.html

All the best,
The %(short_title)s Admins
""" % fill_helper

        logger.info('Send email: to: %s, header: %s, msg: %s, smtp_server: %s'
                    % (email, email_header, email_msg, smtp_server))
        if not send_email(email, email_header, email_msg, logger,
                          configuration):
            output_objects.append({
                'object_type': 'error_text', 'text': """An error occured trying
to send your account welcome email. Please inform the site admins (%s) manually
and include the session ID: %s""" % (admin_email, tmp_id)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.info('sent welcome email for %s to %s' % (uniq_id, email))

        output_objects.append({'object_type': 'html_form', 'text': """
<p> Creating your %(short_title)s user account and sending welcome email ... </p>
<p class='spinner iconleftpad'>
redirecting to your <a href='%(personal_page_url)s'> personal pages </a> in a
moment.
</p>
<script type='text/javascript'>
    setTimeout(function() {location.href='%(personal_page_url)s';}, 3000);
</script>
""" % fill_helper})
        return (output_objects, returnvalues.OK)

    else:
        logger.warning('autocreate disabled and refused for %s' % client_id)
        output_objects.append({
            'object_type': 'error_text', 'text': """Automatic user creation
disabled on this site. Please contact the site admins (%(admin_email)s) if you
think it should be enabled.
""" % fill_helper})
        return (output_objects, returnvalues.ERROR)
