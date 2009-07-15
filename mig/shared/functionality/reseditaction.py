#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reseditaction - Resource editor action handler back end
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

# Martin Rehr martin@rehr.dk August 2005

"""Handle resource editor actions"""

import socket

from shared.conf import get_configuration_object
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.notification import send_resource_create_request_mail
from shared.resource import parse_resource_config, write_resource_config, \
     retrieve_execution_nodes, retrieve_storage_nodes
import shared.confparser as confparser
import shared.parser as parser
import shared.resconfkeywords as resconfkeywords
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    configuration = get_configuration_object()
    defaults = {'action': REJECT_UNSET, 'HOSTIP': ['']}
    for (key, spec) in resconfkeywords.get_resource_keywords(configuration).items():
        if spec['required']:
            defaults[key] = REJECT_UNSET
        else:
            defaults[key] = spec['Value']
    return ['html_form', defaults]

def merge_var_fields(user_args):
    """Merge the variable fields like runtimeenvironmentX and re_valuesX
    pairs into the final form suitable for input validation. Both fields
    should exist for all X in range(0, runtime_env_fields) .
    """
    re_list = []
    field_count = user_arguments_dict.get('runtime_env_fields', 0)
    for i in range(field_count):
        runtime_env = 'runtimeenvironment' + str(i)
        env_values = 're_values' + str(i)
        if user_args.has_key(runtime_env):
            re_list.append((user_args[runtime_env], user_args[env_values]))
        del user_arguments_dict[runtime_env]
        del user_arguments_dict[env_values]
    user_args['RUNTIMEENVIRONMENT'] = re_list
    execution_nodes = user_args.get('execution_nodes', [''])[-1]
    storage_nodes = user_args.get('storage_nodes', [''])[-1]
    exe_names = retrieve_execution_nodes(execution_nodes)
    store_names = retrieve_storage_nodes(storage_nodes)
    all_exes = []
    all_stores = []
    for name in exe_names:
        user_args['name'] = name
        user_args['execution_dir'] = '###fill later###'
        exe = {}
        for key in resconfkeywords.get_exenode_keywords().keys():
            exe[key] = user_args[key]
        all_exes.append(exe)
    for key in resconfkeywords.get_exenode_keywords().keys():
        del user_args[key]
    for name in store_names:
        user_args['name'] = name
        store = {}
        for key in resconfkeywords.get_storenode_keywords().keys():
            store[key] = user_args[key]
        all_stores.append(store)
    for key in resconfkeywords.get_storenode_keywords().keys():
        del user_args[key]
    return user_args

def prepare_conf(form):
    """Generate conf dictionary from user input"""
    if form.has_key('mig_home') and form.has_key('hosturl')\
         and form.has_key('hostidentifier'):
        form['RESOURCEHOME'] = os.path.join(form['MIGHOME'], 'MiG',
                                            'mig_frontend', 
                                            form['hosturl'] + '.'
                                            + form['hostidentifier'])
    
    exe_count = len(execution_nodes)
    if execution_leader:
        exe_count -= 1
    total_nodes = exe_count * int(form['all_exes']['nodecount'])
    form['NODECOUNT'] = total_nodes

    host_key = ''                      
    if form.has_key('hosturl') and form.has_key('hostip'):
        host_key = form['hosturl'] + ',' + form['hostip']
    if form.has_key('hostkey'):
        raw_key = form['hostkey'].strip()
        if not raw_key.startswith('ssh-rsa'):
            raw_key = 'ssh-rsa ' + raw_key
        host_key += ' ' + raw_key
    form['HOSTKEY'] = host_key

    form['FRONTENDLOG'] = os.path.join(form['RESOURCEHOME'], 'frontend.log')

    if form.has_key('max_download_bandwidth')\
         and form['max_download_bandwidth'] != '0':
        fd.write('::MAXDOWNLOADBANDWIDTH::\n')
        fd.write(form['max_download_bandwidth'] + '\n')
        fd.write('\n')

    if form.has_key('max_upload_bandwidth')\
         and form['max_upload_bandwidth'] != '0':
        fd.write('::MAXUPLOADBANDWIDTH::\n')
        fd.write(form['max_upload_bandwidth'] + '\n')
        fd.write('\n')

    fd.write('::LRMSTYPE::\n')
    fd.write(lrms_type + '\n')
    fd.write('\n')

    fd.write('::LRMSDELAYCOMMAND::\n')
    if form.has_key('execution_delay_command'):
        fd.write(form['execution_delay_command'] + '\n')
    fd.write('\n')

    fd.write('::LRMSSUBMITCOMMAND::\n')
    if form.has_key('submit_job_command'):
        fd.write(form['submit_job_command'] + '\n')
    fd.write('\n')

    fd.write('::LRMSREMOVECOMMAND::\n')
    if form.has_key('remove_job_command'):
        fd.write(form['remove_job_command'] + '\n')
    fd.write('\n')

    fd.write('::LRMSDONECOMMAND::\n')
    if form.has_key('query_done_command'):
        fd.write(form['query_done_command'] + '\n')

    for execution_node in execution_nodes:
        execution_dir = ''
        start_command = ''
        status_command = ''
        stop_command = ''
        clean_command = ''
        vgrid = ''

        if form.has_key('hosturl') and form.has_key('hostidentifier'
                ) and form.has_key('mig_home'):
            execution_dir = form['mig_home'] + '/MiG'\
                 + '/mig_exe/' + form['hosturl'] + '.'\
                 + form['hostidentifier'] + '/'\
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
            fd.write(form['nodecount'])
        else:
            fd.write('1')
        fd.write('\n')

        fd.write('cputime=')
        if form.has_key('cputime'):
            fd.write(form['cputime'])
        else:
            fd.write('3600')
        fd.write('\n')

        fd.write('execution_precondition=')
        if form.has_key('execution_precondition'):
            fd.write("'" + form['execution_precondition']
                      + "'")
        fd.write('\n')

        fd.write('prepend_execute=')
        if form.has_key('prepend_execute'):
            fd.write('"' + form['prepend_execute'] + '"')
        fd.write('\n')

        fd.write('exehostlog=')
        fd.write(execution_dir + 'exehostlog\n')

        fd.write('joblog=')
        fd.write(execution_dir + 'joblog\n')

        fd.write('execution_user=')
        if form.has_key('mig_user'):
            fd.write(form['mig_user'])
        fd.write('\n')

        fd.write('execution_node=%s\n' % execution_node)
        fd.write('execution_dir=%s\n' % execution_dir)

        fd.write('start_command=')
        if form.has_key('execute_command'):
            if 'default' == form['execute_command'].strip():
                fd.write(get_default_execute_command(execution_dir,
                         execution_node))
            elif 'local' == form['execute_command'].strip():
                fd.write(get_local_execute_command(execution_dir,
                         execution_node, script_prefix))
            else:
                fd.write(form['execute_command'])
        fd.write('\n')

        fd.write('status_command=')
        if form.has_key('status_command'):
            if 'default' == form['status_command'].strip():
                fd.write(get_default_status_command(execution_dir,
                         execution_node))
            elif 'local' == form['status_command'].strip():
                fd.write(get_local_status_command(execution_dir,
                         execution_node, script_prefix))
            else:
                fd.write(form['status_command'])
        fd.write('\n')

        fd.write('stop_command=')
        if form.has_key('stop_command'):
            if 'default' == form['stop_command'].strip():
                fd.write(get_default_stop_command(execution_dir,
                         execution_node))
            elif 'local' == form['stop_command'].strip():
                fd.write(get_local_stop_command(execution_dir,
                         execution_node, script_prefix))
            else:
                fd.write(form['stop_command'])
        fd.write('\n')

        fd.write('clean_command=')
        if form.has_key('clean_command'):
            if 'default' == form['clean_command'].strip():
                fd.write(get_default_clean_command(execution_dir,
                         execution_node))
            elif 'local' == form['clean_command'].strip():
                fd.write(get_local_clean_command(execution_dir,
                         execution_node, script_prefix))
            else:
                fd.write(form['clean_command'])
        fd.write('\n')

        fd.write('continuous=')
        if form.has_key('continuous'):
            fd.write(form['continuous'])
        fd.write('\n')

        fd.write('shared_fs=')
        if form.has_key('shared_fs'):
            fd.write(form['shared_fs'])
        fd.write('\n')

        if form.has_key('vgrid'):
            vgrid = ', '.join(form.getlist('vgrid'))
        else:
            vgrid = default_vgrid
        fd.write('vgrid=%s\n' % vgrid)

    fd.close()


def create_new_resource(configuration, user_vars):
    """Create resource configuration from request"""

    lrms_type = 'Native'
    execution_leader = False
    if form.has_key('lrms_type'):
        lrms_type = form['lrms_type']
        if -1 != lrms_type.find('-execution-leader'):
            execution_leader = True


    # Parse Execution nodes

    execution_nodes = []
    if form.has_key('execution_nodes'):
        execution_nodes = \
            retrieve_execution_nodes(form['execution_nodes'],
                execution_leader)

    if not execution_nodes:
        execution_nodes.append(form['frontend_node'])

    logger.info(client_id
                + ' is trying to create a new resource configuration for '
                + form['hosturl'])

    try:
        logger.info('write to file: %s' % pending_file)
        write_res_conf(configuration, user_vars, pending_file)
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
                form['hosturl'], pending_file, logger,
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
             + form['hosturl']\
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
             % (form['hosturl'], form['hostidentifier'])

def update_resource(user_vars):
    """Update existing resource configuration from request"""

    lrms_type = 'Native'
    execution_leader = False
    if form.has_key('lrms_type'):
        lrms_type = form['lrms_type']
        if -1 != lrms_type.find('-execution-leader'):
            execution_leader = True


    # Parse Execution nodes

    execution_nodes = []
    if form.has_key('execution_nodes'):
        execution_nodes = \
            retrieve_execution_nodes(form['execution_nodes'],
                execution_leader)

    if not execution_nodes:
        execution_nodes.append(form['frontend_node'])

    logger.info(client_id
                + ' is trying to update the configuration for '
                + form['hosturl'])

    if not os.path.isdir(os.path.dirname(pending_file)):
        try:
            os.makedirs(os.path.dirname(pending_file))
        except Exception, excep:
            o.out('Could not create directory to hold resource configuration!'
                  , excep)
            o.reply_and_exit(o.ERROR)

    try:
        logger.info('write to file: %s' % pending_file)
        write_res_conf(user_vars, pending_file)
    except Exception, err:
        o.out('File: ' + conf_file + ' was not written! ' + str(err))
        o.reply_and_exit(o.ERROR)


    (status, msg) = confparser.run(pending_file, resource_id)
    if not status:
        logger.error(msg)
        o.out('Accepted config, but failed to parse it! Failed:'
              + str(msg))
        o.reply_and_exit(o.ERROR)
        
    o.out(msg)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    defaults = signature()[1]

    # Some input variables like those for Runtimeenvironments are not on
    # a form suitable for input validation. Run a merge function first to
    # to transform them to a suitable form before validation.
    
    merge_var_fields(user_arguments_dict)
    
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    action = accepted['action'][-1]

    status = returnvalues.OK

    output_objects.append({'object_type': 'title', 'text': 'Resource edit actions'
                          })
    output_objects.append({'object_type': 'header', 'text': 'Resource edit actions'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Resource configuraton changes'})
    if 'new_resource' == action:
        output_objects.append({'object_type': 'text', 'text'
                               : 'Handling your resource creation request'
                               })
        write_pending_file(pending_path)
        create_new_resource(configuraton, user_arguments_dict, pending_path)
        

    elif 'apply_changes' == action:
        output_objects.append({'object_type': 'text', 'text'
                               : 'Handling your resource configuration updates'
                               })
    else:
        output_objects.append({'object_type': 'text', 'text'
                               : 'Unknown action request!'
                               })

    return (output_objects, status)
