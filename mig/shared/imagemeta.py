#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# imagemeta - Managing MiG image meta data
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

"""Image meta data helper functions"""

import os
import time
import traceback

import shared.returnvalues as returnvalues
from shared.defaults import img_trigger_prefix
from shared.fileio import touch, makedirs_rec, listdirs_rec, \
    delete_file, make_symlink, remove_dir
from shared.imagemetaio import get_image_file_setting, \
    get_image_volume_setting, get_image_file_count, \
    get_image_volume_count, remove_image_file_settings, \
    remove_image_volume_settings, __metapath, get_image_file_settings, \
    allowed_image_types, allowed_settings_status, \
    update_image_file_setting, update_image_volume_setting, \
    add_image_file_setting, add_image_volume_setting, __image_metapath, \
    __revision, get_image_file, get_image_volume, \
    get_preview_image_url, get_image_xdmf_filepath
from shared.vgrid import in_vgrid_share, vgrid_add_triggers, \
    vgrid_remove_triggers, vgrid_is_trigger, vgrid_add_imagesettings, \
    vgrid_remove_imagesettings
from shared.vgridaccess import get_vgrid_map_vgrids


def __get_preview_mrsl_template():
    """General template for image preview trigger jobs"""

    return """

::OUTPUTFILES::

::CPUTIME::
172800

::MEMORY::
2000000

::DISK::
100

::VGRID::

::RUNTIMEENVIRONMENT::
PYTHON-2.X-1
PYTHON-OPENCV-2.X-1
PYTABLES-3.X-1
PYLIBTIFF-0.X-1
"""


def __create_previews_mrsl_template(datapath, extension):
    """Template for changed image preview setting trigger jobs"""

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
ls -la 'shared/*'
ls -la '%(datapath)s/'
ls -la '%(datapath)s/.meta'
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


def __get_vgrid_datapath(vgrid_name, path):
    """Resolve vgrid datapath from *path*"""

    vgrid_datapath = path[len(vgrid_name):]

    return '/'.join([x for x in vgrid_datapath.split('/') if x])


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
        logger.debug('path: %s' % path)
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


def __is_valid_image_settings_update(
    configuration,
    base_dir,
    vgrid_name,
    vgrid_path,
    extension,
    settings_recursive,
    image_type,
    data_type,
    ):
    """Check if valid image settings update"""

    result = True
    msg = ''

    logger = configuration.logger

    # Check for image types

    if image_type not in allowed_image_types or data_type \
        not in allowed_image_types[image_type]:
        result = False
        msg = 'Invalid image and data_type: %s -> %s' % (image_type,
                data_type)

    # Check for vgrid

    if result:
        vgrid_list = get_vgrid_map_vgrids(configuration)
        if not vgrid_name in vgrid_list:
            result = False
            msg = "'%s' is _NOT_ workflow enabled." % vgrid_name

    # Check for child folder image settings

    if result and settings_recursive:

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
                result = False
                current_vgrid_path = path.replace(base_dir, '', 1)
                msg = \
                    "Settings for extension: '%s' found in path: '%s'." \
                    % (extension, current_vgrid_path)
                msg = '%s Overloading _NOT_ supported' % msg

    # Check for parent folder image settings

    if result:
        vgrid_path_array = ('%s/%s' % (vgrid_name,
                            vgrid_path)).split('/')[:-2]

        while result and len(vgrid_path_array) > 0:
            current_vgrid_path = os.sep.join(vgrid_path_array)
            abs_vgrid_path = os.path.join(base_dir, current_vgrid_path)
            try:
                image_meta = get_image_file_setting(logger,
                        abs_vgrid_path, extension)
            except Exception:
                image_meta = None
                logger.debug(str(traceback.format_exc()))
            if image_meta is not None \
                and image_meta['settings_recursive']:
                result = False
                msg = \
                    "settings for extension: '%s' found in path: '%s'." \
                    % (extension, current_vgrid_path)
                msg = '%s Overloading _NOT_ supported' % msg
            vgrid_path_array = vgrid_path_array[:-1]

    # Check image settings status

    abs_path = os.path.join(base_dir, os.path.join(vgrid_name,
                            vgrid_path))
    image_file_meta = get_image_file_setting(logger, abs_path,
            extension)
    if image_file_meta is not None and image_file_meta['settings_status'
            ] != allowed_settings_status['ready'] \
        and image_file_meta['settings_status'] \
        != allowed_settings_status['failed']:
        result = False
        msg = 'File not ready for update, status: %s' \
            % image_file_meta['settings_status']

    image_volume_meta = get_image_volume_setting(logger, abs_path,
            extension)
    if image_volume_meta is not None \
        and image_volume_meta['settings_status'] \
        != allowed_settings_status['ready'] \
        and image_volume_meta['settings_status'] \
        != allowed_settings_status['failed']:
        result = False
        msg = 'Volume not ready for update, status: %s' \
            % image_volume_meta['settings_status']

    return (result, msg)


def __remove_image_file_trigger(
    configuration,
    vgrid_name,
    path,
    extension,
    rule_id,
    output_objects,
    ):
    """Remove vgrid submit trigger for image files"""

    logger = configuration.logger
    trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
            configuration, recursive=False)
    status = returnvalues.OK
    if trigger_exists:
        (remove_status, remove_msg) = \
            vgrid_remove_triggers(configuration, vgrid_name, [rule_id])
        if remove_status:
            status = returnvalues.OK
            OK_MSG = \
                "Removed old image files trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Failed to remove old image files trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)
            logger.error('vgrid_remove_triggers returned: %s'
                         % remove_msg)
    else:
        logger.debug('No trigger: %s for vgrid: %s' % (rule_id,
                     vgrid_name))
    return status


def __get_image_file_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image file changes"""

    path_array = path.split('/')

    return '%s_%s_%s_files' % (img_trigger_prefix,
                               '_'.join(path_array), extension)


def __get_image_settings_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image settings changes"""

    path_array = path.split('/')
    logger.debug('checkpoint: %s' % str(path_array))
    return '%s_%s_%s_settings' % (img_trigger_prefix,
                                  '_'.join(path_array), extension)


def __remove_image_settings_trigger(
    configuration,
    vgrid_name,
    path,
    extension,
    rule_id,
    output_objects,
    ):
    """Remove vgrid submit trigger for image settings"""

    logger = configuration.logger

    trigger_exists = vgrid_is_trigger(vgrid_name, rule_id,
            configuration, recursive=False)
    status = returnvalues.OK
    if trigger_exists:
        (remove_status, remove_msg) = \
            vgrid_remove_triggers(configuration, vgrid_name, [rule_id])
        if remove_status:
            status = returnvalues.OK
            OK_MSG = \
                "Removed old image setting trigger for extension: '%s', path '%s'" \
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


def __get_vgrid_imagesetting_id(logger, path, extension):
    """Generate unique vgrid imagesettings id"""

    path_array = [x for x in path.split('/') if x]

    return '%s_%s' % ('_'.join(path_array), extension)


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

    logger.debug('get_volume: base_dir: %s' % base_dir)
    logger.debug('get_volume: path: %s' % path)
    volume_meta = __seek_volume_meta(logger, base_dir, path,
            data_entries=data_entries)
    logger.debug('volume_meta: : %s' % str(volume_meta))
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
        logger.debug('preview_xdmf_filename: %s'
                     % volume_meta['preview_xdmf_filename'])
        logger.debug('base_path: %s' % volume_meta['base_path'])
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

        logger.debug('get_volume name: %s' % name)

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


def list_image_meta_settings(
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
                    'No volume settings found for path: %s, extension: %s' \
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
        logger.debug('%s' % MSG)

    logger.debug('image_status: %s' % str(image_status))
    logger.debug('volume_status: %s' % str(volume_status))
    if image_status or volume_status:
        status = returnvalues.OK
        logger.debug('extension_list: %s' % str(extension_list))
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
        logger.debug('output_objects: %s' % str(output_objects))
    else:
        status = returnvalues.ERROR

    return status


def get_image_meta_setting(
    configuration,
    abs_path,
    path,
    extension,
    output_objects,
    ):
    """Get image meta setting for *path* and *extension*"""

    logger = configuration.logger
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
        output_objects.append({'object_type': 'text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


def create_image_meta_setting(
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
    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)
    vgrid_metapath = os.path.join(vgrid_datapath, __metapath)
    vgrid_image_metapath = os.path.join(vgrid_datapath,
            __image_metapath)

    settings_status = ''.join(create_dict['settings_status'])
    if ''.join(create_dict['settings_recursive']) == 'True':
        settings_recursive = True
    else:
        settings_recursive = False
    image_type = ''.join(create_dict['image_type'])
    data_type = ''.join(create_dict['data_type'])
    volume_slice_filepattern = \
        ''.join(create_dict['volume_slice_filepattern'])
    offset = int(''.join(create_dict['offset']))
    x_dimension = int(''.join(create_dict['x_dimension']))
    y_dimension = int(''.join(create_dict['y_dimension']))
    z_dimension = int(''.join(create_dict['z_dimension']))
    preview_image_extension = \
        ''.join(create_dict['preview_image_extension'])
    preview_x_dimension = int(''.join(create_dict['preview_x_dimension'
                              ]))
    preview_y_dimension = int(''.join(create_dict['preview_y_dimension'
                              ]))
    preview_z_dimension = int(''.join(create_dict['preview_z_dimension'
                              ]))
    preview_cutoff_min = float(''.join(create_dict['preview_cutoff_min'
                               ]))
    preview_cutoff_max = float(''.join(create_dict['preview_cutoff_max'
                               ]))

    settings_update_progress = None

    OK_MSG = \
        "Created/updated settings for image extension: '%s' for path '%s'" \
        % (extension, path)
    ERROR_MSG = \
        "Failed to change settings for image extension: '%s' for path: '%s'" \
        % (extension, path)

    (is_valid, is_valid_msg) = __is_valid_image_settings_update(
        configuration,
        base_dir,
        vgrid_name,
        vgrid_datapath,
        extension,
        settings_recursive,
        image_type,
        data_type,
        )

    if is_valid:
        status = returnvalues.OK
    else:
        status = returnvalues.ERROR
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        output_objects.append({'object_type': 'error_text',
                              'text': is_valid_msg})
        logger.error('%s' % ERROR_MSG)
        logger.error('%s' % is_valid_msg)

    # Ensure meta path existence

    if status == returnvalues.OK:
        makedirs_rec(os.path.join(base_dir, os.path.join(vgrid_name,
                     vgrid_metapath)), configuration)

        # Ensure image meta path existence

        makedirs_rec(os.path.join(base_dir, os.path.join(vgrid_name,
                     vgrid_image_metapath)), configuration)

        # Update image file settings

        try:
            add_status = add_image_file_setting(
                logger,
                abs_path,
                extension,
                settings_status,
                settings_update_progress,
                settings_recursive,
                image_type,
                data_type,
                offset,
                x_dimension,
                y_dimension,
                preview_image_extension,
                preview_x_dimension,
                preview_y_dimension,
                preview_cutoff_min,
                preview_cutoff_max,
                overwrite=True,
                )
        except Exception:
            add_status = False
            logger.debug(str(traceback.format_exc()))

        # Update image volume settings

        if add_status:
            if volume_slice_filepattern != '':
                volume_type = 'slice'
                try:
                    add_status = add_image_volume_setting(
                        logger,
                        abs_path,
                        extension,
                        settings_status,
                        settings_update_progress,
                        settings_recursive,
                        image_type,
                        volume_type,
                        data_type,
                        volume_slice_filepattern,
                        offset,
                        x_dimension,
                        y_dimension,
                        z_dimension,
                        preview_x_dimension,
                        preview_y_dimension,
                        preview_z_dimension,
                        preview_cutoff_min,
                        preview_cutoff_max,
                        overwrite=True,
                        )
                except Exception:
                    add_status = False
                    logger.debug(str(traceback.format_exc()))
            else:
                try:
                    remove_image_volume_settings(logger, abs_path,
                            extension)
                except Exception:
                    logger.debug(str(traceback.format_exc()))

        # Create image meta links used by Paraview render

        if add_status:
            logger.debug('paraview: path: %s' % path)

            dest_path = os.path.join(configuration.vgrid_files_home,
                    os.path.join(path, __metapath))

            paraview_datapath = os.path.join('worker', path)
            paraview_datapath_link = os.path.join(paraview_datapath,
                    __metapath)

            src_path = os.path.join(configuration.paraview_home,
                                    paraview_datapath)

            src_path_link = os.path.join(src_path, __metapath)

            logger.debug('paraview symlink dest_path: %s' % dest_path)
            logger.debug('paraview symlink src_path: %s' % src_path)
            logger.debug('paraview symlink src_path_link: %s'
                         % src_path_link)

            add_status = makedirs_rec(src_path, configuration)
            logger.debug('add_status checkpoint1: %s' % str(add_status))
            if add_status:

                add_status = make_symlink(dest_path, src_path_link,
                        logger, force=True)
                logger.debug('add_status checkpoint2: %s'
                             % str(add_status))

        # logger.debug('add_status checkpoint3: %s' % str(add_status))

        if add_status:
            status = returnvalues.OK
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)

    if status == returnvalues.OK:
        logger.debug('settings_recursive: %s' % settings_recursive)

        # Generate vgrid trigger for files

        if settings_recursive:
            vgrid_trigger_path = os.path.join(vgrid_datapath, '*/*.%s'
                    % extension)
        else:
            vgrid_trigger_path = os.path.join(vgrid_datapath, '*.%s'
                    % extension)

        rule_id = __get_image_file_trigger_rule_id(logger,
                vgrid_datapath, extension)
        logger.debug('RULE_ID: %s' % rule_id)
        logger.debug('vgrid_datapath: %s' % vgrid_datapath)
        rule_dict = {
            'rule_id': rule_id,
            'vgrid_name': vgrid_name,
            'path': vgrid_trigger_path,
            'match_dirs': False,
            'match_recursive': settings_recursive,
            'changes': ['created', 'modified', 'deleted', 'moved'],
            'run_as': client_id,
            'action': 'submit',
            'arguments': 'template_from_filemetaio.py',
            'templates': [__update_preview_mrsl_template(path)],
            'settle_time': '60s',
            'rate_limit': '',
            }

        # Remove old vgrid submit trigger for files

        status = __remove_image_file_trigger(
            configuration,
            vgrid_name,
            path,
            extension,
            rule_id,
            output_objects,
            )

    if status == returnvalues.OK:

        # Add generated vgrid submit trigger for files

        (add_status, add_msg) = vgrid_add_triggers(configuration,
                vgrid_name, [rule_dict])
        if add_status:
            status = returnvalues.OK
            OK_MSG = \
                "Created/updated image file trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Failed change image file trigger for extension: '%s', path '%s'" \
                % (extension, path)
            ERROR_MSG2 = "Makes sure '%s' is a VGrid" % vgrid_name
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG2})
            logger.error('%s' % ERROR_MSG)
            logger.error('%s' % ERROR_MSG2)

    if status == returnvalues.OK:

        # Generate vgrid trigger for settings

        vgrid_trigger_filepath = \
            __get_image_settings_trigger_last_modified_filepath(logger,
                vgrid_datapath, extension)

        rule_id = __get_image_settings_trigger_rule_id(logger,
                vgrid_datapath, extension)
        rule_dict = {
            'rule_id': rule_id,
            'rule_changes': ['created', 'deleted'],
            'vgrid_name': vgrid_name,
            'path': vgrid_trigger_filepath,
            'match_dirs': False,
            'match_recursive': False,
            'changes': ['modified', 'deleted'],
            'run_as': client_id,
            'action': 'submit',
            'arguments': 'template_from_filemetaio.py',
            'templates': [__create_previews_mrsl_template(path,
                          extension)],
            'settle_time': '1s',
            'rate_limit': '',
            }

        # Remove old vgrid submit trigger for settings

        status = __remove_image_settings_trigger(
            configuration,
            vgrid_name,
            path,
            extension,
            rule_id,
            output_objects,
            )

    if status == returnvalues.OK:

        # Add generated vgrid submit trigger for settings

        (add_status, add_msg) = vgrid_add_triggers(configuration,
                vgrid_name, [rule_dict])
        if add_status:
            status = returnvalues.OK
            OK_MSG = \
                "Created/updated old image setting trigger for extension: '%s', path '%s'" \
                % (extension, path)
            output_objects.append({'object_type': 'text',
                                  'text': OK_MSG})
        else:
            status = returnvalues.ERROR
            ERROR_MSG = \
                "Failed change old image setting trigger for extension: '%s', path '%s'" \
                % (extension, path)
            ERROR_MSG2 = "Makes sure '%s' is a VGrid" % vgrid_name
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG2})
            logger.error('%s' % ERROR_MSG)
            logger.error('%s' % ERROR_MSG2)

    if status == returnvalues.OK:
        imagesetting_id = __get_vgrid_imagesetting_id(configuration,
                vgrid_datapath, extension)
        imagesetting_dict = {
            'imagesetting_id': imagesetting_id,
            'metarev': __revision,
            'metapath': vgrid_metapath,
            'paraview': {'datapath': paraview_datapath_link},
            'triggers': {'settings': __get_image_settings_trigger_rule_id(logger,
                         vgrid_datapath, extension),
                         'files': __get_image_file_trigger_rule_id(logger,
                         vgrid_datapath, extension)},
            }

        logger.debug('imagesetting_dict: %s' % str(imagesetting_dict))

        vgrid_add_status = vgrid_add_imagesettings(configuration,
                vgrid_name, [imagesetting_dict])
        logger.debug('vgrid_add_status: %s' % str(vgrid_add_status))

        # Trigger Trigger (Trigger Happty)

        abs_vgrid_trigger_filepath = os.path.join(base_dir,
                os.path.join(vgrid_name, vgrid_trigger_filepath))

        # FYSIKER HACK: Sleep 1 to prevent trigger rule/event race
        # TODO: Modify events handler to accept add+trigger action

        time.sleep(1)
        timestamp = time.time()
        touch(abs_vgrid_trigger_filepath, timestamp)
    return status


def update_image_meta_setting(
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
    logger.debug('UPDATE: %s' % path)
    status = returnvalues.OK
    OK_MSG = "Updated settings for image extension: '%s' for path '%s'" \
        % (extension, path)
    ERROR_MSG = \
        "Failed to update settings for image extension: '%s' for path: '%s'" \
        % (extension, path)
    ERROR2_MSG = None

    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    # Update image file settings

    image_file_setting = get_image_file_setting(logger, abs_path,
            extension)
    if image_file_setting is not None:
        for (key, value) in image_file_setting.iteritems():

            # logger.debug('key: %s : %s -> %s' % (key, value, type(value)))

            if update_dict.has_key(key):
                user_value = value.dtype.type(''.join(update_dict[key]))
                if value != user_value:
                    logger.debug('updating image key: %s : %s -> %s'
                                 % (key, value, user_value))
                    image_file_setting[key] = user_value

    # Update image volume settings

    image_volume_setting = get_image_volume_setting(logger, abs_path,
            extension)
    if image_volume_setting is not None:
        for (key, value) in image_volume_setting.iteritems():
            if update_dict.has_key(key):
                user_value = value.dtype.type(''.join(update_dict[key]))
                if value != user_value:
                    logger.debug('update volume key: %s : %s -> %s'
                                 % (key, value, user_value))
                    image_volume_setting[key] = user_value

    if image_file_setting is None and image_volume_setting is None:
        status = returnvalues.ERROR

    if status == returnvalues.OK:
        settings_recursive = str(image_file_setting['settings_recursive'
                                 ])
        image_type = str(image_file_setting['image_type'])
        data_type = str(image_file_setting['data_type'])

        (is_valid, is_valid_msg) = __is_valid_image_settings_update(
            configuration,
            base_dir,
            vgrid_name,
            vgrid_datapath,
            extension,
            settings_recursive,
            image_type,
            data_type,
            )

        if is_valid:
            status = returnvalues.OK
        else:
            status = returnvalues.ERROR
            ERROR2_MSG = is_valid_msg

    # UPDATE tables

    if status == returnvalues.OK:

        # File settings

        file_status = True

        if image_file_setting is not None:
            image_file_setting['settings_status'] = \
                allowed_settings_status['pending']
            image_file_setting['settings_update_progress'] = None
            file_status = update_image_file_setting(logger, abs_path,
                    image_file_setting)

        # Volume settings

        volume_status = True
        if image_volume_setting is not None:
            image_volume_setting['settings_status'] = \
                allowed_settings_status['pending']
            image_volume_setting['settings_update_progress'] = None
            volume_status = update_image_volume_setting(logger,
                    abs_path, image_volume_setting)

        if not (file_status and volume_status):
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
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR2_MSG})
        logger.error('%s' % ERROR_MSG)
        logger.error('%s' % ERROR2_MSG)

    return status


def remove_image_meta_setting(
    configuration,
    abs_path,
    path,
    extension,
    output_objects,
    ):
    """Remove image meta setting for *path* and *extension*"""

    logger = configuration.logger

    vgrid_name = in_vgrid_share(configuration, abs_path)
    vgrid_datapath = __get_vgrid_datapath(vgrid_name, path)

    if extension != '':
        remove_ext = extension
    try:
        (file_status, removed_ext_list) = \
            remove_image_file_settings(logger, abs_path, remove_ext)
    except Exception:
        file_status = None
        logger.debug(str(traceback.format_exc()))

    try:
        (volume_status, _) = remove_image_volume_settings(logger,
                abs_path, remove_ext)
    except Exception:
        volume_status = None
        logger.debug(str(traceback.format_exc()))
    logger.debug('volume_status: %s' % str(volume_status))

    if file_status is not None:
        status = returnvalues.OK
        OK_MSG = \
            "Removed settings for image extension: '%s' for path '%s'" \
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

        if delete_file(abs_last_modified_filepath, logger):

            # FYSIKER HACK: Sleep 1 to prevent trigger rule/event race
            # TODO: Modify events handler to accept trigger action + delete

            time.sleep(1)

            # Remove old vgrid submit trigger for files

            rule_id = __get_image_file_trigger_rule_id(logger,
                    vgrid_datapath, removed_ext)
            remove_status = __remove_image_file_trigger(
                configuration,
                vgrid_name,
                path,
                extension,
                rule_id,
                output_objects,
                )
            if remove_status != returnvalues.OK:
                status = remove_status

            # Remove old vgrid submit trigger for settings

            rule_id = __get_image_settings_trigger_rule_id(logger,
                    vgrid_datapath, removed_ext)
            remove_status = __remove_image_settings_trigger(
                configuration,
                vgrid_name,
                path,
                extension,
                rule_id,
                output_objects,
                )
            if remove_status != returnvalues.OK:
                status = remove_status
        else:
            status = returnvalues.ERROR
            ERROR_MSG = 'Unable to remove file: %s ' \
                % abs_last_modified_filepath
            output_objects.append({'object_type': 'text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)

    # Remove image meta links used by Paraview render

    paraview_path = os.path.join(configuration.paraview_home,
                                 os.path.join('worker', path))
    paraview_link = os.path.join(paraview_path, __metapath)

    logger.debug('deleting Paraview link: %s' % paraview_link)

    if not delete_file(paraview_link, logger):
        status = returnvalues.ERROR
        ERROR_MSG = 'Unable to remove paraview link: %s ' \
            % str(paraview_link)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)
    else:
        logger.debug('removing paraview_path: %s' % paraview_path)
        remove_dir_status = remove_dir(paraview_path, configuration)
        logger.debug('remove_dir_status: %s' % remove_dir_status)
        path_array = path.split('/')
        pos = len(path_array) - 2
        while remove_dir_status:
            logger.debug('removing paraview_path pos: %s' % pos)
            logger.debug('removing path: %s' % path_array[:pos])
            remove_path = os.path.join(configuration.paraview_home,
                    os.path.join('worker',
                    os.sep.join(path_array[:pos])))
            logger.debug('removing paraview_path: %s' % remove_path)
            remove_dir_status = remove_dir(remove_path, configuration)
            logger.debug('remove_dir_status: %s' % remove_dir_status)
            pos -= 1

    imagesetting_id = __get_vgrid_imagesetting_id(configuration,
            vgrid_datapath, '')

    for removed_ext in removed_ext_list:

        imagesetting_remove_id = '%s%s' % (imagesetting_id, removed_ext)

        logger.debug('removing: %s' % imagesetting_remove_id)
        (vgrid_remove_status, _) = \
            vgrid_remove_imagesettings(configuration, vgrid_name,
                [imagesetting_remove_id])
        logger.debug('vgrid_remove_status: %s' % vgrid_remove_status)

        if not vgrid_remove_status:
            status = returnvalues.ERROR
            ERROR_MSG = 'Unable to remove imagesetting with id: %s ' \
                % str(imagesetting_remove_id)
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('%s' % ERROR_MSG)

    return status


def reset_image_meta_setting_status(
    configuration,
    abs_path,
    path,
    extension,
    output_objects,
    ):
    """Reset status for image meta setting with *path* and *extension*"""

    logger = configuration.logger
    status = returnvalues.OK
    file_reset = volume_reset = True

    image_file_settings = get_image_file_setting(logger, abs_path,
            extension)

    if image_file_settings is not None:
        image_file_settings['settings_status'] = \
            allowed_settings_status['ready']
        image_file_settings['settings_update_progress'] = None
        file_reset = update_image_file_setting(logger, abs_path,
                image_file_settings)
        MSG = 'Image file settings reset: %s' % file_reset
        output_objects.append({'object_type': 'text', 'text': MSG})

        # Check volume setting
        # NOTE: Volume setting is _NOT_ required

    image_volume_settings = get_image_volume_setting(logger, abs_path,
            extension)
    if image_volume_settings is not None:
        image_volume_settings['settings_status'] = \
            allowed_settings_status['ready']
        image_volume_settings['settings_update_progress'] = None
        volume_reset = update_image_volume_setting(logger, abs_path,
                image_volume_settings)
        MSG = 'Image volume settings reset: %s' % file_reset
        output_objects.append({'object_type': 'text', 'text': MSG})
    else:
        MSG = \
            'No image volume settings found for path: %s, extension: %s' \
            % (path, extension)
        output_objects.append({'object_type': 'error_text',
                              'text': MSG})
    if image_file_settings is None and image_volume_settings is None:
        status = returnvalues.ERROR
        ERROR_MSG = \
            'No image file/volume settings found for path: %s, extension: %s' \
            % (path, extension)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})

    return status


def get_image_meta(
    configuration,
    base_dir,
    path,
    output_objects,
    ):
    """Get image meta for file with *path*"""

    logger = configuration.logger

    # Get image settings, image- and volume-meta inforation for file base_dir/path

    logger.debug('base_dir: %s' % base_dir)
    logger.debug('path: %s' % path)

    image_meta = __get_image_meta(logger, base_dir, path,
                                  data_entries=['preview_histogram'])

    logger.debug('IMAGE_META: %s' % str(image_meta))

    volume_meta = __get_volume_meta(logger, base_dir, path,
                                    data_entries=['preview_histogram'])
    if image_meta is not None:
        logger.debug('get_info: image meta')
        output_objects.append(image_meta)

        # Return image settings as well as image meta

        abs_base_path = os.path.join(base_dir, image_meta['base_path'])

        image_settings = __get_image_meta_setting(logger,
                abs_base_path, image_meta['path'],
                image_meta['extension'])
        if image_settings is not None:
            logger.debug('get_info: image meta -> image_settings')
            output_objects.append(image_settings)
        else:
            logger.debug('missing image_settings for path: %s, extension: %s'
                          % (image_meta['path'], image_meta['extension'
                         ]))

        # Volume exists and is generated from stack of slices
        # Return alogn with image_meta

        if image_settings['volume_count'] > 0 \
            and image_settings['volume_type'] == 'slice':
            volume_path = os.path.join(image_meta['base_path'],
                    os.path.join(image_meta['path'],
                    os.path.join(image_settings['volume_slice_filepattern'
                    ])))

            slice_volume_meta = __get_volume_meta(logger, base_dir,
                    volume_path)
            if slice_volume_meta is not None:
                logger.debug('get_info: image meta -> slice_volume_meta'
                             )
                output_objects.append(slice_volume_meta)
            else:
                logger.debug('missing slice_volume_meta for path: %s'
                             % path)

        status = returnvalues.OK

    if volume_meta is not None:
        logger.debug('get_info: volume_meta')
        output_objects.append(volume_meta)

        abs_base_path = os.path.join(base_dir, volume_meta['base_path'])

        image_settings = __get_image_meta_setting(logger,
                abs_base_path, volume_meta['extension'])
        if image_settings is not None:
            logger.debug('get_info: volume_meta -> image_settings')
            output_objects.append(image_settings)
        else:
            logger.debug('missing image_settings for path: %s, extension: %s'
                          % (image_meta['path'], image_meta['extension'
                         ]))

        status = returnvalues.OK

    if image_meta is None and volume_meta is None:
        status = returnvalues.ERROR
        ERROR_MSG = 'No meta information for file: %s' % path
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('%s' % ERROR_MSG)

    return status


