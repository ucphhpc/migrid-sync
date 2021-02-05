#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userscriptgen - Generator backend for user scripts
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

# TODO: filter exit code from cgi output and use in own exit code?

# TODO: mig-ls.* -r fib.out incorrectly lists entire home recursively
# TODO: ls -r is not recursive -> use -R!

"""Generate MiG user scripts for the specified programming
languages. Called without arguments the generator creates scripts
for all supported languages. If one or more languages are supplied
as arguments, only those languages will be generated.
"""
from __future__ import print_function
from __future__ import absolute_import

import sys
import getopt

# Generator version (automagically updated by svn)

__version__ = '$Revision$'

# Save original __version__ before truncate with wild card import

_userscript_version = __version__

from mig.shared.base import get_xgi_bin
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import file_dest_sep, upload_block_size, keyword_auto
from mig.shared.publicscriptgen import *
_publicscript_version = __version__
__version__ = '%s,%s' % (_userscript_version, _publicscript_version)

# ######################################
# Script generator specific functions #
# ######################################
# Generator usage


def usage():
    """ Usage helper"""

    print('Usage: userscriptgen.py OPTIONS [LANGUAGE ... ]')
    print('Where OPTIONS include:')
    print(' -c CURL_CMD\t: Use curl from CURL_CMD')
    print(' -d DST_DIR\t: write scripts to DST_DIR')
    print(' -h\t\t: Print this help')
    print(' -l\t\t: Do not generate shared library module')
    print(' -p PYTHON_CMD\t: Use PYTHON_CMD as python interpreter')
    print(' -s SH_CMD\t: Use SH_CMD as sh interpreter')
    print(' -t\t\t: Generate self testing script')
    print(' -v\t\t: Verbose output')
    print(' -V\t\t: Show version')


def version():
    """Version info"""

    print('MiG User Script Generator: %s' % __version__)


def version_function(lang):
    """Version helper"""

    s = ''
    s += begin_function(lang, 'version', [], 'Show version details')
    if lang == 'sh':
        s += "    echo 'MiG User Scripts: %s'" % __version__
    elif lang == 'python':
        s += "    print 'MiG User Scripts: %s'" % __version__
    s += end_function(lang, 'version')

    return s


# ##########################
# Script helper functions #
# ##########################


def shared_usage_function(op, lang, extension):
    """General wrapper for the specific usage functions.
    Simply rewrites first arg to function name."""

    return eval('%s_usage_function' % op)(lang, extension)


def cancel_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] JOBID [JOBID ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def cat_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def cp_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC...] DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    force_usage_string = '-f\t\tforce action'
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n    echo "%s"' % force_usage_string
        s += '\n    echo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % force_usage_string
        s += '\n    print "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def createbackup_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    # TODO: support multi src here (cumbersome due to freeze_copy_N format)
    usage_str = 'Usage: %s%s.%s [OPTIONS] NAME SRC'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def createfreeze_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    # TODO: support multi src here (cumbersome due to freeze_copy_N format)
    usage_str = 'Usage: %s%s.%s [OPTIONS] FLAVOR NAME DSC AUTHOR DPT ORG SRC'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def datatransfer_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ' % (mig_prefix, op, extension)
    usage_str += 'ACTION [TRANSFER_ID PROTOCOL FQDN PORT USERNAME PASSWORD'
    usage_str += 'KEY_ID NOTIFY FLAGS SRC [SRC...] DST]'
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def deletebackup_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FREEZE_ID' \
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def deletefreeze_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FLAVOR FREEZE_ID' \
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def doc_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [TOPIC ...]' % (mig_prefix,
                                                          op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def freezedb_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS]' % (mig_prefix,
                                              op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def imagepreview_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ACTION PATH [ARG ...]' % (mig_prefix,
                                                                    op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    action_usage_string = 'ACTION\t\tlist_settings : List imagepreview settings for directory PATH'
    action_usage_string2 = '\t\tcreate_setting : Create imagepreview setting for directory PATH with extension=EXT'
    action_usage_string3 = '\t\tupdate_setting : Update imagepreview setting for directory PATH with extension=EXT'
    action_usage_string4 = '\t\tremove_setting : Remove imagepreview setting for directory PATH with extension=EXT'
    action_usage_string5 = '\t\treset_setting : Reset imagepreview setting for directory PATH with extension=EXT'
    action_usage_string6 = '\t\tget_setting : Get imagepreview setting for directory PATH with extension=EXT'
    action_usage_string7 = '\t\tget : Get imagepreview for file PATH'
    action_usage_string8 = '\t\tremove : Remove imagepreview for file PATH'
    action_usage_string9 = '\t\tclean : Delete all imagepreview system components for directory PATH'
    action_usage_string10 = '\t\tcleanrecursive : Recursively delete all imagepreview system components for directory PATH'
    action_usage_string11 = '\t\trefresh : Update imagepreview system components for directory PATH'
    image_usage_string = '-i\t\tDisplay imagepreviews'

    if lang == 'sh':
        s += '\n    echo "%s"' % action_usage_string
        s += '\n    echo "%s"' % action_usage_string2
        s += '\n    echo "%s"' % action_usage_string3
        s += '\n    echo "%s"' % action_usage_string4
        s += '\n    echo "%s"' % action_usage_string5
        s += '\n    echo "%s"' % action_usage_string6
        s += '\n    echo "%s"' % action_usage_string7
        s += '\n    echo "%s"' % action_usage_string8
        s += '\n    echo "%s"' % action_usage_string9
        s += '\n    echo "%s"' % action_usage_string10
        s += '\n    echo "%s"' % action_usage_string11
    elif lang == 'python':
        s += '\n    print "%s"' % action_usage_string
        s += '\n    print "%s"' % action_usage_string2
        s += '\n    print "%s"' % action_usage_string3
        s += '\n    print "%s"' % action_usage_string4
        s += '\n    print "%s"' % action_usage_string5
        s += '\n    print "%s"' % action_usage_string6
        s += '\n    print "%s"' % action_usage_string7
        s += '\n    print "%s"' % action_usage_string8
        s += '\n    print "%s"' % action_usage_string9
        s += '\n    print "%s"' % action_usage_string10
        s += '\n    print "%s"' % action_usage_string11
    s += end_function(lang, 'usage')

    return s


def get_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...] FILE'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n    echo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def grep_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] PATTERN FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def head_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tShow first N lines of the file(s)'
    if lang == 'sh':
        s += '\n    echo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def jobaction_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ACTION JOBID [JOBID ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def liveio_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ACTION JOBID SRC [SRC ...] DST' % \
                (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def ls_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [FILE ...]' % (mig_prefix,
                                                         op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    all_usage_string = "-a\t\tDo not hide entries starting with '.'"
    long_usage_string = '-l\t\tDisplay long format'
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n    echo "%s"' % all_usage_string
        s += '\n    echo "%s"' % long_usage_string
        s += '\n    echo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % all_usage_string
        s += '\n    print "%s"' % long_usage_string
        s += '\n    print "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def login_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS]' % \
                (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def logout_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS]' % \
                (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def md5sum_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def mkdir_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] DIRECTORY [DIRECTORY ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    parents_usage_string = '-p\t\tmake parent directories as needed'
    if lang == 'sh':
        s += '\n    echo "%s"' % parents_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % parents_usage_string
    s += end_function(lang, 'usage')

    return s


def mqueue_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ACTION QUEUE [MSG]' % \
                (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def mv_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC...] DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def put_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...] FILE' % (mig_prefix,
                                                                   op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)

    package_usage_string = \
        '-p\t\tSubmit mRSL files (also in packages if -x is specified) after upload'
    recursive_usage_string = '-r\t\tact recursively'
    extract_usage_string = \
        '-x\t\tExtract package (.zip etc) after upload'
    if lang == 'sh':
        s += '\n    echo "%s"' % package_usage_string
        s += '\n    echo "%s"' % recursive_usage_string
        s += '\n    echo "%s"' % extract_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % package_usage_string
        s += '\n    print "%s"' % recursive_usage_string
        s += '\n    print "%s"' % extract_usage_string

    s += end_function(lang, 'usage')

    return s


def read_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] START END SRC DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def resubmit_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] JOBID [JOBID ...]' % (mig_prefix, op,
                                                                extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def rm_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    force_usage_string = '-f\t\tforce action'
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n    echo "%s"' % force_usage_string
        s += '\n    echo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % force_usage_string
        s += '\n    print "%s"' % recursive_usage_string
    s += end_function(lang, 'usage')

    return s


def rmdir_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] DIRECTORY [DIRECTORY ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    parents_usage_string = '-p\t\tremove parent directories as needed'
    if lang == 'sh':
        s += '\n    echo "%s"' % parents_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % parents_usage_string

    s += end_function(lang, 'usage')

    return s


def scripts_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] LANG FLAVOR' % (mig_prefix,
                                                          op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    dest_usage_string = '-d DST_DIR\t: write scripts to DST_DIR'
    if lang == 'sh':
        s += '\n    echo "%s"' % dest_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % dest_usage_string
    s += end_function(lang, 'usage')

    return s


def sha1sum_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def sharelink_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ' % (mig_prefix, op, extension)
    usage_str += 'ACTION [SHARE_ID PATH READ WRITE EXPIRE INVITE MSG]'
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def showbackup_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FREEZE_ID' \
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def showfreeze_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FLAVOR FREEZE_ID' \
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def stat_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [...]' % (mig_prefix,
                                                         op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def status_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [JOBID ...]' % (mig_prefix,
                                                          op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    max_jobs_usage_string = '-m M\t\tShow status for at most M jobs'
    sort_jobs_usage_string = '-S\t\tSort jobs by modification time'
    if lang == 'sh':
        s += '\n    echo "%s"' % max_jobs_usage_string
        s += '\n    echo "%s"' % sort_jobs_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % max_jobs_usage_string
        s += '\n    print "%s"' % sort_jobs_usage_string

    s += end_function(lang, 'usage')

    return s


def submit_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]' % (mig_prefix, op,
                                                              extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    local_usage_string = '-l\t\tUse local job file(s) - includes upload'
    if lang == 'sh':
        s += '\n    echo "%s"' % local_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % local_usage_string
    s += end_function(lang, 'usage')

    return s


def tail_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tShow last N lines of the file(s)'
    if lang == 'sh':
        s += '\n    echo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def test_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [OPERATION ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    prefix_usage_string = '-p PREFIX\tUse PREFIX for file and dir names'
    if lang == 'sh':
        s += '\n    echo "%s"' % prefix_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % prefix_usage_string
    s += end_function(lang, 'usage')

    return s


def touch_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [FILE ...]' % (mig_prefix,
                                                         op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def truncate_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tTruncate file(s) to at most N bytes'
    if lang == 'sh':
        s += '\n    echo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def twofactor_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] ACTION TOKEN [REDIRECT_URL]' % \
                (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def unzip_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC...] DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def uploadchunked_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC ...] DST' % (mig_prefix,
                                                                op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)

    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n    echo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def wc_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    bytes_usage_string = '-b N\t\tShow byte count'
    lines_usage_string = '-l N\t\tShow line count'
    words_usage_string = '-w N\t\tShow word count'
    if lang == 'sh':
        s += '\n    echo "%s"' % bytes_usage_string
        s += '\n    echo "%s"' % lines_usage_string
        s += '\n    echo "%s"' % words_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % bytes_usage_string
        s += '\n    print "%s"' % lines_usage_string
        s += '\n    print "%s"' % words_usage_string
    s += end_function(lang, 'usage')

    return s


def write_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] START END SRC DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def zip_usage_function(lang, extension):
    """Generate usage help for the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC...] DST'\
        % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    curdir_usage_string = '-w PATH\t\tUse PATH as remote working directory'
    if lang == 'sh':
        s += '\n    echo "%s"' % curdir_usage_string
    elif lang == 'python':
        s += '\n    print "%s"' % curdir_usage_string
    s += end_function(lang, 'usage')

    return s


# ##########################
# Communication functions #
# ##########################


def shared_op_function(configuration, op, lang, curl_cmd):
    """General wrapper for the specific op functions.
    Simply rewrites first arg to function name."""

    return eval('%s_function' % op)(configuration, lang, curl_cmd)


def cancel_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with job_list as argument"""

    relative_url = '"%s/jobaction.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=cancel"'
        urlenc_data = '(${job_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=cancel' % (default_args, server_flags)"
        urlenc_data = "job_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'cancel_job', ['job_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'cancel_job')
    return s


def cat_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/cat.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'cat_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'cat_file')
    return s


def cp_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with src_list and dst as arguments"""

    relative_url = '"%s/cp.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("${src_list[@]}" "dst=$dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = 'src_list + ["dst=" + dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'cp_file', ['src_list', 'dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'cp_file')
    return s


def createbackup_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the freeze_name and src args as
    arguments.
    """

    relative_url = '"%s/createbackup.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("freeze_name=$freeze_name" "freeze_copy_0=$src")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["freeze_name=" + freeze_name, "freeze_copy_0=" + src]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'create_backup', ['freeze_name', 'src'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'create_backup')
    return s


def createfreeze_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with flavor, freeze_name,
    freeze_description, freeze_author, freeze_department, freeze_organization,
    freeze_publish and src as arguments.
    """

    relative_url = '"%s/createfreeze.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("flavor=$flavor" "freeze_name=$freeze_name" "freeze_description=$freeze_description" "freeze_author=$freeze_author" "freeze_department=$freeze_department" "freeze_organization=$freeze_organization" "freeze_publish=$freeze_publish" "freeze_copy_0=$src")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["flavor=" + flavor, "freeze_name=" + freeze_name, "freeze_description=" + freeze_description, "freeze_author=" + freeze_author, "freeze_department=" + freeze_department, "freeze_organization=" + freeze_organization, "freeze_publish=" + freeze_publish, "freeze_copy_0=" + src]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'create_freeze', ['flavor', 'freeze_name', 'freeze_description', 'freeze_author', 'freeze_department', 'freeze_organization', 'freeze_publish', 'src'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'create_freeze')
    return s


def datatransfer_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with all arguments"""

    relative_url = '"%s/datatransfer.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action;'
        post_data += 'transfer_id=$transfer_id;protocol=$protocol;fqdn=$fqdn;'
        post_data += 'port=$port;username=$username;key_id=$key_id;'
        post_data += 'flags=$flags;"'
        urlenc_data = '("transfer_pw=$transfer_pw" "notify=$notify" '
        urlenc_data += '"${transfer_src[@]}" "transfer_dst=$transfer_dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s;transfer_id=%s;protocol=%s;"
        post_data += "fqdn=%s;port=%s;username=%s;key_id=%s;flags=%s'"
        post_data += "% (default_args, server_flags, action, transfer_id, "
        post_data += "protocol, fqdn, port, username, key_id, flags)"
        urlenc_data = '["transfer_pw=" + transfer_pw, "notify=" + notify] + '
        urlenc_data += 'transfer_src + ["transfer_dst=" + transfer_dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'datatransfer', ['action', 'transfer_id',
                                               'protocol', 'fqdn', 'port',
                                               'username', 'transfer_pw',
                                               'key_id', 'notify', 'flags',
                                               'transfer_src', 'transfer_dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'datatransfer')
    return s


def deletebackup_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the freeze_id as argument.
    """

    relative_url = '"%s/deletebackup.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("freeze_id=$freeze_id")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["freeze_id=" + freeze_id]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'delete_backup', ['freeze_id'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'delete_backup')
    return s


def deletefreeze_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the freeze_id as argument.
    """

    relative_url = '"%s/deletefreeze.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("flavor=$flavor" "freeze_id=$freeze_id")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["flavor=" + flavor, "freeze_id=" + freeze_id]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'delete_freeze', ['flavor', 'freeze_id'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'delete_freeze')
    return s


def doc_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the search and show as
    arguments.
    """

    relative_url = '"%s/docs.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("search=$search" "show=$show")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["search=" + search, "show=" + show]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'show_doc', ['search', 'show'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'show_doc')
    return s


def expand_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list and destinations
    as arguments.
    """

    relative_url = '"%s/expand.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;with_dest=$destinations"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;with_dest=%s' % (default_args, server_flags, destinations)"
        urlenc_data = 'path_list'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'expand_name', ['path_list',
                                              'server_flags', 'destinations'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'expand_name')
    return s


def freezedb_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the 'job_list' as argument"""

    relative_url = '"%s/freezedb.py"' % get_xgi_bin(configuration)
    query = '""'
    urlenc_data = '""'
    # NOTE: we request non-AJAX version (showlist) below to get useful output
    if lang == 'sh':
        post_data = '"$default_args;operation=showlist;flags=$server_flags"'
    elif lang == 'python':
        post_data = "'%s;operation=showlist;flags=%s' % (default_args, server_flags)"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'freeze_db', [],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'freeze_db')
    return s


def imagepreview_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path, action and key=val pairs
    as arguments.
    """

    relative_url = '"%s/imagepreview.py"' % get_xgi_bin(configuration)
    query = '""'
    # TODO: is arg_list really a list here?
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action"'
        urlenc_data = '("path=$path" "${arg_list[@]}")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s' % (default_args, server_flags, action)"
        urlenc_data = '["path=" + path] + arg_list'

    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'imagepreview', ['action', 'path', 'arg_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'imagepreview')
    return s


def get_function(configuration, lang, curl_cmd,
                 curl_flags='--compressed --create-dirs'):
    """Call the corresponding cgi script with src_path and dst_path as
    arguments.
    """

    post_data = '""'
    query = '""'
    urlenc_data = '""'
    if lang == 'sh':

        # TODO: should we handle below double slash problem here, too?

        relative_url = '"$auth_redir/$src_path"'
        curl_target = '("--output \'$dst_path\'")'
    elif lang == 'python':

        # Apache chokes on possible double slash in url and that causes
        # fatal errors in migfs-fuse - remove it from src_path.

        relative_url = "'%s/%s' % (auth_redir, src_path.lstrip('/'))"
        curl_target = "['--output', dst_path]"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'get_file', ['src_path', 'dst_path'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
    )
    s += end_function(lang, 'get_file')
    return s


def grep_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with pattern and 'path_list' as
    arguments.
    """

    relative_url = '"%s/grep.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("${path_list[@]}" "pattern=$pattern")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = 'path_list + ["pattern=" + pattern]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'grep_file', ['pattern', 'path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'grep_path')
    return s


def head_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/head.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;lines=$lines"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;lines=%s' % (default_args, server_flags, lines)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'head_file', ['lines', 'path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'head_file')
    return s


def jobaction_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with the 'job_list' and action as
    arguments.
    """

    relative_url = '"%s/jobaction.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action"'
        urlenc_data = '(${job_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s' % (default_args, server_flags, action)"
        urlenc_data = "job_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'job_action', ['action', 'job_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'job_action')
    return s


def liveio_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with src_list, dst, job_id and action
    as arguments.
    """

    relative_url = '"%s/liveio.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action"'
        urlenc_data = '("${src_list[@]}" "job_id=$job_id" "dst=$dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s' % (default_args, server_flags, action)"
        urlenc_data = 'src_list + ["job_id=" + job_id, "dst=" + dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'job_liveio', ['action', 'job_id', 'src_list',
                                             'dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'job_liveio')
    return s


def ls_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/ls.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'ls_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'ls_file')
    return s


def login_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call helper to setup an OpenID login session possibly with 2FA auth
    session included if enabled for the chosen OpenID login.
    """

    # Strip /id prefix from landing page get the required url form
    relative_url = configuration.site_landing_page.strip('/')
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    # Strip /id suffix from openid provider URL to get the required base form
    extoid_base = os.path.dirname(
        configuration.user_ext_oid_provider.rstrip('/'))
    migoid_base = os.path.dirname(
        configuration.user_mig_oid_provider.rstrip('/'))

    twofactor_url = ''
    if configuration.site_enable_twofactor:
        twofactor_url = '%s/twofactor.py' % get_xgi_bin(configuration)

    s = ''
    s += begin_function(lang, 'login_session', ['user_conf', 'username', 'password'],
                        'Init active login session')
    s += curl_chain_login_steps(
        lang,
        relative_url,
        post_data,
        migoid_base,
        extoid_base,
        twofactor_url,
    )
    s += end_function(lang, 'login_session')
    return s


def logout_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call a helper to retire an active OpenID login session possibly with
    2FA auth session included if enabled for the chosen OpenID login.
    """
    # Strip /id prefix from landing page get the required url form
    relative_url = configuration.site_landing_page.strip('/')
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    # Strip /id suffix from openid provider URL to get the required base form
    extoid_base = os.path.dirname(
        configuration.user_ext_oid_provider.rstrip('/'))
    migoid_base = os.path.dirname(
        configuration.user_mig_oid_provider.rstrip('/'))

    s = ''
    s += begin_function(lang, 'logout_session', ['user_conf'],
                        'Exit active login session')
    s += curl_chain_logout_steps(
        lang,
        relative_url,
        post_data,
        migoid_base,
        extoid_base
    )
    s += end_function(lang, 'logout_session')
    return s


def md5sum_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the chksum cgi script with implicit md5 and 'path_list' as
    argument.
    """

    relative_url = '"%s/chksum.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;hash_algo=md5"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;hash_algo=md5' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'md5_sum', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'md5_sum')
    return s


def mkdir_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/mkdir.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'mk_dir', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'mk_dir')
    return s


def mqueue_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with action, queue and msg as
    arguments."""

    relative_url = '"%s/mqueue.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action"'
        urlenc_data = '("queue=$queue" "msg=$msg")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s' % (default_args, server_flags, action)"
        urlenc_data = '["queue=" + queue, "msg=" + msg]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'job_mqueue', ['action', 'queue', 'msg'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'job_mqueue')
    return s


def mv_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with src_list and dst as arguments"""

    relative_url = '"%s/mv.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("${src_list[@]}" "dst=$dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = 'src_list + ["dst=" + dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'mv_file', ['src_list', 'dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'mv_file')
    return s


def put_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with src_path, dst_path, submit_mrsl
    and extract_package as arguments.
    """

    post_data = '""'
    query = '""'
    urlenc_data = '""'
    if lang == 'sh':

        # TODO: should we handle below double slash problem here, too?

        relative_url = '"$auth_redir/$dst_path"'
        curl_target = \
            '("--upload-file \'$src_path\'" "--header $content_type" "-X $put_arg")'
    elif lang == 'python':

        # Apache chokes on possible double slash in url and that causes
        # fatal errors in migfs-fuse - remove it from src_path.

        relative_url = '"%s/%s" % (auth_redir, dst_path.lstrip("/"))'
        curl_target = \
            "['--upload-file', src_path, '--header', '%s' % content_type, '-X', put_arg]"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'put_file', ['src_path', 'dst_path',
                                           'submit_mrsl', 'extract_package'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    if lang == 'sh':
        s += """
    content_type="''"
    if [ $submit_mrsl -eq 1 ] && [ $extract_package -eq 1 ]; then
        content_type='Content-Type:submitandextract'
    elif [ $submit_mrsl -eq 1 ]; then
        content_type='Content-Type:submitmrsl'
    elif [ $extract_package -eq 1 ]; then
        content_type='Content-Type:extractpackage'
    fi
"""
    elif lang == 'python':
        s += """
    content_type = "''"
    if submit_mrsl and extract_package:
        content_type = 'Content-Type:submitandextract'
    elif submit_mrsl:
        content_type = 'Content-Type:submitmrsl'
    elif extract_package:
        content_type = 'Content-Type:extractpackage'
"""
    else:
        print('Error: %s not supported!' % lang)
        return ''
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
    )
    s += end_function(lang, 'put_file')
    return s


def read_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the src_path, dst_path, first
    and last as arguments.
    """

    # TODO: switch to default get_xgi_bin when rangefileaccess is ported
    relative_url = '"%s/rangefileaccess.py"' % get_xgi_bin(
        configuration, force_legacy=True)
    # TODO: switch to post_data and urlenc_data when rangefileaccess is ported
    # query = '""'
    post_data = '""'
    urlenc_data = '""'
    if lang == 'sh':
        query = \
            '"?$default_args;flags=$server_flags;file_startpos=$first;file_endpos=$last;path=$src_path"'
        # post_data = \
        #    '"$default_args;flags=$server_flags;file_startpos=$first;file_endpos=$last"'
        #urlenc_data = '("src_path=$src_path")'
        curl_target = '("--output \'$dst_path\'")'
    elif lang == 'python':
        query = \
            "'?%s;flags=%s;file_startpos=%s;file_endpos=%s;path=%s' % (default_args, server_flags, first, last, src_path)"
        # post_data = \
        #    "'%s;flags=%s;file_startpos=%s;file_endpos=%s' % (default_args, server_flags, first, last)"
        #urlenc_data = '["src_path=%s" % src_path]'
        curl_target = "['--output', dst_path]"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'read_file', ['first', 'last', 'src_path',
                                            'dst_path'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
    )
    s += end_function(lang, 'read_file')
    return s


def resubmit_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with the 'job_list' as argument"""

    relative_url = '"%s/resubmit.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${job_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "job_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'resubmit_job', ['job_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'resubmit_job')
    return s


def rm_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/rm.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'rm_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'rm_file')
    return s


def rmdir_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/rmdir.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'rm_dir', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'rm_dir')
    return s


def scripts_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the search and show as
    arguments.
    """

    relative_url = '"%s/scripts.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("lang=$lang" "flavor=$flavor" "script_dir=$script_dir")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["lang=" + lang, "flavor=" + flavor, "script_dir=" + script_dir]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'generate_scripts', ['lang', 'flavor',
                                                   'script_dir'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'generate_scripts')
    return s


def sha1sum_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the chksum cgi script with implicit sha1 and 'path_list' as
    argument.
    """

    relative_url = '"%s/chksum.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;hash_algo=sha1"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;hash_algo=sha1' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'sha1_sum', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'sha1_sum')
    return s


def sharelink_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with all arguments"""

    relative_url = '"%s/sharelink.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action;'
        post_data += 'share_id=$share_id;read_access=$read_access;'
        post_data += 'write_access=$write_access;expire=$expire"'
        urlenc_data = '("path=$path" "invite=$invite" "msg=$msg")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s;share_id=%s;read_access=%s;"
        post_data += "write_access=%s;expire=%s' % (default_args, "
        post_data += "server_flags, action, share_id, read_access, "
        post_data += "write_access, expire)"
        urlenc_data = '["path=" + path, "invite=" + invite, "msg=" + msg]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'sharelink', ['action', 'share_id', 'path',
                                            'read_access', 'write_access',
                                            'expire', 'invite', 'msg'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'sharelink')
    return s


def showbackup_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the freeze_id as argument.
    """

    relative_url = '"%s/showbackup.py"' % get_xgi_bin(configuration)
    query = '""'
    # NOTE: we request non-AJAX version (showlist) below to get useful output
    if lang == 'sh':
        post_data = '"$default_args;operation=showlist;flags=$server_flags"'
        urlenc_data = '("freeze_id=$freeze_id")'
    elif lang == 'python':
        post_data = "'%s;operation=showlist;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["freeze_id=" + freeze_id]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'show_backup', ['freeze_id'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'show_backup')
    return s


def showfreeze_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the freeze_id as argument.
    """

    relative_url = '"%s/showfreeze.py"' % get_xgi_bin(configuration)
    query = '""'
    # NOTE: we request non-AJAX version (showlist) below to get useful output
    if lang == 'sh':
        post_data = '"$default_args;operation=showlist;flags=$server_flags"'
        urlenc_data = '("flavor=$flavor" "freeze_id=$freeze_id")'
    elif lang == 'python':
        post_data = "'%s;operation=showlist;flags=%s' % (default_args, server_flags)"
        urlenc_data = '["flavor=" + flavor, "freeze_id=" + freeze_id]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'show_freeze', ['flavor', 'freeze_id'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'show_freeze')
    return s


def stat_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/statpath.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'stat_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'stat_file')
    return s


def status_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the 'job_list' as argument"""

    relative_url = '"%s/jobstatus.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;max_jobs=$max_job_count"'
        urlenc_data = '(${job_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;max_jobs=%s' % (default_args, server_flags, max_job_count)"
        urlenc_data = "job_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'job_status', ['job_list', 'max_job_count'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'job_status')
    return s


def submit_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/submit.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    put_helper = put_function(configuration, lang, curl_cmd, curl_flags)

    s = ''

    # Simply use a private copy of put_file function if local flag was given

    s += put_helper.replace('put_file', '__put_file')

    # Else proceed with server-side only submit

    s += begin_function(lang, 'submit_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'submit_file')
    return s


def tail_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/tail.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;lines=$lines"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;lines=%s' % (default_args, server_flags, lines)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'tail_file', ['lines', 'path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'tail_file')
    return s


def test_function(configuration, lang, curl_cmd, curl_flags=''):
    """Test one or more of the user scripts"""

    # TODO: pass original -c and -s options on to tested scripts

    s = ''
    s += begin_function(lang, 'test_op', ['op', 'test_prefix'],
                        'Execute simple function tests')
    if lang == 'sh':
        s += """
    valid_ops=(%(valid_ops)s)
    mig_prefix='%(mig_prefix)s'
    script_ext='sh'
""" % {'valid_ops': ' '.join(script_ops), 'mig_prefix': mig_prefix}
        s += """
    valid=0
    for valid_op in ${valid_ops[*]}; do
        if [ $op = $valid_op ]; then
            valid=1
            break
        fi
    done

    if [ $valid -eq 0 ]; then
        echo \"Ignoring test of invalid operation: $op\"
        return 1
    fi
       
    path_prefix=`dirname $0`
    if [ -z \"$path_prefix\" ]; then
        path_prefix='.'
    fi
    dir_test=\"${test_prefix}-dir\"
    mrsl_test=\"${test_prefix}.mRSL\"
    txt_test=\"${test_prefix}.txt\"
    zip_test=\"${test_prefix}.zip\"
    mrsl_helper=\"${test_prefix}-helper.mRSL\"
    txt_helper=\"${test_prefix}-helper.txt\"
    txt_tmp=\"${test_prefix}-tmp.txt\"

    echo \"=== running $op test(s) ===\"
    cmd=\"${path_prefix}/${mig_prefix}${op}.${script_ext}\"
    ls_cmd=\"${path_prefix}/${mig_prefix}ls.${script_ext}\"
    mkdir_cmd=\"${path_prefix}/${mig_prefix}mkdir.${script_ext}\"
    put_cmd=\"${path_prefix}/${mig_prefix}put.${script_ext}\"
    rm_cmd=\"${path_prefix}/${mig_prefix}rm.${script_ext}\"
    #submit_cmd=\"${path_prefix}/${mig_prefix}submit.${script_ext}\"
    zip_cmd=\"${path_prefix}/${mig_prefix}zip.${script_ext}\"
    declare -a cmd_args
    declare -a verify_cmds
    # Default to no action
    pre_cmds[1]=''
    cmd_args[1]=''
    verify_cmds[1]=''
    post_cmds[1]=''
    case $op in
        'cat' | 'head' | 'ls' | 'md5sum' | 'sha1sum' | 'stat' | 'tail' | 'wc')
            cmd_args[1]=\"'${txt_helper}'\"
            ;;
        'cancel')
            # TODO: submit and cancel real job?
            #pre_cmds[1]=\"${submit_cmd} '${mrsl_helper}'\"
            cmd_args[1]='DUMMY_JOB_ID'
            ;;
        'cp')
            pre_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            cmd_args[1]=\"'${txt_helper}' '${txt_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            ;;
        'createbackup')
            pre_cmds[1]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[1]=\"'${test_prefix}' '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            ;;
        'datatransfer')
            cmd_args[1]=\"show\"
            ;;
        'deletebackup')
            cmd_args[1]=\"'${test_prefix}'\"
            ;;
        'doc')
            cmd_args[1]=''
            ;;
        'get')
            cmd_args[1]=\"'${txt_helper}' .\"
            ;;
        'grep')
            cmd_args[1]=\"test '${txt_helper}'\"
            ;;
        'jobaction')
            # TODO: submit and cancel real job?
            #pre_cmds[1]=\"${submit_cmd} '${mrsl_helper}'\"
            cmd_args[1]=\"cancel DUMMY_JOB_ID\"
            ;;
        'mkdir')
            pre_cmds[1]=\"${rm_cmd} -r '${dir_test}'\"
            cmd_args[1]=\"'${dir_test}'\"
            verify_cmds[1]=\"${ls_cmd} -la '${dir_test}'\"
            post_cmds[1]=\"${rm_cmd} -r '${dir_test}'\"
            ;;
        'mv')
            pre_cmds[1]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[1]=\"'${txt_test}' '${txt_tmp}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_tmp}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_tmp}'\"
            ;;
        'mqueue')
            cmd_args[1]=\"show default\"
            ;;
        'put')
            pre_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            cmd_args[1]=\"'${txt_test}' .\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            pre_cmds[2]=\"\"
            cmd_args[2]=\"'${txt_test}' '${txt_test}'\"
            verify_cmds[2]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[2]=\"${rm_cmd} '${txt_test}'\"
            pre_cmds[3]=\"\"
            cmd_args[3]=\"'${txt_test}' '${txt_tmp}'\"
            verify_cmds[3]=\"${ls_cmd} -l '${txt_tmp}'\"
            post_cmds[3]=\"${rm_cmd} '${txt_tmp}'\"
            pre_cmds[4]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[4]=\"'${txt_test}' '${dir_test}/'\"
            verify_cmds[4]=\"${ls_cmd} -l '${dir_test}/${txt_test}'\"
            post_cmds[4]=\"${rm_cmd} -r '${dir_test}'\"
            pre_cmds[5]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[5]=\"'${txt_test}' '${dir_test}/${txt_tmp}'\"
            verify_cmds[5]=\"${ls_cmd} -l '${dir_test}/${txt_tmp}'\"
            post_cmds[5]=\"${rm_cmd} -r '${dir_test}'\"
            pre_cmds[6]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[6]=\"'${test_prefix}.*' '${dir_test}/'\"
            verify_cmds[6]=\"${ls_cmd} -l '${dir_test}/${test_prefix}.*'\"
            post_cmds[6]=\"${rm_cmd} -r '${dir_test}'\"
            ;;
        'read')
            cmd_args[1]=\"0 16 '${txt_helper}' -\"
            ;;
        'rm')
            pre_cmds[1]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[1]=\"'${txt_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} -r '${txt_test}'\"
            ;;
        'rmdir')
            pre_cmds[1]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[1]=\"'${dir_test}'\"
            verify_cmds[1]=\"${ls_cmd} -la '${dir_test}'\"
            post_cmds[1]=\"${rm_cmd} -r '${dir_test}'\"
            ;;
        'scripts')
            pre_cmds[1]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[1]=\"-d '${dir_test}' ALL user\"
            verify_cmds[1]=\"${ls_cmd} -l '${dir_test}.zip'\"
            post_cmds[1]=\"${rm_cmd} -r '${dir_test}' '${dir_test}.zip'\"
            pre_cmds[2]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[2]=\"-d '${dir_test}' ALL resource\"
            verify_cmds[2]=\"${ls_cmd} -l '${dir_test}.zip'\"
            post_cmds[2]=\"${rm_cmd} -r '${dir_test}' '${dir_test}.zip'\"
            ;;
        'sharelink')
            cmd_args[1]=\"show\"
            ;;
        'showbackup')
            cmd_args[1]=\"'${test_prefix}'\"
            ;;
        'status')
            cmd_args[1]=''
            ;;
        'submit')
            cmd_args[1]=\"'${mrsl_helper}'\"
            cmd_args[2]=\"-l '${mrsl_test}'\"
            # TODO: cancel test jobs
            ;;
        'touch')
            pre_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            cmd_args[1]=\"'${txt_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            pre_cmds[2]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[2]=\"'${txt_test}'\"
            verify_cmds[2]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[2]=\"${rm_cmd} '${txt_test}'\"
            ;;
        'truncate')
            pre_cmds[1]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[1]=\"'${txt_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            ;;
        'unzip')
            pre_cmds[1]=\"${zip_cmd} '${txt_helper}' '${zip_test}'\"
            cmd_args[1]=\"'${zip_test}' ./\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_helper}'\"
            post_cmds[1]=\"${rm_cmd} '${zip_test}'\"
            ;;
        'uploadchunked')
            pre_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            cmd_args[1]=\"'${txt_test}' .\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            pre_cmds[2]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[2]=\"'${txt_test}' '${dir_test}/'\"
            verify_cmds[2]=\"${ls_cmd} -l '${dir_test}/${txt_test}'\"
            post_cmds[2]=\"${rm_cmd} -r '${dir_test}'\"
            pre_cmds[3]=\"${mkdir_cmd} '${dir_test}'\"
            cmd_args[3]=\"'${test_prefix}.*' '${dir_test}/'\"
            verify_cmds[3]=\"${ls_cmd} -l '${dir_test}/${test_prefix}.*'\"
            post_cmds[3]=\"${rm_cmd} -r '${dir_test}'\"
            ;;
        'write')
            pre_cmds[1]=\"${put_cmd} '${txt_test}' .\"
            cmd_args[1]=\"4 8 '${txt_test}' '${txt_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${txt_test}'\"
            post_cmds[1]=\"${rm_cmd} '${txt_test}'\"
            ;;
        'zip')
            pre_cmds[1]=\"${rm_cmd} '${zip_test}' .\"
            cmd_args[1]=\"'${txt_helper}' '${zip_test}'\"
            verify_cmds[1]=\"${ls_cmd} -l '${zip_test}'\"
            post_cmds[1]=\"${rm_cmd} '${zip_test}'\"
            ;;
        *)
            echo \"No test available for $op!\"
            return 1
            ;;
    esac


    index=1
    for args in \"${cmd_args[@]}\"; do
        echo \"test $index: $cmd $args\"
        pre=\"${pre_cmds[index]}\"
        if [ -n \"$pre\" ]; then
            echo \"setting up with: $pre\"
            eval $pre >& /dev/null
        fi
        eval $cmd $args >& /dev/null
        ret=$?
        if [ $ret -eq 0 ]; then
            echo \"   $op test $index SUCCEEDED\"
        else
            echo \"   $op test $index FAILED!\"
        fi
        verify=\"${verify_cmds[index]}\"
        if [ -n \"$verify\" ]; then
            echo \"verifying with: $verify\"
            eval $verify
        fi
        post=\"${post_cmds[index]}\"
        if [ -n \"$post\" ]; then
            echo \"cleaning up with: $post\"
            eval $post >& /dev/null
        fi
        index=$((index+1))
    done
    return $ret
"""
    elif lang == 'python':
        s += """
    valid_ops = %(valid_ops)s
    mig_prefix = '%(mig_prefix)s'
    script_ext = 'py'
""" % {'valid_ops': script_ops, 'mig_prefix': mig_prefix}
        s += """
    if not op in valid_ops:
        print 'Ignoring test of invalid operation: %s' % op
        return 1
       
    path_prefix = os.path.dirname(sys.argv[0])
    if path_prefix == '':
        path_prefix = '.'
    print '=== running %s test ===' % op
    cmd = os.path.join(path_prefix, mig_prefix + op + '.' + script_ext)
    pre_cmds = []
    cmd_args = []
    post_cmds = []
    verify_cmds = []
    dir_test = test_prefix + '-dir'
    mrsl_test = test_prefix + '.mRSL'
    txt_test = test_prefix + '.txt'
    zip_test = test_prefix + '.zip'
    mrsl_helper = test_prefix + '-helper.mRSL'
    txt_helper = test_prefix + '-helper.txt'
    txt_tmp = test_prefix + '-tmp.txt'

    ls_cmd = os.path.join(path_prefix, mig_prefix + 'ls.' + script_ext) 
    mkdir_cmd = os.path.join(path_prefix, mig_prefix + 'mkdir.' + script_ext) 
    put_cmd = os.path.join(path_prefix, mig_prefix + 'put.' + script_ext) 
    rm_cmd = os.path.join(path_prefix, mig_prefix + 'rm.' + script_ext) 
    #submit_cmd = os.path.join(path_prefix, mig_prefix + 'submit.' + script_ext) 
    zip_cmd = os.path.join(path_prefix, mig_prefix + 'zip.' + script_ext) 
    if op in ('cat', 'head', 'ls', 'md5sum', 'sha1sum', 'stat', 'tail', 'wc'):
            cmd_args.append([txt_helper])
    elif op == 'cancel':
            # TODO: submit and cancel real job?
            #pre_cmds.append([submit_cmd, mrsl_helper])
            cmd_args.append(['DUMMY_JOB_ID'])
    elif op == 'cp':
            pre_cmds.append([rm_cmd, txt_test, '.'])
            cmd_args.append([txt_helper, txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
    elif op == 'createbackup':
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append([test_prefix, txt_test])
            post_cmds.append([rm_cmd, txt_test])
    elif op == 'datatransfer':
            cmd_args.append(['show'])
    elif op == 'deletebackup':
            cmd_args.append(['backup', test_prefix])
    elif op in ('doc', 'status'):
            cmd_args.append([''])
    elif op == 'get':
            cmd_args.append([txt_helper, '.'])
    elif op == 'grep':
            cmd_args.append(['test', txt_helper])
    elif op == 'jobaction':
            # TODO: submit and cancel real job?
            #pre_cmds.append([submit_cmd, mrsl_helper])
            cmd_args.append(['cancel', 'DUMMY_JOB_ID'])
    elif op == 'mkdir':
            pre_cmds.append([rm_cmd, '-r', dir_test])
            cmd_args.append([dir_test])
            verify_cmds.append([ls_cmd, '-la', dir_test])
            post_cmds.append([rm_cmd, '-r', dir_test])
    elif op == 'mv':
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append([txt_test, txt_tmp])
            verify_cmds.append([ls_cmd, '-l', txt_tmp])
            post_cmds.append([rm_cmd, txt_tmp])
    elif op == 'mqueue':
            cmd_args.append(['show', 'default'])
    elif op == 'put':
            pre_cmds.append([rm_cmd, txt_test])
            cmd_args.append([txt_test, '.'])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
            pre_cmds.append([])
            cmd_args.append([txt_test, txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
            pre_cmds.append([])
            cmd_args.append([txt_test, txt_tmp])
            verify_cmds.append([ls_cmd, '-l', txt_tmp])
            post_cmds.append([rm_cmd, txt_tmp])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append([txt_test, '%s/' % dir_test])
            verify_cmds.append([ls_cmd, '-l', '%s/%s' % (dir_test, txt_test)])
            post_cmds.append([rm_cmd, '-r', dir_test])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append([txt_test, '%s/%s' % (dir_test, txt_tmp)])
            verify_cmds.append([ls_cmd, '-l', '%s/%s' % (dir_test, txt_tmp)])
            post_cmds.append([rm_cmd, '-r', dir_test])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append(['%s.*' % test_prefix, '%s/' % dir_test])
            verify_cmds.append([ls_cmd, '-l', '%s/%s.*' % (dir_test, test_prefix)])
            post_cmds.append([rm_cmd, '-r', dir_test])
    elif op == 'read':
            cmd_args.append(['0', '16', txt_helper, '-'])
    elif op == 'rm':
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append([txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
    elif op == 'rmdir':
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append([dir_test])
            verify_cmds.append([ls_cmd, '-la', dir_test])
            post_cmds.append([rm_cmd, '-r', dir_test])
    elif op == 'scripts':
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append(['-d', dir_test, 'ALL', 'user'])
            verify_cmds.append([ls_cmd, '-l', '%s.zip' % dir_test])
            post_cmds.append([rm_cmd, '-r', dir_test, '%s.zip' % dir_test])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append(['-d', dir_test, 'ALL', 'resource'])
            verify_cmds.append([ls_cmd, '-l', '%s.zip' % dir_test])
            post_cmds.append([rm_cmd, '-r', dir_test, '%s.zip' % dir_test])
    elif op == 'sharelink':
            cmd_args.append(['show'])
    elif op == 'showbackup':
            cmd_args.append([test_prefix])
    elif op == 'submit':
            cmd_args.append([mrsl_helper])
            cmd_args.append(['-l', mrsl_test])
            # TODO: cancel test jobs
    elif op == 'touch':
            pre_cmds.append([rm_cmd, txt_test])
            cmd_args.append([txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append([txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
    elif op == 'truncate':
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append([txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
    elif op == 'unzip':
            pre_cmds.append([zip_cmd, txt_helper, zip_test])
            cmd_args.append([zip_test,'./'])
            verify_cmds.append([ls_cmd, '-l', txt_helper])
            post_cmds.append([rm_cmd, zip_test])
    elif op == 'uploadchunked':
            pre_cmds.append([rm_cmd, txt_test])
            cmd_args.append([txt_test, '.'])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append([txt_test, '%s/' % dir_test])
            verify_cmds.append([ls_cmd, '-l', '%s/%s' % (dir_test, txt_test)])
            post_cmds.append([rm_cmd, '-r', dir_test])
            pre_cmds.append([mkdir_cmd, dir_test])
            cmd_args.append(['%s.*' % test_prefix, '%s/' % dir_test])
            verify_cmds.append([ls_cmd, '-l', '%s/%s.*' % (dir_test, test_prefix)])
            post_cmds.append([rm_cmd, '-r', dir_test])
    elif op == 'write':
            pre_cmds.append([put_cmd, txt_test, '.'])
            cmd_args.append(['4', '8', txt_test, txt_test])
            verify_cmds.append([ls_cmd, '-l', txt_test])
            post_cmds.append([rm_cmd, txt_test])
    elif op == 'zip':
            cmd_args.append([txt_helper, zip_test])
            verify_cmds.append([ls_cmd, '-l', zip_test])
            post_cmds.append([rm_cmd, zip_test])
    else:
            print 'No test available for %s!' % op
            return False

    index = 0
    for args in cmd_args:
        print 'test %d: %s %s' % (index, cmd, args)
        if pre_cmds[index:] and pre_cmds[index]:
            pre = pre_cmds[index]
            print 'setting up with: %s' % pre
            subprocess.call(pre, stdout=subprocess.PIPE)
        ret = subprocess.call([cmd] + args, stdout=subprocess.PIPE)
        if ret == 0:
            print '   %s test %d SUCCEEDED' % (op, index)
        else:
            print '   %s test %d FAILED!' % (op, index)
        if verify_cmds[index:]:
            verify = verify_cmds[index]
            print 'verifying with: %s' % verify
            subprocess.call(verify)
        if post_cmds[index:]:
            post = post_cmds[index]
            print 'cleaning up with: %s' % post
            subprocess.call(post, stdout=subprocess.PIPE)
        index += 1
    return ret
"""
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s += end_function(lang, 'test_op')
    return s


def touch_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/touch.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'touch_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'touch_file')
    return s


def truncate_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/truncate.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;size=$size"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s;size=%s' % (default_args, server_flags, size)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'truncate_file', ['size', 'path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'truncate_file')
    return s


def twofactor_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with action, queue and msg as
    arguments."""

    relative_url = '"%s/twofactor.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags;action=$action;token=$token"'
        urlenc_data = '("redirect_url=$redirect_url")'
    elif lang == 'python':
        post_data = "'%s;flags=%s;action=%s;token=%s' % (default_args, server_flags, action, token)"
        urlenc_data = '["redirect_url=" + redirect_url]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'twofactor_auth', ['action', 'token', 'redirect_url'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'twofactor_auth')
    return s


def unzip_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the 'src_list' and dst as
    argument.
    """

    relative_url = '"%s/unzip.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("${src_list[@]}" "dst=$dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = 'src_list + ["dst=" + dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'unzip_file', ['src_list', 'dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'unzip_file')
    return s


def uploadchunked_function(configuration, lang, curl_cmd,
                           curl_flags='--compressed'):
    """Call the corresponding cgi script with action, src_path, dst_path
    arguments.
    """
    relative_url = '"%s/uploadchunked.py"' % get_xgi_bin(configuration)
    query = '""'
    post_data = '""'
    urlenc_data = '""'
    curl_stdin_move = '""'
    if lang == 'sh':
        target_template = '("--form \\"$auth_data\\"" "--form \\"$out_form\\"" "--form \\"flags=$server_flags\\"" "--form \\"current_dir=$current_dir\\"" %s)'
        curl_target_put = target_template % '"--form \\"action=put\\"" "--form \\"files[]=@-;filename=$(basename $path)\\"" "--range \\"$start-$end\\""'
        curl_target_move = target_template % '"--form \\"action=move\\"" "--form \\"files[]=@-;filename=$(basename $path)\\""'
        curl_stdin_put = "'split -n $((chunk_no+1))/$total_chunks \"$path\"'"
        curl_stdin_move = "'echo DUMMY'"
    elif lang == 'python':
        target_template = "['--form', '%%s' %% auth_data, '--form', '%%s' %% out_form, '--form', 'flags=%%s' %% server_flags, '--form', 'current_dir=%%s' %% current_dir, %s]"
        curl_target_put = target_template % "'--form', 'action=put', '--form', 'files[]=@-;filename=%s' % os.path.basename(path), '--range', '%d-%d' % (start, end)"
        curl_target_move = target_template % "'--form', 'action=move', '--form', 'files[]=@-;filename=%s' % os.path.basename(path)"
        # Don't require external split command with python - just read chunks
        #curl_stdin_put = '["split", "-n", "%d/%d" % (chunk_no + 1, total_chunks), path]'
        curl_stdin_put = 'path'
        # Don't require external echo, just read first byte from path
        curl_stdin_move = 'path'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'uploadchunked_put', ['path', 'current_dir',
                                                    'chunk_no', 'chunk_size',
                                                    'total_chunks',
                                                    'total_size'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    if lang == 'sh':
        s += '''
    # Helpers used for input chunking below
    start=$((chunk_no*chunk_size))
    # The range parameter takes is on the form "first-last" i.e. inclusive
    end=$(((chunk_no+1)*chunk_size-1))
    # Last chunk includes remainder after splitting evenly into total_chunks
    if [ $chunk_no -eq $((total_chunks - 1)) ]; then
        end=$((total_size-1))
    fi
    chunk_bytes=$((1+end-start)) 
'''
    elif lang == 'python':
        s += '''
    # Helpers used for input chunking below
    start = chunk_no * chunk_size
    # The range parameter takes is on the form "first-last" i.e. inclusive
    end = (chunk_no + 1) * chunk_size - 1
    # Last chunk includes remainder after splitting evenly into total_chunks
    if chunk_no == total_chunks - 1:
        end = total_size - 1
    chunk_bytes = 1 + end - start
'''
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target_put,
        curl_stdin_put,
    )
    s += end_function(lang, 'uploadchunked_put')

    s += begin_function(lang, 'uploadchunked_move', ['path', 'current_dir',
                                                     'chunk_no', 'chunk_size',
                                                     'total_chunks',
                                                     'total_size'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    if lang == 'sh':
        s += '''
    start=0
    end=0
    chunk_bytes=1 
    chunk_bytes=$((1+end-start)) 
'''
    elif lang == 'python':
        s += '''
    start = 0
    end = 0
    chunk_bytes = 1 + end - start
'''
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target_move,
        curl_stdin_move,
    )
    s += end_function(lang, 'uploadchunked_move')

    return s


def wc_function(configuration, lang, curl_cmd, curl_flags=''):
    """Call the corresponding cgi script with path_list as argument"""

    relative_url = '"%s/wc.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '(${path_list[@]})'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = "path_list"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'wc_file', ['path_list'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'wc_file')
    return s


def write_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the src_path, dst_path, first
    and last arguments.
    """

    # TODO: switch to default get_xgi_bin when rangefileaccess is ported
    relative_url = '"%s/rangefileaccess.py"' % get_xgi_bin(
        configuration, force_legacy=True)
    # TODO: switch to post_data and urlenc_data when rangefileaccess is ported
    # query = '""'
    post_data = '""'
    urlenc_data = '""'
    if lang == 'sh':
        query = \
            '"?$default_args;flags=$server_flags;file_startpos=$first;file_endpos=$last;path=$dst_path"'
        # post_data = \
        #    '"$default_args;flags=$server_flags;file_startpos=$first;file_endpos=$last"'
        #urlenc_data = '("path=$dst_path")'
        curl_target = '("--upload-file \'$src_path\'")'
    elif lang == 'python':
        query = \
            "'?%s;flags=%s;file_startpos=%s;file_endpos=%s;path=%s' % (default_args, server_flags, first, last, dst_path)"
        # post_data = \
        #    "'%s;flags=%s;file_startpos=%s;file_endpos=%s' % (default_args, server_flags, first, last)"
        #urlenc_data = '["path=%s" % dst_path]'
        curl_target = "['--upload-file', src_path]"
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'write_file', ['first', 'last', 'src_path',
                                             'dst_path'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
    )
    s += end_function(lang, 'write_file')
    return s


def zip_function(configuration, lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the 'src_list', dst and
    current_dir as arguments.
    """

    relative_url = '"%s/zip.py"' % get_xgi_bin(configuration)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args;flags=$server_flags"'
        urlenc_data = '("${src_list[@]}" "current_dir=$current_dir" "dst=$dst")'
    elif lang == 'python':
        post_data = "'%s;flags=%s' % (default_args, server_flags)"
        urlenc_data = 'src_list + ["current_dir=" + current_dir, "dst=" + dst]'
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, 'zip_file', ['current_dir', 'src_list', 'dst'],
                        'Execute the corresponding server operation')
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        urlenc_data,
        query,
        curl_cmd,
        curl_flags,
    )
    s += end_function(lang, 'zip_file')
    return s


# #######################
# Main part of scripts #
# #######################


def expand_list(
    lang,
    input_list,
    expanded_list,
    destinations=False,
    warnings=True,
):
    """Inline expansion of remote filenames from a list of patterns possibly
    with wild cards.

    Output from CGI script is on the form:
    Exit code: 0 Description OK (done in 0.012s)
    Title: MiG Files

    ___MIG FILES___

    test.txt%stest.txt
    """ % file_dest_sep

    s = ''
    if lang == 'sh':
        s += """
declare -a %s
# Save original args
orig_args=(\"${%s[@]}\")

index=1
# For loop automatically expands wild cards
# We use the advice from http://tldp.org/LDP/abs/html/internalvariables.html
# to explicitly remove ordinary space from IFS to prevent spaces in filenames
# breaking things. Newlines and tabs are still effective.
IFS=\"$(printf '\n\t')\" 
for pattern in ${src_list[@]}; do
    expanded_path=$(expand_name \"path=$pattern\" \"$server_flags\" \"%s\" 2> /dev/null)
    # Expected output format is something like
    # Exit code: 0 Description OK (done in 0.047s)
    # Title: BLABLA Files
    #
    # ___BLABLA FILES___
    #
    # SRC%sDST
    exit_code=\"${expanded_path/Exit code: /}\"
    exit_code=\"${exit_code/ Description */}\"
    if [ \"$exit_code\" -ne \"0\" ]; then
""" % (expanded_list, input_list, str(destinations).lower(), file_dest_sep)
        if warnings:
            s += \
                """
        # output warning/error message(s) from expand
        echo \"$0: $@\"
"""
        s += """
        continue
    fi
    # Strip everything before the actual line with expansion
    expand_paths=\"${expanded_path/Exit code: *___$'\\n\\n'/}\"
    while [ ! -z \"$expand_paths\" ]; do
        #echo \"DEBUG: expand_paths: ${expand_paths}\"
        line=\"${expand_paths/$'\\n'*/}\"            
        src=\"${line/%s*/}\"
        dst=\"${line/*%s/}\"
        #echo \"DEBUG: expand_paths: src $src ; dst $dst\"
        %s+=(\"$src\" \"$dst\")
        # Move to next line
        expand_paths=\"${expand_paths/$line/}\"
        expand_paths=\"${expand_paths/$'\\n'/}\"
    done
done
""" % (file_dest_sep, file_dest_sep, expanded_list)
    elif lang == 'python':
        s += """
%s = []
for pattern in %s:
    (status, out) = expand_name('path=' + pattern, server_flags, '%s')
    result = [line.strip() for line in out if line.strip()]
    status = result[0].split()[2]
    src_list = result[3:]
    if status != '0':
"""\
             % (expanded_list, input_list, str(destinations).lower())
        if warnings:
            s += \
                """
        # output warning/error message(s) from expand
        print sys.argv[0] + ": " + ' '.join(src_list)
"""
        s += """
        continue
    %s += src_list
""" % expanded_list
    else:
        print('Error: %s not supported!' % lang)
        return ''

    return s


def shared_main(op, lang):
    """General wrapper for the specific main functions.
    Simply rewrites first arg to function name."""

    return eval('%s_main' % op)(lang)


def cancel_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    Currently 'sh' and 'python' are supported.

    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'job_id_list', 'job_id')
    if lang == 'sh':
        s += """
cancel_job ${job_id_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = cancel_job(job_id_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def cat_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
cat_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = cat_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def cp_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # cp cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'fr',
                           '''        f)  server_flags="${server_flags}f"
            flags="${flags} -f";;
        r)  server_flags="${server_flags}r"
            flags="${flags} -r";;''')
    elif lang == 'python':
        s += parse_options(lang, 'fr',
                           '''    elif opt == "-f":
        server_flags += "f"
    elif opt == "-r":
        server_flags += "r"''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'src')
    if lang == 'sh':
        s += """
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
unset src_list[$last_index]
cp_file ${src_list[@]} \"$dst\"
"""
    elif lang == 'python':
        s += """
del src_list[-1]
dst = sys.argv[-1]
(status, out) = cp_file(src_list, dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def createbackup_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
freeze_name=$1
src=$2
create_backup \"$freeze_name\" \"$src\"
"""
    elif lang == 'python':
        s += """
freeze_name = sys.argv[1]
src = sys.argv[2]
(status, out) = create_backup(freeze_name, src)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def createfreeze_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 8, 8)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
flavor=$1
freeze_name=$2
freeze_description=$3
freeze_author=$4
freeze_department=$5
freeze_organization=$6
freeze_publish=$7
src=$8
create_freeze \"$flavor\" \"$freeze_name\" \"$freeze_description\" \"$freeze_author\" \"$freeze_department\" \"$freeze_organization\" \"$freeze_publish\" \"$src\"
"""
    elif lang == 'python':
        s += """
flavor = sys.argv[1]
freeze_name = sys.argv[2]
freeze_description = sys.argv[3]
freeze_author = sys.argv[4]
freeze_department = sys.argv[5]
freeze_organization = sys.argv[6]
freeze_publish = sys.argv[7]
src = sys.argv[8]
(status, out) = create_freeze(flavor, freeze_name, freeze_description, freeze_author, freeze_department, freeze_organization, freeze_publish, src)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def datatransfer_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'transfer_src')
    if lang == 'sh':
        s += """
# We included most args in packing above - remove again
action=\"${orig_args[0]}\"
transfer_id=\"${orig_args[1]}\"
protocol=\"${orig_args[2]}\"
fqdn=\"${orig_args[3]}\"
port=\"${orig_args[4]}\"
username=\"${orig_args[5]}\"
transfer_pw=\"${orig_args[6]}\"
key_id=\"${orig_args[7]}\"
notify=\"${orig_args[8]}\"
flags=\"${orig_args[9]}\"
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
for i in 0 1 2 3 4 5 6 7 8 9 $last_index; do
    unset src_list[$i]
done
datatransfer \"$action\" \"$transfer_id\" \"$protocol\" \"$fqdn\" \"$port\" \"$username\" \"$transfer_pw\" \"$key_id\" \"$notify\" \"$flags\" ${src_list[@]} \"$dst\" '' '' '' '' '' '' '' '' '' '' ''
"""
    elif lang == 'python':
        s += """
# optional 2nd to 12th argument depending on action - add dummies
sys.argv += (12 - len(sys.argv[1:])) * ['']
# We included most args in packing above - remove again
action = \"%s\" % sys.argv[1]
transfer_id = \"%s\" % sys.argv[2]
protocol = \"%s\" % sys.argv[3]
fqdn = \"%s\" % sys.argv[4]
port = \"%s\" % sys.argv[5]
username = \"%s\" % sys.argv[6]
transfer_pw = \"%s\" % sys.argv[7]
key_id = \"%s\" % sys.argv[8]
notify = \"%s\" % sys.argv[9]
flags = \"%s\" % sys.argv[10]
dst = \"%s\" % sys.argv[-1]
src_list = src_list[10:-1]
(status, out) = datatransfer(action, transfer_id, protocol, fqdn, port,
                             username, transfer_pw, key_id, notify, flags, src_list,
                             dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def deletebackup_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, 1)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
freeze_id=$1
delete_backup \"$freeze_id\"
"""
    elif lang == 'python':
        s += """
freeze_id = sys.argv[1]
(status, out) = delete_backup(freeze_id)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def deletefreeze_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
flavor=$1
freeze_id=$2
delete_freeze \"$flavor\" \"$freeze_id\"
"""
    elif lang == 'python':
        s += """
flavor = sys.argv[1]
freeze_id = sys.argv[2]
(status, out) = delete_freeze(flavor, freeze_id)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def doc_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
if [ $# -gt 0 ]; then
    # SearchList=()
    TopicList=(\"$@\")
else
    SearchList=(\"*\")
    # TopicList=()
fi

for Search in \"${SearchList[@]}\"; do
    show_doc \"$Search\" \"\"
done
for Topic in \"${TopicList[@]}\"; do
    show_doc \"\" \"$Topic\"
done
"""
    elif lang == 'python':
        s += """
if len(sys.argv) - 1 > 0:
    SearchList = ""
    TopicList = sys.argv[1:]
else:
    SearchList = '*'
    TopicList = ""

out = []
for Search in SearchList:
    (status, search_out) = show_doc(Search, "")
    out += search_out
for Topic in TopicList:
    (status, topic_out) = show_doc("", Topic)
    out += topic_out
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def freezedb_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
freeze_db
"""
    elif lang == 'python':
        s += """
(status, out) = freeze_db()
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def imagepreview_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
# Build the arg string used directly:
# action=$1 path=$2 ("arg=$3" ... "arg=$N")
declare -a arg_list
orig_args=(\"$@\")
action=\"$1\"
shift
path=\"$1\"
shift
arg_list=(\"$@\")
shift $#
imagepreview \"$action\" \"$path\" \"${arg_list[@]}\"
"""
    elif lang == 'python':
        s += """
# Build the arg string used directly:
# action=$1 path=$2 ['abc=$3', ..., 'xyz=$N']
action = \"%s\" % sys.argv[1]
path = \"%s\" % sys.argv[2]
arg_list = [i for i in sys.argv[3:]]
(status, out) = imagepreview(action, path, arg_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def get_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'r',
                           '        r)  server_flags="${server_flags}r";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'r',
                           '''    elif opt == "-r":
        server_flags += "r"''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':

        # Advice about parsing taken from:
        # http://www.shelldorado.com/goodcoding/cmdargs.html

        s += """
orig_args=(\"$@\")
src_list=(\"$@\")
raw_dst=\"${src_list[$(($#-1))]}\"
unset src_list[$(($#-1))]
"""
        s += expand_list(lang, 'src_list', 'expanded_list', True)
        s += """
# Use '--' to handle case where no expansions succeeded
set -- \"${expanded_list[@]}\"
# Expand doesn't automatically split the output lines, so they are still on the
#src%sdst
# form here.
while [ $# -gt 0 ]; do
    src=\"$1\"
    dest=\"$2\"
    shift; shift
    dst=\"$raw_dst/$dest\"
    get_file \"$src\" \"$dst\"
done
""" % file_dest_sep
    elif lang == 'python':
        s += """
raw_dst = sys.argv[-1]
src_list = sys.argv[1:-1]
"""
        s += expand_list(lang, 'src_list', 'expanded_list', True)
        s += """
# Expand doesn't automatically split the output lines, so they are still on the
#src%sdest
# form here.
for line in expanded_list:
    src, dest = line.split('%s', 1)
    dst = raw_dst + os.sep + dest
    (status, out) = get_file(src, dst)
sys.exit(status)
""" % (file_dest_sep, file_dest_sep)
    else:
        print('Error: %s not supported!' % lang)

    return s


def grep_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # Client side wild card expansion doesn't make sense for grep

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
# We included pattern in packing above - remove again
pattern=\"${orig_args[0]}\"
unset path_list[0]
grep_file \"$pattern\" ${path_list[@]}
"""
    elif lang == 'python':
        s += """
# We included pattern in packing above - remove again
pattern = \"%s\" % sys.argv[1]
del path_list[0]
(status, out) = grep_file(pattern, path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def head_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'lines=20\n'
        s += parse_options(lang, 'n:', '        n)  lines="$OPTARG";;')
    elif lang == 'python':
        s += 'lines = 20\n'
        s += parse_options(lang, 'n:',
                           '''    elif opt == "-n":
        lines = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
head_file \"$lines\" ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = head_file(lines, path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def jobaction_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'job_id_list', 'job_id')
    if lang == 'sh':
        s += """
# We included action in packing above - remove again
action=\"${orig_args[0]}\"
unset job_id_list[0]
job_action \"$action\" ${job_id_list[@]}
"""
    elif lang == 'python':
        s += """
# We included action in packing above - remove again
action = \"%s\" % sys.argv[1]
del job_id_list[0]
(status, out) = job_action(action, job_id_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def liveio_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 4, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'src')
    if lang == 'sh':
        s += """
# We included all args in packing above - remove again
action=\"${orig_args[0]}\"
job_id=\"${orig_args[1]}\"
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
unset src_list[$last_index]
unset src_list[1]
unset src_list[0]
job_liveio \"$action\" \"$job_id\" ${src_list[@]} \"$dst\"
"""
    elif lang == 'python':
        s += """
# We included all args in packing above - remove again
action = \"%s\" % sys.argv[1]
job_id = \"%s\" % sys.argv[2]
dst = \"%s\" % sys.argv[-1]
del src_list[-1]
del src_list[1]
del src_list[0]
(status, out) = job_liveio(action, job_id, src_list, dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def ls_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # ls cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'alr',
                           '''        a)  server_flags="${server_flags}a"
            flags="${flags} -a";;
        l)  server_flags="${server_flags}l"
            flags="${flags} -l";;
        r)  server_flags="${server_flags}r"
            flags="${flags} -r";;''')
    elif lang == 'python':
        s += parse_options(lang, 'alr',
                           '''    elif opt == "-a":
        server_flags += "a"
    elif opt == "-l":
        server_flags += "l"
    elif opt == "-r":
        server_flags += "r"''')
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
if [ ${#orig_args[@]} -eq 0 ]; then
    path_list+=('path=.')
fi
ls_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
if not sys.argv[1:]:
    path_list += ['path=.']
(status, out) = ls_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def login_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_conf(lang, 'user_conf')
    if lang == 'sh':
        s += """
login_session \"$user_conf\" \"$username\" \"$password\"
"""
    elif lang == 'python':
        s += """
(status, out) = login_session(user_conf, username, password)
# All output here is manual messages without newlines
print('\\n'.join(out))
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def logout_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_conf(lang, 'user_conf')
    if lang == 'sh':
        s += """
logout_session \"$user_conf\"
"""
    elif lang == 'python':
        s += """
(status, out) = logout_session(user_conf)
# All output here is manual messages without newlines
print('\\n'.join(out))
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def md5sum_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # Client side wild card expansion doesn't make sense for md5sum

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
md5_sum ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = md5_sum(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def mkdir_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # Client side wild card expansion doesn't make sense for mkdir

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'p',
                           '        p)  server_flags="${server_flags}p"\n            flags="${flags} -p";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'p',
                           '    elif opt == "-p":\n        server_flags += "p"'
                           )
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
mk_dir ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = mk_dir(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def mqueue_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 3)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
# optional third argument depending on action - add dummy
job_mqueue \"$@\" ''
"""
    elif lang == 'python':
        s += """
# optional third argument depending on action - add dummy
sys.argv.append('')
(status, out) = job_mqueue(*(sys.argv[1:4]))
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def mv_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # mv cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'src')
    if lang == 'sh':
        s += """
# We included dst in packing above - remove again
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
unset src_list[$last_index]
mv_file ${src_list[@]} \"$dst\"
"""
    elif lang == 'python':
        s += """
# We included dst in packing above - remove again
dst = \"%s\" % sys.argv[-1]
del src_list[-1]
(status, out) = mv_file(src_list, dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def put_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # We should handle uploads like this:
    # migput localfile . -> localfile
    # migput localfile remotefile -> remotefile
    # migput localfile remotedir -> remotedir/localfile
    # migput ../localdir/localfile remotedir -> upload as file and expect server ERROR
    # migput ../localdir/localfile remotedir/ -> remotedir/localfile
    # migput ../localdir . -> ERROR?
    # migput -r ../localdir . -> localdir
    # migput -r ../localdir remotedir -> remotedir/localdir
    #                                   -> remotedir/localdir/*

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'submit_mrsl=0\n'
        s += 'recursive=0\n'
        s += 'extract_package=0\n'
        s += parse_options(lang, 'prx',
                           '        p)  submit_mrsl=1;;\n        r)  recursive=1;;\n        x)  extract_package=1;;'
                           )
    elif lang == 'python':
        s += 'submit_mrsl = False\n'
        s += 'recursive = False\n'
        s += 'extract_package = False\n'
        s += parse_options(lang, 'prx',
                           '''    elif opt == "-p":
        submit_mrsl = True
    elif opt == "-r":
        recursive = True
    elif opt == "-x":
        extract_package = True''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    # NOTE: using pack_list is cumbersome here so we don't
    if lang == 'sh':
        s += """
src_list=(\"$@\")
raw_dst=\"${src_list[$(($#-1))]}\"
unset src_list[$(($#-1))]

# remove single '.' to avoid problems with missing ending slash
if [ \".\" = \"$raw_dst\" ]; then
    dst=\"\"
else
    dst=\"$raw_dst\"
fi

# For loop automatically expands wild cards
# We use the advice from http://tldp.org/LDP/abs/html/internalvariables.html
# to explicitly remove ordinary space from IFS to prevent spaces in filenames
# breaking things. Newlines and tabs are still effective.
IFS=\"$(printf '\n\t')\" 
for src in ${src_list[@]}; do
    if [ ! -e \"$src\" ]; then
        echo \"No such file or directory: $src !\"
        continue
    fi
    if [ -d \"$src\" ]; then
        if [ $recursive -ne 1 ]; then
            echo \"Nonrecursive put skipping directory: $src\"
            continue
        fi
        # Recursive dirs may not exist - create them first
        # we could leave it to backend handler but then we miss empty dirs
        src_parent=`dirname $src`
        src_target=`basename $src`
        dirs=`cd $src_parent && find $src_target -type d`
        # force mkdir -p
        old_flags=\"$server_flags\"
        server_flags=\"p\"
        declare -a dir_list
        for dir in $dirs; do
            dir_list+=(\"path=$dst/$dir\")
        done
        mk_dir ${dir_list[@]}
        server_flags=\"$old_flags\"
        sources=`cd $src_parent && find $src_target -type f`
        for path in $sources; do
            put_file \"$src_parent/$path\" \"$dst/$path\" $submit_mrsl $extract_package
        done
    else
        put_file \"$src\" \"$dst\" \"$submit_mrsl\" \"$extract_package\"
    fi
done
"""
    elif lang == 'python':
        s += """
from glob import glob

raw_list = sys.argv[1:-1]
raw_dst = sys.argv[-1]
if \".\" == raw_dst:
    dst = \"\"
else:
    dst = raw_dst

# Expand sources
status = 2
src_list = []
for src in raw_list:
    expanded = glob(src)
    if expanded:
        src_list += expanded
    else:
        # keep bogus pattern for correct output order
        src_list += [src]

for src in src_list:
    if not os.path.exists(src):
        print \"No such file or directory: %s !\" % src
        continue
    if os.path.isdir(src):
        if not recursive:
            print \"Nonrecursive put skipping directory: %s\" % src
            continue
        src_parent = os.path.abspath(os.path.dirname(src))
        for root, dirs, files in os.walk(os.path.abspath(src)):
            # Recursive dirs may not exist - create them first
            # force mkdir -p
            old_flags = \"$server_flags\"
            server_flags = \"p\"
            rel_root = root.replace(src_parent, '', 1).lstrip(os.sep)
            dir_list = ['path=%s' % os.path.join(dst, rel_root, i) for i in dirs]
            # add current root
            dir_list.append('path=%s' % os.path.join(dst, rel_root))
            mk_dir(dir_list)
            server_flags = \"$old_flags\"
            for name in files:
                src_path = os.path.join(root, name)
                dst_path = os.path.join(dst, rel_root, name)
                (status, out) = put_file(src_path, dst_path, submit_mrsl, extract_package)
                # Trailing comma to prevent double newlines
                print ''.join(out),
    else:
        (status, out) = put_file(src, dst, submit_mrsl, extract_package)
        # Trailing comma to prevent double newlines
        print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def read_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 4, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
read_file \"$@\"
"""
    elif lang == 'python':
        s += """
(status, out) = read_file(*(sys.argv[1:]))
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def resubmit_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'job_id_list', 'job_id')
    if lang == 'sh':
        s += """
resubmit_job ${job_id_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = resubmit_job(job_id_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def rm_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # rm cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'fr',
                           '''        f)  server_flags="${server_flags}f"
            flags="${flags} -f";;
        r)  server_flags="${server_flags}r"
            flags="${flags} -r";;''')
    elif lang == 'python':
        s += parse_options(lang, 'fr',
                           '''    elif opt == "-f":
        server_flags += "f"
    elif opt == "-r":
        server_flags += "r"''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
rm_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = rm_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def rmdir_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # Client side wild card expansion doesn't make sense for rmdir

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'p',
                           '        p)  server_flags="${server_flags}p"\n            flags="${flags} -p";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'p',
                           '    elif opt == "-p":\n        server_flags += "p"'
                           )
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
rm_dir ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = rm_dir(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def scripts_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'script_dir="%s"\n' % keyword_auto
        s += parse_options(lang, 'd:', '        d)  script_dir="$OPTARG";;')
    elif lang == 'python':
        s += 'script_dir = "%s"\n' % keyword_auto
        s += parse_options(lang, 'd:',
                           '''    elif opt == "-d":
        script_dir = "%s" % val
''')
    s += arg_count_check(lang, 2, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
lang=$1
flavor=$2
generate_scripts \"$lang\" \"$flavor\" \"$script_dir\"
"""
    elif lang == 'python':
        s += """
lang = sys.argv[1]
flavor = sys.argv[2]
(status, out) = generate_scripts(lang, flavor, script_dir)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def sha1sum_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # Client side wild card expansion doesn't make sense for sha1sum

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
sha1_sum ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = sha1_sum(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def sharelink_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, 8)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
# optional 2nd to 8th argument depending on action - add dummies
sharelink \"$@\" '' '' '' '' '' '' ''
"""
    elif lang == 'python':
        s += """
# optional 2nd to 8th argument depending on action - add dummies
sys.argv +=  (8 - len(sys.argv[1:])) * ['']
(status, out) = sharelink(*(sys.argv[1:9]))
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def showbackup_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, 1)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
freeze_id=$1
show_backup \"$freeze_id\"
"""
    elif lang == 'python':
        s += """
freeze_id = sys.argv[1]
(status, out) = show_backup(freeze_id)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def showfreeze_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
flavor=$1
freeze_id=$2
show_freeze \"$flavor\" \"$freeze_id\"
"""
    elif lang == 'python':
        s += """
flavor = sys.argv[1]
freeze_id = sys.argv[2]
(status, out) = show_freeze(flavor, freeze_id)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def stat_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
stat_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = stat_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def status_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += "max_job_count='1000000'\n"
        s += parse_options(lang, 'm:S',
                           '''        m)  max_job_count="$OPTARG";;
        S)  server_flags="${server_flags}s"
            flags="${flags} -S";;''')
    elif lang == 'python':
        s += "max_job_count = '1000000'\n"
        s += parse_options(lang, 'm:S',
                           '''    elif opt == "-m":
        max_job_count = val
    elif opt == "-S":
        server_flags += "s"''')
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'job_id_list', 'job_id')
    if lang == 'sh':
        s += """
job_status ${job_id_list[@]} \"$max_job_count\"
"""
    elif lang == 'python':
        s += """
(status, out) = job_status(job_id_list, max_job_count)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def submit_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += "local_file=0\n"
        s += parse_options(lang, 'l',
                           '        l)  local_file=1;;'
                           )
    elif lang == 'python':
        s += "local_file = False\n"
        s += parse_options(lang, 'l',
                           '    elif opt == "-l":\n        local_file = True'
                           )
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
if [ \"$local_file\" -eq 1 ]; then
    extract_package=1
    submit_mrsl=1
    src_list=(\"${orig_args[@]}\")
    for src in \"${src_list[@]}\"; do
        dst=`basename \"$src\"`
        __put_file \"$src\" $dst $submit_mrsl $extract_package
    done
else
    submit_file ${path_list[@]}
fi
"""
    elif lang == 'python':
        s += """
if local_file:
    extract_package = True
    submit_mrsl = True

    src_list = sys.argv[1:]

    for src in src_list:
        dst = os.path.basename(src)
        (status, out) = __put_file(src, dst, submit_mrsl, extract_package)
        # Trailing comma to prevent double newlines
        print ''.join(out),
else:
    (status, out) = submit_file(path_list)
    # Trailing comma to prevent double newlines
    print ''.join(out),
    sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def tail_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'lines=20\n'
        s += parse_options(lang, 'n:', '        n)  lines="$OPTARG";;')
    elif lang == 'python':
        s += 'lines = 20\n'
        s += parse_options(lang, 'n:',
                           '''    elif opt == "-n":
        lines = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
tail_file \"$lines\" ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = tail_file(lines, path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def test_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'test_prefix="mig-test"\n'
        s += parse_options(lang, 'p:', '        p)  test_prefix="$OPTARG";;')
    elif lang == 'python':
        s += 'test_prefix = "mig-test"\n'
        s += parse_options(lang, 'p:',
                           '''    elif opt == "-p":
        test_prefix = val
''')
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
mrsl_test=\"${test_prefix}.mRSL\"
txt_test=\"${test_prefix}.txt\"
mrsl_helper=\"${test_prefix}-helper.mRSL\"
txt_helper=\"${test_prefix}-helper.txt\"

echo \"=== prepare local files for file operations ===\"
echo 'this is a test file used by the MiG self test' > \"${txt_test}\"
echo '::EXECUTE::' > \"${mrsl_test}\"
echo 'pwd' >> \"${mrsl_test}\"

echo '=== upload local files used as helpers in tests ==='
for ext in txt mRSL; do
    if [ \"$ext\" = \"txt\" ]; then 
        ext_test=\"${txt_test}\"
        ext_helper=\"${txt_helper}\"
    elif [ \"$ext\" = \"mRSL\" ]; then 
        ext_test=\"${mrsl_test}\"
        ext_helper=\"${mrsl_helper}\"
    else
        echo \"Invalid file extension ${ext}!\"
        exit 1
    fi
    put_file \"${ext_test}\" \"${ext_helper}\" 0 0 >& /dev/null
    if [ $? -ne 0 ]; then
        echo \"Upload ${ext_test} failed!\"
        exit 1
    else
        echo \"Upload ${ext_test} succeeded\"
    fi
done

if [ $# -eq 0 ]; then
    op_list=(%s)
else
    op_list=(\"$@\")
fi

for op in \"${op_list[@]}\"; do
    test_op \"$op\" \"${test_prefix}\"
done

echo '=== remove local and uploaded test files again ==='
for ext in txt mRSL; do
    if [ \"$ext\" = \"txt\" ]; then 
        ext_test=\"${txt_test}\"
        ext_helper=\"${txt_helper}\"
    elif [ \"$ext\" = \"mRSL\" ]; then 
        ext_test=\"${mrsl_test}\"
        ext_helper=\"${mrsl_helper}\"
    else
        echo \"Invalid file extension ${ext}!\"
        exit 1
    fi
    rm -f \"${ext_test}\" &> /dev/null
    rm_file \"path=${ext_helper}\" >& /dev/null
done
""" % ' '.join(script_ops)
    elif lang == 'python':
        s += """
mrsl_test = test_prefix + '.mRSL'
txt_test = test_prefix + '.txt'
mrsl_helper = test_prefix + '-helper.mRSL'
txt_helper = test_prefix + '-helper.txt'

print '=== prepare local files for file operations ==='
txt_fd = open(txt_test, 'w')
txt_fd.write('''this is a test file used by the MiG self test''')
txt_fd.close()
job_fd = open(mrsl_test, 'w')
job_fd.write('''::EXECUTE::
pwd
''')
job_fd.close()

print '=== upload local files used as helpers in tests ==='
for ext in ('txt', 'mRSL'):
    if ext == 'txt':
        ext_test = txt_test
        ext_helper = txt_helper
    elif ext == 'mRSL':
        ext_test = mrsl_test
        ext_helper = mrsl_helper
    else:
        print 'invalid ext: '+ ext
        sys.exit(1)
    (ret, out) = put_file(ext_test, ext_helper, False, False)
    if ret != 0:
        print 'Upload ' + ext_test + ' failed!'
        sys.exit(1)
    else:
        print 'Upload ' + ext_test + ' succeeded'

if sys.argv[1:]:
    op_list = sys.argv[1:]
else:   
    op_list = %s

for op in op_list:
    test_op(op, test_prefix)
    
print '=== remove local and uploaded test files again ==='
for ext in ('txt', 'mRSL'):
    if ext == 'txt':
        ext_test = txt_test
        ext_helper = txt_helper
    elif ext == 'mRSL':
        ext_test = mrsl_test
        ext_helper = mrsl_helper
    else:
        print 'invalid file extension: '+ext
        sys.exit(1)
    os.remove(ext_test)
    rm_file(['path=' + ext_helper])
""" % script_ops
    else:
        print('Error: %s not supported!' % lang)

    return s


def touch_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # touch cgi supports wild cards natively so no need to use
    # expand here
    # Client side wild card expansion doesn't make sense for touch

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
touch_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = touch_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def truncate_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'size=0\n'
        s += parse_options(lang, 'n:', '        n)  size="$OPTARG";;')
    elif lang == 'python':
        s += 'size = 0\n'
        s += parse_options(lang, 'n:',
                           '''    elif opt == "-n":
        size = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
truncate_file \"$size\" ${path_list[@]}
"""
    elif lang == 'python':
        s += """
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = truncate_file(size, path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def twofactor_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 3)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
# optional third argument depending on action - add dummy
twofactor_auth \"$@\" ''
"""
    elif lang == 'python':
        s += """
# optional third argument depending on action - add dummy
sys.argv.append('')
(status, out) = twofactor_auth(*(sys.argv[1:4]))
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def unzip_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # unzip cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'src')
    if lang == 'sh':
        s += """
# We included dst in packing above - remove again
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
unset src_list[$last_index]

unzip_file ${src_list[@]} \"$dst\"
"""
    elif lang == 'python':
        s += """
dst = sys.argv[-1]
del src_list[-1]
(status, out) = unzip_file(src_list, dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def uploadchunked_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # We should handle uploads like this:
    # migupload localfile . -> localfile
    # migupload localfile remotefile -> remotefile
    # migupload localfile remotedir -> remotedir/localfile
    # migupload ../localdir/localfile remotedir -> upload as file and expect server ERROR
    # migupload ../localdir/localfile remotedir/ -> remotedir/localfile
    # migupload ../localdir . -> ERROR?
    # migupload -r ../localdir . -> localdir
    # migupload -r ../localdir remotedir -> remotedir/localdir
    #                                   -> remotedir/localdir/*

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'recursive=0\n'
        s += parse_options(lang, 'r',
                           '        r)  recursive=1;;'
                           )
    elif lang == 'python':
        s += 'recursive = False\n'
        s += parse_options(lang, 'r',
                           '''    elif opt == "-r":
        recursive = True''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    # NOTE: using pack_list is cumbersome here so we don't
    if lang == 'sh':
        s += """
function upload_file_chunks() {
    path=\"$1\"
    current_dir=\"$2\"
    target_chunk_size=%d
    file_size=$(stat --printf='%%s' \"$path\") 
    chunk_count=$((file_size/target_chunk_size))
    # Make sure we have at least one chunk and chunks are about even size
    if [ $((chunk_size*chunk_count)) -lt $file_size ]; then
        chunk_count=$((chunk_count+1))
    fi
    # NOTE: split distributes evenly on chunk_count with remainder on last one
    chunk_size=$((file_size/chunk_count))
    action=\"put\"
    chunk_no=0
    while [ $chunk_no -lt $chunk_count ]; do
        uploadchunked_put \"$path\" \"$current_dir\" $chunk_no $chunk_size $chunk_count $file_size
        chunk_no=$((chunk_no+1))
    done
    # Fake last chunk again with move to final destination
    chunk_no=$((chunk_no-1))
    uploadchunked_move \"$path\" \"$current_dir\" $chunk_no $chunk_size $chunk_count $file_size
}
""" % upload_block_size
        s += """
src_list=(\"$@\")
dst=\"${src_list[$(($#-1))]}\"
unset src_list[$(($#-1))]

# For loop automatically expands wild cards
# We use the advice from http://tldp.org/LDP/abs/html/internalvariables.html
# to explicitly remove ordinary space from IFS to prevent spaces in filenames
# breaking things. Newlines and tabs are still effective.
IFS=\"$(printf '\n\t')\" 
for src in ${src_list[@]}; do
    if [ ! -e \"$src\" ]; then
        echo \"No such file or directory: $src !\"
        continue
    fi
    if [ -d \"$src\" ]; then
        if [ $recursive -ne 1 ]; then
            echo \"Nonrecursive upload skipping directory: $src\"
            continue
        fi
        # Recursive dirs may not exist - create them first
        # we could leave it to backend handler but then we miss empty dirs
        src_parent=`dirname $src`
        src_target=`basename $src`
        dirs=`cd $src_parent && find $src_target -type d`
        # force mkdir -p
        old_flags=\"$server_flags\"
        server_flags=\"p\"
        declare -a dir_list
        for dir in $dirs; do
            dir_list+=(\"path=$dst/$dir\")
        done
        mk_dir ${dir_list[@]}
        server_flags=\"$old_flags\"
        sources=`cd $src_parent && find $src_target -type f`
        for path in $sources; do
            rel_root=`dirname $path`
            current_dir=\"$dst/$rel_root\"
            upload_file_chunks \"$src_parent/$path\" \"$current_dir/\"
        done
    else
        current_dir=\"$dst\"
        upload_file_chunks \"$src\" \"$current_dir/\"
    fi
done
"""
    elif lang == 'python':
        s += """
from glob import glob
from math import ceil

def upload_file_chunks(path, current_dir):
    '''Split file into parts for chunked uploading like the fancy upload on web'''
    target_chunk_size = %d
    status, out, file_size = 0, [], os.path.getsize(path)
    # Make sure we have at least one chunk and chunks are about even size
    chunk_count = int(ceil((1.0 * file_size) / target_chunk_size))
    # NOTE: split distributes evenly on chunk_count with remainder on last one
    chunk_size = file_size / chunk_count
    action = \"put\"
    for chunk_no in xrange(chunk_count):
        (cur, tmp) = uploadchunked_put(path, current_dir, chunk_no, chunk_size,
                                       chunk_count, file_size)
        status &= cur
        out += tmp
    # Fake last chunk again for move to final destination
    (cur, tmp) = uploadchunked_move(path, current_dir, chunk_no, chunk_size,
                                    chunk_count, file_size)
    status &= cur
    out += tmp
    # Trailing comma to prevent double newlines
    print ''.join(out),
    return status
""" % upload_block_size
        s += """
raw_list = sys.argv[1:-1]
dst = sys.argv[-1]

# Expand sources
status = 2
src_list = []
for src in raw_list:
    expanded = glob(src)
    if expanded:
        src_list += expanded
    else:
        # keep bogus pattern for correct output order
        src_list += [src]

for src in src_list:
    if not os.path.exists(src):
        print \"No such file or directory: %s !\" % src
        continue
    if os.path.isdir(src):
        if not recursive:
            print \"Nonrecursive upload skipping directory: %s\" % src
            continue
        src_parent = os.path.abspath(os.path.dirname(src))
        for root, dirs, files in os.walk(os.path.abspath(src)):
            # Recursive dirs may not exist - create them first
            # force mkdir -p
            old_flags = server_flags
            server_flags = \"p\"
            rel_root = root.replace(src_parent, '', 1).lstrip(os.sep)
            dir_list = ['path=%s' % os.path.join(dst, rel_root, i) for i in dirs]
            # add current root
            dir_list.append('path=%s' % os.path.join(dst, rel_root))
            mk_dir(dir_list)
            server_flags = old_flags
            for name in files:
                src_path = os.path.join(root, name)
                current_dir = os.path.join(dst, rel_root)
                status &= upload_file_chunks(src_path, current_dir)
    else:
        current_dir = dst
        status = upload_file_chunks(src, current_dir)
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def wc_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += parse_options(lang, 'blw',
                           '''        b)  server_flags="${server_flags}b"
            flags="${flags} -b";;
        l)  server_flags="${server_flags}l"
            flags="${flags} -l";;
        w)  server_flags="${server_flags}w"
            flags="${flags} -w";;''')
    elif lang == 'python':
        s += parse_options(lang, 'blw',
                           '''    elif opt == "-b":
        server_flags += "b"
    elif opt == "-l":
        server_flags += "l"
    elif opt == "-w":
        server_flags += "w"''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'path_list', 'path')
    if lang == 'sh':
        s += """
wc_file ${path_list[@]}
"""
    elif lang == 'python':
        s += """
(status, out) = wc_file(path_list)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def write_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 4, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
write_file \"$@\"
"""
    elif lang == 'python':
        s += """
(status, out) = write_file(*(sys.argv[1:]))
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


def zip_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # zip cgi supports wild cards natively so no need to use
    # expand here

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += 'current_dir=""\n'
        s += parse_options(lang, 'w:', '        w)  current_dir="$OPTARG";;')
    elif lang == 'python':
        s += 'current_dir = ""\n'
        s += parse_options(lang, 'w:',
                           '''    elif opt == "-w":
        current_dir = val
''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    s += pack_list(lang, 'src_list', 'src')
    if lang == 'sh':
        s += """
# We included dst in packing above - remove again
last_index=$((${#src_list[@]}-1))
dst=\"${orig_args[$last_index]}\"
unset src_list[$last_index]

# current_dir may be empty
zip_file \"$current_dir\" ${src_list[@]} \"$dst\"
"""
    elif lang == 'python':
        s += """
# We included dst in packing above - remove again
dst = sys.argv[-1]
del src_list[-1]
(status, out) = zip_file(current_dir, src_list, dst)
# Trailing comma to prevent double newlines
print ''.join(out),
sys.exit(status)
"""
    else:
        print('Error: %s not supported!' % lang)

    return s


# ######################
# Generator functions #
# ######################


def generate_cancel(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_cat(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_cp(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_createbackup(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_createfreeze(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_datatransfer(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_deletebackup(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_deletefreeze(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_doc(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_freezedb(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_imagepreview(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)


def generate_get(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += expand_function(configuration, lang, curl_cmd)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_grep(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_head(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_jobaction(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_lib(configuration, script_ops, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate shared lib for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s for %s' % (op, lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += curl_perform_flex(lang, 'user_conf', 'base_val', 'url_val',
                                    'post_val', 'urlenc_val', 'query_val')
        script += expand_function(configuration, lang, curl_cmd)
        for function in script_ops:
            script += shared_op_function(configuration, function, lang,
                                         curl_cmd)
        script += basic_main_init(lang)
        script += check_conf_readable(lang)
        script += configure(lang)

        write_script(script, dest_dir + os.sep + script_name, mode=0o644)

    return True


def generate_liveio(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_ls(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_login(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += curl_perform_flex(lang, 'user_conf', 'base_val', 'url_val',
                                    'post_val', 'urlenc_val', 'query_val')
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_logout(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += curl_perform_flex(lang, 'user_conf', 'base_val', 'url_val',
                                    'post_val', 'urlenc_val', 'query_val')
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_md5sum(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_mkdir(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_mqueue(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_mv(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_put(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)

        # Recursive put requires mkdir

        script += mkdir_function(configuration, lang, curl_cmd)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_read(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_resubmit(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_rm(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_rmdir(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_scripts(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_sha1sum(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_sharelink(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_showbackup(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_showfreeze(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_stat(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_status(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_submit(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_tail(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_test(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)

        # use put function for preparation and rm function for clean up

        script += shared_op_function(configuration, 'put', lang, curl_cmd)
        script += shared_op_function(configuration, 'rm', lang, curl_cmd)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_touch(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_truncate(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_twofactor(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_unzip(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_uploadchunked(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)

        # Recursive upload requires mkdir

        script += mkdir_function(configuration, lang, curl_cmd)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_wc(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_write(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_zip(configuration, scripts_languages, dest_dir='.'):
    """Generate the corresponding script"""

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('generate_', '')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += shared_usage_function(op, lang, extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += shared_op_function(configuration, op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


# Defaults

verbose_mode = False
shared_lib = True
test_script = True
include_license = True

# Supported MiG operations (don't add 'test' as it is optional)

# TODO: add find, *re, jobfeasible, jobschedule, mrslview, people,
#           settings, vm*,

script_ops = [
    'cancel',
    'cat',
    'cp',
    'datatransfer',
    'doc',
    'freezedb',
    'imagepreview',
    'get',
    'grep',
    'head',
    'jobaction',
    'liveio',
    'ls',
    'login',
    'logout',
    'md5sum',
    'mkdir',
    'mqueue',
    'mv',
    'put',
    'read',
    'rm',
    'rmdir',
    'scripts',
    'sha1sum',
    'sharelink',
    'stat',
    'status',
    'submit',
    'resubmit',
    'tail',
    'touch',
    'truncate',
    'twofactor',
    'unzip',
    'uploadchunked',
    'wc',
    'write',
    'zip',
    # NOTE: test requires create, show, delete archive in that order
    'createbackup',
    'showbackup',
    'deletebackup',
    'createfreeze',
    'showfreeze',
    'deletefreeze',
]

# Script prefix for all user scripts

mig_prefix = 'mig'

# Default commands:

sh_lang = 'sh'
sh_cmd = '/bin/sh'
sh_ext = 'sh'
python_lang = 'python'

# python_cmd is only actually used on un*x so don't worry about path

python_cmd = '/usr/bin/python'
python_ext = 'py'

# curl_cmd must be generic for cross platform support

curl_cmd = 'curl'
dest_dir = '.'

# ###########
# ## Main ###
# ###########
# Only run interactive commands if called directly as executable

if __name__ == '__main__':
    opts_str = 'c:d:hlp:s:tvV'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opts_str)
    except getopt.GetoptError as goe:
        print('Error: %s' % goe)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            curl_cmd = val
        elif opt == '-d':
            dest_dir = val
        elif opt == '-i':
            include_license = False
        elif opt == '-l':
            shared_lib = False
        elif opt == '-p':
            python_cmd = val
        elif opt == '-s':
            sh_cmd = val
        elif opt == '-t':
            test_script = True
        elif opt == '-v':
            verbose_mode = True
        elif opt == '-V':
            version()
            sys.exit(0)
        elif opt == '-h':
            usage()
            sys.exit(0)
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(1)

    configuration = get_configuration_object()

    verbose(verbose_mode, 'using curl from: %s' % curl_cmd)
    verbose(verbose_mode, 'using sh from: %s' % sh_cmd)
    verbose(verbose_mode, 'using python from: %s' % python_cmd)
    verbose(verbose_mode, 'writing script to: %s' % dest_dir)

    if not os.path.isdir(dest_dir):
        print("Error: destination directory doesn't exist!")
        sys.exit(1)

    argc = len(args)
    if argc == 0:

        # Add new languages here

        languages = [(sh_lang, sh_cmd, sh_ext), (python_lang,
                                                 python_cmd, python_ext)]
        for (lang, cmd, ext) in languages:
            print('Generating %s scripts' % lang)
    else:
        languages = []

        # check arguments

        for lang in args:
            if lang == 'sh':
                interpreter = sh_cmd
                extension = sh_ext
            elif lang == 'python':
                interpreter = python_cmd
                extension = python_ext
            else:
                print('Unknown script language: %s - ignoring!' % lang)
                continue

            print('Generating %s scripts' % lang)

            languages.append((lang, interpreter, extension))

    # Generate all scripts

    for op in script_ops:
        generator = 'generate_%s' % op
        eval(generator)(configuration, languages, dest_dir)

    if shared_lib:
        generate_lib(configuration, script_ops, languages, dest_dir)

    if test_script:
        generate_test(configuration, languages, dest_dir)

    if include_license:
        write_license(configuration, dest_dir)

    sys.exit(0)
