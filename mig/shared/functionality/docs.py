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
        output_objects.append({'object_type': 'link',
                               'destination': './docs.py?show=%s' % subject,
                               'class': 'urllink',
                               'title': '%s Documentation' % subject,
                               'text': subject,
                               })
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


def runtime_environments(output_objects):

    output_objects.append({'object_type': 'header', 'text'
                          : 'Runtime Environments'})

    output_objects.append({'object_type': 'text', 'text'
                          : """Runtime environments work as a kind of contract
between users and resources. The user can not as such expect a given resource
to provide any particular software or execution environment. However, jobs can
request one or more runtime environments listed here in order to only get
scheduled to resources advertising that environment."""})
    output_objects.append({'object_type': 'text', 'text'
                           : """Anyone can create new runtime environments but
it is up to the resource owners to actually advertise the environments that
their resources provide.
For example a resource with the Python interpreter installed could advertise a
corresponding python runtime environment, so that all jobs that depend on
python to run can request that runtime environment and only end up on resources
with python."""})
    output_objects.append({'object_type': 'text', 'text'
                           : """Runtime environments can be quite flexible in
order to support many kinds of software or hardware environments."""})

def license_information(output_objects, configuration):

    output_objects.append({'object_type': 'header', 'text'
                          : 'License'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
%s is based on the Minimum intrusion Grid (MiG) middleware. You can read about MiG at the
<a class="urllink" href="http://code.google.com/p/migrid/">project web site</a>.<br />
The MiG software license follows below.
""" % configuration.site_title })
    output_objects.append({'object_type': 'text', 'text'
                           : 'Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter'
                           })

    output_objects.append({'object_type': 'text', 'text' :"""
MiG is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""})

    output_objects.append({'object_type': 'text', 'text' :"""
MiG is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""})

    output_objects.append({'object_type': 'text', 'text' :"""
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""})

    output_objects.append({'object_type': 'header', 'text'
                          : 'Acknowledgements' })

    output_objects.append({'object_type': 'text', 'text' : """
This software is mainly implemented in Python:""" })
    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://python.org/',
                           'class': 'urllink',
                           'title': 'Python Home Page',
                           'text': 'Python and extension modules (PSF license)'})
    output_objects.append({'object_type': 'text', 'text' : """
web interfaces additionally rely on JavaScript from:""" })
    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://jquery.com/',
                           'class': 'urllink',
                           'title': 'JQuery Home Page',
                           'text': 'JQuery and extension modules (GPL/MIT and Creative Commons 3.0 licenses)'})
    output_objects.append({'object_type': 'text', 'text' : ''})
    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://marijn.haverbeke.nl/codemirror/',
                           'class': 'urllink',
                           'title': 'CodeMirror Home Page',
                           'text': 'CodeMirror web code editor (BSD compatible license)'})
    output_objects.append({'object_type': 'text', 'text' : ''})
    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://markitup.jaysalvat.com/',
                           'class': 'urllink',
                           'title': 'markItUp! Home Page',
                           'text': 'markItUp! web markup editor (GPL/MIT license)'})
    output_objects.append({'object_type': 'text', 'text' : """
and icons from the following sources:""" })

    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://pixel-mixer.com/',
                           'class': 'urllink',
                           'title': 'PixelMixer Home Page',                           
                           'text': 'pixel-mixer.com icons (free to use, acknowledgement required)' })
    output_objects.append({'object_type': 'text', 'text' : ''})

    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://www.famfamfam.com/lab/icons/silk/',
                           'class': 'urllink',
                           'title': 'FamFamFam Icons Home Page',
                           'text': 'famfamfam.com silk icons (Creative Commons 2.5 license)'})
    output_objects.append({'object_type': 'text', 'text' : ''})

    output_objects.append({'object_type': 'link', 
                           'destination' : 'http://www.kde-look.org/content/show.php/Crystal+SVG?content=8341',
                           'class': 'urllink',
                           'title': 'KDE Crystal Icons HomePage',
                           'text': 'KDE Crystal Icons, LGPL'})
    output_objects.append({'object_type': 'text', 'text' : ''})


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_menu=client_id)
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
                'Valid outputformats': (valid_outputformats, (output_objects, )),
                'Runtime Environments': (runtime_environments, (output_objects, )),
                'License and Acknowledgements': 
                (license_information, (output_objects, configuration, )),
                }

    output_objects.append({'object_type': 'header', 'text'
                          : '%s On-demand Documentation' % \
                            configuration.short_title })
    if not show:
        output_objects.append({'object_type': 'text',
                               'text': '''
This is the integrated help system for %s. You can search for a topic in the
search field or select the particular section directly. Please note that the
integrated help is rather limited to short overviews and technical
specifications.''' % configuration.short_title })

        output_objects.append({'object_type': 'text',
                               'text': '''
You can find more user friendly tutorials and examples on the
official site support pages:''' })
        output_objects.append({'object_type': 'link', 'destination':
                               configuration.site_external_doc,
                               'class': 'urllink', 'title': 'external documentation',
                               'text': 'external %s documentation' % \
                               configuration.site_title })

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
