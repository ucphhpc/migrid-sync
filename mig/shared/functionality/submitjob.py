#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submitjob - Job submission interfaces
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Simple front end to job and file uploads"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import any_vgrid, default_mrsl_filename, maxfill_fields, \
    keyword_all, csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.htmlgen import fancy_upload_js, fancy_upload_html, \
    themed_styles
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.mrslkeywords import get_job_specs
from mig.shared.parser import parse_lines
from mig.shared.refunctions import list_runtime_environments
from mig.shared.useradm import get_default_mrsl
from mig.shared.vgridaccess import user_vgrid_access, user_allowed_res_exes


def signature():
    """Signature of the main function"""

    defaults = {'description': ['False']}
    return ['html_form', defaults]


def available_choices(configuration, client_id, field, spec):
    """Find the available choices for the selectable field.
    Tries to lookup all valid choices from configuration if field is
    specified to be a string variable.
    """
    if 'boolean' == spec['Type']:
        choices = [True, False]
    elif spec['Type'] in ('string', 'multiplestrings'):
        try:
            choices = getattr(configuration, '%ss' % field.lower())
        except AttributeError as exc:
            configuration.logger.error('%s' % exc)
            choices = []
    else:
        choices = []
    if not spec['Required']:
        choices = [''] + choices
    default = spec['Value']
    if default in choices:
        choices = [default] + [i for i in choices if not default == i]
    return choices


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
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

    show_description = accepted['description'][-1].lower() == 'true'

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Job execution is not enabled on this system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    template_path = os.path.join(base_dir, default_mrsl_filename)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Submit Job'
    user_settings = title_entry.get('user_settings', {})
    output_objects.append({'object_type': 'header', 'text': 'Submit Job'})
    default_mrsl = get_default_mrsl(template_path, logger)
    if not user_settings or 'SUBMITUI' not in user_settings:
        logger.info('Settings dict does not have SUBMITUI key - using default'
                    )
        submit_style = configuration.submitui[0]
    else:
        submit_style = user_settings['SUBMITUI']

    # We generate all 3 variants of job submission (fields, textarea, files),
    # initially hide them and allow to switch between them using js.

    # could instead extract valid prefixes as in settings.py
    # (means: by "eval" from configuration). We stick to hard-coding.
    submit_options = ['fields_form', 'textarea_form', 'files_form']

    open_button_id = 'open_fancy_upload'
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'dest_dir': '.' + os.sep, 'fancy_open': open_button_id,
                    'default_mrsl': default_mrsl, 'form_method': form_method,
                    'csrf_field': csrf_field, 'csrf_limit': csrf_limit}
    target_op = 'uploadchunked'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    (add_import, add_init, add_ready) = fancy_upload_js(configuration,
                                                        csrf_token=csrf_token)
    add_init += '''
    submit_options = %s;

    function setDisplay(this_id, new_d) {
        //console.log("setDisplay with: "+this_id);
        el = document.getElementById(this_id)
        if (el == undefined || el.style == undefined) {
            console.log("failed to locate display element: "+this_id);
            return; // avoid js null ref errors
        }
        el.style.display=new_d;
    }

    function switchTo(name) {
        //console.log("switchTo: "+name);
        for (o=0; o < submit_options.length; o++) {
            if (name == submit_options[o]) {
                setDisplay(submit_options[o],"block");
            } else {
                setDisplay(submit_options[o],"none");
            }
        }
    }
    ''' % submit_options
    add_ready += '''
    switchTo("%s");
    setUploadDest("%s");
    /* wrap openFancyUpload in function to avoid event data as argument */
    $("#%s").click(function() { openFancyUpload(); });
    ''' % (submit_style + "_form", fill_helpers['dest_dir'], open_button_id)
    fancy_dialog = fancy_upload_html(configuration)
    # TODO: can we update style inline to avoid explicit themed_styles?
    title_entry['style'] = themed_styles(configuration,
                                         base=['jquery.fileupload.css',
                                               'jquery.fileupload-ui.css'],
                                         skin=['fileupload-ui.custom.css'],
                                         user_settings=user_settings)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'text', 'text':
                           'This page is used to submit jobs to the grid.'})

    output_objects.append({'object_type': 'verbatim',
                           'text': '''
There are %s interface styles available that you can choose among:''' %
                           len(submit_options)})

    links = []
    for opt in submit_options:
        name = opt.split('_', 2)[0]
        links.append({'object_type': 'link',
                      'destination': "javascript:switchTo('%s')" % opt,
                      'class': 'submit%slink iconspace' % name,
                      'title': 'Switch to %s submit interface' % name,
                      'text': '%s style' % name,
                      })
    output_objects.append({'object_type': 'multilinkline', 'links': links})

    output_objects.append({'object_type': 'text', 'text': '''
Please note that changes to the job description are *not* automatically
transferred if you switch style.'''})

    output_objects.append({'object_type': 'html_form', 'text':
                           '<div id="fields_form" style="display:none;">\n'})

    # Fields
    output_objects.append({'object_type': 'sectionheader', 'text': 'Please fill in your job description in the fields'
                           ' below:'
                           })
    output_objects.append({'object_type': 'text', 'text': """
Please fill in one or more fields below to define your job before hitting
Submit Job at the bottom of the page.
Empty fields will simply result in the default value being used and each field
is accompanied by a help link providing further details about the field."""})

    fill_helpers.update({'fancy_dialog': fancy_dialog})
    target_op = 'submitfields'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    output_objects.append({'object_type': 'html_form', 'text': """
<div class='submitjob'>
<form method='%(form_method)s' action='%(target_op)s.py'> 
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
""" % fill_helpers})
    show_fields = get_job_specs(configuration)
    try:
        parsed_mrsl = dict(parse_lines(default_mrsl))
    except:
        parsed_mrsl = {}

    # Find allowed VGrids and Runtimeenvironments and add them to
    # configuration object for automated choice handling

    vgrid_access = user_vgrid_access(configuration, client_id) + \
        [any_vgrid]
    vgrid_access.sort()
    configuration.vgrids = vgrid_access
    (re_status, allowed_run_envs) = list_runtime_environments(configuration)
    if not re_status:
        logger.error('Failed to extract allowed runtime envs: %s' %
                     allowed_run_envs)
        allowed_run_envs = []
    allowed_run_envs.sort()
    configuration.runtimeenvironments = allowed_run_envs
    # TODO: next call is slow because we walk and reload all pickles
    user_res = user_allowed_res_exes(configuration, client_id)

    # Add valid MAXFILL values to automated choice handling

    configuration.maxfills = [keyword_all] + maxfill_fields

    # Allow any exe unit on all allowed resources

    allowed_resources = ['%s_*' % res for res in user_res]
    allowed_resources.sort()
    configuration.resources = allowed_resources
    field_size = 30
    area_cols = 80
    area_rows = 5

    for (field, spec) in show_fields:
        title = spec['Title']
        if show_description:
            description = '%s<br />' % spec['Description']
        else:
            description = ''
        field_type = spec['Type']
        # Use saved value and fall back to default if it is missing
        saved = parsed_mrsl.get('::%s::' % field, None)
        if saved:
            if not spec['Type'].startswith('multiple'):
                default = saved[0]
            else:
                default = saved
        else:
            default = spec['Value']
        # Hide sandbox field if sandboxes are disabled
        if field == 'SANDBOX' and not configuration.site_enable_sandboxes:
            continue
        if 'invisible' == spec['Editor']:
            continue
        if 'custom' == spec['Editor']:
            continue
        output_objects.append({'object_type': 'html_form', 'text': """
<b>%s:</b>&nbsp;<a class='infolink iconspace' href='docs.py?show=job#%s'>
help</a><br />
%s""" % (title, field, description)
        })

        if 'input' == spec['Editor']:
            if field_type.startswith('multiple'):
                output_objects.append({'object_type': 'html_form', 'text': """
<textarea class='fillwidth padspace' name='%s' cols='%d' rows='%d'>%s</textarea><br />
""" % (field, area_cols, area_rows, '\n'.join(default))
                })
            elif field_type == 'int':
                output_objects.append({'object_type': 'html_form', 'text': """
<input type='number' name='%s' size='%d' value='%s' min=0 required pattern='[0-9]+' /><br />
""" % (field, field_size, default)
                })
            else:
                output_objects.append({'object_type': 'html_form', 'text': """
<input type='text' name='%s' size='%d' value='%s' /><br />
""" % (field, field_size, default)
                })
        elif 'select' == spec['Editor']:
            choices = available_choices(configuration, client_id,
                                        field, spec)
            res_value = default
            value_select = ''
            if field_type.startswith('multiple'):
                value_select += '<div class="scrollselect">'
                for name in choices:
                    name = "%s" % name
                    # Blank default value does not make sense here
                    if not name:
                        continue
                    selected = ''
                    if name in res_value:
                        selected = 'checked'
                    value_select += '''
                        <input type="checkbox" name="%s" %s value=%s>%s<br />
                        ''' % (field, selected, name, name)
                value_select += '</div>\n'
            else:
                value_select += "<select name='%s'>\n" % field
                res_value = "%s" % res_value
                for name in choices:
                    name = "%s" % name
                    selected = ''
                    if res_value == name:
                        selected = 'selected'
                    display = name
                    if display == '':
                        display = ' '
                    value_select += """<option %s value='%s'>%s</option>\n""" \
                                    % (selected, name, display)
                value_select += """</select><br />\n"""
            output_objects.append({'object_type': 'html_form', 'text': value_select
                                   })
        output_objects.append({'object_type': 'html_form', 'text': "<br />"})

    output_objects.append({'object_type': 'html_form', 'text': """
<br />
<table class='centertext'>
<tr><td><input type='submit' value='Submit Job' />
<input type='checkbox' name='save_as_default'> Save as default job template
</td></tr>
</table>
<br />
</form>
</div>
"""
                           })
    output_objects.append({'object_type': 'html_form', 'text': '''
</div><!-- fields_form-->
<div id="textarea_form" style="display:none;">
'''})

    # Textarea
    output_objects.append({'object_type': 'sectionheader', 'text': 'Please enter your mRSL job description below:'
                           })
    output_objects.append({'object_type': 'html_form', 'text': """
<div class='smallcontent'>
Job descriptions can use a wide range of keywords to specify job requirements
and actions.<br />
Each keyword accepts one or more values of a particular type.<br />
The full list of keywords with their default values and format is available in
the on-demand <a href='docs.py?show=job'>mRSL Documentation</a>.
<p>
Actual examples for inspiration:
<a href=/public/cpuinfo.mRSL>CPU Info</a>,
<a href=/public/basic-io.mRSL>Basic I/O</a>,
<a href=/public/notification.mRSL>Job Notification</a>,
<a href=/public/povray.mRSL>Povray</a> and
<a href=/public/vcr.mRSL>VCR</a>
</div>
    """})

    target_op = 'textarea'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    output_objects.append({'object_type': 'html_form', 'text': """
<!-- 
Please note that textarea.py chokes if no nonempty KEYWORD_X_Y_Z fields 
are supplied: thus we simply send a bogus jobname which does nothing
-->
<form method='%(form_method)s' action='%(target_op)s.py'> 
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<table class='submitjob'>
<tr><td class='centertext'>
<input type=hidden name=jobname_0_0_0 value=' ' />
<textarea class='fillwidth padspace' rows='25' name='mrsltextarea_0'>
%(default_mrsl)s
</textarea>
</td></tr>
<tr><td class='centertext'>
<input type='submit' value='Submit Job' />
<input type='checkbox' name='save_as_default' >Save as default job template
</td></tr>
</table>
</form>
""" % fill_helpers})

    output_objects.append({'object_type': 'html_form',
                           'text': '''
</div><!-- textarea_form-->
<div id="files_form" style="display:none;">
'''})
    # Upload form

    output_objects.append({'object_type': 'sectionheader', 'text': 'Please upload your job file or packaged job files'
                           ' below:'
                           })
    output_objects.append({'object_type': 'html_form', 'text': """
<form enctype='multipart/form-data' method='%(form_method)s'
    action='%(target_op)s.py'> 
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<table class='files'>
<tr class='title'><td class='centertext' colspan=4>
Upload job files
</td></tr>
<tr><td colspan=3>
Upload file to current directory (%(dest_dir)s)
</td><td><br /></td></tr>
<tr><td colspan=2>
Extract package files (.zip, .tar.gz, .tar.bz2)
</td><td colspan=2>
<input type=checkbox name='extract_0' />
</td></tr>
<tr><td colspan=2>
Submit mRSL files (also .mRSL files included in packages)
</td><td colspan=2>
<input type=checkbox name='submitmrsl_0' checked />
</td></tr>
<tr><td>    
File to upload
</td><td class='righttext' colspan=3>
<input name='fileupload_0_0_0' type='file'/>
</td></tr>
<tr><td>
Optional remote filename (extra useful in windows)
</td><td class='righttext' colspan=3>
<input name='default_remotefilename_0' type='hidden' value='%(dest_dir)s'/>
<input name='remotefilename_0' type='text' size='50' value='%(dest_dir)s'/>
<input type='submit' value='Upload' name='sendfile'/>
</td></tr>
</table>
</form>
<table class='files'>
<tr class='title'><td class='centertext'>
Upload other files efficiently (using chunking).
</td></tr>
<tr><td class='centertext'>
<button id='%(fancy_open)s'>Open Upload dialog</button>
</td></tr>
</table>
</div><!-- files_form-->

%(fancy_dialog)s
""" % fill_helpers})

    return (output_objects, status)
