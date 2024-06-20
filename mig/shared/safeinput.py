#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# safeinput - user input validation functions
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

The valid characters are defined in utf8 encoding but the validations work on
unicode decoded strings since a single character may take up multiple bytes in
the byte string version and we want to validate on a character by character
basis.
"""

from __future__ import print_function
from __future__ import absolute_import

import re
import sys
from email.utils import parseaddr, formataddr
from string import ascii_letters, digits, printable
from unicodedata import category, normalize, name as unicode_name

try:
    import nbformat
except ImportError:
    nbformat = None

PY2 = sys.version_info[0] < 3

escape_html = None
if PY2:
    from cgi import escape as escape_html
else:
    from html import escape as escape_html
assert escape_html is not None

from mig.shared.base import force_unicode, force_utf8
from mig.shared.defaults import src_dst_sep, username_charset, \
    username_max_length, session_id_charset, session_id_length, \
    subject_id_charset, subject_id_min_length, subject_id_max_length, \
    workflow_id_length, MAX_SWEEP, maxfill_fields
from mig.shared.listhandling import frange
from mig.shared.validstring import valid_user_path, silent_email_validator
from mig.shared.valuecheck import lines_value_checker, \
    max_jobs_value_checker

VALID_WORKFLOW_ATTRIBUTES = [
    'persistence_id',
    'vgrid',
    'name',
    'input_file',
    'input_paths'
    'output',
    'recipes',
    'variables',
    'parameterize_over'
]

VALID_WORKFLOW_ENVIRONMENT = [
    'nodes',
    'cpu cores',
    'wall time',
    'memory',
    'disks',
    'retries',
    'cpu-architecture',
    'fill',
    'environment variables',
    'notification',
    'runtime environments'
]

PARAM_START = 'start'
PARAM_STOP = 'stop'
PARAM_JUMP = 'increment'

VALID_PARAM_OVER_ATTRIBUTES = [
    PARAM_START,
    PARAM_STOP,
    PARAM_JUMP
]

VALID_JOB_ATTRIBUTES = [
    'job_id',
    'vgrid'
]

# Accented character constant helpers - the allowed set of accented characters
# is chosen based which of these constants is used as the include_accented
# option to some of the validator functions.
NO_ACCENTED, COMMON_ACCENTED, ANY_ACCENTED = range(3)

# Unicode letter categories as defined on
# http://www.unicode.org/reports/tr44/#GC_Values_Table
# TODO: should we go all in and allow even these very exotic modifiers?
#_ACCENT_CATS = frozenset(('Lu', 'Ll', 'Lt', 'Lm', 'Lo', ))
_ACCENT_CATS = frozenset(('Lu', 'Ll', 'Lt', ))

# Use utf8 byte string representation here ("something" and not u"something")
# We explicitly translate to the unicode representation in the functions

# These are the ascii plus most common accented letters in utf8 for names:
# http://practicaltypography.com/common-accented-characters.html
# ./getglyphs.py http://practicaltypography.com/common-accented-characters.html
# found glyphs: áÁàÀâÂäÄãÃåÅæÆçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔöÖõÕøØœŒßúÚùÙûÛüÜ
# Explicitly add a few common Northern Atlantic chars as requested in issue 35.

VALID_ACCENTED = \
    'áÁàÀâÂäÄãÃåÅæÆçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔöÖõÕøØœŒßúÚùÙûÛüÜ' + 'ıİ' + 'ÐðÝýÞþ'

# NOTE: we carefully avoid shell interpretation of dollar everywhere

CURRENCY = '¤$€£¢¥₣₤'

# We must be careful about characters that have special regex meaning

VALID_SAFE_PATH_CHARACTERS = ascii_letters + digits + "/.,_-+="
VALID_PATH_CHARACTERS = ascii_letters + digits + CURRENCY + "/.,_-+±×÷=½¾" + \
    " " + "'" + ":;@§%‰()~!&¶"

# Plain text here only - *no* html tags, i.e. no '<' or '>' !!

VALID_TEXT_CHARACTERS = VALID_PATH_CHARACTERS + CURRENCY + '?#*[]{}' + '"' + \
    "`|^" + '\\' + '\n\r\t'
VALID_FQDN_CHARACTERS = ascii_letters + digits + '.-'
VALID_BACKEND_NAME_CHARACTERS = ascii_letters + digits + '-_'
VALID_BASEURL_CHARACTERS = VALID_FQDN_CHARACTERS + ':/_'
VALID_URL_CHARACTERS = VALID_BASEURL_CHARACTERS + '?;&%='
# According to https://tools.ietf.org/html/rfc3986#section-2 URLs may contain
# '%'-encoded chars, alphanum chars and query chars "-._~:/?#[]@!$&'()*+,;=`."
VALID_COMPLEXURL_CHARACTERS = VALID_BASEURL_CHARACTERS + \
    "%-._~:/?#[]@!$&'()*+,;=`."
VALID_JOB_ID_CHARACTERS = VALID_FQDN_CHARACTERS + '_'
VALID_JOB_NAME_CHARACTERS = VALID_FQDN_CHARACTERS + '_+@%'
VALID_BASE_VGRID_NAME_CHARACTERS = VALID_FQDN_CHARACTERS + '_ '
VALID_VGRID_NAME_CHARACTERS = VALID_BASE_VGRID_NAME_CHARACTERS + '/'
VALID_ARCHIVE_NAME_CHARACTERS = VALID_FQDN_CHARACTERS + '_ '
# Do not allow space in cloud labels as it makes ssh helpers cumbersome
VALID_CLOUD_LABEL_CHARACTERS = VALID_FQDN_CHARACTERS + '+_=@'
# We do allow space in image names
VALID_CLOUD_NAME_CHARACTERS = VALID_CLOUD_LABEL_CHARACTERS + ' '
VALID_CLOUD_INSTANCE_ID_CHARACTERS = VALID_CLOUD_NAME_CHARACTERS + ':'
REJECT_UNSET = 'MUST_BE_SET_AND_NO_DEFAULT_VALUE'
ALLOW_UNSAFE = \
    'THIS INPUT IS NOT VERIFIED: DO NOT EVER PRINT IT UNESCAPED! '

# Allow these chars in addition to plain letters and digits
# We explicitly allow email chars in CN to work around broken DNs

# *****************************************************************************
# * IMPORTANT: never allow '+' or '_' in name: reserved for path translation! *
# *****************************************************************************

# NOTE: only real name extra chars here
name_extras = ' -.'
# NOTE: organization may also contain comma as in UNIVERSITY, DEPARTMENT
org_extras = name_extras + ','

# NOTE: We may encounter exotic chars in roles e.g. from AD
# IMPORTANT: never use role values in shell commands!
role_extras = name_extras + ',_!#^~'

# *****************************************************************************
# * IMPORTANT: never allow '+' in DN: reserved for path translation!          *
# *****************************************************************************
# We allow ':' in DN, however, as it is used by e.g. DanID:
# /C=DK/O=Ingen organisatorisk tilknytning/CN=${NAME}/serialNumber=PID:${SERIAL}
# Similarly we must allow '_' in DN since it is valid in emailAddress. We only
# need to make sure it doesn't appear in name parts above.

# NOTE: org_extras includes name_extras, and we add @ for email part.
dn_extras = org_extras + '/=:_@'

# Allow explicit sign and exponential notation in integers and floats
integer_extras = '+-eE'
float_extras = integer_extras + '.'
password_extras = ' -_#.,:;!@%/()[]{}+=?<>'
# Absolute length limits for all passwords - further restricted in backends
password_min_len = 4
password_max_len = 256
dn_max_len = 96

valid_integer_chars = digits + integer_extras
valid_float_chars = digits + float_extras
valid_password_chars = ascii_letters + digits + password_extras
valid_name_chars = ascii_letters + digits + name_extras
valid_org_chars = ascii_letters + digits + org_extras
valid_dn_chars = ascii_letters + digits + dn_extras
valid_username_chars = username_charset
valid_role_chars = ascii_letters + digits + role_extras
VALID_INTEGER_CHARACTERS = valid_integer_chars
VALID_FLOAT_CHARACTERS = valid_float_chars
VALID_PASSWORD_CHARACTERS = valid_password_chars
VALID_NAME_CHARACTERS = valid_name_chars
VALID_ORG_CHARACTERS = valid_org_chars
VALID_DN_CHARACTERS = valid_dn_chars
VALID_USERNAME_CHARACTERS = valid_username_chars
VALID_ROLE_CHARACTERS = valid_role_chars

# Helper functions and variables

# Type and value guess helpers - filled first time used

__type_map = {}
__value_map = {}


# TODO: consider switching to a re.match with a precompiled expression
# Should be more efficient and would ease any-unicode-word character matching
# >>> extras="/.,_-+= :;+@%()~¶!"
# >>> name_regex = re.compile(r'('+extras+r'|\w)+$', re.U)
# >>> print name_regex.match(u"ab$c")
# None
# >>> print name_regex.match(u"áÁàÀâÂäÄãÃåÅæÆçÇéÉèÈêÊëËíÍìÌîÎïÏñÑóÓòÒôÔöÖõÕø")
# <_sre.SRE_Match object at 0x7f671ad53d78>

def __valid_contents(
    contents,
    valid_chars,
    min_length=0,
    max_length=-1,
    include_accented=NO_ACCENTED,
    unicode_normalize=False,
):
    """This is a general function to verify that the supplied contents string
    only contains characters from the supplied valid_chars string. Both input
    strings are on byte string format but we explicitly convert to unicode
    first to compare full character by character and avoid comparing single
    bytes from multibyte characters.
    Additionally a check for valid length is supported by use of the
    min_length and max_length parameters.
    The optional include_accented argument can be set to COMMON_ACCENTED to
    automatically add the most common accented unicode characters to
    valid_chars or to ANY_ACCENTED to do a more loose check against all
    characters considered unicode word letters before giving up. This adds a
    wider acceptance of exotic accented characters without letting through any
    control characters.
    The optional unicode_normalize argument is used to first force any
    decomposed unicode characters to the Normal Form Composed (NFC) version.
    This is typically useful when certain language setups in e.g. OS X write
    the Danish letter 'å' as an 'a' followed by the 'combining-dot' code. For
    more background information please refer to something like:
    http://en.wikipedia.org/wiki/Unicode_equivalence
    """

    contents = force_unicode(contents)
    if unicode_normalize:
        contents = normalize('NFC', contents)
    valid_chars = force_unicode(valid_chars)
    accented_chars = force_unicode(VALID_ACCENTED)
    if len(contents) < min_length:
        raise InputException('shorter than minimum length (%d)'
                             % min_length)
    if max_length > 0 and len(contents) > max_length:
        raise InputException('maximum length (%d) exceeded'
                             % max_length)
    for char in contents:
        if char in valid_chars or \
           include_accented == COMMON_ACCENTED and char in accented_chars or \
           include_accented == ANY_ACCENTED and category(char) in _ACCENT_CATS:
            continue
        raise InputException("found invalid character: %r (allowed: %s)"
                             % (char, valid_chars))


def __filter_contents(contents, valid_chars, include_accented=NO_ACCENTED,
                      illegal_handler=None, unicode_normalize=False):
    """This is a general function to filter out any illegal characters
    from the supplied contents.
    Please see the documentation for __valid_contents for information about
    the optional include_accented argument.
    The optional illegal_handler option can be used to replace any illegal
    characters with the output of the call illegal_handler(char). The default
    None value results in simply skipping illegal characters.
    Please refer to __valid_contents doc-string for an explanation of the
    unicode_normalize argument.
    """

    contents = force_unicode(contents)
    if unicode_normalize:
        contents = normalize('NFC', contents)
    valid_chars = force_unicode(valid_chars)
    accented_chars = force_unicode(VALID_ACCENTED)
    result = ''
    for char in contents:
        if char in valid_chars or \
           include_accented == COMMON_ACCENTED and char in accented_chars or \
           include_accented == ANY_ACCENTED and category(char) in _ACCENT_CATS:
            result += char
        elif illegal_handler:
            result += illegal_handler(char)
    return result


def __wrap_unicode_name(char):
    """Build __NAME__ where NAME is the unicodedata name for the char"""
    return '__%s__' % unicode_name(force_unicode(char))


def __wrap_unicode_val(char):
    """Build __uVAL__ where VAL is the unicode code point for the char"""
    return '__u%s__' % ord(force_unicode(char))


# Public functions

def html_escape(contents, quote=None):
    """Use an stdlib escape to encode contents in a html safe way. In that
    way the resulting data can be included in a html page without risk
    of XSS vulnerabilities.
    The optional quote argument is passed as-is to enable additional escaping
    of single and double quotes.
    """

    # We use html_escape as a general protection even though it is
    # mostly html request related

    return escape_html(contents, quote)


def valid_printable(contents, min_length=0, max_length=-1):
    """Verify that supplied contents only contain ascii characters
    (where 'ascii characters' means printable ASCII, not just letters)"""

    __valid_contents(contents, printable, min_length, max_length)


def valid_ascii(contents, min_length=0, max_length=-1, extra_chars=''):
    """Verify that supplied contents only contain ascii characters"""

    __valid_contents(
        contents, ascii_letters + extra_chars, min_length, max_length)


def valid_numeric(contents, min_length=0, max_length=-1):
    """Verify that supplied contents only contain numeric characters"""

    __valid_contents(contents, digits, min_length, max_length)


def valid_alphanumeric(contents, min_length=0, max_length=-1, extra_chars=''):
    """Verify that supplied contents only contain alphanumeric characters"""

    __valid_contents(
        contents, ascii_letters + digits + extra_chars, min_length,
        max_length)


def valid_alphanumeric_and_spaces(contents, min_length=0, max_length=-1,
                                  extra_chars=''):
    """Verify that supplied contents only contain alphanumeric characters and
    spaces"""

    valid_alphanumeric(contents, min_length, max_length, ' ' + extra_chars)


def valid_date(contents, min_length=10, max_length=10):
    """Verify that supplied contents only contain something like DD-MM-YYYY
    date characters"""

    __valid_contents(contents, digits + '-/', min_length,
                     max_length)


def valid_plain_text(
    text,
    min_length=-1,
    max_length=-1,
    extra_chars='',
):
    """Verify that supplied text only contains characters that we consider
    valid"""

    valid_chars = VALID_TEXT_CHARACTERS + extra_chars
    __valid_contents(text, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


def valid_label_text(
    text,
    min_length=-1,
    max_length=-1,
    extra_chars='',
):
    """Verify that supplied text only contains characters that we consider
    valid"""

    valid_chars = ascii_letters + digits + extra_chars
    __valid_contents(text, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


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
    max_length=4096,
    extra_chars='',
):
    """Verify that supplied path only contains characters that we consider
    valid"""

    valid_chars = VALID_PATH_CHARACTERS + extra_chars
    __valid_contents(path, valid_chars, min_length, max_length, ANY_ACCENTED,
                     unicode_normalize=True)


def valid_safe_path(
    path,
    min_length=1,
    max_length=1024,
    extra_chars='',
):
    """Verify that supplied path only contains characters that we consider
    valid and shell safe"""

    valid_chars = VALID_SAFE_PATH_CHARACTERS + extra_chars
    __valid_contents(path, valid_chars, min_length, max_length, NO_ACCENTED)


def valid_path_src_dst_lines(
    path,
    min_length=0,
    max_length=4096,
    extra_chars='',
):
    """Verify that supplied path only contains characters that we consider
    valid for the src or src dst format used in job descriptions.
    """
    # Always allow separator char(s) and newlines
    extra_chars += src_dst_sep + '\r\n'
    return valid_path(path, min_length, max_length, extra_chars)


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

    valid_chars = VALID_NAME_CHARACTERS + extra_chars
    __valid_contents(commonname, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


def valid_organization(
    organization,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied organization name only contains
    characters that we consider valid.
    """

    valid_chars = VALID_ORG_CHARACTERS + extra_chars
    __valid_contents(organization, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


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
                     max_length, COMMON_ACCENTED)


def valid_username(
    username,
    min_length=1,
    max_length=username_max_length,
    extra_chars='',
):
    """Verify that supplied username only contains
    characters that we consider valid.
    NOTE: we use min_length 1 here since it also covers remote unix user names
    """

    valid_chars = VALID_USERNAME_CHARACTERS + extra_chars
    __valid_contents(username, valid_chars, min_length, max_length)


def valid_role(
    role,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied role name only contains
    characters that we consider valid.
    """

    valid_chars = VALID_ROLE_CHARACTERS + extra_chars
    __valid_contents(role, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


def valid_base_url(
    base_url,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied base_url only contains
    characters that we consider valid.
    """

    valid_chars = VALID_BASEURL_CHARACTERS + extra_chars
    __valid_contents(base_url, valid_chars, min_length, max_length)


def valid_url(
    url,
    min_length=1,
    max_length=1024,
    extra_chars='',
):
    """Verify that supplied url only contains
    characters that we consider valid.
    """

    valid_chars = VALID_URL_CHARACTERS + extra_chars
    __valid_contents(url, valid_chars, min_length, max_length)


def valid_complex_url(
    url,
    min_length=1,
    max_length=1024,
    extra_chars='',
):
    """Verify that supplied url only contains
    characters that we consider valid.
    IMPORTANT: only use where URLs are not used carelessly in shell commands!
               For almost all cases the valid_url function should do.
    """

    valid_chars = VALID_COMPLEXURL_CHARACTERS + extra_chars
    __valid_contents(url, valid_chars, min_length, max_length)


def valid_integer(
    contents,
    min_length=0,
    max_length=-1,
    extra_chars='',
):
    """Verify that supplied integer only contain valid characters"""

    valid_chars = VALID_INTEGER_CHARACTERS + extra_chars
    __valid_contents(contents, valid_chars, min_length, max_length)


def valid_float(
    contents,
    min_length=0,
    max_length=-1,
    extra_chars='',
):
    """Verify that supplied contents only contain float characters"""

    valid_chars = VALID_FLOAT_CHARACTERS + extra_chars
    __valid_contents(contents, valid_chars, min_length, max_length)


def valid_password(
    password,
    min_length=password_min_len,
    max_length=password_max_len,
    extra_chars='',
):
    """Verify that supplied password only contains
    characters that we consider valid.
    """

    valid_chars = VALID_PASSWORD_CHARACTERS + extra_chars
    __valid_contents(password, valid_chars, min_length, max_length,
                     COMMON_ACCENTED)


def valid_backend_name(
    backend_name,
    min_length=1,
    max_length=64,
    extra_chars='',
):
    """Verify that supplied backend name, only contains characters that we
    consider valid. Backend names are (potentially) user provided names of
    modules from the shared/functionality directory.
    """

    valid_chars = VALID_BACKEND_NAME_CHARACTERS + extra_chars
    __valid_contents(backend_name, valid_chars, min_length, max_length)


def valid_sid(
    sid,
    min_length=session_id_length,
    max_length=session_id_length,
    extra_chars='',
):
    """Verify that supplied session ID, sid, is expected length and only
    contains characters that we consider valid. Session IDs are generated
    using hexlify() on a random string, so it only contains valid hexadecimal
    values, i.e. digits and a few ascii letters.
    """

    valid_chars = session_id_charset + extra_chars
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


def valid_job_name(
    job_name,
    min_length=0,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied job name, only contains characters that we
    consider valid. Job names are user provided names possibly with common
    special characters.
    """

    valid_chars = VALID_JOB_NAME_CHARACTERS + extra_chars
    __valid_contents(job_name, valid_chars, min_length, max_length)


def valid_subject_id(
    subject_id,
    min_length=subject_id_min_length,
    max_length=subject_id_max_length,
    extra_chars='',
):
    """Verify that supplied subject ID is expected length and only contains
    characters that we consider valid. Subject IDs are ID Provider unique user
    IDs and may use different formats including some that resemble email
    addresses and others that are more like a simple random ascii string.
    """

    valid_chars = subject_id_charset + extra_chars
    __valid_contents(subject_id, valid_chars, min_length, max_length)


def valid_backup_names(
    names,
    min_length=0,
    max_length=4096,
    extra_chars='',
):
    """Verify that supplied names only contains characters that we consider
    valid for multiline backup names. I.e. we reuse job_name but with with
    addition of newlines and extended length. We do NOT allow slashes in names
    as they would interfere with our json path handling and potentially lead
    to illegal path traversal.
    """
    # Always allow newlines
    extra_chars += '\r\n'
    return valid_job_name(names, min_length, max_length, extra_chars)


def valid_base_vgrid_name(
    vgrid_name,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied root VGrid name, only contains characters that we
    consider valid. Root VGrid names are user provided names possibly with common
    special characters.
    """

    valid_chars = VALID_BASE_VGRID_NAME_CHARACTERS + extra_chars
    __valid_contents(vgrid_name, valid_chars, min_length, max_length)


def valid_vgrid_name(
    vgrid_name,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied VGrid name, only contains characters that we
    consider valid. VGrid names are user provided names possibly with common
    special characters.
    """

    valid_chars = VALID_VGRID_NAME_CHARACTERS + extra_chars
    __valid_contents(vgrid_name, valid_chars, min_length, max_length)


def valid_archive_name(
    archive_name,
    min_length=1,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied archive name, only contains characters that we
    consider valid. Archive names are user provided names possibly with common
    special characters.
    """

    valid_chars = VALID_ARCHIVE_NAME_CHARACTERS + extra_chars
    __valid_contents(archive_name, valid_chars, min_length, max_length)


def valid_path_pattern(
    pattern,
    min_length=1,
    max_length=4096,
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
    max_length=4096,
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


def valid_user_path_name(
    safe_path,
    path,
    home_dir,
    allow_equal=False,
):
    """Wrap valid_user_path and valid_path name checks in one to check both
    destination dir and filename characters. Returns error using safe_path if
    validation fails.
    NOTE: path MUST already be abs-expanded for valid_user_path to succeed.
    """

    (status, msg) = (True, '')
    try:
        valid_path(path)
    except InputException as iex:
        status = False
        msg = 'Invalid path! (%s: %s)' % (safe_path, iex)
    # Automatic configuration extraction
    configuration = None
    if not valid_user_path(configuration, path, home_dir, allow_equal):
        status = False
        msg = 'Invalid path! (%s expands to illegal path)' % safe_path
    return (status, html_escape(msg))


def valid_email_address(addr, allow_real_name=True):
    """Conservative email check using parseaddr and formataddr from email.utils
    in the standard library to validate both characters and format.
    We basically check that the address parses with parseaddr *and* that the
    resulting real name and address parts result in the original address when
    passed to formataddr. If not one or more illegal characters have been
    filtered out or the address is incompliant in other ways.
    NOTE: Extra spaces may yield false positives, but better safe than sorry!
    We manualy check that address contains '@' since it is not strictly
    required by parseaddr.
    The optional allow_real_name option is used to extend the check to include
    addresses on the full RFC format with a real name followed by the plain
    address enclosed in less-than and greater-than sign like:
    John Doe <john@doe.org>
    """

    (real_name, plain_addr) = name_address_pair = parseaddr(addr)
    if real_name and not allow_real_name:
        raise InputException("Only plain addresses without name allowed")
    if not silent_email_validator(plain_addr):
        raise InputException("No actual email address included")
    merged = formataddr(name_address_pair)
    if merged != addr:
        raise InputException("Invalid email format")


def valid_simple_email_address(addr):
    """Simple email address check only accepting plain address without real
    name prefix or anything.
    """
    valid_email_address(addr, False)


def valid_email_addresses(addresses, allow_real_name=False, delimiter=None):
    """Parse one or more delimiter-separated email addresses contained in a
    single string. Useful e.g. for checking input fields and textarea for
    one or more emails. If delimiter is None any white-space string is a
    separator and empty strings are removed from the result.
    """
    for addr in addresses.split(delimiter):
        valid_email_address(addr.strip(), allow_real_name)


def is_valid_simple_email(addr):
    """Helper for quick testing of plain email address validity"""
    try:
        valid_simple_email_address(addr)
        return True
    except InputException:
        return False


def __valid_gdp_var(gdp_var):
    """Verify that supplied gdp_var only contains characters that
    we consider valid in various gdp variable names.
    """
    __valid_contents(gdp_var, ascii_letters + '_')


def valid_gdp_category_id(category_id):
    """Verify that supplied category_id only contains characters that
    we consider valid in GDP categories.
    """
    __valid_gdp_var(category_id)


def valid_gdp_ref_id(ref_id):
    """Verify that supplied ref_id only contains characters that
    we consider valid in GDP ref IDs.
    """
    __valid_gdp_var(ref_id)


def valid_gdp_ref_value(ref_value):
    """Verify that supplied ref_value only contains characters that
    we consider valid in GDP ref values.
    """
    __valid_contents(ref_value, ascii_letters + digits + '+-=/.:_')


def valid_cloud_instance_id(
    instance_id,
    min_length=0,
    max_length=255,
    extra_chars='',
):
    """Verify that supplied instance ID, only contains characters that we
    consider valid. Cloud IDs are generated using user email and user specified
    name and a session ID, so it may contain FQDN chars, email chars and simple
    separators.
    """

    valid_chars = VALID_CLOUD_INSTANCE_ID_CHARACTERS + extra_chars
    __valid_contents(instance_id, valid_chars, min_length, max_length)


def valid_cloud_label(
    cloud_label,
    min_length=0,
    max_length=64,
    extra_chars='',
):
    """Verify that supplied cloud instance label, only contains characters that
    we consider valid. Cloud labels are entered by users, so they should be
    relatively flexible.
    IMPORTANT: We avoid colon (:) and space to avoid collisions with the saved
    instance_id format and to avoid ssh choking on word breaks.
    """

    valid_chars = VALID_CLOUD_LABEL_CHARACTERS + extra_chars
    __valid_contents(cloud_label, valid_chars, min_length, max_length)


def valid_cloud_name(
    cloud_name,
    min_length=0,
    max_length=64,
    extra_chars='',
):
    """Verify that supplied cloud name, only contains characters that we
    consider valid. Cloud names are the colon-separated parts contained in
    cloud instance_id and they are either decided by cloud admins or entered
    by users, so they should be relatively flexible.
    IMPORTANT: We avoid colon (:) to avoid collisions with the saved
    instance_id format.
    """

    valid_chars = VALID_CLOUD_NAME_CHARACTERS + extra_chars
    __valid_contents(cloud_name, valid_chars, min_length, max_length)


def valid_workflow_pers_id(persistence_id):
    """Verify that supplied persistence_id only contains characters that
    we consider valid in a workflow persistence id.
    """
    valid_sid(persistence_id, workflow_id_length, workflow_id_length)


def valid_workflow_vgrid(vgrid):
    """Verify that supplied vgrid only contains characters that
    we consider valid in a workflow vgrid name.
    """
    valid_vgrid_name(vgrid)


def valid_workflow_name(name):
    """Verify that supplied name only contains characters that
    we consider valid in a workflow name.
    """
    valid_alphanumeric(name, extra_chars='+-=:_-')


def valid_workflow_input_file(ifile):
    """Verify that supplied ifile value only contains characters that
    we consider valid in a workflow ifile variable value.
    """
    valid_alphanumeric(ifile, extra_chars='+-=:_-')


def valid_workflow_input_paths(paths):
    """Verify that supplied input paths only contains characters that
    we consider valid workflow input paths.
    """
    valid_path_patterns(paths, min_length=0)


def valid_workflow_output(output):
    """Verify that supplied output dictionary only contains characters that
    we consider valid workflow output key value pairs.
    """
    if not isinstance(output, dict):
        raise InputException("Workflow attribute 'output' must be "
                             "of type 'dict'. Was given %s. " % type(output))
    for o_key, o_value in output.items():
        # Validate that the output key is a variable
        # name compliant string
        valid_alphanumeric(o_key, extra_chars='_')
        valid_path_pattern(o_value, min_length=0, extra_chars='{}')


def valid_workflow_recipes(recipes):
    """Verify that supplied recipes list only contains characters that
    we consider a valid workflow recipe for each entry.
    """
    if not isinstance(recipes, list):
        raise InputException("Workflow attribute: recipes must be "
                             "of type list. Was given %s. " % type(recipes))
    for recipe in recipes:
        valid_alphanumeric(recipe, extra_chars='+-=:_-')


def valid_workflow_variables(variables):
    """Verify that supplied variables dictionary only contains characters that
    we consider valid workflow variable key value pairs.
    """
    if not isinstance(variables, dict):
        raise InputException("Workflow attribute: variables must be of "
                             "type dict. Was given %s. " % type(variables))
    for _key, _value in variables.items():
        valid_alphanumeric(_key, extra_chars='_-')
        # Essentially no validation since this is a python variable
        # value, don't evaluate this.
        valid_free_text(_value)


def valid_workflow_param_over(params):
    """Verify that supplied params dictionary only contains keys and values
    that we consider valid.
    """
    if not isinstance(params, dict):
        raise InputException("Workflow attribute params must be "
                             "of type dict. Was given %s. " % type(params))

    for _name, _param in params.items():
        valid_alphanumeric(_name, extra_chars='_-')

        if not isinstance(_param, dict):
            raise InputException(
                "Workflow parameterize over attribute '%s' must be of type: "
                "dict" % html_escape(_name))

        for _key, _value in _param.items():
            if _key not in VALID_PARAM_OVER_ATTRIBUTES:
                raise InputException(
                    "Workflow attribute '%s' is illegal. Valid are: %s"
                    % (html_escape(_key), VALID_PARAM_OVER_ATTRIBUTES))

        for _key in VALID_PARAM_OVER_ATTRIBUTES:
            if _key not in _param:
                raise InputException(
                    "Required workflow attribute '%s' is missing" % _key)

            valid_float(_param[_key])

        # TODO expand this to allow more than just upwards loops
        if not float(_param[PARAM_START]) < float(_param[PARAM_STOP]):
            raise InputException(
                "Cannot parameterise between start '%s' and  end '%s' as end "
                "value is not bigger than the start value"
                % (_param[PARAM_START], _param[PARAM_STOP]))

        if not float(_param[PARAM_JUMP]) > 0:
            raise InputException(
                "Cannot parameterise with an increment of '%s'. Must be "
                "positive and non-zero. " % html_escape(_param[PARAM_JUMP])
            )

        frange(
            float(_param[PARAM_START]),
            float(_param[PARAM_STOP]),
            float(_param[PARAM_JUMP]),
            inc=True,
            limit=MAX_SWEEP
        )


def valid_workflow_source(source):
    """Verify that supplied source dictionary expressed a valid jupyter
    notebook.
    """
    if not nbformat:
        return False
    try:
        nbformat.validate(source, version=4)
    except nbformat.ValidationError:
        return False
    return True


def valid_workflow_recipe(recipe):
    """Verify that supplied recipe name only contains valid characters.
    """
    valid_alphanumeric(recipe, extra_chars='+-=:_-')


def valid_workflow_environments(environments):
    """Verify that supplied environments dictionary only contains keys and
    values that we consider valid. Note that here we are not checking the
    content of any of these values.
    """
    if not isinstance(environments, dict):
        raise InputException("Workflow attribute environments must "
                             "be of type: dict. Was given %s"
                             % type(environments))

    if 'mig' not in environments:
        return True

    for env_key, env_val in environments['mig'].items():
        if not isinstance(env_key, basestring):
            raise InputException(
                "Unexpected format for key '%s'. Expected to be a string but "
                "got '%s'" % (html_escape(env_key), type(env_key)))

        if env_key not in VALID_WORKFLOW_ENVIRONMENT:
            raise InputException(
                "Unknown environment key '%s' was provided. Valid keys are "
                "%s" % (html_escape(env_key),
                        ', '.join(VALID_WORKFLOW_ENVIRONMENT)))

        if env_key == 'cpu-architecture':
            valid_alphanumeric(env_val, extra_chars='+-=:_- ')

        elif env_key == 'fill':
            if not isinstance(env_val, list):
                raise InputException(
                    "Unexpected format for value '%s'. Expected to "
                    "be a list but got '%s'"
                    % (html_escape(env_val), type(env_val)))
            for entry in env_val:
                if not isinstance(entry, basestring):
                    raise InputException(
                        "Unexpected format for entry '%s'. Expected to "
                        "be a string but got '%s'"
                        % (html_escape(entry), type(entry)))
                if entry not in maxfill_fields:
                    raise InputException(
                        "Invalid fill keyword '%s'. Valid are %s."
                        % (html_escape(entry), ', '.join(maxfill_fields)))

        elif env_key == 'environment variables':
            if not isinstance(env_val, list):
                raise InputException(
                    "Unexpected format for value '%s'. Expected to "
                    "be a list but got '%s'"
                    % (html_escape(env_val), type(env_val)))
            for entry in env_val:
                if not isinstance(entry, basestring):
                    raise InputException(
                        "Unexpected format for '%s'. Expected to "
                        "be a string but got '%s'"
                        % (html_escape(entry), type(entry)))
                variable = entry.split('=')
                if len(variable) != 2 \
                        or not variable[0] \
                        or not variable[1]:
                    raise InputException(
                        "Incorrect formatting of variable '%s'. Must be of "
                        "form 'key=value'. Multiple variables should be "
                        "placed as separate entries" % html_escape(entry))
                # This could be checked using the [a-zA-Z_][a-zA-Z0-9_]* regex
                valid_alphanumeric(variable[0], extra_chars='_')
                if variable[0][0] in digits:
                    raise InputException(
                        "Cannot start environment variable %s with a digit."
                        % html_escape(variable[0]))

        elif env_key == 'notification':
            if not isinstance(env_val, list):
                raise InputException(
                    "Unexpected format for value '%s'. Expected to "
                    "be a list but got '%s'"
                    % (html_escape(env_val), type(env_val)))
            for entry in env_val:
                if not isinstance(entry, basestring):
                    raise InputException(
                        "Unexpected format for '%s'. Expected to "
                        "be a string but got '%s'"
                        % (html_escape(entry), type(entry)))
                notification = entry.split(':')
                if len(notification) != 2 \
                        or not notification[0] \
                        or not notification[1]:
                    raise InputException(
                        "Incorrect formatting of notification '%s'. Must be "
                        "of form 'key:value'. Multiple notifications should "
                        "be placed as separate entries" % html_escape(entry))
                valid_ascii(notification[0])
                notification[1] = notification[1].strip()
                if notification[1] != 'SETTINGS':
                    valid_email_address(notification[1])

        elif env_key == 'runtime environments':
            if not isinstance(env_val, list):
                raise InputException(
                    "Unexpected format for '%s'. Expected to "
                    "be a list but got '%s'"
                    % (html_escape(env_val), type(env_val)))
            for entry in env_val:
                if not isinstance(entry, basestring):
                    raise InputException(
                        "Unexpected format for '%s'. Expected to "
                        "be a string but got '%s'"
                        % (html_escape(entry), type(entry)))
                valid_alphanumeric(entry, extra_chars='+-=:_- ')

        elif env_key == 'nodes' \
                or env_key == 'cpu cores' \
                or env_key == 'wall time' \
                or env_key == 'memory' \
                or env_key == 'disks' \
                or env_key == 'retries':
            valid_numeric(env_val)

        else:
            # Be strict on MiG definitions. Nothing other than the keys already
            # specified should be used but we don't want unpredictable
            # behaviour from rogue definitions.
            raise InputException(
                "No environment check implemented for key '%s'. "
                % html_escape(env_key))
        return True


def valid_workflow_attributes(attributes):
    """Verify that supplied attributes dictionary only contains entries that
      we consider valid workflow attribute keys.
      """
    """Type validation filter of input attributes to a workflow"""
    if not isinstance(attributes, dict):
        raise InputException("Expects workflow attributes to be a dictionary")

    for _key, _value in attributes.items():
        if _key not in VALID_WORKFLOW_ATTRIBUTES:
            raise InputException("Workflow attribute '%s' is illegal"
                                 % html_escape(_key))


def valid_workflow_operation(operation):
    """Verify that the supplied workflow operation only contains letters and
    underscores.
    """
    valid_ascii(operation, extra_chars='_')


def valid_workflow_type(type):
    """Verify that the supplied workflow type only contains letters"""
    valid_ascii(type, extra_chars='_')


def valid_request_operation(operation):
    """Verify that the supplied request operation only contains letters and
    underscores.
    """
    valid_ascii(operation, extra_chars='_')


def valid_request_type(type):
    """Verify that the supplied request type only contains letters"""
    valid_ascii(type, extra_chars='_')


def valid_request_vgrid(vgrid):
    """Verify that supplied vgrid only contains characters that
    we consider valid in a vgrid name."""
    valid_vgrid_name(vgrid)


def valid_request_attributes(attributes):
    """Verify that supplied attributes is a dictionary. Note, does not check
    contents of said dictionary.
    """
    if not isinstance(attributes, dict):
        raise InputException("Expects requests attributes to be a dictionary")


def valid_job_vgrid(vgrid):
    """Verify that supplied vgrid only contains characters that
    we consider valid in a vgrid name."""
    valid_vgrid_name(vgrid)


def valid_job_attributes(attributes):
    """Verify that supplied attributes dictionary only contains entries that
      we consider valid job attribute keys.
      """
    if not isinstance(attributes, dict):
        raise InputException("Expects job attributes to be a dictionary")

    for _key, _value in attributes.items():
        if _key not in VALID_JOB_ATTRIBUTES:
            raise InputException("Job attribute '%s' is illegal"
                                 % html_escape(_key))


def valid_job_type(type):
    """Verify that the supplied job type only contains letters and
    underscores.
    """
    valid_ascii(type, extra_chars='_')


def valid_job_operation(operation):
    """Verify that the supplied job operation only contains letters and
    underscores.
    """
    valid_ascii(operation, extra_chars='_')


def filter_ascii(contents):
    """Filter supplied contents to only contain ascii characters"""

    return __filter_contents(contents, ascii_letters)


def filter_numeric(contents):
    """Filter supplied contents to only contain numeric characters"""

    return __filter_contents(contents, digits)


def filter_alphanumeric(contents):
    """Filter supplied contents to only contain alphanumeric characters"""

    return __filter_contents(contents, ascii_letters + digits)


def filter_alphanumeric_and_spaces(contents):
    """Filter supplied contents to only contain alphanumeric characters"""

    return __filter_contents(contents, ascii_letters + digits + ' ')


def filter_date(contents):
    """Filter supplied contents to only contain date characters"""

    return __filter_contents(contents, digits + '-/')


def filter_commonname(contents, illegal_handler=None):
    """Filter supplied contents to only contain valid commonname characters"""

    return __filter_contents(contents, VALID_NAME_CHARACTERS, COMMON_ACCENTED,
                             illegal_handler=illegal_handler)


def filter_organization(contents):
    """Filter supplied contents to only contain valid organization characters"""

    return __filter_contents(contents, VALID_ORG_CHARACTERS, COMMON_ACCENTED)


def filter_password(contents):
    """Filter supplied contents to only contain valid password characters"""

    return __filter_contents(contents, VALID_PASSWORD_CHARACTERS,
                             COMMON_ACCENTED)


def filter_plain_text(contents):
    """Filter supplied contents to only contain valid text characters"""

    return __filter_contents(contents, VALID_TEXT_CHARACTERS)


def filter_path(contents):
    """Filter supplied contents to only contain valid path characters"""

    # TODO: consider switching to illegal_handler=__wrap_unicode_val here
    return __filter_contents(contents, VALID_PATH_CHARACTERS, ANY_ACCENTED,
                             unicode_normalize=True)


def filter_safe_path(contents):
    """Filter supplied contents to only contain valid safe path characters"""

    return __filter_contents(contents, VALID_SAFE_PATH_CHARACTERS, NO_ACCENTED,
                             illegal_handler=__wrap_unicode_val)


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

        if ("%s" % default_value).lower() != first.lower():
            result = not default_value
    except:
        pass
    return (result, err)


def validated_string(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_alphanumeric(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_alphanumeric(first), err)


def validated_plain_text(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:

        # valid_alphanumeric_and_spaces(first)

        valid_plain_text(first)
    except InputException as iex:
        err += '%s' % iex

    # return filter_alphanumeric_and_spaces(first), err

    return (filter_plain_text(first), err)


def validated_path(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:

        # valid_alphanumeric_and_spaces(first)

        valid_path(first)
    except InputException as iex:
        err += '%s' % iex

    # return filter_alphanumeric_and_spaces(first), err

    return (filter_path(first), err)


def validated_fqdn(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_fqdn(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_fqdn(first), err)


def validated_commonname(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_commonname(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_commonname(first), err)


def validated_organization(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_organization(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_commonname(first), err)


def validated_password(user_arguments_dict, name, default):
    """Fetch first value of name argument and validate it"""

    err = ''

    # Force default value into a string

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_password(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_password(first), err)


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
    except InputException as iex:
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

    default_value = "%s" % default
    if default != default_value:
        err += 'Invalid string default value (%s)' % default
    try:
        first = user_arguments_dict[name][0]
    except:
        first = "%s" % default

    # Validate input

    try:
        valid_job_id(first)
    except InputException as iex:
        err += '%s' % iex
    return (filter_job_id(first), err)


def guess_type(name):
    """Maps variable names to expected types - only init map once"""

    if not __type_map:

        # TODO: extend to include all used variables here

        # NOTE: we keep the defaults tight here and force 'path' to be a plain
        #       path and not a path pattern, although it sometimes may be.
        #       One should *explicitly* override the validator for 'path' vars
        #       using the typecheck_overrides arg in validate_input calls in
        #       the backends where wildcard paths are accepted (i.e. in ls,
        #       cat, head, ...) but leave it to default for all the others.
        for key in (
            'path',
            'src',
            'dst',
            'current_dir',
            'fileupload',
            'public_image',
            'script_dir',
        ):
            # IMPORTANT: please do NOT change this to valid_path_pattern!
            __type_map[key] = valid_path
        for key in (
            'pattern',
            'arguments',
            'hostkey',
            'exclude',
        ):
            __type_map[key] = valid_path_pattern
        for key in (
            'executables',
            'inputfiles',
            'outputfiles',
            'verifyfiles',
        ):
            __type_map[key] = valid_path_src_dst_lines
        # NOTE: verifies that resource conf values and datatransfer paths are
        #       safe for ssh/lftp/rsync calls
        for key in (
            'resourcehome',
            'frontendlog',
            'exehostlog',
            'joblog',
            'curllog',
            'execution_dir',
            'storage_dir',
            'cmd',
            'site_script_deps',
            'modauthopenid.error',
        ):
            __type_map[key] = valid_safe_path
        # We include vgrid_name and a few more here to enforce sane name policy
        for key in ('base_vgrid_name', ):
            __type_map[key] = valid_base_vgrid_name
        # We include vgrid_name and a few more here to enforce sane name policy
        for key in ('vgrid_name', 'rate_limit', 'vgrids_allow_im',
                    'vgrids_allow_email', 'enforcelimits', ):
            __type_map[key] = valid_vgrid_name
        for key in ('freeze_name', ):
            __type_map[key] = valid_archive_name
        for key in ('jobname', ):
            __type_map[key] = valid_job_name
        for key in ('hash_algo', 'checksum', ):
            __type_map[key] = valid_backend_name
        for key in ('job_id', 'req_id', 'resource', 'search', ):
            __type_map[key] = valid_job_id_pattern
        for key in (
            'action',
            're_name',
            'rename',
            're_template',
            'lang',
            'machine_name',
            'freeze_id',
            'rule_id',
            'transfer_id',
            'key_id',
            'share_id',
            'miguser',
            'reset_token',
            'oidc.claim.oid',
        ):
            __type_map[key] = valid_job_id
        for key in (
            'country',
            'openid.sreg.country',
            'oidc.claim.country',
        ):
            # Country must be a two-letter ascii code
            __type_map[key] = lambda x: valid_ascii(x, min_length=2,
                                                    max_length=2)
        for key in (
            'state',
            'openid.sreg.state',
            'oidc.claim.state',
        ):
            # State must be empty or a two-letter ascii code
            __type_map[key] = lambda x: len(x) == 0 or \
                valid_ascii(x, min_length=2, max_length=2)
        for key in (
            'flags',
            'desktopname',
            'menu',
            'group_in_time',
            'display',
        ):
            __type_map[key] = valid_ascii
        for key in (
            'backups',
        ):
            __type_map[key] = valid_backup_names
        for key in (
            'max_jobs',
            'lines',
            'cputime',
            'size',
            'software_entries',
            'environment_entries',
            'testprocedure_entry',
            'width',
            'height',
            'depth',
            'hd_size',
            'memory',
            'disk',
            'net_bw',
            'cpu_count',
            'cpu_time',
            'field_count',
            'nodecount',
            'cpucount',
            'sshport',
            'maxdownloadbandwidth',
            'maxuploadbandwidth',
            'storage_disk',
            'storage_port',
        ):
            __type_map[key] = valid_numeric
        for key in ('peers_expire', ):
            __type_map[key] = valid_date
        for key in ('offset', ):
            __type_map[key] = valid_integer
        for key in (
            'fqdn',
            'unique_resource_name',
            'hosturl',
            'exe_name',
            'exe',
            'os',
            'flavor',
            'hypervisor_re',
            'sys_re',
            'time_start',
            'time_end',
            'frontendnode',
            'frontendproxy',
            'lrmstype',
            'platform',
            'architecture',
            'localjobname',
        ):
            __type_map[key] = valid_fqdn
        # NOTE: we need to allow some empty STORECONFIG and EXECONFIG fields,
        #       underscore in RTE environment name and space in RTE software
        #       name
        for key in ('name', ):
            __type_map[key] = lambda x: valid_fqdn(
                x, min_length=0, extra_chars='_ ')
        for key in ('execution_node', 'storage_node', ):
            __type_map[key] = lambda x: valid_fqdn(x, min_length=0)
        for key in ('execution_user', 'storage_user'):
            __type_map[key] = lambda x: valid_job_id(x, min_length=0)
        # dept and org may be empty or a comma-separated list
        for key in ('freeze_department', 'freeze_organization'):
            __type_map[key] = lambda x: valid_organization(x, min_length=0)
        # author may be empty or a comma-separated and extremely long list
        for key in ('freeze_author', ):
            __type_map[key] = lambda x: valid_organization(x, min_length=0,
                                                           max_length=2048)
        # EXECONFIG vgrid field which may be empty or a comma-separated list
        for key in ('vgrid', ):
            __type_map[key] = lambda x: valid_vgrid_name(x, min_length=0,
                                                         extra_chars=",")
        for key in (
            'full_name',
            'cert_name',
            'machine_software',
            'openid.sreg.cn',
            'openid.sreg.fullname',
            'openid.sreg.full_name',
            'openid.sreg.association',
            'oidc.claim.fullname',
            'oidc.claim.name',
            'oidc.claim.association',
            'changes',
            'version',
        ):
            __type_map[key] = valid_commonname
        # openid.sreg.required and role may have commas - reuse organization
        for key in (
            'org',
            'openid.sreg.o',
            'openid.sreg.ou',
            'organization',
            'oidc.claim.o',
            'oidc.claim.organization',
            'oidc.claim.ou',
            'oidc.claim.organizational_unit',
            'oidc.claim.locality',
            'openid.sreg.required',
        ):
            __type_map[key] = valid_organization
        for key in (
            'openid.sreg.role',
            'openid.sreg.roles',
            'oidc.claim.role',
            'oidc.claim.roles',
        ):
            __type_map[key] = valid_role
        for key in ('cert_id',
                    'run_as',):
            __type_map[key] = valid_distinguished_name
        for key in (
            'request_text',
            'public_profile',
            'resconfig',
            'redescription',
            'description',
            'example',
            'testprocedure',
            'environment',
            'software',
            'verifystdout',
            'verifystderr',
            'verifystatus',
            'msg_subject',
            'msg_body',
            'comment',
            'msg',
            'notify',
            'invite',
            'runtimeenvironment',
            'mount',
            'publicname',
            'publicinfo',
            'start_command',
            'stop_command',
            'status_command',
            'clean_command',
            'lrmsdelaycommand',
            'lrmssubmitcommand',
            'lrmsremovecommand',
            'lrmsdonecommand',
            'execution_precondition',
            'prepend_execute',
            'minprice',
            'crontab',
            'atjobs',
        ):
            __type_map[key] = valid_plain_text
        for key in (
            'aol',
            'yahoo',
            'msn',
            'icq',
            'jabber',
            'email',
            'openid.sreg.nickname',
            'openid.sreg.email',
            'openid.sreg.mail',
            'adminemail',
        ):
            __type_map[key] = valid_email_address
        for key in (
            'oidc.claim.upn',
            'oidc.claim.sub',
        ):
            __type_map[key] = valid_subject_id
        for key in (
            'peers_full_name',
        ):
            # NOTE: allow space or comma as delimiter
            __type_map[key] = lambda x: valid_commonname(
                x, extra_chars=',')
        # NOTE: some OIDCs concat email list into comma-separated string
        #       accept and handle unpacking explicitly in autocreate.py
        for key in (
            'peers_email',
            'oidc.claim.email',
        ):
            # NOTE: allow space or comma as delimiter
            __type_map[key] = lambda x: valid_email_addresses(
                x, delimiter=',')

        for key in ('username', 'ro_fields', ):
            __type_map[key] = valid_username
        for key in (
            'editarea',
            'execute',
            'premenu',
            'postmenu',
            'precontent',
            'postcontent',
            'publickeys',
            'freeze_description',
            # NOTE: we accept free text on overall EXECONFIG and STORECONFIG
            # because the sub level variables are parsed individually
            'execonfig',
            'storeconfig',
            'peers_content',
        ):
            __type_map[key] = valid_free_text
        for key in ('show', ):
            __type_map[key] = valid_label_text
        for key in ('password', 'verifypassword', 'transfer_pw', ):
            __type_map[key] = valid_password
        for key in ('hostidentifier', ):
            __type_map[key] = valid_alphanumeric
        for key in ('proxy_upload', ):
            __type_map[key] = valid_printable
        for key in (
                'openid.ns',
                'openid.ns.sreg',
                'oidc.claim.iss',
                'oidc.claim.aud',
                'url',
                'icon',
        ):
            __type_map[key] = valid_base_url
        for key in ('modauthopenid.referrer',
                    'transfer_src',
                    'transfer_dst',
                    'redirect_url',
                    ):
            __type_map[key] = valid_url

        # Image meta data (imagemeta.py)

        for key in ('image_type', 'data_type'):
            __type_map[key] = valid_alphanumeric

        for key in ('offset', 'x_dimension', 'y_dimension', 'z_dimension'):
            __type_map[key] = valid_numeric

        for key in ('preview_cutoff_min', 'preview_cutoff_max'):
            __type_map[key] = valid_float

        for key in ('volume_slice_filepattern', ):
            __type_map[key] = valid_path_pattern

        # GDP

        for key in ('gdp_category_id', ):
            __type_map[key] = valid_gdp_category_id
        for key in ('gdp_ref_id', ):
            __type_map[key] = valid_gdp_ref_id
        for key in ('gdp_ref_value', ):
            __type_map[key] = valid_gdp_ref_value
        for key in ('instance_id', ):
            __type_map[key] = valid_cloud_instance_id
        for key in ('cloud_id', 'instance_image', ):
            __type_map[key] = valid_cloud_name
        for key in ('instance_label', 'peers_label', ):
            __type_map[key] = valid_cloud_label

    # Return type checker from __type_map with fall back to alphanumeric

    return __type_map.get(name.lower().strip(), valid_alphanumeric)


def guess_value(name):
    """Maps variable names to expected values - only init map once"""

    if not __value_map:
        for key in ('lines', ):
            __value_map[key] = lines_value_checker
        for key in ('max_jobs', ):
            __value_map[key] = max_jobs_value_checker

    # Return value checker from __value_map with fall back to id function

    return __value_map.get(name.lower().strip(), id)


def validated_input(
    input_dict,
    defaults,
    type_override={},
    value_override={},
    list_wrap=False
):
    """Intelligent input validation with fall back default values.
    Specifying a default value of REJECT_UNSET, results in the
    variable being rejected if no value is found.
    """

    type_checks = {}
    value_checks = {}

    for name in defaults:
        if name in type_override:
            type_checks[name] = type_override[name]
        else:
            type_checks[name] = guess_type(name)
        if name in value_override:
            value_checks[name] = value_override[name]
        else:
            value_checks[name] = guess_value(name)
    (accepted, rejected) = validate_helper(input_dict, list(defaults),
                                           type_checks, value_checks,
                                           list_wrap)

    # Fall back to defaults when allowed and reject if required and unset
    for (key, val) in defaults.items():
        if REJECT_UNSET != val:
            if key not in accepted:
                accepted[key] = val
        else:
            if key not in accepted and key not in rejected:
                rejected[key] = (key, ['is required but missing', ''])

    return (accepted, rejected)


def validate_helper(
    input_dict,
    fields,
    type_checks,
    value_checks,
    list_wrap=False
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
        if isinstance(values, dict):
            a_values, r_values = validate_dict_values(key,
                                                      values,
                                                      fields,
                                                      type_checks,
                                                      value_checks)
            rejected.update(r_values)
            accepted.update(a_values)
        else:
            ok_values, bad_values = validate_values(key, values, fields,
                                                    type_checks,
                                                    value_checks,
                                                    list_wrap)
            if ok_values:
                accepted[key] = ok_values
            if bad_values:
                rejected[key] = bad_values
    return (accepted, rejected)


def validate_dict_values(
    key,
    values,
    fields,
    type_checks,
    value_checks
):
    """Validates a dictionary by executing the predefined type_checks
    and value_checks maps with a prepopulated function where the map key
    is the key for each entry in values

    Returns two dictionaries containing the passed and failed validations"""
    accepted_v = {}
    rejected_v = {}
    if key not in fields:
        err = 'unexpected field: %s' % key
        rejected_v[key] = ((html_escape(key),
                            html_escape("%s" % err)))
        return accepted_v, rejected_v

    for _key, _value in values.items():
        if _key in type_checks:
            try:
                type_checks[_key](_value)
            except Exception as err:
                # Probably illegal type hint
                rejected_v[_key] = ((html_escape(",".join(values)),
                                     html_escape("%s" % err)))
                continue
        if _key in value_checks:
            try:
                value_checks[_key](_value)
            except Exception as err:
                # Value check failed
                rejected_v[_key] = ((html_escape(",".join(values)),
                                     html_escape("%s" % err)))
                continue
        accepted_v[_key] = _value
    return accepted_v, rejected_v


def validate_values(
    key,
    values,
    fields,
    type_checks,
    value_checks,
    list_wrap=False
):
    """Validates the values in 'values' by passing each entry to
     a predefined type_checks and value_checks map with a matching 'key'

    Returns two lists containing the passed and failed validations"""
    ok_values = []
    bad_values = []

    if list_wrap and not isinstance(values, list):
        values = [values]

    for entry in values:
        # Never show actual passwords in output
        show_val = entry
        if type_checks.get(key, None) is valid_password:
            show_val = '*' * len(entry)

        if key not in fields:
            err = 'unexpected field: %s' % key
            bad_values.append((html_escape(show_val),
                               html_escape("%s" % err)))
            continue
        if key not in type_checks:
            # No type check - just accept as is
            continue
        try:
            type_checks[key](entry)
        except Exception as err:
            # Probably illegal type hint
            bad_values.append((html_escape(show_val),
                               html_escape("%s" % err)))
            continue
        if key not in value_checks:
            # No value check - just accept as is
            continue
        try:
            value_checks[key](entry)
        except Exception as err:
            # Value check failed
            bad_values.append((html_escape(show_val),
                               html_escape("%s" % err)))
            continue
        ok_values.append(entry)
    return ok_values, bad_values


class InputException(Exception):

    """Shared input validation exception - forced back to UTF-8"""

    def __init__(self, value):
        """Init InputException"""

        Exception.__init__(self)
        self.value = value

    def __str__(self):
        """Return string representation"""

        return force_utf8(force_unicode(self.value))


def main(_print=print):
    print = _print # workaround print as reserved word on PY2

    for test_org in ('UCPH', 'Some University, Some Dept.', 'Green Shoes Ltd.',
                     u'Unicode Org', "Invalid R+D", "Invalid R/D",
                     "Invalid R@D", 'Test HTML Invalid <code/>'):
        try:
            print('Testing valid_organization: %r' % test_org)
            print('Filtered organization: %s' % filter_organization(test_org))
            valid_organization(test_org)
            print('Accepted raw organization!')
        except Exception as exc:
            print('Rejected raw organization %r: %s' % (test_org, exc))

    for test_path in ('test.txt', 'Test Æøå', 'Test Überh4x0r',
                      'Test valid Jean-Luc Géraud', 'Test valid Źacãŕ',
                      'Test valid special%&()!$¶â€', 'Test look-alike-å å',
                      'Test north Atlantic Barður Ðýþ', 'Test exotic لرحيم',
                      'Test Invalid ?', 'Test Invalid `',
                      'Test invalid <', 'Test Invalid >',
                      'Test Invalid *', 'Test Invalid "'):
        try:
            print('Testing valid_path: %s' % test_path)
            print('Filtered path: %s' % filter_path(test_path))
            # print 'DEBUG %s only in %s' % ([test_path],
            #                               [VALID_PATH_CHARACTERS])
            valid_path(test_path)
            print('Accepted raw path!')
        except Exception as exc:
            print('Rejected raw path %r: %s' % (test_path, exc))

    for test_addr in ('', 'invalid', 'abc@dk', 'abc@def.org', 'abc@def.gh.org',
                      'aBc@Def.org', '<invalid@def.org>',
                      'Test <abc@def.org>', 'Test Æøå <æøå@abc.org>',
                      'Test <abc.def@ghi.org>', 'Test <abc+def@ghi.org>',
                      'A valid-name <abc@ghi.org>',
                      ' false-positive@ghi.org',
                      'False Positive  <abc@ghi.org>',
                      ' Another False Positive  <abc@ghi.org>',
                      'invalid <abc@ghi,org>', 'invalid <abc@',
                      'invalid abc@def.org',
                      'Test <abc@ghi.org>, twice <def@def.org>',
                      'A !#¤%/) positive  <abc@ghi.org>',
                      'a@b.c<script>alert("XSS vulnerable");</script>',
                      '<script>alert("XSS vulnerable");</script>',
                      '<script>alert("XSS vulnerable a@b.c");</script>'):
        try:
            print('Testing valid_email_address: %s' % test_addr)
            valid_email_address(test_addr)
            print('Accepted raw address! %s' % [parseaddr(test_addr)])
        except Exception as exc:
            print('Rejected raw address %r: %s' % (test_addr, exc))

    # OpenID 2.0 version
    autocreate_defaults = {
        'openid.ns.sreg': [''],
        'openid.sreg.nickname': [''],
        'openid.sreg.fullname': [''],
        'openid.sreg.o': [''],
        'openid.sreg.ou': [''],
        'openid.sreg.timezone': [''],
        'openid.sreg.short_id': [''],
        'openid.sreg.full_name': [''],
        'openid.sreg.organization': [''],
        'openid.sreg.organizational_unit': [''],
        'openid.sreg.email': [''],
        'openid.sreg.country': ['DK'],
        'openid.sreg.state': [''],
        'openid.sreg.locality': [''],
        'openid.sreg.role': [''],
        'openid.sreg.roles': [''],
        'openid.sreg.association': [''],
        # Please note that we only get sreg.required here if user is
        # already logged in at OpenID provider when signing up so
        # that we do not get the required attributes
        'openid.sreg.required': [''],
        'openid.ns': [''],
        'password': [''],
        'comment': ['(Created through autocreate)'],
        'proxy_upload': [''],
        'proxy_uploadfilename': [''],
    }
    user_arguments_dict = {'openid.ns.sreg':
                           ['http://openid.net/extensions/sreg/1.1'],
                           'openid.sreg.ou': ['nbi'],
                           'openid.sreg.nickname': ['brs278@ku.dk'],
                           'openid.sreg.fullname': ['Jonas Bardino'],
                           'openid.sreg.role': ['tap', 'staff'],
                           'openid.sreg.roles': ['tap, staff', 'developer'],
                           'openid.sreg.association': ['sci-nbi-tap'],
                           'openid.sreg.o': ['science'],
                           'openid.sreg.email': ['bardino@nbi.ku.dk']}
    (accepted, rejected) = validated_input(
        user_arguments_dict, autocreate_defaults)
    print("Accepted:")
    for (key, val) in accepted.items():
        print("\t%s: %s" % (key, val))
    print("Rejected:")
    for (key, val) in rejected.items():
        print("\t%s: %s" % (key, val))
    user_arguments_dict['openid.sreg.fullname'] = [
        force_unicode('Jonas Æøå Bardino')]
    (accepted, rejected) = validated_input(
        user_arguments_dict, autocreate_defaults)
    print("Accepted:")
    for (key, val) in accepted.items():
        print("\t%s: %s" % (key, val))
    print("Rejected:")
    for (key, val) in rejected.items():
        print("\t%s: %s" % (key, val))

    # OpenID Connect version
    autocreate_defaults = {
        'oidc.claim.iss': [''],
        'oidc.claim.sub': [''],
        'oidc.claim.upn': [''],
        'oidc.claim.oid': [''],
        'oidc.claim.aud': [''],
        'oidc.claim.nickname': [''],
        'oidc.claim.email': [''],
        'oidc.claim.name': [''],
        'oidc.claim.fullname': [''],
        'oidc.claim.o': [''],
        'oidc.claim.ou': [''],
        'oidc.claim.organization': [''],
        'oidc.claim.organizational_unit': [''],
        'oidc.claim.country': ['DK'],
        'oidc.claim.state': [''],
        'oidc.claim.locality': [''],
        'oidc.claim.role': [''],
        'oidc.claim.roles': [''],
        'oidc.claim.association': [''],
        'oidc.claim.timezone': [''],
        'password': [''],
        'comment': ['(Created through autocreate)'],
        'proxy_upload': [''],
        'proxy_uploadfilename': [''],
    }
    user_arguments_dict = {'oidc.claim.sub': ['e_zahNgeiwaet6loNah3ieD7x_hZ0su6'],
                           'oidc.claim.iss': ['https://your.id.provider/nidp/oauth/nam'],
                           'oidc.claim.aud': ['d34db33f-a13f-4ea0-de63-3bd8f9ef9392'],
                           'oidc.claim.oid': ['a323_d34db33f-a13f_de63-3bd8f9ef1234'],
                           'oidc.claim.ou': ['nbi, faksek'],
                           'oidc.claim.upn': ['brs278@ku.dk'],
                           'oidc.claim.nickname': ['brs278'],
                           'oidc.claim.fullname': ['Jonas Bardino'],
                           'oidc.claim.role': ['tap', 'staff'],
                           'oidc.claim.roles': ['tap, staff', 'developer', 'full-time_employee'],
                           'oidc.claim.association': ['sci-nbi-tap'],
                           'oidc.claim.o': ['science'],
                           'oidc.claim.email': ['bardino@nbi.ku.dk']}
    (accepted, rejected) = validated_input(user_arguments_dict,
                                           autocreate_defaults)
    print("Accepted:")
    for (key, val) in accepted.items():
        print("\t%s: %s" % (key, val))
    print("Rejected:")
    for (key, val) in rejected.items():
        print("\t%s: %s" % (key, val))
    user_arguments_dict = {'oidc.claim.aud': ['http://somedomain.org'],
                           'oidc.claim.country': ['DK'],
                           'oidc.claim.email': ['bardino@nbi.ku.dk,bardino@science.ku.dk'],
                           'oidc.claim.iss': ['https://wayf.wayf.dk'],
                           'oidc.claim.name': ['Jonas Bardino'],
                           'oidc.claim.organization': ['ku.dk'],
                           'oidc.claim.role': ['staff'],
                           'oidc.claim.sub': ['brs278@ku.dk'],
                           # 'oidc.claim.oid': [''], 'oidc.claim.upn': [''],
                           # 'oidc.claim.nickname': [''],
                           # 'oidc.claim.fullname': [''], 'oidc.claim.o': [''],
                           # 'oidc.claim.ou': [''],
                           # 'oidc.claim.organizational_unit': [''],
                           # 'oidc.claim.timezone': [''],
                           # 'oidc.claim.state': [''],
                           # 'oidc.claim.locality': [''],
                           # 'oidc.claim.roles': [''],
                           # 'oidc.claim.association': ['']
                           }
    (accepted, rejected) = validated_input(user_arguments_dict,
                                           autocreate_defaults)
    print("Accepted:")
    for (key, val) in accepted.items():
        print("\t%s: %s" % (key, val))
    print("Rejected:")
    for (key, val) in rejected.items():
        print("\t%s: %s" % (key, val))

if __name__ == '__main__':
    main()
