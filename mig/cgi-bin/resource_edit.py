#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource_edit - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid
# Martin Rehr martin@rehr.dk August 2005

# TODO: input validation!!!
#  fix a number of directory traversal vulnerabilities:
#  - *must* check that user input used in filenames doesn't use
#    '..' or similar that can cause writes in illegal locations!
#  - take a look at head.py for an example:
#    i.e. 'real_path.startswith(base)'
#  valid values in general and some format issues:
#  - generally only accept valid input strings to avoid bad side
#    effects of using variables
#  - must strip input of extra space to avoid problems in e.g.
#    resource creation commands

import cgi
import cgitb
cgitb.enable()
import os
import time
import re

import shared.resconfkeywords as resconfkeywords
import shared.confparser as confparser
import shared.parser as parser
from shared.findtype import is_owner
from shared.html import get_cgi_html_header, html_encode
from shared.refunctions import list_runtime_environments, \
    get_active_re_list
from shared.cgishared import init_cgi_script_with_cert
from shared.notification import send_resource_create_request_mail
from shared.ssh import default_ssh_options
from shared.vgrid import user_allowed_vgrids, default_vgrid
from shared.useradm import client_id_dir


def get_regex_non_numeric():
    return re.compile('[^0-9]*')


def get_local_execute_command(dir, node, name='master'):
    return 'cd %(dir)s ; chmod 700 %(name)s_node_script_%(node)s.sh; nice ./%(name)s_node_script_%(node)s.sh start'\
         % {'dir': dir, 'node': node, 'name': name}


def get_default_execute_command(execution_dir, execution_node):
    return r'ssh %s %s \\"%s\\"' % (' '.join(default_ssh_options()),
                                    execution_node,
                                    get_local_execute_command(execution_dir,
                                    execution_node))


def get_local_status_command(dir, node, name='master'):
    if 'master' != name:
        return 'cd %(dir)s; nice ./%(name)s_node_script_%(node)s.sh status %(pgid)s'\
             % {
            'dir': dir,
            'node': node,
            'name': name,
            'pgid': '$mig_exe_pgid',
            }
    return r'if [ \\`ps -o pid= -g $mig_exe_pgid | wc -l \\` -eq 0 ]; then exit 1; else exit 0;fi'\
         % {'dir': dir, 'node': node, 'name': name}


def get_default_status_command(execution_dir, execution_node):
    pgid_file = execution_dir + 'job.pgid'
    return r'ssh %s %s  \"MIG_EXE_PGID=$mig_exe_pgid ; if [ \\\\\\`ps -o pid= -g \\\\\\$MIG_EXE_PGID | wc -l \\\\\\` -eq 0 ]; then exit 1; else exit 0;fi \"'\
         % (' '.join(default_ssh_options()), execution_node)


def get_local_stop_command(dir, node, name='master'):
    if 'master' != name:
        return 'cd %(dir)s; nice ./%(name)s_node_script_%(node)s.sh stop %(pgid)s'\
             % {
            'dir': dir,
            'node': node,
            'name': name,
            'pgid': '$mig_exe_pgid',
            }
    return 'kill -9 -$mig_exe_pgid ' % {'dir': dir, 'node': node,
            'name': name}


def get_default_stop_command(execution_dir, execution_node):
    return r'ssh %s %s \\"%s\\"' % (' '.join(default_ssh_options()),
                                    execution_node,
                                    get_local_stop_command(execution_dir,
                                    execution_node))


def get_local_clean_command(dir, node, name='master'):
    if 'master' != name:
        return 'cd %(dir)s; nice ./%(name)s_node_script_%(node)s.sh clean %(pgid)s'\
             % {
            'dir': dir,
            'node': node,
            'name': name,
            'pgid': '$mig_exe_pgid',
            }
    return 'killall -9 %(name)s_node_script_%(node)s.sh; rm -rf %(dir)s'\
         % {'dir': dir, 'node': node, 'name': name}


def get_default_clean_command(execution_dir, execution_node):
    return r'ssh %s %s \\"%s\\"' % (' '.join(default_ssh_options()),
                                    execution_node,
                                    get_local_clean_command(execution_dir,
                                    execution_node))


def parse_resource_config(conf_dict, config_file):
    external_dict = ''
    result = ''

    result = parser.parse(config_file)

    external_dict = resconfkeywords.get_keywords_dict(conf_dict)

    (status, msg) = parser.check_types(result, external_dict, conf_dict)

    if not status:
        return (False, 'Parse failed (typecheck) ' + msg)

    # Insert the parts from mrslkeywords we need in the rest of the MiG system

    for (key, value_dict) in external_dict.iteritems():
        conf_dict[key] = value_dict['Value']

    return (status, msg)


def retrieve_execution_nodes(exe_nodes, prepend_leader=False):
    """Return an ordered list of exe nodes from the allowed range formats.
    Prepend execution-leader node if prepend_leader is set.
    """

    execution_nodes = []
    regex_nonnumeric = get_regex_non_numeric()
    index = 0

    if prepend_leader:
        execution_nodes.append('execution-leader')

    for noderange in exe_nodes.split(';'):
        noderange = noderange.replace(' ', '')

        node_array = noderange.split('->')

        if len(node_array) == 1:
            node_name = node_array[0]
            if not node_name in execution_nodes:
                execution_nodes.append(node_name)
        elif len(node_array) == 2:

            start_node = regex_nonnumeric.split(node_array[0])[-1]
            end_node = regex_nonnumeric.split(node_array[1])[-1]
            node_name = (node_array[0])[0:0 - len(start_node)]

            if start_node.isdigit() and end_node.isdigit():
                start_node = int(start_node)
                end_node = int(end_node) + 1
            else:
                start_node = -1
                end_node = -1

            for i in range(start_node, end_node):
                if not node_name in execution_nodes:
                    execution_nodes.append(node_name + str(i))
    return execution_nodes


def generate_execution_node_string(exe_nodes, hide_leader=True):
    """Create a node name string from list of exe config dictionaries"""

    execution_nodes = ''
    node_name = ''
    new_node_name = ''
    node_index = -1
    new_node_index = -1
    add_node_index = [-1, -1]
    regex_nonnumeric = get_regex_non_numeric()

    if hide_leader:
        exe_nodes = [exe for exe in exe_nodes if 'execution-leader'
                      != exe['execution_node']]
    for execution_node in exe_nodes:

        # If only NonNumeric characters, write the execnode as it is.

        if not execution_node['name'].isdigit():
            if execution_nodes:
                execution_nodes = execution_nodes + '; '
            execution_nodes = execution_nodes + execution_node['name']
        else:
            non_numeric_split = \
                regex_nonnumeric.split(execution_node['name'])

            new_node_index = int(non_numeric_split[-1])
            new_node_name = (execution_node['name'])[0:0
                 - len(non_numeric_split[-1])]

            if node_name == new_node_name and node_index\
                 == new_node_index - 1:
                add_node_index[1] = new_node_index
            else:
                if -1 != add_node_index[0]:
                    if execution_nodes:
                        execution_nodes += '; '

                    if -1 == add_node_index[1]:
                        execution_nodes += node_name\
                             + str(add_node_index[0])
                    else:
                        execution_nodes += node_name + ' '\
                             + str(add_node_index[0]) + '->'\
                             + str(add_node_index[1])

                add_node_index[0] = new_node_index
                add_node_index[1] = -1

            node_name = new_node_name
            node_index = new_node_index

    if -1 != add_node_index[0]:
        if len(execution_nodes) > 0:
            execution_nodes += '; '

        if -1 != add_node_index[1]:
            execution_nodes += node_name + ' ' + str(add_node_index[0])\
                 + '->' + str(add_node_index[1])
        else:
            execution_nodes += node_name + str(add_node_index[0])

    return execution_nodes


# ## Main ###

(logger, configuration, client_id, o) = init_cgi_script_with_cert()
client_dir = client_id_dir(client_id)
logger.info('Starting Resource edit GUI.')

form = cgi.FieldStorage()

# Admin mail probably contains <ADDRESS> which is ignored as an unknown tag.
# Escape the string to avoid that the browser simply hides the address.

admin_email = cgi.escape(configuration.admin_email)

# Please note that base_dir must end in slash to avoid access to other
# user dirs when own name is a prefix of another user name

base_dir = os.path.abspath(os.path.join(configuration.resource_pending,
                           client_dir)) + os.sep

RUNTIMEENVIRONMENT_FIELDS = 10
VGRID_FIELDS = 3

if form.has_key('new_resource'):
    conf_file = ''
    pending_file = ''

    if form.has_key('Ok'):
        pending_file = os.path.join(base_dir, form['hosturl'].value
                                     + '.' + str(time.time()))
elif form.has_key('hosturl') and form.has_key('hostidentifier'):

    resource_id = form['hosturl'].value + '.' + form['hostidentifier'
            ].value
    if not is_owner(client_id, resource_id,
                    configuration.resource_home, logger):
        o.out('Failure: You (' + client_id + ') must be an owner of '
               + form['hosturl'].value + ' to edit it.')
        o.reply_and_exit(o.ERROR)

    conf_file = configuration.resource_home + resource_id\
         + '/config.MiG'
    pending_file = os.path.join(base_dir, form['hosturl'].value + '.'
                                 + str(time.time()))
else:

    o.out('Failure: hosturl and hostidentifier must be supplied.')
    o.reply_and_exit(o.ERROR)
if (form.has_key('new_resource') or form.has_key('apply_changes'))\
     and form.has_key('hosturl') and form.has_key('hostidentifier'):

    lrms_type = 'Native'
    execution_leader = False
    if form.has_key('lrms_type'):
        lrms_type = form['lrms_type'].value
        if -1 != lrms_type.find('-execution-leader'):
            execution_leader = True

    # Parse Execution nodes

    execution_nodes = []
    if form.has_key('execution_nodes'):
        execution_nodes = \
            retrieve_execution_nodes(form['execution_nodes'].value,
                execution_leader)

    if not execution_nodes:
        execution_nodes.append(form['frontend_node'].value)

    if form.has_key('apply_changes'):
        logger.info(client_id
                     + ' is trying to update the configuration for '
                     + form['hosturl'].value)
    elif form.has_key('new_resource'):
        logger.info(client_id
                     + ' is trying to create a new resource configuration for '
                     + form['hosturl'].value)

    if not os.path.isdir(os.path.dirname(pending_file)):
        try:
            os.makedirs(os.path.dirname(pending_file))
        except Exception, excep:
            o.out('Could not create directory to hold resource configuration!'
                  , excep)
            o.reply_and_exit(o.ERROR)

    # write file to disk

    try:
        logger.info('write to file: %s' % pending_file)
        fd = open(pending_file, 'w')

        fd.write('::MIGUSER::\n')
        if form.has_key('mig_user'):
            fd.write(form['mig_user'].value + '\n')
        fd.write('\n')

        fd.write('::HOSTURL::\n')
        if form.has_key('hosturl'):
            fd.write(form['hosturl'].value + '\n')
        fd.write('\n')

        fd.write('::HOSTIDENTIFIER::\n')
        if form.has_key('hostidentifier'):
            fd.write(form['hostidentifier'].value + '\n')
        fd.write('\n')

        if form.has_key('publicname') and form['publicname'].value:
            fd.write('::PUBLICNAME::\n')
            fd.write(form['publicname'].value + '\n')
            fd.write('\n')

        fd.write('::RESOURCEHOME::\n')
        if form.has_key('mig_home') and form.has_key('hosturl')\
             and form.has_key('hostidentifier'):
            fd.write(form['mig_home'].value + '/MiG' + '/mig_frontend/'
                      + form['hosturl'].value + '.'
                      + form['hostidentifier'].value + '\n')
        fd.write('\n')

        fd.write('::SCRIPTLANGUAGE::\n')
        if form.has_key('scriptlanguage'):
            fd.write(form['scriptlanguage'].value + '\n')
        fd.write('\n')

        fd.write('::JOBTYPE::\n')
        if form.has_key('jobtype'):
            fd.write(form['jobtype'].value + '\n')
        fd.write('\n')

        fd.write('::SSHPORT::\n')
        if form.has_key('sshport'):
            fd.write(form['sshport'].value + '\n')
        fd.write('\n')

        if form.has_key('sshmultiplex') and form['sshmultiplex'].value\
             != '0':
            fd.write('::SSHMULTIPLEX::\n')
            fd.write(form['sshmultiplex'].value + '\n')
            fd.write('\n')

        fd.write('::MEMORY::\n')
        if form.has_key('memory'):
            fd.write(form['memory'].value + '\n')
        fd.write('\n')

        fd.write('::DISK::\n')
        if form.has_key('disk'):
            fd.write(form['disk'].value + '\n')
        fd.write('\n')

        fd.write('::CPUCOUNT::\n')
        if form.has_key('cpucount'):
            fd.write(form['cpucount'].value + '\n')
        fd.write('\n')

        fd.write('::ARCHITECTURE::\n')
        if form.has_key('architecture'):
            fd.write(form['architecture'].value + '\n')
        fd.write('\n')

        exe_count = len(execution_nodes)
        if execution_leader:
            exe_count -= 1
        total_nodes = exe_count * int(form['nodecount'].value)

        fd.write('::NODECOUNT::\n')
        fd.write(str(total_nodes) + '\n')
        fd.write('\n')

        fd.write('::RUNTIMEENVIRONMENT::\n')

        for i in range(int(form['runtime_env_fields'].value)):
            runtime_env = 'runtimeenvironment' + str(i)
            env_values = 're_values' + str(i)
            if form.has_key(runtime_env):
                fd.write('name: ' + form[runtime_env].value + '\n')
                if form.has_key(env_values):
                    fd.write(form[env_values].value + '\n')

        fd.write('\n')

        fd.write('::HOSTKEY::\n')
        if form.has_key('frontend_node') and form.has_key('hostip'):
            fd.write(form['frontend_node'].value + ',' + form['hostip'
                     ].value)
            if not form.has_key('hostkey'):
                fd.write('\n')
        if form.has_key('hostkey'):
            raw_key = form['hostkey'].value.strip()
            if not raw_key.startswith('ssh-rsa'):
                raw_key = 'ssh-rsa ' + raw_key
            fd.write(' ' + raw_key + '\n')
        fd.write('\n')

        fd.write('::FRONTENDNODE::\n')
        if form.has_key('frontend_node'):
            fd.write(form['frontend_node'].value + '\n')
        fd.write('\n')

        fd.write('::FRONTENDLOG::\n')
        if form.has_key('mig_home') and form.has_key('hosturl')\
             and form.has_key('hostidentifier'):
            fd.write(form['mig_home'].value + '/MiG' + '/mig_frontend/'
                      + form['hosturl'].value + '.'
                      + form['hostidentifier'].value + '/frontendlog'
                      + '\n')
        fd.write('\n')

        if form.has_key('max_download_bandwidth')\
             and form['max_download_bandwidth'].value != '0':
            fd.write('::MAXDOWNLOADBANDWIDTH::\n')
            fd.write(form['max_download_bandwidth'].value + '\n')
            fd.write('\n')

        if form.has_key('max_upload_bandwidth')\
             and form['max_upload_bandwidth'].value != '0':
            fd.write('::MAXUPLOADBANDWIDTH::\n')
            fd.write(form['max_upload_bandwidth'].value + '\n')
            fd.write('\n')

        fd.write('::LRMSTYPE::\n')
        fd.write(lrms_type + '\n')
        fd.write('\n')

        fd.write('::LRMSDELAYCOMMAND::\n')
        if form.has_key('execution_delay_command'):
            fd.write(form['execution_delay_command'].value + '\n')
        fd.write('\n')

        fd.write('::LRMSSUBMITCOMMAND::\n')
        if form.has_key('submit_job_command'):
            fd.write(form['submit_job_command'].value + '\n')
        fd.write('\n')

        fd.write('::LRMSREMOVECOMMAND::\n')
        if form.has_key('remove_job_command'):
            fd.write(form['remove_job_command'].value + '\n')
        fd.write('\n')

        fd.write('::LRMSDONECOMMAND::\n')
        if form.has_key('query_done_command'):
            fd.write(form['query_done_command'].value + '\n')

        for execution_node in execution_nodes:
            execution_dir = ''
            start_command = ''
            status_command = ''
            stop_command = ''
            clean_command = ''
            vgrid = ''

            if form.has_key('hosturl') and form.has_key('hostidentifier'
                    ) and form.has_key('mig_home'):
                execution_dir = form['mig_home'].value + '/MiG'\
                     + '/mig_exe/' + form['hosturl'].value + '.'\
                     + form['hostidentifier'].value + '/'\
                     + execution_node + '/'

            # In the execution leader model all executors share a working dir

            if execution_leader:

                # replace exe dir name with "all" but keep trailing slash

                execution_dir = \
                    os.path.join(os.path.dirname(execution_dir.rstrip(os.sep)),
                                 'all' + os.sep)
                if execution_node == 'execution-leader':
                    script_prefix = 'leader'
                else:
                    script_prefix = 'dummy'
            else:
                script_prefix = 'master'

            fd.write('\n')
            fd.write('::EXECONFIG::\n')
            fd.write('name=%s\n' % execution_node)
            fd.write('nodecount=')
            if form.has_key('nodecount'):
                fd.write(form['nodecount'].value)
            else:
                fd.write('1')
            fd.write('\n')

            fd.write('cputime=')
            if form.has_key('cputime'):
                fd.write(form['cputime'].value)
            else:
                fd.write('3600')
            fd.write('\n')

            fd.write('execution_precondition=')
            if form.has_key('execution_precondition'):
                fd.write("'" + form['execution_precondition'].value
                          + "'")
            fd.write('\n')

            fd.write('prepend_execute=')
            if form.has_key('prepend_execute'):
                fd.write('"' + form['prepend_execute'].value + '"')
            fd.write('\n')

            fd.write('exehostlog=')
            fd.write(execution_dir + 'exehostlog\n')

            fd.write('joblog=')
            fd.write(execution_dir + 'joblog\n')

            fd.write('execution_user=')
            if form.has_key('mig_user'):
                fd.write(form['mig_user'].value)
            fd.write('\n')

            fd.write('execution_node=%s\n' % execution_node)
            fd.write('execution_dir=%s\n' % execution_dir)

            fd.write('start_command=')
            if form.has_key('execute_command'):
                if 'default' == form['execute_command'].value.strip():
                    fd.write(get_default_execute_command(execution_dir,
                             execution_node))
                elif 'local' == form['execute_command'].value.strip():
                    fd.write(get_local_execute_command(execution_dir,
                             execution_node, script_prefix))
                else:
                    fd.write(form['execute_command'].value)
            fd.write('\n')

            fd.write('status_command=')
            if form.has_key('status_command'):
                if 'default' == form['status_command'].value.strip():
                    fd.write(get_default_status_command(execution_dir,
                             execution_node))
                elif 'local' == form['status_command'].value.strip():
                    fd.write(get_local_status_command(execution_dir,
                             execution_node, script_prefix))
                else:
                    fd.write(form['status_command'].value)
            fd.write('\n')

            fd.write('stop_command=')
            if form.has_key('stop_command'):
                if 'default' == form['stop_command'].value.strip():
                    fd.write(get_default_stop_command(execution_dir,
                             execution_node))
                elif 'local' == form['stop_command'].value.strip():
                    fd.write(get_local_stop_command(execution_dir,
                             execution_node, script_prefix))
                else:
                    fd.write(form['stop_command'].value)
            fd.write('\n')

            fd.write('clean_command=')
            if form.has_key('clean_command'):
                if 'default' == form['clean_command'].value.strip():
                    fd.write(get_default_clean_command(execution_dir,
                             execution_node))
                elif 'local' == form['clean_command'].value.strip():
                    fd.write(get_local_clean_command(execution_dir,
                             execution_node, script_prefix))
                else:
                    fd.write(form['clean_command'].value)
            fd.write('\n')

            fd.write('continuous=')
            if form.has_key('continuous'):
                fd.write(form['continuous'].value)
            fd.write('\n')

            fd.write('shared_fs=')
            if form.has_key('shared_fs'):
                fd.write(form['shared_fs'].value)
            fd.write('\n')

            if form.has_key('vgrid'):
                vgrid = ', '.join(form.getlist('vgrid'))
            else:
                vgrid = default_vgrid
            fd.write('vgrid=%s\n' % vgrid)

        fd.close()
    except Exception, err:

        o.out('File: ' + conf_file + ' was not written! ' + str(err))
        o.reply_and_exit(o.ERROR)

    if not form.has_key('new_resource'):
        (status, msg) = confparser.run(pending_file, resource_id)
        if status:
            logger.info(msg)
            try:
                pass
                os.rename(pending_file, conf_file)
            except Exception, exc:
                o.out('Accepted config, but failed to save it! Failed:'
                       + str(exc))
                o.reply_and_exit(o.ERROR)
        else:
            o.out(msg)

            # o.out(open(pending_file, "r").readlines())

            o.reply_and_exit(o.CLIENT_ERROR)
    elif form.has_key('new_resource'):

        (status, msg) = send_resource_create_request_mail(client_id,
                form['hosturl'].value, pending_file, logger,
                configuration)
        logger.info(msg)
        if not status:
            o.client("<BR>Failed to send an email to the MiG server administrator(s), your configuration was saved on the server in:<BR><BR> '"
                      + conf_file
                      + "'<BR><BR>Please contact the MiG server administrator(s) (%s)."
                      % admin_email)
            o.reply_and_exit(o.CLIENT_ERROR)

if form.has_key('Ok'):
    if form.has_key('new_resource'):
        print get_cgi_html_header('MiG Resource creation confirmation',
                                  'MiG resource creation confirmation.')

        public_key_file_content = ''
        try:
            key_fh = open(configuration.public_key_file, 'r')
            public_key_file_content = key_fh.read()
            key_fh.close()

            # Avoid line breaks in displayed key

            public_key_info = \
                'The public key you must add:<br>***BEGIN KEY***<BR>%s<BR>***END KEY***<BR><BR>'\
                 % public_key_file_content.replace(' ', '&nbsp;')
        except:
            public_key_file_content = None
            public_key_info = \
                '<BR>Please request an SSH public key from the MiG administrator(s) (%s)<BR><BR>'\
                 % admin_email

        print "Your creation request of the resource: <B>'"\
             + form['hosturl'].value\
             + """'</B>
        has been sent to the MiG server administration and will be processed as soon as possible.
        <hr>Until you get a confirmation from a MiG administrator, please make sure the MiG server 
        can SSH to your resource without a passphrase. The MiG server's public key should be in the
        .ssh/authorized_keys in the home directory of the mig user on the resource frontend. %s
        <br>
        <a href='resadmin.py'>View existing resources</a>
        </body>
        </html>
        """\
             % public_key_info
    else:
        print "<HTML><SCRIPT>this.document.location.href='./resadmin.py?output_format=html#%s.%s';</SCRIPT></HTML>"\
             % (form['hosturl'].value, form['hostidentifier'].value)
else:

    # initialize form values

    runtimeenvironment = ['' for i in range(RUNTIMEENVIRONMENT_FIELDS)]
    saved_re_values = []
    runtime_env_fields = RUNTIMEENVIRONMENT_FIELDS
    vgrid_fields = VGRID_FIELDS
    vgrid_list = ['' for i in range(VGRID_FIELDS)]

    if form.has_key('hosturl'):
        hosturl = form['hosturl'].value
    else:
        hosturl = ''

    if form.has_key('hostidentifier'):
        hostidentifier = form['hostidentifier'].value
    else:
        hostidentifier = '$HOSTIDENTIFIER'

    mig_user = 'mig'
    mig_home = '/home/mig'
    hostkey = ''
    hostip = ''
    publicname = ''
    sshport = '22'
    sshmultiplex = ''
    scriptlanguage = '0'
    jobtype = '0'
    cputime = '3600'
    memory = '512'
    disk = '10'
    nodecount = '1'
    cpucount = '1'
    architecture = ''
    frontend_node = ''
    max_download_bandwidth = '0'
    max_upload_bandwidth = '0'
    lrms_type = ''
    execution_delay_command = ''
    submit_job_command = ''
    remove_job_command = ''
    query_done_command = ''
    execution_nodes = ''
    execution_precondition = ' '
    prepend_execute = 'nice -19'
    execute_command = 'default'
    status_command = 'default'
    stop_command = 'default'
    clean_command = 'default'
    continuous = 'True'
    shared_fs = 'True'

    if os.path.exists(conf_file):
        (status, msg, conf_dict) = \
            confparser.get_resource_config_dict(conf_file)

        if not status:
            o.out('Failure: Invalid resource configuration format detected in config file.'
                  , conf_file)
            o.reply_and_exit(o.ERROR)

        if status:
            mig_user = str(conf_dict['MIGUSER'])

            if conf_dict['RESOURCEHOME'].find('/MiG/') != -1:
                mig_home = str((conf_dict['RESOURCEHOME'
                               ])[0:str(conf_dict['RESOURCEHOME'
                               ]).index('/MiG/')])
            else:
                mig_home = '/home/' + mig_user

            hosturl = str(conf_dict['HOSTURL'])
            hostidentifier = str(conf_dict['HOSTIDENTIFIER'])

            if int(hostidentifier) != int(form['hostidentifier'].value):
                o.out("Failure: ::HOSTIDENTIFIER:: in file '"
                       + conf_file
                       + "' does'nt match hostidentifier provided: '"
                       + str(form['hostidentifier'].value) + "'")
                o.reply_and_exit(o.ERROR)

            scriptlanguage = str(conf_dict['SCRIPTLANGUAGE'])
            jobtype = str(conf_dict['JOBTYPE'])
            memory = str(conf_dict['MEMORY'])
            disk = str(conf_dict['DISK'])
            cpucount = str(conf_dict['CPUCOUNT'])
            architecture = str(conf_dict['ARCHITECTURE'])

            i = 0
            while i < RUNTIMEENVIRONMENT_FIELDS and i\
                 < len(conf_dict['RUNTIMEENVIRONMENT']):
                runtimeenvironment[i] += \
                    str(conf_dict['RUNTIMEENVIRONMENT'][i][0])
                saved_re_values.append(conf_dict['RUNTIMEENVIRONMENT'
                        ][i][1])
                i += 1

            while i < len(conf_dict['RUNTIMEENVIRONMENT']):
                runtimeenvironment.append(str(conf_dict['RUNTIMEENVIRONMENT'
                        ][i][0]))
                saved_re_values.append(conf_dict['RUNTIMEENVIRONMENT'
                        ][i][1])
                i += 1

            # Leave empty space for additional REs and update field counter

            if i >= RUNTIMEENVIRONMENT_FIELDS:
                runtimeenvironment.append('')
                saved_re_values.append([])
                runtime_env_fields = i + 1
            else:
                runtime_env_fields = RUNTIMEENVIRONMENT_FIELDS

            ip_start_index = -1
            hostkey_start_index = -1

            if conf_dict['HOSTKEY'].find(',') != -1:
                ip_start_index = conf_dict['HOSTKEY'].index(',')

            if conf_dict['HOSTKEY'].find('ssh-rsa ') != -1:
                hostkey_start_index = conf_dict['HOSTKEY'
                        ].index('ssh-rsa ')

            if ip_start_index != -1:
                if hostkey_start_index == -1:
                    hostip = str((conf_dict['HOSTKEY'])[ip_start_index
                                  + 1:])
                else:
                    hostip = str((conf_dict['HOSTKEY'])[ip_start_index
                                  + 1:hostkey_start_index - 1])

            if conf_dict.has_key('PUBLICNAME'):
                publicname = str(conf_dict['PUBLICNAME'])

            if conf_dict.has_key('SSHPORT'):
                sshport = str(conf_dict['SSHPORT'])

            if conf_dict.has_key('SSHMULTIPLEX'):
                sshmultiplex = str(conf_dict['SSHMULTIPLEX'])

            if hostkey_start_index != -1:
                hostkey = str((conf_dict['HOSTKEY'])[hostkey_start_index
                               + 8:])

            frontend_node = str(conf_dict['FRONTENDNODE'])

            if conf_dict.has_key('MAXDOWNLOADBANDWIDTH'):
                max_download_bandwidth = \
                    str(conf_dict['MAXDOWNLOADBANDWIDTH'])

            if conf_dict.has_key('MAXUPLOADBANDWIDTH'):
                max_upload_bandwidth = \
                    str(conf_dict['MAXUPLOADBANDWIDTH'])

            if conf_dict.has_key('LRMSTYPE'):
                lrms_type = str(conf_dict['LRMSTYPE'])
            else:
                lrms_type = 'Native'

            if conf_dict.has_key('LRMSDELAYCOMMAND'):
                execution_delay_command = \
                    str(conf_dict['LRMSDELAYCOMMAND'])

            if conf_dict.has_key('LRMSSUBMITCOMMAND'):
                submit_job_command = str(conf_dict['LRMSSUBMITCOMMAND'])

            if conf_dict.has_key('LRMSREMOVECOMMAND'):
                remove_job_command = str(conf_dict['LRMSREMOVECOMMAND'])

            if conf_dict.has_key('LRMSDONECOMMAND'):
                query_done_command = str(conf_dict['LRMSDONECOMMAND'])

            nodecount = str(conf_dict['EXECONFIG'][0]['nodecount'])
            cputime = str(conf_dict['EXECONFIG'][0]['cputime'])
            if conf_dict['EXECONFIG'
                         ][0].has_key('execution_precondition'):
                execution_precondition = str(conf_dict['EXECONFIG'
                        ][0]['execution_precondition']).strip("'")
            prepend_execute = str(conf_dict['EXECONFIG'
                                  ][0]['prepend_execute']).strip('"')

            execution_nodes = \
                generate_execution_node_string(conf_dict['EXECONFIG'])

            execute_command = str(conf_dict['EXECONFIG'
                                  ][0]['start_command'])
            default_execute_command = \
                get_default_execute_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if execute_command.strip().replace('\\', '')\
                 == default_execute_command.strip().replace('\\', ''):
                execute_command = 'default'
            local_execute_command = \
                get_local_execute_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if execute_command.strip().replace('\\', '')\
                 == local_execute_command.strip().replace('\\', ''):
                execute_command = 'local'
            local_leader_execute_command = \
                get_local_execute_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'leader')
            if execute_command.strip().replace('\\', '')\
                 == local_leader_execute_command.strip().replace('\\',
                    ''):
                execute_command = 'local'
            local_dummy_execute_command = \
                get_local_execute_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'dummy')
            if execute_command.strip().replace('\\', '')\
                 == local_dummy_execute_command.strip().replace('\\', ''
                    ):
                execute_command = 'local'

            status_command = str(conf_dict['EXECONFIG'
                                 ][0]['status_command'])
            default_status_command = \
                get_default_status_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if status_command.strip().replace('\\', '')\
                 == default_status_command.strip().replace('\\', ''):
                status_command = 'default'
            local_status_command = \
                get_local_status_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if status_command.strip().replace('\\', '')\
                 == local_status_command.strip().replace('\\', ''):
                status_command = 'local'
            local_leader_status_command = \
                get_local_status_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'leader')
            if status_command.strip().replace('\\', '')\
                 == local_leader_status_command.strip().replace('\\', ''
                    ):
                status_command = 'local'
            local_dummy_status_command = \
                get_local_status_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'dummy')
            if status_command.strip().replace('\\', '')\
                 == local_dummy_status_command.strip().replace('\\', ''
                    ):
                status_command = 'local'

            stop_command = str(conf_dict['EXECONFIG'][0]['stop_command'
                               ])
            default_stop_command = \
                get_default_stop_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if stop_command.strip().replace('\\', '')\
                 == default_stop_command.strip().replace('\\', ''):
                stop_command = 'default'
            local_stop_command = \
                get_local_stop_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if stop_command.strip().replace('\\', '')\
                 == local_stop_command.strip().replace('\\', ''):
                stop_command = 'local'
            local_leader_stop_command = \
                get_local_stop_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'leader')
            if stop_command.strip().replace('\\', '')\
                 == local_leader_stop_command.strip().replace('\\', ''):
                stop_command = 'local'
            local_dummy_stop_command = \
                get_local_stop_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'dummy')
            if stop_command.strip().replace('\\', '')\
                 == local_dummy_stop_command.strip().replace('\\', ''):
                stop_command = 'local'

            clean_command = str(conf_dict['EXECONFIG'
                                ][0]['clean_command'])
            default_clean_command = \
                get_default_clean_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if clean_command.strip().replace('\\', '')\
                 == default_clean_command.strip().replace('\\', ''):
                clean_command = 'default'
            local_clean_command = \
                get_local_clean_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']))
            if clean_command.strip().replace('\\', '')\
                 == local_clean_command.strip().replace('\\', ''):
                clean_command = 'local'
            local_leader_clean_command = \
                get_local_clean_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'leader')
            if clean_command.strip().replace('\\', '')\
                 == local_leader_clean_command.strip().replace('\\', ''
                    ):
                clean_command = 'local'
            local_dummy_clean_command = \
                get_local_clean_command(str(conf_dict['EXECONFIG'
                    ][0]['execution_dir']), str(conf_dict['EXECONFIG'
                    ][0]['name']), 'dummy')
            if clean_command.strip().replace('\\', '')\
                 == local_dummy_clean_command.strip().replace('\\', ''):
                clean_command = 'local'

            # Handle old typo gracefully

            if conf_dict['EXECONFIG'][0].has_key('continuous'):
                continuous = str(conf_dict['EXECONFIG'][0]['continuous'
                                 ])
            else:
                continuous = str(conf_dict['EXECONFIG'][0]['continious'
                                 ])

            shared_fs = str(conf_dict['EXECONFIG'][0]['shared_fs'])

            # Read in list value

            vgrid_list = conf_dict['EXECONFIG'][0]['vgrid']
            parts = len(vgrid_list)
            if parts < vgrid_fields:

                # Append empty fields if list is shorter than fields

                vgrid_list += ['' for i in range(vgrid_fields - parts)]
            elif parts > vgrid_fields:
                vgrid_fields = parts
            while vgrid_fields - parts < 3:

                # Make space for some extra fields

                vgrid_fields += 1
                vgrid_list.append('')
    print get_cgi_html_header('MiG Resource administration', '')
    print '<h1>MiG resource editor</h1>'
    print 'Please fill in or edit the fields below to fit your MiG resource reservation. Most fields will work with their default values. So if you are still in doubt after reading the help description, you can likely just leave the field alone.'
    print """<form name="resource_edit" method='post' action='./resource_edit.py' onSubmit='return submit_check(this);'>"""
    if form.has_key('new_resource'):
        print """            <input type="hidden" name="new_resource" value="true">"""
    else:
        print """            <input type="hidden" name="apply_changes" value="true">"""

    print """                <BR>
                             <B>Host FQDN:</B>&nbsp;<A HREF="./resedithelp.py#hosturl">help</A><BR>"""
    if form.has_key('new_resource'):
        print """<input type="text" name="hosturl" size="30" value='"""\
             + hosturl + """'>"""
    else:
        print hosturl
        print """<input type="hidden" name="hosturl" size="30" value='"""\
             + hosturl\
             + """'>
                 <BR><BR>
                 <B>Host identifier:</B>&nbsp;<A HREF="./resedithelp.py#hostidentifier">help</A><BR>"""
        print hostidentifier

    print """                   <input type="hidden" name="hostidentifier" size="30" value='"""\
         + hostidentifier\
         + """'> 
                                <BR><BR>
                                <B>Public name:</B>&nbsp<A HREF="./resedithelp.py#publicname">help</A>
                                <BR>
                                <input type="text" name="publicname" size="30" value='"""\
         + html_encode(publicname)\
         + """'>
                                <BR><BR>
                                <B>MiG user:</B>&nbsp;<A HREF="./resedithelp.py#miguser">help</A>
                                <BR>
                                <input type="text" name="mig_user" size="30" value='"""\
         + html_encode(mig_user)\
         + """'>
                                <BR><BR>
                                <B>MiG home:</B>&nbsp;<A HREF="./resedithelp.py#resourcehome">help</A>
                                <BR>                            
                                <input type="text" name="mig_home" size="30" value='"""\
         + html_encode(mig_home)\
         + """'> 
                                <BR><BR>
                                <B>Host IP:</B>&nbsp;<A HREF="./resedithelp.py#hostip">help</A>
                                <BR>
                                <input type="text" name="hostip" size="30" value='"""\
         + html_encode(hostip)\
         + """'>
                                <BR><BR>
                                <B>Ssh port:</B>&nbsp<A HREF="./resedithelp.py#sshport">help</A>
                                <BR>
                                <input type="text" name="sshport" size="30" value='"""\
         + html_encode(sshport)\
         + """'>
                                <BR><BR>
                                <B>Ssh multiplex:</B>&nbsp<A HREF="./resedithelp.py#sshmultiplex">help</A>
                                <BR>
                                <input type="text" name="sshmultiplex" size="30" value='"""\
         + html_encode(sshmultiplex)\
         + """'>
                                <BR><BR>        
                                <B>Host key:</B>&nbsp;<A HREF="./resedithelp.py#hostkey">help</A>
                                <BR>
                                <input type="text" name="hostkey" size="260" value='"""\
         + html_encode(hostkey)\
         + """'>
                                <BR><BR>        
                                <B>Frontend node:</B>&nbsp;<A HREF="./resedithelp.py#frontendnode">help</A>
                                <BR>
                                <input type="text" name="frontend_node" size="30" value='"""\
         + html_encode(frontend_node)\
         + """'>
                                <BR><BR>        
                                <B>Max download bandwidth:</B>&nbsp;<A HREF="./resedithelp.py#maxdownloadbandwidth">help</A>
                                <BR>
                                <input type="text" name="max_download_bandwidth" size="30" value='"""\
         + html_encode(max_download_bandwidth)\
         + """'>
                                <BR><BR>
                                <B>Max upload bandwidth:</B>&nbsp;<A HREF="./resedithelp.py#maxuploadbandwidth">help</A>
                                <BR>
                                <input type="text" name="max_upload_bandwidth" size="30" value='"""\
         + html_encode(max_upload_bandwidth)\
         + """'>
                                <BR><BR>        
                                <B>LRMS type:</B>&nbsp;<A HREF="./resedithelp.py#lrmstype">help</A>
                                <BR>
                                <select name="lrms_type">"""

    for lrms in [
        'Native',
        'Native-execution-leader',
        'Batch',
        'Batch-execution-leader',
        'PBS',
        'PBS-execution-leader',
        'SGE',
        'SGE-execution-leader',
        ]:
        if lrms == lrms_type:

            # this is the lrms type currently used in res.conf, select as default

            selected = 'selected'
        else:
            selected = ''

        # create list entry

        print """<OPTION """ + selected + """ value=""" + lrms + """>"""\
             + lrms + """</OPTION>"""

    print """           </select>       
                                <BR><BR>        
                                <B>LRMS execution delay command:</B>&nbsp;<A HREF="./resedithelp.py#lrmsdelaycommand">help</A>
                                <BR>
                                <input type="text" name="execution_delay_command" size="50" value='"""\
         + html_encode(execution_delay_command)\
         + """'>
                                <BR><BR>        
                                <B>LRMS submit job command:</B>&nbsp;<A HREF="./resedithelp.py#lrmssubmitcommand">help</A>
                                <BR>
                                <input type="text" name="submit_job_command" size="50" value='"""\
         + html_encode(submit_job_command)\
         + """'>
                                <BR><BR>        
                                <B>LRMS remove job command:</B>&nbsp;<A HREF="./resedithelp.py#lrmsremovecommand">help</A>
                                <BR>
                                <input type="text" name="remove_job_command" size="50" value='"""\
         + html_encode(remove_job_command)\
         + """'>
                                <BR><BR>        
                                <B>LRMS query done command:</B>&nbsp;<A HREF="./resedithelp.py#lrmsdonecommand">help</A>
                                <BR>
                                <input type="text" name="query_done_command" size="50" value='"""\
         + html_encode(query_done_command)\
         + """'>
                                <BR><BR>
                                <B>Execution node(s):</B>&nbsp;<A HREF="./resedithelp.py#executionnodes">help</A>
                                <BR>
                                <input type="text" name="execution_nodes" size="30" value='"""\
         + html_encode(execution_nodes)\
         + """'>
                                <BR><BR>
                                <B>Node count:</B>&nbsp;<A HREF="./resedithelp.py#nodecount">help</A>
                                <BR>
                                <input type="text" name="nodecount" size="30" value='"""\
         + html_encode(nodecount)\
         + """'>
                                <BR><BR>
                                <B>CPU count:</B>&nbsp;<A HREF="./resedithelp.py#cpucount">help</A>
                                <BR>
                                <input type="text" name="cpucount" size="30" value='"""\
         + html_encode(cpucount)\
         + """'>
                                <BR><BR>
                                <B>CPU time:</B>&nbsp<A HREF="./resedithelp.py#cputime">help</A>
                                <BR>
                                <input type="text" name="cputime" size="30" value='"""\
         + html_encode(cputime)\
         + """'>
                                <BR><BR>
                                <B>Memory (MB):</B>&nbsp<A HREF="./resedithelp.py#memory">help</A>
                                <BR>
                                <input type="text" name="memory" size="30" value='"""\
         + html_encode(memory)\
         + """'>
                                <BR><BR>
                                <B>Disk (GB):</B>&nbsp<A HREF="./resedithelp.py#disk">help</A>
                                <BR>
                                <input type="text" name="disk" size="10" value='"""\
         + html_encode(disk)\
         + """'> 
                                <BR><BR>
                                <B>Architecture:</B>&nbsp<A HREF="./resedithelp.py#architecture">help</A>
                                <BR>
                                <select name="architecture">"""

    for arch in configuration.architectures:
        if arch == architecture:

            # this is the arch currently used in res.conf, select as default

            selected = 'selected'
        else:
            selected = ''

        # create list entry

        print """<OPTION """ + selected + """ value=""" + arch + """>"""\
             + arch + """</OPTION>"""

    print """           </select>       
                                
                                <BR><BR>
                                <B>Script language:</B>&nbsp<A HREF="./resedithelp.py#scriptlanguage">help</A>
                                <BR>
                                <select name="scriptlanguage">"""

    for lang in configuration.scriptlanguages:
        if lang == scriptlanguage:

            # this is the scriptlanguage currently used in res.conf, select as default

            selected = 'selected'
        else:
            selected = ''

        # create list entry

        print """<OPTION """ + selected + """ value=""" + lang + """>"""\
             + lang + """</OPTION>"""

    print """                   </select>
                                <BR><BR>
                                <B>Job type:</B>&nbsp<A HREF="./resedithelp.py#jobtype">help</A>
                                <BR>
                                <select name="jobtype">"""

    for kind in configuration.jobtypes:
        if kind == jobtype:

            # this is the jobtype currently used in res.conf, select as default

            selected = 'selected'
        else:
            selected = ''

        # create list entry

        print """<OPTION """ + selected + """ value=""" + kind + """>"""\
             + kind + """</OPTION>"""

    print """                   </select>
                                <BR><BR>
                                <B>Runtime environments:</B>&nbsp<A HREF="./resedithelp.py#runtimeenvironment">help</A>
                                                
                                <input type="hidden" name="runtime_env_fields" size="30" value='"""\
         + str(runtime_env_fields) + """'>"""

    (status, re_list) = list_runtime_environments(configuration)

    # (status, msg, re_list) = get_active_re_list(configuration.RE_files_dir)

    for i in range(runtime_env_fields):
        if '' != runtimeenvironment[i] and runtimeenvironment[i]\
             not in re_list:
            re_list.append(runtimeenvironment[i].upper())

    re_list.sort()

    for i in range(runtime_env_fields):
        print """<BR><select name='runtimeenvironment""" + str(i)\
             + """'>"""
        print """<option value=''></OPTION>"""

        for re in re_list:
            selected = ''
            if re == runtimeenvironment[i].upper():
                selected = 'selected'

            print """<option """ + selected + """ value='""" + re\
                 + """'>""" + re + """</OPTION>"""

        print """</select><BR>"""

        # Create a free text area for input of required RE env vars

        values = ''
        if runtimeenvironment[i]:
            for (name, value) in saved_re_values[i]:
                values += '%s=%s\n' % (name, value)

        print 'Variable settings (lines of NAME=VALUE)<br>'
        print """<textarea cols='30' rows='3' name='re_values%d'>%s</textarea><BR>"""\
             % (i, values.strip())

        # print """<input type="text" name='runtimeenvironment""" + str(i) + """' size="30" value='""" + html_encode(runtimeenvironment[i]) + """'><BR>"""

    print """                   <BR><BR>
                                <B>Execution precondition:</B>&nbsp<A HREF="./resedithelp.py#execution_precondition">help</A>
                                <BR>
                                <input type="text" name="execution_precondition" size="30" value='"""\
         + html_encode(execution_precondition)\
         + """'
                                <BR><BR>
                                <B>Prepend execute:</B>&nbsp<A HREF="./resedithelp.py#prepend_execute">help</A>
                                <BR>
                                <input type="text" name="prepend_execute" size="30" value='"""\
         + html_encode(prepend_execute)\
         + """'>
                                <BR><BR>
                                <B>Execute command:</B>&nbsp<A HREF="./resedithelp.py#start_command">help</A>
                                <BR>
                                <input type="text" name="execute_command" size="30" value='"""\
         + html_encode(execute_command)\
         + """'>
                                <BR><BR>
                                <B>Status command:</B>&nbsp<A HREF="./resedithelp.py#status_command">help</A>
                                <BR>
                                <input type="text" name="status_command" size="30" value='"""\
         + html_encode(status_command)\
         + """'>
                                <BR><BR>
                                <B>Stop command:</B>&nbsp<A HREF="./resedithelp.py#stop_command">help</A>
                                <BR>
                                <input type="text" name="stop_command" size="30" value='"""\
         + html_encode(stop_command)\
         + """'
                                <BR><BR>
                                <B>Clean command:</B>&nbsp<A HREF="./resedithelp.py#clean_command">help</A>
                                <BR>
                                <input type="text" name="clean_command" size="30" value='"""\
         + html_encode(clean_command)\
         + """'
                                <BR><BR>
                                <B>Job mode:</B>&nbsp<A HREF="./resedithelp.py#continuous">help</A>
                                <BR>
                                <select name="continuous">"""
    selectedtrue = ''
    selectedfalse = ''
    if continuous == 'True':
        selectedtrue = 'selected'
    else:
        selectedfalse = 'selected'

    print """<OPTION """ + selectedtrue\
         + """ value="True">Continuous</OPTION>"""
    print """<OPTION """ + selectedfalse\
         + """ value="False">Single</OPTION>"""

    print """                   </select>
                                <BR><BR>
                                <B>Shared filesystem:</B>&nbsp<A HREF="./resedithelp.py#shared_fs">help</A>
                                <BR>
                                <select name="shared_fs">"""
    selectedtrue = ''
    selectedfalse = ''
    if shared_fs == 'True':
        selectedtrue = 'selected'
    else:
        selectedfalse = 'selected'

    print """<OPTION """ + selectedtrue\
         + """ value="True">Yes</OPTION>"""
    print """<OPTION """ + selectedfalse\
         + """ value="False">No</OPTION>"""

    print """                   </select>
                                <br><br>
                                <b>VGrid:</b>&nbsp<a href="./resedithelp.py#vgrid">help</a>
                                <br>"""
    print """                   <input type="hidden" name="vgrid_fields" size="30" value='"""\
         + str(vgrid_fields) + """'>"""

    vg_list = user_allowed_vgrids(configuration, client_id)

    for i in range(vgrid_fields):
        if vgrid_list[i] and vgrid_list[i] not in vg_list:
            vg_list.append(vgrid_list[i])
    vg_list.sort()

    for i in range(vgrid_fields):
        print """<BR><select name='vgrid'>"""
        print """<option value=''></OPTION>"""

        for vg in vg_list:
            selected = ''
            if vg == vgrid_list[i]:
                selected = 'selected'

            print """<option """ + selected + """ value='""" + vg\
                 + """'>""" + vg + """</OPTION>"""

        print """</select>"""
    print """                   <br><br>
                                <hr>
                                <input type="submit" name="Ok" value="    Ok    ">&nbsp;&nbsp;"""

    if not form.has_key('new_resource'):
        print """               <input type="submit" name="Apply" value="Apply ">&nbsp;&nbsp;"""
    print """                   <input type="submit" name="Cancel" value="Cancel" onClick="return cancel_submit()">
                                </form>
                    </body>

                    <SCRIPT>
                        function check_filled(form)
                        {
                           status = true;
                           alert_str = "The following fields must be filled:\\n";
                           if (form.mig_user.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Mig user'";
                           }
                           if (form.mig_home.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Mig home'";
                           }

                           if (form.hosturl.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Host FQDN'";
                           }
                           if (form.hostip.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Host IP'";
                           }
                           if (form.sshport.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Sshport'";
                           }
                           if (form.hostkey.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Host key'";
                           }
                           if (form.frontend_node.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Frontend node'";
                           }
                           if (form.execution_nodes.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Execution node(s)'";
                           }
                           if (form.cpucount.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'CPU count'";
                           }
                           if (form.cputime.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'CPU time'";
                           }
                           if (form.memory.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Memory'";
                           }
                           if (form.disk.value == '')
                           {
                              status = false;
                              alert_str = alert_str +  "\\n'Disk'";
                           }
                           if (status == false)
                           {
                              alert(alert_str);
                              return false;
                           }
                           else
                           {
                              return true;
                           }
                        }
                        
                        function check_numeric(check_str)
                        {
                           check_str = check_str.replace(/^\s*/, '');
                           check_str = check_str.replace(/\s*$/, '');
                           match = /^[0-9]*$/;
                        
                           if(check_str.search(match) == -1)
                           {
                              return false;
                           }
                           else
                           {
                              return true;
                           }
                        }
                        
                        function check_numeric_fields(form)
                        {
                           status = true;
                           alert_str = "The following fields must be numeric:\\n"
                           if (!check_numeric(form.sshport.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Sshport'";
                           }
                           if (!check_numeric(form.sshmultiplex.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Ssh multiplex'";
                           }
                           if (!check_numeric(form.max_download_bandwidth.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Max download bandwidth'";
                           }
                           if (!check_numeric(form.max_upload_bandwidth.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Max upload bandwidth'";
                           }
                           if (!check_numeric(form.cpucount.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'CPU count'";
                           }
                           if (!check_numeric(form.cputime.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'CPU time'";
                           }
                           if (!check_numeric(form.memory.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Memory'";
                           }
                           if (!check_numeric(form.disk.value))
                           {
                              status = false;
                              alert_str = alert_str + "\\n'Disk'";
                           }
                           if (status == false)
                           {
                              alert(alert_str);
                           }
                           return status;
                        }
                        
                        function submit_check(form)
                        {
                            status = check_filled(form);
                            if (status == true)
                            {
                               status = check_numeric_fields(form);
                            }
                            return status;
                        }
                        function cancel_submit(obj)
                        {
                        """

                        # for debug
                        # this.document.location.href = "./resource_list.py";

    print """              this.document.location.href = "./resadmin.py?output_format=html#%s.%s";
                           return false;
                        }
                    </SCRIPT>
                    </html>
                    """\
         % (hosturl, hostidentifier)
