#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource - resource configuration functions
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

"""Resource configuration functions"""

import os
import dircache
import re
import socket
try:
    from hashlib import md5 as hash_algo
except ImportError:
    from md5 import new as hash_algo

from shared.base import client_id_dir
from shared.confparser import get_resource_config_dict, run
from shared.defaults import exe_leader_name, keyword_auto
from shared.fileio import pickle, move
from shared.modified import mark_resource_modified, mark_vgrid_modified
from shared.resconfkeywords import get_resource_specs, get_exenode_specs, \
    get_storenode_specs, get_resource_keywords, get_exenode_keywords, \
    get_storenode_keywords
from shared.serial import load, dump
from shared.ssh import default_ssh_options


def get_regex_non_numeric():
    """Match everything except numbers"""
    return re.compile('[^0-9]*')


def anon_resource_id(res_id, keep_exe=True):
    """Generates an anonymous but (practically) unique resource ID for
    resource with provided unique res_id. The anonymous ID is just a md5
    hash of the res_id to keep ID relatively short.
    If keep_exe is set any '_exename' suffix is stripped before hashing
    and appended again afterwards.
    """
    res_part, exe_part = res_id, ''
    if keep_exe:
        parts = res_id.rsplit('_', 1) + ['']
        res_part, exe_part = parts[0], parts[1]
    anon_id = hash_algo(res_part).hexdigest()
    if exe_part:
        anon_id += "_%s" % exe_part
    return anon_id


def exclude_exe_leader(exe_nodes):
    """Remove any occurences of execution leader from the exe_nodes list of
    exe node names"""
    while exe_leader_name in exe_nodes:
        exe_nodes.remove(exe_leader_name)
    return exe_nodes


def include_exe_leader(exe_nodes):
    """Insert execution leader into the exe_nodes list of exe node names if
    not there already"""
    if not exe_leader_name in exe_nodes:
        exe_nodes.insert(0, exe_leader_name)
    return exe_nodes


def retrieve_execution_nodes(exe_nodes, prepend_leader=False):
    """Return an ordered list of exe nodes from the allowed range formats.
    Prepend execution leader node if prepend_leader is set.
    """

    execution_nodes = []
    regex_nonnumeric = get_regex_non_numeric()
    index = 0

    if prepend_leader:
        execution_nodes.append(exe_leader_name)

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


def retrieve_storage_nodes(store_nodes):
    """Return an ordered list of store nodes from the allowed range formats.
    """

    return retrieve_execution_nodes(store_nodes)


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
        exe_nodes = [exe for exe in exe_nodes if exe_leader_name
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


def generate_storage_node_string(store_nodes):
    """Create a node name string from list of store config dictionaries"""
    return generate_execution_node_string(store_nodes, False)


def local_exe_start_command(node_config, kind='master'):
    """Command to start exe on resource using local execution"""
    helper = {'kind': kind}
    helper.update(node_config)
    cmd = 'cd %(execution_dir)s && chmod 700 %(kind)s_node_script_%(name)s.sh '
    cmd += '&& nice ./%(kind)s_node_script_%(name)s.sh start'
    cmd = (cmd % helper)
    return cmd


# TODO: consider ssh ProxyForward -W %h:%p instead of nested ssh in default_X

def default_exe_start_command(node_config):
    """Command to start exe on resource using remote node execution"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['execution_user'],
                                      node_config['execution_node'],
                                      local_exe_start_command(node_config))


# TODO: switch master node resources to SCRIPT COMMAND form, too

def local_exe_status_command(node_config, kind='master', escape=False):
    """Command to query exe status on resource using local execution"""
    helper = {'pgid': '$mig_exe_pgid', 'kind': kind}
    helper.update(node_config)
    if 'master' != kind:
        cmd = 'cd %(execution_dir)s && '
        cmd += 'nice ./%(kind)s_node_script_%(name)s.sh status %(pgid)s'
    else:
        # we list process id + user for each process in the saved exe script
        # process group, then grep user to check if they run. Prevents most
        # false positives.
        cmd = r'ps -o pid= -o user= -g %(pgid)s | grep %(execution_user)s'
    cmd = (cmd % helper)
    return cmd


def default_exe_status_command(node_config):
    """Command to query exe status on resource using remote node execution"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['execution_user'],
                                      node_config['execution_node'],
                                      local_exe_status_command(node_config))


def local_exe_stop_command(node_config, kind='master'):
    """Command to start exe on resource using local execution"""
    helper = {'pgid': '$mig_exe_pgid', 'kind': kind}
    helper.update(node_config)
    if 'master' != kind:
        cmd = 'cd %(execution_dir)s && '
        cmd += 'nice ./%(kind)s_node_script_%(name)s.sh stop %(pgid)s'
    else:
        cmd = 'kill -9 -%(pgid)s'
    cmd = (cmd % helper)
    return cmd


def default_exe_stop_command(node_config):
    """Command to stop exe on resource using remote node execution"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['execution_user'],
                                      node_config['execution_node'],
                                      local_exe_stop_command(node_config))


def local_exe_clean_command(node_config, kind='master'):
    """Command to clean exe on resource using local execution"""
    helper = {'pgid': '$mig_exe_pgid', 'kind': kind}
    helper.update(node_config)
    if 'master' != kind:
        cmd = 'cd %(execution_dir)s && '
        cmd += 'nice ./%(kind)s_node_script_%(name)s.sh clean %(pgid)s'
    else:
        cmd = 'killall -9 -u %(execution_user)s %(kind)s_node_script_%(name)s.sh'
        cmd += '; rm -rf --one-file-system %(execution_dir)s'
    cmd = (cmd % helper)
    return cmd


def default_exe_clean_command(node_config):
    """Command to clean exe on resource using remote node execution"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['execution_user'],
                                      node_config['execution_node'],
                                      local_exe_clean_command(node_config))


def local_store_start_command(node_config):
    """Command to start store on resource using local storage"""
    return 'echo no action required for %(name)s' % node_config


def default_store_start_command(node_config):
    """Command to start store on resource using remote node storage"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['storage_user'],
                                      node_config['storage_node'],
                                      local_store_start_command(node_config))


def local_store_status_command(node_config):
    """Command to query store status on resource using local storage"""
    return 'echo no action required for %(name)s' % node_config


def default_store_status_command(node_config):
    """Command to query store status on resource using remote node storage"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['storage_user'],
                                      node_config['storage_node'],
                                      local_store_status_command(node_config))


def local_store_stop_command(node_config, kind='master'):
    """Command to stop store on resource using local storage"""
    return 'echo no action required for %(name)s' % node_config


def default_store_stop_command(node_config):
    """Command to stop store on resource using remote node storage"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['storage_user'],
                                      node_config['storage_node'],
                                      local_store_stop_command(node_config))


def local_store_clean_command(node_config, kind='master'):
    """Command to clean store on resource using local storage"""
    return 'echo no action required for %(name)s' % node_config


def default_store_clean_command(node_config):
    """Command to clean store on resource using remote node storage"""
    return r'ssh -n %s %s@%s "%s"' % (' '.join(default_ssh_options()),
                                      node_config['storage_user'],
                                      node_config['storage_node'],
                                      local_store_clean_command(node_config))


def init_conf(configuration, hosturl='', hostidentifier=''):
    """Pull out a full configuration for specified resource with all missing
    fields set to default values.
    """

    conf = {}
    if not hosturl:
        return conf
    resource_id = '%s.%s' % (hosturl, hostidentifier)
    conf_file = os.path.join(configuration.resource_home, resource_id,
                             'config.MiG')
    if not os.path.isfile(conf_file):
        return conf
    (status, msg, conf) = get_resource_config_dict(configuration, conf_file)
    if not status:
        return conf

    # Fill in frontendhome if not already set

    if not conf.get('frontendhome', None):
        conf['frontendhome'] = ''
        if conf.get('RESOURCEHOME', None):
            home = conf['RESOURCEHOME']
            base_index = home.find('/MiG/mig_frontend/')
            if base_index != -1:
                home = home[:base_index]
            conf['frontendhome'] = home

    if conf.get('HOSTKEY', None):
        if re.match('^[a-zA-Z0-9.-]+,[0-9.]+$', conf['HOSTKEY'].split()[0]):
            conf['HOSTKEY'] = conf['HOSTKEY'].split(None, 1)[1]

    # Fill in all_X if not already set

    if not conf.get('all_exes', None):
        all = {}
        all['execution_user'] = ''
        all['nodecount'] = 1
        all['cputime'] = 3600
        all['execution_precondition'] = ' '
        all['prepend_execute'] = 'nice -19'
        all['exehostlog'] = ''
        all['joblog'] = ''
        all['start_command'] = 'default'
        all['status_command'] = 'default'
        all['stop_command'] = 'default'
        all['clean_command'] = 'default'
        all['continuous'] = True
        all['shared_fs'] = True
        all['vgrid_list'] = []
        all['executionnodes'] = []
        all['executionhome'] = ''

        if conf.get('EXECONFIG', None):
            all['executionnodes'] = generate_execution_node_string(
                conf['EXECONFIG'])
            first = conf['EXECONFIG'][0]

            home = str(first['execution_dir'])
            base_index = home.find('/MiG/mig_exe/')
            if base_index != -1:
                home = home[:base_index]
            all['executionhome'] = home
            all['execution_user'] = str(first['execution_user'])
            all['nodecount'] = first['nodecount']
            all['cputime'] = first['cputime']
            all['execution_precondition'] = str(
                first['execution_precondition']).strip("'")
            all['prepend_execute'] = str(first['prepend_execute']).strip('"')

            all['start_command'] = str(first['start_command'])
            default_start_command = default_exe_start_command(first)
            if all['start_command'].strip().replace('\\', '') == \
                    default_start_command.strip().replace('\\', ''):
                all['start_command'] = 'default'
            local_start_command = local_exe_start_command(first)
            if all['start_command'].strip().replace('\\', '') == \
                    local_start_command.strip().replace('\\', ''):
                all['start_command'] = 'local'
            local_leader_start_command = local_exe_start_command(first,
                                                                 'leader')
            if all['start_command'].strip().replace('\\', '') == \
                    local_leader_start_command.strip().replace('\\', ''):
                all['start_command'] = 'local'
            local_dummy_start_command = local_exe_start_command(first, 'dummy')
            if all['start_command'].strip().replace('\\', '') == \
                    local_dummy_start_command.strip().replace('\\', ''):
                all['start_command'] = 'local'

            all['status_command'] = str(first['status_command'])
            default_status_command = default_exe_status_command(first)
            if all['status_command'].strip().replace('\\', '') == \
                    default_status_command.strip().replace('\\', ''):
                all['status_command'] = 'default'
            local_status_command = local_exe_status_command(first)
            if all['status_command'].strip().replace('\\', '') == \
                    local_status_command.strip().replace('\\', ''):
                all['status_command'] = 'local'
            local_leader_status_command = local_exe_status_command(first,
                                                                   'leader')
            if all['status_command'].strip().replace('\\', '') == \
                    local_leader_status_command.strip().replace('\\', ''):
                all['status_command'] = 'local'
            local_dummy_status_command = local_exe_status_command(first,
                                                                  'dummy')
            if all['status_command'].strip().replace('\\', '') == \
                    local_dummy_status_command.strip().replace('\\', ''):
                all['status_command'] = 'local'

            all['stop_command'] = str(first['stop_command'])
            default_stop_command = default_exe_stop_command(first)
            if all['stop_command'].strip().replace('\\', '') == \
                    default_stop_command.strip().replace('\\', ''):
                all['stop_command'] = 'default'
            local_stop_command = local_exe_stop_command(first)
            if all['stop_command'].strip().replace('\\', '') == \
                    local_stop_command.strip().replace('\\', ''):
                all['stop_command'] = 'local'
            local_leader_stop_command = local_exe_stop_command(first, 'leader')
            if all['stop_command'].strip().replace('\\', '') == \
                    local_leader_stop_command.strip().replace('\\', ''):
                all['stop_command'] = 'local'
            local_dummy_stop_command = local_exe_stop_command(first, 'dummy')
            if all['stop_command'].strip().replace('\\', '') == \
                    local_dummy_stop_command.strip().replace('\\', ''):
                conf['stop_command'] = 'local'

            all['clean_command'] = str(first['clean_command'])
            default_clean_command = default_exe_clean_command(first)
            if all['clean_command'].strip().replace('\\', '') == \
                    default_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'default'
            local_clean_command = local_exe_clean_command(first)
            if all['clean_command'].strip().replace('\\', '') == \
                    local_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'local'
            local_leader_clean_command = local_exe_clean_command(first,
                                                                 'leader')
            if all['clean_command'].strip().replace('\\', '') == \
                    local_leader_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'local'
            local_dummy_clean_command = local_exe_clean_command(first, 'dummy')
            if all['clean_command'].strip().replace('\\', '') == \
                    local_dummy_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'local'

            # Handle old typo gracefully

            if first.has_key('continuous'):
                all['continuous'] = first['continuous']
            else:
                all['continuous'] = first['continious']

            all['shared_fs'] = first['shared_fs']

            # Read in list value

            all['vgrid'] = first['vgrid']

        conf['all_exes'] = all

    if not conf.get('all_stores', None):
        all = {}
        all['storage_disk'] = 10
        all['storage_protocol'] = 'sftp'
        all['storage_port'] = 22
        all['storage_user'] = 'miguser'
        all['storage_dir'] = '/home/miguser/MiG-storage'
        all['start_command'] = 'default'
        all['status_command'] = 'default'
        all['stop_command'] = 'default'
        all['clean_command'] = 'default'
        all['shared_fs'] = True
        all['vgrid'] = []
        all['storagenodes'] = ''
        all['storagehome'] = ''

        if conf.get('STORECONFIG', None):
            all['storagenodes'] = generate_storage_node_string(
                conf['STORECONFIG'])
            first = conf['STORECONFIG'][0]
            home = str(first['storage_dir'])
            base_index = home.find('/MiG/mig_store/')
            if base_index != -1:
                home = home[:base_index]
            all['storagehome'] = home
            all['storage_disk'] = first['storage_disk']
            all['storage_protocol'] = str(first['storage_protocol'])
            all['storage_port'] = first['storage_port']
            all['storage_user'] = str(first['storage_user'])
            all['storage_dir'] = str(first['storage_dir'])

            all['start_command'] = str(first['start_command'])
            default_start_command = default_store_start_command(first)
            if all['start_command'].strip().replace('\\', '') == \
                    default_start_command.strip().replace('\\', ''):
                all['start_command'] = 'default'
            local_start_command = local_store_start_command(first)
            if all['start_command'].strip().replace('\\', '') == \
                    local_start_command.strip().replace('\\', ''):
                all['start_command'] = 'local'

            all['status_command'] = str(first['status_command'])
            default_status_command = default_store_status_command(first)
            if all['status_command'].strip().replace('\\', '') == \
                    default_status_command.strip().replace('\\', ''):
                all['status_command'] = 'default'
            local_status_command = local_store_status_command(first)
            if all['status_command'].strip().replace('\\', '') == \
                    local_status_command.strip().replace('\\', ''):
                all['status_command'] = 'local'

            all['stop_command'] = str(first['stop_command'
                                            ])
            default_stop_command = default_store_stop_command(first)
            if all['stop_command'].strip().replace('\\', '') == \
                    default_stop_command.strip().replace('\\', ''):
                all['stop_command'] = 'default'
            local_stop_command = local_store_stop_command(first)
            if all['stop_command'].strip().replace('\\', '') == \
                    local_stop_command.strip().replace('\\', ''):
                all['stop_command'] = 'local'

            all['clean_command'] = str(conf['STORECONFIG'
                                            ][0]['clean_command'])
            default_clean_command = default_store_clean_command(first)
            if all['clean_command'].strip().replace('\\', '') == \
                    default_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'default'
            local_clean_command = local_store_clean_command(first)
            if all['clean_command'].strip().replace('\\', '') == \
                    local_clean_command.strip().replace('\\', ''):
                all['clean_command'] = 'local'

            all['shared_fs'] = first['shared_fs']

            # Read in list value

            all['vgrid'] = first['vgrid']

        conf['all_stores'] = all

    return conf


def prepare_conf(configuration, input_args, resource_id):
    """Update minimally validated user input dictionary to one suitable
    for resource conf parsing.
    """

    # Flatten list structure for all fields except vgrid ones

    user_args = {}
    for (key, val) in input_args.items():
        if key.endswith('vgrid'):
            user_args[key] = val
        else:
            user_args[key] = val[-1].strip()

    # Merge the variable fields like runtimeenvironmentX and re_valuesX
    # pairs into the final form suitable for parsing. Both fields
    # should exist for all X in range(0, runtime_env_fields) .

    re_list = []
    field_count = 0
    field_count_arg = user_args.get('runtime_env_fields', None)
    if field_count_arg:
        field_count = int(field_count_arg)
        del user_args['runtime_env_fields']
    for i in range(field_count):
        runtime_env = 'runtimeenvironment' + str(i)
        env_values = 're_values' + str(i)
        if user_args.has_key(runtime_env):
            if user_args.has_key(env_values):
                # re_valuesX is a single line, A=vx yz\nB=def, with all assignments
                var_lines = user_args[env_values].split('\n')
                re_values = [tuple(line.split('=', 1)) for line in var_lines]
                del user_args[env_values]
            else:
                re_values = []
            re_list.append((user_args[runtime_env], re_values))
            del user_args[runtime_env]
    user_args['RUNTIMEENVIRONMENT'] = re_list
    frontend_home = user_args.get('frontendhome', None)
    if frontend_home:
        if not user_args.get('RESOURCEHOME', None):
            user_args['RESOURCEHOME'] = frontend_home
        del user_args['frontendhome']

    execution_leader = False
    if user_args.get('LRMSTYPE', '').find('-execution-leader') != -1:
        execution_leader = True
    all_exes = []
    execution_nodes = user_args.get('exe-executionnodes', '')
    exe_names = retrieve_execution_nodes(execution_nodes, execution_leader)
    for name in exe_names:
        exe = {}
        if not user_args.get('exe-execution_dir', None):
            user_args['exe-execution_dir'] = user_args.get(
                'exe-executionhome', '')
        for (key, __) in get_exenode_specs(configuration):
            exe[key] = user_args.get("exe-%s" % key, '')
        exe['name'] = exe['execution_node'] = name
        all_exes.append(exe)
    user_args['EXECONFIG'] = all_exes
    all_stores = []
    storage_nodes = user_args.get('store-storagenodes', '')
    store_names = retrieve_storage_nodes(storage_nodes)
    for name in store_names:
        store = {}
        if not user_args.get('store-storage_dir', None):
            user_args['store-storage_dir'] = user_args.get(
                'store-storagehome', '')
        for (key, __) in get_storenode_specs(configuration):
            store[key] = user_args.get("store-%s" % key, '')
        store['name'] = store['storage_node'] = name
        all_stores.append(store)
    user_args['STORECONFIG'] = all_stores
    for key in user_args.keys():
        if key.startswith('exe-') or key.startswith('store-'):
            del user_args[key]

    conf = {}
    conf.update(user_args)

    # Now all fields should be valid conf fields, but we still need to
    # merge some partially filled ones

    if conf.get('RESOURCEHOME', None):
        if conf['RESOURCEHOME'].find(conf['HOSTURL']) == -1:
            conf['RESOURCEHOME'] = os.path.join(conf['RESOURCEHOME'], 'MiG',
                                                'mig_frontend',
                                                resource_id)
        if not conf.get('FRONTENDLOG', None):
            conf['FRONTENDLOG'] = os.path.join(conf['RESOURCEHOME'],
                                               'frontend.log')

    # We can not be sure to have any exes so remain conservative here

    execution_nodes = conf['EXECONFIG']
    storage_nodes = conf['STORECONFIG']
    nodes = 0
    if execution_nodes and execution_nodes[-1]['nodecount'].isdigit():
        nodes = int(execution_nodes[-1]['nodecount'])
    exe_count = len([i for i in exe_names if i])
    store_count = len([i for i in store_names if i])
    if execution_leader:
        exe_count -= 1
    total_nodes = exe_count * nodes + store_count
    conf['NODECOUNT'] = total_nodes

    if conf.get('HOSTKEY', None):
        # HOSTKEY is either saved one with "FQDN,IP" prefixed or raw key
        # Make sure HOSTIP gets set and that HOSTKEY gets "FQDN,IP" prefix
        # if not already set. Leave key bits and comment alone.
        key_parts = conf['HOSTKEY'].split() + ['']
        # Simplified FQDN,IP matcher which just needs to distinguish from raw
        # ssh keys. We do that since the keys have evolved and may now contain
        # a number of different prefix strings like e.g. ecdsa-sha2-nistp256
        # rather than just the old ssh-rsa one.
        if not re.match('^[a-zA-Z0-9.-]+,[0-9.]+$', key_parts[0]):
            try:
                fallback_ip = socket.gethostbyname(conf['HOSTURL'])
            except:
                fallback_ip = '0.0.0.0'
            conf['HOSTIP'] = conf.get('HOSTIP', fallback_ip)
            host_key = conf['HOSTURL'] + ',' + conf['HOSTIP']
            raw_key = conf['HOSTKEY'].strip()
            host_key += ' ' + raw_key
            conf['HOSTKEY'] = host_key

    for exe in execution_nodes:
        execution_node = exe['execution_node']
        execution_dir = exe['execution_dir']
        if execution_dir.find(conf['HOSTURL']) == -1:
            execution_dir = os.path.join(exe['execution_dir'],
                                         'MiG', 'mig_exe', resource_id)

        # In the execution leader model all executors share a working dir

        if execution_leader:

            # replace exe dir name with "all" but keep trailing slash

            execution_dir = os.path.join(execution_dir, 'all')
            if exe['name'] == exe_leader_name:
                script_prefix = 'leader'
            else:
                script_prefix = 'dummy'
        else:
            execution_dir = os.path.join(execution_dir, exe['name'])
            script_prefix = 'master'

        if not exe.get('exehostlog', None):
            exe['exehostlog'] = os.path.join(execution_dir, 'exehost.log')
        if not exe.get('joblog', None):
            exe['joblog'] = os.path.join(execution_dir, 'job.log')

        exe['execution_dir'] = execution_dir

        if 'default' == exe.get('start_command', '').strip():
            exe['start_command'] = default_exe_start_command(exe)
        elif 'local' == exe.get('start_command', '').strip():
            exe['start_command'] = local_exe_start_command(exe, script_prefix)

        if 'default' == exe.get('status_command', '').strip():
            exe['status_command'] = default_exe_status_command(exe)
        elif 'local' == exe.get('status_command', '').strip():
            exe['status_command'] = local_exe_status_command(
                exe, script_prefix)

        if 'default' == exe.get('stop_command', '').strip():
            exe['stop_command'] = default_exe_stop_command(exe)
        elif 'local' == exe.get('stop_command', '').strip():
            exe['stop_command'] = local_exe_stop_command(exe, script_prefix)

        if 'default' == exe.get('clean_command', '').strip():
            exe['clean_command'] = default_exe_clean_command(exe)
        elif 'local' == exe.get('clean_command', '').strip():
            exe['clean_command'] = local_exe_clean_command(exe, script_prefix)

    for store in storage_nodes:
        storage_node = store['storage_node']
        storage_dir = store['storage_dir']
        if storage_dir.find(conf['HOSTURL']) == -1:
            storage_dir = os.path.join(store['storage_dir'],
                                       'MiG', 'mig_store', resource_id,
                                       store['name'])

        store['storage_dir'] = storage_dir

        if 'default' == store.get('start_command', '').strip():
            store['start_command'] = default_store_start_command(store)
        elif 'local' == store.get('start_command', '').strip():
            store['start_command'] = local_store_start_command(store)

        if 'default' == store.get('status_command', '').strip():
            store['status_command'] = default_store_status_command(store)
        elif 'local' == store.get('status_command', '').strip():
            store['status_command'] = local_store_status_command(store)

        if 'default' == store.get('stop_command', '').strip():
            store['stop_command'] = default_store_stop_command(store)
        elif 'local' == store.get('stop_command', '').strip():
            store['stop_command'] = local_store_stop_command(store)

        if 'default' == store.get('clean_command', '').strip():
            store['clean_command'] = default_store_clean_command(store)
        elif 'local' == store.get('clean_command', '').strip():
            store['clean_command'] = local_store_clean_command(store)

    return conf


def empty_resource_config(configuration):
    """Prepares a basic resource configuration for use in creation of
    new resources.
    """
    conf = {'frontendhome': ''}
    for (field, spec) in get_resource_keywords(configuration).items():
        conf[field] = spec['Value']
    conf['all_exes'] = {'executionnodes': '', 'executionhome': ''}
    for (field, spec) in get_exenode_keywords(configuration).items():
        conf['all_exes'][field] = spec['Value']
    conf['all_stores'] = {'storagenodes': '', 'storagehome': ''}
    for (field, spec) in get_storenode_keywords(configuration).items():
        conf['all_stores'][field] = spec['Value']
    return conf


def write_resource_config(configuration, resource_conf, conf_path):
    """Write resource_conf dictionary settings into conf_path on disk"""

    lines = []
    for (field, __) in get_resource_specs(configuration):
        value = resource_conf.get(field, None)
        if value:
            if 'RUNTIMEENVIRONMENT' == field:
                lines.append('::%s::' % field)
                for (re_name, env_pairs) in value:
                    lines.append('name: %s' % re_name)
                    for (env_name, env_val) in env_pairs:
                        lines.append('%s=%s' % (env_name, env_val))
                lines.append('')
            elif 'EXECONFIG' == field:
                for exe in resource_conf['EXECONFIG']:
                    lines.append('::%s::' % field)
                    for (exe_field, __) in get_exenode_specs(configuration):
                        if exe_field.endswith('vgrid'):
                            lines.append('%s=%s' %
                                         (exe_field, ','.join(exe[exe_field])))
                        else:
                            lines.append('%s=%s' % (exe_field, exe[exe_field]))
                    lines.append('')
            elif 'STORECONFIG' == field:
                for store in resource_conf['STORECONFIG']:
                    lines.append('::%s::' % field)
                    for (store_field, __) in get_storenode_specs(configuration):
                        if store_field.endswith('vgrid'):
                            lines.append('%s=%s' % (
                                store_field, ','.join(store[store_field])))
                        else:
                            lines.append('%s=%s' %
                                         (store_field, store[store_field]))
                    lines.append('')
            else:
                lines.append('::%s::' % field)
                lines.append('%s' % value)
                lines.append('')

    if not os.path.isdir(os.path.dirname(conf_path)):
        os.makedirs(os.path.dirname(conf_path))

    conf_fd = open(conf_path, 'w')
    conf_fd.write('\n'.join(lines))
    conf_fd.close()

    return lines


def list_resources(resource_home, only_valid=False):
    """Return a list of all resources by listing the resource configuration
    directories in resource_home. Uses dircache for efficiency when used more
    than once per session.
    Use only_valid parameter to filter out deleted and broken resources.
    """
    resources = []
    children = dircache.listdir(resource_home)
    for name in children:
        path = os.path.join(resource_home, name)

        # skip all files and dot dirs - they are _not_ resources

        if not os.path.isdir(path):
            continue
        if path.find(os.sep + '.') != -1:
            continue
        if only_valid and not os.path.isfile(os.path.join(path, 'config')):
            continue
        resources.append(name)
    return resources


def anon_to_real_res_map(resource_home):
    """Return a mapping from anonymous resource names to real names"""
    anon_map = {}
    for name in list_resources(resource_home):
        anon_map[anon_resource_id(name)] = name
    return anon_map


def real_to_anon_res_map(resource_home):
    """Return a mapping from real resource names to anonymous names"""
    res_map = {}
    for name in list_resources(resource_home):
        res_map[name] = anon_resource_id(name)
    return res_map


def create_resource_home(configuration, client_id, resource_name):
    """Create unique resource home dir and return host identifier"""

    names = list_resources(configuration.resource_home)

    # This is a bit dangerous, but if all administrators use this script to
    # create resources it should not be a problem.

    maxcounter = -1
    for direntry in names:
        lastdot = direntry.rindex('.')
        if direntry[:lastdot] == resource_name:
            counter = int(direntry[lastdot + 1:])
            if counter > maxcounter:
                maxcounter = counter

    resource_identifier = maxcounter + 1
    unique_resource_name = resource_name + '.'\
        + str(resource_identifier)
    newdir = os.path.join(configuration.resource_home, unique_resource_name)
    try:
        os.mkdir(newdir)
    except:
        return (False, 'could not create: %s\n' % newdir)

    owner_list = [client_id]
    (status, add_msg) = resource_set_owners(configuration,
                                            unique_resource_name, owner_list)
    if not status:
        msg = """
Resource '%s' was NOT successfully created. Please take a look at the lines
above - there should be some error output
""" % unique_resource_name
        try:
            os.rmdir(newdir)
        except Exception, err:
            pass
        return (status, msg)
    else:
        return (status, resource_identifier)


# TODO: switch oneclick, sss and ps3 sandboxes to use create_resource()

def create_resource(configuration, client_id, resource_name, pending_file):
    """Create unique resource home dir and fill with resource config based on
    resource request in pending_file.
    If pending_file is a relative path it will prefixed with the
    resource_pending dir of the client_id. Thus sandbox confs with no required
    user can use e.g. /tmp for the pending file and still use this function.
    Returns creation status and host identifier for the new resource.
    """

    (status, id_msg) = create_resource_home(configuration, client_id,
                                            resource_name)
    if not status:
        return (False, id_msg)
    (status, msg) = create_resource_conf(configuration, client_id,
                                         resource_name, id_msg, pending_file)
    if not status:
        remove_resource(configuration, client_id, resource_name, id_msg)
        return (False, msg)
    return (True, id_msg)


def update_resource(configuration, client_id, resource_name,
                    resource_identifier, pending_file):
    """Update configuration for existing resource based on config request in
    pending_file.
    If pending_file is a relative path it will prefixed with the
    resource_pending dir of the client_id. Thus sandbox confs with no required
    user can use e.g. /tmp for the pending file and still use this function.
    Returns update status and a message string.
    """
    return create_resource_conf(configuration, client_id, resource_name,
                                resource_identifier, pending_file,
                                new_resource=False)


def remove_resource(configuration, client_id, resource_name, resource_identifier):
    """Remove a resource home dir"""
    msg = "\nRemoving host: '%s.%s'" % (resource_name,
                                        resource_identifier)

    unique_resource_name = resource_name + '.' + str(resource_identifier)
    resource_path = os.path.join(
        configuration.resource_home, unique_resource_name)

    for (root, dirs, files) in os.walk(resource_path):
        for filename in files:
            try:
                os.remove(os.path.join(root, filename))
            except Exception, err:
                msg += "\n  Could not remove file: '%s'. Failure: %s"\
                    % (os.path.join(root, filename), err)
    try:
        os.rmdir(resource_path)
    except Exception, err:
        msg += "\n  Could not remove dir: '%s' Failure: %s"\
            % (resource_path, err)
        return (False, msg)

    mark_resource_modified(configuration, unique_resource_name)
    mark_vgrid_modified(configuration, unique_resource_name)
    return (True, msg)


def create_resource_conf(
    configuration,
    client_id,
    resource_name,
    resource_identifier,
    resource_configfile,
    new_resource=True
):
    """Create a resource from conf in pending file. If pending_file is a
    relative path it will prefixed with the resource_pending dir of the
    client_id.
    """
    if new_resource:
        msg = """
Trying to create configuration for new resource: '%s.%s' from file '%s':
""" % (resource_name, str(resource_identifier),
            resource_configfile)
    else:
        msg = """
Trying to update configuration for existing resource '%s.%s':
""" % (resource_name, str(resource_identifier))

    client_dir = client_id_dir(client_id)

    if os.path.isabs(resource_configfile):
        pending_file = resource_configfile
    else:
        pending_file = os.path.join(configuration.resource_pending, client_dir,
                                    resource_configfile)
    tmpfile = pending_file + '.tmp'
    new_configfile = os.path.join(configuration.resource_home, '%s.%s' %
                                  (resource_name, resource_identifier),
                                  'config.MiG')

    if not os.path.exists(pending_file):
        msg += """
Failure:
  File: '%s' doesn't exist."""\
             % pending_file
        return (False, msg)

    (status, conf_msg, config_dict) = get_resource_config_dict(configuration,
                                                               pending_file)
    if not status:
        msg += '\n%s' % conf_msg
        return (False, msg)

    if config_dict['HOSTURL'] != resource_name:
        msg += \
            """
Failure:
  resource_name: '%s'
  does'nt match hosturl: '%s'
  in configfile: '%s'"""\
             % (resource_name, config_dict['HOSTURL'], pending_file)
        return (False, msg)

    if not new_resource and \
            config_dict['HOSTIDENTIFIER'] != resource_identifier:
        msg += \
            """
Failure:
  resource_identifier: '%s'
  does'nt match hostidentifier: '%s'
  in configfile: '%s'"""\
             % (resource_identifier, config_dict['HOSTIDENTIFIER'],
                pending_file)
        return (False, msg)

    try:
        fr = open(pending_file, 'r')
        fw = open(tmpfile, 'w')
        readline = fr.readline()
        while len(readline) > 0:
            fw.write(readline.replace(keyword_auto,
                                      str(resource_identifier)))
            readline = fr.readline()
        fw.close()
        fr.close()
    except Exception, err:

        msg += \
            'Failed to apply hostidentifier to configfile. Failure: %s'\
            % err
        return (False, msg)

    unique_resource_name = resource_name + '.' + str(resource_identifier)
    (status, run_msg) = run(configuration, tmpfile, unique_resource_name)
    msg += '\n' + run_msg
    if not status:
        return (False, msg)

    # truncate old conf with new accepted file

    try:
        move(tmpfile, new_configfile)
    except Exception, err:
        msg += '\nAccepted config, but failed to save it! Failed: %s'\
            % err
        return (False, msg)

    mark_resource_modified(configuration, unique_resource_name)
    mark_vgrid_modified(configuration, unique_resource_name)

    try:
        os.remove(pending_file)
    except Exception, err:
        pass
    msg += '\nNew configfile successfully applied.'
    return (True, msg)


def resource_owners(configuration, unique_resource_name):
    """Load list of resource owners for unique_resource_name"""
    owners_file = os.path.join(configuration.resource_home,
                               unique_resource_name, 'owners')
    try:
        owners = load(owners_file)
        return (True, owners)
    except Exception, exc:
        return (False, "could not load owners for %s: %s" %
                (unique_resource_name, exc))


def resource_is_owner(unique_resource_name, client_id, configuration):
    """Check if client_id is an owner of unique_resource_name"""
    (status, owners) = resource_owners(configuration, unique_resource_name)
    return (status and client_id in owners)


def resource_add_owners(configuration, unique_resource_name, clients):
    """Append list of clients to pickled list of resource owners"""
    owners_file = os.path.join(configuration.resource_home,
                               unique_resource_name, 'owners')
    try:
        owners = load(owners_file)
        owners += [i for i in clients if not i in owners]
        dump(owners, owners_file)
        mark_resource_modified(configuration, unique_resource_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not add owners for %s: %s" %
                (unique_resource_name, exc))


def resource_remove_owners(configuration, unique_resource_name, clients,
                           allow_empty=False):
    """Remove list of clients from pickled list of resource owners. The
    optional allow_empty option is used to prevent or allow removal of last
    owner.
    """
    owners_file = os.path.join(configuration.resource_home,
                               unique_resource_name, 'owners')
    try:
        owners = load(owners_file)
        owners = [i for i in owners if not i in clients]
        if not owners and not allow_empty:
            raise ValueError("not allowed to remove last owner")
        dump(owners, owners_file)
        mark_resource_modified(configuration, unique_resource_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not remove owners for %s: %s" %
                (unique_resource_name, exc))


def resource_set_owners(configuration, unique_resource_name, clients):
    """Set list of owners for given resource"""
    owners_file = os.path.join(configuration.resource_home,
                               unique_resource_name, 'owners')
    try:
        dump(clients, owners_file)
        mark_resource_modified(configuration, unique_resource_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not set owners for %s: %s" %
                (unique_resource_name, exc))
