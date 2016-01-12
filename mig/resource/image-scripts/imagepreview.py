#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# imagepreview - Generating MiG image preview and meta data
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

"""Image preview and meta data generator helper functions"""

import os
import cv2
import traceback

from shared.imagemetaio import allowed_data_types, add_image_file, \
    get_image_file_setting, get_image_file_settings, \
    get_image_preview_path, add_image_file_preview_data, \
    add_image_file_preview_histogram, get_image_files, \
    remove_image_files, update_image_file_setting, \
    allowed_settings_status

from numpy import fromfile, uint8, uint32, cast, mean, zeros, floor, \
    mean, median
from libtiff import TIFF
import hashlib


def fill_md5sum(logger, image, blocksize=65536):
    """Generate md5sum"""

    result = False

    filepath = os.path.join(os.path.join(image['base_path'],
                            image['path']), image['filename'])

    try:
        hash = hashlib.md5()
        fh = open(filepath, 'rb')
        for block in iter(lambda : fh.read(blocksize), ''):
            hash.update(block)
        fh.close()
        image['md5sum'] = hash.hexdigest()
        result = True
    except Exception, ex:
        logger.error(traceback.format_exc())
        result = False
    return result


def fill_data(logger, image):
    """Load data"""

    result = False

    filepath = os.path.join(os.path.join(image['base_path'],
                            image['path']), image['filename'])
    logger.debug('imagepreview.py: fill_data -> filepath: %s'
                 % filepath)
    image_type = image['setting']['image_type']
    if image_type == 'raw':
        offset = image['setting']['offset']
        x_dimension = image['setting']['x_dimension']
        y_dimension = image['setting']['y_dimension']
        data_type = allowed_data_types[image['setting']['data_type']]

        try:
            fh = open(filepath, 'rb')
            fh.seek(offset)
            image['data'] = fromfile(fh, dtype=data_type)
            fh.close()
            image['data'].shape = (y_dimension, x_dimension)
            result = True
        except Exception, ex:
            logger.error(traceback.format_exc())
            result = False
    elif image_type == 'tiff':
        try:
            tif = TIFF.open(filepath, mode='r')
            data = tif.read_image()
            tif.close()

            image['data'] = data
            image['setting']['offset'] = 0
            image['setting']['x_dimension'] = data.shape[1]
            image['setting']['y_dimension'] = data.shape[0]
            image['setting']['data_type'] = data.dtype.name
            logger.debug('imagepreview.py: fill_data -> x_dimension: %s, y_dimension: %s, data_type: %s'
                         , image['setting']['x_dimension'],
                         image['setting']['y_dimension'],
                         image['setting']['data_type'])
            result = True
        except Exception, ex:
            logger.error(traceback.format_exc())
            result = False
    else:
        logger.error('image_type: %s _NOT_ supported yet' % image_type)

    return result


def fill_image_stats(logger, image):
    """Generate image statistics"""

    result = True

    image['stats'] = {}
    image['stats']['mean'] = mean(image['data'])
    image['stats']['median'] = median(image['data'])
    image['stats']['min_value'] = image['data'].min()
    image['stats']['max_value'] = image['data'].max()

    return result


def fill_preview(logger, image):
    """Generate image preview"""

    result = False

    data = image['data']
    x_dimension = image['setting']['preview_x_dimension']
    y_dimension = image['setting']['preview_y_dimension']
    image['preview'] = {}
    image['setting']['min_value'] = data.min()
    image['setting']['max_value'] = data.max()

    # Cutoff data

    if image['setting']['preview_cutoff_min'] == 0 and image['setting'
            ]['preview_cutoff_max'] == 0:

        cmin = image['setting']['min_value']
        cmax = image['setting']['max_value']
    else:
        cmin = image['setting']['preview_cutoff_min']
        cmax = image['setting']['preview_cutoff_max']

    # Set image threshold to cutoff min and cutoff max

    data[data<cmin] = cmin
    data[data>cmax] = cmax

    # TODO: Check if the NOTE below is still valid now that we 
    #       set the image threshold to cmin and cmax
    # NOTE: Using reszied data for rescaling doesn't fare well
    # cmin and cmax for rescaled data doesn't
    # match cmin and cmax of original data, and
    # thereby we get inconsinstency between user settings
    # and the settings used for rescaling.
    # Use original data so far for rescaling.

    # Rescale using cuttoff min and max and convert to uint8 data

    (low, high) = (0, 255)
    scale = high * 1. / (cmax - cmin or 1)

    bytedata = ((data * 1. - cmin) * scale + 0.4999).astype(uint8)
    bytedata += cast[uint8](low)

    # Resize data

    dim_scale = max(data.shape[0] / y_dimension, data.shape[1]
                    / x_dimension)
    new_y_dimension = int(floor(data.shape[0] / dim_scale))
    new_x_dimension = int(floor(data.shape[1] / dim_scale))

    logger.debug('Resizing to: %s, %s' % (new_x_dimension,
                 new_y_dimension))

    rescaled_data = zeros((new_y_dimension, new_x_dimension),
                          dtype=uint8)
    rescaled_data[:] = cv2.resize(bytedata, (new_y_dimension,
                                  new_x_dimension))
    logger.debug('Rescaled and resized data -> dtype: %s, shape: %s'
                 % (rescaled_data.dtype, rescaled_data.shape))

    image['preview']['cutoff_min'] = cmin
    image['preview']['cutoff_max'] = cmax
    image['preview']['scale'] = scale
    image['preview']['rescaled_data'] = rescaled_data
    image['preview']['x_dimension'] = new_x_dimension
    image['preview']['y_dimension'] = new_y_dimension

    result = True

    return result


def fill_preview_histogram(logger, image):
    """Generate histogram for preview data"""

    result = False
    histogram_bins = 256

    preview_data = image['preview'].get('rescaled_data', None)

    if preview_data is not None:

        # Calculate histogram

        hist_data = cv2.calcHist([preview_data], [0], None,
                                 [histogram_bins], [0,
                                 histogram_bins]).astype(uint32)
        image['preview']['histogram'] = hist_data
        result = True

    return result


def write_preview_image(logger, image):
    """Write preview image file to disk"""

    result = False

    base_path = image['base_path']
    path = image['path']
    filename = image['filename']

    preview_extension = image['setting']['preview_image_extension']
    preview_image_filename = '%s.image.%s' % (filename,
            preview_extension)

    image['preview']['filepath'] = os.path.join(path,
            preview_image_filename)
    image['preview']['extension'] = preview_extension

    preview_path = get_image_preview_path(logger, base_path, path,
            makedirs=True)

    write_preview_image_filepath = os.path.join(base_path,
            os.path.join(preview_path, preview_image_filename))
    logger.debug('Writing preview image: %s'
                 % write_preview_image_filepath)

    if cv2.imwrite(write_preview_image_filepath, image['preview'
                   ]['rescaled_data']):
        result = True

    return result


def add_image_meta_data(logger, image):
    """Add collected meta data to tables file"""

    result = add_image_file(
        logger,
        image['base_path'],
        image['path'],
        image['filename'],
        image['setting']['extension'],
        image['setting']['image_type'],
        image['setting']['data_type'],
        image['setting']['offset'],
        image['setting']['x_dimension'],
        image['setting']['y_dimension'],
        image['stats']['min_value'],
        image['stats']['max_value'],
        image['stats']['mean'],
        image['stats']['median'],
        image['md5sum'],
        image['preview']['filepath'],
        image['preview']['extension'],
        image['setting']['data_type'],
        image['preview']['x_dimension'],
        image['preview']['y_dimension'],
        image['preview']['cutoff_min'],
        image['preview']['cutoff_max'],
        image['preview']['scale'],
        overwrite=True,
        )

    return result


def add_preview_data(logger, image):
    """Add preview data to tables file"""

    result = add_image_file_preview_data(logger, image['base_path'],
            image['path'], image['filename'], image['preview'
            ]['rescaled_data'])
    return result


def add_preview_histogram(logger, image):
    """Add histogram data to tables file"""

    result = add_image_file_preview_histogram(logger, image['base_path'
            ], image['path'], image['filename'], image['preview'
            ]['histogram'])
    return result


def cleanup_previews(logger, base_path):
    """Remove previews for removed files"""

    logger.debug('base_path: %s' % base_path)

    result = True
    image_file_settings = get_image_file_settings(logger, base_path)
    image_file_entries = get_image_files(logger, base_path)

    if image_file_entries is not None:
        for entry in image_file_entries:
            status = True
            path = entry['path']
            name = entry['name']
            extension = entry['extension']

            logger.debug('checking => path: %s, name: %s, extension: %s'
                          % (path, name, extension))

            image_settings_index_list = [index for (index, value) in
                    enumerate(image_file_settings) if value['extension'
                    ] == extension]
            if len(image_settings_index_list) == 0:
                logger.debug('extension: %s _NOT_ found in settings <= CLEANUP'
                              % extension)

                status = remove_image_files(logger, base_path,
                        extension=extension)
            elif len(image_settings_index_list) == 1:

                image_settings_index = image_settings_index_list[0]
                image_setting = \
                    image_file_settings[image_settings_index]

                logger.debug('extension: %s found in settings'
                             % extension)

                settings_recursive = image_setting['settings_recursive']

                logger.debug('settings_recursive: %s found in settings'
                             % settings_recursive)

                if not settings_recursive and path != '':
                    logger.debug('extension: %s, path: %s, settings_recursive: %s <= CLEANUP'
                                  % (extension, path,
                                 settings_recursive))
                    status = remove_image_files(logger, base_path,
                            path=path, name=name, extension=extension)
                else:
                    filepath = os.path.join(base_path,
                            os.path.join(path, name))
                    if not os.path.isfile(filepath):
                        logger.debug('missing file: %s <= Removing entry from tables'
                                 % filepath)
                        status = remove_image_files(logger, base_path,
                                path=path, name=name,
                                extension=extension)
                    else:
                        logger.debug('file exists: %s <= OK => _NO_ CLEANUP'
                                 % filepath)
            else:
                logger.error('Multiple settings #%s found for extension: %s'
                              % (len(image_settings_index_list),
                             extension))
                status = False

            if not status:
                result = False
    else:

        logger.error('Failed getting image file entries for base_path: %s'
                      % base_path)

    return result


def update_preview(logger, base_path, filepath):
    """Update preview for image *filepath*"""

    filepath_list = filepath.split(os.sep)
    path = os.sep.join(filepath_list[0:-1])
    filename = filepath_list[-1]
    extension = filename.split('.')[-1]

    logger.debug("base_path: '%s', path: '%s', filename: '%s', extension: '%s'"
                  % (base_path, path, filename, extension))

    result = False

    image = {}
    image['base_path'] = base_path
    image['path'] = path
    image['filename'] = filename
    image['setting'] = get_image_file_setting(logger, base_path,
            extension)

    if image['setting'] is not None:
        if fill_data(logger, image) and fill_image_stats(logger, image) \
            and fill_md5sum(logger, image) and fill_preview(logger,
                image) and write_preview_image(logger, image) \
            and add_image_meta_data(logger, image) \
            and add_preview_data(logger, image) \
            and fill_preview_histogram(logger, image) \
            and add_preview_histogram(logger, image):
            result = True
        else:
            logger.info('Skipping update for: %s, %s' % (base_path,
                        filepath))

    logger.debug('result: %s' % str(result))

    return result


def update_previews(logger, base_path, extension):
    """Update image previews for *extension* in *base_path*"""

    logger.debug("base_path: '%s', extension: '%s'" % (base_path,
                 extension))
    image_setting = get_image_file_setting(logger, base_path, extension)
    logger.debug('image_setting: %s' % image_setting)

    result = True
    status_pending = allowed_settings_status['pending']
    status_updating = allowed_settings_status['updating']
    status_failed = allowed_settings_status['failed']
    status_ready = allowed_settings_status['ready']

    if image_setting is not None:
        settings_status = image_setting['settings_status']
        if settings_status == status_pending:
            logger.debug('settings recursive: %s'
                         % image_setting['settings_recursive'])
            image_setting['settings_status'] = status_updating
            logger.debug('settings status: %s'
                         % image_setting['settings_status'])

            # Count files to process and set status / update progress

            processed_filecount = 0
            total_filecount = 0
            if image_setting['settings_recursive']:
                for (root, _, files) in os.walk(base_path):
                    for name in files:
                        if not name.startswith('.') \
                            and name.endswith('.%s' % extension):
                            total_filecount += 1
            else:
                for name in os.listdir(base_path):
                    if not name.startswith('.') and name.endswith('.%s'
                            % extension):
                        total_filecount += 1

            image_setting['settings_update_progress'] = '%s/%s' \
                % (processed_filecount, total_filecount)
            logger.debug('settings_status: %s'
                         % image_setting['settings_status'])
            logger.debug('settings_update_progress: %s'
                         % image_setting['settings_update_progress'])
            update_image_file_setting(logger, base_path, image_setting)

            # Process image files

            if image_setting['settings_recursive']:
                for (root, _, files) in os.walk(base_path):
                    for name in files:
                        if not name.startswith('.') \
                            and name.endswith('.%s' % extension):
                            path = root.replace(base_path, '',
                                    1).strip('/')
                            filepath = os.path.join(path, name)
                            logger.debug('check entry -> path: %s, filepath: %s'
                                     % (path, filepath))
                            if update_preview(logger, base_path,
                                    filepath):
                                processed_filecount += 1

                                image_setting['settings_update_progress'
                                        ] = '%s/%s' \
                                    % (processed_filecount,
                                        total_filecount)
                                logger.debug('settings_update_progress: %s'

                                        % image_setting['settings_update_progress'
                                        ])
                                update_image_file_setting(logger,
                                        base_path, image_setting)
                            else:
                                result = False
            else:
                for name in os.listdir(base_path):
                    logger.debug('check entry: %s' % name)
                    if not name.startswith('.') and name.endswith('.%s'
                            % extension):
                        filepath = os.path.join(base_path, name)
                        if os.path.isfile(filepath):
                            if update_preview(logger, base_path, name):
                                processed_filecount += 1

                                image_setting['settings_update_progress'
                                        ] = '%s/%s' \
                                    % (processed_filecount,
                                        total_filecount)
                                logger.debug('settings_update_progress: %s'

                                        % image_setting['settings_update_progress'
                                        ])
                                update_image_file_setting(logger,
                                        base_path, image_setting)
                            else:
                                result = False

            # Set final update status and progress

            image_setting['settings_update_progress'] = None
            if result:
                image_setting['settings_status'] = status_ready
            else:
                image_setting['settings_status'] = status_failed
                image_setting['settings_update_progress'] = None
            logger.debug('status: %s' % image_setting['settings_status'
                         ])
            update_image_file_setting(logger, base_path, image_setting)
        else:
            logger.info("Skipping update for: %s, %s, expected status: 'Pending', found '%s'"
                         % (base_path, extension, settings_status))
    else:
        logger.info('Skipping update for: %s, %s -> No image settings found'
                     % (base_path, extension))

    return result


