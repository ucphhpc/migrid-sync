#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# shell - advanced shell
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

"""Emulate a command line interface with all the cgi functions"""

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""
    defaults = {'menu': 'yes'}
    return ['html_form', defaults]


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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Advanced Shell'
    if accepted['menu'][-1] == 'no':
        title_entry['skipmenu'] = True
        title_entry['skipwidgets'] = True
        title_entry['style'] = '''
<style type="text/css">
#content { margin: 10px }
</style>'''
    # Please have href points to the CSS file and have basedir changed to the
    # directory where JavaScripts are placed.
    title_entry['script']['advanced'] += '''
<link rel="stylesheet" type="text/css" href="/images/css/shell.css" media="screen"/>
'''
    title_entry['script']['init'] = '''
  var  basedir="/images/js/";

  var shell;
  var interval;
  // scripts have to be loaded in sequence, thereby this recursion.
  var scripts=["toolkits.js","gui.js","ajax.js","intellisense.js",
               "output.js","status.js","lib.js","shell.js"];
  function loadAll(s_i) {
        if(s_i<1)
        {
            shell=new Shell('shell', 'shell', 'xmlrpcinterface.py');
            shell.Init();
            return;
        }
        var script=document.createElement('script');
        script.setAttribute('type','text/javascript');
        script.setAttribute('src',basedir + scripts[ scripts.length - s_i ]);
        document.getElementsByTagName('head')[0].appendChild(script);

        if ( script.readyState ) {
           // IE style browser
           script.onreadystatechange= function () {
                if(this.readyState=='loaded'||this.readyState=='complete')
                    loadAll( s_i-1 );
            }
        } else {
        // other browser, should support onload
            script.onload=function()
            {
                loadAll( s_i-1 );
            }
        }
        return;
    }
'''
    title_entry['script']['body'] = ' onload="loadAll(scripts.length);"'

    output_objects.append({'object_type': 'header', 'text': 'Advanced Shell'
                           })
    output_objects.append({'object_type': 'html_form',
                           'text': '<div id="shell"><!-- filled by js --></div>'})

    return (output_objects, status)
