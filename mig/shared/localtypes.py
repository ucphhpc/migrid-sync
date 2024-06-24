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

import enum
from past.builtins import basestring

""" A module containing a set of commonly used local data strutures.

The use of no internal dependencies ensures the provided primitives
can be used as the basis for defining any other parts of the system.
"""


def _isascii(value):
    """Given a string establish that is conatains only plain ascii.
    """
    assert isinstance(value, basestring)
    return not any((b > 0x7f for b in bytearray(value, 'utf8')))


class AsciiEnum(str, enum.Enum):
    """
    Enum where members behave as strings and are reuired to contain only ascii.
    """

    def __new__(cls, *values):
        if len(values) != 1:
            raise TypeError(
                'only a single argument is supported: %r' % (values, ))
        thestring = str(values[0])
        if not isinstance(thestring, basestring):
            raise TypeError('%r is not a string' % (thestring, ))
        if not _isascii(thestring):
            raise TypeError('%r is not pure ascii' % (thestring, ))
        member = str.__new__(cls, thestring)
        member._value_ = thestring
        return member
