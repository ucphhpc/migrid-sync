#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# safeeval - Safe evaluation of expressions and commands
# Copyright (C) 2003-2023  The MiG Project
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

import codecs
import os
import string
import sys

sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../..")))

from mig.shared.defaults import username_charset

UNSAFE_CHARS = sorted(list(set(string.printable) - set(username_charset)))
UNSAFE_CHARS_ORD = list(ord(c) for c in UNSAFE_CHARS)
UNSAFE_CHARS_NAMES = list(str(o).zfill(3) for o in UNSAFE_CHARS_ORD)
UNSAFE_SUBSTIUTIONS = dict(zip(UNSAFE_CHARS_ORD, UNSAFE_CHARS_NAMES))
PY2 = sys.version_info[0] == 2

if PY2:
    def _as_ascii_string(value): return value
else:
    def _as_ascii_string(value): return codecs.decode(value, 'ascii')


def safename_encode(value):
    punycoded = _as_ascii_string(codecs.encode(value, 'punycode'))
    characters = list(punycoded)

    for index, character in enumerate(characters):
        character_ordinal = ord(character)
        character_substitute = UNSAFE_SUBSTIUTIONS.get(character_ordinal, None)
        if character_substitute is not None:
            characters[index] = ":%s" % character_substitute

    return ''.join(characters)


def safename_decode(value):
    chunked = value.split(':')

    if len(chunked) > 1:
        for index, chunk in enumerate(chunked):
            if chunk == '':
                continue
            trailer = chunk[3:]
            character_substitute = chunk[0:3]
            character_ordinal = int(character_substitute)
            chunked[index] = "%s%s" % (chr(character_ordinal), trailer)

    return codecs.decode(''.join(chunked), 'punycode')


if __name__ == '__main__':
    d = dict(zip(UNSAFE_CHARS_ORD, UNSAFE_CHARS_NAMES))
    print(len(d))
    print(d)
