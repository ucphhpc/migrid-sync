#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# publicscriptgen - Basic script generator functions
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

# TODO: allow use of xmlrpc instead of curl from python

"""Shared helper functions for generating public MiG scripts
for the supported programming languages.
"""

import os

# ##########################
# Script helper functions #
# ##########################


def begin_function(lang, name, arguments):
    s = ''
    if lang == 'sh':
        s += '%s(' % name
        s += ') {\n'
        i = 1
        for arg in arguments:
            s += '\t%s=$%d\n' % (arg, i)
            i += 1
    elif lang == 'python':
        s += 'def %s(%s):\n' % (name, ', '.join(arguments))
    else:
        print 'Error: %s not supported!' % lang
    return s


def end_function(lang, name):
    s = ''
    if lang == 'sh':
        s += '''
}
'''
    elif lang == 'python':
        s += '\n'
    else:
        print 'Error: %s not supported!' % lang

    s += '\n'
    return s


def read_conf_function(lang):
    s = ''
    s += begin_function(lang, 'read_conf', ['conf', 'option'])
    if lang == 'sh':
        s += \
            """
        # This function reads the supplied configuration
        # file and returns the value of option in the
        # conf_value variable
        conf_value=\"\"
        while read opt val bogus; do
                if [ \"$opt\" = \"$option\" ]; then
                        conf_value=\"$val\"
                        return
                fi
        done < $conf
"""
    elif lang == 'python':
        s += \
            """
        '''Extract a value from the user conf file: format is KEY and VALUE separated by whitespace'''
        try:
            conf_file = open(conf, 'r')
            for line in conf_file:
                line = line.strip()
                # split on any whitespace and assure at least two parts
                parts = line.split() + ['', '']
                opt, val = parts[0], parts[1]
                if opt == option:
                    return val
            conf_file.close()
        except Exception:
            return ''
"""
    else:
        print 'Error: %s not supported!' % lang

    s += end_function(lang, 'usage')

    return s


def check_var_function(lang):
    s = ''
    s += begin_function(lang, 'check_var', ['name', 'var'])
    if lang == 'sh':
        s += \
            """
        if [ -z \"$var\" ]; then
           echo \"Error: Variable \'$name\' not set!\"
           echo \"Please set in configuration file or through the command line\"
           exit 1
        fi"""
    elif lang == 'python':
        s += \
            """
        if not var:
           print name + \" not set! Please set in configuration file or through the command line\"
           sys.exit(1)"""
    s += end_function(lang, 'version')

    return s


def basic_usage_options(usage_str, lang):

    # Return usage instructions for the basic script flags.
    # Additional instructions can simply be appended.

    s = ''
    if lang == 'sh':
        s += \
            """
        echo \"%s\"
        echo \"Where OPTIONS include:\"
        echo \"-c CONF\t\tread configuration from CONF instead of\"
        echo \"\t\t\tdefault (~/.mig/miguser.conf).\"
        echo \"-h\t\tdisplay this help\"
        echo \"-s MIG_SERVER\tforce use of MIG_SERVER.\"
        echo \"-v\t\tverbose mode\"
        echo \"-V\t\tdisplay version\""""\
             % usage_str
    elif lang == 'python':
        s += \
            """
        print \"%s\"
        print \"Where OPTIONS include:\"
        print \"-c CONF\t\tread configuration from CONF instead of\"
        print \"\t\tdefault (~/.mig/miguser.conf).\"
        print \"-h\t\tdisplay this help\"
        print \"-s MIG_SERVER\tforce use of MIG_SERVER.\"
        print \"-v\t\tverbose mode\"
        print \"-V\t\tdisplay version\""""\
             % usage_str
    else:
        print 'Error: %s not supported!' % lang

    return s


# ##########################
# Communication functions #
# ##########################


def ca_check_init(lang):
    s = ''
    if lang == 'sh':
        s += \
            """
        if [ -z \"$ca_cert_file\" ]; then
           ca_check='--insecure'
        else
           ca_check=\"--cacert $ca_cert_file\"
        fi
        """
    elif lang == 'python':
        s += \
            """
        if not ca_cert_file:
           ca_check = '--insecure'
        else:
           ca_check = \"--cacert %s\" % (ca_cert_file)
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def password_check_init(lang):
    s = ''
    if lang == 'sh':
        s += \
            """
        if [ -z \"$password\" ]; then
                password_check=''
        else
                password_check=\"--pass $password\"
        fi
        """
    elif lang == 'python':
        s += \
            """
        if not password:
           password_check = ''
        else:
           password_check = \"--pass %s\" % (password)
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def timeout_check_init(lang):
    s = ''
    if lang == 'sh':
        s += \
            """
        timeout=''
        if [ -n \"$max_time\" ]; then
                timeout=\"--max-time $max_time\"
        fi
        if [ -n \"$connect_timeout\" ]; then
                timeout=\"$timeout --connect-timeout $connect_timeout\"
        fi
        """
    elif lang == 'python':
        s += \
            """
        timeout = ''
        if max_time:
           timeout += \"--max-time %s\" % (max_time)
        if connect_timeout:
           timeout += \" --connect-timeout %s\" % (connect_timeout)
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def max_jobs_check_init(lang):
    s = ''
    if lang == 'sh':
        s += \
            """
        if [ -z \"$max_job_count\" ]; then
                max_jobs=''
        else
                max_jobs=\"max_jobs=$max_job_count\"
        fi
        """
    elif lang == 'python':
        s += \
            """
        if not max_job_count:
           max_jobs = ''
        else:
           max_jobs = \"max_jobs=%s\" % (max_job_count)
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def curl_perform(
    lang,
    relative_url="''",
    post_data="''",
    query="''",
    curl_cmd='curl',
    curl_flags='',
    curl_target="''",
    ):
    """Expands relative_url, query and curl_target before
    issuing curl command. Thus those variables should contain
    appropriately escaped or quoted strings.
    """

    s = ''
    if lang == 'sh':
        s += \
            """
        curl=\"%s %s\"
        target=%s
        location=%s
        post_data=%s
        query=%s
        data=""
        if [ ! -z "$post_data" ]; then
                data="--data \"$post_data\""
        fi
        $curl \\
                --location \\
                --fail \\
                --silent \\
                --show-error \\
                --cert $cert_file \\
                --key $key_file \\
                $data \\
                $ca_check \\
                $password_check \\
                $timeout \\
                $target \\
                --url \"$mig_server/$location$query\"
"""\
             % (
            curl_cmd,
            curl_flags,
            curl_target,
            relative_url,
            post_data,
            query,
            )
    elif lang == 'python':
        s += \
            """

        curl = '%s %s'
        target = %s
        location = %s
        post_data = %s
        query = %s
        data = ''
        if post_data:
            data = '--data "%%s"' %% post_data
        command = \"%%s --location --fail --silent --show-error --cert %%s --key %%s %%s %%s %%s %%s %%s --url '%%s/%%s%%s'\" %% (curl, cert_file, key_file, data, ca_check, password_check, timeout, target, mig_server, location, query)
        proc = subprocess.Popen(command, shell=True, bufsize=0,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        buffer = StringIO.StringIO(proc.communicate()[0])
        proc.stdout.close()
        out = buffer.readlines()
        exit_code = proc.returncode

        return (exit_code, out)
"""\
             % (
            curl_cmd,
            curl_flags,
            curl_target,
            relative_url,
            post_data,
            query,
            )
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


# #######################
# Main part of scripts #
# #######################


def basic_main_init(lang):
    s = '\n'

    if lang == 'sh':
        s += comment(lang, '=== Main ===')
        s += \
            """
verbose=0
conf=\"$HOME/.mig/miguser.conf\"
flags=""
server_flags=""
mig_server=""
script_path="$0"
script_name=`basename $script_path`
script_dir=`dirname $script_path`
"""
    elif lang == 'python':
        s += comment(lang, '=== Main ===')

        s += \
            """
verbose = 0
conf = os.path.expanduser(\"~/.mig/miguser.conf\")
flags = ""
mig_server = ""
server_flags = ""
script_path = sys.argv[0]
script_name = os.path.basename(script_path)
script_dir = os.path.dirname(script_path)
"""
    else:
        print 'Error: %s not supported!' % lang
    return s


def parse_options(lang, extra_opts, extra_opts_handler):
    s = ''
    if lang == 'sh':

        # Advice about parsing taken from:
        # http://www.shelldorado.com/goodcoding/cmdargs.html

        opts_str = 'c:hrs:vV'
        if extra_opts:
            opts_str += extra_opts
        s += 'while getopts %s opt; do' % opts_str
        s += \
            """
    case \"$opt\" in
          c) conf=\"$OPTARG\"
             flags="$flags -c $conf";;
          h) usage
             exit 0;;
          s) mig_server=\"$OPTARG\";;
          v) verbose=1
             server_flags="${server_flags}v"
             flags="$flags -v";;
          V) version
             exit 0;;
"""
        if extra_opts_handler:
            s += extra_opts_handler
        s += \
            """
          \?) # unknown flag
             usage
             exit 1;;
    esac
done
# Drop options
shift `expr $OPTIND - 1`

"""
    elif lang == 'python':
        opts_str = 'c:hrs:vV'
        if extra_opts:
            opts_str += extra_opts
        s += 'opt_args = "%s"' % opts_str
        s += \
            """

# preserve arg 0
arg_zero = sys.argv[0]
args = sys.argv[1:]
try:
        opts, args = getopt.getopt(args, opt_args)
except getopt.GetoptError, e:
        print \"Error: \", e.msg
        usage()
        sys.exit(1)

for (opt, val) in opts:
        if opt == \"-c\":
                conf = val
        elif opt == \"-h\":
                usage()
                sys.exit(0)
        elif opt == \"-s\":
                mig_server = val
        elif opt == \"-v\":
                verbose = True
        elif opt == \"-V\":
                version()
                sys.exit(0)
"""
        if extra_opts_handler:
            s += extra_opts_handler
        s += \
            """
        else:
                print \"Error: %s not supported!\" % (opt)

        # Drop options while preserving original sys.argv[0] 
        sys.argv = [arg_zero] + args
"""
    else:
        print 'Error: %s not supported!' % lang
    return s


def check_conf_readable(lang):
    s = ''

    if lang == 'sh':
        s += \
            """
if [ ! -r \"$conf\" ]; then
   echo \"Failed to read configuration file: $conf\"
   exit 1
fi

if [ "$verbose" -eq "1" ]; then
    echo \"using configuration in $conf\"
fi
"""
    elif lang == 'python':
        s += \
            """
if not os.path.isfile(conf):
   print \"Failed to read configuration file: %s\" % (conf)
   sys.exit(1)

if verbose:
    print \"using configuration in %s\" % (conf)
"""
    else:
        print 'Error: %s not supported!' % lang
    return s


def configure(lang):
    s = ''

    if lang == 'sh':
        s += \
            """
if [ -z "$mig_server" ]; then
   read_conf $conf 'migserver'
   mig_server=\"$conf_value\"
fi

read_conf $conf 'certfile'
cert_file=\"$conf_value\"
read_conf $conf 'keyfile'
key_file=\"$conf_value\"
read_conf $conf 'cacertfile'
ca_cert_file=\"$conf_value\"
read_conf $conf 'password'
password=\"$conf_value\"
read_conf $conf 'connect_timeout'
connect_timeout=\"$conf_value\"
read_conf $conf 'max_time'
max_time=\"$conf_value\"

check_var migserver \"$mig_server\"
check_var certfile \"$cert_file\"
check_var keyfile \"$key_file\"
"""
    elif lang == 'python':
        s += \
            """
if not mig_server:
   mig_server = read_conf(conf, 'migserver')

cert_file = read_conf(conf, 'certfile')
key_file = read_conf(conf, 'keyfile')
ca_cert_file = read_conf(conf, 'cacertfile')
password = read_conf(conf, 'password')
connect_timeout = read_conf(conf, 'connect_timeout')
max_time = read_conf(conf, 'max_time')

check_var("migserver", mig_server)
check_var("certfile", cert_file)
check_var("keyfile", key_file)
"""
    else:
        print 'Error: %s not supported!' % lang
    return s


def arg_count_check(lang, mincount, maxcount):
    s = ''
    if lang == 'sh':
        s += 'arg_count=$#\n'
        if mincount:
            s += 'min_count=%d\n' % mincount
            s += \
                """
if [ $arg_count -lt $min_count ]; then
   echo \"Too few arguments: got $arg_count, expected $min_count!\"
   usage
   exit 1
fi
"""
        if maxcount:
            s += 'max_count=%d\n' % maxcount
            s += \
                """
if [ $arg_count -gt $max_count ]; then
   echo \"Too many arguments: got $arg_count, expected $max_count!\"
   usage
   exit 1
fi
"""
    elif lang == 'python':

        s += 'arg_count = len(sys.argv) - 1\n'
        if mincount:
            s += 'min_count = %d\n' % mincount
            s += \
                """
if arg_count < min_count:
   print \"Too few arguments: got %d, expected %d!\" % (arg_count, min_count)
   usage()
   sys.exit(1)
"""
        if maxcount:
            s += 'max_count = %d\n' % maxcount
            s += \
                """
if arg_count > max_count:
   print \"Too many arguments: got %d, expected %d!\" % (arg_count, max_count)
   usage()
   sys.exit(1)
"""
    else:
        print 'Error: %s not supported!' % lang

    return s


# ######################
# Generator functions #
# ######################


def comment(lang, string):

    # Insert string as a comment in the script
    # Multi line comments (string with newlines) also work

    s = ''
    if lang == 'sh':
        s += '# %s\n' % string.replace('\n', '\n# ')
    elif lang == 'python':
        s += '# %s\n' % string.replace('\n', '\n# ')
    else:
        print 'Error: %s not supported!' % lang
    return s


def init_script(
    name,
    lang,
    interpreter,
    interpreter_flags='',
    ):

    s = '#!%s %s\n' % (interpreter, interpreter_flags)
    if lang == 'sh':
        pass
    elif lang == 'python':
        s += comment(lang, '-*- coding: utf-8 -*-')
    header = \
        """
mig%s - a part of the MiG scripts
Copyright (C) 2004-2009  MiG Core Developers lead by Brian Vinter

This file is part of MiG.

MiG is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

MiG is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""\
         % name
    intro = \
        """
This MiG %s script was autogenerated by the MiG User Script Generator !!!
Any changes should be made in the generator and not here !!!
"""\
         % lang
    s += comment(lang, header)
    s += comment(lang, intro)
    s += '\n'

    if lang == 'sh':
        pass
    elif lang == 'python':
        s += \
            """import sys
import os
import getopt
import subprocess
import StringIO

"""
    else:
        print 'Error: %s not supported!' % lang

    return s


def write_script(contents, filename, mode=0755):
    try:
        script_file = open(filename, 'w')
        script_file.write(contents)
        script_file.close()
        os.chmod(filename, mode)
    except Exception, exc:
        print 'Error: failed to write %s: %s' % (filename, exc)
        return False

    return True


def verbose(verbose_mode, txt):
    if verbose_mode:
        print txt
