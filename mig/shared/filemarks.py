#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# filemarks - helpers for various site state info relying on simple file marks
# Copyright (C) 2020  The MiG Project lead by Brian Vinter
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

"""This module contains various helpers used to keep track of site state using
simple file marks. I.e. empty files where only the name, existance and
timestamp carries information.
"""
from __future__ import absolute_import

import os

from .shared.fileio import makedirs_rec, touch


def update_filemark(configuration, base_dir, rel_path, timestamp):
    """Create or update file mark file in rel_path under base_dir and set the
    given timestamp.
    """
    _logger = configuration.logger
    mark_path = os.path.join(base_dir, rel_path.lstrip(os.sep))
    mark_dir = os.path.dirname(mark_path)
    if not makedirs_rec(mark_dir, configuration):
        _logger.error("could not create required mark dir: %s" %
                      mark_dir)
        return False
    return touch(mark_path, configuration, timestamp)


def get_filemark(configuration, base_dir, rel_path):
    """Check if mark in rel_path under base_dir exists and if so return the
    timestamp associated with it. Otherwise return None.
    """
    _logger = configuration.logger
    mark_path = os.path.join(base_dir, rel_path.lstrip(os.sep))
    if not os.path.isfile(mark_path):
        _logger.debug("no file mark for %s" % mark_path)
        return None
    try:
        timestamp = os.path.getmtime(mark_path)
    except Exception as exc:
        _logger.debug("found no timestamp for file mark: %s" % mark_path)
        return None
    return timestamp


def reset_filemark(configuration, base_dir, mark_list=None):
    """Reset mark(s) in the cache for one or more marks given by mark_list
    considered relative to base_dir. The default value of None means all
    marks but it can also a list of strings.
    """
    _logger = configuration.logger
    if mark_list is None:
        try:
            rel_list = os.listdir(base_dir)
        except Exception as exc:
            _logger.warning("failed to list mark files in %s : %s" %
                            (base_dir, exc))
            return False
    elif isinstance(mark_list, basestring):
        rel_list = [mark_list]
    elif isinstance(mark_list, list):
        rel_list = mark_list
    else:
        _logger.error("invalid mark list: %s" % mark_list)
        return False
    for rel_path in rel_list:
        update_filemark(configuration, base_dir, rel_path, 0)
