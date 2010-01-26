#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html - html helper functions
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

import os
import sys


# Define all possible menu items
menu_items = {}
menu_items['dashboard'] = {'class': 'dashboard', 'url': 'dashboard.py',
                           'title': 'Dashboard'}
menu_items['submitjob'] = {'class': 'submitjob', 'url': 'submitjob.py',
                           'title': 'Submit Job'}
menu_items['files'] = {'class': 'files', 'url': 'fileman.py', 'title': 'Files'}
menu_items['jobs'] = {'class': 'jobs', 'url': 'jobman.py', 'title': 'Jobs'}
menu_items['vgrids'] = {'class': 'vgrids', 'url': 'vgridadmin.py',
                        'title': 'VGrids'}
menu_items['resources'] = {'class': 'resources', 'url': 'resadmin.py',
                           'title': 'Resources'}
menu_items['downloads'] = {'class': 'downloads', 'url': 'downloads.py',
                           'title': 'Downloads'}
menu_items['runtimeenvs'] = {'class': 'runtimeenvs', 'url': 'redb.py',
                             'title': 'Runtime Envs'}
menu_items['settings'] = {'class': 'settings', 'url': 'settings.py',
                          'title': 'Settings'}
menu_items['shell'] = {'class': 'shell', 'url': 'shell.py', 'title': 'Shell'}


def html_print(formatted_text, html=True):
    print html_add(formatted_text, html)


def html_add(formatted_text, html=True):
    """Convenience function to only append html formatting to a text
    string in html mode"""

    if html:
        return formatted_text
    else:
        return ''


def render_menu(configuration, menu_class='navmenu', 
                current_element='Unknown'):
    """Render the menu contents using configuration"""

    raw_order = configuration.site_default_menu + configuration.site_user_menu
    menu_order = []
    # Remove duplicates
    for name in raw_order:
        if not name in menu_order:
            menu_order.append(name)

    menu_lines = '<div class="%s">\n' % menu_class
    menu_lines += ' <ul>\n'
    for name in menu_order:
        spec = menu_items.get(name, None)
        if not spec:
            menu_lines += '   <!-- No such menu item: "%s" !!! -->\n' % name
            continue
        selected = ''
        if spec['url'].find(current_element) > -1:
            selected = ' class="selected" '
        menu_lines += '   <li %s class="%s"><a href="%s" %s>%s</a></li>\n'\
             % (spec.get('attr', ''), spec['class'], spec['url'], selected,
                spec['title'])

    menu_lines += ' </ul>\n'
    menu_lines += '</div>\n'

    return menu_lines


def get_cgi_html_header(
    configuration,
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
        current_page = os.path.basename(sys.argv[0]).replace('.py', '')
        menu_lines = render_menu(configuration, 'navmenu', current_page)

    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>

<link rel="icon" type="image/vnd.microsoft.icon" href="%s"/>

%s
<title>
%s
</title>
</head>
<body %s>
<div id="topspace">
</div>
<div id="toplogo">
<img src="%s" id="logoimage" alt="site logo"/>
<span id="logotitle">
%s
</span>
</div>
%s
<div id="migheader">
%s
</div>
<div id="content">
    '''\
         % (configuration.site_default_css, configuration.site_user_css,
            configuration.site_fav_icon, scripts, title,
            bodyfunctions, configuration.site_logo_image,
            configuration.site_logo_text, menu_lines, header)


def get_cgi_html_footer(configuration, footer='', html=True):
    """Return the html tags to mark the end of a page. If a footer string
    is supplied it is inserted at the bottom of the page.
    """

    if not html:
        return ''

    out = footer
    out += '''
</div>
<div id="bottomlogo">
<img src="%s" id="creditsimage" alt=""/>
<span id="credits">
%s
</span>
</div>
<div id="bottomspace">
</div>
</body>
</html>
''' % (configuration.site_credits_image, configuration.site_credits_text)
    return out


def html_encode(raw_string):
    """Encode some common reserved html characters"""
    result = raw_string.replace("'", '&#039;')
    result = result.replace('"', '&#034;')
    return result

