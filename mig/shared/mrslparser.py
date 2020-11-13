#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mrslparser - Parse mRSL job descriptions
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Job description parser and validator"""
from __future__ import absolute_import

import os
import time
import types

from mig.shared.base import client_id_dir
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import default_vgrid, any_vgrid, src_dst_sep
from mig.shared.fileio import unpickle, pickle, send_message_to_grid_script
from mig.shared.mrslkeywords import get_keywords_dict as mrsl_get_keywords_dict
from mig.shared.parser import parse as core_parse, check_types
from mig.shared.refunctions import is_runtime_environment
from mig.shared.safeinput import html_escape, valid_path
from mig.shared.vgridaccess import user_vgrid_access

try:
    from mig.shared import arcwrapper
except:
    # Ignore errors and let it crash if ARC is enabled without the lib
    pass


def replace_variables(text, replace_list):
    """Replace all occurrences of variables from replace_list keys in text
    with the corresponding value. replace_list is an ordered list of tuples
    with variable names and their expanded values.
    """
    out = text
    for (key, val) in replace_list:
        out = out.replace(key, val)
    return out


def expand_variables(job_dict):
    """Expand reserved job variables like +JOBID+ and + JOBNAME+ to actual
    values from the job dictionary.
    The expansion is in-place so caller should consider any side effects.
    """
    # Users can specify "special keywords" in all string and list fields.
    # There are two "special keywords" at the moment: +JOBNAME+ and +JOBID+
    # The function replaces these keywords with the runtime assigned jobname
    # and jobid.
    # Please be careful if adding new expansions here:
    # They are expanded *after* parsing and accepting the raw job so they
    # must be safe against abuse. Simple replacement of keywords with
    # constant string values should be safe.
    var_map = [('+JOBID+', job_dict.get('JOB_ID', '+JOBID+')),
               ('+JOBNAME+', job_dict.get('JOBNAME', '+JOBNAME+'))]
    for (key, value) in job_dict.iteritems():
        if isinstance(value, list):
            newlist = []
            for elem in value[:]:
                if type(elem) is tuple:

                    # Environment? tuple

                    (name, val) = elem
                    name = replace_variables(name, var_map)
                    val = replace_variables(val, var_map)
                    env = (name, val)
                    newlist.append(env)
                elif type(elem) is bytes:
                    newlist.append(replace_variables(str(elem),
                                                     var_map))
                else:

                    # elem was not a tuple/string, dont try to replace

                    newlist.append(elem)
            job_dict[key] = newlist
        elif isinstance(value, str):
            job_dict[key] = replace_variables(str(value), var_map)
    return job_dict


def parse(
    localfile_spaces,
    job_id,
    client_id,
    forceddestination,
    outfile='AUTOMATIC',
    workflow_job=None
):
    """Parse job description and optionally write results to parsed mRSL file.
    If outfile is non-empty it is used as destination file, and the keyword
    AUTOMATIC is replaced by the default mrsl dir destination.
    """

    configuration = get_configuration_object()
    logger = configuration.logger
    client_dir = client_id_dir(client_id)

    # return a tuple (bool status, str msg). This is done because cgi-scripts
    # are not allowed to print anything before 'the first two special lines'
    # are printed

    result = core_parse(localfile_spaces)

    external_dict = mrsl_get_keywords_dict(configuration)

    # The mRSL has the right structure check if the types are correct too
    # and inline update the default external_dict entries with the ones
    # from the actual job specification

    (status, msg) = check_types(result, external_dict, configuration)
    if not status:
        return (False, 'Parse failed (typecheck) %s' % msg)

    logger.debug('check_types updated job dict to: %s' % external_dict)

    global_dict = {}

    # Insert the parts from mrslkeywords we need in the rest of the MiG system

    for (key, value_dict) in external_dict.iteritems():
        global_dict[key] = value_dict['Value']

    # We do not expand any job variables yet in order to allow any future
    # resubmits to properly expand job ID.

    vgrid_list = global_dict['VGRID']
    vgrid_access = user_vgrid_access(configuration, client_id)

    # Replace any_vgrid keyword with all allowed vgrids (on time of submit!)

    try:
        any_pos = vgrid_list.index(any_vgrid)
        vgrid_list[any_pos:any_pos] = vgrid_access

        # Remove any additional any_vgrid keywords

        while any_vgrid in vgrid_list:
            vgrid_list.remove(any_vgrid)
    except ValueError:

        # No any_vgrid keywords in list - move along

        pass

    # Now validate supplied vgrids

    for vgrid_name in vgrid_list:
        if not vgrid_name in vgrid_access:
            return (False, """Failure: You must be an owner or member of the
'%s' vgrid to submit a job to it!""" % vgrid_name)

    # Fall back to default vgrid if no vgrid was supplied

    if not vgrid_list:

        # Please note that vgrid_list is a ref to global_dict list
        # so we must modify and not replace with a new list!

        vgrid_list.append(default_vgrid)

    # convert specified runtime environments to upper-case and verify they
    # actually exist

    # do not check runtime envs if the job is for ARC (submission will
    # fail later)
    if global_dict.get('JOBTYPE', 'unset') != 'arc' \
            and 'RUNTIMEENVIRONMENT' in global_dict:
        re_entries_uppercase = []
        for specified_re in global_dict['RUNTIMEENVIRONMENT']:
            specified_re = specified_re.upper()
            re_entries_uppercase.append(specified_re)
            if not is_runtime_environment(specified_re, configuration):
                return (False, """You have specified a non-nexisting runtime
environment '%s', therefore the job can not be run on any resources.""" %
                        specified_re)
        if global_dict.get('MOUNT', []) != []:
            if configuration.res_default_mount_re.upper()\
                    not in re_entries_uppercase:
                re_entries_uppercase.append(
                    configuration.res_default_mount_re.upper())

        global_dict['RUNTIMEENVIRONMENT'] = re_entries_uppercase

    if global_dict.get('JOBTYPE', 'unset').lower() == 'interactive':

        # if jobtype is interactive append command to create the notification
        # file .interactivejobfinished that breaks the infinite loop waiting
        # for the interactive job to finish and send output files to the MiG
        # server

        global_dict['EXECUTE'].append('touch .interactivejobfinished')

    # put job id and name of user in the dictionary

    global_dict['JOB_ID'] = job_id
    global_dict['USER_CERT'] = client_id

    # if workflow job mark
    if workflow_job:
        global_dict['WORKFLOW_TRIGGER_ID'] = workflow_job['trigger_id']
        global_dict['WORKFLOW_TRIGGER_PATH'] = workflow_job['trigger_path']
        global_dict['WORKFLOW_TRIGGER_TIME'] = workflow_job['trigger_time']
        global_dict['WORKFLOW_PATTERN_ID'] = workflow_job['patter_id']
        global_dict['WORKFLOW_PATTERN_NAME'] = workflow_job['pattern_name']
        global_dict['WORKFLOW_RECIPES'] = workflow_job['recipes']

    # mark job as received

    global_dict['RECEIVED_TIMESTAMP'] = time.gmtime()
    global_dict['STATUS'] = 'PARSE'
    if forceddestination:
        global_dict['FORCEDDESTINATION'] = forceddestination
        if 'UNIQUE_RESOURCE_NAME' in forceddestination:
            global_dict["RESOURCE"] = "%(UNIQUE_RESOURCE_NAME)s_*" % \
                                      forceddestination
        if 'RE_NAME' in forceddestination:
            re_name = forceddestination['RE_NAME']

            # verify the verifyfiles entries are not modified (otherwise RE creator
            # can specify multiple ::VERIFYFILES:: keywords and give the entries
            # other names (perhaps overwriting files in the home directories of
            # resource owners executing the testprocedure)

            for verifyfile in global_dict['VERIFYFILES']:
                verifytypes = ['.status', '.stderr', '.stdout']
                found = False
                for verifytype in verifytypes:
                    if verifyfile == 'verify_runtime_env_%s%s' % (re_name,
                                                                  verifytype):
                        found = True
                if not found:
                    return (False, '''You are not allowed to specify the
::VERIFY:: keyword in a testprocedure, it is done automatically''')

    # normalize any path fields to be taken relative to home

    for field in ('INPUTFILES', 'OUTPUTFILES', 'EXECUTABLES',
                  'VERIFYFILES'):
        if field not in global_dict:
            continue
        normalized_field = []
        for line in global_dict[field]:
            normalized_parts = []
            line_parts = line.split(src_dst_sep)
            if len(line_parts) < 1 or len(line_parts) > 2:
                return (False,
                        '%s entries must contain 1 or 2 space-separated items'
                        % field)
            for part in line_parts:

                # deny leading slashes i.e. force absolute to relative paths

                part = part.lstrip('/')
                if part.find('://') != -1:

                    # keep external targets as is - normpath breaks '://'

                    normalized_parts.append(part)
                    check_path = part.split('/')[-1]
                else:

                    # normalize path to avoid e.g. './' which breaks dir
                    # handling on resource

                    check_path = os.path.normpath(part)
                    normalized_parts.append(check_path)
                try:
                    valid_path(check_path)
                except Exception as exc:
                    return (False, 'Invalid %s part in %s: %s' %
                            (field, html_escape(part), exc))
            normalized_field.append(' '.join(normalized_parts))
        global_dict[field] = normalized_field

    # if this is an ARC job (indicated by a flag), check proxy existence
    # and lifetime. grid_script will submit the job directly.

    if global_dict.get('JOBTYPE', 'unset') == 'arc':
        if not configuration.arc_clusters:
            return (False, 'No ARC support!')

        logger.debug('Received job for ARC.')
        user_home = os.path.join(configuration.user_home, client_dir)
        try:
            session = arcwrapper.Ui(user_home)
            timeleft = session.getProxy().getTimeleft()
            req_time = int(global_dict.get('CPUTIME', '0'))
            logger.debug('CPU time (%s), proxy lifetime (%s)'
                         % (req_time, timeleft))
            if timeleft < req_time:
                return (False, 'Proxy time shorter than requested CPU time')

        except arcwrapper.ARCWrapperError as err:
            return (False, err.what())
        except arcwrapper.NoProxyError as err:
            return (False, 'No Proxy found: %s' % err.what())
        except Exception as err:
            return (False, err.__str__())

    # save file
    if outfile == 'AUTOMATIC':
        filename = \
            os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                         client_dir, job_id + '.mRSL'))
    else:
        filename = outfile

    if not pickle(global_dict, filename, logger):
        return (False, 'Fatal error: Could not write %s' % filename)

    if not outfile == 'AUTOMATIC':

        # an outfile was specified, so this is just for testing - dont tell
        # grid_script

        return (True, '')

    # tell 'grid_script'

    message = 'USERJOBFILE %s/%s\n' % (client_dir, job_id)

    if not send_message_to_grid_script(message, logger, configuration):
        return (False, '''Fatal error: Could not get exclusive access or write
to %s''' % configuration.grid_stdin)

    if forceddestination and 'RE_NAME' in forceddestination:

        # add job_id to runtime environment verification history

        unique_resource_name = forceddestination['UNIQUE_RESOURCE_NAME']
        re_name = forceddestination['RE_NAME']

        resource_config_filename = configuration.resource_home\
            + unique_resource_name + '/config'

        # open resource config

        resource_config = unpickle(resource_config_filename, logger)
        if not resource_config:
            logger.error('error unpickling resource config')
            return (False, 'error unpickling resource config')

        dict_entry = (job_id, client_id)

        # add entry to runtime verification history

        if 'RUNTVERIFICATION' not in resource_config:
            resource_config['RUNTVERIFICATION'] = \
                {re_name: [dict_entry]}
        else:
            before_runt_dict = resource_config['RUNTVERIFICATION']
            if re_name not in before_runt_dict:
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
        from mig.shared.functionality.vncsession import main
        return main(client_id, {})

    # print global_dict

    # phew, we made it. Everything ok

    return (True, '')
