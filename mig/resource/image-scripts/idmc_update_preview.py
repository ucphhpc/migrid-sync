#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# idmc_update_preview - Generating MiG image preview and meta data
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

"""Image preview and meta data generator"""

import sys
import logging
from imagepreview import update_preview, cleanup_previews


def main():
    logger_format = \
        '%(asctime)s %(module)s:%(funcName)s:%(lineno)s %(levelname)s %(message)s'
    logging.basicConfig(format=logger_format, level=logging.DEBUG)
    logger = logging

    argc = len(sys.argv) - 1
    if argc != 3:
        logger.error('USAGE: %s action base_path triggerpath'
                     % sys.argv[0])
        sys.exit(1)

    action = sys.argv[1]
    base_path = sys.argv[2]
    triggerpath = sys.argv[3]
    filepath = triggerpath.replace(base_path, '', 1)
    logger.info('idmc_create_preview: action: %s, base_path: %s, triggerpath: %s, filepath: %s'
                 % (action, base_path, triggerpath, filepath))

    update_status = None
    cleanup_status = None

    if action == 'created' or action == 'modified':
        update_status = update_preview(logger, base_path, filepath)
        if update_status:
            cleanup_status = cleanup_previews(logger, base_path)
    elif action == 'deleted':

    # elif action == 'moved' or action == 'deleted':

        cleanup_status = cleanup_previews(logger, base_path)
    else:

    #    status = update_preview(logger, 'remove', base_path, filepath)

        logger.error('idmc_create_preview: unsupported action: %s'
                     % action)

    if update_status is not None:
        if update_status:
            logger.info('idmc_update_preview: update success')
        else:
            logger.info('idmc_update_preview: update failure')

    if cleanup_status is not None:
        if cleanup_status:
            logger.info('idmc_update_preview: cleanup success')
        else:
            logger.info('idmc_update_preview: cleanup failure')


if __name__ == '__main__':
    main()

