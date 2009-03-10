#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html - [insert a few words of module description on this line]
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

"""HTML formatting functions"""


def html_print(formatted_text, html=True):
    print html_add(formatted_text, html)


def html_add(formatted_text, html=True):
    """Convenience function to only append html formatting to a text
    string in html mode"""

    if html:
        return formatted_text
    else:
        return ''


# TODO: scripts variable is only last in var list for
# backward-compatibility


def get_cgi_html_header(
    title,
    header,
    html=True,
    scripts='',
    bodyfunctions='',
    menu=True,
    ):
    """Return the html tags to mark the beginning of a page."""

    if not html:
        return ''
    menu_lines = ''
    if menu:
        menu_lines = \
            '''
<div id="mignavmenu">
<ul id="mignavlist">
<li class="submitjob">
<a href="/cgi-bin/submitjob.py">Submit Job</a>
</li>
<li class="files">
<a href="/cgi-bin/ls.py?flags=a">Files</a>
</li>
<li class="jobs">
<a href="/cgi-bin/managejobs.py">Jobs</a>
</li>
<li class="vgrids">
<a href="/cgi-bin/vgridadmin.py">VGrids</a>
</li>
<li class="resources">
<a href="/cgi-bin/resadmin.py">Resources</a>
</li>
<li class="downloads">
<a href="/cgi-bin/downloads.py">Downloads</a>
</li>
<li class="runtimeenvs">
<a href="/cgi-bin/redb.py">Runtime Envs</a>
</li>
<li class="settings">
<a href="/cgi-bin/settings.py">Settings</a>
</li>
<li class="shell">
<a href="/cgi-bin/shell.py">Shell</a>
</li>
</ul>
</div>
'''

    return '''<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<link rel="stylesheet" type="text/css" href="/images/migcss.css" media="screen"/>
<title>
 %s
 </title>
 %s
 <SCRIPT TYPE="text/javascript" SRC="/images/backlink.js"></SCRIPT>
 </head>
<body %s>
<div id="toplogo">
<img src="/images/MiG-logo.png" id="logoimage" alt=""/>
</div>
%s
<div id="migheader">
%s
</div>
<div id="content">
    '''\
         % (title, scripts, bodyfunctions, menu_lines, header)


def get_cgi_html_footer(footer='', html=True):
    """Return the html tags to mark the end of a page. If a footer string
    is supplied it is inserted at the bottom of the page.
    """

    if not html:
        return ''

    out = footer
    out += \
        '''
</div>
<br><br>
<div id="credits">This page is made for
  the <a href="http://www.migrid.org">MiG project</a><br>
  All rights reserved.
</div>
        </body>
</html>
'''
    return out


# Wrappers used during transition phase - replace with
# get_cgi_html_X contents when cgi-scripts all use add_cgi_html_X
# instead of if printhtml: print get_cgi_html_X


def add_cgi_html_header(
    title,
    header,
    html=True,
    scripts='',
    ):

    if html:
        print get_cgi_html_header(title, header, html, scripts)


def add_cgi_html_footer(footer, html=True):
    if html:
        print get_cgi_html_footer(footer, html)


def html_encode(raw_string):
    result = raw_string.replace("'", '&#039;')
    result = result.replace('"', '&#034;')
    return result


# TODO: remove these backwards compatibility names

addMiGhtmlHeader = add_cgi_html_header
addMiGhtmlFooter = add_cgi_html_footer
htmlEncode = html_encode
