#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# safeinput - user input validation functions
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

"""This module contains general functions for validating input
to an extent where it can be used in back ends and output
without worrying about XSS vulnerabilities, etc.
"""

import os
from string import letters, digits

from shared.valuecheck import lines_value_checker, \
    max_jobs_value_checker
from shared.validstring import valid_user_path, valid_dir_input

VALID_PATH_CHARACTERS = letters + digits + '/.,_-+='\
     + ' :;+@%\xe6\xf8\xe5\xc6\xd8\xc5'

# Plain text here only - *no* html tags, i.e. no '<' or '>' !!

VALID_TEXT_CHARACTERS = VALID_PATH_CHARACTERS + '?!#$\xa4%&()[]{}*'\
     + '"' + "'`|^~" + '\\' + '\n\r\t'
VALID_FQDN_CHARACTERS = letters + digits + '.-'
VALID_JOB_ID_CHARACTERS = VALID_FQDN_CHARACTERS + '_'
REJECT_UNSET = 'MUST_BE_SET_AND_NO_DEFAULT_VALUE'
ALLOW_UNSAFE = \
    'THIS INPUT IS NOT VERIFIED: DO NOT EVER PRINT IT UNESCAPED! '

# Allow these chars in addition to plain letters and digits

name_extras = ' -'
dn_extras = name_extras + '/=@._'
password_extras = ' -_#.,:;!@%/()[]{}+=?<>'
password_min_len = 4
password_max_len = 64
dn_max_len = 96

valid_password_chars = letters + digits + password_extras
valid_name_chars = letters + digits + name_extras
valid_dn_chars = letters + digits + dn_extras
VALID_PASSWORD_CHARACTERS = valid_password_chars
VALID_NAME_CHARACTERS = valid_name_chars
VALID_DN_CHARACTERS = valid_dn_chars

# Helper functions

# TODO: switch to use similar cgiinput function
# ... only possible when cgiinput no longer imports from here!!


def __html_escape(contents):
    """Uses cgi.escape() to encode contents in a html safe way. In that
    way the resulting data can be included in a html page without risk
    of XSS vulnerabilities.
    """

    # We us html_escape as a general protection even though it is
    # mostly html (cgi) related

    import cgi
    return cgi.escape(contents)


def __valid_contents(
    contents,
    valid_chars,
    min_length=0,
    max_length=-1,
    ):
    """This is a general function to verify that the supplied contents
    only contains characters from the supplied valid_chars string.
    Additionally a check for valid length is supported by use of the
    min_length and max_length parameters.
    """

    contents = str(contents)
    if len(contents) < min_length:
        raise InputException('shorter than minimum length (%d)'
                              % min_length)
    if max_length > 0 and len(contents) > max_length:
        raise InputException('maximum length (%d) exceeded'
                              % max_length)
    for char in contents:
        if not char in valid_chars:
            raise InputException('found invalid character: %s' % char)


def __filter_contents(contents, valid_chars):
    """This is a general function to filter out any illegal characters
    from the supplied contents.
    """

    result = ''
    for char in str(contents):
        if char in valid_chars:
            result += char
    return result


# Public functions


def valid_ascii(contents, min_length=0, max_length=-1):
    """Verify that supplied contents only contain ascii characters"""

    __valid_contents(contents, letters, min_length, max_length)


def valid_numeric(contents, min_length=0, max_length=-1):
    """Verify that supplied contents only contain numeric characters"""

    __valid_contents(contents, digits, min_length, max_length)


def valid_alphanumeric(contents, min_length=0, max_length=-1):
    """Verify that supplied contents only contain alphanumeric characters"""

    __valid_contents(contents, letters + digits, min_length, max_length)


def valid_alphanumeric_and_spaces(contents, min_length=0,
                                  max_length=-1):
    """Verify that supplied contents only contain alphanumeric characters and spaces"""

    __valid_contents(contents, letters + digits + ' ' + '_',
                     min_length, max_length)


def valid_plain_text(
    text,
    min_length=-1,
    max_length=-1,
    extra_chars='',
    ):
    """Verify that supplied text only contains characters that we consider
    valid"""

    valid_chars = VALID_TEXT_CHARACTERS + extra_chars
    __valid_contents(text, valid_chars, min_length, max_length)


def valid_free_text(
    text,
    min_length=-1,
    max_length=-1,
    extra_chars='',
    ):
    """Verify that supplied text only contains characters that we consider
    valid"""

    return True


def valid_path(
    path,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied path only contains characters that we consider
    valid"""

    valid_chars = VALID_PATH_CHARACTERS + extra_chars
    __valid_contents(path, valid_chars, min_length, max_length)


def valid_fqdn(
    fqdn,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied fully qualified domain name only contains
    characters that we consider valid. This check also succeeds for
    the special case where fqdn is really a hostname without domain.
    """

    valid_chars = VALID_FQDN_CHARACTERS + extra_chars
    __valid_contents(fqdn, valid_chars, min_length, max_length)


def valid_commonname(
    commonname,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied commonname only contains
    characters that we consider valid. 
    """

    valid_chars = VALID_NAME_CHARACTERS + '_' + extra_chars
    __valid_contents(commonname, valid_chars, min_length, max_length)


def valid_distinguished_name(
    distinguished_name,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied distinguished_name only contains
    characters that we consider valid. 
    """

    valid_chars = VALID_DN_CHARACTERS + extra_chars
    __valid_contents(distinguished_name, valid_chars, min_length,
                     max_length)


def valid_password(
    password,
    min_length=password_min_len,
    max_length=password_max_len,
    extra_chars='',
    ):
    """Verify that supplied commonname only contains
    characters that we consider valid. 
    """

    valid_chars = VALID_PASSWORD_CHARACTERS + extra_chars
    __valid_contents(password, valid_chars, min_length, max_length)


def valid_sid(
    sid,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied session ID, sid, only contains
    characters that we consider valid. Session IDs are generated using
    hexlify() on a random string, so it only contains valid hexadecimal
    values, i.e. digits and a few ascii letters.
    """

    valid_chars = digits + 'abcdef' + extra_chars
    __valid_contents(sid, valid_chars, min_length, max_length)


def valid_job_id(
    job_id,
    min_length=1,
    max_length=255,
    extra_chars='',
    ):
    """Verify that supplied job ID, only contains characters that we
    consider valid. Job IDs are generated using time and fqdn of server,
    so it only contains FQDN chars and underscores.
    """

    valid_chars = VALID_JOB_ID_CHARACTERS + extra_chars
    __valid_contents(job_id, valid_chars, min_length, max_length)


def valid_path_pattern(
    pattern,
    min_length=1,
    max_length=255,
    extra_chars='.*?',
    ):
    """Verify that supplied pattern only contains characters that
    we consider valid in paths. Valid wild card characters are added
    by default.
    """

    valid_path(pattern, min_length, max_length, extra_chars)


def valid_path_patterns(
    pattern_list,
    min_length=1,
    max_length=255,
    extra_chars='.*?',
    ):
    """Verify that supplied pattern_list only contains characters that
    we consider valid in paths. Valid wild card characters are added
    by default.
    """

    for pattern in pattern_list:
        valid_path(pattern, min_length, max_length, extra_chars)


def valid_job_id_pattern(
    pattern,
    min_length=1,
    max_length=255,
    extra_chars='.*?',
    ):
    """Verify that supplied pattern only contains characters that
    we consider valid in paths. Valid wild card characters are added
    by default.
    """

    valid_job_id(pattern, min_length, max_length, extra_chars)


def valid_job_id_patterns(
    pattern_list,
    min_length=1,
    max_length=255,
    extra_chars='.*?',
    ):
    """Verify that supplied pattern_list only contains characters that
    we consider valid in paths. Valid wild card characters are added
    by default.
    """

    for pattern in pattern_list:
        valid_job_id(pattern, min_length, max_length, extra_chars)


def valid_email_address(addr):
    """From http://www.secureprogramming.com/?action=view&feature=recipes&recipeid=1"""

    rfc822_specials = '()<>@,;:\\"[]'

    # First we validate the name portion (name@domain)

    c = 0
    while c < len(addr):
        if addr[c] == '"' and (not c or addr[c - 1] == '.' or addr[c
                                - 1] == '"'):
            c += 1
            while c < len(addr):
                if addr[c] == '"':
                    break
                if addr[c] == '\\' and addr[c + 1] == ' ':
                    c += 2
                    continue
                if ord(addr[c]) < 32 or ord(addr[c]) >= 127:
                    return False
                c += 1
            else:
                return False
            if addr[c] == '@':
                break
            if addr[c] != '.':
                return False
            c += 1
            continue
        if addr[c] == '@':
            break
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        if addr[c] in rfc822_specials:
            return False
        c += 1
    if not c or addr[c - 1] == '.':
        return False

    # Next we validate the domain portion (name@domain)

    domain = c = c + 1
    if domain >= len(addr):
        return False
    count = 0
    while c < len(addr):
        if addr[c] == '.':
            if c == domain or addr[c - 1] == '.':
                return False
            count += 1
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        if addr[c] in rfc822_specials:
            return False
        c += 1
    return count >= 1


def filter_ascii(contents):
    """Filter supplied contents to only contain ascii characters"""

    return __filter_contents(contents, letters)


def filter_numeric(contents):
    """Filter supplied contents to only contain numeric characters"""

    return __filter_contents(contents, digits)


def filter_alphanumeric(contents):
    """Filter supplied contents to only contain alphanumeric characters"""

    return __filter_contents(contents, letters + digits)


def filter_alphanumeric_and_spaces(contents):
    """Filter supplied contents to only contain alphanumeric characters"""

    return __filter_contents(contents, letters + digits + ' ')


def filter_commonname(contents):
    """Filter supplied contents to only contain valid commonname characters"""

    return __filter_contents(contents, letters + ' ' + '_-')


def filter_plain_text(contents):
    """Filter supplied contents to only contain valid text characters"""

    return __filter_contents(contents, VALID_TEXT_CHARACTERS)


def filter_path(contents):
    """Filter supplied contents to only contain valid path characters"""

    return __filter_contents(contents, VALID_PATH_CHARACTERS)


def filter_fqdn(contents):
    """Filter supplied contents to only contain valid fqdn characters"""

    return __filter_contents(contents, VALID_FQDN_CHARACTERS)


def filter_job_id(contents):
    """Filter supplied contents to only contain valid job ID characters"""

    return __filter_contents(contents, VALID_JOB_ID_CHARACTERS)


def validated_boolean(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a boolean

    default_value = bool(default)
    if default != default_value:
        err += 'Invalid boolean default value (%s)' % default
    result = default_value

    # Transition to string and back enforces valid result even
    # for a string value as 'default' argument

    try:
        first = user_arguments_dict[name][0]

        # Slightly cryptic way of assuring a correct boolean

        if str(default_value).lower() != first.lower():
            result = not default_value
    except:
        pass
    return (result, err)


def validated_string(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:
        valid_alphanumeric(first)
    except InputException, iex:
        err += '%s' % iex
    return (filter_alphanumeric(first), err)


def validated_plain_text(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:

        # valid_alphanumeric_and_spaces(first)

        valid_plain_text(first)
    except InputException, iex:
        err += '%s' % iex

    # return filter_alphanumeric_and_spaces(first), err

    return (filter_plain_text(first), err)


def validated_path(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:

        # valid_alphanumeric_and_spaces(first)

        valid_path(first)
    except InputException, iex:
        err += '%s' % iex

    # return filter_alphanumeric_and_spaces(first), err

    return (filter_path(first), err)


def validated_fqdn(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:
        valid_fqdn(first)
    except InputException, iex:
        err += '%s' % iex
    return (filter_fqdn(first), err)


def validated_commonname(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:
        valid_commonname(first)
    except InputException, iex:
        err += '%s' % iex
    return (filter_commonname(first), err)


def validated_password(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:
        valid_password(first)
    except InputException, iex:
        err += '%s' % iex
    return (filter_commonname(first), err)


def validated_integer(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    try:
        default_value = int(default)
    except:
        err += 'Invalid string default value (%s)' % default
        default_value = -42
    try:
        first = user_arguments_dict[name][0]
    except Exception:
        first = default_value

    # Validate input

    try:
        valid_numeric(first)
        return (int(first), err)
    except InputException, iex:
        err += '%s' % iex
    filtered = filter_numeric(first)
    if filtered:

        # At least one integer in input

        return (int(filtered), err)
    else:
        return (default_value, err)


def validated_job_id(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = str(default)
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = str(default)

    # Validate input

    try:
        valid_job_id(first)
    except InputException, iex:
        err += '%s' % iex
    return (filter_job_id(first), err)


def guess_type(name):
    """Maps variable names to expected types"""

    if name.find('path') != -1:
        return valid_path_pattern
    elif name.find('job_id') != -1:
        return valid_job_id_pattern
    elif name.find('flags') != -1:
        return valid_ascii
    elif name.find('max_jobs') != -1:
        return valid_numeric
    elif name.find('lines') != -1:
        return valid_numeric
    elif name.find('cputime') != -1:
        return valid_numeric
    elif name.find('unique_resource_name') != -1:
        return valid_fqdn
    elif name.find('exe_name') != -1:
        return valid_fqdn
    elif name.find('cert_name') != -1:
        return valid_commonname
    elif name.find('cert_id') != -1:
        return valid_distinguished_name
    elif name.find('vgrid_name') != -1:
        return valid_path
    elif name.find('re_name') != -1:
        return valid_job_id
    elif name.find('re_template') != -1:
        return valid_job_id
    elif name.find('src') != -1:
        return valid_path_pattern
    elif name.find('dst') != -1:
        return valid_path_pattern
    elif name.find('size') != -1:
        return valid_numeric
    elif name.find('request_text') != -1:
        return valid_plain_text
    elif name.find('AOL') != -1:
        return valid_email_address
    elif name.find('YAHOO') != -1:
        return valid_email_address
    elif name.find('MSN') != -1:
        return valid_email_address
    elif name.find('ICQ') != -1:
        return valid_email_address
    elif name.find('JABBER') != -1:
        return valid_email_address
    elif name.find('EMAIL') != -1:
        return valid_email_address
    elif name.find('resconfig') != -1:
        return valid_plain_text
    elif name.find('redescription') != -1:
        return valid_plain_text
    elif name.find('testprocedure') != -1:
        return valid_plain_text
    elif name.find('environment') != -1:
        return valid_plain_text
    elif name.find('software') != -1:
        return valid_plain_text
    elif name.find('verifystdout') != -1:
        return valid_plain_text
    elif name.find('verifystderr') != -1:
        return valid_plain_text
    elif name.find('verifystatus') != -1:
        return valid_plain_text
    elif name.find('editarea') != -1:
        return valid_free_text
    elif name.find('software_entries') != -1:
        return valid_numeric
    elif name.find('environment_entries') != -1:
        return valid_numeric
    elif name.find('testprocedure_entry') != -1:
        return valid_numeric
    elif name.find('current_dir') != -1:
        return valid_path_pattern
    elif name.find('search') != -1:
        return valid_job_id_pattern
    elif name.find('show') != -1:
        return valid_job_id_pattern
    elif name.find('country') != -1:
        return valid_ascii
    elif name.find('state') != -1:
        return valid_ascii
    elif name.find('email') != -1:
        return valid_email_address
    elif name.find('comment') != -1:
        return valid_plain_text
    elif name.find('password') != -1:
        return valid_password
    elif name.find('verifypassword') != -1:
        return valid_password
    elif name.find('cmd') != -1:
        return valid_path_pattern
    elif name.find('pattern') != -1:
        return valid_path_pattern
    elif name.find('name') != -1:
        return valid_job_id_pattern
    elif name.find('lang') != -1:
        return valid_job_id
    elif name.find('EXECUTE') != -1:
        return valid_plain_text
    elif name.find('EXECUTABLES') != -1:
        return valid_plain_text
    elif name.find('INPUTFILES') != -1:
        return valid_plain_text
    elif name.find('OUTPUTFILES') != -1:
        return valid_plain_text
    elif name.find('VERIFYFILES') != -1:
        return valid_plain_text
    elif name.find('NOTIFY') != -1:
        return valid_plain_text
    elif name.find('VGRID') != -1:
        return valid_plain_text
    elif name.find('RUNTIMEENVIRONMENT') != -1:
        return valid_plain_text
    elif name.find('width') != -1:
        return valid_numeric
    elif name.find('height') != -1:
        return valid_numeric
    elif name.find('depth') != -1:
        return valid_numeric
    elif name.find('desktopname') != -1:
        return valid_ascii
    else:

    # TODO: extend to include all used variables here

        return valid_alphanumeric


def guess_value(name):
    """Maps variable names to expected values"""

    if name.find('lines') != -1:
        return lines_value_checker
    elif name.find('max_jobs') != -1:
        return max_jobs_value_checker
    else:
        return id


def validated_input(
    input_dict,
    defaults,
    type_override={},
    value_override={},
    ):
    """Intelligent input validation with fall back default values.
    Specifying a default value of REJECT_UNSET, results in the
    variable being rejected if no value is found.
    """

    type_checks = {}
    value_checks = {}

    for name in defaults.keys():
        if type_override.has_key(name):
            type_checks[name] = type_override[name]
        else:
            type_checks[name] = guess_type(name)
        if value_override.has_key(name):
            value_checks[name] = value_override[name]
        else:
            value_checks[name] = guess_value(name)
    (accepted, rejected) = validate_helper(input_dict, defaults.keys(),
            type_checks, value_checks)

    # Fall back to defaults when allowed and reject if required and unset

    for (key, val) in defaults.items():
        if REJECT_UNSET != val:
            if not accepted.has_key(key):
                accepted[key] = val
        else:
            if not accepted.has_key(key) and not rejected.has_key(key):
                rejected[key] = (key, ['is required but missing', ''])

    return (accepted, rejected)


def validate_helper(
    input_dict,
    fields,
    type_checks,
    value_checks,
    ):
    """This function takes a dictionary of user input as returned by
    fieldstorage_to_dict and validates all fields according to
    type_checks and value_checks.
    Type checks are functions that must throw an exception if the
    supplied value doesn't fit with the expected type.
    Value checks are functions that must throw an exception if the
    supplied value is not within valid 'range'.
    
    The return value is a tuple containing:
    - a dictionary of accepted fields and their value list
    - a dictionary of rejected fields and their (value, error)-list

    Please note that all expected variable names must be included in
    the fields list in order to be accepted.
    """

    accepted = {}
    rejected = {}
    for (key, values) in input_dict.items():
        ok_values = []
        bad_values = []
        for entry in values:
            if not key in fields:
                err = 'unexpected field: %s' % key
                bad_values.append((__html_escape(entry),
                                  __html_escape(str(err))))
                continue
            if not type_checks.has_key(key):

                # No type check - just accept as is

                continue
            try:
                type_checks[key](entry)
            except Exception, err:

                # Probably illegal type hint

                bad_values.append((__html_escape(entry),
                                  __html_escape(str(err))))
                continue
            if not value_checks.has_key(key):

                # No value check - just accept as is

                continue
            try:
                value_checks[key](entry)
            except Exception, err:

                # Value check failed

                bad_values.append((__html_escape(entry),
                                  __html_escape(str(err))))
                continue
            ok_values.append(entry)
        if ok_values:
            accepted[key] = ok_values
        if bad_values:
            rejected[key] = bad_values
    return (accepted, rejected)


class InputException(Exception):

    """Shared input validation exception"""

    def __init__(self, value):
        """Init InputException"""

        Exception.__init__(self)
        self.value = value

    def __str__(self):
        """Return string representation"""

        return repr(self.value)


