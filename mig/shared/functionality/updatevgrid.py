#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# updatevgrid - [insert a few words of module description on this line]
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Update a VGrid with missing components"""

import os
import shutil
import subprocess
from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.fileio import write_file, pickle, make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.validstring import valid_dir_input
from shared.vgrid import vgrid_is_owner
from shared.functionality.createvgrid import create_wiki, create_scm, \
     create_tracker, create_forum

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1]

    # prepare support for confirm dialog (by css/jquery)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = "Update VGrid: %s" % vgrid_name

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >

$(document).ready(function() {

          // init confirmation dialog
          $( "#confirm_dialog" ).dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 500,
                buttons: {
                   "Cancel": function() { $( "#" + name ).dialog("close"); }
                }
              });
     }
);
</script>
'''

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"></textarea>
 </div>
'''                       })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : "Update '%s'" % vgrid_name })

    if not vgrid_is_owner(vgrid_name, client_id, configuration):

        output_objects.append({'object_type': 'error_text', 'text': 
                    'Only owners of %s can administrate it.' % vgrid_name })

        js_name = 'reqvgridowner%s' % hexlify(vgrid_name)
        helper = html_post_helper(js_name, 'sendrequestaction.py',
                                  {'vgrid_name': vgrid_name,
                                   'request_type': 'vgridowner',
                                   'request_text': ''})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append({'object_type': 'link',
                               'destination':
                               "javascript: confirmDialog(%s, '%s', '%s');"\
                               % (js_name, "Request ownership of " + \
                                  vgrid_name + ":<br/>" + \
                                  "\nPlease write a message to the owners (field below).",
                                  'request_text'),
                               'class': 'addadminlink',
                               'title': 'Request ownership of %s' % vgrid_name,
                               'text': 'Apply to become an owner'})

        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                               vgrid_name)) + os.sep
    public_base_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name)) + os.sep
    public_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridwiki')) + os.sep
    public_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridscm')) + os.sep
    public_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridtracker')) + os.sep
    private_base_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name)) + os.sep
    private_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridwiki')) + os.sep
    private_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridscm')) + os.sep
    private_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridtracker')) + os.sep
    private_forum_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridforum')) + os.sep
    vgrid_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name)) + os.sep
    vgrid_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridwiki')) + os.sep
    vgrid_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridscm')) + os.sep
    vgrid_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridtracker')) + os.sep

    output_objects.append({'object_type': 'text', 'text'
                           : 'Updating vgrid %s components ...' % vgrid_name})
    
    # Try to create all base directories used for vgrid files

    for path in (base_dir, public_base_dir, private_base_dir, vgrid_files_dir):
        try:
            os.mkdir(path)
        except Exception, exc:
            pass

    # Try component creation or repair

    if configuration.moin_share and configuration.moin_etc:

        # create public, member, owner wiki's in the vgrid dirs

        output_objects.append({'object_type': 'text', 'text'
                               : 'vgrid wiki update warnings:'})
        for wiki_dir in [public_wiki_dir, private_wiki_dir,
                         vgrid_wiki_dir]:
            tmp_output = []
            create_wiki(configuration, client_id, vgrid_name, wiki_dir,
                        tmp_output, repair=True)
            output_objects += tmp_output

    all_scm_dirs = ['', '', '']
    if configuration.hg_path and configuration.hgweb_scripts:

        # create participant scm repo in the vgrid shared dir

        output_objects.append({'object_type': 'text', 'text'
                               : 'vgrid scm update warnings:'})
        all_scm_dirs = [public_scm_dir, private_scm_dir, vgrid_scm_dir]
        for scm_dir in all_scm_dirs:
            tmp_output = []
            create_scm(configuration, client_id, vgrid_name, scm_dir,
                       tmp_output, repair=True)
            output_objects += tmp_output

    all_tracker_dirs = ['', '', '']
    if configuration.trac_admin_path:

        # create participant tracker in the vgrid shared dir

        output_objects.append({'object_type': 'text', 'text'
                               : 'vgrid tracker update warnings:'})
        all_tracker_dirs = [public_tracker_dir, private_tracker_dir,
                            vgrid_tracker_dir]
        for (tracker_dir, scm_dir) in zip(all_tracker_dirs, all_scm_dirs):
            tmp_output = []
            create_tracker(configuration, client_id, vgrid_name, tracker_dir,
                           scm_dir, tmp_output, repair=True)
            output_objects += tmp_output

    # create participant forum in the vgrid shared dir
        
    output_objects.append({'object_type': 'text', 'text'
                           : 'vgrid forum update warnings:'})
    for forum_dir in [private_forum_dir]:
        tmp_output = []
        create_forum(configuration, client_id, vgrid_name, forum_dir,
                     tmp_output, repair=True)
        output_objects += tmp_output

    output_objects.append({'object_type': 'text', 'text'
                          : 'vgrid %s updated!' % vgrid_name})
    output_objects.append({'object_type': 'link',
                           'destination': 'adminvgrid.py?vgrid_name=%s' % vgrid_name,
                           'class': 'adminlink',
                           'title': 'Administrate your VGrid',
                           'text': 'Administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


def dummy_owner_check(vgrid_name, client_id, configuration):
    """Fake owner check"""
    return True


if __name__ == "__main__":
    # Force update of all vgrids if run from command line
    # Useful in relation to e.g. dist-upgrades breaking Moin and Mercurial
    #

    import sys

    from shared.conf import get_configuration_object
    from shared.defaults import default_vgrid
    from shared.output import txt_format
    from shared.vgrid import vgrid_list_vgrids
    
    # use dummy owner check
    vgrid_is_owner = dummy_owner_check
    try:
        configuration = get_configuration_object()
    except IOError, ioe:
        print "Error loading conf: %s" % ioe
        print "maybe you need to set MIG_CONF environment?"
        sys.exit(1)

    script = __file__
    query = ""
    if sys.argv[1:]:
        client_id = sys.argv[1]
    else:
        print "you must supply a valid user ID to fake run as"
        sys.exit(1)
    extra_environment = {
        'REQUEST_METHOD': 'GET',
        'SSL_CLIENT_S_DN': client_id,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'PATH': '/bin:/usr/bin:/usr/local/bin',
        }
    
    extra_environment['SCRIPT_FILENAME'] = script
    extra_environment['QUERY_STRING'] = query
    extra_environment['REQUEST_URI'] = '%s%s' % (script, query)
    extra_environment['REQUEST_METHOD'] = 'POST'
    extra_environment['SCRIPT_URL'] = script
    extra_environment['SCRIPT_NAME'] = script
    extra_environment['SCRIPT_URI'] = 'https://localhost/cgi-bin/%s'\
                                      % script
    os.environ.update(extra_environment)

    (list_status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not list_status:
        print "Error: could not load vgrid list"
        sys.exit(1)
    for vgrid_name in all_vgrids:
        if vgrid_name == default_vgrid:
            continue
        print "update %s" % vgrid_name
        ret_msg = ''
        (output_objects, ret_val) = main(client_id, {'vgrid_name': [vgrid_name]})
        print txt_format(configuration, ret_val, ret_msg, output_objects)
