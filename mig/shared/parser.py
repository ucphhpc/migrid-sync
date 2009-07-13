#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# parser - General parser functions for jobs and resource confs
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

"""Parser helper functions"""

import re
import types
import os
import base64
import tempfile

from shared.rekeywords import get_keywords_dict
from shared.resconfkeywords import get_keywords_dict as resconf_get_keywords_dict

comment_char = '#'

# escape char is \, the first \ is for local escaping

escape_char = '\\'
valid_escape_chars = [comment_char]
used_env_names = []

# Users can specify "special keywords" in all string and list fields.
# There are two "special keywords" at the moment: +JOBNAME+ and +JOBID+
# The function replaces these keywords with the runtime assigned jobname and jobid


def replace(inputstr, jobname, jobid):
    output = inputstr.replace('+JOBNAME+', jobname)
    return output.replace('+JOBID+', jobid)


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


def replace_special(global_dict):
    for (key, value) in global_dict.iteritems():
        if isinstance(value, list):
            newlist = []
            for elem in value[:]:
                if type(elem) is types.TupleType:

                    # Environment? tuple

                    (name, val) = elem
                    name = replace(name, global_dict['JOBNAME'],
                                   global_dict['JOB_ID'])
                    val = replace(val, global_dict['JOBNAME'],
                                  global_dict['JOB_ID'])
                    env = (name, val)
                    newlist.append(env)
                elif type(elem) is types.StringType:
                    newlist.append(replace(str(elem),
                                   global_dict['JOBNAME'],
                                   global_dict['JOB_ID']))
                else:

                    # elem was not a tuple/string, dont try to replace

                    newlist.append(elem)
            global_dict[key] = newlist
        elif isinstance(value, str):
            global_dict[key] = replace(str(value), global_dict['JOBNAME'
                    ], global_dict['JOB_ID'])

    return global_dict


def handle_escapes(inputstring):
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

                if char == comment_char:

                    # a comment

                    return new_string
                else:

                    # just a normal char

                    new_string += char
            escape_met = False
    return new_string


def read_block(input_file):
    result = []
    data = True
    while data:

        # read a line
        # readline returns "" string when EOF, to separate EOF and
        # blank lines .strip must be added later

        line = input_file.readline().strip()

        if re.sub('[ \n\t]', '', line) != '':
            line = handle_escapes(line)
            if not line:
                continue
            else:
                line = line.strip()
                if len(line) > 0:
                    result.append(line)
        else:
            data = False
    return result


def parse(mrsl_file):
    data = []
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
        target.append(read_block(input_file))
        data.append(target)

    input_file.close()
    return data


def print_type_error(
    keyword,
    msg,
    keyword_dict,
    keyword_data,
    ):

    keyword_with_colons = '::%s::' % keyword

    out = \
        '<table border=1><tr><td>Keyword</td><td>%s</td></tr><tr><td>Error</td><td>%s</td></tr>'\
         % (keyword_with_colons, msg)
    out += '<tr><td>You supplied</td><td>%s</td></tr>' % keyword_data
    out += '<tr><td>Keyword example</td><td>%s</td></tr>'\
         % keyword_dict['Example']
    out += \
        '<tr><td>Keyword description</td><td>%s</td></tr></table><br>'\
         % keyword_dict['Description']
    out += \
        '''

<!-- ****** INFORMATION ABOUT THE TYPE ERROR IN TEXT FORMAT ******
'''
    out += \
        '''Keyword: %s
Error: %s
You supplied: %s
Keyword example: %s
Keyword description: %s
*******************************************************************
-->
'''\
         % (keyword_with_colons, msg, keyword_data,
            keyword_dict['Example'], keyword_dict['Description'])
    return out


def check_types(parse_output, external_keyword_dict, configuration):
    status = True
    msg = ''

    for keyword_block in parse_output:

        # remove the two colons before and after the keyword

        job_keyword = keyword_block[0].strip(':')
        keyword_data = keyword_block[1]

        if not external_keyword_dict.has_key(job_keyword):
            status = False
            msg += 'unknown keyword: %s\n' % job_keyword
        else:

            # name of keyword ok, check if the type is correct

            keyword_dict = external_keyword_dict[job_keyword]
            keyword_type = keyword_dict['Type']
            value = keyword_dict['Value']

            # Required = keyword_dict["Required"]

            if keyword_type == 'int':
                if not len(keyword_data) == 1:
                    status = False
                    msg += print_type_error(job_keyword,
                            'requires only a single integer',
                            keyword_dict, keyword_data)
                else:
                    try:

                        # assign

                        keyword_dict['Value'] = int(keyword_data[0])
                    except:

                        # could not convert value to int

                        status = False
                        msg += print_type_error(job_keyword,
                                'requires an integer', keyword_dict,
                                keyword_data)
            elif keyword_type == 'string':

                if not keyword_data:

                    # use default value

                    keyword_data.append(keyword_dict['Value'])
                if len(keyword_data) > 1:
                    status = False
                    msg += print_type_error(job_keyword,
                            'requires only a single string',
                            keyword_dict, keyword_data)
                else:
                    try:

                        # assign

                        keyword_dict['Value'] = str(keyword_data[0])
                    except:

                        # could not convert value to string

                        status = False
                        msg += print_type_error(job_keyword,
                                'requires a string', keyword_dict,
                                keyword_data)
                if job_keyword == 'RENAME':

                    # assign in upper case

                    keyword_dict['Value'] = str(keyword_data[0]).upper()
                if job_keyword == 'ARCHITECTURE':
                    if not str(keyword_data[0])\
                         in configuration.architectures:
                        status = False
                        msg += print_type_error(job_keyword,
                                'specified architecture not valid, should be %s'
                                 % configuration.architectures,
                                keyword_dict, keyword_data)
                if job_keyword == 'SCRIPTLANGUAGE':
                    if not str(keyword_data[0])\
                         in configuration.scriptlanguages:
                        status = False
                        msg += print_type_error(job_keyword,
                                'specified scriptlanguage not valid, should be %s'
                                 % configuration.scriptlanguages,
                                keyword_dict, keyword_data)
                if job_keyword == 'JOBTYPE':
                    if not str(keyword_data[0])\
                         in configuration.jobtypes:
                        status = False
                        msg += print_type_error(job_keyword,
                                'specified jobtype not valid, should be %s'
                                 % configuration.jobtypes,
                                keyword_dict, keyword_data)
            elif keyword_type == 'multiplestrings':

                for single_line in keyword_data:
                    try:
                        value.append(str(single_line))
                    except:
                        status = False
                        msg += print_type_error(job_keyword,
                                'requires one or more strings',
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

                    # TODO: avoid recursive imports and put code back in action
                    # from shared.mrslparser import parse
                    # (status, retmsg) = parse(tmpfile, "testprocedure_job_id", "testprocedure_test_parse__cert_name_not_specified", False, outfile="%s.parsed" % tmpfile)

                    msg += \
                        'handling of testprocedures is temporarily disabled!'
                    status = False

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
                    msg += print_type_error(job_keyword,
                            'could not append testprocedure',
                            keyword_dict, keyword_data)
            elif keyword_type == 'multiplekeyvalues':

                for single_line in keyword_data:
                    try:
                        if single_line.find('=') == -1:
                            status = False
                            msg += print_type_error(job_keyword,
                                    "requires one or more key=value rows. '=' not found on line."
                                    , keyword_dict, keyword_data)
                        else:
                            keyval = single_line.split('=', 1)
                            env = (str(keyval[0]), str(keyval[1]))
                            value.append(env)
                    except:
                        status = False
                        msg += print_type_error(job_keyword,
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
                    msg += print_type_error(job_keyword,
                            'Error in sub level parsing: %s'
                             % exe_dict, keyword_dict, keyword_data)

                try:
                    continuous = exe_dict['continuous']

                        # Keep old typo for backwards compatibility

                    if continuous == 'False':
                        exe_dict['continuous'] = False
                        exe_dict['continious'] = exe_dict['continuous']
                    elif continuous == 'True':
                        exe_dict['continuous'] = True
                        exe_dict['continious'] = exe_dict['continuous']
                    else:
                        status = False
                        msg += print_type_error(job_keyword,
                                'continuous must be True or False',
                                keyword_dict, keyword_data)

                    shared_fs = exe_dict['shared_fs']
                    if shared_fs == 'False':
                        exe_dict['shared_fs'] = False
                    elif shared_fs == 'True':
                        exe_dict['shared_fs'] = True
                    else:
                        status = False
                        msg += print_type_error(job_keyword,
                                'shared_fs must be True or False',
                                keyword_dict, keyword_data)

                    vgrid_value = exe_dict['vgrid']

                        # Split between comma and remove extra whitespace

                    exe_dict['vgrid'] = [i.strip() for i in
                            vgrid_value.split(',')]
                    value.append(exe_dict)
                except Exception, err:
                    status = False
                    msg += print_type_error(job_keyword,
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
                    msg += print_type_error(job_keyword,
                            'Error in sub level parsing: %s'
                             % store_dict, keyword_dict, keyword_data)

                supported_protocols = ['sftp']
                try:
                    protocol = store_dict['storage_protocol']
                    if protocol not in supported_protocols:
                        status = False
                        msg += print_type_error(job_keyword,
                                'storage_protocol must be in %s' % supported_protocols,
                                keyword_dict, keyword_data)

                    shared_fs = store_dict['shared_fs']
                    if shared_fs == 'False':
                        store_dict['shared_fs'] = False
                    elif shared_fs == 'True':
                        store_dict['shared_fs'] = True
                    else:
                        status = False
                        msg += print_type_error(job_keyword,
                                'shared_fs must be True or False',
                                keyword_dict, keyword_data)

                    vgrid_value = store_dict['vgrid']

                        # Split between comma and remove extra whitespace

                    store_dict['vgrid'] = [i.strip() for i in
                            vgrid_value.split(',')]
                    value.append(store_dict)
                except Exception, err:
                    status = False
                    msg += print_type_error(job_keyword,
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
                                msg += print_type_error(job_keyword,
                                        "Name of runtime environment not specified after 'name:'"
                                        , keyword_dict, keyword_data)
                        else:

                            # new environment for RE

                            if not name:

                                # Trying to assign value to an unnamed RE

                                status = False
                                msg += print_type_error(job_keyword,
                                        'Trying to assign value to an unnamed runtime environment'
                                        , keyword_dict, keyword_data)
                            if single_line.find('=') == -1:
                                status = False
                                msg += print_type_error(job_keyword,
                                        'Environment values must be on the form: envname=envvalue'
                                        , keyword_dict, keyword_data)

                            # ok

                            keyval = single_line.split('=', 1)
                            env = (keyval[0].strip(), keyval[1].strip())
                            val.append(env)
                    except:
                        status = False
                        msg += print_type_error(job_keyword,
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
                        msg += print_type_error(job_keyword,
                                'Error in sub level parsing: %s'
                                 % software_dict, keyword_dict,
                                keyword_data)
                    else:
                        value.append(software_dict)
                except Exception, err:
                    status = False
                    msg += print_type_error(job_keyword,
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
                            msg += print_type_error(job_keyword,
                                    "Environment name '%s' used more than once."
                                     % env_name, keyword_dict,
                                    keyword_data)
                        used_env_names.append(env_name)

                        value.append(env_vars)
                    else:

                        # sub level parsing error

                        status = False
                        msg += print_type_error(job_keyword,
                                'Error in sub level parsing: %s'
                                 % env_vars, keyword_dict, keyword_data)
                except Exception, err:

                    status = False
                    msg += print_type_error(job_keyword,
                            'Error getting RE_environmentvariable value.'
                            , keyword_dict, keyword_data)
            else:
                status = False
                msg += \
                    'Internal error: Keyword %s with unknown type %s was accepted!'\
                     % (job_keyword, keyword_type)

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


