#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - [insert a few words of module description on this line]
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

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables
from shared.settings import load_settings, load_widgets
from shared.settingskeywords import get_settings_specs
from shared.widgetskeywords import get_widgets_specs
from shared.useradm import client_id_dir, mrsl_template, css_template, \
    get_default_mrsl, get_default_css

try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass

def signature():
    """Signature of the main function"""

    defaults = {'topic': ['general']}
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

    valid_topics = ['general', 'job', 'style', 'widgets']
    if configuration.arc_clusters:
        valid_topics.append('arc')
    topics = accepted['topic']
    topics = [i for i in topics if i in valid_topics]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Settings'})

    links = []
    for name in valid_topics:
        links.append({'object_type': 'link', 
                      'destination': "settings.py?topic=%s" % name,
                      'class': '%ssettingslink' % name,
                      'title': 'Switch to %s settings' % name,
                      'text' : '%s settings' % name,
                      })
    output_objects.append({'object_type': 'multilinkline', 'links': links})
    output_objects.append({'object_type': 'text', 'text': ''})

    # load current settings

    current_settings_dict = load_settings(client_id, configuration)
    if not current_settings_dict:

        # no current settings found

        current_settings_dict = {}

    if not topics:
        output_objects.append({'object_type': 'error_text', 'text': 'No valid topics!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if 'general' in topics:
        html = \
             '''
        <div id="settings">
        <table class="settings">
        <tr class="title"><td class="centertext">
        Select your %s settings
        </td></tr>
        <tr><td>
        </td></tr>
        <tr><td>
        <form method="post" action="settingsaction.py">
        Please note that if you want to set multiple values (e.g. addresses) in the same field, you must write each value on a separate line.
        </td></tr>
        <tr><td>
        </td></tr>
        ''' % configuration.site_title
        settings_entries = get_settings_specs()
        for (keyword, val) in settings_entries:
            if 'notify' == val['Context'] and keyword.lower() not in configuration.notify_protocols:
                continue
            html += \
                """
            <tr class=title><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """\
                 % (keyword, val['Description'])
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_settings_dict.has_key(keyword):
                        current_choice = current_settings_dict[keyword]

                    if len(valid_choices) > 0:
                        html += '<select multiple name=%s>' % keyword
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'selected'
                            html += '<option %s value=%s>%s</option>'\
                                    % (selected, choice, choice)
                        html += '</select><br />'
                except:
                    # failed on evaluating configuration.%s

    #        elif val['Type'] == 'multiplestrings':
                    html += \
                         """<textarea cols="40" rows="1" wrap="off" name="%s">"""\
                         % keyword
                    if current_settings_dict.has_key(keyword):
                        html += '\n'.join(current_settings_dict[keyword])
                    html += '</textarea><br />'

            elif val['Type'] == 'string':

                # get valid choices from conf

                valid_choices = eval('configuration.%s' % keyword.lower())
                current_choice = ''
                if current_settings_dict.has_key(keyword):
                    current_choice = current_settings_dict[keyword]

                if len(valid_choices) > 0:
                    html += '<select name=%s>' % keyword
                    for choice in valid_choices:
                        selected = ''
                        if choice == current_choice:
                            selected = 'selected'
                        html += '<option %s value=%s>%s</option>'\
                             % (selected, choice, choice)
                    html += '</select><br />'
            html += """
            </td></tr>
            """

        html += \
            """
        <tr><td>
        <input type="submit" value="Save Settings" />
        </form>
        </td></tr>
        </table>
        </div>
        """
        output_objects.append({'object_type': 'html_form', 'text': html})

    if 'job' in topics:
        mrsl_path = os.path.join(base_dir, mrsl_template)

        default_mrsl = get_default_mrsl(mrsl_path)
        html = \
        '''
<div id="defaultmrsl">
<table class="defaultjob">
<tr class="title"><td class="centertext">
Default job on submit page
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you use the same fields and values in many of your jobs, you can save your preferred job description here to always start out with that description on your submit job page.
</td></tr>
<tr><td>
</td></tr>
<tr><td>
<form method="post" action="editfile.py">
<input type="hidden" name="path" value="%(mrsl_template)s" />
<input type="hidden" name="newline" value="unix" />
<textarea cols="82" rows="25" wrap="off" name="editarea">
%(default_mrsl)s
</textarea>
</td></tr>
<tr><td>
<input type="submit" value="Save template" />
<input type="reset" value="Forget changes" />
</form>
</td></tr>
</table>
</div>
''' % {
            'default_mrsl': default_mrsl,
            'mrsl_template': mrsl_template,
            'site': configuration.short_title,
            }

        output_objects.append({'object_type': 'html_form', 'text': html})

    if 'style' in topics:
        css_path = os.path.join(base_dir, css_template)
        default_css = get_default_css(css_path)
        html = \
             '''
<div id="defaultcss">
<table class="defaultstyle">
<tr class="title"><td class="centertext">
Default CSS (style) for all pages
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to customize the look and feel of the %(site)s web interfaces you can override default values here. If you leave the style file blank you will just use the default style.<br />
You can copy paste from the available style file links below if you want to override specific parts.<br />
Please note that you can not save an empty style file, but must at least leave a blank line to use defaults.
</td></tr>
<tr><td>
<a class="urllink" href="/images/default.css">default</a> , <a class="urllink" href="/images/bluesky.css">bluesky</a>
</td></tr>
<tr><td>
</td></tr>
<tr><td>
<form method="post" action="editfile.py">
<input type="hidden" name="path" value="%(css_template)s" />
<input type="hidden" name="newline" value="unix" />
<textarea cols="82" rows="25" wrap="off" min_len=1 name="editarea">
%(default_css)s
</textarea>
</td></tr>
<tr><td>
<input type="submit" value="Save style" />
<input type="reset" value="Forget changes" />
</form>
</td></tr>
</table>
</div>
'''\
        % {
            'default_css': default_css,
            'css_template': css_template,
            'site': configuration.short_title,
            }

        output_objects.append({'object_type': 'html_form', 'text': html})

    if 'widgets' in topics:

        # load current widgets

        current_widgets_dict = load_widgets(client_id, configuration)
        if not current_widgets_dict:
            
            # no current widgets found
            
            current_widgets_dict = {}

        html = \
             '''
<div id="widgets">
<table class="swidgets">
<tr class="title"><td class="centertext">
Default user defined widgets for all pages
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to customize the look and feel of the %s web interfaces you can add your own widgets here. If you leave the widgets blank you will just get the default empty widget spaces.<br />
You can simply copy/paste from the available widget file links below if you want to reuse existing widgets.<br />
</td></tr>
<tr><td>
<a class="urllink" href="/images/widgets/hello-grid.app">hello grid</a>,
<a class="urllink" href="/images/widgets/simple-calendar.app">simple calendar</a>,
<a class="urllink" href="/images/widgets/calendar.app">calendar</a>,
<a class="urllink" href="/images/widgets/calculator.app">calculator</a>,
<a class="urllink" href="/images/widgets/rss.app">rss reader</a>,
<a class="urllink" href="/images/widgets/clock.app">clock</a>,
<a class="urllink" href="/images/widgets/weather.app">weather</a>,
<a class="urllink" href="/images/widgets/progressbar.app">progress bar</a>,
<a class="urllink" href="/images/widgets/countdown.app">countdown</a>
</td></tr>
<tr><td>
<div class="warningtext">Please note that the widgets parser is rather grumpy so you may have to avoid blank lines and "#" signs in your widget code below. Additionally any errors in your widgets code may cause severe corruption in your pages, so it may be a good idea to keep another browser tab/window open on this page while experimenting.</div> 
</td></tr>
<tr><td>
<form method="post" action="widgetsaction.py">
</td></tr>
<tr><td>
''' % configuration.short_title

        widgets_entries = get_widgets_specs()
        for (keyword, val) in widgets_entries:
            html += \
                """
            <tr class=title><td>
            %s
            </td></tr>
            <tr><td>
            %s
            </td></tr>
            <tr><td>
            """\
                 % (keyword, val['Description'])
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if current_widgets_dict.has_key(keyword):
                        current_choice = current_widgets_dict[keyword]

                    if len(valid_choices) > 0:
                        html += '<select multiple name=%s>' % keyword
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'selected'
                            html += '<option %s value=%s>%s</option>'\
                                    % (selected, choice, choice)
                        html += '</select><br />'
                except:
                    html += \
                         """<textarea cols="78" rows="10" wrap="off" name="%s">"""\
                         % keyword
                    if current_widgets_dict.has_key(keyword):
                        html += '\n'.join(current_widgets_dict[keyword])
                    html += '</textarea><br />'

        html += \
             '''
        <tr><td>
        <input type="submit" value="Save Widgets" />
        </form>
</td></tr>
</table>
</div>
'''
        output_objects.append({'object_type': 'html_form', 'text': html})

    # if ARC-enabled server:
    if 'arc' in topics:
        # provide information about the available proxy, offer upload
        try:
            home_dir = os.path.normpath(base_dir)
            session_Ui = arc.Ui(home_dir)
            proxy = session_Ui.getProxy()
            if proxy.IsExpired():
                # can rarely happen, constructor will throw exception
                output_objects.append({'object_type': 'text', 
                                       'text': 'Proxy certificate is expired.'})
            else:
                output_objects.append({'object_type': 'text', 
                                       'text': 'Proxy for %s' \
                                       % proxy.GetIdentitySN()})
                output_objects.append(
                    {'object_type': 'text', 
                     'text': 'Proxy certificate will expire on %s (in %s sec.)' \
                     % (proxy.Expires(), proxy.getTimeleft())
                     })
        except arc.NoProxyError, err:
            output_objects.append({'object_type':'warning',
                                   'text': 'No proxy certificate to load: %s' \
                                   % err.what()})
    
        output_objects = output_objects + arc.askProxy()
    
    return (output_objects, returnvalues.OK)


