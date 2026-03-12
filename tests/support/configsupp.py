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

from mig.shared.compat import SimpleNamespace
from mig.shared.configuration import (
    _CONFIGURATION_ARGUMENTS,
    _CONFIGURATION_PROPERTIES,
)
from tests.support.loggersupp import FakeLogger


def _ensure_only_configuration_keys(thedict):
    """Check a dictionary contains only keys valid as Configuration properties."""

    unknown_keys = set(thedict.keys()) - set(_CONFIGURATION_ARGUMENTS)
    assert len(unknown_keys) == 0, "non-Configuration keys: %s" % (
        ", ".join(unknown_keys),
    )


def _generate_namespace_kwargs():
    """Create plain dictionary with supported properties and keys that map to
    their default values suitable for use in fabricating a namespace.
    """

    properties_and_defaults = dict(_CONFIGURATION_PROPERTIES)
    properties_and_defaults["logger"] = None
    return properties_and_defaults


class FakeConfiguration(SimpleNamespace):
    """An object that can act as a representative Configuration which can be
    programmed with particular values required to exercise code under test.

    This object will track standard values as would be present on a genuine
    Configuration instance such that code under test expecting such can be
    handed something. The defaults are overlaid by any explicit keyword args.

    Automatically attaches a FakeLogger instance if no logger is provided in
    kwargs.
    """

    def __init__(self, logger=None, **kwargs):
        """Initialise instance attributes based on the defaults plus any
        supplied additional options.
        """

        SimpleNamespace.__init__(self, **_generate_namespace_kwargs())

        if logger is None:
            # TODO: remove this conditional once all callers that require a
            #       FakeConfiguration request it via _provide_configuration()
            logger = FakeLogger()
        self.logger = logger

        if kwargs:
            _ensure_only_configuration_keys(kwargs)
            for k, v in kwargs.items():
                setattr(self, k, v)

    def reload_config(self, *args, **kwargs):
        """Stub defined to quack like Configuration."""

        pass
