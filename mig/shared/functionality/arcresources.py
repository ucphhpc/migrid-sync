#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# arcresources - list arc resources and queues
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

"""Display the ARC queues accessible for submission by this server"""

import os
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

def signature():
    """Signature of the main function"""

    defaults = {'benchmark': 'false'}
    return ['html_form', defaults]

# shared functions to name things:
def q_anchor(q):
    return ('__'.join([q.name] + q.cluster.hostname.split(".")))
def q_displayname(q):
    return ('%s on %s' % (q.name, q.cluster.alias))

# HARDCODED STRING to name the zero-install ARC runtime environment
# We already use a hardcoded string in jobscriptgenerator. Merge/configure?
zero_install_arc = 'ENV/ZERO-INSTALL' 

def display_arc_queue(queue):
    """Format and print detailed information about an ARC queue.
    """

    html = '<div id=%(n)s class="queue"><a name="%(n)s"></a>\n' % \
           {'n':q_anchor(queue)}
    html += \
    '<table class=resources><tr class=title><td colspan=2>' + \
    '<h3>%s</h3></td>' % q_displayname(queue)
    html += '<td>Status: %s</td></tr>\n' % queue.status

    # figure out the real CPU characteristics...

    # The information "cores per node" is provided per-cluster in ARC.
    # through the field cpu_distribution (which is a mapping of
    # number_of_cores -> number_of_nodes. There we only use the first
    # of possibly several values

    d = dict(queue.cluster.cpu_distribution)
    if d.keys():
        cores = d.keys()[0]
    else:
        cores = 1

    def row(col1, col2=None, col3=None):
        if col2 and col3:
            return ('<tr><td>%s<td>%s<td>%s</tr>\n' % (col1, col2, col3))
        elif col2:
            return ('<tr><td>%s<td colspan=2>%s</tr>\n' % (col1, col2))
        else:
            return ('<tr><td colspan=3>%s</tr>\n' % (col1))

    html += \
    row('Architecture: %s' % queue.cluster.architecture,
        'Max. runnable jobs: %s' % queue.max_running,
        'Running Jobs: %s' % queue.grid_running)

    if (queue.total_cpus == -1):
        cpus = queue.cluster.total_cpus
    else:
        cpus = queue.total_cpus
    html += \
    row('Total Cores: %s (%s cores/node)' % (cpus, cores),
        'Max. time per job: %s sec.' % queue.max_wall_time, 
        'Queued Jobs:  %s' % queue.grid_queued)
    html += \
    row('%s' % queue.node_cpu,
        ' ', '(%s)' % queue.mds_validfrom)

    if zero_install_arc in map(str, queue.cluster.runtime_environments):
        html += row('Node Memory: %s' % queue.node_memory,
                    'Provides Zero-Install runtime environment')
    else:
        html += row('Node Memory: %s' % queue.node_memory)

    html += '</table></div>'
    return html

def queue_resource(queue):
    """Return a 'resource' dictionary for an ARC queue.

    Information mapping is straightforward, and most of it is
    independent of other parts. Exception: the name has to follow the
    format <queue.name>:<queue.cluster.hostname> to match submit page
    and mrsltoxrsl translation"""

    resource = {'object_type' :'resource',
                'name'        : queue.name + ':' + queue.cluster.hostname,
                'PUBLICNAME'  : 'ARC: ' + \
                                queue.name + ' on ' + queue.cluster.alias,

                'MEMORY'      : queue.node_memory,

                # information not available for queues, and 
                # queue.cluster.session_dir_total is astronomic!
                # '%.3f' % (float(queue.cluster.session_dir_total)/2**30),
                'DISK'        : '',
                                
                # this would actually need a precise mapping between
                # ARC and MiG, as done for the translation
                'ARCHITECTURE': queue.cluster.architecture,
                # indicating whether the queue active/inactive 
                
                'STATUS' : queue.status
                }
    # instead of a view link, we indicate "ARC"
    resource['viewreslink'] = {'object_type': 'link',
                               'destination': '#%s' % q_anchor(queue),
                               'class': 'infolink arclink iconspace '
                                    + queue.cluster.alias, # HACK for sorting
                               'title': 'Show queue details', 
                               'text': '(details)'}
    
    # 'NODECOUNT' : queue.total_cpus is sometimes -1.
    # ... we use another provided value, queue.cluster.total_cpus,
    # even though this one is not always correct either (not all CPUs
    # might be assigned to the queue)

    if (queue.total_cpus == -1):
        resource['NODECOUNT'] = queue.cluster.total_cpus
    else:
        resource['NODECOUNT'] = queue.total_cpus

    # ARC does not provide this readily, only through cpu_distribution
    # (which is a mapping of number_of_cores -> number_of_nodes. There
    # is no way to reserve cores on the same node, we set it to 1

    resource['CPUCOUNT'] = 1

    resource['RUNTIMEENVIRONMENT'] = []
    z_i = 'ENV/ZERO-INSTALL' # hard-wired name, same as in jobscriptgenerator
    if z_i in map(str, queue.cluster.runtime_environments):
        resource['RUNTIMEENVIRONMENT'] = ['ZERO-INSTALL (ARC)']
        
    return resource

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
                          : 'Available ARC queues'})

    if not configuration.site_enable_griddk:
        output_objects.append({'object_type': 'text', 'text':
                               '''Grid.dk features are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    # could factor out from here, to be usable from outside
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
        
    res_list = {'object_type': 'resource_list', 'resources':[]}
    for q in queues:
        res_list['resources'].append(queue_resource(q))

    output_objects.append(res_list)

    output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Queue details'})

    # queue details (current usage and some machine information) 
    for q in queues:
        output_objects.append({'object_type': 'html_form', 'text' 
                               : display_arc_queue(q) })
    # end of "factoring out"

    return (output_objects, returnvalues.OK)

