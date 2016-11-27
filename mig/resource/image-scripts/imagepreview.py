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
import re
import cv2
import traceback

from shared.imagemetaio import __tables_image_volumes_preview_data_group, \
    __settings_file, __get_data_node_name, get_image_xdmf_path, \
    allowed_data_types, allowed_xdmf_data_types, \
    allowed_xdmf_precisions, add_image_file, get_image_file_setting, \
    get_image_file_settings, get_image_preview_path, \
    add_image_file_preview_data, add_image_file_preview_image, \
    add_image_file_preview_histogram, get_image_files, \
    remove_image_files, update_image_file_setting, \
    get_image_file_count, get_image_files, get_image_volume_setting, \
    get_image_file_preview_data, add_image_volume_preview_data, \
    allowed_settings_status, add_image_volume, \
    update_image_volume_setting

from numpy import zeros, empty, fromfile, int8, uint8, int16, uint16, \
    int32, uint32, int64, uint64, float64, cast, rint, mean, floor, \
    median
from libtiff import TIFF
import hashlib


def __init_meta(
    logger,
    base_path,
    path,
    filename=None,
    ):
    """Generate dict with path and file information"""

    extension = None
    if filename is not None:
        extension = filename.split('.')[-1]

    logger.debug("base_path: '%s', path: '%s', filename: '%s', extension: '%s'"
                  % (base_path, path, str(filename), str(extension)))

    result = {}
    result['base_path'] = base_path
    result['path'] = path
    result['filename'] = filename
    result['extension'] = extension
    result['2D'] = {}
    result['2D']['stats'] = {}
    result['3D'] = {}
    result['3D']['stats'] = {}

    return result


def fill_image_md5sum(logger, meta, blocksize=65536):
    """Generate md5sum"""

    result = False
    image = meta['2D']

    filepath = os.path.join(os.path.join(meta['base_path'], meta['path'
                            ]), meta['filename'])
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


def fill_image_data(logger, meta):
    """Load 2D image data"""

    result = False

    image = meta['2D']
    settings = image['settings']
    filepath = os.path.join(os.path.join(meta['base_path'], meta['path'
                            ]), meta['filename'])
    logger.debug('filepath: %s' % filepath)

    if settings['image_type'] == 'raw':
        offset = settings['offset']
        x_dimension = settings['x_dimension']
        y_dimension = settings['y_dimension']
        data_type = allowed_data_types[settings['data_type']]

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
    elif settings['image_type'] == 'tiff':
        try:
            tif = TIFF.open(filepath, mode='r')
            data = tif.read_image()
            tif.close()

            image['data'] = data
            settings['offset'] = 0
            settings['x_dimension'] = data.shape[1]
            settings['y_dimension'] = data.shape[0]
            settings['data_type'] = data.dtype.name
            logger.debug('x_dimension: %s, y_dimension: %s, data_type: %s'
                         , settings['x_dimension'],
                         settings['y_dimension'], settings['data_type'])
            result = True
        except Exception, ex:
            logger.error(traceback.format_exc())
            result = False
    else:
        logger.error('image_type: %s _NOT_ supported yet'
                     % settings['image_type'])

    return result


def fill_image_stats(logger, meta):
    """Generate image statistics"""

    result = True
    image = meta['2D']

    image['stats']['mean'] = mean(image['data'])
    image['stats']['median'] = median(image['data'])
    image['stats']['min_value'] = image['data'].min()
    image['stats']['max_value'] = image['data'].max()

    return result


def fill_image_preview(logger, meta):
    """Generate image preview"""

    result = False

    image = meta['2D']
    data = image['data']
    settings = image['settings']
    x_dimension = settings['preview_x_dimension']
    y_dimension = settings['preview_y_dimension']
    settings['min_value'] = data.min()
    settings['max_value'] = data.max()

    # Cutoff data

    if settings['preview_cutoff_min'] == 0 \
        and settings['preview_cutoff_max'] == 0:

        cmin = settings['min_value']
        cmax = settings['max_value']
    else:
        cmin = settings['preview_cutoff_min']
        cmax = settings['preview_cutoff_max']

    # NOTE: Using reszied data for rescaling doesn't fare well
    # cmin and cmax for rescaled data doesn't
    # match cmin and cmax of original data, and
    # thereby we get inconsinstency between user settings
    # and the settings used for rescaling.
    # Use original data so far for rescaling.
    #
    # It might work to cut off values in original data,
    # then resize + rescale

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

    logger.debug('Resizing to: %s, %s' % (new_y_dimension,
                 new_x_dimension))

    rescaled_data = zeros((new_y_dimension, new_x_dimension),
                          dtype=uint8)
    rescaled_data[:] = cv2.resize(bytedata, (new_x_dimension,
                                  new_y_dimension))
    logger.debug('Rescaled and resized data -> dtype: %s, shape: %s'
                 % (rescaled_data.dtype, rescaled_data.shape))

    image['preview'] = preview = {}
    preview['cutoff_min'] = cmin
    preview['cutoff_max'] = cmax
    preview['scale'] = scale
    preview['rescaled_data'] = rescaled_data
    logger.debug('data.shape: %s' % str(data.shape))
    logger.debug('data.dtype: %s' % str(data.dtype))

    # cv2.resize can't handle (u)ints of more than 16 bit

    if data.dtype == int32 or data.dtype == uint32 or data.dtype \
        == int64 or data.dtype == uint64:
        preview['resized_data'] = zeros((new_y_dimension,
                new_x_dimension), dtype=data.dtype)
        resized_data = cv2.resize(data.astype(float64),
                                  (new_x_dimension, new_y_dimension))
        rint(resized_data, out=preview['resized_data'])
    else:
        preview['resized_data'] = cv2.resize(data, (new_x_dimension,
                new_y_dimension))

    preview['x_dimension'] = new_x_dimension
    preview['y_dimension'] = new_y_dimension

    result = True

    return result


def fill_image_preview_histogram(logger, meta):
    """Generate histogram for preview data"""

    result = False
    histogram_bins = 256

    preview = meta['2D']['preview']
    preview_data = preview.get('rescaled_data', None)

    if preview_data is not None:

        # Calculate histogram

        hist_data = cv2.calcHist([preview_data], [0], None,
                                 [histogram_bins], [0,
                                 histogram_bins]).astype(uint32)
        preview['histogram'] = hist_data
        result = True

    return result


def write_preview_image(logger, meta):
    """Write preview image file to disk"""

    result = False

    base_path = meta['base_path']
    path = meta['path']
    filename = meta['filename']
    settings = meta['2D']['settings']
    preview = meta['2D']['preview']
    preview_extension = settings['preview_image_extension']
    preview_image_filename = '%s.image.%s' % (filename,
            preview_extension)

    preview['image_filename'] = preview_image_filename
    preview['extension'] = preview_extension

    preview_path = get_image_preview_path(logger, base_path, path,
            makedirs=True)

    write_preview_image_filepath = os.path.join(base_path,
            os.path.join(preview_path, preview_image_filename))
    logger.debug('Writing preview image: %s'
                 % write_preview_image_filepath)

    if cv2.imwrite(write_preview_image_filepath, preview['rescaled_data'
                   ]):
        result = True

    return result


def add_image_meta_data(logger, meta):
    """Add collected meta data to tables file"""

    image = meta['2D']
    settings = image['settings']

    result = add_image_file(
        logger,
        meta['base_path'],
        meta['path'],
        meta['filename'],
        settings['extension'],
        settings['image_type'],
        settings['data_type'],
        settings['offset'],
        settings['x_dimension'],
        settings['y_dimension'],
        image['stats']['min_value'],
        image['stats']['max_value'],
        image['stats']['mean'],
        image['stats']['median'],
        image['md5sum'],
        image['preview']['image_filename'],
        image['preview']['extension'],
        settings['data_type'],
        image['preview']['x_dimension'],
        image['preview']['y_dimension'],
        image['preview']['cutoff_min'],
        image['preview']['cutoff_max'],
        image['preview']['scale'],
        overwrite=True,
        )

    return result


def add_image_preview_data(logger, meta):
    """Add resized preview data to tables file"""

    image = meta['2D']
    result = add_image_file_preview_data(logger, meta['base_path'],
            meta['path'], meta['filename'], image['preview'
            ]['resized_data'])
    return result


def add_image_preview_image(logger, meta):
    """Add resized and rescaled preview data to tables file"""

    image = meta['2D']
    result = add_image_file_preview_image(logger, meta['base_path'],
            meta['path'], meta['filename'], image['preview'
            ]['rescaled_data'])
    return result


def add_image_preview_histogram(logger, meta):
    """Add histogram data to tables file"""

    image = meta['2D']
    result = add_image_file_preview_histogram(logger, meta['base_path'
            ], meta['path'], meta['filename'], image['preview'
            ]['histogram'])
    return result


def fill_volume_preview_meta(logger, meta):
    """Generate volume preview metadata"""

    result = True

    image = meta['2D']
    volume = meta['3D']
    volume['preview'] = preview = {}
    settings = volume['settings']
    x_dimension = settings['preview_x_dimension']
    y_dimension = settings['preview_y_dimension']
    z_dimension = settings['preview_y_dimension']
    preview['data_type'] = settings['data_type']
    preview['cutoff_min'] = 0
    preview['cutoff_max'] = 0
    preview['x_dimension'] = settings['preview_x_dimension']
    preview['y_dimension'] = settings['preview_y_dimension']
    preview['z_dimension'] = settings['preview_z_dimension']

    return result


def fill_volume_stats(logger, meta):
    """Generate image statistics"""

    # TODO: Implement for raw volumes

    result = True
    volume = meta['3D']

    volume['stats']['mean'] = 0
    volume['stats']['median'] = 0
    volume['stats']['min_value'] = 0
    volume['stats']['max_value'] = 0

    return result


def fill_volume_md5sum(logger, meta, blocksize=65536):
    """Generate md5sum"""

    # TODO: Implement for raw volumes

    result = True
    volume = meta['3D']
    volume['md5sum'] = 0

    return result


def add_volume_meta_data(logger, meta):
    """Add collected meta data to tables file"""

    volume = meta['3D']
    settings = volume['settings']
    preview = volume['preview']

    logger.debug('base_path: %s' % meta['base_path'])
    logger.debug('path: %s' % meta['path'])
    logger.debug('volume_slice_filepattern: %s'
                 % settings['volume_slice_filepattern'])
    logger.debug('extension: %s' % settings['extension'])
    logger.debug('image_type: %s' % settings['image_type'])
    logger.debug('volume_type: %s' % settings['volume_type'])
    logger.debug('data_type: %s' % settings['data_type'])
    logger.debug('offset: %s' % settings['offset'])
    logger.debug('x_dimension: %s' % settings['x_dimension'])
    logger.debug('y_dimension: %s' % settings['y_dimension'])
    logger.debug('z_dimension: %s' % settings['z_dimension'])
    logger.debug('min_value: %s' % volume['stats']['min_value'])
    logger.debug('max_value: %s' % volume['stats']['max_value'])
    logger.debug('mean: %s' % volume['stats']['mean'])
    logger.debug('median: %s' % volume['stats']['median'])
    logger.debug('md5sum: %s' % volume['md5sum'])
    logger.debug('preview xdmf_filename: %s' % preview['xdmf_filename'])
    logger.debug('preview data_type: %s' % preview['data_type'])
    logger.debug('preview_x_dimension: %s' % preview['x_dimension'])
    logger.debug('preview_y_dimension: %s' % preview['y_dimension'])
    logger.debug('preview_z_dimension: %s' % preview['z_dimension'])
    logger.debug('preview_cutoff_min: %s' % preview['cutoff_min'])
    logger.debug('preview_cutoff_max: %s' % preview['cutoff_max'])

    result = add_image_volume(
        logger,
        meta['base_path'],
        meta['path'],
        settings['volume_slice_filepattern'],
        settings['extension'],
        settings['image_type'],
        settings['volume_type'],
        settings['data_type'],
        settings['offset'],
        settings['x_dimension'],
        settings['y_dimension'],
        settings['z_dimension'],
        volume['stats']['min_value'],
        volume['stats']['max_value'],
        volume['stats']['mean'],
        volume['stats']['median'],
        volume['md5sum'],
        preview['xdmf_filename'],
        preview['data_type'],
        preview['x_dimension'],
        preview['y_dimension'],
        preview['z_dimension'],
        preview['cutoff_min'],
        preview['cutoff_max'],
        overwrite=True,
        )

    logger.debug('result: %s' % str(result))

    return result


def write_preview_xdmf(logger, meta):
    """Write prevkiew xdmf file to disk"""

    result = False

    volume = meta['3D']
    settings = volume['settings']
    preview = volume['preview']
    base_path = meta['base_path']
    path = meta['path']
    volume_slice_filepattern = settings['volume_slice_filepattern']
    data_type = settings['data_type']
    preview_x_dimension = preview['x_dimension']
    preview_y_dimension = preview['y_dimension']
    preview_z_dimension = preview['z_dimension']

    xdmf_template = \
        """<?xml version="1.0" ?>
<!DOCTYPE Xdmf SYSTEM "Xdmf.dtd" []>
<Xdmf xmlns:xi="http://www.w3.org/2003/XInclude" Version="2.2">
<Domain>
<Grid Name="Particle Images" GridType="Uniform">
    <Topology TopologyType="3DCORECTMesh" Dimensions="%(z_dimension)i %(y_dimension)i %(x_dimension)i"/>
    <Geometry GeometryType="ORIGIN_DXDYDZ">
        <DataItem Name="Origin" Dimensions="3" NumberType="%(data_type)s" Precision="%(precision)i" Format="XML">
            0 0 0
        </DataItem>
        <DataItem Name="Spacing" Dimensions="3" NumberType="%(data_type)s" Precision="%(precision)i" Format="XML">
            1 1 1
        </DataItem>
    </Geometry>
    <Attribute Name="%(name)s" AttributeType="Scalar" Center="Node">
        <DataItem Format="HDF" NumberType="%(data_type)s" Precision="%(precision)i" Dimensions="%(z_dimension)i %(y_dimension)i %(x_dimension)i">
            %(volume_path)s
        </DataItem>
    </Attribute>
</Grid>
</Domain>
</Xdmf>"""

    if not preview['data_type'] in allowed_xdmf_data_types:
        logger.error("Preview data_type: '%s' not in allowed xdmf data types: %s'"
                      % (preview['data_type'], allowed_xdmf_data_types))
        return result

    if not preview['data_type'] in allowed_xdmf_precisions:
        logger.error("Preview data_type: '%s' not in allowed xdmf precisions: %s'"
                      % (preview['data_type'], allowed_xdmf_precisions))
        return result

    xdmf_data_type = allowed_xdmf_data_types[preview['data_type']]
    xdmf_data_precision = allowed_xdmf_precisions[preview['data_type']]

    xdmf_path = get_image_xdmf_path(logger, base_path, ensure=True,
                                    makedirs=True)

    image_data_node_name = __get_data_node_name(logger, path,
            volume_slice_filepattern)
    image_data_node_path = '%s/%s' \
        % (__tables_image_volumes_preview_data_group,
           image_data_node_name)

    volume_path = '../%s:%s' % (__settings_file, image_data_node_path)
    xdmf = xdmf_template % {
        'data_type': xdmf_data_type,
        'precision': xdmf_data_precision,
        'name': volume_slice_filepattern,
        'x_dimension': preview_x_dimension,
        'y_dimension': preview_y_dimension,
        'z_dimension': preview_z_dimension,
        'volume_path': volume_path,
        }
    preview['xdmf_filename'] = xdmf_filename = '%s.xdmf' \
        % image_data_node_name
    xdmf_filepath = os.path.join(xdmf_path, xdmf_filename)
    logger.debug('Writing xdmf: \n%s\nTo : %s' % (xdmf, xdmf_filepath))

    fd = open(xdmf_filepath, 'w')
    fd.write(xdmf)
    fd.close()
    result = True

    return result


def add_volume_preview_slice_data(logger, meta):
    """Add volume slice data to tables file"""

    result = True
    base_path = meta['base_path']
    path = meta['path']
    volume = meta['3D']
    settings = volume['settings']
    preview = volume['preview']
    volume_nr = volume['volume_nr']
    volume_count = volume['volume_count']
    logger.debug('volume_nr: %s' % volume_nr)
    logger.debug('volume_count: %s' % volume_count)
    if settings is not None:
        data_type = settings['data_type']
        preview_x_dimension = preview['x_dimension']
        preview_y_dimension = preview['y_dimension']
        preview_z_dimension = preview['z_dimension']
        z_dimension = settings['z_dimension']
        volume_slice_filepattern = settings['volume_slice_filepattern']
        logger.debug('z_dimension: %s' % z_dimension)
        logger.debug('volume_slice_filepattern: %s'
                     % volume_slice_filepattern)

        # TODO: put this the right place when propper stats are collected

        fill_volume_stats(logger, meta)
        fill_volume_md5sum(logger, meta)

        # DEBUG

        extension = volume_slice_filepattern.split('.')[-1]
        logger.debug('extension: %s' % extension)
        filepattern_index = volume_slice_filepattern.find('%')
        logger.debug('filepattern_index: %s' % filepattern_index)
        image_files = get_image_files(logger, base_path, path=path,
                extension=extension, data_entries=None)
        logger.debug('image_files count: %s' % len(image_files))

        # Get metadata

        volume_slice_dict = {}
        slice_data_type = None
        for entry in image_files:
            logger.debug('image file: %s' % entry['name'])
            if (entry['name'])[:filepattern_index] \
                == volume_slice_filepattern[:filepattern_index]:
                logger.debug('pattern_match')

                # Find slice index

                slice_index_list = re.findall(r'\d+', (entry['name'
                        ])[filepattern_index:])
                slice_index_list = [int(i) for i in slice_index_list]

                logger.debug('slice_index_list: %s ' % slice_index_list)
                if len(slice_index_list) == 0:
                    logger.debug('Empty slice_index_list')
                else:
                    slice_index = int(slice_index_list[0])
                    logger.debug('Found slice_index: %s' % slice_index)
                    volume_slice_dict[slice_index] = entry
                    if slice_data_type is None or slice_data_type \
                        == entry['data_type']:
                        slice_data_type = entry['data_type']
                        volume_slice_dict[slice_index] = entry
                    else:
                        logger.debug('Incosistent slice data types: %s != %s'
                                 % (slice_data_type, entry['data_type'
                                ]))

        # Check if all slices are pre-processed

        slice_count = len(volume_slice_dict.keys())
        volume_progress = 0
        volume_progress_step = 100.0 / (slice_count
                + preview_x_dimension)
        if slice_count >= z_dimension:
            logger.debug('Creating preview volume from: %s slices'
                         % slice_count)
            settings['settings_status'] = \
                allowed_settings_status['updating']
            settings['settings_update_progress'] = '%s/%s : %s%%' \
                % (volume_nr, volume_count, int(round(volume_progress)))
            update_image_volume_setting(logger, base_path, settings)

            # Find slices data type, check if consistent

            sorted_keys = sorted(volume_slice_dict.keys())
            logger.debug('sorted_keys: %s' % sorted_keys)

            # Create tmp array to be resized
            # tmp = empty((z_dimension, preview_y_dimension, preview_x_dimension), dtype=data_type)

            tmp_volume = zeros((z_dimension, preview_y_dimension,
                               preview_x_dimension), dtype=data_type)
            logger.debug('tmp_volume shape: %s' % str(tmp_volume.shape))
            slice_idx = 0
            max_slice_shape = (0, 0)

            for file_idx in sorted_keys[:z_dimension]:
                volume_progress += volume_progress_step
                settings['settings_update_progress'] = '%s/%s : %s%%' \
                    % (volume_nr, volume_count,
                       int(round(volume_progress)))
                update_image_volume_setting(logger, base_path, settings)

                filename = volume_slice_filepattern % int(file_idx)
                slice_preview_data = \
                    get_image_file_preview_data(logger, base_path,
                        path, filename)

                tmp_volume[slice_idx, :slice_preview_data.shape[0], :
                           slice_preview_data.shape[1]] = \
                    slice_preview_data
                max_slice_shape = (max(max_slice_shape[0],
                                   slice_preview_data.shape[0]),
                                   max(max_slice_shape[1],
                                   slice_preview_data.shape[1]))

                logger.debug('slice_preview_data: %s, shape: %s, min: %s, max: %s'
                              % (slice_idx,
                             str(slice_preview_data.shape),
                             tmp_volume[slice_idx].min(),
                             tmp_volume[slice_idx].max()))
                logger.debug('max_slice_shape: %s'
                             % str(max_slice_shape))
                slice_idx += 1

            # Resize volume

            # resized_volume = empty((preview_z_dimension, preview_y_dimension, preview_x_dimension), dtype=data_type)

            resized_volume_shape = (preview_z_dimension,
                                    max_slice_shape[0],
                                    max_slice_shape[1])
            resize_z_dimension = resized_volume_shape[0]
            resize_y_dimension = resized_volume_shape[1]
            resize_x_dimension = resized_volume_shape[2]

            preview['z_dimension'] = resize_z_dimension
            preview['y_dimension'] = resize_y_dimension
            preview['x_dimension'] = resize_x_dimension

            logger.debug('volume settings: %s' % str(volume['settings'
                         ]))

            tmp_volume = tmp_volume[:resize_z_dimension, :
                                    resize_y_dimension, :
                                    resize_x_dimension:]
            logger.debug('tmp_volume new_shape: %s'
                         % str(tmp_volume.shape))
            resized_volume = zeros(resized_volume_shape,
                                   dtype=data_type)
            for x in xrange(resize_x_dimension):
                settings['settings_update_progress'] = '%s/%s : %s%%' \
                    % (volume_nr, volume_count,
                       int(round(volume_progress)))
                update_image_volume_setting(logger, base_path, settings)
                logger.debug('resize_x_dimension: %s, tmp slice: shape: %s, min: %s, max: %s'
                              % (x, str(tmp_volume[:, :, x].shape),
                             tmp_volume[:, :, x].min(), tmp_volume[:, :
                             , x].max()))
                resized_zy_slice = cv2.resize(tmp_volume[:, :, x],
                        (resize_z_dimension, resize_y_dimension))
                resized_volume[:, :, x] = resized_zy_slice
                logger.debug('resized_zy_slice: %s, min: %s, max: %s'
                             % (str(resized_zy_slice.shape),
                             resized_zy_slice.min(),
                             resized_zy_slice.max()))
                logger.debug('resized_volume[:,:,x]: %s, min: %s, max: %s'
                              % (str(resized_volume[:, :, x].shape),
                             resized_volume[:, :, x].min(),
                             resized_volume[:, :, x].max()))
            logger.debug('resized_volume: %s, min: %s, max: %s'
                         % (str(resized_volume.shape),
                         resized_volume.min(), resized_volume.max()))

            result = add_image_volume_preview_data(logger, base_path,
                    path, volume_slice_filepattern, resized_volume)
        else:
            result = False
            logger.debug('Missing: %s slices to create volume'
                         % (z_dimension - slice_count))

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


def update_file_preview(
    logger,
    base_path,
    path,
    filename,
    ):
    """Update file preview for image *path*/*filename"""

    result = False

    meta = __init_meta(logger, base_path, path, filename)
    meta['2D']['settings'] = settings = get_image_file_setting(logger,
            base_path, meta['extension'])

    if settings is not None:
        if fill_image_data(logger, meta) and fill_image_stats(logger,
                meta) and fill_image_md5sum(logger, meta) \
            and fill_image_preview(logger, meta) \
            and write_preview_image(logger, meta) \
            and add_image_meta_data(logger, meta) \
            and add_image_preview_data(logger, meta) \
            and add_image_preview_image(logger, meta) \
            and fill_image_preview_histogram(logger, meta) \
            and add_image_preview_histogram(logger, meta):
            result = True
        else:
            logger.info('Skipping update for: %s, %s, %s' % (base_path,
                        path, filename))

    logger.debug('result: %s' % str(result))

    return result


def update_volume_preview(
    logger,
    base_path,
    path,
    filename=None,
    volume_nr=1,
    volume_count=1,
    ):
    """Update volume preview"""

    meta = __init_meta(logger, base_path, path, filename)
    volume = meta['3D']
    volume['settings'] = settings = get_image_volume_setting(logger,
            base_path, meta['extension'])
    volume['volume_nr'] = volume_nr
    volume['volume_count'] = volume_count

    result = False
    if settings is not None:
        if settings['volume_type'] == 'slice':
            if fill_volume_preview_meta(logger, meta) \
                and add_volume_preview_slice_data(logger, meta) \
                and write_preview_xdmf(logger, meta) \
                and add_volume_meta_data(logger, meta):

                result = True
        else:
            logger.error('Unsupported volume type: %s'
                         % settings['volume_type'])

    return result


def update_preview(
    logger,
    base_path,
    path,
    filename,
    ):
    """Update image preview for *extension* in *base_path*"""

    result = False
    if update_file_preview(logger, base_path, path, filename) \
        and update_volume_preview(logger, base_path, path, filename):
        result = True

    return result


def update_previews(logger, base_path, extension):
    """Update image previews for *extension* in *base_path*"""

    logger.debug("base_path: '%s', extension: '%s'" % (base_path,
                 extension))
    image_setting = get_image_file_setting(logger, base_path, extension)
    logger.debug('image_setting: %s' % image_setting)
    volume_setting = get_image_volume_setting(logger, base_path,
            extension)
    logger.debug('volume_setting: %s' % volume_setting)

    result = True
    image_status = True
    volume_status = True
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

            processed_volume_count = 0
            total_volume_count = 0
            if volume_setting is not None \
                and volume_setting['volume_type'] == 'slice':
                total_volume_count = int(floor(total_filecount
                        / volume_setting['z_dimension']))

            if image_setting['settings_recursive']:
                for (root, _, files) in os.walk(base_path):
                    slice_modified = False
                    path = root.replace(base_path, '', 1).strip('/')
                    for name in files:
                        if not name.startswith('.') \
                            and name.endswith('.%s' % extension):
                            logger.debug('check entry -> path: %s, name: %s'
                                     % (path, name))
                            if update_file_preview(logger, base_path,
                                    path, name):
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
                                slice_modified = True
                            else:
                                image_status = False
                    if slice_modified and volume_setting is not None:
                        volume_status = update_volume_preview(logger,
                                base_path, path,
                                volume_nr=processed_volume_count,
                                volume_count=total_volume_count)
                        if volume_status:
                            processed_volume_count += 1
            else:
                slice_modified = False
                path = ''
                for name in os.listdir(base_path):
                    logger.debug('check entry: %s' % name)
                    if not name.startswith('.') and name.endswith('.%s'
                            % extension):
                        filepath = os.path.join(base_path, name)
                        if os.path.isfile(filepath):
                            if update_file_preview(logger, base_path,
                                    path, name):
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
                                slice_modified = True
                            else:
                                image_status = False
                if slice_modified and volume_setting is not None:
                    volume_status = update_volume_preview(logger,
                            base_path, path)
                    if volume_status:
                        processed_volume_count += 1

            # Set final update status and progress

            image_setting['settings_update_progress'] = None
            if image_status:
                image_setting['settings_status'] = status_ready
            else:
                image_setting['settings_status'] = status_failed
            logger.debug('image settings status: %s'
                         % image_setting['settings_status'])
            update_image_file_setting(logger, base_path, image_setting)

            if volume_setting is not None:
                image_setting['settings_update_progress'] = None
                if volume_status:
                    volume_setting['settings_status'] = status_ready
                else:
                    volume_setting['settings_status'] = status_failed
                logger.debug('volume settings status: %s'
                             % image_setting['settings_status'])
                update_image_volume_setting(logger, base_path,
                        volume_setting)
        else:
            logger.info("Skipping update for: %s, %s, expected status: 'Pending', found '%s'"
                         % (base_path, extension, settings_status))
    else:
        logger.info('Skipping update for: %s, %s -> No image settings found'
                     % (base_path, extension))

    return result


