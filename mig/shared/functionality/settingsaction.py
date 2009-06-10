#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settingsaction - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import sys
import os
import tempfile

from shared.settingskeywords import get_keywords_dict
from shared.fileio import pickle
from shared.settings import parse_and_save_settings
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""
    defaults = {}
    keywords_dict = get_keywords_dict()
    for keyword in keywords_dict.keys():
        defaults[keyword] = ['']
    return ['text', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG settings'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    settings_mrsl = ''

    for keyword in get_keywords_dict().keys():
        received_arguments = accepted[keyword]
        if received_arguments != None and received_arguments != ['\r\n'
                ]:
            settings_mrsl += '''::%s::
%s

''' % (keyword.upper(),
                    '\n'.join(received_arguments))

    # Save content to temp file

    try:
        (filehandle, tmpsettingsfile) = tempfile.mkstemp(text=True)
        os.write(filehandle, settings_mrsl)
        os.close(filehandle)
    except Exception:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Problem writing temporary settings file on server.'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Parse settings

    (parse_status, parse_msg) = \
        parse_and_save_settings(tmpsettingsfile, cert_name_no_spaces,
                                configuration)
    try:
        os.remove(tmpsettingsfile)
    except Exception:
        pass  # probably deleted by parser!

        # output_objects.append({"object_type":"error_text", "text": "Could not remove temporary settings file %s, exception: %s" % (tmpsettingsfile, e)})

    if not parse_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error parsing settings file: %s'
                               % parse_msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # print saved settings

    output_objects.append({'object_type': 'text', 'text'
                          : 'Saved settings:'})
    for line in settings_mrsl.split('\n'):
        output_objects.append({'object_type': 'text', 'text': line})

    return (output_objects, returnvalues.OK)


