#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobfeasibility - capability of the submitted job to be executed
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Validation of job specifications against available resources - Returns a
'Job Readiness Condition' and a dictionary containing error descriptions.
Via the job_cond colors in the configuration each color can specify an
arbitrary number of validations that the particular level has to pass. Thus
the granularity of the validation at each level can be customized.
All or individual validations can be omitted through configuration.
Each job_cond color is a subset of the one above it; in numerical ascension
i.e. job_cond orange is a subset of job_cond yellow.
"""

from __future__ import absolute_import

import os
from time import time

from mig.shared.base import client_id_dir
from mig.shared.defaults import default_vgrid, keyword_all
from mig.shared.mrslkeywords import get_keywords_dict
from mig.shared.resource import anon_resource_id, list_resources, \
    anon_to_real_res_map
from mig.shared.resconfkeywords import get_resource_keywords
from mig.shared.safeinput import is_valid_simple_email
from mig.shared.vgrid import vgrid_resources
from mig.shared.vgridaccess import get_vgrid_map, get_resource_map, \
    real_to_anon_res_map, user_vgrid_access, CONF, RESOURCES, ALLOW
from functools import reduce

# Condition colors in descending order (order is essential!)

(RED, ORANGE, YELLOW, GREEN) = ('RED', 'ORANGE', 'YELLOW', 'GREEN')
job_cond_colors = (RED, ORANGE, YELLOW, GREEN)

__all__ = ['job_feasibility']


def job_feasibility(configuration, job):
    """Returns a feasibility message dictionary for the submitted job"""

    job_cond = {}
    errors = {}
    message = {}
    suggestion = ''

    if keyword_all in configuration.skip_validation:
        job_cond['JOB_COND'] = GREEN
        message['verdict'] = 'All feasibility tests are disabled!'
        message['color'] = job_cond['JOB_COND']
        message['icon'] = get_job_cond_color_icon(job_cond['JOB_COND'])
        return message

    (job_cond, errors, vgrid_resource_dict) = standard_implementation(
        configuration, job)

    if configuration.enable_suggest and \
            threshold_color_to_value(job_cond['JOB_COND']) < \
            threshold_color_to_value(configuration.suggest_threshold):
        suggestion = suggestion_envelope(configuration, job, job_cond, errors,
                                         vgrid_resource_dict)

    error_desc = assemble_errors(job_cond, errors)
    job_cond_color = job_cond['JOB_COND']

    if job_cond_color == GREEN:
        verdict = 'Job is feasible'
    else:
        verdict = 'The job is not feasible due to the following condition(s):'

    message['verdict'] = verdict
    message['color'] = job_cond_color
    message['icon'] = get_job_cond_color_icon(job_cond['JOB_COND'])
    if suggestion:
        message['suggestion'] = suggestion
    if error_desc:
        message['error_desc'] = error_desc

    return message


def standard_implementation(configuration, job):
    """Finding vgrids and resources to determine the feasibility of a job"""

    # {vgrid: [res, res, ..., res], ..., vgrid: [res, res, ..., res]}

    vgrid_resource_dict = {}
    vgrids = []
    resources = set()
    job_cond = {}
    errors = {}

    vgrids = validate_vgrid(configuration, job, errors)
    if not vgrids:
        return none_available(job_cond, errors, 'VGRID', fake_dict=True)

    for vgrid in vgrids:
        resources = set(validate_resource(configuration, job, vgrid, errors))
        vgrid_resource_dict[vgrid] = list(resources)

    (job_cond, errors) = validate(configuration, job, vgrid_resource_dict,
                                  job_cond, errors)
    return (job_cond, errors, vgrid_resource_dict)


def suggestion_envelope(configuration, job, job_cond, errors,
                        vgrid_resource_dict):
    """Handles the suggesting functionality."""

    (suggest_job_cond, suggest_errors) = suggestion_implementation(
        configuration, job, job_cond.copy(), errors.copy(),
        vgrid_resource_dict)

    suggestion = 'Suggesting in effect. '

    if threshold_color_to_value(job_cond['JOB_COND']) < \
        threshold_color_to_value(suggest_job_cond['JOB_COND']) and \
        (suggest_job_cond.get('vgrid_suggested', False) or
            suggest_job_cond.get('resource_suggested', False)):
        suggestion += assemble_suggest_msg(job_cond)
    else:
        suggestion += \
            'Suggestion ignored as the resulting feasibility was worse.'

    return suggestion


def suggestion_implementation(configuration, job, job_cond, errors,
                              vgrid_resource_dict):
    """Finding suitable alternate vgrids and resources to suggest
    to determine the feasibility of a job.
    """

    vgrids = list(vgrid_resource_dict)
    all_resources = list(vgrid_resource_dict.values())
    resources = [res for sublist in all_resources for res in sublist]
    vgrid_resource_dict.clear()

    comp_vgrids = complement_vgrids(configuration, job, vgrids)
    if not comp_vgrids:
        return none_available(job_cond, errors, 'VGRID', True)

    job_cond.clear()
    errors.clear()

    job_cond['vgrid_suggested'] = True

    for comp_vgrid in comp_vgrids:
        comp_resources = complement_resources(configuration, job, comp_vgrid,
                                              resources)
        if not comp_resources:
            return none_available(job_cond, errors, 'RESOURCE', True)

        vgrid_resource_dict[comp_vgrid] = list(comp_resources)

    job_cond['resource_suggested'] = True

    return validate(configuration, job, vgrid_resource_dict, job_cond, errors)


def validate(configuration, job, vgrid_resource_map, job_cond, errors):
    """Validates the readiness condition of a submitted job in respect to the
    requested specifications of vgrid, resource etc.
    """

    best_job_cond = {}
    best_job_cond['JOB_COND'] = RED
    best_errors = errors
    found_best = False
    other_errors = {}

    # Avoid repeated get_resource_map calls for every single resource

    resource_map = get_resource_map(configuration)
    for (vgrid, resources) in vgrid_resource_map.items():

        if best_job_cond['JOB_COND'] == GREEN:
            break

        for resource_id in resources:

            resource = get_resource_configuration(
                configuration, resource_id, resource_map)

            # vgrid_resource_map may contain e.g. deleted resources

            if not resource:
                continue

            # Check resource availability

            job_cond['REGISTERED'] = validate_resource_seen(configuration,
                                                            resource, errors,
                                                            resource_id)
            job_cond['SEEN_WITHIN_X'] = \
                validate_resource_seen_within_x_hours(configuration, resource,
                                                      errors, resource_id)

            # Check mRSL requested specs

            job_cond['ARCHITECTURE'] = validate_architecture(configuration,
                                                             job, resource,
                                                             errors)
            job_cond['CPUCOUNT'] = validate_cpucount(configuration, job,
                                                     resource, errors)
            job_cond['CPUTIME'] = validate_cputime(configuration, job,
                                                   resource, errors)
            job_cond['DISK'] = validate_disk(configuration, job, resource,
                                             errors)
            job_cond['JOBTYPE'] = validate_jobtype(configuration, job,
                                                   resource, errors)
            job_cond['MAXPRICE'] = validate_maxprice(configuration, job,
                                                     resource, errors)
            job_cond['MEMORY'] = validate_memory(configuration, job, resource,
                                                 errors)
            job_cond['NODECOUNT'] = validate_nodecount(configuration, job,
                                                       resource, errors)
            job_cond['PLATFORM'] = validate_platform(configuration, job,
                                                     resource, errors)
            job_cond['RETRIES'] = validate_retries(configuration, job, errors)
            job_cond['RUNTIMEENVIRONMENT'] = validate_runtimeenvironment(
                configuration, job, resource, errors)
            job_cond['SANDBOX'] = validate_sandbox(configuration, job,
                                                   resource, errors)

            job_cond['suggested_vgrid'] = vgrid
            job_cond['suggested_resource'] = anon_resource_id(resource_id,
                                                              False)

            set_pass_level(configuration, job_cond)

            if threshold_color_to_value(job_cond['JOB_COND']) >= \
                    threshold_color_to_value(best_job_cond['JOB_COND']):
                if not found_best or (len(errors) <= len(best_errors)):
                    found_best = True
                    best_job_cond = job_cond.copy()
                    best_errors = errors.copy()

                    if best_job_cond['JOB_COND'] == GREEN:
                        break

            job_cond.clear()
            errors.clear()

    # Run resource independent checks only once

    job_cond['INPUTFILES'] = validate_inputfiles(configuration, job,
                                                 other_errors)
    job_cond['EXECUTABLES'] = validate_executables(configuration, job,
                                                   other_errors)
    job_cond['VERIFYFILES'] = validate_verifyfiles(configuration, job,
                                                   other_errors)
    job_cond['NOTIFY'] = validate_notify(configuration, job, other_errors)

    if not found_best:
        best_job_cond['RESOURCE'] = False
        best_errors['RESOURCE'] = 'No valid/allowed resources available.'
    else:
        best_job_cond.update(job_cond)

    if other_errors:
        best_errors.update(other_errors)
        if best_job_cond['JOB_COND'] == GREEN:
            best_job_cond['JOB_COND'] = YELLOW
    return (best_job_cond, best_errors)


#
# ## Validation functions ##
#


def validate_architecture(configuration, job, resource, errors):
    """Validates job request vs. what resource provides; should be =="""

    return validate_str_case(configuration, job, resource, errors,
                             'ARCHITECTURE', True)


def validate_cpucount(configuration, job, resource, errors):
    """Validates job request vs. resource limit of cpus; should be <="""

    return validate_int_case(configuration, job, resource, errors, 'CPUCOUNT')


def validate_cputime(configuration, job, resource, errors):
    """Validates job request vs. resource limit of cpu time; should be <="""

    return validate_int_case(configuration, job, resource, errors, 'CPUTIME')


def validate_disk(configuration, job, resource, errors):
    """Validates job request vs. resource limit of disk space; should be <="""

    return validate_int_case(configuration, job, resource, errors, 'DISK',
                             True)


def validate_executables(configuration, job, errors):
    """Validates the presense of specific local/remote files."""

    return validate_files(configuration, job, errors, 'EXECUTABLES')


def validate_inputfiles(configuration, job, errors):
    """Validates the presense of specific local/remote files."""

    return validate_files(configuration, job, errors, 'INPUTFILES')


def validate_jobtype(configuration, job, resource, errors):
    """Validates job request vs. what resource provides; should be =="""

    if skip_validation(configuration, job, 'JOBTYPE', resource):
        return True

    job_value = job['JOBTYPE'].upper()
    res_value = resource['JOBTYPE'].upper()

    # 1st term matches 'all'
    # 2nd conjunction is due to 'batch' being a subset of 'bulk'
    # 3rd term is the general case

    if not ((job_value == keyword_all) or
            (job_value == 'batch' and res_value == 'bulk') or
            (job_value == res_value)):
        errors['JOBTYPE'] = std_err_desc(job_value, res_value)

    return 'JOBTYPE' not in errors


def validate_maxprice(configuration, job, resource, errors):
    """Validates job max vs. resource min price to execute; should be <="""

    if skip_validation(configuration, job, 'MAXPRICE'):
        return True

    # The economy is not yet enforced, so until then this is just for
    # completeness

    return True


def validate_memory(configuration, job, resource, errors):
    """Validates job request vs. resource limit of memory; should be <="""

    return validate_int_case(configuration, job, resource, errors, 'MEMORY')


def validate_nodecount(configuration, job, resource, errors):
    """Validates job request vs. resource limit of nodes; should be <="""

    return validate_int_case(configuration, job, resource, errors,
                             'NODECOUNT')


def validate_notify(configuration, job, errors):
    """Validates job specified vs. syntactic correctness"""

    if skip_validation(configuration, job, 'NOTIFY'):
        return True

    # Lightweight version of shared/notification.notify_user() only validating
    # syntax of notify addreses

    job_value = job['NOTIFY']
    syntax_is_valid = True
    for notify_line in job_value:

        if not syntax_is_valid:
            errors['NOTIFY'] = std_err_desc(job_value)
            break

        supported_im_protocols = configuration.notify_protocols
        email_keyword_list = ['mail', 'email']

        notify_line_colon_split = notify_line.split(':', 1)
        notify_line_first_part = notify_line_colon_split[0].strip()

        if notify_line_first_part in supported_im_protocols:
            # There is no validation of IM-addresses. See comment in
            # shared/notification.notify_user()
            continue

        elif notify_line_first_part in email_keyword_list:
            recipients = notify_line.replace('%s: '
                                             % notify_line_first_part,
                                             '').strip()

            if recipients.strip().upper() in ['SETTINGS', '']:
                continue
            else:
                for recipient in recipients:
                    if not syntax_is_valid:
                        errors['NOTIFY'] = std_err_desc(job_value)
                        break
                    else:
                        syntax_is_valid = is_valid_simple_email(recipient)

        else:
            syntax_is_valid = False

    return 'NOTIFY' not in errors


def validate_platform(configuration, job, resource, errors):
    """Validates job request vs. resource available of platforms;
    should be ==
    """

    return validate_str_case(configuration, job, resource, errors, 'PLATFORM',
                             True)


def validate_resource(configuration, job, vgrid, errors):
    """Returns a list of user specified resources that are allowed.
    A job submitted to a VGrid must be executed by a resource from
    that VGrid.
    """

    allowed_resources = set()
    if vgrid == default_vgrid:
        allowed_resources = set(default_vgrid_resources(configuration))
    else:
        (status, vgrid_res) = vgrid_resources(vgrid, configuration)
        if not status:
            vgrid_res = []
        allowed_resources = set(vgrid_res)

    if skip_validation(configuration, job, 'RESOURCE'):

        # all allowed, possibly empty

        return list(allowed_resources)

    specified_resources = anon_to_real_resources(configuration,
                                                 job['RESOURCE'])

    not_allowed = specified_resources.difference(allowed_resources)
    if not_allowed:
        anon_not_allowed = real_to_anon_resources(configuration, not_allowed)
        errors['RESOURCE'] = \
            'The following resources are illegal for VGrid %s:, %s' \
            % (vgrid, list(anon_not_allowed))

    if not allowed_resources.intersection(specified_resources):

        # all allowed, possibly []

        return list(allowed_resources)
    else:

        # validated specifed and allowed

        return list(allowed_resources.intersection(specified_resources))


def validate_retries(configuration, job, errors):
    """Validates job request vs. scheduler limit; should be <="""

    if skip_validation(configuration, job, 'RETRIES'):
        return True

    job_value = int(job['RETRIES'])
    scheduler_value = configuration.job_retries

    if job_value < 0 or not job_value <= scheduler_value:
        errors['RETRIES'] = 'Job/Scheduler values: %s / %s' \
            % (job_value, scheduler_value)

    return 'RETRIES' not in errors


def validate_runtimeenvironment(configuration, job, resource, errors):
    """Validates job request vs. resource available runtimeenvironments;
    should be ==
    """

    if skip_validation(configuration, job, 'RUNTIMEENVIRONMENT', resource):
        return True

    # Validation code taken from mig/server/scheduler.job_fits_resource()
    # It has been slightly modified to fit the validation context.

    runtime_env_errors = []

    for job_runtimeenv in job['RUNTIMEENVIRONMENT']:
        found = False

        for resource_runtimeenv in resource['RUNTIMEENVIRONMENT']:
            if job_runtimeenv == resource_runtimeenv[0]:
                found = True
                break

        if not found:
            res_envs = [env[0] for env in resource['RUNTIMEENVIRONMENT']]
            runtime_env_errors.append('Job/Resource values: %s / %s'
                                      % (job_runtimeenv,
                                         ' '.join(res_envs)))

    if runtime_env_errors:
        errors['RUNTIMEENVIRONMENT'] = '; \n'.join(runtime_env_errors)

    return 'RUNTIMEENVIRONMENT' not in errors


def validate_verifyfiles(configuration, job, errors):
    """Validates the presense of specific local files."""

    return validate_files(configuration, job, errors, 'VERIFYFILES', True)


def validate_vgrid(configuration, job, errors):
    """Returns a list of user specified vgrids that are allowed."""

    vgrid_access = set(user_vgrid_access(configuration, job['USER_CERT']))

    if skip_validation(configuration, job, 'VGRID'):

        # all allowed, possibly empty

        return list(vgrid_access)

    specified_vgrids = set(job['VGRID'])

    not_allowed = specified_vgrids.difference(vgrid_access)
    if not_allowed:
        errors['VGRID'] = \
            'The following VGrids are not allowed' \
            + ' for the current user:, %s' \
            % (not_allowed)

    if not vgrid_access.intersection(specified_vgrids):

        # all allowed, possibly []

        return list(vgrid_access)
    else:

        # validated specifed and allowed

        return list(vgrid_access.intersection(specified_vgrids))


def validate_sandbox(configuration, job, resource, errors):
    """Do not schedule non-sandbox jobs on a sandbox resource."""

    if skip_validation(configuration, job, 'SANDBOX', resource):
        return True

    job_value = bool(job['SANDBOX'])
    res_value = bool(resource['SANDBOX'])

    # do not allow non-sandbox jobs on a sandbox resource
    # sandbox jobs on non-sandbox resources are ok, however

    if not job_value and res_value:
        errors['SANDBOX'] = std_err_desc(job_value, res_value)

    return 'SANDBOX' not in errors


def validate_resource_seen(configuration, resource, errors, resource_id):
    """Has the resource been registered at some point?"""

    if in_skip_list(configuration, 'REGISTERED'):
        return True

    # use if/when LAST_SEEN and FIRST_SEEN are moved to shared/scheduling.py

#    elif resource.has_key('FIRST_SEEN') and bool(resource['FIRST_SEEN']):
#        resource_seen = now - resource['FIRST_SEEN']

    all_valid_resources = list_resources(configuration.resource_home, True)

    if not resource_id in all_valid_resources:
        errors['REGISTERED'] = 'The resource %s is not available' \
            % (resource_id)

    return 'REGISTERED' not in errors


def validate_resource_seen_within_x_hours(configuration, resource, errors,
                                          resource_id):
    """Has the resource been seen within the last x hours?"""

    if in_skip_list(configuration, 'SEEN_WITHIN_X'):
        return True

    # use if/when LAST_SEEN and FIRST_SEEN are moved to shared/scheduling.py

#    if resource.has_key('LAST_SEEN') and bool(resource['LAST_SEEN']):
#        resource_seen = now - resource['LAST_SEEN']
#    elif resource.has_key('FIRST_SEEN') and bool(resource['FIRST_SEEN']):
#        resource_seen = now - resource['FIRST_SEEN']

    resource_seen = time() - exe_last_seen(configuration, resource_id)[1]
    hours = int(configuration.resource_seen_within_hours)

    if 'REGISTERED' in errors or (hours * 3600 <= resource_seen):
        errors['SEEN_WITHIN_X'] = \
            'The resource %s has not been seen within the last %i hour(s).' \
            % (resource_id, hours)

    return 'SEEN_WITHIN_X' not in errors


def validate_files(configuration, job, errors, mrsl_attribute,
                   verify_file=False):
    """Validates the presense of specific input-, execute- and verify-files
    at local and remote locations.
    The optional verify_file option is used to tell the check that it is
    called for the VERIFYFILES keyword. If set the file extension must match
    one of our status file extensions (status/stdout/stderr).
    """

    if skip_validation(configuration, job, mrsl_attribute):
        return True

    missing_files = []
    invalid_verify = []

    # file lines may be single src/dst path or separate src dst pair

    src_files = [i.split(' ', 1)[0] for i in job[mrsl_attribute]]
    for filename in src_files:

        configuration.logger.info('checking filename %s' % filename)

        # Extra check for VERIFYFILES to match status extension

        if verify_file and not True in [filename.endswith(i) for i in
                                        ['status', 'stdout', 'stderr']]:
            invalid_verify.append(filename)
            continue

        # Separate local and remote file checks

        if filename.find('://') == -1:
            filename = filename.lstrip('/')
            filename = os.path.normpath(filename)
            abs_path = os.path.join(configuration.user_home,
                                    client_id_dir(job['USER_CERT']),
                                    filename)
            if not os.path.isfile(abs_path):
                missing_files.append(filename)
        else:
            dest_file = '/dev/null'
            # We rely on (py)curl since it supports all our protocols including
            # sftp. Check only first byte to limit overhead for big files.
            configuration.logger.info('checking remote file with pycurl')
            try:
                import pycurl
                curl = pycurl.Curl()
                # Never use proxy
                curl.setopt(pycurl.PROXY, "")
                curl.setopt(pycurl.URL, filename)
                curl.setopt(pycurl.RANGE, '0-0')
                curl.setopt(pycurl.NOBODY, True)
                curl.setopt(pycurl.FOLLOWLOCATION, True)
                curl.setopt(pycurl.MAXREDIRS, 5)
                curl.setopt(pycurl.HEADERFUNCTION, lambda x: None)
                curl.setopt(pycurl.WRITEFUNCTION, lambda x: None)
                curl.perform()
                curl.getinfo(pycurl.RESPONSE_CODE)
                curl_result = curl.getinfo(pycurl.RESPONSE_CODE)
                curl.close()
            except Exception as exc:
                configuration.logger.error('failed to curl check %s : %s'
                                           % (filename, exc))
                curl_result = -1
            configuration.logger.debug('got curl result %d' % curl_result)
            if 200 <= curl_result and curl_result < 300:
                configuration.logger.debug('curl success result %d'
                                           % curl_result)
            else:
                configuration.logger.warning('curl error result %d'
                                             % curl_result)
                missing_files.append(filename)

    if missing_files:
        file_cnt = len(src_files)
        missing_file_cnt = len(missing_files)
        errors[mrsl_attribute] = \
            'The following (%d of %d) files are missing: %s' \
            % (missing_file_cnt, file_cnt, ', '.join(missing_files))
    if verify_file and invalid_verify:
        errors[mrsl_attribute] = \
            'The following verify files are invalid' \
            + ' (must match status ext): %s' \
            % ', '.join(invalid_verify)

    return mrsl_attribute not in errors


def validate_str_case(configuration, job, resource, errors, mrsl_attribute,
                      empty_str=False):
    """Validates job request vs. what resource provides; should be == .
    Automatic fall back to resource conf default value for optional settings.
    """

    if skip_validation(configuration, job, mrsl_attribute, resource):
        return True

    job_value = job[mrsl_attribute].upper()
    if mrsl_attribute in resource:
        res_value = resource[mrsl_attribute].upper()
    else:
        resource_keywords = get_resource_keywords(configuration)
        res_value = resource_keywords[mrsl_attribute]['Value'].upper()

    if empty_str:
        if not job_value == '' and not job_value == res_value:
            errors[mrsl_attribute] = std_err_desc(job_value, res_value)
    else:
        if not job_value == res_value:
            errors[mrsl_attribute] = std_err_desc(job_value, res_value)

    return mrsl_attribute not in errors


def validate_int_case(configuration, job, resource, errors, mrsl_attribute,
                      geq=False):
    """Validates job request vs. resource limit; should be <= or < depending
    on value of parameter qeq.
    """

    if skip_validation(configuration, job, mrsl_attribute, resource):
        return True

    job_value = job[mrsl_attribute]
    res_value = None

    if mrsl_attribute not in resource:

        # Get value from one of the execution nodes

        for execution_node in resource['EXECONFIG']:
            if mrsl_attribute.lower() in execution_node:
                res_value = execution_node[mrsl_attribute.lower()]
                if job_value <= res_value:
                    break
    else:
        res_value = resource[mrsl_attribute]

    if geq:
        if not job_value >= 0:
            errors[mrsl_attribute] = 'Value %i < 0' % (job_value)
    else:
        if not job_value > 0:
            errors[mrsl_attribute] = 'Value %i <= 0' % (job_value)

    if not job_value <= res_value:
        errors[mrsl_attribute] = std_err_desc(job_value, res_value)

    return mrsl_attribute not in errors


#
# ## Utility functions ##
#


def set_pass_level(configuration, job_cond):
    """Updates the job_cond level achieved with the current resource/vgrid.
    Failing a particular level implies passing the previous level, lowest
    level being the exception.
    """

    job_color = RED
    for color in job_cond_colors:
        if pass_job_cond(configuration, job_cond, color):
            job_color = color
        else:
            break
    job_cond['JOB_COND'] = job_color


def pass_job_cond(configuration, job_cond, job_cond_color):
    """Validates whether the constructed job_cond dictionary passes
    the required validations configured for a specific job_cond color.
    """

    if reduce(lambda x, y: x and y, list(job_cond.values())):
        return True
    else:
        job_cond_config = []

        if job_cond_color == RED:
            job_cond_config = configuration.job_cond_red
        elif job_cond_color == ORANGE:
            job_cond_config = configuration.job_cond_orange
        elif job_cond_color == YELLOW:
            job_cond_config = configuration.job_cond_yellow
        elif job_cond_color == GREEN:
            job_cond_config = configuration.job_cond_green

        try:
            return reduce(lambda x, y: x and y,
                          [val for (key, val) in job_cond.items()
                           for test in job_cond_config
                           if key.upper() == test.upper() and not val])

        # reduction of empty list

        except TypeError:
            return True


def none_available(job_cond, errors, mrsl_attribute, suggest=False,
                   fake_dict=False):
    """Prepares the job_cond and errors dictionaries for non-existing
    vgrids and resources.
    """

    job_cond['JOB_COND'] = RED

    if suggest:
        err_msg = 'There are no valid/allowed %ss available to suggest.' \
            % (mrsl_attribute.lower())

        if mrsl_attribute == 'VGRID':
            job_cond['vgrid_suggested'] = False
            errors['vgrid_suggested'] = err_msg

        elif mrsl_attribute == 'RESOURCE':
            job_cond['resource_suggested'] = False
            errors['resource_suggested'] = err_msg

    else:
        job_cond[mrsl_attribute] = False
        errors[mrsl_attribute] = \
            'There are no valid/allowed %ss available.' \
            % mrsl_attribute.lower()

    if fake_dict:
        return (job_cond, errors, {})
    return (job_cond, errors)


def get_resource_configuration(configuration, resource_id, resource_map=None):
    """Returns empty dict if resource_id is missing/deleted"""
    if not resource_map:
        resource_map = get_resource_map(configuration)
    return resource_map.get(resource_id, {CONF: {}})[CONF]


def default_vgrid_resources(configuration):
    """Returns a list of user allowed resources for the default_vgrid."""

    resources_and_vgrids = get_vgrid_map(configuration)[RESOURCES]
    resources = []

    for resource in resources_and_vgrids:
        if default_vgrid in resources_and_vgrids[resource][ALLOW]:
            resources.append(resource)

    return resources


def complement_vgrids(configuration, job, vgrids):
    """Returns a list of allowed vgrids where those specified-and-allowed
    have been subtracted.
    """

    vgrid_access = set(user_vgrid_access(configuration, job['USER_CERT']))

    return list(vgrid_access.difference(vgrids))


def complement_resources(configuration, job, vgrid, resources):
    """Returns a set of allowed resources where those specified-and-allowed
    have been subtracted.
    A job submitted to a VGrid must be executed by a resource from
    that VGrid.
    """

    allowed_resources = set()
    if vgrid == default_vgrid:
        allowed_resources = set(default_vgrid_resources(configuration))
    else:
        (status, vgrid_res) = vgrid_resources(vgrid, configuration)
        if not status:
            vgrid_res = []
        allowed_resources = set(vgrid_res)

    return allowed_resources.difference(resources)


def in_skip_list(configuration, mrsl_attribute):
    """Refrains from performing validation of tests
    listed in the configuration file.
    """

    return mrsl_attribute in configuration.skip_validation


def skip_validation(configuration, job, mrsl_attribute, *args):
    """If the job and/or resource dictionary lacks the mrsl-attribute,
    if listed in the configuration files skip_validation list or has the
    default value, validation is omitted.
    """

    is_in_skip_list = in_skip_list(configuration, mrsl_attribute)
    job_has_key = False
    it_has_default_value = False
    args_present = False
    args_has_key = False

    if not is_in_skip_list:
        job_has_key = mrsl_attribute in job
        if job_has_key:
            it_has_default_value = has_default_value(configuration,
                                                     mrsl_attribute,
                                                     job[mrsl_attribute])
        if args and len(args) == 1:
            args_present = True
            args_has_key = mrsl_attribute in args[0]

    if args_present:
        return is_in_skip_list or (not job_has_key) or it_has_default_value \
            or (not args_has_key)
    else:
        return is_in_skip_list or (not job_has_key) or it_has_default_value


def has_default_value(configuration, mrsl_attribute, value):
    """Returns True/False to wether the mrsl value is the default."""

    default_value = None

    keywords_dict = get_keywords_dict(configuration)
    if mrsl_attribute in keywords_dict:
        default_value = keywords_dict[mrsl_attribute].get('Value')

    return default_value == value


def anon_to_real_resources(configuration, anon_resources):
    """Returns the real names of anonymous resources."""

    anon_specified_resources = set(anon_resources)
    alt_anon_specified_resources = set()

    for asr in anon_specified_resources:
        alt_anon_specified_resources.add(asr[:asr.rfind('_')])

    anon_to_real_map = anon_to_real_res_map(configuration.resource_home)
    specified_resources = set()

    [specified_resources.add(anon_to_real_map[aasr])
     for aasr in alt_anon_specified_resources
     if aasr in anon_to_real_map]

    return specified_resources


def real_to_anon_resources(configuration, real_resources):
    """Returns the anonymous names of real resources."""

    real_to_anon_map = real_to_anon_res_map(configuration.resource_home)
    anon_not_allowed = set()
    [anon_not_allowed.add(real_to_anon_map[rr])
     for rr in real_resources
     if rr in real_to_anon_map]

    return anon_not_allowed


def std_err_desc(job_value, *args):
    """Returns a standard error description for those validations
    that do not pass.
    """

    if args and len(args) == 1:
        return 'Job/Resource values: %s / %s' \
            % (job_value, args[0])
    else:
        return 'Job value: %s' % (job_value)


def assemble_errors(job_cond, errors):
    """Turns the two dictionaries into one with attributes
    accompanied with errors.
    """

    if errors == {}:
        return []

    return dict([(key.upper(), val_) for (key, val) in job_cond.items()
                 for (key_, val_) in errors.items()
                 if key.upper() == key_.upper() and not val])


def get_job_cond_color_icon(job_cond):
    """Returns the path for the icon corresponding to the job_cond color."""

    icon_path = '/images/icons'
    icon = ''

    if job_cond == GREEN:
        icon = os.path.join(icon_path, 'green.png')
    elif job_cond == YELLOW:
        icon = os.path.join(icon_path, 'yellow.png')
    elif job_cond == ORANGE:
        icon = os.path.join(icon_path, 'orange.png')
    elif job_cond == RED:
        icon = os.path.join(icon_path, 'red.png')

    return icon


def threshold_color_to_value(job_cond_color):
    """Returns the index of job_cond_color in list of all colors"""

    # tuple does not support index() before python-2.6

    return list(job_cond_colors).index(job_cond_color.upper())


def assemble_suggest_msg(job_cond):
    """Returns an assembled suggestions message to be part of the
    feasibility verdict.
    """

    suggestion = ''

    if job_cond.get('vgrid_suggested', False):
        suggestion += 'Utilizing VGrid \'%s\'' % (job_cond['suggested_vgrid'])
        if job_cond.get('resource_suggested', False):
            suggestion += ' and resource \'%s\'' \
                % (job_cond['suggested_resource'])
        else:
            suggestion += ' (however, no applicable resource was found)'
        suggestion += ' the feasibility achieved is:'
    else:
        suggestion += ' No applicable VGrid was found.'

    return suggestion


def exe_last_seen(configuration, resource_id):
    """Returns the name and modification time of the last modified exe in
    configuration.resource_home. Thus it can be deduced that all other exe's
    for the resource have been 'seen' earlier."""

    latest_stamp = 0
    latest_exe = None
    dirname = os.path.join(configuration.resource_home, resource_id)

    for lrf in [filename for filename in os.listdir(dirname)
                if filename.startswith('last_request.')]:
        exe_stamp = os.path.getmtime(os.path.join(dirname, lrf))
        if exe_stamp > latest_stamp:
            latest_exe = lrf.split('.', 1)[1]
            latest_stamp = exe_stamp

    return (latest_exe, latest_stamp)
