#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# autocreate - auto create user from signed certificate or openid login
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

"""Automatic sign up back end for external certificates and OpenID logins

   Also see req-/extcertaction.py. Differences: 
     - no e-mail sent: only auto-create functionality or nothing
     - automatic upload of a proxy certificate when provided
     - no special check for KU organisation
     - allows empty fields for things like country, email, and state
"""

import os
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import cert_valid_days, oid_valid_days
from shared.fileio import write_file
from shared.functional import validate_input, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.useradm import db_name, distinguished_name_to_user, \
     create_user, fill_user, fill_distinguished_name
try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

def signature(login_type):
    """Signature of the main function"""

    if login_type == 'oid':
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
            'password': [''],
            'comment': ['(Created through autocreate)'],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
            }
    elif login_type == 'cert':
        defaults = {
            'cert_id': REJECT_UNSET,
            'cert_name': REJECT_UNSET,
            'org': REJECT_UNSET,
            'email': [''],
            'country': [''],
            'state': [''],
            'comment': ['(Created through autocreate)'],
            'proxy_upload': [''],
            'proxy_uploadfilename': [''],
            }
    else:
        raise ValueError("no such login_type: %s" % login_type)
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
    proxy_path = os.path.join(config.user_home, client_dir, arc.Ui.proxy_name)

    if not config.arc_clusters:
        output.append({'object_type': 'error_text', 'text':
                       'No ARC support!'})
        return output

    # store the file
    try:
        write_file(proxy_string, proxy_path, config.logger)
        os.chmod(proxy_path, 0600)
    except Exception, exc:
        output.append({'object_type': 'error_text', 'text'
                              : 'Proxy file could not be written (%s)!'
                               % str(exc).replace(proxy_dir, '')})
        return output

    # provide information about the uploaded proxy
    try:
        session_ui = arc.Ui(proxy_dir)
        proxy = session_ui.getProxy()
        if proxy.IsExpired():
            # can rarely happen, constructor will throw exception
            output.append({'object_type': 'warning', 
                               'text': 'Proxy certificate is expired.'})
        else:
            output.append({'object_type': 'text', 
                                   'text': 'Proxy for %s' \
                                           % proxy.GetIdentitySN()})
            output.append({'object_type': 'text', 
                 'text': 'Proxy certificate will expire on %s (in %s sec.)' \
                         % (proxy.Expires(), proxy.getTimeleft())
                })
    except arc.NoProxyError, err:
        
        output.append({'object_type':'warning', 'text': 
                       'No proxy certificate to load: %s' % err.what()})
    return output


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=False)
    logger = configuration.logger
    logger.info('autocreate: args: %s' % user_arguments_dict)
    
    output_objects.append({'object_type': 'header', 'text'
                          : 'Automatic %s sign up' % \
                            configuration.short_title })
    if os.environ.get('SSL_CLIENT_S_DN', ''):
        login_type = 'cert'
        base_url = configuration.migserver_https_cert_url
    elif os.environ.get('REMOTE_USER', ''):
        login_type = 'oid'
        base_url = configuration.migserver_https_oid_url
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text': 'Missing user credentials'})
        return (output_objects, returnvalues.CLIENT_ERROR)
        
    defaults = signature(login_type)[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.debug('Accepted arguments: %s' % accepted)

    # Unfortunately OpenID redirect does not use POST
    if login_type != 'oid' and not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    admin_email = configuration.admin_email
    openid_names = []

    # force name to capitalized form (henrik karlsen -> Henrik Karlsen)
        
    if login_type == 'cert':
        uniq_id = accepted['cert_id'][-1].strip()
        full_name = accepted['full_name'][-1].strip().title()
        country = accepted['country'][-1].strip().upper()
        state = accepted['state'][-1].strip().title()
        organization = accepted['org'][-1].strip()
        organizational_unit = ''
        locality = ''
        timezone = ''
        # lower case email address
        email = accepted['email'][-1].strip().lower()
        raw_login = None
    elif login_type == 'oid':
        uniq_id = accepted['openid.sreg.nickname'][-1].strip() or \
                   accepted['openid.sreg.short_id'][-1].strip()
        full_name = accepted['openid.sreg.full_name'][-1].strip().title() or \
                    accepted['openid.sreg.fullname'][-1].strip().title()
        country = accepted['openid.sreg.country'][-1].strip().upper()
        state = accepted['openid.sreg.state'][-1].strip().title()
        organization = accepted['openid.sreg.organization'][-1].strip() or \
                       accepted['openid.sreg.o'][-1].strip()
        organizational_unit = accepted['openid.sreg.organizational_unit'][-1].strip() or \
                              accepted['openid.sreg.ou'][-1].strip()
        locality = accepted['openid.sreg.locality'][-1].strip()
        timezone = accepted['openid.sreg.timezone'][-1].strip()
        # lower case email address
        email = accepted['openid.sreg.email'][-1].strip().lower()
        id_url = os.environ['REMOTE_USER'].strip()
        raw_login = None
        for oid_provider in configuration.user_openid_providers:
            openid_prefix = oid_provider.rstrip('/') + '/'
            if id_url.startswith(openid_prefix):
                raw_login = id_url.replace(openid_prefix, '')
                break

    if raw_login:
        openid_names.append(raw_login)

    # we should have the proxy file read...
    proxy_content = accepted['proxy_upload'][-1]

    # keep comment to a single line

    comment = accepted['comment'][-1].replace('\n', '   ')

    # single quotes break command line format - remove

    comment = comment.replace("'", ' ')

    user_dict = {
        'short_id': uniq_id,
        'full_name': full_name,
        'organization': organization,
        'organizational_unit': organizational_unit,
        'locality': locality,
        'state': state,
        'country': country,
        'email': email,
        'timezone': timezone,
        'password': '',
        'comment': '%s: %s' % ('Existing certificate', comment),
        'openid_names': openid_names,
        }

    # We must receive some ID from the provider
    if not uniq_id and not email:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'No ID information received!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if login_type == 'cert':
        user_dict['expire'] = int(time.time() + cert_valid_days * 24 * 60 * 60)
        try:
            distinguished_name_to_user(uniq_id)
            user_dict['distinguished_name'] = uniq_id,
        except:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : '''Illegal Distinguished name:
Please note that the distinguished name must be a valid certificate DN with
multiple "key=val" fields separated by "/".
'''})
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif login_type == 'oid':
        user_dict['expire'] = int(time.time() + oid_valid_days * 24 * 60 * 60)
        fill_distinguished_name(user_dict)
        uniq_id = user_dict['distinguished_name']

    # If server allows automatic addition of users with a CA validated cert
    # we create the user immediately and skip mail
    
    if login_type == 'cert' and configuration.auto_add_cert_user or \
           login_type == 'oid' and configuration.auto_add_oid_user:
        fill_user(user_dict)

        # Now all user fields are set and we can begin adding the user

        db_path = os.path.join(configuration.mig_server_home, db_name)
        try:
            create_user(user_dict, configuration.config_file, 
                        db_path, ask_renew=False, default_renew=True)
            if configuration.site_enable_griddk and \
                   accepted['proxy_upload'] != ['']:
                # save the file, display expiration date
                proxy_out = handle_proxy(proxy_content, uniq_id, 
                                         configuration)
                output_objects.extend(proxy_out)
        except Exception, err:
            logger.error('Failed to create user with existing certificate %s: %s'
                     % (uniq_id, err))
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : '''Could not create the user account for you:
Please report this problem to the grid administrators (%s).''' % \
                 admin_email})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({'object_type': 'html_form', 'text'
                                   : '''Created the user account for you -
please open <a href="%s">your personal page</a> to proceed using it.
''' % base_url})
        return (output_objects, returnvalues.OK)
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Automatic user creation disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})        
        return (output_objects, returnvalues.ERROR)

