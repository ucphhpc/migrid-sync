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

INDICATOR_CH = ':'
INVALID_INSERTION_POINT = -2
MARKER = INDICATOR_CH * 2
UNSAFE_CHARS = sorted(list(set(string.printable) - set(username_charset)))
UNSAFE_CHARS_ORD = list(ord(c) for c in UNSAFE_CHARS)
UNSAFE_CHARS_NAMES = list(str(o).zfill(3) for o in UNSAFE_CHARS_ORD)
UNSAFE_SUBSTIUTIONS = dict(zip(UNSAFE_CHARS_ORD, UNSAFE_CHARS_NAMES))
PY2 = sys.version_info[0] == 2

if PY2:
    def _as_ascii_string(value): return value
else:
    def _as_ascii_string(value): return codecs.decode(value, 'ascii')


# TODO
# - swap to converting the ord char value to hex as a way to save bytes

def safename_encode(value):
    punycoded = _as_ascii_string(codecs.encode(value, 'punycode'))

    if len(punycoded) == 0:
        return ''

    insertion_point = INVALID_INSERTION_POINT

    if punycoded[-1] == '-':
        # the value is punycoded ascii - record this fact and
        # remove this trailing character which will be added
        # back later bsaed on the indication character
        insertion_point = -1
    else:
        try:
            insertion_point = punycoded.rindex('-')
        except ValueError:
            # the marker could not be located so the insertion
            # point as not updated and thus remains set invalid
            pass
    if insertion_point == INVALID_INSERTION_POINT:
        raise AssertionError(None)


    characters = list(punycoded)

    for index, character in enumerate(characters):
        character_ordinal = ord(character)
        character_substitute = UNSAFE_SUBSTIUTIONS.get(character_ordinal, None)
        if character_substitute is not None:
            characters[index] = "%s%s" % (INDICATOR_CH, character_substitute)

    if insertion_point != INVALID_INSERTION_POINT:
        # replace punycode single hyphen trailer with an escaped indicator
        characters[insertion_point] = INDICATOR_CH
        characters.insert(insertion_point, INDICATOR_CH)

    return ''.join(characters)


def safename_decode(value):
    if value == '':
        return value

    value_to_decode = None
    try:
        idx = value.rindex(MARKER)
        value_to_decode = ''.join((value[:idx + 1], '045', value[idx + 2:]))
    except ValueError:
        raise RuntimeError()

    chunked = value_to_decode.split(INDICATOR_CH)

    skip_first_chunk = chunked[0] != ''
    index = 1 if skip_first_chunk else 0

    while index < len(chunked):
        chunk = chunked[index]
        if chunk == '':
            index += 1
            continue
        character_substitute = chr(int(chunk[0:3]))
        chunked[index] = "%s%s" % (character_substitute, chunk[3:])
        index += 1

    try:
        return codecs.decode(''.join(chunked), 'punycode')
    except Exception as e:
        raise e


if __name__ == '__main__':
    def visibly_print(characters):
        pieces = []
        for c in UNSAFE_CHARS:
            c_ord = ord(c)
            if c == ' ':
                pieces.append("\\N{SPACE}")
            elif c == '"':
                pieces.append('\\"')
            elif c_ord < 10:
                # single digit control chars
                pieces.append("\\x0%d" % c_ord)
            elif c_ord < 32:
                # double digit control chars
                pieces.append("\\x%s" % c_ord)
            else:
                pieces.append(c)
        return ''.join(pieces)
    print("%d username chars: %s" % (len(UNSAFE_CHARS), visibly_print(UNSAFE_CHARS)))
