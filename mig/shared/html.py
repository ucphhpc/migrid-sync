#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html - html helper functions
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

from shared.base import requested_page
from shared.defaults import default_pager_entries, trash_linkname, csrf_field

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
menu_items['vgrids'] = {'class': 'vgrids', 'url': 'vgridman.py',
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
menu_items['archives'] = {'class': 'archives', 'url': 'freezedb.py',
                             'title': 'Archives', 
                           'hover': 'frozen archives: write-once file archives'}
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
menu_items['people'] = {'class': 'people', 'url': 'people.py',
                           'title': 'People', 
                           'hover': 'view and communicate with other users'}
menu_items['migadmin'] = {'class': 'migadmin', 'url': 'migadmin.py',
                           'title': 'Server Admin', 
                           'hover': 'administrate this MiG server'}
menu_items['vmachines'] = {'class': 'vmachines', 'url': 'vmachines.py',
                           'title': 'Virtual Machines', 
                           'hover': 'Manage Virtual Machines'}
menu_items['vmrequest'] = {'class': 'vmrequest', 'url': 'vmrequest.py',
                           'title': 'Request Virtual Machine', 
                           'hover': 'Request Virtual Machine'}
menu_items['vmconnect'] = {'class': 'vmconnect', 'url': 'vmconnect.py',
                           'title': 'Connect to Virtual Machine', 
                           'hover': 'Connect to Virtual Machine'}
menu_items['logout'] = {'class': 'logout', 'url': 'logout.py',
                           'title': 'Logout', 
                           'hover': 'Logout'}

# Define all possible VGrid page columns
vgrid_items = {}
vgrid_items['files'] = {'class': 'vgridfiles', 'title': 'Files', 
                        'hover': 'Open shared files'}
vgrid_items['web'] = {'class': 'vgridweb', 'title': 'Web Pages', 
                      'hover': 'View/edit private and public web pages'}
vgrid_items['scm'] = {'class': 'vgridscm', 'title': 'SCM', 
                      'hover':
                      'Inspect private and public Source Code Management systems'}
vgrid_items['tracker'] = {'class': 'vgridtracker', 'title': 'Tracker Tools', 
                          'hover': 'Open private and public project collaboration tools'}
vgrid_items['forum'] = {'class': 'vgridforum', 'title': 'Forum', 
                        'hover': 'Enter private forum'}
vgrid_items['workflows'] = {'class': 'vgridworkflows', 'title': 'Workflows', 
                            'hover': 'Enter private workflows'}
vgrid_items['monitor'] = {'class': 'vgridmonitor', 'title': 'Monitor', 
                          'hover': 'Open private resource monitor'}

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
                current_element='Unknown', base_menu=[],
                user_menu=[]):
    """Render the menu contents using configuration"""

    raw_order = []
    raw_order += base_menu
    raw_order += user_menu
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
        # Override VGrids label now we have configuration
        if name == 'vgrids':
            title = spec['title'].replace('VGrid',
                                          configuration.site_vgrid_label)
            hover = spec['hover'].replace('VGrid',
                                          configuration.site_vgrid_label)
            spec['title'] = title
            spec['hover'] = hover
        selected = ''
        if spec['url'].find(current_element) > -1:
            selected = ' class="selected" '
        menu_lines += '   <li %s class="%s"><a href="%s" %s title="%s">%s</a></li>\n'\
             % (spec.get('attr', ''), spec['class'], spec['url'], selected,
                spec.get('hover',''), spec['title'])

    menu_lines += ' </ul>\n'
    menu_lines += '</div>\n'

    return menu_lines


def get_css_helpers(configuration):
    """Returns a dictionary of string expansion helpers for css"""
    return {'base_prefix': os.path.join(configuration.site_images, 'css'),
            'advanced_prefix': os.path.join(configuration.site_images, 'css'),
            'skin_prefix': configuration.site_skin_base}

def extend_styles(configuration, styles, base=[], advanced=[], skin=[]):
    """Appends any stylesheets specified in the base, advanced and skin lists
    in the corresponding sections of the styles dictionary.
    """
    css_helpers = get_css_helpers(configuration)
    for name in base:
        css_helpers['name'] = name
        styles['base'] += '''
<link rel="stylesheet" type="text/css" href="%(base_prefix)s/%(name)s" media="screen"/>
''' % css_helpers
    for name in advanced:
        css_helpers['name'] = name
        styles['advanced'] += '''
<link rel="stylesheet" type="text/css" href="%(advanced_prefix)s/%(name)s" media="screen"/>
''' % css_helpers
    for name in skin:
        css_helpers['name'] = name
        styles['skin'] += '''
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/%(name)s" media="screen"/>
''' % css_helpers

def base_styles(configuration, base=[], advanced=[], skin=[]):
    """Returns a dictionary of basic stylesheets for unthemed pages"""
    css_helpers = get_css_helpers(configuration)
    styles = {'base': '', 'advanced': '', 'skin': ''}
    extend_styles(configuration, styles, base, advanced, skin)
    return styles

def themed_styles(configuration, base=[], advanced=[], skin=[]):
    """Returns a dictionary of basic stylesheets for themed JQuery UI pages.
    Appends any stylesheets specified in the base, advanced and skin lists.
    """
    css_helpers = get_css_helpers(configuration)
    styles = {'base': '''
<link rel="stylesheet" type="text/css" href="%(base_prefix)s/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(base_prefix)s/jquery.managers.css" media="screen"/>
''' % css_helpers,
              'advanced': '',
              'skin': '''
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/core.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-theme.custom.css" media="screen"/>
''' % css_helpers
              }
    extend_styles(configuration, styles, base, advanced, skin)
    return styles

def jquery_ui_js(configuration, js_import, js_init, js_ready):
    """Fill standard javascript template for JQuery UI pages. The three args
    add custom extra javascript in the usual load, init and ready phase used
    with jquery pages.
    """
    return '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
%(js_import)s
<script type="text/javascript" >

    %(js_init)s
    
    $(document).ready( function() {
         //console.log("document ready handler");
         %(js_ready)s
    });

</script>
''' % {'js_import': js_import, 'js_init': js_init, 'js_ready': js_ready}
            
def tablesorter_js(configuration, tables_list=[], include_ajax=True):
    """Build standard tablesorter dependency imports, init and ready snippets.
    The tables_list contains one or more table definitions with id and options
    to intitialize the table(s) with.
    The optional include_ajax option can be used to disable the AJAX loading
    setup needed by most managers.
    """
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js">
</script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
    '''
    if include_ajax:
        add_import += '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>
        '''

    add_init = ''
    add_ready = ''
    for table_dict in tables_list:
        add_ready += '''
        %(tablesort_init)s

        $("#%(table_id)s").tablesorter(%(tablesort_args)s).tablesorterPager(%(pager_args)s);
        %(pager_init)s
        %(refresh_init)s
        ''' % table_dict
    return (add_import, add_init, add_ready)

def confirm_js(configuration, width=500):
    """Build standard confirm dialog dependency imports, init and ready
    snippets.
    """
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>
    '''
    add_init = ''
    add_ready = '''
          // init confirmation dialog
          $( "#confirm_dialog" ).dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: %d,
                buttons: {
                   "Cancel": function() { $( "#" + name ).dialog("close"); }
                }
              });
    ''' % width
    return (add_import, add_init, add_ready)    

def confirm_html(configuration, rows=4, cols=40, cls="fillwidth padspace"):
    """Build standard js filled confirm overlay dialog html"""
    html = '''
    <div id="confirm_dialog" title="Confirm" style="background:#fff;">
        <div id="confirm_text"><!-- filled by js --></div>
        <textarea class="%s" cols="%s" rows="%s" id="confirm_input"
       style="display:none;"></textarea>
    </div>
    ''' % (cls, cols, rows)
    return html

def man_base_js(configuration, table_dicts, overrides={}):
    """Build base js for managers, i.e. dependency imports, init and ready
    snippets. The table_dicts argument is a list of table dictionaries to set
    up tablesorter and pager for. They come with common defaults for things
    like sorting and pager, but can contain complete setting if needed.
    """
    confirm_overrides = {}
    for name in ('width', ):
        if overrides.has_key(name):
            confirm_overrides[name] = overrides[name]
    filled_table_dicts = []
    tablesort_init = '''
        // initial table sorting column and direction is %(sort_order)s.
        // use image path for sorting if there is any inside
        var imgTitle = function(contents) {
            var key = $(contents).find("a").attr("class");
            if (key == null) {
                key = $(contents).html();
            }
            return key;
        }
    '''
    tablesort_args = '''{widgets: ["zebra", "saveSort"],
                         sortList: %(sort_order)s,
                         textExtraction: imgTitle
                         }'''
    pager_args = '''{container: $("#%(pager_id)s"),
                     size: %(pager_entries)d
                     }'''
    pager_init = '''$("#%(pager_id)srefresh").click(function() {
                        %(pager_id)s_refresh();
                    });
    '''
    refresh_init = '''function %(pager_id)s_refresh() {
    %(refresh_call)s;
}
'''
    for entry in table_dicts:
        filled = {'table_id': entry.get('table_id', 'managertable'),
                  'pager_id': entry.get('pager_id', 'pager'), 
                  'sort_order': entry.get('sort_order', '[[0,1]]'),
                  'pager_entries': entry.get('pager_entries',
                                             default_pager_entries),
                  'refresh_call': entry.get('refresh_call',
                                            'location.reload()')}
        filled.update({'tablesort_init': tablesort_init % filled,
                       'tablesort_args': tablesort_args % filled,
                       'pager_args': pager_args % filled,
                       'pager_init': pager_init % filled,
                       'refresh_init': refresh_init % filled
                       })
        filled.update(entry)
        filled_table_dicts.append(filled)
    (cf_import, cf_init, cf_ready) = confirm_js(configuration,
                                                **confirm_overrides)
    (ts_import, ts_init, ts_ready) = tablesorter_js(configuration,
                                                    filled_table_dicts)
    add_import = '''
%s
%s
    ''' % (cf_import, ts_import)
    add_init = '''
%s
%s
    ''' % (cf_init, ts_init)
    add_ready = '''
%s
%s
    ''' % (cf_ready, ts_ready)
    return (add_import, add_init, add_ready)

def man_base_html(configuration, overrides={}):
    """Build base html skeleton for js-filled managers, i.e. prepare confirm
    dialog and a table with dynamic tablesorter and pager.
    """
    confirm_overrides = {}
    for name in ('rows', 'cols', ):
        if overrides.has_key(name):
            confirm_overrides[name] = overrides[name]
    return confirm_html(configuration, **confirm_overrides)

def fancy_upload_js(configuration, callback=None, share_id='', csrf_token=''):
    """Build standard fancy upload dependency imports, init and ready
    snippets.
    """
    # callback must be a function
    if not callback:
        callback = 'function() { return false; }'
    add_import = '''
<!--  Filemanager is only needed for fancy upload init wrapper -->
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>

<!-- Fancy file uploader and dependencies -->
<!-- The Templates plugin is included to render the upload/download listings -->
<script type="text/javascript" src="/images/js/tmpl.min.js"></script>
<!-- The Load Image plugin is included for the preview images and image resizing functionality -->
<script type="text/javascript" src="/images/js/load-image.min.js"></script>
<!-- The Iframe Transport is required for browsers without support for XHR file uploads -->
<script type="text/javascript" src="/images/js/jquery.iframe-transport.js"></script>
<!-- The basic File Upload plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload.js"></script>
<!-- The File Upload processing plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-process.js"></script>
<!-- The File Upload image preview & resize plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-image.js"></script>
<!-- The File Upload validation plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-validate.js"></script>
<!-- The File Upload user interface plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-ui.js"></script>
<!-- The File Upload jQuery UI plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-jquery-ui.js"></script>

<!-- The template to display files available for upload -->
<script id="template-upload" type="text/x-tmpl">
{% console.log("using upload template"); %}
{% console.log("... with upload files: "+$.fn.dump(o)); %}
{% var dest_dir = "./" + $("#fancyfileuploaddest").val(); %}
{% console.log("using upload dest: "+dest_dir); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath(dest_dir+"/"+file.name); %}
    {% console.log("using upload rel_path: "+rel_path); %}
    <tr class="template-upload fade">
        <td>
            <span class="preview"></span>
        </td>
        <td>
            <p class="name">{%=rel_path%}</p>
            <strong class="error"></strong>
        </td>
        <td>
            <div class="size pending">Processing...</div>
            <div class="progress"></div>
        </td>
        <td>
            {% if (!i && !o.options.autoUpload) { %}
                <button class="start" disabled>Start</button>
            {% } %}
            {% if (!i) { %}
                <button class="cancel">Cancel</button>
            {% } %}
        </td>
    </tr>
{% } %}
</script>
<!-- The template to display files available for download -->
<script id="template-download" type="text/x-tmpl">
{% console.log("using download template"); %}
{% console.log("... with download files: "+$.fn.dump(o)); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath("./"+file.name); %}
    {% var plain_name = rel_path.substring(rel_path.lastIndexOf("/") + 1); %}
    {% console.log("using download rel_path: "+rel_path); %}
    {% console.log("original delete URL: "+file.deleteUrl); %}
    {% function encodeName(str, match) { return "filename="+encodeURIComponent(match)+";files"; }  %}
    {% if (file.deleteUrl != undefined) { file.deleteUrl = file.deleteUrl.replace(/filename\=(.+)\;files/, encodeName); console.debug("updated delete URL: "+file.deleteUrl); } %}    
    <tr class="template-download fade">
        <td>
            <span class="preview">
                {% if (file.thumbnailUrl) { %}
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=plain_name%}" data-gallery><img src="{%=file.thumbnailUrl%}"></a>
                {% } %}
            </span>
        </td>
        <td>
            <p class="name">
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=plain_name%}" {%=file.thumbnailUrl?\'data-gallery\':\'\'%}>{%=rel_path%}</a>
            </p>
            {% if (file.error) { %}
                <div><span class="error">Error</span> {%=file.error%}</div>
            {% } %}
        </td>
        <td>
            <div class="size">{%=o.formatFileSize(file.size)%}</div>
        </td>
        <td>
            <button class="delete" data-type="{%=file.deleteType%}" data-url="{%=file.deleteUrl%}"{% if (file.deleteWithCredentials) { %} data-xhr-fields=\'{"withCredentials":true}\'{% } %}>{% if (file.deleteUrl) { %}Delete{% } else { %}Dismiss{% } %}</button>
            <input type="checkbox" name="delete" value="1" class="toggle">
        </td>
    </tr>
{% } %}
</script>
    '''
    add_init = '''
    var trash_linkname = "%(trash_linkname)s";
    var csrf_field = "%(csrf_field)s";

    /* Default fancy upload dest - optionally override before open_dialog call */
    var remote_path = ".";
    function setUploadDest(path) {
        remote_path = path;
    }
    function openFancyUpload() {
        var open_dialog = mig_fancyuploadchunked_init("fancyuploadchunked_dialog");
        open_dialog("Upload Files", %(callback)s, remote_path, false, 
                    "%(share_id)s", "%(csrf_token)s");
    }
    ''' % {"callback": callback, "share_id": share_id,
           "trash_linkname": trash_linkname, "csrf_field": csrf_field,
           "csrf_token": csrf_token}
    add_ready = ''
    return (add_import, add_init, add_ready)

def fancy_upload_html(configuration):
    """Build standard html fancy upload overlay dialog"""
    html = """
    <div id='fancyuploadchunked_dialog' title='Upload File' style='display: none;'>

    <!-- The file upload form used as target for the file upload widget -->
    <!-- IMPORTANT: the form action and hidden args are set in upload JS -->
    <form id='fancyfileupload' enctype='multipart/form-data' method='post'
        action='uploadchunked.py'>
        <fieldset id='fancyfileuploaddestbox'>
            <label id='fancyfileuploaddestlabel' for='fancyfileuploaddest'>
                Optional final destination dir:
            </label>
            <input id='fancyfileuploaddest' type='text' size=60 value=''>
        </fieldset>

        <!-- The fileupload-buttonbar contains buttons to add/delete files and
            start/cancel the upload -->
        <div class='fileupload-buttonbar'>
            <div class='fileupload-buttons'>
                <!-- The fileinput-button span is used to style the file input
                    field as button -->
                <span class='fileinput-button'>
                    <span>Add files...</span>
                    <input type='file' name='files[]' multiple>
                </span>
                <button type='submit' class='start'>Start upload</button>
                <button type='reset' class='cancel'>Cancel upload</button>
                <button type='button' class='delete'>Delete</button>
                <input type='checkbox' class='toggle'>
                <!-- The global file processing state -->
                <span class='fileupload-process'></span>
            </div>
            <!-- The global progress state -->
            <div class='fileupload-progress fade' style='display:none'>
                <!-- The global progress bar -->
                <div class='progress' role='progressbar' aria-valuemin='0'
                    aria-valuemax='100'></div>
                <!-- The extended global progress state -->
                <div class='progress-extended'>&nbsp;</div>
            </div>
        </div>
        <!-- The table listing the files available for upload/download -->
        <table role='presentation' class='table table-striped'>
        <tbody class='uploadfileslist'></tbody></table>
    </form>
    <!-- For status and error output messages -->
    <div id='fancyuploadchunked_output'></div>
    </div>
    """
    return html

def get_cgi_html_preamble(
    configuration,
    title,
    header,
    meta='',
    base_styles='',
    advanced_styles='',
    skin_styles='',
    scripts='',
    widgets=True,
    userstyle=True,
    user_widgets={},
    ):
    """Return the html tags to mark the beginning of a page."""
    
    user_styles = ''
    user_scripts = ''
    if widgets:
        script_deps = user_widgets.get('SITE_SCRIPT_DEPS', [''])
        for dep in script_deps:
            # Avoid reloading already included scripts
            if dep and scripts.find(dep) == -1:
                if dep.endswith('.js'):
                    user_scripts += '''
<script type="text/javascript" src="/images/js/%s"></script>
''' % dep
                elif dep.endswith('.css'):
                    user_styles += '''
<link rel="stylesheet" type="text/css" href="/images/css/%s" media="screen"/>
''' % dep

    style_overrides = ''
    if userstyle:
        style_overrides = '''
<!-- finally override with user-specific styles -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>
''' % configuration.site_user_css

    # Please note that we insert user widget styles after our own styles even
    # though it means that dependencies may override defaults (e.g. zss* and
    # jobman even/odd color. Such style clashes should be solved elsewhere.

    # Use HTML5
    out = '''<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
<!-- page specific meta tags -->
%s

<!-- site default style -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>

<!-- site static skin style -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>

<!-- base page styles -->
%s
<!-- advanced page styles -->
%s
<!-- skin page styles -->
%s

<!-- begin user supplied style dependencies -->
%s
<!-- end user supplied style dependencies -->

<!-- override with any site-specific styles -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>
%s

<link rel="icon" type="image/vnd.microsoft.icon" href="%s"/>

<!-- specific page scripts -->
%s

<!-- begin user supplied script dependencies -->
%s
<!-- end user supplied script dependencies -->
<title>
%s
</title>
</head>
''' % (meta, configuration.site_default_css, configuration.site_static_css,
       base_styles, advanced_styles, skin_styles, user_styles,
       configuration.site_custom_css, style_overrides,
       configuration.site_fav_icon, scripts, user_scripts, title)
    return out

def get_cgi_html_header(
    configuration,
    title,
    header,
    html=True,
    meta='',
    base_styles='',
    advanced_styles='',
    skin_styles='',
    scripts='',
    bodyfunctions='',
    menu=True,
    widgets=True,
    userstyle=True,
    base_menu=[],
    user_menu=[],
    user_widgets={},
    ):
    """Return the html tags to mark the beginning of a page."""
    
    if not html:
        return ''

    user_pre_menu = ''
    user_post_menu = ''
    user_pre_content = ''
    if widgets:
        pre_menu = '\n'.join(user_widgets.get('PREMENU', ['<!-- empty -->']))
        post_menu = '\n'.join(user_widgets.get('POSTMENU', ['<!-- empty -->']))
        pre_content = '\n'.join(user_widgets.get('PRECONTENT', ['<!-- empty -->']))
        user_pre_menu = '''<div class="premenuwidgets">
<!-- begin user supplied pre menu widgets -->
%s
<!-- end user supplied pre menu widgets -->
</div>''' % pre_menu
        user_post_menu = '''<div class="postmenuwidgets">
<!-- begin user supplied post menu widgets -->
%s
<!-- end user supplied post menu widgets -->
</div>''' % post_menu
        user_pre_content = '''<div class="precontentwidgets">
<!-- begin user supplied pre content widgets -->
%s
<!-- end user supplied pre content widgets -->
</div>''' % pre_content
        
    out = get_cgi_html_preamble(configuration,
                                title,
                                header,
                                meta,
                                base_styles,
                                advanced_styles,
                                skin_styles,
                                scripts,
                                widgets,
                                userstyle,
                                user_widgets,
                                )
    out += '''
<body %s>
<div id="topspace">
</div>
<div id="toplogo">
<div id="toplogoleft">
<img src="%s" id="logoimageleft" alt="site logo left"/>
</div>
<div id="toplogocenter">
<span id="logotitle">
%s
</span>
</div>
<div id="toplogoright">
<img src="%s" id="logoimageright" alt="site logo right"/>
</div>
</div>
''' % (bodyfunctions, configuration.site_logo_left,
       configuration.site_logo_center, configuration.site_logo_right)
    menu_lines = ''
    if menu:
        maximize = ''
        current_page = os.path.basename(requested_page()).replace('.py', '')
        menu_lines = render_menu(configuration, 'navmenu', current_page,
                                 base_menu, user_menu)
        out += '''
<div class="menublock">
%s
%s
%s
</div>
''' % (user_pre_menu, menu_lines, user_post_menu)
    else:
        maximize = 'id="nomenu"'
    out += '''
<div class="contentblock" %s>
%s
<div id="migheader">
%s
</div>
<div id="content" class="i18n" lang="en">
''' % (maximize, user_pre_content, header)

    return out


def get_cgi_html_footer(configuration, footer='', html=True, widgets=True, user_widgets={}):
    """Return the html tags to mark the end of a page. If a footer string
    is supplied it is inserted at the bottom of the page.
    """

    if not html:
        return ''

    user_post_content = ''
    if widgets:
        post_content = '\n'.join(user_widgets.get('POSTCONTENT', ['<!-- empty -->']))
        user_post_content = '''
<div class="postcontentwidgets">
<!-- begin user supplied post content widgets -->
%s
<!-- end user supplied post content widgets -->
</div>
''' % post_content
    out = '''
</div>
%s
</div>''' % user_post_content
    out += footer
    out += '''
<div id="bottomlogo">
<div id="bottomlogoleft">
<div id="support">
<img src="%s" id="supportimage" alt=""/>
<div class="supporttext i18n" lang="en">
%s
</div>
</div>
</div>
<div id="bottomlogoright">
<div id="credits">
<img src="%s" id="creditsimage" alt=""/>
<div class="creditstext i18n" lang="en">
%s
</div>
</div>
</div>
</div>
<div id="bottomspace">
</div>
</body>
</html>
''' % (configuration.site_support_image, configuration.site_support_text,
       configuration.site_credits_image, configuration.site_credits_text)
    return out


def html_encode(raw_string):
    """Encode some common reserved html characters"""
    result = raw_string.replace("'", '&#039;')
    result = result.replace('"', '&#034;')
    return result

def html_post_helper(function_name, destination, fields):
    """Create a hidden html form and a corresponding javascript function,
    function_name, that can be called to POST the form.
    """
    html = '''<script type="text/javascript">
    function %s(input)
        {
            for(var key in input) {
                if (input.hasOwnProperty(key)) {
                    var value = input[key];
                    document.getElementById("%s"+key+"field").value = value;
                }
            }
            document.getElementById("%sform").submit();
        }
</script>
''' % (function_name, function_name, function_name)
    html += '<form id="%sform" method="post" action="%s">\n' % (function_name,
                                                                destination)
    for (key, val) in fields.items():
        html += '<input id="%s%sfield" type="hidden" name="%s" value="%s" />\n'\
                % (function_name, key, key, val)
    html += '</form>\n'
    return html

def console_log_javascript():
    """Javascript console logging: just include this and set cur_log_level before
    calling init_log() to get console.debug/info/warn/error helpers.
    """
    return '''
<script type="text/javascript" >
/* default console log verbosity defined here - change before calling init_log
to override. */
var log_level = "info";
var all_log_levels = {"none": 0, "error": 1, "warn": 2, "info": 3, "debug": 4};
/* 
   Make sure we can always use console.X without scripts crashing. IE<=9
   does not init it unless in developer mode and things thus randomly fail
   without a trace.
*/
var noOp = function(){}; // no-op function
if (!window.console) {
    console = {
	debug: noOp,
	log: noOp,
	info: noOp,
	warn: noOp,
	error: noOp
    }
}
/* 
   Make sure we can use Date.now which was not available in IE<9
*/
if (!Date.now) {
    Date.now = function now() {
        return new Date().getTime();
    };
}

/* call this function to set up console logging after log_level is set */
var init_log = function() {
    if (all_log_levels[log_level] >= all_log_levels["debug"]) {
        console.debug = function(msg) { 
            console.log(Date.now()+" DEBUG: "+msg)
            }; 
    } else {
	console.debug = noOp;
    }
    if (all_log_levels[log_level] >= all_log_levels["info"]) {
	console.info = function(msg){ 
            console.log(Date.now()+" INFO: "+msg)
            };
    } else {
	console.info = noOp;
    }
    if (all_log_levels[log_level] >= all_log_levels["warn"]) {
	console.warn = function(msg){ 
            console.log(Date.now()+" WARN: "+msg)
            };
    } else {
	console.warn = noOp;
    }
    if (all_log_levels[log_level] >= all_log_levels["error"]) {
	console.error = function(msg){ 
            console.log(Date.now()+" ERROR: "+msg)
            };
    } else {
	console.error = noOp;
    }
    console.debug("log ready");
}
</script>
'''    
