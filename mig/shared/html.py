#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# html - html helper functions
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
from shared.defaults import default_pager_entries, trash_linkname, \
    csrf_field, keyword_all

ICONS_ONLY, TEXT_ONLY = "ICONS_ONLY", "TEXT_ONLY"

# Define all possible menu items
menu_items = {}
# Old dashboard
menu_items['dashboard'] = {'class': 'dashboard fas fa-tachometer-alt', 'url': 'dashboard.py',
                           'legacy_only': True, 'title': 'Dashboard',
                           'hover': 'The original dashboard start page'}
# New dashboard replacement
menu_items['home'] = {'class': 'home fas fa-home', 'url': 'home.py',
                      'legacy_only': False, 'title': 'Home',
                      'hover': 'App overview and launch page'}
menu_items['submitjob'] = {'class': 'submitjob fas fa-running', 'url': 'submitjob.py',
                           'title': 'Submit Job',
                           'hover': 'Submit a job for execution on a resource'}
menu_items['files'] = {'class': 'files fas fa-folder', 'url': 'fileman.py', 'title': 'Files',
                       'hover': 'Manage files and folders in your home directory'}
menu_items['jobs'] = {'class': 'jobs fas fa-tasks', 'url': 'jobman.py', 'title': 'Jobs',
                      'hover': 'Manage and monitor your grid jobs'}
menu_items['vgrids'] = {'class': 'vgrids fas fa-network-wired', 'url': 'vgridman.py',
                        'title': 'VGrids',
                        'hover': 'Virtual organisations sharing some resources and files'}
menu_items['resources'] = {'class': 'resources fas fa-server', 'url': 'resman.py',
                           'title': 'Resources',
                           'hover': 'Resources available in the system'}
menu_items['downloads'] = {'class': 'downloads fas fa-download', 'url': 'downloads.py',
                           'title': 'Downloads',
                           'hover': 'Download scripts to work directly from your local machine'}
menu_items['runtimeenvs'] = {'class': 'runtimeenvs fas fa-warehouse', 'url': 'redb.py',
                             'title': 'Runtime Envs',
                             'hover': 'Runtime environments: software which can be made available'}
menu_items['archives'] = {'class': 'archives fas fa-archive', 'url': 'freezedb.py',
                          'title': 'Archives',
                          'hover': 'Frozen archives: write-once file archives'}
menu_items['settings'] = {'class': 'settings fas fa-user', 'url': 'settings.py',
                          'legacy_only': True, 'title': 'Settings',
                          'hover': 'Your personal settings for these pages'}
menu_items['setup'] = {'class': 'setup fas fa-user-cog', 'url': 'setup.py',
                       'legacy_only': True, 'title': 'Setup',
                       'hover': 'Your client access settings for this site'}
menu_items['transfers'] = {'class': 'transfers fas fa-datatransfer', 'url': 'datatransfer.py',
                           'title': 'Data Transfers',
                           'hover': 'For background batch transfers of data'}
menu_items['sharelinks'] = {'class': 'sharelinks fas fa-share-alt', 'url': 'sharelink.py',
                            'title': 'Share Links',
                            'hover': 'Manage share links for easy data exchange'}
menu_items['crontab'] = {'class': 'crontab fas fa-calendar-check', 'url': 'crontab.py',
                         'title': 'Schedule Tasks',
                         'hover': 'Your personal task scheduler'}
# NOTE: we rely on seafile location from conf and only fill it in render
menu_items['seafile'] = {'class': 'seafile fas fa-seafile', 'url': '', 'title': 'Seafile',
                         'hover': 'Access the associated Seafile service',
                         'target': '_blank'}
menu_items['jupyter'] = {'class': 'jupyter fas fa-jupyter', 'url': 'jupyter.py',
                         'title': 'Jupyter',
                         'hover': 'Access the associated Jupyter data analysis services'}
menu_items['cloud'] = {'class': 'cloud fas fa-cloud', 'url': 'cloud.py',
                       'title': 'Cloud',
                       'hover': 'Access the associated cloud computing services'}

menu_items['shell'] = {'class': 'shell fas fa-keyboard', 'url': 'shell.py', 'title': 'Shell',
                       'legacy_only': True, 'hover':
                       'A command line interface, based on javascript and xmlrpc'}
menu_items['wshell'] = {'class': 'shell  fas fa-keyboard-alt',
                        'url': 'javascript:\
             window.open(\'shell.py?menu=no\',\'shellwindow\',\
             \'dependent=yes,menubar=no,status=no,toolbar=no,\
               height=650px,width=800px\');\
             window.reload();',
                        'legacy_only': True, 'title': 'Shell',
                        'hover': 'A command line interface, based on javascript and xmlrpc. Opens in a new window'}
menu_items['statistics'] = {'class': 'statistics fas fa-poll', 'url': 'showstats.py',
                            'legacy_only': True, 'title': 'Statistics',
                            'hover': 'Usage overview for resources and users on this server'}
menu_items['docs'] = {'class': 'docs fas fa-book', 'url': 'docs.py',
                      'title': 'Docs',
                      'hover': 'Some built-in documentation for reference'}
menu_items['people'] = {'class': 'people fas fa-users', 'url': 'people.py',
                        'title': 'People',
                        'hover': 'View and communicate with other users'}
menu_items['migadmin'] = {'class': 'migadmin fas fa-user-lock', 'url': 'migadmin.py',
                          'title': 'Server Admin',
                          'hover': 'Administrate this server'}
menu_items['vmachines'] = {'class': 'vmachines fas fa-desktop',
                           'url': 'vmachines.py',
                           'title': 'Virtual Machines',
                           'hover': 'Manage Virtual Machines'}
menu_items['vmrequest'] = {'class': 'vmrequest fas fa-tv', 'url': 'vmrequest.py',
                           'title': 'Request Virtual Machine',
                           'hover': 'Request Virtual Machine'}
menu_items['vmconnect'] = {'class': 'vmconnect fas fa-plug', 'url': 'vmconnect.py',
                           'title': 'Connect to Virtual Machine',
                           'hover': 'Connect to Virtual Machine'}
menu_items['logout'] = {'class': 'logout fas fa-sign-out-alt',
                        'url': 'logout.py', 'title': 'Logout',
                        'legacy_only': True, 'hover': 'Logout'}

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


def legacy_user_interface(configuration, user_settings,
                          legacy_versions=["V1", "V2"]):
    """Helper to ease detection of legacy user interfaces"""
    # Default to first config value or V3 if explicitly unset
    active_ui = (configuration.user_interface + ['V3'])[0]
    # Please note that user_settings may be boolean False if never saved
    if user_settings:
        active_ui = user_settings.get('USER_INTERFACE', active_ui)
    if active_ui in legacy_versions:
        return True
    else:
        return False


def render_menu(configuration, menu_class='navmenu',
                current_element='Unknown', base_menu=[],
                user_menu=[], user_settings={}, display=keyword_all):
    """Render the menu contents using configuration"""

    legacy_ui = legacy_user_interface(configuration, user_settings)
    raw_order = []
    raw_order += base_menu
    raw_order += user_menu
    menu_order = []
    # Remove duplicates and force logout last
    for name in raw_order:
        if not name in menu_order and name != 'logout':
            menu_order.append(name)
    if 'logout' in raw_order:
        menu_order.append('logout')

    if legacy_ui:
        menu_wrap = '''
    <div class="%s">
        <ul>
            %%s
        </ul>
    </div>
        ''' % menu_class
        # Icon and select marker are on li in legacy mode
        menu_item_wrap = '''<li %(selected)s class="%(class)s">
        <a href="%(url)s" %(selected)s %(attr)s class=%(link_class)s title="%(hover)s">
        %(title)s</a></li>
        '''
    else:
        menu_wrap = '''%s
        '''
        if display != ICONS_ONLY:
            menu_wrap = '''
    <div class="%s slider-middle col-12 align-self-center">
        %%s
    </div>
        ''' % menu_class
        # Icon and selected marker are on span in modern mode
        menu_item_wrap = '''<a href="%(url)s" %(selected)s %(attr)s class="%(link_class)s" title="%(hover)s">
        <span %(selected)s class="%(class)s"></span>%(title)s</a>
        '''
    menu_lines = ''
    for name in menu_order:
        spec = menu_items.get(name, None)
        if not spec:
            menu_lines += '   <!-- No such menu item: "%s" !!! -->\n' % name
            continue
        # Helper to allow style parent tag in nav menu (especially custom jupyter icon)
        spec['link_class'] = ' '.join(['link-%s' %
                                       i for i in spec.get('class', '').split(' ')])
        if not legacy_ui and spec.get('legacy_only', False):
            menu_lines += '   <!-- Skip built-in %s for modern UI -->\n' % name
            continue
        # Override VGrids label now we have configuration
        if name == 'vgrids':
            title = spec['title'].replace('VGrid',
                                          configuration.site_vgrid_label)
            hover = spec['hover'].replace('VGrid',
                                          configuration.site_vgrid_label)
            spec['title'] = title
            spec['hover'] = hover
        if name == 'seafile':
            spec['url'] = configuration.user_seahub_url

        menu_entry = {}
        menu_entry.update(spec)
        # Force set all required values
        for name in ('url', 'selected', 'attr', 'hover', 'class', 'title'):
            menu_entry[name] = spec.get(name, '')
        menu_entry['target'] = 'target="%s"' % spec.get('target', '')
        if os.path.splitext(spec['url'])[0] == current_element:
            menu_entry['selected'] = 'id="selected"'
            menu_entry['class'] += " selected"
        # Optional display of icons or text only
        if display == ICONS_ONLY:
            menu_entry['title'] = ''
        elif display == TEXT_ONLY:
            menu_entry['class'] += " hidden"

        # menu_entry = '   <a href="%s" %s %s title="%s">%s%s</a>'\
        #    % (spec['url'], spec.get('attr', ''), target,
        #       spec.get('hover', ''), item_icon, item_text)

        menu_lines += menu_item_wrap % menu_entry

    return menu_wrap % menu_lines


def render_apps(configuration, title_entry, active_menu):
    """Render the apps selection contents using configuration"""

    user_settings = title_entry.get('user_settings', {})
    legacy_ui = legacy_user_interface(configuration, user_settings)
    raw_order = []
    raw_order += active_menu
    app_order = []
    # Remove duplicates
    for name in raw_order:
        if not name in app_order:
            app_order.append(name)

    app_lines = '''
        <div class="home-page__content col-12">
            <h2>Your apps & app-setup</h2>
            <div class="app-row row app-grid">
    '''

    for name in app_order:
        spec = menu_items.get(name, None)
        if not spec:
            app_lines += '   <!-- No such menu item: "%s" !!! -->\n' % name
            continue
        # Skip built-in ones if on modern UI
        if not legacy_ui and spec.get('legacy_only', False):
            app_lines += '   <!-- Skip built-in %s for modern UI -->\n' % name
            continue
        # Override VGrids label now we have configuration
        if name == 'vgrids':
            title = spec['title'].replace('VGrid',
                                          configuration.site_vgrid_label)
            hover = spec['hover'].replace('VGrid',
                                          configuration.site_vgrid_label)
            spec['title'] = title
            spec['hover'] = hover
        if name == 'seafile':
            spec['url'] = configuration.user_seahub_url
        spec['hover'] = spec.get('hover', '')
        app_lines += '''
                <div class="col-lg-2 app-cell">
                    <div class="app__btn col-12">
                        <a href="%(url)s" title="%(hover)s"><span class="fas %(class)s"></span><h3>%(title)s</h3></a>
                    </div>
                </div>
        ''' % spec
    app_lines += '''
                <div class="col-lg-2">
                    <div class="add-app__btn col-12" onclick="addApp()">
                         <a href="#"><span class="fas fa-plus"></span><h3>Add</h3></a>
                    </div>
                </div>
            </div>
        </div>
    '''

    return app_lines


def render_body_start(configuration, script_map={}, user_settings={}):
    """Render the default body init for specific UI configuration and insert
    provided body additions like classes and meta.
    """
    if legacy_user_interface(configuration, user_settings):
        body_id = 'legacy-ui-body'
    else:
        body_id = 'modern-ui-body'
    # NOTE: we bail out if script_map['body'] tries to set id, too
    body_extras = script_map.get('body', '')
    if body_extras.find('id=') != -1:
        configuration.logger.error("Body cannot have a 2nd 'id'!")
        body_extras = ''
    return '''
<body id="%s" %s>
    ''' % (body_id, body_extras)


def render_body_end(configuration, user_settings={}):
    """Render the default body termination"""
    return """</body>
    """


def render_before_menu(configuration, script_map={}, user_settings={}):
    """Render the default structure from body and until the navigation menu
    entries using the user provided script_map for further customization.
    """
    fill_helper = {'short_title': configuration.short_title,
                   'status_url': configuration.site_status_url,
                   'sitestatus_button': ''}
    if legacy_user_interface(configuration, user_settings):
        html = '''
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
        ''' % (configuration.site_logo_left, configuration.site_logo_center,
               configuration.site_logo_right)
    else:
        if configuration.site_enable_sitestatus:
            fill_helper['sitestatus_button'] = '''
                <li id="sitestatus-button" class="nav__item nav_item--expanded fas fa-question-circle custom-show" onclick="show_message()"></li>
            '''

        html = '''
    <!-- Push notifications: updated/filled by AJAX -->
    <div id="sitestatus-popup" class="toast hidden" data-autohide="false">
        <div id="sitestatus-top" class="toast-header">
            <div id="sitestatus-title" class="toast-title">
                <!-- TODO: move inline style to css files -->
                <!-- NOTE: reuse 1.5rem size with ml-2 and mb-1 classes to mimic close -->
                <span id="sitestatus-icon" class="fas fa-question-circle ml-2 mb-1" style="color: grey; font-size: 1.5rem; float: left;"></span>
                <strong class="mr-auto text-primary" style="float: left;">
                    <h3 id="sitestatus-caption" style="margin-left: 5px;">SITE STATUS</h3>
                </strong>
                <small id="sitestatus-timestamp" class="text-muted" style="float: right;"></small>
            </div>
        <div id="sitestatus-close" class="">
            <button type="button" class="ml-2 mb-1 close" data-dismiss="toast">&times;</button>
        </div>
    </div>
    <div id="sitestatus-content" class="toast-body">
        <h3>Site Status</h3>
        <p id="sitestatus-line" class="status-text">
        <!-- Filled by AJAX -->
        </p>
        <div id="sitestatus-recent" class="hidden"><h3>Active Announcements</h3>
            <p id="sitestatus-announce" class="announce-text"></p>
        </div>
    </div>
    <div id="sitestatus-more" class="toast-body">
        <a target=_blank href="%(status_url)s">More details ...</a>
    </div>
</div>
'''

        html += '''

<!--HEADER INFO AREA-->
<nav id="headerNav">
    <ul class="nav__items">
        <li class="nav__item">
            <a id="supportInfoButton" href="#" class="nav__label" onclick="toggle_info(\'supportInfo\')">Support</a>
        </li>
        <li class="nav__item nav_item--expanded">
            <a id="aboutInfoButton" href="#" class="nav__label" onclick="toggle_info(\'aboutInfo\')">About</a>
        </li>
                <!-- NOTE: completely skip feedback button for now to avoid border
                <li id="sitefeedback-button" class="nav__item nav_item--expanded fas fa-thumbs-up custom-hidden"></li>
                -->
                %(sitestatus_button)s
    </ul>
</nav>

<div id="infoArea" class="infoArea-container">
</div>

<div id="supportInfo" class="infoArea-container">
    <span class="far fa-times-circle close_btn" onclick="toggle_info(\'supportInfo\')"></span>
    <div class="popup container">
        <div class="row">
            <div id="quickstart-content" class="col-lg-12">
            <!-- Filled by AJAX -->
            </div>

            <div id="faq-content" class="col-lg-12 invert-theme">
            <!-- Filled by AJAX -->
            </div>

            <div class="vertical-spacer"></div>
        </div>
    </div>
</div>

<div id="aboutInfo" class="infoArea-container">
<span class="far fa-times-circle close_btn" onclick="toggle_info(\'aboutInfo\')"></span>
    <div class="popup container">
        <div class="row">
            <div id="about-content" class="col-lg-12">
                <!-- Filled by AJAX -->
                </div>

                <div class="vertical-spacer"></div>
        </div>
    </div>
</div>
    '''

    return html % fill_helper


def render_after_menu(configuration, user_settings={}):
    """Render the default structure after the navigation menu and until the end
    of the page.
    """
    # TODO: move slide out and user menu here for UI V3?
    return ''


def get_css_helpers(configuration, user_settings):
    """Returns a dictionary of string expansion helpers for css"""
    skin_base = configuration.site_skin_base
    if legacy_user_interface(configuration, user_settings):
        base_path = configuration.site_assets
        ui_suffix = 'V2'
    else:
        base_path = configuration.site_assets
        ui_suffix = 'V3'
    return {'base_prefix': os.path.join(base_path, 'css', ui_suffix),
            'advanced_prefix': os.path.join(base_path, 'css', ui_suffix),
            'skin_prefix': skin_base, 'ui_suffix': ui_suffix}


def extend_styles(configuration, styles, base=[], advanced=[], skin=[],
                  user_settings={}):
    """Appends any stylesheets specified in the base, advanced and skin lists
    in the corresponding sections of the styles dictionary.
    """
    css_helpers = get_css_helpers(configuration, user_settings)
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


def base_styles(configuration, base=[], advanced=[], skin=[], user_settings={}):
    """Returns a dictionary of basic stylesheets for unthemed pages"""
    css_helpers = get_css_helpers(configuration, user_settings)
    styles = {'base': '', 'advanced': '', 'skin': ''}
    extend_styles(configuration, styles, base, advanced, skin, user_settings)
    return styles


def themed_styles(configuration, base=[], advanced=[], skin=[], user_settings={}):
    """Returns a dictionary of basic stylesheets for themed JQuery UI pages.
    Appends any stylesheets specified in the base, advanced and skin lists.
    """
    css_helpers = get_css_helpers(configuration, user_settings)
    styles = {'base': '''
<link rel="stylesheet" type="text/css" href="/assets/vendor/jquery-ui/css/jquery-ui.css" media="screen"/>
''' % css_helpers,
              'ui_base': '',
              'advanced': '''
<link rel="stylesheet" type="text/css" href="%(base_prefix)s/jquery.managers.css" media="screen"/>
                ''' % css_helpers,
              'skin': '''
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/core.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-theme.custom.css" media="screen"/>
''' % css_helpers,
              'ui_skin': ''
              }
    if not legacy_user_interface(configuration, user_settings):
        styles['ui_base'] += '''
<!-- User interface version-specific setup -->
<link rel="stylesheet" href="/assets/vendor/bootstrap/css/bootstrap.min.css">
<link rel="stylesheet" href="/assets/vendor/fontawesome/css/all.css"> <!--load all styles -->

<!-- UI V3 CSS -->
<link rel="stylesheet" href="/assets/css/V3/ui.css">
<link rel="stylesheet" href="/assets/css/V3/style.css">
<link rel="stylesheet" href="/assets/css/V3/nav.css">
        '''
        styles['ui_skin'] += '''
<!-- UI V3-only skin overrides -->
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-v3.custom.css" media="screen"/>
        ''' % css_helpers
    else:
        styles['ui_skin'] += '''
<!-- UI V2-only skin overrides -->
<link rel="stylesheet" type="text/css" href="%(skin_prefix)s/ui-v2.custom.css" media="screen"/>
        ''' % css_helpers

    extend_styles(configuration, styles, base, advanced, skin, user_settings)
    return styles


# TODO: eliminate this legacy wrapper now handled in init
def jquery_ui_js(configuration, js_import, js_init, js_ready):
    """Fill standard javascript template for JQuery UI pages. The three args
    add custom extra javascript in the usual load, init and ready phase used
    with jquery pages.
    """
    return '''
%(js_import)s

<script type="text/javascript" >

    %(js_init)s

    $(document).ready(function() {
        //console.log("document ready handler");
        %(js_ready)s
    });

</script>
''' % {'js_import': js_import, 'js_init': js_init, 'js_ready': js_ready}


def themed_scripts(configuration, base=[], advanced=[], skin=[], init=[],
                   ready=[], user_settings={}, logged_in=True):
    """Returns a dictionary of basic script snippets for themed JQuery UI
    pages.
    Appends any scripts specified in the base, advanced, skin, init and
    ready lists for easy use in page head generation.
    Theming and UI version is selected based on user_settings and logged_in
    status. If not logged in the site default UI version is used.
    """
    scripts = {'base': [] + base, 'advanced': [] + advanced,
               'skin': [] + skin, 'init': [] + init,
               'ready': [] + ready}
    scripts['base'].append('''
<script type="text/javascript" src="/assets/vendor/jquery/js/jquery.js"></script>
    ''')
    scripts['skin'].append('''
<script type="text/javascript" src="/assets/vendor/jquery-ui/js/jquery-ui.js"></script>
    ''')
    # Always init basic js logging
    scripts['init'].append(console_log_javascript(script_wrap=False))

    if legacy_user_interface(configuration, user_settings):
        # Always add site status helpers
        scripts['skin'].append('''
<script src="/assets/js/V2/ui-dynamic.js"></script>
        ''')
    else:
        scripts['base'].append('''
<script src="/assets/vendor/jquery/js/popper.js"></script>
<script src="/assets/vendor/jquery/js/jquery.validate.min.js"></script>
        ''')
        scripts['skin'].append('''
<!-- UI V3 JS -->
<script src="/assets/vendor/bootstrap/js/bootstrap.min.js"></script>
<script src="/assets/js/V3/ui-global.js"></script>
<script src="/assets/js/V3/ui-extra.js"></script>
<script src="/assets/js/V3/ui-dynamic.js"></script>
        ''')
        if logged_in:
            quickstart_init = 'load_quickstart_dynamic'
        else:
            quickstart_init = 'load_quickstart_static'
        quickstart_url = configuration.site_quickstart_snippet_url
        faq_url = configuration.site_faq_snippet_url
        about_url = configuration.site_about_snippet_url
        dyn_scripts = '''
            var locale = extract_default_locale()
            console.log("loading dynamic snippet content");
            %s("%s");
            load_faq("%s");
            load_about("%s");
        ''' % (quickstart_init, quickstart_url, faq_url, about_url)
        if configuration.site_enable_sitestatus:
            # TODO: remote status page may require CORS headers
            sitestatus_url = configuration.site_status_url
            sitestatus_events = configuration.site_status_events
            sitestatus_system_match = configuration.site_status_system_match
            dyn_scripts += '''
            load_sitestatus("%s", %s, locale);
            ''' % (sitestatus_events, sitestatus_system_match)
        # Call dynamic content scripts on page ready
        scripts['ready'].append(dyn_scripts)

    wrapped = {'base': '\n'.join(scripts['base']),
               'advanced': '\n'.join(scripts['advanced']),
               'skin': '\n'.join(scripts['skin']),
               'init': '\n'.join(scripts['init']),
               'ready': '\n'.join(scripts['ready'])
               }
    return wrapped


def tablesorter_pager(configuration, id_prefix='', entry_name='files',
                      page_entries=[5, 10, 20, 25, 40, 50, 80, 100, 250, 500,
                                    1000],
                      default_entries=25, form_prepend='', form_append='',
                      enable_refresh_button=True):
    """Generate html pager for tablesorter table"""
    toolbar = '''
<div>
    <div class="toolbar">
        <div class="pager" id="%spager">
        <form style="display: inline;" action="">
%s
''' % (id_prefix, form_prepend)
    # NOTE: UI V3 and V2 assign icons in CSS
    toolbar += '''
        <span class="pager-nav-wrap first icon"></span>
        <span class="pager-nav-wrap prev icon"></span>
        <input class="pagedisplay" type="text" size=18 readonly="readonly" />
        <span class="pager-nav-wrap next icon"></span>
        <span class="pager-nav-wrap last icon"></span>
        <select class="pagesize pager-select styled-select html-select">
'''
    for value in page_entries:
        selected = ''
        if value == default_entries:
            selected = 'selected'
        toolbar += '<option %s value="%d">%d %s per page</option>\n' % \
                   (selected, value, value, entry_name)
    toolbar += '''
        </select>
        %s
''' % form_append
    if enable_refresh_button:
        refresh_button = '''
            <span class="pager-nav-wrap refresh icon" title="Refresh"></span>
        '''
    else:
        refresh_button = ""
    toolbar += '''
        <div id="%spagerrefresh" class="inline">
            %s
            <div id="ajax_status" class="inline"><!-- Dynamically filled by js --></div>
        </div>
''' % (id_prefix, refresh_button)
    toolbar += '''
        </form>
        </div>
    </div>
</div>
    '''
    return toolbar


def tablesorter_js(configuration, tables_list=[], include_ajax=True):
    """Build standard tablesorter dependency imports, init and ready snippets.
    The tables_list contains one or more table definitions with id and options
    to intitialize the table(s) with.
    The optional include_ajax option can be used to disable the AJAX loading
    setup needed by most managers.
    """
    # TODO: migrate to assets
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
    # TODO: migrate to assets
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>
    '''
    add_init = ''
    add_ready = '''
        // init confirmation dialog
        $("#confirm_dialog").dialog(
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
    <div id="confirm_dialog" title="Confirm">
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


def fancy_upload_js(configuration, callback=None, share_id='', csrf_token='',
                    chroot=''):
    """Build standard fancy upload dependency imports, init and ready
    snippets.
    """
    # callback must be a function
    if not callback:
        callback = 'function() { return false; }'
    # TODO: migrate to assets
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
<!-- The File Upload jQuery UI plugin using simple jQuery UI -->
<!-- Please note that this is no longer distributed with file uploader since
     switch to bootstrap. We still use it to style the fileupload dialog buttons. -->
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
    /* Required options for internal use in fancy upload open_dialog handler */
    var options = {
            chroot: "%(chroot)s",
            enableGDP: %(enable_gdp)s,
        };

    /* Default fancy upload dest - optionally override before open_dialog call */
    var remote_path = ".";
    function setUploadDest(path) {
        remote_path = path;
    }
    var open_dialog = null;
    function initFancyUpload() {
        open_dialog = mig_fancyuploadchunked_init("fancyuploadchunked_dialog",
                                                  options);
    }
    /* NOTE: all args are optional and will be set to default if not given */
    function openFancyUpload(title_text, action, chroot, dest_dir, automatic_dest,
                             share_id, csrf_token) {
        if (open_dialog === null) {
            initFancyUpload();
        }
        if (title_text === undefined) {
            title_text = "Upload Files";
        }
        if (action === undefined) {
            action = %(callback)s;
        }
        if (chroot === undefined) {
            chroot = options.chroot;
        }
        if (dest_dir === undefined) {
            dest_dir = remote_path;
        }
        if (automatic_dest === undefined) {
            automatic_dest = false;
        }
        if (share_id === undefined) {
            share_id = "%(share_id)s";
        }
        if (csrf_token === undefined) {
            csrf_token = "%(csrf_token)s";
        }
        open_dialog(title_text, action, chroot, dest_dir, automatic_dest, share_id,
                    csrf_token);
    }
    ''' % {"callback": callback, "share_id": share_id,
           "trash_linkname": trash_linkname, "csrf_field": csrf_field,
           "csrf_token": csrf_token, "chroot": chroot,
           "enable_gdp": ("%s" % configuration.site_enable_gdp).lower()}
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
                <span class='fileupload-process'><!-- dynamic --></span>
            </div>
            <!-- The global progress state -->
            <div class='fileupload-progress fade' style='display:none'>
                <!-- The global progress bar -->
                <div class='progress' role='progressbar' aria-valuemin='0'
                    aria-valuemax='100'><!-- dynamic --></div>
                <!-- The extended global progress state -->
                <div class='progress-extended'>&nbsp;</div>
            </div>
        </div>
        <!-- The table listing the files available for upload/download -->
        <table role='presentation' class='table table-striped'>
        <tbody class='uploadfileslist'><!-- dynamic --></tbody></table>
    </form>
    <!-- For status and error output messages -->
    <div id='fancyuploadchunked_output'></div>
    </div>
    """
    return html


def save_settings_js(configuration):
    """Build AJAX save settings/setup dependency imports, init and ready
    snippets.
    """
    if configuration.site_enable_wsgi:
        save_url = "/wsgi-bin/settingsaction.py"
    else:
        save_url = "/cgi-bin/settingsaction.py"
    # TODO: migrate to assets
    add_import = '''
<!-- for AJAX submit form -->
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
    '''
    add_init = '''
    function renderWorking(msg) {
        return "<span class=\'spinner skin iconleftpad\'>"+msg+"</span>";
    }
    function renderSuccess(msg) {
        return "<span class=\'ok skin iconleftpad\'>"+msg+"</span>";
    }
    function renderWarning(msg) {
        return "<span class=\'warn skin warningtext iconleftpad\'>"+msg+"</span>";
    }
    function renderError(msg) {
        return "<span class=\'error skin errortext iconleftpad\'>"+msg+"</span>";
    }

    var saved = false;
    var statusMsg = "";
    var warningMsg = "";
    var errorMsg = "";

    var okSaveDialog = {buttons: {Ok: function(){ $(this).dialog("close");}},
                        minWidth: 600, width: "auto", autoOpen: false, closeOnEscape: true,
                        modal: true};

    //console.debug("submit form serialized: "+$(".save_settings").serialize());
    var options = {
                    url: "%(save_url)s?output_format=json",
                    dataType: "json",
                    type: "POST",
                    beforeSubmit: function() {
                        $(".savestatus").html(renderWorking("Saving ..."));
                        $(".savestatus span").fadeIn(200);
                    },
                    success: function(responseObject, statusText) {
                        /* Reset status */
                        saved = false;
                        statusText = "";
                        warningMsg = "";
                        errorMsg = "";
                        //console.log("verify post response: "+statusText);
                        for (var i=0; i<(responseObject.length); i++) {
                            if(responseObject[i]["object_type"] === "text") {
                                statusMsg = responseObject[i]["text"];
                                if (statusMsg.indexOf("Saved ") !== -1) {
                                    console.info(
                                            "Save success: "+statusMsg);
                                            saved = true;
                                            /* strip trailing colon */
                                            statusMsg = statusMsg.replace(
                                                ":", "");
                                    break;
                                } else if (statusMsg.indexOf("Input ") !== -1) {
                                    errorMsg = "Save failed: "+responseObject[i]["text"];
                                    console.error(errorMsg);
                                    break;
                                } else {
                                    console.debug(
                                            "ignoring other text entry: "+statusMsg);
                                }
                            } else if(responseObject[i]["object_type"] === "error_text") {
                                errorMsg = "Save failure: "+responseObject[i]["text"];
                                console.error(errorMsg);
                                break;
                            } else if(responseObject[i]["object_type"] === "warning") {
                                warningMsg = "warning: "+responseObject[i]["text"];
                                console.warn(warningMsg);
                            }
                        }
                        if (saved) {
                            var saveMsg = renderSuccess(statusMsg);
                            if (warningMsg) {
                                saveMsg += "<br/> "+renderWarning(warningMsg);
                            }
                            $(".savestatus").html(saveMsg);
                            $(".savestatus span").fadeIn(200);
                            setTimeout(function() { $(".savestatus span").fadeOut(3000);
                                                }, 1000);
                            if (statusMsg.indexOf("duplicati") >= 0) {
                                console.info(
                                    "force reload for duplicati to update backup sets");
                                setTimeout(function() {
                                    $(".savestatus").html(renderWorking("refreshing ..."));
                                    $(".savestatus span").fadeIn(200);
                                }, 4000);
                                setTimeout(function() { location.reload(); }, 5000);
                            } else if (location.href.indexOf("home") >= 0) {
                                console.info("force reload for apps to update");
                                setTimeout(function() {
                                    $(".savestatus").html(renderWorking("refreshing ..."));
                                    $(".savestatus span").fadeIn(200);
                                }, 4000);
                                setTimeout(function() { location.reload(); }, 5000);
                            }
                        } else {
                            if (!errorMsg) {
                                errorMsg = "Save failed - please retry";
                            }
                            console.error(errorMsg);
                            $(".savestatus").html(renderError(errorMsg));
                            $(".savestatus span").fadeIn(100);
                        }
                    },
                    error: function(jqXHR, textStatus, errorThrown) {
                        errorMsg = "background save failed: ";
                        errorMsg += textStatus;
                        console.error(errorMsg);
                        console.error("error thrown: "+ errorThrown);
                        $(".savestatus").html(renderError(errorMsg));
                        $(".savestatus span").fadeIn(100);
                    }
                };
    /* Prevent enter in fields submitting directly to backend */
    $(".save_settings").on("keypress", function(e) {
            return e.which !== 13;
            });
    $(".save_settings").ajaxForm(options);
    $(".save_settings").submit();
    console.debug("fired ajaxform");
    ''' % {'save_url': save_url}
    add_ready = ''
    return (add_import, add_init, add_ready)


def save_settings_html(configuration):
    """Build standard html save settings/setup content"""
    html = """
<div class='savestatus'><!-- filled by script --></div>
    """
    return html


def twofactor_wizard_js(configuration):
    """Build standard twofactor wizard dependency imports, init and ready
    snippets.
    """
    # TODO: migrate to assets
    add_import = '''
<!-- for AJAX submit token verification -->
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<!-- for 2FA QR codes -->
<script type="text/javascript" src="/images/js/qrious.js"></script>
'''
    add_init = '''
    var toggleHidden = function(classname) {
        // classname supposed to have a leading dot
        $(classname).toggleClass("hidden");
    }

    function renderWorking(msg) {
        return "<span class=\'spinner iconleftpad\'>"+msg+"</span>";
    }
    function renderSuccess(msg) {
        return "<span class=\'ok iconleftpad\'>"+msg+"</span>";
    }
    function renderError(msg) {
        return "<span class=\'errortext error iconleftpad\'>"+msg+"</span>";
    }

    var acceptedOTP = false;
    var statusMsg = "";
    var errorMsg = "";
    var okOTPDialog = {buttons: {Ok: function(){ $(this).dialog("close");}},
                       minWidth: 600, width: "auto", autoOpen: false, closeOnEscape: true,
                       modal: true};
    var verifyOTPDialog = {
        buttons: {
            Verify: {
              id: "twofactor_verify_button",
              text: "Verify",
              click: function() {
                //console.log("clicked verify in popup");
                /* save dialog handle for AJAX callback use */
                var dialog_handle = $(this);
                var activate_id = $(this).data("activate_id");
                //console.log("found activate_id: "+activate_id);
                var verify_url = $(this).data("verify_url");
                //console.log("found verify_url: "+verify_url);
                $("#twofactor_verify_button").prop("disabled", true);
                $("#twofactorstatus").html(renderWorking("checking ..."));
                acceptedOTP = false;
                try {
                    //console.log("submit form: "+$("#otp_token_form"));
                    //console.log("submit form with token: "+$("#otp_token_form [name=token]").val());
                    //console.log("submit form serialized: "+$("#otp_token_form").serialize());
                    var options = {
                        url: verify_url,
                        dataType: "json",
                        type: "POST",
                        success: function(responseObject, statusText) {
                            //console.log("verify post response: "+statusText);
                            for (var i=0; i<(responseObject.length); i++) {
                                if(responseObject[i]["object_type"] === "text") {
                                    statusMsg = responseObject[i]["text"];
                                    if (statusMsg.indexOf("Correct token") !== -1) {
                                        console.debug(
                                            "Verify success: "+statusMsg);
                                        acceptedOTP = true;
                                        break;
                                    } else if (statusMsg.indexOf("Incorrect token") !== -1) {
                                        errorMsg = "Wrong token - please retry or check client";
                                        console.error(
                                            "Verify failure: "+statusMsg);
                                        break;
                                    } else {
                                        console.debug(
                                            "ignoring other text entry: "+statusMsg);
                                    }
                                }
                            }
                            if (acceptedOTP) {
                                $("#twofactorstatus").html(renderSuccess(statusMsg));
                                console.debug("accepted - close verify popup");
                                setTimeout(function() {$(dialog_handle).dialog("close")},
                                           2000);
                            } else {
                                if (errorMsg === "") {
                                    errorMsg = "Failed to verify token - please retry";
                                }
                                console.error(errorMsg);
                                $("#twofactorstatus").html(renderError(errorMsg));
                                $("#twofactor_verify_button").prop("disabled", false);
                                $("#token").focus();
                            }
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            errorMsg = "OTP background check failed: ";
                            errorMsg += textStatus;
                            $("#twofactorstatus").html(renderError(errorMsg));
                            console.error(errorMsg);
                            console.error("error thrown: "+ errorThrown);
                            $("#twofactor_verify_button").prop("disabled", false);
                            $("#token").focus();
                        }
                    }
                    $("#otp_token_form").ajaxForm(options);
                    $("#otp_token_form").submit();
                } catch(err) {
                    console.error("ajaxform error: "+ err);
                }
                //console.debug("fired ajaxform");
              }
            },
            Cancel: function() { $(this).dialog("close");}
        },
        //width: 480, minHeight: 640,
        autoOpen: false,
        closeOnEscape: true, modal: true
    };

    function checkOTPVerified() {
        //console.debug("in checkOTPVerified: "+ acceptedOTP);
        if (acceptedOTP) {
            //console.debug("checkOTPVerified passed");
            return true;
        } else {
            console.error("checkOTPVerified failed!");
            $("#warning_dialog").dialog(okOTPDialog);
            $("#warning_dialog").html("<span class=\'warn warningtext leftpad\'>Please use the verify link to confirm correct client setup first!</span>");
            $("#warning_dialog").dialog("open");
            return false;
        }
    }
    function toggleOTPDepends() {
        var fade_time = 500;
        //console.debug("display deps if any web 2FA is enabled");
        if ($(".provides-twofactor-base input[type=checkbox]:checked").length) {
            console.debug("2FA web enabled - show deps");
            $(".requires-twofactor-base").fadeIn(fade_time);
        } else {
            console.debug("2FA web disabled - hide deps");
            if ($(".requires-twofactor-base input[type=checkbox]:checked").length) {
                console.warn("force 2FA off for services requiring web 2FA");
                $(".requires-twofactor-base input[type=checkbox]:checked").click();
                /* NOTE: make fade slow enough to let above unchecking show */
                fade_time *= 4;
            }
            $(".requires-twofactor-base").fadeOut(fade_time);
        }        
    }
    function initOTPDepends(static) {
        //console.debug("init deps");
        /* NOTE: in GDP mode we force deps on so no need to show them */
        if (static) {
            $(".requires-twofactor-base").hide();
            $(".requires-twofactor-base input[type=checkbox]:not(:checked)").click();
        } else {
            /* Dynamic display of deps when provider changes */
            toggleOTPDepends();
            $(".provides-twofactor-base input[type=checkbox]").change(toggleOTPDepends);
        }
    }
    function switchOTPState(current, next) {
        $(".otp_wizard."+current+".switch_button").hide();
        $(".otp_wizard."+next).show();
        if (next === "otp_ready") {
            initOTPDepends(%s);
        }
    }
    /* Fast-forward through OTP states like user clicks would do */
    function setOTPProgress(states) {
        var i;
        for (i=0; i < states.length-1; i++) {
            switchOTPState(states[i], states[i+1]);
        }
    }
    function showQRCodeOTPDialog(elem_id, otp_uri) {
          // init OTP dialog for QR code
          $("#"+elem_id).dialog(okOTPDialog);
          $("#"+elem_id).dialog("open");
          $("#"+elem_id).html("<canvas id=\'otp_qr\'><!-- filled by script --></canvas>");
          var qr = new QRious({
                               element: document.getElementById("otp_qr"),
                               value: otp_uri,
                               size: 300
                               });
    }
    function showTextOTPDialog(elem_id, otp_key) {
          // init OTP dialog for text key
          $("#"+elem_id).dialog(okOTPDialog);
          $("#"+elem_id).dialog("open");
          $("#"+elem_id).html("<span id=\'otp_text\'>"+otp_key+"</span>");
    }
    function verifyClientToken(dialog_id, activate_id, verify_url) {
        //console.debug("open verify in popup");
        // Open a dialog to let user verify OTP and only then activate button
        $("#"+dialog_id).dialog(verifyOTPDialog);
        /* Pass activate_id to function implicitly called without arguments */
        $("#"+dialog_id).data("activate_id", activate_id)
        $("#"+dialog_id).data("verify_url", verify_url)
        /* Hide submit and override default action for enter in token input */
        $("#"+dialog_id+" .submit").hide()
        /* Prevent enter in token field submitting directly to backend */
        $("#otp_token_form").on("keypress", function(e) {
                if (e.which === 13) {
                    $("#twofactor_verify_button").click();
                    return false;
                }
                return true;
            });
        /* Change output to json format */
        $("#otp_token_form").append("<input type=\'hidden\' name=\'output_format\' value=\'json\'>");
        $("#"+dialog_id).dialog("open");
        /* Resize to actual dialog contents */
        $("#"+dialog_id).dialog("option", "width", "auto");
        $("#"+dialog_id).dialog("option", "height", "auto");
        //console.debug("opened verify popup");
    }
''' % str(configuration.site_enable_gdp).lower()
    add_ready = ''
    return (add_import, add_init, add_ready)


def twofactor_wizard_html(configuration):
    """Build standard html twofactor wizard table content"""
    html = """
<tr class='otp_wizard otp_intro'><td>
<div id='warning_dialog' title='Warning'
    class='centertext hidden'><!-- filled by script --></div>
<div id='otp_secret_dialog' title='TOTP Secret to Import in Your App'
    class='hidden'><!-- filled by script --></div>
<p>We %(demand_twofactor)s 2-factor authentication on %(site)s for greater
password login security.
In short it means that you enter a generated single-use <em>token</em> from
e.g. your phone or tablet along with your usual login. This combination makes
account abuse <b>much</b> harder, because even if your password gets stolen,
it can't be used without your device.</p>
</td></tr>
<tr class='otp_wizard otp_intro'><td>
<p>Preparing and enabling 2-factor authentication for your login is done in four
steps.</p>
</td></tr>
<tr class='otp_wizard otp_intro switch_button'><td>
<button type=button class='ui-button'
    onClick='switchOTPState(\"otp_intro\", \"otp_install\");'>
Okay, let's go!</button>
</td></tr>
<tr class='otp_wizard otp_install hidden'><td>
<h3>1. Install an Authenticator App</h3>
<p>You first need to install a TOTP authenticator client like
<a href='https://en.wikipedia.org/wiki/Google_Authenticator' target='_blank'>
Google Authenticator</a>,
<a href='https://freeotp.github.io/' target='_blank'>FreeOTP</a>,
<a href='https://www.microfocus.com/en-us/products/netiq-advanced-authentication/overview' target='_blank'>NetIQ Advanced Authentication</a> or
<a href='https://authy.com/download/' target='_blank'>Authy</a> on your phone
or tablet. You can find and install either of them on your device through your
usual app store.</p>
</td></tr>
<tr class='otp_wizard otp_install switch_button hidden'><td>
<button type=button class='ui-button'
    onClick='switchOTPState(\"otp_install\", \"otp_import\");'>
I've got it installed!</button>
</td></tr>
<tr class='otp_wizard otp_import hidden'><td>
<h3>2. Import Secret in Authenticator App</h3>
<p>Open the chosen authenticator app and import your personal 2-factor secret in one of two ways:</p>
<ul class='dbllineheight' type='A'>
<li><span id='otp_qr_link' class='fakelink iconspace'
    onClick='showQRCodeOTPDialog(\"otp_secret_dialog\", \"%(otp_uri)s\");'>
Scan your personal QR code</span></li>
<li><span id='otp_key_link' class='fakelink iconspace'
    onClick='showTextOTPDialog(\"otp_secret_dialog\", \"<p><b>Secret</b>: %(b32_key)s</p><p><b>Interval</b>: %(otp_interval)s</p>\");'>
Enter your personal key</span></li>
</ul>
<p><br/>The latter is usually more cumbersome but may be needed if your app or smart
device doesn't support scanning QR codes. Most apps automatically add service
and account info on QR code scanning, but otherwise you can manually enter it.</p>
</td></tr>
<tr class='otp_wizard otp_import switch_button hidden'><td>
<button type=button class='ui-button'
    onClick='switchOTPState(\"otp_import\", \"otp_verify\");'>
Yes, I've imported it!</button>
</td></tr>
<tr class='otp_wizard otp_verify hidden'><td>
<h3>3. Verify the Authenticator App Setup</h3>
<p>Please <span id='otp_verify_link' class='fakelink infolink'
    onClick='verifyClientToken(\"otp_verify_dialog\", \"otp_verified_button\", \"%(check_url)s\");'>
verify</span> that your authenticator app displays correct new tokens every 30
seconds before you actually enable 2-factor authentication. Otherwise you could
end up locking yourself out once you enable 2-factor authentication!<p/>
</td></tr>
<tr class='otp_wizard otp_verify switch_button hidden'><td>
<button type=button id='otp_verified_button' class='ui-button'
    onClick='checkOTPVerified() && switchOTPState(\"otp_verify\", \"otp_ready\");'>
It works!</button>
</td></tr>
<tr class='otp_wizard otp_ready hidden'><td>
<h5>4. Enable 2-Factor Authentication</h5>
Once you've followed the three steps above and verified your authenticator
app, you can proceed to %(enable_hint)s.<br/>
Afterwards you can simply logout and login again to verify that a token is
requested right after your usual %(site)s login.
</td></tr>
<tr class='otp_wizard otp_ready hidden'><td>
<p class='warningtext'>SECURITY NOTE: please immediately contact the %(site)s admins to
reset your secret 2-factor authentication key if you ever loose a device with
it installed or otherwise suspect someone may have gained access to it.
</p>
</td></tr>
"""
    return html


def twofactor_token_html(configuration):
    """Render html for 2FA token input - similar to the template used in the
    apache_2fa example but with a few custumizations to include our own logo
    and force input focus on load.
    """
    html = '''<!-- make sure content div covers any background pattern -->
<div class="twofactorbg">
<div id="twofactorstatus"><!-- filled by script --></div>
<div id="twofactorbox" class="staticpage">
<img class="sitelogo" src="%(skin_base)s/logo-left.png"><br/>
<img class="authlogo" src="https://lh3.googleusercontent.com/HPc5gptPzRw3wFhJE1ZCnTqlvEvuVFBAsV9etfouOhdRbkp-zNtYTzKUmUVPERSZ_lAL=w300"><br/>
    <!-- IMPORTANT: this form should not have an explicit action! -->
    <form id="otp_token_form" method="POST">
        <input class="tokeninput" type="text" id="token" name="token"
            placeholder="Authentication Token" autocomplete="off" autofocus><br/>
        <input id="otp_token_submit" class="submit" type="submit" value="Submit">
    </form>
</div>
</div>
''' % {'skin_base': configuration.site_skin_base}
    return html


def openid_page_template(configuration, head_extras):
    """Generate a general page template for filling and use in grid_openid.
    Should render in a way similar to logged in pages just with a few dynamic
    features disabled.
    """
    theme_helpers = themed_styles(configuration)
    script_helpers = themed_scripts(configuration, logged_in=False)
    script_helpers['body'] = 'class="staticpage openid"'
    page_title = '%s OpenID Server' % configuration.short_title
    html = get_xgi_html_header(configuration, page_title, '', True, '',
                               theme_helpers, script_helpers, frame=True,
                               menu=False, widgets=False, userstyle=False,
                               head_extras=head_extras)
    html += '''
    <div class="container">
        <div id="content" class="staticpage">
            <div class="banner staticpage">
                <div class="container righttext staticpage">
                    You are %(user_link)s
                </div>
            </div>
            <div class="vertical-spacer"></div>
            %(body)s
        </div>
    </div>
    '''
    html += get_xgi_html_footer(configuration, ' ', True)
    return html


def get_xgi_html_preamble(
    configuration,
    title,
    header,
    meta='',
    style_map={},
    script_map={},
    widgets=True,
    userstyle=True,
    user_settings={},
    user_widgets={},
    user_profile={},
    head_extras=''
):
    """Return the html tags to mark the beginning of a page."""

    user_styles, user_scripts = '', ''
    if widgets:
        script_deps = user_widgets.get('SITE_SCRIPT_DEPS', [''])
        core_scripts = script_map['base'] + script_map['advanced'] + \
            script_map['skin']
        for dep in script_deps:
            # Avoid reloading already included scripts
            if dep and core_scripts.find(dep) == -1:
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
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- page specific meta tags -->
%s

<!-- site default style -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>

<!-- base page styles -->
%s
%s

<!-- specific page styles -->
%s
%s

<!-- skin page styles -->
%s
%s

<!-- override with any site-specific styles -->
<link rel="stylesheet" type="text/css" href="%s" media="screen"/>
%s

<!-- begin user supplied style dependencies -->
%s
<!-- end user supplied style dependencies -->


<!-- Set site favicon -->
<link rel="icon" type="image/vnd.microsoft.icon" href="%s"/>


<!-- base page scripts -->
%s
%s

<!-- skin page scripts -->
%s
%s

<!-- specific page scripts -->
%s
%s

<!-- general script init and ready handlers -->
<script type="text/javascript" >
    %s
    $(document).ready(function() {
        //console.log("document ready handler");
        %s
    });
</script>

<!-- begin user supplied script dependencies -->
%s
<!-- end user supplied script dependencies -->


    ''' % (meta, configuration.site_default_css, style_map.get('base', ''),
           style_map.get('ui_base', ''), style_map.get('page', ''),
           style_map.get('advanced', ''), style_map.get('skin', ''),
           style_map.get('ui_skin', ''), configuration.site_custom_css,
           user_styles, style_overrides, configuration.site_fav_icon,
           script_map.get('base', ''), script_map.get('ui_base', ''),
           script_map.get('skin', ''), script_map.get('ui_skin', ''),
           script_map.get('page', ''), script_map.get('advanced', ''),
           script_map.get('init', ''), script_map.get('ready', ''),
           user_scripts)

    out += '''
<title>
%s
</title>
%s
</head>
    ''' % (title, head_extras)
    return out


def get_xgi_html_header(
    configuration,
    title,
    header,
    html=True,
    meta='',
    style_map={},
    script_map={},
    frame=True,
    menu=True,
    widgets=True,
    userstyle=True,
    base_menu=[],
    user_menu=[],
    user_settings={},
    user_widgets={},
    user_profile={},
    head_extras=''
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
        pre_content = '\n'.join(user_widgets.get(
            'PRECONTENT', ['<!-- empty -->']))
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

    out = get_xgi_html_preamble(configuration,
                                title,
                                header,
                                meta,
                                style_map,
                                script_map,
                                widgets,
                                userstyle,
                                user_settings,
                                user_widgets,
                                user_profile,
                                head_extras,
                                )

    out += render_body_start(configuration, script_map, user_settings)
    out += render_before_menu(configuration, script_map, user_settings)

    # User account menu and slider only enabled along with menu
    menu_slider = ''
    account_menu = ''
    # Maximize is used to toggle menu spacing
    maximize = ''
    if frame:
        maximize += 'frame '
    else:
        maximize += 'noframe '
    if menu:
        maximize += 'menu '
    else:
        maximize += 'nomenu '

    if frame:
        current_page = os.path.splitext(os.path.basename(requested_page()))[0]

        menu_helpers = {'short_title': configuration.short_title,
                        'icon_lines': '', 'text_lines': '', 'menu_lines': '',
                        'home_url': ''}
        if menu:
            menu_helpers['home_url'] = 'home.py'

        if legacy_user_interface(configuration, user_settings):
            out += '''
<!--Legacy nav side bar -->
<nav id="sideBar" >
<div class="menublock sidebar-container row">
'''

            if menu:
                out += '''
%s
                ''' % user_pre_menu
                # Render classic menu
                menu_helpers['menu_lines'] = render_menu(configuration, 'navmenu', current_page,
                                                         base_menu, user_menu, user_settings)
                out += '''
                %(menu_lines)s
                ''' % menu_helpers
                out += '''
%s
                ''' % user_post_menu

            out += '''
</div>
</nav>
            '''
        else:
            # Render side bar with optional nav menu and user profile access
            out += '''
<!--New nav side bar -->
<nav id="sideBar" >
    <!--SIDEBAR-->
    <div class="sidebar-container row">
        <div class="sidebar-header col-12 align-self-start">
            <a id="logoMenu" href="%(home_url)s">
                <div class="home-nav-logo"></div>
            </a>
        </div>
            ''' % menu_helpers
            if menu:
                out += '''
                %s
                ''' % user_pre_menu
                # Render apps icons with slider menu and user profile access
                menu_helpers['icon_lines'] = render_menu(configuration, 'navmenu', current_page,
                                                         base_menu, user_menu, user_settings, display=ICONS_ONLY)
                menu_helpers['text_lines'] = render_menu(configuration, 'navmenu', current_page,
                                                         base_menu, user_menu, user_settings, display=TEXT_ONLY)
                out += '''

        <div class="sidebar-middle col-12 align-self-center">

                    %(icon_lines)s

                    <div id="hamBtn" class="hamburger hamburger--vortex" onclick="hamburgerMenuToggle()">
                        <div class="hamburger-box">
                            <!--<div class="hamburger-inner"></div>-->
                            <h3>...</h3>
                        </div>
                        <!--<div id="menuTxt">Menu</div>-->
                    </div>
        </div>
        <div class="col-12 align-self-end home-nav-user__container">
            <div id="userMenuButton" class="fas fa-user home-nav-user" onclick="userMenuToggle()" title="Your personal settings for %(short_title)s"></div>
        </div>

                ''' % menu_helpers

                menu_slider += '''
                <div id="hamMenu" class="slidernav-container">

                    <div class="slider-container__inner row">
            <div class="slider-header col-12 align-self-start">
                <h2>%(short_title)s</h2>
            </div>
            <div class="slider-middle col-12 align-self-center">
                            %(text_lines)s
            </div>
            <div class="slider-footer col-12 align-self-end home-nav-user__inner">
                            <a onclick="userMenuToggle()">User</a>
            </div>
            </div>
                </div>
                ''' % menu_helpers

                profile_helper = {'full_name': '',
                                  'profile_image': '',
                                  'email_address': '',
                                  'help_url': configuration.site_external_doc}
                profile_helper.update(user_profile)
                if profile_helper['profile_image']:
                    profile_helper['avatar_image'] = '''
                    <img class="avatar-image" src="%(profile_image)s" alt="profile picture" />
                    ''' % profile_helper
                else:
                    profile_helper['avatar_image'] = '''
                    <span class="avatar-image anonymous"></span>
                    '''
                account_menu = '''
<!--USER ACCOUNT MENU POPUP - HIDDEN-->
<div id="userMenu" class="popup-container row">
    <div class="popup-header col-12">
        <div class="row">
            <div class="col-3">
                <div class="user-avatar">
                %(avatar_image)s
                </div>
            </div>
            <div class="col-9">
                %(full_name)s
                <button class="avatar-link" onclick="window.location.href='settings.py'">Change photo</button>
            </div>
        </div>
    </div>
    <div class="popup-middle col-12">
        <a class="user-menu__item" href="home.py">Home</a>
        <a class="user-menu__item" href="settings.py">Settings</a>
        <a class="user-menu__item" href="setup.py">Setup</a>
        <a class="user-menu__item" href="%(help_url)s">Help</a>
    </div>
    <div class="popup-footer col-12">
        <a href="logout.py">Sign Out</a>
    </div>
</div>
                ''' % profile_helper

                out += '''
        %s
                ''' % user_post_menu

            out += '''
    </div>
</nav>

%s

%s
            ''' % (menu_slider, account_menu)
    else:
        # No frame
        out += '''
<!-- No frame or menu on this page --->
'''

    out += render_after_menu(configuration, user_settings)

    out += '''

<section id="globalContainer" class="global-container %s">
<div class="wallpaper"></div>

%s
<div id="migheader">
%s
</div>


<div id="content" class="i18n" lang="en">
''' % (maximize, user_pre_content, header)

    return out


def get_xgi_html_footer(configuration, footer='', html=True, user_settings={},
                        widgets=True, user_widgets={}):
    """Return the html tags to mark the end of a page. If a footer string
    is supplied it is inserted at the bottom of the page.
    """

    if not html:
        return ''

    user_post_content = ''
    if widgets:
        post_content = '\n'.join(user_widgets.get(
            'POSTCONTENT', ['<!-- empty -->']))
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
''' % user_post_content

    out += footer
    out += '''
</section>
    '''
    if legacy_user_interface(configuration, user_settings):
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
<div id="privacy">
<img src="%s" id="privacyimage" alt=""/>
<div class="privacytext i18n" lang="en">
%s
</div>
</div>
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
        ''' % (configuration.site_support_image,
               configuration.site_support_text,
               configuration.site_privacy_image,
               configuration.site_privacy_text,
               configuration.site_credits_image,
               configuration.site_credits_text)

    out += render_body_end(configuration, user_settings)
    out += '''
</html>
    '''
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
        html += '<input id="%s%sfield" type="hidden" name="%s" value="%s" />\n' % \
                (function_name, key, key, val)
    html += '</form>\n'
    return html


def console_log_javascript(script_wrap=True):
    """Javascript console logging: just include this and set cur_log_level before
    calling init_log() to get console.debug/info/warn/error helpers.
    """
    log_init = []
    if script_wrap:
        log_init.append('<script type="text/javascript" >')
    log_init.append('''
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
''')
    if script_wrap:
        log_init.append('</script>')
    return '\n'.join(log_init)
