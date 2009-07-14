#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resedithelp - 
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

import shared.resconfkeywords as resconfkeywords
import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


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

    status = returnvalues.OK

    resource_keywords = resconfkeywords.get_resource_keywords(configuration)
    exenode_keywords = resconfkeywords.get_exenode_keywords(configuration)
    storenode_keywords = resconfkeywords.get_storenode_keywords(configuration)

    output_objects.append({'object_type': 'title', 'text': 'Resource administration help'
                          })
    output_objects.append({'object_type': 'header', 'text': 'Resource administration help'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Welcome to the MiG resource administration help'})
    output_objects.append({'object_type': 'text', 'text'
                          : 'Help for each of the resource editor fields is available below.'
                          })

    res_fields = [('Host FQDN', 'HOSTURL'), ('Host identifier', 'HOSTIDENTIFIER'),
                  ('Public name', 'PUBLICNAME'), ('MiG user', 'MIGUSER'),
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

    exe_fields = [('Node Count', 'NODECOUNT'), ('CPU/Wall Time (s)', 'CPUTIME'), 
                  ('Execution precondition', 'EXECUTION_PRECONDITION'),
                  ('Prepend Execute', 'PREPEND_EXECUTE'),
                  ('Start Executing Command', 'START_COMMAND'),
                  ('Executing Status Command', 'STATUS_COMMAND'),
                  ('Stop Executing Command', 'STOP_COMMAND'),
                  ('Executing Clean Up Command', 'CLEAN_COMMAND'),
                  ('Executing Mode', 'CONTINUOUS'), ('Shared File System', 'SHARED_FS'),
                  ('VGrid Participation', 'VGRID'),
                  ]

    store_fields = [('Storage Disk (GB)', 'STORAGE_DISK'),
                    ('Storage Protocol', 'STORAGE_PROTOCOL'),
                    ('Storage Port', 'STORAGE_PORT'),
                    ('Storage User', 'STORAGE_USER'),
                    ('Storage Node', 'STORAGE_NODE'),
                    ('Storage Directory', 'STORAGE_DIR'),
                    ('Start Storage Command', 'START_COMMAND'),
                    ('Storage Status Command', 'STATUS_COMMAND'),
                    ('Stop Storage Command', 'STOP_COMMAND'),
                    ('Storage Clean Up Command', 'CLEAN_COMMAND'),
                    ('Shared File System', 'SHARED_FS'),
                    ('VGrid Participation', 'VGRID'),
                    ]

    # Resource overall fields

    for (title, field) in res_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % (field.lower(), title, resource_keywords[field]['Description'],
               resource_keywords[field]['Example'])
                               })

    # Not all exenode fields map directly to documentation in resconfkeywords

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % ('hostip', 'Host IP',
           """This is the external IP address which corresponds to the 'Host FQDN'""",
           '1.2.3.4')
                               })

    field = 'RUNTIMEENVIRONMENT'
    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % (field.lower(), 'Runtime Environment',
           resource_keywords[field]['Description'],
           resource_keywords[field]['Example'].replace('name: ', '').replace('\n', '<br>'))
                               })

    # Execution node fields

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % ('executionnodes', 'Execution Node(s)',
           exenode_keywords['NAME']['Description'],
           """
This fields configures all the job execution nodes in one MiG resource.<br>
It is possible to specify several execution nodes by seperating them with ';'<br>
and it's possible to denote ranges of execution nodes by using '->'.<br>
<br>
Example:&nbsp; n0->n8 ; n10 ; n12->n24<br>
<br>
Specifies the nodes n0 to n8, n10 and n12 to n24.<br>
<br>
Please note that the following node count field specifies the number of actual
physical hosts associated with each of these MiG execution nodes. In case of a
one-to-one mapping between MiG execution nodes and actual nodes, it should just
be set to 1. Only if each MiG execution node gives access to multiple nodes e.g.
in a cluster or batch system, should it be set higher.<br>
""")
                               })

    for (title, field) in exe_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % (field.lower(), title, exenode_keywords[field]['Description'],
               exenode_keywords[field]['Example'])
                               })

    # Storage node fields

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % ('storagenodes', 'Storage Node(s)',
           storenode_keywords['NAME']['Description'],
           """
This fields configures all the storage nodes in one MiG resource.<br>
It is possible to specify several storage nodes by seperating them with ';'<br>
and it's possible to denote ranges of storage nodes by using '->'.<br>
<br>
Example:&nbsp; n0->n8 ; n10 ; n12->n24<br>
<br>
Specifies the nodes n0 to n8, n10 and n12 to n24.<br>
<br>
Please note that the following disk field specifies the amount of actual
physical storage reserved for MiG on each of these MiG storage nodes.<br>
""")
                               })

    for (title, field) in store_fields:
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='%s'>%s:</A></b><br>
%s<br>
<br>
Example:&nbsp;%s<br>
<br>""" % (field.lower(), title, storenode_keywords[field]['Description'],
               storenode_keywords[field]['Example'])
                               })

    return (output_objects, status)
