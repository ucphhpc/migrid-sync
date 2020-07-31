#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# downloads - on-demand generation of scripts
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

"""Simple front end to script generators"""
from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.defaults import csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    status = returnvalues.OK
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

    output_objects.append({'object_type': 'header', 'text': 'Downloads'})
    output_objects.append({'object_type': 'html_form', 'text': """
<div class="migcontent">
This page provides access to on-demand downloads of the %(site)s user scripts in all available formats.<br />
Simply pick your flavor of choice to generate the latest user scripts in your %(site)s home directory and as a zip file for easy download.<p>
In order to use the scripts your need the interpreter of choice (bash or python at the moment) and the
<a href='http://curl.haxx.se' class='urllink iconspace'>cURL</a> command line client.<br />
There's a tutorial with examples of all the commands available on the %(site)s page. The python version of the user scripts additionally includes a miglib python module, which may be used to incorporate %(site)s commands in your python applications.
</div>
""" % {'site': configuration.short_title}})
    output_objects.append({'object_type': 'sectionheader',
                           'text': '%s User Scripts' % configuration.short_title})
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'short_title': configuration.short_title,
                    'form_method': form_method,
                    'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'scripts'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    output_objects.append({'object_type': 'html_form', 'text': """
<div class='migcontent'>
Generate %(short_title)s user scripts to manage jobs and files:<br/>
    <div class='row button-grid'>
        <div class='col-lg-4 left'>
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='hidden' name='lang' value='python' />
            <input type='submit' value='python version' />
            </form>
        </div>
        <div class='col-lg-4 middle'>
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='hidden' name='lang' value='sh' />
            <input type='submit' value='sh version' />
            </form>
        </div>
        <div class='col-lg-4 right'>
        
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='submit' value='all versions' />
            </form>
        </div>
    </div>
</div>
<br />
    """ % fill_helpers})
    output_objects.append({'object_type': 'sectionheader',
                           'text': '%s Resource Scripts' % configuration.short_title})
    output_objects.append({'object_type': 'html_form', 'text': """
<div class='migcontent'>
Generate %(short_title)s scripts to administrate resources and vgrids:<br/>
<div class='row button-grid'>
        <div class='col-lg-4 left'>
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='hidden' name='lang' value='python' />
            <input type='hidden' name='flavor' value='resource' />
            <input type='submit' value='python version' />
            </form>
        </div>
        <div class='col-lg-4 middle'>
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='hidden' name='lang' value='sh' />
            <input type='hidden' name='flavor' value='resource' />
            <input type='submit' value='sh version' />
            </form>
        </div>
        <div class='col-lg-4 right'>
            <form method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='output_format' value='html' />
            <input type='hidden' name='flavor' value='resource' />
            <input type='submit' value='all versions' />
            </form>
        </div>
    </div>
</div>
    """ % fill_helpers})

    return (output_objects, status)
