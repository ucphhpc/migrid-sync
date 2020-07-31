#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resedithelp - Help back end for resource editor fields
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

"""Display resource editor help"""
from __future__ import absolute_import

from mig.shared import resconfkeywords
from mig.shared import returnvalues
from mig.shared.functional import validate_input_and_cert
from mig.shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
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

    status = returnvalues.OK

    resource_keywords = resconfkeywords.get_resource_keywords(configuration)
    exenode_keywords = resconfkeywords.get_exenode_keywords(configuration)
    storenode_keywords = resconfkeywords.get_storenode_keywords(configuration)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource administration help'
    output_objects.append({'object_type': 'header', 'text': 'Resource administration help'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                        : 'Welcome to the %s resource administration help' % \
                          configuration.short_title })
    output_objects.append({'object_type': 'text', 'text'
                          : 'Help for each of the resource editor fields is available below.'
                          })

    res_fields = resconfkeywords.get_resource_specs(configuration)
    exe_fields = resconfkeywords.get_exenode_specs(configuration)
    store_fields = resconfkeywords.get_storenode_specs(configuration)

    # Resource overall fields

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='%s'>%s:</a></b><br />
%s<br />
<br />""" % ('frontendhome', 'Frontend Home Path',
           """The %s user home directory on the frontend""" % \
                configuration.short_title )
                               })

    for (field, spec) in res_fields:
        if 'invisible' == spec['Editor']:
            continue
        title = spec['Title']
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='res-%s'>%s:</a></b><br />
%s<br />
<br />
Example:&nbsp;%s<br />
<br />""" % (field, title, resource_keywords[field]['Description'],
               resource_keywords[field]['Example'])
                               })

    # Execution node fields

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='exe-%s'>%s:</a></b><br />
%s<br />
<br />
Example:&nbsp;%s<br />
<br />""" % ('executionnodes', 'Execution Node(s)',
           exenode_keywords['name']['Description'],
           """
This fields configures all the job execution nodes in one %(site)s resource.<br />
It is possible to specify several execution nodes by seperating them with ';'<br />
and it's possible to denote ranges of execution nodes by using '->'.<br />
<br />
Example:&nbsp; n0->n8 ; n10 ; n12->n24<br />
<br />
Specifies the nodes n0 to n8, n10 and n12 to n24.<br />
<br />
Please note that the following node count field specifies the number of actual
physical hosts associated with each of these %(site)s execution nodes. In case of a
one-to-one mapping between %(site)s execution nodes and actual nodes, it should just
be set to 1. Only if each %(site)s execution node gives access to multiple nodes e.g.
in a cluster or batch system, should it be set higher.<br />
""" % {'site' : configuration.short_title} )
                               })

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='exe-%s'>%s:</a></b><br />
%s<br />
<br />""" % ('executionhome', 'Execution Home Path',
           """The %s user home directory on execution nodes""" % \
             configuration.short_title )
                               })

    for (field, spec) in exe_fields:
        if 'invisible' == spec['Editor']:
            continue
        title = spec['Title']
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='exe-%s'>%s:</a></b><br />
%s<br />
<br />
Example:&nbsp;%s<br />
<br />""" % (field, title, exenode_keywords[field]['Description'],
               exenode_keywords[field]['Example'])
                               })

    # Storage node fields

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='store-%s'>%s:</a></b><br />
%s<br />
<br />
Example:&nbsp;%s<br />
<br />""" % ('store-storagenodes', 'Storage Node(s)',
           storenode_keywords['name']['Description'],
           """
This fields configures all the storage nodes in one %(site)s resource.<br />
It is possible to specify several storage nodes by seperating them with ';'<br />
and it's possible to denote ranges of storage nodes by using '->'.<br />
<br />
Example:&nbsp; n0->n8 ; n10 ; n12->n24<br />
<br />
Specifies the nodes n0 to n8, n10 and n12 to n24.<br />
<br />
Please note that the following disk field specifies the amount of actual
physical storage reserved for %(site)s on each of these %(site)s storage nodes.<br />
""" % { 'site' : configuration.short_title} )
                               })

    output_objects.append({'object_type': 'html_form', 'text'
                           : """
<b><a name='store-%s'>%s:</a></b><br />
%s<br />
<br />""" % ('storagehome', 'Storage Home Path',
           """The %s user home directory on storage nodes""" % \
            configuration.short_title )
                               })

    for (field, spec) in store_fields:
        if 'invisible' == spec['Editor']:
            continue
        title = spec['Title']
        output_objects.append({'object_type': 'html_form', 'text'
                               : """
<b><a name='store-%s'>%s:</a></b><br />
%s<br />
<br />
Example:&nbsp;%s<br />
<br />""" % (field, title, storenode_keywords[field]['Description'],
               storenode_keywords[field]['Example'])
                               })

    return (output_objects, status)
