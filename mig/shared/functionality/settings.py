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
from shared.base import client_alias
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_settings, load_widgets
from shared.settingskeywords import get_settings_specs
from shared.widgetskeywords import get_widgets_specs
from shared.useradm import client_id_dir, mrsl_template, css_template, \
    ssh_authkeys, get_default_mrsl, get_default_css, get_ssh_authkeys

try:
    import shared.arcwrapper as arc
except Exception, exc:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass


cm_prefix = '/images/lib/codemirror'
cm_css_prefix = '%s/css' % cm_prefix
cm_js_prefix = '%s/js' % cm_prefix
txt_parsers, txt_stylesheets = ['parsedummy.js'], []
css_parsers, css_stylesheets = ["parsecss.js"], ["%s/csscolors.css" % cm_css_prefix]
web_parsers = ["parsexml.js", "parsecss.js", "tokenizejavascript.js",
               "parsejavascript.js", "parsehtmlmixed.js"]
web_stylesheets = ["%s/%s" % (cm_css_prefix, i) for i in \
                   ["xmlcolors.css", "jscolors.css", "csscolors.css"]]
edit_defaults = {'parserfile': txt_parsers, 'stylesheet': txt_stylesheets,
                  'path': "%s/" % cm_js_prefix, 'autoMatchParens': "true",
                  'tabMode': "spaces", 'indentUnit': 4, 'height': '600px'}
general_edit = edit_defaults.copy()
general_edit['height'] = '50px'
ssh_edit = edit_defaults.copy()
ssh_edit['height'] = '200px'
style_edit = edit_defaults.copy()
style_edit['parserfile'] = css_parsers
style_edit['stylesheet'] = css_stylesheets
widgets_edit = edit_defaults.copy()
widgets_edit['parserfile'] = web_parsers
widgets_edit['stylesheet'] = web_stylesheets
widgets_edit['height'] = '400px'


def py_to_js(options):
    """Format python dictionary as dictionary string used in javascript"""

    out = []
    for (key, val) in options.items():
        if isinstance(val, basestring):
            val = '"%s"' % val
        out.append('%s: %s' % (key, val))
    return '{%s}' % ', '.join(out)

def wrap_edit_area(name, area, edit_opts=edit_defaults, toolbar_buttons='ALL'):
    """Wrap HTML textarea in user friendly editor with syntax highlighting
    and optional basic toolbar.
    """
    init_buttons = ''
    button_impl = ''
    if toolbar_buttons:
        # TODO: switch to python generated html with icon buttons!
        init_buttons = '''  
  this.spellcheck;
  makeField(this.searchid, 15);
  makeButton("Search", "search");
  makeField(this.replaceid, 15);
  makeButton("Replace", "replace");
  makeButton("Replace All", "replaceall");
  makeSpace("SearchSep");
  makeButton("Undo", "undo");
  makeButton("Redo", "redo");
  makeSpace("UndoSep");
  makeButton("Help", "help");
'''
        button_impl = '''
  search: function() {
    var text = document.getElementById(this.searchid).value;
    if (!text) {
      alert("Please specify something in the search field!");
      return;
    }
    var first = true;
    do {
      var cursor = this.editor.getSearchCursor(text, first);
      first = false;
      while (cursor.findNext()) {
        cursor.select();
        return;
      }
    } while (confirm("End of document reached. Start over?"));
  },

  replace: function() {
    var from = document.getElementById(this.searchid).value;
    if (!from) {
      alert("Please specify something to replace in the search field!");
      return;
    }
    var to = document.getElementById(this.replaceid).value;
    var cursor = this.editor.getSearchCursor(from, false);
    while (cursor.findNext()) {
      cursor.select();
      if (confirm("Replace selected entry with '" + to + "'?")) {
        cursor.replace(to);
      }
    }
  },

  replaceall: function() {
    var from = document.getElementById(this.searchid).value, to;
    if (!from) {
      alert("Please specify something to replace in the search field!");
      return;
    }
    var to = document.getElementById(this.replaceid).value;

    var cursor = this.editor.getSearchCursor(from, false);
    while (cursor.findNext()) {
      cursor.replace(to);
    }
  },

  undo: function() {
    this.editor.undo();
  },
  
  redo: function() {
    this.editor.redo();
  },
  
  help: function() {
    alert("Quick help:\\n\\nShortcuts:\\nCtrl-z: undo\\nCtrl-y: redo\\nTab re-indents line\\nEnter inserts a new indented line\\n\\nPlease refer the CodeMirror manual for more detailed help.");
  },
'''

    if toolbar_buttons == 'ALL':
        init_buttons += '''
  makeSpace("HelpSep");
  makeField(this.jumpid, 2);
  makeButton("Jump to line", "jump");
  makeSpace("JumpSep");
  makeButton("Re-Indent all", "reindent");
  makeSpace("IndentSep");
  makeButton("Toggle line numbers", "line");
  //makeSpace("LineSep");
  //makeButton("Toggle spell check", "spell");
'''
        button_impl += '''
  jump: function() {
    var line = document.getElementById(this.jumpid).value;
    if (line && !isNaN(Number(line)))
      this.editor.jumpToLine(Number(line));
    else
      alert("Please specify a line to jump to in the jump field!");
  },

  line: function() {
    this.editor.setLineNumbers(!this.editor.lineNumbers);
    this.editor.focus();
  },

  reindent: function() {
    this.editor.reindent();
  },
  
  spell: function() {
    if (this.spellcheck == undefined) this.spellcheck = !this.editor.options.disableSpellcheck;
    this.spellcheck = !this.spellcheck
    this.editor.setSpellcheck(this.spellcheck);
    this.editor.focus();
  },
'''

    script = '''
/*
Modified version of the MirrorFrame example from CodeMirror:
Adds a basic toolbar to the editor widget with limited use of alert popups.
*/


function dumpobj(obj) {
  alert("dump: " + obj.toSource());
}


function TextAreaEditor(toolbar, textarea, options) {
  this.bar = toolbar;
  this.prefix = textarea;
  this.searchid = this.prefix + "searchfield";
  this.replaceid = this.prefix + "replacefield";
  this.jumpid = this.prefix + "jumpfield";

  var self = this;
  function makeButton(name, action) {
    var button = document.createElement("INPUT");
    button.type = "button";
    button.value = name;
    self.bar.appendChild(button);
    button.onclick = function() { self[action].call(self); };
  }
  function makeField(name, size) {
    var field = document.createElement("INPUT");
    field.type = "text";
    field.id = name;
    field.size = size;
    self.bar.appendChild(field);
  }
  function makeSpace(name) {
    var elem = document.createTextNode(" | ");
    self.bar.appendChild(elem);
  }

%s  

  this.editor = CodeMirror.fromTextArea(textarea, options);
}

TextAreaEditor.prototype = {
%s
};
''' % (init_buttons, button_impl)
    out = '''
<div class="inlineeditor" id="%sinlineeditor">
<div class="editortoolbar" id="%stoolbar">
<!--- filled by script --->
</div>
%s
<script type="text/javascript">
%s
var editor = new TextAreaEditor(document.getElementById("%stoolbar"), "%s", %s);
</script>
</div>
'''
    return out % (name, name, area, script, name, name, py_to_js(edit_opts))


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

    javascript = '''
<script type="text/javascript" src="%s/codemirror.js"></script>
''' % cm_js_prefix

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Settings'
    title_entry['javascript'] = javascript

    valid_topics = ['general', 'job', 'style']
    if configuration.site_script_deps:
        valid_topics.append('widgets')
    if configuration.arc_clusters:
        valid_topics.append('arc')
    if configuration.site_enable_sftp:
        valid_topics.append('ssh')
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
        <input type="hidden" name="topic" value="general" />
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
                        html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            html += '<input type="checkbox" name="%s" %s value=%s>%s<br />'\
                                    % (keyword, selected, choice, choice)
                        html += '</div>'
                except:
                    # failed on evaluating configuration.%s

                    area = \
                         '''<textarea id="%s" cols=40 rows=1 name="%s">''' % (keyword,
                                                               keyword)
                    if current_settings_dict.has_key(keyword):
                        area += '\n'.join(current_settings_dict[keyword])
                    area += '</textarea><br />'
                    html += wrap_edit_area(keyword, area, general_edit, 'BASIC')

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
            elif val['Type'] == 'boolean':
                valid_choices = [True, False]
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
'''
        keyword = "defaultjob"
        area = '''
<textarea id="%(keyword)s" cols=82 rows=25 name="editarea">
%(default_mrsl)s
</textarea>
'''
        html += wrap_edit_area(keyword, area, edit_defaults, 'BASIC')
        
        html += '''
</td></tr>
<tr><td>
<input type="submit" value="Save template" />
</form>
</td></tr>
</table>
</div>
'''
        html = html % {
            'default_mrsl': default_mrsl,
            'mrsl_template': mrsl_template,
            'site': configuration.short_title,
            'keyword': keyword
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
<input type="submit" value="Save style" />
</form>
</td></tr>
</table>
</div>
'''
        html = html % {
            'default_css': default_css,
            'css_template': css_template,
            'site': configuration.short_title,
            'keyword': keyword
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
<table class="widgets">
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
<a class="urllink" href="/images/widgets/localrss.app">local rss reader</a>,
<a class="urllink" href="/images/widgets/rss.app">rss reader</a>,
<a class="urllink" href="/images/widgets/clock.app">clock</a>,
<a class="urllink" href="/images/widgets/weather.app">weather</a>,
<a class="urllink" href="/images/widgets/progressbar.app">progress bar</a>,
<a class="urllink" href="/images/widgets/simple-move.app">simple-move</a>,
<a class="urllink" href="/images/widgets/portlets.app">portlets</a>,
<a class="urllink" href="/images/widgets/countdown.app">countdown</a>,
<a class="urllink" href="/images/widgets/sparkline.app">mini chart</a>,
<a class="urllink" href="/images/widgets/piechart.app">pie chart</a>,
<a class="urllink" href="/images/widgets/simple-jobmon.app">simple-jobmon</a>,
<a class="urllink" href="/images/widgets/cert-countdown.app">certificate countdown</a>,
<a class="urllink" href="/images/widgets/disk-use.app">disk use progress bar</a>,
<a class="urllink" href="/images/widgets/jobs-stats.app">jobs stats table</a>,
<a class="urllink" href="/images/widgets/jobs-stats-chart.app">jobs stats chart</a>,
<a class="urllink" href="/images/widgets/kunet-login.app">KUnet login</a>
</td></tr>
<tr><td>
<div class="warningtext">Please note that the widgets parser is rather grumpy so you may have to avoid blank lines in your widget code below. Additionally any errors in your widgets code may cause severe corruption in your pages, so it may be a good idea to keep another browser tab/window open on this page while experimenting.</div> 
</td></tr>
<tr><td>
<form method="post" action="settingsaction.py">
<input type="hidden" name="topic" value="widgets" />
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
                        html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            html += '<input type="checkbox" name="%s" %s value=%s>%s<br />'\
                                    % (keyword, selected, choice, choice)
                        html += '</div>'
                except:
                    area = \
                         """<textarea id='%s' cols=78 rows=10 name='%s'>""" % \
                         (keyword, keyword)
                    if current_widgets_dict.has_key(keyword):
                        area += '\n'.join(current_widgets_dict[keyword])
                    area += '</textarea><br />'
                    html += wrap_edit_area(keyword, area, widgets_edit)

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

    if 'ssh' in topics:
        authkeys_path = os.path.join(base_dir, ssh_authkeys)
        default_authkeys = '\n'.join(get_ssh_authkeys(authkeys_path))
        sftp_server = configuration.user_sftp_address
        # address may be empty to use all interfaces - then use FQDN
        if not sftp_server:
            sftp_server = configuration.server_fqdn
        sftp_port = configuration.user_sftp_port
        html = \
        '''
<div id="sshaccess">
<table class="sshsettings">
<tr class="title"><td class="centertext">
SSH/SFTP access to your MiG account
</td></tr>
<tr><td>
</td></tr>
<tr><td>
<p>
Allow SSH/SFTP login to your %(site)s account with provided public key(s)
and your automatic username:
<pre>%(username)s</pre>
</p>
<p>
You can use any existing SSH RSA keys you may have or create a new one with:
<pre>
ssh-keygen -t rsa -f ~/.mig/id_rsa
</pre>
Then save the contents of the public key (id_rsa.pub) below.
</p>
<p>
Finally save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details each time:<br />
<pre>
Host %(sftp_server)s
Hostname %(sftp_server)s
User %(username)s
Port %(sftp_port)s
IdentityFile ~/.mig/id_rsa
</pre>
</p>
<p>
From then on you can use sftp and sshfs to access your MiG home:
<pre>
sftp %(sftp_server)s
</pre>
<pre>
sshfs %(sftp_server)s: mig-home -o uid=$(id -u) -o gid=$(id -g)
</pre>
</p>
</td></tr>
<tr><td>
<form method="post" action="editfile.py">
<input type="hidden" name="path" value="%(ssh_authkeys)s" />
<input type="hidden" name="newline" value="unix" />
'''
        keyword = "authkeys"
        area = '''
<textarea id="%(keyword)s" cols=82 rows=5 name="editarea">
%(default_authkeys)s
</textarea>
'''
        html += wrap_edit_area(keyword, area, ssh_edit, 'BASIC')
        
        html += '''
</td></tr>
<tr><td>
<input type="submit" value="Save keys" />
</form>
</td></tr>
</table>
</div>
'''
        html = html % {
            'default_authkeys': default_authkeys,
            'ssh_authkeys': ssh_authkeys,
            'site': configuration.short_title,
            'keyword': keyword,
            'username': client_alias(client_id),
            'sftp_server': sftp_server,
            'sftp_port': sftp_port,
            }

        output_objects.append({'object_type': 'html_form', 'text': html})

    # if ARC-enabled server:
    if 'arc' in topics:
        # provide information about the available proxy, offer upload
        try:
            home_dir = os.path.normpath(base_dir)
            session_Ui = arc.Ui(home_dir, require_user_proxy=True)
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


