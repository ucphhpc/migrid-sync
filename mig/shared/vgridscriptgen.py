#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridscriptgen - vgrid and resource script generator backend
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import getopt

from mig.shared.base import get_xgi_bin
from mig.shared.conf import get_configuration_object
from mig.shared.publicscriptgen import *

# Generator version (automagically updated by svn)

vgridscript_version = "$Revision$"
__version__ = 'Scripts %s / Core %s' % (vgridscript_version,
                                        publicscript_version)


# ######################################
# Script generator specific functions #
# ######################################

# Generator usage


def usage():
    """Usage help"""
    print('Usage: vgridscriptgen.py OPTIONS [LANGUAGE ... ]')
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


def version(short_name="MiG", flavor="VGrid"):
    """Version info"""
    print('%s %s Script Generator: %s' % (short_name, flavor, __version__))


def version_function(lang):
    """Version helper for generated scripts"""
    return shared_version_function(lang, flavor="VGrid", version=__version__)


# ##########################
# Script helper functions #
# ##########################

def lookup_vgridscript_function(op, helper):
    """Simply looks up op helper in globals and returns matching function"""

    return globals()['%s_%s' % (op, helper)]


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


def vgrid_any_arguments_usage_function(lang, extension, op, *args):
    """Usage function for scripts with ANY number of arguments"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = 'Usage: %s%s.%s [OPTIONS]' % (mig_prefix, op, extension)
    if args:
        usage_str += ' ' + ' '.join(args)
    s = ''
    s += begin_function(lang, 'usage', [], 'Usage help for %s' % op)
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, 'usage')
    return s


# ##########################
# Communication functions #
# ##########################

def test_function(configuration, lang, curl_cmd, curl_flags=''):
    """Test one or more of the vgrid scripts"""

    # TODO: pass original -c and -s options on to tested scripts

    script_op_names = [i[0] for i in script_ops]

    s = ''
    s += begin_function(lang, 'test_op', ['op', 'test_prefix'],
                        'Execute simple function tests')
    if lang == 'sh':
        s += """
    valid_ops=(%(valid_ops)s)
    mig_prefix='%(mig_prefix)s'
    script_ext='sh'
""" % {'valid_ops': ' '.join(script_op_names), 'mig_prefix': mig_prefix}
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
    vgrid_test=\"${test_prefix}-vgrid\"
    res_test=\"${test_prefix}-res\"

    echo \"=== running $op test(s) ===\"
    cmd=\"${path_prefix}/${mig_prefix}${op}.${script_ext}\"
    createvgrid_cmd=\"${path_prefix}/${mig_prefix}createvgrid.${script_ext}\"
    removevgrid_cmd=\"${path_prefix}/${mig_prefix}removevgrid.${script_ext}\"
    lsvgridowners_cmd=\"${path_prefix}/${mig_prefix}lsvgridowners.${script_ext}\"
    lsvgridmembers_cmd=\"${path_prefix}/${mig_prefix}lsvgridmembers.${script_ext}\"
    lsvgridtriggers_cmd=\"${path_prefix}/${mig_prefix}lsvgridtriggers.${script_ext}\"
    lsresowners_cmd=\"${path_prefix}/${mig_prefix}lsresowners.${script_ext}\"
    declare -a cmd_args
    declare -a verify_cmds
    # Default to no action
    pre_cmds[1]=''
    cmd_args[1]=''
    verify_cmds[1]=''
    post_cmds[1]=''
    case $op in
        'createvgrid')
            # pre_cmds[1]=\"${removevgrid_cmd} 'DUMMY_VGRID'\"
            cmd_args[1]=\"'DUMMY_VGRID'\"
            post_cmds[1]=\"${removevgrid_cmd} 'DUMMY_VGRID'\"
            ;;
        'lsresowners')
            cmd_args[1]=\"'${res_test}'\"
            ;;
        'lsvgridowners' | 'lsvgridmembers' | 'lsvgridtriggers')
            cmd_args[1]=\"'${vgrid_test}'\"
            ;;
        'removevgrid')
            # TODO: create and remove real vgrid?
            # pre_cmds[1]=\"${createvgrid} 'DUMMY_VGRID'\"
            cmd_args[1]='DUMMY_VGRID'
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
""" % {'valid_ops': script_op_names, 'mig_prefix': mig_prefix}
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
    vgrid_test = test_prefix + '-vgrid'
    res_test = test_prefix + '-res'

    createvgrid_cmd = os.path.join(
        path_prefix, mig_prefix + 'createvgrid.' + script_ext)
    removevgrid_cmd = os.path.join(
        path_prefix, mig_prefix + 'removevgrid.' + script_ext)
    lsvgridowners_cmd = os.path.join(
        path_prefix, mig_prefix + 'lsvgridowners.' + script_ext)
    lsvgridmembers_cmd = os.path.join(
        path_prefix, mig_prefix + 'lsvgridmembers.' + script_ext)
    lsvgridtriggers_cmd = os.path.join(
        path_prefix, mig_prefix + 'lsvgridtriggers.' + script_ext)
    lsresowners_cmd = os.path.join(
        path_prefix, mig_prefix + 'lsresowners.' + script_ext)
    if op == 'createvgrid':
            # pre_cmds.append([removevgrid, 'DUMMY_VGRID'])
            cmd_args.append(['DUMMY_VGRID'])
            post_cmds.append([removevgrid, 'DUMMY_VGRID'])
    elif op in ('lsresowners', ):
            cmd_args.append([res_test])
    elif op in ('lsvgridowners', 'lsvgridmembers', 'lsvgridtriggers'):
            cmd_args.append([vgrid_test])
    elif op == 'removevgrid':
            # TODO: create and remove real vgrid?
            # pre_cmds.append([submit_cmd, mrsl_helper])
            cmd_args.append(['DUMMY_JOB_ID'])
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


def vgrid_any_arguments_function(
    configuration,
    lang,
    curl_cmd,
    command,
    *args,
    **kwargs


):
    """Core function for scripts with any number of arguments"""
    relative_url = '"%s/%s.py"' % (get_xgi_bin(configuration), command)
    query = '""'
    curl_flags = kwargs.get('curl_flags', '')
    if lang == 'sh':
        post_data = '"$default_args"'
        urlenc_data = '(%s)' % ' '.join(['"%s=$%s"' % (i, i) for i in args])
    elif lang == 'python':
        post_data = "'%s' % default_args"
        urlenc_data = "[%s]" % ', '.join(["'%s=' + %s" % (i, i) for i in args])
    else:
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, command, args,
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
    s += end_function(lang, command)
    return s


# TODO: remove this legacy function once upload version is ported to any arg

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
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, command, [first_arg],
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
    s += end_function(lang, command)
    return s


# TODO: reimplement with any arg function above

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
        print('Error: %s not supported!' % lang)
        return ''

    s = ''
    s += begin_function(lang, command, [first_arg],
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
    s += end_function(lang, command)
    return s


# #######################
# Main part of scripts #
# #######################


def test_main(lang):
    """Generate main part of corresponding scripts.
    lang specifies which script language to generate in.
    """

    script_op_names = [i[0] for i in script_ops]

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
if [ $# -eq 0 ]; then
    op_list=(%s)
else
    op_list=(\"$@\")
fi

for op in \"${op_list[@]}\"; do
    test_op \"$op\" \"${test_prefix}\"
done
""" % ' '.join(script_op_names)
    elif lang == 'python':
        s += """
if sys.argv[1:]:
    op_list = sys.argv[1:]
else:
    op_list = %s

for op in op_list:
    test_op(op, test_prefix)
""" % script_op_names
    else:
        print('Error: %s not supported!' % lang)

    return s


def vgrid_any_arguments_main(lang, command, *args):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """

    s = ''
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, len(args), len(args))
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':
        s += """
%s %s
""" % (command, ' '.join(['\"$%d\"' % i for i in range(1, len(args)+1)]))
    elif lang == 'python':
        s += """
(status, out) = %s(%s)
print ''.join(out),
sys.exit(status)
""" % (command, ', '.join('sys.argv[%d]' % i for i in range(1, len(args)+1)))
    else:
        print('Error: %s not supported!' % lang)

    return s


# ######################
# Generator functions #
# ######################


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
        script += lookup_vgridscript_function(op, 'usage_function')(lang,
                                                                    extension)
        script += check_var_function(lang)
        script += read_conf_function(lang)

        # TODO: any helpers needed here for add and clean up?
        for helper_op in ():
            script += lookup_vgridscript_function(helper_op, 'function')(
                configuration, lang, curl_cmd)
        script += lookup_vgridscript_function(op, 'function')(configuration,
                                                              lang, curl_cmd)
        script += lookup_vgridscript_function(op, 'main')(lang)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_lib(configuration, scripts_languages, script_ops, dest_dir='.'):
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
        # script += expand_function(configuration, lang, curl_cmd)
        for lib_op_list in script_ops:
            script += vgrid_any_arguments_function(configuration, lang,
                                                   curl_cmd, *lib_op_list,
                                                   curl_flags='')
        script += basic_main_init(lang)
        script += check_conf_readable(lang)
        script += configure(lang)

        write_script(script, dest_dir + os.sep + script_name, mode=0o644)

    return True


def generate_any_arguments(
    configuration,
    scripts_languages,
    op,
    *args,
    **kwargs


):
    """Generator for zero argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''
    arg_list = args
    dest_dir = kwargs.get('dest_dir', '.')

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += vgrid_any_arguments_usage_function(lang, extension, op,
                                                     *arg_list)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_any_arguments_function(configuration, lang, curl_cmd,
                                               op, *arg_list, curl_flags='')
        script += vgrid_any_arguments_main(lang, op, *arg_list)

        write_script(script, dest_dir + os.sep + script_name)

    return True


# TODO: eliminate these two after switch to 'any' version

def generate_single_argument(
    configuration,
    scripts_languages,
    op,
    first_arg,
    dest_dir='.',
):
    """Generator for single argument scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''
    arg_list = [first_arg]

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += vgrid_any_arguments_usage_function(lang, extension, op,
                                                     *arg_list)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_any_arguments_function(configuration, lang, curl_cmd,
                                               op, *arg_list, curl_flags='')
        script += vgrid_any_arguments_main(lang, op, *arg_list)

        write_script(script, dest_dir + os.sep + script_name)

    return True


def generate_single_argument_upload(
    configuration,
    scripts_languages,
    op,
    content_type,
    first_arg,
    dest_dir='.',
):
    """Generator for single argument upload scripts"""

    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")

    curl_flags = ''
    arg_list = [first_arg]

    # Generate op script for each of the languages in scripts_languages

    for (lang, interpreter, extension) in scripts_languages:
        verbose(verbose_mode, 'Generating %s script for %s' % (op,
                                                               lang))
        script_name = '%s%s.%s' % (mig_prefix, op, extension)

        script = ''
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        script += vgrid_any_arguments_usage_function(lang, extension, op,
                                                     *arg_list)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        # TODO: reimplement with any helper and custom upload keyword arg
        script += vgrid_single_argument_upload_function(
            configuration,
            lang,
            curl_cmd,
            op,
            content_type,
            first_arg,
            curl_flags='',
        )
        script += vgrid_any_arguments_main(lang, op, *arg_list)

        write_script(script, dest_dir + os.sep + script_name)

    return True


# Defaults to extend the values from publicscriptgen

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
script_ops_two_args.append(['lsvgrids', 'vgrid_name', 'allowed_only'])


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

script_ops_single_upload_arg = []
script_ops_single_upload_arg.append(['submitresconf',
                                     'text/resourceconf',
                                     'configuration_file'])
script_ops_single_upload_arg.append(['submitnewre',
                                     'text/runtimeenvconf',
                                     'configuration_file'])


# All supported MiG operations
# TODO: eliminate or properly handle upload version here
# script_ops = script_ops_single_arg + script_ops_single_upload_arg + \
#    script_ops_two_args + script_ops_ten_args
script_ops = script_ops_single_arg + script_ops_two_args + script_ops_ten_args

# ###########
# ## Main ###
# ###########

# Only run interactive commands if called directly as executable

if __name__ == '__main__':
    opts_str = 'c:d:hp:s:tvV'
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

    for op in script_login_session:
        lookup_publicscript_function('generate', op)(configuration, languages,
                                                     dest_dir)

    for op in script_ops_single_arg:
        generate_any_arguments(configuration, languages, *op,
                               dest_dir=dest_dir)

    for op in script_ops_single_upload_arg:
        # TODO: port to use 'any' version
        generate_single_argument_upload(configuration, languages, *op,
                                        dest_dir=dest_dir)

    for op in script_ops_two_args:
        generate_any_arguments(configuration, languages, *op,
                               dest_dir=dest_dir)

    for op in script_ops_ten_args:
        generate_any_arguments(configuration, languages, *op,
                               dest_dir=dest_dir)

    if shared_lib:
        generate_lib(configuration, languages, script_ops, dest_dir)

    if test_script:
        generate_test(configuration, languages, dest_dir)

    if include_license:
        write_license(configuration, dest_dir)

    sys.exit(0)
