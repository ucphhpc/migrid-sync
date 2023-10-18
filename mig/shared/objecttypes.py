#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# objecttypes - output object types and validation
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

""" Defines valid objecttypes and provides a method to verify if an object is correct """

start = {'object_type': 'start', 'required': [], 'optional': ['headers'
                                                              ]}
end = {'object_type': 'end', 'required': [], 'optional': []}
timing_info = {'object_type': 'timing_info', 'required': [],
               'optional': []}
title = {'object_type': 'title', 'required': ['text'],
         'optional': ['meta', 'style', 'script']}
text = {'object_type': 'text', 'required': ['text'], 'optional': []}
verbatim = {'object_type': 'verbatim', 'required': ['text'],
            'optional': []}
binary = {'object_type': 'binary', 'required': ['data'], 'optional': []}
script_status = {'object_type': 'script_status', 'required': [],
                 'optional': ['text']}
header = {'object_type': 'header', 'required': ['text'], 'optional': []}
sectionheader = {'object_type': 'sectionheader', 'required': ['text'],
                 'optional': []}
link = {'object_type': 'link', 'required': ['destination', 'text'],
        'optional': []}
error_text = {'object_type': 'error_text', 'required': ['text'],
              'optional': ['exc']}
job = {'object_type': 'job', 'required': ['job_id',
                                          'execution_histories'], 'optional': []}
trigger_job = {'object_type': 'trigger_job', 'required': ['job_id',
                                                          'rule_id'], 'optional': []}
warning = {'object_type': 'warning', 'required': ['text'],
           'optional': []}
direntry = {'object_type': 'direntry', 'required': ['name', 'type'],
            'optional': []}
# TODO: file is not a good naming due to collision with file() builtin
file = {'object_type': 'file', 'required': ['name'], 'optional': []}
progress = {'object_type': 'progress', 'required': [
    'progress_type',
    'path',
    'cur_size',
    'total_size',
    'percent',
    'done',
], 'optional': []}
progress_list = {'object_type': 'progress_list',
                 'required_list': [('progress_list', 'progress')]}
stat = {'object_type': 'stat', 'required': [
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
], 'optional': ['name']}
directory = {'object_type': 'directory', 'required': ['name'],
             'optional': []}
html_form = {'object_type': 'html_form', 'required': ['text'],
             'optional': []}
filewc = {'object_type': 'filewc', 'required': ['name'],
          'optional': ['lines', 'words', 'bytes']}
filedu = {'object_type': 'filedu', 'required': ['name', 'bytes'],
          'optional': []}
# TODO: list is not a good naming due to collision with list() builtin
list = {'object_type': 'list', 'required': ['list'], 'optional': []}
project_info = {'object_type': 'project_info',
                'required': ['info'], 'optional': []}
file_not_found = {'object_type': 'file_not_found', 'required': ['name'
                                                                ], 'optional': []}
file_output = {'object_type': 'file_output', 'required': ['lines'],
               'optional': ['path']}
environment = {'object_type': 'environment', 'required':
               ['name', 'example', 'description'], 'optional': []}
software = {'object_type': 'software', 'required':
            ['name', 'icon', 'url', 'description', 'version'], 'optional': []}
runtimeenvironment = {
    'object_type': 'runtimeenvironment',
    'required': [
        'name',
        'description',
        'creator',
        'created',
        'job_count',
        'resource_count',
        'testprocedure',
        'verifystdout',
        'verifystderr',
        'verifystatus',
    ],
    'required_list': [('software', 'software'), ('environments',
                                                 'environment')],
    'optional': [],
}
peer = {'object_type': 'peer', 'required':
        ['full_name', 'organization', 'email',
            'country', 'label', 'kind', 'expire'],
        'optional': []}
# Used by workflowjsoninterface
# TODO, add the explicit fields that it uses
workflow = {
    'object_type': 'workflow',
    # 'required': [],
    # 'optional': [workflowpattern, workflowrecipe]
}
job_dict = {
    'object_type': 'job_dict'
}

frozenfile = {'object_type': 'frozenfile', 'required':
              ['name', 'size', 'checksum', 'timestamp'], 'optional': []}
frozenarchive = {
    'object_type': 'frozenarchive',
    'required': ['id', 'name', 'description', 'creator', 'created'],
    'required_list': [('frozenfiles', 'frozenfile')],
    'optional': [],
}
freezestatus = {'object_type': 'freezestatus', 'required':
                ['freeze_id', 'flavor', 'freeze_state'], 'optional': []}
uploadfile = {'object_type': 'uploadfile', 'required':
              ['name', 'size', 'url'], 'optional': ['error']}
uploadfiles = {
    # list entry must be called 'files' for jquery fileupload plugin to work
    'object_type': 'uploadfiles',
    'required': [],
    'required_list': [('files', 'uploadfile')],
    'optional': [],
}
datatransfer = {
    'object_type': 'datatransfer',
    'required': ['transfer_id', 'action', 'protocol', 'fqdn', 'port',
                 'username', 'src', 'dst', 'password', 'key', 'status'],
    'optional': ['deltransferlink', 'viewtransferlink', 'redotransferlink',
                 'exit_code', 'flags'],
}
transferkey = {
    'object_type': 'transferkey',
    'required': ['key_id', 'created', 'type', 'bits', 'public_key'],
    'optional': ['delkeylink'],
}
sharelink = {
    'object_type': 'sharelink',
    'required': ['share_id', 'path', 'access', 'expire', 'password_hash',
                 'invites', 'created', 'owner'],
    'optional': ['viewsharelink', 'delsharelink'],
}
accessrequest = {
    'object_type': 'accessrequest',
    'required': ['client_id', 'request_type', 'target'],
    'optional': [],
}
accountreq = {'object_type': 'accountreq', 'required': [
    'id',
    'full_name',
    'email',
    'organization',
    'country',
    'state',
    'comment',
    'created',
], 'optional': []}
changedstatusjob = {'object_type': 'changedstatusjob',
                    'required': ['job_id'], 'optional': []}
saveschedulejob = {'object_type': 'saveschedulejob',
                   'required': ['job_id'], 'optional': []}
checkcondjob = {'object_type': 'checkcondjob', 'required': ['job_id']}
resubmitobj = {'object_type': 'resubmitobj', 'required': ['job_id'],
               'optional': []}
submitstatus = {'object_type': 'submitstatus', 'required':
                ['name', 'status'], 'optional': ['job_id', 'message']}
fileuploadobj = {'object_type': 'fileuploadobj',
                 'required': ['submitmrsl', 'saved', 'extract_packages',
                              'size', 'name'], 'optional': ['message']}
sandboxinfo = {'object_type': 'sandboxinfo', 'required':
               ['username', 'resource', 'jobs'], 'optional': []}
signature = {'object_type': 'signature', 'required':
             ['function', 'signature'], 'optional': []}
objects = {'object_type': 'objects', 'required': ['objects'],
           'optional': []}
jobobj = {'object_type': 'jobobj', 'required': ['jobobj'],
          'optional': []}

# a list named jobs containing job objects

resubmitobjs = {'object_type': 'resubmitobjs',
                'required_list': [('resubmitobjs', 'resubmitobj')]}
job_list = {'object_type': 'job_list', 'required_list': [('jobs', 'job'
                                                          )]}
trigger_job_list = {'object_type': 'trigger_job_list', 'required_list':
                    [('trigger_jobs', 'trigger_job'
                      )]}
trigger_log = {'object_type': 'trigger_log', 'required':
               ['log_content']}
crontab_log = {'object_type': 'crontab_log', 'required':
               ['log_content']}
crontab_listing = {'object_type': 'crontab_listing', 'required':
                   ['crontab', 'atjobs']}
filewcs = {'object_type': 'filewcs', 'required_list': [('filewcs',
                                                        'filewc')]}
filedus = {'object_type': 'filedus', 'required_list': [('filedus',
                                                        'filedu')]}
stats = {'object_type': 'stats', 'required_list': [('stats', 'stat')]}

# file_list = {"object_type": "file_list", "required_list":[("files", "file")]}

execution_histories = {'object_type': 'execution_histories',
                       'required_list': [('execution_histories',
                                          'execution_history')]}
execution_history = {'object_type': 'execution_history',
                     'required': ['queued', 'executing', 'failed',
                                  'failed_message'], 'optional': []}
dir_listing = {'object_type': 'dir_listing',
               'required_list': [('entries', 'direntry'), 'flags',
                                 'dirname_with_dir']}
dir_listings = {'object_type': 'dir_listings',
                'required_list': [('dir_listings', 'dir_listing')]}
runtimeenvironments = {'object_type': 'runtimeenvironments',
                       'required_list': [('runtimeenvironments',
                                          'runtimeenvironment')]}
peers = {'object_type': 'peers', 'required_list': [('peers', 'peer')]}
workflows = {'object_type': 'workflows'}
workflow_report = {'object_type': 'workflow_report'}
frozenarchives = {'object_type': 'frozenarchives',
                  'required_list': [('frozenarchives', 'frozenarchive'
                                     )]}
datatransfers = {'object_type': 'datatransfers',
                 'required_list': [('datatransfers', 'datatransfer'
                                    )]}
transferkeys = {'object_type': 'transferkeys',
                'required_list': [('transferkeys', 'transferkey'
                                   )]}
sharelinks = {'object_type': 'sharelinks',
              'required_list': [('sharelinks', 'sharelink'
                                 )]}
accessrequests = {'object_type': 'accessrequests',
                  'required_list': [('accessrequests', 'accessrequest'
                                     )]}
accountreqs = {'object_type': 'accountreqs', 'required_list': [('accountreqs',
                                                                'accountreq')]}
changedstatusjobs = {'object_type': 'changedstatusjobs',
                     'required_list': [('changedstatusjobs',
                                        'changedstatusjob')]}
saveschedulejobs = {'object_type': 'saveschedulejobs',
                    'required_list': [('saveschedulejobs',
                                       'saveschedulejob')]}
checkcondjobs = {'object_type': 'checkcondjobs',
                 'required_list': [('checkcondjobs', 'checkcondjob')]}
submitstatuslist = {'object_type': 'submitstatuslist',
                    'required_list': [('submitstatuslist',
                                       'submitstatus')]}
fileuploadobjs = {'object_type': 'fileuploadobjs',
                  'required_list': [('fileuploadobjs', 'fileuploadobj'
                                     )]}
sandboxinfos = {'object_type': 'sandboxinfos',
                'required_list': [('sandboxinfos', 'sandboxinfo')]}
signatures = {'object_type': 'signatures',
              'required_list': [('signatures', 'signature')]}
linklist = {'object_type': 'linklist', 'required_list': [('links',
                                                          'link')]}
multilinkline = {'object_type': 'multilinkline',
                 'required_list': [('links', 'link')]}
resource_list = {'object_type': 'resource_list',
                 'required_list': [('resources', 'resource')]}
resource_info = {'object_type': 'resource_info',
                 'required': ['unique_resource_name', 'fields', 'exes']}
upgrade_info = {'object_type': 'upgrade_info', 'required': ['text',
                                                            'commands']}
user_list = {'object_type': 'user_list', 'required_list': [('users',
                                                            'user')]}
user_info = {'object_type': 'user_info', 'required': ['user_id',
                                                      'fields']}
vgrid_info = {'object_type': 'vgrid_info', 'required': ['vgrid_name',
                                                        'fields']}
forum_threads = {'object_type': 'forum_threads',
                 'required': ['threads', 'status', 'vgrid_name']}
forum_thread_messages = {'object_type': 'forum_thread_messages',
                         'required': ['messages', 'status', 'vgrid_name'
                                      ]}
vgrid_list = {'object_type': 'vgrid_list', 'required_list': [('vgrids',
                                                              'vgrid')]}
user_stats = {'object_type': 'user_stats', 'required':
              ['disk', 'jobs', 'resources', 'certificate'], 'optional': []}
openid_status = {'object_type': 'openid_status', 'required':
                 ['server', 'status', 'error'], 'optional': []}
seafile_status = {'object_type': 'seafile_status', 'required':
                  ['server', 'status', 'error'], 'optional': ['data']}
service = {'object_type': 'service', 'required': ['name', 'targetlink'],
           'optional': []}
services = {'object_type': 'services',
            'required_list': [('services', 'service')]}
table_pager = {'object_type': 'table_pager', 'required': ['entry_name'],
               'optional': ['id_prefix', 'default_entries']}
object_types = {'object_type': 'object_types',
                'required_list': [('object_types', 'objects')]}
image_meta = {'object_type': 'image_meta', 'required': [
    'image_type',
    'preview_image_url',
    'preview_histogram',
    'base_path',
    'path',
    'name',
    'extension',
    'offset',
    'x_dimension',
    'y_dimension',
    'preview_x_dimension',
    'preview_y_dimension',
    'preview_cutoff_min',
    'preview_cutoff_max',
    'preview_image_scale',
    'mean_value',
    'median_value',
    'file_md5sum',
    'data_type',
], 'optional': []}
volume_meta = {'object_type': 'volume_meta', 'required': [
    'image_type',
    'volume_type',
    'preview_histogram',
    'base_path',
    'path',
    'name',
    'extension',
    'offset',
    'x_dimension',
    'y_dimension',
    'z_dimension',
    'preview_x_dimension',
    'preview_y_dimension',
    'preview_z_dimension',
    'preview_cutoff_min',
    'preview_cutoff_max',
    'mean_value',
    'median_value',
    'file_md5sum',
    'data_type',
], 'optional': []}

image_settings_list = {'object_type': 'image_settings_list',
                       'required':
                       ['extension_list', 'image_settings_status_list',
                        'volume_settings_status_list',
                        'image_settings_progress_list',
                        'volume_settings_progress_list',
                        'image_count_list', 'volume_count_list'],
                       'optional': []}
image_setting = {'object_type': 'image_setting', 'required': [
    'image_type',
    'extension',
    'image_settings_status',
    'image_settings_update_progress',
    'volume_settings_status',
    'volume_settings_update_progress',
    'settings_recursive',
    'image_count',
    'volume_slice_filepattern',
    'offset',
    'x_dimension',
    'y_dimension',
    'z_dimension',
    'preview_x_dimension',
    'preview_y_dimension',
    'preview_z_dimension',
    'preview_cutoff_min',
    'preview_cutoff_max',
    'data_type',
], 'optional': []}
valid_types_list = [
    start,
    end,
    timing_info,
    title,
    text,
    verbatim,
    binary,
    script_status,
    header,
    sectionheader,
    link,
    error_text,
    job,
    trigger_job,
    warning,
    job_list,
    job_dict,
    trigger_job_list,
    trigger_log,
    crontab_log,
    crontab_listing,
    direntry,
    file,
    progress,
    progress_list,
    directory,
    dir_listing,
    html_form,
    dir_listings,
    file_output,
    runtimeenvironment,
    runtimeenvironments,
    peer,
    peers,
    workflow,
    workflows,
    workflow_report,
    frozenfile,
    frozenarchive,
    frozenarchives,
    freezestatus,
    uploadfile,
    uploadfiles,
    datatransfer,
    datatransfers,
    transferkey,
    transferkeys,
    sharelink,
    sharelinks,
    accessrequest,
    accessrequests,
    accountreq,
    accountreqs,
    file_not_found,
    filewc,
    filewcs,
    filedu,
    filedus,
    changedstatusjobs,
    changedstatusjob,
    saveschedulejobs,
    saveschedulejob,
    checkcondjobs,
    checkcondjob,
    resubmitobj,
    resubmitobjs,
    submitstatuslist,
    submitstatus,
    sandboxinfos,
    sandboxinfo,
    fileuploadobjs,
    fileuploadobj,
    list,
    project_info,
    stats,
    stat,
    linklist,
    multilinkline,
    signatures,
    signature,
    object_types,
    objects,
    jobobj,
    resource_list,
    resource_info,
    upgrade_info,
    user_list,
    user_info,
    vgrid_info,
    forum_threads,
    forum_thread_messages,
    vgrid_list,
    user_stats,
    openid_status,
    seafile_status,
    service,
    services,
    table_pager,
    image_meta,
    volume_meta,
    image_setting,
    image_settings_list,
]

# valid_types_dict = {"title":title, "link":link, "header":header}

# autogenerate dict based on list. Dictionary access is prefered to allow
# direct access to the member instead of O(n) loops when validate runs

# TODO: rework this validation setup to eliminate the deprecated `eval` call
#       and remove the implicit binding between var name and object_type val
#       in the above. E.g. that we MUST have list = {object_type = 'list', ...}

valid_types_dict = {}
for valid_type in valid_types_list:
    valid_types_dict[valid_type['object_type']] = \
        eval(valid_type['object_type'])


def get_object_type_info(object_type_list):
    if len(object_type_list) == 0:

        # all, make list of strings

        valid_types_list_strings = []
        for ele in valid_types_list:
            valid_types_list_strings.append(ele['object_type'])
        object_type_list = valid_types_list_strings
    out = []
    for object_t in object_type_list:
        if object_t in valid_types_dict:
            try:
                out.append((object_t, valid_types_dict[object_t]))
            except:
                out.append((object_t,
                            "Information about '%s' object type not available"
                            % object_t))
        else:
            out.append((object_t,
                        "Information about '%s' object type not available"
                        % object_t))
    return out


def validate(input_object):
    """ validate input_object """

    if not type(input_object) == type([]):

        # (ret_val, ret_msg) = out
        # (ret_val, ret_msg) = validate(input_object[0])
        # if not ret_val:
            #  return (ret_val, ret_msg)
            # except Exception, e:

        return (False, 'validate object must be a list' % ())

    for obj in input_object:
        try:
            'object_type' in obj
        except Exception as exc:
            return (False,
                    'input_object does not have object_type key %s (%s)'
                    % (obj, exc))
        try:
            if obj['object_type'] not in valid_types_dict:
                return (False,
                        'specified object_type: %s is not a valid object_type'
                        % obj['object_type'])

            this_object_type = obj['object_type']
            valid_object_type = valid_types_dict[this_object_type]
            if 'required' in valid_object_type:
                for req in valid_object_type['required']:
                    if req not in obj:
                        return (False,
                                'Required key %s for object_type %s not found!'
                                % (req, this_object_type))
                for checkele in obj:
                    if checkele == 'object_type':
                        continue

                    # if not checkele in valid_object_type["required"] and not checkele in valid_object_type["optional"]:
                        # return (False, "%s has an invalid member %s, valid required members: %s, valid optional members: %s" % (obj, checkele, ", ".join(valid_object_type["required"]), ", ".join(valid_object_type["optional"])))

            if 'required_list' in valid_object_type:
                for (req, reqtype) in valid_object_type['required_list']:
                    if req not in obj:
                        return (False,
                                'Required list  %s for object_type %s not found!'
                                % (req, this_object_type))

                    # check it is a list

                    if not type(obj[req]) == type([]):
                        return (False, 'Required list  %s is not a list'
                                % req)
                    for list_entry in obj[req]:
                        if 'object_type' not in list_entry:
                            return (False,
                                    '%s key does not have required object_type member'
                                    % req)
                        if not list_entry['object_type'] == reqtype:
                            return (False,
                                    'elements in %s is not of required type %s'
                                    % (req, reqtype))
        except Exception as exc:
            return (False, 'exc %s, %s' % (exc, obj))
    return (True, '')
