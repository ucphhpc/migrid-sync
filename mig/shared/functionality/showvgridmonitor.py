#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showvgridmonitor - show private vgrid monitor to vgrid participants
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Show the monitor page for requested vgrids - all_vgrids keyword for all
allowed vgrids"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.defaults import all_vgrids
from mig.shared.functional import validate_input_and_cert
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.vgrid import vgrid_is_owner_or_member
from mig.shared.vgridaccess import user_vgrid_access


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': [all_vgrids]}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = '%s Resource Monitor' % label
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

    meta = '''<meta http-equiv="refresh" content="%s" />
''' % configuration.sleep_secs
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
    '''
    add_init = ''
    add_ready = '''
          // table initially sorted by col. 1 (name)
          var sortOrder = [[1,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }
          $("table.monitor").tablesorter({widgets: ["zebra"],
                                          textExtraction: imgTitle,
                                         });
          $("table.monitor").each(function () {
              try {
                  $(this).trigger("sorton", [sortOrder]);
              } catch(err) {
                  /* tablesorter chokes on empty tables - just continue */
              }
          });
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    title_entry['meta'] = meta

    vgrid_access = user_vgrid_access(configuration, client_id)
    vgrid_list = accepted['vgrid_name']
    if all_vgrids in accepted['vgrid_name']:
        vgrid_list = [i for i in vgrid_list if all_vgrids != i]\
            + vgrid_access

    # Force list to sequence of unique entries

    for vgrid_name in set(vgrid_list):
        html = ''
        if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                        configuration):
            output_objects.append({'object_type': 'error_text', 'text':
                                   '''You must be an owner or member of %s %s
to access the monitor.''' % (vgrid_name, label)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        monitor_file = os.path.join(configuration.vgrid_home, vgrid_name,
                                    '%s.html' % configuration.vgrid_monitor)
        try:
            # TODO: port yo read_file
            monitor_fd = open(monitor_file, 'r')
            past_header = False
            for line in monitor_fd:
                if -1 != line.find('end of raw header'):
                    past_header = True
                    continue
                if not past_header:
                    continue
                if -1 != line.find('begin raw footer:'):
                    break
                html += "%s" % line
            monitor_fd.close()
        except Exception as exc:
            logger.error("parsing %s failed: %s" % (monitor_file, exc))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error reading %s monitor page' % label})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({'object_type': 'html_form', 'text': html})
    return (output_objects, returnvalues.OK)
