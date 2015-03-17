#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settingsaction - [insert a few words of module description on this line]
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

"""Backe end for personal settings"""

import os
import tempfile

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.settings import parse_and_save_settings, parse_and_save_widgets, \
     parse_and_save_profile, parse_and_save_ssh, parse_and_save_davs, \
     parse_and_save_ftps
from shared.profilekeywords import get_keywords_dict as profile_keywords
from shared.settingskeywords import get_keywords_dict as settings_keywords
from shared.widgetskeywords import get_keywords_dict as widgets_keywords


def extend_defaults(defaults, user_args):
    """Extract topic from untrusted user_args dictionary and safely extend
    defaults with topic-specific defaults before validation.
    """
    topic = user_args.get('topic', defaults['topic'])[-1]
    if topic == 'general':
        keywords_dict = settings_keywords()
    elif topic == 'widgets':
        keywords_dict = widgets_keywords()
    elif topic == 'profile':
        keywords_dict = profile_keywords()
    elif topic == 'sftp':
        keywords_dict = {'publickeys': '', 'password': ''}
    elif topic == 'webdavs':
        keywords_dict = {'publickeys': '', 'password': ''}
    elif topic == 'ftps':
        keywords_dict = {'publickeys': '', 'password': ''}
    else:
        # should never get here
        keywords_dict = {}
    for keyword in keywords_dict.keys():
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
    output_objects.append({'object_type': 'header', 'text'
                          : '%s settings' % configuration.short_title })

    defaults = signature()[1]
    extend_defaults(defaults, user_arguments_dict)
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    topic = accepted['topic'][-1]
    topic_mrsl = ''

    if topic == 'general':
        keywords_dict = settings_keywords()
    elif topic == 'widgets':
        keywords_dict = widgets_keywords()
    elif topic == 'profile':
        keywords_dict = profile_keywords()
    elif topic in ('sftp', 'webdavs', 'ftps'):
        # We don't use mRSL parser here
        keywords_dict = {}
    else:
        # should never get here
        keywords_dict = {}
    for keyword in keywords_dict.keys():
        received_arguments = accepted[keyword]
        if received_arguments != None and received_arguments != ['\r\n'
                ]:
            topic_mrsl += '''::%s::
%s

''' % (keyword.upper(),
                    '\n'.join(received_arguments))

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
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No such settings topic: %s' % topic
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)
        
    try:
        os.remove(tmptopicfile)
    except Exception, exc:
        pass  # probably deleted by parser!

        # output_objects.append(
        #    {"object_type":"error_text", "text":
        #     "Could not remove temporary topic file %s, exception: %s" % \
        #     (tmptopicfile, exc)})

    if not parse_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error parsing %s settings file: %s'
                               % (topic, parse_msg)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # print saved topic

    output_objects.append({'object_type': 'text', 'text'
                          : 'Saved %s settings:' % topic})

    # Enable next lines for debug
    #for line in topic_mrsl.split('\n'):
    #    output_objects.append({'object_type': 'text', 'text': line})

    output_objects.append({'object_type': 'link',
                           'destination': 'settings.py?topic=%s' % topic,
                           'class': 'backlink',
                           'title': 'Go back to %s settings' % topic,
                           'text': 'Back to %s settings' % topic})

    return (output_objects, returnvalues.OK)


