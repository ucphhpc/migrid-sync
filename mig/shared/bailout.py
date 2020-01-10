#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# bailout - emergency backend output helpers
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

import time


def bailout_helper(configuration, backend, out_obj, title_text="Runtime Error",
                   header_text="Internal Error"):
    """Fall back output helper to init basic emergency output"""
    _logger = configuration.logger
    if out_obj is None:
        out_obj = []
    title = {'object_type': 'title', 'text': title_text}
    # Try hard to display something mildly formatted
    try:
        from shared.html import themed_styles, themed_scripts
        title['style'] = themed_styles(configuration)
        title['script'] = themed_scripts(configuration, logged_in=False)
        # Hide menu to avoid message truncation
        title['skipmenu'] = True
    except Exception, exc:
        _logger.error("failed to provide even basic styling for %s" % backend)
    out_obj.append(title)
    if header_text:
        out_obj.append({'object_type': 'header', 'text': header_text})
    return out_obj

def crash_helper(configuration, backend, out_obj, error_id=None):
    """Fall back output helper to display emergency output"""
    _logger = configuration.logger
    _logger.info("in crash helper for %s" % backend)
    if error_id is None:
        error_id = time.time()
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
    _logger.info("crash helper for %s returns: %s" % (backend, out_obj))
    return out_obj

