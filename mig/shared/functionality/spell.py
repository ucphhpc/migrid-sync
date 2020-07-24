#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# spell - [insert a few words of module description on this line]
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Spell check a file using an native spell checker."""

import os
import glob

from shared import returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.parseflags import verbose
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'path': REJECT_UNSET,
        'lang': ['en'],
        'mode': ['none'],
        }
    return ['file_output', defaults]


def spellcheck(
    path,
    mode,
    lang,
    user_dict_path=None,
    ):
    """Use pyenchant module to spell check the provided file path"""

    (res, msg) = ([], '')
    try:
        import enchant
        if user_dict_path:
            check_dict = enchant.DictWithPWL(lang, user_dict_path)
        else:
            check_dict = enchant.Dict(lang)
        target_fd = open(path, 'r')
        for line in target_fd:
            line = line.strip()
            for word in line.split(' '):
                if word and not check_dict.check(word):

                    # TODO: local chars are not encoded correctly here

                    res.append('%s: %s' % (word,
                               ', '.join(check_dict.suggest(word))))
    except Exception, err:
        msg = 'Failed to run spell check: %s' % err
    return (res, msg)


def adv_spellcheck(
    path,
    mode,
    lang,
    user_dict_path=None,
    ):
    """Use pyenchant module to spell check the provided file path"""

    # TODO: This fails with internal pyenchant index out of bounds error

    (res, msg) = ([], '')
    try:
        from enchant.checker import SpellChecker
        spell_checker = SpellChecker(lang)
        target_fd = open(path, 'r')
        spell_checker.set_text(target_fd.read())
        for entry in spell_checker:
            res.append('%s: %s' % (entry.word, entry.suggest()))
        target_fd.close()
    except Exception, err:
        msg = 'Failed to run spell check: %s' % err
    return (res, msg)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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
    pattern_list = accepted['path']
    lang = accepted['lang'][-1].lower()
    mode = accepted['mode'][-1]

    output_objects.append({'object_type': 'header', 'text'
                          : '%s spell check' % configuration.short_title })

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    status = returnvalues.OK
    allowed_modes = ['none', 'url', 'email', 'sgml', 'tex']

    # Include both base languages and variants

    allowed_langs = [
        'da',
        'da_dk',
        'de',
        'en',
        'en_gb',
        'en_us',
        'es',
        'fi',
        'fr',
        'it',
        'nl',
        'no',
        'se',
        ]

    # TODO: use path from settings file

    dict_path = '%s/%s' % (base_dir, '.personal_dictionary')

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    if not mode in allowed_modes:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported mode: %s' % mode})
        status = returnvalues.CLIENT_ERROR

    if not lang in allowed_langs:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported lang: %s' % mode})
        status = returnvalues.CLIENT_ERROR

    # Show all if no flags given

    if not flags:
        flags = 'blw'

    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
            output_lines = []
            try:
                (out, err) = spellcheck(abs_path, mode, lang,
                        dict_path)
                if err:
                    output_objects.append({'object_type': 'error_text',
                            'text': err})

                for line in out:
                    output_lines.append(line + '\n')
            except Exception, err:
                output_objects.append({'object_type': 'error_text',
                        'text': "%s: '%s': %s" % (op_name,
                        relative_path, err)})
                status = returnvalues.SYSTEM_ERROR
                continue

            if verbose(flags):
                output_objects.append({'object_type': 'file_output',
                        'path': relative_path, 'lines': output_lines})
            else:
                output_objects.append({'object_type': 'file_output',
                        'lines': output_lines})
            htmlform = \
                '''
<form method="get" action="editor.py">
<input type="hidden" name="path" value="%s" />
<input type="submit" value="Edit file" />
</form>
''' % relative_path
            output_objects.append({'object_type': 'html_form', 'text'
                                  : htmlform})

    return (output_objects, status)


