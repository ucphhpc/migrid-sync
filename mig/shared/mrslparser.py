#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mrslparser - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import os
import time

import shared.mrslkeywords as mrslkeywords
import shared.parser as parser
from shared.refunctions import is_runtime_environment
from shared.vgrid import vgrid_is_owner_or_member, user_allowed_vgrids, \
    vgrid_is_default, any_vgrid, default_vgrid
from shared.fileio import unpickle, pickle, send_message_to_grid_script
from shared.conf import get_configuration_object
from shared.useradm import client_id_dir


def parse(
    localfile_spaces,
    job_id,
    client_id,
    forceddestination,
    outfile='not_specified',
    ):

    configuration = get_configuration_object()
    logger = configuration.logger
    client_dir = client_id_dir(client_id)

    # return a tuple (bool status, str msg). This is done because cgi-scripts are not allowed to print anything
    # before 'the first two special lines' are printed

    result = parser.parse(localfile_spaces)

    external_dict = mrslkeywords.get_keywords_dict(configuration)

    # The mRSL has the right structure check if the types are correct too
    # and inline update the default external_dict entries with the ones
    # from the actual job specification

    (status, msg) = parser.check_types(result, external_dict,
            configuration)
    if not status:
        return (False, 'Parse failed (typecheck) %s' % msg)

    logger.debug('check_types updated job dict to: %s' % external_dict)

    global_dict = {}

    # Insert the parts from mrslkeywords we need in the rest of the MiG system

    for (key, value_dict) in external_dict.iteritems():
        global_dict[key] = value_dict['Value']

    vgrid_list = global_dict['VGRID']
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Replace ANY wildcard with all allowed vgrids (on time of submit!)

    try:
        any_pos = vgrid_list.index(any_vgrid)
        vgrid_list[any_pos:any_pos] = allowed_vgrids

        # Remove any additional ANY wildcards

        while any_vgrid in vgrid_list:
            vgrid_list.remove(any_vgrid)
    except ValueError:

        # No ANY wildcards in list - move along

        pass

    # Now validate supplied vgrids

    for vgrid_name in vgrid_list:
        if not vgrid_name in allowed_vgrids:
            return (False,
                    "Failure: You must be an owner or member of the '%s' vgrid to submit a job to it!"
                     % vgrid_name)

    # Fall back to default vgrid if no vgrid was supplied

    if not vgrid_list:

        # Please note that vgrid_list is a ref to global_dict list
        # so we must modify and not replace with a new list!

        vgrid_list.append(default_vgrid)

    # convert specified runtime environments to upper-case and verify they actually exist

    if global_dict.has_key('RUNTIMEENVIRONMENT'):
        re_entries_uppercase = []
        for specified_re in global_dict['RUNTIMEENVIRONMENT']:
            specified_re = specified_re.upper()
            re_entries_uppercase.append(specified_re)
            if not is_runtime_environment(specified_re, configuration):
                return (False,
                        "You have specified a non-nexisting runtime environment '%s', therefore the job can not be run on any resources."
                         % specified_re)

        global_dict['RUNTIMEENVIRONMENT'] = re_entries_uppercase

    if global_dict.get('JOBTYPE', 'unset').lower() == 'interactive':

        # if jobtype is interactive append command to create the notification file .interactivejobfinished that breaks
        # the infinite loop waiting for the interactive job to finish and send output files to the MiG server

        global_dict['EXECUTE'].append('touch .interactivejobfinished')

    # put job id and name of user in the dictionary

    global_dict['JOB_ID'] = job_id
    global_dict['USER_CERT'] = client_id

    # mark job as received

    global_dict['RECEIVED_TIMESTAMP'] = time.gmtime()
    global_dict['STATUS'] = 'PARSE'
    if forceddestination and forceddestination.has_key('RE_NAME'):

        # global_dict["FORCEDDESTINATION"] = forceddestination["UNIQUE_RESOURCE_NAME"]

        global_dict['FORCEDDESTINATION'] = forceddestination
        re_name = forceddestination['RE_NAME']

        # verify the verifyfiles entries are not modified (otherwise RE creator can specify multiple
        # ::VERIFYFILES:: keywords and give the entries other names (perhaps overwriting files in
        # the home directories of resource owners executing the testprocedure)

        for verifyfile in global_dict['VERIFYFILES']:
            verifytypes = ['.status', '.stderr', '.stdout']
            found = False
            for verifytype in verifytypes:
                if verifyfile == 'verify_runtime_env_%s%s' % (re_name,
                        verifytype):
                    found = True
            if not found:
                return (False,
                        'You are not allowed to specify the ::VERIFY:: keyword in a testprocedure, it is done automatically'
                        )

    # normalize any path fields to be taken relative to home

    for field in ('INPUTFILES', 'OUTPUTFILES', 'EXECUTABLES',
                  'VERIFYFILES'):
        if not global_dict.has_key(field):
            continue
        normalized_field = []
        for line in global_dict[field]:
            normalized_parts = []
            for part in line.split():

                # deny leading slashes i.e. force absolute to relative paths

                part = part.lstrip('/')
                if part.find('://') != -1:

                    # keep external targets as is - normpath breaks '://'

                    normalized_parts.append(part)
                else:

                    # normalize path to avoid e.g. './' which breaks dir handling on resource

                    normalized_parts.append(os.path.normpath(part))
            normalized_field.append(' '.join(normalized_parts))
        global_dict[field] = normalized_field

    # replace special keywords

    replaced_dict = parser.replace_special(global_dict)

    # save file

    if outfile == 'not_specified':
        filename = \
            os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                            client_dir, job_id + '.mRSL'))
    else:
        filename = outfile

    if not pickle(replaced_dict, filename, logger):
        return (False, 'Fatal error: Could not write %s' % filename)

    if not outfile == 'not_specified':

        # an outfile was specified, so this is just for testing - dont tell grid_script

        return (True, '')

    # tell 'grid_script'

    message = 'USERJOBFILE %s/%s\n' % (client_dir, job_id)

    if not send_message_to_grid_script(message, logger, configuration):
        return (False,
                'Fatal error: Could not get exclusive access or write to %s'
                 % configuration.grid_stdin)

    if forceddestination and forceddestination.has_key('RE_NAME'):

        # add job_id to runtime environment verification history

        unique_resource_name = forceddestination['UNIQUE_RESOURCE_NAME']
        re_name = forceddestination['RE_NAME']

        resource_config_filename = configuration.resource_home\
             + unique_resource_name + '/config'

        # open resource config

        resource_config = unpickle(resource_config_filename, logger)
        if not resource_config:
            logger.error('error unpickling resource config')
            return False

        dict_entry = (job_id, client_id)

        # add entry to runtime verification history

        if not resource_config.has_key('RUNTVERIFICATION'):
            resource_config['RUNTVERIFICATION'] = \
                {re_name: [dict_entry]}
        else:
            before_runt_dict = resource_config['RUNTVERIFICATION']
            if not before_runt_dict.has_key(re_name):
                before_runt_dict[re_name] = [].append(dict_entry)
            else:
                before_runt_dict[re_name].append(dict_entry)

        # save dict with added entry

        if not pickle(resource_config, resource_config_filename,
                      logger):
            return (False,
                    'Fatal error pickling resource config: Could not write %s'
                     % filename)

    if global_dict.get('JOBTYPE', 'unset').lower() == 'interactive':
        from shared.functionality.vncsession import main
        return main(client_id, {})

    # print global_dict

    # phew, we made it. Everything ok

    return (True, '')


