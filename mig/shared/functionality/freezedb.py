#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# freezedb - manage frozen archives
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

"""Manage all owned frozen archives"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries
from shared.freezefunctions import build_freezeitem_object, \
     list_frozen_archives, get_frozen_meta, get_frozen_archive
from shared.functional import validate_input_and_cert
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {'action': ['show']}
    return ['frozenarchives', defaults]

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

    action = accepted['action'][-1]
    
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Frozen Archives'

    if action in ["show", "showlist"]:

        # jquery support for tablesorter and confirmation on delete
        # table initially sorted by col. 3 (Created date) then 2 (name)
    
        table_spec = {'table_id': 'frozenarchivetable', 'sort_order':
                      '[[3,1],[2,0]]'}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        add_init += '''
        var permanent_freeze=%s;
        
        function format_link(link_item) {
            return "<a class=\'"+link_item.class+"\' href=\\""+link_item.destination+"\\"></a>";
        }
        function refresh_archives() {
            console.debug("load archives");
            $("#load_status").addClass("spinner iconleftpad");
            $("#load_status").html("Loading archives ...");
            /* Request archive list in the background and handle as soon as
            results come in */
            $.ajax({
              url: "?output_format=json;action=list",
              type: "GET",
              dataType: "json",
              cache: false,
              success: function(jsonRes, textStatus) {
                  console.debug("got response from list");
                  var i = 0, j = 0;
                  var arch, entry;
                  //console.debug("empty table");
                  $("#frozenarchivetable tbody").empty();
                  /*
                      Grab results from json response and insert archive items
                      in table and append delete helpers to body to make
                      confirm dialog work.
                  */
                  for(i=0; i<jsonRes.length; i++) {
                      //console.debug("looking for content: "+ jsonRes[i].object_type);
                      if (jsonRes[i].object_type == "html_form") {
                          entry = jsonRes[i].text;
                          if (entry.match(/function delete[0-9]+/)) {
                              //console.debug("append delete helper: "+entry);
                              $("body").append(entry);
                          }
                      } else if (jsonRes[i].object_type == "frozenarchives") {
                          var archives = jsonRes[i].frozenarchives;
                          var j = 0;
                          for(j=0; j<archives.length; j++) {
                              arch = archives[j];
                              //console.info("found archive: "+arch.name);
                              var viewlink = format_link(arch.viewfreezelink);
                              var dellink = "";
                              if(!permanent_freeze) {
                                  dellink = "<td>"+format_link(arch.delfreezelink)+"</td>";
                              }
                              entry = "<tr><td>"+arch.id+"</td><td>"+viewlink+
                                      "</td><td>"+arch.name+"</td><td>"+
                                      arch.created+"</td><td>"+
                                      arch.frozenfiles+"</td>"+dellink+
                                      "</tr>";
                              //console.debug("append entry: "+entry);
                              $("#frozenarchivetable tbody").append(entry);
                          }
                      }
                  }
                  $("#load_status").removeClass("spinner iconleftpad");
                  $("#load_status").empty();
                  $("#frozenarchivetable").trigger("update");

              },
              error: function(jqXHR, textStatus, errorThrown) {
                  console.error("list failed: "+errorThrown);
                  $("#load_status").removeClass("spinner iconleftpad");
                  var err = "<span class=\'errortext\'>Failed to load list of archives: "+errorThrown+"</span>";
                  $("#load_status").html(err);
              }
          });
        }
        ''' % str(configuration.site_permanent_freeze).lower()

        if action == "show":
            add_ready += '''
        refresh_archives();
            '''
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

    output_objects.append({'object_type': 'header', 'text'
                          : 'Frozen Archives'})

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    output_objects.append(
        {'object_type': 'text', 'text' :
         '''Frozen archives are write-once collections of files used e.g. in
 relation to conference paper submissions. Please note that local policies may
 prevent users from deleting frozen archives without explicit acceptance from
 the management.
         '''})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Existing frozen archives'})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
    <div id="load_status"><!-- Dynamically filled by js --></div>
    '''})

    frozenarchives = []
    if action in ["list", "showlist"]:
        (status, ret) = list_frozen_archives(configuration, client_id)
        if not status:
            logger.error("%s: failed for '%s': %s" % (op_name,
                                                      client_id, ret))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : ret})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.debug("%s %s: building list of archives" % (op_name, action))
        for freeze_id in ret:
            # TODO: add file count to meta and switch here
            #(load_status, freeze_dict) = get_frozen_meta(freeze_id,
            #                                             configuration)
            (load_status, freeze_dict) = get_frozen_archive(freeze_id,
                                                            configuration,
                                                            checksum='')
            if not load_status:
                logger.error("%s: load failed for '%s': %s" % \
                             (op_name, freeze_id, freeze_dict))
                output_objects.append({'object_type': 'error_text', 'text'
                                       : 'Could not read details for "%s"' % \
                                       freeze_id})
                return (output_objects, returnvalues.SYSTEM_ERROR)
            freeze_item = build_freezeitem_object(configuration, freeze_dict,
                                                  summary=True)
            freeze_id = freeze_item['id']
            flavor = freeze_item.get('flavor', 'freeze')

            freeze_item['viewfreezelink'] = {
                'object_type': 'link',
                'destination': "showfreeze.py?freeze_id=%s;flavor=%s" % \
                (freeze_id, flavor),
                'class': 'infolink iconspace', 
                'title': 'View frozen archive %s' % freeze_id, 
                'text': ''}
            if client_id == freeze_item['creator']:
                js_name = 'delete%s' % hexlify(freeze_id)
                helper = html_post_helper(js_name, 'deletefreeze.py',
                                          {'freeze_id': freeze_id,
                                           'flavor': flavor})
                output_objects.append({'object_type': 'html_form', 'text': helper})
                freeze_item['delfreezelink'] = {
                    'object_type': 'link', 'destination':
                    "javascript: confirmDialog(%s, '%s');" % \
                    (js_name, 'Really remove %s?' % freeze_id),
                    'class': 'removelink iconspace', 'title': 'Remove %s' % \
                    freeze_id, 'text': ''}
            frozenarchives.append(freeze_item)
        logger.debug("%s %s: inserting list of %d archives" % \
                     (op_name, action, len(frozenarchives)))
    if action in ["show", "showlist"]:
        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'frozen archives',
                               'default_entries': default_pager_entries})

    output_objects.append({'object_type': 'frozenarchives',
                           'frozenarchives': frozenarchives})

    if action in ["show", "showlist"]:
        output_objects.append({'object_type': 'sectionheader', 'text':
                               'Additional Frozen Archives'})
        output_objects.append({'object_type': 'link',
                               'destination': 'adminfreeze.py',
                               'class': 'addlink iconspace',
                               'title': 'Specify a new frozen archive', 
                               'text': 'Create a new frozen archive'})

    return (output_objects, returnvalues.OK)
