#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# init - shared helpers to init functionality backends
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

"""Script initialization helper functions"""

from __future__ import absolute_import

import mimetypes
import os
import time

from mig.shared.base import requested_backend, extract_field
from mig.shared.conf import get_configuration_object
from mig.shared.html import themed_styles, themed_scripts
from mig.shared.settings import load_settings, load_widgets, load_profile


def make_basic_entry(kind, values):
    """Create basic entry for output_objects"""
    entry = {'object_type': kind}
    entry.update(values)
    return entry


def make_start_entry(headers=[]):
    """Create start entry for output_objects"""
    return make_basic_entry('start', {'headers': headers})


def make_title_entry(text, meta='', style={}, script={}, skipmenu=False,
                     skipwidgets=False, skipuserstyle=False,
                     skipuserprofile=False, backend=''):
    """Create title entry for output_objects"""
    return make_basic_entry('title', {'text': text,
                                      'meta': meta,
                                      'style': style,
                                      'script': script,
                                      'skipmenu': skipmenu,
                                      'skipwidgets': skipwidgets,
                                      'skipuserstyle': skipuserstyle,
                                      'skipuserprofile': skipuserprofile,
                                      'backend': backend,
                                      })


def make_header_entry(text):
    """Create header entry for output_objects"""
    return make_basic_entry('header', {'text': text})


def find_entry(output_objects, kind):
    """Find entry in output_objects"""
    for entry in output_objects:
        if kind == entry['object_type']:
            return entry
    return None


def start_download(configuration, path, output):
    """Helper to set the headers required to force a file download instead of
    plain output delivery. Automatically detects mimetype of path and sets
    content size to size of output.
    """
    _logger = configuration.logger
    (content_type, _) = mimetypes.guess_type(path)
    if not content_type:
        content_type = 'application/octet-stream'
    # NOTE: we need to set content length to fit binary data
    size = sum([len(line) for line in output])
    _logger.debug('force %s output for %s of size %d' % (content_type, path,
                                                         size))
    return make_start_entry([('Content-Length', "%d" % size),
                             ('Content-Type', content_type),
                             ('Content-Disposition',
                              'attachment; filename="%s";'
                              % os.path.basename(path))])


def initialize_main_variables(client_id, op_title=True, op_header=True,
                              op_menu=True):
    """Script initialization is identical for most scripts in 
    shared/functionality. This function should be called in most cases.
    """

    configuration = get_configuration_object()
    logger = configuration.logger
    output_objects = []
    start_entry = make_start_entry()
    output_objects.append(start_entry)
    op_name = requested_backend()

    if op_title:
        skipwidgets = not configuration.site_enable_widgets or not client_id
        skipuserstyle = not configuration.site_enable_styling or not client_id
        title_object = make_title_entry('%s' % op_name, skipmenu=(not op_menu),
                                        skipwidgets=skipwidgets,
                                        skipuserstyle=skipuserstyle,
                                        skipuserprofile=(not client_id),
                                        backend=op_name,)
        # Make sure base_menu is always set for extract_menu
        # Typicall overriden based on client_id cases below
        title_object['base_menu'] = configuration.site_default_menu
        output_objects.append(title_object)
    if op_header:
        header_object = make_header_entry('%s' % op_name)
        output_objects.append(header_object)
    if client_id:
        # add the user-defined menu and widgets (if possible)
        title = find_entry(output_objects, 'title')
        if title:
            settings = load_settings(client_id, configuration)
            # NOTE: loaded settings may be False rather than dict here
            if not settings:
                settings = {}
            title['style'] = themed_styles(configuration,
                                           user_settings=settings)
            title['script'] = themed_scripts(configuration,
                                             user_settings=settings)
            if settings:
                title['user_settings'] = settings
                base_menu = settings.get('SITE_BASE_MENU', 'default')
                if not base_menu in configuration.site_base_menu:
                    base_menu = 'default'
                if base_menu == 'simple' and configuration.site_simple_menu:
                    title['base_menu'] = configuration.site_simple_menu
                elif base_menu == 'advanced' and \
                        configuration.site_advanced_menu:
                    title['base_menu'] = configuration.site_advanced_menu
                else:
                    title['base_menu'] = configuration.site_default_menu
                user_menu = settings.get('SITE_USER_MENU', None)
                if configuration.site_user_menu and user_menu:
                    title['user_menu'] = user_menu
                if settings.get('ENABLE_WIDGETS', True) and \
                        configuration.site_script_deps:
                    user_widgets = load_widgets(client_id, configuration)
                    if user_widgets:
                        title['user_widgets'] = user_widgets
            user_profile = load_profile(client_id, configuration)
            if user_profile:
                # These data are used for display in own profile view only
                profile_image_list = user_profile.get('PUBLIC_IMAGE', [])
                if profile_image_list:
                    # TODO: copy profile image e.g. to /user_home/avatars/X
                    #       and use it from there instead
                    profile_image = os.path.join(configuration.site_user_redirect,
                                                 profile_image_list[-1])
                else:
                    profile_image = ''
                user_profile['profile_image'] = profile_image
            else:
                user_profile = {}
            # Always set full name for use in personal user menu
            full_name = extract_field(client_id, 'full_name')
            user_profile['full_name'] = full_name
            title['user_profile'] = user_profile
            logger.debug('setting user profile: %s' % user_profile)
    else:
        # No user so we just enforce default site style and scripts
        title = find_entry(output_objects, 'title')
        if title:
            title['style'] = themed_styles(configuration)
            title['script'] = themed_scripts(configuration, logged_in=False)
    return (configuration, logger, output_objects, op_name)


def extract_menu(configuration, title_entry):
    """Extract the list of active menu items from title_entry. Useful to
    detect if a particular feature should be enabled for this particular set
    of default and user configured menu items.
    """
    if title_entry:
        menu_items = title_entry['base_menu'] + \
            title_entry.get('user_menu', [])
    else:
        menu_items = configuration.site_default_menu
    return menu_items
