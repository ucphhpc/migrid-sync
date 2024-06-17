#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# output - general formatting of backend output objects
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Helper functions to generate output in format specified by the client"""

from __future__ import absolute_import

import os
import sys
import time
import traceback

from mig.shared import returnvalues
from mig.shared.bailout import bailout_title, crash_helper, \
    filter_output_objects
from mig.shared.base import hexlify
from mig.shared.defaults import file_dest_sep, keyword_any, keyword_updating
from mig.shared.htmlgen import get_xgi_html_header, get_xgi_html_footer, \
    vgrid_items, html_post_helper, tablesorter_pager
from mig.shared.objecttypes import validate
from mig.shared.prettyprinttable import pprint_table
from mig.shared.pwcrypto import sorted_hash_algos
from mig.shared.safeinput import html_escape


row_name = ('even', 'odd')
_valid_output_formats = ['txt', 'html', 'soap', 'pickle', 'pickle1', 'pickle2',
                         'yaml', 'xmlrpc', 'resource', 'json', 'file']


def reject_main(client_id, user_arguments_dict):
    """A simple main-function to use if functionality backend is disabled"""
    output_objs = [bailout_title(None, 'Access Error'),
                   {'object_type': 'header', 'text': 'Access Error'},
                   {'object_type': 'error_text', 'text':
                    "This backend is disabled by site configuration!"}]
    return (output_objs, returnvalues.CLIENT_ERROR)


def dummy_main(client_id, user_arguments_dict):
    """Dummy main-function to override with backend import"""
    output_objs = [bailout_title(None, 'Internal Error'),
                   {'object_type': 'header', 'text': 'Internal Error'},
                   {'object_type': 'error_text', 'text':
                    "This backend should always be overriden!"}]
    return (output_objs, returnvalues.SYSTEM_ERROR)


def filter_exc(configuration, exc):
    """Helper to strip any private file system details from exception"""
    _logger = configuration.logger
    filtered = '%s' % exc
    for prefix in (configuration.user_home,
                   configuration.user_pending,
                   configuration.user_cache,
                   configuration.user_messages,
                   configuration.user_settings,
                   configuration.mrsl_files_dir,
                   configuration.gridstat_files_dir,
                   configuration.vgrid_files_home,
                   configuration.vgrid_files_writable,
                   configuration.vgrid_files_readonly,
                   configuration.vgrid_public_base,
                   configuration.vgrid_private_base,
                   configuration.vgrid_home,
                   configuration.re_files_dir,
                   configuration.re_pending_dir,
                   configuration.re_home,
                   configuration.log_dir,
                   configuration.mig_server_home,
                   configuration.resource_pending,
                   configuration.resource_home,
                   configuration.webserver_home,
                   configuration.user_db_home,
                   configuration.sss_home,
                   configuration.sandbox_home,
                   configuration.freeze_home,
                   configuration.freeze_tape,
                   configuration.sharelink_home,
                   configuration.twofactor_home,
                   configuration.gdp_home,
                   configuration.workflows_home,
                   configuration.workflows_db_home,
                   configuration.notify_home,
                   # Fallbacks
                   configuration.state_path,
                   configuration.mig_path,
                   configuration.certs_path,
                   ):
        if prefix and prefix in filtered:
            _logger.debug("strip %s from %s" % (prefix, filtered))
            filtered = filtered.replace(prefix, '')
    return filtered


def txt_table_if_have_keys(header, input_dict, keywordlist):
    """create txt table contents based on keys in a dictionary"""

    table = header
    for dictionary in input_dict:
        this_status_list = []
        for key in keywordlist:
            if key in dictionary:
                this_status_list.append(dictionary[key])
            else:
                this_status_list.append('')
        table.append(this_status_list)
    return table


def txt_link(obj):
    """Text format link"""

    return '(Link: __%s__) -> __%s__' % (obj['destination'], obj['text'])


def txt_cond_summary(job_cond_msg):
    """Pretty format job feasibilty condition"""
    lines = []
    if not job_cond_msg:
        lines.append('No job_cond message.')
    else:
        lines.append('Job Id: %s' % job_cond_msg['job_id'])
        if 'suggestion' in job_cond_msg:
            lines.append('%s' % job_cond_msg['suggestion'])
        if 'verdict' in job_cond_msg:
            lines.append('%s %s' % ('Job readiness condition',
                                    job_cond_msg['color']))
            lines.append(job_cond_msg['verdict'])
        if 'error_desc' in job_cond_msg:
            for (mrsl_attrib, desc) in job_cond_msg['error_desc'].items():
                lines.append('%s' % mrsl_attrib)
                if desc.find('[') != -1 or desc.find(']') != -1:
                    desc = desc.replace('[', '').replace(']', '')
                if desc.find("'") != -1:
                    desc = desc.replace("'", "")
                if desc.find(', ') != -1:
                    for item in desc.split(', '):
                        lines.append('%s' % item)
                else:
                    lines.append('%s' % desc)
    return '\n'.join(lines)


def txt_file_info(file_dict):
    """Format a dir_listing file_info dictionary for ls output"""
    modified_time = "%(modified)s" % file_dict
    date_string = time.ctime(float(modified_time))
    date_pad = date_string.rjust(32)
    size = "%(size)s" % file_dict
    size_pad = size.rjust(16)
    file_details = "%s %s" % (size_pad, date_pad)
    return file_details


def txt_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in txt format"""

    lines = []
    binary_output = False
    timing_info = 'no timing information'
    status_line = 'Exit code: %s Description %s (TIMING_INFO)\n' % (ret_val,
                                                                    ret_msg)

    for i in out_obj:
        if i['object_type'] == 'error_text':
            msg = "%(text)s" % i
            if i.get('exc', False):
                msg += filter_exc(configuration, ': %(exc)s' % i)
            lines.append('** %s **\n' % msg)
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
            binary_output = True
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
        elif i['object_type'] == 'progress_list':
            progress_list = i['progress_list']
            header = [['Path', 'Size', 'Total Size', 'Percent', 'Completed']]
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         progress_list,
                                                         ['path', 'cur_size',
                                                          'total_size',
                                                          'percent', 'done']))

        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                lines.append('No job submit status found!\n')
            else:
                header = [['File', 'Status', 'Job ID', 'Message']]
                lines += pprint_table(txt_table_if_have_keys(
                    header, submitstatuslist, ['name', 'status', 'job_id',
                                               'message']))
        elif i['object_type'] == 'frozenarchives':
            frozenarchives = i['frozenarchives']
            header = [['ID', 'Name', 'Created', 'Flavor', 'Files']]
            mangle_fields = ['created']
            content_keys = ['id', 'name', 'created_mangled', 'flavor',
                            'frozenfiles']
            for single_archive in frozenarchives:
                for key in mangle_fields:
                    val = single_archive[key]
                    key = "%s_mangled" % key
                    if key.startswith('created_'):
                        marker = '</div>'
                        val = val[val.find(marker) + len(marker):]
                    else:
                        val = ','.join(val)
                    single_archive[key] = val
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         frozenarchives,
                                                         content_keys))
        elif i['object_type'] == 'frozenarchive':
            frozenarchive = i
            frozenfiles = frozenarchive['frozenfiles']
            header = [['Name', 'Date', 'Size in bytes', 'MD5 checksum']]
            content_keys = ['name', 'date', 'size', 'md5sum']
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         frozenfiles,
                                                         content_keys))

            flavor = i.get('flavor', 'freeze')
            lines.append('\nArchive details\n')
            lines.append('ID: %(id)s\n' % frozenarchive)
            if flavor in ('freeze', 'backup'):
                lines.append('Name: %(name)s\n' % frozenarchive)
            elif flavor == 'phd':
                lines.append('Title: %(name)s\n' % frozenarchive)
            lines.append('Flavor: %(flavor)s\n' % frozenarchive)
            if flavor in ('freeze', 'phd'):
                if i.get('author', '') not in ('', 'UNSET'):
                    lines.append('Author: %(author)s\n' % frozenarchive)
                if i.get('department', '') not in ('', 'UNSET'):
                    lines.append('Department: %(department)s\n' %
                                 frozenarchive)
                if i.get('organization', '') not in ('', 'UNSET'):
                    lines.append('Organization: %(organization)s\n' %
                                 frozenarchive)
                lines.append('Description: %(description)s\n' % frozenarchive)
                if i.get('publish', False):
                    published = 'Yes'
                    publish_url = i.get('publish_url', '')
                    published += ' (<a href="%s">%s</a>)' % (publish_url,
                                                             publish_url)
                else:
                    published = 'No'
                lines.append('Published: %s\n' % published)
            lines.append('Creator: %(creator)s\n' % frozenarchive)
            marker = '</div>'
            val = frozenarchive['created']
            val = val[val.find(marker) + len(marker):]
            lines.append('Created: %s\n' % val)
            for (location, store_date) in i.get('location', []):
                lines.append('On %s: %s\n' % (location, store_date))
        elif i['object_type'] == 'freezestatus':
            # We only use this element for scripted archive creation
            pass
        elif i['object_type'] == 'datatransfers':
            datatransferslist = i['datatransfers']
            header = [['ID', 'Action', 'Protocol', 'Host', 'Port', 'Login',
                       'Source(s)', 'Destination', 'Created', 'Status']]
            mangle_fields = ['created', 'src']
            content_keys = ['transfer_id', 'action', 'protocol', 'fqdn',
                            'port', 'username', 'src_mangled', 'dst',
                            'created_mangled', 'status']
            for single_transfer in datatransferslist:
                for key in mangle_fields:
                    val = single_transfer[key]
                    key = "%s_mangled" % key
                    if key.startswith('created_'):
                        marker = '</div>'
                        val = val[val.find(marker) + len(marker):]
                    else:
                        val = ','.join(val)
                    single_transfer[key] = val
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         datatransferslist,
                                                         content_keys))
        elif i['object_type'] == 'transferkeys':
            transferkeyslist = i['transferkeys']
            header = [['ID', 'Created', 'Type', 'Bits', 'Public Key']]
            mangle_fields = ['created']
            content_keys = ['key_id', 'created_mangled', 'type', 'bits',
                            'public_key']
            for single_key in transferkeyslist:
                for key in mangle_fields:
                    val = single_key[key]
                    key = "%s_mangled" % key
                    if key.startswith('created_'):
                        marker = '</div>'
                        val = val[val.find(marker) + len(marker):]
                    else:
                        val = ','.join(val)
                    single_key[key] = val
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         transferkeyslist,
                                                         content_keys))
        elif i['object_type'] == 'sharelinks':
            sharelinkslist = i['sharelinks']
            skip_list = i.get('skip_list', [])
            header = [['ID', 'Path']]
            optional_cols = [('access', 'Access'), ('created', 'Created'),
                             ('active', 'Active'), ('owner', 'Owner'),
                             ('invites', 'Invites'),  ('expire', 'Expire'),
                             ('single_file', 'Single file'),
                             ]
            content_keys = ['share_id', 'path']
            mangle_fields = ['access', 'created', 'invites']
            for (key, title) in optional_cols:
                if not key in skip_list:
                    header[0].append(title)
                    # Some fields need mangling for text print
                    if key in mangle_fields:
                        key = "%s_mangled" % key
                    content_keys.append(key)
            for single_share in sharelinkslist:
                for key in mangle_fields:
                    val = single_share[key]
                    key = "%s_mangled" % key
                    if key.startswith('created_'):
                        marker = '</div>'
                        val = val[val.find(marker) + len(marker):]
                    else:
                        val = ','.join(val)
                    single_share[key] = val
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         sharelinkslist,
                                                         content_keys))
        elif i['object_type'] == 'upgrade_info':
            lines.append('%s\n' % i['text'])
            for cmd in i['commands']:
                lines.append('%s\n' % cmd)
        elif i['object_type'] == 'uploadfiles':
            fileslist = i['files']
            header = [['Name', 'Size', 'URL']]
            content_keys = ['name', 'size', 'url']
            lines += pprint_table(txt_table_if_have_keys(header,
                                                         fileslist,
                                                         content_keys))
        elif i['object_type'] == 'table_pager':
            continue
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            header = [['Job ID', 'Resubmit status', 'New job ID',
                       'Message']]
            lines += pprint_table(txt_table_if_have_keys(
                header, resubmitobjs, ['job_id', 'status', 'new_job_id',
                                       'message']))
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            header = [['Job ID', 'Old status', 'New status',
                       'Message']]
            lines += pprint_table(txt_table_if_have_keys(
                header, changedstatusjobs, ['job_id', 'oldstatus', 'newstatus',
                                            'message']))
        elif i['object_type'] == 'saveschedulejobs':
            saveschedulejobs = i['saveschedulejobs']
            if len(saveschedulejobs) == 0:
                continue
            header = [['Job ID', 'Message']]
            lines += pprint_table(txt_table_if_have_keys(
                header, saveschedulejobs, ['job_id', 'message']))
        elif i['object_type'] == 'checkcondjobs':
            checkcondjobs = i['checkcondjobs']
            if len(checkcondjobs) == 0:
                continue
            header = [['Job ID', 'Feasibility', 'Message']]
            for checkcond in checkcondjobs:
                checkcond['cond_summary'] = txt_cond_summary(checkcond)
            lines += pprint_table(txt_table_if_have_keys(
                header, checkcondjobs, ['job_id', 'cond_summary', 'message']))
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
                    if 'execute' in obj:
                        lines.append('Execute: %(execute)s\n' % obj)
                    if 'verified' in obj:
                        lines.append('Verified status: %(verified)s\n'
                                     % obj)
                    if 'verified_timestamp' in obj:
                        lines.append('Verified: %(verified_timestamp)s\n'
                                     % obj)
                    if 'received_timestamp' in obj:
                        lines.append('Received: %(received_timestamp)s\n'
                                     % obj)
                    if 'queued_timestamp' in obj:
                        lines.append('Queued: %(queued_timestamp)s\n'
                                     % obj)
                    if 'schedule_timestamp' in obj:
                        lines.append('Scheduled: %(schedule_timestamp)s\n'
                                     % obj)
                    if 'schedule_hint' in obj:
                        lines.append('Schedule hint: %(schedule_hint)s\n'
                                     % obj)
                    if 'schedule_hits' in obj:
                        lines.append('Suitable resources: %(schedule_hits)s\n'
                                     % obj)
                    if 'expected_delay' in obj:
                        lines.append('Expected delay: %(expected_delay)s\n'
                                     % obj)
                    if 'executing_timestamp' in obj:
                        lines.append('Executing: %(executing_timestamp)s\n'
                                     % obj)
                    if 'resource' in obj:
                        lines.append('Resource: %(resource)s\n'
                                     % obj)
                    if 'vgrid' in obj:
                        lines.append('%s: %s'
                                     % (configuration.site_vgrid_label, obj['vgrid']))
                    if 'finished_timestamp' in obj:
                        lines.append('Finished: %(finished_timestamp)s\n'
                                     % obj)
                    if 'failed_timestamp' in obj:
                        lines.append('Failed: %(failed_timestamp)s\n'
                                     % obj)
                    if 'canceled_timestamp' in obj:
                        lines.append('Canceled: %(canceled_timestamp)s\n'
                                     % obj)
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        lines.append('Execution history</td><td>#%s</td></tr>'
                                     % count)
                        if 'queued' in single_history:
                            lines.append('Queued %s: %s\n' % (count,
                                                              single_history['queued']))
                        if 'executing' in single_history:
                            lines.append('Executing %s: %s\n' % (count,
                                                                 single_history['executing']))
                        if 'resource' in single_history:
                            lines.append('Resource %s: %s\n' % (count,
                                                                single_history['resource']))
                        if 'vgrid' in single_history:
                            lines.append('%s %s: %s' %
                                         (configuration.site_vgrid_label,
                                          count, single_history['vgrid']))
                        if 'failed' in single_history:
                            lines.append('Failed %s: %s\n' % (count,
                                                              single_history['failed']))
                        if 'failed_message' in single_history:
                            lines.append('Failed message %s: %s\n'
                                         % (count,
                                            single_history['failed_message']))

                    # add newline before next job)

                    lines.append('\n')
        elif i['object_type'] == 'filewcs':
            filewcs = i['filewcs']
            if len(filewcs) == 0:
                lines.append('No files to run wc on\n')
            else:
                for filewc in filewcs:
                    out = ''
                    if 'name' in filewc:
                        out += '%s\t' % filewc['name']
                    out += '\t'
                    if 'lines' in filewc:
                        out += '%s' % filewc['lines']
                    out += '\t'
                    if 'words' in filewc:
                        out += '%s' % filewc['words']
                    out += '\t'
                    if 'bytes' in filewc:
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
                        if 'long_format' in directory:
                            if directory == dir_listing['entries'][0]:
                                lines.append('%s:\ntotal %s\n'
                                             % (dir_listing['relative_path'],
                                                len(dir_listing['entries'])))
                        if 'actual_dir' in directory:
                            line += '%s ' % directory['actual_dir']
                        line += '%s\n' % directory['name']
                        lines.append(line)
                    elif 'file' == entry['type']:
                        this_file = entry
                        if 'long_format' in this_file:
                            line += '%s ' % this_file['long_format']
                        line += '%s' % this_file['name']
                        if 'file_dest' in this_file:
                            line += '%s%s' % (file_dest_sep,
                                              this_file['file_dest'])
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
            if 'path' in i:
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
        elif i['object_type'] == 'image_settings_list' or \
                i['object_type'] == 'image_setting' or \
                i['object_type'] == 'image_meta' or \
                i['object_type'] == 'volume_meta':
            for elm in i:
                lines.append('%s: %s\n' % (elm, i[elm]))
        elif i['object_type'] == 'script_status':
            status_line = i.get('text')
        elif i['object_type'] == 'timing_info':
            timing_info = i.get('text')
        elif i['object_type'] == 'end':
            pass
        elif i['object_type'] == 'wsgi':
            pass
        else:
            lines.append('unknown object %s\n' % i)

    if status_line:
        status_line = status_line.replace('TIMING_INFO', timing_info)
        lines = [status_line] + lines

    # NOTE: careful handling required for binary on python3+
    if sys.version_info[0] > 2 and binary_output:
        return b''.join(lines)
    else:
        return ''.join(lines)


def html_link(obj):
    """html format link"""

    extra_fields = ['id', 'class', 'title', 'target']
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
        lines.append('<tr><th>Job Id: %s</th></tr>' %
                     job_cond_msg['job_id'])
        if 'suggestion' in job_cond_msg:
            lines.append('<tr><td>%s</td></tr>' %
                         job_cond_msg['suggestion'])
        if 'verdict' in job_cond_msg:
            img_tag = '<img src="%s" alt="%s %s" />' % \
                      (job_cond_msg['icon'], 'Job readiness condition',
                       job_cond_msg['color'])
            lines.append('<tr><td>%s&nbsp;%s</td></tr>' %
                         (img_tag, job_cond_msg['verdict']))
        if 'error_desc' in job_cond_msg:
            lines.append('<tr><td><dl>')
            for (mrsl_attrib, desc) in job_cond_msg['error_desc'].items():
                lines.append('<dt>%s</dt>' % mrsl_attrib)
                if desc.find('[') != -1 or desc.find(']') != -1:
                    desc = desc.replace('[', '').replace(']', '')
                if desc.find("'") != -1:
                    desc = desc.replace("'", "")
                if desc.find(', ') != -1:
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
        if key in dictionary:
            outputstring += '<td>%s</td>' % dictionary[key]
        else:
            outputstring += '<td></td>'
    return outputstring


def html_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in html format"""

    lines = []
    binary_output = False
    user_settings = {}
    include_widgets = True
    user_widgets = {}
    timing_info = 'no timing information'
    status_line = \
        """
    <div id='exitcode'>
    <span class='spacer'></span>
    Exit code: %s Description: %s (TIMING_INFO)
    <span class='spacer'></span>
    </div>
""" % (ret_val, ret_msg)
    for i in out_obj:
        if i['object_type'] == 'start':
            pass
        elif i['object_type'] == 'error_text':
            msg = "%(text)s" % i
            if i.get('exc', False):
                msg += filter_exc(configuration, ': %(exc)s' % i)
            lines.append('<p class="errortext">%s</p>' % html_escape(msg))
        elif i['object_type'] == 'warning':
            lines.append('<p class="warningtext">%s</p>' %
                         html_escape(i['text']))
        elif i['object_type'] == 'header':
            lines.append('<h1 class="header %s">%s</h1>' % (i.get('class', ''),
                                                            html_escape(i['text'])))
        elif i['object_type'] == 'sectionheader':
            lines.append('<h3 class="sectionheader %s">%s</h3>' %
                         (i.get('class', ''), html_escape(i['text'])))
        elif i['object_type'] == 'title':
            meta = i.get('meta', '')
            backend = i.get('backend', '')
            style_entry = i.get('style', '')
            style_helpers = {'base': '', 'advanced': '', 'page': '',
                             'skin': ''}
            if isinstance(style_entry, dict):
                style_helpers.update(style_entry)
            else:
                style_helpers['base'] += style_entry
            script_entry = i.get('script', '')
            script_helpers = {'base': '', 'advanced': '', 'skin': '',
                              'page': '', 'init': '', 'ready': '', 'body': ''}
            if isinstance(script_entry, dict):
                script_helpers.update(script_entry)
            else:
                script_helpers['base'] += script_entry

            include_frame = not i.get('skipframe', False)
            include_menu = not i.get('skipmenu', False)
            include_widgets = not i.get('skipwidgets',
                                        not configuration.site_enable_widgets)
            include_userstyle = not i.get('skipuserstyle',
                                          not configuration.site_enable_styling)
            base_menu = i.get('base_menu', configuration.site_default_menu)
            user_menu = i.get('user_menu', [])
            user_settings = i.get('user_settings', {})
            user_widgets = i.get('user_widgets', {})
            user_profile = i.get('user_profile', {})
            # NOTE: record backend as general information and user script helper
            if backend:
                # IMPORTANT: keep any changes here in sync with publicscriptgen
                meta += '''<meta name="generator" content="%s">
''' % backend

            if configuration.site_enable_openid:
                oid_url = os.path.join(configuration.migserver_https_sid_url,
                                       'cgi-sid', 'oiddiscover.py')
                meta += '''
<!-- advertise any valid OpenID entry points in line with spec -->
<meta http-equiv="X-XRDS-Location" content="%s" />
''' % oid_url

            lines.append(get_xgi_html_header(
                configuration, html_escape(i['text']),
                '',
                True,
                meta,
                style_helpers,
                script_helpers,
                include_frame,
                include_menu,
                include_widgets,
                include_userstyle,
                base_menu,
                user_menu,
                user_settings,
                user_widgets,
                user_profile,
            ))
            # TODO: move inside get_xgi_html_header?
            # Global container introduced with UI V3
            # the optional container_class is used to switch to full width
            lines.append('''
<!-- Begin UI container -->
<div class="container page-content %s">
''' % i.get('container_class', ''))
        elif i['object_type'] == 'text':
            lines.append('<p>%s</p>' % html_escape(i['text']))
        elif i['object_type'] == 'verbatim':
            lines.append('%s' % html_escape(i['text']))
        elif i['object_type'] == 'binary':
            binary_output = True
            lines.append(i['data'])
        elif i['object_type'] == 'link':
            lines.append(html_link(i))
        elif i['object_type'] == 'job_list':
            if len(i['jobs']) > 0:
                jobs = i['jobs']
                lines.append('''
<div class="table-responsive">
<table class="jobs">
''')
                for obj in jobs:
                    lines.append('<tr><th>Job Id</th><th>%s</th></tr>'
                                 % obj['job_id'])
                    lines.append('<tr><td>Status</td><td>%s</td></tr>'
                                 % obj['status'])
                    if 'execute' in obj:
                        lines.append('<tr><td>Execute</td><td>%s</td></tr>'
                                     % obj['execute'])
                    if 'verified' in obj:
                        lines.append('<tr><td>Verified status</td>'
                                     '<td>%s</td></tr>' % obj['verified'])
                    if 'verified_timestamp' in obj:
                        lines.append('<tr><td>Verified</td><td>%s</td></tr>'
                                     % obj['verified_timestamp'])
                    if 'received_timestamp' in obj:
                        lines.append('<tr><td>Received</td><td>%s</td></tr>'
                                     % obj['received_timestamp'])
                    if 'queued_timestamp' in obj:
                        lines.append('<tr><td>Queued</td><td>%s</td></tr>'
                                     % obj['queued_timestamp'])
                    if 'schedule_timestamp' in obj:
                        lines.append('<tr><td>Scheduled</td><td>%s</td></tr>'
                                     % obj['schedule_timestamp'])
                    if 'schedule_hint' in obj:
                        lines.append('<tr><td>Schedule result</td>'
                                     '<td>%s</td></tr>' % obj['schedule_hint'])
                    if 'schedule_hits' in obj:
                        lines.append('<tr><td>Suitable resources</td>'
                                     '<td>%s</td></tr>' % obj['schedule_hits'])
                    if 'expected_delay' in obj:
                        lines.append(
                            '<tr><td>Expected delay</td><td>%s</td></tr>' %
                            obj['expected_delay'])
                    if 'executing_timestamp' in obj:
                        lines.append('<tr><td>Executing</td><td>%s</td></tr>'
                                     % obj['executing_timestamp'])
                    if 'resource' in obj:
                        lines.append('<tr><td>Resource</td><td>%s</td></tr>'
                                     % obj['resource'])
                    if 'vgrid' in obj:
                        lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                     % (configuration.site_vgrid_label,
                                        obj['vgrid']))
                    if 'finished_timestamp' in obj:
                        lines.append('<tr><td>Finished</td><td>%s</td></tr>'
                                     % obj['finished_timestamp'])
                    if 'failed_timestamp' in obj:
                        lines.append('<tr><td>Failed</td><td>%s</td></tr>'
                                     % obj['failed_timestamp'])
                    if 'canceled_timestamp' in obj:
                        lines.append('<tr><td>Canceled</td><td>%s</td></tr>'
                                     % obj['canceled_timestamp'])
                    for execution_history in obj['execution_histories']:
                        count = execution_history['count']
                        single_history = \
                            execution_history['execution_history']
                        lines.append('<tr><td>Execution history</td>'
                                     '<td>#%s</td></tr>' % count)
                        if 'queued' in single_history:
                            lines.append(
                                '<tr><td>Queued %s</td><td>%s</td></tr>'
                                % (count, single_history['queued']))
                        if 'executing' in single_history:
                            lines.append(
                                '<tr><td>Executing %s</td><td>%s</td></tr>'
                                % (count, single_history['executing']))
                        if 'resource' in single_history:
                            lines.append(
                                '<tr><td>Resource %s</td><td>%s</td></tr>'
                                % (count, single_history['resource']))
                        if 'vgrid' in single_history:
                            lines.append(
                                '<tr><td>%s %s</td><td>%s</td></tr>'
                                % (configuration.site_vgrid_label, count,
                                   single_history['vgrid']))
                        if 'failed' in single_history:
                            lines.append(
                                '<tr><td>Failed %s</td><td>%s</td></tr>'
                                % (count, single_history['failed']))
                        if 'failed_message' in single_history:
                            lines.append(
                                '<tr>'
                                '<td>Failed message %s</td><td>%s</td></tr>'
                                % (count, single_history['failed_message']))

                    if 'statuslink' in obj:
                        lines.append('<tr><td>Links</td><td>')
                        lines.append('%s<br />' % html_link(obj['statuslink'
                                                                ]))
                        lines.append('%s<br />' % html_link(obj['mrsllink']))
                        lines.append('%s<br />' % html_link(obj['resubmitlink'
                                                                ]))
                        lines.append('%s<br />' % html_link(obj['freezelink']))
                        lines.append('%s<br />' % html_link(obj['thawlink']))
                        lines.append('%s<br />' % html_link(obj['cancellink'
                                                                ]))
                        lines.append('%s<br />'
                                     % html_link(obj['jobschedulelink']))
                        lines.append('%s<br />'
                                     % html_link(obj['jobfeasiblelink']))
                        lines.append('%s<br />'
                                     % html_link(obj['liveiolink']))
                    if 'outputfileslink' in obj:
                        lines.append('<br />%s'
                                     % html_link(obj['outputfileslink']))
                    lines.append('<tr><td colspan=2><br /></td></tr>')

                lines.append('''
</table>
</div>
''')
        elif i['object_type'] == 'trigger_job_list':
            jobs = i['trigger_jobs']
            lines.append('''
<table id="workflowstable" class="jobs columnsort">
    <thead>
        <tr>
            <th>Job ID</th>
            <th>Rule</th>
            <th>Path</th>
            <th>Change</th>
            <th>Time</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
''')

            for obj in jobs:
                lines.append('''<tr>
    <td>%(job_id)s</td><td>%(rule_id)s</td><td>%(path)s</td><td>%(action)s</td>
    <td>%(time)s</td></td><td>%(status)s</td>
</tr>''' % obj)
            lines.append('''
    </tbody>
</table>
''')
        elif i['object_type'] in ('trigger_log', 'crontab_log'):
            log_content = i['log_content']
            lines.append('''
 <div class="form_container">
 <textarea id="logarea" rows=20 readonly="readonly">%s</textarea>
 </div>
''' % log_content)
        elif i['object_type'] == 'resubmitobjs':
            resubmitobjs = i['resubmitobjs']
            if len(resubmitobjs) == 0:
                continue
            lines.append("<table class='resubmit'><tr><th>Job ID</th>"
                         "<th>Resubmit status</th><th>New job ID</th>"
                         "<th>Message</th></tr>")
            for resubmitobj in resubmitobjs:
                lines.append('<tr>%s</tr>'
                             % html_table_if_have_keys(
                                 resubmitobj,
                                 ['job_id', 'status', 'new_job_id',
                                  'message']))
            lines.append('</table>')
        elif i['object_type'] == 'changedstatusjobs':
            changedstatusjobs = i['changedstatusjobs']
            if len(changedstatusjobs) == 0:
                continue
            lines.append("<table class='changedstatusjobs'><tr><th>Job ID</th>"
                         "<th>Old status</th><th>New status</th>"
                         "<th>Message</th></tr>")
            for changedstatus in changedstatusjobs:
                lines.append('<tr>%s</tr>'
                             % html_table_if_have_keys(
                                 changedstatus, ['job_id', 'oldstatus',
                                                 'newstatus', 'message']))
            lines.append('</table>')
        elif i['object_type'] == 'saveschedulejobs':
            saveschedulejobs = i['saveschedulejobs']
            if len(saveschedulejobs) == 0:
                continue
            lines.append("<table class='saveschedulejobs'><tr><th>Job ID</th>"
                         "<th>Message</th></tr>")
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
            lines.append("<table class='checkcondjobs'><tr><th>Job ID</th>"
                         "<th>Feasibility</th><th>Message</th></tr>")
            for checkcond in checkcondjobs:
                checkcond['cond_summary'] = html_cond_summary(checkcond)
                lines.append('<tr>%s</tr>' % html_table_if_have_keys(
                    checkcond, ['job_id', 'cond_summary', 'message']))
            lines.append('</table>')
        elif i['object_type'] == 'stats':
            stats = i['stats']
            if len(stats) == 0:
                continue
            lines.append("<table class='stats'><tr><th>Filename</th>"
                         "<th>Device</th><th>Inode</th><th>Mode</th>"
                         "<th>Nlink</th><th>User ID</th><th>Group ID</th>"
                         "<th>RDEV</th><th>Size</th><th>Last accessed</th>"
                         "<th>Modified time</th><th>Created time</th></tr>")
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
                lines.append("<table class='fileupload'><tr><th>Filename</th>"
                             "<th>Saved</th><th>Extract packages</th>"
                             "<th>Submit flag</th><th>File size</th>"
                             "<th>Message</th></tr>")
                for fileuploadobj in fileuploadobjs:
                    lines.append('<tr>%s</tr>'
                                 % html_table_if_have_keys(
                                     fileuploadobj, ['name', 'saved',
                                                     'extract_packages',
                                                     'submitmrsl', 'size',
                                                     'message', ]))
                lines.append('</table>')
        elif i['object_type'] == 'jobobj':
            job_dict = i['jobobj'].to_dict()
            lines.append("<table class='jobobj'><tr><th>Field</th><th>Value"
                         "</th></tr>")
            for (key, val) in job_dict.items():
                lines.append('<tr><td>%s</td><td>%s</td></tr>' % (key,
                                                                  val))
            lines.append('</table>')
        elif i['object_type'] == 'html_form':
            lines.append(i['text'])
        elif i['object_type'] == 'dir_listings':
            redirect_name = i.get('redirect_name',
                                  configuration.site_user_redirect)
            redirect_path = i.get('redirect_path', redirect_name)
            ls_url_template = i['ls_url_template']
            rmdir_url_template = i['rmdir_url_template']
            rm_url_template = i['rm_url_template']
            editor_url_template = i['editor_url_template']
            redirect_url_template = i['redirect_url_template']
            if len(i['dir_listings']) == 0:
                continue
            columns = 7
            if i.get('show_dest', False):
                columns += 1
            lines.append("<table class='files enable_read'>")
            lines.append('<tr class="if_full">')
            cols = 0
            lines.append('<td>Info</td>')
            cols += 1
            lines.append("""<td>
<input type='checkbox' id='checkall_box' name='allbox' value='allbox' />
</td>""")
            cols += 1

            # lines.append("<td><br /></td>"
            # cols += 1

            lines.append('<td colspan=%d>Select/deselect all files</td>'
                         % (columns - cols))
            lines.append('</tr>')
            lines.append('<tr class="if_full">')
            cols = 0
            lines.append('<td colspan=%d><hr></td>'
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
                            lines.append('<tr class="if_full">')
                            lines.append('<td width=20%%>%s:<br />total %s</td>'
                                         % (dir_listing['relative_path'],
                                            len(dir_listing['entries'])))
                            cols += 1
                            lines.append(
                                '''<td class="empty_cell narrow" colspan="%d"></td>
                                ''' % (columns - cols))
                            lines.append('</tr>')
                            cols = columns

                        lines.append('<tr class="%s">' % row_class)
                        cols = 0
                        lines.append('<td class="empty_cell narrow"></td>')
                        cols += 1
                        lines.append("""<td class='if_full narrow'>
<input type='checkbox' name='path' value='%s' />
</td>""" % directory['dirname_with_dir'])
                        cols += 1

                        cls = "file_details"
                        if 'actual_dir' in directory:
                            details = directory['actual_dir']
                        elif 'file_info' in directory:
                            details = txt_file_info(directory['file_info'])
                        else:
                            cls = ""
                            details = ''
                        lines.append('<td class="%s"><tt>%s</tt></td>' %
                                     (cls, details.replace(' ', '&nbsp;')))
                        cols += 1
                        # TODO: enable edit in sharelink and remove if_full here?
                        lines.append(
                            "<td class='enable_write if_full narrow'></td>")
                        cols += 1
                        # Note: this includes CSRF token
                        rmdir_url = rmdir_url_template % directory
                        js_name = 'delete%s' % hexlify(directory['rel_path'])
                        helper = html_post_helper(js_name, rmdir_url, {})
                        lines.append(helper)
                        rmdir_link = html_link({
                            'object_type': 'link', 'destination':
                            "javascript: confirmDialog(%s, '%s');" %
                            (js_name, 'Really completely remove %(rel_path)s?'
                             % directory),
                            'class': 'rmdir icon', 'title': 'Remove %(rel_path)s'
                            % directory, 'text': ''})
                        lines.append("<td class='enable_write narrow'>%s</td>" %
                                     rmdir_link)
                        cols += 1
                        ls_url = ls_url_template % directory
                        extra_class = directory.get('extra_class', '')
                        special = directory.get('special', '')
                        open_link = '''
                        <a class="leftpad directoryicon %s" title="%s %s" href="%s">
                        %s</a>''' % (extra_class, directory['name'], special,
                                     ls_url, directory['name'])
                        lines.append('<td>%s</td>' % open_link)
                        cols += 1
                        lines.append('''<td class="empty_cell narrow" colspan="%d">
</td>''' % (columns - cols))
                        cols = columns
                    elif 'file' == entry['type']:
                        this_file = entry
                        lines.append('<tr class="%s">' % row_class)
                        cols = 0
                        lines.append('<td class="empty_cell narrow"></td>')
                        cols += 1
                        lines.append("""<td class='if_full narrow'>
<input type='checkbox' name='path' value='%s' />
</td>""" % this_file['file_with_dir'])
                        cols += 1
                        cls = "file_details"
                        if 'long_format' in this_file:
                            details = this_file['long_format']
                        elif 'file_info' in this_file:
                            details = txt_file_info(this_file['file_info'])
                        else:
                            cls = ""
                            details = ''
                        lines.append('<td class="%s"><tt>%s</tt></td>' %
                                     (cls, details.replace(' ', '&nbsp;')))
                        cols += 1
                        edit_url = editor_url_template % this_file
                        edit_link = """
                        <a class='edit icon narrow' title='edit' href='%s'></a>
                        """ % edit_url
                        # TODO: enable edit in sharelink?
                        lines.append("<td class='enable_write if_full narrow'>%s</td>"
                                     % edit_link)
                        cols += 1
                        # Note: this includes CSRF token
                        rm_url = rm_url_template % this_file
                        js_name = 'delete%s' % hexlify(this_file['rel_path'])
                        helper = html_post_helper(js_name, rm_url, {})
                        lines.append(helper)
                        rm_link = html_link({
                            'object_type': 'link', 'destination':
                            "javascript: confirmDialog(%s, '%s');" %
                            (js_name, 'Really remove %(rel_path)s?' %
                             this_file),
                            'class': 'rm icon', 'title': 'Remove %(rel_path)s'
                            % this_file, 'text': ''})
                        lines.append("<td class='enable_write narrow'>%s</td>" %
                                     rm_link)
                        cols += 1
                        filename = this_file['name']
                        file_stem, file_ext = os.path.splitext(filename)
                        open_url = redirect_url_template % this_file
                        cols += 1
                        open_link = '''
                        <a class="leftpad fileicon ext_%s" title="open" href="%s">
                        %s</a>''' % (file_ext.lstrip('.').lower(), open_url,
                                     filename)
                        lines.append("<td>%s</td>" % open_link)
                        cols += 1
                        if this_file.get('file_dest', False):
                            lines.append('<td class="if_full narrow">%s</td>'
                                         % this_file['file_dest'])
                            cols += 1
                        lines.append('''<td class="empty_cell narrow" colspan="%d">
</td>''' % (columns - cols))
                        cols = columns
                    row_number += 1
            lines.append('</table>')
            lines.append('')
        elif i['object_type'] == 'filewcs':
            filewcs = i['filewcs']
            if len(filewcs) == 0:
                lines.append('No files to run wc on')
            else:
                lines.append('''
<table class="wc">
<tr><th>File</th><th>Lines</th><th>Words</th><th>Bytes</th></tr>
''')
                for filewc in filewcs:
                    lines.append('<tr><td>%s</td>' % filewc['name'])
                    lines.append('<td>')
                    if 'lines' in filewc:
                        lines.append('%s' % filewc['lines'])
                    lines.append('</td><td>')
                    if 'words' in filewc:
                        lines.append('%s' % filewc['words'])
                    lines.append('</td><td>')
                    if 'bytes' in filewc:
                        lines.append('%s' % filewc['bytes'])
                    lines.append('</td></tr>')
                lines.append('</table>')
        elif i['object_type'] == 'filedus':
            filedus = i['filedus']
            if len(filedus) == 0:
                lines.append('No files to run du on')
            else:
                lines.append('''
<table class="du"><tr><th>File</th><th>Bytes</th></tr>
''')
                for filedu in filedus:
                    lines.append('<tr><td>%s</td>' % filedu['name'])
                    lines.append('<td>')
                    if 'bytes' in filedu:
                        lines.append('%s' % filedu['bytes'])
                    lines.append('</td></tr>')
                lines.append('</table>')
        elif i['object_type'] == 'file_not_found':

            lines.append('File %s was <b>not</b> found!' % i['name'])
        elif i['object_type'] == 'file_output':
            if 'path' in i:
                lines.append('File: %s<br />' % i['path'])
            # NOTE: we shouldn't expect user file contents to be safe here
            lines.append('<pre>%s</pre><br />' %
                         html_escape(''.join(i['lines'])))
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
                lines.append('<table class="links"><tr><th>Name</th>'
                             '<th>Link</th></tr>')
                for link in links:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                 % (html_escape(link['text']),
                                     html_link(link)))
                lines.append('</table>')
        elif i['object_type'] == 'multilinkline':
            links = i['links']
            if len(links) == 0:
                lines.append('No links found!')
            else:
                sep = i.get('sep', ' , ')
                lines.append(sep.join([html_link(link) for link in
                                       links]))
        elif i['object_type'] == 'file':
            lines.append(i['name'])
        elif i['object_type'] == 'progress_list':
            progress_list = i['progress_list']
            header = [['Path', 'Size', 'Total Size', 'Percent', 'Completed']]
            if len(progress_list) == 0:
                lines.append('No progress status found!')
            else:

                lines.append('<table class="progress"><tr>')
                for title in header[0]:
                    lines.append('<th>%s</th>' % title)
                lines.append('</tr>')
                for progress in progress_list:
                    lines.append('<tr>%s</tr>'
                                 % html_table_if_have_keys(progress,
                                                           ['path',
                                                            'cur_size',
                                                            'total_size',
                                                            'percent',
                                                            'done']))
                lines.append('</table>')
        elif i['object_type'] == 'submitstatuslist':
            submitstatuslist = i['submitstatuslist']
            if len(submitstatuslist) == 0:
                lines.append('No job submit status found!')
            else:
                lines.append('''
<div class="table-responsive">
<table class="submitstatus">
<tr><th>File</th><th>Status</th><th>Job Id</th><th>Message</th></tr>
''')
                for submitstatus in submitstatuslist:
                    lines.append('<tr>%s</tr>' % html_table_if_have_keys(
                        submitstatus, ['name', 'status', 'job_id', 'message']))
                lines.append('''
</table>
</div>
''')
        elif i['object_type'] == 'objects':
            objects = i['objects']
            if len(objects) == 0:
                lines.append('No objects found!')
            else:
                lines.append('<table class="objects"><tr><th>Object</th>'
                             '<th>Info</th></tr>')
                for (name, val) in objects:
                    lines.append('<tr><td>%s</td><td>%s</td></tr>'
                                 % (name, val))
                lines.append('</table>')
        elif i['object_type'] == 'sandboxinfos':
            sandboxinfos = i['sandboxinfos']
            lines.append('<table class="sandboxinfo"><tr><th>Username</th>'
                         '<th>Resource(s)</th><th>Jobs</th><th>Walltime</th>'
                         '</tr>')
            row_number = 1
            if not sandboxinfos:
                help_text = 'No sandboxes found - please download a sandbox '
                'below to proceed'
                lines.append('<tr class="%s"><td colspan=4>%s</td></tr>' %
                             (row_name[row_number], help_text))
            for sandboxinfo in sandboxinfos:
                row_class = row_name[row_number % 2]
                lines.append('<tr class="%s">%s</tr>'
                             % (row_class, html_table_if_have_keys(
                                 sandboxinfo, ['username', 'resource', 'jobs',
                                               'walltime'])))
                row_number += 1
            lines.append('</table>')
        elif i['object_type'] == 'runtimeenvironments':
            runtimeenvironments = i['runtimeenvironments']
            lines.append('''
<div class="table-responsive">
<table class="runtimeenvs columnsort" id="runtimeenvtable">
<thead class="title">
    <tr>
        <th>Name</th>
        <th class="icon"><!-- View --></th>
        <th class="icon"><!-- Owner --></th>
        <th>Description</th>
        <th class="icon">Resources</th>
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
<td>%s</td><td class="centertext">%s</td><td class="centertext">%s</td><td>%s
</td><td class="centertext" title="%s">%s</td><td>%s</td>
</tr>''' % (single_re['name'], viewlink, ownerlink, single_re['description'],
                    ', '.join(single_re['providers']
                              ), single_re['resource_count'],
                    single_re['created']))

            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'runtimeenvironment':

            software_html = '''
<div class="table-responsive">
<table class="runtimeenvsw">
'''
            for software in i['software']:
                software_html += '''
<tr>
    <td><img alt="logo" src="%(icon)s" width="80" height="80" /></td><td></td>
</tr>
<tr><td>Name:</td><td>%(name)s</td>
</tr>
<tr>
    <td>Url:</td><td><a class="urllink iconspace" href="%(url)s">%(url)s</a></td>
</tr>
<tr>
    <td>Description:</td><td>%(description)s</td>
</tr>
<tr><td>Version:</td><td>%(version)s</td>
</tr>
''' % software
            software_html += '</table>'

            environment_html = '<table class="runtimeenvvars">'
            for environment in i['environments']:
                environment_html += '''
<tr>
    <td>Name:</td><td>%(name)s (use with ${%(name)s})</td>
</tr>
<tr>
    <td>Example:</td><td>%(example)s</td>
</tr>
<tr>
    <td>Description:</td><td>%(description)s</td>
    </tr>
''' % environment
            environment_html += '</table>'

            lines.append('<table class="runtimeenvdetails">')
            lines.append('<tr><td>Name</td><td>%s</td></tr>' % i['name'
                                                                 ])
            lines.append('<tr><td>Description</td><td>%s</td></tr>'
                         % i['description'])
            lines.append('<tr><td>Needed&nbsp;software</td><td>%s</td></tr>'
                         % software_html)
            lines.append('<tr><td>Environment&nbsp;variables</td>'
                         '<td>%s</td></tr>' % environment_html)
            if i['testprocedure']:
                lines.append("<tr><td>Testprocedure</td>"
                             "<td style='vertical-align:top;'>%s</td></tr>" %
                             i['testprocedure'])
            if i['verifystdout']:
                lines.append("<tr><td>Verifystdout</td>"
                             "<td style='vertical-align:top;'>%s</td></tr>"
                             % i['verifystdout'])
            if i['verifystderr']:
                lines.append("<tr><td>Verifystderr</td>"
                             "<td style='vertical-align:top;'>%s</td></tr>"
                             % i['verifystderr'])
            if i['verifystatus']:
                lines.append("<tr><td>Verifystatus</td>"
                             "<td style='vertical-align:top;'>%s</td></tr>"
                             % i['verifystatus'])
            lines.append('<tr><td>Created</td><td>%s</td></tr>'
                         % i['created'])
            lines.append('<tr><td>Creator</td><td>%s</td></tr>'
                         % i['creator'])
            lines.append('<tr><td>Job&nbsp;count</td><td>%s</td></tr>'
                         % i['job_count'])
            view_providers = [
                {'text': name,
                 'destination': 'viewres.py?unique_resource_name=%s'
                 % name} for name in i['providers']]
            provider_links = [html_link(res) for res in view_providers]
            lines.append('<tr><td>Resources</td><td>%s</td></tr>'
                         % ', '.join(provider_links))
            lines.append('''
</table>
</div>
''')
        elif i['object_type'] == 'peers':
            peers = i['peers']
            lines.append('''
<div class="table-responsive">
<table class="peers columnsort" id="peers">
<thead class="title">
    <tr>
        <th>Full Name</th>
        <th>Organization</th>
        <th>Email</th>
        <th>Country</th>
        <th>State</th>
        <th>Kind</th>
        <th>Label</th>
        <th>Expire</th>
        <th>Actions</th>
    </tr>
</thead>
<tbody>
''')
            if not peers:
                lines.append('''
<td colspan=8>No peers registered yet ...</td>
''')

            for single_peer in peers:
                editlink = single_peer.get('editpeerlink', '')
                invitelink = single_peer.get('invitepeerlink', '')
                viewlink = single_peer.get('viewpeerlink', '')
                dellink = single_peer.get('delpeerlink', '')
                if editlink:
                    editlink = html_link(editlink)
                if invitelink:
                    invitelink = html_link(invitelink)
                if viewlink:
                    viewlink = html_link(viewlink)
                if dellink:
                    dellink = html_link(dellink)
                single_peer['action_links'] = "%s %s %s %s" % \
                                              (editlink, invitelink, viewlink,
                                               dellink)
                single_peer['state'] = single_peer.get('state', '')
                if not single_peer['state']:
                    single_peer['state'] = 'NA'
                lines.append('''<tr>
<td>%(full_name)s</td><td>%(organization)s</td><td>%(email)s</td>
<td>%(country)s</td><td>%(state)s</td><td>%(kind)s</td><td>%(label)s</td><td>%(expire)s</td>
<td>%(action_links)s</td>
</tr>
''' % single_peer)
            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'frozenarchives':
            frozenarchives = i['frozenarchives']
            lines.append('''
<div class="table-responsive">
<table class="frozenarchives columnsort" id="frozenarchivetable">
<thead class="title">
    <tr>
        <th>ID</th>
        <th class="icon"><!-- View / Delete--></th>
        <th>Name</th>
        <th>Created</th>
        <th>Flavor</th>
        <th>State</th>
        <th>Files</th>
    </tr>
</thead>
<tbody>
'''
                         )
            for single_freeze in frozenarchives:
                viewlink = single_freeze.get('viewfreezelink', '')
                editlink = single_freeze.get('editfreezelink', '')
                dellink = single_freeze.get('delfreezelink', '')
                if viewlink:
                    viewlink = html_link(viewlink)
                if editlink:
                    editlink = html_link(editlink)
                if dellink:
                    dellink = html_link(dellink)
                if isinstance(single_freeze['frozenfiles'], int):
                    file_count = single_freeze['frozenfiles']
                else:
                    file_count = len(single_freeze['frozenfiles'])
                lines.append('''
<tr>
<td>%s</td><td class="centertext">%s%s%s</td><td>%s</td><td>%s</td><td>%s</td>
<td>%s</td><td class="centertext">%s</td>
</tr>''' % (single_freeze['id'], viewlink, editlink, dellink,
                    single_freeze['name'], single_freeze['created'],
                    single_freeze['flavor'], single_freeze['state'], file_count))

            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'frozenarchive':

            lines.append('<div class="archive">')
            frozenfile_html = '''
<div class="archive-files">
<div class="table-responsive">
<table class="frozenfiles columnsort" id="frozenfilestable">
<thead class="title">
    <tr>
        <th>Name</th>
        <th class="icon">Action<!-- Open, Delete --></th>
        <th>Date added / original</th>
        <th>Size in bytes</th>'''
            for algo in sorted_hash_algos:
                checksum_field = '%ssum' % algo
                frozenfile_html += '''
        <th class="%s hidden">%s checksum</th>''' % (checksum_field, algo.upper())
            frozenfile_html += '''
    </tr>
</thead>
<tbody>
'''
            for frozenfile in i['frozenfiles']:
                show_entry, del_entry = '', ''
                if frozenfile.get('showfile_link', ''):
                    show_entry = html_link(frozenfile['showfile_link'])
                if frozenfile.get('delfile_link', ''):
                    del_entry = html_link(frozenfile['delfile_link'])

                frozenfile['show_file'] = show_entry
                frozenfile['del_file'] = del_entry
                frozenfile_html += '''
    <tr>
        <td>%(name)s</td><td class="centertext">%(show_file)s %(del_file)s</td>
        <td class="centertext">%(date)s</td>
        <td class="centertext">%(size)s</td>''' % frozenfile
                for algo in sorted_hash_algos:
                    checksum_field = '%ssum' % algo
                    frozenfile_html += '''
        <td class="%s monospace hidden">%s</td>''' % \
                        (checksum_field, frozenfile[checksum_field])
                frozenfile_html += '''
    </tr>
'''
            frozenfile_html += '''
</tbody>
</table>
</div>
</div>'''
            lines.append(frozenfile_html)
            flavor = i.get('flavor', 'freeze')
            lines.append('<div class="archive-metadata">')
            lines.append('<table class="frozenarchivedetails">')
            lines.append('<tr><td class="title">ID</td><td>%s</td></tr>' %
                         i['id'])
            if flavor in ('freeze', 'backup'):
                lines.append('<tr><td class="title">Name</td>'
                             '<td>%s</td></tr>' % i['name'])
            elif flavor == 'phd':
                lines.append('<tr><td class="title">Title</td>'
                             '<td>%s</td></tr>' % i['name'])
            lines.append('<tr><td class="title">Flavor</td>'
                         '<td>%s</td></tr>' % i['flavor'])
            if flavor in ('freeze', 'phd'):
                if i.get('author', '') not in ('', 'UNSET'):
                    lines.append('<tr><td class="title">Author</td>'
                                 '<td>%s</td></tr>' % i['author'])
                if i.get('department', '') not in ('', 'UNSET'):
                    lines.append('<tr><td class="title">Department</td>'
                                 '<td>%s</td></tr>' % i['department'])
                if i.get('organization', '') not in ('', 'UNSET'):
                    lines.append('<tr><td class="title">Organization</td>'
                                 '<td>%s</td></tr>' % i['organization'])
                desc_html = '<tr><td class="title">Description</td><td>'
                desc_html += '<pre class="archive-description">%s</pre>' % \
                             i['description']
                desc_html += '</td></tr>'
                lines.append(desc_html)
                if i.get('publish', False):
                    published = 'Yes'
                    publish_url = i.get('publish_url', '')
                    published += ' (<a href="%s">%s</a>)' % (publish_url,
                                                             publish_url)
                else:
                    published = 'No'
                lines.append('<tr><td class="title">Published</td>'
                             '<td>%s</td></tr>' % published)
            lines.append('<tr><td class="title">State</td><td>%s</td></tr>'
                         % i['state'])
            lines.append('<tr><td class="title">Creator</td><td>%s</td></tr>'
                         % i['creator'])
            lines.append('<tr><td class="title">Created</td><td>%s</td></tr>'
                         % i['created'])
            for (location, store_date) in i.get('location', []):
                lines.append('<tr><td class="title">On %s</td><td>%s</td></tr>'
                             % (location, store_date))
            lines.append('''
</table>
</div>
''')

            checksum_html = ''
            for algo in sorted_hash_algos:
                link_name = '%ssum_link' % algo
                if i.get(link_name, ''):
                    checksum_html += '''<p>
%s
</p>
''' % html_link(i[link_name])

            lines.append("""<div class='checksumarchive'>
Show archive with file checksums - might take quite a while to calculate:
    <div id='checksumbuttons'>
""")
            if checksum_html:
                lines.append(checksum_html)
            else:
                lines.append('<!-- Filled by AJAX -->')

            lines.append("""    </div>
</div>""")

            show_updating, show_edit, show_register = 3 * ['hidden']
            edit_link, finalize_link, register_link = 3 * \
                ['<!-- filled by AJAX-->']
            if i.get('state', '') == keyword_updating:
                show_updating = ''
            if i.get('editarch_link', ''):
                edit_link = html_link(i['editarch_link'])
                show_edit = ''
            if i.get('finalizearch_link', ''):
                finalize_link = html_link(i['finalizearch_link'])
                # NOTE: edit and finalize share div
                show_edit = ''
            if i.get('registerdoi_link', ''):
                register_link = html_link(i['registerdoi_link'])
                show_register = ''

            lines.append("""
<div class='updatearchive %s'>
<p class='warn_message'>
Archive is currently in the process of being updated. No further changes can be
applied until running archive operations are completed.
</p>
</div>
<div class='editarchive %s'>
<p>
You can continue inspecting and changing your archive until you're satisfied,
then finalize it for actual persistent freezing.
</p>
<p id='editfreezebutton'>%s</p>
<p id='finalizefreezebutton'>%s</p>
</div>
<div class='registerarchive %s'>
<p>
You can register a <a href='http://www.doi.org/index.html'>Digital Object
Identifier (DOI)</a> for finalized archives. This may be useful in case you
want to reference the contents in a publication.
</p>
%s
<p id='registerdoibutton'>%s</p>
</div>
<div class='vertical-spacer'></div>
</div>
""" % (show_updating, show_edit, edit_link, finalize_link, show_register,
                configuration.site_freeze_doi_text, register_link))

        elif i['object_type'] == 'freezestatus':
            # We only use this element for scripted archive creation
            pass
        elif i['object_type'] == 'datatransfers':
            datatransfers = i['datatransfers']
            lines.append('''
<div class="table-responsive">
<table class="table datatransfers columnsort" id="datatransferstable">
<thead class="title">
    <tr>
        <th>ID</th>
        <th class="icon"><!-- Delete --></th>
        <th>Action</th>
        <th>Protocol</th>
        <th>Host</th>
        <th>Port</th>
        <th>Login</th>
        <th>Source(s)</th>
        <th>Destination</th>
        <th>Exclude(s)</th>
        <th>Compress</th>
        <th>Updated</th>
        <th>Status</th>
    </tr>
</thead>
<tbody>
''')
            for single_transfer in datatransfers:
                outputlink = html_link(single_transfer.get('viewoutputlink',
                                                           ''))
                # optional links
                datalink = single_transfer.get('viewdatalink', '')
                editlink = single_transfer.get('edittransferlink', '')
                dellink = single_transfer.get('deltransferlink', '')
                redolink = single_transfer.get('redotransferlink', '')
                datalink_html = ''
                if datalink:
                    datalink_html = html_link(datalink)
                editlink_html = ''
                if editlink:
                    editlink_html = html_link(editlink)
                dellink_html = ''
                if editlink:
                    editlink_html = html_link(editlink)
                dellink_html = ''
                if dellink:
                    dellink_html = html_link(dellink)
                redolink_html = ''
                if redolink:
                    redolink_html = html_link(redolink)
                if single_transfer.get('password', ''):
                    login = '%(username)s : ' % single_transfer
                    login += '*' * len(single_transfer['password'])
                elif single_transfer.get('key', ''):
                    login = '%(username)s : %(key)s' % single_transfer
                else:
                    login = 'anonymous'
                lines.append('''
<tr>
<td>%s</td><td class="centertext">%s %s</td><td>%s</td><td>%s</td><td>%s</td>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>
<!-- use nested table to distribute status and icons consistenly -->
<table class="datatransfers status" style="width: 100%%;"><tr>
<td style="min-width: 60%%;">%s</td><td>%s</td><td>%s</td><td>%s</td>
</tr></table>
</tr>''' % (single_transfer['transfer_id'], editlink_html, dellink_html,
                    single_transfer['action'], single_transfer['protocol'],
                    single_transfer['fqdn'], single_transfer['port'], login,
                    ', '.join(single_transfer['src']), single_transfer['dst'],
                    ', '.join(single_transfer.get('exclude', [])),
                    single_transfer.get(
                        'compress', False), single_transfer['updated'],
                    single_transfer['status'], outputlink, datalink_html,
                    redolink_html))
            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'transferkeys':
            transferkeys = i['transferkeys']
            lines.append('''
<div class="table-responsive">
<table class="transferkeys columnsort" id="transferkeystable">
<thead class="title">
    <tr>
        <th>ID</th>
        <th class="icon"><!-- Delete --></th>
        <th>Created</th>
        <th>Type</th>
        <th>Bits</th>
        <th>Public Key</th>
    </tr>
</thead>
<tbody>
''')
            for single_key in transferkeys:
                dellink = single_key.get('delkeylink', '')
                dellink_html = ''
                if dellink:
                    dellink_html = html_link(dellink)
                lines.append('''
<tr>
<td>%s</td><td class="centertext">%s</td><td>%s</td><td>%s</td><td>%s</td>
<td style="width: 70%%;">
<textarea class="publickey" rows="5" readonly="readonly">%s</textarea>
</tr>''' % (single_key['key_id'], dellink_html,
                    single_key['created'], single_key['type'],
                    single_key['bits'], single_key['public_key']))
            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'sharelinks':
            sharelinks = i['sharelinks']
            skip_list = i.get('skip_list', [])
            optional_cols = [('access', 'Access'), ('created', 'Created'),
                             ('active', 'Active'), ('owner', 'Owner'),
                             ('invites', 'Invites'),  ('expire', 'Expire'),
                             ('single_file', 'Single file'),
                             ]
            # IMPORTANT: AdBlock Plus hides elements with class sharelink(s)
            #            so we stray from naming pattern and call it linkshares
            #            here to avoid trouble.
            lines.append('''
<div class="table-responsive">
<table class="linkshares columnsort" id="sharelinkstable">
<thead class="title">
    <tr>
        <th>ID</th>
        <th class="icon">Action<!-- Open, Edit, Delete --></th>
        <th>Path</th>
    ''')
            for (key, title) in optional_cols:
                if not key in skip_list:
                    lines.append('<th>%s</th>' % title)
            lines.append('''
    </tr>
</thead>
<tbody>
''')
            for single_share in sharelinks:
                openlink = single_share.get('opensharelink', '')
                openlink_html = ''
                if openlink and not 'opensharelink' in skip_list:
                    openlink_html = html_link(openlink)
                editlink = single_share.get('editsharelink', '')
                editlink_html = ''
                if editlink and not 'editsharelink' in skip_list:
                    editlink_html = html_link(editlink)
                else:
                    # Leave the icon space empty if not set (used in edit)
                    editlink_html = '<span class="iconleftpad"></span>'
                dellink = single_share.get('delsharelink', '')
                dellink_html = ''
                if dellink and not 'delsharelink' in skip_list:
                    dellink_html = html_link(dellink)
                access = ' & '.join(single_share['access'])
                lines.append('''
<tr>
<td>%s</td><td class="centertext">%s%s%s</td><td>%s</td>''' % (single_share['share_id'],
                                                               openlink_html, editlink_html,
                                                               dellink_html,
                                                               single_share['path']))
                for (key, title) in optional_cols:
                    if not key in skip_list:
                        if isinstance(single_share[key], basestring):
                            val = single_share[key]
                        elif isinstance(single_share[key], list):
                            val = ', '.join(single_share[key])
                        else:
                            val = single_share[key]
                        lines.append('<td>%s</td>' % val)
                lines.append('''
</tr>
''')

            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'accessrequests':
            accessrequests = i['accessrequests']
            lines.append('''
<div class="table-responsive">
<table class="accessrequests columnsort" id="accessrequeststable">
<thead class="title">
    <tr>
        <th>Type</th>
        <th class="icon"><!-- Accept --></th>
        <th class="icon"><!-- Reject --></th>
        <th>ID</th>
        <th>Date</th>
        <th>Message</th>
    </tr>
</thead>
<tbody>
''')
            for single_req in accessrequests:
                # Map request_type from vgridowner/-member or resourceowner
                if single_req['request_type'].endswith('member'):
                    req_type = "Member"
                elif single_req['request_type'].endswith('resource'):
                    req_type = "Resource"
                elif single_req['request_type'].endswith('owner'):
                    req_type = "Owner"
                else:
                    req_type = "Unknown"
                acceptlink = single_req.get('acceptrequestlink', '')
                acceptlink_html = ''
                if acceptlink:
                    acceptlink_html = html_link(acceptlink)
                rejectlink = single_req.get('rejectrequestlink', '')
                rejectlink_html = ''
                if rejectlink:
                    rejectlink_html = html_link(rejectlink)
                lines.append('''
<tr>
<td>%s</td><td class="centertext">%s</td><td class="centertext">%s</td><td>%s</td><td>%s</td><td>%s</td>
</tr>''' % (req_type, acceptlink_html, rejectlink_html, single_req['entity'],
                    single_req['created'], single_req['request_text']))

            lines.append('''
</tbody>
</table>
</div>
''')
        elif i['object_type'] == 'accountreqs':
            accountreqs = i['accountreqs']
            table_head = '''
<div class="table-responsive">
<table class="accountreqs columnsort" id="accountreqtable">
<thead class="title">
    <tr>
        <th>ID</th>
        <th class="icon"><!-- Action icons --></th>
        <th>Full Name</th>
        <th>Email</th>
        <th>Organization</th>
        <th>Country</th>
        <th>State</th>'''
            if configuration.site_enable_peers:
                for name in configuration.site_peers_explicit_fields:
                    table_head += '''<th>Peers contact(s) %s</th>
                ''' % name.replace('_', ' ').capitalize()
            table_head += '''
        <th>Comment</th>
        <th>Auth Access</th>
        <th>Created</th>
    </tr>
</thead>
<tbody>
'''
            lines.append(table_head)
            for single_accountreq in accountreqs:
                createlink = single_accountreq.get('createaccountreqlink', '')
                createlink_html = ''
                if createlink:
                    createlink_html = '%s' % html_link(createlink)
                peerlink = single_accountreq.get('peeraccountreqlink', '')
                peerlink_html = ''
                if peerlink:
                    peerlink_html = '%s' % html_link(peerlink)
                rejectlink = single_accountreq.get('rejectaccountreqlink', '')
                rejectlink_html = ''
                if rejectlink:
                    rejectlink_html = '%s' % html_link(rejectlink)
                table_line = '''
<tr>
<td>%s</td><td class="centertext iconspace">%s %s %s</td>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>'''
                if configuration.site_enable_peers:
                    for name in configuration.site_peers_explicit_fields:
                        field = 'peers_%s' % name
                        value = single_accountreq.get(field, '')
                        table_line += '''<td>%s</td>''' % value
                table_line += '''<td>%s</td><td>%s</td>
<td>%s</td>
</tr>'''
                lines.append(table_line % (single_accountreq['id'],
                                           createlink_html, peerlink_html,
                                           rejectlink_html,
                                           single_accountreq['full_name'],
                                           single_accountreq['email'],
                                           single_accountreq['organization'],
                                           single_accountreq['country'],
                                           single_accountreq['state'],
                                           single_accountreq['comment'],
                                           ', '.join(
                    single_accountreq['auth']),
                    single_accountreq['created']))
            lines.append('''
</tbody>
</table>
</div>
<br/>''')
        elif i['object_type'] == 'table_pager':
            id_prefix = i.get('id_prefix', '')
            entry_name = i['entry_name']
            page_entries = i.get('page_entries', [5, 10, 20, 25, 40, 50, 80,
                                                  100, 250, 500, 1000])
            default_entries = i.get('default_entries', 20)
            if not default_entries in page_entries:
                page_entries.append(default_entries)
            form_prepend = i.get('form_prepend', '')
            form_append = i.get('form_append', '')
            enable_refresh_button = i.get('refresh_button', True)
            toolbar = tablesorter_pager(configuration, id_prefix, entry_name,
                                        page_entries, default_entries,
                                        form_prepend, form_append,
                                        enable_refresh_button)
            lines.append(toolbar)
        elif i['object_type'] == 'resource_list':
            if len(i['resources']) > 0:
                res_fields = ['PUBLICNAME', 'NODECOUNT', 'CPUCOUNT', 'MEMORY',
                              'DISK', 'ARCHITECTURE']
                resources = i['resources']
                lines.append('''
<div class="table-responsive">
<table class="resources columnsort" id="resourcetable">
<thead class="title">
<tr>
  <th>Resource ID</th>
  <th class="icon"><!-- View / Admin --></th>
  <th class="icon"><!-- Remove owner --></th>
  <th class="centertext">Runtime envs</th>
  <th class="centertext">Alias</th>
  <th class="centertext">Nodes</th>
  <th class="centertext">CPUs</th>
  <th class="centertext">Mem (MB)</th>
  <th class="centertext">Disk (GB)</th>
  <th class="centertext">Arch</th>
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
                    lines.append(
                        '<td class="%sres iconspace iconleftpad" title="%s resource">%s</td>' %
                        (res_type, res_type, obj['name']))
                    lines.append('<td class="centertext">')
                    # view or admin link depending on ownership
                    if 'resdetailslink' in obj:
                        lines.append('%s' % html_link(obj['resdetailslink']))
                    lines.append('</td>')
                    lines.append('<td class="centertext">')
                    if 'resownerlink' in obj:
                        lines.append('%s' % html_link(obj['resownerlink']))
                    lines.append('</td>')
                    # List number of runtime environments in field and add
                    # actual names as mouse-over
                    rte_list = obj.get('RUNTIMEENVIRONMENT', [])
                    lines.append('<td class="centertext" title="%s">' %
                                 ', '.join(rte_list))
                    lines.append('%d' % len(rte_list))
                    lines.append('</td>')
                    # Remaining fields
                    for name in res_fields:
                        lines.append('<td class="centertext">')
                        lines.append('%s' % obj.get(name, ''))
                        lines.append('</td>')
                    lines.append('</tr>')
                lines.append('</tbody></table>')
            else:
                lines.append('No matching Resources found')
        elif i['object_type'] == 'resource_info':
            resource_html = ''
            resource_html += '<h3>Details for %s</h3>' % i['unique_resource_name']
            resource_html += '''
<table class="resource"><tr>
<td colspan=2><h3>General</h3></td>
</tr>'''
            for (key, val) in i['fields']:
                resource_html += '''
<tr>
<td>%s</td><td>%s</td>
</tr>
''' % (key, val)
            resource_html += '''
<tr>
<td colspan=2><h3>Exes</h3></td>
</tr>
'''
            for (exe_name, exe_spec) in i['exes'].items():
                resource_html += '''
<tr>
<td colspan=2><b>%s</b></td>
</tr>''' % exe_name
                for (key, val) in exe_spec:
                    resource_html += '''
<tr>
<td>%s</td><td>%s</td>
</tr>
''' % (key, val)
            if not i['exes']:
                resource_html += '<tr><td coslpan=2>None</td></tr>'

            resource_html += '''
<tr>
<td colspan=2><h3>Stores</h3></td>
</tr>'''
            for (store_name, store_spec) in i['stores'].items():
                resource_html += '''
<tr>
<td colspan=2><b>%s</b></td>
</tr>
''' % store_name
                for (key, val) in store_spec:
                    resource_html += '''
<tr>
<td>%s</td><td>%s</td>
</tr>
''' % (key, val)
            if not i['stores']:
                resource_html += '<tr><td coslpan=2>None</td></tr>'

            resource_html += '''
</table>
</div>
'''
            lines.append(resource_html)
        elif i['object_type'] == 'upgrade_info':
            user_html = ''
            user_html += '<h3>%s</h3>' % i['text']
            for cmd in i['commands']:
                user_html += '<tt>%s</tt><br/>' % cmd
            lines.append(user_html)
        elif i['object_type'] == 'user_list':
            if len(i['users']) > 0:
                user_fields = []
                notify_headers = ''
                for proto in configuration.notify_protocols:
                    user_fields.append('send%slink' % proto)
                    notify_headers += '  <th class="centertext">%s</th>' % \
                                      proto
                users = i['users']
                lines.append('''
<div class="table-responsive">
<table class="people columnsort" id="usertable"><thead class="title">
<tr>
  <th class="avatar iconspace"><!-- avatar --></th>
  <th>User ID</th>
  <th class="icon"><!-- View --></th>
  %s
</tr>
</thead>
<tbody>
''' % notify_headers
                             )
                for obj in users:
                    lines.append('<tr>')
                    img_html = ''
                    if obj.get('avatar_url', ''):
                        img_html = '<img alt="avatar" class="profile-thumb" src="%(avatar_url)s">' % obj
                    lines.append('<td class="avatar">%s</td>' % img_html)
                    lines.append('<td class="user" title="user">%s</td>' %
                                 obj.get('pretty_id', obj['name']))
                    lines.append('<td class="centertext">')
                    if 'userdetailslink' in obj:
                        lines.append('%s' % html_link(obj['userdetailslink']))
                    lines.append('</td>')
                    # Remaining fields
                    for name in user_fields:
                        lines.append('<td class="centertext">')
                        if name in obj:
                            lines.append('%s' % html_link(obj[name]))
                        else:
                            lines.append('---')
                        lines.append('</td>')
                    lines.append('</tr>')
                lines.append('''
</tbody>
</table>
</div>
''')
            else:
                lines.append('No matching users found')
        elif i['object_type'] == 'user_info':
            user_html = ''
            user_html += '<!--<h3>%s</h3>-->' % i['user_id']
            user_html += '<div class="row">'
            for (key, val) in i['fields']:
                user_html += '''
                    <div class="col-lg-12"><h3>%s</h3></div>
                    <div class="col-lg-12">%s</div>
                ''' % (key, val)
            user_html += '</div>'
            lines.append(user_html)
        elif i['object_type'] == 'vgrid_info':
            vgrid_html = ''
            vgrid_html += '<h3>%s</h3>' % i['vgrid_name']
            vgrid_html += '<table class="vgrid">'
            for (key, val) in i['fields']:
                if isinstance(val, basestring):
                    val = val.replace('\n', '<br/>')
                vgrid_html += \
                    '<tr><td><h4>%s</h4></td><td>%s</td></tr>' % \
                    (key, val)
            vgrid_html += '</table>'
            lines.append(vgrid_html)
        elif i['object_type'] == 'forum_threads':
            thread_fields = ['last', 'subject', 'author', 'date',
                             'replies']
            if i.get('status', None):
                lines.append('<p class="status_message">%s</p>' % i['status'])
            if len(i['threads']) > 0:
                threads = i['threads']
                lines.append('''
<div class="table-responsive">
<table class="forum_threads columnsort" id="forumtable">
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
                                          '%s&vgrid_name=%s' %
                                          (entry['link'], i['vgrid_name'])}
                            lines.append('%s' % html_link(link_entry))
                        else:
                            lines.append('%s' % val)
                        lines.append('</td>')
                        # Reset marker after first entry
                        marker_class = ''
                    lines.append('</tr>')
                lines.append('''
</tbody>
</table>
</div>
''')
            else:
                lines.append('No matching threads found')
            max_subject_len, max_body_len = 100, 10000
            if 'vgrid_name' in i:
                lines.append('''
<p>
<div id="search_threads">
<a class="searchlink iconspace"
href="javascript:toggle_new('search_form', 'search_threads');">
Search threads</a>
</div>
<div class="hidden_form framed_form" id="search_form">
<form method="post" action="?">
<input type="hidden" name="action" value="search"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<p>Subject:
<input id="search_form_main" name="msg_subject" type="text" maxlength="%s"
size="80" value=""/></p>
<p class="hidden_form">Body:
<input name="msg_body" type="text" maxlength="%s" size="80" value=""/></p>
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
<a class="newpostlink iconspace" href="javascript:toggle_new('new_form', 'new_link');">
Start a new thread</a>
</div>
<div class="hidden_form framed_form" id="new_form">
<form method="post" action="?">
<input type="hidden" name="action" value="new_thread"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<p>Subject: <input id="new_form_main" type="text" name="msg_subject"
maxlength="%s" size="80"/>
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
<a class="refreshlink iconspace" href="?show_all&vgrid_name=%s">Reload threads</a>
</p>''' % i['vgrid_name'])
                lines.append('''
<div id="subscribe_form">
<form method="post" action="?">
<input type="hidden" name="action" value="toggle_subscribe"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<input class="submit_button" type="submit"
  value="Subscribe/unsubscribe to forum updates"/>
</form>
</div>
''' % i['vgrid_name'])
        elif i['object_type'] == 'forum_thread_messages':
            message_fields = ['date', 'author', 'body']
            if i.get('status', None):
                lines.append('<p class="status_message">%s</p>' % i['status'])
            if len(i['messages']) > 0:
                lines.append("<h2>%s</h2>" % i['messages'][0]['subject'])
                lines.append('''
<div class="table-responsive">
<table class="forum_messages columnsort" id="forumtable">
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
                lines.append('''
</table>
</div>
''')
            else:
                lines.append('No messages in thread')
            if 'vgrid_name' in i and 'thread' in i:
                lines.append('''
<p>
<div id="new_link">
<a class="replylink iconspace" href="javascript:toggle_new('reply_form', 'new_link')">
Reply to this thread</a></p>
</div>
<div class="hidden_form framed_form" id="reply_form">
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
<p><a class="refreshlink iconspace" href="?show_thread&vgrid_name=%s&thread=%s">
Reload thread</a></p>''' % (i['vgrid_name'], i['thread']))
                lines.append('''
<p><a class="backlink iconspace" href="?vgrid_name=%s">Return to forum index</a></p>
''' % i['vgrid_name'])
                lines.append('''
<div id="subscribe_form">
<form method="post" action="?">
<input type="hidden" name="action" value="toggle_subscribe"/>
<input type="hidden" name="vgrid_name" value="%s"/>
<input type="hidden" name="thread" value="%s"/>
<input class="submit_button" type="submit"
  value="Subscribe/unsubscribe to thread updates"/>
</form>
</div>
''' % (i['vgrid_name'], i['thread']))
        elif i['object_type'] == 'vgrid_list':
            if len(i['vgrids']) > 0:
                vgrids = i['vgrids']
                components = i['components']
                titles = []
                # hide links to public components which are disabled in apache
                component_links = {
                    'files': ['sharedfolderlink'],
                    'web': ['enterprivatelink', 'editprivatelink',
                            'enterpubliclink', 'editpubliclink'],
                    'scm': ['ownerscmlink', 'memberscmlink'
                            # 'publicscmlink'
                            ],
                    'tracker': ['ownertrackerlink', 'membertrackerlink'
                                # 'publictrackerlink'
                                ],
                    'forum': ['privateforumlink'],
                    'workflows': ['privateworkflowslink'],
                    'monitor': ['privatemonitorlink'],
                }
                lines.append('''
<div class="table-responsive">
<table class="vgrids columnsort" id="vgridtable">
''')
                # make vgrid component links optional, like it is in the
                # configuration
                for key in components:
                    titles.append('''
  <th class="centertext %(class)s" title="%(hover)s" colspan="1">
      %(title)s
  </th>
''' % vgrid_items[key])

                lines.append('''
<thead class="title">
<tr>
  <th title="%s name with slashes indicating nesting">Name</th>
  <th title="View details" class="icon"><!-- View --></th>
  <th title="Ownership actions" class="icon"><!-- Owner --></th>
  <th title="Membership actions" class="icon"><!-- Member --></th>
  %s
</tr>
</thead>
<tbody>
''' % (configuration.site_vgrid_label, '\n'.join(titles)))
                for obj in vgrids:
                    lines.append('<tr>')
                    lines.append('<td>%s</td>' % obj['name'])
                    lines.append('<td class="centertext">')
                    if 'viewvgridlink' in obj:
                        lines.append('%s'
                                     % html_link(obj['viewvgridlink']))
                    lines.append('</td>')
                    lines.append('<td class="centertext">')
                    if 'administratelink' in obj:
                        lines.append('%s'
                                     % html_link(obj['administratelink']))
                    lines.append('</td>')
                    lines.append('<td class="centertext">')
                    # membership links: should be there in any case
                    if 'memberlink' in obj:
                        lines.append('%s'
                                     % html_link(obj['memberlink']))
                    lines.append('</td>')
                    for key in components:
                        lines.append('<td class="centertext">')
                        for link in component_links[key]:
                            if link in obj:
                                lines.append('%s ' % html_link(obj[link]))
                            else:
                                lines.append('')
                        lines.append('</td>')
                    lines.append('</tr>')
                lines.append('''
</tbody>
</table>
</div>
''')
            else:
                lines.append('No matching %ss found' %
                             configuration.site_vgrid_label)
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
        elif i['object_type'] == 'openid_status':
            if i.get('server', None):
                lines.append('<h2>Server</h2><p>%s</p>' % i['server'])
            if i.get('status', None):
                lines.append('<h2>Status</h2><p>%s</p>' % i['status'])
            if i.get('error', None):
                lines.append('<h2>Error</h2><p>%s</p>' % i['error'])
        elif i['object_type'] == 'seafile_status':
            if i.get('server', None):
                lines.append('<h2>Server</h2><p>%s</p>' % i['server'])
            if i.get('status', None):
                lines.append('<h2>Status</h2><p>%s</p>' % i['status'])
            if i.get('error', None):
                lines.append('<h2>Error</h2><p>%s</p>' % i['error'])
            # NOTE: data is html of source page which we don't want to show
            if i.get('data', None):
                lines.append('<h2>Content Size</h2><p>%d</pre></p>' %
                             len(i['data']))
        elif i['object_type'] == 'service':
            service = i
            lines.append('''
            <a class="ui-button" id="service" href="%s" target="_blank">%s</a>
            ''' % (service['targetlink'], service['name']))
        elif i['object_type'] == 'services':
            services = i['services']
            for service in services:
                lines.append('''
                <a class="ui-button" id="service" href="%s">%s</a>
                ''' % (service['targetlink'], service['name']))
        elif i['object_type'] == 'script_status':
            status_line = i.get('text')
        elif i['object_type'] == 'timing_info':
            timing_info = i.get('text')
        elif i['object_type'] == 'end':
            pass
        elif i['object_type'] == 'wsgi':
            pass
        else:
            lines.append('unknown object %s' % i)

    if status_line:
        timing_footer = ''
        status_line = status_line.replace('TIMING_INFO', timing_info)
        if user_settings.get('USER_INTERFACE', configuration.user_interface[-1]) == 'V2':
            timing_footer = status_line
        # TODO: move inside get_xgi_html_footer?
        # Terminate UI V3 container
        lines.append('''
<!-- End UI container -->
</div>
'''
                     )
        lines.append(get_xgi_html_footer(configuration, timing_footer, True,
                                         user_settings, include_widgets,
                                         user_widgets))

    # NOTE: careful handling required for binary on python3+
    if sys.version_info[0] > 2 and binary_output:
        return b''.join(lines)
    else:
        return '\n'.join(lines)


# def xml_format(configuration, ret_val, ret_msg, out_obj):
#    """Generate output in xml format"""
#
#    print "xml format not implemented yet"
#    return True


def soap_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in soap format"""

    import SOAPpy
    return SOAPpy.buildSOAP(out_obj)


def pickle_helper(configuration, ret_val, ret_msg, out_obj, protocol=None):
    """Generate output in requested pickle protocol format"""

    from mig.shared.serial import dumps
    return dumps(out_obj, protocol)


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

    import yaml
    return yaml.dump(out_obj)


def xmlrpc_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in xmlrpc format"""

    import xmlrpclib
    # Wrap any explicit binary entries to avoid encoding errors
    for entry in out_obj:
        if entry.get('wrap_binary', False):
            for key in entry.get('wrap_targets', []):
                if not key in entry:
                    continue
                entry[key] = xmlrpclib.Binary(entry[key])
    return xmlrpclib.dumps((out_obj, ), allow_none=True)


def json_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in json format"""

    # python >=2.6 includes native json module with loads/dumps methods
    import json
    return json.dumps(out_obj)


def resource_format(configuration, ret_val, ret_msg, out_obj):
    """Generate output in resource format"""
    # TODO: is this right? not sure where it is used if ever!
    #       Function is needed as long as it's listed in _valid_output_formats
    return txt_format(configuration, ret_val, ret_msg, out_obj)


def file_format(configuration, ret_val, ret_msg, out_obj):
    """Dump raw file contents"""

    # TODO: use wsgi file_wrapper helper here if out_obj has wsgi entry?

    file_content = ''

    for entry in out_obj:
        if entry['object_type'] == 'file_output':
            for line in entry['lines']:
                file_content += line
        elif entry['object_type'] == 'binary':
            file_content = entry['data']

    return file_content


def get_valid_outputformats():
    """Return list of valid outputformats"""
    return list(_valid_output_formats)


def get_outputformat_helper(name, default_format='html'):
    """Lookup the format helper function for outputformat name, with fallback
    to default_format if not available.
    """
    if not name in _valid_output_formats:
        if default_format in _valid_output_formats:
            # Fall back to default format
            name = default_format
        else:
            # Emergency fall back to plain txt
            name = 'txt'
    # TODO: can we use functools or similar to generate this map on the fly?
    valid_format_map = {'txt': txt_format, 'html': html_format,
                        'soap': soap_format, 'pickle': pickle_format,
                        'pickle1': pickle1_format, 'pickle2': pickle2_format,
                        'yaml': yaml_format, 'xmlrpc': xmlrpc_format,
                        'resource': resource_format, 'json': json_format,
                        'file': file_format}
    return valid_format_map[name]


def format_output(
    configuration,
    backend,
    ret_val,
    ret_msg,
    out_obj,
    outputformat,
):
    """This is the public method that should be called from other scripts"""

    logger = configuration.logger
    #logger.debug("format output to %s" % outputformat)
    valid_formats = get_valid_outputformats()
    (val_ret, val_msg) = validate(out_obj)
    if not val_ret:
        logger.error("%s formatting failed: %s (%s)" %
                     (outputformat, val_msg, val_ret))
        (ret_val, ret_msg) = returnvalues.OUTPUT_VALIDATION_ERROR

        # TODO: we should really preserve basic init elemes or use crash helper
        #       Currently validation errors here result in severely broken page

        # hide previous output

        out_obj = []
        out_obj.extend([{'object_type': 'error_text', 'text':
                         'Validation error! %s' % val_msg},
                        {'object_type': 'title', 'text': 'Validation error!'}])

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
                'meta': '',
                'style': {},
                'script': {},
            }] + out_obj

    # NOTE: strip wsgi helpers and info unless needed for output formatting
    if not outputformat in ('txt', 'html', 'file'):
        out_obj = [i for i in out_obj if i['object_type'] != 'wsgi']

    #logger.debug("%s formatting output" % outputformat)
    try:
        # return eval('%s_format(configuration, ret_val, ret_msg, out_obj)' %
        #            outputformat)
        format_helper = get_outputformat_helper(outputformat, 'txt')
        formatted = format_helper(configuration, ret_val, ret_msg, out_obj)
        return formatted
    except Exception as err:
        logger.error("%s formatting failed: %s\n%s" %
                     (outputformat, err, traceback.format_exc()))
        out_filtered = filter_output_objects(configuration, out_obj)
        logger.error("original %r response was: %s" % (backend, out_filtered))

    # Try simple crash message on requested format
    try:
        logger.warning("trying to %s format simple crash info" % outputformat)
        crash_out = crash_helper(configuration, backend, [])
        # return eval('%s_format(configuration, ret_val, ret_msg, crash_out)' %
        #             outputformat)
        format_helper = get_outputformat_helper(outputformat, 'txt')
        formatted = format_helper(configuration, ret_val, ret_msg, crash_out)
        return formatted
    except Exception as err:
        logger.error("%s formatting even simple crash info failed: %s\n%s" %
                     (outputformat, err, traceback.format_exc()))
        # Return None and leave bailout to caller
        return None


def format_timedelta(timedelta):
    """Formats timedelta as '[Years,] [days,] HH:MM:SS'"""
    years = timedelta.days // 365
    days = timedelta.days - (years*365)
    hours = timedelta.seconds // 3600
    minutes = (timedelta.seconds-(hours*3600)) // 60
    seconds = timedelta.seconds - (hours*3600) - (minutes*60)

    hours_str = "%s" % hours
    if hours < 10:
        hours_str = "0%s" % hours_str

    minutes_str = "%s" % minutes
    if minutes < 10:
        minutes_str = "0%s" % minutes_str

    seconds_str = "%s" % seconds
    if seconds < 10:
        seconds_str = "0%s" % seconds_str

    if years > 0:
        result = "%s years, %s days, %s:%s:%s" % (years, days,
                                                  hours_str, minutes_str,
                                                  seconds_str)
    elif days > 0:
        result = "%s days, %s:%s:%s" % (days, hours_str, minutes_str,
                                        seconds_str)
    else:
        result = "%s:%s:%s" % (hours_str, minutes_str, seconds_str)

    return result
