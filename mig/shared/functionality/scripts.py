#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# scripts - backend to generate user and resource scripts
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import os
import time
import zipfile

from mig.shared import returnvalues
from mig.shared import userscriptgen
from mig.shared import vgridscriptgen
from mig.shared.publicscriptgen import script_login_session, \
    lookup_publicscript_function
from mig.shared.base import client_id_dir
from mig.shared.defaults import keyword_all, keyword_auto
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.validstring import valid_user_path

sh_cmd_def = '/bin/bash'
python_cmd_def = '/usr/bin/python'


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'lang': [keyword_all],
        'flavor': [],
        'sh_cmd': [sh_cmd_def],
        'python_cmd': [python_cmd_def],
        'script_dir': [keyword_auto]
    }
    return ['link', defaults]


def usage(output_objects, valid_langs, valid_flavors):
    """Script usage help"""

    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Generator usage'})
    output_objects.append({'object_type': 'text', 'text': 'SERVER_URL/scripts.py?[with_html=(true|false)&][lang=(%s)&[...]][flags=h&][flavor=(%s)&[...]][sh_cmd=sh_path&][python_cmd=python_path&]'
                           % ('|'.join(list(valid_langs)),
                              '|'.join(list(valid_flavors)))})
    output_objects.append({'object_type': 'text', 'text': '- each occurrence of lang adds the specified scripting language to the list of scripts to be generated.'
                           })
    output_objects.append({'object_type': 'text', 'text': '- flags is a string of one character flags to be passed to the script'
                           })
    output_objects.append({'object_type': 'text', 'text': '- each occurrence of flavor adds the specified flavor to the list of scripts to be generated.'
                           })
    output_objects.append({'object_type': 'text', 'text': "- sh_cmd is the sh-interpreter command used on un*x if the scripts are run without specifying the interpreter (e.g. './migls.sh' rather than 'bash ./migls.sh')"
                           })
    output_objects.append({'object_type': 'text', 'text': "- python_cmd is the python-interpreter command used on un*x if the scripts are run without specifying the interpreter (e.g. './migls.py' rather than 'python ./migls.py')"
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

    flags = ''.join(accepted['flags'])
    langs = accepted['lang']
    flavor_list = accepted['flavor']
    sh_cmd = accepted['sh_cmd'][-1]
    python_cmd = accepted['python_cmd'][-1]
    script_dir = accepted['script_dir'][-1]

    flavors = []

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Script generator'
    output_objects.append(
        {'object_type': 'header', 'text': 'Script generator'})

    status = returnvalues.OK

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    if 'h' in flags:
        output_objects = usage(output_objects, valid_langs,
                               valid_flavors)
        return (output_objects, status)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Filter out any invalid flavors to avoid illegal filenames, etc.

    for f in flavor_list:
        if f in valid_flavors:
            flavors.append(f)

    # Default to user scripts

    if not flavors:
        if flavor_list:
            output_objects.append(
                {'object_type': 'text', 'text':
                 'No valid flavors specified - falling back to user scripts'})
        flavors = ['user']

    if not langs or keyword_all in langs:

        # Add new languages here

        languages = [(userscriptgen.sh_lang, sh_cmd, userscriptgen.sh_ext),
                     (userscriptgen.python_lang, python_cmd,
                      userscriptgen.python_ext)]
    else:
        languages = []

        # check arguments

        for lang in langs:
            if lang == 'sh':
                interpreter = sh_cmd
                extension = userscriptgen.sh_ext
            elif lang == 'python':
                interpreter = python_cmd
                extension = userscriptgen.python_ext
            else:
                output_objects.append({'object_type': 'warning', 'text':
                                       'Unknown script language: %s - ignoring!'
                                       % lang})
                continue

            languages.append((lang, interpreter, extension))

    if not languages:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'No valid languages specified - aborting script generation'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    for flavor in flavors:
        if not script_dir or script_dir == keyword_auto:
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
            script_dir = '%s-%s-scripts-%s' % (configuration.short_title,
                                               flavor, timestamp)
        else:
            # Avoid problems from especially trailing slash (zip recursion)
            script_dir = script_dir.strip(os.sep)

        # IMPORTANT: path must be expanded to abs for proper chrooting
        abs_dir = os.path.abspath(os.path.join(base_dir, script_dir))
        if not valid_user_path(configuration, abs_dir, base_dir, True):

            # out of bounds

            logger.warning('%s tried to %s restricted path %s ! (%s)'
                           % (client_id, op_name, abs_dir, script_dir))
            output_objects.append({'object_type': 'error_text', 'text':
                                   "You're not allowed to work in %s!"
                                   % script_dir})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not os.path.isdir(abs_dir):
            try:
                os.mkdir(abs_dir)
            except Exception as exc:
                logger.error("create script dest %s failed: %s" % (abs_dir,
                                                                   exc))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     '''Failed to create destination dir (%s) - aborting script
generation''' % script_dir})
                return (output_objects, returnvalues.SYSTEM_ERROR)

        for (lang, _, _) in languages:
            output_objects.append({'object_type': 'text', 'text':
                                   '''Generating %s %s scripts in the %s
subdirectory of your %s home directory''' % (lang, flavor, script_dir,
                                             configuration.short_title)})
        logger.debug('generate %s scripts in %s' % (flavor, abs_dir))

        # Generate all scripts

        if flavor == 'user':
            for op in userscriptgen.script_ops:
                generator = userscriptgen.lookup_userscript_function(
                    'generate', op)
                generator(configuration, languages, dest_dir=abs_dir)

            if userscriptgen.shared_lib:
                userscriptgen.generate_lib(configuration, languages,
                                           userscriptgen.script_ops,
                                           dest_dir=abs_dir)

            if userscriptgen.test_script:
                userscriptgen.generate_test(configuration, languages, abs_dir)
        elif flavor in ('resource', 'vgrid'):
            # TODO: use concatenated script_ops in one loop when upload is gone
            for op in vgridscriptgen.script_ops_single_arg:
                vgridscriptgen.generate_any_arguments(configuration, languages,
                                                      *op, dest_dir=abs_dir)
            for op in vgridscriptgen.script_ops_single_upload_arg:
                # TODO: port to use 'any' version
                vgridscriptgen.generate_single_argument_upload(configuration,
                                                               languages, *op,
                                                               dest_dir=abs_dir)
            for op in vgridscriptgen.script_ops_two_args:
                vgridscriptgen.generate_any_arguments(configuration, languages,
                                                      *op, dest_dir=abs_dir)
            for op in vgridscriptgen.script_ops_ten_args:
                vgridscriptgen.generate_any_arguments(configuration, languages,
                                                      *op, dest_dir=abs_dir)

            if vgridscriptgen.shared_lib:
                vgridscriptgen.generate_lib(configuration, languages,
                                            vgridscriptgen.script_ops,
                                            dest_dir=abs_dir)

            if vgridscriptgen.test_script:
                vgridscriptgen.generate_test(configuration, languages, abs_dir)
        else:
            output_objects.append(
                {'object_type': 'warning_text', 'text': 'Unknown flavor: %s' % flavor})
            continue

        # Shared login/logout/twofactor session helpers
        for op in script_login_session:
            generator = lookup_publicscript_function('generate', op)
            generator(configuration, languages, dest_dir=abs_dir)

        # Always include license conditions file

        userscriptgen.write_license(configuration, abs_dir)

        output_objects.append({'object_type': 'text', 'text': '... Done'
                               })
        output_objects.append({'object_type': 'text', 'text': '%s %s scripts are now available in your %s home directory:'
                               % (configuration.short_title, flavor, configuration.short_title)})
        output_objects.append({'object_type': 'link', 'text': 'View directory',
                               'destination': 'fileman.py?path=%s/' % script_dir})

        # Create zip from generated dir

        output_objects.append({'object_type': 'text', 'text': 'Generating zip archive of the %s %s scripts'
                               % (configuration.short_title, flavor)})

        script_zip = script_dir + '.zip'
        dest_zip = '%s%s' % (base_dir, script_zip)
        logger.debug('packing generated scripts from %s in %s' % (abs_dir,
                                                                  dest_zip))

        # Force compression
        zip_file = zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED)

        # Directory write is not supported - add each file manually

        for script in os.listdir(abs_dir):
            zip_file.write(abs_dir + os.sep + script, script_dir
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
            logger.error("zip file integrity check on %s failed: %s" %
                         (dest_zip, err))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Zip file integrity check failed!'})
            status = returnvalues.SYSTEM_ERROR
            continue

        output_objects.append({'object_type': 'text', 'text': '... Done'
                               })
        output_objects.append(
            {'object_type': 'text', 'text':
             '''Zip archive of the %s %s scripts are now available in your %s
home directory''' % (configuration.short_title, flavor,
                     configuration.short_title)})
        output_objects.append(
            {'object_type': 'link', 'text':
             'Download zip archive %s' % script_zip,
             'destination': os.path.join('..', client_dir, script_zip)})
        output_objects.append(
            {'object_type': 'upgrade_info', 'text': '''
You can upgrade from an existing user scripts folder with the commands:''',
             'commands': ["./migget.sh '%s' ../" % script_zip,
                          "cd ..", "unzip '%s'" % script_zip,
                          "cd '%s'" % script_dir]})

    return (output_objects, status)
