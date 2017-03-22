#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging

MIG_HOME = '%s/mig' % os.environ['HOME']
MIG_CONF = '%s/server/MiGserver.conf' % MIG_HOME
TRIGGER_DICT_FILE = 'trigger_dict.pck'

os.environ['MIG_CONF'] = MIG_CONF
sys.path.append(MIG_HOME)

from shared.conf import get_configuration_object
from shared.logger import _debug_format, _default_format
from shared.fileio import unpickle


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


def get_vgrids_dict(vgrids_dict):
    vgrid_list = [vgrids_dict[key]['vgrid'] for key in
                  vgrids_dict.keys()]
    unique_vgrid_list = set(vgrid_list)

    return unique_vgrid_list


def main():
    configuration = get_configuration_object()

    # Overwrite default logger

    logger = configuration.logger = get_logger(logging.INFO)

    logger = configuration.logger = get_logger(logging.INFO)
    vgrids_dict = unpickle(TRIGGER_DICT_FILE, logger)

    vgrid_list = get_vgrids_dict(vgrids_dict)
    for name in vgrid_list:
        print name


if __name__ == '__main__':
    sys.exit(main())

