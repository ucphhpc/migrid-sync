#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# confparser - [insert a few words of module description on this line]
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

# Initial version Brian Vinter
# Henrik Hoey Karlsen
# Martin Rehr

import shared.parser as parser
import shared.refunctions as refunctions
import shared.resconfkeywords as resconfkeywords
from shared.conf import get_configuration_object
from shared.serial import dumps
from shared.vgrid import vgrid_is_resource

configuration = get_configuration_object()


def get_resource_config_dict(config_file):
    """Find and return configuration dictionary in provided
    conf file"""

    result = parser.parse(config_file)
    external_dict = resconfkeywords.get_keywords_dict(configuration)

    # The Configfile has the right structure
    # Check if the types are correct too

    (status, msg) = parser.check_types(result, external_dict,
            configuration)

    if not status:
        return (False, 'Parse failed (typecheck) ' + msg, external_dict)

    global_dict = {}

    for (key, value_dict) in external_dict.iteritems():
        global_dict[key] = value_dict['Value']

    return (status, msg, global_dict)


def run(localfile_spaces, unique_resource_name, outfile='AUTOMATIC'
        ):
    """Parse configuration in localfile_spaces and write results to outfile
    if non-empty. The keyword AUTOMATIC is replaced by the expected resource
    configuration path.
    """

    (status, msg, conf) = get_resource_config_dict(localfile_spaces)

    if not status:
        return (False, msg)

    # verify runtimeenvironments are specified correctly

    if conf.has_key('RUNTIMEENVIRONMENT'):
        for re in conf['RUNTIMEENVIRONMENT']:
            try:
                (name, value) = re
            except Exception, err:
                return (False, 'Runtimeenvironment error: %s' % err)
            if not refunctions.is_runtime_environment(name,
                    configuration):
                return (False,
                        "Non existing runtime environment specified ('%s'), please create the runtime environment before specifying it in resource configurations."
                         % name)

            (re_dict, msg) = refunctions.get_re_dict(name,
                    configuration)
            if not re_dict:
                return (False,
                        'Runtimeenvironment error, could not open (%s) %s'
                         % (name, msg))

            if not re_dict.has_key('ENVIRONMENTVARIABLE'):
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
                except Exception, err:

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

    for exe in conf['EXECONFIG']:

        # replace +EXENAME+ with specified exe name

        for exe_key in exe.keys():
            if type(exe[exe_key]) == type(''):
                exe[exe_key] = exe[exe_key].replace('+EXENAME+',
                        exe['name'])

        # verify resource is in specified vgrid

        vgrid_name = exe['vgrid']

        # print "vgrid_name in exe" + vgrid_name

        if vgrid_name == '':

            # ok

            pass
        else:
            if type(vgrid_name) == type([]):

                # list

                for vgrid in vgrid_name:
                    if not vgrid_is_resource(vgrid,
                            unique_resource_name, configuration):
                        return (False,
                                "Your resource is not allowed in the vgrid '%s' specified in the configuation for the '%s' execution unit. Please contact the vgrid owner and ask if you can be included in the vgrid."
                                 % (vgrid, exe['name']))
            else:

                # string

                if not vgrid_is_resource(vgrid_name,
                        unique_resource_name, configuration):
                    return (False,
                            "Your resource is not allowed in the vgrid '%s' specified in the configuation for the '%s' execution unit. Please contact the vgrid owner and ask if you can be included in the vgrid."
                             % (vgrid_name, exe['name']))

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
    except Exception, err:
        return (False, "Fatal error: could not open '" + filename
                 + "' for writing!" + '\n Msg: ' + str(err))
    return (True, 'Everything ok, config updated')


