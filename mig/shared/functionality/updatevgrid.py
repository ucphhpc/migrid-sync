#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# updatevgrid - update or repair vgrid components
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

"""Update a VGrid with missing components"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import zip
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import csrf_field
from mig.shared.fileio import make_symlink
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.vgrid import vgrid_is_owner, vgrid_list, vgrid_set_entities
from mig.shared.vgridaccess import get_vgrid_map, VGRIDS, OWNERS
from mig.shared.functionality.createvgrid import create_scm, create_tracker, \
    create_forum


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'caching': ['true']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Update %s Components" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Update %s Components' % label})
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

    vgrid_name = accepted['vgrid_name'][-1]
    caching = (accepted['caching'][-1].lower() in ('true', 'yes'))

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
                               })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not vgrid_is_owner(vgrid_name, client_id, configuration):

        output_objects.append({'object_type': 'error_text', 'text':
                               'Only owners of %s can administrate it.' %
                               vgrid_name})

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'vgrid_label': label,
                        'vgrid_name': vgrid_name,
                        'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit}
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <form method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="vgrid_name" value="%(vgrid_name)s"/>
        <input type="hidden" name="request_type" value="vgridowner"/>
        <input type="text" size=50 name="request_text" />
        <input type="hidden" name="output_format" value="html" />
        <input type="submit" value="Request %(vgrid_label)s access" />
        </form>
    ''' % fill_helpers})

        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                                            vgrid_name)) + os.sep
    public_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                                     vgrid_name)) + os.sep
    public_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                                     vgrid_name, '.vgridscm')) + os.sep
    public_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                                     vgrid_name, '.vgridtracker')) + os.sep
    private_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                     vgrid_name)) + os.sep
    private_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                     vgrid_name)) + os.sep
    private_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                     vgrid_name, '.vgridscm')) + os.sep
    private_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                     vgrid_name, '.vgridtracker')) + os.sep
    private_forum_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                                     vgrid_name, '.vgridforum')) + os.sep
    vgrid_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                     vgrid_name)) + os.sep
    vgrid_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                     vgrid_name, '.vgridscm')) + os.sep
    vgrid_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                     vgrid_name, '.vgridtracker')) + os.sep
    vgrid_files_link = os.path.join(configuration.user_home, client_dir,
                                    vgrid_name)

    output_objects.append({'object_type': 'text', 'text':
                           'Updating %s %s components ...' %
                           (label, vgrid_name)})

    # Try to create all base directories used for vgrid files

    for path in (base_dir, public_files_dir, private_files_dir, vgrid_files_dir):
        try:
            os.mkdir(path)
        except Exception as exc:
            pass

    # Prepare for vgrid map consistency check as well

    logger.info("check vgrid map with caching %s" % caching)
    vgrid_map = get_vgrid_map(configuration, caching=caching)

    # Try entity creation or repair

    output_objects.append({'object_type': 'text', 'text':
                           'Participant update warnings:'})
    for kind in ['owners', 'members', 'resources', 'triggers']:
        (list_status, id_list) = vgrid_list(vgrid_name, kind, configuration,
                                            recursive=False,
                                            allow_missing=False)
        logger.info("vgrid_list returned %s : %s" % (list_status, id_list))
        dirty = False
        if not list_status:
            dirty = True
            if kind == 'owners':
                id_list = [client_id]
            else:
                id_list = []
        elif kind == 'owners':
            # NOTE: under heavy load vgrid cache update can miss owners
            # TODO: investigate where the probable underlying race lies
            vgrid_dict = vgrid_map[VGRIDS].get(vgrid_name, {})
            cached_entries = vgrid_dict[OWNERS]
            missing_entries = [i for i in id_list if not i in cached_entries]
            if kind == 'owners' and missing_entries:
                logger.info("add missing owner(s) for %s in cache: %s" %
                            (vgrid_name, missing_entries))
                dirty = True
                id_list = vgrid_dict[OWNERS] + missing_entries
            else:
                logger.debug("all owner(s) %s already in cache: %s" %
                             (id_list, cached_entries))

        if dirty:
            (set_status, set_msg) = vgrid_set_entities(configuration,
                                                       vgrid_name, kind,
                                                       id_list,
                                                       (kind != 'owners'))
            if not set_status:
                output_objects.append({'object_type': 'error_text', 'text':
                                       'Could not create/fix %s list: %s'
                                       % (kind, set_msg)})

    # TODO: add any missing public/private web links, too
    output_objects.append({'object_type': 'text', 'text':
                           'Link check warnings:'})
    if not os.path.exists(vgrid_files_link):
        src = vgrid_files_dir
        if not make_symlink(src, vgrid_files_link, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to %s files!' %
                                   label})

    user_public_base = os.path.join(configuration.user_home,
                                    client_dir, 'public_base')
    user_private_base = os.path.join(configuration.user_home,
                                     client_dir, 'private_base')

    # Try to create all base directories used for vgrid web dirs

    for path in (user_public_base, user_private_base):
        try:
            os.mkdir(path)
        except Exception as exc:
            pass

    public_base_dst = os.path.join(user_public_base, vgrid_name)
    if not os.path.exists(public_base_dst):
        if not make_symlink(public_files_dir, public_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to public_base dir!'
                                   })
    private_base_dst = os.path.join(user_private_base, vgrid_name)
    if not os.path.exists(private_base_dst):
        if not make_symlink(private_files_dir, private_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to private_base dir!'
                                   })

    wwwpublic_vgrid_link = os.path.join(configuration.wwwpublic, 'vgrid',
                                        vgrid_name)
    if not os.path.exists(wwwpublic_vgrid_link):
        if not make_symlink(public_files_dir, wwwpublic_vgrid_link, logger,
                            force=True):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create public web alias %s' %
                                   vgrid_name})

    # Try component creation or repair

    all_scm_dirs = ['', '', '']
    if configuration.hg_path and configuration.hgweb_scripts:

        # create participant scm repo in the vgrid shared dir

        output_objects.append({'object_type': 'text', 'text':
                               'SCM update warnings:'})
        all_scm_dirs = [public_scm_dir, private_scm_dir, vgrid_scm_dir]
        for scm_dir in all_scm_dirs:
            tmp_output = []
            create_scm(configuration, client_id, vgrid_name, scm_dir,
                       tmp_output, repair=True)
            output_objects += tmp_output

    all_tracker_dirs = ['', '', '']
    if configuration.trac_admin_path:

        # create participant tracker in the vgrid shared dir

        output_objects.append({'object_type': 'text', 'text':
                               'Tracker update warnings:'})
        all_tracker_dirs = [public_tracker_dir, private_tracker_dir,
                            vgrid_tracker_dir]
        for (tracker_dir, scm_dir) in zip(all_tracker_dirs, all_scm_dirs):
            tmp_output = []
            create_tracker(configuration, client_id, vgrid_name, tracker_dir,
                           scm_dir, tmp_output, repair=True)
            output_objects += tmp_output

    # create participant forum in the vgrid shared dir

    output_objects.append({'object_type': 'text', 'text':
                           'Forum update warnings:'})
    for forum_dir in [private_forum_dir]:
        tmp_output = []
        create_forum(configuration, client_id, vgrid_name, forum_dir,
                     tmp_output, repair=True)
        output_objects += tmp_output

    output_objects.append({'object_type': 'text', 'text':
                           '%s %s updated!' % (label, vgrid_name)})
    output_objects.append({'object_type': 'link',
                           'destination': 'adminvgrid.py?vgrid_name=%s' %
                           vgrid_name,
                           'class': 'adminlink iconspace',
                           'title': 'Administrate your %s' % label,
                           'text': 'Administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


def dummy_owner_check(vgrid_name, client_id, configuration):
    """Fake owner check"""
    return True


if __name__ == "__main__":
    # Force update of all vgrids if run from command line
    # Useful in relation to e.g. dist-upgrades breaking Moin and Mercurial
    #

    import sys

    from mig.shared.conf import get_configuration_object
    from mig.shared.defaults import default_vgrid
    from mig.shared.output import txt_format
    from mig.shared.vgridaccess import get_vgrid_map_vgrids

    # use dummy owner check
    vgrid_is_owner = dummy_owner_check
    try:
        configuration = get_configuration_object()
    except IOError as ioe:
        print("Error loading conf: %s" % ioe)
        print("maybe you need to set MIG_CONF environment?")
        sys.exit(1)

    script = __file__
    query = ""
    if sys.argv[1:]:
        client_id = sys.argv[1]
    else:
        print("you must supply a valid user ID to fake run as")
        sys.exit(1)
    extra_environment = {
        'REQUEST_METHOD': 'GET',
        'SSL_CLIENT_S_DN': client_id,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'PATH': '/bin:/usr/bin:/usr/local/bin',
    }

    extra_environment['SCRIPT_FILENAME'] = script
    extra_environment['QUERY_STRING'] = query
    extra_environment['REQUEST_URI'] = '%s%s' % (script, query)
    extra_environment['REQUEST_METHOD'] = 'POST'
    extra_environment['SCRIPT_URL'] = script
    extra_environment['SCRIPT_NAME'] = script
    extra_environment['SCRIPT_URI'] = 'https://localhost/cgi-bin/%s' % script
    os.environ.update(extra_environment)

    all_vgrids = get_vgrid_map_vgrids(configuration)
    for vgrid_name in all_vgrids:
        if vgrid_name == default_vgrid:
            continue
        print("update %s" % vgrid_name)
        ret_msg = ''
        (output_objects, ret_val) = main(client_id, {'vgrid_name':
                                                     [vgrid_name]})
        print(txt_format(configuration, ret_val, ret_msg, output_objects))
