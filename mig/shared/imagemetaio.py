#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# imagemetaio - Managing MiG image meta data
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

from tables import open_file
import tables.exceptions
from numpy import dtype, float32, float64, uint8, uint16, uint32, \
    uint64, int8, int16, int32, int64, empty
from shared.fileio import acquire_file_lock, release_file_lock
import traceback

__revision = '3093'
__metapath = '.meta'
__settings_file = 'settings.h5'
__settings_filepath = os.path.join(__metapath, __settings_file)
__image_metapath = os.path.join(__metapath, 'image')
__image_preview_path = os.path.join(__image_metapath, 'preview')
__image_xdmf_path = os.path.join(__metapath, 'xdmf')

__tables_settings_group = '/settings'
__tables_settings_image_file_types_table = '/settings/image_file_types'
__tables_settings_image_volume_types_table = \
    '/settings/image_volume_types'
__tables_image_group = '/image'
__tables_image_files_group = '/image/files'
__tables_image_files_meta_table = '/image/files/meta'
__tables_image_files_preview_group = '/image/files/preview'
__tables_image_files_preview_data_group = '/image/files/preview/data'
__tables_image_files_preview_image_group = '/image/files/preview/image'
__tables_image_files_preview_histogram_group = \
    '/image/files/preview/histogram'
__tables_image_volumes_group = '/image/volumes'
__tables_image_volumes_meta_table = '/image/volumes/meta'
__tables_image_volumes_preview_group = '/image/volumes/preview'
__tables_image_volumes_preview_data_group = \
    '/image/volumes/preview/data'
__tables_image_volumes_preview_histogram_group = \
    '/image/volumes/preview/histogram'

allowed_settings_status = {
    'ready': 'Ready',
    'pending': 'Pending',
    'updating': 'Updating',
    'failed': 'Failed',
    }

allowed_data_types = {
    'float32': float32,
    'float64': float64,
    'uint8': uint8,
    'uint16': uint16,
    'uint32': uint32,
    'uint64': uint64,
    'int8': int8,
    'int16': int16,
    'int32': int32,
    'int64': int64,
    }

allowed_xdmf_data_types = {'float32': 'Float',
			   'uint16': 'UInt'}

allowed_xdmf_precisions = {'float32': 4,
			   'uint16': 2}

allowed_image_types = {'raw': allowed_data_types.keys(),
                       'tiff': ['uint8', 'uint16']}

allowed_volume_types = ['slice', 'file']

image_file_settings_ent = dtype([
    ('extension', 'S16'),
    ('settings_status', 'S8'),
    ('settings_update_progress', 'S64'),
    ('settings_recursive', bool),
    ('image_type', 'S8'),
    ('data_type', 'S8'),
    ('offset', uint64),
    ('x_dimension', uint64),
    ('y_dimension', uint64),
    ('preview_image_extension', 'S16'),
    ('preview_x_dimension', uint64),
    ('preview_y_dimension', uint64),
    ('preview_cutoff_min', float64),
    ('preview_cutoff_max', float64),
    ])

image_file_ent = dtype([
    ('extension', 'S16'),
    ('image_type', 'S8'),
    ('base_path', 'S4096'),
    ('path', 'S4096'),
    ('name', 'S4096'),
    ('data_type', 'S8'),
    ('offset', uint64),
    ('x_dimension', uint64),
    ('y_dimension', uint64),
    ('min_value', float64),
    ('max_value', float64),
    ('mean_value', float64),
    ('median_value', float64),
    ('file_md5sum', 'S4096'),
    ('preview_image_filename', 'S4096'),
    ('preview_image_extension', 'S16'),
    ('preview_data_type', 'S8'),
    ('preview_x_dimension', uint64),
    ('preview_y_dimension', uint64),
    ('preview_cutoff_min', float64),
    ('preview_cutoff_max', float64),
    ('preview_image_scale', float64),
    ])

image_volume_settings_ent = dtype([
    ('extension', 'S16'),
    ('settings_status', 'S8'),
    ('settings_update_progress', 'S64'),
    ('settings_recursive', bool),
    ('volume_type', 'S8'),
    ('image_type', 'S8'),
    ('data_type', 'S8'),
    ('volume_slice_filepattern', 'S4096'),
    ('offset', uint64),
    ('x_dimension', uint64),
    ('y_dimension', uint64),
    ('z_dimension', uint64),
    ('preview_x_dimension', uint64),
    ('preview_y_dimension', uint64),
    ('preview_z_dimension', uint64),
    ('preview_cutoff_min', float64),
    ('preview_cutoff_max', float64),
    ])

image_volume_ent = dtype([
    ('extension', 'S16'),
    ('image_type', 'S8'),
    ('base_path', 'S4096'),
    ('path', 'S4096'),
    ('name', 'S4096'),
    ('data_type', 'S8'),
    ('volume_type', 'S8'),
    ('offset', uint64),
    ('x_dimension', uint64),
    ('y_dimension', uint64),
    ('z_dimension', uint64),
    ('min_value', float64),
    ('max_value', float64),
    ('mean_value', float64),
    ('median_value', float64),
    ('file_md5sum', 'S4096'),
    ('preview_xdmf_filename', 'S4096'),
    ('preview_data_type', 'S8'),
    ('preview_x_dimension', uint64),
    ('preview_y_dimension', uint64),
    ('preview_z_dimension', uint64),
    ('preview_cutoff_min', float64),
    ('preview_cutoff_max', float64),
    ])

preview_image_settings = {
    'image_type': 'png',
    'extension': 'png',
    'x_dimension': 256,
    'y_dimension': 256,
    }

preview_volume_settings = {
    'image_type': 'raw',
    'extension': 'raw',
    'x_dimension': 256,
    'y_dimension': 256,
    'z_dimension': 256,
    }


def __ensure_filepath(logger, filepath, makedirs=False):
    """Ensure that meta file path exists"""

    result = None

    if makedirs:
        try:
            os.makedirs(filepath)
        except Exception, ex:
            if not os.path.exists(filepath):
                logger.debug('__ensure_filepath: %s' % str(ex))

    if os.path.exists(filepath):
        result = filepath

    return result


def __get_settings_filepath(logger, base_path, makedirs=False):
    """Returns settings filepath, created if non-existent"""

    result = None

    metapath = os.path.join(base_path, __metapath)
    if __ensure_filepath(logger, metapath, makedirs) is not None:
        result = os.path.join(base_path, __settings_filepath)

    return result


def __get_image_metapath(logger, base_path, makedirs=False):
    """Returns image meta path, created if non-existent"""

    result = None

    if __ensure_filepath(logger, base_path, makedirs) is not None:
        image_metapath = os.path.join(base_path, __image_metapath)
        result = __ensure_filepath(logger, image_metapath, makedirs)

    return result


def __ensure_tables_format(logger, metafile):
    """Ensure that pytables in metafile has the correct structure"""

    tables = metafile['tables']

    root = tables.root

    if not tables.__contains__(__tables_settings_group):
        settings_group = tables.create_group('/', 'settings',
                'Directory Settings Entries')
    else:
        settings_group = root.settings

    if not tables.__contains__(__tables_settings_image_file_types_table):
        tables.create_table(settings_group, 'image_file_types',
                            image_file_settings_ent, 'Image File Types')
    if not tables.__contains__(__tables_settings_image_volume_types_table):
        tables.create_table(settings_group, 'image_volume_types',
                            image_volume_settings_ent,
                            'Image Volume Types')

    if not tables.__contains__(__tables_image_group):
        image_group = tables.create_group('/', 'image',
                'Directory Image Entries')
    else:
        image_group = root.image

    if not tables.__contains__(__tables_image_files_group):
        image_files_group = tables.create_group(image_group, 'files',
                'Image Files')
    else:
        image_files_group = root.image.files

    if not tables.__contains__(__tables_image_files_meta_table):
        tables.create_table(image_files_group, 'meta', image_file_ent,
                            'Image Files Metadata')

    if not tables.__contains__(__tables_image_files_preview_group):
        image_files_preview_group = \
            tables.create_group(image_files_group, 'preview',
                                'Image File Previews')
    else:
        image_files_preview_group = root.image.files.preview

    if not tables.__contains__(__tables_image_files_preview_data_group):
        image_files_preview_data_group = \
            tables.create_group(image_files_preview_group, 'data',
                                'Image File Preview Data')
    else:
        image_files_preview_data_group = root.image.files.preview.data

    if not tables.__contains__(__tables_image_files_preview_image_group):
        image_files_preview_image_group = \
            tables.create_group(image_files_preview_group, 'image',
                                'Image File Preview Image')
    else:
        image_files_preview_image_group = root.image.files.preview.image

    if not tables.__contains__(__tables_image_files_preview_histogram_group):
        image_files_preview_histogram_group = \
            tables.create_group(image_files_preview_group, 'histogram',
                                'Image File Preview Histograms')

    if not tables.__contains__(__tables_image_volumes_group):
        image_volumes_group = tables.create_group(image_group, 'volumes'
                , 'Image Volumes')
    else:
        image_volumes_group = root.image.volumes

    if not tables.__contains__(__tables_image_volumes_meta_table):
        tables.create_table(image_volumes_group, 'meta',
                            image_volume_ent, 'Image Volumes Metadata')

    if not tables.__contains__(__tables_image_volumes_preview_group):
        image_volumes_preview_group = \
            tables.create_group(image_volumes_group, 'preview',
                                'Image Volume Previews')
    else:
        image_volumes_preview_group = root.image.volumes.preview

    if not tables.__contains__(__tables_image_volumes_preview_data_group):
        image_volumes_preview_data_group = \
            tables.create_group(image_volumes_preview_group, 'data',
                                'Image Volume Preview Data')
    else:
        image_volumes_preview_data_group = \
            root.image.volumes.preview.data

    # TODO: Do we want this ?

    if not tables.__contains__(__tables_image_volumes_preview_histogram_group):
        image_volumes_preview_histogram_group = \
            tables.create_group(image_volumes_preview_group, 'histogram'
                                , 'Image Volume Preview Histograms')
    else:
        image_volumes_preview_histogram_group = \
            root.image.volumes.preview.histogram

    return tables


def __clean_image_preview_path(logger, base_path):
    """Clean image preview path"""

    result = True

    abs_preview_path = os.path.join(base_path, __image_preview_path)

    if os.path.exists(abs_preview_path):
        for file_ent in os.listdir(abs_preview_path):

            # TODO: Uncomment action below when sure paths are correct
            # os.remove(file_ent)

            logger.info('imagefileio.py: (dry run) Removing preview file: %s'
                         % file_ent)

    return result


def __open_image_settings_file(logger, base_path, makedirs=False):
    """Opens image settings file with exclusive lock.
    NOTE: Locks are not consistently enforced through fuse"""

    logger.debug('base_path: %s' % base_path)

    metafile = None

    if __ensure_filepath(logger, base_path, makedirs) is not None:

        image_settings_filepath = __get_settings_filepath(logger,
                base_path, makedirs)
        logger.debug('image_settings_filepath: %s'
                     % image_settings_filepath)

        if image_settings_filepath is not None:
            metafile = {}
            metafile['lock'] = __acquire_file_lock(logger,
                    image_settings_filepath)

            if image_settings_filepath is not None:
                if os.path.exists(image_settings_filepath):
                    filemode = 'r+'
                else:
                    filemode = 'w'
                try:
                    metafile['tables'] = \
                        open_file(image_settings_filepath,
                                  mode=filemode,
                                  title='Image directory meta-data file'
                                  )
                    __ensure_tables_format(logger, metafile)
                except Exception, ex:
                    logger.error("opening: '%s' in mode '%s'"
                                 % (image_settings_filepath, filemode))
                    logger.error(traceback.format_exc())
                    __close_image_settings_file(logger, metafile)
                    metafile = None

    return metafile


def __close_image_settings_file(logger, metafile):
    """Closes image settings file releasing exclusive lock.
    NOTE: Locks are not consistently enforced through fuse"""

    result = True

    if metafile is not None:
        if metafile.has_key('tables'):
            try:
                metafile['tables'].close()
            except Exception, ex:
                logger.error(traceback.format_exc())
                result = False

        if metafile.has_key('lock'):
            try:
                __release_file_lock(logger, metafile)
            except Exception, ex:
                logger.error(traceback.format_exc())
                result = False

    return result


def __acquire_file_lock(logger, image_settings_filepath):
    """Obtain lock.
    NOTE: Locks are not consistently enforced through fuse"""

    lock_path = '%s.lock' % image_settings_filepath
    logger.debug('lock_path: %s' % lock_path)

    return acquire_file_lock(lock_path)


def __release_file_lock(logger, metafile):
    """Release lock.
    NOTE: Locks are not consistently enforced through fuse"""

    result = True
    lock_handle = metafile['lock']
    logger.debug('lock_path: %s' % lock_handle.name)
    release_file_lock(lock_handle)

    return result


def __get_image_file_settings_node(logger, metafile):
    """Returns image file settings node"""

    return metafile['tables'].root.settings.image_file_types


def __get_image_file_meta_node(logger, metafile):
    """Returns image file meta node"""

    return metafile['tables'].root.image.files.meta


def __get_image_file_data_node(logger, metafile):
    """Returns image file data node"""

    return metafile['tables'].root.image.files.preview.data


def __get_image_file_image_node(logger, metafile):
    """Returns image file image node"""

    return metafile['tables'].root.image.files.preview.image


def __get_image_file_histogram_node(logger, metafile):
    """Returns image file histogram node"""

    return metafile['tables'].root.image.files.preview.histogram


def __get_image_volume_settings_node(logger, metafile):
    """Returns image file settings node"""

    return metafile['tables'].root.settings.image_volume_types


def __get_image_volume_meta_node(logger, metafile):
    """Returns image file meta node"""

    return metafile['tables'].root.image.volumes.meta


def __get_image_volume_data_node(logger, metafile):
    """Returns image file data node"""

    return metafile['tables'].root.image.volumes.preview.data


def __get_image_volume_histogram_node(logger, metafile):
    """Returns image volume histogram node"""

    return metafile['tables'].root.image.volumes.preview.histogram


def __get_data_node_name(logger, path, name):
    """Returns data node name"""

    result = os.path.join(path, name)
    result = result.replace('/', '|')

    return result


def __add_image_file_ent(
    logger,
    table_row,
    extension,
    image_type,
    settings_status=None,
    settings_update_progress=None,
    settings_recursive=None,
    data_type=None,
    base_path=None,
    path=None,
    name=None,
    offset=0,
    x_dimension=0,
    y_dimension=0,
    min_value=0,
    max_value=0,
    mean_value=0,
    median_value=0,
    file_md5sum=None,
    preview_image_filename=None,
    preview_image_extension=None,
    preview_data_type=None,
    preview_x_dimension=0,
    preview_y_dimension=0,
    preview_cutoff_min=0,
    preview_cutoff_max=0,
    preview_image_scale=0,
    update=False,
    settings=False,
    ):
    """Add image setting or file entry"""

    if not image_type in allowed_image_types:
        logger.error("Image_type: '%s' not in allowed: %s'"
                     % (image_type, allowed_image_types))
        return None

    if settings and image_type == 'raw':
        if offset is None and x_dimension is None and y_dimension \
            is None and data_type is None:
            msg = "settings for: '%s', image_type: '%s'" % (extension,
                    image_type)
            msg = \
                '%s missing offset, x_dimension, y_dimension and data_type' \
                % msg
            logger.warning(msg)

    table_row['extension'] = extension
    table_row['image_type'] = image_type
    table_row['data_type'] = data_type
    table_row['offset'] = offset
    table_row['x_dimension'] = x_dimension
    table_row['y_dimension'] = y_dimension
    table_row['preview_image_extension'] = preview_image_extension
    table_row['preview_x_dimension'] = preview_x_dimension
    table_row['preview_y_dimension'] = preview_y_dimension
    table_row['preview_cutoff_min'] = preview_cutoff_min
    table_row['preview_cutoff_max'] = preview_cutoff_max

    if settings == True:
        table_row['settings_status'] = settings_status
        table_row['settings_update_progress'] = settings_update_progress
        table_row['settings_recursive'] = settings_recursive
    else:
        table_row['base_path'] = base_path
        table_row['path'] = path
        table_row['name'] = name
        table_row['min_value'] = min_value
        table_row['max_value'] = max_value
        table_row['mean_value'] = mean_value
        table_row['median_value'] = median_value
        table_row['file_md5sum'] = file_md5sum
        table_row['preview_image_filename'] = preview_image_filename
        table_row['preview_data_type'] = preview_data_type
        table_row['preview_image_scale'] = preview_image_scale

    if update:
        table_row.update()
    else:
        table_row.append()

    logger.debug('added table_row: %s' % str(table_row))

    return table_row


def __get_row_idx_list(logger, table, condition):
    """Get a list of row indexes from *table*, based
    on *condition*, if condition is '' return all row indexes"""

    logger.debug("condition: '%s'" % condition)

    if condition is None or condition == '':
        row_list = [i for i in xrange(table.nrows)]
    else:
        row_list = table.get_where_list(condition)

    return row_list


def __remove_row(
    logger,
    metafile,
    table,
    row_idx,
    ):
    """Remove row with index *row_idx* from *table*"""

    result = None

    nodepath = table._v_pathname

    # If last row, delete and re-create table structure to get around:
    # PyTables NotImplementedError: You are trying to delete all the rows in table
    # This is not supported right now due to limitations on the underlying HDF5 library

    if table.nrows > 1:
        logger.debug('row_idx: %s' % row_idx)
        table.remove_row(row_idx)
        result = table
    else:
        logger.debug('rebuild settings_table')
        table._f_remove(recursive=True, force=True)
        __ensure_tables_format(logger, metafile)
        result = metafile['tables'].get_node(nodepath)

    return result


def __remove_image_files(
    logger,
    metafile,
    base_path,
    path=None,
    name=None,
    extension=None,
    ):
    """Remove image files, based on *path*, *name* and *extension*"""

    status = False
    removed = []

    logger.debug('base_path: %s, path: %s, name: %s, extension: %s'
                 % (base_path, path, name, extension))

    if metafile is not None:
        image_file_table = __get_image_file_meta_node(logger, metafile)

        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)

        row_list = __get_row_idx_list(logger, image_file_table,
                condition)

        logger.debug('Removing #%s row(s)' % len(row_list))

        status = True
        while status and len(row_list) > 0:
            row_idx = row_list[0]
            table_row = image_file_table[row_idx]
            row_base_path = table_row['base_path']
            row_path = table_row['path']
            row_name = table_row['name']
            row_preview_image_filename = \
                table_row['preview_image_filename']
            if __remove_image_file_preview(
                logger,
                metafile,
                row_base_path,
                row_path,
                row_name,
                row_preview_image_filename,
                ):
                if row_path != '':
                    removed.append('%s/%s' % (row_base_path.strip('/'),
                                   row_name.strip('/')))
                else:
                    removed.append('%s/%s/%s' % (row_base_path.strip('/'
                                   ), row_path.strip('/'),
                                   row_name.strip('/')))
                image_file_table = __remove_row(logger, metafile,
                        image_file_table, row_idx)
                row_list = __get_row_idx_list(logger, image_file_table,
                        condition)
            else:
                status = False

    logger.debug('status: %s, removed: %s' % (str(status),
                 str(removed)))

    return (status, removed)


def __remove_image_file_preview(
    logger,
    metafile,
    base_path,
    path,
    name,
    preview_image_filename,
    ):
    """Remove image preview file, data and histogram"""

    result = False
    preview_data_group = __get_image_file_data_node(logger, metafile)
    preview_image_group = __get_image_file_image_node(logger, metafile)
    preview_histogram_group = __get_image_file_histogram_node(logger,
            metafile)

    image_array_name = __get_data_node_name(logger, path, name)

    # Remove preview image file

    abs_preview_image_filename = os.path.join(base_path,
            os.path.join(__image_preview_path, preview_image_filename))

    logger.debug('removing preview image: %s'
                 % abs_preview_image_filename)
    if os.path.exists(abs_preview_image_filename):
        os.remove(abs_preview_image_filename)

    # Remove preview data

    if preview_data_group.__contains__(image_array_name):
        logger.debug('removing preview data: %s' % image_array_name)
        preview_data_group.__getattr__(image_array_name).remove()
    else:
        logger.debug('missing preview data: %s' % image_array_name)

    # Remove preview image

    if preview_image_group.__contains__(image_array_name):
        logger.debug('removing preview image: %s' % image_array_name)
        preview_image_group.__getattr__(image_array_name).remove()
    else:
        logger.debug('missing preview image: %s' % image_array_name)

    # Remove histogram data

    if preview_histogram_group.__contains__(image_array_name):
        logger.debug('removing preview histogram: %s'
                     % image_array_name)
        preview_histogram_group.__getattr__(image_array_name).remove()
    else:
        logger.debug('missing preview histogram: %s' % image_array_name)

    result = True

    return result


def __get_image_file_preview_data(
    logger,
    metafile,
    path,
    filename,
    ):
    """Returns handle to preview data table array"""

    result = None

    if metafile is not None:
        data_group = __get_image_file_data_node(logger, metafile)
        name = __get_data_node_name(logger, path, filename)

        try:
            result = data_group.__getattr__(name)
            logger.debug('type: %s, data_ent: %s, %s, %s'
                         % (type(result), result.dtype, result.shape,
                         result))
        except tables.exceptions.NoSuchNodeError:
            result = None
    return result


def __get_image_file_preview_image(
    logger,
    metafile,
    path,
    filename,
    ):
    """Returns handle to rescaled and resized preview data table array"""

    result = None

    if metafile is not None:
        data_group = __get_image_file_image_node(logger, metafile)
        name = __get_data_node_name(logger, path, filename)

        try:
            result = data_group.__getattr__(name)
            logger.debug('type: %s, data_ent: %s, %s, %s'
                         % (type(result), result.dtype, result.shape,
                         result))
        except tables.exceptions.NoSuchNodeError:
            result = None
    return result


def __get_image_file_preview_histogram_data(
    logger,
    metafile,
    path,
    filename,
    ):
    """Returns handle to preview histogram table array"""

    result = None

    if metafile is not None:
        histogram_group = __get_image_file_histogram_node(logger,
                metafile)
        name = __get_data_node_name(logger, path, filename)

        try:
            result = histogram_group.__getattr__(name)
            logger.debug('type: %s, data_ent: %s, %s, %s'
                         % (type(result), result.dtype, result.shape,
                         result))
        except tables.exceptions.NoSuchNodeError:
            result = None

    return result


def __add_image_volume_ent(
    logger,
    table_row,
    extension,
    image_type,
    volume_type,
    settings_status=None,
    settings_update_progress=None,
    settings_recursive=None,
    data_type=None,
    base_path=None,
    path=None,
    name=None,
    volume_slice_filepattern=None,
    offset=0,
    x_dimension=0,
    y_dimension=0,
    z_dimension=0,
    min_value=0,
    max_value=0,
    mean_value=0,
    median_value=0,
    file_md5sum=None,
    preview_xdmf_filename=None,
    preview_data_type=None,
    preview_x_dimension=0,
    preview_y_dimension=0,
    preview_z_dimension=0,
    preview_cutoff_min=0,
    preview_cutoff_max=0,
    update=False,
    settings=False,
    ):
    """Add image voloume setting or entry"""

    logger.debug('extension: %s' % extension)
    logger.debug('image_type: %s' % image_type)
    logger.debug('volume_type: %s' % volume_type)
    logger.debug('settings_status: %s' % settings_status)
    logger.debug('settings_update_progress: %s'
                 % settings_update_progress)
    logger.debug('settings_recursive: %s' % settings_recursive)
    logger.debug('data_type: %s' % data_type)
    logger.debug('base_path: %s' % base_path)
    logger.debug('path: %s' % path)
    logger.debug('name: %s' % name)
    logger.debug('volume_slice_filepattern: %s'
                 % volume_slice_filepattern)
    logger.debug('offset: %s' % offset)
    logger.debug('x_dimension: %s' % x_dimension)
    logger.debug('y_dimension: %s' % y_dimension)
    logger.debug('z_dimension: %s' % z_dimension)
    logger.debug('min_value: %s' % min_value)
    logger.debug('max_value: %s' % max_value)
    logger.debug('mean_value: %s' % mean_value)
    logger.debug('median_value: %s' % median_value)
    logger.debug('file_md5sum: %s' % file_md5sum)
    logger.debug('preview_xdmf_filename: %s' % preview_xdmf_filename)
    logger.debug('preview_data_type: %s' % preview_data_type)
    logger.debug('preview_x_dimension: %s' % preview_x_dimension)
    logger.debug('preview_y_dimension: %s' % preview_y_dimension)
    logger.debug('preview_z_dimension: %s' % preview_z_dimension)
    logger.debug('preview_cutoff_min: %s' % preview_cutoff_min)
    logger.debug('preview_cutoff_max: %s' % preview_cutoff_max)
    logger.debug('update: %s' % str(update))
    logger.debug('settings: %s' % str(settings))

    if not image_type in allowed_image_types:
        logger.error("Image type: '%s' not in allowed: %s'"
                     % (image_type, allowed_image_types))
        return None

    if not volume_type in allowed_volume_types:
        logger.error("Volume type: '%s' not in allowed: %s'"
                     % (volume_type, allowed_volume_types))
        return None

    if settings and image_type == 'raw':
        if offset is None and x_dimension is None and y_dimension \
            is None and data_type is None:
            msg = "settings for: '%s', image_type: '%s'" % (extension,
                    image_type)
            msg = \
                '%s missing offset, x_dimension, y_dimension and data_type' \
                % msg
            logger.warning(msg)

    table_row['extension'] = extension
    table_row['image_type'] = image_type
    table_row['volume_type'] = volume_type
    table_row['data_type'] = data_type
    table_row['offset'] = offset
    table_row['x_dimension'] = x_dimension
    table_row['y_dimension'] = y_dimension
    table_row['z_dimension'] = z_dimension
    table_row['preview_x_dimension'] = preview_x_dimension
    table_row['preview_y_dimension'] = preview_y_dimension
    table_row['preview_z_dimension'] = preview_z_dimension
    table_row['preview_cutoff_min'] = preview_cutoff_min
    table_row['preview_cutoff_max'] = preview_cutoff_max

    if settings == True:
        table_row['settings_status'] = settings_status
        table_row['settings_update_progress'] = settings_update_progress
        table_row['settings_recursive'] = settings_recursive
        table_row['volume_slice_filepattern'] = volume_slice_filepattern
    else:
        table_row['base_path'] = base_path
        table_row['path'] = path
        table_row['name'] = name
        table_row['min_value'] = min_value
        table_row['max_value'] = max_value
        table_row['mean_value'] = mean_value
        table_row['median_value'] = median_value
        table_row['file_md5sum'] = file_md5sum
        table_row['preview_xdmf_filename'] = preview_xdmf_filename
        table_row['preview_data_type'] = preview_data_type

    if update:
        table_row.update()
    else:
        table_row.append()

    logger.debug('added table_row: %s' % str(table_row))

    return table_row


def __remove_image_volumes(
    logger,
    metafile,
    base_path,
    path=None,
    name=None,
    extension=None,
    ):
    """Remove image volumes, based on *path*, *name* and *extension*"""

    status = False
    removed = []

    logger.debug('base_path: %s, path: %s, name: %s, extension: %s'
                 % (base_path, path, name, extension))

    if metafile is not None:
        image_volume_table = __get_image_volume_meta_node(logger,
                metafile)

        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)

        row_list = __get_row_idx_list(logger, image_volume_table,
                condition)

        logger.debug('removing #%s row(s)' % len(row_list))

        status = True
        while len(row_list) > 0:
            row_idx = row_list[0]
            table_row = image_volume_table[row_idx]
            row_base_path = table_row['base_path']
            row_path = table_row['path']
            row_name = table_row['name']
            if __remove_image_volume_preview(logger, metafile,
                    row_base_path, row_path, row_name):
                if row_path != '':
                    removed.append('%s/%s' % (row_base_path.strip('/'),
                                   row_name.strip('/')))
                else:
                    removed.append('%s/%s/%s' % (row_base_path.strip('/'
                                   ), row_path.strip('/'),
                                   row_name.strip('/')))
                image_volume_table = __remove_row(logger, metafile,
                        image_volume_table, row_idx)
                row_list = __get_row_idx_list(logger,
                        image_volume_table, condition)
            else:
                status = False

    logger.debug('status: %s, removed: %s' % (str(status),
                 str(removed)))

    return (status, removed)


def __remove_image_volume_preview(
    logger,
    metafile,
    base_path,
    path,
    name,
    ):
    """Remove image preview volume, data and histogram"""

    result = False

    volume_preview_data_group = __get_image_volume_data_node(logger,
            metafile)
    volume_array_name = __get_data_node_name(logger, path, name)

     # Remove preview data

    if volume_preview_data_group.__contains__(volume_array_name):
        logger.debug('removing volume preview data: %s'
                     % volume_array_name)
        volume_preview_data_group.__getattr__(volume_array_name).remove()
    else:
        logger.debug('missing volume preview data: %s'
                     % volume_array_name)

    result = True

    return result


def __get_image_volume_preview_data(
    logger,
    metafile,
    path,
    filename,
    ):
    """Returns handle to preview volume data table array"""

    result = None

    if metafile is not None:
        data_group = __get_image_volume_data_node(logger, metafile)
        name = __get_data_node_name(logger, path, filename)

        try:
            result = data_group.__getattr__(name)
            logger.debug('type: %s, data_ent: %s, %s, %s'
                         % (type(result), result.dtype, result.shape,
                         result))
        except tables.exceptions.NoSuchNodeError:
            result = None
    return result


def __get_image_volume_preview_histogram_data(
    logger,
    metafile,
    path,
    filename,
    ):
    """Returns handle to preview volume histogram table array"""

    result = None

    if metafile is not None:
        histogram_group = __get_image_volume_histogram_node(logger,
                metafile)
        name = __get_data_node_name(logger, path, filename)

        try:
            result = histogram_group.__getattr__(name)
            logger.debug('type: %s, data_ent: %s, %s, %s'
                         % (type(result), result.dtype, result.shape,
                         result))
        except tables.exceptions.NoSuchNodeError:
            result = None

    return result


def get_preview_image_url(logger, base_url, path, filename):
    """Returns VGrid image url for generated preview image file"""

    return '%s/%s/%s/%s' % (base_url, __image_preview_path.strip('/'),
                        path,
                        filename)


def to_ndarray(logger, tables_array, out=None):
    """Converts table array to ndarray, this issues a copy"""

    logger.debug('type: %s, dir: %s' % (type(tables_array),
                 dir(tables_array)))
    if out is None:
        result = empty(tables_array.shape, tables_array.dtype)
    else:
        result = out

    result[:] = tables_array

    return result


def add_image_file_setting(
    logger,
    base_path,
    extension,
    settings_status,
    settings_update_progress,
    settings_recursive,
    image_type,
    data_type=None,
    offset=0,
    x_dimension=0,
    y_dimension=0,
    preview_image_extension=None,
    preview_x_dimension=0,
    preview_y_dimension=0,
    preview_cutoff_min=0,
    preview_cutoff_max=0,
    overwrite=False,
    ):
    """Add image file setting to metadata"""

    result = False

    metafile = __open_image_settings_file(logger, base_path,
            makedirs=True)

    if metafile is not None:
        settings_table = __get_image_file_settings_node(logger,
                metafile)

        condition = 'extension == b"%s"' % extension
        row_list = __get_row_idx_list(logger, settings_table, condition)

        if not overwrite and len(row_list) > 0 or overwrite \
            and len(row_list) > 1:
            logger.debug('Image settings for files with extension: "%s" allready exists, #settings: %s'
                          % (extension, len(row_list)))
        else:
            if overwrite and len(row_list) == 1:
                rows = settings_table.where(condition)
                update = True
            else:
                rows = [settings_table.row]
                update = False

            result = True
            for row in rows:
                table_row = __add_image_file_ent(
                    logger,
                    row,
                    extension,
                    image_type,
                    settings_status=settings_status,
                    settings_update_progress=settings_update_progress,
                    settings_recursive=settings_recursive,
                    data_type=data_type,
                    offset=offset,
                    x_dimension=x_dimension,
                    y_dimension=y_dimension,
                    preview_image_extension=preview_image_extension,
                    preview_x_dimension=preview_x_dimension,
                    preview_y_dimension=preview_y_dimension,
                    preview_cutoff_min=preview_cutoff_min,
                    preview_cutoff_max=preview_cutoff_max,
                    update=update,
                    settings=True,
                    )
                if table_row is None:
                    result = False

        __close_image_settings_file(logger, metafile)

    return result


def remove_image_file_setting(logger, base_path, extension):
    """Remove image file setting"""

    return remove_image_file_settings(logger, base_path, extension)


def remove_image_file_settings(logger, base_path, extension=None):
    """Remove image file settings"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))
    status = False
    removed = []

    metafile = __open_image_settings_file(logger, base_path)

    if metafile is not None:
        status = True

        settings_table = __get_image_file_settings_node(logger,
                metafile)

        condition = ''
        if extension is not None:
            condition = 'extension == b"%s"' % extension

        row_list = __get_row_idx_list(logger, settings_table, condition)

        logger.debug('row_list: %s' % row_list)
        while status and len(row_list) > 0:
            logger.debug('row_list: %s' % row_list)
            row_idx = row_list[0]

            (status_files, _) = __remove_image_files(logger, metafile,
                    base_path, extension=extension)
            if status_files:
                logger.debug('settings_table.nrows: %s'
                             % settings_table.nrows)
                removed.append(settings_table[row_idx]['extension'])
                settings_table = __remove_row(logger, metafile,
                        settings_table, row_idx)
                row_list = __get_row_idx_list(logger, settings_table,
                        condition)
            else:
                status = False

    __close_image_settings_file(logger, metafile)

    logger.debug('status: %s, removed: %s' % (str(status),
                 str(removed)))

    return (status, removed)


def add_image_file(
    logger,
    base_path,
    path,
    name,
    extension,
    image_type,
    data_type,
    offset,
    x_dimension,
    y_dimension,
    min_value,
    max_value,
    mean_value,
    median_value,
    file_md5sum,
    preview_image_filename,
    preview_image_extension,
    preview_data_type,
    preview_x_dimension,
    preview_y_dimension,
    preview_cutoff_min,
    preview_cutoff_max,
    preview_image_scale,
    overwrite=False,
    ):
    """Add image file entry to meta data"""

    result = False

    logger.debug('x_dimension: %s, y_dimension: %s, data_type: %s'
                 % (x_dimension, y_dimension, data_type))

    metafile = __open_image_settings_file(logger, base_path)

    if metafile is not None:
        image_file_table = __get_image_file_meta_node(logger, metafile)

        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)

        row_list = __get_row_idx_list(logger, image_file_table,
                condition)

        if not overwrite and len(row_list) > 0 or overwrite \
            and len(row_list) > 1:
            logger.debug("'%s' for path: '%s' allready exists, #entries: %s"
                          % (name, base_path, len(row_list)))
        else:
            if overwrite and len(row_list) == 1:
                rows = image_file_table.where(condition)
                update = True
            else:
                rows = [image_file_table.row]
                update = False

            for row in rows:
                __add_image_file_ent(
                    logger,
                    row,
                    extension,
                    image_type,
                    settings_status=None,
                    settings_update_progress=None,
                    settings_recursive=None,
                    data_type=data_type,
                    base_path=base_path,
                    path=path,
                    name=name,
                    offset=offset,
                    x_dimension=x_dimension,
                    y_dimension=y_dimension,
                    min_value=min_value,
                    max_value=max_value,
                    mean_value=mean_value,
                    median_value=median_value,
                    file_md5sum=file_md5sum,
                    preview_image_filename=preview_image_filename,
                    preview_image_extension=preview_image_extension,
                    preview_data_type=preview_data_type,
                    preview_x_dimension=preview_x_dimension,
                    preview_y_dimension=preview_y_dimension,
                    preview_cutoff_min=preview_cutoff_min,
                    preview_cutoff_max=preview_cutoff_max,
                    preview_image_scale=preview_image_scale,
                    update=update,
                    settings=False,
                    )
            result = True
        __close_image_settings_file(logger, metafile)

    return result


def remove_image_files(
    logger,
    base_path,
    path=None,
    name=None,
    extension=None,
    ):
    """Remove image files"""

    logger.debug('base_path: %s, path: %s, name: %s, extension: %s'
                 % (base_path, path, name, extension))

    metafile = __open_image_settings_file(logger, base_path)
    (result, removed) = __remove_image_files(
        logger,
        metafile,
        base_path,
        path,
        name,
        extension,
        )
    __close_image_settings_file(logger, metafile)

    return (result, removed)


def update_image_file_setting(logger, base_path, setting):
    """Update image file setting"""

    return add_image_file_setting(
        logger,
        base_path,
        setting['extension'],
        setting['settings_status'],
        setting['settings_update_progress'],
        setting['settings_recursive'],
        setting['image_type'],
        setting['data_type'],
        setting['offset'],
        setting['x_dimension'],
        setting['y_dimension'],
        setting['preview_image_extension'],
        setting['preview_x_dimension'],
        setting['preview_y_dimension'],
        setting['preview_cutoff_min'],
        setting['preview_cutoff_max'],
        overwrite=True,
        )


def get_image_file_setting(logger, base_path, extension):
    """Get image file setting"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))
    result = None

    settings_result = get_image_file_settings(logger, base_path,
            extension)
    if settings_result is not None:
        if len(settings_result) == 1:
            result = settings_result[0]
        elif len(settings_result) > 1:
            logger.warning('expected result of length 0 or 1, got: %s'
                           % len(result))

    return result


def update_image_file_setting(logger, base_path, setting):
    """Update image file setting"""

    return add_image_file_setting(
        logger,
        base_path,
        setting['extension'],
        setting['settings_status'],
        setting['settings_update_progress'],
        setting['settings_recursive'],
        setting['image_type'],
        setting['data_type'],
        setting['offset'],
        setting['x_dimension'],
        setting['y_dimension'],
        setting['preview_image_extension'],
        setting['preview_x_dimension'],
        setting['preview_y_dimension'],
        setting['preview_cutoff_min'],
        setting['preview_cutoff_max'],
        overwrite=True,
        )


def get_image_file_settings(logger, base_path, extension=None):
    """Get image file settings"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))

    result = None

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        result = []
        image_settings_table = __get_image_file_settings_node(logger,
                metafile)

        condition = ''
        if extension is not None:
            condition = 'extension == b"%s" ' % extension
        row_list = __get_row_idx_list(logger, image_settings_table,
                condition)
        for row_idx in row_list:
            entry = {}
            entry['extension'] = \
                image_settings_table[row_idx]['extension']
            entry['settings_status'] = \
                image_settings_table[row_idx]['settings_status']
            entry['settings_update_progress'] = \
                image_settings_table[row_idx]['settings_update_progress'
                    ]
            entry['settings_recursive'] = \
                image_settings_table[row_idx]['settings_recursive']
            entry['image_type'] = \
                image_settings_table[row_idx]['image_type']
            entry['data_type'] = \
                image_settings_table[row_idx]['data_type']
            entry['offset'] = image_settings_table[row_idx]['offset']
            entry['x_dimension'] = \
                image_settings_table[row_idx]['x_dimension']
            entry['y_dimension'] = \
                image_settings_table[row_idx]['y_dimension']
            entry['preview_image_extension'] = \
                image_settings_table[row_idx]['preview_image_extension']
            entry['preview_x_dimension'] = \
                image_settings_table[row_idx]['preview_x_dimension']
            entry['preview_y_dimension'] = \
                image_settings_table[row_idx]['preview_y_dimension']
            entry['preview_cutoff_min'] = \
                image_settings_table[row_idx]['preview_cutoff_min']
            entry['preview_cutoff_max'] = \
                image_settings_table[row_idx]['preview_cutoff_max']
            result.append(entry)
        __close_image_settings_file(logger, metafile)

    return result


def get_image_file(
    logger,
    base_path,
    path,
    name,
    data_entries=None,
    ):
    """Get image file"""

    result = None

    result_list = get_image_files(
        logger,
        base_path,
        path,
        name,
        extension=None,
        data_entries=data_entries,
        )
    if result_list is not None:
        if len(result_list) == 1:
            result = result_list[0]
        elif len(result_list) > 1:
            logger.warning('expected result of length 0 or 1, got: %s'
                           % len(result))

    return result


def get_image_files(
    logger,
    base_path,
    path=None,
    name=None,
    extension=None,
    data_entries=None,
    ):
    """Get list of image file entries"""

    result = None

    logger.debug("base_path: '%s', path: '%s', name: '%s', extension: '%s'"
                  % (base_path, path, name, extension))

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        image_file_table = __get_image_file_meta_node(logger, metafile)
        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)
        row_list = __get_row_idx_list(logger, image_file_table,
                condition)
        logger.debug('#rows: %s' % len(row_list))
        result = []
        for row_idx in row_list:
            entry = {}
            entry['image_type'] = image_file_table[row_idx]['image_type'
                    ]
            entry['base_path'] = image_file_table[row_idx]['base_path']
            entry['path'] = image_file_table[row_idx]['path']
            entry['name'] = image_file_table[row_idx]['name']
            entry['extension'] = image_file_table[row_idx]['extension']
            entry['data_type'] = image_file_table[row_idx]['data_type']
            entry['offset'] = image_file_table[row_idx]['offset']
            entry['x_dimension'] = \
                image_file_table[row_idx]['x_dimension']
            entry['y_dimension'] = \
                image_file_table[row_idx]['y_dimension']
            entry['min_value'] = image_file_table[row_idx]['min_value']
            entry['max_value'] = image_file_table[row_idx]['max_value']
            entry['mean_value'] = image_file_table[row_idx]['mean_value'
                    ]
            entry['median_value'] = \
                image_file_table[row_idx]['median_value']
            entry['file_md5sum'] = \
                image_file_table[row_idx]['file_md5sum']
            entry['preview_image_filename'] = \
                image_file_table[row_idx]['preview_image_filename']
            entry['preview_image_extension'] = \
                image_file_table[row_idx]['preview_image_extension']
            entry['preview_cutoff_min'] = \
                image_file_table[row_idx]['preview_cutoff_min']
            entry['preview_cutoff_max'] = \
                image_file_table[row_idx]['preview_cutoff_max']
            entry['preview_data_type'] = \
                image_file_table[row_idx]['preview_data_type']
            entry['preview_x_dimension'] = \
                image_file_table[row_idx]['preview_x_dimension']
            entry['preview_y_dimension'] = \
                image_file_table[row_idx]['preview_y_dimension']
            entry['preview_image_scale'] = \
                image_file_table[row_idx]['preview_image_scale']
            entry['preview_data'] = None
            entry['preview_image'] = None
            entry['preview_histogram'] = None
            if data_entries is not None:
                if 'preview_data' in data_entries:
                    entry['preview_data'] = to_ndarray(logger,
                            __get_image_file_preview_data(logger,
                            metafile, entry['path'], entry['name']))
                if 'preview_image' in data_entries:
                    entry['preview_image'] = to_ndarray(logger,
                            __get_image_file_preview_image(logger,
                            metafile, entry['path'], entry['name']))
                if 'preview_histogram' in data_entries:
                    entry['preview_histogram'] = to_ndarray(logger,
                            __get_image_file_preview_histogram_data(logger,
                            metafile, entry['path'], entry['name']))
            result.append(entry)
    __close_image_settings_file(logger, metafile)

    return result


def get_image_file_count(
    logger,
    base_path,
    path=None,
    name=None,
    extension=None,
    ):
    """Returns number of files currently in metadata"""

    result = 0
    metafile = __open_image_settings_file(logger, base_path)
    if metafile:
        image_file_table = __get_image_file_meta_node(logger, metafile)
        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)
        row_list = __get_row_idx_list(logger, image_file_table,
                condition)
        result = len(row_list)

    __close_image_settings_file(logger, metafile)

    return result


def get_image_preview_path(
    logger,
    base_path,
    path,
    makedirs=False,
    ):
    """Returns image preview path, created if non-existent"""

    logger.debug('base_path: %s, path: %s' % (base_path, path))
    result = None

    if __ensure_filepath(logger, base_path) is not None:
        preview_path = os.path.join(__image_preview_path, path)
        full_preview_path = os.path.join(base_path, preview_path)
        if __ensure_filepath(logger, full_preview_path, makedirs) \
            is not None:
            result = preview_path

    return result


def get_image_xdmf_path(
    logger,
    base_path,
    ensure=False,
    makedirs=False,
    ):
    """Returns image xdmf path, created if non-existent"""

    result = None

    image_xdmf_path = os.path.join(base_path, __image_xdmf_path)

    logger.debug('get_image_xdmf_path: image_xdmf_path: %s'
                 % image_xdmf_path)

    if ensure:
        result = __ensure_filepath(logger, image_xdmf_path, makedirs)
    else:
        result = image_xdmf_path

    return result


def get_image_xdmf_filepath(logger, base_path, filename):
    """Returns xdmf filepath"""

    image_xdmf_path = get_image_xdmf_path(logger, base_path)

    logger.debug('image_xdmf_path: %s' % image_xdmf_path)
    return os.path.join(image_xdmf_path, filename)


def add_image_file_preview_data(
    logger,
    base_path,
    path,
    filename,
    data,
    ):
    """Put preview *data* into a table array, created if non-existent"""

    result = False

    logger.debug('base_path: %s, path: %s, filename: %s, data: %s'
                 % (base_path, path, filename, data))

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        data_group = __get_image_file_data_node(logger, metafile)
        image_filepath = os.path.join(path, filename)
        title = 'Image preview data for: %s' % image_filepath
        name = __get_data_node_name(logger, path, filename)

        logger.debug('name: %s' % name)
        logger.debug('title: %s' % title)
        logger.debug('data: %s, %s' % (data.dtype, str(data.shape)))
        try:
            data_ent = data_group.__getattr__(name)
            data_ent[:] = data
        except tables.exceptions.NoSuchNodeError:
            data_ent = metafile['tables'].create_array(data_group,
                    name, obj=data, title=title)

        logger.debug('tables data: %s, %s' % (data_ent.dtype,
                     data_ent.shape))

        result = True

    __close_image_settings_file(logger, metafile)

    return result


def get_image_file_preview_data(
    logger,
    base_path,
    path,
    filename,
    ):
    """Returns ndarray copy of preview file data"""

    metafile = __open_image_settings_file(logger, base_path)
    result = to_ndarray(logger, __get_image_file_preview_data(logger,
                        metafile, path, filename))
    __close_image_settings_file(logger, metafile)

    return result


def add_image_file_preview_image(
    logger,
    base_path,
    path,
    filename,
    data,
    ):
    """Put rescaled and resized *data* into a table array, created if non-existent"""

    result = False

    logger.debug('base_path: %s, path: %s, filename: %s, data: %s'
                 % (base_path, path, filename, data))

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        image_group = __get_image_file_image_node(logger, metafile)
        image_filepath = os.path.join(path, filename)
        title = 'Resized and rescaled image data for: %s' \
            % image_filepath
        name = __get_data_node_name(logger, path, filename)

        logger.debug('imagefileio.py: add_image_file_preview_image -> name: %s'
                      % name)
        logger.debug('imagefileio.py: add_image_file_preview_image -> title: %s'
                      % title)
        logger.debug('imagefileio.py: add_image_file_preview_image -> data: %s, %s'
                      % (data.dtype, str(data.shape)))
        try:
            data_ent = image_group.__getattr__(name)
            data_ent[:] = data
        except tables.exceptions.NoSuchNodeError:
            data_ent = metafile['tables'].create_array(image_group,
                    name, obj=data, title=title)

        logger.debug('tables data: %s, %s' % (data_ent.dtype,
                     data_ent.shape))

        result = True

    __close_image_settings_file(logger, metafile)

    return result


def get_image_file_preview_image(
    logger,
    base_path,
    path,
    filename,
    ):
    """Returns ndarray copy of rescaled and resized image data"""

    metafile = __open_image_settings_file(logger, base_path)
    result = to_ndarray(logger, __get_image_file_preview_image(logger,
                        metafile, path, filename))
    __close_image_settings_file(logger, metafile)

    return result


def add_image_file_preview_histogram(
    logger,
    base_path,
    path,
    filename,
    histogram,
    ):
    """Put *histogram* into a table array, created if non-existent"""

    result = False

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        histogram_group = __get_image_file_histogram_node(logger,
                metafile)
        image_filepath = os.path.join(path, filename)
        title = 'Histogram for resized and rescaled preview data: %s' \
            % image_filepath
        name = __get_data_node_name(logger, path, filename)
        logger.debug('name: %s' % name)
        logger.debug('title: %s' % title)
        logger.debug('histogram: %s, %s' % (histogram.dtype,
                     str(histogram.shape)))
        try:
            histogram_ent = histogram_group.__getattr__(name)
            histogram_ent[:] = histogram
        except tables.exceptions.NoSuchNodeError:
            histogram_ent = metafile['tables'
                    ].create_array(histogram_group, name,
                                   obj=histogram, title=title)

        logger.debug('histogram_ent: %s, %s, %s'
                     % (histogram_ent.dtype, histogram_ent.shape,
                     histogram_ent))

        result = True

    __close_image_settings_file(logger, metafile)

    return result


def get_image_file_preview_histogram(
    logger,
    base_path,
    path,
    filename,
    ):
    """Returns ndarray copy of preview file histogram"""

    metafile = __open_image_settings_file(logger, base_path)
    result = to_ndarray(logger,
                        __get_image_file_preview_histogram_data(logger,
                        metafile, path, filename))
    __close_image_settings_file(logger, metafile)

    return result


def add_image_volume_setting(
    logger,
    base_path,
    extension,
    settings_status,
    settings_update_progress,
    settings_recursive,
    image_type,
    volume_type,
    data_type=None,
    volume_slice_filepattern=None,
    offset=0,
    x_dimension=0,
    y_dimension=0,
    z_dimension=0,
    preview_x_dimension=0,
    preview_y_dimension=0,
    preview_z_dimension=0,
    preview_cutoff_min=0,
    preview_cutoff_max=0,
    overwrite=False,
    ):
    """Add image volume setting to metadata"""

    result = False

    metafile = __open_image_settings_file(logger, base_path,
            makedirs=True)

    if metafile is not None:
        settings_table = __get_image_volume_settings_node(logger,
                metafile)

        condition = 'extension == b"%s"' % extension
        row_list = __get_row_idx_list(logger, settings_table, condition)

        if not overwrite and len(row_list) > 0 or overwrite \
            and len(row_list) > 1:
            logger.debug('Image settings for volumes with extension: "%s" allready exists, #settings: %s'
                          % (extension, len(row_list)))
        else:
            if overwrite and len(row_list) == 1:
                rows = settings_table.where(condition)
                update = True
            else:
                rows = [settings_table.row]
                update = False

            result = True
            for row in rows:
                table_row = __add_image_volume_ent(
                    logger,
                    row,
                    extension,
                    image_type,
                    volume_type,
                    settings_status=settings_status,
                    settings_update_progress=settings_update_progress,
                    settings_recursive=settings_recursive,
                    data_type=data_type,
                    volume_slice_filepattern=volume_slice_filepattern,
                    offset=offset,
                    x_dimension=x_dimension,
                    y_dimension=y_dimension,
                    z_dimension=z_dimension,
                    preview_x_dimension=preview_x_dimension,
                    preview_y_dimension=preview_y_dimension,
                    preview_z_dimension=preview_z_dimension,
                    preview_cutoff_min=preview_cutoff_min,
                    preview_cutoff_max=preview_cutoff_max,
                    update=update,
                    settings=True,
                    )
                if table_row is None:
                    result = False

        __close_image_settings_file(logger, metafile)

    return result


def add_image_volume_preview_data(
    logger,
    base_path,
    path,
    filename,
    data,
    ):
    """Put resized *data* into a table array, created if non-existent"""

    result = False

    logger.debug('base_path: %s, path: %s, filename: %s, data: %s'
                 % (base_path, path, filename, data))

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        data_group = __get_image_volume_data_node(logger, metafile)
        image_filepath = os.path.join(path, filename)
        title = 'Rescaled data for: %s' % image_filepath
        name = __get_data_node_name(logger, path, filename)
        logger.debug('name: %s' % name)
        logger.debug('title: %s' % title)
        logger.debug('data: %s, %s' % (data.dtype, str(data.shape)))
        try:
            data_ent = data_group.__getattr__(name)
            data_ent[:] = data
        except tables.exceptions.NoSuchNodeError:
            data_ent = metafile['tables'].create_array(data_group,
                    name, obj=data, title=title)

        logger.debug('tables data: %s, %s' % (data_ent.dtype,
                     data_ent.shape))

        result = True

    __close_image_settings_file(logger, metafile)

    return result


def add_image_volume(
    logger,
    base_path,
    path,
    name,
    extension,
    image_type,
    volume_type,
    data_type,
    offset,
    x_dimension,
    y_dimension,
    z_dimension,
    min_value,
    max_value,
    mean_value,
    median_value,
    file_md5sum,
    preview_xdmf_filename,
    preview_data_type,
    preview_x_dimension,
    preview_y_dimension,
    preview_z_dimension,
    preview_cutoff_min,
    preview_cutoff_max,
    overwrite=False,
    ):
    """Add image volume entry to meta data"""

    result = False

    logger.debug('x_dimension: %s, y_dimension: %s, z_dimension: %s, data_type: %s'
                  % (x_dimension, y_dimension, z_dimension, data_type))

    metafile = __open_image_settings_file(logger, base_path)

    if metafile is not None:
        image_volume_table = __get_image_volume_meta_node(logger,
                metafile)
        condition = 'name == b"%s"' % name
        row_list = __get_row_idx_list(logger, image_volume_table,
                condition)

        if not overwrite and len(row_list) > 0 or overwrite \
            and len(row_list) > 1:
            logger.debug("'%s' for path: '%s' allready exists, #entries: %s"
                          % (name, base_path, len(row_list)))
        else:
            if overwrite and len(row_list) == 1:
                rows = image_volume_table.where(condition)
                update = True
            else:
                rows = [image_volume_table.row]
                update = False

            for row in rows:
                __add_image_volume_ent(
                    logger,
                    row,
                    extension,
                    image_type,
                    volume_type,
                    settings_status=None,
                    settings_update_progress=None,
                    settings_recursive=None,
                    data_type=data_type,
                    base_path=base_path,
                    path=path,
                    name=name,
                    offset=offset,
                    x_dimension=x_dimension,
                    y_dimension=y_dimension,
                    z_dimension=z_dimension,
                    min_value=min_value,
                    max_value=max_value,
                    mean_value=mean_value,
                    median_value=median_value,
                    file_md5sum=file_md5sum,
                    preview_xdmf_filename=preview_xdmf_filename,
                    preview_data_type=preview_data_type,
                    preview_x_dimension=preview_x_dimension,
                    preview_y_dimension=preview_y_dimension,
                    preview_z_dimension=preview_z_dimension,
                    preview_cutoff_min=preview_cutoff_min,
                    preview_cutoff_max=preview_cutoff_max,
                    update=update,
                    settings=False,
                    )
            result = True
        __close_image_settings_file(logger, metafile)

    return result


def update_image_volume_setting(logger, base_path, setting):
    """Update image volume setting"""

    return add_image_volume_setting(
        logger,
        base_path,
        setting['extension'],
        setting['settings_status'],
        setting['settings_update_progress'],
        setting['settings_recursive'],
        setting['image_type'],
        setting['volume_type'],
        setting['data_type'],
        setting['volume_slice_filepattern'],
        setting['offset'],
        setting['x_dimension'],
        setting['y_dimension'],
        setting['z_dimension'],
        setting['preview_x_dimension'],
        setting['preview_y_dimension'],
        setting['preview_z_dimension'],
        setting['preview_cutoff_min'],
        setting['preview_cutoff_max'],
        overwrite=True,
        )


def get_image_volume_setting(logger, base_path, extension):
    """Get image volume setting"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))
    result = None

    settings_result = get_image_volume_settings(logger, base_path,
            extension)
    if settings_result is not None:
        if len(settings_result) == 1:
            result = settings_result[0]
        elif len(settings_result) > 1:
            logger.warning('expected result of length 0 or 1, got: %s'
                           % len(result))

    return result


def get_image_volume_settings(logger, base_path, extension=None):
    """Get image volume settings"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))

    result = None

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        result = []
        image_settings_table = __get_image_volume_settings_node(logger,
                metafile)

        condition = ''
        if extension is not None:
            condition = 'extension == b"%s" ' % extension
        row_list = __get_row_idx_list(logger, image_settings_table,
                condition)
        for row_idx in row_list:
            entry = {}
            entry['extension'] = \
                image_settings_table[row_idx]['extension']
            entry['settings_status'] = \
                image_settings_table[row_idx]['settings_status']
            entry['settings_update_progress'] = \
                image_settings_table[row_idx]['settings_update_progress'
                    ]
            entry['settings_recursive'] = \
                image_settings_table[row_idx]['settings_recursive']
            entry['image_type'] = \
                image_settings_table[row_idx]['image_type']
            entry['volume_type'] = \
                image_settings_table[row_idx]['volume_type']
            entry['data_type'] = \
                image_settings_table[row_idx]['data_type']
            entry['volume_slice_filepattern'] = \
                image_settings_table[row_idx]['volume_slice_filepattern'
                    ]
            entry['offset'] = image_settings_table[row_idx]['offset']
            entry['x_dimension'] = \
                image_settings_table[row_idx]['x_dimension']
            entry['y_dimension'] = \
                image_settings_table[row_idx]['y_dimension']
            entry['z_dimension'] = \
                image_settings_table[row_idx]['z_dimension']
            entry['preview_x_dimension'] = \
                image_settings_table[row_idx]['preview_x_dimension']
            entry['preview_y_dimension'] = \
                image_settings_table[row_idx]['preview_y_dimension']
            entry['preview_z_dimension'] = \
                image_settings_table[row_idx]['preview_z_dimension']
            entry['preview_cutoff_min'] = \
                image_settings_table[row_idx]['preview_cutoff_min']
            entry['preview_cutoff_max'] = \
                image_settings_table[row_idx]['preview_cutoff_max']
            result.append(entry)
        __close_image_settings_file(logger, metafile)

    return result


def get_image_volume(
    logger,
    base_path,
    path,
    name,
    data_entries=None,
    ):
    """Get image volume"""

    result = None

    result_list = get_image_volumes(
        logger,
        base_path,
        path,
        name,
        extension=None,
        data_entries=data_entries,
        )
    if result_list is not None:
        if len(result_list) == 1:
            result = result_list[0]
        elif len(result_list) > 1:
            logger.warning('expected result of length 0 or 1, got: %s'
                           % len(result))
    return result


def get_image_volumes(
    logger,
    base_path,
    path=None,
    name=None,
    extension=None,
    data_entries=None,
    ):
    """Get list of image volume entries"""

    result = None

    logger.debug("base_path: '%s', path: '%s', name: '%s', extension: '%s'"
                  % (base_path, path, name, extension))

    metafile = __open_image_settings_file(logger, base_path)
    if metafile is not None:
        image_volume_table = __get_image_volume_meta_node(logger,
                metafile)
        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)
        row_list = __get_row_idx_list(logger, image_volume_table,
                condition)
        logger.debug('#rows: %s' % len(row_list))
        result = []
        for row_idx in row_list:
            entry = {}
            entry['image_type'] = \
                image_volume_table[row_idx]['image_type']
            entry['volume_type'] = \
                image_volume_table[row_idx]['volume_type']
            entry['base_path'] = image_volume_table[row_idx]['base_path'
                    ]
            entry['path'] = image_volume_table[row_idx]['path']
            entry['name'] = image_volume_table[row_idx]['name']
            entry['extension'] = image_volume_table[row_idx]['extension'
                    ]
            entry['data_type'] = image_volume_table[row_idx]['data_type'
                    ]
            entry['offset'] = image_volume_table[row_idx]['offset']
            entry['x_dimension'] = \
                image_volume_table[row_idx]['x_dimension']
            entry['y_dimension'] = \
                image_volume_table[row_idx]['y_dimension']
            entry['z_dimension'] = \
                image_volume_table[row_idx]['z_dimension']
            entry['min_value'] = image_volume_table[row_idx]['min_value'
                    ]
            entry['max_value'] = image_volume_table[row_idx]['max_value'
                    ]
            entry['mean_value'] = \
                image_volume_table[row_idx]['mean_value']
            entry['median_value'] = \
                image_volume_table[row_idx]['median_value']
            entry['file_md5sum'] = \
                image_volume_table[row_idx]['file_md5sum']
            entry['preview_xdmf_filename'] = \
                image_volume_table[row_idx]['preview_xdmf_filename']
            entry['preview_data_type'] = \
                image_volume_table[row_idx]['preview_data_type']
            entry['preview_x_dimension'] = \
                image_volume_table[row_idx]['preview_x_dimension']
            entry['preview_y_dimension'] = \
                image_volume_table[row_idx]['preview_y_dimension']
            entry['preview_z_dimension'] = \
                image_volume_table[row_idx]['preview_z_dimension']
            entry['preview_cutoff_min'] = \
                image_volume_table[row_idx]['preview_cutoff_min']
            entry['preview_cutoff_max'] = \
                image_volume_table[row_idx]['preview_cutoff_max']
            entry['preview_data'] = None
            entry['preview_histogram'] = None
            if data_entries is not None:
                if 'preview_data' in data_entries:
                    entry['preview_data'] = to_ndarray(logger,
                            __get_image_volume_preview_data(logger,
                            metafile, entry['path'], entry['name']))
                if 'preview_histogram' in data_entries:
                    logger.info('Volume histogram _NOT_ implemented yet'
                                )
                    entry['preview_histogram'] = None

            result.append(entry)
    __close_image_settings_file(logger, metafile)

    return result


def get_image_volume_count(
    logger,
    base_path,
    path=None,
    name=None,
    extension=None,
    ):
    """Returns number of volumes currently in metadata"""

    result = 0
    metafile = __open_image_settings_file(logger, base_path)
    if metafile:
        image_volume_table = __get_image_volume_meta_node(logger,
                metafile)

        condition = ''
        if path is not None:
            condition = '%s & (path == b"%s")' % (condition, path)
        if name is not None:
            condition = '%s & (name == b"%s")' % (condition, name)
        if extension is not None:
            condition = '%s & (extension == b"%s")' % (condition,
                    extension)
        condition = condition.replace(' & ', '', 1)
        row_list = __get_row_idx_list(logger, image_volume_table,
                condition)
        result = len(row_list)

    __close_image_settings_file(logger, metafile)

    return result


def remove_image_file_setting(logger, base_path, extension):
    """Remove image volume setting"""

    return remove_image_volume_settings(logger, base_path, extension)


def remove_image_volume_settings(logger, base_path, extension=None):
    """Remove image file settings"""

    logger.debug('base_path: %s, extension: %s' % (base_path,
                 extension))

    status = False
    removed = []

    metafile = __open_image_settings_file(logger, base_path)

    if metafile is not None:
        status = True

        settings_table = __get_image_volume_settings_node(logger,
                metafile)

        condition = ''
        if extension is not None:
            condition = 'extension == b"%s"' % extension

        row_list = __get_row_idx_list(logger, settings_table, condition)

        logger.debug('row_list: %s' % row_list)
        while status and len(row_list) > 0:
            logger.debug('row_list: %s' % row_list)
            row_idx = row_list[0]

            (status_volumes, _) = __remove_image_volumes(logger,
                    metafile, base_path, extension=extension)
            if status_volumes:
                logger.debug('settings_table.nrows: %s'
                             % settings_table.nrows)
                removed.append(settings_table[row_idx]['extension'])
                settings_table = __remove_row(logger, metafile,
                        settings_table, row_idx)
                row_list = __get_row_idx_list(logger, settings_table,
                        condition)
            else:
                status = False

    __close_image_settings_file(logger, metafile)

    logger.debug('status: %s, removed: %s' % (str(status),
                 str(removed)))

    return (status, removed)


