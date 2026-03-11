#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# picklesupp - pickled file helpers for unit tests
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Pickle related details within the test support library."""

import pickle

from tests.support.suppconst import TEST_OUTPUT_DIR
from tests.support.fixturesupp import _HINTS_APPLIERS_ARGLESS


class PickleAssertMixin:
    """Assertions for working with pickled files to be used as a mixin."""

    def assertPickledFile(self, pickle_file_path, apply_hints=None):
        """
        Check a particular pickled file exists and is loadable.

        Any data contained within it is returned for further assertions
        having been optionally transformed as requested by hints.
        """

        with open(pickle_file_path, "rb") as picklefile:
            pickled = pickle.load(picklefile)

        if not apply_hints:
            return pickled

        result = pickled
        for hint_name in apply_hints:
            if not hint_name in _HINTS_APPLIERS_ARGLESS:
                raise NotImplementedError("unknown hint %s" % (hint_name,))
            hint_fn = _HINTS_APPLIERS_ARGLESS[hint_name]
            result = hint_fn(pickled, modifier=None)
        return result
