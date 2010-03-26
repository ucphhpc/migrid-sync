#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resadmin - [insert a few words of module description on this line]
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

"""Display the ARC queues accessible for submission by this server"""

import os
import time

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables, find_entry
from shared.functional import validate_input_and_cert
from shared.useradm import client_id_dir
try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

def signature():
    """Signature of the main function"""

    defaults = {'benchmark': 'false'}
    return ['html_form', defaults]

def display_arc_queue(queue):
    """Format and print information about a queue to submit to.
    """

    html = '<p><a name="%s"></a>\n' % (q_anchor(queue))
    html += \
    '<table class=resources><tr class=title><td colspan=2>' + \
    '<h3>%s</h3></td>' % q_displayname(queue)
    html += '<td>Status: %s</td></tr>\n' % queue.status

    def row(col1, col2=None, col3=None):
        if col2 and col3:
            return ('<tr><td>%s<td>%s<td>%s</tr>\n' % (col1, col2, col3))
        elif col2:
            return ('<tr><td>%s<td colspan=2>%s</tr>\n' % (col1, col2))
        else:
            return ('<tr><td colspan=3>%s</tr>\n' % (col1))

    html += \
    row('Architecture: %s' % queue.cluster.architecture,
        'Running Jobs: %s' % queue.grid_running,
        'Max. runnable jobs: %s' % queue.max_running)
    html += \
    row('Total CPUs: %s' %  queue.total_cpus, 
        'Queued Jobs:  %s' % queue.grid_queued,
        'Max. time per job: %s sec.' % queue.max_wall_time)
    html += \
    row('%s' % queue.node_cpu,
        '(%s)' % queue.mds_validfrom,' ')
    html += \
    row('Node Memory: %s' % queue.node_memory,' ', ' ')
    html += \
    row('<b>Available runtime env.s:</b> ' +
        ', '.join([re.__str__()
                   for re in queue.cluster.runtime_environments]))

    html += '</table></p>'
    return html

# shared functions to name things:
def q_anchor(q):
    return ('__'.join([q.name,q.cluster.hostname]))
def q_displayname(q):
    return ('%s on %s' % (q.name, q.cluster.alias))

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

    user_dir = os.path.join(configuration.user_home, 
                            client_id_dir(client_id))

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'ARC Queues'
    output_objects.append({'object_type': 'header', 'text'
                          : 'ARC Resources available'})
    if not configuration.arc_clusters:
        output_objects.append({'object_type': 'error_text', 'text':
                               'No ARC support!'})
        return (output_objects, returnvalues.ERROR)
    try:
        session = arc.Ui(user_dir)
        queues = session.getQueues()

    except arc.NoProxyError, err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error while retrieving: %s' % err.what()
                              })
        output_objects += arc.askProxy()
        return (output_objects, returnvalues.ERROR)
    except Exception, err:
        logger.error('Exception while retrieving ARC resources\n%s' % err) 
        output_objects.append({'object_type':'warning', 'text'
                               :'Could not retrieve information: %s' % err})
        return(output_objects, returnvalues.ERROR)
        
    output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Job queues discovered'})

    for q in queues:
        output_objects.append({'object_type': 'html_form', 'text' 
                               :'<p><a href="#%s">%s</a>' % \
                               (q_anchor(q),q_displayname(q))})

    output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Queue details'})
    for q in queues:
        output_objects.append({'object_type': 'html_form', 'text' 
                               : display_arc_queue(q) })

    return (output_objects, returnvalues.OK)

