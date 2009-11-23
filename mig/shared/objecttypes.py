#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# objecttypes - [insert a few words of module description on this line]
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

""" Defines valid objecttypes and provides a method to verify if an object is correct """

start = {'object_type': 'start', 'required': ['headers'], 'optional': []}
title = {'object_type': 'title', 'required': ['text'],
         'optional': ['javascript', 'bodyfunctions']}
text = {'object_type': 'text', 'required': ['text'], 'optional': []}
verbatim = {'object_type': 'verbatim', 'required': ['text'],
            'optional': []}
binary = {'object_type': 'binary', 'required': ['data'],
            'optional': []}
header = {'object_type': 'header', 'required': ['text'], 'optional': []}
sectionheader = {'object_type': 'sectionheader', 'required': ['text'],
                 'optional': []}
link = {'object_type': 'link', 'required': ['destination', 'text'],
        'optional': []}
error_text = {'object_type': 'error_text', 'required': ['text'],
              'optional': []}
job = {'object_type': 'job', 'required': ['job_id',
       'execution_histories'], 'optional': []}
warning = {'object_type': 'warning', 'required': ['text'],
           'optional': []}
direntry = {'object_type': 'direntry', 'required': ['name', 'type'],
            'optional': []}
file = {'object_type': 'file', 'required': ['name'], 'optional': []}
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
filewc = {'object_type': 'filewc', 'required': ['name', 'size'],
          'optional': []}
list = {'object_type': 'list', 'required': ['list'], 'optional': []}
file_not_found = {'object_type': 'file_not_found', 'required': ['name'
                  ], 'optional': []}
file_output = {'object_type': 'file_output', 'required': ['lines'],
               'optional': ['path']}
environment = {'object_type': 'environment', 'required': ['name',
               'example', 'description'], 'optional': []}
software = {'object_type': 'software', 'required': ['name', 'icon',
            'url', 'description', 'version'], 'optional': []}
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
changedstatusjob = {'object_type': 'changedstatusjob',
                    'required': ['job_id'], 'optional': []}
saveschedulejob = {'object_type': 'saveschedulejob',
                   'required': ['job_id'], 'optional': []}
resubmitobj = {'object_type': 'resubmitobj', 'required': ['job_id'],
               'optional': []}
submitstatus = {'object_type': 'submitstatus', 'required': ['name',
                'status'], 'optional': ['job_id', 'message']}
fileuploadobj = {'object_type': 'fileuploadobj',
                 'required': ['submitmrsl', 'saved', 'extract_packages'
                 , 'size', 'name'], 'optional': ['message']}
sandboxinfo = {'object_type': 'sandboxinfo', 'required': ['username',
               'resource', 'jobs'], 'optional': []}
signature = {'object_type': 'signature', 'required': ['function',
             'signature'], 'optional': []}
objects = {'object_type': 'objects', 'required': ['objects'],
           'optional': []}
jobobj = {'object_type': 'jobobj', 'required': ['jobobj'],
          'optional': []}

# a list named jobs containing job objects

resubmitobjs = {'object_type': 'resubmitobjs',
                'required_list': [('resubmitobjs', 'resubmitobj')]}
job_list = {'object_type': 'job_list', 'required_list': [('jobs', 'job'
            )]}
filewcs = {'object_type': 'filewcs', 'required_list': [('filewcs',
           'filewc')]}
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
changedstatusjobs = {'object_type': 'changedstatusjobs',
                     'required_list': [('changedstatusjobs',
                     'changedstatusjob')]}
saveschedulejobs = {'object_type': 'saveschedulejobs',
                    'required_list': [('saveschedulejobs',
                    'saveschedulejob')]}
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
vgrid_list = {'object_type': 'vgrid_list', 'required_list': [('vgrids',
              'vgrid')]}
object_types = {'object_type': 'object_types',
                'required_list': [('object_types', 'objects')]}

valid_types_list = [
    start,
    title,
    text,
    verbatim,
    binary,
    header,
    sectionheader,
    link,
    error_text,
    job,
    warning,
    job_list,
    direntry,
    file,
    directory,
    dir_listing,
    html_form,
    dir_listings,
    file_output,
    runtimeenvironment,
    runtimeenvironments,
    file_not_found,
    filewc,
    filewcs,
    changedstatusjobs,
    changedstatusjob,
    saveschedulejobs,
    saveschedulejob,
    resubmitobj,
    resubmitobjs,
    submitstatuslist,
    submitstatus,
    sandboxinfos,
    sandboxinfo,
    fileuploadobjs,
    fileuploadobj,
    list,
    stats,
    stat,
    linklist,
    multilinkline,
    signatures,
    signature,
    object_types,
    objects,
    jobobj,
    vgrid_list,
    ]

# valid_types_dict = {"title":title, "link":link, "header":header}

# autogenerate dict based on list. Dictionary access is prefered to allow
# direct access to the member instead of O(n) loops when validate runs

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
        if valid_types_dict.has_key(object_t):
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
            obj.has_key('object_type')
        except Exception, exc:
            return (False,
                    'input_object does not have object_type key %s (%s)'
                     % (obj, exc))
        try:
            if not valid_types_dict.has_key(obj['object_type']):
                return (False,
                        'specified object_type: %s is not a valid object_type'
                         % obj['object_type'])

            this_object_type = obj['object_type']
            valid_object_type = valid_types_dict[this_object_type]
            if valid_object_type.has_key('required'):
                for req in valid_object_type['required']:
                    if not obj.has_key(req):
                        return (False,
                                'Required key %s for object_type %s not found!'
                                 % (req, this_object_type))
                for checkele in obj.keys():
                    if checkele == 'object_type':
                        continue

                    # if not checkele in valid_object_type["required"] and not checkele in valid_object_type["optional"]:
                        # return (False, "%s has an invalid member %s, valid required members: %s, valid optional members: %s" % (obj, checkele, ", ".join(valid_object_type["required"]), ", ".join(valid_object_type["optional"])))

            if valid_object_type.has_key('required_list'):
                for (req, reqtype) in valid_object_type['required_list'
                        ]:
                    if not obj.has_key(req):
                        return (False,
                                'Required list  %s for object_type %s not found!'
                                 % (req, this_object_type))

                    # check it is a list

                    if not type(obj[req]) == type([]):
                        return (False, 'Required list  %s is not a list'
                                 % req)
                    for list_entry in obj[req]:
                        if not list_entry.has_key('object_type'):
                            return (False,
                                    '%s key does not have required object_type member'
                                     % req)
                        if not list_entry['object_type'] == reqtype:
                            return (False,
                                    'elements in %s is not of required type %s'
                                     % (req, reqtype))
        except Exception, exc:
            return (False, 'exc %s, %s' % (exc, obj))
    return (True, '')


