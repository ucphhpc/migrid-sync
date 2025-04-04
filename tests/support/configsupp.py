#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# configsupp - configuration helpers for unit tests
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Configuration related details within the test support library."""

from tests.support.loggersupp import FakeLogger

from mig.shared.compat import SimpleNamespace
from mig.shared.configuration import _without_noforward_keys, \
    _CONFIGURATION_ARGUMENTS, _CONFIGURATION_DEFAULTS


def _generate_namespace_kwargs():
    d = dict(_CONFIGURATION_DEFAULTS)
    d['logger'] = None
    return d


def _ensure_only_configuration_keys(d):
    """Check the dictionary arguments contains only premitted keys."""

    unknown_keys = set(d.keys()) - set(_CONFIGURATION_ARGUMENTS)
    assert len(unknown_keys) == 0, \
        "non-Configuration keys: %s" % (', '.join(unknown_keys),)


class FakeConfiguration(SimpleNamespace):
    """A simple helper to pretend we have a Configuration object populated
    with defaults overlaid with any explicitly supplied attributes.

    Automatically attaches a FakeLogger instance if no logger is provided in
    kwargs.
    """

    def __init__(self, **kwargs):
        """Initialise instance attributes based on the defaults plus any
        supplied additional options.
        """

        SimpleNamespace.__init__(self, **_generate_namespace_kwargs())

        if kwargs:
            _ensure_only_configuration_keys(kwargs)
            for k, v in kwargs.items():
                setattr(self, k, v)

        if 'logger' not in kwargs:
            self.logger = FakeLogger()

    @staticmethod
    def as_dict(thing):
        assert isinstance(thing, FakeConfiguration)
        return _without_noforward_keys(thing.__dict__)
