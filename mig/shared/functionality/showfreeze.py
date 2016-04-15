#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showfreeze - back end to request freeze files in write-once fashion
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

"""Show summary contents of frozen archive"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries
from shared.freezefunctions import is_frozen_archive, get_frozen_archive, \
     build_freezeitem_object, freeze_flavors
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import themed_styles
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {
        'freeze_id': REJECT_UNSET,
        'flavor': ['freeze'],
        'checksum': ['']}
    return ['html_form', defaults]

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

    freeze_id = accepted['freeze_id'][-1]
    flavor = accepted['flavor'][-1]
    checksum = accepted['checksum'][-1]

    if not flavor in freeze_flavors.keys():
        output_objects.append({'object_type': 'error_text', 'text':
                           'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['showfreeze_title']
    output_objects.append({'object_type': 'header', 'text': title})
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    # jquery support for tablesorter

    css_helpers = {'css_base': os.path.join(configuration.site_images, 'css'),
                   'skin_base': configuration.site_skin_base}
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>

<script type="text/javascript" >

$(document).ready(function() {

          // table initially sorted by col. 0 (filename)
          var sortOrder = [[0,1]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }


          $("#frozenfilestable").tablesorter({widgets: ["zebra", "saveSort"],
                                        sortList:sortOrder,
                                        textExtraction: imgTitle
                                        })
                               .tablesorterPager({ container: $("#pager"),
                                        size: %s
                                        });
     }
);
</script>
''' % default_pager_entries

    # NB: the restrictions on freeze_id prevents illegal directory traversal
    
    if not is_frozen_archive(freeze_id, configuration):
        logger.error("%s: invalid freeze '%s': %s" % (op_name,
                                                      client_id, freeze_id))
        output_objects.append({'object_type': 'error_text', 'text'
                               : "'%s' is not an existing frozen archive!"
                               % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (load_status, freeze_dict) = get_frozen_archive(freeze_id, configuration,
                                                    checksum)
    if not load_status:
        logger.error("%s: load failed for '%s': %s" % \
                     (op_name, freeze_id, freeze_dict))
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not read details for "%s"' % \
                               freeze_id})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if freeze_dict.get('FLAVOR', 'freeze') != flavor:
        logger.error("%s: flavor mismatch for '%s': %s vs %s" % \
                     (op_name, freeze_id, flavor, freeze_dict))
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'No such %s archive "%s"' % (flavor,
                                                              freeze_id)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'table_pager', 'entry_name':
                           'frozen files', 'default_entries':
                           default_pager_entries, 'refresh_button': False})
    output_objects.append(build_freezeitem_object(configuration, freeze_dict))

    output_objects.append({'object_type': 'html_form', 'text': '<p>'})
    output_objects.append({
            'object_type': 'link',
            'destination': "showfreeze.py?freeze_id=%s;flavor=%s;checksum=%s" \
        % (freeze_id, flavor, 'md5'),
            'class': 'infolink', 
            'title': 'View archive with MD5 sums', 
            'text': 'Show with MD5 checksums - may take long'})
    # TODO: we hide sha1 column and link for now
    output_objects.append({'object_type': 'html_form', 'text': '</p><p class="hidden">'})
    output_objects.append({
            'object_type': 'link',
            'destination': "showfreeze.py?freeze_id=%s;flavor=%s;checksum=%s" \
        % (freeze_id, flavor, 'sha1'),
            'class': 'infolink', 
            'title': 'View archive with SHA1 sums', 
            'text': 'Show with SHA1 checksums - may take long'})
    output_objects.append({'object_type': 'html_form', 'text': '</p>'})

    return (output_objects, returnvalues.OK) 
