#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# parseflags - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Parse string of flags passed to a cgi script. Includes convenience
functions for the most common flags to hide underlying layout."""


def contains_letter(flags, letter):
    """Verify if flags contain the provided letter"""

    return letter in flags


def all(flags, letter='a'):
    return contains_letter(flags, letter)


def byte_count(flags, letter='b'):
    return contains_letter(flags, letter)


def binary(flags, letter='b'):
    return contains_letter(flags, letter)


def format(flags, letter='l'):
    if long_list(flags, letter):
        return 'long'
    else:
        return 'basic'


def interactive(flags, letter='i'):
    return contains_letter(flags, letter)

def in_place(flags, letter='i'):
    return contains_letter(flags, letter)

def line_count(flags, letter='l'):
    return contains_letter(flags, letter)


def long_list(flags, letter='l'):
    return contains_letter(flags, letter)


def force(flags, letter='f'):
    return contains_letter(flags, letter)


def file_info(flags, letter='f'):
    return contains_letter(flags, letter)


def parents(flags, letter='p'):
    """Verify if flags contain the parents flag"""

    return contains_letter(flags, letter)


def recursive(flags, letter='r'):
    """Verify if flags contain the recursive flag"""

    return contains_letter(flags, letter)


def sorted(flags, letter='s'):
    """Verify if flags contain the sort flag"""

    return contains_letter(flags, letter)


def summarize(flags, letter='s'):
    """Verify if flags contain the summarize flag"""

    return contains_letter(flags, letter)


def verbose(flags, letter='v'):
    """Verify if flags contain the verbose flag"""

    return contains_letter(flags, letter)


def word_count(flags, letter='w'):
    return contains_letter(flags, letter)

