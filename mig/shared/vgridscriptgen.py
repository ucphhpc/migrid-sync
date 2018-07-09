#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridscriptgen - vgrid and resource script generator backend
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Generate MiG vgrid scripts for the speficied programming languages. Called
without arguments the generator creates scripts for all supported languages. If
one or more languages are supplied as arguments, only those languages will be
generated.
"""

# Generator version (automagically updated by svn)

__version__ = '$Revision$'

import os
import sys
import getopt

from shared.base import get_xgi_bin
from shared.conf import get_configuration_object
from shared.publicscriptgen import *

# ######################################
# Script generator specific functions #
# ######################################
# Generator usage


def usage():
    """Use help"""
    print 'Usage: vgridscriptgen.py OPTIONS [LANGUAGE ... ]'
    print 'Where OPTIONS include:'
    print ' -c CURL_CMD\t: Use curl from CURL_CMD'
    print ' -h\t\t: Print this help'
    print ' -p PYTHON_CMD\t: Use PYTHON_CMD as python interpreter'
    print ' -s SH_CMD\t: Use SH_CMD as sh interpreter'
    print ' -v\t\t: Verbose output'
    print ' -V\t\t: Show version'


def version():
    """Version info"""
    print 'MiG VGrid Script Generator: %s' % __version__


def version_function(lang):
    """Version helper"""
    s = ''
    s += begin_function(lang, 'version', [], 'Show version details')
    if lang == 'sh':
        s += '    echo "MiG VGrid Scripts: %s"\n' % __version__
    elif lang == 'python':
        s += '    print "MiG VGrid Scripts: %s"\n' % __version__
    s += end_function(lang, 'version')

    return s


# ##########################
# Script helper functions #
# ##########################


def vgrid_single_argument_usage_function(
    lang,
    extension,
    op,
    first_arg,
):
    """Usage functions for single argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = 'Usage: %s%s.%s [OPTIONS] %s' % (mig_prefix, op,
                                                 extension, first_arg)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def vgrid_two_arguments_usage_function(
    lang,
    extension,
    op,
    first_arg,
    second_arg,
):
    """Usage functions for two argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = 'Usage: %s%s.%s [OPTIONS] %s %s' % (mig_prefix, op,
                                                    extension, first_arg, second_arg)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


def vgrid_ten_arguments_usage_function(
    lang,
    extension,
    op,
    first_arg,
    second_arg,
    third_arg,
    fourth_arg,
    fifth_arg,
    sixth_arg,
    seventh_arg,
    eighth_arg,
    ninth_arg,
    tenth_arg,
):
    """Usage functions for ten argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = 'Usage: %s%s.%s [OPTIONS] %s %s %s %s %s %s %s %s %s %s' % \
                (mig_prefix, op, extension, first_arg, second_arg, third_arg,
                 fourth_arg, fifth_arg, sixth_arg, seventh_arg, eighth_arg, ninth_arg, tenth_arg)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')

    return s


# ##########################
# Communication functions #
# ##########################


def vgrid_single_argument_function(
    configuration,
    lang,
    curl_cmd,
    command,
    first_arg,
    curl_flags='',
):
    """Core function for single argument scripts"""
    relative_url = '"%s/%s.py"' % (get_xgi_bin(configuration), command)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args"'
        urlenc_data = '("%s=$%s")' % (first_arg, first_arg)
    elif lang == 'python':
        post_data = "'%s' % default_args"
        urlenc_data = "['%s=' + %s]" % (first_arg, first_arg)
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'submit_command', [first_arg],
                        'Call corresponding server operation')
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
    s += end_function(lang, 'submit_command')
    return s


def vgrid_single_argument_upload_function(
    configuration,
    lang,
    curl_cmd,
    command,
    content_type,
    first_arg,
    curl_flags='',
):
    """Core function for single argument upload scripts"""
    relative_url = '""'
    query = '""'
    urlenc_data = '""'
    post_data = '""'
    if lang == 'sh':
        curl_target = '"--header Content-Type:%s --upload-file $%s"' % \
                      (content_type, first_arg)
    elif lang == 'python':
        curl_target = '"--header Content-Type:%s --upload-file " + %s' % \
                      (content_type, first_arg)
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'submit_command', [first_arg],
                        'Call corresponding server operation')
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
    s += end_function(lang, 'submit_command')
    return s


def vgrid_two_arguments_function(
    configuration,
    lang,
    curl_cmd,
    command,
    first_arg,
    second_arg,
    curl_flags='',
):
    """Core function for two argument scripts"""
    relative_url = '"%s/%s.py"' % (get_xgi_bin(configuration), command)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args"'
        urlenc_data = '("%s=$%s" "%s=$%s")' % (first_arg, first_arg,
                                               second_arg, second_arg)
    elif lang == 'python':
        post_data = "'%s' % default_args"
        urlenc_data = "['%s=' + %s, '%s=' + %s]" % (first_arg, first_arg,
                                                    second_arg, second_arg)
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'submit_command', [first_arg, second_arg],
                        'Call corresponding server operation')
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
    s += end_function(lang, 'submit_command')
    return s


def vgrid_ten_arguments_function(
    configuration,
    lang,
    curl_cmd,
    command,
    first_arg,
    second_arg,
    third_arg,
    fourth_arg,
    fifth_arg,
    sixth_arg,
    seventh_arg,
    eighth_arg,
    ninth_arg,
    tenth_arg,
    curl_flags='',
):
    """Core function for ten argument scripts"""
    relative_url = '"%s/%s.py"' % (get_xgi_bin(configuration), command)
    query = '""'
    if lang == 'sh':
        post_data = '"$default_args"'
        urlenc_data = '("%s=$%s" "%s=$%s" "%s=$%s" "%s=$%s" "%s=$%s" ' % \
                      (first_arg, first_arg, second_arg, second_arg, third_arg,
                       third_arg, fourth_arg, fourth_arg, fifth_arg, fifth_arg)
        urlenc_data += '"%s=$%s" "%s=$%s" "%s=$%s" "%s=$%s" "%s=$%s")' % \
                       (sixth_arg, sixth_arg, seventh_arg, seventh_arg,
                        eighth_arg, eighth_arg, ninth_arg, ninth_arg,
                        tenth_arg, tenth_arg)
    elif lang == 'python':
        post_data = "'%s' % default_args"
        urlenc_data = "['%s=' + %s, '%s=' + %s, '%s=' + %s, '%s=' + %s, " % \
                      (first_arg, first_arg, second_arg, second_arg, third_arg,
                       third_arg, fourth_arg, fourth_arg)
        urlenc_data += "'%s=' + %s, '%s=' + %s, '%s=' + %s, '%s=' + %s, " % \
                       (fifth_arg, fifth_arg, sixth_arg, sixth_arg,
                        seventh_arg, seventh_arg, eighth_arg, eighth_arg)
        urlenc_data += "'%s=' + %s, '%s=' + %s]" % (ninth_arg, ninth_arg,
                                                    tenth_arg, tenth_arg)
    else:
        print 'Error: %s not supported!' % lang
        return ''

    s = ''
    s += begin_function(lang, 'submit_command', [first_arg, second_arg,
                                                 third_arg, fourth_arg,
                                                 fifth_arg, sixth_arg,
                                                 seventh_arg, eighth_arg,
                                                 ninth_arg, tenth_arg],
                        'Call corresponding server operation')
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
    s += end_function(lang, 'submit_command')
    return s


# #######################
# Main part of scripts #
# #######################


def vgrid_single_argument_main(lang):
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

first_arg=\"$1\"

submit_command \"$first_arg\"
"""
    elif lang == 'python':
        s += """
first_arg = sys.argv[1]

(status, out) = submit_command(first_arg)
print ''.join(out),
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def vgrid_two_arguments_main(lang):
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

first_arg=\"$1\"
second_arg=\"$2\"

submit_command \"$first_arg\" \"$second_arg\"
"""
    elif lang == 'python':
        s += """
first_arg = sys.argv[1]
second_arg = sys.argv[2]

(status, out) = submit_command(first_arg, second_arg)
print ''.join(out),
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def vgrid_ten_arguments_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 10, 10)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """

first_arg=\"${1}\"
second_arg=\"${2}\"
third_arg=\"${3}\"
fourth_arg=\"${4}\"
fifth_arg=\"${5}\"
sixth_arg=\"${6}\"
seventh_arg=\"${7}\"
eighth_arg=\"${8}\"
ninth_arg=\"${9}\"
tenth_arg=\"${10}\"

submit_command \"$first_arg\" \"$second_arg\" \"$third_arg\" \"$fourth_arg\" \"$fifth_arg\" \"$sixth_arg\" \"$seventh_arg\" \"$eighth_arg\" \"$ninth_arg\" \"$tenth_arg\"
"""
    elif lang == 'python':
        s += """
first_arg = sys.argv[1]
second_arg = sys.argv[2]
third_arg = sys.argv[3]
fourth_arg = sys.argv[4]
fifth_arg = sys.argv[5]
sixth_arg = sys.argv[6]
seventh_arg = sys.argv[7]
eighth_arg = sys.argv[8]
ninth_arg = sys.argv[9]
tenth_arg = sys.argv[10]

(status, out) = submit_command(first_arg, second_arg, third_arg, fourth_arg,
                               fifth_arg, sixth_arg, seventh_arg, eighth_arg,
                               ninth_arg, tenth_arg)
print ''.join(out),
sys.exit(status)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


# ######################
# Generator functions #
# ######################


def generate_single_argument(
    configuration,
    op,
    first_arg,
    scripts_languages,
    dest_dir='.',
):
    """Generator for single argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)

        script += vgrid_single_argument_usage_function(lang, extension,
                                                       op, first_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_single_argument_function(configuration, lang, curl_cmd,
                                                 op, first_arg, curl_flags='')
        script += vgrid_single_argument_main(lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_single_argument_upload(
    configuration,
    op,
    content_type,
    first_arg,
    scripts_languages,
    dest_dir='.',
):
    """Generator for single argument upload scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)

        script += vgrid_single_argument_usage_function(lang, extension,
                                                       op, first_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_single_argument_upload_function(
            configuration,
            lang,
            curl_cmd,
            op,
            content_type,
            first_arg,
            curl_flags='',
        )
        script += vgrid_single_argument_main(lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_two_arguments(
    configuration,
    op,
    first_arg,
    second_arg,
    scripts_languages,
    dest_dir='.',
):
    """Generator for two argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)

        script += vgrid_two_arguments_usage_function(lang, extension,
                                                     op, first_arg, second_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_two_arguments_function(
            configuration,
            lang,
            curl_cmd,
            op,
            first_arg,
            second_arg,
            curl_flags='',
        )
        script += vgrid_two_arguments_main(lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_ten_arguments(
    configuration,
    op,
    first_arg,
    second_arg,
    third_arg,
    fourth_arg,
    fifth_arg,
    sixth_arg,
    seventh_arg,
    eighth_arg,
    ninth_arg,
    tenth_arg,
    scripts_languages,
    dest_dir='.',
):
    """Generator for seven argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)

        script += vgrid_ten_arguments_usage_function(
            lang, extension, op, first_arg, second_arg, third_arg, fourth_arg,
            fifth_arg, sixth_arg, seventh_arg, eighth_arg, ninth_arg, tenth_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_ten_arguments_function(
            configuration,
            lang,
            curl_cmd,
            op,
            first_arg,
            second_arg,
            third_arg,
            fourth_arg,
            fifth_arg,
            sixth_arg,
            seventh_arg,
            eighth_arg,
            ninth_arg,
            tenth_arg,
            curl_flags='',
        )
        script += vgrid_ten_arguments_main(lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


# ###########
# ## Main ###
# ###########

# Defaults

verbose_mode = False
test_script = False
include_license = True

# Supported MiG operations (don't add 'test' as it is optional)

script_ops_ten_args = []

# VGrid functions

script_ops_ten_args.append(['addvgridtrigger', 'rule_id', 'vgrid_name',
                            'path', 'match_dirs', 'match_recursive',
                            'changes', 'action', 'arguments',
                            'rate_limit', 'settle_time'])

script_ops_two_args = []

# VGrid functions

script_ops_two_args.append(['addvgridmember', 'cert_id', 'vgrid_name'])
script_ops_two_args.append(['addvgridowner', 'cert_id', 'vgrid_name'])
script_ops_two_args.append(['addvgridres', 'unique_resource_name',
                            'vgrid_name'])
script_ops_two_args.append(['rmvgridmember', 'cert_id', 'vgrid_name'])
script_ops_two_args.append(['rmvgridowner', 'cert_id', 'vgrid_name'])
script_ops_two_args.append(['rmvgridres', 'unique_resource_name',
                            'vgrid_name'])
script_ops_two_args.append(['rmvgridtrigger', 'rule_id', 'vgrid_name'])


# Res functions

script_ops_two_args.append(['addresowner', 'unique_resource_name',
                            'cert_id'])
script_ops_two_args.append(['rmresowner', 'unique_resource_name',
                            'cert_id'])

script_ops_two_args.append(['startexe', 'unique_resource_name',
                            'exe_name'])
script_ops_two_args.append(['statusexe', 'unique_resource_name',
                            'exe_name'])
script_ops_two_args.append(['stopexe', 'unique_resource_name',
                            'exe_name'])
script_ops_two_args.append(['restartexe', 'unique_resource_name',
                            'exe_name'])
script_ops_two_args.append(['cleanexe', 'unique_resource_name', 'exe_name'])

script_ops_two_args.append(['startallexes', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['statusallexes', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['stopallexes', 'unique_resource_name', 'all'
                            ])
script_ops_two_args.append(['restartallexes', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['cleanallexes', 'unique_resource_name',
                            'all'])

script_ops_two_args.append(['startstore', 'unique_resource_name',
                            'store_name'])
script_ops_two_args.append(['statusstore', 'unique_resource_name',
                            'store_name'])
script_ops_two_args.append(['stopstore', 'unique_resource_name',
                            'store_name'])
script_ops_two_args.append(['restartstore', 'unique_resource_name',
                            'store_name'])
script_ops_two_args.append(
    ['cleanstore', 'unique_resource_name', 'store_name'])

script_ops_two_args.append(['startallstores', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['statusallstores', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['stopallstores', 'unique_resource_name', 'all'
                            ])
script_ops_two_args.append(['restartallstores', 'unique_resource_name',
                            'all'])
script_ops_two_args.append(['cleanallstores', 'unique_resource_name',
                            'all'])

script_ops_single_arg = []

# VGrid functions

script_ops_single_arg.append(['createvgrid', 'vgrid_name'])
script_ops_single_arg.append(['lsvgridmembers', 'vgrid_name'])
script_ops_single_arg.append(['lsvgridowners', 'vgrid_name'])
script_ops_single_arg.append(['lsvgridres', 'vgrid_name'])
script_ops_single_arg.append(['lsvgridtriggers', 'vgrid_name'])

# Res functions

script_ops_single_arg.append(['lsresowners', 'unique_resource_name'])

script_ops_single_arg.append(['startfe', 'unique_resource_name'])
script_ops_single_arg.append(['statusfe', 'unique_resource_name'])
script_ops_single_arg.append(['stopfe', 'unique_resource_name'])
script_ops_single_arg.append(['cleanfe', 'unique_resource_name'])

# action_allexes scripts obsolete, use actionexe all=true instead
# script_ops_single_arg.append(["startallexes", "unique_resource_name"])
# script_ops_single_arg.append(["statusallexes", "unique_resource_name"])
# script_ops_single_arg.append(["stopallexes", "unique_resource_name"])
# script_ops_single_arg.append(["restartallexes", "unique_resource_name"])
# script_ops_single_arg.append(["resetallexes", "unique_resource_name"])

script_ops_single_upload_arg = []
script_ops_single_upload_arg.append(['submitresconf',
                                     'text/resourceconf',
                                     'configuration_file'])
script_ops_single_upload_arg.append(['submitnewre',
                                     'text/runtimeenvconf',
                                     'configuration_file'])

# Script prefix for all user scripts

mig_prefix = 'mig'

# Default commands:

sh_lang = 'sh'

# Disable globbing with the '-f' flag

sh_cmd = '/bin/sh -f'
sh_ext = 'sh'
python_lang = 'python'
python_cmd = '/usr/bin/python'
python_ext = 'py'
# curl_cmd must be generic for cross platform support
curl_cmd = 'curl'
dest_dir = '.'

# Only run interactive commands if called directly as executable

if __name__ == '__main__':
    opts_str = 'c:d:hp:s:tvV'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opts_str)
    except getopt.GetoptError, goe:
        print 'Error: %s' % goe
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            curl_cmd = val
        elif opt == '-d':
            dest_dir = val
        elif opt == '-i':
            include_license = False
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

    configuration = get_configuration_object()

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

    for op in script_ops_single_arg:
        generate_single_argument(configuration, op[0], op[1], languages,
                                 dest_dir)

    for op in script_ops_single_upload_arg:
        generate_single_argument_upload(configuration, op[0], op[1], op[2],
                                        languages, dest_dir)

    for op in script_ops_two_args:
        generate_two_arguments(configuration, op[0], op[1], op[2], languages,
                               dest_dir)

    for op in script_ops_ten_args:
        generate_ten_arguments(configuration, op[0], op[1], op[2], op[3],
                               op[4], op[5], op[6], op[7], op[8], op[9],
                               op[10], languages, dest_dir)

    # if test_script:
    #    generate_test(languages)

    if include_license:
        write_license(configuration, dest_dir)

    sys.exit(0)
