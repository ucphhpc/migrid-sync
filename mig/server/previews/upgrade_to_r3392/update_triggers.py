#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
import time

MIG_HOME = '%s/mig' % os.environ['HOME']
MIG_CGI_BIN = '%s/cgi-bin' % MIG_HOME
MIG_CONF = '%s/server/MiGserver.conf' % MIG_HOME
TRIGGER_DICT_FILE = 'trigger_dict.pck'

os.environ['MIG_CONF'] = MIG_CONF
sys.path.append(MIG_HOME)

from mig.shared.conf import get_configuration_object
from mig.shared.logger import _debug_format, _default_format
from mig.shared.fileio import pickle, unpickle, copy, move, delete_file
from mig.shared.safeeval import subprocess_call
from mig.shared.vgrid import vgrid_owners
from mig.shared.findtype import is_user


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


def get_valid_vgrid_owner_id(configuration, vgrid_name):
    """Returns the first valid owner_id for *vgrid_name*
    """

    result = None

    # Look for owner in current (sub)vgrid

    (owners_status, owners_id) = vgrid_owners(vgrid_name,
            configuration, recursive=False)

    if owners_status:

        # Only allow valid users

        for owner_id in owners_id:
            if is_user(owner_id, configuration.mig_server_home):
                result = owner_id

    if result is None:

        # If no valid vgrid owners found look recursively towards top-vgrid

        (owners_status, owners_id) = vgrid_owners(vgrid_name,
                configuration, recursive=True)

        if owners_status:
            for owner_id in owners_id:
                if is_user(owner_id, configuration.mig_server_home):
                    result = owner_id

    return result


def filter_vgrids_dict(configuration, vgrids_dict,
                       user_vgrid_list=None):
    """Returns vgrid_dict and unique vgrid_list
    associated with vgrids specified in *user_vgrid_list*
    """

    if user_vgrid_list is None:
        vgrid_list = [vgrids_dict[key]['vgrid'] for key in
                      vgrids_dict.keys()]
    else:
        vgrid_list = [vgrids_dict[key]['vgrid'] for key in
                      vgrids_dict.keys() if vgrids_dict[key]['vgrid']
                      in user_vgrid_list]
        for key in vgrids_dict.keys():
            if not vgrids_dict[key]['vgrid'] in vgrid_list:
                del vgrids_dict[key]

    unique_vgrid_list = set(vgrid_list)

    return (vgrids_dict, unique_vgrid_list)


def backup_trigger_files(configuration, vgrid_list):
    """Backup trigger dict in configuration.vgrid_home"""

    status = True
    logger = configuration.logger

    logger.info('==============================================')
    logger.info('Backing up triggerfiles')
    logger.info('==============================================')

    for vgrid in vgrid_list:
        logger.info('----------------------------------------------')
        logger.info('vgrid: %s' % vgrid)
        logger.info('----------------------------------------------')
        trigger_src_filepath = os.path.join(configuration.vgrid_home,
                os.path.join(vgrid, configuration.vgrid_triggers))
        if os.path.exists(trigger_src_filepath):
            trigger_dest_filepath = '%s.preview.%s.bck' \
                % (trigger_src_filepath, time.strftime('%d%m%y-%H%M%S',
                   time.gmtime()))
            logger.info('Backing up trigger file:')
            logger.info("srcfile: '%s'" % trigger_src_filepath)
            logger.info("destfile: '%s'" % trigger_dest_filepath)

            # NOTE: We can _NOT_ move triggers as they are _NOT_ reserved for image previews

            copy(trigger_src_filepath, trigger_dest_filepath)
        else:
            logger.warning("Missing trigger file: '%s'"
                           % trigger_src_filepath)

    return status


def backup_imagesettings_files(configuration, vgrid_list):
    """Backup imagesetting dict in configuration.vgrid_home"""

    status = True
    logger = configuration.logger

    logger.info('==============================================')
    logger.info('Backing up imagesettings files')
    logger.info('==============================================')

    for vgrid in vgrid_list:
        logger.info('----------------------------------------------')
        logger.info('vgrid: %s' % vgrid)
        logger.info('----------------------------------------------')
        imagesettings_src_filepath = \
            os.path.join(configuration.vgrid_home, os.path.join(vgrid,
                         configuration.vgrid_imagesettings))
        if os.path.exists(imagesettings_src_filepath):
            imagesettings_dest_filepath = '%s.preview.%s.bck' \
                % (imagesettings_src_filepath,
                   time.strftime('%d%m%y-%H%M%S', time.gmtime()))
            logger.info("srcfile: '%s'" % imagesettings_src_filepath)
            logger.info("destfile: '%s'" % imagesettings_dest_filepath)
            move(imagesettings_src_filepath,
                 imagesettings_dest_filepath)
        else:
            logger.warning("Missing imagesettings file: '%s'"
                           % imagesettings_src_filepath)

    return status


def backup_paraview_links(configuration, vgrid_list):
    """Backup paraview_links in configuration.paraview_home"""

    status = True
    logger = configuration.logger

    logger.info('==============================================')
    logger.info('Backing up paraview links')
    logger.info('==============================================')

    for vgrid in vgrid_list:
        logger.info('----------------------------------------------')
        logger.info('vgrid: %s' % vgrid)
        logger.info('----------------------------------------------')
        paraview_link_src_filepath = \
            os.path.join(configuration.vgrid_home,
                         os.path.join(configuration.paraview_home,
                         os.path.join('worker', vgrid)))
        if os.path.exists(paraview_link_src_filepath):
            paraview_link_dest_filepath = '%s.preview.%s.bck' \
                % (paraview_link_src_filepath,
                   time.strftime('%d%m%y-%H%M%S', time.gmtime()))
            logger.info("srcfile: '%s'" % paraview_link_src_filepath)
            logger.info("destfile: '%s'" % paraview_link_dest_filepath)
            move(paraview_link_src_filepath,
                 paraview_link_dest_filepath)
        else:
            logger.warning("Missing paraview link: '%s'"
                           % paraview_link_src_filepath)

    return status


def get_update_trigger_dict_and_check_for_unique_clientid(configuration,
        vgrids_dict):
    """Return trigger dict with entries needed for trigger update
    We can't currently handle updates for imagesettings 
    with different client_id's per directory. 

    NOTE: A directory has one associated client_id per extension
    """

    result = {}
    logger = configuration.logger

    # Check for unique client_id's
    # We need to add client_id to settings table in order to support
    # NON unique client_ids for the same folder

    logger.info('==============================================')
    logger.info('Generating trigger update dict checking for unique client_id'
                )
    logger.info('==============================================')

    for key in vgrids_dict.keys():
        run_as = {}
        for trigger in vgrids_dict[key]['triggers']:
            rule_id = trigger['rule_id']
            logger.info('rule_id: %s' % rule_id)
            if rule_id != 'system_imagesettings_meta_created' \
                and rule_id != 'system_imagesettings_dir_deleted':
                client_id = trigger['run_as']
                if client_id in run_as:
                    run_as[client_id] += 1
                else:
                    run_as[client_id] = 1

        logger.info('----------------------------------------------')
        logger.info("Imagesetting: '%s'" % key)
        logger.info("vgrid: '%s'" % vgrids_dict[key]['vgrid'])
        logger.info("vgridpath: '%s'" % vgrids_dict[key]['vgridpath'])
        logger.info("run_as: '%s'" % run_as)
        logger.info('----------------------------------------------')

        # Try to find missing 'run_as' in vgrid owners

        if len(run_as.keys()) == 0:
            owner_id = get_valid_vgrid_owner_id(configuration,
                    vgrids_dict[key]['vgrid'])
            if owner_id is not None:
                run_as[owner_id] = 1
                logger.warning("Missing trigger, setting 'run_as' to vgrid owner: '%s'"
                                % owner_id)

        if len(run_as.keys()) == 0:
            result = None
            logger.error("Unable to identify trigger owner for '%s'"
                         % key)
            break
        elif len(run_as.keys()) > 1:

            result = None
            logger.error("Triggers for '%s' are not unique: '%s'"
                         % (key, run_as.keys()))
            break

        result[key] = {}
        result[key]['vgrid'] = vgrids_dict[key]['vgrid']
        result[key]['vgridpath'] = vgrids_dict[key]['vgridpath']
        result[key]['run_as'] = run_as

    return result


def remove_triggers(configuration, vgrids_dict):
    """Remove old triggers"""

    status = True
    logger = configuration.logger

    logger.info('==============================================')
    logger.info('Removing triggers')
    logger.info('==============================================')

    triggers_removed = {}

    for key in vgrids_dict.keys():
        vgrid = vgrids_dict[key]['vgrid']
        vgridpath = vgrids_dict[key]['vgridpath']
        logger.info('----------------------------------------------')
        logger.info('Imagesettings: %s' % str(key))
        logger.info('vgrid: %s' % vgrid)
        logger.info('vgridpath: %s' % vgridpath)
        logger.info('----------------------------------------------')

        if vgrid not in triggers_removed:
            triggers_removed[vgrid] = []

        for trigger in vgrids_dict[key]['triggers']:
            rule_id = trigger['rule_id']
            run_as = trigger['run_as']
            logger.info('Removing trigger:')
            logger.info("rule_id: '%s'" % rule_id)
            logger.info("run_as: '%s'" % run_as)

            # Skip image setting triggers that were previously removed,
            # System triggers such as:
            # 'system_imagesettings_meta_created' and
            # 'system_imagesettings_dir_deleted' are represented
            # are present for each settings file in vgrids_dict

            if rule_id in triggers_removed[vgrid]:
                logger.info("Skipping trigger '%s' previously removed from vgrid: '%s'"
                             % (rule_id, vgrid))
            else:
                command = [
                    'python',
                    '%s/fakecgi.py' % MIG_CGI_BIN,
                    '%s/rmvgridtrigger.py' % MIG_CGI_BIN,
                    'POST',
                    'rule_id=%s;vgrid_name=%s;output_format=text'
                        % (rule_id, vgrid),
                    '%s' % run_as,
                    'true',
                    ]
                logger.info(command)
                logger.info('*****************************************************'
                            )
                subprocess_call(command, stdin=open('/dev/null', 'r'))
                logger.info('*****************************************************'
                            )

                triggers_removed[vgrid].append(rule_id)

    return status


def update_backend(configuration, update_dict):
    """Update backend by calling imagepreview.py refresh
    through fakecgi"""

    status = True
    logger = configuration.logger

    logger.info('==============================================')
    logger.info('Updating backend')
    logger.info('==============================================')

    # Refresh previews

    logger.info('----------------------------------------------')
    logger.info('Updating previews')

    if status:
        for key in update_dict.keys():
            vgrid = update_dict[key]['vgrid']
            vgridpath = update_dict[key]['vgridpath']
            run_as = update_dict[key]['run_as']
            logger.info('----------------------------------------------'
                        )
            logger.info('Imagesettings: %s' % str(key))
            logger.info('vgrid: %s' % vgrid)
            logger.info('vgridpath: %s' % vgridpath)
            logger.info('run_as: %s' % run_as)

            if len(run_as.keys()) == 1:
                command = [
                    'python',
                    '%s/fakecgi.py' % MIG_CGI_BIN,
                    '%s/imagepreview.py' % MIG_CGI_BIN,
                    'POST',
                    'action=refresh;path=%s;output_format=text'
                        % vgridpath,
                    '%s' % run_as.keys()[0],
                    'true',
                    ]
                logger.info(command)
                logger.info('*****************************************************'
                            )
                subprocess_call(command, stdin=open('/dev/null', 'r'))
                logger.info('*****************************************************'
                            )

    return status


def main():
    status = True
    configuration = get_configuration_object()
    logger = configuration.logger = get_logger(logging.INFO)

    # Overwrite default logger

    argc = len(sys.argv) - 1
    user_vgrid_list = None
    if argc == 1:
        user_vgrid_list = [vgrid.strip() for vgrid in
                           sys.argv[1].split(',')]
        logger.info('Using custom vgrid_list: %s' % user_vgrid_list)

    vgrids_dict = unpickle(TRIGGER_DICT_FILE, logger)
    update_trigger_dict = None

    if vgrids_dict:
        (vgrids_dict, vgrid_list) = filter_vgrids_dict(configuration,
                vgrids_dict, user_vgrid_list)
    else:
        status = False
        logger.error("Missing vgrid dict file: '%s'"
                     % TRIGGER_DICT_FILE)

    if status:
        status = backup_trigger_files(configuration, vgrid_list)

    if status:
        status = backup_imagesettings_files(configuration, vgrid_list)

    if status:
        status = backup_paraview_links(configuration, vgrid_list)

    if status:
        update_trigger_dict = \
            get_update_trigger_dict_and_check_for_unique_clientid(configuration,
                vgrids_dict)
        if update_trigger_dict is None:
            status = False

    if status:
        status = remove_triggers(configuration, vgrids_dict)

    if status:
        status = update_backend(configuration, update_trigger_dict)

    if status:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())

