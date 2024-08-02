# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# support - helper functions for unit testing
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

"""This file contains an assortment of compatibility functions whose
lifetime is intentionally intended to be time limited. We intentionally
place these in their own namespace to make them easily identifiable and
ease their subsequent removal.
"""

from __future__ import absolute_import
from past.builtins import basestring

import codecs
import inspect
import sys

PY2 = sys.version_info[0] < 3
_TYPE_UNICODE = type(u"")


if PY2:
    class SimpleNamespace(dict):
        """Bare minimum SimpleNamespace for Python 2."""

        def __getattribute__(self, name):
            if name == '__dict__':
                return dict(**self)

            return self[name]
else:
    from types import SimpleNamespace


def _is_unicode(val):
    """Return boolean indicating if the value is a unicode string.

    We avoid the `isinstance(val, unicode)` recommended by PEP8 here since it
    breaks when combined with python-future and futurize.
    """
    return (type(val) == _TYPE_UNICODE)


def ensure_native_string(string_or_bytes):
    """Given a supplied input which can be either a string or bytes
    return a representation providing string operations while ensuring that
    its contents represent a valid series of textual characters.

    Arrange identical operation across python 2 and 3 - specifically,
    the presence of invalid UTF-8 bytes (thus the input not being a
    valid textual string) will trigger a UnicodeDecodeError on PY3.
    Force the same to occur on PY2.
    """
    if PY2:
        # Simulate decoding done by PY3 to trigger identical exceptions
        # note the use of a forced "utf8" encoding value: this function
        # is generally used to wrap, for example, substitutions of values
        # into strings that are defined in the source code. In Python 3
        # these are mandated to be UTF-8, and thus decoding as "utf8" is
        # what will be attempted on supplied input. Match it.
        textual_output = codecs.encode(string_or_bytes, 'utf8')
    elif not _is_unicode(string_or_bytes):
        textual_output = str(string_or_bytes, 'utf8')
    else:
        textual_output = string_or_bytes
    return textual_output


def inspect_args(func):
    """Wrapper to return the arguments of a function."""

    if PY2:
        return inspect.getargspec(func).args
    else:
        return inspect.getfullargspec(func).args
