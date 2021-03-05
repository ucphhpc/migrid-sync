#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# bailout - emergency backend output helpers
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Emergency bailout output helpers used to display something relatively sane
even when something essential breaks in the backend output delivery.
"""
from __future__ import absolute_import

import time

# IMPORTANT: this is emergency handling so do NOT import any custom modules!
#            Python standard library modules should be okay, but anything else
#            should only be imported with exception handling to avoid errors.


def bailout_title(configuration=None, title_text=""):
    """Helper to handle very basic title output in a failsafe way"""
    # Hide menu to avoid message truncation
    title = {'object_type': 'title', 'text': title_text, 'skipmenu': True,
             'style': '', 'script': ''}
    _logger = None
    try:
        if not configuration:
            from mig.shared.conf import get_configuration_object
            configuration = get_configuration_object()
            _logger = configuration.logger
        from mig.shared.html import themed_styles, themed_scripts
        title['style'] = themed_styles(configuration)
        title['script'] = themed_scripts(configuration, logged_in=False)
    except Exception as exc:
        if _logger:
            _logger.error("failed to provide even basic styling for title")
    return title


def compact_lines(raw_lines, truncate_max_lines, truncate_max_chars):
    """Returns a compacted copy of raw_lines without touching the original"""
    limit_lines = []
    keep_lines = max(1, truncate_max_lines / 2)
    keep_chars = truncate_max_chars / 2
    raw_line_count = len(raw_lines)
    for i in range(raw_line_count):
        if i >= keep_lines and i < len(raw_lines) - keep_lines:
            if i == keep_lines:
                limit_lines.append(' .... %d line(s) ...' %
                                   (raw_line_count - 2 * keep_lines))
            continue
        line = raw_lines[i]
        if len(line) > truncate_max_chars:
            limit_lines.append(line[0:keep_chars] + ' ... ' +
                               line[-keep_chars:])
        else:
            limit_lines.append(line)
    return limit_lines


def filter_output_objects(configuration, out_obj, truncate_out_len=78,
                          truncate_max_lines=4):
    """Helper to remove noise from out_obj before logging. Strip style and
    script noise from title entry in log and shorten any file_output to max
    truncate_out_len chars showing only prefix and suffix. Entries with many
    lines are pruned from the middle to truncate_max_lines of total output.
    """
    out_filtered = []
    for entry in out_obj:
        if entry.get('object_type', 'UNKNOWN') == 'title':
            # NOTE: shallow copy so we must be careful not to edit original
            stripped_title = entry.copy()
            for name in ('style', 'script', 'user_profile', 'user_settings'):
                stripped_title[name] = '{ ... }'
            out_filtered.append(stripped_title)
        elif entry.get('object_type', 'UNKNOWN') == 'file_output':
            # NOTE: shallow copy so we must be careful not to edit original
            stripped_output = entry.copy()
            stripped_lines = stripped_output.get('lines', [])
            stripped_output['lines'] = compact_lines(stripped_lines,
                                                     truncate_max_lines,
                                                     truncate_out_len)
            out_filtered.append(stripped_output)
        else:
            out_filtered.append(entry)
    return out_filtered


def bailout_helper(configuration, backend, out_obj, title_text="Runtime Error",
                   header_text="Internal Error"):
    """Fall back output helper to init basic emergency output"""
    _logger = configuration.logger
    if out_obj is None:
        out_obj = []
    title = bailout_title(configuration, title_text)
    out_obj.append(title)
    if header_text:
        out_obj.append({'object_type': 'header', 'text': header_text})
    return out_obj


def crash_helper(configuration, backend, out_obj, error_id=None):
    """Fall back output helper to display emergency output"""
    _logger = configuration.logger
    if error_id is None:
        error_id = time.time()
    _logger.info("detected crash in %r: %s" % (backend, error_id))
    out_obj = bailout_helper(configuration, backend, out_obj)
    out_obj.append(
        {'object_type': 'error_text', 'text':
         """A critical internal error occured in the %s backend. It has been
logged internally with error ID %s
         """ % (backend, error_id)})
    out_obj.append(
        {'object_type': 'error_text', 'text':
         """Please report it to the %s site admins %s if the problem persists.
         """ % (configuration.short_title, configuration.admin_email)})
    out_filtered = filter_output_objects(configuration, out_obj)
    _logger.info("crash helper for %s returns: %s" % (backend, out_filtered))
    return out_obj
