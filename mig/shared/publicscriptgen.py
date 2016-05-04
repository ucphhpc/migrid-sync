#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# publicscriptgen - Basic script generator functions
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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


# Generator version (automagically updated by svn)

__version__ = '$Revision$'

# ##########################
# Script helper functions #
# ##########################

def doc_string(lang, string, indent=0):
    """Insert doc string or comment in the script.
    Multi line comments (string with newlines) also work.
    """

    s = indent * ' '
    
    if lang == 'sh':
        s += '# %s\n' % string.replace('\n', '\n' + indent * ' ' + '# ')
    elif lang == 'python':
        s += '"""%s"""\n' % string.replace('\n', '\n' + indent * ' ')
    else:
        print 'Error: %s not supported!' % lang
    return s


def begin_function(lang, name, arguments, doc=''):
    """Insert function header. Please note that arguments named X_list are
    automatically treated specially to support array arguments in shell script
    version where it requires explicit handling.
    """
    s = ''
    if lang == 'sh':
        s += '%s(' % name
        s += ') {\n'
    elif lang == 'python':
        s += 'def %s(%s):\n' % (name, ', '.join(arguments))
    else:
        print 'Error: %s not supported!' % lang

    if doc:
        s += doc_string(lang, doc, 4)

    # sh needs variable extraction from stack and list args are cumbersome

    if lang == 'sh':
        i = 1
        for arg in arguments:
            if arg.endswith('_list'):
                remain = len(arguments) - i
                s += '''    local extract_count=$((${#@}-%d))
    local %s=${@:1:$extract_count}
    shift $extract_count
''' % (remain, arg)
            else:
                s += '''    local %s=$1
    shift
''' % arg
            i += 1

    return s


def end_function(lang, name):
    """Insert function footer"""
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
    s += begin_function(lang, 'read_conf', ['conf', 'option'],
                        '''Extract a value from the user conf file: format is KEY and VALUE
separated by whitespace''')
    if lang == 'sh':
        s += """
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
        s += """
    try:
        conf_file = open(conf, 'r')
        for line in conf_file:
            line = line.strip()
            # split on any whitespace and assure at least two parts
            parts = line.split(' ', 1) + ['', '']
            opt, val = parts[0], parts[1]
            if opt == option:
                return val
        conf_file.close()
    except Exception:
        return ''
"""
    else:
        print 'Error: %s not supported!' % lang

    s += end_function(lang, 'read_conf')

    return s


def check_var_function(lang):
    s = ''
    s += begin_function(lang, 'check_var', ['name', 'var'],
                        'Check that conf variable, name, is set')
    if lang == 'sh':
        s += """
    if [ -z \"$var\" ]; then
        echo \"Error: Variable \'$name\' not set!\"
        echo \"Please set in configuration file or through the command line\"
        exit 1
    fi"""
    elif lang == 'python':
        s += """
    if not var:
        print \"Error: Variable %s not set!\" % name
        print \"Please set in configuration file or through the command line\"
        sys.exit(1)"""
    s += end_function(lang, 'check_var')

    return s


def pack_list(lang, list_name, var_name):
    """Helper to generate list/array of formatted arguments. Takes all argv
    elements, so manual pruning may be necessary afterwards.
    """
    s = ''
    fill = {'list_name': list_name, 'var_name': var_name}
    if lang == 'sh':
        s += """
# Build the %(var_name)s array used directly:
# '%(var_name)s=$1' ... '%(var_name)s=$N'
orig_args=(\"$@\")
declare -a %(list_name)s
while [ \"$#\" -gt \"0\" ]; do
    %(list_name)s+=(\"%(var_name)s=$1\")
    shift
done
""" % fill
    elif lang == 'python':
        s += """
# Build the %(var_name)s list used directly:
# ['%(var_name)s=$1',..., '%(var_name)s=$N']
%(list_name)s = [\"%(var_name)s=%%s\" %% i for i in sys.argv[1:]]
""" % fill
    else:
        print 'Error: %s not supported!' % lang

    return s

        
def basic_usage_options(usage_str, lang):

    # Return usage instructions for the basic script flags.
    # Additional instructions can simply be appended.

    s = ''
    if lang == 'sh':
        s += """
    echo \"%s\"
    echo \"Where OPTIONS include:\"
    echo \"-A AUTHTYPE\tuse e.g. sharelink auth rather than user cert\"
    echo \"-c CONF\tread configuration from CONF instead of\"
    echo \"\t\tdefault (~/.mig/miguser.conf).\"
    echo \"-h\t\tdisplay this help\"
    echo \"-s MIG_SERVER\tforce use of MIG_SERVER.\"
    echo \"-v\t\tverbose mode\"
    echo \"-V\t\tdisplay version\""""\
             % usage_str
    elif lang == 'python':
        s += """
    print \"%s\"
    print \"Where OPTIONS include:\"
    print \"-A AUTHTYPE\tuse e.g. sharelink auth rather than user cert\"
    print \"-c CONF\tread configuration from CONF instead of\"
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


def auth_check_init(lang):
    """Init all auth variables"""
    s = ''
    if lang == 'sh':
        s += """
    declare -a ca_check
    if [ -z \"$ca_cert_file\" ]; then
        ca_check=(\"--insecure\")
    elif [ \"$ca_cert_file\" == 'AUTO' ]; then
        ca_check=(\"\")
    else
        ca_check=(\"--cacert $ca_cert_file\")
    fi
    declare -a auth_check
    if [ \"$auth_redir\" == \"cert_redirect\" ]; then
        auth_check=(\"--cert $cert_file\" \"--key $key_file\")
        put_arg=\"CERTPUT\"
        auth_data=\"\"
    else
        auth_check=(\"\")
        put_arg=\"SHAREPUT\"
        auth_data=\"share_id=${auth_redir/share_redirect\//}\"
    fi
    if [ -z \"$password\" ]; then
        password_check=("")
    else
        password_check=(\"--pass $password\")
    fi
    """
    elif lang == 'python':
        s += """
    if not ca_cert_file:
        ca_check = ['--insecure']
    elif ca_cert_file == 'AUTO':
        ca_check = []
    else:
        ca_check = [\"--cacert\", ca_cert_file]
    if auth_redir == \"cert_redirect\":
        auth_check = [\"--cert\", cert_file, \"--key\", key_file]
        put_arg = \"CERTPUT\"
        auth_data = \"\"
    else:
        auth_check = []
        put_arg = \"SHAREPUT\"
        auth_data = \"share_id=%s\" % auth_redir.replace(\"share_redirect/\",
                                                         \"\")
    if not password:
        password_check = []
    else:
        password_check = [\"--pass\", password]
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s

def timeout_check_init(lang):
    """Init timeout_check"""
    s = ''
    if lang == 'sh':
        s += """
    declare -a timeout
    if [ -n \"$max_time\" ]; then
        timeout+=(\"--max-time $max_time\")
    fi
    if [ -n \"$connect_timeout\" ]; then
        timeout+=(\"--connect-timeout $connect_timeout\")
    fi
    """
    elif lang == 'python':
        s += """
    timeout = []
    if max_time:
        timeout += [\"--max-time\", max_time]
    if connect_timeout:
        timeout += [\"--connect-timeout\", connect_timeout]
"""
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def curl_perform(
    lang,
    relative_url="''",
    post_data="''",
    urlenc_data="''",
    query="''",
    curl_cmd='curl',
    curl_flags='',
    curl_target="''",
    curl_stdin="''"
    ):
    """Expands relative_url, query and curl_target before
    issuing curl command. Thus those variables should contain
    appropriately escaped or quoted strings.
    """

    s = ''
    if lang == 'sh':
        s += """
    # https://blogs.gnome.org/shaunm/2009/12/05/urlencode-and-urldecode-in-sh/
    urlquote() {
        LANG=C
        arg=\"$@\"
        i=\"0\"
        while [ \"$i\" -lt ${#arg} ]; do
            c=${arg:$i:1}
            if echo \"$c\" | grep -q '[a-zA-Z0-9/:_\.\-]'; then
                echo -n \"$c\"
            else
                echo -n \"%%\"
                printf \"%%X\" \"'$c'\"
            fi
            i=$((i+1))
        done
    }
    default_args=\"\"
    if [ -n \"$auth_data\" ]; then
        default_args+=\"$auth_data;\"
    fi
    default_args+=\"output_format=txt\"
    curl=\"%s %s --location --fail --silent --show-error\"
    target_data=%s
    location=%s
    post_data=%s
    urlenc_data=%s
    query=%s
    curl_stdin=%s
    # Keep target, data and urlenc as arrays to preserve quoting of spaces
    declare -a target
    declare -a data
    declare -a urlenc
    if [ ! -z \"$target_data\" ]; then
        # Support target_data as string or array while preserving space
        index=0
        while [ $index -lt ${#target_data[@]} ]; do
            # NOTE: trailing space matters - data is already quoted here
            target+=\"${target_data[$index]} \"
            index=$((index+1))
        done
    fi
    if [ ! -z \"$post_data\" ]; then
        # Support post_data as string or array while preserving space
        index=0
        while [ $index -lt ${#post_data[@]} ]; do
            # NOTE: trailing space matters
            data+=\"--data '${post_data[$index]}' \"
            index=$((index+1))
        done
    fi
    if [ ! -z \"$urlenc_data\" ]; then
        # Support urlenc_data as string or array while preserving space
        index=0
        while [ $index -lt ${#urlenc_data[@]} ]; do
            # NOTE: trailing space matters
            data+=\"--data-urlencode '${urlenc_data[$index]}' \"
            index=$((index+1))
        done
    fi
    # Make sure e.g. spaces are encoded since they are not allowed in URL
    url=\"--url '$mig_server/$(urlquote $location)$query'\"
    if [ -z \"$curl_stdin\" ]; then
        command=\"\"
    else
        command=\"$curl_stdin | \"
    fi
    command+=\"$curl ${auth_check[@]} ${ca_check[@]} ${password_check[@]} \"
    command+=\"${timeout[@]} ${data[@]} ${urlenc[@]} ${target[@]} $url\"
    #echo \"DEBUG: command: $command\"
    eval $command
"""% (
                    curl_cmd,
                    curl_flags,
                    curl_target,
                    relative_url,
                    post_data,
                    urlenc_data,
                    query,
                    curl_stdin,
            )
    elif lang == 'python':
        s += """
    default_args = \"\"
    if auth_data:
        default_args += \"%%s;\" %% auth_data
    default_args += \"output_format=txt\"
    curl = ['%s'] + '%s'.split() + ['--location', '--fail', '--silent',
                                    '--show-error']
    target_data = %s
    location = %s
    post_data = %s
    urlenc_data = %s
    query = %s
    curl_stdin = %s
    target = []
    data = []
    urlenc = []
    if target_data:
        if isinstance(target_data, basestring):
            target += [target_data]
        else:
            for val in target_data:
                target += [val]
    if post_data:
        if isinstance(post_data, basestring):
            data += ['--data', post_data]
        else:
            for val in post_data:
                data += ['--data', val]
    if urlenc_data:
        if isinstance(urlenc_data, basestring):
            urlenc += ['--data-urlencode', urlenc_data]
        else:
            for val in urlenc_data:
                urlenc += ['--data-urlencode', val]
    # Make sure e.g. spaces are encoded since they are not allowed in URL
    from urllib import quote as urlquote
    url = ['--url', mig_server + '/' + urlquote(location) + query]
    if curl_stdin:
        input_gen = subprocess.Popen(curl_stdin, stdout=subprocess.PIPE)
        input_source = input_gen.stdout
    else:
        input_source = None
    # NOTE: we build list directly in order to preserve e.g. spaces in paths
    command_list = curl + auth_check + ca_check + password_check + timeout + \\
                   data + urlenc + target + url
    #print \"DEBUG: command: %%s\" %% command_list
    # NOTE: for security we do not invoke shell here
    proc = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=input_source)
    if curl_stdin:
        input_source.close()  # Allow p1 to receive a SIGPIPE if p2 exits. 
    out_buffer = StringIO.StringIO(proc.communicate()[0])
    proc.stdout.close()
    out = out_buffer.readlines()
    #print \"DEBUG: out: %%s\" %% out
    exit_code = proc.returncode
    return (exit_code, out)
""" % (
            curl_cmd,
            curl_flags,
            curl_target,
            relative_url,
            post_data,
            urlenc_data,
            query,
            curl_stdin,
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
        s += """
verbose=0
conf=\"$HOME/.mig/miguser.conf\"
auth_redir=""
flags=""
server_flags=""
mig_server=""
script_path="$0"
script_name=`basename $script_path`
script_dir=`dirname $script_path`
"""
    elif lang == 'python':
        s += comment(lang, '=== Main ===')

        s += """
verbose = 0
conf = os.path.expanduser(\"~/.mig/miguser.conf\")
auth_redir=""
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

        opts_str = 'A:c:hrs:vV'
        if extra_opts:
            opts_str += extra_opts
        s += 'while getopts %s opt; do' % opts_str
        s += """
    case \"$opt\" in
        A)  auth_redir=\"$OPTARG\";;
        c)  conf=\"$OPTARG\"
            flags="$flags -c $conf";;
        h)  usage
            exit 0;;
        s)  mig_server=\"$OPTARG\";;
        v)  verbose=1
            server_flags="${server_flags}v"
            flags="$flags -v";;
        V)  version
            exit 0;;
"""
        if extra_opts_handler:
            s += extra_opts_handler
        s += """
        \?)  # unknown flag
             usage
             exit 1;;
    esac
done
# Drop options
shift `expr $OPTIND - 1`

"""
    elif lang == 'python':
        opts_str = 'A:c:hrs:vV'
        if extra_opts:
            opts_str += extra_opts
        s += 'opt_args = "%s"' % opts_str
        s += """

# preserve arg 0
arg_zero = sys.argv[0]
args = sys.argv[1:]
try:
    opts, args = getopt.getopt(args, opt_args)
except getopt.GetoptError, goe:
    print \"Error: %s\" %  goe
    usage()
    sys.exit(1)

for (opt, val) in opts:
    if opt == \"-A\":
        auth_redir = val
    elif opt == \"-c\":
        conf = val
    elif opt == \"-h\":
        usage()
        sys.exit(0)
    elif opt == \"-s\":
        mig_server = val
    elif opt == \"-v\":
        verbose = 1
        server_flags += \"v\"
    elif opt == \"-V\":
        version()
        sys.exit(0)
"""
        if extra_opts_handler:
            s += extra_opts_handler
        s += """
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
        s += """
if [ ! -r \"$conf\" ]; then
    echo \"Failed to read configuration file: $conf\"
    exit 1
fi

if [ \"$verbose\" -eq \"1\" ]; then
    echo \"using configuration in $conf\"
fi
"""
    elif lang == 'python':
        s += """
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
        s += """
if [ -z \"$mig_server\" ]; then
    read_conf $conf 'migserver'
    mig_server=\"$conf_value\"
fi
if [ -z \"$auth_redir\" ]; then
    read_conf $conf 'auth_redir'
    auth_redir=\"$conf_value\"
fi
# Fall back to cert if not set
if [ -z \"$auth_redir\" ]; then
    auth_redir=\"cert_redirect\"
fi

# Force tilde and variable expansion on path vars
read_conf $conf 'certfile'
eval cert_file=\"$conf_value\"
read_conf $conf 'keyfile'
eval key_file=\"$conf_value\"
read_conf $conf 'cacertfile'
eval ca_cert_file=\"$conf_value\"
read_conf $conf 'password'
password=\"$conf_value\"
read_conf $conf 'connect_timeout'
connect_timeout=\"$conf_value\"
read_conf $conf 'max_time'
max_time=\"$conf_value\"

check_var migserver \"$mig_server\"
if [ \"$auth_redir\" == \"cert_redirect\" ]; then
    check_var certfile \"$cert_file\"
    check_var keyfile \"$key_file\"
fi
"""
    elif lang == 'python':
        s += """
if not mig_server:
    mig_server = read_conf(conf, 'migserver')
if not auth_redir:
    auth_redir = read_conf(conf, 'auth_redir')
# Fall back to cert if not set
if not auth_redir:
    auth_redir = \"cert_redirect\"

def expand_path(path):
    '''Expand user home'''
    result = None
    if path is not None:
        result = os.path.expanduser(os.path.expandvars(path))
    return result

# Force tilde and variable expansion on path vars
cert_file = expand_path(read_conf(conf, 'certfile'))
key_file = expand_path(read_conf(conf, 'keyfile'))
ca_cert_file = expand_path(read_conf(conf, 'cacertfile'))
password = read_conf(conf, 'password')
connect_timeout = read_conf(conf, 'connect_timeout')
max_time = read_conf(conf, 'max_time')

check_var('migserver', mig_server)
if auth_redir == \"cert_redirect\":
    check_var('certfile', cert_file)
    check_var('keyfile', key_file)
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
    """Insert string as a comment in the script.
    Multi line comments (string with newlines) also work.
    """

    s = ''
    if lang == 'sh':
        s += '# %s\n' % string.replace('\n', '\n# ')
    elif lang == 'python':
        s += '# %s\n' % string.replace('\n', '\n# ')
    else:
        print 'Error: %s not supported!' % lang
    return s


def get_xgi_bin(configuration, force_legacy=False):
    """Lookup the preferred Xgi-bin for server URLs. If WSGI is enabled in the
    configuration wsgi-bin is used. Otherwise the legacy cgi-bin is used.
    The optional force_legacy argument can be used to force legacy cgi-bin use
    e.g. for scripts that are not supported in WSGI.
    """
    
    if not force_legacy and configuration.site_enable_wsgi:
        return 'wsgi-bin'
    return 'cgi-bin'


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
Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter

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
    s += '\n'
    s += doc_string(lang, intro)
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


def write_license(configuration, dst_dir, name='COPYING'):
    """Write license file to dst_dir/name"""
    src_path = os.path.join(os.path.dirname(__file__), '..', '..', name)
    dst_path = os.path.abspath(os.path.join(dst_dir, name))
    try:
        src_fd = open(src_path, 'r')
        dst_fd = open(dst_path, 'w')
        dst_fd.write(src_fd.read())
        src_fd.close()
        dst_fd.close()
    except Exception, exc:
        print 'Error: failed to write license %s: %s' % (dst_path, exc)
        return False
        
