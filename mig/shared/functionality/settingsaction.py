#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settingsaction - handle user settings updates
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Backend for personal settings"""

from __future__ import absolute_import

import os
import tempfile

from mig.shared import returnvalues
from mig.shared.accountstate import check_update_account_expire
from mig.shared.duplicatikeywords import get_keywords_dict as duplicati_keywords
from mig.shared.functional import validate_input_and_cert
from mig.shared.gdp.all import get_client_id_from_project_client_id
from mig.shared.handlers import get_csrf_limit, safe_handler
from mig.shared.init import initialize_main_variables
from mig.shared.profilekeywords import get_keywords_dict as profile_keywords
from mig.shared.safeinput import valid_email_addresses
from mig.shared.settings import parse_and_save_settings, parse_and_save_widgets, \
    parse_and_save_profile, parse_and_save_ssh, parse_and_save_davs, \
    parse_and_save_ftps, parse_and_save_seafile, parse_and_save_duplicati, \
    parse_and_save_cloud, parse_and_save_twofactor
from mig.shared.settingskeywords import get_keywords_dict as settings_keywords
from mig.shared.useradm import create_seafile_mount_link, remove_seafile_mount_link
from mig.shared.twofactorkeywords import get_keywords_dict as twofactor_keywords
from mig.shared.widgetskeywords import get_keywords_dict as widgets_keywords


def extend_defaults(configuration, defaults, user_args):
    """Extract topic from untrusted user_args dictionary and safely extend
    defaults with topic-specific defaults before validation.
    """
    topic_list = user_args.get('topic', defaults['topic'])
    keywords_map = {}
    for topic in topic_list:
        if topic == 'general':
            keywords_map[topic] = settings_keywords()
        elif topic == 'widgets':
            keywords_map[topic] = widgets_keywords()
        elif topic == 'profile':
            keywords_map[topic] = profile_keywords()
        elif topic == 'duplicati':
            keywords_map[topic] = duplicati_keywords()
        elif topic == 'twofactor':
            keywords_map[topic] = twofactor_keywords(configuration)
        elif topic == 'sftp':
            keywords_map[topic] = {'publickeys': '', 'password': ''}
        elif topic == 'webdavs':
            keywords_map[topic] = {'publickeys': '', 'password': ''}
        elif topic == 'ftps':
            keywords_map[topic] = {'publickeys': '', 'password': ''}
        elif topic == 'seafile':
            keywords_map[topic] = {'password': ''}
        elif topic == 'cloud':
            keywords_map[topic] = {'publickeys': '', 'password': ''}
        else:
            # should never get here
            configuration.logger.warning("invalid topic: %s" % topic)
            continue

    for topic in topic_list:
        for keyword in keywords_map[topic].keys():
            defaults[keyword] = ['']
    return defaults


def signature():
    """Signature of the main function"""

    defaults = {'topic': ['general']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    output_objects.append(
        {'object_type': 'header', 'text': '%s settings' % configuration.short_title})

    defaults = signature()[1]
    extend_defaults(configuration, defaults, user_arguments_dict)
    # NOTE: EMAIL from general settings is a newline-separated list of emails
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        typecheck_overrides={'EMAIL': valid_email_addresses},
    )
    if not validate_status:
        logger.debug("failed validation: %s %s" % (accepted, defaults))
        return (accepted, returnvalues.CLIENT_ERROR)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_status = returnvalues.OK
    topic_list = accepted['topic']

    for topic in topic_list:
        topic_mrsl = ''
        if topic == 'general':
            keywords_dict = settings_keywords()
        elif topic == 'widgets':
            keywords_dict = widgets_keywords()
        elif topic == 'profile':
            keywords_dict = profile_keywords()
        elif topic == 'duplicati':
            keywords_dict = duplicati_keywords()
        elif topic == 'twofactor':
            keywords_dict = twofactor_keywords(configuration)
        elif topic in ('sftp', 'webdavs', 'ftps', 'seafile', 'cloud', ):
            # We don't use mRSL parser here
            keywords_dict = {}
        else:
            # should never get here
            logger.warning("invalid topic: %s" % topic)
            continue
        for keyword in keywords_dict.keys():
            received_arguments = accepted[keyword]
            # Skip keywords for other topics
            if not keyword in keywords_dict:
                continue
            if received_arguments != None and received_arguments != ['\r\n']:
                topic_mrsl += '''::%s::
%s

''' % (keyword.upper(), '\n'.join(received_arguments))

        # Save content to temp file

        try:
            (filehandle, tmptopicfile) = tempfile.mkstemp(text=True)
            os.write(filehandle, topic_mrsl)
            os.close(filehandle)
        except Exception:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Problem writing temporary topic file on server.'})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # Parse topic

        if topic == 'general':
            (parse_status, parse_msg) = \
                parse_and_save_settings(tmptopicfile, client_id,
                                        configuration)
        elif topic == 'widgets':
            (parse_status, parse_msg) = \
                parse_and_save_widgets(tmptopicfile, client_id,
                                       configuration)
        elif topic == 'profile':
            (parse_status, parse_msg) = \
                parse_and_save_profile(tmptopicfile, client_id,
                                       configuration)
        elif topic == 'duplicati':
            (parse_status, parse_msg) = \
                parse_and_save_duplicati(tmptopicfile, client_id,
                                         configuration)
        elif topic == 'twofactor':
            # GDP shares twofactor for all projects of user
            real_user = client_id
            if configuration.site_enable_gdp:
                real_user = get_client_id_from_project_client_id(configuration,
                                                                 client_id)
            (parse_status, parse_msg) = \
                parse_and_save_twofactor(tmptopicfile, real_user,
                                         configuration)
        elif topic == 'sftp':
            publickeys = '\n'.join(accepted.get('publickeys', ['']))
            password = accepted.get('password', [''])[-1].strip()
            (parse_status, parse_msg) = \
                parse_and_save_ssh(publickeys, password, client_id,
                                   configuration)
        elif topic == 'webdavs':
            publickeys = '\n'.join(accepted.get('publickeys', ['']))
            password = accepted.get('password', [''])[-1].strip()
            (parse_status, parse_msg) = \
                parse_and_save_davs(publickeys, password, client_id,
                                    configuration)
        elif topic == 'ftps':
            publickeys = '\n'.join(accepted.get('publickeys', ['']))
            password = accepted.get('password', [''])[-1].strip()
            (parse_status, parse_msg) = \
                parse_and_save_ftps(publickeys, password, client_id,
                                    configuration)
        elif topic == 'seafile':
            password = accepted.get('password', [''])[-1].strip()
            (parse_status, parse_msg) = \
                parse_and_save_seafile(password, client_id,
                                       configuration)
            if password:
                create_seafile_mount_link(client_id, configuration)
            else:
                remove_seafile_mount_link(client_id, configuration)
        elif topic == 'cloud':
            publickeys = '\n'.join(accepted.get('publickeys', ['']))
            password = accepted.get('password', [''])[-1].strip()
            (parse_status, parse_msg) = \
                parse_and_save_cloud(publickeys, password, client_id,
                                     configuration)
            raw_keys = publickeys.split('\n')
            auth_keys = [i.split('#', 1)[0].strip() for i in raw_keys]
            auth_keys = [i for i in auth_keys if i]
            if not auth_keys:
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     'No valid keys saved - create cloud instances will fail'})
            elif auth_keys[1:]:
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     'Only the first key will be activated on instances'})
        else:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'No such settings topic: %s' % topic
                                   })
            return (output_objects, returnvalues.CLIENT_ERROR)

        # Try to refresh expire if possible to make sure it works for a while
        if topic in ['sftp', 'webdavs', 'ftps']:
            (_, account_expire, _) = check_update_account_expire(
                configuration, client_id)
            logger.debug("check and update account expire returned %s" %
                         account_expire)

        try:
            os.remove(tmptopicfile)
        except Exception as exc:
            pass  # probably deleted by parser!

        if not parse_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error parsing and saving %s settings: %s' %
                                   (topic, parse_msg)})
            output_status = returnvalues.CLIENT_ERROR
        else:
            if parse_msg:
                output_objects.append({'object_type': 'html_form', 'text':
                                       '<span class="warningtext">%s</span>' %
                                       parse_msg})
        # print saved topic

        logger.debug("saved %s settings" % topic)
        output_objects.append(
            {'object_type': 'text', 'text': 'Saved %s settings:' % topic})

    if topic_list:
        topics_str = '?topic=%s' % ';topic='.join(topic_list)
    else:
        topics_str = ''
    output_objects.append({'object_type': 'link',
                           'destination': 'settings.py%s' % topics_str,
                           'class': 'backlink iconspace',
                           'title': 'Go back to settings',
                           'text': 'Back to settings'})

    logger.debug("all done in save %s settings" % topic)
    return (output_objects, output_status)
