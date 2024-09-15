#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# htmlsupp - test support library for HTML
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

"""Test support library for HTML."""


class HtmlAssertMixin:
    """Custom assertions for HTML containing strings."""

    def assertHtmlElement(self, value, tag_name):
        """Check that an occurrence of the specifid tag within an HTML input
        string can be found. Returns the textual content of the first match.
        """

        self.assertIsValidHtmlDocument(value, permit_no_close=True)

        # TODO: this is a definitively stop-gap way of finding a tag within the HTML
        #       and is used purely to keep this initial change to a reasonable size.

        tag_open = ''.join(['<', tag_name, '>'])
        tag_open_index = value.index(tag_open)
        tag_open_index_after = tag_open_index + len(tag_open)

        tag_close = ''.join(['</', tag_name, '>'])
        tag_close_index = value.index(tag_close, tag_open_index_after)

        return value[tag_open_index_after:tag_close_index]

    def assertIsValidHtmlDocument(self, value, permit_no_close=False):
        """Check that the input string contains a valid HTML document.
        """

        assert isinstance(value, type(u""))

        error = None
        try:
            has_doctype = value.startswith("<!DOCTYPE html") or value.startswith("<!doctype html")
            assert has_doctype, "no valid document opener"
            end_html_tag_idx = value.rfind('</html>')
            if end_html_tag_idx == -1 and permit_no_close:
                return
            maybe_document_end = value[end_html_tag_idx:].rstrip()
            assert maybe_document_end == '</html>', "no valid document closer"
        except Exception as exc:
            error = exc
        if error:
            raise AssertionError("failed to verify input string as HTML: %s", str(error))
