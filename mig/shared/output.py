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
    print ret_val
    for i in out_obj:
        if i['object_type'] == 'link':
            print i['destination']
    return True


def txt_format(ret_val, ret_msg, out_obj):
    """Generate output in txt format"""

    print 'Exit code: %s Description %s' % (ret_val, ret_msg)

    for i in out_obj:
        if i['object_type'] == 'error_text':
            print '** %s **' % i['text']
        elif i['object_type'] == 'warning':
            print '! %s !' % i['text']
        elif i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'header':
            print
            print '___%s___' % i['text'].upper()
            print
        elif i['object_type'] == 'sectionheader':
            print
            print '___%s___' % i['text']
            print
        elif i['object_type'] == 'title':
            print 'Title: %s' % i['text']
        elif i['object_type'] == 'text':
            print '%s' % i['text']
        elif i['object_type'] == 'link':

            # We do not want link junk in plain text
            # print txt_link(i)

            continue
        elif i['object_type'] == 'multilinkline':

            # We do not want link junk in plain text
            # links = i["links"]
            # if len(links) == 0:
            #    print "No links found!"
            # else:
            #    print ' / '.join([txt_link(link) for link in links])

            continue
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            header = [['Job ID', 'Old status', 'New status Message',
                      'Message']]
            pprint_table(txt_table_if_have_keys(header,
                         changedstatusjobs, ['job_id', 'oldstatus',
                         'newstatus', 'message']))
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            for stat in stats:
                print 'device\t%(device)s' % stat
                print 'inode\t%(inode)s' % stat
                print 'mode\t%(mode)s' % stat
                print 'nlink\t%(nlink)s' % stat
                print 'uid\t%(uid)s' % stat
                print 'gid\t%(gid)s' % stat
                print 'rdev\t%(rdev)s' % stat
                print 'size\t%(size)s' % stat
                print 'atime\t%(atime)s' % stat
                print 'mtime\t%(mtime)s' % stat
                print 'ctime\t%(ctime)s' % stat
        elif i['object_type'] == 'job_list':
            if len(i['jobs']) > 0:
                jobs = i['jobs']

                for obj in jobs:
                    print 'Job Id: %s' % obj['job_id']
                    print 'Status: %s' % obj['status']
                    if obj.has_key('execute'):
                        print 'Execute: %s' % obj['execute']
                    if obj.has_key('verified'):
                        print 'Verified status: %s' % obj['verified']
                    if obj.has_key('verified_timestamp'):
                        print 'Verified: %s' % obj['verified_timestamp']
                    if obj.has_key('received_timestamp'):
                        print 'Received: %s' % obj['received_timestamp']
                    if obj.has_key('queued_timestamp'):
                        print 'Queued: %s' % obj['queued_timestamp']
                    if obj.has_key('executing_timestamp'):
                        print 'Executing: %s'\
                             % obj['executing_timestamp']
                    if obj.has_key('finished_timestamp'):
                        print 'Finished: %s' % obj['finished_timestamp']
                    if obj.has_key('failed_timestamp'):
                        print 'Failed: %s' % obj['failed_timestamp']
                    if obj.has_key('canceled_timestamp'):
                        print 'Canceled: %s' % obj['canceled_timestamp']
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        print 'Execution history</td><td>#%s</td></tr>'\
                             % count
                        if single_history.has_key('queued'):
                            print 'Queued %s: %s' % (count,
                                    single_history['queued'])
                        if single_history.has_key('executing'):
                            print 'Executing %s: %s' % (count,
                                    single_history['executing'])
                        if single_history.has_key('failed'):
                            print 'Failed %s: %s' % (count,
                                    single_history['failed'])
                        if single_history.has_key('failed_message'):
                            print 'Failed message %s: %s' % (count,
                                    single_history['failed_message'])

                    # print newline before next job

                    print ''
        elif i['object_type'] == 'filewcs':

            # if len(i["jobs"]) > 0:
                # jobs = i["jobs"]
                # print "||------------------------------------||"
                # print "|| Job ID | Status | Queued timestamp ||"
                # for obj in jobs:
                #    print "|| %s | %s | %s ||" % (obj["job_id"], obj["status"], obj["queued_timestamp"])
                # print "||------------------------------------||"

            filewcs = i['filewcs']
            if len(filewcs) == 0:
                print 'No files to run wc on'
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
                    print out
        elif i['object_type'] == 'file_not_found':
            print '%s: No such file or directory' % i['name']
        elif i['object_type'] == 'dir_listings':
            if len(i['dir_listings']) == 0:
                continue
            columns = 6
            cols = 0
            for dir_listing in i['dir_listings']:
                for entry in dir_listing['entries']:
                    line = ''
                    if 'directory' == entry['type']:
                        directory = entry
                        if directory.has_key('long_format'):
                            if directory == dir_listing['entries'][0]:
                                print '%s:\ntotal %s'\
                                     % (dir_listing['relative_path'],
                                        len(dir_listing['entries']))
                        line += '\t\t'
                        if directory.has_key('actual_dir'):
                            line += '%s' % directory['actual_dir']
                        else:
                            line += '\t'
                        line += '%s' % directory['name']
                        print line
                    elif 'file' == entry['type']:
                        this_file = entry
                        line += '\t\t'
                        if this_file.has_key('long_format'):
                            line += '%s' % this_file['long_format']
                        else:
                            line += '\t'
                        line += '%s' % this_file['name']
                        print line
        elif i['object_type'] == 'html_form':
            pass
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                print 'File: %s' % i['path']
            for line in i['lines']:
                print line
        elif i['object_type'] == 'list':
            for list_item in i['list']:
                print '%s' % list_item
        else:
            print 'unknown object %s' % i

    return True


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

    for i in out_obj:
        if i['object_type'] == 'start':
            pass  # for now
        elif i['object_type'] == 'error_text':
            print '<p class=errortext>%s</p>' % i['text']
        elif i['object_type'] == 'warning':
            print '<p class=warningtext>%s</p>' % i['text']
        elif i['object_type'] == 'header':
            print '<h1>%s</h1>' % i['text']
        elif i['object_type'] == 'sectionheader':
            print '<h3>%s</h3>' % i['text']
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
            print get_cgi_html_header(
                i['text'],
                '',
                True,
                javascript,
                bodyfunctions,
                include_menu,
                )
        elif i['object_type'] == 'text':
            print '<p>%s</p>' % i['text']
        elif i['object_type'] == 'link':
            print html_link(i)
        elif i['object_type'] == 'job_list':

            # print "<a href=%s>%s</a>" % (i["destination"], i["text"])

            if len(i['jobs']) > 0:
                jobs = i['jobs']
                print "<table class='jobs'>"

                # <tr><td>Job ID</td><td>Status</td><td>Queued timestamp</td></tr>"

                for obj in jobs:
                    print '<tr><th>Job Id</th><th>%s</th></tr>'\
                         % obj['job_id']
                    print '<tr><td>Status</td><td>%s</td></tr>'\
                         % obj['status']
                    if obj.has_key('execute'):
                        print '<tr><td>Execute</td><td>%s</td></tr>'\
                             % obj['execute']
                    if obj.has_key('verified'):
                        print '<tr><td>Verified status</td><td>%s</td></tr>'\
                             % obj['verified']
                    if obj.has_key('verified_timestamp'):
                        print '<tr><td>Verified</td><td>%s</td></tr>'\
                             % obj['verified_timestamp']
                    if obj.has_key('received_timestamp'):
                        print '<tr><td>Received</td><td>%s</td></tr>'\
                             % obj['received_timestamp']
                    if obj.has_key('queued_timestamp'):
                        print '<tr><td>Queued</td><td>%s</td></tr>'\
                             % obj['queued_timestamp']
                    if obj.has_key('executing_timestamp'):
                        print '<tr><td>Executing</td><td>%s</td></tr>'\
                             % obj['executing_timestamp']
                    if obj.has_key('finished_timestamp'):
                        print '<tr><td>Finished</td><td>%s</td></tr>'\
                             % obj['finished_timestamp']
                    if obj.has_key('failed_timestamp'):
                        print '<tr><td>Failed</td><td>%s</td></tr>'\
                             % obj['failed_timestamp']
                    if obj.has_key('canceled_timestamp'):
                        print '<tr><td>Canceled</td><td>%s</td></tr>'\
                             % obj['canceled_timestamp']
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        print '<tr><td>Execution history</td><td>#%s</td></tr>'\
                             % count
                        if single_history.has_key('queued'):
                            print '<tr><td>Queued %s</td><td>%s</td></tr>'\
                                 % (count, single_history['queued'])
                        if single_history.has_key('executing'):
                            print '<tr><td>Executing %s</td><td>%s</td></tr>'\
                                 % (count, single_history['executing'])
                        if single_history.has_key('failed'):
                            print '<tr><td>Failed %s</td><td>%s</td></tr>'\
                                 % (count, single_history['failed'])
                        if single_history.has_key('failed_message'):
                            print '<tr><td>Failed message %s</td><td>%s</td></tr>'\
                                 % (count,
                                    single_history['failed_message'])

                    print '<tr><td>Links</td><td>'
                    print '%s<br>' % html_link(obj['statuslink'])
                    print '%s<br>' % html_link(obj['mrsllink'])
                    print '%s<br>' % html_link(obj['resubmitlink'])
                    print '%s<br>' % html_link(obj['cancellink'])
                    print '%s<br>' % html_link(obj['liveoutputlink'])
                    if obj.has_key('outputfileslink'):
                        print '<br>%s' % html_link(obj['outputfileslink'
                                ])
                    print '</td></tr><tr><td><br></td></tr>'

                print '</table>'
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            print "<table class='resubmit'><tr><th>Job ID</th><th>Resubmit status</th><th>New jobid</th><th>Message</th></tr>"
            for resubmitobj in resubmitobjs:
                print '<tr>%s</tr>'\
                     % html_table_if_have_keys(resubmitobj, ['job_id',
                        'status', 'new_job_id', 'message'])
            print '</table>'
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            print "<table class='changedjobstatus'><tr><th>Job ID</th><th>Old status</th><th>New status</th><th>Message</th></tr>"
            for changedstatus in changedstatusjobs:
                print '<tr>%s</tr>'\
                     % html_table_if_have_keys(changedstatus, ['job_id'
                        , 'oldstatus', 'newstatus', 'message'])
            print '</table>'
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            print "<table class='stats'><tr><th>Filename</th><th>Device</th><th>Inode</th><th>Mode</th><th>Nlink</th><th>User ID</th><th>Group ID</th><th>RDEV</th><th>Size</th><th>Last accessed</th><th>Modified time</th><th>Created time</th></tr>"
            for stat in stats:
                print '<tr>%s</tr>' % html_table_if_have_keys(stat, [
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
                    ])
            print '</table>'
        elif i['object_type'] == 'fileuploadobjs':
            fileuploadobjs = i['fileuploadobjs']
            if len(fileuploadobjs) == 0:
                print 'No jobs submitted!'
            else:
                print "<table class='fileupload'><tr><th>Filename</th><th>Saved</th><th>Extract packages</th><th>Submit flag</th><th>File size</th><th>Message</th></tr>"
                for fileuploadobj in fileuploadobjs:
                    print '<tr>%s</tr>'\
                         % html_table_if_have_keys(fileuploadobj, [
                        'name',
                        'saved',
                        'extract_packages',
                        'submitmrsl',
                        'size',
                        'message',
                        ])
                print '</table>'
        elif i['object_type'] == 'html_form':
            print i['text']
        elif i['object_type'] == 'dir_listings':
            if len(i['dir_listings']) == 0:
                continue
            columns = 6
            print "<table class='files'>"
            print '<tr>'
            cols = 0
            print '<td>Info</td>'
            cols += 1
            print "<td><input type='checkbox' name='allbox' value='allbox' onclick='un_check()'></td>"
            cols += 1

            # print "<td><br></td>"
            # cols += 1

            print '<td colspan=%d>Select/deselect all files</td>'\
                 % (columns - cols)
            print '</tr>'
            print '<tr>'
            cols = 0
            print '<td colspan=%d><hr width=100%%></td>' % (columns
                     - cols)
            print '</tr>'

            for dir_listing in i['dir_listings']:
                for entry in dir_listing['entries']:
                    cols = 0
                    if 'directory' == entry['type']:
                        directory = entry
                        if directory == dir_listing['entries'][0]:
                            print '<tr>'
                            print '<td width=20%%>%s:<br>total %s</td>'\
                                 % (dir_listing['relative_path'],
                                    len(dir_listing['entries']))
                            cols += 1
                            print '<td><br></td>' * (columns - cols)\
                                 + '</tr>'
                            cols = columns

                        print '<tr>'
                        cols = 0
                        print '<td><br></td>'
                        cols += 1
                        print "<td><input type='checkbox' name='path' value='%s'></td>"\
                             % directory['dirname_with_dir']
                        cols += 1
                        if directory.has_key('actual_dir'):
                            print '<td>%s</td>' % directory['actual_dir'
                                    ]
                        else:
                            print '<td><br></td>'
                        cols += 1
                        print "<td><a href='ls.py?path=%s;flags=%s;output_format=html'>show</a></td><td>DIR</td>"\
                             % (directory['dirname_with_dir'],
                                dir_listing['flags'])
                        cols += 2
                        print '<td>%s</td>' % directory['name']
                        cols += 1
                        print '<td><br></td>' * (columns - cols)\
                             + '</tr>'
                        cols = columns
                        print '</tr>'
                    elif 'file' == entry['type']:
                        this_file = entry
                        print '<tr>'
                        cols = 0
                        print '<td><br></td>'
                        cols += 1
                        print "<td><input type='checkbox' name='path' value='%s'></td>"\
                             % this_file['file_with_dir']
                        cols += 1
                        if this_file.has_key('long_format'):
                            print '<td>%s</td>'\
                                 % this_file['long_format']
                        else:
                            print '<td><br></td>'
                        cols += 1
                        print "<td><a href='/%s/%s'>show</a></td>"\
                             % ('cert_redirect',
                                this_file['file_with_dir'])
                        cols += 1
                        print "<td><a href='editor.py?path=%s;output_format=html'>edit</a></td>"\
                             % this_file['file_with_dir']
                        cols += 1
                        print '<td>%s</td>' % this_file['name']
                        cols += 1
                        print '<td><br></td>' * (columns - cols)\
                             + '</tr>'
                        cols = columns
                        print '</tr>'
            print '</form></table>'
            print ""
        elif i['object_type'] == 'filewcs':
            filewcs = i['filewcs']
            if len(filewcs) == 0:
                print 'No files to run wc on'
            else:
                print '<table class="wc"><tr><th>File</th><th>Lines</th><th>Words</th><th>Bytes</th></tr>'
                for filewc in filewcs:
                    print '<tr><td>%s</td>' % filewc['name']
                    print '<td>'
                    if filewc.has_key('lines'):
                        print filewc['lines']
                    print '</td><td>'
                    if filewc.has_key('words'):
                        print filewc['words']
                    print '</td><td>'
                    if filewc.has_key('bytes'):
                        print filewc['bytes']
                    print '</td></tr>'
                print '</table>'
        elif i['object_type'] == 'file_not_found':

            print 'File %s was <B>not</B> found!' % i['name']
        elif i['object_type'] == 'file_output':
            if i.has_key('path'):
                print 'File: %s<br>' % i['path']
            print '<br>'.join(i['lines']) + '<br>'
        elif i['object_type'] == 'list':
            print '<ul>'
            for list_item in i['list']:
                print ('<li>%s</li>' % list_item).replace('\n', '<br>')
            print '</ul>'
        elif i['object_type'] == 'linklist':
            links = i['links']
            if len(links) == 0:
                print 'No links found!'
            else:
                print '<table class="links"><th>Name</th><th>Link</th></tr>'
                for link in links:
                    print '<tr><td>%s</td><td>%s</td></tr>'\
                         % (link['text'], html_link(link))
                print '</table>'
        elif i['object_type'] == 'multilinkline':
            links = i['links']
            if len(links) == 0:
                print 'No links found!'
            else:
                print ' / '.join([html_link(link) for link in links])
        elif i['object_type'] == 'file':
            print i['name']
        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                print 'No job submit status found!'
            else:
                print '<table class="submitstatus"><th>File</th><th>Status</th><th>Job Id</th><th>Message</th></tr>'
                for submitstatus in submitstatuslist:
                    print '<tr>%s</tr>'\
                         % html_table_if_have_keys(submitstatus, ['name'
                            , 'status', 'job_id', 'message'])
                print '</table>'
        elif i['object_type'] == 'objects':
            objects = i['objects']
            if len(objects) == 0:
                print 'No objects found!'
            else:
                print '<table class="objects"><th>Object</th><th>Info</th></tr>'
                for (name, val) in objects:
                    print '<tr><td>%s</td><td>%s</td></tr>' % (name,
                            val)
                print '</table>'
        elif i['object_type'] == 'sandboxinfos':
            sandboxinfos = i['sandboxinfos']
            if len(sandboxinfos) == 0:
                print 'No sandboxes found!'
            else:
                print '<table class="sandboxinfo"><th>Username</th><th>Resource</th><th>Jobs</th></tr>'
                for sandboxinfo in sandboxinfos:
                    print '<tr>%s</tr>'\
                         % html_table_if_have_keys(sandboxinfo,
                            ['username', 'resource', 'jobs'])
                print '</table>'
        elif i['object_type'] == 'runtimeenvironments':
            runtimeenvironments = i['runtimeenvironments']
            if len(runtimeenvironments) == 0:
                print 'No runtime environments found!'
            else:
                print '<table class="runtimeenvs"><th>Name</th><th>Description</th><th>Details</th><th>Creator</th></tr>'
                for single_re in runtimeenvironments:
                    print '<tr><td>%s</td><td>%s</td><td><a href=showre.py?re_name=%s>View</a></td><td>%s</td></tr>'\
                         % (single_re['name'], single_re['description'
                            ], single_re['name'], single_re['creator'])
                print '</table>'
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

            print '<table class="runtimeenvdetails">'
            print '<tr><td>Name</td><td>%s</td></tr>' % i['name']
            print '<tr><td>Description</td><td>%s</td></tr>'\
                 % i['description']
            print '<tr><td>Creator</td><td>%s</td></tr>' % i['creator']
            print '<tr><td>Created</td><td>%s</td></tr>' % i['created']
            print '<tr><td>Job count</td><td>%s</td></tr>'\
                 % i['job_count']
            print '<tr><td>Resource count</td><td>%s</td></tr>'\
                 % i['resource_count']
            print '<tr><td>Needed software</td><td>%s</td></tr>'\
                 % software_html
            print "<tr><td>Testprocedure</td><td valign='top'>%s</td></tr>"\
                 % i['testprocedure']
            print "<tr><td>Verifystdout</td><td valign='top'>%s</td></tr>"\
                 % i['verifystdout']
            print "<tr><td>Verifystderr</td><td valign='top'>%s</td></tr>"\
                 % i['verifystderr']
            print "<tr><td>Verifystatus</td><td valign='top'>%s</td></tr>"\
                 % i['verifystatus']
            print '<tr><td>Environments</td><td>%s</td></tr>'\
                 % environment_html
            print '</table>'
        elif i['object_type'] == 'vgrid_list':
            if len(i['vgrids']) > 0:
                vgrids = i['vgrids']
                print "<table class='vgrids'>"
                print '<tr class="title"><td>Name</td><td>Actions</td><td class=centertext colspan=2>Private page</td><td class=centertext colspan=2>Public page</td><td class=centertext colspan=2>Wiki</td><td class=centertext colspan=2>Monitor</td></tr>'
                for obj in vgrids:
                    print '<tr>'
                    print '<td>%s</td>' % obj['name']
                    print '<td>'
                    if obj.has_key('administratelink'):
                        print '%s' % html_link(obj['administratelink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('editprivatelink'):
                        print '%s ' % html_link(obj['editprivatelink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('enterprivatelink'):
                        print '%s ' % html_link(obj['enterprivatelink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('editpubliclink'):
                        print '%s ' % html_link(obj['editpubliclink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('enterpubliclink'):
                        print '%s ' % html_link(obj['enterpubliclink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('privatewikilink'):
                        print '%s ' % html_link(obj['privatewikilink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('publicwikilink'):
                        print '%s ' % html_link(obj['publicwikilink'])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('privatemonitorlink'):
                        print '%s ' % html_link(obj['privatemonitorlink'
                                ])
                    else:
                        print '-----'
                    print '</td>'
                    print '<td class=centertext>'
                    if obj.has_key('publicmonitorlink'):
                        print '%s ' % html_link(obj['publicmonitorlink'
                                ])
                    else:
                        print '-----'
                    print '</td>'
                    print '</tr>'
                print '</table>'
            else:
                print 'No matching VGrids found'
        else:
            print 'unknown object %s' % i
    footer = """</div>
    <div id="exitcode">
Exit code: %s Description: %s<br>
    </div>
<br>    
""" % (ret_val, ret_msg)

    print get_cgi_html_footer(footer)
    return True


# def xml_format(ret_val, ret_msg, out_obj):
#    """Generate output in xml format"""
#
#    print "xml format not implemented yet"
#    return True


def soap_format(ret_val, ret_msg, out_obj):
    """Generate output in soap format"""

    try:
        import SOAPpy
        print SOAPpy.buildSOAP(out_obj)
    except Exception, exc:
        print 'SOAPpy not available on server! Defaulting to .txt output. (%s)'\
             % exc
        txt_format(ret_val, ret_msg, out_obj)

    return True


def pickle_helper(
    ret_val,
    ret_msg,
    out_obj,
    protocol=None,
    ):
    """Shared helper to generate output in pickle"""

    print pickle.dumps(out_obj, protocol)
    return True


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
        print yaml.dump(out_obj)
    except Exception, exc:
        print 'yaml not available on server! Defaulting to .txt output. (%s)'\
             % exc
        txt_format(ret_val, ret_msg, out_obj)
    return True


def xmlrpc_format(ret_val, ret_msg, out_obj):
    """Generate output in xmlrpc format"""

    try:
        import xmlrpclib
        print xmlrpclib.dumps((out_obj, ), allow_none=True)
    except Exception, exc:
        print 'xmlrpclib not available on server! Defaulting to .txt output. (%s)'\
             % exc
        txt_format(ret_val, ret_msg, out_obj)
    return True


def json_format(ret_val, ret_msg, out_obj):
    """Generate output in json format"""

    try:
        import json
        try:
            # python >=2.6 includes native json module with loads/dumps methods 
            print json.dumps(out_obj)
        except AttributeError:
            # python <2.6 + python-json module with read/write methods
            print json.write(out_obj)
    except Exception, exc:
        print 'json not available on server! Defaulting to .txt output. (%s)'\
             % exc
        txt_format(ret_val, ret_msg, out_obj)
    return True


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


def do_output(
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
    if not outputformat in outputformats:
        return txt_format(ret_val, ret_msg, out_obj)

    return eval('%s_format(ret_val, ret_msg, out_obj)' % outputformat)


