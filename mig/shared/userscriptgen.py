#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userscriptgen - Generator backend for user scripts
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

# TODO: finish generator for automatic testing of scripts
# TODO: filter exit code from cgi output and use in own exit code?

# TODO: mig-ls.* -r fib.out incorrectly lists entire home recursively
# TODO: ls -r is not recursive -> use -R!

"""Generate MiG user scripts for the specified programming
languages. Called without arguments the generator creates scripts
for all supported languages. If one or more languages are supplied
as arguments, only those languages will be generated.
"""

import sys
import getopt

# Generator version (automagically updated by cvs)

__version__ = '$Revision: 2591 $'

# $Id: userscriptgen.py 2591 2009-02-25 10:56:13Z jones $

# Save original __version__ before truncate with wild card import

_userscript_version = __version__
from publicscriptgen import *
_publicscript_version = __version__
__version__ = '%s,%s' % (_userscript_version, _publicscript_version)

# ######################################
# Script generator specific functions #
# ######################################
# Generator usage


def usage():
    print 'Usage: userscriptgen.py OPTIONS [LANGUAGE ... ]'
    print 'Where OPTIONS include:'
    print ' -c CURL_CMD\t: Use curl from CURL_CMD'
    print ' -d DST_DIR\t: write scripts to DST_DIR'
    print ' -h\t\t: Print this help'
    print ' -l\t\t: Do not generate shared library module'
    print ' -p PYTHON_CMD\t: Use PYTHON_CMD as python interpreter'
    print ' -s SH_CMD\t: Use SH_CMD as sh interpreter'
    print ' -t\t\t: Generate self testing script'
    print ' -v\t\t: Verbose output'
    print ' -V\t\t: Show version'


def version():
    print 'MiG User Script Generator: %s' % __version__


def version_function(lang):
    s = ''
    s += begin_function(lang, 'version', [])
    if lang == 'sh':
        s += '\techo "MiG User Scripts: %s"\n' % __version__
    elif lang == 'python':
        s += '\tprint "MiG User Scripts: %s"\n' % __version__
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

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] JOBID [JOBID ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def cat_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def doc_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [TOPIC ...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def get_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...] FILE'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n\techo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def head_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tShow first N lines of the file(s)'
    if lang == 'sh':
        s += '\n\techo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def ls_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [FILE ...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    all_usage_string = "-a\t\tDo not hide entries starting with '.'"
    long_usage_string = '-l\t\tDisplay long format'
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n\techo "%s"' % all_usage_string
        s += '\n\techo "%s"' % long_usage_string
        s += '\n\techo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % all_usage_string
        s += '\n\tprint "%s"' % long_usage_string
        s += '\n\tprint "%s"' % recursive_usage_string

    s += end_function(lang, 'usage')

    return s


def mkdir_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] DIRECTORY [DIRECTORY ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    parents_usage_string = '-p\t\tmake parent directories as needed'
    if lang == 'sh':
        s += '\n\techo "%s"' % parents_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % parents_usage_string
    s += end_function(lang, 'usage')

    return s


def mv_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] SRC [SRC...] DST'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def put_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s FILE [FILE ...] FILE' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)

    package_usage_string = \
        '-p\t\tSubmit mRSL files (also in packages if -x is specified) after upload'
    recursive_usage_string = '-r\t\tact recursively'
    extract_usage_string = \
        '-x\t\tExtract package (.zip etc) after upload'
    if lang == 'sh':
        s += '\n\techo "%s"' % package_usage_string
        s += '\n\techo "%s"' % recursive_usage_string
        s += '\n\techo "%s"' % extract_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % package_usage_string
        s += '\n\tprint "%s"' % recursive_usage_string
        s += '\n\tprint "%s"' % extract_usage_string

    s += end_function(lang, 'usage')

    return s


def read_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] START END SRC DST'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def resubmit_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s JOBID [JOBID ...]' % (mig_prefix, op,
            extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def rm_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    recursive_usage_string = '-r\t\tact recursively'
    if lang == 'sh':
        s += '\n\techo "%s"' % recursive_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % recursive_usage_string
    s += end_function(lang, 'usage')

    return s


def rmdir_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] DIRECTORY [DIRECTORY ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    parents_usage_string = '-p\t\tremove parent directories as needed'
    if lang == 'sh':
        s += '\n\techo "%s"' % parents_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % parents_usage_string

    s += end_function(lang, 'usage')

    return s


def stat_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def status_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [JOBID ...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    max_jobs_usage_string = '-m M\t\tShow status for at most M jobs'
    sort_jobs_usage_string = '-S\t\tSort jobs by modification time'
    if lang == 'sh':
        s += '\n\techo "%s"' % max_jobs_usage_string
        s += '\n\techo "%s"' % sort_jobs_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % max_jobs_usage_string
        s += '\n\tprint "%s"' % sort_jobs_usage_string

    s += end_function(lang, 'usage')

    return s


def submit_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s FILE [FILE ...]' % (mig_prefix, op,
            extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def tail_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tShow last N lines of the file(s)'
    if lang == 'sh':
        s += '\n\techo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def test_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [OPERATION ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def touch_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [FILE ...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def truncate_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    lines_usage_string = '-n N\t\tTruncate file(s) to at most N bytes'
    if lang == 'sh':
        s += '\n\techo "%s"' % lines_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % lines_usage_string
    s += end_function(lang, 'usage')

    return s


def wc_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] FILE [FILE ...]'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    bytes_usage_string = '-b N\t\tShow byte count'
    lines_usage_string = '-l N\t\tShow line count'
    words_usage_string = '-w N\t\tShow word count'
    if lang == 'sh':
        s += '\n\techo "%s"' % bytes_usage_string
        s += '\n\techo "%s"' % lines_usage_string
        s += '\n\techo "%s"' % words_usage_string
    elif lang == 'python':
        s += '\n\tprint "%s"' % bytes_usage_string
        s += '\n\tprint "%s"' % lines_usage_string
        s += '\n\tprint "%s"' % words_usage_string
    s += end_function(lang, 'usage')

    return s


def write_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] START END SRC DST'\
         % (mig_prefix, op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def liveoutput_usage_function(lang, extension):

    # Extract op from function name

    op = sys._getframe().f_code.co_name.replace('_usage_function', '')

    usage_str = 'Usage: %s%s.%s [OPTIONS] [JOBID ...]' % (mig_prefix,
            op, extension)
    s = ''
    s += begin_function(lang, 'usage', [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


# ##########################
# Communication functions #
# ##########################


def shared_op_function(op, lang, curl_cmd):
    """General wrapper for the specific op functions.
    Simply rewrites first arg to function name."""

    return eval('%s_function' % op)(lang, curl_cmd)


def cancel_function(lang, curl_cmd, curl_flags=''):
    relative_url = '"cgi-bin/canceljob.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;job_id=$job_id"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;job_id=%s' % (server_flags, job_id)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'cancel_job', ['job_id'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'cancel_job')
    return s


def cat_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/cat.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'cat_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'cat_file')
    return s


def doc_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/docs.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;search=$search;show=$show"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;search=%s;show=%s' % (server_flags, search, show)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'show_doc', ['search', 'show'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'show_doc')
    return s


def expand_function(lang, curl_cmd, curl_flags='--compressed'):
    """Call the expand cgi script with the string 'path_list' as argument. Thus
    the variable 'path_list' should be on the form
    \"path=pattern1[;path=pattern2[ ... ]]\"
    This may seem a bit awkward but it's difficult to do in a better way when
    begin_function() doesn't support variable length or array args.
    """

    relative_url = '"cgi-bin/expand.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;$path_list;with_dest=$destinations"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s;with_dest=%s' % (server_flags, path_list, destinations)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'expand_name', ['path_list',
                        'server_flags', 'destinations'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'expand_name')
    return s


def get_function(lang, curl_cmd, curl_flags='--compressed --create-dirs'
                 ):
    post_data = '""'
    query = '""'
    if lang == 'sh':

        # TODO: should we handle below double slash problem here, too?

        relative_url = '"cert_redirect/$src_path"'
        curl_target = '"--output $dst_path"'
    elif lang == 'python':

        # Apache chokes on possible double slash in url and that causes
        # fatal errors in migfs-fuse - remove it from src_path.

        relative_url = '"cert_redirect/%s" % src_path.lstrip("/")'
        curl_target = "'--output %s' % dst_path"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'get_file', ['src_path', 'dst_path'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
        )
    s += end_function(lang, 'get_file')
    return s


def head_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/head.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;$path_list;lines=$lines"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s;lines=%s' % (server_flags, path_list, lines)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'head_file', ['lines', 'path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'head_file')
    return s


def ls_function(lang, curl_cmd, curl_flags='--compressed'):
    """Call the ls cgi script with the string 'path_list' as argument. Thus
    the variable 'path_list' should be on the form
    \"path=pattern1[;path=pattern2[ ... ]]\"
    This may seem a bit awkward but it's difficult to do in a better way when
    begin_function() doesn't support variable length or array args.
    """

    relative_url = '"cgi-bin/ls.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'ls_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'ls_file')
    return s


def mkdir_function(lang, curl_cmd, curl_flags=''):
    """Call the mkdir cgi script with 'path' as argument."""

    relative_url = '"cgi-bin/mkdir.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'mk_dir', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'mk_dir')
    return s


def mv_function(lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the string 'src_list' as argument. Thus
    the variable 'path_list' should be on the form
    \"src=pattern1[;src=pattern2[ ... ]]\"
    This may seem a bit awkward but it's difficult to do in a better way when
    begin_function() doesn't support variable length or array args.
    """

    relative_url = '"cgi-bin/mv.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;dst=$dst;$src_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;dst=%s;%s' % (server_flags, dst, src_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'mv_file', ['src_list', 'dst'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'mv_file')
    return s


def put_function(lang, curl_cmd, curl_flags='--compressed'):
    post_data = '""'
    query = '""'
    if lang == 'sh':

        # TODO: should we handle below double slash problem here, too?

        relative_url = '"$dst_path"'
        curl_target = \
            '"--upload-file $src_path --header $content_type -X CERTPUT"'
    elif lang == 'python':

        # Apache chokes on possible double slash in url and that causes
        # fatal errors in migfs-fuse - remove it from src_path.

        relative_url = '"%s" % dst_path.lstrip("/")'
        curl_target = \
            "'--upload-file %s --header %s -X CERTPUT' % (src_path, content_type)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'put_file', ['src_path', 'dst_path',
                        'submit_mrsl', 'extract_package'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    if lang == 'sh':
        s += \
            """
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
        s += \
            """
        content_type = "''"
        if submit_mrsl and extract_package:
           content_type = 'Content-Type:submitandextract'
        elif submit_mrsl:
           content_type = 'Content-Type:submitmrsl'
        elif extract_package:
           content_type = 'Content-Type:extractpackage'
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
        )
    s += end_function(lang, 'put_file')
    return s


def read_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/rangefileaccess.py"'
    post_data = '""'
    if lang == 'sh':
        query = \
            '"?output_format=txt;flags=$server_flags;file_startpos=$first;file_endpos=$last;path=$src_path"'
        curl_target = '"--output $dst_path"'
    elif lang == 'python':
        query = \
            "'?output_format=txt;flags=%s;file_startpos=%s;file_endpos=%s;path=%s' % (server_flags, first, last, src_path)"
        curl_target = "'--output %s' % dst_path"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'read_file', ['first', 'last', 'src_path'
                        , 'dst_path'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
        )
    s += end_function(lang, 'read_file')
    return s


def resubmit_function(lang, curl_cmd, curl_flags=''):
    relative_url = '"cgi-bin/resubmit.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;job_id=$job_id"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;job_id=%s' % (server_flags, job_id)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'resubmit_job', ['job_id'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'resubmit_job')
    return s


def rm_function(lang, curl_cmd, curl_flags=''):
    """Call the rm cgi script with the string 'path_list' as argument. Thus
    the variable 'path_list' should be on the form
    \"path=pattern1[;path=pattern2[ ... ]]\"
    This may seem a bit awkward but it's difficult to do in a better way when
    begin_function() doesn't support variable length or array args.
    """

    relative_url = '"cgi-bin/rm.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'rm_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'rm_file')
    return s


def rmdir_function(lang, curl_cmd, curl_flags=''):
    """Call the rmdir cgi script with 'path' as argument."""

    relative_url = '"cgi-bin/rmdir.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'rm_dir', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'rm_dir')
    return s


def stat_function(lang, curl_cmd, curl_flags='--compressed'):
    """Call the corresponding cgi script with the string 'path_list' as argument. Thus
    the variable 'path_list' should be on the form
    \"path=pattern1[;path=pattern2[ ... ]]\"
    This may seem a bit awkward but it's difficult to do in a better way when
    begin_function() doesn't support variable length or array args.
    """

    relative_url = '"cgi-bin/stat.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'stat_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'stat_file')
    return s


def status_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/jobstatus.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;max_jobs=$max_job_count;$job_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;max_jobs=%s;%s' % (server_flags, max_job_count, job_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'job_status', ['job_list', 'max_job_count'
                        ])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += max_jobs_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'job_status')
    return s


def submit_function(lang, curl_cmd, curl_flags=''):

    # Simply use Put function

    s = put_function(lang, curl_cmd, curl_flags)
    return s.replace('put_file', 'submit_file')


def tail_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/tail.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;lines=$lines;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;lines=%s;%s' % (server_flags, lines, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'tail_file', ['lines', 'path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'tail_file')
    return s


def test_function(lang, curl_cmd, curl_flags=''):

    # TODO: pass original -c and -s options on to tested scripts

    s = ''
    s += begin_function(lang, 'test_op', ['op'])
    if lang == 'sh':
        s += \
            """
        valid=0
        valid_ops=(%s)
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
        echo \"running $op test(s)\"
        cmd=\"$path_prefix/%s${op}.%s\"
        declare -a cmd_args
        declare -a verify_cmd
        case $op in
           'cancel')
              pre_cmd=\"$path_prefix/migsubmit.sh mig-test.mRSL\"
              cmd_args[1]='DUMMY_JOB_ID'
              ;;
           'cat')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'doc')
              cmd_args[1]=''
              ;;
           'get')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt .'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'head')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'ls')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'mkdir')
              pre_cmd=\"$path_prefix/migrm.sh -r mig-test-dir\"
              cmd_args[1]='mig-test-dir'
              verify_cmd[1]=\"$path_prefix/migls.sh mig-test-dir\"
              post_cmd=\"$path_prefix/migrm.sh -r mig-test-dir\"
              ;;
           'mv')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt mig-test-new.txt'
              post_cmd=\"$path_prefix/migrm.sh mig-test-new.txt\"
              ;;
           'put')
              pre_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              cmd_args[1]='mig-test.txt .'
              verify_cmd[1]=\"$path_prefix/migls.sh mig-test.txt\"
              post_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              cmd_args[2]='mig-test.t*t mig-test.txt'
              verify_cmd[2]=\"$path_prefix/migrm.sh mig-test.txt\"
              cmd_args[3]='mig-test.txt mig-test.txt'
              verify_cmd[3]=\"$path_prefix/migrm.sh mig-test.txt\"
              cmd_args[4]='mig-test.txt mig-remote-test.txt'
              verify_cmd[4]=\"$path_prefix/migrm.sh mig-remote-test.txt\"
              cmd_args[5]='mig-test.txt mig-test-dir/'
              verify_cmd[5]=\"$path_prefix/migrm.sh mig-test-dir/mig-test.txt\"
              cmd_args[6]='mig-test.txt mig-test-dir/mig-remote-test.txt'
              verify_cmd[6]=\"$path_prefix/migrm.sh mig-test-dir/mig-remote-test.txt\"

              # Disabled since put doesn't support wildcards in destination (yet?)
              # cmd_args[]='mig-test.txt 'mig-test-d*/''
              # cmd_args[]='mig-test.txt 'mig-test-d*/mig-remote-test.txt''
              # verify_cmd[]=\"$path_prefix/migrm.sh mig-test-dir/mig-remote-test.txt\"
              # verify_cmd[]=\"$path_prefix/migrm.sh mig-test-dir/mig-remote-test.txt\"
              ;;
           'read')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='0 16 mig-test.txt -'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'rm')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              verify_cmd[1]=\"$path_prefix/migls.sh mig-test.txt\"
              ;;
           'rmdir')
              pre_cmd=\"$path_prefix/migmkdir.sh mig-test-dir\"
              cmd_args[1]='mig-test-dir'
              verify_cmd[1]=\"$path_prefix/migls.sh mig-test-dir\"
              post_cmd=\"$path_prefix/migrm.sh -r mig-test-dir\"
              ;;
           'stat')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'status')
              cmd_args[1]=''
              ;;
           'submit')
              cmd_args[1]='mig-test.mRSL'
              ;;
           'tail')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              ;;
           'touch')
              pre_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              cmd_args[1]='mig-test.txt'
              verify_cmd[1]=\"$path_prefix/migls.sh mig-test.txt\"
              post_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              ;;
           'truncate')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='mig-test.txt'
              post_cmd[1]=\"$path_prefix/migrm.sh mig-test.txt\"
              ;;
           'wc')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt\"
              cmd_args[1]='mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           'write')
              pre_cmd=\"$path_prefix/migput.sh mig-test.txt .\"
              cmd_args[1]='4 8 mig-test.txt mig-test.txt'
              post_cmd=\"$path_prefix/migrm.sh -r mig-test.txt\"
              ;;
           *)
           echo \"No test available for $op!\"
              return 1
              ;;
        esac
    

        index=1
        for args in \"${cmd_args[@]}\"; do
            echo \"test $index: $cmd $test_flags $args\"
            pre=\"${pre_cmd[index]}\"
            if [ -n \"$pre\" ]; then
                echo \"setting up with: $pre\"
                $pre >& /dev/null
            fi
            ./$cmd $test_flags $args >& /dev/null
            ret=$?
            if [ $ret -eq 0 ]; then
                echo \"   $op test $index SUCCEEDED\"
            else
                echo \"   $op test $index FAILED!\"
            fi
            verify=\"${verify_cmd[index]}\"
            if [ -n \"$verify\" ]; then
                echo \"verifying with: $verify\"
                $verify
            fi
            post=\"${post_cmd[index]}\"
            if [ -n \"$post\" ]; then
                echo \"cleaning up with: $post\"
                $post >& /dev/null
            fi
            index=$((index+1))
        done
        return $ret
"""\
             % (' '.join(script_ops), mig_prefix, 'sh')
    elif lang == 'python':
        s += """
        print \"running %s test\" % (op)
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s += end_function(lang, 'test_op')
    return s


def touch_function(lang, curl_cmd, curl_flags=''):
    """Call the touch cgi script with 'path' as argument."""

    relative_url = '"cgi-bin/touch.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'touch_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'touch_file')
    return s


def truncate_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/truncate.py"'
    query = '""'
    if lang == 'sh':
        post_data = \
            '"output_format=txt;flags=$server_flags;size=$size;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;size=%s;%s' % (server_flags, size, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'truncate_file', ['size', 'path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'truncate_file')
    return s


def wc_function(lang, curl_cmd, curl_flags=''):
    relative_url = '"cgi-bin/wc.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$path_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, path_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'wc_file', ['path_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'wc_file')
    return s


def write_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/rangefileaccess.py"'
    post_data = '""'
    if lang == 'sh':
        query = \
            '"?output_format=txt;flags=$server_flags;file_startpos=$first;file_endpos=$last;path=$dst_path"'
        curl_target = '"--upload-file $src_path"'
    elif lang == 'python':
        query = \
            "'?output_format=txt;flags=%s;file_startpos=%s;file_endpos=%s;path=%s' % (server_flags, first, last, dst_path)"
        curl_target = "'--upload-file %s' % src_path"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'write_file', ['first', 'last', 'src_path'
                        , 'dst_path'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        curl_target,
        )
    s += end_function(lang, 'write_file')
    return s


def liveoutput_function(lang, curl_cmd, curl_flags='--compressed'):
    relative_url = '"cgi-bin/liveoutput.py"'
    query = '""'
    if lang == 'sh':
        post_data = '"output_format=txt;flags=$server_flags;$job_list"'
    elif lang == 'python':
        post_data = \
            "'output_format=txt;flags=%s;%s' % (server_flags, job_list)"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'job_liveoutput', ['job_list'])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(
        lang,
        relative_url,
        post_data,
        query,
        curl_cmd,
        curl_flags,
        )
    s += end_function(lang, 'job_liveoutput')
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
    with wild cards."""

    s = ''
    if lang == 'sh':
        s += \
            """
declare -a %s
# Save original args
orig_args=(\"${%s[@]}\")

index=1
for pattern in \"${orig_args[@]}\"; do
    expanded_path=$(expand_name \"path=$pattern\" \"$server_flags\" \"%s\" 2> /dev/null)
    set -- $expanded_path
    shift; shift
    exit_code=\"$1\"
    shift; shift; shift; shift; shift; shift; shift; shift    
    if [ \"$exit_code\" -ne \"0\" ]; then
"""\
             % (expanded_list, input_list, str(destinations).lower())
        if warnings:
            s += \
                """
        # output warning/error message(s) from expand
        echo \"$0: $@\"
"""
        s += \
            """
        continue
    fi
    while [ \"$#\" -gt \"0\" ]; do
        %s[$index]=$1
        index=$((index+1))
        shift
    done
done
"""\
             % expanded_list
    elif lang == 'python':
        s += \
            """
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
        print 'Error: %s not supported!' % lang
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

    # TODO: join to a single query now that cancel cgi supports multiple job_ids

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
job_list=(\"$@\")
for job in \"${job_list[@]}\"; do
    cancel_job \"$job\"
done
"""
    elif lang == 'python':
        s += \
            """
job_list = sys.argv[1:]
for job in job_list:
   (status, out) = cancel_job(job)
   for line in out:
      print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
    if lang == 'sh':
        s += \
            """
# Build the path string used directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
path_list="path=$1"
shift
while [ $# -gt "0" ]; do
    path_list="$path_list;path=$1"
    shift
done
cat_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = cat_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
        s += \
            """
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
        s += \
            """
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
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
                           '          r) server_flags="${server_flags}r";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'r',
                           '''        elif opt == "-r":
                server_flags += "r"''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':

        # Advice about parsing taken from:
        # http://www.shelldorado.com/goodcoding/cmdargs.html

        s += \
            """
orig_args=(\"$@\")
src_list=(\"$@\")
raw_dst=\"${src_list[$(($#-1))]}\"
unset src_list[$(($#-1))]
"""
        s += expand_list(lang, 'src_list', 'expanded_list', True)
        s += \
            """
# Use '--' to handle case where no expansions succeeded
set -- \"${expanded_list[@]}\"
while [ $# -gt 0 ]; do
    src=$1
    dest=$2
    shift; shift
    dst=\"$raw_dst/$dest\"
    get_file \"$src\" \"$dst\"
done
"""
    elif lang == 'python':
        s += """
raw_dst = sys.argv[-1]
src_list = sys.argv[1:-1]
"""
        s += expand_list(lang, 'src_list', 'expanded_list', True)
        s += \
            """
# Expand does not automatically split the outputlines, so they are still on
# the src\tdest form
for line in expanded_list:
    src, dest = line.split()
    dst = raw_dst + os.sep + dest
    (status, out) = get_file(src, dst)
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
        s += parse_options(lang, 'n:', '          n) lines="$OPTARG";;')
    elif lang == 'python':
        s += 'lines = 20\n'
        s += parse_options(lang, 'n:',
                           '''        elif opt == "-n":
                lines = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
path_list="path=$1"
shift
while [ $# -gt "0" ]; do
    path_list="$path_list;path=$1"
    shift
done
head_file $lines $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = head_file(lines, path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
                           '''          a) server_flags="${server_flags}a"
             flags="${flags} -a";;
          l) server_flags="${server_flags}l"
             flags="${flags} -l";;
          r) server_flags="${server_flags}r"
             flags="${flags} -r";;''')
    elif lang == 'python':
        s += parse_options(lang, 'alr',
                           '''        elif opt == "-a":
                server_flags += "a"
        elif opt == "-l":
                server_flags += "l"
        elif opt == "-r":
                server_flags += "r"''')
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used in ls directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
if [ $# -gt 0 ]; then
    path_list="path=$1"
    shift
else
    path_list="path=."
fi
while [ $# -gt "0" ]; do
    path_list="$path_list;path=$1"
    shift
done
ls_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
if len(sys.argv) == 1:
    sys.argv.append(".")
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = ls_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
                           '          p) server_flags="${server_flags}p"\n             flags="${flags} -p";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'p',
                           '        elif opt == "-p":\n                server_flags += "p"'
                           )
    s += arg_count_check(lang, 1, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used in rm directly:
# 'path=$1;path=$2;...;path=$N'
orig_args=(\"$@\")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
mk_dir $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path=$1;path=$2;...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = mk_dir(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
    if lang == 'sh':
        s += \
            """
# Build the src_list string used in mv directly:
# 'src="$1";src="$2";...;src=$N'
orig_args=("$@")
src_list="src=$1"
shift
while [ $# -gt 1 ]; do
    src_list="$src_list;src=$1"
    shift
done
dst=$1
mv_file $src_list $dst
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'src="$1";src="$2";...;src=$N'
src_list = \"src=%s\" % \";src=\".join(sys.argv[1:-1])
dst = sys.argv[-1]
(status, out) = mv_file(src_list, dst)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def put_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    # TODO: can we support wildcards in destination? (do we want to?)
    #      - destination like somedir*/somefile ?
    #        - when somedir* and somefile exists
    #        - when somedir* exists but somefile doesn't exists there
    #        -> we need to expand dirname alone too for both to work!
    #      - destination like somedir*/somefile* ?
    #      - what about ambiguous expansions?

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
                           '          p) submit_mrsl=1;;\n          r) recursive=1;;\n          x) extract_package=1;;'
                           )
    elif lang == 'python':
        s += 'submit_mrsl = False\n'
        s += 'recursive = False\n'
        s += 'extract_package = False\n'
        s += parse_options(lang, 'prx',
                           '''        elif opt == "-p":
                submit_mrsl = True
        elif opt == "-r":
                recursive = True
        elif opt == "-x":
                extract_package = True''')
    s += arg_count_check(lang, 2, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
src_list=(\"$@\")
raw_dst=\"${src_list[$(($#-1))]}\"
unset src_list[$(($#-1))]

# remove single '.' to avoid problems with missing ending slash
if [ \".\" = \"$raw_dst\" ]; then
    dst=\"\"
else
    dst=\"$raw_dst\"
fi

# The for loop automatically expands any wild cards in src_list
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
        src_parent=`dirname $src`
        src_target=`basename $src`
        dirs=`cd $src_parent && find $src_target -type d`
        # force mkdir -p
        old_flags=\"$server_flags\"
        server_flags=\"p\"
        dir_list=\"\"
        for dir in $dirs; do
            dir_list=\"$dir_list;path=$dst/$dir\"
        done
        mk_dir \"$dir_list\"
        server_flags=\"$old_flags\"
        sources=`cd $src_parent && find $src_target -type f`
        for path in $sources; do
            put_file \"$src_parent/$path\" \"$dst/$path\" $submit_mrsl $extract_package
        done
    else
        put_file \"$src\" \"$dst\" $submit_mrsl $extract_package
    fi
done
"""
    elif lang == 'python':
        s += \
            """
from glob import glob

raw_list = sys.argv[1:-1]

raw_dst = sys.argv[-1]
if \".\" == raw_dst:
    dst = \"\"
else:
    dst = raw_dst

# Expand sources
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
            dir_list = ';'.join(['path=%s' % os.path.join(dst, rel_root, i) for i in dirs])
            # add current root
            dir_list += ';path=%s' % os.path.join(dst, rel_root)
            mk_dir(dir_list)
            server_flags = \"$old_flags\"
            for name in files:
                src_path = os.path.join(root, name)
                dst_path = os.path.join(dst, rel_root, name)
                (status, out) = put_file(src_path, dst_path, submit_mrsl, extract_package)
    else:
        (status, out) = put_file(src, dst, submit_mrsl, extract_package)
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
read_file $@
"""
    elif lang == 'python':
        s += \
            """
(status, out) = read_file(*(sys.argv[1:]))
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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

    # TODO: wildcard expansion!

    if lang == 'sh':
        s += \
            """
src_list="$@"


for src in ${src_list}; do
   resubmit_job $src
done
"""
    elif lang == 'python':
        s += \
            """
src_list = sys.argv[1:]

for src in src_list:
   (status, out) = resubmit_job(src)
   for line in out:
      print line.strip()

"""
    else:
        print 'Error: %s not supported!' % lang

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
        s += parse_options(lang, 'r',
                           '          r) server_flags="${server_flags}r"\n             flags="${flags} -r";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'r',
                           '        elif opt == "-r":\n                server_flags += "r"'
                           )
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used in rm directly:
# 'path=$1;path=$2;...;path=$N'
orig_args=(\"$@\")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
rm_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path=$1;path=$2;...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = rm_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
                           '          p) server_flags="${server_flags}p"\n             flags="${flags} -p";;'
                           )
    elif lang == 'python':
        s += parse_options(lang, 'p',
                           '        elif opt == "-p":\n                server_flags += "p"'
                           )
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used in rm directly:
# 'path=$1;path=$2;...;path=$N'
orig_args=(\"$@\")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
rm_dir $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path=$1;path=$2;...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = rm_dir(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
    if lang == 'sh':
        s += \
            """
# Build the path string used directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
stat_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = stat_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def status_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    if lang == 'sh':
        s += "max_job_count=''\n"
        s += parse_options(lang, 'm:S',
                           '''          m) max_job_count="$OPTARG";;
          S) server_flags="${server_flags}s"
             flags="${flags} -S";;''')
    elif lang == 'python':
        s += "max_job_count = ''\n"
        s += parse_options(lang, 'm:S',
                           '''        elif opt == "-m":
                max_job_count = val
        elif opt == "-S":
                server_flags += "s"''')
    s += arg_count_check(lang, None, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the job_id string used directly:
# 'job_id="$1";job_id="$2";...;job_id=$N'
orig_args=("$@")
job_id_list=\"job_id=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    job_id_list=\"$job_id_list;job_id=$1\"
    shift
done
job_status $job_id_list $max_job_count
"""
    elif lang == 'python':
        s += \
            """
# Build the job_id_list string used in wild card expansion:
# 'job_id="$1";job_id="$2";...;job_id=$N'
job_id_list = \"job_id=%s\" % \";job_id=\".join(sys.argv[1:])
(status, out) = job_status(job_id_list, max_job_count)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def submit_main(lang):
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
    if lang == 'sh':
        s += \
            """
extract_package=1
submit_mrsl=1

src_list=(\"$@\")

for src in \"${src_list[@]}\"; do
   dst=`basename \"$src\"`
   submit_file \"$src\" $dst $submit_mrsl $extract_package
done
"""
    elif lang == 'python':
        s += \
            """
extract_package = True
submit_mrsl = True

src_list = sys.argv[1:]

for src in src_list:
   dst = os.path.basename(src)
   (status, out) = submit_file(src, dst, submit_mrsl, extract_package)
   for line in out:
      print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
        s += parse_options(lang, 'n:', '          n) lines="$OPTARG";;')
    elif lang == 'python':
        s += 'lines = 20\n'
        s += parse_options(lang, 'n:',
                           '''        elif opt == "-n":
                lines = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
tail_file $lines $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = tail_file(lines, path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def test_main(lang):
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
        s += \
            """
# Prepare for file operations
echo 'this is a test file used by the MiG self test' > mig-test.txt
echo '::EXECUTE::' > mig-test.mRSL
echo 'pwd' >> mig-test.mRSL

echo 'Upload test file used in other tests'
put_file mig-test.txt .  0 0 >& /dev/null
if [ $? -ne 0 ]; then
   echo 'Upload failed!'
   exit 1
else
   echo 'Upload succeeded'
fi

if [ $# -eq 0 ]; then
   op_list=(%s)
else
   op_list=(\"$@\")
fi

for op in \"${op_list[@]}\"; do
   test_op \"$op\"
done
"""\
             % ' '.join(script_ops)
    elif lang == 'python':
        s += \
            """
if len(sys.argv) - 1 == 0:
   op_list = %s
else:   
   op_list = sys.argv[1:]

for op in op_list:
   test_op(op)
"""\
             % script_ops
    else:
        print 'Error: %s not supported!' % lang

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
    if lang == 'sh':
        s += \
            """
# Build the path string used in url directly:
# 'path=$1;path=$2;...;path=$N'
orig_args=(\"$@\")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
touch_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path=$1;path=$2;...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = touch_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
        s += parse_options(lang, 'n:', '          n) size="$OPTARG";;')
    elif lang == 'python':
        s += 'size = 0\n'
        s += parse_options(lang, 'n:',
                           '''        elif opt == "-n":
                size = val
''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used directly:
# 'path="$1";path="$2";...;path=$N'
orig_args=("$@")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
truncate_file $size $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path="$1";path="$2";...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = truncate_file(size, path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
                           '''          b) server_flags="${server_flags}b"
             flags="${flags} -b";;
          l) server_flags="${server_flags}l"
             flags="${flags} -l";;
          w) server_flags="${server_flags}w"
             flags="${flags} -w";;''')
    elif lang == 'python':
        s += parse_options(lang, 'blw',
                           '''        elif opt == "-b":
                server_flags += "b"
        elif opt == "-l":
                server_flags += "l"
        elif opt == "-w":
                server_flags += "w"''')
    s += arg_count_check(lang, 1, None)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += \
            """
# Build the path string used in wc directly:
# 'path=$1;path=$2;...;path=$N'
orig_args=(\"$@\")
path_list=\"path=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    path_list=\"$path_list;path=$1\"
    shift
done
wc_file $path_list
"""
    elif lang == 'python':
        s += \
            """
# Build the path_list string used in wild card expansion:
# 'path=$1;path=$2;...;path=$N'
path_list = \"path=%s\" % \";path=\".join(sys.argv[1:])
(status, out) = wc_file(path_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

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
write_file $@
"""
    elif lang == 'python':
        s += \
            """
(status, out) = write_file(*(sys.argv[1:]))
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def liveoutput_main(lang):
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
        s += \
            """
# Build the job_id string used directly:
# 'job_id="$1";job_id="$2";...;job_id=$N'
orig_args=("$@")
job_id_list=\"job_id=$1\"
shift
while [ \"$#\" -gt \"0\" ]; do
    job_id_list=\"$job_id_list;job_id=$1\"
    shift
done
job_liveoutput $job_id_list
"""
    elif lang == 'python':
        s += \
            """
# Build the job_id_list string used in wild card expansion:
# 'job_id="$1";job_id="$2";...;job_id=$N'
job_id_list = \"job_id=%s\" % \";job_id=\".join(sys.argv[1:])
(status, out) = job_liveoutput(job_id_list)
for line in out:
    print line.strip()
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


# ######################
# Generator functions #
# ######################


def generate_cancel(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_cat(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_doc(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_get(scripts_languages, dest_dir='.'):

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
        script += expand_function(lang, curl_cmd)
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_head(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_lib(script_ops, scripts_languages, dest_dir='.'):

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
        script += expand_function(lang, curl_cmd)
        for function in script_ops:
            script += shared_op_function(function, lang, curl_cmd)
        script += basic_main_init(lang)
        script += check_conf_readable(lang)
        script += configure(lang)

        write_script(script, dest_dir + os.sep + script_name, mode=0644)

    return True


def generate_ls(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_mkdir(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_mv(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_put(scripts_languages, dest_dir='.'):

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

        script += mkdir_function(lang, curl_cmd)
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_read(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_resubmit(scripts_languages):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, script_name)

    return True


def generate_rm(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_rmdir(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_stat(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_status(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_submit(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_tail(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_test(scripts_languages, dest_dir='.'):

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

        # use put function for preparation

        script += shared_op_function('put', lang, curl_cmd)
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_touch(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_truncate(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_wc(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_write(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_liveoutput(scripts_languages, dest_dir='.'):

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
        script += shared_op_function(op, lang, curl_cmd)
        script += shared_main(op, lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


# Defaults

verbose_mode = False
shared_lib = True
test_script = True

# Supported MiG operations (don't add 'test' as it is optional)
# add resubmit?

script_ops = [
    'cancel',
    'cat',
    'doc',
    'get',
    'head',
    'ls',
    'mkdir',
    'mv',
    'put',
    'read',
    'rm',
    'rmdir',
    'stat',
    'status',
    'submit',
    'tail',
    'touch',
    'truncate',
    'wc',
    'write',
    'liveoutput',
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
    except getopt.GetoptError, e:
        print 'Error: ', e.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            curl_cmd = val
        elif opt == '-d':
            dest_dir = val
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
            print 'Error: %s not supported!' % opt
            usage()
            sys.exit(1)

    verbose(verbose_mode, 'using curl from: %s' % curl_cmd)
    verbose(verbose_mode, 'using sh from: %s' % sh_cmd)
    verbose(verbose_mode, 'using python from: %s' % python_cmd)
    verbose(verbose_mode, 'writing script to: %s' % dest_dir)

    if not os.path.isdir(dest_dir):
        print "Error: destination directory doesn't exist!"
        sys.exit(1)

    argc = len(args)
    if argc == 0:

        # Add new languages here

        languages = [(sh_lang, sh_cmd, sh_ext), (python_lang,
                     python_cmd, python_ext)]
        for (lang, cmd, ext) in languages:
            print 'Generating %s scripts' % lang
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
                print 'Unknown script language: %s - ignoring!' % lang
                continue

            print 'Generating %s scripts' % lang

            languages.append((lang, interpreter, extension))

    # Generate all scripts

    for op in script_ops:
        generator = 'generate_%s' % op
        eval(generator)(languages, dest_dir)

    if shared_lib:
        generate_lib(script_ops, languages, dest_dir)

    if test_script:
        generate_test(languages, dest_dir)

    sys.exit(0)
