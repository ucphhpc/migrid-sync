#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# multi_writer - [insert a few words of module description on this line]
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

from __future__ import print_function
import sys
from docutils.core import publish_string

# Setup a restructured text example

reST = \
    """
Example of reST:
================

This is a small example of the way reST can be used as a base
for generating HTML formatted text that:

- looks nice
- is standards compliant
- is flexible

We *may* decide to start using this as text formatting tool in
MiG__ later on.

__ http://mig-1.imada.sdu.dk/


We can also use it for creating tables if we want to:

=====  =====  ======
Input         Output
------------  ------
A      B      A or B
=====  =====  ======
False  False  False
True   False  True
False  True   True
True   True   True
=====  =====  ======

Have fun!

----

Cheers, Jonas
"""

# Raw reST

if len(sys.argv) == 1 or 'raw' in sys.argv:
    print('reST:')
    print(reST)

    print()

if len(sys.argv) == 1 or 'rest' in sys.argv:

    # Parsed reST

    raw = publish_string(reST, writer=None)

    print('RAW:')
    print(raw)

    print()

if len(sys.argv) == 1 or 'html' in sys.argv:
    from docutils.writers.html4css1 import Writer

    # Setup a translator writer

    html_writer = Writer()

    # Translate reST to html

    html = publish_string(reST, writer=html_writer)

    print('HTML:')
    print(html)

    print()

if len(sys.argv) == 1 or 'latex' in sys.argv:

    # Setup a translator writer

    from docutils.writers.latex2e import Writer
    latex_writer = Writer()

    # Translate reST to latex

    latex = publish_string(reST, writer=latex_writer)

    print('Latex:')
    print(latex)

    print()

if len(sys.argv) == 1 or 'xml' in sys.argv:

    # Setup a translator writer

    from docutils.writers.docutils_xml import Writer
    xml_writer = Writer()

    # Translate reST to pdf

    xml = publish_string(reST, writer=xml_writer)

    print('XML:')
    print(xml)

