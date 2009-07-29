#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# output - [insert a few words of module description on this line]
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

"""Module with functions to generate output in format
specified by the client."""

import pickle

import shared.returnvalues as returnvalues
from shared.html import get_cgi_html_header, get_cgi_html_footer
from shared.objecttypes import validate
from shared.prettyprinttable import pprint_table

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


def resource_format(ret_val, ret_msg, out_obj):
    txt = ret_val
    for i in out_obj:
        if i['object_type'] == 'link':
            txt += i['destination']
    return txt


def txt_format(ret_val, ret_msg, out_obj):
    """Generate output in txt format"""

    lines = []
    lines.append('Exit code: %s Description %s' % (ret_val, ret_msg))

    for i in out_obj:
        if i['object_type'] == 'error_text':
            lines.append('** %s **' % i['text'])
        elif i['object_type'] == 'warning':
            lines.append('! %s !' % i['text'])
        elif i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'header':
            lines.append('')
            lines.append('___%s___' % i['text'].upper())
            lines.append('')
        elif i['object_type'] == 'sectionheader':
            lines.append('')
            lines.append('___%s___' % i['text'])
            lines.append('')
        elif i['object_type'] == 'title':
            lines.append('Title: %s' % i['text'])
        elif i['object_type'] == 'text':
            lines.append('%s' % i['text'])
        elif i['object_type'] == 'verbatim':
            lines.append('%s' % i['text'])
        elif i['object_type'] == 'link':

            # We do not want link junk in plain text
            # lines.append(txt_link(i)

            continue
        elif i['object_type'] == 'multilinkline':

            # We do not want link junk in plain text
            # links = i["links"]
            # if len(links) == 0:
            #    lines.append("No links found!"
            # else:
            #    lines.append(' / '.join([txt_link(link) for link in links])

            continue
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            header = [['Job ID', 'Old status', 'New status Message',
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
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            for stat in stats:
                lines.append('device\t%(device)s' % stat)
                lines.append('inode\t%(inode)s' % stat)
                lines.append('mode\t%(mode)s' % stat)
                lines.append('nlink\t%(nlink)s' % stat)
                lines.append('uid\t%(uid)s' % stat)
                lines.append('gid\t%(gid)s' % stat)
                lines.append('rdev\t%(rdev)s' % stat)
                lines.append('size\t%(size)s' % stat)
                lines.append('atime\t%(atime)s' % stat)
                lines.append('mtime\t%(mtime)s' % stat)
                lines.append('ctime\t%(ctime)s' % stat)
        elif i['object_type'] == 'job_list':
            if len(i['jobs']) > 0:
                jobs = i['jobs']

                for obj in jobs:
                    lines.append('Job Id: %s' % obj['job_id'])
                    lines.append('Status: %s' % obj['status'])
                    if obj.has_key('execute'):
                        lines.append('Execute: %s' % obj['execute'])
                    if obj.has_key('verified'):
                        lines.append('Verified status: %s'
                                 % obj['verified'])
                    if obj.has_key('verified_timestamp'):
                        lines.append('Verified: %s'
                                 % obj['verified_timestamp'])
                    if obj.has_key('received_timestamp'):
                        lines.append('Received: %s'
                                 % obj['received_timestamp'])
                    if obj.has_key('queued_timestamp'):
                        lines.append('Queued: %s'
                                 % obj['queued_timestamp'])
                    if obj.has_key('schedule_timestamp'):
                        lines.append('Scheduled: %s'
                                 % obj['schedule_timestamp'])
                    if obj.has_key('schedule_hint'):
                        lines.append('Schedule hint: %s'
                                 % obj['schedule_hint'])
                    if obj.has_key('executing_timestamp'):
                        lines.append('Executing: %s'
                                 % obj['executing_timestamp'])
                    if obj.has_key('finished_timestamp'):
                        lines.append('Finished: %s'
                                 % obj['finished_timestamp'])
                    if obj.has_key('failed_timestamp'):
                        lines.append('Failed: %s'
                                 % obj['failed_timestamp'])
                    if obj.has_key('canceled_timestamp'):
                        lines.append('Canceled: %s'
                                 % obj['canceled_timestamp'])
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        lines.append('Execution history</td><td>#%s</td></tr>'
                                 % count)
                        if single_history.has_key('queued'):
                            lines.append('Queued %s: %s' % (count,
                                    single_history['queued']))
                        if single_history.has_key('executing'):
                            lines.append('Executing %s: %s' % (count,
                                    single_history['executing']))
                        if single_history.has_key('failed'):
                            lines.append('Failed %s: %s' % (count,
                                    single_history['failed']))
                        if single_history.has_key('failed_message'):
                            lines.append('Failed message %s: %s'
                                     % (count,
                                    single_history['failed_message']))

                    # add newline before next job)

                    lines.append('')
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
                lines.append('No files to run wc on')
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
                    lines.append(out)
        elif i['object_type'] == 'file_not_found':
            lines.append('%s: No such file or directory' % i['name'])
        elif i['object_type'] == 'dir_listings':
            if len(i['dir_listings']) == 0:
                continue
            columns = 6
            cols = 0
            if i['show_dest']:
                columns += 1
            for dir_listing in i['dir_listings']:
                for entry in dir_listing['entries']:
                    line = ''
                    if 'directory' == entry['type']:
                        directory = entry
                        if directory.has_key('long_format'):
                            if directory == dir_listing['entries'][0]:
                                lines.append('%s:\ntotal %s'
                                         % (dir_listing['relative_path'
                                        ], len(dir_listing['entries'])))
                        line += '\t\t'
                        if directory.has_key('actual_dir'):
                            line += '%s' % directory['actual_dir']
                        else:
                            line += '\t'
                        line += '%s' % directory['name']
                        lines.append(line)
                    elif 'file' == entry['type']:
                        this_file = entry
                        line += '\t\t'
                        if this_file.has_key('long_format'):
                            line += '%s' % this_file['long_format']
                        else:
                            line += '\t'
                        line += '%s' % this_file['name']
                        if this_file.has_key('show_dest'):
                            line += '%s' % this_file['dest']
                        lines.append(line)
        elif i['object_type'] == 'jobobj':
            job_dict = i['jobobj'].to_dict()
            lines.append('Field\t\tValue')
            for (key, val) in job_dict.items():
                lines.append('%s\t\t%s' % (key, val))
        elif i['object_type'] == 'html_form':
            pass
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                lines.append('File: %s' % i['path'])
            for line in i['lines']:
                lines.append(line)
        elif i['object_type'] == 'list':
            for list_item in i['list']:
                lines.append('%s' % list_item)
        else:
            lines.append('unknown object %s' % i)

    return '\n'.join(lines)


def html_link(obj):
    """html format link"""

    return '<a href=%s>%s</a>' % (obj['destination'], obj['text'])


def html_table_if_have_keys(dictionary, keywordlist):
    """create html table contents based on keys in a dictionary"""

    outputstring = ''
    for key in keywordlist:
        if dictionary.has_key(key):
            outputstring += '<td>%s</td>' % dictionary[key]
        else:
            outputstring += '<td></td>'
    return outputstring


def html_format(ret_val, ret_msg, out_obj):
    """Generate output in html format"""

    lines = []
    for i in out_obj:
        if i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'error_text':
            lines.append('<p class=errortext>%s</p>' % i['text'])
        elif i['object_type'] == 'warning':
            lines.append('<p class=warningtext>%s</p>' % i['text'])
        elif i['object_type'] == 'header':
            lines.append('<h1>%s</h1>' % i['text'])
        elif i['object_type'] == 'sectionheader':
            lines.append('<h3>%s</h3>' % i['text'])
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
            lines.append(get_cgi_html_header(
                i['text'],
                '',
                True,
                javascript,
                bodyfunctions,
                include_menu,
                ))
        elif i['object_type'] == 'text':
            lines.append('<p>%s</p>' % i['text'])
        elif i['object_type'] == 'verbatim':
            lines.append('%s' % i['text'])
        elif i['object_type'] == 'link':
            lines.append(html_link(i))
        elif i['object_type'] == 'job_list':

            # lines.append("<a href=%s>%s</a>" % (i["destination"], i["text"])

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
                    if obj.has_key('executing_timestamp'):
                        lines.append('<tr><td>Executing</td><td>%s</td></tr>'
                                 % obj['executing_timestamp'])
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
                        if single_history.has_key('failed'):
                            lines.append('<tr><td>Failed %s</td><td>%s</td></tr>'
                                     % (count, single_history['failed'
                                    ]))
                        if single_history.has_key('failed_message'):
                            lines.append('<tr><td>Failed message %s</td><td>%s</td></tr>'
                                     % (count,
                                    single_history['failed_message']))

                    lines.append('<tr><td>Links</td><td>')
                    lines.append('%s<br>' % html_link(obj['statuslink'
                                 ]))
                    lines.append('%s<br>' % html_link(obj['mrsllink']))
                    lines.append('%s<br>' % html_link(obj['resubmitlink'
                                 ]))
                    lines.append('%s<br>' % html_link(obj['cancellink'
                                 ]))
                    lines.append('%s<br>'
                                  % html_link(obj['jobschedulelink']))
                    lines.append('%s<br>'
                                  % html_link(obj['liveoutputlink']))
                    if obj.has_key('outputfileslink'):
                        lines.append('<br>%s'
                                 % html_link(obj['outputfileslink']))
                    lines.append('</td></tr><tr><td><br></td></tr>')

                lines.append('</table>')
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            lines.append("<table class='resubmit'><tr><th>Job ID</th><th>Resubmit status</th><th>New jobid</th><th>Message</th></tr>"
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
            columns = 6
            if 'full' == i['style']:
                columns += 1
            if i.get('show_dest', False):
                columns += 1
            lines.append("<table class='files'>")
            lines.append('<tr>')
            cols = 0
            lines.append('<td>Info</td>')
            cols += 1
            if 'full' == i['style']:
                lines.append("<td><input type='checkbox' name='allbox' value='allbox' onclick='un_check()'></td>"
                             )
                cols += 1

                # lines.append("<td><br></td>"
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
                            lines.append('<td width=20%%>%s:<br>total %s</td>'
                                     % (dir_listing['relative_path'],
                                    len(dir_listing['entries'])))
                            cols += 1
                            lines.append('<td><br></td>' * (columns
                                     - cols) + '</tr>')
                            cols = columns

                        lines.append('<tr class=%s>' % row_class)
                        cols = 0
                        lines.append('<td><br></td>')
                        cols += 1
                        if 'full' == i['style']:
                            lines.append("<td><input type='checkbox' name='path' value='%s'></td>"
                                     % directory['dirname_with_dir'])
                            cols += 1
                        if directory.has_key('actual_dir'):
                            lines.append('<td>%s</td>'
                                     % directory['actual_dir'])
                        else:
                            lines.append('<td><br></td>')
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
                        lines.append('<td><br></td>' * (columns - cols)
                                 + '</tr>')
                        cols = columns
                        lines.append('</tr>')
                    elif 'file' == entry['type']:
                        this_file = entry
                        lines.append('<tr class=%s>' % row_class)
                        cols = 0
                        lines.append('<td><br></td>')
                        cols += 1
                        if 'full' == i['style']:
                            lines.append("<td><input type='checkbox' name='path' value='%s'></td>"
                                     % this_file['file_with_dir'])
                            cols += 1
                        if this_file.has_key('long_format'):
                            lines.append('<td>%s</td>'
                                     % this_file['long_format'])
                        else:
                            lines.append('<td><br></td>')
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
                        if this_file.get('show_dest', False):
                            lines.append('<td>%s</td>'
                                     % this_file['dest'])
                            cols += 1
                        lines.append('<td><br></td>' * (columns - cols)
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
                        lines.append(filewc['lines'])
                    lines.append('</td><td>')
                    if filewc.has_key('words'):
                        lines.append(filewc['words'])
                    lines.append('</td><td>')
                    if filewc.has_key('bytes'):
                        lines.append(filewc['bytes'])
                    lines.append('</td></tr>')
                lines.append('</table>')
        elif i['object_type'] == 'file_not_found':

            lines.append('File %s was <B>not</B> found!' % i['name'])
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                lines.append('File: %s<br>' % i['path'])
            lines.append('<br>'.join(i['lines']) + '<br>')
        elif i['object_type'] == 'list':
            lines.append('<ul>')
            for list_item in i['list']:
                lines.append(('<li>%s</li>' % list_item).replace('\n',
                             '<br>'))
            lines.append('</ul>')
        elif i['object_type'] == 'linklist':
            links = i['links']
            if len(links) == 0:
                lines.append('No links found!')
            else:
                lines.append('<table class="links"><th>Name</th><th>Link</th></tr>'
                             )
                for link in links:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                  % (link['text'], html_link(link)))
                lines.append('</table>')
        elif i['object_type'] == 'multilinkline':
            links = i['links']
            if len(links) == 0:
                lines.append('No links found!')
            else:
                lines.append(' / '.join([html_link(link) for link in
                             links]))
        elif i['object_type'] == 'file':
            lines.append(i['name'])
        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                lines.append('No job submit status found!')
            else:
                lines.append('<table class="submitstatus"><th>File</th><th>Status</th><th>Job Id</th><th>Message</th></tr>'
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
                lines.append('<table class="objects"><th>Object</th><th>Info</th></tr>'
                             )
                for (name, val) in objects:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                  % (name, val))
                lines.append('</table>')
        elif i['object_type'] == 'sandboxinfos':
            sandboxinfos = i['sandboxinfos']
            if len(sandboxinfos) == 0:
                lines.append('No sandboxes found!')
            else:
                lines.append('<table class="sandboxinfo"><th>Username</th><th>Resource(s)</th><th>Jobs</th><th>Walltime</th></tr>'
                             )
                row_number = 1
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
            if len(runtimeenvironments) == 0:
                lines.append('No runtime environments found!')
            else:
                lines.append('<table class="runtimeenvs"><th>Name</th><th>Description</th><th>Details</th><th>Creator</th></tr>'
                             )
                row_number = 1
                for single_re in runtimeenvironments:
                    row_class = row_name[row_number % 2]
                    lines.append('<tr class=%s><td>%s</td><td>%s</td><td><a href=showre.py?re_name=%s>View</a></td><td>%s</td></tr>'
                                  % (row_class, single_re['name'],
                                 single_re['description'],
                                 single_re['name'], single_re['creator'
                                 ]))
                    row_number += 1
                lines.append('</table>')
        elif i['object_type'] == 'runtimeenvironment':
            software_html = ''
            for software in i['software']:
                software_html += \
                    '<table class="runtimeenvsw" frame=hsides rules=none cellpadding=5>'
                software_html += \
                    '<tr><td><img src=%s width=80 height=80></td><td></td></tr>'\
                     % software['icon']
                software_html += '<tr><td>Name:</td><td>%s</td></tr>'\
                     % software['name']
                software_html += \
                    '<tr><td>Url:</td><td><a href=%s>%s</a></td></tr>'\
                     % (software['url'], software['url'])
                software_html += \
                    '<tr><td>Description:</td><td>%s</td></tr>'\
                     % software['description']
                software_html += '<tr><td>Version:</td><td>%s</td></tr>'\
                     % software['version']
                software_html += '</table>'
            environment_html = ''
            for environment in i['environments']:
                environment_html += \
                    '<table class="runtimeenvvars" frame=hsides rules=none cellpadding=5>'
                environment_html += '<tr><td>Name:</td><td>%s</td></tr>'\
                     % environment['name']
                environment_html += \
                    '<tr><td>Example::</td><td>%s</td></tr>'\
                     % environment['example']
                environment_html += \
                    '<tr><td>Description:</td><td>%s</td></tr>'\
                     % environment['description']
                environment_html += '</table>'

            lines.append('<table class="runtimeenvdetails">')
            lines.append('<tr><td>Name</td><td>%s</td></tr>' % i['name'
                         ])
            lines.append('<tr><td>Description</td><td>%s</td></tr>'
                          % i['description'])
            lines.append('<tr><td>Creator</td><td>%s</td></tr>'
                          % i['creator'])
            lines.append('<tr><td>Created</td><td>%s</td></tr>'
                          % i['created'])
            lines.append('<tr><td>Job count</td><td>%s</td></tr>'
                          % i['job_count'])
            lines.append('<tr><td>Resource count</td><td>%s</td></tr>'
                          % i['resource_count'])
            lines.append('<tr><td>Needed software</td><td>%s</td></tr>'
                          % software_html)
            lines.append("<tr><td>Testprocedure</td><td valign='top'>%s</td></tr>"
                          % i['testprocedure'])
            lines.append("<tr><td>Verifystdout</td><td valign='top'>%s</td></tr>"
                          % i['verifystdout'])
            lines.append("<tr><td>Verifystderr</td><td valign='top'>%s</td></tr>"
                          % i['verifystderr'])
            lines.append("<tr><td>Verifystatus</td><td valign='top'>%s</td></tr>"
                          % i['verifystatus'])
            lines.append('<tr><td>Environments</td><td>%s</td></tr>'
                          % environment_html)
            lines.append('</table>')
        elif i['object_type'] == 'vgrid_list':
            if len(i['vgrids']) > 0:
                vgrids = i['vgrids']
                lines.append("<table class='vgrids'>")
                lines.append('<tr class="title"><td>Name</td><td>Actions</td><td class=centertext colspan=2>Private page</td><td class=centertext colspan=2>Public page</td><td class=centertext colspan=2>Wiki</td><td class=centertext colspan=2>Monitor</td></tr>'
                             )
                row_number = 1
                for obj in vgrids:
                    row_class = row_name[row_number % 2]
                    lines.append('<tr class=%s>' % row_class)
                    lines.append('<td>%s</td>' % obj['name'])
                    lines.append('<td>')
                    if obj.has_key('administratelink'):
                        lines.append('%s'
                                 % html_link(obj['administratelink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('editprivatelink'):
                        lines.append('%s '
                                 % html_link(obj['editprivatelink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('enterprivatelink'):
                        lines.append('%s '
                                 % html_link(obj['enterprivatelink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('editpubliclink'):
                        lines.append('%s '
                                 % html_link(obj['editpubliclink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('enterpubliclink'):
                        lines.append('%s '
                                 % html_link(obj['enterpubliclink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('privatewikilink'):
                        lines.append('%s '
                                 % html_link(obj['privatewikilink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('publicwikilink'):
                        lines.append('%s '
                                 % html_link(obj['publicwikilink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('privatemonitorlink'):
                        lines.append('%s '
                                 % html_link(obj['privatemonitorlink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('<td class=centertext>')
                    if obj.has_key('publicmonitorlink'):
                        lines.append('%s '
                                 % html_link(obj['publicmonitorlink']))
                    else:
                        lines.append('-----')
                    lines.append('</td>')
                    lines.append('</tr>')
                    row_number += 1
                lines.append('</table>')
            else:
                lines.append('No matching VGrids found')
        else:
            lines.append('unknown object %s' % i)
    footer = \
        """</div>
    <div id="exitcode">
Exit code: %s Description: %s<br>
    </div>
<br>    
"""\
         % (ret_val, ret_msg)

    lines.append(get_cgi_html_footer(footer))
    return '\n'.join(lines)


# def xml_format(ret_val, ret_msg, out_obj):
#    """Generate output in xml format"""
#
#    print "xml format not implemented yet"
#    return True


def soap_format(ret_val, ret_msg, out_obj):
    """Generate output in soap format"""

    try:
        import SOAPpy
        return SOAPpy.buildSOAP(out_obj)
    except Exception, exc:
        print 'SOAPpy not available on server! Defaulting to .txt output. (%s)'\
             % exc
        return None


def pickle_helper(
    ret_val,
    ret_msg,
    out_obj,
    protocol=None,
    ):
    """Shared helper to generate output in pickle"""

    return pickle.dumps(out_obj, protocol)


def pickle_x86_format(ret_val, ret_msg, out_obj):
    """Generate output in pickle x86 format - deprecated!"""

    # There's no guarantee that output is actually X86
    # it probably depends on the server arch if anything

    return pickle_helper(ret_val, ret_msg, out_obj)


def pickle_format(ret_val, ret_msg, out_obj):
    """Generate output in pickle default protocol format"""

    return pickle_helper(ret_val, ret_msg, out_obj)


def pickle2_format(ret_val, ret_msg, out_obj):
    """Generate output in pickle protocol 2 format"""

    return pickle_helper(ret_val, ret_msg, out_obj, 2)


def yaml_format(ret_val, ret_msg, out_obj):
    """Generate output in yaml format"""

    try:
        import yaml
        return yaml.dump(out_obj)
    except Exception, exc:
        print 'yaml not available on server! Defaulting to .txt output. (%s)'\
             % exc
        return None


def xmlrpc_format(ret_val, ret_msg, out_obj):
    """Generate output in xmlrpc format"""

    try:
        import xmlrpclib
        return xmlrpclib.dumps((out_obj, ), allow_none=True)
    except Exception, exc:
        print 'xmlrpclib not available on server! Defaulting to .txt output. (%s)'\
             % exc
        return None


def json_format(ret_val, ret_msg, out_obj):
    """Generate output in json format"""

    try:
        import json
        try:

            # python >=2.6 includes native json module with loads/dumps methods

            return json.dumps(out_obj)
        except AttributeError:

            # python <2.6 + python-json module with read/write methods

            return json.write(out_obj)
    except Exception, exc:
        print 'json not available on server! Defaulting to .txt output. (%s)'\
             % exc
        return None


def get_valid_outputformats():
    """Return list of valid outputformats"""

    return [
        'html',
        'txt',
        'soap',
        'pickle_x86',
        'pickle',
        'pickle2',
        'yaml',
        'xmlrpc',
        'resource',
        'json',
        ]


def format_output(
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
            out_obj = [{'object_type': 'header', 'text': 'MiG error'}]\
                      + out_obj
        if not title:
            out_obj = [{
                'object_type': 'title',
                'text': 'MiG error',
                'javascript': '',
                'bodyfunctions': '',
                }] + out_obj

    if not outputformat in outputformats:
        return txt_format(ret_val, ret_msg, out_obj)

    return eval('%s_format(ret_val, ret_msg, out_obj)' % outputformat)


