#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html_writer - [insert a few words of module description on this line]
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
from docutils.writers.html4css1 import Writer, HTMLTranslator
from docutils.core import publish_string

# Setup a translator writer

html_writer = Writer()
html_writer.translator_class = HTMLTranslator

# Setup a restructured text example

reST = \
    """
Example of reST:
================

This is a small example of the way reST can be used as a base for generating HTMLformatted text that:

- looks nice
- is standards compliant
- is flexible

We *may* decide to start using this as text formatting tool in MiG__ later on.

__ http://mig-1.imada.sdu.dk/


We can also use it for creating tables if we want to:

=====  =====  ======
Input         Output
-----  -----  ------
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

# Translate reST to html

html = publish_string(reST, settings_overrides={'output_encoding'
                      : 'unicode'}, writer=html_writer)

print(html)

