#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testresupport - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid

import cgi
import cgitb
cgitb.enable()
import base64
import tempfile
import os

from shared.cgishared import init_cgi_script_with_cert
from shared.fileio import unpickle, write_file
from shared.findtype import is_owner, client_id_dir
from shared.html import get_cgi_html_header, get_cgi_html_footer
from shared.job import new_job
from shared.refunctions import get_re_dict
from shared.validstring import valid_dir_input


def create_verify_files(types, base_dir):
    for ver_type in types:
        if re_dict.has_key('VERIFY%s' % ver_type.upper()):
            if re_dict['VERIFY%s' % ver_type.upper()] != []:
                file_content = ''
                for line in re_dict['VERIFY%s' % ver_type.upper()]:
                    file_content += line + '\n'
                if not write_file(file_content.strip(),
                                  '%sverify_runtime_env_%s.%s'
                                   % (base_dir, re_name,
                                  ver_type.lower()), logger):
                    o.out('Exception writing temporary verify.%s file. Runtime environment support verification job not submitted!'
                           % ver_type.upper())
                    o.reply_and_exit(o.ERROR)


def testresource_has_re_specified(unique_resource_name, re_name,
                                  configuration):
    resource_config = unpickle(configuration.resource_home
                                + unique_resource_name + '/config',
                               configuration.logger)
    if not resource_config:
        logger.error('error unpickling resource config')
        return False

    for rre in resource_config['RUNTIMEENVIRONMENT']:
        (res_name, res_val) = rre
        if re_name == res_name:
            return True

    return False


# ## Main ###

(logger, configuration, client_id, o) = init_cgi_script_with_cert()
client_dir = client_id_dir(client_id)

fieldstorage = cgi.FieldStorage()
htmlquery = fieldstorage.getfirst('with_html', '')
re_name = fieldstorage.getfirst('re_name', '').strip().upper()
unique_resource_name = fieldstorage.getfirst('unique_resource_name', ''
        ).strip()

printhtml = False
if htmlquery == 'true' or not htmlquery:
    printhtml = True

o.client(get_cgi_html_header(configuration, 'Verify runtime environment',
         'Verify runtime environment', printhtml, scripts=''))

if re_name == '':
    o.out('Please specify the name of the runtime environment!')
    o.reply_and_exit(o.CLIENT_ERROR)

if not valid_dir_input(configuration.re_home, re_name):
    o.out('Illegal re_name: %s' % re_name)
    logger.warning("createre registered possible illegal directory traversal attempt by '%s': re_name '%s'"
                    % (client_id, re_name))
    o.reply_and_exit(o.CLIENT_ERROR)

if '/' in re_name:
    o.out("'/' not allowed in runtime environment name!")
    o.reply_and_exit(o.CLIENT_ERROR)

if unique_resource_name == '':
    o.out('Please specify the name of the resource!')
    o.reply_and_exit(o.CLIENT_ERROR)

if not valid_dir_input(configuration.resource_home,
                       unique_resource_name):
    o.out('Illegal unique_resource_name: %s' % unique_resource_name)
    logger.warning("createre registered possible illegal directory traversal attempt by '%s': unique_resource_name '%s'"
                    % (client_id, unique_resource_name))
    o.reply_and_exit(o.CLIENT_ERROR)

if not is_owner(client_id, unique_resource_name,
                configuration.resource_home, logger):
    o.out('You must be an owner of the resource to validate runtime environment support. (resource %s)'
           % unique_resource_name)
    o.reply_and_exit(o.CLIENT_ERROR)

(re_dict, re_msg) = get_re_dict(re_name, configuration)
if not re_dict:
    o.out('Could not get re_dict %s' % re_msg)
    o.reply_and_exit(o.ERROR)

if not testresource_has_re_specified(unique_resource_name, re_name,
        configuration):
    o.out('You must specify the runtime environment in the resource configuration before verifying if it is supported!'
          )
    o.reply_and_exit(o.CLIENT_ERROR)

base64string = ''
for stringpart in re_dict['TESTPROCEDURE']:
    base64string += stringpart

mrslfile_content = base64.decodestring(base64string)

try:
    (filehandle, mrslfile) = tempfile.mkstemp(text=True)
    os.write(filehandle, mrslfile_content)
    os.close(filehandle)
except Exception, e:
    o.out('Exception writing temporary mrsl file. Runtime environment support job not submitted! %s'
           % e, str(e))
    o.reply_and_exit(o.ERROR)

# Please note that base_dir must end in slash to avoid access to other
# user dirs when own name is a prefix of another user name

base_dir = os.path.abspath(os.path.join(configuration.user_home,
                           client_dir)) + os.sep

create_verify_files(['status', 'stdout', 'stderr'], base_dir)

forceddestination_dict = {'UNIQUE_RESOURCE_NAME': unique_resource_name,
                          'RE_NAME': re_name}

(status, msg) = new_job(mrslfile, client_id, configuration,
                        forceddestination_dict)
if not status:
    o.out('%s' % msg)
    try:
        os.remove(mrslfile)
    except:
        pass
    o.reply_and_exit(o.CLIENT_ERROR)

try:
    os.remove(mrslfile)
except:
    pass

o.out('Runtime environment test job successfuly submitted! %s' % msg)

o.client(get_cgi_html_footer(configuration,
                             "<p><a href='resadmin.py'>Back to resource administration page.</a>",
                             printhtml))
o.reply_and_exit(o.OK)
