#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridman - backend to manage vgrids
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""VGrid management back end functionality"""

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid, all_vgrids, default_pager_entries, \
     csrf_field
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_settings
from shared.useradm import get_full_user_map
from shared.vgrid import vgrid_create_allowed
from shared.vgridaccess import get_vgrid_map, VGRIDS, OWNERS, MEMBERS, SETTINGS

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {'operation': ['show']}
    return ['vgrids', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    status = returnvalues.OK
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%ss" % configuration.site_vgrid_label
    title_entry['text'] = "%s management" % label
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

    operation = accepted['operation'][-1]

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    vgrid_items, active_vgrid_links = [], []
    member_list = {'object_type': 'vgrid_list', 'vgrids': vgrid_items,
                   'components': active_vgrid_links}

    # Check if user wants advanced VGrid component links

    settings = load_settings(client_id, configuration)        
    collaboration_links = settings.get('SITE_COLLABORATION_LINKS', 'default')
    if not collaboration_links in configuration.site_collaboration_links or \
           collaboration_links == 'default':
        active_vgrid_links += configuration.site_default_vgrid_links
    elif collaboration_links == 'advanced':
        active_vgrid_links += configuration.site_advanced_vgrid_links

    # General fill helpers including CSRF fields

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers =  {'vgrid_label': configuration.site_vgrid_label,
                     'form_method': form_method,
                     'csrf_field': csrf_field,
                     'csrf_limit': csrf_limit}

    if operation in show_operations:

        # jquery support for tablesorter and confirmation on request and leave
        # table initially sorted by col. 2 (admin), then 3 (member), then 0 (name)

        refresh_call = 'ajax_vgridman("%s", %s)' % \
                       (configuration.site_vgrid_label, active_vgrid_links)
        table_spec = {'table_id': 'vgridtable', 'sort_order':
                      '[[2,1],[3,1],[0,0]]', 'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration, 
                                                        [table_spec])
        if operation == "show":
            add_ready += refresh_call
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        # Append VGrid alias note if custom
        if configuration.site_vgrid_label != 'VGrid':
            label += ' (i.e. VGrids)'
        output_objects.append({'object_type': 'header', 'text': label})
        output_objects.append({'object_type': 'text', 'text'
                              : '''
    %ss share files, a number of collaboration tools and resources. Members can access web pages, files, tools and resources. Owners can additionally edit pages, as well as add and remove members or resources.
    ''' % configuration.site_vgrid_label
                           })

        if configuration.site_vgrid_label != 'VGrid':
            output_objects.append({'object_type': 'text', 'text'
                              : """Please note that for historical reasons %ss are
    also referred to as VGrids in some contexts.""" % \
                                   configuration.site_vgrid_label})

        output_objects.append({'object_type': 'sectionheader', 'text'
                              : '%ss managed on this server' % \
                               configuration.site_vgrid_label})

        # Helper forms for requests and removes

        for post_type in ["vgridowner", "vgridmember"]:
            target_op = 'sendrequestaction'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            helper = html_post_helper('req%s' % post_type,
                                      '%s.py' % target_op,
                                      {'vgrid_name': '__DYNAMIC__',
                                       'request_type': post_type,
                                       'request_text': '',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
        for post_type in ["vgridowner", "vgridmember"]:
            target_op = 'rm%s' % post_type
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            helper = html_post_helper(target_op,
                                      '%s.py' % target_op,
                                      {'vgrid_name': '__DYNAMIC__',
                                       'cert_id': client_id,
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})

        output_objects.append({'object_type': 'table_pager', 'entry_name': '%ss' % \
                               configuration.site_vgrid_label,
                               'default_entries': default_pager_entries})

    if operation in list_operations:
        vgrid_map = get_vgrid_map(configuration)
        vgrid_list = vgrid_map[VGRIDS].keys()
        
        # Iterate through vgrids and print details for each

        if 'monitor' in active_vgrid_links:
            vgrid_list = [all_vgrids] + vgrid_list
        else:
            vgrid_list.remove(default_vgrid)
        # User vgrid_list here to include default and all mangling above
        for vgrid_name in vgrid_list:
            vgrid_dict = vgrid_map[VGRIDS].get(vgrid_name, {})
            settings_dict = dict(vgrid_dict.get(SETTINGS, []))
            if settings_dict.get('hidden', False):
                logger.info("skip hidden vgrid %s" % vgrid_name)
                continue
            vgrid_obj = {'object_type': 'vgrid', 'name': vgrid_name}

            if vgrid_name == default_vgrid:

                # Everybody is member and allowed to see statistics, Noone
                # can own it or leave it. Do not add any page links.

                vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                                   'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                                                   % vgrid_name,
                                                   'class': 'monitorlink iconspace',
                                                   'title': 'View %s monitor' % \
                                                   vgrid_name, 
                                                   'text': 'View'}
                vgrid_obj['memberlink'] = {'object_type': 'link',
                                           'destination':'',
                                           'class': 'infolink iconspace',
                                           'title': 'Every user is member of the %s %s' \
                                           % (default_vgrid,
                                              configuration.site_vgrid_label),
                                           'text': ''}
                vgrid_obj['administratelink'] = {'object_type': 'link',
                                                 'destination':'',
                                                 'class': 'infolink iconspace',
                                                 'title': 'Nobody owns the %s %s' \
                                                 % (default_vgrid,
                                                    configuration.site_vgrid_label),
                                                 'text': ''}
                vgrid_obj['viewvgridlink'] = {'object_type': 'link',
                                              'destination':'viewvgrid.py?vgrid_name=%s' % \
                                              vgrid_name,
                                              'class': 'infolink iconspace',
                                              'title': 'View details for the %s %s' \
                                              % (default_vgrid,
                                                 configuration.site_vgrid_label),
                                              'text': ''}
                vgrid_items.append(vgrid_obj)
                continue
            elif vgrid_name == all_vgrids:

                # Only show global monitor link for all_vgrids, Noone
                # can own it or leave it. Do not add any page links.

                vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                                   'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                                                   % vgrid_name,
                                                   'class': 'monitorlink iconspace',
                                                   'title': 'View global monitor', 
                                                   'text': 'View'}
                vgrid_obj['memberlink'] = {'object_type': 'link',
                                           'destination':'',
                                           'class': 'infolink iconspace',
                                           'title': 'Not a real %s - only for global monitor' % \
                                           configuration.site_vgrid_label,
                                           'text': ''}
                vgrid_obj['administratelink'] = {'object_type': 'link',
                                                 'destination':'',
                                                 'class': '',
                                                 'title': '',
                                                 'text': ''}
                vgrid_obj['viewvgridlink'] = {'object_type': 'link',
                                              'destination':'',
                                              'class': 'infolink iconspace',
                                              'title': 'Not a real %s - only for global monitor' % \
                                              configuration.site_vgrid_label,
                                              'text': ''}
                vgrid_items.append(vgrid_obj)
                continue

            # links for everyone: public pages and membership request

            vgrid_obj['publicscmlink'] = {'object_type': 'link',
                    'destination': '%s/vgridpublicscm/%s'\
                                           % (configuration.migserver_http_url,
                                              vgrid_name),
                                           'class': 'scmlink public iconspace',
                                           'title': 'Open %s public SCM' % \
                                           vgrid_name,
                                           'text': 'Open'}
            vgrid_obj['publictrackerlink'] = {'object_type': 'link',
                    'destination': '%s/vgridpublictracker/%s'\
                                           % (configuration.migserver_http_url,
                                              vgrid_name),
                                           'class': 'trackerlink public iconspace',
                                           'title': 'Open %s public tracker' % \
                                           vgrid_name,
                                           'text': 'Open'}
            vgrid_obj['enterpubliclink'] = {'object_type': 'link',
                                            'destination':
                                            '%s/vgrid/%s/path/index.html' % \
                                            (configuration.migserver_http_url,
                                             vgrid_name),
                                            'class': 'urllink member iconspace',
                                            'title': 'View public %s web page' % \
                                            vgrid_name,
                                            'text': 'View'}

            # Link to show vgrid details

            vgrid_obj['viewvgridlink'] = \
                                       {'object_type': 'link',
                                        'destination': 'viewvgrid.py?vgrid_name=%s' % \
                                        vgrid_name,
                                        'class': 'infolink iconspace',
                                        'title': 'View details for the %s %s' \
                                        % (vgrid_name,
                                           configuration.site_vgrid_label),
                                        'text': ''}

            # link to become member: overwritten later for members

            vgrid_obj['memberlink'] = {
                'object_type': 'link',
                'destination':
                "javascript: confirmDialog(%s, '%s', '%s', %s);" % \
                ('reqvgridmember', "Request membership of " + vgrid_name + \
                 ":<br/>\nPlease write a message to the owners (field below).",
                 'request_text', "{vgrid_name: '%s'}" % vgrid_name),
                'class': 'addlink iconspace',
                'title': 'Request membership of %s' % vgrid_name,
                'text': ''}

            # link to become owner: overwritten later for owners

            vgrid_obj['administratelink'] = {
                'object_type': 'link',
                'destination':
                "javascript: confirmDialog(%s, '%s', '%s', %s);" % \
                ('reqvgridowner', "Request ownership of " + vgrid_name + \
                 ":<br/>\nPlease write a message to the owners (field below).",
                 'request_text', "{vgrid_name: '%s'}" % vgrid_name),
                'class': 'addadminlink iconspace',
                'title': 'Request ownership of %s' % vgrid_name,
                'text': ''}

            # members/owners are allowed to view private pages and monitor

            if client_id in vgrid_dict[OWNERS] + vgrid_dict[MEMBERS]:
                vgrid_obj['enterprivatelink'] = {'object_type': 'link',
                                                 'destination':
                                                 '../vgrid/%s/path/index.html' % \
                                                 vgrid_name,
                                                 'class': 'urllink owner iconspace',
                                                 'title':
                                                 'View private %s web page' % \
                                                 vgrid_name, 
                                                 'text': 'View'}
                vgrid_obj['sharedfolderlink'] = {'object_type': 'link',
                                                 'destination':
                                                 'fileman.py?path=%s/' % vgrid_name,
                                                 'class': 'sharedfolderlink iconspace',
                                                 'title': 'Open shared %s folder' \
                                                 % vgrid_name, 
                                                 'text': 'Open'}
                vgrid_obj['memberscmlink'] = {'object_type': 'link',
                                              'destination': '/vgridscm/%s' % \
                                              vgrid_name,
                                              'class': 'scmlink member iconspace',
                                              'title': 'View %s members scm' % \
                                              vgrid_name,
                                              'text': 'View'}
                vgrid_obj['membertrackerlink'] = {'object_type': 'link',
                                              'destination': '/vgridtracker/%s' % \
                                              vgrid_name,
                                              'class': 'trackerlink member iconspace',
                                              'title': 'View %s members tracker' % \
                                              vgrid_name,
                                              'text': 'View'}
                vgrid_obj['privateforumlink'] = {'object_type': 'link',
                                                 'destination':
                                                 'vgridforum.py?vgrid_name=%s' % \
                                                 vgrid_name,
                                                 'class': 'forumlink iconspace',
                                                 'title': 'Open %s private forum' \
                                                 % vgrid_name, 
                                                   'text': 'Open'}
                vgrid_obj['privateworkflowslink'] = {'object_type': 'link',
                                                 'destination':
                                                 'vgridworkflows.py?vgrid_name=%s' % \
                                                 vgrid_name,
                                                 'class': 'workflowslink iconspace',
                                                 'title': 'Open %s private workflows' \
                                                 % vgrid_name, 
                                                   'text': 'Open'}
                vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                                   'destination':
                                                   'showvgridmonitor.py?vgrid_name=%s'\
                                                   % vgrid_name,
                                                   'class': 'monitorlink iconspace',
                                                   'title': 'View %s monitor' % \
                                                   vgrid_name, 
                                                   'text': 'View'}

                # to leave this VGrid (remove ourselves). Note that we are
                # going to overwrite the link later for owners.

                vgrid_obj['memberlink'].update({
                    'destination':
                    "javascript: confirmDialog(%s, '%s', %s, %s);" % \
                    ('rmvgridmember', "Really leave " + vgrid_name + "?",
                     'undefined',
                     "{vgrid_name: '%s'}" % vgrid_name),
                    'class': 'removelink iconspace',
                    'title': 'Leave %s members' % vgrid_name, 
                    })

            # owners are allowed to edit pages and administrate

            if client_id in vgrid_dict[OWNERS]:
                vgrid_obj['ownerscmlink'] = {'object_type': 'link',
                                             'destination': '/vgridownerscm/%s' % \
                                             vgrid_name,
                                             'class': 'scmlink owner iconspace',
                                             'title': 'View %s owners scm' % \
                                             vgrid_name,
                                             'text': 'View'}
                vgrid_obj['ownertrackerlink'] = {'object_type': 'link',
                                             'destination': '/vgridownertracker/%s' % \
                                             vgrid_name,
                                             'class': 'trackerlink owner iconspace',
                                             'title': 'View %s owners tracker' % \
                                             vgrid_name,
                                             'text': 'View'}

                # correct the link to leave the VGrid

                vgrid_obj['memberlink'].update({
                    'destination':
                    "javascript: confirmDialog(%s, '%s', %s, %s);" % \
                    ('rmvgridowner', "Really leave " + vgrid_name + "?",
                     'undefined', "{vgrid_name: '%s'}" % vgrid_name),
                    'class': 'removeadminlink iconspace',
                    'title': 'Leave %s owners' % vgrid_name
                    })

                # add more links: administrate and edit pages

                vgrid_obj['administratelink'] = {'object_type': 'link',
                                                 'destination': 'adminvgrid.py?vgrid_name=%s'\
                                                 % vgrid_name,
                                                 'class': 'adminlink iconspace',
                                                 'title': 'Administrate %s' % vgrid_name,
                                                 'text': ''}
                vgrid_obj['editprivatelink'] = {'object_type': 'link',
                                                'destination': 'fileman.py?path=private_base/%s/'\
                                                % vgrid_name,
                                                'class': 'editlink owner iconspace',
                                                'title': 'Edit private %s web page' % vgrid_name,
                                                'text': 'Edit'}
                vgrid_obj['editpubliclink'] = {'object_type': 'link',
                                               'destination': 'fileman.py?path=public_base/%s/'\
                                               % vgrid_name,
                                               'class': 'editlink member iconspace',
                                               'title': 'Edit public %s web page' % vgrid_name,
                                               'text': 'Edit'}


            vgrid_items.append(vgrid_obj)

    if operation == "show":
        # insert dummy placeholder to build table
        vgrid_obj = {'object_type': 'vgrid', 'name': default_vgrid}
        for field in active_vgrid_links:
            vgrid_obj[field] = ''
        vgrid_items.append(vgrid_obj)

    output_objects.append(member_list)

    if operation in show_operations:
        user_map = get_full_user_map(configuration)
        user_dict = user_map.get(client_id, None)
        # Optional limitation of create vgrid permission
        if user_dict and vgrid_create_allowed(configuration, user_dict):
            output_objects.append({'object_type': 'sectionheader', 'text'
                                   : 'Additional %ss' % \
                                   configuration.site_vgrid_label})

            output_objects.append(
                {'object_type': 'text', 'text':
                 '''Please enter a name for the new %(label)s to add, using slashes to
     specify nesting. I.e. if you own a %(label)s called ABC, you can create a
     sub-%(label)s called DEF by entering ABC/DEF below.''' % \
                 {'label': configuration.site_vgrid_label}})
            
            target_op = 'createvgrid'
            csrf_token = make_csrf_token(configuration, form_method, target_op,
                                         client_id, csrf_limit)
            fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': '''
        <form method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="text" size=40 name="vgrid_name" />
        <input type="hidden" name="output_format" value="html" />
        <input type="submit" value="Create %(vgrid_label)s" />
        </form>
     ''' % fill_helpers})

        output_objects.append({'object_type': 'sectionheader', 'text'
                                   : 'Request Access to %ss' % \
                                   configuration.site_vgrid_label})

        output_objects.append(
            {'object_type': 'text', 'text':
             '''You can request access to %(label)ss using the individual plus-icons above directly or by entering the name of the %(label)s to request access to, what kind of access and an optional message to the admins below''' % \
                 {'label': configuration.site_vgrid_label}})
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <form method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="text" size=40 name="vgrid_name" />
        <select name="request_type">
            <option value="vgridmember">membership</option> 
            <option value="vgridowner">ownership</option>
        </select>
        <input type="text" size=50 name="request_text" />
        <input type="hidden" name="output_format" value="html" />
        <input type="submit" value="Request %(vgrid_label)s access" />
        </form>
    ''' % fill_helpers})

    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, status)
