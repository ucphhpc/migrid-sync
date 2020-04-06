#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# home - home page
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


"""Home page generator with dynamic app selection"""


import shared.returnvalues as returnvalues
from shared.defaults import csrf_field
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry, extract_menu
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import save_settings_js, save_settings_html, render_apps, \
    menu_items, legacy_user_interface
from shared.settings import load_settings
from shared.settingskeywords import get_keywords_dict


def html_tmpl(configuration, client_id, title_entry, csrf_map={}, chroot=''):
    """HTML page base: some upload and menu entries depend on configuration"""

    active_menu = extract_menu(configuration, title_entry)
    user_settings = title_entry.get('user_settings', {})
    legacy_ui = legacy_user_interface(configuration, user_settings)
    fill_helpers = {'short_title': configuration.short_title}
    html = '''
    <!-- CONTENT -->

			<div class="container">
				<div id="app-nav-container" class="row">
                                <h1>Welcome to %(short_title)s!</h1>
					<div class="home-page__header col-12">
						<p class="sub-title">Tools from %(short_title)s helps you with storage, sharing and archiving of data. %(short_title)s delivers centralised storage space for personal and shared files.</p>
					</div>

                                        <div id="tips-container" class="col-12">
                                            <div id="tips-content" class="tips-placeholder">
                                                <!-- NOTE: filled by AJAX .. init for space -->
                                            </div>
                                        </div>
            ''' % fill_helpers
    html += render_apps(configuration, title_entry, active_menu)
    html += '''
                                <div class="col-lg-12 vertical-spacer"></div>
				</div>
			</div>

    '''

    # Dynamic app selection
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'settingsaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    settings_specs = get_keywords_dict()
    current_settings_dict = load_settings(client_id, configuration)
    if not current_settings_dict:

        # no current settings found

        current_settings_dict = {}
    fill_helpers['form_prefix'] = '''
    <form class="save_settings save_apps" action="settingsaction.py" method="%s">
        <input type="hidden" name="%s" value="%s">
    ''' % (form_method, csrf_field, csrf_token)
    fill_helpers['form_suffix'] = '''
            %s
            <input type="submit" value="Save">
        </form>
    ''' % save_settings_html(configuration)
    apps_field = 'SITE_USER_MENU'
    # NOTE: build list of all default and user selectable apps in that order
    app_list = [app_id for app_id in configuration.site_default_menu]
    app_list += [app_id for app_id in configuration.site_user_menu if not
                 app_id in app_list]

    mandatory_apps = []
    for app_name in configuration.site_default_menu:
        mandatory_apps.append(menu_items[app_name]['title'])
    fill_helpers['mandatory_apps'] = ', '.join(mandatory_apps)
    html += '''
<!-- APP POP-UP -->
		<div id="add-app__window" class="app-container hidden">
			<span class="add-app__close far fa-times-circle" onclick="closeAddApp()"></span>
			<div class="container">
				<div class="row">
					<div class="app-page__header col-12">
						<h1>Your apps & app-setup</h1>
                        <p class="sub-title-white">Here you can select which apps you want to use in your %(short_title)s system. Only %(mandatory_apps)s are mandatory.</p>
					</div>
					<div class="app-page__header col-12">
						<h2>Select your apps</h2>
                                                %(form_prefix)s
    ''' % fill_helpers
    # The backend form requires all user settings even if we only want to edit
    # the user apps subset here - just fill as hidden values.
    # TODO: consider a save version with only relevant values.
    for (key, val) in current_settings_dict.items():
        if key == apps_field:
            continue
        spec = settings_specs[key]
        if spec['Type'] == 'multiplestrings':
            html += '''        <textarea class="hidden" name="%s">%s</textarea>
            ''' % (key, '\n'.join(val))

        elif spec['Type'] == 'string':
            html += '''        <input type="hidden" name="%s" value="%s">
            ''' % (key, val)
        elif spec['Type'] == 'boolean':
            html += '''        <input type="hidden" name="%s" value="%s">
            ''' % (key, val)

    html += '''						<div class="app-grid row">
    '''
    for app_id in app_list:
        app = menu_items[app_id]
        app_name = app['title']
        if not legacy_ui and app.get('legacy_only', False):
            continue
        if app_id == 'vgrids':
            app_name = '%ss' % configuration.site_vgrid_label
        mandatory = (app_id in configuration.site_default_menu)
        app_btn_classes = 'app__btn col-12 '
        if mandatory:
            app_btn_classes += "mandatory"
        else:
            app_btn_classes += "optional"
        app_icon_classes = app['class']
        check_field = ''
        if not mandatory:
            checked, checkmark = "", "checkmark"
            if app_id in current_settings_dict.get(apps_field, []):
                checked = "checked='checked'"
                checkmark = "checkmark"
            check_field = '''
        <input type="checkbox" name="SITE_USER_MENU" %s value="%s">
        <span class="%s"></span>
            ''' % (checked, app_id, checkmark)
        html += '''
                            <div class="col-lg-2">
			        <div class="%s">
                                    <label class="app-content">
                                    %s
                                    <div class="background-app">
                                        <span class="%s"></span><h3>%s</h3>
                                    </div>
                                    </label>
                                </div>
                            </div>
                ''' % (app_btn_classes, check_field, app_icon_classes, app_name)

    html += '''
						</div>
                                                <br />
                                                %(form_suffix)s
					</div>
				</div>
			</div>
                <div class="col-lg-12 vertical-spacer"></div>
            </div>
                ''' % fill_helpers

    return html


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # output_objects.append({'object_type': 'header', 'text': 'Welcome to %s!' %
    #                       configuration.short_title})

    # Generate and insert the page HTML
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s Home' % configuration.short_title

    # jquery support for AJAX saving

    (add_import, add_init, add_ready) = save_settings_js(configuration)
    add_init += '''
    function addApp() {
        $("#app-nav-container").hide();
        $("#add-app__window").show();
    }
    function closeAddApp() {
        console.log("close add app");
        $("#app-nav-container").show();
        $("#add-app__window").hide();
    }
    '''
    add_ready += '''
                load_tips("%s");
    ''' % configuration.site_tips_snippet_url
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    html = html_tmpl(configuration, client_id, title_entry)
    output_objects.append({'object_type': 'html_form', 'text': html})

    return (output_objects, returnvalues.OK)
