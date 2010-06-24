#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html - html helper functions
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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
                           'title': 'Dashboard', 
                           'hover': 'this is the overview page to start with'}
menu_items['submitjob'] = {'class': 'submitjob', 'url': 'submitjob.py',
                           'title': 'Submit Job',
                           'hover': 'submit a job for execution on a resource'}
menu_items['files'] = {'class': 'files', 'url': 'fileman.py', 'title': 'Files',
                           'hover': 'manage files and folders in your home directory'}
menu_items['jobs'] = {'class': 'jobs', 'url': 'jobman.py', 'title': 'Jobs', 
                           'hover': 'manage and monitor your grid jobs'}
menu_items['vgrids'] = {'class': 'vgrids', 'url': 'vgridadmin.py',
                        'title': 'VGrids',
                           'hover': 'virtual organisations sharing some resources and files'}
menu_items['resources'] = {'class': 'resources', 'url': 'resman.py',
                           'title': 'Resources',
                           'hover': 'Resources available in the system'}
menu_items['downloads'] = {'class': 'downloads', 'url': 'downloads.py',
                           'title': 'Downloads',
                           'hover': 'download scripts to work directly from your local machine'}
menu_items['runtimeenvs'] = {'class': 'runtimeenvs', 'url': 'redb.py',
                             'title': 'Runtime Envs', 
                           'hover': 'runtime environments: software which can be made available'}
menu_items['settings'] = {'class': 'settings', 'url': 'settings.py',
                          'title': 'Settings',
                           'hover': 'your personal settings for these pages'}
menu_items['shell'] = {'class': 'shell', 'url': 'shell.py', 'title': 'Shell', 
                           'hover': 'a command line interface, based on javascript and xmlrpc'}
menu_items['wshell'] = {'class': 'shell',
    'url': 'javascript:\
             window.open(\'shell.py?menu=no\',\'shellwindow\',\
             \'dependent=yes,menubar=no,status=no,toolbar=no,\
               height=650px,width=800px\');\
             window.reload();',
    'title': 'Shell',
    'hover': 'a command line interface, based on javascript and xmlrpc. Opens in a new window'}
menu_items['statistics'] = {'class': 'statistics', 'url': 'showstats.py',
                          'title': 'Statistics',
                           'hover': 'usage overview for resources and users on this server'}
menu_items['docs'] = {'class': 'docs', 'url': 'docs.py',
                          'title': 'Docs',
                          'hover': 'some built-in documentation for reference'}


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
                current_element='Unknown',
                user_menu=[]):
    """Render the menu contents using configuration"""

    raw_order = configuration.site_default_menu + user_menu
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
        menu_lines += '   <li %s class="%s"><a href="%s" %s title="%s">%s</a></li>\n'\
             % (spec.get('attr', ''), spec['class'], spec['url'], selected,
                spec.get('hover',''), spec['title'])

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
    widgets=True,
    user_menu=[],
    user_widgets={},
    ):
    """Return the html tags to mark the beginning of a page."""
    
    if not html:
        return ''
    menu_lines = ''
    if menu:
        current_page = os.path.basename(sys.argv[0]).replace('.py', '')
        menu_lines = render_menu(configuration, 'navmenu', current_page, user_menu)

    user_scripts = ''
    pre_menu = ''
    post_menu = ''
    pre_content = ''
    if widgets:
        script_deps = user_widgets.get('SITE_SCRIPT_DEPS', [''])
        pre_menu = '\n'.join(user_widgets.get('PREMENU', ['<!-- empty -->']))
        post_menu = '\n'.join(user_widgets.get('POSTMENU', ['<!-- empty -->']))
        pre_content = '\n'.join(user_widgets.get('PRECONTENT', ['<!-- empty -->']))
        for dep in script_deps:
            # Avoid reloading already included scripts
            if dep and scripts.find(dep) == -1:
                if dep.endswith('.js'):
                    user_scripts += '''
<script type="text/javascript" src="/images/js/%s"></script>
''' % dep
                elif dep.endswith('.css'):
                    user_scripts += '''
<link rel="stylesheet" type="text/css" href="/images/css/%s" media="screen"/>
''' % dep
    
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>

<link rel="icon" type="image/vnd.microsoft.icon" href="%s"/>

%s
<!-- begin user supplied script dependencies -->
%s
<!-- end user supplied script dependencies -->
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
<div class="menublock">
<div class="premenuwidgets">
<!-- begin user supplied pre menu widgets -->
%s
<!-- end user supplied pre menu widgets -->
</div>
%s
<div class="postmenuwidgets">
<!-- begin user supplied post menu widgets -->
%s
<!-- end user supplied post menu widgets -->
</div>
</div>
<div class="contentblock">
<div class="precontentwidgets">
<!-- begin user supplied pre content widgets -->
%s
<!-- end user supplied pre content widgets -->
</div>
<div id="migheader">
%s
</div>
<div id="content">
    '''\
         % (configuration.site_default_css, configuration.site_user_css,
            configuration.site_fav_icon, scripts, user_scripts, title,
            bodyfunctions, configuration.site_logo_image,
            configuration.site_logo_text, pre_menu, menu_lines,
            post_menu, pre_content, header)


def get_cgi_html_footer(configuration, footer='', html=True, widgets=True, user_widgets={}):
    """Return the html tags to mark the end of a page. If a footer string
    is supplied it is inserted at the bottom of the page.
    """

    if not html:
        return ''

    post_content = ''
    if widgets:
        post_content = '\n'.join(user_widgets.get('POSTCONTENT', ['<!-- empty -->']))

    out = '''
</div>
<div class="postcontentwidgets">
<!-- begin user supplied post content widgets -->
%s
<!-- end user supplied post content widgets -->
</div>
</div>''' % post_content
    out += footer
    out += '''
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
