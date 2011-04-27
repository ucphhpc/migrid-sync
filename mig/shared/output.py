#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# output - General formatting of backend output objects
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

"""Module with functions to generate output in format
specified by the client."""

import traceback

import shared.returnvalues as returnvalues
from shared.html import get_cgi_html_header, get_cgi_html_footer
from shared.objecttypes import validate
from shared.prettyprinttable import pprint_table
from shared.safeinput import html_escape

row_name = ('even_row', 'odd_row')


def txt_table_if_have_keys(header, input_dict, keywordlist):
    """create txt table contents based on keys in a dictionary"""

    table = header
    for dictionary in input_dict:
        this_status_list = []
        for key in keywordlist:
            if dictionary.has_key(key):
                this_status_list.append(dictionary[key])
            else:
                this_status_list.append('')
        table.append(this_status_list)
    return table


def txt_link(obj):
    """Text format link"""

    return '(Link: __%s__) -> __%s__' % (obj['destination'], obj['text'
            ])


def txt_cond_summary(job_cond_msg):
    """Pretty format job feasibilty condition"""
    lines = []
    if not job_cond_msg:
        lines.append('No job_cond message.')
    else:
        lines.append('Job Id: %s' % job_cond_msg['job_id'])
        if job_cond_msg.has_key('suggestion'):
            lines.append('%s' % job_cond_msg['suggestion'])
        if job_cond_msg.has_key('verdict'):
            lines.append('%s %s' % ('Job readiness condition',
                                    job_cond_msg['color']))
            lines.append(job_cond_msg['verdict'])
        if job_cond_msg.has_key('error_desc'):
            for (mrsl_attrib, desc) in job_cond_msg['error_desc'].items():
                lines.append('%s' % mrsl_attrib)
                if desc.find('[') is not -1 or desc.find(']') is not -1:
                    desc = desc.replace('[', '').replace(']', '')
                if desc.find("'") is not -1:
                    desc = desc.replace("'", "")
                if desc.find(', ') is not -1:
                    for item in desc.split(', '):
                        lines.append('%s' % item)
                else:
                    lines.append('%s' % desc)
    return '\n'.join(lines)


def resource_format(ret_val, ret_msg, out_obj):
    txt = ret_val
    for i in out_obj:
        if i['object_type'] == 'link':
            txt += i['destination']
    return txt


def txt_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in txt format"""

    lines = []
    status_line = 'Exit code: %s Description %s\n' % (ret_val, ret_msg)

    for i in out_obj:
        if i['object_type'] == 'error_text':
            lines.append('** %s **\n' % i['text'])
        elif i['object_type'] == 'warning':
            lines.append('! %s !\n' % i['text'])
        elif i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'header':
            lines.append('''
___%s___

''' % i['text'].upper())
        elif i['object_type'] == 'sectionheader':
            lines.append('''
___%s___

''' % i['text'])
        elif i['object_type'] == 'title':
            lines.append('Title: %s\n' % i['text'])
        elif i['object_type'] == 'text':
            lines.append('%s\n' % i['text'])
        elif i['object_type'] == 'verbatim':
            lines.append('%s\n' % i['text'])
        elif i['object_type'] == 'binary':
            lines.append(i['data'])
        elif i['object_type'] == 'link':

            # We do not want link junk in plain text
            # lines.append('%s\n' % txt_link(i))

            # Show any explicit plain_text contents
            if i.get('plain_text', False):
                lines.append('%s\n' % i['plain_text'])
        elif i['object_type'] == 'multilinkline':

            # We do not want link junk in plain text
            # links = i["links"]
            # if len(links) == 0:
            #    lines.append("No links found!"
            # else:
            #    lines.append(' / \n'.join([txt_link(link) for link in links])

            continue
        elif i['object_type'] == 'file':
            lines.append('%s\n' % i['name'])
        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                lines.append('No job submit status found!\n')
            else:
                header = [['File', 'Status', 'Job ID', 'Message']]
                lines += pprint_table(txt_table_if_have_keys(header,
                                  submitstatuslist, ['name', 'status',
                                                     'job_id', 'message']))
        elif i['object_type'] == 'table_pager':
            continue
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            header = [['Job ID', 'Resubmit status', 'New job ID',
                      'Message']]
            lines += pprint_table(txt_table_if_have_keys(header,
                                  resubmitobjs, ['job_id',
                                  'status', 'new_job_id', 'message']))
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            header = [['Job ID', 'Old status', 'New status',
                      'Message']]
            lines += pprint_table(txt_table_if_have_keys(header,
                                  changedstatusjobs, ['job_id',
                                  'oldstatus', 'newstatus', 'message']))
        elif i['object_type'] == 'saveschedulejobs':
            saveschedulejobs = i['saveschedulejobs']
            if len(saveschedulejobs) == 0:
                continue
            header = [['Job ID', 'Message']]
            lines += pprint_table(txt_table_if_have_keys(header,
                                  saveschedulejobs, ['job_id', 'message'
                                  ]))
        elif i['object_type'] == 'checkcondjobs':
            checkcondjobs = i['checkcondjobs']
            if len(checkcondjobs) == 0:
                continue
            header = [['Job ID', 'Feasibility', 'Message']]
            for checkcond in checkcondjobs:
                checkcond['cond_summary'] = txt_cond_summary(checkcond)
            lines += pprint_table(txt_table_if_have_keys(header,
                                  checkcondjobs, ['job_id', 'cond_summary',
                                                  'message'
                                  ]))
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            for stat in stats:
                lines.append('''device\t%(device)s
inode\t%(inode)s
mode\t%(mode)s
nlink\t%(nlink)s
uid\t%(uid)s
gid\t%(gid)s
rdev\t%(rdev)s
size\t%(size)s
atime\t%(atime)s
mtime\t%(mtime)s
ctime\t%(ctime)s
''' % stat)
        elif i['object_type'] == 'job_list':
            if len(i['jobs']) > 0:
                jobs = i['jobs']

                for obj in jobs:
                    lines.append('Job Id: %(job_id)s\n' % obj)
                    lines.append('Status: %(status)s\n' % obj)
                    if obj.has_key('execute'):
                        lines.append('Execute: %(execute)s\n' % obj)
                    if obj.has_key('verified'):
                        lines.append('Verified status: %(verified)s\n'
                                 % obj)
                    if obj.has_key('verified_timestamp'):
                        lines.append('Verified: %(verified_timestamp)s\n'
                                 % obj)
                    if obj.has_key('received_timestamp'):
                        lines.append('Received: %(received_timestamp)s\n'
                                 % obj)
                    if obj.has_key('queued_timestamp'):
                        lines.append('Queued: %(queued_timestamp)s\n'
                                 % obj)
                    if obj.has_key('schedule_timestamp'):
                        lines.append('Scheduled: %(schedule_timestamp)s\n'
                                 % obj)
                    if obj.has_key('schedule_hint'):
                        lines.append('Schedule hint: %(schedule_hint)s\n'
                                 % obj)
                    if obj.has_key('schedule_hits'):
                        lines.append('Suitable resources: %(schedule_hits)s\n'
                                 % obj)
                    if obj.has_key('expected_delay'):
                        lines.append('Expected delay: %(expected_delay)s\n'
                                 % obj)
                    if obj.has_key('executing_timestamp'):
                        lines.append('Executing: %(executing_timestamp)s\n'
                                 % obj)
                    if obj.has_key('resource'):
                        lines.append('Resource: %(resource)s\n'
                                 % obj)
                    if obj.has_key('vgrid'):
                        lines.append('VGrid: %s'
                                 % obj['vgrid'])
                    if obj.has_key('finished_timestamp'):
                        lines.append('Finished: %(finished_timestamp)s\n'
                                 % obj)
                    if obj.has_key('failed_timestamp'):
                        lines.append('Failed: %(failed_timestamp)s\n'
                                 % obj)
                    if obj.has_key('canceled_timestamp'):
                        lines.append('Canceled: %(canceled_timestamp)s\n'
                                 % obj)
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        lines.append('Execution history</td><td>#%s</td></tr>'
                                 % count)
                        if single_history.has_key('queued'):
                            lines.append('Queued %s: %s\n' % (count,
                                    single_history['queued']))
                        if single_history.has_key('executing'):
                            lines.append('Executing %s: %s\n' % (count,
                                    single_history['executing']))
                        if single_history.has_key('resource'):
                            lines.append('Resource %s: %s\n' % (count,
                                    single_history['resource']))
                        if single_history.has_key('vgrid'):
                            lines.append('VGrid %s: %s' % (count,
                                    single_history['vgrid']))
                        if single_history.has_key('failed'):
                            lines.append('Failed %s: %s\n' % (count,
                                    single_history['failed']))
                        if single_history.has_key('failed_message'):
                            lines.append('Failed message %s: %s\n'
                                     % (count,
                                    single_history['failed_message']))

                    # add newline before next job)

                    lines.append('\n')
        elif i['object_type'] == 'filewcs':

            # if len(i["jobs"]) > 0:
                # jobs = i["jobs"]
                # lines.append("||------------------------------------||")
                # lines.append("|| Job ID | Status | Queued timestamp ||")
                # for obj in jobs:
                #    lines.append("|| %s | %s | %s ||" % (obj["job_id"], obj["status"], obj["queued_timestamp"]))
                # lines.append("||------------------------------------||")

            filewcs = i['filewcs']
            if len(filewcs) == 0:
                lines.append('No files to run wc on\n')
            else:
                for filewc in filewcs:
                    out = ''
                    if filewc.has_key('name'):
                        out += '%s\t' % filewc['name']
                    out += '\t'
                    if filewc.has_key('lines'):
                        out += '%s' % filewc['lines']
                    out += '\t'
                    if filewc.has_key('words'):
                        out += '%s' % filewc['words']
                    out += '\t'
                    if filewc.has_key('bytes'):
                        out += '%s' % filewc['bytes']
                    out += '\n'
                    lines.append(out)
        elif i['object_type'] == 'file_not_found':
            lines.append('%s: No such file or directory\n' % i['name'])
        elif i['object_type'] == 'dir_listings':
            if len(i['dir_listings']) == 0:
                continue
            columns = 6
            cols = 0
            if i.get('show_dest', False):
                columns += 1
            for dir_listing in i['dir_listings']:
                for entry in dir_listing['entries']:
                    line = ''
                    if 'directory' == entry['type']:
                        directory = entry
                        if directory.has_key('long_format'):
                            if directory == dir_listing['entries'][0]:
                                lines.append('%s:\ntotal %s\n'
                                         % (dir_listing['relative_path'
                                        ], len(dir_listing['entries'])))
                        if directory.has_key('actual_dir'):
                            line += '%s ' % directory['actual_dir']
                        line += '%s\n' % directory['name']
                        lines.append(line)
                    elif 'file' == entry['type']:
                        this_file = entry
                        if this_file.has_key('long_format'):
                            line += '%s ' % this_file['long_format']
                        line += '%s' % this_file['name']
                        if this_file.has_key('file_dest'):
                            line += ' %s' % this_file['file_dest']
                        line += '\n'
                        lines.append(line)
        elif i['object_type'] == 'jobobj':
            job_dict = i['jobobj'].to_dict()
            lines.append('Field\t\tValue\n')
            for (key, val) in job_dict.items():
                lines.append('%s\t\t%s\n' % (key, val))
        elif i['object_type'] == 'html_form':
            pass
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                lines.append('File: %s\n' % i['path'])
            for line in i['lines']:
                # Do not add newlines here!
                lines.append(line)
        elif i['object_type'] == 'list':
            for list_item in i['list']:
                lines.append('%s\n' % list_item)
        elif i['object_type'] == 'user_stats':
            if i.get('disk', None):
                disk_info = '== Disk stats ==\n'
                for (key, val) in i['disk'].items():
                    disk_info += '%s: %s\n' % (key, val)
                lines.append(disk_info)
            if i.get('jobs', None):
                jobs_info = '== Job stats ==\n'
                for (key, val) in i['jobs'].items():
                    jobs_info += '%s: %s\n' % (key, val)
                lines.append(jobs_info)
            if i.get('resources', None):
                resources_info = '== Resource stats ==\n'
                for (key, val) in i['resources'].items():
                    resources_info += '%s: %s\n' % (key, val)
                lines.append(resources_info)
            if i.get('certificate', None):
                certificate_info = '== Certificate stats ==\n'
                for (key, val) in i['certificate'].items():
                    certificate_info += '%s: %s\n' % (key, val)
                lines.append(certificate_info)
        elif i['object_type'] == 'script_status':
            status_line = i.get('text')
        elif i['object_type'] == 'end':
            pass
        else:
            lines.append('unknown object %s\n' % i)
            
    if status_line:
        lines = [status_line] + lines
    return ''.join(lines)


def html_link(obj):
    """html format link"""
    
    extra_fields = ['id', 'class', 'title']
    extra_params = []
    # Set parameter in link
    for name in extra_fields:
        value = obj.get(name, '')
        if value:
            extra_params.append('%s="%s"' % (name, value))
    link = '<a href="%s" %s>%s</a>' % (obj['destination'],
                                       ' '.join(extra_params), obj['text'])
    return link

def html_cond_summary(job_cond_msg):
    """Pretty format job feasibilty condition"""
    lines = []
    if not job_cond_msg:
        lines.append('No job_cond message.')
    else:
        lines.append('<table class="job_cond_verdict">')
        lines.append('<tr><th>Job Id: %s</th></tr>' % \
                     job_cond_msg['job_id'])
        if job_cond_msg.has_key('suggestion'):
            lines.append('<tr><td>%s</td></tr>' % \
                         job_cond_msg['suggestion'])
        if job_cond_msg.has_key('verdict'):
            img_tag = '<img src="%s" alt="%s %s" />' % \
                      (job_cond_msg['icon'], 'Job readiness condition', 
                       job_cond_msg['color'])
            lines.append('<tr><td>%s&nbsp;%s</td></tr>' % \
                         (img_tag, job_cond_msg['verdict']))
        if job_cond_msg.has_key('error_desc'):
            lines.append('<tr><td><dl>')
            for (mrsl_attrib, desc) in job_cond_msg['error_desc'].items():
                lines.append('<dt>%s</dt>' % mrsl_attrib)
                if desc.find('[') is not -1 or desc.find(']') is not -1:
                    desc = desc.replace('[', '').replace(']', '')
                if desc.find("'") is not -1:
                    desc = desc.replace("'", "")
                if desc.find(', ') is not -1:
                    for item in desc.split(', '):
                        lines.append('<dd>%s</dd>' % item)
                else:
                    lines.append('<dd>%s</dd>' % desc)
            lines.append('</dl></td></tr>')
        lines.append('</table>')
    return '\n'.join(lines)

def html_table_if_have_keys(dictionary, keywordlist):
    """create html table contents based on keys in a dictionary"""

    outputstring = ''
    for key in keywordlist:
        if dictionary.has_key(key):
            outputstring += '<td>%s</td>' % dictionary[key]
        else:
            outputstring += '<td></td>'
    return outputstring


def html_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in html format"""

    lines = []
    include_widgets = True
    user_widgets = {}
    status_line = \
        """
    <div id="exitcode">
Exit code: %s Description: %s<br />
    </div>
<br />    
"""\
         % (ret_val, ret_msg)
    for i in out_obj:
        if i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'error_text':
            lines.append('<p class=errortext>%s</p>' % html_escape(i['text']))
        elif i['object_type'] == 'warning':
            lines.append('<p class=warningtext>%s</p>' % html_escape(i['text']))
        elif i['object_type'] == 'header':
            lines.append('<h1>%s</h1>' % html_escape(i['text']))
        elif i['object_type'] == 'sectionheader':
            lines.append('<h3>%s</h3>' % html_escape(i['text']))
        elif i['object_type'] == 'title':
            javascript = ''
            if i.has_key('javascript'):
                javascript = i['javascript']
            bodyfunctions = ''
            if i.has_key('bodyfunctions'):
                bodyfunctions = i['bodyfunctions']
            include_menu = True
            if i.has_key('skipmenu'):
                include_menu = not i['skipmenu']
            if i.has_key('skipwidgets'):
                include_widgets = not i['skipwidgets']
            user_menu = []
            if i.has_key('user_menu'):
                user_menu = i['user_menu']
            if i.has_key('user_widgets'):
                user_widgets = i['user_widgets']
            lines.append(get_cgi_html_header(
                configuration, html_escape(i['text']),
                '',
                True,
                javascript,
                bodyfunctions,
                include_menu,
                include_widgets,
                user_menu,
                user_widgets
                ))
        elif i['object_type'] == 'text':
            lines.append('<p>%s</p>' % html_escape(i['text']))
        elif i['object_type'] == 'verbatim':
            lines.append('%s' % html_escape(i['text']))
        elif i['object_type'] == 'binary':
            lines.append(i['data'])
        elif i['object_type'] == 'link':
            lines.append(html_link(i))
        elif i['object_type'] == 'job_list':

            # lines.append("<a href="%s">%s</a>" % (i["destination"], i["text"])

            if len(i['jobs']) > 0:
                jobs = i['jobs']
                lines.append("<table class='jobs'>")

                # <tr><td>Job ID</td><td>Status</td><td>Queued timestamp</td></tr>"

                for obj in jobs:
                    lines.append('<tr><th>Job Id</th><th>%s</th></tr>'
                                  % obj['job_id'])
                    lines.append('<tr><td>Status</td><td>%s</td></tr>'
                                  % obj['status'])
                    if obj.has_key('execute'):
                        lines.append('<tr><td>Execute</td><td>%s</td></tr>'
                                 % obj['execute'])
                    if obj.has_key('verified'):
                        lines.append('<tr><td>Verified status</td><td>%s</td></tr>'
                                 % obj['verified'])
                    if obj.has_key('verified_timestamp'):
                        lines.append('<tr><td>Verified</td><td>%s</td></tr>'
                                 % obj['verified_timestamp'])
                    if obj.has_key('received_timestamp'):
                        lines.append('<tr><td>Received</td><td>%s</td></tr>'
                                 % obj['received_timestamp'])
                    if obj.has_key('queued_timestamp'):
                        lines.append('<tr><td>Queued</td><td>%s</td></tr>'
                                 % obj['queued_timestamp'])
                    if obj.has_key('schedule_timestamp'):
                        lines.append('<tr><td>Scheduled</td><td>%s</td></tr>'
                                 % obj['schedule_timestamp'])
                    if obj.has_key('schedule_hint'):
                        lines.append('<tr><td>Schedule result</td><td>%s</td></tr>'
                                 % obj['schedule_hint'])
                    if obj.has_key('schedule_hits'):
                        lines.append('<tr><td>Suitable resources</td><td>%s</td></tr>'
                                 % obj['schedule_hits'])
                    if obj.has_key('expected_delay'):
                        lines.append('<tr><td>Expected delay</td><td>%s</td></tr>'
                                 % obj['expected_delay'])
                    if obj.has_key('executing_timestamp'):
                        lines.append('<tr><td>Executing</td><td>%s</td></tr>'
                                 % obj['executing_timestamp'])
                    if obj.has_key('resource'):
                        lines.append('<tr><td>Resource</td><td>%s</td></tr>'
                                 % obj['resource'])
                    if obj.has_key('vgrid'):
                        lines.append('<tr><td>VGrid</td><td>%s</td></tr>'
                                 % obj['vgrid'])
                    if obj.has_key('finished_timestamp'):
                        lines.append('<tr><td>Finished</td><td>%s</td></tr>'
                                 % obj['finished_timestamp'])
                    if obj.has_key('failed_timestamp'):
                        lines.append('<tr><td>Failed</td><td>%s</td></tr>'
                                 % obj['failed_timestamp'])
                    if obj.has_key('canceled_timestamp'):
                        lines.append('<tr><td>Canceled</td><td>%s</td></tr>'
                                 % obj['canceled_timestamp'])
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        lines.append('<tr><td>Execution history</td><td>#%s</td></tr>'
                                 % count)
                        if single_history.has_key('queued'):
                            lines.append('<tr><td>Queued %s</td><td>%s</td></tr>'
                                     % (count, single_history['queued'
                                    ]))
                        if single_history.has_key('executing'):
                            lines.append('<tr><td>Executing %s</td><td>%s</td></tr>'
                                     % (count,
                                    single_history['executing']))
                        if single_history.has_key('resource'):
                            lines.append('<tr><td>Resource %s</td><td>%s</td></tr>'
                                     % (count,
                                    single_history['resource']))
                        if single_history.has_key('vgrid'):
                            lines.append('<tr><td>VGrid %s</td><td>%s</td></tr>'
                                     % (count,
                                    single_history['vgrid']))
                        if single_history.has_key('failed'):
                            lines.append('<tr><td>Failed %s</td><td>%s</td></tr>'
                                     % (count, single_history['failed'
                                    ]))
                        if single_history.has_key('failed_message'):
                            lines.append('<tr><td>Failed message %s</td><td>%s</td></tr>'
                                     % (count,
                                    single_history['failed_message']))

                    if obj.has_key('statuslink'):
                        lines.append('<tr><td>Links</td><td>')
                        lines.append('%s<br />' % html_link(obj['statuslink'
                                                                ]))
                        lines.append('%s<br />' % html_link(obj['mrsllink']))
                        lines.append('%s<br />' % html_link(obj['resubmitlink'
                                                                ]))
                        lines.append('%s<br />' % html_link(obj['cancellink'
                                                                ]))
                        lines.append('%s<br />'
                                     % html_link(obj['jobschedulelink']))
                        lines.append('%s<br />'
                                     % html_link(obj['liveiolink']))
                    if obj.has_key('outputfileslink'):
                        lines.append('<br />%s'
                                 % html_link(obj['outputfileslink']))
                    lines.append('</td></tr><tr><td><br /></td></tr>')


                lines.append('</table>')
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            lines.append("<table class='resubmit'><tr><th>Job ID</th><th>Resubmit status</th><th>New job ID</th><th>Message</th></tr>"
                         )
            for resubmitobj in resubmitobjs:
                lines.append('<tr>%s</tr>'
                              % html_table_if_have_keys(resubmitobj,
                             ['job_id', 'status', 'new_job_id',
                             'message']))
            lines.append('</table>')
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            lines.append("<table class='changedstatusjobs'><tr><th>Job ID</th><th>Old status</th><th>New status</th><th>Message</th></tr>"
                         )
            for changedstatus in changedstatusjobs:
                lines.append('<tr>%s</tr>'
                              % html_table_if_have_keys(changedstatus,
                             ['job_id', 'oldstatus', 'newstatus',
                             'message']))
            lines.append('</table>')
        elif i['object_type'] == 'saveschedulejobs':
            saveschedulejobs = i['saveschedulejobs']
            if len(saveschedulejobs) == 0:
                continue
            lines.append("<table class='saveschedulejobs'><tr><th>Job ID</th><th>Message</th></tr>"
                         )
            for saveschedule in saveschedulejobs:
                lines.append('<tr>%s</tr>'
                              % html_table_if_have_keys(saveschedule,
                             ['job_id', 'message']))
            lines.append('</table>')
            lines.append(i['savescheduleinfo'])
        elif i['object_type'] == 'checkcondjobs':
            checkcondjobs = i['checkcondjobs']
            if len(checkcondjobs) == 0:
                continue
            lines.append("<table class='checkcondjobs'><tr><th>Job ID</th><th>Feasibility</th><th>Message</th></tr>"
                         )
            for checkcond in checkcondjobs:
                checkcond['cond_summary'] = html_cond_summary(checkcond)
                lines.append('<tr>%s</tr>'
                              % html_table_if_have_keys(checkcond,
                             ['job_id', 'cond_summary', 'message']))
            lines.append('</table>')
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            lines.append("<table class='stats'><tr><th>Filename</th><th>Device</th><th>Inode</th><th>Mode</th><th>Nlink</th><th>User ID</th><th>Group ID</th><th>RDEV</th><th>Size</th><th>Last accessed</th><th>Modified time</th><th>Created time</th></tr>"
                         )
            for stat in stats:
                lines.append('<tr>%s</tr>'
                              % html_table_if_have_keys(stat, [
                    'name',
                    'device',
                    'inode',
                    'mode',
                    'nlink',
                    'uid',
                    'gid',
                    'rdev',
                    'size',
                    'atime',
                    'mtime',
                    'ctime',
                    ]))
            lines.append('</table>')
        elif i['object_type'] == 'fileuploadobjs':
            fileuploadobjs = i['fileuploadobjs']
            if len(fileuploadobjs) == 0:
                lines.append('No jobs submitted!')
            else:
                lines.append("<table class='fileupload'><tr><th>Filename</th><th>Saved</th><th>Extract packages</th><th>Submit flag</th><th>File size</th><th>Message</th></tr>"
                             )
                for fileuploadobj in fileuploadobjs:
                    lines.append('<tr>%s</tr>'
                                  % html_table_if_have_keys(fileuploadobj,
                                 [
                        'name',
                        'saved',
                        'extract_packages',
                        'submitmrsl',
                        'size',
                        'message',
                        ]))
                lines.append('</table>')
        elif i['object_type'] == 'jobobj':
            job_dict = i['jobobj'].to_dict()
            lines.append("<table class='jobobj'><tr><th>Field</th><th>Value</th></tr>"
                         )
            for (key, val) in job_dict.items():
                lines.append('<tr><td>%s</td><td>%s</td></tr>' % (key,
                             val))
            lines.append('</table>')
        elif i['object_type'] == 'html_form':
            lines.append(i['text'])
        elif i['object_type'] == 'dir_listings':
            if len(i['dir_listings']) == 0:
                continue
            columns = 7
            if i.get('show_dest', False):
                columns += 1
            lines.append("<table class='files'>")
            lines.append('<tr>')
            cols = 0
            lines.append('<td>Info</td>')
            cols += 1
            lines.append("<td><input type='checkbox' name='allbox' value='allbox' onclick='un_check()' /></td>"
                         )
            cols += 1

            # lines.append("<td><br /></td>"
            # cols += 1

            lines.append('<td colspan=%d>Select/deselect all files</td>'
                         % (columns - cols))
            lines.append('</tr>')
            lines.append('<tr>')
            cols = 0
            lines.append('<td colspan=%d><hr width=100%%></td>'
                          % (columns - cols))
            lines.append('</tr>')

            row_number = 1
            for dir_listing in i['dir_listings']:
                for entry in dir_listing['entries']:
                    cols = 0
                    row_class = row_name[row_number % 2]
                    if 'directory' == entry['type']:
                        directory = entry
                        if directory == dir_listing['entries'][0]:
                            lines.append('<tr>')
                            lines.append('<td width=20%%>%s:<br />total %s</td>'
                                     % (dir_listing['relative_path'],
                                    len(dir_listing['entries'])))
                            cols += 1
                            lines.append('<td><br /></td>' * (columns
                                     - cols) + '</tr>')
                            cols = columns

                        lines.append('<tr class=%s>' % row_class)
                        cols = 0
                        lines.append('<td><br /></td>')
                        cols += 1
                        lines.append("<td><input type='checkbox' name='path' value='%s' /></td>"
                                     % directory['dirname_with_dir'])
                        cols += 1
                        if directory.has_key('actual_dir'):
                            lines.append('<td>%s</td>'
                                     % directory['actual_dir'])
                        else:
                            lines.append('<td><br /></td>')
                        cols += 1
                        lines.append("<td><a href='ls.py?path=%s;flags=%s;output_format=html'>show</a></td><td>DIR</td>"
                                 % (directory['dirname_with_dir'],
                                dir_listing['flags']))
                        cols += 1
                        lines.append("<td><a href='rmdir.py?path=%s;output_format=html'>remove</a></td>"
                                 % directory['dirname_with_dir'])
                        cols += 1
                        lines.append('<td>%s</td>' % directory['name'])
                        cols += 1
                        lines.append('<td><br /></td>' * (columns - cols)
                                 + '</tr>')
                        cols = columns
                        lines.append('</tr>')
                    elif 'file' == entry['type']:
                        this_file = entry
                        lines.append('<tr class=%s>' % row_class)
                        cols = 0
                        lines.append('<td><br /></td>')
                        cols += 1
                        lines.append("<td><input type='checkbox' name='path' value='%s' /></td>"
                                     % this_file['file_with_dir'])
                        cols += 1
                        if this_file.has_key('long_format'):
                            lines.append('<td>%s</td>'
                                     % this_file['long_format'])
                        else:
                            lines.append('<td><br /></td>')
                        cols += 1
                        lines.append("<td><a href='/%s/%s'>show</a></td>"
                                 % ('cert_redirect',
                                this_file['file_with_dir']))
                        cols += 1
                        lines.append("<td><a href='editor.py?path=%s;output_format=html'>edit</a></td>"
                                 % this_file['file_with_dir'])
                        cols += 1
                        lines.append("<td><a href='rm.py?path=%s;output_format=html'>delete</a></td>"
                                 % this_file['file_with_dir'])
                        cols += 1
                        lines.append('<td>%s</td>' % this_file['name'])
                        cols += 1
                        if this_file.get('file_dest', False):
                            lines.append('<td>%s</td>'
                                     % this_file['file_dest'])
                            cols += 1
                        lines.append('<td><br /></td>' * (columns - cols)
                                 + '</tr>')
                        cols = columns
                        lines.append('</tr>')
                    row_number += 1
            lines.append('</form></table>')
            lines.append('')
        elif i['object_type'] == 'filewcs':
            filewcs = i['filewcs']
            if len(filewcs) == 0:
                lines.append('No files to run wc on')
            else:
                lines.append('<table class="wc"><tr><th>File</th><th>Lines</th><th>Words</th><th>Bytes</th></tr>'
                             )
                for filewc in filewcs:
                    lines.append('<tr><td>%s</td>' % filewc['name'])
                    lines.append('<td>')
                    if filewc.has_key('lines'):
                        lines.append('%s' % filewc['lines'])
                    lines.append('</td><td>')
                    if filewc.has_key('words'):
                        lines.append('%s' % filewc['words'])
                    lines.append('</td><td>')
                    if filewc.has_key('bytes'):
                        lines.append('%s' % filewc['bytes'])
                    lines.append('</td></tr>')
                lines.append('</table>')
        elif i['object_type'] == 'file_not_found':

            lines.append('File %s was <b>not</b> found!' % i['name'])
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                lines.append('File: %s<br />' % i['path'])
            lines.append('<pre>%s</pre><br />' % ''.join(i['lines']))
        elif i['object_type'] == 'list':
            lines.append('<ul>')
            for list_item in i['list']:
                lines.append(('<li>%s</li>' % list_item).replace('\n',
                             '<br />'))
            lines.append('</ul>')
        elif i['object_type'] == 'linklist':
            links = i['links']
            if len(links) == 0:
                lines.append('No links found!')
            else:
                lines.append('<table class="links"><tr><th>Name</th><th>Link</th></tr>'
                             )
                for link in links:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                  % (html_escape(link['text']), html_link(link)))
                lines.append('</table>')
        elif i['object_type'] == 'multilinkline':
            links = i['links']
            if len(links) == 0:
                lines.append('No links found!')
            else:
                lines.append(' , '.join([html_link(link) for link in
                             links]))
        elif i['object_type'] == 'file':
            lines.append(i['name'])
        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                lines.append('No job submit status found!')
            else:
                lines.append('<table class="submitstatus"><tr><th>File</th><th>Status</th><th>Job Id</th><th>Message</th></tr>'
                             )
                for submitstatus in submitstatuslist:
                    lines.append('<tr>%s</tr>'
                                  % html_table_if_have_keys(submitstatus,
                                 ['name', 'status', 'job_id', 'message'
                                 ]))
                lines.append('</table>')
        elif i['object_type'] == 'objects':
            objects = i['objects']
            if len(objects) == 0:
                lines.append('No objects found!')
            else:
                lines.append('<table class="objects"><tr><th>Object</th><th>Info</th></tr>'
                             )
                for (name, val) in objects:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                  % (name, val))
                lines.append('</table>')
        elif i['object_type'] == 'sandboxinfos':
            sandboxinfos = i['sandboxinfos']
            lines.append('<table class="sandboxinfo"><tr><th>Username</th><th>Resource(s)</th><th>Jobs</th><th>Walltime</th></tr>'
                         )
            row_number = 1
            if not sandboxinfos:
                help_text = 'No sandboxes found - please download a sandbox below to proceed'
                lines.append('<tr class=%s><td colspan=4>%s</td></tr>' % (row_name[row_number], help_text))
            for sandboxinfo in sandboxinfos:
                row_class = row_name[row_number % 2]
                lines.append('<tr class=%s>%s</tr>'
                             % (row_class, html_table_if_have_keys(sandboxinfo,
                                                                   ['username', 'resource', 'jobs',
                                                                    'walltime'])))
                row_number += 1
            lines.append('</table>')
        elif i['object_type'] == 'runtimeenvironments':
            runtimeenvironments = i['runtimeenvironments']
            lines.append('''<table class="runtimeenvs columnsort" id="runtimeenvtable">
<thead class="title">
    <tr>
        <th>Name</th>
        <th width="8"><!-- View --></th>
        <th width="8"><!-- Owner --></th>
        <th>Description</th>
        <th width="8">Resources</th>
        <th>Created</th>
    </tr>
</thead>
<tbody>
'''
                         )
            for single_re in runtimeenvironments:
                viewlink = html_link(single_re['viewruntimeenvlink'])
                ownerlink = single_re.get('ownerlink', '')
                if ownerlink:
                    ownerlink = html_link(ownerlink)
                lines.append('''
<tr>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td title="%s">%s</td><td>%s</td>
</tr>''' % (single_re['name'], viewlink, ownerlink, single_re['description'],
            ', '.join(single_re['providers']), single_re['resource_count'],
            single_re['created']))
                
            lines.append('''
</tbody>
</table>''')
        elif i['object_type'] == 'runtimeenvironment':

            software_html = \
                    '<table class="runtimeenvsw" frame=hsides rules=none cellpadding=5>'
            for software in i['software']:
                software_html += \
                    '<tr><td><img src="%s" width="80" height="80" /></td><td></td></tr>'\
                     % software['icon']
                software_html += '<tr><td>Name:</td><td>%s</td></tr>'\
                     % software['name']
                software_html += \
                    '<tr><td>Url:</td><td><a class="urllink" href="%s">%s</a></td></tr>'\
                     % (software['url'], software['url'])
                software_html += \
                    '<tr><td>Description:</td><td>%s</td></tr>'\
                     % software['description']
                software_html += '<tr><td>Version:</td><td>%s</td></tr>'\
                     % software['version']
            software_html += '</table>'

            environment_html = \
                    '<table class="runtimeenvvars" frame=hsides rules=none cellpadding=5>'
            for environment in i['environments']:
                environment_html += \
                                 '<tr><td>Name:</td><td>%(name)s (use with $%(name)s)</td></tr>'
                environment_html += \
                    '<tr><td>Example:</td><td>%(example)s</td></tr>'
                environment_html += \
                    '<tr><td>Description:</td><td>%(description)s</td></tr>'
                environment_html = environment_html % environment
            environment_html += '</table>'

            lines.append('<table class="runtimeenvdetails">')
            lines.append('<tr><td>Name</td><td>%s</td></tr>' % i['name'
                         ])
            lines.append('<tr><td>Description</td><td>%s</td></tr>'
                          % i['description'])
            lines.append('<tr><td>Needed&nbsp;software</td><td>%s</td></tr>'
                          % software_html)
            lines.append('<tr><td>Environment&nbsp;variables</td><td>%s</td></tr>'
                          % environment_html)
            if i['testprocedure']:
                lines.append("<tr><td>Testprocedure</td><td valign='top'>%s</td></tr>"
                             % i['testprocedure'])
            if i['verifystdout']:
                lines.append("<tr><td>Verifystdout</td><td valign='top'>%s</td></tr>"
                             % i['verifystdout'])
            if i['verifystderr']:
                lines.append("<tr><td>Verifystderr</td><td valign='top'>%s</td></tr>"
                             % i['verifystderr'])
            if i['verifystatus']:
                lines.append("<tr><td>Verifystatus</td><td valign='top'>%s</td></tr>"
                             % i['verifystatus'])
            lines.append('<tr><td>Created</td><td>%s</td></tr>'
                          % i['created'])
            lines.append('<tr><td>Creator</td><td>%s</td></tr>'
                          % i['creator'])
            lines.append('<tr><td>Job&nbsp;count</td><td>%s</td></tr>'
                          % i['job_count'])
            lines.append('<tr><td>Resources</td><td>%s</td></tr>'
                          % ', '.join(i['providers']))
            lines.append('</table>')
        elif i['object_type'] == 'table_pager':
            page_entries = i.get('page_entries', [5, 10, 20, 25, 40, 50, 80,
                                                  100, 250, 500, 1000])
            default_entries = i.get('default_entries', 20)
            if not default_entries in page_entries:
                page_entries.append(default_entries)
            toolbar = '''
  <div>
    <div class="toolbar">        
      <div class="pager" id="pager">
      <form style="display: inline;" action="">
        <img class="first" src="/images/icons/arrow_left.png"/>
        <img class="prev" src="/images/icons/arrow_left.png"/>
        <input type="text" class="pagedisplay" size=5 />
        <img class="next" src="/images/icons/arrow_right.png"/>
        <img class="last" src="/images/icons/arrow_right.png"/>
        <select class="pagesize">
'''
            for value in page_entries:
                selected = ''
                if value == default_entries:
                    selected = 'selected'
                toolbar += '<option %s value="%d">%d %s per page</option>\n'\
                           % (selected, value, value, '%(entry_name)s')
            toolbar += '''
        </select>
      </form>
      </div>
    </div>
  </div>
'''
            lines.append(toolbar % {'entry_name': i['entry_name']})
        elif i['object_type'] == 'resource_list':
            if len(i['resources']) > 0:
                res_fields = ['PUBLICNAME', 'NODECOUNT', 'CPUCOUNT', 'MEMORY', 'DISK',
                              'ARCHITECTURE']
                resources = i['resources']
                lines.append("<table class='resources columnsort' id='resourcetable'>")
                lines.append('''
<thead class="title">
<tr>
  <th>Resource ID</th>
  <th width="8"><!-- View / Admin --></th>
  <th width="8"><!-- Remove owner --></th>
  <th class=centertext>Runtime envs</th>
  <th class=centertext>Alias</th>
  <th class=centertext>Nodes</th>
  <th class=centertext>CPUs</th>
  <th class=centertext>Mem (MB)</th>
  <th class=centertext>Disk (GB)</th>
  <th class=centertext>Arch</th>
</tr>
</thead>
<tbody>
'''
                             )
                for obj in resources:
                    lines.append('<tr>')
                    res_type = 'real'
                    if obj.get('SANDBOX', False):
                        res_type = 'sandbox'
                    lines.append('<td class="%sres" title="%s resource">%s</td>' % \
                                 (res_type, res_type, obj['name']))
                    lines.append('<td>')
                    # view or admin link depending on ownership
                    if obj.has_key('resdetailslink'):
                        lines.append('%s' % html_link(obj['resdetailslink']))
                    lines.append('</td>')
                    lines.append('<td>')
                    if obj.has_key('resownerlink'):
                        lines.append('%s' % html_link(obj['resownerlink']))
                    lines.append('</td>')
                    # List number of runtime environments in field and add
                    # actual names as mouse-over
                    rte_list = obj.get('RUNTIMEENVIRONMENT', [])
                    lines.append('<td class=centertext title="%s">' % \
                                 ', '.join(rte_list))
                    lines.append('%d' % len(rte_list))
                    lines.append('</td>')
                    # Remaining fields
                    for name in res_fields:
                        lines.append('<td class=centertext>')
                        lines.append('%s' % obj.get(name, ''))
                        lines.append('</td>')
                    lines.append('</tr>')
                lines.append('</tbody></table>')
            else:
                lines.append('No matching Resources found')
        elif i['object_type'] == 'resource_info':
            resource_html = ''
            resource_html += '<h3>%s</h3>' % i['unique_resource_name']
            resource_html += \
                          '<table class="resource" frame=hsides rules=none cellpadding=5>'
            for (key, val) in i['fields']:
                resource_html += \
                          '<tr><td>%s</td><td>%s</td></tr>' % \
                          (key, val)
            for (exe_name, exe_spec) in i['exes'].items():
                resource_html += '<tr><td><b>%s</b></td></tr>' % exe_name
                for (key, val) in exe_spec:
                    resource_html += \
                                  '<tr><td>%s</td><td>%s</td></tr>' % \
                                  (key, val)
            resource_html += '</table>'
            lines.append(resource_html)
        elif i['object_type'] == 'user_list':
            if len(i['users']) > 0:
                user_fields = []
                notify_headers = ''
                for proto in configuration.notify_protocols:
                    user_fields.append('send%slink' % proto)
                    notify_headers += '  <th class=centertext>%s</th>' % proto
                users = i['users']
                lines.append("<table class='users columnsort' id='usertable'>")
                lines.append('''
<thead class="title">
<tr>
  <th>User ID</th>
  <th width="8"><!-- View --></th>
  %s
</tr>
</thead>
<tbody>
''' % notify_headers
                             )
                for obj in users:
                    lines.append('<tr>')
                    lines.append('<td class="user" title="user">%s</td>' % \
                                 obj['name'])
                    lines.append('<td>')
                    if obj.has_key('userdetailslink'):
                        lines.append('%s' % html_link(obj['userdetailslink']))
                    lines.append('</td>')
                    # Remaining fields
                    for name in user_fields:
                        lines.append('<td class=centertext>')
                        if obj.has_key(name):
                            lines.append('%s' % html_link(obj[name]))
                        else:
                            lines.append('---')
                        lines.append('</td>')
                    lines.append('</tr>')
                lines.append('</tbody></table>')
            else:
                lines.append('No matching users found')
        elif i['object_type'] == 'user_info':
            user_html = ''
            user_html += '<h3>%s</h3>' % i['user_id']
            user_html += \
                          '<table class="user" frame=hsides rules=none cellpadding=5>'
            for (key, val) in i['fields']:
                user_html += \
                          '<tr><td>%s</td><td>%s</td></tr>' % \
                          (key, val)
            user_html += '</table>'
            lines.append(user_html)
        elif i['object_type'] == 'forum_threads':
            thread_fields = ['last', 'subject', 'author', 'date',
                             'replies']
            if i.get('status', None):
                lines.append('<p class="status_message">%s</p>' % i['status'])
            if len(i['threads']) > 0:
                threads = i['threads']
                lines.append("<table class='forum_threads columnsort' id='forumtable'>")
                lines.append('''
<thead class="title">
<tr>
  <th>Last Update</th>
  <th>Subject</th>
  <th>Author</th>
  <th>Created</th>
  <th>Replies</th>
</tr>
</thead>
<tbody>
''')
                for entry in threads:
                    message_class, marker_class = '', 'class="centertext"'
                    if entry['new']:
                        message_class = 'class="highlight_message"'
                        marker_class = 'class="centertext new_message"'
                    lines.append('<tr %s>' % message_class)
                    # Remaining fields
                    for name in thread_fields:
                        val = entry.get(name, '---')
                        lines.append('<td %s>' % marker_class)
                        if name == 'subject':
                            link_entry = {'object_type': 'link', 'text':
                                          val, 'destination':
                                          '%s&vgrid_name=%s' % \
                                          (entry['link'], i['vgrid_name'])}
                            lines.append('%s' % html_link(link_entry))
                        else:
                            lines.append('%s' % val)
                        lines.append('</td>')
                        # Reset marker after first entry
                        marker_class = ''
                    lines.append('</tr>')
                lines.append('</tbody></table>')
            else:
                lines.append('No matching threads found')
            max_subject_len, max_body_len = 100, 10000
            if i.has_key('vgrid_name'):
                lines.append('''
<p>
<div id="search_threads">
<a class="searchlink"
href="javascript:toggle_new('search_form', 'search_threads');">
Search threads</a>
</div>
<div class="hidden_form" id="search_form">
<form method="post" action="?">
<input type="hidden" name="action" value="search"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<p>Subject: <input id="search_form_main" name="msg_subject" maxlength="%s"
size="80" value=""/></p>
<p class="hidden_form">Body: <input name="msg_body" maxlength="%s" size="80" value=""/></p>
<p>
<input class="submit_button" type="submit" value="Search threads"/>
<input class="submit_button" type="submit" value="Cancel"
onclick="javascript:toggle_new('search_form', 'search_threads');
return false;"/>
</p>
</form>
</div>
</p>
''' % (i['vgrid_name'], max_subject_len, max_body_len))
                lines.append('''
<p>
<div id="new_link">
<a class="newpostlink" href="javascript:toggle_new('new_form', 'new_link');">
Start a new thread</a>
</div>
<div class="hidden_form" id="new_form">
<form method="post" action="?">
<input type="hidden" name="action" value="new_thread"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<p>Subject: <input id="new_form_main" name="msg_subject" maxlength="%s"
size="80"/>
</p>
<p><textarea name="msg_body" rows="10" cols="80"></textarea></p>
<p>
<input class="submit_button" type="submit" value="Post"/>
<input class="submit_button" type="reset" value="Clear"/>
<input class="submit_button" type="submit" value="Cancel"
onclick="javascript:toggle_new('new_form', 'new_link'); return false;"/>
</p>
</form>
</div>
</p>
''' % (i['vgrid_name'], max_subject_len))
                lines.append('''<p>
<a class="refreshlink" href="?show_all&vgrid_name=%s">Reload threads</a>
</p>''' % i['vgrid_name'])
                lines.append('''
<div id="subscribe_form">
<form method="post" action="?">
<input type="hidden" name="action" value="toggle_subscribe"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<input class="submit_button" type="submit" value="Subscribe/unsubscribe to forum updates"/>
</form>
</div>
''' % i['vgrid_name'])
        elif i['object_type'] == 'forum_thread_messages':
            message_fields = ['date', 'author', 'body']
            if i.get('status', None):
                lines.append('<p class="status_message">%s</p>' % i['status'])
            if len(i['messages']) > 0:
                lines.append("<h2>%s</h2>" % i['messages'][0]['subject'])
                lines.append("<table class='forum_messages columnsort' id='forumtable'>")
                lines.append('''
<thead class="title">
<tr>
  <th>Date</th>
  <th>Author</th>
  <th>Message</th>
</tr>
</thead>
<tbody>
''')
                for entry in i['messages']:
                    message_class, marker_class = '', 'class="centertext"'
                    if entry['new']:
                        message_class = 'class="highlight_message"'
                        marker_class = 'class="centertext new_message"'
                    lines.append('<tr %s>' % message_class)
                    for name in message_fields:
                        val = entry.get(name, '---')
                        lines.append('<td %s>%s</td>' % (marker_class, val))
                        # Reset marker after first entry
                        marker_class = ''
                    lines.append('</tr>')
                lines.append('</table>')
            else:
                lines.append('No messages in thread')
            if i.has_key('vgrid_name') and i.has_key('thread'):
                lines.append('''
<p>
<div id="new_link">
<a class="replylink" href="javascript:toggle_new('reply_form', 'new_link')">
Reply to this thread</a></p>
</div>
<div class="hidden_form" id="reply_form">
<form method="post" action="?">
<input type="hidden" name="action" value="reply"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<input type="hidden" name="thread" value="%s"/>
<p><textarea id="reply_form_main" name="msg_body" rows="10"
cols="80"></textarea></p>
<p>
<input class="submit_button" type="submit" value="Post"/>
<input class="submit_button" type="reset" value="Clear"/>
<input class="submit_button" type="submit" value="Cancel"
onclick="javascript:toggle_new('reply_form', 'new_link'); return false;"/>
</p>
</form>
</div>
''' % (i['vgrid_name'], i['thread']))
                lines.append('''
<p><a class="refreshlink" href="?show_thread&vgrid_name=%s&thread=%s">
Reload thread</a></p>''' % (i['vgrid_name'], i['thread']))
                lines.append('''
<p><a class="backlink" href="?vgrid_name=%s">Return to forum index</a></p>
''' % i['vgrid_name'])
                lines.append('''
<div id="subscribe_form">
<form method="post" action="?">
<input type="hidden" name="action" value="toggle_subscribe"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<input type="hidden" name="thread" value="%s"/>
<input class="submit_button" type="submit" value="Subscribe/unsubscribe to thread updates"/>
</form>
</div>
''' % (i['vgrid_name'], i['thread']))
        elif i['object_type'] == 'vgrid_list':
            if len(i['vgrids']) > 0:
                vgrids = i['vgrids']
                lines.append("<table class='vgrids columnsort' id='vgridtable'>")
                # Hide public wiki column as it is disabled
                #public_wiki = '<th class=centertext colspan="1">Public Wiki</th>'
                public_wiki = ''
                # Hide public scm column as it is disabled
                #public_scm = '<th class=centertext colspan="1">Public SCM</th>'
                public_scm = ''

                # make "SCM" optional, as it is in the configuration
                if configuration.hg_path and configuration.hgweb_path:
                    scm = '''
  <th class=centertext colspan="1">Owner SCM</th>
  <th class=centertext colspan="1">Member SCM</th>
  %s
''' % public_scm
                else:
                    scm = ''

                lines.append('''
<thead class="title">
<tr>
  <th>Name</th>
  <th width="8"><!-- Owner --></th>
  <th width="8"><!-- Member --></th>
  <th class=centertext colspan="2">Private web pages</th>
  <th class=centertext colspan="2">Public web pages</th>
  <th class=centertext colspan="1">Owner Wiki</th>
  <th class=centertext colspan="1">Member Wiki</th>
  %s
  %s
  <th class=centertext colspan="1">Forum</th>
  <th class=centertext colspan="1">Monitor</th>
</tr>
</thead>
<tbody>
''' % (public_wiki, scm)
                             )
                for obj in vgrids:
                    lines.append('<tr>')
                    lines.append('<td>%s</td>' % obj['name'])
                    lines.append('<td>')
                    if obj.has_key('administratelink'):
                        lines.append('%s'
                                 % html_link(obj['administratelink']))
                    lines.append('</td>')
                    lines.append('<td>')
                    # membership links: should be there in any case
                    if obj.has_key('memberlink'):
                        lines.append('%s'
                                 % html_link(obj['memberlink']))
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('editprivatelink'):
                        lines.append('%s '
                                 % html_link(obj['editprivatelink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('enterprivatelink'):
                        lines.append('%s '
                                 % html_link(obj['enterprivatelink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('editpubliclink'):
                        lines.append('%s '
                                 % html_link(obj['editpubliclink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('enterpubliclink'):
                        lines.append('%s '
                                 % html_link(obj['enterpubliclink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('ownerwikilink'):
                        lines.append('%s '
                                 % html_link(obj['ownerwikilink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('memberwikilink'):
                        lines.append('%s '
                                 % html_link(obj['memberwikilink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    # hide link to public wiki which is disabled in apache
                    #lines.append('<td class=centertext>')
                    #if obj.has_key('publicwikilink'):
                    #    lines.append('%s '
                    #             % html_link(obj['publicwikilink']))
                    #else:
                    #    lines.append('---')
                    #lines.append('</td>')
                    if scm:
                        lines.append('<td class=centertext>')
                        if obj.has_key('ownerscmlink'):
                            lines.append('%s '
                                     % html_link(obj['ownerscmlink']))
                        else:
                            lines.append('---')
                        lines.append('</td>')
                        lines.append('<td class=centertext>')
                        if obj.has_key('memberscmlink'):
                            lines.append('%s '
                                     % html_link(obj['memberscmlink']))
                        else:
                            lines.append('---')
                        lines.append('</td>')
                        # hide link to public scm which is disabled in apache
                        #lines.append('<td class=centertext>')
                        #if obj.has_key('publicscmlink'):
                        #    lines.append('%s '
                        #             % html_link(obj['publicscmlink']))
                        #else:
                        #    lines.append('---')
                        #lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('privateforumlink'):
                        lines.append('%s '
                                 % html_link(obj['privateforumlink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('privatemonitorlink'):
                        lines.append('%s '
                                 % html_link(obj['privatemonitorlink']))
                    else:
                        lines.append('---')
                    lines.append('</td>')
                    # All monitors are private for now
                    #lines.append('<td class=centertext>')
                    #if obj.has_key('publicmonitorlink'):
                    #    lines.append('%s '
                    #             % html_link(obj['publicmonitorlink']))
                    #else:
                    #    lines.append('---')
                    #lines.append('</td>')
                    lines.append('</tr>')
                lines.append('</tbody></table>')
            else:
                lines.append('No matching VGrids found')
        elif i['object_type'] == 'user_stats':
            if i.get('disk', None):
                disk_info = '<h2>Disk stats</h2>'
                for (key, val) in i['disk'].items():
                    disk_info += '%s: %s<br />' % (key, val)
                lines.append(disk_info)
            if i.get('jobs', None):
                jobs_info = '<h2>Job stats</h2>'
                for (key, val) in i['jobs'].items():
                    jobs_info += '%s: %s<br />' % (key, val)
                lines.append(jobs_info)
            if i.get('resources', None):
                resources_info = '<h2>Resource stats</h2>'
                for (key, val) in i['resources'].items():
                    resources_info += '%s: %s<br />' % (key, val)
                lines.append(resources_info)
            if i.get('certificate', None):
                certificate_info = '<h2>Certificate stats</h2>'
                for (key, val) in i['certificate'].items():
                    certificate_info += '%s: %s<br />' % (key, val)
                lines.append(certificate_info)
        elif i['object_type'] == 'script_status':
            status_line = i.get('text')
        elif i['object_type'] == 'end':
            pass
        else:
            lines.append('unknown object %s' % i)

    if status_line:
        lines.append(get_cgi_html_footer(configuration, status_line, True, include_widgets, user_widgets))
    return '\n'.join(lines)


# def xml_format(configuration, ret_val, ret_msg, out_obj):
#    """Generate output in xml format"""
#
#    print "xml format not implemented yet"
#    return True


def soap_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in soap format"""

    try:
        import SOAPpy
        return SOAPpy.buildSOAP(out_obj)
    except Exception, exc:
        configuration.logger.error('soap unavailable (%s) - using txt' % exc)
        return None


def pickle_helper(configuration, ret_val, ret_msg, out_obj, protocol=None):
    """Generate output in requested pickle protocol format"""

    try:
        from shared.serial import dumps
        return dumps(out_obj, protocol)
    except Exception, exc:
        configuration.logger.error('pickle unavailable (%s) - using txt' % exc)
        return None

def pickle_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in default pickle protocol format"""

    return pickle_helper(configuration, ret_val, ret_msg, out_obj, protocol=0)

def pickle1_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in pickle protocol 1 format"""

    return pickle_helper(configuration, ret_val, ret_msg, out_obj, protocol=1)

def pickle2_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in default pickle protocol 2 format"""

    return pickle_helper(configuration, ret_val, ret_msg, out_obj, protocol=2)


def yaml_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in yaml format"""

    try:
        import yaml
        return yaml.dump(out_obj)
    except Exception, exc:
        configuration.logger.error('yaml unavailable (%s) - using txt' % exc)
        return None


def xmlrpc_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in xmlrpc format"""

    try:
        import xmlrpclib
        # Wrap any explicit binary entries to avoid encoding errors
        for entry in out_obj:
            if entry.get('wrap_binary', False):
                for key in entry.get('wrap_targets', []):
                    if not key in entry:
                        continue
                    entry[key] = xmlrpclib.Binary(entry[key])
        return xmlrpclib.dumps((out_obj, ), allow_none=True)
    except Exception, exc:
        configuration.logger.error('xmlrpc unavailable (%s) - using txt' % exc)
        return None


def json_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in json format"""

    try:
        try:
            import json
        except:
            import simplejson as json
        # python >=2.6 includes native json module with loads/dumps methods
        # python <2.6 + python-json module with read/write methods
        if not hasattr(json, 'dumps') and hasattr(json, 'write'):
            json.dumps = json.write
        return json.dumps(out_obj)
    except Exception, exc:
        configuration.logger.error('json unavailable (%s) - using txt' % exc)
        return None

def file_format(configuration, ret_val, ret_msg, out_obj):
    
    file_content = ''
    
    for entry in out_obj:
        if entry['object_type'] == 'file_output':
            for line in entry['lines']:
                file_content += line
                
    return file_content

def get_valid_outputformats():
    """Return list of valid outputformats"""

    return [
        'html',
        'txt',
        'soap',
        'pickle',
        'pickle1',
        'pickle2',
        'yaml',
        'xmlrpc',
        'resource',
        'json',
        'file'
        ]


def format_output(
    configuration,
    ret_val,
    ret_msg,
    out_obj,
    outputformat,
    ):
    """This is the public method that should be called from other scripts"""

    outputformats = get_valid_outputformats()
    (val_ret, val_msg) = validate(out_obj)
    if not val_ret:
        (ret_val, ret_msg) = returnvalues.OUTPUT_VALIDATION_ERROR

        # hide previous output

        out_obj = []
        out_obj.extend([{'object_type': 'error_text', 'text'
                       : 'Validation error! %s' % val_msg},
                       {'object_type': 'title', 'text'
                       : 'Validation error!'}])

    start = None
    title = None
    header = None

    # Add header if missing

    for entry in out_obj:
        obj_type = entry.get('object_type', None)
        if 'start' == obj_type:
            start = entry
        elif 'title' == obj_type:
            title = entry
        elif 'header' == obj_type:
            header = entry
    if not start:
        if not header:
            out_obj = [{'object_type': 'header', 
                        'text': '%s error' % configuration.short_title}]\
                      + out_obj
        if not title:
            out_obj = [{
                'object_type': 'title',
                'text': '%s error' % configuration.short_title,
                'javascript': '',
                'bodyfunctions': '',
                }] + out_obj

    if not outputformat in outputformats:
        return txt_format(configuration, ret_val, ret_msg, out_obj)

    try:
        return eval('%s_format(configuration, ret_val, ret_msg, out_obj)' % \
                    outputformat)
    except Exception, err:
        msg = '%s failed on server! Defaulting to txt output. (%s)' % \
              (outputformat, err)
        configuration.logger.error(msg)
        configuration.logger.error(traceback.format_exc())
        return (txt_format(configuration, ret_val, msg, out_obj))

def format_timedelta(timedelta):
    """Formats timedelta as '[Years,] [days,] HH:MM:SS'"""
    years = timedelta.days/365
    days = timedelta.days - (years*365)
    hours = timedelta.seconds/3600
    minutes = (timedelta.seconds-(hours*3600))/60
    seconds = timedelta.seconds - (hours*3600) - (minutes*60)

    hours_str = "%s" % (str(hours))
    if (hours < 10):
        hours_str = "0%s" % (hours_str)

    minutes_str = "%s" % (str(minutes))
    if (minutes < 10):
        minutes_str = "0%s" % (minutes_str)
        
    seconds_str = "%s" % (str(seconds))
    if (seconds < 10):
        seconds_str = "0%s" % (seconds_str)

    if (years > 0):
        result = "%s years, %s days, %s:%s:%s" % (str(years), str(days), hours_str, minutes_str, seconds_str)
    elif (days > 0):
        result = "%s days, %s:%s:%s" % (str(days), hours_str, minutes_str, seconds_str)
    else:
        result = "%s:%s:%s" % (hours_str, minutes_str, seconds_str)
        
    return result

    
