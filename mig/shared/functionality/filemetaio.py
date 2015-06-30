#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# filemetaio - Managing MiG file meta io
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

"""Script to provide users with a means of listing file meta data from
their home directories.
"""

import os
import time
import traceback

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_settings
from shared.imagemetaio import get_image_file, add_image_file_setting, \
    get_image_file_settings, get_image_file_setting, \
    remove_image_file_settings, get_preview_image_url, \
    allowed_settings_status, get_image_file_count, __metapath, \
    __image_metapath
from shared.vgrid import vgrid_add_triggers, vgrid_remove_triggers, \
    vgrid_list_vgrids, vgrid_is_trigger
from shared.fileio import touch, makedirs_rec, listdirs_rec, delete_file


def __get_mrsl_template():
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


def __get_image_create_previews_mrsl_template(datapath, extension):
    """Template for changed image preview setting trigger jobs"""

    result = \
        """::EXECUTE::
echo "hostname: `hostname -f`"
echo "uname: `uname -a`"
echo "TRIGGERPATH: +TRIGGERPATH+"
echo "TRIGGERDIRNAME: +TRIGGERDIRNAME+"
echo "TRIGGERFILENAME: +TRIGGERFILENAME+"
echo "TRIGGERPREFIX: +TRIGGERPREFIX+"
echo "TRIGGEREXTENSION: +TRIGGEREXTENSION+"
echo "TRIGGERCHANGE: +TRIGGERCHANGE+"
echo "TRIGGERVGRIDNAME: +TRIGGERVGRIDNAME+"
echo "TRIGGERRUNAS: +TRIGGERRUNAS+"
echo "datapath: %(datapath)s"
echo "extension: %(extension)s"
# DEBUG
ls -la
ls -la shared/*
ls -la %(datapath)s/
ls -la %(datapath)s/.meta
# end DEBUG
python idmc_update_previews.py +TRIGGERCHANGE+ %(datapath)s %(extension)s

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
        + __get_mrsl_template()

    return result


def __get_image_update_preview_mrsl_template(datapath):
    """Template for image file changed preview setting trigger jobs"""

    result = \
        """::EXECUTE::
echo "hostname: `hostname`"
echo "uname: `uname`"
echo "TRIGGERPATH: +TRIGGERPATH+"
echo "TRIGGERDIRNAME: +TRIGGERDIRNAME+"
echo "TRIGGERFILENAME: +TRIGGERFILENAME+"
echo "TRIGGERPREFIX: +TRIGGERPREFIX+"
echo "TRIGGEREXTENSION: +TRIGGEREXTENSION+"
echo "TRIGGERCHANGE: +TRIGGERCHANGE+"
echo "TRIGGERVGRIDNAME: +TRIGGERVGRIDNAME+"
echo "TRIGGERRUNAS: +TRIGGERRUNAS+"
echo "datapath: %(datapath)s"
# DEBUG
ls -la
ls -la %(datapath)s/
ls -la %(datapath)s/.meta
# end DEBUG
python idmc_update_preview.py +TRIGGERCHANGE+ %(datapath)s +TRIGGERPATH+

::MOUNT::
+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+

::EXECUTABLES::

::INPUTFILES::
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/imagemetaio.py imagemetaio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/imagepreview.py imagepreview.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/idmc_update_preview.py idmc_update_preview.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/__init__.py shared/__init__.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/defaults.py shared/defaults.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/fileio.py shared/fileio.py
http://www.migrid.org/vgrid/eScience/Projects/NBI/IDMC/trigger_scripts/shared/serial.py shared/serial.py
""" \
        % {'datapath': datapath} + __get_mrsl_template()

    return result


def __find_image_meta(logger, base_dir, filepath):
    """Recursively seek upwards for image meta data"""

    result = None

    path_array = filepath.split('/')
    filename = path_array.pop()
    path = ''
    while result is None and len(path_array) > 0:
        abs_base_path = os.path.join(base_dir, os.sep.join(path_array))
        try:
            image_meta = get_image_file(logger, abs_base_path, path,
                    filename)
        except Exception, ex:
            image_meta = None
            logger.debug(str(traceback.format_exc()))
        if image_meta is not None:
            result = image_meta
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
    ):
    """Check if valid image settings update"""

    result = True
    msg = ''

    logger = configuration.logger

    # Check for vgrid

    (status, vgrid_list) = vgrid_list_vgrids(configuration)
    if not status or status and not vgrid_name in vgrid_list:
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
            except Exception, ex:
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
            except Exception, ex:
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
    image_meta = get_image_file_setting(logger, abs_path, extension)
    if image_meta is not None and image_meta['settings_status'] \
        != allowed_settings_status['ready'] \
        and image_meta['settings_status'] \
        != allowed_settings_status['failed']:
        result = False
        msg = 'Not ready for update, status: %s' \
            % image_meta['settings_status']

    return (result, msg)


def __get_image_settings_trigger_last_modified_filepath(logger, path,
        extension):
    """Returns filepath for last_modified file used to trigger image settting changes"""

    metapath = os.path.join(path, __metapath)

    return os.path.join(metapath, '%s.last_modified' % extension)


def __get_image_file_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image file changes"""

    path_array = path.split('/')

    return 'system_imagesettings_%s_%s_files' % ('_'.join(path_array),
            extension)


def __get_image_settings_trigger_rule_id(logger, path, extension):
    """Return id of trigger rule used when image settings changes"""

    path_array = path.split('/')

    return 'system_imagesettings_%s_%s_settings' \
        % ('_'.join(path_array), extension)


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


def signature():
    """Signature of the main function"""

    defaults = {
        'action': ['list'],
        'flags': [''],
        'path': ['.'],
        'extension': [''],
        'settings_status': [allowed_settings_status['pending']],
        'settings_recursive': ['False'],
        'image_type': [''],
        'data_type': [''],
        'offset': ['0'],
        'x_dimension': ['0'],
        'y_dimension': ['0'],
        'preview_image_extension': ['png'],
        'preview_x_dimension': ['256'],
        'preview_y_dimension': ['256'],
        'preview_cutoff_min': ['0.0'],
        'preview_cutoff_max': ['0.0'],
        }

    return ['filemetaio', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]

    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )

    if not validate_status:
        WARNING_MSG = str(accepted)
        output_objects.append({'object_type': 'warning',
                              'text': WARNING_MSG})
        return (accepted, returnvalues.CLIENT_ERROR)

    action = ''.join(accepted['action'])
    flags = ''.join(accepted['flags'])
    path = ''.join(accepted['path'])
    extension = ''.join(accepted['extension'])

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    abs_path = os.path.join(base_dir, path)

    settings_dict = load_settings(client_id, configuration)
    javascript = None

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'FILEMETAIO Management'
    title_entry['javascript'] = javascript
    output_objects.append({'object_type': 'header',
                          'text': 'FILEMETAIO Management'})
    status = returnvalues.ERROR

    if flags == 'i':
        if action == 'list':
            image_meta = get_image_file_settings(logger, abs_path)
            if image_meta is not None:
                extension_list = []
                settings_status_list = []
                settings_progress_list = []
                image_count_list = []
                for entry in image_meta:
                    extension_list.append(entry['extension'])
                    settings_status_list.append(entry['settings_status'
                            ])
                    settings_progress_list.append(entry['settings_update_progress'
                            ])
                    image_count_list.append(get_image_file_count(logger,
                            abs_path, entry['extension']))

                output_objects.append({
                    'object_type': 'image_settings_list',
                    'extension_list': extension_list,
                    'settings_status_list': settings_status_list,
                    'settings_progress_list': settings_progress_list,
                    'image_count_list': image_count_list,
                    })
                status = returnvalues.OK
            else:
                status = returnvalues.ERROR
                ERROR_MSG = "No image settings found for path: '%s'" \
                    % path
                output_objects.append({'object_type': 'text',
                        'text': ERROR_MSG})
                logger.error('filemetaio.py: %s -> %s' % (action,
                             ERROR_MSG))
        elif action == 'remove_dir':
            remove_ext = None
            vgrid_name = path.split('/')[0]

            if extension != '':
                remove_ext = extension
            try:
                (result, removed_ext_list) = \
                    remove_image_file_settings(logger, abs_path,
                        remove_ext)
            except Exception, ex:
                logger.debug(str(traceback.format_exc()))

            if result is not None:
                result = returnvalues.OK
            else:
                result = returnvalues.ERROR
                ERROR_MSG = \
                    'Unable to remove image settings for path: %s' \
                    % path
                output_objects.append({'object_type': 'text',
                        'text': ERROR_MSG})
                logger.error('filemetaio.py: %s -> %s' % (action,
                             ERROR_MSG))

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
                            path, removed_ext)
                    status = __remove_image_file_trigger(
                        configuration,
                        vgrid_name,
                        path,
                        extension,
                        rule_id,
                        output_objects,
                        )
                    if status != returnvalues.OK:
                        result = status

                    # Remove old vgrid submit trigger for settings

                    rule_id = \
                        __get_image_settings_trigger_rule_id(logger,
                            path, removed_ext)
                    status = __remove_image_settings_trigger(
                        configuration,
                        vgrid_name,
                        path,
                        extension,
                        rule_id,
                        output_objects,
                        )
                    if status != returnvalues.OK:
                        result = status
                else:
                    result = returnvalues.ERROR
                    ERROR_MSG = 'Unable to remove file: %s ' \
                        % abs_last_modified_filepath
                    output_objects.append({'object_type': 'text',
                            'text': ERROR_MSG})
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG))
        elif action == 'get_dir':

            image_count = get_image_file_count(logger, abs_path,
                    extension)
            image_meta = get_image_file_setting(logger, abs_path,
                    extension)

            if image_meta is not None:
                extension = str(image_meta['extension'])
                settings_status = str(image_meta['settings_status'])
                settings_update_progress = \
                    str(image_meta['settings_update_progress'])
                settings_recursive = str(image_meta['settings_recursive'
                        ])
                image_count = str(image_count)
                image_type = str(image_meta['image_type'])
                offset = str(image_meta['offset'])
                x_dimension = str(image_meta['x_dimension'])
                y_dimension = str(image_meta['y_dimension'])
                preview_image_extension = \
                    str(image_meta['preview_image_extension'])
                preview_x_dimension = \
                    str(image_meta['preview_x_dimension'])
                preview_y_dimension = \
                    str(image_meta['preview_y_dimension'])
                preview_cutoff_min = str(image_meta['preview_cutoff_min'
                        ])
                preview_cutoff_max = str(image_meta['preview_cutoff_max'
                        ])
                data_type = str(image_meta['data_type'])

                output_objects.append({
                    'object_type': 'image_setting',
                    'path': path,
                    'extension': extension,
                    'settings_status': settings_status,
                    'settings_update_progress': settings_update_progress,
                    'settings_recursive': settings_recursive,
                    'image_count': image_count,
                    'image_type': image_type,
                    'offset': offset,
                    'x_dimension': x_dimension,
                    'y_dimension': y_dimension,
                    'preview_image_extension': preview_image_extension,
                    'preview_x_dimension': preview_x_dimension,
                    'preview_y_dimension': preview_y_dimension,
                    'preview_cutoff_min': preview_cutoff_min,
                    'preview_cutoff_max': preview_cutoff_max,
                    'data_type': data_type,
                    })
                status = returnvalues.OK
            else:
                status = returnvalues.ERROR
                ERROR_MSG = \
                    "No image setting information for path: '%s', extension: '%s'" \
                    % (path, extension)
                output_objects.append({'object_type': 'text',
                        'text': ERROR_MSG})
                logger.error('filemetaio.py: %s -> %s' % (action,
                             ERROR_MSG))
        elif action == 'put_dir':
            settings_status = ''.join(accepted['settings_status'])
            if ''.join(accepted['settings_recursive']) == 'True':
                settings_recursive = True
            else:
                settings_recursive = False
            image_type = ''.join(accepted['image_type'])
            data_type = ''.join(accepted['data_type'])
            offset = int(''.join(accepted['offset']))
            x_dimension = int(''.join(accepted['x_dimension']))
            y_dimension = int(''.join(accepted['y_dimension']))
            preview_image_extension = \
                ''.join(accepted['preview_image_extension'])
            preview_x_dimension = \
                int(''.join(accepted['preview_x_dimension']))
            preview_y_dimension = \
                int(''.join(accepted['preview_y_dimension']))
            preview_cutoff_min = \
                float(''.join(accepted['preview_cutoff_min']))
            preview_cutoff_max = \
                float(''.join(accepted['preview_cutoff_max']))

            path_array = path.split('/')
            vgrid_name = path_array[0]
            vgrid_data_path = '/'.join(path_array[1:])
            vgrid_meta_path = os.path.join(vgrid_data_path, __metapath)
            vgrid_image_meta_path = os.path.join(vgrid_data_path,
                    __image_metapath)

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
                vgrid_data_path,
                extension,
                settings_recursive,
                )

            if is_valid:
                status = returnvalues.OK
            else:
                status = returnvalues.ERROR
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                output_objects.append({'object_type': 'error_text',
                        'text': is_valid_msg})
                logger.error('filemetaio.py: %s -> %s' % (action,
                             ERROR_MSG))
                logger.error('filemetaio.py: %s -> %s' % (action,
                             is_valid_msg))

            # Ensure meta path existence

            if status == returnvalues.OK:
                makedirs_rec(os.path.join(base_dir,
                             os.path.join(vgrid_name,
                             vgrid_meta_path)), configuration)

                # Ensure image meta path existence

                makedirs_rec(os.path.join(base_dir,
                             os.path.join(vgrid_name,
                             vgrid_image_meta_path)), configuration)

                try:
                    add_status = add_image_file_setting(
                        logger,
                        abs_path,
                        extension,
                        settings_status,
                        None,
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
                except Exception, ex:
                    add_status = False
                    logger.debug(str(traceback.format_exc()))

                if add_status:
                    status = returnvalues.OK
                    output_objects.append({'object_type': 'text',
                            'text': OK_MSG})
                else:
                    status = returnvalues.ERROR
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG})
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG))

            if status == returnvalues.OK:

                # Generate vgrid trigger for files

                if settings_recursive:
                    vgrid_trigger_path = os.path.join(vgrid_data_path,
                            '*/*.%s' % extension)
                else:
                    vgrid_trigger_path = os.path.join(vgrid_data_path,
                            '*.%s' % extension)

                rule_id = __get_image_file_trigger_rule_id(logger,
                        path, extension)
                rule_dict = {
                    'rule_id': rule_id,
                    'vgrid_name': vgrid_name,
                    'path': vgrid_trigger_path,
                    'changes': ['created', 'modified', 'deleted',
                                'moved'],
                    'run_as': client_id,
                    'action': 'submit',
                    'arguments': 'template_from_filemetaio.py',
                    'templates': [__get_image_update_preview_mrsl_template(path)],
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

                (add_status, add_msg) = \
                    vgrid_add_triggers(configuration, vgrid_name,
                        [rule_dict])
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
                    ERROR_MSG2 = "Makes sure '%s' is a VGrid" \
                        % vgrid_name
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG})
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG2})
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG))
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG2))

            if status == returnvalues.OK:

                # Generate vgrid trigger for settings

                vgrid_path = '/'.join(path.split('/')[1:])
                vgrid_trigger_filepath = \
                    __get_image_settings_trigger_last_modified_filepath(logger,
                        vgrid_path, extension)

                rule_id = __get_image_settings_trigger_rule_id(logger,
                        path, extension)
                rule_dict = {
                    'rule_id': rule_id,
                    'vgrid_name': vgrid_name,
                    'path': vgrid_trigger_filepath,
                    'changes': ['modified', 'deleted'],
                    'run_as': client_id,
                    'action': 'submit',
                    'arguments': 'template_from_filemetaio.py',
                    'templates': [__get_image_create_previews_mrsl_template(path,
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

                (add_status, add_msg) = \
                    vgrid_add_triggers(configuration, vgrid_name,
                        [rule_dict])
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
                    ERROR_MSG2 = "Makes sure '%s' is a VGrid" \
                        % vgrid_name
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG})
                    output_objects.append({'object_type': 'error_text',
                            'text': ERROR_MSG2})
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG))
                    logger.error('filemetaio.py: %s -> %s' % (action,
                                 ERROR_MSG2))

            if status == returnvalues.OK:

                # Trigger Trigger (Trigger Happty)

                abs_vgrid_trigger_filepath = os.path.join(base_dir,
                        os.path.join(vgrid_name,
                        vgrid_trigger_filepath))

                # FYSIKER HACK: Sleep 1 to prevent trigger rule/event race
                # TODO: Modify events handler to accept add+trigger action

                time.sleep(1)
                timestamp = time.time()
                touch(abs_vgrid_trigger_filepath, timestamp)
        elif action == 'get_file':
            image_meta = __find_image_meta(logger, base_dir, path)
            if image_meta is not None:
                image_type = str(image_meta['image_type'])
                preview_image_url = get_preview_image_url(logger,
                        '/cert_redirect/%s' % image_meta['base_path'],
                        image_meta['preview_image_filepath'])
                base_path = str(image_meta['base_path'])
                path = str(image_meta['path'])
                name = str(image_meta['name'])
                extension = str(image_meta['extension'])
                offset = str(image_meta['offset'])
                x_dimension = str(image_meta['x_dimension'])
                y_dimension = str(image_meta['y_dimension'])
                preview_x_dimension = \
                    str(image_meta['preview_x_dimension'])
                preview_y_dimension = \
                    str(image_meta['preview_y_dimension'])
                preview_cutoff_min = str(image_meta['preview_cutoff_min'
                        ])
                preview_cutoff_max = str(image_meta['preview_cutoff_max'
                        ])
                preview_image_scale = \
                    str(image_meta['preview_image_scale'])
                preview_histogram = image_meta['preview_histogram'
                        ].tolist()
                min_value = str(image_meta['min_value'])
                max_value = str(image_meta['max_value'])
                median_value = str(image_meta['median_value'])
                mean_value = str(image_meta['mean_value'])
                file_md5sum = str(image_meta['file_md5sum'])
                data_type = str(image_meta['data_type'])

                output_objects.append({
                    'object_type': 'image_meta',
                    'image_type': image_type,
                    'preview_image_url': preview_image_url,
                    'preview_histogram': preview_histogram,
                    'base_path': base_path,
                    'path': path,
                    'name': name,
                    'extension': extension,
                    'offset': offset,
                    'x_dimension': x_dimension,
                    'y_dimension': y_dimension,
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
                    })
                status = returnvalues.OK
            else:
                ERROR_MSG = 'No image information for file: %s' % path
                output_objects.append({'object_type': 'error_text',
                        'text': ERROR_MSG})
                logger.error('filemetaio.py: %s -> %s' % (action,
                             ERROR_MSG))
        elif action == 'put_file':
            ERROR_MSG = "action: 'put' _NOT_ implemented yet"
            output_objects.append({'object_type': 'error_text',
                                  'text': ERROR_MSG})
            logger.error('filemetaio.py: %s -> %s' % (action,
                         ERROR_MSG))
    else:
        ERROR_MSG = "Unsupported request: action: '%s', flags: '%s'" \
            % (action, flags)
        output_objects.append({'object_type': 'error_text',
                              'text': ERROR_MSG})
        logger.error('filemetaio.py: %s -> %s' % (action, ERROR_MSG))

    return (output_objects, status)


