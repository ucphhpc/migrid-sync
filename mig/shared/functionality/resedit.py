#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resedit - Resource editor back end
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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
from __future__ import print_function
from __future__ import absolute_import

from builtins import range
import socket

from mig.shared import resconfkeywords
from mig.shared import returnvalues
from mig.shared.defaults import csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.refunctions import list_runtime_environments
from mig.shared.resource import init_conf, empty_resource_config
from mig.shared.vgridaccess import res_vgrid_access


def signature():
    """Signature of the main function"""

    defaults = {'hosturl': [''], 'hostidentifier': ['']}
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


def available_choices(configuration, client_id, resource_id, field, spec):
    """Find the available choices for the selectable field.
    Tries to lookup all valid choices from configuration if field is
    specified to be a string variable.
    """
    if 'boolean' == spec['Type']:
        choices = [True, False]
    elif spec['Type'] in ('string', 'multiplestrings'):
        try:
            choices = getattr(configuration, '%ss' % field.lower())
        except AttributeError as exc:
            print(exc)
            choices = []
    else:
        choices = []
    if not spec['Required']:
        choices = [''] + choices
    default = spec['Value']
    if default in choices:
        choices = [default] + [i for i in choices if not default == i]
    return choices


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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

    if not configuration.site_enable_resources:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Resources are not enabled on this system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Find allowed VGrids and Runtimeenvironments and add them to
    # configuration object for automated choice handling

    allowed_vgrids = [''] + res_vgrid_access(configuration, resource_id)
    allowed_vgrids.sort()

    configuration.vgrids = allowed_vgrids
    (re_status, allowed_run_envs) = list_runtime_environments(configuration)
    allowed_run_envs.sort()
    area_cols = 80
    area_rows = 5

    status = returnvalues.OK

    logger.info('Starting Resource edit GUI.')

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource Editor'
    output_objects.append({'object_type': 'header', 'text': 'Resource Editor'
                           })
    output_objects.append({'object_type': 'sectionheader',
                           'text': '%s Resource Editor' % configuration.short_title})
    output_objects.append({'object_type': 'text', 'text': '''
Please fill in or edit the fields below to fit your %s resource reservation. Most fields
will work with their default values. So if you are still in doubt after reading the help
description, you can likely just leave the field alone.''' % configuration.short_title
                           })

    if hosturl and hostidentifier:
        conf = init_conf(configuration, hosturl, hostidentifier)
        if not conf:
            status = returnvalues.CLIENT_ERROR
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '''No such resource! (%s.%s)''' % (hosturl, hostidentifier)})
            return (output_objects, status)
    else:
        conf = empty_resource_config(configuration)

    res_fields = resconfkeywords.get_resource_specs(configuration)
    exe_fields = resconfkeywords.get_exenode_specs(configuration)
    store_fields = resconfkeywords.get_storenode_specs(configuration)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'short_title': configuration.short_title,
                    'form_method': form_method,
                    'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'reseditaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    output_objects.append({'object_type': 'html_form', 'text': """
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
""" % fill_helpers
                           })

    # Resource overall fields

    output_objects.append(
        {'object_type': 'sectionheader', 'text': "Main Resource Settings"})
    output_objects.append(
        {'object_type': 'text', 'text':
         """This section configures general options for the resource."""
         })

    (title, field) = ('Host FQDN', 'HOSTURL')
    if hosturl:
        try:
            hostip = conf.get('HOSTIP', socket.gethostbyname(hosturl))
        except:
            hostip = '<unknown>'
        output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a><br />
<input type='hidden' name='%s' value='%s' />
<input type='hidden' name='hostip' value='%s' />
%s
<br />
<br />""" % (title, field, field, conf[field], hostip,
             conf[field])
        })
    else:
        output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='%s' size='%d' value='%s'
    required pattern='[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+'
    title='Fully qualified domain name or Internet IP address of the resource'
/>
<br />
<br />""" % (title, field, field, field_size(conf[field]),
             conf[field])
        })

    (title, field) = ('Host identifier', 'HOSTIDENTIFIER')
    if hostidentifier:
        output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a><br />
<input type='hidden' name='%s' value='%s' />
%s
<br />
<br />""" % (title, field, field, conf[field], conf[field])
        })

    (field, title) = 'frontendhome', 'Frontend Home Path'
    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='%s' size='%d' value='%s'
    required pattern='[^ ]+' title='Absolute path to user home on the resource'
/>
<br />
<br />""" % (title, field, field,
             field_size(conf[field]), conf[field])
    })

    for (field, spec) in res_fields:
        title = spec['Title']
        field_type = spec['Type']
        if spec['Required']:
            required_str = 'required'
        else:
            required_str = ''

        if 'invisible' == spec['Editor']:
            continue
        elif 'input' == spec['Editor']:
            if spec['Type'] == 'int':
                input_str = """
<input class='fillwidth padspace' type='number' name='%s' size='%d' value='%s'
    min=0 pattern='[0-9]+' %s />
""" % (field, field_size(conf[field]), conf[field], required_str)
            else:
                input_str = """
<input class='fillwidth padspace' type='text' name='%s' size='%d' value='%s'
    %s />
""" % (field, field_size(conf[field]), conf[field], required_str)
            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a>
<br />
%s<br />
<br />""" % (title, field, input_str)
            })
        elif 'select' == spec['Editor']:
            choices = available_choices(configuration, client_id,
                                        resource_id, field, spec)
            res_value = conf[field]
            value_select = ''
            if field_type.startswith('multiple'):
                select_count = len(res_value) + extra_selects
            else:
                select_count = 1
                res_value = [res_value]
            for i in range(select_count):
                value_select += "<select name='%s'>\n" % field
                for name in choices:
                    selected = ''
                    if i < len(res_value) and res_value[i] == name:
                        selected = 'selected'
                    display = "%s" % name
                    if display == '':
                        display = ' '
                    value_select += """<option %s value='%s'>%s</option>\n""" \
                                    % (selected, name, display)
                value_select += """</select><br />\n"""
            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a><br />
%s
<br />""" % (title, field, value_select)
            })

    # Not all resource fields here map directly to keywords/specs input field

    (title, field) = ('Runtime Environments', 'RUNTIMEENVIRONMENT')
    re_list = conf[field]
    show = re_list + [('', []) for i in range(extra_selects)]
    re_select = "<input type='hidden' name='runtime_env_fields' value='%s'/>\n" \
                % len(show)
    i = 0
    for active in show:
        re_select += "<select name='runtimeenvironment%d'>\n" % i
        for name in allowed_run_envs + ['']:
            selected = ''
            if active[0] == name:
                selected = 'selected'
            display = "%s" % name
            if display == '':
                display = ' '
            re_select += """<option %s value='%s'>%s</option>\n""" % \
                         (selected, name, display)
        re_select += """</select><br />\n"""
        values = '\n'.join(['%s=%s' % pair for pair in active[1]])
        re_select += "<textarea class='fillwidth padspace' cols='%d' rows='%d' name='re_values%d'>%s</textarea><br />\n" % \
                     (area_cols, area_rows, i, values)
        i += 1

    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#res-%s'>help</a><br />
Please enter any required environment variable settings on the form NAME=VALUE in the box below
each selected runtimeenvironment.<br />
%s
<br />""" % (title, field, re_select)
    })

    # Execution node fields

    output_objects.append(
        {'object_type': 'sectionheader', 'text': "Execution nodes"})
    output_objects.append(
        {'object_type': 'text', 'text':
         """This section configures execution nodes on the resource."""
         })
    (field, title) = 'executionnodes', 'Execution Node(s)'
    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#exe-%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='exe-%s' size='%d' value='%s' />
<br />
<br />""" % (title, field, field,
             field_size(conf['all_exes'][field]), conf['all_exes'][field])
    })

    (field, title) = 'executionhome', 'Execution Home Path'
    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#exe-%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='exe-%s' size='%d' value='%s' />
<br />
<br />""" % (title, field, field,
             field_size(conf['all_exes'][field]), conf['all_exes'][field])
    })

    for (field, spec) in exe_fields:
        title = spec['Title']
        field_type = spec['Type']
        # We don't really have a good map of required fields here so disable
        required_str = ''
        if 'invisible' == spec['Editor']:
            continue
        elif 'input' == spec['Editor']:
            if spec['Type'] == 'int':
                input_str = """
<input class='fillwidth padspace' type='number' name='exe-%s' size='%d' value='%s'
    min=0 pattern='[0-9]+' %s />
""" % (field, field_size(conf['all_exes'][field]), conf['all_exes'][field],
                    required_str)
            else:
                input_str = """
<input class='fillwidth padspace' type='text' name='exe-%s' size='%d' value='%s'
    %s />
""" % (field, field_size(conf['all_exes'][field]), conf['all_exes'][field],
                    required_str)

            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#exe-%s'>help</a>
<br />
%s
<br />
<br />""" % (title, field, input_str)
            })
        elif 'select' == spec['Editor']:
            choices = available_choices(configuration, client_id,
                                        resource_id, field, spec)
            exe_value = conf['all_exes'][field]
            value_select = ''
            if field_type.startswith('multiple'):
                select_count = len(exe_value) + extra_selects
            else:
                select_count = 1
                exe_value = [exe_value]
            for i in range(select_count):
                value_select += "<select name='exe-%s'>\n" % field
                for name in choices:
                    selected = ''
                    if i < len(exe_value) and exe_value[i] == name:
                        selected = 'selected'
                    display = "%s" % name
                    if display == '':
                        display = ' '
                    value_select += """<option %s value='%s'>%s</option>\n""" \
                                    % (selected, name, display)
                value_select += """</select><br />\n"""
            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#exe-%s'>help</a><br />
%s
<br />""" % (title, field, value_select)
            })

    # Storage node fields

    output_objects.append(
        {'object_type': 'sectionheader', 'text': "Storage nodes"})
    output_objects.append(
        {'object_type': 'text', 'text':
         """This section configures storage nodes on the resource."""
         })

    (field, title) = 'storagenodes', 'Storage Node(s)'
    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#store-%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='store-%s' size='%d' value='%s' />
<br />
<br />""" % (title, field, field,
             field_size(conf['all_stores'][field]), conf['all_stores'][field])
    })

    (field, title) = 'storagehome', 'Storage Home Path'
    output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#store-%s'>help</a><br />
<input class='fillwidth padspace' type='text' name='store-%s' size='%d' value='%s' />
<br />
<br />""" % (title, field, field,
             field_size(conf['all_stores'][field]), conf['all_stores'][field])
    })

    for (field, spec) in store_fields:
        title = spec['Title']
        field_type = spec['Type']
        # We don't really have a good map of required fields here so disable
        required_str = ''
        if 'invisible' == spec['Editor']:
            continue
        elif 'input' == spec['Editor']:
            if spec['Type'] == 'int':
                input_str = """
<input class='fillwidth padspace' type='number' name='store-%s' size='%d' value='%s'
    min=0 pattern='[0-9]+' %s />
""" % (field, field_size(conf['all_stores'][field]), conf['all_stores'][field],
                    required_str)
            else:
                input_str = """
<input class='fillwidth padspace' type='text' name='store-%s' size='%d' value='%s'
    %s />
""" % (field, field_size(conf['all_stores'][field]), conf['all_stores'][field],
                    required_str)

            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#store-%s'>help</a>
<br />
%s
<br />
<br />""" % (title, field, input_str)
            })
        elif 'select' == spec['Editor']:
            choices = available_choices(configuration, client_id,
                                        resource_id, field, spec)
            store_value = conf['all_stores'][field]
            value_select = ''
            if field_type.startswith('multiple'):
                select_count = len(store_value) + extra_selects
            else:
                select_count = 1
                store_value = [store_value]
            for i in range(select_count):
                value_select += "<select name='store-%s'>\n" % field
                for name in choices:
                    selected = ''
                    if i < len(store_value) and store_value[i] == name:
                        selected = 'selected'
                    display = "%s" % name
                    if display == '':
                        display = ' '
                    value_select += """<option %s value='%s'>%s</option>\n""" \
                                    % (selected, name, display)
                value_select += """</select><br />\n"""
            output_objects.append({'object_type': 'html_form', 'text': """<br />
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='resedithelp.py#store-%s'>help</a><br />
%s
<br />""" % (title, field, value_select)
            })

    output_objects.append({'object_type': 'html_form', 'text': """
<input type='submit' value='Save' />
</form>
"""
                           })

    return (output_objects, status)
