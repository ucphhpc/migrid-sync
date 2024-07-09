#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# autocreate - auto create user from signed certificate or openid login
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

# TODO: this backend is horribly KU/UCPH-specific, should move that to conf

"""Automatic sign up back end for external certificates, OpenID 2.0 and
OpenID Connect logins.

   Also see req-/extcertaction.py
   Differences:
     - automatic upload of a proxy certificate when provided
     - no special check for KU organization
     - allows empty fields for things like country, email, and state
"""

from __future__ import absolute_import

import base64
import os
import time

from mig.shared import returnvalues
from mig.shared.accountreq import auto_add_user_allowed
from mig.shared.accountstate import default_account_expire
from mig.shared.bailout import filter_output_objects
from mig.shared.base import client_id_dir, canonical_user, mask_creds, \
    fill_user, distinguished_name_to_user, fill_distinguished_name, \
    get_site_base_url, requested_page
from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT, AUTH_MIG_CERT, AUTH_EXT_CERT, AUTH_MIG_OID, \
    AUTH_EXT_OID, AUTH_MIG_OIDC, AUTH_EXT_OIDC, keyword_auto
from mig.shared.fileio import write_file
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.httpsclient import extract_client_id, detect_client_auth, \
    build_autologout_url
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.notification import send_email
from mig.shared.safeinput import filter_commonname
from mig.shared.useradm import create_user
from mig.shared.userdb import default_db_path
from mig.shared.validstring import is_valid_email_address

try:
    from mig.shared import arcwrapper
except Exception as exc:

    # Ignore errors and let it crash if ARC is enabled without the lib

    pass


def signature(configuration, auth_type):
    """Signature of the main function"""

    if auth_type == AUTH_OPENID_V2:
        # Please note that we only get sreg.required here if user is
        # already logged in at OpenID provider when signing up so
        # that we do not get the required attributes
        defaults = {
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
            'openid.sreg.roles': [''],
            'openid.sreg.association': [''],
            'openid.sreg.required': [''],
            'openid.ns': [''],
            'password': [''],
            'comment': [''],
            'accept_terms': [''],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
            'authsig': ['']
        }
    elif auth_type == AUTH_CERTIFICATE:
        # We end up here from extcert if conf allows auto creation
        # TODO: switch to add fields from cert_field_order in shared.defaults
        defaults = {
            'cert_id': REJECT_UNSET,
            'cert_name': [''],
            'org': [''],
            'email': [''],
            'country': [''],
            'state': [''],
            # NOTE: do NOT enable unvalidated role or association here
            # 'role': [''],
            # 'association': [''],
            'comment': [''],
            'accept_terms': [''],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
        }
        if configuration.site_enable_peers:
            if configuration.site_peers_mandatory:
                peers_default = REJECT_UNSET
            else:
                peers_default = ['']
            for field_name in configuration.site_peers_explicit_fields:
                defaults['peers_%s' % field_name] = peers_default
    elif auth_type == AUTH_OPENID_CONNECT:
        # IMPORTANT: consistently lowercase to avoid case sensitive validation
        # NOTE: at least one of sub, oid or upn should be set - check later
        defaults = {
            'oidc.claim.sub': [''],
            'oidc.claim.oid': [''],
            'oidc.claim.upn': [''],
            'oidc.claim.iss': REJECT_UNSET,
            'oidc.claim.aud': REJECT_UNSET,
            'oidc.claim.nickname': [''],
            'oidc.claim.fullname': [''],
            'oidc.claim.name': [''],
            'oidc.claim.o': [''],
            'oidc.claim.ou': [''],
            'oidc.claim.organization': [''],
            'oidc.claim.organizational_unit': [''],
            'oidc.claim.timezone': [''],
            'oidc.claim.email': [''],
            'oidc.claim.country': [''],
            'oidc.claim.state': [''],
            'oidc.claim.locality': [''],
            'oidc.claim.role': [''],
            'oidc.claim.roles': [''],
            'oidc.claim.association': [''],
            'comment': [''],
            'accept_terms': [''],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
        }
    else:
        raise ValueError('no such auth_type: %s' % auth_type)
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
                       % ("%s" % exc).replace(proxy_dir, '')})
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


def split_comma_concat(value_list, sep=','):
    """Take a list of values and adjust it so that any values with given sep
    inside is expanded to the individual values without the separator.
    I.e. the list ['abc,def'] is transformed into ['abc', 'def'].
    """
    result = []
    for val in value_list:
        parts = val.split(sep)
        result += parts
    return result


def lookup_filter_illegal_handler(filter_method):
    """Get the illegal handler function to match filter_method. The output is
    directly suitable for the filter_X helpers with illegal_handler argument.
    """
    # NOTE: the None value is a special case that means skip illegal values
    if filter_method in ('', 'skip'):
        return None
    elif filter_method == 'hexlify':
        def hex_wrap(val):
            """Insert a clearly marked hex representation of val"""
            # NOTE: use '.X' as '.x' will typically be capitalized in use anyway
            return ".X%s" % base64.b16encode(val)
        return hex_wrap
    else:
        raise ValueError("unsupported filter_method: %r" % filter_method)


def populate_prefilters(configuration, prefilter_map, auth_type):
    """Populate the prefilter map applied to input values before anything else
    so that they can be used e.g. to mangle illegal values into compliance.
    Particularly useful for making sure we keep file system names to something
    we can actually safely handle.
    """
    _logger = configuration.logger
    _logger.debug("populate prefilters for %s" % auth_type)
    # TODO: add better reversible filters like punycode or base64 on whole name
    filter_name = configuration.auto_add_filter_method
    illegal_handler = lookup_filter_illegal_handler(filter_name)
    _logger.debug("populate prefilters found filter illegal char handler %s" %
                  illegal_handler)
    if auth_type == AUTH_OPENID_V2:
        if filter_name and 'full_name' in configuration.auto_add_filter_fields:
            def _filter_helper(x):
                return filter_commonname(x, illegal_handler)
            # NOTE: KUIT OpenID 2.0 provides full name as 'fullname'
            for name in ('openid.sreg.fullname', 'openid.sreg.full_name'):
                prefilter_map[name] = _filter_helper
    elif auth_type == AUTH_OPENID_CONNECT:
        if configuration.auto_add_filter_method and \
                'full_name' in configuration.auto_add_filter_fields:
            def _filter_helper(x):
                return filter_commonname(x, illegal_handler)
            # NOTE: WAYF provides full name as 'name'
            for name in ('oidc.claim.fullname', 'oidc.claim.full_name',
                         'oidc.claim.name'):
                prefilter_map[name] = _filter_helper
    elif auth_type == AUTH_CERTIFICATE:
        if configuration.auto_add_filter_method and \
                'full_name' in configuration.auto_add_filter_fields:
            def _filter_helper(x):
                return filter_commonname(x, illegal_handler)
            for name in ('cert_name', ):
                prefilter_map[name] = _filter_helper
    else:
        raise ValueError("unsupported auth_type in populate_prefilters: %r" %
                         auth_type)
    _logger.debug("populate prefilters returns: %s" % prefilter_map)
    return prefilter_map


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=False)
    logger = configuration.logger
    prefilter_map = {}

    output_objects.append({'object_type': 'header',
                           'text': 'Automatic %s sign up'
                           % configuration.short_title})
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    identity = extract_client_id(configuration, environ, lookup_dn=False)
    if client_id and auth_type == AUTH_CERTIFICATE:
        if auth_flavor == AUTH_MIG_CERT:
            base_url = configuration.migserver_https_mig_cert_url
        elif auth_flavor == AUTH_EXT_CERT:
            base_url = configuration.migserver_https_ext_cert_url
        else:
            logger.warning('no matching sign up auth flavor %s' % auth_flavor)
            output_objects.append({'object_type': 'error_text', 'text':
                                   '%s sign up not supported' % auth_flavor})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        # NOTE: simple filters to handle unsupported chars e.g. in full name
        populate_prefilters(configuration, prefilter_map, auth_type)
    elif identity and auth_type == AUTH_OPENID_V2:
        if auth_flavor == AUTH_MIG_OID:
            base_url = configuration.migserver_https_mig_oid_url
        elif auth_flavor == AUTH_EXT_OID:
            base_url = configuration.migserver_https_ext_oid_url
        else:
            logger.warning('no matching sign up auth flavor %s' % auth_flavor)
            output_objects.append({'object_type': 'error_text', 'text':
                                   '%s sign up not supported' % auth_flavor})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        # NOTE: simple filters to handle unsupported chars e.g. in full name
        populate_prefilters(configuration, prefilter_map, auth_type)
    elif identity and auth_type == AUTH_OPENID_CONNECT:
        if auth_flavor == AUTH_MIG_OIDC:
            base_url = configuration.migserver_https_mig_oidc_url
        elif auth_flavor == AUTH_EXT_OIDC:
            base_url = configuration.migserver_https_ext_oidc_url
        else:
            logger.warning('no matching sign up auth flavor %s' % auth_flavor)
            output_objects.append({'object_type': 'error_text', 'text':
                                   '%s sign up not supported' % auth_flavor})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        oidc_keys = list(signature(configuration, AUTH_OPENID_CONNECT)[1])
        # NOTE: again we lowercase to avoid case sensitivity in validation
        for key in environ:
            low_key = key.replace('OIDC_CLAIM_', 'oidc.claim.').lower()
            if low_key in oidc_keys:
                user_arguments_dict[low_key] = [environ[key]]
        # NOTE: simple filters to handle unsupported chars e.g. in full name
        populate_prefilters(configuration, prefilter_map, auth_type)
    else:
        logger.error('autocreate without ID rejected for %s' % client_id)
        output_objects.append({'object_type': 'error_text',
                               'text': 'Missing user credentials'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    defaults = signature(configuration, auth_type)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
                                                 defaults, output_objects,
                                                 allow_rejects=False,
                                                 prefilter_map=prefilter_map)
    if not validate_status:
        # NOTE: 'accepted' is a non-sensitive error string here
        logger.warning('%s from %s got invalid input: %s' %
                       (op_name, client_id,
                        filter_output_objects(configuration, accepted)))
        return (accepted, returnvalues.CLIENT_ERROR)

    # IMPORTANT: do NOT log credentials
    logger.debug('Accepted arguments: %s' % mask_creds(accepted))
    # logger.debug('with environ: %s' % environ)

    support_email = configuration.support_email
    smtp_server = configuration.smtp_server
    (openid_names, oid_extras, peers_extras) = ([], {}, {})
    peer_pattern = None
    tmp_id = 'tmp%s' % time.time()

    logger.info('Received autocreate from %s with ID %s' % (client_id, tmp_id))

    # Extract raw values

    if auth_type == AUTH_CERTIFICATE:
        main_id = accepted['cert_id'][-1].strip()
        # TODO: consider switching short_id to email?
        short_id = main_id
        full_name = accepted['cert_name'][-1].strip()
        country = accepted['country'][-1].strip()
        state = accepted['state'][-1].strip()
        org = accepted['org'][-1].strip()
        org_unit = ''
        # NOTE: leave role and association alone here
        role = ''
        association = ''
        locality = ''
        timezone = ''
        email = accepted['email'][-1].strip()
        if configuration.site_enable_peers:
            # Peers are passed as multiple strings of comma or space separated emails
            # so we reformat to a consistently comma+space separated string.
            peers_full_name_list = []
            for entry in accepted.get('peers_full_name', ['']):
                peers_full_name_list += [i.strip() for i in entry.split(',')]
            peers_full_name = ', '.join(peers_full_name_list)
            peers_email_list = []
            for entry in accepted.get('peers_email', ['']):
                peers_email_list += [i.strip() for i in entry.split(',')]
            peers_email = ', '.join(peers_email_list)
            peers_extras['peers_full_name'] = peers_full_name
            peers_extras['peers_email'] = peers_email
            peer_pattern = keyword_auto
    elif auth_type == AUTH_OPENID_V2:
        # No guaranteed unique ID from OpenID 2.0 - mirror main and short
        main_id = accepted['openid.sreg.nickname'][-1].strip() \
            or accepted['openid.sreg.short_id'][-1].strip()
        short_id = main_id
        full_name = accepted['openid.sreg.fullname'][-1].strip() \
            or accepted['openid.sreg.full_name'][-1].strip()
        country = accepted['openid.sreg.country'][-1].strip()
        state = accepted['openid.sreg.state'][-1].strip()
        org = accepted['openid.sreg.o'][-1].strip() \
            or accepted['openid.sreg.organization'][-1].strip()
        org_unit = accepted['openid.sreg.ou'][-1].strip() \
            or accepted['openid.sreg.organizational_unit'][-1].strip()

        # We may receive multiple roles and associations

        merged = accepted['openid.sreg.role'] + accepted['openid.sreg.roles']
        role = ','.join([i for i in merged if i])
        association = ','.join([i for i in
                                accepted['openid.sreg.association']
                                if i])
        locality = accepted['openid.sreg.locality'][-1].strip()
        timezone = accepted['openid.sreg.timezone'][-1].strip()
        email = accepted['openid.sreg.email'][-1].strip()
    elif auth_type == AUTH_OPENID_CONNECT:
        # OpenID Connect identity advice recommends sub or oid as unique
        main_id = accepted['oidc.claim.sub'][-1].strip() \
            or accepted['oidc.claim.oid'][-1].strip()
        # NOTE: UCPH provides common abc123@ku.dk username in upn
        short_id = accepted['oidc.claim.upn'][-1].strip()
        full_name = accepted['oidc.claim.fullname'][-1].strip() \
            or accepted['oidc.claim.name'][-1].strip()
        country = accepted['oidc.claim.country'][-1].strip()
        state = accepted['oidc.claim.state'][-1].strip()
        org = accepted['oidc.claim.o'][-1].strip() \
            or accepted['oidc.claim.organization'][-1].strip()
        org_unit = accepted['oidc.claim.ou'][-1].strip() \
            or accepted['oidc.claim.organizational_unit'][-1].strip()
        token_issuer = accepted['oidc.claim.iss'][-1].strip()
        token_audience = accepted['oidc.claim.aud'][-1].strip()

        # We may receive multiple roles and associations

        merged = accepted['oidc.claim.role'] + accepted['oidc.claim.roles']
        role = ','.join([i for i in merged if i])
        association = ','.join([i for i in
                                accepted['oidc.claim.association']
                                if i])
        locality = accepted['oidc.claim.locality'][-1].strip()
        timezone = accepted['oidc.claim.timezone'][-1].strip()
        # NOTE: some OIDC providers may comma-separate values concatenated
        #       translate to individual args instead in that case. E.g. as in
        #       'john@doe.org,jd@doe.org' -> ['john@doe.org', 'jd@doe.org']
        email = split_comma_concat(accepted['oidc.claim.email'])[-1].strip()

    # We may encounter results without an email, fall back to try plain IDs then
    if not email:
        if is_valid_email_address(short_id, logger):
            email = short_id
        elif is_valid_email_address(main_id, logger):
            email = main_id

    accept_terms = (accepted['accept_terms'][-1].strip().lower() in
                    ('1', 'o', 'y', 't', 'on', 'yes', 'true'))

    if auth_type in (AUTH_OPENID_V2, AUTH_OPENID_CONNECT):

        # KU OpenID sign up does not deliver accept_terms so we implicitly
        # let it imply acceptance for now
        accept_terms = True

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

        base_url = requested_page(environ, fallback='/')
        backend = 'home.py'
        if configuration.site_enable_gdp:
            backend = 'gdpman.py'
        elif configuration.site_autolaunch_page:
            backend = os.path.basename(configuration.site_autolaunch_page)
        elif configuration.site_landing_page:
            backend = os.path.basename(configuration.site_landing_page)
        base_url = base_url.replace('autocreate.py', backend)

        raw_login = ''
        if auth_type == AUTH_OPENID_V2:
            # OpenID 2.0 provides user ID on URL format - only add plain ID
            for oid_provider in configuration.user_openid_providers:
                openid_prefix = oid_provider.rstrip('/') + '/'
                if identity.startswith(openid_prefix):
                    raw_login = identity.replace(openid_prefix, '')
                    break
        elif auth_type == AUTH_OPENID_CONNECT:
            raw_login = identity

        if raw_login and not raw_login in openid_names:
            openid_names.append(raw_login)
        if email and not email in openid_names:
            openid_names.append(email)
        # TODO: Add additional ext oid/oidc provider ID aliases here?

    # we should have the proxy file read...

    proxy_content = accepted['proxy_upload'][-1]

    # keep comment to a single line

    comment = accepted['comment'][-1].replace('\n', '   ')

    # single quotes break command line format - remove

    comment = comment.replace("'", ' ')

    # TODO: improve and enforce full authsig from extoid/extoidc provider
    authsig_list = accepted.get('authsig', [])
    # if len(authsig_list) != 1:
    #    logger.warning('%s from %s got invalid authsig: %s' %
    #                   (op_name, client_id, authsig_list))

    raw_user = {
        'main_id': main_id,
        'short_id': short_id,
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
        'comment': 'Signed up through autocreate with %s' % auth_type,
        'openid_names': openid_names,
    }
    raw_user.update(oid_extras)
    raw_user.update(peers_extras)
    # Force user ID fields to canonical form for consistency
    # Title name, lowercase email, uppercase country and state, etc.
    user_dict = canonical_user(configuration, raw_user, raw_user.keys())

    # We must receive some ID from the provider otherwise we probably hit the
    # already logged in situation and must autologout first

    if not short_id and not email:
        if auth_type == AUTH_OPENID_V2 and identity and \
                accepted.get('openid.sreg.required', ''):
            logger.warning('autocreate forcing autologut for %s' % client_id)
            output_objects.append({'object_type': 'html_form',
                                   'text': '''<p class="spinner iconleftpad">
Auto log out first to avoid sign up problems ...
</p>'''})
            autologout_url = build_autologout_url(configuration,
                                                  environ,
                                                  client_id,
                                                  requested_page(environ),
                                                  user_arguments_dict)
            title_entry = find_entry(output_objects, 'title')
            title_entry['meta'] = """<meta http-equiv = "refresh" content = "0; url=%s" />""" \
                % autologout_url
        else:
            logger.warning('%s autocreate without ID refused for %s' %
                           (auth_type, client_id))

        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: Unfortunately external OpenID 2.0 redirect does not enforce POST
    # Extract helper environments from Apache to verify request authenticity

    redirector = environ.get('HTTP_REFERER', '')
    extoid_prefix = configuration.user_ext_oid_provider.replace('id/', '')
    # TODO: extend redirector check to match the full signup request?
    #       may not work with recent browser policy changes to limit referrer
    #       details on cross site requests.
    # NOTE: FF now defaults to a no-referrer policy so disable if empty!
    if auth_flavor == AUTH_EXT_OID and redirector and not \
        (redirector.startswith(extoid_prefix) or
         redirector.startswith(configuration.migserver_https_sid_url) or
         redirector.startswith(configuration.migserver_http_url) or
         redirector.startswith(configuration.migserver_https_url) or
         redirector.startswith(configuration.migserver_public_url) or
         redirector.startswith(configuration.migserver_public_alias_url) or
         redirector.startswith(get_site_base_url(configuration))):
        logger.error('stray %s autocreate rejected for %r (ref: %r)' %
                     (auth_flavor, client_id, redirector))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting authentic requests through %s OpenID 2.0''' %
                               configuration.user_ext_oid_title})
        return (output_objects, returnvalues.CLIENT_ERROR)
    # NOTE: implicit openid connect claim signature
    #       manually check correct issuer and audience to verify claim trust
    elif auth_flavor == AUTH_EXT_OIDC and \
        (configuration.user_ext_oidc_audience != token_audience or
         configuration.user_ext_oidc_issuer != token_issuer):
        logger.error('stray %s autocreate rejected for %r (%r@%r vs %r@%r)' %
                     (auth_flavor, client_id, token_audience, token_issuer,
                      configuration.user_ext_oidc_audience,
                      configuration.user_ext_oidc_issuer))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting authentic requests through %s OpenID Connect''' %
                               configuration.user_ext_oidc_title})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif auth_flavor not in [AUTH_EXT_OID, AUTH_EXT_OIDC] and not safe_handler(
            configuration, 'post', op_name, client_id,
            get_csrf_limit(configuration), accepted):
        logger.error('unsafe %s autocreate rejected for %s' % (auth_flavor,
                                                               client_id))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting CSRF-filtered POST requests to prevent unintended updates'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if auth_flavor == AUTH_EXT_CERT:
        ext_login_title = "%s certificate" % configuration.user_ext_cert_title
        personal_page_url = configuration.migserver_https_ext_cert_url
        # TODO: consider limiting expire to real cert expire if before default?
        user_dict['expire'] = default_account_expire(configuration,
                                                     AUTH_CERTIFICATE)
        try:
            distinguished_name_to_user(main_id)
            user_dict['distinguished_name'] = main_id
        except:
            logger.error('%s autocreate with bad DN refused for %s' %
                         (auth_flavor, client_id))
            output_objects.append({'object_type': 'error_text',
                                   'text': '''Illegal Distinguished name:
Please note that the distinguished name must be a valid certificate DN with
multiple "key=val" fields separated by "/".
'''})
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif auth_flavor == AUTH_EXT_OID:
        ext_login_title = "%s login" % configuration.user_ext_oid_title
        personal_page_url = configuration.migserver_https_ext_oid_url
        user_dict['expire'] = default_account_expire(configuration,
                                                     AUTH_OPENID_V2)
        fill_distinguished_name(user_dict)
    elif auth_flavor == AUTH_EXT_OIDC:
        ext_login_title = "%s login" % configuration.user_ext_oidc_title
        personal_page_url = configuration.migserver_https_ext_oidc_url
        user_dict['expire'] = default_account_expire(configuration,
                                                     AUTH_OPENID_CONNECT)
        fill_distinguished_name(user_dict)
    else:
        # Reject the migX sign up methods through this handler
        logger.error('%s autocreate not supported for %s - only ext auth' %
                     (auth_flavor, client_id))
        output_objects.append({'object_type': 'error_text', 'text': '''
Unsuported %s sign up method - you should sign up through the official
sign up wrappers or go through the dedicated web form for %s.''' %
                               (auth_type, auth_flavor)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_id = user_dict['distinguished_name']

    # IMPORTANT: do NOT let a user create with ID different from client_id
    if auth_type == AUTH_CERTIFICATE and client_id != user_id:
        # IMPORTANT: do NOT log credentials
        logger.error('refusing autocreate invalid user for %s: %s' %
                     (client_id, mask_creds(user_dict)))
        output_objects.append({'object_type': 'error_text', 'text': '''Only
accepting create matching supplied ID!'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not accept_terms:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must accept the terms of use in sign up!'})
        output_objects.append(
            {'object_type': 'link', 'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "Try again"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Save auth access method

    user_dict['auth'] = user_dict.get('auth', None)
    if not user_dict['auth']:
        user_dict['auth'] = []
    elif isinstance(user_dict['auth'], basestring):
        user_dict['auth'] = [user_dict['auth']]
    user_dict['auth'].append(auth_flavor)

    fill_helper = {'short_title': configuration.short_title,
                   'base_url': base_url, 'support_email': support_email,
                   'ext_login_title': ext_login_title,
                   'front_page_url': get_site_base_url(configuration),
                   'personal_page_url': personal_page_url}
    fill_helper.update(user_dict)

    # If server allows automatic addition of users with a CA validated cert
    # we create the user immediately and skip mail

    if auth_type == AUTH_CERTIFICATE and configuration.auto_add_cert_user \
            or auth_type == AUTH_OPENID_V2 and \
            configuration.auto_add_oid_user \
            or auth_type == AUTH_OPENID_CONNECT and \
            configuration.auto_add_oidc_user:
        fill_user(user_dict)

        if not auto_add_user_allowed(configuration, user_dict):
            logger.warning('autocreate not permitted for %s' % client_id)
            output_objects.append({
                'object_type': 'error_text', 'text':
                """Your credentials do not fit the automatic account sign up
criteria permitted on this site.
Please contact the %(short_title)s support (%(support_email)s) if you think it
should be enabled.""" % fill_helper})
            return (output_objects, returnvalues.ERROR)

        # IMPORTANT: do NOT log credentials
        logger.info('create user: %s' % mask_creds(user_dict))

        # Now all user fields are set and we can begin adding the user

        db_path = default_db_path(configuration)
        try:
            create_user(user_dict, configuration.config_file, db_path,
                        ask_renew=False, default_renew=True,
                        verify_peer=peer_pattern)
            if configuration.site_enable_griddk \
                    and accepted['proxy_upload'] != ['']:

                # save the file, display expiration date

                proxy_out = handle_proxy(proxy_content, user_id,
                                         configuration)
                output_objects.extend(proxy_out)
        except Exception as err:
            logger.error('create failed for %s: %s' % (user_id, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   """Could not create the user account for you:
Please report this problem to %(short_title)s site support (%(support_email)s).
""" % fill_helper})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.info('created user account for %s' % user_id)

        email_header = 'Welcome to %s' % configuration.short_title
        email_msg = """Hi and welcome to %(short_title)s!

Your account sign up succeeded and you can now log in to your account using
your %(ext_login_title)s from
%(front_page_url)s
There you'll also find further information about making the most of
%(short_title)s, including various guides and answers to Frequently Asked
Questions, along with site status and support information.
You're welcome to contact our support on %(support_email)s with
questions or comments. You may also find further support details on the above
page or on your personal %(short_title)s pages.

Please note that by signing up and using %(short_title)s you also formally
accept the site Terms of Use, which you'll always find in the current form at
%(front_page_url)s/terms.html

All the best,
The %(short_title)s Admins
""" % fill_helper

        logger.info('Send email: to: %s, header: %s, smtp_server: %s'
                    % (email, email_header, smtp_server))
        logger.debug('email body:  %s' % email_msg)
        if not send_email(email, email_header, email_msg, logger,
                          configuration):
            output_objects.append({
                'object_type': 'error_text', 'text': """An error occurred trying
to send your account welcome email. Please contact support (%s) and include the
session ID: %s""" % (support_email, tmp_id)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.info('sent welcome email for %s to %s' % (user_id, email))

        output_objects.append({'object_type': 'html_form', 'text': """
<p>Creating your %(short_title)s user account and sending welcome email ... </p>
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
            'object_type': 'error_text', 'text':
            """Automatic user creation disabled on this site.
Please contact the %(short_title)s support (%(support_email)s) if you think it
should be enabled.""" % fill_helper})
        return (output_objects, returnvalues.ERROR)
