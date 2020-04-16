#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# publicscriptgen - Basic script generator functions
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

# TODO: allow use of xmlrpc instead of curl from python

"""Shared helper functions for generating public MiG scripts
for the supported programming languages.
"""

import os

from shared.base import get_xgi_bin

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
    local %s=(${@:1:$extract_count})
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

# Names of miguser conf variables wrapped in conf container - no credentials
_conf_pack = ['mig_server', 'auth_cookie_file', 'ca_cert_file', 'auth_redir',
              'max_time', 'connect_timeout']


def pack_conf(lang, conf_name):
    """Pack each miguser conf variable from _conf_pack for function arg"""
    s = ''
    if lang == 'sh':
        pairs = ['[\"%s\"]=\"${%s}\"' % (name, name) for name in _conf_pack]
        s += """
    declare -A %s
    %s=(%s)
        """ % (conf_name, conf_name, ' '.join(pairs))
    elif lang == 'python':
        pairs = ['\"%s\": %s' % (name, name) for name in _conf_pack]
        s += """
    %s = {%s}
""" % (conf_name, ', '.join(pairs))
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def unpack_conf(lang, conf_name):
    """Unpack each miguser conf variable from _conf_pack for local function"""
    s = ''
    if lang == 'sh':
        # TODO: implement proper unpack here? not needed due to global args
        # pairs = ['    %s=${%s["%s"]}' %
        #         (name, conf_name, name) for name in _conf_pack]
        pairs = ['    %s="${%s}"' % (name, name) for name in _conf_pack]
        s += "\n".join(pairs) + "\n"
    elif lang == 'python':
        pairs = ['    %s = %s.get("%s", "")' % (name, conf_name, name)
                 for name in _conf_pack]
        s += "\n".join(pairs) + "\n"
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


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
        if [ -z \"$auth_cookie_file\" ]; then
            auth_check=(\"--cert $cert_file\" \"--key $key_file\")
            put_arg=\"CERTPUT\"
            # We must set something for form argument
            auth_data=\"_=certauth\"
        else
            auth_check=(\"--cookie $auth_cookie_file\" \"--cookie-jar $auth_cookie_file\")
            put_arg=\"PUT\"
            # We must set something for form argument
            auth_data=\"_=oidauth\"
        fi
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
        if not auth_cookie_file:
            auth_check = [\"--cert\", cert_file, \"--key\", key_file]
            put_arg = \"CERTPUT\"
            # We must set something for form argument
            auth_data = \"_=certauth\"
        else:
            auth_check = [\"--cookie\", auth_cookie_file, \"--cookie-jar\", auth_cookie_file]
            put_arg = \"PUT\"
            # We must set something for form argument
            auth_data = \"_=oidauth\"
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
    curl_stdin="''",
    override_url_base='""'
):
    """Expands relative_url, query and curl_target before
    issuing curl command. Thus those variables should contain
    appropriately escaped or quoted strings.
    If override_url_base is set it will be prefixed to relative_url instead of
    automatic mig_server value.
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
    out_form=\"output_format=txt\"
    if [ -n \"$auth_data\" ]; then
        default_args+=\"$auth_data;\"
    fi
    default_args+=\"$out_form\"
    curl=\"%s %s --location --fail --silent --show-error\"
    target_data=%s
    location=%s
    url_prefix=%s
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
    # Use mig_server as base url unless explicitly overridden
    if [ -z \"$url_prefix\" ]; then
        url_prefix=\"$mig_server/\"
    fi
    # Make sure e.g. spaces are encoded since they are not allowed in URL
    url=\"--url '$url_prefix$(urlquote $location)$query'\"
    if [ -z \"$curl_stdin\" ]; then
        command=\"\"
    else
        command=\"$curl_stdin | \"
    fi
    command+=\"$curl ${auth_check[@]} ${ca_check[@]} ${password_check[@]} \"
    command+=\"${timeout[@]} ${data[@]} ${urlenc[@]} ${target[@]} $url\"
    #echo \"DEBUG: command: $command\"
    # TODO: better mimic python return (exit_code, out)?
    #       doing it like this breaks various things :-(
    #out=$(eval $command 2>&1)
    eval $command
    exit_code=$?
""" % (
            curl_cmd,
            curl_flags,
            curl_target,
            relative_url,
            override_url_base,
            post_data,
            urlenc_data,
            query,
            curl_stdin,
        )
    elif lang == 'python':
        if curl_stdin == "''":
            s += """
    # Init these variables to dummy values: they are only actually used for
    # scripts using curl_stdin, so only define them to make pylint happy.
    start, chunk_bytes = 0, 1
"""
        s += """
    default_args = \"\"
    out_form = \"output_format=txt\"
    if auth_data:
        default_args += \"%%s;\" %% auth_data
    default_args += out_form
    curl = ['%s'] + '%s'.split() + ['--location', '--fail', '--silent',
                                    '--show-error']
    target_data = %s
    location = %s
    url_prefix = %s
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

    if not url_prefix:
        url_prefix = mig_server + '/'

    # Make sure e.g. spaces are encoded since they are not allowed in URL
    from urllib import quote as urlquote
    url = ['--url', url_prefix + urlquote(location) + query]
    input_fd = None
    if curl_stdin:
        input_source = subprocess.PIPE
        if isinstance(curl_stdin, basestring):
            input_fd = open(curl_stdin, 'rb')
            input_fd.seek(start)
        elif isinstance(curl_stdin, list):
            input_gen = subprocess.Popen(curl_stdin, stdout=subprocess.PIPE)
            input_fd = input_gen.stdout
        else:
            print 'ERROR: unexpected curl input: %%s' %% curl_stdin
    else:
        input_source = None
    # NOTE: we build list directly in order to preserve e.g. spaces in paths
    command_list = curl + auth_check + ca_check + password_check + timeout + \\
                   data + urlenc + target + url
    #print \"DEBUG: command: %%s\" %% command_list
    # NOTE: for security we do not invoke shell here
    proc = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=input_source)
    if input_fd:
        out_buffer = StringIO.StringIO(proc.communicate(input_fd.read(chunk_bytes))[0])
        input_fd.close()
    else:
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
            override_url_base,
            post_data,
            urlenc_data,
            query,
            curl_stdin,
        )
    else:
        print 'Error: %s not supported!' % lang
        return ''

    return s


def curl_perform_flex(lang, conf_arg, base_arg, url_arg, post_arg, urlenc_arg,
                      query_arg, curl_cmd='curl', curl_flags=''):
    """Helper to use curl_perform with dynamic variables for the X_arg vars"""

    s = ''
    if lang == 'sh':
        base_val = "${%s}" % base_arg
        url_val = "${%s}" % url_arg
        post_val = "${%s}" % post_arg
        urlenc_val = "${%s}" % urlenc_arg
        query_val = "${%s}" % query_arg
    elif lang == 'python':
        base_val = "%s" % base_arg
        url_val = "%s" % url_arg
        post_val = "%s" % post_arg
        urlenc_val = "%s" % urlenc_arg
        query_val = "%s" % query_arg
    else:
        print 'Error: %s not supported!' % lang
        return ''
    # NOTE: we pass and unwrap loaded miguser conf values in user_conf container
    s += begin_function(lang, 'curl_post_flex',
                        ['user_conf', 'base_val', 'url_val', 'post_val',
                         'urlenc_val', 'query_val'],
                        '''Wrap a curl POST for further use of output page''')
    s += unpack_conf(lang, conf_arg)
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(lang, url_val, post_val, urlenc_val, query_val, curl_cmd,
                      curl_flags, override_url_base=base_val)
    s += end_function(lang, 'curl_post_flex')
    s += begin_function(lang, 'curl_get_flex',
                        ['user_conf', 'base_val', 'url_val', 'post_val',
                         'urlenc_val', 'query_val'],
                        '''Wrap a curl GET for further use of output page''')
    s += unpack_conf(lang, conf_arg)
    s += auth_check_init(lang)
    s += timeout_check_init(lang)
    s += curl_perform(lang, url_val, post_val, urlenc_val, query_val, curl_cmd,
                      curl_flags + ' -G', override_url_base=base_val)
    s += end_function(lang, 'curl_get_flex')
    return s


def curl_chain_login_steps(
    lang,
    relative_url="''",
    post_data="''",
    migoid_base='',
    extoid_base=''
):
    """Run a series of curl commands to initialize a openid login session using
    relative_url as the target URL to trigger OpenID and any 2-Factor Auth
    handlers in turn.
    """
    s = ''
    s += """
    # Run curl and extract location of openid redirector from output
    # NOTE: no form or query args for initial call
"""
    if lang == 'sh':
        s += """
    extoid_base='%s'
    migoid_base='%s'
    home_url=%s
    base_val=''
    url_val=%s
    post_val=''
""" % (extoid_base, migoid_base, relative_url, relative_url)
        base_val = '${base_val}'
        url_val = '${url_val}'
        post_val = '${post_val}'
    elif lang == 'python':
        s += """
    extoid_base = '%s'
    migoid_base = '%s'
    home_url = %s
    base_val = ''
    url_val = %s
    post_val = ''
""" % (extoid_base, migoid_base, relative_url, relative_url)
        base_val = 'base_val'
        url_val = 'url_val'
        post_val = 'post_val'
    else:
        print 'Error: %s not supported!' % lang
        return ''

    if lang == 'sh':
        s += """
    # NOTE: curl_post_flex sets return val in $exit_code and curl output to stdout
    out=$(curl_post_flex \"$user_conf\" \"$base_val\" \"$url_val\" \"$post_val\" '' '')
    if echo $out | grep -q \"$extoid_base\" ; then
        # Extract CSRF token
        ct_value=$(echo $out | sed 's@.* name=\"ct\" value=\"\([0-9a-f]\+\)\".*@\\1@g')
        if [ ${#ct_value} -ne 40 ]; then
            echo 'Could not extract extoid CSRF token value'
            exit 1
        fi
        while [ -z \"$username\" ]; do
            echo -n 'Username: '
            read username
        done
        while [ -z \"$password\" ]; do
            # Hide typing
            stty -echo
            echo -n 'Password: '
            read password
            echo
            stty echo
        done
        # Post login and password credentials, redirects to actual site URL
        base_val=\"${extoid_base}/\" 
        url_val=\"processTrustResult\" 
        post_val=\"user=${username}&pwd=${password}&ct=${ct_value};allow=Yes\"
        out=$(curl_post_flex \"$user_conf\" \"$base_val\" \"$url_val\" \"$post_val\" '' '')
    elif echo $out | grep -q \"$(dirname ${migoid_base})\" ; then
        # No CSRF token here
        while [ -z \"$username\" ]; do
            echo -n 'Username: '
            read username
        done
        while [ -z \"$password\" ]; do
            # Hide typing
            stty -echo
            echo -n 'Password: '
            read password
            echo
            stty echo
        done
        base_val=\"${migoid_base}/\"
        url_val=\"allow\"
        post_val=\"identifier=${username}&password=${password}&remember=yes&yes=yes\"
        out=$(curl_post_flex \"$user_conf\" \"$base_val\" \"$url_val\" \"$post_val\" '' '')
        # TODO: curl fails hard with retval 22 and 404 Not found on login error
        if [ -z \"$out\" ]; then
            out='Authentication failed'
        fi
    elif echo $out | grep -q 'Home' ; then
        echo 'Already completely logged in!'
        exit 0
    elif echo $out | grep -q '2-Factor Authentication' ; then
        echo 'Already logged in to OpenID'
    else
        echo 'Unexpected OpenID redirect result - trying to proceed'
        #echo 'DEBUG: ' $out
    fi

    if echo $out |grep -q 'Authentication failed' ; then
        echo 'OpenID login failed!'
        exit 1
    fi

    # Optional 2FA at this point
    twofactor_enabled=0
    for attempt in 1 2 3; do
        if echo $out | grep -q '2-Factor Authentication' ; then
            twofactor_enabled=1
            token=''
            while [ -z \"$token\" ]; do
                echo -n '2-Factor Auth token: '
                read token
            done
            base_val=\"${mig_server}/\"
            # TODO: extract url from out instead?
            url_val=\"wsgi-bin/twofactor.py\"
            post_val=\"output_format=txt&action=auth&token=${token}&redirect_url=/${home_url}\"
            out=$(curl_post_flex \"$user_conf\" \"$base_val\" \"$url_val\" \"$post_val\" '' '')
        else
            #echo 'DEBUG: past 2FA auth'
            #echo \"DEBUG: $out\"
            break
        fi
    done

    if echo $out | grep -q 'Home' ; then
        echo 'Login succeeded!'
        exit 0
    elif [ $twofactor_enabled -eq 1 ]; then
        echo '2-Factor Auth failed!'
        #echo \"DEBUG: $out\"
        exit 2
    else
        echo 'Login failed with unexpected result!'
        #echo \"DEBUG: $out\"
        exit 3
    fi
        """
    elif lang == 'python':
        s += """
    retval, msg = 0, []
    (status, out) = curl_post_flex(user_conf, base_val, url_val, post_val, '', '')
    if [line for line in out if extoid_base in line]:
        # Extract CSRF token
        ct_value = ''
        ct_prefix = ' name=\"ct\" value=\"'
        ct_suffix = '\">'
        for line in out:
            if ct_prefix in line:
                ct_value = line.split(ct_prefix, 1)[1].split(ct_suffix, 1)[0]
        if len(ct_value) != 40:
            msg.append('Could not extract extoid CSRF token value')
            return (1, msg)
        while not username:
            username = raw_input('Username: ').strip()
        while not password:
            password = getpass.getpass()
        # Post login and password credentials, redirects to actual site URL
        base_val = extoid_base + '/' 
        url_val = \"processTrustResult\" 
        post_val = 'user=%s&pwd=%s&ct=%s&allow=Yes' % (username, password, ct_value)
        (status, out) = curl_post_flex(user_conf, base_val, url_val, post_val, '', '')
    # NOTE: page only has URL without openid suffix
    elif [line for line in out if os.path.dirname(migoid_base) in line]:
        # No CSRF token here
        while not username:
            username = raw_input('Username: ').strip()
        while not password:
            password = getpass.getpass()
        base_val = migoid_base + '/'
        url_val = \"allow\"
        post_val = 'identifier=%s&password=%s&remember=yes&yes=yes' % (username, password)
        (status, out) = curl_post_flex(user_conf, base_val, url_val, post_val, '', '')
        # NOTE: curl fails hard with retval 22 and 404 Not found on login error
        if status == 22:
            out.append('Authentication failed')
    elif [line for line in out if 'Home' in line]:
        msg.append('Already completely logged in!')
        return (0, msg)
    elif [line for line in out if '2-Factor Authentication' in line]:
        msg.append('Already logged in to OpenID')
    else:
        msg.append('Unexpected OpenID redirect result - trying to proceed')
        #msg.append('DEBUG: %s' % out)

    if [line for line in out if 'Authentication failed' in line]:
        msg.append('OpenID login failed!')
        return (1, msg)

    # Optional 2FA at this point
    twofactor_enabled = False
    for attempt in range(3):
        if [line for line in out if '2-Factor Authentication' in line]:
            twofactor_enabled = True
            token = ''
            while not token:
                token = raw_input('2-Factor Auth token: ')
            base_val = mig_server + '/'
            # TODO: extract url from out instead?
            url_val = \"wsgi-bin/twofactor.py\"
            post_val = \"output_format=txt&action=auth&token=\"+token+\"&redirect_url=/\"+home_url
            (status, out) = curl_post_flex(user_conf, base_val, url_val, post_val, '', '')
        else:
            #msg.append('DEBUG: past 2FA auth')
            #msg.append('DEBUG: '+out)
            break

    #msg.append('DEBUG: '+out)
    if [line for line in out if 'Home' in line]:
        msg.append('Login succeeded!')
        return (0, msg)
    elif twofactor_enabled:
        msg.append('2-Factor Auth failed!')
        return (2, msg)
    else:
        msg.append('Login failed with unexpected result!')
        return (3, msg)
        """

    return s


def curl_chain_logout_steps(
    lang,
    relative_url="''",
    post_data="''",
    migoid_base='',
    extoid_base=''
):
    """Run a series of curl commands to tear down an active openid login
    session.
    """
    s = ''
    s += """
    # Run curl and extract location of openid redirector from output
    # NOTE: no form or query args for initial call
"""
    if lang == 'sh':
        s += """
    logout_url=%s
    extoid_base='%s'
    migoid_base='%s'
    url_base=''
    url_val=%s
    post_val=''
""" % (relative_url, extoid_base, migoid_base, relative_url)
        url_val = '${url_val}'
        post_val = '${post_val}'
    elif lang == 'python':
        s += """
    logout_url = %s
    extoid_base = '%s'
    migoid_base = '%s'
    url_base = ''
    url_val = %s
    post_val = ''
""" % (relative_url, extoid_base, migoid_base, relative_url)
        url_val = 'url_val'
        post_val = 'post_val'
    else:
        print 'Error: %s not supported!' % lang
        return ''

    if lang == 'sh':
        s += """
    # NOTE: curl_post_flex sets return val in $exit_code and curl output on stdout
    out=$(curl_post_flex \"$user_conf\" \"$url_base\" \"$url_val\" \"$post_val\" '' '')
    if echo $out | grep -q \"$extoid_base\" ; then
        url_base=\"${extoid_base}/\"
        url_val=\"logout\"
        if echo $out | grep -q $url_val ; then
            # NOTE: we must use GET rather than POST here
            post_val=\"return_to=${mig_server}/${logout_url}?logout=true\"
            out=$(curl_get_flex \"$user_conf\" \"$url_base\" \"$url_val\" \"$post_val\" '' '')
        else
            echo 'No active login session found.'
        fi
    # NOTE: page only prints URL without openid suffix
    elif echo $out | grep -q \"$(dirname ${migoid_base})\" ; then
        url_base=\"${migoid_base}/\"
        url_val=\"logout\"
        if echo $out | grep -q \"$url_val\" ; then
            post_val=\"return_to=${mig_server}/${logout_url}?logout=true\"
            out=$(curl_post_flex \"$user_conf\" \"$url_base\" \"$url_val\" \"$post_val\" '' '')
        else
            echo 'No active login session found.'
        fi
    elif echo $out | grep -q 'with a user certificate'; then
            echo 'Certificate logins do not use login sessions.'    
    else
        echo 'Unexpected logout page content - trying to proceed'
    fi

    if echo $out |grep -q 'You are now logged out' ; then
        echo 'Logout succeeded!'
    else
        echo 'Logout failed!'
    fi

    # TODO: clear cookies?
    #rm -f ${auth_cookie_file}
"""
    elif lang == 'python':
        s += """
    retval, msg = 0, []
    (status, out) = curl_post_flex(user_conf, url_base, url_val, post_val, '', '')
    if [line for line in out if extoid_base in line]:
        url_base = extoid_base + '/'
        url_val = \"logout\"
        if [line for line in out if url_val in line]:
            # NOTE: we must use GET rather than POST here
            post_val = 'return_to='+mig_server+'/'+logout_url+'?logout=true'
            (status, out) = curl_get_flex(user_conf, url_base, url_val, post_val, '', '')
        else:
            msg.append('No active login session found.')
    # NOTE: page only prints URL without openid suffix
    elif [line for line in out if os.path.dirname(migoid_base) in line]:
        url_base = migoid_base + '/'
        url_val = \"logout\"
        if [line for line in out if url_val in line]:
            post_val = 'return_to='+mig_server+'/'+logout_url+'?logout=true'
            (status, out) = curl_post_flex(user_conf, url_base, url_val, post_val, '', '')
        else:
            msg.append('No active login session found.')
    elif [line for line in out if 'with a user certificate' in line]:
        msg.append('Certificate logins do not use login sessions.')
    else:
        msg.append('Unexpected logout page content - trying to proceed')

    if [line for line in out if 'You are now logged out' in line]:
        msg.append('Logout succeeded!')
        retval = 0
    else:
        msg.append('Logout failed!')
        retval = 1

    #msg.append('DEBUG: '+ '\\n'.join(msg))
    
    # TODO: clear cookies?
    #os.remove(auth_cookie_file)

    return (retval, msg)
"""

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
read_conf $conf 'authcookiefile'
eval auth_cookie_file=\"$conf_value\"
read_conf $conf 'username'
eval username=\"$conf_value\"
read_conf $conf 'password'
password=\"$conf_value\"
read_conf $conf 'connect_timeout'
connect_timeout=\"$conf_value\"
read_conf $conf 'max_time'
max_time=\"$conf_value\"

check_var migserver \"$mig_server\"
if [ \"$auth_redir\" == \"cert_redirect\" ]; then
    if [ -z \"$auth_cookie_file\" ]; then
        check_var certfile \"$cert_file\"
        check_var keyfile \"$key_file\"
    else
        check_var authcookiefile \"$auth_cookie_file\"
    fi
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
auth_cookie_file = expand_path(read_conf(conf, 'authcookiefile'))
username = read_conf(conf, 'username')
password = read_conf(conf, 'password')
connect_timeout = read_conf(conf, 'connect_timeout')
max_time = read_conf(conf, 'max_time')

check_var('migserver', mig_server)
if auth_redir == \"cert_redirect\":
    if not auth_cookie_file:
        check_var('certfile', cert_file)
        check_var('keyfile', key_file)
    else:
        check_var('authcookiefile', auth_cookie_file)
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
Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter

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
""" % name
    intro = \
        """
This MiG %s script was autogenerated by the MiG User Script Generator !!!
Any changes should be made in the generator and not here !!!
""" % lang
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
import getpass
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
