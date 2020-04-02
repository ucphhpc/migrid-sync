#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - back end for the settings page
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

"""Provide all the settings subpages"""

import base64
import os
import urllib

import shared.returnvalues as returnvalues
from shared.auth import get_twofactor_secrets
from shared.base import client_alias, client_id_dir, extract_field, get_xgi_bin
from shared.defaults import default_mrsl_filename, \
    default_css_filename, profile_img_max_kb, profile_img_extensions, \
    seafile_ro_dirname, duplicati_conf_dir, csrf_field, \
    duplicati_protocol_choices, duplicati_schedule_choices
from shared.duplicatikeywords import get_duplicati_specs
from shared.editing import cm_css, cm_javascript, cm_options, wrap_edit_area
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import man_base_js, man_base_html, console_log_javascript, \
    twofactor_wizard_html, twofactor_wizard_js, twofactor_token_html, \
    legacy_user_interface, save_settings_js, save_settings_html
from shared.init import initialize_main_variables, find_entry, extract_menu
from shared.settings import load_settings, load_widgets, load_profile, \
    load_ssh, load_davs, load_ftps, load_seafile, load_duplicati, load_cloud, \
    load_twofactor
from shared.profilekeywords import get_profile_specs
from shared.pwhash import parse_password_policy
from shared.safeinput import html_escape, password_min_len, password_max_len, \
    valid_password_chars
from shared.settingskeywords import get_settings_specs
from shared.twofactorkeywords import get_twofactor_specs
from shared.widgetskeywords import get_widgets_specs
from shared.useradm import create_alias_link, get_default_mrsl, \
    get_default_css, get_short_id


from shared.vgridaccess import get_vgrid_map_vgrids

try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass


general_edit = cm_options.copy()
ssh_edit = cm_options.copy()
davs_edit = cm_options.copy()
ftps_edit = cm_options.copy()
seafile_edit = cm_options.copy()
style_edit = cm_options.copy()
style_edit['mode'] = 'css'
widgets_edit = cm_options.copy()
widgets_edit['mode'] = 'htmlmixed'
profile_edit = cm_options.copy()
profile_edit['mode'] = 'htmlmixed'
duplicati_edit = cm_options.copy()
duplicati_edit['mode'] = 'htmlmixed'
cloud_edit = cm_options.copy()


def signature():
    """Signature of the main function"""

    defaults = {'topic': [], 'caching': ['true']}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Settings'

    # jquery support for toggling views and popup dialog

    (add_import, add_init, add_ready) = man_base_js(configuration, [])
    (tfa_import, tfa_init, tfa_ready) = twofactor_wizard_js(configuration)
    (save_import, save_init, save_ready) = save_settings_js(configuration)
    # prepare support for toggling the views (by css/jquery)
    title_entry['style']['skin'] += '''
%s
''' % cm_css
    add_import += '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>

%s

%s

%s

%s
    ''' % (cm_javascript, console_log_javascript(), tfa_import, save_import)
    add_init += '''
    /* prepare global logging from console_log_javascript */
    try {
        log_level = "info";
        init_log();
    } catch(err) {
        alert("error: "+err);
    }

%s

%s
    ''' % (tfa_init, save_init)
    add_ready += '''
              /* Init variables helper as foldable but closed and with individual
              heights */
              $(".variables-accordion").accordion({
                                           collapsible: true,
                                           active: false,
                                           heightStyle: "content"
                                          });
              /* fix and reduce accordion spacing */
              $(".ui-accordion-header").css("padding-top", 0)
                                       .css("padding-bottom", 0).css("margin", 0);

%s

%s
''' % (tfa_ready, save_ready)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    active_menu = extract_menu(configuration, title_entry)

    # Always load current user settings for use in rendering
    user_settings = load_settings(client_id, configuration)
    # NOTE: loaded settings may be the boolean False rather than dict here
    if not user_settings:
        user_settings = {}

    # Hide default settings in GDP mode
    if configuration.site_enable_gdp:
        valid_topics = []
    else:
        valid_topics = ['general']
    if configuration.site_enable_styling:
        valid_topics.append('style')
    if 'submitjob' in active_menu:
        valid_topics.append('job')
    if 'people' in active_menu:
        valid_topics.append('profile')
    if configuration.site_enable_widgets and configuration.site_script_deps:
        valid_topics.append('widgets')
    if configuration.arc_clusters:
        valid_topics.append('arc')
    if 'setup' not in active_menu:
        if configuration.site_enable_sftp or configuration.site_enable_sftp_subsys:
            valid_topics.append('sftp')
        if configuration.site_enable_davs:
            valid_topics.append('webdavs')
        if configuration.site_enable_ftps:
            valid_topics.append('ftps')
        if configuration.site_enable_seafile:
            valid_topics.append('seafile')
        if configuration.site_enable_duplicati:
            valid_topics.append('duplicati')
        if configuration.site_enable_cloud:
            valid_topics.append('cloud')
        if configuration.site_enable_twofactor \
                and not configuration.site_enable_gdp:
            valid_topics.append('twofactor')

    caching = (accepted['caching'][-1].lower() in ('true', 'yes'))
    topic_list = accepted['topic']
    topic_list = [topic for topic in topic_list if topic in valid_topics]
    # Default to general or general+profile if no valid topics given
    if not topic_list:
        if not legacy_user_interface(configuration, user_settings):
            topic_list = ['general', 'profile']
        else:
            topic_list.append(valid_topics[0])
    # Backwards compatibility
    if topic_list and 'ssh' in topic_list:
        topic_list.remove('ssh')
        topic_list.append('sftp')
    topic_list = [i for i in topic_list if i in valid_topics]
    topic_titles = dict([(i, i.title()) for i in valid_topics])
    for (key, val) in [('sftp', 'SFTP'), ('webdavs', 'WebDAVS'),
                       ('ftps', 'FTPS'), ('seafile', 'Seafile'),
                       ('duplicati', 'Duplicati'), ('cloud', 'Cloud'),
                       ('twofactor', '2-Factor Auth'),
                       ]:
        if key in valid_topics:
            topic_titles[key] = val

    output_objects.append({'object_type': 'header', 'text': 'Settings'})

    links = []
    for name in valid_topics:
        active_menu = ''
        if topic_list[0] == name:
            active_menu = 'activebutton'
        links.append({'object_type': 'link',
                      'destination': "settings.py?topic=%s" % name,
                      'class': '%ssettingslink settingsbutton %s'
                      % (name, active_menu),
                      'title': 'Switch to %s settings' % topic_titles[name],
                      'text': '%s' % topic_titles[name],
                      })

    # Only a single general and profile settings page without tabs in new UI
    if legacy_user_interface(configuration, user_settings):
        output_objects.append({'object_type': 'multilinkline', 'links': links,
                               'sep': '  '})

    output_objects.append({'object_type': 'text', 'text': ''})

    if not topic_list:
        output_objects.append({'object_type': 'error_text', 'text':
                               'No valid topics!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Site policy dictates pw min length greater or equal than password_min_len
    policy_min_len, policy_min_classes = parse_password_policy(configuration)
    save_html = save_settings_html(configuration)
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {
        'site': configuration.short_title, 'form_method': form_method,
        'csrf_field': csrf_field, 'csrf_limit': csrf_limit,
        'valid_password_chars': html_escape(valid_password_chars),
        'password_min_len': max(policy_min_len, password_min_len),
        'password_max_len': password_max_len,
        'password_min_classes': max(policy_min_classes, 1),
        'save_html': save_html}

    # Switch between merged or stand-alone general and profile settings below
    general_save = 'Save General Settings'
    profile_save = 'Save Profile Settings'
    if 'general' in topic_list and 'profile' in topic_list:
        general_save = profile_save = "Save Settings"

    fill_helpers.update({'general_save': general_save,
                         'profile_save': profile_save})

    logger.debug("DEBUG: showing topics %s out of valid topics %s" %
                 (topic_list, valid_topics))

    if "general" in topic_list:
        current_settings_dict = user_settings
        if not current_settings_dict:

            # no current settings found

            current_settings_dict = {}

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
        <div id="settings">
        <form class="save_settings save_general" method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="topic" value="general" />
        <table class="settings fixedlayout">
        <tr class="title"><td class="centertext">
        Select your %(site)s settings
        </td></tr>
        <tr><td>
        </td></tr>
        <tr><td>
        Please note that if you want to set multiple values (e.g. addresses)
        in the same field, you must write each value on a separate line but
        without blank lines.
        </td></tr>
        <tr><td>
        </td></tr>
        '''
        settings_entries = get_settings_specs()
        for (keyword, val) in settings_entries:
            if keyword == 'SUBMITUI' and \
                    'job' not in valid_topics:
                continue
            if keyword == 'ENABLE_WIDGETS' and \
                    not configuration.site_enable_widgets:
                html += '<input type="hidden" name="%s" value="False" />' % keyword
                continue
            if val['Context'] == 'notify' and \
                    keyword.lower() not in configuration.notify_protocols:
                continue
            entry = """
            <tr class='title'><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """ % (keyword.replace('_', ' ').title(), val['Description'])
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_settings_dict.has_key(keyword):
                        current_choice = current_settings_dict[keyword]

                    if valid_choices:
                        entry += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            entry += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        entry += '</div>'
                    else:
                        entry += ''
                except:
                    # failed on evaluating configuration.%s

                    area = '''
                <textarea id="%s" cols=40 rows=1 name="%s">''' \
                        % (keyword, keyword)
                    if current_settings_dict.has_key(keyword):
                        area += '\n'.join(current_settings_dict[keyword])
                    area += '</textarea>'
                    entry += wrap_edit_area(keyword, area, general_edit,
                                            'BASIC')

            elif val['Type'] == 'string':

                # get valid choices from conf

                valid_choices = eval('configuration.%s' % keyword.lower())
                current_choice = ''
                if current_settings_dict.has_key(keyword):
                    current_choice = current_settings_dict[keyword]

                if valid_choices:
                    entry += '<select class="styled-select semi-square html-select" name="%s">' % keyword
                    for choice in valid_choices:
                        selected = ''
                        if choice == current_choice:
                            selected = 'selected'
                        entry += '<option %s value="%s">%s</option>'\
                            % (selected, choice, choice)
                    entry += '</select><br />'
                else:
                    entry += ''
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if current_settings_dict.has_key(keyword):
                    current_choice = current_settings_dict[keyword]

                checked = ''
                if current_choice == True:
                    checked = 'checked'
                entry += '<label class="switch">'
                entry += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                   checked)
                entry += '<span class="slider round"></span></label>'
                entry += '<br /><br />'

            html += """%s
            </td></tr>
            """ % entry

        # Only end form with submit here if general is a stand-alone topic
        if not 'profile' in topic_list:
            html += """
        <tr><td>
        %(save_html)s
        <input type='submit' value='%(general_save)s' />
        </td></tr>
        </table>
        </form>
        </div>
        """
        else:
            html += """
        </table>
"""
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if "profile" in topic_list:

        # load current profile

        current_profile_dict = load_profile(client_id, configuration)
        if not current_profile_dict:

            # no current profile found

            current_profile_dict = {}

        all_vgrids = get_vgrid_map_vgrids(configuration, caching=caching)
        configuration.vgrids_allow_email = all_vgrids
        configuration.vgrids_allow_im = all_vgrids
        images = []
        for path in os.listdir(base_dir):
            real_path = os.path.join(base_dir, path)
            if os.path.splitext(path)[1].strip('.') in profile_img_extensions \
                    and os.path.getsize(real_path) < profile_img_max_kb*1024:
                images.append(path)
        configuration.public_image = images
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        # Only begin new form and container if profile is a stand-alone topic
        html = ''
        if not 'general' in topic_list:
            html = '''
<div id="profile">
<form class="save_settings save_profile" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
'''

        html += '''
<input type="hidden" name="topic" value="profile" />
<table class="profile fixedlayout">
<tr class="title"><td class="centertext">
Public profile information visible to other users.

</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to let other users know more about you can add your own text here.
If you leave the text area blank you will just get the default empty profile
information.<br />
</td></tr>
<tr><td>
<div class="warningtext">Please note that the profile parser is rather grumpy
so you may have to avoid blank lines in your text below.
</div>
</td></tr>
<tr><td>
'''

        profile_entries = get_profile_specs()
        for (keyword, val) in profile_entries:
            # Mask VGrid name if configured
            mask_title = keyword.replace(
                'VGRID', configuration.site_vgrid_label.upper())
            mask_desc = val['Description'].replace(
                'VGrid', configuration.site_vgrid_label)
            html += \
                """
            <tr class=title><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """ % (mask_title.replace('_', ' ').title(),
                   html_escape(mask_desc))
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_profile_dict.has_key(keyword):
                        current_choice = current_profile_dict[keyword]

                    if valid_choices:
                        html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            html += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        html += '</div>'
                except:
                    area = """<textarea id='%s' cols=78 rows=10 name='%s'>""" \
                        % (keyword, keyword)
                    if current_profile_dict.has_key(keyword):
                        area += '\n'.join(current_profile_dict[keyword])
                    area += '</textarea>'
                    html += wrap_edit_area(keyword, area, profile_edit)
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if current_profile_dict.has_key(keyword):
                    current_choice = current_profile_dict[keyword]
                checked = ''
                if current_choice == True:
                    checked = 'checked'
                html += '<label class="switch">'
                html += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                  checked)
                html += '<span class="slider round"></span></label>'
                html += '<br /><br />'

        # Always end form and structure here even for merged settings
        html += '''
        <tr><td>
        %(save_html)s
        <input type="submit" value="%(profile_save)s" />
</td></tr>
</table>
</form>
</div>
'''
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'job' in topic_list:
        mrsl_path = os.path.join(base_dir, default_mrsl_filename)

        default_mrsl = get_default_mrsl(mrsl_path)
        target_op = 'editfile'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="defaultmrsl">
<form class="save_settings save_job" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="defaultjob fixedlayout">
<tr class="title"><td class="centertext">
Default job on submit page
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you use the same fields and values in many of your jobs, you can save your
preferred job description here to always start out with that description on
your submit job page.
</td></tr>
<tr><td>
</td></tr>
<tr><td>
<input type="hidden" name="path" value="%(mrsl_template)s" />
<input type="hidden" name="newline" value="unix" />
'''
        keyword = "defaultjob"
        area = '''
<textarea id="%(keyword)s" cols=82 rows=25 name="editarea">
%(default_mrsl)s
</textarea>
'''
        html += wrap_edit_area(keyword, area, cm_options, 'BASIC')

        html += '''
</td></tr>
<tr><td>
%(save_html)s
<input type="submit" value="Save Job Template" />
</td></tr>
</table>
</form>
</div>
'''
        fill_helpers.update({
            'default_mrsl': default_mrsl,
            'mrsl_template': default_mrsl_filename,
            'keyword': keyword
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'style' in topic_list:
        css_path = os.path.join(base_dir, default_css_filename)
        default_css = get_default_css(css_path)
        target_op = 'editfile'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="defaultcss">
<form class="save_settings save_style" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="defaultstyle fixedlayout">
<tr class="title"><td class="centertext">
Default CSS (style) for all pages
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to customize the look and feel of the %(site)s web interfaces you
can override default values here. If you leave the style file blank you will
just use the default style.<br />
You can copy paste from the available style file links below if you want to
override specific parts.<br />
<div class="warningtext">Please note that you can not save an empty style
file, but must at least leave a blank line to use defaults. Additionally some
errors in your style code may potentially cause severe corruption in your page
layouts, so it may be a good idea to keep another browser tab/window ready to
(re)move your .default.css file to restore the defaults while experimenting
here.
</div>
</td></tr>
<tr><td>
<a class="urllink iconspace" href="/images/default.css">default</a> ,
<a class="urllink iconspace" href="/images/bluesky.css">bluesky</a>
</td></tr>
<tr><td>
</td></tr>
<tr><td>
<input type="hidden" name="path" value="%(css_template)s" />
<input type="hidden" name="newline" value="unix" />
'''
        keyword = "defaultstyle"
        area = '''
<textarea id="%(keyword)s" cols=82 rows=25 min_len=1 name="editarea">
%(default_css)s
</textarea>
'''
        html += wrap_edit_area(keyword, area, style_edit)
        html += '''
</td></tr>
<tr><td>
%(save_html)s
<input type="submit" value="Save Style Settings" />
</td></tr>
</table>
</form>
</div>
'''
        fill_helpers.update({
            'default_css': default_css,
            'css_template': default_css_filename,
            'keyword': keyword
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'widgets' in topic_list:

        # load current widgets

        current_widgets_dict = load_widgets(client_id, configuration)
        if not current_widgets_dict:

            # no current widgets found

            current_widgets_dict = {}

        show_widgets = current_settings_dict.get('ENABLE_WIDGETS', True)
        if show_widgets:
            edit_widgets = '''You can simply copy/paste from the available
widget file links below if you want to reuse existing widgets.<br />
</td></tr>
<tr><td>
<a class="urllink iconspace" href="/images/widgets/hello-grid.app">hello grid</a>,
<a class="urllink iconspace" href="/images/widgets/simple-calendar.app">simple calendar</a>,
<a class="urllink iconspace" href="/images/widgets/calendar.app">calendar</a>,
<a class="urllink iconspace" href="/images/widgets/gcal.app">google calendar</a>,
<a class="urllink iconspace" href="/images/widgets/calculator.app">calculator</a>,
<a class="urllink iconspace" href="/images/widgets/localrss.app">local rss reader</a>,
<a class="urllink iconspace" href="/images/widgets/rss.app">rss reader</a>,
<a class="urllink iconspace" href="/images/widgets/clock.app">clock</a>,
<a class="urllink iconspace" href="/images/widgets/weather.app">weather</a>,
<a class="urllink iconspace" href="/images/widgets/progressbar.app">progress bar</a>,
<a class="urllink iconspace" href="/images/widgets/simple-move.app">simple-move</a>,
<a class="urllink iconspace" href="/images/widgets/portlets.app">portlets</a>,
<a class="urllink iconspace" href="/images/widgets/countdown.app">countdown</a>,
<a class="urllink iconspace" href="/images/widgets/sparkline.app">mini chart</a>,
<a class="urllink iconspace" href="/images/widgets/piechart.app">pie chart</a>,
<a class="urllink iconspace" href="/images/widgets/simple-jobmon.app">simple-jobmon</a>,
<a class="urllink iconspace" href="/images/widgets/cert-countdown.app">certificate countdown</a>,
<a class="urllink iconspace" href="/images/widgets/disk-use.app">disk use progress bar</a>,
<a class="urllink iconspace" href="/images/widgets/jobs-stats.app">jobs stats table</a>,
<a class="urllink iconspace" href="/images/widgets/jobs-stats-chart.app">jobs stats chart</a>,
<a class="urllink iconspace" href="/images/widgets/daily-wm-comic.app">Daily WulffMorgenthaler comic</a>,
<a class="urllink iconspace" href="/images/widgets/kunet-login.app">KUnet login</a>
<a class="urllink iconspace" href="/images/widgets/tdchotspot-login.app">TDC Hotspot login</a>
</td></tr>
<tr><td>
<div class="warningtext">Please note that the widgets parser is rather grumpy
so you may have to avoid blank lines in your widget code below. Additionally
any errors in your widgets code may cause severe corruption in your pages, so
it may be a good idea to keep another browser tab/window ready for emergency
disabling of widgets while experimenting here.</div>
</td></tr>
<tr><td>
<input type="hidden" name="topic" value="widgets" />
</td></tr>
<tr><td>
'''

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="widgets">
<form class="save_settings save_widgets" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="widgets fixedlayout">
<tr class="title"><td class="centertext">
Default user defined widgets for all pages
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to customize the look and feel of the %(site)s web interfaces you
can add your own widgets here. If you leave the widgets blank you will just
get the default empty widget spaces.<br />
'''

        widgets_entries = get_widgets_specs()
        widgets_html = ''
        for (keyword, val) in widgets_entries:
            widgets_html += \
                """
            <tr class=title><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """\
                 % (keyword.replace('_', ' ').title(), val['Description'])
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_widgets_dict.has_key(keyword):
                        current_choice = current_widgets_dict[keyword]

                    if valid_choices:
                        widgets_html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            widgets_html += '''
                    <input type="checkbox" name="%s" %s value="%s">%s<br />'''\
                            % (keyword, selected, choice, choice)
                        widgets_html += '</div>'
                except:
                    area = """<textarea id='%s' cols=78 rows=10 name='%s'>""" \
                        % (keyword, keyword)
                    if current_widgets_dict.has_key(keyword):
                        area += '\n'.join(current_widgets_dict[keyword])
                    area += '</textarea>'
                    widgets_html += wrap_edit_area(keyword, area, widgets_edit)

        if show_widgets:
            edit_widgets += '''
        %s
            ''' % widgets_html
            edit_widgets += '''
        <tr><td>
        %(save_html)s
        <input type="submit" value="Save Widgets Settings" />
</td></tr>
'''
        else:
            edit_widgets = '''
<br/>
<div class="warningtext">
Widgets are disabled on your <em>General</em> settings page. Please enable
them there first if you want to customize your grid pages.
</div>
'''
        html += '''
%s
</table>
</form>
</div>
''' % edit_widgets
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'sftp' in topic_list:

        # load current ssh/sftp

        current_ssh_dict = load_ssh(client_id, configuration)
        if not current_ssh_dict:

            # no current ssh found

            current_ssh_dict = {}

        default_authkeys = current_ssh_dict.get('authkeys', '')
        default_authpassword = current_ssh_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_sftp_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_sftp_alias)
            create_alias_link(username, client_id, configuration.user_home)
        sftp_server = configuration.user_sftp_show_address
        sftp_port = configuration.user_sftp_show_port
        fingerprint_info = ''
        sftp_md5 = configuration.user_sftp_key_md5
        sftp_sha256 = configuration.user_sftp_key_sha256
        sftp_trust_dns = configuration.user_sftp_key_from_dns
        fingerprints = []
        hostkey_from_dns = 'ask'
        if sftp_md5:
            fingerprints.append("%s (MD5)" % sftp_md5)
        if sftp_sha256:
            fingerprints.append("%s (SHA256)" % sftp_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint <tt>%s</tt> first time you connect.''' % ' or '.join(fingerprints)
        if sftp_trust_dns:
            hostkey_from_dns = 'yes'
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="sshaccess">
<form class="save_settings save_sftp" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="sshsettings fixedlayout">
<tr class="title"><td class="centertext">
SFTP access to your %(site)s account
</td></tr>
<tr><td>
</td></tr>
<tr><td>
You can configure SFTP login to your %(site)s account for efficient file
access. On Linux/UN*X it also allows transparent access through SSHFS, and some
Linux distributions even natively integrate SFTP access in the file manager.
<br/>
<h3>Login Details</h3>
<ul>
<li>Host <em>%(sftp_server)s</em></li>
<li>Port <em>%(sftp_port)s</em></li>
<li>Username <em>%(username)s</em></li>
<li>%(auth_methods)s <em>as you choose below</em></li>
</ul>
%(fingerprint_info)s
</td></tr>
<tr><td>
<input type="hidden" name="topic" value="sftp" />
<div class="div-sftp-client-notes hidden">
<a href="javascript:toggleHidden('.div-sftp-client-notes');"
    class="removeitemlink iconspace" title="Toggle view">
    Show less SFTP client details...</a>
<h3>Graphical SFTP access</h3>
The FileZilla client is known to generally work for graphical access to your
%(site)s home over SFTP. It runs on all popular platforms and in the
<a href="http://portableapps.com/apps/internet/filezilla_portable">portable
version</a> it does not even require install privileges.<br/>
Enter the following values in the FileZilla Site Manager:
<pre>
Host %(sftp_server)s
Port %(sftp_port)s
Protocol SFTP
User %(username)s
Password YOUR_PASSWORD_HERE (leave empty for ssh key from key-agent)
</pre>
Other graphical clients like WinSCP should work as well.
<h3>Command line SFTP/SSHFS access on Linux/UN*X</h3>
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:<br />
<pre>
Host %(sftp_server)s
Hostname %(sftp_server)s
VerifyHostKeyDNS %(hostkey_from_dns)s
User %(username)s
Port %(sftp_port)s
# Assuming you have your private key in ~/.mig/id_rsa
IdentityFile ~/.mig/id_rsa
</pre>
From then on you can use sftp, lftp and sshfs to access your %(site)s home:
<pre>
sftp -B 258048 %(sftp_server)s
</pre>
<pre>
lftp -e "set net:connection-limit %(max_sessions)d" -p %(sftp_port)s sftp://%(sftp_server)s
</pre>
<pre>
mkdir -p remote-home
sshfs %(sftp_server)s: remote-home -o idmap=user -o big_writes -o reconnect
</pre>
You can also integrate with ordinary mounts by adding a line like:
<pre>
sshfs#%(username)s@%(sftp_server)s: /home/USER/remote-home fuse noauto,user,idmap=user,big_writes,reconnect,port=%(sftp_port)d 0 0
</pre>
to your /etc/fstab .
</div>
<div class="div-sftp-client-notes">
<a href="javascript:toggleHidden('.div-sftp-client-notes');"
    class="additemlink iconspace" title="Toggle view">Show more SFTP client details...
    </a>
</div>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_sftp_auth:
            html += '''
</td></tr>
<tr><td>
<h3>Authorized Public Keys</h3>
You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
<br/>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ssh_edit, 'BASIC')
            html += '''
(leave empty to disable sftp access with public keys)
</td></tr>
'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_sftp_auth:

            # We only want a single password and a masked input field
            html += '''
<tr><td>
<h3>Authorized Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<input type=password id="%(keyword_password)s" size=40 name="password"
value="%(default_authpassword)s" />
(leave empty to disable sftp access with password)
</p>
</td></tr>
'''

        html += '''
<tr><td>
%(save_html)s
<input type="submit" value="Save SFTP Settings" />
</td></tr>
'''

        html += '''
</table>
</form>
</div>
'''
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'sftp_server': sftp_server,
            'sftp_port': sftp_port,
            'hostkey_from_dns': hostkey_from_dns,
            'max_sessions': configuration.user_sftp_max_sessions,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_sftp_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'webdavs' in topic_list:

        # load current davs

        current_davs_dict = load_davs(client_id, configuration)
        if not current_davs_dict:

            # no current davs found

            current_davs_dict = {}

        default_authkeys = current_davs_dict.get('authkeys', '')
        default_authpassword = current_davs_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_davs_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_davs_alias)
            create_alias_link(username, client_id, configuration.user_home)
        davs_server = configuration.user_davs_show_address
        davs_port = configuration.user_davs_show_port
        fingerprint_info = ''
        # We do not support pretty outdated SHA1 in conf
        # davs_sha1 = configuration.user_davs_key_sha1
        davs_sha1 = ''
        davs_sha256 = configuration.user_davs_key_sha256
        fingerprints = []
        if davs_sha1:
            fingerprints.append("%s (SHA1)" % davs_sha1)
        if davs_sha256:
            fingerprints.append("%s (SHA256)" % davs_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint <tt>%s</tt> first time you connect.''' % ' or '.join(fingerprints)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="davsaccess">
<form class="save_settings save_davs" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="davssettings fixedlayout">
<tr class="title"><td class="centertext">
WebDAVS access to your %(site)s account
</td></tr>
<tr><td>

</td></tr>
<tr><td>
You can configure WebDAVS login to your %(site)s account for transparent file
access from your PC or workstation.<br/>
<h3>Login Details</h3>
<ul>
<li>Host <em>%(davs_server)s</em></li>
<li>Port <em>%(davs_port)s</em></li>
<li>Username <em>%(username)s</em></li>
<li>%(auth_methods)s <em>as you choose below</em></li>
</ul>
%(fingerprint_info)s
</td></tr>
<tr><td>
<input type="hidden" name="topic" value="webdavs" />
<div class="div-webdavs-client-notes hidden">
<a href="javascript:toggleHidden('.div-webdavs-client-notes');"
    class="removeitemlink iconspace" title="Toggle view">
    Show less WebDAVS client details...</a>
<h3>Graphical WebDAVS access</h3>
Several native file browsers and web browsers are known to generally work for
graphical access to your %(site)s home over WebDAVS.
<br />
Enter the address https://%(davs_server)s:%(davs_port)s and when fill in the
login details:
<pre>
Username %(username)s
Password YOUR_PASSWORD_HERE
</pre>
other graphical clients should work as well.
<h3>Command line WebDAVS access on Linux/UN*X</h3>
Save something like the following lines in your local ~/.netrc
to avoid typing the full login details every time:<br />
<pre>
machine %(davs_server)s
login %(username)s
password YOUR_PASSWORD_HERE
</pre>
From then on you can use e.g. cadaver or fusedav to access your %(site)s home:
<pre>
cadaver https://%(davs_server)s:%(davs_port)s
</pre>
<pre>
fusedav https://%(davs_server)s:%(davs_port)s remote-home -o uid=$(id -u) -o gid=$(id -g)
</pre>
</div>
<div class="div-webdavs-client-notes">
<a href="javascript:toggleHidden('.div-webdavs-client-notes');"
    class="additemlink iconspace" title="Toggle view">
    Show more WebDAVS client details...</a>
</div>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_davs_auth:
            html += '''
</td></tr>
<tr><td>
<h3>Authorized Public Keys</h3>
You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
<br/>'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, davs_edit, 'BASIC')
            html += '''
(leave empty to disable davs access with public keys)
</td></tr>
'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_davs_auth:
            # We only want a single password and a masked input field
            html += '''
<tr><td>
<h3>Authorized Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<input type=password id="%(keyword_password)s" size=40 name="password"
value="%(default_authpassword)s" />
(leave empty to disable davs access with password)
</p>
</td></tr>
'''

        html += '''
<tr><td>
%(save_html)s
<input type="submit" value="Save WebDAVS Settings" />
</td></tr>
'''

        html += '''
</table>
</form>
</div>
'''
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'davs_server': davs_server,
            'davs_port': davs_port,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_davs_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'ftps' in topic_list:

        # load current ftps

        current_ftps_dict = load_ftps(client_id, configuration)
        if not current_ftps_dict:

            # no current ftps found

            current_ftps_dict = {}

        default_authkeys = current_ftps_dict.get('authkeys', '')
        default_authpassword = current_ftps_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_ftps_alias:
            username = extract_field(client_id, configuration.user_ftps_alias)
            create_alias_link(username, client_id, configuration.user_home)
        ftps_server = configuration.user_ftps_show_address
        ftps_ctrl_port = configuration.user_ftps_show_ctrl_port
        fingerprint_info = ''
        # We do not support pretty outdated SHA1 in conf
        # ftps_sha1 = configuration.user_ftps_key_sha1
        ftps_sha1 = ''
        ftps_sha256 = configuration.user_ftps_key_sha256
        fingerprints = []
        if ftps_sha1:
            fingerprints.append("%s (SHA1)" % ftps_sha1)
        if ftps_sha256:
            fingerprints.append("%s (SHA256)" % ftps_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint <tt>%s</tt> first time you connect.''' % ' or '.join(fingerprints)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="ftpsaccess">
<form class="save_settings save_ftps" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="ftpssettings fixedlayout">
<tr class="title"><td class="centertext">
FTPS access to your %(site)s account
</td></tr>
<tr><td>
</td></tr>
<tr><td>
You can configure FTPS login to your %(site)s account for efficient file
access.<br/>
<h3>Login Details</h3>
<ul>
<li>Host <em>%(ftps_server)s</em></li>
<li>Port <em>%(ftps_ctrl_port)s</em></li>
<li>Username <em>%(username)s</em></li>
<li>%(auth_methods)s <em>as you choose below</em></li>
</ul>
%(fingerprint_info)s
</td></tr>
<tr><td>
<input type="hidden" name="topic" value="ftps" />
<div class="div-ftps-client-notes hidden">
<a href="javascript:toggleHidden('.div-ftps-client-notes');"
    class="removeitemlink iconspace" title="Toggle view">
    Show less FTPS client details...</a>
<h3>Graphical FTPS access</h3>
The FileZilla client is known to generally work for graphical access to your
%(site)s home over FTPS.
Enter the following values in the FileZilla Site Manager:
<pre>
Host %(ftps_server)s
Port %(ftps_ctrl_port)s
Protocol FTP
Encryption Explicit FTP over TLS
User %(username)s
Password YOUR_PASSWORD_HERE
</pre>
Other graphical clients like WinSCP should work as well. Some web browsers may
also work, if you enter the address ftps://%(ftps_server)s:%(ftps_ctrl_port)s
and fill in the login details when prompted:
<pre>
Username %(username)s
Password YOUR_PASSWORD_HERE
</pre>
<h3>Command line FTPS access on Linux/UN*X</h3>
Save something like the following lines in your local ~/.netrc
to avoid typing the full login details every time:<br />
<pre>
machine %(ftps_server)s
login %(username)s
password YOUR_PASSWORD_HERE
</pre>
From then on you can use e.g. lftp or CurlFtpFS to access your %(site)s home:
<pre>
lftp -e "set ftp:ssl-protect-data on; set net:connection-limit %(max_sessions)d" \\
     -p %(ftps_ctrl_port)s %(ftps_server)s
</pre>
<pre>
curlftpfs -o ssl %(ftps_server)s:%(ftps_ctrl_port)s remote-home \\
          -o user=%(username)s -ouid=$(id -u) -o gid=$(id -g)
</pre>
</div>
<div class="div-ftps-client-notes">
<a href="javascript:toggleHidden('.div-ftps-client-notes');"
    class="additemlink iconspace" title="Toggle view">Show more FTPS client details...
</a>
</div>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_ftps_auth:
            html += '''
</td></tr>
<tr><td>
<h3>Authorized Public Keys</h3>
You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
<br/>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ftps_edit, 'BASIC')
            html += '''
(leave empty to disable ftps access with public keys)
</td></tr>
'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_ftps_auth:

            # We only want a single password and a masked input field
            html += '''
<tr><td>
<h3>Authorized Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<input type=password id="%(keyword_password)s" size=40 name="password"
value="%(default_authpassword)s" />
(leave empty to disable ftps access with password)
</p>
</td></tr>
'''

        html += '''
<tr><td>
%(save_html)s
<input type="submit" value="Save FTPS Settings" />
</td></tr>
'''

        html += '''
</table>
</form>
</div>
'''
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'ftps_server': ftps_server,
            'ftps_ctrl_port': ftps_ctrl_port,
            'max_sessions': configuration.user_sftp_max_sessions,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_ftps_auth).title(),
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'seafile' in topic_list:

        # load current seafile

        current_seafile_dict = load_seafile(client_id, configuration)
        if not current_seafile_dict:

            # no current seafile found

            current_seafile_dict = {}

        keyword_password = "authpassword"
        default_authpassword = current_seafile_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_seafile_alias:
            username = extract_field(
                client_id, configuration.user_seafile_alias)
            create_alias_link(username, client_id, configuration.user_home)

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<script type="text/javascript" >
/* Helper function to open Seafile login window and fill username. Gives up
after max_tries * sleep_secs seconds if still not found.
*/
var login_window = null;
var user = '';
var try_count = 1;
var max_tries = 60;
var sleep_secs = 1;
function set_username() {
    var account_elem = login_window.document.getElementById("account");
    if (account_elem) {
        console.info("already logged in - no need to set user name");
        return true;
    }
    console.debug("set username "+user);
    var elems = login_window.document.getElementsByName("username");
    var i;
    for (i = 0; i < elems.length; i++) {
        console.debug("check elem "+i);
        if (elems[i].type == "text") {
            console.debug("found username elem "+i);
            elems[i].value = user;
            elems[i].readOnly = "readonly";
            console.info("done setting username in login form");
            return true;
        }
    }
    if (try_count >= max_tries) {
        console.warn("giving up after "+try_count+" tries to set username");
        return false;
    }
    console.debug("keep trying... ("+try_count+" of "+max_tries+")");
    try_count = try_count+1;
    setTimeout("set_username();", sleep_secs * 1000);
}
function open_login_window(url, username) {
    console.info("open login window "+url+" as "+username);
    user = username;
    login_window = window.open(url, "Seafile for "+username,
                               "width=1080, height=700, top=100, left=100");
    console.debug("call set_username");
    set_username();
}
</script>
<div id="seafileaccess">
<div id="seafileregaccess">
<form id="seafile_reg_form" method="post" action="%(seareg_url)s" target="_blank">
<table class="seafilesettings fixedlayout">
<tr class="title"><td class="centertext">
Seafile Synchronization on %(site)s
</td></tr>
<tr><td>
You can register a Seafile account on %(site)s to get synchronization and
sharing features like those known from e.g. Dropbox.<br/>
This enables you to keep one or more folders synchronized between
all your computers and to share those files and folders with other people.<br/>
</td></tr>
<tr><td>
<fieldset>
<legend>Register %(site)s Seafile Account</legend>
<input type="hidden" name="csrfmiddlewaretoken" value="" />
<!-- prevent user changing email but show it as read-only input field -->
<input class="input" id="id_email" name="email" type="hidden"
    value="%(username)s" />
<label for="dummy_email">Seafile Username</label>
<input class="input" id="dummy_email" type="text" value="%(username)s"
    readonly />
<br/>
<!-- NOTE: we require password policy in this case because pw MUST be set -->
<label for="id_password1">Choose Password</label>
<input class="input" id="id_password1" name="password1"
minlength=%(password_min_len)d maxlength=%(password_max_len)d required
pattern=".{%(password_min_len)d,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
type="password" />
<br/>
<label for="id_password2">Confirm Password</label>
<input class="input" id="id_password2" name="password2"
minlength=%(password_min_len)d maxlength=%(password_max_len)d required
pattern=".{%(password_min_len)d,%(password_max_len)d}"
title="Repeat your chosen password" type="password" />
<br/>
<input id="seafileregbutton" type="submit" value="Register" class="submit" />
and wait for email confirmation before continuing below.
</fieldset>
</td></tr>
</table>
</form>
</table>
<tr><td>
<fieldset>
<legend>Login and Install Clients</legend>
Once your %(site)s Seafile account is in place
<input id="seafileloginbutton" type="submit" value="log in"
onClick="open_login_window(\'%(seahub_url)s\', \'%(username)s\'); return false"
/> to it and install the client available there on any computers where you want
folder synchronization.<br/>
Optionally also install it on any mobile device(s) from which you want easy
access.<br/>
Then return here and <input id="seafilenextbutton" type="submit" value="proceed"
onClick="select_seafile_section(\'seafilesave\'); return false" /> with the
client set up and %(site)s integration.
</fieldset>
</td></tr>
</table>
</div>
<div id="seafilesaveaccess" style="display: none;">
<table class="seafilesettings fixedlayout">
<tr class="title"><td class="centertext">
Seafile Client Setup and %(site)s Integration
</td></tr>
<tr><td>
<fieldset>
<legend>Seafile Client Setup Details</legend>
You need to enter the following details to actually configure the Seafile
client(s) you installed in the previous step.
<br/>
<br/>
<label for="id_server">Server</label>
<input id=id_server type=text value="%(seafile_url)s" %(size)s %(ro)s /><br/>
<label for="id_username">Username</label>
<input id="id_username" type=text value="%(username)s" %(size)s %(ro)s /><br/>
<label for="id_password">Password</label>
<input id="id_password" type=text value="...the Seafile password you chose..."
%(size)s %(ro)s/><br/>
<br/>
You can always
<input id="seafilepreviousbutton" type="submit"
    value="go back"
    onClick="select_seafile_section(\'seafilereg\'); return false" />
to that registration and install step if you skipped a part of it or just want
to install more clients.<br/>
You can also directly open your
<input id="seafileloginbutton" type="submit" value="Seafile account"
onClick="open_login_window(\'%(seahub_url)s\', \'%(username)s\'); return false"
/> web page.<br/>
After the setup you can use your Seafile account as a standalone synchronization
and sharing solution.<br/>
</fieldset>
</td></tr>
<tr><td>
'''

        if configuration.user_seafile_ro_access:
            html += '''
<form class="save_settings save_seafile" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="seafile" />
<fieldset>
<legend>%(site)s Seafile Integration</legend>
If you wish you can additionally save your credentials here for Seafile
integration in your %(site)s user home.<br/>
Then your Seafile libraries will show up in a read-only mode under a new
<em>%(seafile_ro_dirname)s</em> folder e.g. on the Files page.<br/>
<br/>
'''

            if 'password' in configuration.user_seafile_auth:

                # We only want a single password and a masked input field
                html += '''
<p>
Please enter and save your chosen Seafile password again in the text field
below, to enable the read-only Seafile integration in your user home.
</p>
<p>
<input type=password id="%(keyword_password)s" size=40 name="password"
value="%(default_authpassword)s" />
(leave empty to disable seafile integration)
</p>
'''

            html += '''
%(save_html)s
<input id="seafilesavebutton" type="submit" value="Save Seafile Password" />
</fieldset>
</form>
'''
        html += '''
</td></tr>
</table>
</div>
<div id="seafileserverstatus"></div>
<!-- Dynamically fill CSRF token above and select active div if possible -->
<script type="text/javascript" >
    prepare_seafile_settings("%(seareg_url)s", "%(username)s",
                             "%(default_authpassword)s", "seafileserver",
                             "seafilereg", "seafilesave");
</script>
</div>
'''
        fill_helpers.update({
            'default_authpassword': default_authpassword,
            'keyword_password': keyword_password,
            'username': username,
            'seafile_ro_dirname': seafile_ro_dirname,
            'seahub_url': configuration.user_seahub_url,
            'seareg_url': configuration.user_seareg_url,
            'seafile_url': configuration.user_seafile_url,
            'auth_methods':
                ' / '.join(configuration.user_seafile_auth).title(),
            'ro': 'readonly=readonly',
            'size': 'size=50',
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'duplicati' in topic_list:

        # load current duplicati

        current_duplicati_dict = load_duplicati(client_id, configuration)
        if not current_duplicati_dict:

            # no current duplicati found

            current_duplicati_dict = {}

        configuration.protocol, configuration.username = [], []
        configuration.schedule = [i for (i, j) in duplicati_schedule_choices]
        # We save the pretty names in pickle but use internal ones here
        if configuration.user_duplicati_protocols:
            protocol_order = configuration.user_duplicati_protocols
        else:
            protocol_order = [j for (i, j) in duplicati_protocol_choices]
        reverse_proto_map = dict([(j, i) for (i, j) in
                                  duplicati_protocol_choices])

        enabled_map = {
            'davs': configuration.site_enable_davs,
            'sftp': configuration.site_enable_sftp or
            configuration.site_enable_sftp_subsys,
            'ftps': configuration.site_enable_ftps
        }
        username_map = {
            'davs': extract_field(client_id, configuration.user_davs_alias),
            'sftp': extract_field(client_id, configuration.user_sftp_alias),
            'ftps': extract_field(client_id, configuration.user_ftps_alias)
        }
        for proto in protocol_order:
            pretty_proto = reverse_proto_map[proto]
            if not enabled_map[proto]:
                continue
            if not pretty_proto in configuration.protocol:
                configuration.protocol.append(pretty_proto)
            if not username_map[proto] in configuration.username:
                configuration.username.append(username_map[proto])

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="duplicatiaccess">
<form class="save_settings save_duplicati" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="duplicati" />
<table class="duplicatisettings fixedlayout">
<tr class="title"><td class="centertext">
Duplicati Backup to %(site)s
</td></tr>
<tr><td>
You can install the <a href="https://www.duplicati.com">Duplicati</a> client on
your local machine and use it to backup arbitrary data to %(site)s.<br/>
We recommend the <a href="https://www.duplicati.com/download">
most recent version of Duplicati</a> to be able to import the generated
configurations from here directly.
<h3>Configure Backup Sets</h3>
You can define the backup sets here and then afterwards just download and
import the configuration file in your Duplicati client, to set up everything
for %(site)s backup use.
</td></tr>
'''

        duplicati_entries = get_duplicati_specs()
        for (keyword, val) in duplicati_entries:
            if val['Editor'] == 'hidden':
                continue
            html += """
            <tr class='title'><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """ % (keyword.replace('_', ' ').title(), val['Description'])

            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_duplicati_dict.has_key(keyword):
                        current_choice = current_duplicati_dict[keyword]

                    if valid_choices:
                        html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            html += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        html += '</div>'
                except:
                    area = """<textarea id='%s' cols=78 rows=10 name='%s'>""" \
                        % (keyword, keyword)
                    if current_duplicati_dict.has_key(keyword):
                        area += '\n'.join(current_duplicati_dict[keyword])
                    area += '</textarea>'
                    html += wrap_edit_area(keyword, area, duplicati_edit)
            elif val['Type'] == 'string':

                current_choice = ''
                if current_duplicati_dict.has_key(keyword):
                    current_choice = current_duplicati_dict[keyword]
                if val['Editor'] == 'select':
                    # get valid choices from conf

                    valid_choices = eval('configuration.%s' % keyword.lower())

                    if valid_choices:
                        html += '<select class="styled-select semi-square html-select" name="%s">' % keyword
                        for choice in valid_choices:
                            selected = ''
                            if choice == current_choice:
                                selected = 'selected'
                            html += '<option %s value="%s">%s</option>'\
                                % (selected, choice, choice)
                        html += '</select>'
                    else:
                        html += ''
                elif val['Editor'] == 'password':
                    html += '<input type="password" name="%s" value="%s"/>' \
                        % (keyword, current_choice)
                else:
                    html += '<input type="text" name="%s" value="%s"/>' \
                        % (keyword, current_choice)
                html += '<br />'
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if current_duplicati_dict.has_key(keyword):
                    current_choice = current_duplicati_dict[keyword]
                checked = ''
                if current_choice == True:
                    checked = 'checked'
                html += '<label class="switch">'
                html += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                  checked)
                html += '<span class="slider round"></span></label>'
                html += '<br /><br />'

            html += '''
            </td></tr>
        '''
        html += '''
        <tr><td>
        %(save_html)s
        <input type="submit" value="Save Duplicati Settings" />
        </td></tr>
</table>
</form>
'''

        html += '''
<table>
<tr><td>
<h3>Import Backup Sets</h3>
Your saved %(site)s Duplicati backup settings are available for download below:
<p>
'''

        saved_backup_sets = current_duplicati_dict.get('BACKUPS', [])
        duplicati_confs_path = os.path.join(base_dir, duplicati_conf_dir)
        duplicati_confs = []
        duplicati_confs += saved_backup_sets
        for conf_name in duplicati_confs:
            conf_file = "%s.json" % conf_name
            # Check existance of conf_file
            conf_path = os.path.join(duplicati_confs_path, conf_file)
            if not os.path.isfile(conf_path):
                logger.warning(
                    "saved duplicati conf %s is missing" % conf_path)
                continue
            html += '<a href="/cert_redirect/%s/%s">%s</a><br/>' \
                % (duplicati_conf_dir, conf_file, conf_file)
        if not duplicati_confs:
            html += '<em>No backup sets configured</em>'

        html += '''
</p>
After downloading you can import them directly in the most recent Duplicati
client versions from the link above.<br/>
</td></tr>
</table>
</div>
'''

        fill_helpers.update({
            'client_id': client_id,
            'size': 'size=50',
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'cloud' in topic_list:

        # load current cloud

        current_cloud_dict = load_cloud(client_id, configuration)
        if not current_cloud_dict:

            # no current cloud found

            current_cloud_dict = {}

        default_authkeys = current_cloud_dict.get('authkeys', '')
        default_authpassword = current_cloud_dict.get('authpassword', '')
        username = client_alias(client_id)
        cloud_host_pattern = '[One of your Cloud instances]'
        if configuration.user_cloud_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_cloud_alias)
            create_alias_link(username, client_id, configuration.user_home)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="cloudaccess">
    <form class="save_settings save_cloud" method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />

        <div>SSH access to your %(site)s cloud instance(s)</div>

<p>
You can configure SSH login to your %(site)s cloud instance(s) for interactive
use.
</p>
<h3>Login Details</h3>
Please refer to your Cloud management page for specific instance login details.
However, in general login requires the following: 
<ul>
<li>Host <em>%(cloud_host_pattern)s</em></li>
<li>Username <em>%(username)s</em></li>
<li>%(auth_methods)s <em>as you choose below</em></li>
</ul>

<input type="hidden" name="topic" value="cloud" />
<div class="div-cloud-client-notes hidden">
<a href="javascript:toggleHidden('.div-cloud-client-notes');"
    class="removeitemlink iconspace" title="Toggle view">
    Show less cloud client details...</a>

<h3>Graphical Cloud access</h3>
<p>The PuTTY client is known to generally work for graphical SSH access to
your %(site)s cloud instances. It runs on all popular platforms and in the
<a href="https://portableapps.com/apps/internet/putty_portable">portable
version</a> it does not even require install privileges.</p>
<p>
<!-- TODO: is this the right naming for PuTTY? -->
Enter the following values in the PuTTY Site Manager:</p>
<ul>
<li>Host %(cloud_host_pattern)s</li>
<li>Port 22</li>
<li>Protocol SSH</li>
<li>User %(username)s</li>
<li>Password YOUR_PASSWORD_HERE (leave empty for ssh key from key-agent)</li>
</ul>

<p>Other graphical clients like MindTerm, etc. should work as well.</p>

<h3>Command line SSH access on Linux/UN*X</h3>
<p>
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:</p>
<ul>
<li>Host %(cloud_host_pattern)s</li>
<li>Hostname %(cloud_host_pattern)s</li>
<li>User %(username)s</li>
<li># Assuming you have your private key in ~/.mig/id_rsa</li>
<li>IdentityFile ~/.mig/id_rsa</li>
</ul>

<p>
From then on you can use ssh to access your %(site)s instance:</p>
<ul>
<li>ssh %(cloud_host_pattern)s</li>
</ul>

</div>
<div class="div-cloud-client-notes">
<a href="javascript:toggleHidden('.div-cloud-client-notes');"
    class="additemlink iconspace" title="Toggle view">Show more cloud client details...
    </a>
</div>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_cloud_ssh_auth:
            html += '''

<h3>Authorized Public Keys</h3>
<p>You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
</p>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ssh_edit, 'BASIC')
            html += '''
<p>(leave empty to disable cloud access with public keys)</p>

'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_cloud_ssh_auth:

            # We only want a single password and a masked input field
            html += '''

<h3>Authorized Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
value="%(default_authpassword)s" />
(leave empty to disable cloud access with password)
</p>
'''

        html += '''
%(save_html)s
<input type="submit" value="Save Cloud Settings" />
'''

        html += '''

</form>
</div>
'''
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'cloud_host_pattern': cloud_host_pattern,
            'auth_methods': ' / '.join(configuration.user_cloud_ssh_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'twofactor' in topic_list:

        # load current twofactor

        current_twofactor_dict = load_twofactor(client_id, configuration)
        if not current_twofactor_dict:

            # no current twofactor found

            current_twofactor_dict = {}

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = """
<div id='otp_verify_dialog' title='Verify Authenticator App Token'
   class='centertext hidden'>
"""
        # NOTE: wizard needs dialog with form outside the main settings form
        # because nested forms cause problems
        html += twofactor_token_html(configuration)
        html += '''</div>
<div id="twofactor">
<form class="save_settings save_twofactor" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="twofactor fixedlayout">
<tr class="title"><td class="centertext">
2-Factor Authentication
</td></tr>
'''

        if configuration.site_enable_twofactor:
            b32_key, otp_interval, otp_uri = get_twofactor_secrets(
                configuration, client_id)
            # We limit key exposure by not showing it in clear and keeping it
            # out of backend dictionary with indirect generation only.

            # TODO: we might want to protect QR code with repeat basic login
            #       or a simple timeout since last login (cookie age).
            html += twofactor_wizard_html(configuration)
            check_url = '/%s/twofactor.py?action=check' % get_xgi_bin(
                configuration)
            fill_helpers.update({'otp_uri': otp_uri, 'b32_key': b32_key,
                                 'otp_interval': otp_interval,
                                 'check_url': check_url, 'demand_twofactor':
                                 'allow', 'enable_hint':
                                 'enable it for login below'})

        twofactor_entries = get_twofactor_specs(configuration)
        html += '''
        <tr class="otp_ready hidden"><td>
        <input type="hidden" name="topic" value="twofactor" />
        </td></tr>
        <tr class="otp_ready hidden"><td>
        </td></tr>
        '''
        for (keyword, val) in twofactor_entries:
            if val.get('Editor', None) == 'hidden':
                continue
            entry = """
            <tr class='otp_ready hidden'><td class='title'>
            %(Title)s
            </td></tr>
            <tr class='otp_ready hidden'><td>
            %(Description)s
            </td></tr>
            <tr class='otp_ready hidden'><td>
            """ % val
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_twofactor_dict.has_key(keyword):
                        current_choice = current_twofactor_dict[keyword]

                    if valid_choices:
                        entry += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            entry += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        entry += '</div>'
                    else:
                        entry += ''
                except:
                    # failed on evaluating configuration.%s

                    area = '''
                <textarea id="%s" cols=40 rows=1 name="%s">''' \
                        % (keyword, keyword)
                    if current_twofactor_dict.has_key(keyword):
                        area += '\n'.join(current_twofactor_dict[keyword])
                    area += '</textarea>'
                    entry += wrap_edit_area(keyword, area, general_edit,
                                            'BASIC')

            elif val['Type'] == 'string':

                # get valid choices from conf

                valid_choices = eval('configuration.%s' % keyword.lower())
                current_choice = ''
                if current_twofactor_dict.has_key(keyword):
                    current_choice = current_twofactor_dict[keyword]

                if valid_choices:
                    entry += '<select class="styled-select semi-square html-select" name="%s">' % keyword
                    for choice in valid_choices:
                        selected = ''
                        if choice == current_choice:
                            selected = 'selected'
                        entry += '<option %s value="%s">%s</option>'\
                            % (selected, choice, choice)
                    entry += '</select><br />'
                else:
                    entry += ''
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if current_twofactor_dict.has_key(keyword):
                    current_choice = current_twofactor_dict[keyword]
                checked = ''
                if current_choice == True:
                    checked = 'checked'
                entry += '<label class="switch">'
                entry += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                   checked)
                entry += '<span class="slider round"></span></label>'
                entry += '<br /><br />'
            html += """%s
            </td></tr>
            """ % entry

        html += '''<tr class="otp_ready hidden"><td>
        %(save_html)s
        <input type="submit" value="Save 2-Factor Auth Settings" />
</td></tr>
</table>
</form>
</div>
'''

        if configuration.site_enable_twofactor and \
            (current_twofactor_dict.get("MIG_OID_TWOFACTOR", False) or
             current_twofactor_dict.get("EXT_OID_TWOFACTOR", False)):
            html += """<script>
    setOTPProgress(['otp_intro', 'otp_install', 'otp_import', 'otp_verify',
                    'otp_ready']);
</script>
        """

        fill_helpers.update({
            'client_id': client_id,
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    # if ARC-enabled server:
    if 'arc' in topic_list:
        # provide information about the available proxy, offer upload
        try:
            home_dir = os.path.normpath(base_dir)
            session_Ui = arc.Ui(home_dir, require_user_proxy=True)
            proxy = session_Ui.getProxy()
            if proxy.IsExpired():
                # can rarely happen, constructor will throw exception
                output_objects.append({'object_type': 'text',
                                       'text':
                                       'Proxy certificate is expired.'})
            else:
                output_objects.append({'object_type': 'text',
                                       'text': 'Proxy for %s'
                                       % proxy.GetIdentitySN()})
                output_objects.append(
                    {'object_type': 'text',
                     'text': 'Proxy certificate will expire on %s (in %s sec.)'
                     % (proxy.Expires(), proxy.getTimeleft())
                     })
        except arc.NoProxyError, err:
            output_objects.append({'object_type': 'warning',
                                   'text': 'No proxy certificate to load: %s'
                                   % err.what()})

        output_objects = output_objects + arc.askProxy()

    output_objects.append({'object_type': 'html_form', 'text':
                           '<div class="vertical-spacer"></div>'})
    return (output_objects, returnvalues.OK)
