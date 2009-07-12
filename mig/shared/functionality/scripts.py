#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# scripts - [insert a few words of module description on this line]
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

"""On demand headless script archive generator used as the base for
delivering the user and vgrid/resource scripts.
"""

import os
import sys
import zipfile
import time

from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues
from shared.useradm import client_id_dir


sh_cmd_def = 'sh'
python_cmd_def = 'python'


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'lang': [],
        'flavor': [],
        'sh_path': [sh_cmd_def],
        'python_path': [python_cmd_def],
        }
    return ['link', defaults]


def usage(
    output_objects,
    migserver_https_url,
    valid_langs,
    valid_flavors,
    ):
    """Script usage help"""

    output_objects.append({'object_type': 'section_header', 'text'
                          : 'Generator usage'})
    output_objects.append({'object_type': 'text', 'text'
                          : 'SERVER_URL/scripts.py?[with_html=(true|false);][lang=(%s);[...]][flags=h;][flavor=(%s);[...]][sh_cmd=sh_path;][python_cmd=python_path;]'
                           % ('|'.join(valid_langs.keys()),
                          '|'.join(valid_flavors.keys()))})
    output_objects.append({'object_type': 'text', 'text'
                          : '- each occurrence of lang adds the specified scripting language to the list of scripts to be generated.'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- flags is a string of one character flags to be passed to the script'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '- each occurrence of flavor adds the specified flavor to the list of scripts to be generated.'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : "- sh_cmd is the sh-interpreter command used on un*x if the scripts are run without specifying the interpreter (e.g. './migls.sh' rather than 'bash ./migls.sh')"
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : "- python_cmd is the python-interpreter command used on un*x if the scripts are run without specifying the interpreter (e.g. './migls.py' rather than 'python ./migls.py')"
                          })
    return output_objects


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    client_dir = client_id_dir(client_id)

    # Change CWD to ../mig/user/ to allow generator access

    cgibin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    mig_base = os.path.abspath(cgibin_dir + '/../')
    generator_dir = mig_base + '/user'
    os.chdir(cgibin_dir)
    sys.path.append(generator_dir)

    valid_langs = {'sh': 'shell', 'python': 'python'}
    valid_flavors = {'user': 'userscriptgen',
                     'resource': 'vgridscriptgen'}
    defaults = signature()[1]
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
    flags = ''.join(accepted['flags'])
    langs = accepted['lang']
    flavor_list = accepted['flavor']
    sh_cmd = accepted['sh_path'][-1]
    python_cmd = accepted['python_path'][-1]

    # Default values: lang = python, flavor = user, no flags
    # langs must be a list - waiting for new input validation for better check
    # langs = []
    # if user_arguments_dict.has_key("lang"):
    #    if type(user_arguments_dict["lang"]) == type([]):
    #        langs = user_arguments_dict["lang"]

    # flags, err = validated_string(user_arguments_dict, "flags", "")
    # if err:
    #    output_objects.append({"object_type":"warning", "text":"illegal flags argument: %s" % err})

    # flavor must be a list - waiting for new input validation for better check
    # flavor_list = []
    # if user_arguments_dict.has_key("flavor"):
    #    if type(user_arguments_dict["flavor"]) == type([]):
    #        flavor_list = user_arguments_dict["flavor"]

    flavors = []

    # We can't print path input until we have parsed it - only print op name for now!

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG script generator'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG script generator'})

    status = returnvalues.OK

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    if 'h' in flags:
        output_objects = usage(output_objects,
                               configuration.migserver_https_url,
                               valid_langs, valid_flavors)

    # Filter out any invalid flavors to avoid illegal filenames, etc.

    for f in flavor_list:
        if f in valid_flavors.keys():
            flavors.append(f)

    # Default to user scripts

    if not flavors:
        if flavor_list:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'No valid flavors specified - falling back to user scripts'
                                  })
        flavors = ['user']

    # Import everything from script generator module (truncates *_cmd's)

    if 'user' in flavors:

        # from userscriptgen import * (import * not allowed in a function)

        exec 'from userscriptgen import *'
    if 'resource' in flavors:

        # from vgridscriptgen import * (import * not allowed in a function)

        exec 'from vgridscriptgen import *'

    # Generate scripts in a "unique" destination directory
    # gmtime([seconds]) -> (tm_year, tm_mon, tm_day, tm_hour, tm_min,
    #                       tm_sec, tm_wday, tm_yday, tm_isdst)

    now = time.gmtime()
    timestamp = '%.2d%.2d%.2d-%.2d%.2d%.2d' % (
        now[2],
        now[1],
        now[0],
        now[3],
        now[4],
        now[5],
        )

    if not langs:

        # Add new languages here

        languages = [(sh_lang, sh_cmd, sh_ext), (python_lang,
                     python_cmd, python_ext)]
    else:
        languages = []

        # check arguments

        for lang in langs:
            if lang == 'sh':
                interpreter = sh_cmd
                extension = sh_ext
            elif lang == 'python':
                interpreter = python_cmd
                extension = python_ext
            else:
                output_objects.append({'object_type': 'warning', 'text'
                        : 'Unknown script language: %s - ignoring!'
                         % lang})
                continue

            languages.append((lang, interpreter, extension))

    if not languages:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No valid languages specified - aborting script generation'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    for flavor in flavors:
        script_dir = 'MiG-%s-scripts-%s' % (flavor, timestamp)
        dest_dir = '%s%s' % (base_dir, script_dir)

        if not os.path.isdir(dest_dir):
            try:
                os.mkdir(dest_dir)
            except Exception, e:
                output_objects.append({'object_type': 'error_text',
                        'text'
                        : 'Failed to create destination directory (%s)- aborting script generation'
                         % e})
                return (output_objects, returnvalues.SYSTEM_ERROR)
                continue

        for (lang, cmd, ext) in languages:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Generating %s %s scripts in the %s subdirectory of your MiG home directory'
                                   % (lang, flavor, script_dir)})

        # Generate all scripts

        if flavor == 'user':
            for op in script_ops:
                generator = 'generate_%s' % op
                eval(generator)(languages, dest_dir)

            if shared_lib:
                generate_lib(script_ops, languages, dest_dir)

            if test_script:
                generate_test(languages, dest_dir)
        elif flavor == 'resource':
            for op in script_ops_single_arg:
                generate_single_argument(op[0], op[1], languages,
                        dest_dir)
            for op in script_ops_single_upload_arg:
                generate_single_argument_upload(op[0], op[1], op[2],
                        languages, dest_dir)
            for op in script_ops_two_args:
                generate_two_arguments(op[0], op[1], op[2], languages,
                        dest_dir)
        else:
            output_objects.append({'object_type': 'warning_text', 'text'
                                  : 'Unknown flavor: %s' % flavor})
            continue

        output_objects.append({'object_type': 'text', 'text': '... Done'
                              })
        output_objects.append({'object_type': 'text', 'text'
                              : 'MiG %s scripts are now available in your MiG home directory:'
                               % flavor})
        output_objects.append({'object_type': 'link', 'text'
                              : 'View directory', 'destination'
                              : 'ls.py?path=%s' % script_dir})

        # Create zip from generated dir

        output_objects.append({'object_type': 'text', 'text'
                              : 'Generating zip archive of the MiG %s scripts'
                               % flavor})

        script_zip = script_dir + '.zip'
        dest_zip = '%s%s' % (base_dir, script_zip)
        zip_file = zipfile.ZipFile(dest_zip, 'w')

        # Directory write is not supported - add each file manually

        for script in os.listdir(dest_dir):
            zip_file.write(dest_dir + os.sep + script, script_dir
                            + os.sep + script)

        # Preserve executable flag in accordance with:
        # http://mail.python.org/pipermail/pythonmac-sig/2005-March/013491.html

        for zinfo in zip_file.filelist:
            zinfo.create_system = 3

        zip_file.close()

        # Verify CRC

        zip_file = zipfile.ZipFile(dest_zip, 'r')
        err = zip_file.testzip()
        zip_file.close()
        if err:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Zip file integrity check failed! (%s)'
                                   % e})
            status = returnvalues.SYSTEM_ERROR
            continue

        output_objects.append({'object_type': 'text', 'text': '... Done'
                              })
        output_objects.append({'object_type': 'text', 'text'
                              : 'Zip archive of the MiG %s scripts are now available in your MiG home directory'
                               % flavor})
        output_objects.append({'object_type': 'link', 'text'
                              : 'Download zip archive', 'destination'
                              : os.path.join('..', client_dir, script_zip)})
    return (output_objects, status)


