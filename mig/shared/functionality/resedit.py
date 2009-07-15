#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resedit - Resource editor back end
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

"""Display resource editor"""

import socket

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
from shared.refunctions import list_runtime_environments
from shared.resource import init_conf, empty_resource_config 
from shared.vgrid import res_allowed_vgrids, default_vgrid


def signature():
    """Signature of the main function"""

    defaults = {'hosturl': [''], 'hostidentifier':['']}
    return ['html_form', defaults]


def field_size(value, default=30):
    """Find best input field size for value"""
    value_len = len("%s" % value)
    if value_len < 40:
        size = default
    elif value_len > 120:
        size = 120
    else:
        size = value_len
    return size


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    defaults = signature()[1]
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

    hosturl = accepted['hosturl'][-1]
    hostidentifier = accepted['hostidentifier'][-1]
    resource_id = '%s.%s' % (hosturl, hostidentifier)
    extra_selects = 3
    allowed_vgrids = res_allowed_vgrids(configuration, resource_id)
    allowed_vgrids.sort()
    (status, allowed_run_envs) = list_runtime_environments(configuration)
    allowed_run_envs.sort()
    
    status = returnvalues.OK

    logger.info('Starting Resource edit GUI.')

    output_objects.append({'object_type': 'title', 'text': 'Resource Editor'
                          })
    output_objects.append({'object_type': 'header', 'text': 'Resource Editor'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'MiG Resource Editor'})
    output_objects.append({'object_type': 'text', 'text'
                           : '''
Please fill in or edit the fields below to fit your MiG resource reservation. Most fields
will work with their default values. So if you are still in doubt after reading the help
description, you can likely just leave the field alone.'''
                          })

    if hosturl and hostidentifier:
        conf = init_conf(configuration, hosturl, hostidentifier)
        if not conf:
            status = returnvalues.CLIENT_ERROR
            output_objects.append({'object_type': 'error_text', 'text'
                           : '''No such resource! (%s.%s)''' % (hosturl, hostidentifier)})
            return (output_objects, status)
    else:
        conf = empty_resource_config(configuration)

    edit_form = """
<form name='resource_edit' method='post' action='reseditaction.py' onSubmit='return submit_check(this);'>
"""

    res_fields = [('Public name', 'PUBLICNAME'), ('MiG user', 'MIGUSER'),
                  ('MiG home', 'RESOURCEHOME'), ('SSH port', 'SSHPORT'),
                  ('SSH Multiplex', 'SSHMULTIPLEX'), ('SSH Host Public Key', 'HOSTKEY'),
                  ('Frontend Node', 'FRONTENDNODE'),
                  ('Max Download Bandwidth', 'MAXDOWNLOADBANDWIDTH'),
                  ('Max Upload Bandwidth', 'MAXUPLOADBANDWIDTH'),
                  ('Type of Local Resource Management System (LRMS)', 'LRMSTYPE'),
                  ('LRMS Execution Delay Command', 'LRMSDELAYCOMMAND'),
                  ('LRMS Submit Jobs Command', 'LRMSSUBMITCOMMAND'),
                  ('LRMS Remove Jobs Command', 'LRMSREMOVECOMMAND'),
                  ('LRMS Query Done Command', 'LRMSDONECOMMAND'),
                  ('Node Count', 'NODECOUNT'), ('CPU Count', 'CPUCOUNT'),
                  ('Memory (MB)', 'MEMORY'), ('Disk (GB)', 'DISK'),
                  ('Architecture', 'ARCHITECTURE'),
                  ('Script Language', 'SCRIPTLANGUAGE'), ('Job Type', 'JOBTYPE'),
                  ]

    exe_fields = [('Node Count', 'nodecount'), ('CPU/Wall Time (s)', 'cputime'), 
                  ('Execution precondition', 'execution_precondition'),
                  ('Prepend Execute', 'prepend_execute'),
                  ('Start Executing Command', 'start_command'),
                  ('Executing Status Command', 'status_command'),
                  ('Stop Executing Command', 'stop_command'),
                  ('Executing Clean Up Command', 'clean_command'),
                  ('Continuous Executing Mode', 'continuous'),
                  ('Shared File System', 'shared_fs'),
                  ]

    store_fields = [('Storage Disk (GB)', 'storage_disk'),
                    ('Storage Protocol', 'storage_protocol'),
                    ('Storage Port', 'storage_port'),
                    ('Storage User', 'storage_user'),
                    ('Storage Directory', 'storage_dir'),
                    ('Start Storage Command', 'start_command'),
                    ('Storage Status Command', 'status_command'),
                    ('Stop Storage Command', 'stop_command'),
                    ('Storage Clean Up Command', 'clean_command'),
                    ('Shared File System', 'shared_fs'),
                    ]

    # Resource overall fields

    output_objects.append({'object_type': 'sectionheader', 'text'
                           : "Main Resource Settings"})
    output_objects.append({'object_type': 'text', 'text'
                           : """This section configures general options for the resource."""
                           })

    (title, field) = ('Host FQDN', 'HOSTURL')
    if hosturl:
        hostip = conf.get('HOSTIP', socket.gethostbyname(hosturl))
        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#res-%s'>help</a><br>
<input type='hidden' name='%s' value='%s'>
<input type='hidden' name='HOSTIP' value='%s'>
%s
<br>
<br>""" % (title, field.lower(), field.lower(), conf[field], hostip,
           conf[field])
                               })
    else:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#res-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % (title, field.lower(), field.lower(), field_size(conf[field]),
           conf[field])
                               })

    (title, field) = ('Host identifier', 'HOSTIDENTIFIER')
    if hostidentifier:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#res-%s'>help</a><br>
<input type='hidden' name='%s' size='%d' value='%s'>
%s
<br>
<br>""" % (title, field.lower(), field.lower(), field_size(conf[field]),
           conf[field], conf[field])
                               })                               

    for (title, field) in res_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#res-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % (title, field.lower(), field.lower(), field_size(conf[field]),
           conf[field])
                               })

    # Not all resource fields here map directly to keywords/specs

    (title, field) = ('Runtime Environments', 'RUNTIMEENVIRONMENT')
    re_list = conf[field]
    show = re_list + ['' for i in range(extra_selects)]
    re_select = ''
    i = 0
    for active in show:
        re_select += "<select name='runtimeenvironment%d'>\n" % i
        for name in allowed_run_envs + ['']:
            selected = ''
            if active == name:
                selected = 'selected'
            re_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
        re_select += """</select><br>\n"""
        re_select += "<textarea cols='30' rows='3' name='re_values%d'></textarea><br>" % i

    output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#res-%s'>help</a><br>
Please enter any required environment variable settings on the form NAME=VALUE in the box below
each selected runtimeenvironment.<br>
%s
<br>
<br>""" % (title, field.lower(), re_select)
                           })


    # Execution node fields

    output_objects.append({'object_type': 'sectionheader', 'text'
                           : "Execution nodes"})
    output_objects.append({'object_type': 'text', 'text'
                           : """This section configures execution nodes on the resource."""
                           })
    field = 'executionnodes'
    output_objects.append({'object_type': 'html_form', 'text'
                           : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#exe-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % ('Execution Node(s)', field, field,
           field_size(conf['all_exes'][field]), conf['all_exes'][field])
                               })

    for (title, field) in exe_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                           : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#exe-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % (title, field.lower(), field.lower(),
           field_size(conf['all_exes'][field]), conf['all_exes'][field])
                               })

    (title, field) = ('VGrid Participation', 'vgrid')
    exe_vgrids = conf['all_exes']['vgrid']
    show = exe_vgrids + ['' for i in range(extra_selects)]
    vgrid_select = ''
    for active in show:
        vgrid_select += "<select name='vgrid'>\n"
        for name in allowed_vgrids + ['']:
            selected = ''
            if active == name:
                selected = 'selected'
            vgrid_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
        vgrid_select += """</select><br>\n"""    
    output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#exe-%s'>help</a><br>
%s
<br>
<br>""" % (title, field.lower(), vgrid_select)
                           })
    
    # Storage node fields

    output_objects.append({'object_type': 'sectionheader', 'text'
                           : "Storage nodes"})
    output_objects.append({'object_type': 'text', 'text'
                           : """This section configures storage nodes on the resource."""
                           })
    
    field = 'storagenodes'
    output_objects.append({'object_type': 'html_form', 'text'
                           : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#store-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % ('Storage Node(s)', field, field,
           field_size(conf['all_stores'][field]), conf['all_stores'][field])
                               })

    for (title, field) in store_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                           : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#store-%s'>help</a><br>
<input type='text' name='%s' size='%d' value='%s'>
<br>
<br>""" % (title, field.lower(), field.lower(),
           field_size(conf['all_stores'][field]), conf['all_stores'][field])
                               })

    (title, field) = ('VGrid Participation', 'vgrid')
    store_vgrids = conf['all_stores']['vgrid']
    show = store_vgrids + ['' for i in range(extra_selects)]
    vgrid_select = ''
    for active in show:
        vgrid_select += "<select name='vgrid'>\n"
        for name in allowed_vgrids + ['']:
            selected = ''
            if active == name:
                selected = 'selected'
            vgrid_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
        vgrid_select += """</select><br>\n"""    
    output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='resedithelp.py#store-%s'>help</a><br>
%s
<br>
<br>""" % (title, field.lower(), vgrid_select)
                           })

    # Finally show it all

    output_objects.append({'object_type': 'html_form', 'text': edit_form})

    return (output_objects, status)
