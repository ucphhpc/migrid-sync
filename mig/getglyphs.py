#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# getglyphs - a simple helper to lookup common accented characters to accept
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Lookup accented characters to allow in safeinput.

Usage:
./getglyphs.py http://practicaltypography.com/common-accented-characters.html
"""

from __future__ import print_function

import os
import sys
import HTMLParser

from mig.shared.url import urlopen


class GlyphParser(HTMLParser.HTMLParser):
    """Extract glyph tag content from html document"""

    in_glyph = False
    glyphs = []

    def handle_starttag(self, tag, attrs):
        """Handle start tag"""
        #print "Encountered a start tag:", tag
        if tag.lower() == 'glyph':
            self.in_glyph = True

    def handle_endtag(self, tag):
        """Handle end tag"""
        #print "Encountered an end tag :", tag
        self.in_glyph = False

    def handle_data(self, data):
        """Handle data tag"""
        #print "Encountered some data  :", data
        if self.in_glyph:
            self.glyphs.append(data)


if __name__ == '__main__':
    if not sys.argv[1:]:
        print("Usage: %s URL")
        print("Please refer to inline documentation in script")
        sys.exit(1)
    url = sys.argv[1]
    print("Looking up glyphs from %s" % url)
    web_sock = urlopen(url)
    out = web_sock.read()
    web_sock.close()
    parser = GlyphParser()
    parser.feed(out)
    print("Found glyphs:\n%s" % ''.join(parser.glyphs))
