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

        self.assertIsValidHtmlDocument(value)

        # TODO: this is a definitively stop-gap way of finding a tag within the HTML
        #       and is used purely to keep this initial change to a reasonable size.

        tag_open = ''.join(['<', tag_name, '>'])
        tag_open_index = value.index(tag_open)
        tag_open_index_after = tag_open_index + len(tag_open)

        tag_close = ''.join(['</', tag_name, '>'])
        tag_close_index = value.index(tag_close, tag_open_index_after)

        return value[tag_open_index_after:tag_close_index]

    def assertHtmlElementTextContent(self, value, tag_name, expected_text, trim_newlines=True):
        """Check there is an occurrence of a tag within an HTML input string
        and check the text it encloses equals exactly the expecatation.
        """

        self.assertIsValidHtmlDocument(value)

        # TODO: this is a definitively stop-gap way of finding a tag within the HTML
        #       and is used purely to keep this initial change to a reasonable size.

        actual_text = self.assertHtmlElement(value, tag_name)
        if trim_newlines:
            actual_text = actual_text.strip('\n')
        self.assertEqual(actual_text, expected_text)

    def assertIsValidHtmlDocument(self, value):
        """Check that the input string contains a valid HTML document.
        """

        assert isinstance(value, type(u"")), "input string was not utf8"

        error = None
        try:
            has_doctype = value.startswith("<!DOCTYPE html")
            assert has_doctype, "no valid document opener"
            end_html_tag_idx = value.rfind('</html>')
            maybe_document_end = value[end_html_tag_idx:].rstrip()
            assert maybe_document_end == '</html>', "no valid document closer"
        except Exception as exc:
            error = exc
        if error:
            raise AssertionError("failed to verify input string as HTML: %s", str(error))
