#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import sys

MIG_HOME = '%s/mig' % os.environ['HOME']
MIG_CONF = '%s/server/MiGserver.conf' % MIG_HOME
SETTINGS_LIST = 'settings.h5.list.txt'
VGRID_DICT_FILE = 'trigger_dict.pck'
METAPATH = '.meta'

os.environ['MIG_CONF'] = MIG_CONF
sys.path.append(MIG_HOME)

try:
    from mig.shared.conf import get_configuration_object
    from mig.shared.fileio import pickle, unpickle
    from mig.shared.logger import _debug_format, _default_format
except:
    print("cannot load migrid code")
    sys.exit(1)


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


def get_vgridtriggerpath(vgrid, path):
    """Some triggers act on meta-paths, remove meta-path part if present"""

    vgridtriggerpath = os.path.dirname(os.path.join(vgrid, path))

    if vgridtriggerpath.endswith(METAPATH):
        vgridtriggerpath = vgridtriggerpath[:-len(METAPATH)].strip('/')

    return vgridtriggerpath


def fill_vgrids(configuration, settings_filepath, vgrids_dict):
    """Retrieve vgrid information from *settings_filepath* and
    add it to *vgrids_dict*"""

    status = True
    logger = configuration.logger

    vgrids_dict[settings_filepath] = {}
    logger.info('----------------------------------------------')
    logger.info("settings_filepath: '%s'" % settings_filepath)
    logger.info('----------------------------------------------')
    settings_filepath_array = \
        settings_filepath[len(configuration.vgrid_files_home):].split('/'
                                                                      )
    settings_path_array = settings_filepath_array[:-2]
    vgridpath = '/'.join(settings_path_array)

    vgrid = None
    tmp_vgridpath = ''
    for ent in settings_path_array:
        tmp_vgridpath = '%s/%s' % (tmp_vgridpath, ent)
        tmp_vgridpath = tmp_vgridpath.strip('/')
        abs_vgrid_home_path = '%s/%s' % (configuration.vgrid_home,
                                         tmp_vgridpath)
        if os.path.exists(abs_vgrid_home_path):
            vgrid = tmp_vgridpath

    if vgrid is None:
        status = False
        logger.error("Couldn't find vgrid for file: '%s'"
                     % settings_filepath)
    else:
        vgrids_dict[settings_filepath]['vgrid'] = vgrid
        vgrids_dict[settings_filepath]['vgridpath'] = vgridpath
        vgrids_dict[settings_filepath]['triggers'] = []
        logger.info('vgrid: %s' % vgrids_dict[settings_filepath]['vgrid'
                                                                 ])
        logger.info('vgridpath: %s'
                    % vgrids_dict[settings_filepath]['vgridpath'])

    logger.info('----------------------------------------------')

    return status


def fill_triggers(configuration, vgrids_dict):
    """Search for system_imagesettings triggers and the needed information,
    such as rule_id, run_as and path to *vgrids_dict*"""

    status = True
    logger = configuration.logger
    logger.info("%s" % vgrids_dict.keys())
    for key in vgrids_dict:
        logger.info('----------------------------------------------')
        logger.info('%s' % key)
        logger.info('----------------------------------------------')

        vgrid = vgrids_dict[key]['vgrid']
        vgridpath = vgrids_dict[key]['vgridpath']

        trigger_file = \
            os.path.join(os.path.join(configuration.vgrid_home, vgrid),
                         configuration.vgrid_triggers)

        if not os.path.exists(trigger_file):
            logger.warning("Missing trigger configuration: '%s'"
                           % trigger_file)
        else:
            triggers = unpickle(trigger_file, logger)
            if not isinstance(triggers, list):
                status = False
                logger.error("Couldn't load trigger configuration: '%s'"
                             % trigger_file)
                break

            for trigger in triggers:
                if trigger['rule_id'].startswith('system_imagesettings_'
                                                 ):
                    vgridtriggerpath = get_vgridtriggerpath(vgrid,
                                                            trigger['path'])
                    if trigger['rule_id'] \
                        == 'system_imagesettings_meta_created' \
                        or trigger['rule_id'] \
                        == 'system_imagesettings_dir_deleted' \
                            or vgridtriggerpath == vgridpath:

                        logger.info("vgrid: '%s'" % vgrid)
                        logger.info("path: '%s'" % vgridpath)
                        logger.info("rule_id: '%s'" % trigger['rule_id'
                                                              ])
                        logger.info("run_as '%s'" % trigger['run_as'])
                        logger.info('----------------------------------------------'
                                    )
                        trigger = {'rule_id': trigger['rule_id'],
                                   'run_as': trigger['run_as'],
                                   'path': vgridpath}
                        vgrids_dict[key]['triggers'].append(trigger)

    return status


def main():
    configuration = get_configuration_object()

    # Overwrite default logger

    logger = configuration.logger = get_logger(logging.INFO)

    vgrids_dict = {}
    logger.info('==================== Filling vgrids ===================='
                )
    fh = open(SETTINGS_LIST)
    for line in fh:
        line = line.strip()
        if len(line) > 0:
            status = fill_vgrids(configuration, line, vgrids_dict)
            if not status:
                break
    fh.close()

    if status:
        logger.info('==================== Filling triggers ===================='
                    )

        status = fill_triggers(configuration, vgrids_dict)

    if status:
        logger.info('==================== Writing triggers dict ===================='
                    )

        logger.info("'Pickle to file: '%s'" % VGRID_DICT_FILE)

        status = pickle(vgrids_dict, VGRID_DICT_FILE, logger)

    if status:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
