#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# scripts - backend to generate user and resource scripts
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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
import zipfile
import time

import shared.returnvalues as returnvalues
import shared.userscriptgen as usergen
import shared.vgridscriptgen as vgridgen
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry

sh_cmd_def = '/bin/bash'
python_cmd_def = '/usr/bin/python'


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'lang': [],
        'flavor': [],
        'sh_cmd': [sh_cmd_def],
        'python_cmd': [python_cmd_def],
        }
    return ['link', defaults]


def usage(output_objects, valid_langs, valid_flavors):
    """Script usage help"""

    output_objects.append({'object_type': 'sectionheader', 'text'
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
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)

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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    langs = accepted['lang']
    flavor_list = accepted['flavor']
    sh_cmd = accepted['sh_cmd'][-1]
    python_cmd = accepted['python_cmd'][-1]

    flavors = []

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Script generator'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Script generator'})

    status = returnvalues.OK

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    if 'h' in flags:
        output_objects = usage(output_objects, valid_langs,
                               valid_flavors)
        return (output_objects, status)

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

        languages = [(usergen.sh_lang, sh_cmd, usergen.sh_ext),
                     (usergen.python_lang, python_cmd,
                     usergen.python_ext)]
    else:
        languages = []

        # check arguments

        for lang in langs:
            if lang == 'sh':
                interpreter = sh_cmd
                extension = usergen.sh_ext
            elif lang == 'python':
                interpreter = python_cmd
                extension = usergen.python_ext
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
        script_dir = '%s-%s-scripts-%s' % (configuration.short_title, flavor, timestamp)
        dest_dir = '%s%s' % (base_dir, script_dir)

        if not os.path.isdir(dest_dir):
            try:
                os.mkdir(dest_dir)
            except Exception, exc:
                output_objects.append({'object_type': 'error_text',
                        'text'
                        : 'Failed to create destination directory (%s) - aborting script generation'
                         % exc})
                return (output_objects, returnvalues.SYSTEM_ERROR)

        for (lang, _, _) in languages:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'Generating %s %s scripts in the %s subdirectory of your %s home directory'
                                   % (lang, flavor, script_dir, configuration.short_title )})

        # Generate all scripts

        if flavor == 'user':
            for op in usergen.script_ops:
                generator = 'usergen.generate_%s' % op
                eval(generator)(configuration, languages, dest_dir)

            if usergen.shared_lib:
                usergen.generate_lib(configuration, usergen.script_ops,
                                     languages, dest_dir)

            if usergen.test_script:
                usergen.generate_test(configuration, languages, dest_dir)
        elif flavor == 'resource':
            for op in vgridgen.script_ops_single_arg:
                vgridgen.generate_single_argument(configuration, op[0], op[1],
                                                  languages, dest_dir)
            for op in vgridgen.script_ops_single_upload_arg:
                vgridgen.generate_single_argument_upload(configuration, op[0],
                                                         op[1], op[2],
                                                         languages, dest_dir)
            for op in vgridgen.script_ops_two_args:
                vgridgen.generate_two_arguments(configuration, op[0], op[1],
                                                op[2], languages, dest_dir)
            for op in vgridgen.script_ops_ten_args:
                vgridgen.generate_ten_arguments(configuration, op[0], op[1],
                                                op[2], op[3], op[4], op[5],
                                                op[6], op[7], op[8], op[9],
                                                op[10], languages, dest_dir)
        else:
            output_objects.append({'object_type': 'warning_text', 'text'
                                  : 'Unknown flavor: %s' % flavor})
            continue

        # Always include license conditions file
        
        usergen.write_license(configuration, dest_dir)
        
        output_objects.append({'object_type': 'text', 'text': '... Done'
                              })
        output_objects.append({'object_type': 'text', 'text'
                              : '%s %s scripts are now available in your %s home directory:'
                               % (configuration.short_title, flavor, configuration.short_title)})
        output_objects.append({'object_type': 'link', 'text'
                              : 'View directory', 'destination'
                              : 'fileman.py?path=%s/' % script_dir})

        # Create zip from generated dir

        output_objects.append({'object_type': 'text', 'text'
                              : 'Generating zip archive of the %s %s scripts'
                               % (configuration.short_title, flavor)})

        script_zip = script_dir + '.zip'
        dest_zip = '%s%s' % (base_dir, script_zip)
        # Force compression
        zip_file = zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED)

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
                                   % err})
            status = returnvalues.SYSTEM_ERROR
            continue

        output_objects.append({'object_type': 'text', 'text': '... Done'
                              })
        output_objects.append({'object_type': 'text', 'text'
                              : 'Zip archive of the %s %s scripts are now available in your %s home directory'
                               % (configuration.short_title, flavor, configuration.short_title)})
        output_objects.append({'object_type': 'link', 'text'
                              : 'Download zip archive', 'destination'
                              : os.path.join('..', client_dir,
                              script_zip)})
    return (output_objects, status)


