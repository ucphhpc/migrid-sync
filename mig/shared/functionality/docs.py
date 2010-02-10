#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# docs - online documentation generator
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

# See all_docs dictionary below for information about adding
# documentation topics.

"""On-demand documentation generator"""

import fnmatch

import shared.mrslkeywords as mrslkeywords
import shared.resconfkeywords as resconfkeywords
import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables
from shared.output import get_valid_outputformats


def signature():
    """Signature of the main function"""

    defaults = {'show': [''], 'search': ['']}
    return ['text', defaults]


def display_topic(output_objects, subject, all_docs):
    """Display specified subject"""
    if subject in all_docs.keys():
        output_objects.append({'object_type': 'link', 'text': subject,
                              'destination': './docs.py?show=%s'
                               % subject})
    else:
        output_objects.append({'object_type': 'text', 'text'
                              : "No documentation found matching '%s'"
                               % subject})
    output_objects.append({'object_type': 'html_form', 'text': '<br />'})


def show_subject(subject, doc_function, doc_args):
    """Show documentation for specified subject"""
    doc_function(*doc_args)


def display_doc(output_objects, subject, all_docs):
    """Show doc"""
    if subject in all_docs.keys():
        (func, args) = all_docs[subject]
        show_subject(subject, func, args)
    else:
        output_objects.append({'object_type': 'text', 'text'
                              : "No documentation found matching '%s'"
                               % subject})


def mrsl_keywords(configuration, output_objects):
    """All job description keywords"""
    keywords_dict = mrslkeywords.get_keywords_dict(configuration)
    output_objects.append({'object_type': 'header', 'text'
                          : 'Job description: mRSL'})
    sorted_keys = keywords_dict.keys()
    sorted_keys.sort()
    for keyword in sorted_keys:
        info = keywords_dict[keyword]
        output_objects.append({'object_type': 'html_form', 'text'
                              : "<a name='%s'></a>" % keyword})
        output_objects.append({'object_type': 'sectionheader', 'text'
                              : keyword})
        entries = []
        for (field, val) in info.items():
            entries.append(field + ': ' + str(val))
        output_objects.append({'object_type': 'list', 'list': entries})


def config_keywords(configuration, output_objects):
    """All resource configuration keywords"""
    resource_keywords = \
        resconfkeywords.get_resource_keywords(configuration)
    exenode_keywords = \
        resconfkeywords.get_exenode_keywords(configuration)
    storenode_keywords = \
        resconfkeywords.get_storenode_keywords(configuration)
    topics = [('Resource configuration', resource_keywords),
              ('Execution node configuration', exenode_keywords),
              ('Storage node configuration', storenode_keywords)]
    for (title, keywords_dict) in topics:
        output_objects.append({'object_type': 'header', 'text': title})
        sorted_keys = keywords_dict.keys()
        sorted_keys.sort()
        for keyword in sorted_keys:
            info = keywords_dict[keyword]
            output_objects.append({'object_type': 'sectionheader', 'text'
                                  : keyword})
            entries = []
            for (field, val) in info.items():
                entries.append(field + ': ' + str(val))
            output_objects.append({'object_type': 'list', 'list'
                                  : entries})


def valid_outputformats(output_objects):
    """All valid output formats"""
    output_objects.append({'object_type': 'header', 'text'
                          : 'Valid outputformats'})
    output_objects.append({'object_type': 'text', 'text'
                          : 'The outputformat is specified with the output_format parameter.'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : 'Example: SERVER_URL/ls.py?output_format=txt'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Valid formats'})
    entries = []
    for outputformat in get_valid_outputformats():
        entries.append(outputformat)
    output_objects.append({'object_type': 'list', 'list': entries})


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    show = accepted['show'][-1].lower()
    search = accepted['search'][-1].lower()

    # Topic to generator-function mapping - add new topics here
    # by adding a 'topic:generator-function' pair.

    all_docs = {'Job description: mRSL': (mrsl_keywords, (configuration, output_objects, )),
                'Resource configuration': (config_keywords, (configuration, output_objects, )),
                'Valid outputformats': (valid_outputformats, (output_objects, ))}

    output_objects.append({'object_type': 'header', 'text'
                          : '%s On-demand Documentation' % \
                            configuration.short_title })
    html = '<p>Filter (using *,? etc.)'
    html += "<form method='post' action='docs.py'>"
    html += "<input type='hidden' name='show' value='' />"
    html += "<input type='text' name='search' value='' />"
    html += "<input type='submit' value='Filter' />"
    html += '</form></p><br />'
    output_objects.append({'object_type': 'html_form', 'text': html})

    # Fall back to show all topics

    if not search and not show:
        search = '*'

    if search:

        # Pattern matching: select all topics that _contain_ search pattern
        # i.e. like re.search rather than re.match

        search_patterns = []
        for topic in all_docs.keys():

            # Match any prefix and suffix.
            # No problem with extra '*'s since'***' also matches 'a')

            if fnmatch.fnmatch(topic.lower(), '*' + search + '*'):
                search_patterns.append(topic)

        output_objects.append({'object_type': 'header', 'text'
                              : 'Documentation topics:'})
        for pattern in search_patterns:
            display_topic(output_objects, pattern, all_docs)
        if not search_patterns:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'No topics matching %s' % search})

    if show:

        # Pattern matching: select all topics that _contain_ search pattern
        # i.e. like re.search rather than re.match

        show_patterns = []
        for topic in all_docs.keys():

            # Match any prefix and suffix.
            # No problem with extra '*'s since'***' also matches 'a')

            if fnmatch.fnmatch(topic.lower(), '*' + show + '*'):
                show_patterns.append(topic)

        for pattern in show_patterns:
            display_doc(output_objects, pattern, all_docs)

        if not show_patterns:
            output_objects.append({'object_type': 'text', 'text'
                                  : 'No topics matching %s' % show})

    return (output_objects, returnvalues.OK)


