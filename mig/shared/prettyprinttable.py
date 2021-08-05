#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# prettyprinttable - [insert a few words of module description on this line]
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

"""
Prints out a table, padded to make it pretty.

MIT License

Original author: Ginstrom IT Solutions, Ryan Ginstrom
http://www.ginstrom.com/scribbles/2007/09/04/pretty-printing-a-table-in-python/

Modified to suit MiG
"""

import locale
locale.setlocale(locale.LC_NUMERIC, '')


def format_num(num):
    """Format a number according to given places.
    Adds commas, etc.

    Will truncate floats into ints!"""

    try:
        inum = int(num)
        return locale.format('%.*f', (0, inum), True)
    except (ValueError, TypeError):
        return "%s" % num


def get_max_width(table, index):
    """Get the maximum width of the given column index
    """

    return max([len(format_num(row[index])) for row in table])


def pprint_table(table):
    """Prints out a table of data, padded for alignment
    @param table: The table to print. A list of lists. Each row must have the same
    number of columns.

    """

    lines = []
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:

        # left col

        lines.append(row[0].ljust(col_paddings[0] + 1))

        # rest of the cols

        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            lines.append(col)
        lines.append('\n')
    return lines
