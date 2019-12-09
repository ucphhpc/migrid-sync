#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# parser - General parser functions for jobs and resource confs
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Parser helper functions"""

import os
import base64
import StringIO
import tempfile

from shared.defaults import keyword_all, maxfill_fields
from shared.rekeywords import get_keywords_dict
from shared.resconfkeywords import get_keywords_dict as resconf_get_keywords_dict
from shared.safeinput import valid_job_name, guess_type, html_escape

comment_char = '#'

# escape char is \, the first \ is for local escaping

escape_char = '\\'
valid_escape_chars = [comment_char]
used_env_names = []


def get_config_sub_level_dict(
    input_list,
    modify_dict,
    required_keywords,
    optional_keywords,
):

    for entry in input_list:
        entry = entry.strip()
        if entry == '':
            continue

    # split by = in max two parts
    # (python 2.5 has partition function, when MiG requires 2.5 switch to use that instead)

    # line must contain = to valid (and to survive the split("=", 2)

        if entry.find('=') == -1:
            continue
        (keyword, rest) = entry.split('=', 1)

    # remove trailing whitespace from keyword, eg. if input is keyword = val

        keyword = keyword.strip()

    # only add valid keywords to dict

        if keyword in required_keywords or keyword in optional_keywords:
            modify_dict[keyword] = rest.strip()
        else:
            return (False,
                    'Invalid sublevel keyword: %s. Required keywords: %s'
                    % (keyword, ', '.join(required_keywords)))

    # verify all required_keywords have been specified

    if len(modify_dict.keys()) == 0:
        specified_keywords = 'None'
    else:
        specified_keywords = ', '.join(modify_dict.keys())
    for req_key in required_keywords:
        if not modify_dict.has_key(req_key):
            return (False,
                    'All required keywords not specified! Specified keywords: %s. Required keywords: %s (at least %s is missing)'
                    % (specified_keywords,
                        ', '.join(required_keywords), req_key))
    return (True, modify_dict)


def handle_escapes(inputstring, strip_comments):
    new_string = ''
    escape_met = False

    # loop entire inputstring

    for char in inputstring:
        if char == escape_char:
            if escape_met:

                # last char was also the escape_char

                new_string += escape_char

                # escape_char met twice. Reset escape_met

                escape_met = False
            else:

                # last char was NOT the escape_char

                escape_met = True
        else:

            # this is not an escape_char

            if escape_met:
                if char in valid_escape_chars:
                    new_string += char
                else:
                    new_string += escape_char + char
            else:

                # here goes the unescaped chars

                if strip_comments and char == comment_char:

                    # found a comment - ignore rest of the line

                    return new_string
                else:

                    # just a normal char

                    new_string += char
            escape_met = False
    return new_string


def read_block(input_file, strip_space, strip_comments):
    """A block is a number of lines terminated by EOF or line with white
    space only. Any line leading and ending white space as well as comments
    are handled as specified with the strip parameters.
    """
    result = []
    data = True
    while data:
        line = input_file.readline().rstrip('\r\n')
        if line.strip():
            line = handle_escapes(line, strip_comments)
            if strip_space:
                line = line.strip()
            if line:
                result.append(line)
        else:
            data = False
    return result


def parse(mrsl_file, strip_space=True, strip_comments=True):
    """Parse an mRSL file or file-like object into a list of lists
    on the form [[KEYWORD, [VALUE, VALUE, ... ]], ... ] .
    """

    data = []
    if hasattr(mrsl_file, 'readline'):
        input_file = mrsl_file
    else:
        input_file = open(mrsl_file, 'rb', 0)

    while True:

        # read a line
        # readline returns "" string when EOF, to separate EOF and
        # blank lines .strip must be added later

        word = input_file.readline()
        if not word:

            # end of file reached

            break
        word = word.strip()
        if len(word) == 0:

            # blank line

            continue

        # a word (hopefully a keyword) was read, append and read block

        target = []
        target.append(word.upper())
        target.append(read_block(input_file, strip_space, strip_comments))
        data.append(target)

    input_file.close()
    return data


def parse_lines(mrsl_text):
    """Wrap lines in IO object to allow parsing from list"""
    mrsl_buffer = StringIO.StringIO(mrsl_text)
    return parse(mrsl_buffer)


def format_type_error(
    keyword,
    msg,
    keyword_dict,
    keyword_data,
):
    """Format type check errors for safe(!) and pretty printing. It is
    essential that raw user input is never printed unescaped as it could lead
    to security hazards.
    """
    out = '''<table border=1>
    <tr><td>Keyword</td><td>%(keyword)s</td></tr>
    <tr><td>Error</td><td>%(msg)s</td></tr>
    <tr><td>You supplied</td><td>%(safe_data)s</td></tr>
    <tr><td>Keyword example</td><td>%(example)s</td></tr>
    <tr><td>Keyword description</td><td>%(description)s</td></tr>
    </table><br />

    <!-- ****** INFORMATION ABOUT THE TYPE ERROR IN TEXT FORMAT ******
    Keyword: %(keyword)s
    Error: %(msg)s
    You supplied: %(safe_data)s
    Keyword example: %(example)s
    Keyword description: %(description)s
    *******************************************************************
    -->
    ''' % {'keyword': html_escape(keyword), 'msg': html_escape(msg),
           'safe_data': ' '.join([html_escape(i) for i in keyword_data]),
           'example': keyword_dict['Example'].replace('\n', '<br/>'),
           'description': keyword_dict['Description']}
    return out


def check_types(parse_output, external_keyword_dict, configuration):
    """Help check input from job descriptions and resource configurations.
    IMPORTANT: we parse raw user input here so we can NOT trust any of it to
    be safe even for for printing. Always handle with utmost care and escape
    any user values if printing values in errors and the like.
    """
    status = True
    msg = ''

    for keyword_block in parse_output:

        # remove the two colons before and after the keyword

        job_keyword = keyword_block[0].strip(':')
        keyword_data = keyword_block[1]

        if not external_keyword_dict.has_key(job_keyword):
            status = False
            # NOTE: we can't trust keyword to be safe for printing
            msg += 'unknown keyword: %s\n' % html_escape(job_keyword)
        else:

            # name of keyword ok, check if the type is correct

            keyword_dict = external_keyword_dict[job_keyword]
            keyword_type = keyword_dict['Type']
            value = keyword_dict['Value']

            # Required = keyword_dict["Required"]

            # IMPORTANT: all values must be strictly safeinput screened!
            # Some resource conf values are used in e.g. ssh commands from
            # subprocess calls. We do try to avoid full shell invocation
            # and thus variable interpretation but better safe than sorry.

            # First we validate all keywords and values to be safeinput

            sub_key = ''
            try:

                # Handle sublevels like execonfig and storeconfig explicitly
                if keyword_dict.get('Sublevel', False):
                    sub_keywords = external_keyword_dict[job_keyword]
                    required = sub_keywords.get('Sublevel_required', [])
                    optional = sub_keywords.get('Sublevel_optional', [])
                    (stat, sub_dict) = get_config_sub_level_dict(
                        keyword_data, {}, required, optional)
                    if not stat:
                        raise Exception('Error in sub level checking: %s %s' %
                                        (job_keyword, sub_dict))
                    for (sub_key, sub_val) in sub_dict.items():
                        safe_checker = guess_type(sub_key)
                        safe_checker(sub_val)
                else:
                    safe_checker = guess_type(job_keyword)
                    for data_val in keyword_data:
                        safe_checker(data_val)
            except Exception, exc:

                # found invalid value

                configuration.logger.error("parser type check for %s: %s" %
                                           (sub_key, exc))
                status = False
                key = job_keyword
                val = keyword_data
                if sub_key:
                    key += ' -> %s' % sub_key
                    val = [sub_val]
                msg += format_type_error(
                    key,
                    'invalid data value: %s' % exc,
                    keyword_dict, val)

            if keyword_type == 'int':
                if len(keyword_data) != 1:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'requires only a single integer',
                                             keyword_dict, keyword_data)
                else:
                    try:

                        # assign

                        keyword_dict['Value'] = int(keyword_data[0])
                    except:

                        # could not convert value to int

                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires an integer', keyword_dict,
                                                 keyword_data)
            elif keyword_type == 'boolean':
                if len(keyword_data) > 1:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'requires only a single boolean',
                                             keyword_dict, keyword_data)
                elif len(keyword_data) < 1:
                    # Unset checkbox results in empty data (html "feature")
                    keyword_dict['Value'] = False
                else:
                    if str(keyword_data[0]).lower() in ['true', '1', 'on']:
                        keyword_dict['Value'] = True
                    elif str(keyword_data[0]).lower() in ['false', '0', 'off']:
                        keyword_dict['Value'] = False
                    else:

                        # could not convert value to boolean

                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires a boolean', keyword_dict,
                                                 keyword_data)
            elif keyword_type == 'string':

                if not keyword_data:

                    # use default value

                    keyword_data.append(keyword_dict['Value'])
                if len(keyword_data) > 1:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'requires only a single string',
                                             keyword_dict, keyword_data)
                else:
                    try:

                        # assign

                        keyword_dict['Value'] = str(keyword_data[0])
                    except:

                        # could not convert value to string

                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires a string', keyword_dict,
                                                 keyword_data)
                if job_keyword == 'RENAME':

                    # assign in upper case

                    keyword_dict['Value'] = str(keyword_data[0]).upper()
                if job_keyword == 'ARCHITECTURE':
                    if not str(keyword_data[0])\
                            in configuration.architectures:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'specified architecture not valid, should be %s'
                                                 % configuration.architectures,
                                                 keyword_dict, keyword_data)
                if job_keyword == 'SCRIPTLANGUAGE':
                    if not str(keyword_data[0])\
                            in configuration.scriptlanguages:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'specified scriptlanguage not valid, should be %s'
                                                 % configuration.scriptlanguages,
                                                 keyword_dict, keyword_data)
                if job_keyword == 'JOBTYPE':
                    if not str(keyword_data[0])\
                            in configuration.jobtypes:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'specified jobtype not valid, should be %s'
                                                 % configuration.jobtypes,
                                                 keyword_dict, keyword_data)
                if job_keyword == 'JOBNAME':
                    try:
                        valid_job_name(str(keyword_data[0]), min_length=0)
                    except Exception, err:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'specified jobname not valid: %s' % err,
                                                 keyword_dict, keyword_data)
            elif keyword_type == 'multiplestrings':
                maxfill_values = [keyword_all] + maxfill_fields
                for single_line in keyword_data:
                    try:
                        value.append(str(single_line))
                    except:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires one or more strings',
                                                 keyword_dict, keyword_data)
                    if job_keyword == 'MAXFILL':
                        if not single_line.strip() in maxfill_values:
                            status = False
                            msg += format_type_error(
                                job_keyword,
                                'specified maxfill not valid, should be in %s' %
                                maxfill_values,
                                keyword_dict, keyword_data)
            elif keyword_type == 'testprocedure':

                # submit testprocedure job to parser to verify it is a valid mrsl file

                base64_string = ''
                for part in keyword_data:
                    base64_string += part

                testprocedure = base64.decodestring(base64_string)

                # do not allow any custom ::VERIFYFILES:: keywords (only allow the automatically added)

                if testprocedure.count('::VERIFYFILES::') > 1:
                    status = False
                    msg += \
                        'Do not specify any ::VERIFYFILES:: sections, this is done automatically'

                tmpfile = None
                if status:

                    # save testprocedure to temporary file

                    try:
                        (filehandle, tmpfile) = \
                            tempfile.mkstemp(text=True)
                        os.write(filehandle, testprocedure)
                        os.close(filehandle)
                    except Exception, err:
                        status = False
                        msg += \
                            'Exception writing temporary testprocedure file. New runtime environment not created! %s'\
                            % err

                retmsg = ''
                if status:
                    from shared.mrslparser import parse as mrslparse
                    (status, retmsg) = mrslparse(
                        tmpfile, "testprocedure_job_id",
                        "testprocedure_test_parse__cert_name_not_specified",
                        False, outfile="%s.parsed" % tmpfile)

                # remove temporary files no matter what happened

                if tmpfile:
                    try:
                        os.remove(tmpfile)
                        os.remove('%s.parsed' % tmpfile)
                    except Exception, err:
                        msg += \
                            'Exception removing temporary testprocedure file %s or %s, %s'\
                            % (tmpfile, '%s.parsed' % tmpfile, err)

                        # should we exit because of this? status = False

                if not status:
                    status = False
                    msg += \
                        'mRSL specified in testprocedure is not valid: %s '\
                        % retmsg

                try:

                    # value.append(str(keyword_data[0]))

                    value.append(str(keyword_data))
                except:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'could not append testprocedure',
                                             keyword_dict, keyword_data)
            elif keyword_type == 'multiplekeyvalues':

                for single_line in keyword_data:
                    try:
                        if single_line.find('=') == -1:
                            status = False
                            msg += format_type_error(job_keyword,
                                                     "requires one or more key=value rows. '=' not found on line.", keyword_dict, keyword_data)
                        else:
                            keyval = single_line.split('=', 1)
                            env = (str(keyval[0]), str(keyval[1]))
                            value.append(env)
                    except:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires one or more key=value rows',
                                                 keyword_dict, keyword_data)
            elif keyword_type == 'execonfig':

                # field_data = [i for i in keyword_data]

                # read required and optional sublevel keywords from resconfkeywords

                resconfkeywords_dict = \
                    resconf_get_keywords_dict(configuration)
                exekeywords = resconfkeywords_dict['EXECONFIG']
                sublevel_required = []
                sublevel_optional = []

                if exekeywords.has_key('Sublevel')\
                        and exekeywords['Sublevel']:
                    sublevel_required = exekeywords['Sublevel_required']
                    sublevel_optional = exekeywords['Sublevel_optional']
                (stat, exe_dict) = \
                    get_config_sub_level_dict(keyword_data, {},
                                              sublevel_required, sublevel_optional)
                if not stat:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error in sub level parsing: %s'
                                             % exe_dict, keyword_dict, keyword_data)

                try:
                    continuous = str(exe_dict['continuous'])

                    # Keep old typo for backwards compatibility

                    if continuous == 'False':
                        exe_dict['continuous'] = False
                        exe_dict['continious'] = exe_dict['continuous']
                    elif continuous == 'True':
                        exe_dict['continuous'] = True
                        exe_dict['continious'] = exe_dict['continuous']
                    else:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'continuous must be True or False',
                                                 keyword_dict, keyword_data)

                    shared_fs = str(exe_dict['shared_fs'])
                    if shared_fs == 'False':
                        exe_dict['shared_fs'] = False
                    elif shared_fs == 'True':
                        exe_dict['shared_fs'] = True
                    else:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'shared_fs must be True or False',
                                                 keyword_dict, keyword_data)

                    vgrid_value = exe_dict['vgrid']

                    # Split between comma and remove extra whitespace

                    exe_dict['vgrid'] = [i.strip() for i in
                                         vgrid_value.split(',') if i.strip()]
                    value.append(exe_dict)
                except Exception, err:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error getting execonfig value',
                                             keyword_dict, keyword_data)
            elif keyword_type == 'storeconfig':

                # field_data = [i for i in keyword_data]

                # read required and optional sublevel keywords from resconfkeywords

                resconfkeywords_dict = \
                    resconf_get_keywords_dict(configuration)
                storekeywords = resconfkeywords_dict['STORECONFIG']
                sublevel_required = []
                sublevel_optional = []

                if storekeywords.has_key('Sublevel')\
                        and storekeywords['Sublevel']:
                    sublevel_required = storekeywords['Sublevel_required']
                    sublevel_optional = storekeywords['Sublevel_optional']
                (stat, store_dict) = \
                    get_config_sub_level_dict(keyword_data, {},
                                              sublevel_required, sublevel_optional)
                if not stat:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error in sub level parsing: %s'
                                             % store_dict, keyword_dict, keyword_data)

                supported_protocols = ['sftp']
                try:
                    protocol = store_dict['storage_protocol']
                    if protocol not in supported_protocols:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'storage_protocol must be in %s' % supported_protocols,
                                                 keyword_dict, keyword_data)

                    shared_fs = str(store_dict['shared_fs'])
                    if shared_fs == 'False':
                        store_dict['shared_fs'] = False
                    elif shared_fs == 'True':
                        store_dict['shared_fs'] = True
                    else:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'shared_fs must be True or False',
                                                 keyword_dict, keyword_data)

                    vgrid_value = store_dict['vgrid']

                    # Split between comma and remove extra whitespace

                    store_dict['vgrid'] = [i.strip() for i in
                                           vgrid_value.split(',') if i.strip()]
                    value.append(store_dict)
                except Exception, err:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error getting storeconfig value',
                                             keyword_dict, keyword_data)
            elif keyword_type == 'configruntimeenvironment':

                # When successful, the result is on the form:
                # [('POVRAY3.6', []), ('HKTEST', [('bla', 'bla2'), ('blaa', 'bla3')]), ('LOCALDISK', [])]

                name = ''
                val = []
                for single_line in keyword_data:
                    try:
                        if single_line.lower().find('name:') == 0:

                            # new RE. Append to list if this is not the first RE

                            if name:
                                runtime_env = (name.upper(), val)
                                value.append(runtime_env)
                                val = []

                            name = single_line.lower().replace('name:',
                                                               '').strip()

                            if not name:
                                status = False
                                msg += format_type_error(job_keyword,
                                                         "Name of runtime environment not specified after 'name:'", keyword_dict, keyword_data)
                        else:

                            # new environment for RE

                            if not name:

                                # Trying to assign value to an unnamed RE

                                status = False
                                msg += format_type_error(job_keyword,
                                                         'Trying to assign value to an unnamed runtime environment', keyword_dict, keyword_data)
                            if single_line.find('=') == -1:
                                status = False
                                msg += format_type_error(job_keyword,
                                                         'Environment values must be on the form: envname=envvalue', keyword_dict, keyword_data)

                            # ok

                            keyval = single_line.split('=', 1)
                            env = (keyval[0].strip(), keyval[1].strip())
                            val.append(env)
                    except:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'requires one or more key=value rows',
                                                 keyword_dict, keyword_data)
                runtime_env = (name.upper(), val)
                if name.strip():
                    value.append(runtime_env)
                    val = []
            elif keyword_type == 'RE_software':

                try:

                    # read required and optional sublevel keywords from rekeywords

                    rekeywords_dict = get_keywords_dict()
                    software = rekeywords_dict['SOFTWARE']
                    sublevel_required = []
                    sublevel_optional = []

                    if software.has_key('Sublevel')\
                            and software['Sublevel']:
                        sublevel_required = software['Sublevel_required'
                                                     ]
                        sublevel_optional = software['Sublevel_optional'
                                                     ]

                    (stat, software_dict) = \
                        get_config_sub_level_dict(keyword_data, {},
                                                  sublevel_required, sublevel_optional)
                    if not stat:
                        status = False
                        msg += format_type_error(job_keyword,
                                                 'Error in sub level parsing: %s'
                                                 % software_dict, keyword_dict,
                                                 keyword_data)
                    else:
                        value.append(software_dict)
                except Exception, err:
                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error getting RE_software value',
                                             keyword_dict, keyword_data)
            elif keyword_type == 'RE_environmentvariable':
                try:

                    # read required and optional sublevel keywords from rekeywords

                    rekeywords_dict = get_keywords_dict()
                    environmentvariable = \
                        rekeywords_dict['ENVIRONMENTVARIABLE']
                    sublevel_required = []
                    sublevel_optional = []

                    if environmentvariable.has_key('Sublevel')\
                            and environmentvariable['Sublevel']:
                        sublevel_required = \
                            environmentvariable['Sublevel_required']
                        sublevel_optional = \
                            environmentvariable['Sublevel_optional']

                    (stat, env_vars) = \
                        get_config_sub_level_dict(keyword_data, {},
                                                  sublevel_required, sublevel_optional)

                    if stat:
                        env_name = env_vars['name']
                        if env_name in used_env_names:
                            status = False
                            msg += format_type_error(job_keyword,
                                                     "Environment name '%s' used more than once."
                                                     % env_name, keyword_dict,
                                                     keyword_data)
                        used_env_names.append(env_name)

                        value.append(env_vars)
                    else:

                        # sub level parsing error

                        status = False
                        msg += format_type_error(job_keyword,
                                                 'Error in sub level parsing: %s'
                                                 % env_vars, keyword_dict, keyword_data)
                except Exception, err:

                    status = False
                    msg += format_type_error(job_keyword,
                                             'Error getting RE_environmentvariable value.', keyword_dict, keyword_data)
            else:
                status = False
                msg += \
                    'Internal error: Keyword %s with unknown type %s was accepted!'\
                    % (html_escape(job_keyword), keyword_type)

            # print str(value)
            # Keyword was found. Change required to False meaning that the keyword is no longer required

            if keyword_data:
                keyword_dict['Required'] = False

    # check if required keywords are in the mRSL file
    # (all Required fields should be False since the Required field
    # of a keyword is changed to False when the parser finds it)

    for keyword_entry in external_keyword_dict.keys():
        entry = external_keyword_dict[keyword_entry]
        if entry.has_key('Required'):
            if entry['Required']:

                # Required keyword not found

                msg += 'REQUIRED keyword %s was not found in your file!'\
                    % keyword_entry
                status = False

    return (status, msg)
