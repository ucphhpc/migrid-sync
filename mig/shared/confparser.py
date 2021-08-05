#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# confparser - parse resource configurations
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

# Initial version Brian Vinter
# Henrik Hoey Karlsen
# Martin Rehr

"""parse resource configurations"""
from __future__ import absolute_import

from mig.shared.conf import get_configuration_object
from mig.shared.parser import parse, check_types
from mig.shared.refunctions import is_runtime_environment, get_re_dict
from mig.shared.resconfkeywords import get_keywords_dict as \
    resconf_get_keywords_dict
from mig.shared.serial import dumps
from mig.shared.vgrid import vgrid_is_resource, vgrid_is_default


def get_resource_config_dict(configuration, config_file):
    """Find and return configuration dictionary in provided
    conf file"""

    if not configuration:
        configuration = get_configuration_object()

    result = parse(config_file)
    external_dict = resconf_get_keywords_dict(configuration)

    # The Configfile has the right structure
    # Check if the types are correct too

    (status, msg) = check_types(result, external_dict, configuration)

    if not status:
        return (False, 'Parse failed (typecheck) ' + msg, external_dict)

    global_dict = {}

    for (key, value_dict) in external_dict.iteritems():
        global_dict[key] = value_dict['Value']

    return (status, msg, global_dict)


def run(configuration, localfile_spaces, unique_resource_name,
        outfile='AUTOMATIC'):
    """Parse configuration in localfile_spaces and write results to outfile
    if non-empty. The keyword AUTOMATIC is replaced by the expected resource
    configuration path.
    """

    if not configuration:
        configuration = get_configuration_object()

    (status, msg, conf) = get_resource_config_dict(configuration,
                                                   localfile_spaces)

    if not status:
        return (False, msg)

    # verify runtime environments are specified correctly

    if 'RUNTIMEENVIRONMENT' in conf:
        for re in conf['RUNTIMEENVIRONMENT']:
            try:
                (name, value) = re
            except Exception as err:
                return (False, 'Runtime environment error: %s' % err)
            if not is_runtime_environment(name, configuration):
                return (False,
                        "Non existing runtime environment specified ('%s'), please create the runtime environment before specifying it in resource configurations."
                        % name)

            (re_dict, msg) = get_re_dict(name, configuration)
            if not re_dict:
                return (False,
                        'Runtime environment error, could not open (%s) %s'
                        % (name, msg))

            if 'ENVIRONMENTVARIABLE' not in re_dict:
                if value:

                    # res conf has envs, but according to the template it should not

                    return (False,
                            "%s should not have any environments and you specified '%s'. Details about the runtime environment <a href=showre.py?re_name=%s>here</a>"
                            % (re, value, name))
                else:
                    continue
            re_dict_environments = re_dict['ENVIRONMENTVARIABLE']
            re_dict_environment_names = []
            for re_environment in re_dict_environments:
                re_dict_environment_names.append(re_environment['name'])

            if not len(value) == len(re_dict_environments):
                return (False,
                        "You have specified %s environments, but the runtime environment '%s' requires %s. Details about the runtime environment <a href='showre.py?re_name=%s'>here.</a>"
                        % (len(value), name,
                            len(re_dict_environments), name))

            # we now know that the number of environments are
            # correct, verify that there are no name duplicates

            used_envnames = []
            for env in value:
                try:
                    (envname, _) = env
                    if envname in used_envnames:

                        # same envname used twice

                        return (False,
                                "You have specified the environment '%s' more than once for the '%s' runtime environment."
                                % (envname, name))
                    used_envnames.append(envname)
                except Exception as err:

                    return (False,
                            'Runtimeenvironment error: Name and value not found in env: %s'
                            % err)

            # verify environment names are correct according to the
            # runtime environment definition do this by comparing
            # list of names specified for runtime environment and
            # res. conf.
            # re_dict_environment_names and used_envnames should
            # have the same entries!

            for n in re_dict_environment_names:

                # any build-in list comparison functionality?

                if not n in used_envnames:
                    return (False,
                            "You have not specified an environment named '%s' which is required by the '%s' runtime environment. Details about the runtime environment <a href=showre.py?re_name=%s>here.</a>"
                            % (n, name, name))

    # check VGrid access

    vgrid_label = configuration.site_vgrid_label
    for (unit_config, unit_name) in (('EXECONFIG', '+EXENAME+'),
                                     ('STORECONFIG', '+STORENAME+')):
        for res_unit in conf[unit_config]:

            # replace unit_name with specified res_unit name

            for res_unit_key in res_unit.keys():
                if type(res_unit[res_unit_key]) == type(''):
                    res_unit[res_unit_key] = res_unit[res_unit_key].replace(
                        unit_name, res_unit['name'])

            # verify resource is in specified vgrid

            vgrid_name = res_unit['vgrid']

            # print "vgrid_name in res_unit" + vgrid_name

            if vgrid_name == '':

                # ok

                pass
            else:
                if type(vgrid_name) == type([]):

                    # list

                    for vgrid in vgrid_name:
                        if not vgrid_is_default(vgrid) and not \
                            vgrid_is_resource(vgrid, unique_resource_name,
                                              configuration):
                            return (False,
                                    """Your resource is not allowed in the %s
'%s' specified in the configuation for the '%s' resource unit. Please contact
the %s owner and ask if you can be included in the %s.""" %
                                    (vgrid_label, vgrid, res_unit['name'],
                                     vgrid_label, vgrid_label))
                else:

                    # string

                    if not vgrid_is_default(vgrid) and not vgrid_is_resource(vgrid_name,
                                                                             unique_resource_name, configuration):
                        return (False,
                                """Your resource is not allowed in the %s '%s'
specified in the configuation for the '%s' resource unit. Please contact the %s
owner and ask if you can be included in the %s.""" %
                                (vgrid_label, vgrid_name, res_unit['name'],
                                 vgrid_label, vgrid_label))

    # save dictionary to a file

    if outfile == 'AUTOMATIC':

        # save configuration as python dictionary in the resource' private directory

        filename = configuration.resource_home + unique_resource_name\
            + '/config'
    elif outfile:

        # outfile specified (DumpConfig)

        filename = outfile
    else:
        return (True, 'Everything ok')

    try:
        fsock = open(filename, 'w')
        st = dumps(conf, 0)
        fsock.write(st)
        fsock.close()
    except Exception as err:
        return (False, "Fatal error: could not open %r for writing!\n Msg: %s"
                % (filename, err))
    return (True, 'Everything ok, config updated')
