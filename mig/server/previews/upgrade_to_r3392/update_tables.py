#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback

MIG_HOME = '%s/mig' % os.environ['HOME']
SETTINGS_LIST = 'settings.h5.list.txt'
sys.path.append(MIG_HOME)

from shared.logger import _debug_format, _default_format
from shared.imagemetaio import __close_image_settings_file, \
    __acquire_file_lock, __ensure_tables_format, __get_table, \
    __modify_table_rows, allowed_volume_types
from tables import open_file


def get_logger(loglevel=logging.INFO):
    if loglevel == logging.DEBUG:
        logformat = _debug_format
    else:
        logformat = _default_format

    logger = logging.getLogger()
    logger.setLevel(loglevel)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(logformat)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def open_image_settings_file(logger, settings_file):
    """Open pytable *settings_file*"""

    metafile = None
    if not os.path.exists(settings_file):
        logger.error('Missing settings_file: %s' % settings_file)
    else:
        metafile = {}
        metafile['lock'] = __acquire_file_lock(logger, settings_file)
        filemode = 'r+'
        try:
            metafile['tables'] = open_file(settings_file,
                    mode=filemode,
                    title='Image directory meta-data file')
        except Exception:
            logger.error("opening: '%s' in mode '%s'" % (settings_file,
                         filemode))
            logger.error(traceback.format_exc())
            __close_image_settings_file(logger, metafile)
            metafile = None

    return metafile


def update_volume_type(logger, settings_file):
    """Update volume type"""

    status = True
    metafile = open_image_settings_file(logger, settings_file)
    modify_dict = {'volume_type': allowed_volume_types['slice']}
    condition = 'volume_type == b"slice"'
    if metafile is None:
        status = False
    else:
        __ensure_tables_format(logger, metafile)

        for table in ['image_volume_settings', 'image_volume']:
            table = __get_table(logger, metafile, table)

            if __modify_table_rows(
                logger,
                table,
                condition,
                modify_dict,
                overwrite=True,
                create=False,
                ):
                logger.info("Updated volume_type: '%s' for table: '%s'"
                            % (modify_dict['volume_type'], table))
            else:
                logger.warning("Failed to update volume_type: '%s' for table: '%s'"
                                % (modify_dict['volume_type'], table))

        __close_image_settings_file(logger, metafile)

    return status


def main():
    logger = get_logger()

    fh = open(SETTINGS_LIST)

    for line in fh:
        line = line.strip()
        if len(line) > 0:
            settings_file = line.replace('settings.h5',
                    'imagepreviews.h5')
            logger.info('--------------------------------------------------------------------'
                        )
            msg = 'Updating: %s' % settings_file
            logger.info(msg)
            logger.info('--------------------------------------------------------------------'
                        )
            status = update_volume_type(logger, settings_file)
            logger.info('--------------------------------------------------------------------'
                        )
            msg = 'update_volume_type: %s' % status
            logger.info(msg)
            logger.info('--------------------------------------------------------------------'
                        )


if __name__ == '__main__':
    main()
