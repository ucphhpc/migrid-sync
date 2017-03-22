#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# imagemeta - Managing MiG image meta data
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Image meta data helper functions"""

import os
import time
import traceback

import shared.returnvalues as returnvalues
from shared.defaults import img_trigger_prefix
from shared.fileio import touch, makedirs_rec, listdirs_rec, \
    delete_file, make_symlink, remove_dir, remove_rec
from shared.imagemetaio import __metapath, __settings_filepath, \
    __image_metapath, __image_preview_path, __image_xdmf_path, \
    __revision, allowed_image_types, allowed_volume_types, \
    allowed_settings_status, add_image_file_setting, \
    add_image_volume_setting, update_image_file_setting, \
    update_image_volume_setting, update_image_file, \
    update_image_volume, remove_image_file_settings, \
    remove_image_volume_settings, get_image_file_setting, \
    get_image_file_settings, get_image_file_settings_count, \
    get_image_volume_setting, get_image_volume_settings_count, \
    get_image_file, get_image_volume, get_image_file_count, \
    get_image_volume_count, get_preview_image_url, \
    get_image_xdmf_filepath, get_image_file_settings_ent_template_dict, \
    get_image_volume_settings_ent_template_dict
from shared.vgrid import in_vgrid_share, vgrid_add_triggers, \
    vgrid_remove_triggers, vgrid_is_trigger, vgrid_add_imagesettings, \
    vgrid_remove_imagesettings, vgrid_imagesettings, \
    vgrid_list_subvgrids, vgrid_list_parents, vgrid_owners
from shared.vgridaccess import get_vgrid_map_vgrids


def __get_preview_mrsl_template():
    """General template for preview trigger jobs"""

    return """
::OUTPUTFILES::

::CPUTIME::
86400

::MEMORY::
131072

::DISK::
10

::VGRID::
ANY

::RUNTIMEENVIRONMENT::
PYTHON-2.X-1
PYTHON-OPENCV-2.X-1
PYTABLES-3.X-1
PYLIBTIFF-0.X-1
"""


def __create_previews_mrsl_template(datapath, extension):
    """Template for changed preview setting trigger jobs"""

    result = \
        """::EXECUTE::
echo "hostname: `hostname -f`"
echo "uname: `uname -a`"
echo "TRIGGERPATH: '+TRIGGERPATH+'"
echo "TRIGGERDIRNAME: '+TRIGGERDIRNAME+'"
echo "TRIGGERFILENAME: '+TRIGGERFILENAME+'"
echo "TRIGGERPREFIX: '+TRIGGERPREFIX+'"
echo "TRIGGEREXTENSION: '+TRIGGEREXTENSION+'"
echo "TRIGGERCHANGE: '+TRIGGERCHANGE+'"
echo "TRIGGERVGRIDNAME: '+TRIGGERVGRIDNAME+'"
echo "TRIGGERRUNAS: '+TRIGGERRUNAS+'"
echo "datapath: '%(datapath)s'"
echo "extension: '%(extension)s'"
# DEBUG
ls -la
ls -la shared/*
ls -la %(datapath)s/
ls -la %(datapath)s/.meta
# end DEBUG
python idmc_update_previews.py '+TRIGGERCHANGE+' '%(datapath)s' '%(extension)s'

::MOUNT::
+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+

::EXECUTABLES::

::INPUTFILES::
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/imagepreview.py imagepreview.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/idmc_update_previews.py idmc_update_previews.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/__init__.py shared/__init__.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/defaults.py shared/defaults.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/fileio.py shared/fileio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/imagemetaio.py shared/imagemetaio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/serial.py shared/serial.py
""" \
        % {'datapath': datapath, 'extension': extension} \
        + __get_preview_mrsl_template()

    return result


def __update_preview_mrsl_template(datapath):
    """Template for image file changed preview setting trigger jobs"""

    result = \
        """::EXECUTE::
echo "hostname: `hostname`"
echo "uname: `uname`"
echo "TRIGGERPATH: '+TRIGGERPATH+'"
echo "TRIGGERDIRNAME: '+TRIGGERDIRNAME+'"
echo "TRIGGERFILENAME: '+TRIGGERFILENAME+'"
echo "TRIGGERPREFIX: '+TRIGGERPREFIX+'"
echo "TRIGGEREXTENSION: '+TRIGGEREXTENSION+'"
echo "TRIGGERCHANGE: '+TRIGGERCHANGE+'"
echo "TRIGGERVGRIDNAME: '+TRIGGERVGRIDNAME+'"
echo "TRIGGERRUNAS: '+TRIGGERRUNAS+'"
echo "datapath: '%(datapath)s'"
# DEBUG
ls -la
ls -la '%(datapath)s/'
ls -la '%(datapath)s/.meta'
# end DEBUG
python idmc_update_preview.py '+TRIGGERCHANGE+' '%(datapath)s' '+TRIGGERDIRNAME+' '+TRIGGERFILENAME+'

::MOUNT::
+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+

::EXECUTABLES::

::INPUTFILES::
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/imagepreview.py imagepreview.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/idmc_update_preview.py idmc_update_preview.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/__init__.py shared/__init__.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/defaults.py shared/defaults.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/fileio.py shared/fileio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/imagemetaio.py shared/imagemetaio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/serial.py shared/serial.py
""" \
        % {'datapath': datapath} + __get_preview_mrsl_template()

    return result


def __strip_metapath(path):
    """Some triggers act on meta-paths, remove meta-path part if present"""

    if path.endswith(__metapath):
        path = path[:-len(__metapath)].strip('/')
    elif path.endswith(__settings_filepath):
        path = path[:-len(__settings_filepath)].strip('/')
    elif path.endswith(__image_preview_path):
        path = path[:-len(__image_preview_path)].strip('/')
    elif path.endswith(__image_xdmf_path):
        path = path[:-len(__image_xdmf_path)].strip('/')

    return path


def __get_vgrid_datapath(vgrid_name, path):
    """Resolve vgrid datapath from *path* and *vgrid_name*"""

    vgrid_datapath = path[len(vgrid_name):]

    return '/'.join([x for x in vgrid_datapath.split('/') if x])


def __get_image_dir_created_trigger_rule_id(logger):
    """Return id of trigger rule used when image dir created"""

    return '%s_meta_created' % img_trigger_prefix


def __get_image_dir_deleted_trigger_rule_id(logger):
    """Return id of trigger rule used when image dir deleted"""

    return '%s_dir_deleted' % img_trigger_prefix


def __get_image_dir_settings_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image settings changes"""

    path_array = path.split('/')
    return '%s_%s_%s_settings' % (img_trigger_prefix,
                                  '_'.join(path_array), extension)


def __get_image_file_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image file changes"""

    path_array = path.split('/')

    return '%s_%s_%s_files' % (img_trigger_prefix,
                               '_'.join(path_array), extension)


def __get_paraview_datapath(logger, path):
    """Return paraview datapath"""

    return os.path.join('worker', path)


def __get_paraview_datapath_link(logger, path):
    """Return paraview datapath link"""

    paraview_datapath = __get_paraview_datapath(logger, path)

    return os.path.join(paraview_datapath, __metapath)


def __fill_image_file_settings_defaults(logger, settings_dict):
    """Fill defaults for file setting"""

    status = returnvalues.OK
    template = get_image_file_settings_ent_template_dict(logger)
    defaults = {
        'settings_recursive': False,
        'preview_image_extension': 'png',
        'preview_x_dimension': 256,
        'preview_y_dimension': 256,
        'preview_cutoff_min': 0.0,
        'preview_cutoff_max': 0.0,
        }
    for key in defaults.keys():
        if not settings_dict.has_key(key):
            try:
                settings_dict[key] = template[key].type(defaults[key])
            except Exception:
                status = returnvalues.ERROR
                logger.error("Failed to cast image file default settings '%s' -> '%s' to type: '%s'"
                              % (key, defaults[key], template[key]))
                break

    return status


def __fill_image_volume_settings_defaults(logger, settings_dict):
    """Fill defaults for volume setting"""

    status = returnvalues.OK
    template = get_image_volume_settings_ent_template_dict(logger)
    defaults = {
        'volume_type': allowed_volume_types['slice'],
        'settings_recursive': False,
        'preview_x_dimension': 256,
        'preview_y_dimension': 256,
        'preview_z_dimension': 256,
        'preview_cutoff_min': 0.0,
        'preview_cutoff_max': 0.0,
        }

    for key in defaults.keys():
        if not settings_dict.has_key(key):
            try:
                settings_dict[key] = template[key].type(defaults[key])
            except Exception:
                status = returnvalues.ERROR
                logger.error("Failed to cast image volume default settings '%s' -> '%s' to type: '%s'"
                              % (key, defaults[key], template[key]))
                break
    return status


def __validate_image_file_settings_dict(logger, settings_dict):
    """Validates *settings_dict* and cast values to the types
    specified in template dict"""

    result = {}

    template = get_image_file_settings_ent_template_dict(logger)
    for key in settings_dict.keys():
        if template.has_key(key):
            try:
                result[key] = template[key].type(settings_dict[key])
            except Exception:
                result = None
                logger.error("Failed to cast image file settings '%s' -> '%s' to type: '%s'"
                              % (key, settings_dict[key],
                             template[key]))
                break
        else:
            logger.debug("Skipping _NON_ image file settings template key: '%s'"
                          % key)

    return result


def __validate_image_volume_settings_dict(logger, settings_dict):
    """Validates *settings_dict* and cast values to the types
    specified in template dict"""

    result = {}

    template = get_image_volume_settings_ent_template_dict(logger)
    for key in settings_dict.keys():
        if template.has_key(key):
            try:
                result[key] = template[key].type(settings_dict[key])
            except Exception:
                result = None
                logger.error("Failed to cast image volume settings '%s' -> '%s' to type: '%s'"
                              % (key, settings_dict[key],
                             template[key]))
                break
        else:
            logger.debug("Skipping _NON_ image volume settings template key: '%s'"
                          % key)

    return result


def __validate_image_settings_dicts(
    configuration,
    base_dir,
    abs_path,
    vgrid_name,
    vgrid_datapath,
    settings_dict,
    output_objects,
    update=False,
    ):
    """Validate setting dicts"""

    logger = configuration.logger
    image_file_setting = __validate_image_file_settings_dict(logger,
            settings_dict)
    image_volume_setting = \
        __validate_image_volume_settings_dict(logger, settings_dict)

    status = __is_valid_settings_dict(
        configuration,
        base_dir,
        abs_path,
        vgrid_name,
        vgrid_datapath,
        image_file_setting,
        output_objects,
        update,
        )

    if status == returnvalues.OK:
        status = __is_valid_settings_dict(
            configuration,
            base_dir,
            abs_path,
            vgrid_name,
            vgrid_datapath,
            image_volume_setting,
            output_objects,
            update,
            )

    if status == returnvalues.OK:
        result = (status, image_file_setting, image_volume_setting)
    else:
        result = (status, None, None)

    return result


def __seek_image_meta(
    logger,
    base_dir,
    filepath,
    data_entries=None,
    ):
    """Recursively seek upwards for image meta data"""

    result = None

    path_array = filepath.split('/')
    filename = path_array.pop()
    path = ''
    while result is None and len(path_array) > 0:
        abs_base_path = os.path.join(base_dir, os.sep.join(path_array))
        try:
            image_meta = get_image_file(logger, abs_base_path, path,
                    filename, data_entries=data_entries)
        except Exception:
            image_meta = None
            logger.debug(str(traceback.format_exc()))
        if image_meta is not None:
            result = image_meta
        path = ('%s%s%s' % (path_array.pop(), os.sep,
                path)).strip(os.sep)
    return result


def __seek_volume_meta(
    logger,
    base_dir,
    filepath,
    data_entries=None,
    ):
    """Recursively seek upwards for volume meta data"""

    result = None

    path_array = filepath.split('/')
    filename = path_array.pop()
    path = ''
    while result is None and len(path_array) > 0:
        abs_base_path = os.path.join(base_dir, os.sep.join(path_array))
        try:
            volume_meta = get_image_volume(logger, abs_base_path, path,
                    filename, data_entries=data_entries)
        except Exception:
            volume_meta = None
            logger.debug(str(traceback.format_exc()))
        if volume_meta is not None:
            result = volume_meta
        path = ('%s%s%s' % (path_array.pop(), os.sep,
                path)).strip(os.sep)
    return result


def __is_valid_settings_dict(
    configuration,
    base_dir,
    abs_path,
    vgrid_name,
    vgrid_path,
    image_setting_dict,
    output_objects,
    update=False,
    ):
    """Check if valid image settings update"""

    status = returnvalues.OK
    logger = configuration.logger

    extension = image_setting_dict.get('extension', '')
    settings_recursive = image_setting_dict.get('settings_recursive',
            False)
    image_type = image_setting_dict.get('image_type', '')
    data_type = image_setting_dict.get('data_type', '')

    # Check for extension

    if len(extension) == 0:
        status = returnvalues.ERROR
        ERROR_MSG = "Invalid image settings extension: '%s'" % extension
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error(ERROR_MSG)

    # Check for image types

    if status == returnvalues.OK and not update and (image_type
            not in allowed_image_types or data_type
            not in allowed_image_types[image_type]):
        status = returnvalues.ERROR
        ERROR_MSG = "Invalid image and data_type: '%s' -> '%s'" \
            % (image_type, data_type)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error(ERROR_MSG)

    # Check for vgrid

    if status == returnvalues.OK:
        vgrid_list = get_vgrid_map_vgrids(configuration)
        if not vgrid_name in vgrid_list:
            status = returnvalues.ERROR
            ERROR_MSG = "'%s' is _NOT_ workflow enabled." % vgrid_name
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    # Check for child folder image settings

    if status == returnvalues.OK and settings_recursive:

        abs_vgrid_path = os.path.join(base_dir,
                os.path.join(vgrid_name, vgrid_path))
        for path in listdirs_rec(abs_vgrid_path):
            try:
                image_meta = get_image_file_setting(logger, path,
                        extension)
            except Exception:
                image_meta = None
                logger.debug(str(traceback.format_exc()))
            if image_meta is not None:
                status = returnvalues.ERROR
                current_vgrid_path = path.replace(base_dir, '', 1)
                ERROR_MSG = \
                    "Settings for extension: '%s' found in path: '%s'." \
                    % (extension, current_vgrid_path)
                ERROR_MSG = '%s Overloading _NOT_ supported' % ERROR_MSG
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error(ERROR_MSG)

    # Check for parent folder image settings

    if status == returnvalues.OK:
        vgrid_path_array = ('%s/%s' % (vgrid_name,
                            vgrid_path)).split('/')[:-2]

        while status == returnvalues.OK and len(vgrid_path_array) > 0:
            current_vgrid_path = os.sep.join(vgrid_path_array)
            abs_vgrid_path = os.path.join(base_dir, current_vgrid_path)
            try:
                image_meta = get_image_file_setting(logger,
                        abs_vgrid_path, extension)
            except Exception:
                image_meta = None
                logger.debug(str(traceback.format_exc()))
            if image_meta is not None \
                and bool(image_meta['settings_recursive']):
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "settings for extension: '%s' found in path: '%s'." \
                    % (extension, current_vgrid_path)
                ERROR_MSG = '%s Overloading _NOT_ supported' % ERROR_MSG
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error(ERROR_MSG)

            vgrid_path_array = vgrid_path_array[:-1]

    # Check image settings status

    if status == returnvalues.OK:
        image_file_meta = get_image_file_setting(logger, abs_path,
                extension)

        if image_file_meta is not None \
            and image_file_meta['settings_status'] \
            != allowed_settings_status['ready'] \
            and image_file_meta['settings_status'] \
            != allowed_settings_status['failed']:

            status = returnvalues.ERROR
            ERROR_MSG = \
                "Image setting '%s' not ready for update, status: '%s'" \
                % (extension, image_file_meta['settings_status'])
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    if status == returnvalues.OK:
        image_volume_meta = get_image_volume_setting(logger, abs_path,
                extension)
        if image_volume_meta is not None \
            and image_volume_meta['settings_status'] \
            != allowed_settings_status['ready'] \
            and image_volume_meta['settings_status'] \
            != allowed_settings_status['failed']:

            status = returnvalues.ERROR
            ERROR_MSG = \
                "Volume setting '%s' not ready for update, status: '%s'" \
                % (extension, image_file_meta['settings_status'])
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    return status


def __add_image_dir_trigger(
    configuration,
    client_id,
    vgrid_name,
    changes,
    output_objects,
    ignore_parent=False,
    ):
    """Add trigger to monitor changes to image directories"""

    status = returnvalues.OK
    logger = configuration.logger

    recursive = True
    if ignore_parent:
        recursive = False

    if changes == 'created':
        vgrid_trigger_path = '/*/%s' % __settings_filepath
        match_dirs = False
        match_files = True
        rule_id = __get_image_dir_created_trigger_rule_id(logger)

        # NOTE: When grid_events discover a new directory then
        # DirCreated and FileCreated are dispatched for sub-dirs/files
        # Therefore we don't need a recursive refresh for new directories

        arguments = ['imagepreview', '', 'refresh', '+TRIGGERPATH+']
    elif changes == 'deleted':

        vgrid_trigger_path = '*'
        match_dirs = True
        match_files = False
        rule_id = __get_image_dir_deleted_trigger_rule_id(logger)
        arguments = ['imagepreview', '', 'cleanrecursive',
                     '+TRIGGERPATH+']
    else:
        status = returnvalues.ERROR
        ERROR_MSG = "Invalid trigger changes: '%s'" % str(changes)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
                configuration, recursive)

        if not trigger_exists:

             # Add vgrid create trigger for dir

            rule_dict = {
                'rule_id': rule_id,
                'vgrid_name': vgrid_name,
                'path': vgrid_trigger_path,
                'match_dirs': match_dirs,
                'match_files': match_files,
                'match_recursive': True,
                'changes': [changes],
                'run_as': client_id,
                'action': 'command',
                'arguments': arguments,
                'templates': [''],
                'settle_time': '',
                'rate_limit': '',
                }

            (add_status, add_msg) = vgrid_add_triggers(configuration,
                    vgrid_name, [rule_dict])
            if add_status:
                status = returnvalues.OK
                OK_MSG = "Created trigger : '%s' : '%s'" % (vgrid_name,
                        rule_id)
                output_objects.append({'object_type': 'text',
                        'text': OK_MSG})
                logger.info(OK_MSG)
            else:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "Failed to create trigger: '%s' : '%s' ->\n%s" \
                    % (vgrid_name, rule_id, add_msg)
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error('%s' % ERROR_MSG)
        else:
            MSG = 'Trigger: %s already exists for vgrid: %s' \
                % (rule_id, vgrid_name)

            logger.warning(MSG)

    return status


def __ensure_image_dir_triggers(configuration, vgrid_name,
                                output_objects):
    """Ensure that image dir triggers exists"""

    status = returnvalues.OK
    logger = configuration.logger
    created_trigger_exists = deleted_trigger_exists = True
    parent_list = vgrid_list_parents(vgrid_name, configuration)

    # Root vgrid is responsible for dir meta

    if len(parent_list) > 0:
        root_vgrid = parent_list[0]
    else:
        root_vgrid = vgrid_name

    # First owner of root vgrid is responsible for dir meta

    (owners_status, owners_id) = vgrid_owners(root_vgrid,
            configuration, recursive=False)

    if owners_status and len(owners_id) > 0:
        owner_id = owners_id[0]
    else:
        status = returnvalues.ERROR

    if status == returnvalues.OK:
        created_rule_id = \
            __get_image_dir_created_trigger_rule_id(logger)
        created_trigger_exists = vgrid_is_trigger(root_vgrid,
                created_rule_id, configuration, recursive=False)

        deleted_rule_id = \
            __get_image_dir_deleted_trigger_rule_id(logger)
        deleted_trigger_exists = vgrid_is_trigger(root_vgrid,
                deleted_rule_id, configuration, recursive=False)

        action_list = []
        if not created_trigger_exists:
            action_list.append('created')
        if not deleted_trigger_exists:
            action_list.append('deleted')

        for action in action_list:

            add_status = __add_image_dir_trigger(configuration,
                    owner_id, root_vgrid, action, output_objects)
            if add_status != returnvalues.OK:
                status = add_status

        # Remove created triggers if one fails

        if status != returnvalues.OK:
            for action in action_list:
                __remove_image_dir_trigger(configuration, root_vgrid,
                        action, output_objects)

    return status


def __ensure_image_setting_triggers(
    configuration,
    client_id,
    vgrid_name,
    abs_path,
    path,
    output_objects,
    ):
    """Ensure that image settings triggers exists"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    image_file_settings = get_image_file_settings(logger, abs_path)

    if image_file_settings is not None:
        trigger_add_list = []
        for image_file_setting in image_file_settings:
            extension = image_file_setting['extension']
            recursive = bool(image_file_setting['settings_recursive'])

            settings_trigger_rule_id = \
                __get_image_dir_settings_trigger_rule_id(logger,
                    vgrid_datapath, extension)
            settings_trigger_exists = vgrid_is_trigger(vgrid_name,
                    settings_trigger_rule_id, configuration,
                    recursive=False)
            if not settings_trigger_exists:
                trigger_add_list.append(settings_trigger_rule_id)
                add_status = __add_image_settings_modified_trigger(
                    configuration,
                    client_id,
                    vgrid_name,
                    path,
                    extension,
                    output_objects,
                    )
                if add_status != returnvalues.OK:
                    status = add_status

            file_trigger_rule_id = \
                __get_image_file_trigger_rule_id(logger,
                    vgrid_datapath, extension)
            file_trigger_exists = vgrid_is_trigger(vgrid_name,
                    file_trigger_rule_id, configuration,
                    recursive=False)
            if not file_trigger_exists:
                trigger_add_list.append(file_trigger_rule_id)
                add_status = __add_image_file_trigger(
                    configuration,
                    client_id,
                    vgrid_name,
                    path,
                    extension,
                    recursive,
                    output_objects,
                    )
                if add_status != returnvalues.OK:
                    status = add_status

        if status != returnvalues.OK:

            (remove_status, remove_msg) = \
                vgrid_remove_triggers(configuration, vgrid_name,
                    [trigger_add_list])

            if not remove_status:
                logger.warning(remove_msg)

    return status


def __add_image_dir_triggers(
    configuration,
    client_id,
    vgrid_name,
    output_objects,
    ):
    """Add triggers needed to monitor image dir changes"""

    status = __add_image_dir_trigger(configuration, client_id,
            vgrid_name, 'created', output_objects)

    if status == returnvalues.OK:
        status = __add_image_dir_trigger(configuration, client_id,
                vgrid_name, 'deleted', output_objects)

    # Remove meta triggers if not all is successfully created

    if status != returnvalues.OK:
        status = __remove_image_dir_triggers(configuration, vgrid_name,
                output_objects)

    return status


def __add_image_file_trigger(
    configuration,
    client_id,
    vgrid_name,
    path,
    extension,
    recursive,
    output_objects,
    ):
    """Add image file trigger"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    if recursive:
        vgrid_trigger_path = os.path.join(vgrid_datapath, '*/*.%s'
                % extension)
    else:
        vgrid_trigger_path = os.path.join(vgrid_datapath, '*.%s'
                % extension)

    rule_id = __get_image_file_trigger_rule_id(logger, vgrid_datapath,
            extension)

    # NOTE: The 'modifed' event is translated to
    #       a 'deleted' + 'created' in grid_events
    # TODO: Find a way to handle image previews for 'deleted'
    #       files without spamming the job-queue
    #       Should imagepreview handle 'addfile' / 'deletefile'
    #       as a command ?

    rule_dict = {
        'rule_id': rule_id,
        'vgrid_name': vgrid_name,
        'path': vgrid_trigger_path,
        'match_dirs': False,
        'match_recursive': recursive,
        'changes': ['created', 'modified'],
        'run_as': client_id,
        'action': 'submit',
        'arguments': ['template_from_imagepreview.py'],
        'templates': [__update_preview_mrsl_template(path)],
        'settle_time': '60s',
        'rate_limit': '',
        }

    # Add generated vgrid submit trigger for files

    (add_status, add_msg) = vgrid_add_triggers(configuration,
            vgrid_name, [rule_dict])
    if add_status:
        status = returnvalues.OK
        OK_MSG = "Created trigger : '%s' : '%s'" % (vgrid_name, rule_id)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = "Failed to create trigger: '%s' : '%s' ->\n%s" \
            % (vgrid_name, rule_id, add_msg)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def __add_image_settings_modified_trigger(
    configuration,
    client_id,
    vgrid_name,
    path,
    extension,
    output_objects,
    ):
    """Add vgrid image settings trigger"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    vgrid_trigger_path = \
        __get_image_settings_trigger_last_modified_filepath(logger,
            vgrid_datapath, extension)
    rule_id = __get_image_dir_settings_trigger_rule_id(logger,
            vgrid_datapath, extension)

    rule_dict = {
        'rule_id': rule_id,
        'rule_changes': ['created', 'deleted'],
        'vgrid_name': vgrid_name,
        'path': vgrid_trigger_path,
        'match_dirs': False,
        'match_recursive': False,
        'changes': ['modified'],
        'run_as': client_id,
        'action': 'submit',
        'arguments': ['template_from_imagepreview.py'],
        'templates': [__create_previews_mrsl_template(path,
                      extension)],
        'settle_time': '1s',
        'rate_limit': '',
        }

    (add_status, add_msg) = vgrid_add_triggers(configuration,
            vgrid_name, [rule_dict])
    if add_status:
        status = returnvalues.OK
        OK_MSG = "Created trigger : '%s' : '%s'" % (vgrid_name, rule_id)

        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = "Failed to create trigger: '%s' : '%s' ->\n%s" \
            % (vgrid_name, rule_id, add_msg)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def __add_paraview_link(configuration, path, output_objects):
    """Add paraview links to data"""

    logger = configuration.logger
    status = returnvalues.OK

    dest_path = os.path.join(configuration.vgrid_files_home,
                             os.path.join(path, __metapath))

    paraview_datapath = __get_paraview_datapath(logger, path)

    src_path = os.path.join(configuration.paraview_home,
                            paraview_datapath)
    src_path_link = os.path.join(src_path, __metapath)

    if makedirs_rec(src_path, configuration) \
        and make_symlink(dest_path, src_path_link, logger, force=True):
        status = returnvalues.OK
        OK_MSG = "Created paraview link : '%s' -> '%s'" \
            % (src_path_link, dest_path)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
        logger.info(OK_MSG)
    else:

        status = returnvalues.ERROR
        ERROR_MSG = 'Unable to create paraview link: %s -> %s' \
            % (src_path_link, dest_path)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def __add_vgrid_imagesetting(
    configuration,
    vgrid_name,
    path,
    extension,
    output_objects,
    overwrite=True,
    ):
    """Add imagesettings dict"""

    status = returnvalues.OK
    logger = configuration.logger

    imagesetting_dict = __get_vgrid_imagesetting_dict(configuration,
            vgrid_name, path, extension)

    update_id = None
    if overwrite:
        update_id = 'imagesetting_id'

    (vgrid_add_status, vgrid_add_msg) = \
        vgrid_add_imagesettings(configuration, vgrid_name,
                                [imagesetting_dict],
                                update_id=update_id)

    logger.debug('vgrid_add_status: %s, msg: %s' % (vgrid_add_status,
                 vgrid_add_msg))

    if vgrid_add_status:
        status = returnvalues.OK
        OK_MSG = "Created imagesetting : '%s' : '%s'" % (vgrid_name,
                imagesetting_dict['imagesetting_id'])
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = vgrid_add_msg
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def __remove_image_dir_triggers(configuration, vgrid_name,
                                output_objects):
    """Remove image dir triggers"""

    created_status = __remove_image_dir_trigger(configuration,
            vgrid_name, 'created', output_objects)

    deleted_status = __remove_image_dir_trigger(configuration,
            vgrid_name, 'deleted', output_objects)

    if created_status == returnvalues.OK and deleted_status \
        == returnvalues.OK:
        status = returnvalues.OK
    else:
        status = returnvalues.ERROR

    return status


def __remove_image_dir_trigger(
    configuration,
    vgrid_name,
    changes,
    output_objects,
    ):
    """Remove image directory trigger"""

    status = returnvalues.OK
    logger = configuration.logger

    if changes == 'created':
        rule_id = __get_image_dir_created_trigger_rule_id(logger)
    elif changes == 'deleted':
        rule_id = __get_image_dir_deleted_trigger_rule_id(logger)
    else:
        status = returnvalues.ERROR
        ERROR_MSG = "Invalid trigger changes: '%s'" % str(changes)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
                configuration, recursive=False)
        if trigger_exists:
            (remove_status, remove_msg) = \
                vgrid_remove_triggers(configuration, vgrid_name,
                    [rule_id])
            if remove_status:
                OK_MSG = \
                    "Removed image dir '%s' trigger for vgrid_name: '%s'" \
                    % (rule_id, vgrid_name)
                output_objects.append({'object_type': 'text',
                        'text': OK_MSG})
            else:
                status = returnvalues.ERROR
                output_objects.append({'object_type': 'text',
                        'text': remove_msg})
                ERROR_MSG = \
                    "Failed to remove image dir '%s' trigger vgrid_name: '%s'" \
                    % (rule_id, vgrid_name)
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error('%s' % ERROR_MSG)
                logger.error('vgrid_remove_triggers returned: %s'
                             % remove_msg)
        else:
            logger.debug("No trigger: '%s' for vgrid_name: %s"
                         % (rule_id, vgrid_name))

    return status


def __remove_image_file_trigger(
    configuration,
    vgrid_name,
    path,
    extension,
    output_objects,
    ):
    """Remove vgrid submit trigger for image files"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    rule_id = __get_image_file_trigger_rule_id(logger, vgrid_datapath,
            extension)

    trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
            configuration, recursive=False)
    if trigger_exists:
        (remove_status, remove_msg) = \
            vgrid_remove_triggers(configuration, vgrid_name, [rule_id])
        if remove_status:
            status = returnvalues.OK
            OK_MSG = \
                "Removed image files trigger for extension: '%s', path: '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Failed to remove old image files trigger for extension: '%s', path: '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)
            logger.error('vgrid_remove_triggers returned: %s'
                         % remove_msg)
    else:
        logger.debug('No trigger: %s for vgrid: %s' % (rule_id,
                     vgrid_name))
    return status


def __remove_image_settings_modified_trigger(
    configuration,
    vgrid_name,
    path,
    extension,
    output_objects,
    ):
    """Remove vgrid submit trigger for image settings"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    rule_id = __get_image_dir_settings_trigger_rule_id(logger,
            vgrid_datapath, extension)

    trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
            configuration, recursive=False)

    if trigger_exists:
        (remove_status, remove_msg) = \
            vgrid_remove_triggers(configuration, vgrid_name, [rule_id])
        if remove_status:
            status = returnvalues.OK
            OK_MSG = \
                "Removed image setting trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Failed to remove old image setting trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)
            logger.error('vgrid_remove_triggers returned: %s'
                         % remove_msg)
    else:
        logger.debug('No trigger: %s for vgrid: %s' % (rule_id,
                     vgrid_name))
    return status


def __remove_paraview_link(
    configuration,
    path,
    output_objects,
    recursive=False,
    ):
    """Remove paraview links to data"""

    status = returnvalues.OK
    logger = configuration.logger

    paraview_path = os.path.join(configuration.paraview_home,
                                 os.path.join('worker', path))

    paraview_link = os.path.join(paraview_path, __metapath)

    if os.path.exists(path) or os.path.islink(path):
        logger.debug('deleting Paraview link: %s' % paraview_link)

        if not delete_file(paraview_link, logger,
                           allow_broken_symlink=True):
            status = returnvalues.ERROR
            ERROR_MSG = 'Unable to remove paraview link: %s ' \
                % str(paraview_link)
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)
        else:
            OK_MSG = 'Removed paraview link: %s' % paraview_link
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
            logger.debug('removing paraview_path: %s' % paraview_path)
            remove_dir_status = remove_dir(paraview_path, configuration)
            if remove_dir_status:
                OK_MSG = 'Removed paraview path: %s' % paraview_path
                output_objects.append({'object_type': 'text',
                        'text': OK_MSG})
            else:
                ERROR_MSG = 'Unable to remove paraview path: %s' \
                    % paraview_path
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
            logger.debug('remove_dir_status: %s' % remove_dir_status)

            if recursive:
                path_array = path.split('/')
                pos = len(path_array) - 2
                while pos > 0 and remove_dir_status:
                    logger.debug('removing paraview_path pos: %s' % pos)
                    logger.debug('removing path: %s' % path_array[:pos])
                    remove_path = \
                        os.path.join(configuration.paraview_home,
                            os.path.join('worker',
                            os.sep.join(path_array[:pos])))
                    logger.debug('removing paraview_path: %s'
                                 % remove_path)
                    remove_dir_status = remove_dir(remove_path,
                            configuration)
                    if remove_dir_status:
                        OK_MSG = 'Removed paraview path: %s' \
                            % paraview_path
                        output_objects.append({'object_type': 'text',
                                'text': OK_MSG})
                    else:
                        ERROR_MSG = \
                            'Unable to remove paraview path: %s' \
                            % paraview_path
                        output_objects.append({'object_type': 'error_text'
                                , 'text': ERROR_MSG})
                        logger.debug('remove_dir_status: %s'
                                % remove_dir_status)
                    OK_MSG = 'Removed path: %s' % path_array[:pos]

                    pos -= 1
    else:
        logger.debug('Missing paraview link: %s' % paraview_link)

    return status


def __remove_vgrid_imagesetting(
    configuration,
    vgrid_name,
    path,
    extension,
    output_objects,
    ):
    """Remove imagesettings dict"""

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    imagesetting_id = __get_vgrid_imagesetting_id(configuration,
            vgrid_datapath, extension)

    logger.debug('removing: %s' % imagesetting_id)

    (vgrid_remove_status, _) = \
        vgrid_remove_imagesettings(configuration, vgrid_name,
                                   [imagesetting_id])

    logger.debug('vgrid_remove_status: %s' % vgrid_remove_status)

    if vgrid_remove_status:
        status = returnvalues.OK
        OK_MSG = "Removed vgrid imagesetting for path: '%s'" % path
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = 'Unable to remove imagesetting with id: %s ' \
            % str(imagesetting_id)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def __get_vgrid_imagesetting_id(logger, path, extension):
    """Generate unique vgrid imagesettings id"""

    path_array = [x for x in path.split('/') if x]

    return '%s_%s' % ('_'.join(path_array), extension)


def __get_vgrid_imagesetting_dict(
    configuration,
    vgrid_name,
    path,
    extension,
    ):
    """Generate vgrid imagesetting dictionary"""

    logger = configuration.logger
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    vgrid_metapath = os.path.join(vgrid_datapath, __metapath)
    vgrid_settingspath = os.path.join(vgrid_datapath,
            __settings_filepath)
    vgrid_imagepath = os.path.join(vgrid_datapath, __image_metapath)
    vgrid_previewpath = os.path.join(vgrid_datapath,
            __image_preview_path)
    imagesetting_id = __get_vgrid_imagesetting_id(configuration,
            vgrid_datapath, extension)

    imagesetting_dict = {
        'imagesetting_id': imagesetting_id,
        'metarev': __revision,
        'updated': time.time(),
        'extension': extension,
        'paths': {
            'data': vgrid_datapath,
            'meta': vgrid_metapath,
            'settings': vgrid_settingspath,
            'image': vgrid_imagepath,
            'preview': vgrid_previewpath,
            },
        'paraview': {'path': __get_paraview_datapath(logger, path),
                     'link': __get_paraview_datapath_link(logger,
                     path)},
        'triggers': {'settings': __get_image_dir_settings_trigger_rule_id(logger,
                     vgrid_datapath, extension),
                     'files': __get_image_file_trigger_rule_id(logger,
                     vgrid_datapath, extension)},
        }

    return imagesetting_dict


def __get_image_settings_trigger_last_modified_filepath(logger, path,
        extension):
    """Returns filepath for last_modified file used to trigger image settting changes"""

    metapath = os.path.join(path, __metapath)

    return os.path.join(metapath, '%s.last_modified' % extension)


def __get_image_meta(
    logger,
    base_dir,
    path,
    data_entries=None,
    ):
    """Returns image meta response object"""

    result = None

    image_meta = __seek_image_meta(logger, base_dir, path,
                                   data_entries=data_entries)
    if image_meta is not None:
        image_type = str(image_meta['image_type'])
        preview_image_url = get_preview_image_url(logger,
                '/cert_redirect/%s' % image_meta['base_path'],
                image_meta['path'], image_meta['preview_image_filename'
                ])
        base_path = str(image_meta['base_path'])
        path = str(image_meta['path'])
        name = str(image_meta['name'])
        extension = str(image_meta['extension'])
        offset = str(image_meta['offset'])
        x_dimension = str(image_meta['x_dimension'])
        y_dimension = str(image_meta['y_dimension'])
        preview_x_dimension = str(image_meta['preview_x_dimension'])
        preview_y_dimension = str(image_meta['preview_y_dimension'])
        preview_cutoff_min = str(image_meta['preview_cutoff_min'])
        preview_cutoff_max = str(image_meta['preview_cutoff_max'])
        preview_image_scale = str(image_meta['preview_image_scale'])
        preview_histogram = image_meta['preview_histogram']
        if preview_histogram is not None:
            preview_histogram = preview_histogram.tolist()
        preview_image = image_meta['preview_image']
        if preview_image is not None:
            preview_image = preview_image.tolist()
        preview_data = image_meta['preview_data']
        if preview_data is not None:
            preview_data = preview_data.tolist()
        min_value = str(image_meta['min_value'])
        max_value = str(image_meta['max_value'])
        median_value = str(image_meta['median_value'])
        mean_value = str(image_meta['mean_value'])
        file_md5sum = str(image_meta['file_md5sum'])
        data_type = str(image_meta['data_type'])

        result = {
            'object_type': 'image_meta',
            'image_type': image_type,
            'base_path': base_path,
            'path': path,
            'name': name,
            'extension': extension,
            'offset': offset,
            'x_dimension': x_dimension,
            'y_dimension': y_dimension,
            'preview_image_url': preview_image_url,
            'preview_histogram': preview_histogram,
            'preview_image': preview_image,
            'preview_data': preview_data,
            'preview_x_dimension': preview_x_dimension,
            'preview_y_dimension': preview_y_dimension,
            'preview_cutoff_min': preview_cutoff_min,
            'preview_cutoff_max': preview_cutoff_max,
            'preview_image_scale': preview_image_scale,
            'min_value': min_value,
            'max_value': max_value,
            'mean_value': mean_value,
            'median_value': median_value,
            'file_md5sum': file_md5sum,
            'data_type': data_type,
            }

    return result


def __get_image_meta_setting(
    logger,
    abs_path,
    path,
    extension,
    ):
    """Returns image file/volume settings response object"""

    result = None

    image_count = get_image_file_count(logger, abs_path,
            extension=extension)

    image_file_setting = get_image_file_setting(logger, abs_path,
            extension)

    if image_file_setting is not None:
        extension = str(image_file_setting['extension'])
        image_settings_status = str(image_file_setting['settings_status'
                                    ])
        image_settings_update_progress = \
            str(image_file_setting['settings_update_progress'])
        settings_recursive = str(image_file_setting['settings_recursive'
                                 ])
        image_count = str(image_count)
        image_type = str(image_file_setting['image_type'])
        offset = str(image_file_setting['offset'])
        x_dimension = str(image_file_setting['x_dimension'])
        y_dimension = str(image_file_setting['y_dimension'])
        preview_image_extension = \
            str(image_file_setting['preview_image_extension'])
        preview_x_dimension = \
            str(image_file_setting['preview_x_dimension'])
        preview_y_dimension = \
            str(image_file_setting['preview_y_dimension'])
        preview_cutoff_min = str(image_file_setting['preview_cutoff_min'
                                 ])
        preview_cutoff_max = str(image_file_setting['preview_cutoff_max'
                                 ])
        data_type = str(image_file_setting['data_type'])

        image_volume_setting = get_image_volume_setting(logger,
                abs_path, extension)

        if image_volume_setting is not None:
            z_dimension = str(image_volume_setting['z_dimension'])
            preview_z_dimension = \
                str(image_volume_setting['preview_z_dimension'])
            volume_type = str(image_volume_setting['volume_type'])
            volume_slice_filepattern = \
                str(image_volume_setting['volume_slice_filepattern'])
            volume_settings_status = \
                str(image_volume_setting['settings_status'])
            volume_settings_update_progress = \
                str(image_volume_setting['settings_update_progress'])
            volume_count = str(get_image_volume_count(logger, abs_path,
                               extension=extension))
        else:
            z_dimension = 0
            preview_z_dimension = 0
            volume_type = ''
            volume_slice_filepattern = ''
            volume_settings_status = ''
            volume_settings_update_progress = ''
            volume_count = 0

        result = {
            'object_type': 'image_setting',
            'path': path,
            'extension': extension,
            'image_settings_status': image_settings_status,
            'image_settings_update_progress': image_settings_update_progress,
            'volume_settings_status': volume_settings_status,
            'volume_settings_update_progress': volume_settings_update_progress,
            'settings_recursive': settings_recursive,
            'image_count': image_count,
            'image_type': image_type,
            'volume_count': volume_count,
            'volume_type': volume_type,
            'volume_slice_filepattern': volume_slice_filepattern,
            'offset': offset,
            'x_dimension': x_dimension,
            'y_dimension': y_dimension,
            'z_dimension': z_dimension,
            'preview_image_extension': preview_image_extension,
            'preview_x_dimension': preview_x_dimension,
            'preview_y_dimension': preview_y_dimension,
            'preview_z_dimension': preview_z_dimension,
            'preview_cutoff_min': preview_cutoff_min,
            'preview_cutoff_max': preview_cutoff_max,
            'data_type': data_type,
            }

    return result


def __get_volume_meta(
    logger,
    base_dir,
    path,
    data_entries=None,
    ):
    """Returns volume meta response object"""

    result = None

    volume_meta = __seek_volume_meta(logger, base_dir, path,
            data_entries=data_entries)
    if volume_meta is not None:
        image_type = str(volume_meta['image_type'])
        volume_type = str(volume_meta['volume_type'])
        base_path = str(volume_meta['base_path'])
        path = str(volume_meta['path'])
        name = str(volume_meta['name'])
        extension = str(volume_meta['extension'])
        offset = str(volume_meta['offset'])
        x_dimension = str(volume_meta['x_dimension'])
        y_dimension = str(volume_meta['y_dimension'])
        z_dimension = str(volume_meta['z_dimension'])
        preview_histogram = volume_meta['preview_histogram']
        if preview_histogram is not None:
            preview_histogram = preview_histogram.tolist()
        preview_data = volume_meta['preview_data']
        if preview_data is not None:
            preview_data = preview_data.tolist()
        preview_xdmf_filepath = get_image_xdmf_filepath(logger,
                base_path, volume_meta['preview_xdmf_filename'])
        preview_x_dimension = str(volume_meta['preview_x_dimension'])
        preview_y_dimension = str(volume_meta['preview_y_dimension'])
        preview_z_dimension = str(volume_meta['preview_z_dimension'])
        preview_cutoff_min = str(volume_meta['preview_cutoff_min'])
        preview_cutoff_max = str(volume_meta['preview_cutoff_max'])
        preview_histogram = volume_meta['preview_histogram']
        if preview_histogram is not None:
            preview_histogram = preview_histogram.tolist()
        min_value = str(volume_meta['min_value'])
        max_value = str(volume_meta['max_value'])
        median_value = str(volume_meta['median_value'])
        mean_value = str(volume_meta['mean_value'])
        file_md5sum = str(volume_meta['file_md5sum'])
        data_type = str(volume_meta['data_type'])

        result = {
            'object_type': 'volume_meta',
            'image_type': image_type,
            'volume_type': volume_type,
            'base_path': base_path,
            'path': path,
            'name': name,
            'extension': extension,
            'offset': offset,
            'x_dimension': x_dimension,
            'y_dimension': y_dimension,
            'z_dimension': z_dimension,
            'preview_data': preview_data,
            'preview_xdmf_filepath': preview_xdmf_filepath,
            'preview_histogram': preview_histogram,
            'preview_x_dimension': preview_x_dimension,
            'preview_y_dimension': preview_y_dimension,
            'preview_z_dimension': preview_z_dimension,
            'preview_cutoff_min': preview_cutoff_min,
            'preview_cutoff_max': preview_cutoff_max,
            'min_value': min_value,
            'max_value': max_value,
            'mean_value': mean_value,
            'median_value': median_value,
            'file_md5sum': file_md5sum,
            'data_type': data_type,
            }

    return result


def __reset_file_settings(
    configuration,
    abs_path,
    path,
    output_objects,
    extension=None,
    ):
    """Reset status for image file meta setting with *path* and *extension*
    If *extension is None all entries for *path* are reset"""

    logger = configuration.logger
    status = returnvalues.OK

    modified_settings = \
        {'settings_status': allowed_settings_status['ready'],
         'settings_update_progress': None}
    if extension is not None and len(extension) > 0:
        modified_settings['extension'] = extension

    file_reset = update_image_file_setting(logger, abs_path,
            modified_settings)
    if file_reset:
        status = returnvalues.OK
        if extension is None or len(extension) == 0:
            OK_MSG = "Reset all image file settings status : '%s'" \
                % path
        else:
            OK_MSG = \
                "Reset image file setting status : '%s', extension: '%s'" \
                % (path, extension)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        if extension is None or len(extension) == 0:
            ERROR_MSG = \
                "Reset image file settings status FAILED : '%s'" % path
        else:
            ERROR_MSG = \
                "Reset image file settings status FAILED : '%s', extension: '%s'" \
                % (path, extension)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})

    return status


def __reset_volume_settings(
    configuration,
    abs_path,
    path,
    output_objects,
    extension=None,
    ):
    """Reset status for image volume meta setting with *path* and *extension*
    If *extension is None all entries for *path* are reset"""

    logger = configuration.logger
    status = returnvalues.OK

    modified_settings = \
        {'settings_status': allowed_settings_status['ready'],
         'settings_update_progress': None}
    if extension is not None and len(extension) > 0:
        modified_settings['extension'] = extension

    volume_reset = update_image_volume_setting(logger, abs_path,
            modified_settings)
    if volume_reset:
        status = returnvalues.OK
        if extension is None or len(extension) == 0:
            OK_MSG = \
                "Reset all image volume settings status for path: '%s'" \
                % path
        else:
            OK_MSG = \
                "Reset image volume setting status for path: '%s', extension: '%s'" \
                % (path, extension)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        if extension is None or len(extension) == 0:
            ERROR_MSG = \
                "Reset image volume settings status FAILED for path: '%s'" \
                % path
        else:
            ERROR_MSG = \
                "Reset image volume settings status FAILED for path: '%s', extension: '%s'" \
                % (path, extension)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})

    return status


def list_settings(
    configuration,
    abs_path,
    path,
    output_objects,
    ):
    """List image meta settings for *path*"""

    logger = configuration.logger
    image_status = True
    extension_list = []
    image_settings_status_list = []
    image_settings_progress_list = []
    image_count_list = []

    volume_status = True
    volume_settings_status_list = []
    volume_settings_progress_list = []
    volume_count_list = []

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    # TODO: Make support for raw volume files without slices
    # That is, return volume meta entries not in image_meta

    image_meta = get_image_file_settings(logger, abs_path)

    if image_meta is not None:
        for image in image_meta:
            extension_list.append(image['extension'])
            image_settings_status_list.append(image['settings_status'])
            image_settings_progress_list.append(image['settings_update_progress'
                    ])
            image_count_list.append(get_image_file_count(logger,
                                    abs_path,
                                    extension=image['extension']))

            volume_settings_status = ''
            volume_settings_update_progress = ''
            volume_count = 0
            volume_meta = get_image_volume_setting(logger, abs_path,
                    extension=image['extension'])
            if volume_meta is not None:
                volume_settings_status = volume_meta['settings_status']
                volume_settings_update_progress = \
                    volume_meta['settings_update_progress']
                volume_count = get_image_volume_count(logger, abs_path,
                        extension=volume_meta['extension'])
            else:
                volume_status = False
                MSG = \
                    "No volume settings found for path: '%s', extension: '%s'" \
                    % (path, image['extension'])
                output_objects.append({'object_type': 'text',
                        'text': MSG})
                logger.debug('%s' % MSG)

            volume_settings_status_list.append(volume_settings_status)
            volume_settings_progress_list.append(volume_settings_update_progress)
            volume_count_list.append(volume_count)
    else:
        image_status = False
        MSG = "No image settings found for path: '%s'" % path
        output_objects.append({'object_type': 'text', 'text': MSG})
        logger.debug(MSG)

    if image_status or volume_status:
        status = returnvalues.OK
        output_objects.append({
            'object_type': 'image_settings_list',
            'extension_list': extension_list,
            'image_settings_status_list': image_settings_status_list,
            'image_settings_progress_list': image_settings_progress_list,
            'image_count_list': image_count_list,
            'volume_settings_status_list': volume_settings_status_list,
            'volume_settings_progress_list': volume_settings_progress_list,
            'volume_count_list': volume_count_list,
            })
    else:
        status = returnvalues.ERROR

    return status


def create_setting(
    configuration,
    client_id,
    base_dir,
    abs_path,
    path,
    extension,
    create_dict,
    output_objects,
    ):
    """Create image meta setting for *path* and *extension*"""

    logger = configuration.logger

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    vgrid_metapath = os.path.join(vgrid_datapath, __metapath)
    vgrid_image_metapath = os.path.join(vgrid_datapath,
            __image_metapath)

    status = returnvalues.OK

    OK_MSG = "Created settings for image extension: '%s' for path '%s'" \
        % (extension, path)
    ERROR_MSG = \
        "Failed to complete settings create for image extension: '%s' for path: '%s'" \
        % (extension, path)

    create_dict['settings_status'] = allowed_settings_status['pending']
    (status, image_file_setting, image_volume_setting) = \
        __validate_image_settings_dicts(
        configuration,
        base_dir,
        abs_path,
        vgrid_name,
        vgrid_datapath,
        create_dict,
        output_objects,
        )

    # Fill image dicts with default create values

    if status == returnvalues.OK:
        status = __fill_image_file_settings_defaults(logger,
                image_file_setting)

    if status == returnvalues.OK:
        status = __fill_image_volume_settings_defaults(logger,
                image_volume_setting)

    # Ensure meta path existence

    if status == returnvalues.OK:

        # Ensure meta path existence

        makedirs_rec(os.path.join(base_dir, os.path.join(vgrid_name,
                     vgrid_metapath)), configuration)

        # Ensure image meta path existence

        makedirs_rec(os.path.join(base_dir, os.path.join(vgrid_name,
                     vgrid_image_metapath)), configuration)

        # Update image file settings

        try:
            add_status = add_image_file_setting(logger, abs_path,
                    image_file_setting, overwrite=True)
            if add_status:
                OK_MSG = "Created image setting : '%s'" % extension
                output_objects.append({'object_type': 'text',
                        'text': OK_MSG})
                logger.info(OK_MSG)
        except Exception:

            add_status = False
            logger.debug(str(traceback.format_exc()))

        # Update image volume settings

        if add_status \
            and image_volume_setting.get('volume_slice_filepattern', ''
                ) != '':
            try:
                add_status = add_image_volume_setting(logger, abs_path,
                        image_volume_setting, overwrite=True)
                if add_status:
                    OK_MSG = "Created volume setting : '%s'" % extension
                    output_objects.append({'object_type': 'text',
                            'text': OK_MSG})
                    logger.info(OK_MSG)
            except Exception:

                add_status = False
                logger.debug(str(traceback.format_exc()))

            # Create image meta links used by Paraview render

            if add_status:
                status = __add_paraview_link(configuration, path,
                        output_objects)
            else:
                status = returnvalues.ERROR

    if status == returnvalues.OK:
        status = __add_image_dir_triggers(configuration, client_id,
                vgrid_name, output_objects)

    if status == returnvalues.OK:

        # Generate vgrid trigger for files

        settings_recursive = \
            bool(image_file_setting.get('settings_recursive', False))

        status = __add_image_file_trigger(
            configuration,
            client_id,
            vgrid_name,
            path,
            extension,
            settings_recursive,
            output_objects,
            )

    if status == returnvalues.OK:

        # Add generated vgrid submit trigger for settings

        status = __add_image_settings_modified_trigger(
            configuration,
            client_id,
            vgrid_name,
            path,
            extension,
            output_objects,
            )

    if status == returnvalues.OK:

        # Add entry to imagesettings dict

        status = __add_vgrid_imagesetting(configuration, vgrid_name,
                path, extension, output_objects)

    if status == returnvalues.OK:

        # Trigger Trigger (Trigger Happy)

        vgrid_trigger_path = \
            __get_image_settings_trigger_last_modified_filepath(logger,
                vgrid_datapath, extension)

        abs_vgrid_trigger_filepath = os.path.join(base_dir,
                os.path.join(vgrid_name, vgrid_trigger_path))

        # FYSIKER HACK: Sleep 1 to prevent trigger rule/event race
        # TODO: Modify events handler to accept add+trigger action

        time.sleep(1)
        timestamp = time.time()
        touch(abs_vgrid_trigger_filepath, timestamp)

    if status == returnvalues.OK:
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def update_setting(
    configuration,
    base_dir,
    abs_path,
    path,
    extension,
    update_dict,
    output_objects,
    ):
    """Update image meta setting for *path* and *extension*"""

    logger = configuration.logger
    status = returnvalues.OK
    OK_MSG = "Updated settings for image extension: '%s' for path '%s'" \
        % (extension, path)
    ERROR_MSG = \
        "Failed to update settings for image extension: '%s' for path: '%s'" \
        % (extension, path)

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    update_dict['settings_status'] = allowed_settings_status['pending']
    (status, image_file_setting, image_volume_setting) = \
        __validate_image_settings_dicts(
        configuration,
        base_dir,
        abs_path,
        vgrid_name,
        vgrid_datapath,
        update_dict,
        output_objects,
        update=True,
        )

    if status == returnvalues.OK:
        if not update_image_file_setting(logger, abs_path,
                image_file_setting):
            status = returnvalues.ERROR

    if status == returnvalues.OK:
        if not update_image_volume_setting(logger, abs_path,
                image_volume_setting):
            status = returnvalues.ERROR

    # Trigger modified event

    if status == returnvalues.OK:
        abs_last_modified_filepath = \
            __get_image_settings_trigger_last_modified_filepath(logger,
                abs_path, extension)

        timestamp = time.time()
        touch(abs_last_modified_filepath, timestamp)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
        logger.debug('trigger timestamp: %s, path: %s ' % (timestamp,
                     abs_last_modified_filepath))
    else:
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def remove_setting(
    configuration,
    abs_path,
    path,
    extension,
    output_objects,
    ):
    """Remove image meta setting, image meta, triggers,
    imagesetting_dict and paraview links for *path*, *extension*
    """

    # TODO:
    # 1) Remove image file entries
    # 2) Remove image volume entries
    # 3) Remove triggers first
    # 4) Remove image thumbnails
    # 5) Make 'helper function' for functionality used by
    #    both 'remove' and 'clean'

    logger = configuration.logger

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    vgrid_name = in_vgrid_share(configuration, abs_path)

    remove_ext = None
    if len(extension) > 0:
        remove_ext = extension
    try:
        (file_status, removed_ext_list) = \
            remove_image_file_settings(logger, abs_path, remove_ext)
    except Exception:
        file_status = None
        removed_ext_list = []

        logger.debug(str(traceback.format_exc()))

    try:
        (volume_status, _) = remove_image_volume_settings(logger,
                abs_path, remove_ext)
    except Exception:
        volume_status = None
        logger.debug(str(traceback.format_exc()))

    if file_status is not None:
        status = returnvalues.OK
        OK_MSG = \
            "Removed settings for image extension: '%s' for path: '%s'" \
            % (extension, path)
        output_objects.append({'object_type': 'text', 'text': OK_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = 'Unable to remove image settings for path: %s' \
            % path
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    for removed_ext in removed_ext_list:
        abs_last_modified_filepath = \
            __get_image_settings_trigger_last_modified_filepath(logger,
                abs_path, removed_ext)

        # Remove trigger

        if delete_file(abs_last_modified_filepath, logger,
                       allow_missing=True):

            # Remove old vgrid submit trigger for files

            remove_status = __remove_image_file_trigger(configuration,
                    vgrid_name, path, removed_ext, output_objects)
            if remove_status != returnvalues.OK:
                status = remove_status

            # Remove old vgrid submit trigger for settings

            remove_status = \
                __remove_image_settings_modified_trigger(configuration,
                    vgrid_name, path, removed_ext, output_objects)
            if remove_status != returnvalues.OK:
                status = remove_status
        else:
            status = returnvalues.ERROR
            ERROR_MSG = 'Unable to remove file: %s ' \
                % abs_last_modified_filepath
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)

    # Remove image meta links used by Paraview render

    remove_status = __remove_paraview_link(configuration, path,
            output_objects, recursive=True)
    if remove_status != returnvalues.OK:
        status = remove_status

    # Remove vgrid removed_ext_list

    for removed_ext in removed_ext_list:

        remove_status = __remove_vgrid_imagesetting(configuration,
                vgrid_name, path, removed_ext, output_objects)

        if remove_status != returnvalues.OK:
            status = remove_status

    return status


def reset_settings(
    configuration,
    abs_path,
    path,
    output_objects,
    extension=None,
    volume=True,
    ):
    """Reset status for image file and volume meta setting
    with *path* and *extension*.
    If *extension is None all entries for *path* are reset"""

    # Remove metapath components from path

    status = __reset_file_settings(configuration, abs_path, path,
                                   output_objects, extension)

    # NOTE: Volume setting is _NOT_ required therefore doesn't effect status

    if volume:
        __reset_volume_settings(configuration, abs_path, path,
                                output_objects, extension)

    return status


def get_setting(
    configuration,
    abs_path,
    path,
    extension,
    output_objects,
    ):
    """Get image meta setting for *path* and *extension*"""

    logger = configuration.logger

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    image_settings = __get_image_meta_setting(logger, abs_path, path,
            extension)
    if image_settings is not None:
        output_objects.append(image_settings)
        status = returnvalues.OK
    else:
        status = returnvalues.ERROR
        ERROR_MSG = \
            "No image setting information for path: '%s', extension: '%s'" \
            % (path, extension)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def get(
    configuration,
    base_dir,
    path,
    output_objects,
    ):
    """Get image meta for file with *path*"""

    logger = configuration.logger
    status = returnvalues.OK

    # Remove metapath components from path

    path = __strip_metapath(path)

    # Get image settings, image meta for file base_dir/path

    image_meta = __get_image_meta(logger, base_dir, path,
                                  data_entries=['preview_histogram'])

    if image_meta is not None:
        output_objects.append(image_meta)

        # Return image settings as well as image meta

        abs_base_path = os.path.join(base_dir, image_meta['base_path'])

        image_settings = __get_image_meta_setting(logger,
                abs_base_path, image_meta['path'],
                image_meta['extension'])

        if image_settings is None:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Missing image_settings for path: '%s', extension: '%s'" \
                % (image_meta['path'], image_meta['extension'])
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)
        else:
            output_objects.append(image_settings)

            # Volume exists and is generated from stack of slices
            # Return alogn with image_meta

            if image_settings['volume_count'] > 0:
                if image_settings['volume_type'] \
                    == allowed_volume_types['slice']:
                    volume_path = os.path.join(image_meta['base_path'],
                            os.path.join(image_meta['path'],
                            os.path.join(image_settings['volume_slice_filepattern'
                            ])))

                    slice_volume_meta = __get_volume_meta(logger,
                            base_dir, volume_path)
                    if slice_volume_meta is not None:
                        output_objects.append(slice_volume_meta)
                    else:
                        logger.warning('Missing slice_volume_meta for path: %s'
                                 % path)
                else:
                    ERROR_MSG = \
                        "Invalid volume type: '%s', allowed: %s" \
                        % (image_settings['volume_type'],
                           allowed_volume_types.values())
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG})
                    logger.error(ERROR_MSG)
    else:
        status = returnvalues.ERROR
        ERROR_MSG = 'No meta information for file: %s' % path
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def remove(
    configuration,
    base_dir,
    abs_path,
    path,
    output_objects,
    ):
    """Remove image meta for file with *path*"""

    ERROR_MSG = 'remove _NOT_ implemented yet'
    output_objects.append({'object_type': 'error_text',
                          'text': ERROR_MSG})

    return returnvalues.ERROR


def refresh(
    configuration,
    client_id,
    base_dir,
    abs_path,
    path,
    output_objects,
    ):
    """Refresh image settings, image meta, triggers,
    imagesetting_dict and paraview links for *path'
    """

    status = returnvalues.OK
    logger = configuration.logger

    # Remove metapath components from path

    abs_path = __strip_metapath(abs_path)
    path = __strip_metapath(path)

    # Get vgrid name from path

    vgrid_name = in_vgrid_share(configuration, abs_path)

    image_file_settings_count = get_image_file_settings_count(logger,
            abs_path)
    image_file_count = get_image_volume_count(logger, abs_path)

    image_volume_settings_count = \
        get_image_volume_settings_count(logger, abs_path)
    image_volume_count = get_image_volume_count(logger, abs_path)

    if image_file_settings_count > 0:
        STATUS_MSG = '============= %s ============' % path
        output_objects.append({'object_type': 'text',
                              'text': STATUS_MSG})
    else:
        status = returnvalues.ERROR
        ERROR_MSG = "No image settings found for path: '%s'" % path
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        reset_volume = False
        if image_volume_settings_count > 0:
            reset_volume = True

        # Reset file and volume settings

        status = reset_settings(configuration, abs_path, path,
                                output_objects, volume=reset_volume)

    if status == returnvalues.OK and image_file_count > 0:

        # Check and update image base file paths

        if update_image_file(logger, abs_path, {'base_path': path}):
            OK_MSG = "Updated file meta base path : '%s'" % path
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = "Failed to update file meta : '%s'" % path
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    if status == returnvalues.OK and image_file_count > 0:

        # Check and update volume base file paths

        if update_image_volume(logger, abs_path, {'base_path': path}):
            OK_MSG = "Updated volume meta base path : '%s'" % path
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = "Failed to update volume meta base path : '%s'" \
                % path
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        # Check and update image dir trigger

        status = __ensure_image_dir_triggers(configuration, vgrid_name,
                output_objects)
        if status != returnvalues.OK:
            ERROR_MSG = 'Failed to updated image dir triggers'
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        # Check and update image settimg trigger

        status = __ensure_image_setting_triggers(
            configuration,
            client_id,
            vgrid_name,
            abs_path,
            path,
            output_objects,
            )
        if status != returnvalues.OK:
            ERROR_MSG = 'Failed to updated image setting triggers'
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error(ERROR_MSG)

    if status == returnvalues.OK:

        # Check and update image meta

        image_meta = get_image_file_settings(logger, abs_path)
        if image_meta is not None:
            status = __add_paraview_link(configuration, path,
                    output_objects)
            if status == returnvalues.OK:
                for image in image_meta:

                    vgrid_add_status = \
                        __add_vgrid_imagesetting(configuration,
                            vgrid_name, path, image['extension'],
                            output_objects)

                    if vgrid_add_status != returnvalues.OK:
                        status = returnvalues.ERROR

    return status


def clean(
    configuration,
    base_dir,
    abs_path,
    path,
    output_objects,
    recursive=False,
    ):
    """Removes image settings, image meta, triggers,
    imagesetting_dict and paraview links for *path'
    """

    status = returnvalues.OK
    logger = configuration.logger
    vgrid_name = in_vgrid_share(configuration, abs_path)

    vgrid_list = [vgrid_name]

    # NOTE: recursive=True is dir top-down

    if recursive:
        (list_status, sub_vgrid_list) = \
            vgrid_list_subvgrids(vgrid_name, configuration)

        if list_status:
            for sub_vgrid in sub_vgrid_list:
                if sub_vgrid.find(path) == 0:
                    vgrid_list.extend(sub_vgrid_list)

    for vgrid in vgrid_list:
        vgrid_datapath = __get_vgrid_datapath(vgrid, path)

        # NOTE: recursive=True for vgrid_imagesettings is vgrid bottom up

        (vgrid_imagesettings_status, imagesettings) = \
            vgrid_imagesettings(vgrid, configuration, recursive=False,
                                allow_missing=True)

        remove_imagesettings_ids = []
        if vgrid_imagesettings_status:
            for imagesetting in imagesettings:
                imagesetting_id = imagesetting.get('imagesetting_id',
                        None)
                imagesetting_extension = imagesetting.get('extension',
                        '')
                imagesetting_datapath = imagesetting.get('paths',
                        {}).get('data', None)
                imagesetting_paraview_path = imagesetting.get('paraview'
                        , {}).get('path', None)
                imagesetting_paraview_link = imagesetting.get('paraview'
                        , {}).get('link', None)

                # imagesetting_metapath = imagesetting.get('paths',
                #         {}).get('meta', None)
                # imagesetting_settingspath = imagesetting.get('paths',
                #        {}).get('settings', None)
                # imagesetting_imagepath = imagesetting.get('paths',
                #         {}).get('image', None)
                # imagesetting_previewpath = imagesetting.get('paths',
                #         {}).get('preview', None)

                if imagesetting_datapath is not None \
                    and (imagesetting_datapath == vgrid_datapath
                         or recursive
                         and imagesetting_datapath[:len(os.path.join(vgrid_datapath,
                         ''))] == os.path.join(vgrid_datapath, '')):

                    STATUS_MSG = '============= %s : %s ============' \
                        % (os.path.join(vgrid, imagesetting_datapath),
                           imagesetting_extension)
                    output_objects.append({'object_type': 'text',
                            'text': STATUS_MSG})

                    # Remove meta dir

                    # TODO: Remove imagemeta paths automatically, but make sure that
                    # we do _NOT_ delete the entire vgrid !!!

                    settings_filepath = os.path.join(path,
                            __settings_filepath)
                    image_metapath = os.path.join(path,
                            __image_metapath)
                    image_preview_path = os.path.join(path,
                            __image_preview_path)
                    image_xdmf_path = os.path.join(path,
                            __image_xdmf_path)

                    STATUS_MSG = \
                        'Remove the following imagepreview dir/files manually if needed:\n'
                    STATUS_MSG += \
                        '--------------------------------------------------------------\n'
                    STATUS_MSG += '''%s
%s
%s
%s
''' \
                        % (settings_filepath, image_metapath,
                           image_preview_path, image_xdmf_path)
                    STATUS_MSG += \
                        '--------------------------------------------------------------'
                    output_objects.append({'object_type': 'text',
                            'text': STATUS_MSG})

                    # Add imagesetting to remove list

                    remove_imagesettings_ids.append(imagesetting_id)
                    remove_triggers = imagesetting['triggers'].values()

                    (remove_status, remove_msg) = \
                        vgrid_remove_triggers(configuration, vgrid,
                            remove_triggers)

                    if remove_status:
                        OK_MSG = "Removed triggers : '%s' : %s" \
                            % (vgrid_name, remove_triggers)
                        output_objects.append({'object_type': 'text',
                                'text': OK_MSG})
                        logger.info(OK_MSG)
                    else:
                        status = returnvalues.ERROR
                        ERROR_MSG = remove_msg
                        output_objects.append({'object_type': 'error_text'
                                , 'text': ERROR_MSG})
                        logger.error(ERROR_MSG)

                    # NOTE: We do _NOT_ use '__remove_paraview_link' here as
                    #       we delete paraview links and paths based on imagesetting_dict
                    #       rateher than os structure

                    if imagesetting_paraview_link is None:
                        status = returnvalues.ERROR
                        WARN_MSG = \
                            'No valid paraview link found in imagesetting'
                        output_objects.append({'object_type': 'warning'
                                , 'text': WARN_MSG})
                        logger.warning(WARN_MSG)
                    else:
                        paraview_link = \
                            os.path.join(configuration.paraview_home,
                                imagesetting_paraview_link)

                        if os.path.exists(paraview_link):
                            delete_status = delete_file(paraview_link,
                                    logger, allow_broken_symlink=True)
                            if delete_status:
                                OK_MSG = "Removed Paraview link : '%s'" \
                                    % paraview_link
                                output_objects.append({'object_type': 'text'
                                        , 'text': OK_MSG})
                                logger.info(OK_MSG)
                            else:
                                status = returnvalues.ERROR
                                WARN_MSG = \
                                    'Failed to remove paraview link: %s' \
                                    % paraview_link
                                output_objects.append({'object_type': 'warning'
                                        , 'text': WARN_MSG})
                                logger.error(WARN_MSG)
                        else:
                            logger.warning('Missing paraview_link: %s'
                                    % paraview_link)

                    if imagesetting_paraview_path is None:
                        status = returnvalues.ERROR
                        WARN_MSG = \
                            'No valid paraview path found in imagesetting'
                        output_objects.append({'object_type': 'warning'
                                , 'text': WARN_MSG})
                        logger.warning(WARN_MSG)
                    else:
                        paraview_path = \
                            os.path.join(configuration.paraview_home,
                                imagesetting_paraview_path)
                        if os.path.exists(paraview_path):

                            # TODO: Use remove_rec here when we are sure
                            # that we do _NOT_ delete the entire vgrid !!!

                            remove_dir_status = \
                                remove_dir(paraview_path, configuration)

                            if remove_dir_status:
                                OK_MSG = "Removed paraview_path: '%s'" \
                                    % paraview_path
                                output_objects.append({'object_type': 'text'
                                        , 'text': OK_MSG})
                                logger.info(OK_MSG)
                            else:
                                WARN_MSG = \
                                    "Failed to remove paraview path: '%s'" \
                                    % paraview_path
                                output_objects.append({'object_type': 'warning'
                                        , 'text': WARN_MSG})
                                logger.warning(WARN_MSG)
                        else:
                            logger.warning('Missing paraview_path: %s'
                                    % paraview_path)

            (vgrid_remove_status, vgrid_remove_msg) = \
                vgrid_remove_imagesettings(configuration, vgrid,
                    remove_imagesettings_ids)

            if not vgrid_remove_status:
                status = returnvalues.ERROR
                ERROR_MSG = vgrid_remove_msg
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error(ERROR_MSG)

    return status


