#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showresupporthistory - [insert a few words of module description on this line]
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
import time

from shared.findtype import is_owner
from shared.html import get_cgi_html_header, get_cgi_html_footer
from shared.validstring import valid_dir_input
from shared.fileio import unpickle
from shared.cgishared import init_cgi_script_with_cert
from shared.refunctions import is_runtime_environment

# ## Main ###

(logger, configuration, cert_name_no_spaces, o) = \
    init_cgi_script_with_cert()

fieldstorage = cgi.FieldStorage()
htmlquery = fieldstorage.getfirst('with_html', '')
re_name = fieldstorage.getfirst('re_name', '').strip().upper()
unique_resource_name = fieldstorage.getfirst('unique_resource_name', ''
        ).strip()

printhtml = False
if htmlquery == 'true' or not htmlquery:
    printhtml = True

o.client(get_cgi_html_header('Runtime environment support history',
         'Runtime environment support', printhtml, scripts=''))

if re_name == '':
    o.out('Please specify the name of the runtime environment (re_name)!'
          )
    o.reply_and_exit(o.CLIENT_ERROR)

if unique_resource_name == '':
    o.out('Please specify the name of the resource (unique_resource_name)!'
          )
    o.reply_and_exit(o.CLIENT_ERROR)

if not valid_dir_input(configuration.re_home, re_name):
    o.out('Illegal re_name: %s' % re_name)
    logger.warning("Registered possible illegal directory traversal attempt by '%s': re_name '%s'"
                    % (cert_name_no_spaces, re_name))
    o.reply_and_exit(o.CLIENT_ERROR)

if '/' in re_name:
    o.out("'/' not allowed in runtime environment name!")
    o.reply_and_exit(o.CLIENT_ERROR)

if not valid_dir_input(configuration.resource_home,
                       unique_resource_name):
    o.out('Illegal unique_resource_name: %s' % unique_resource_name)
    logger.warning("Registered possible illegal directory traversal attempt by '%s': unique_resource_name '%s'"
                    % (cert_name_no_spaces, unique_resource_name))
    o.reply_and_exit(o.CLIENT_ERROR)

# remove the is_owner check to allow vgrid owners to see if a resource (where they know the unique_resoyurce_name)
# supports a specific runtime environment?

if not is_owner(cert_name_no_spaces, unique_resource_name,
                configuration.resource_home, logger):
    o.out('You must be an owner of the resource to get history of runtime environment support. (resource %s)'
           % unique_resource_name)
    o.reply_and_exit(o.CLIENT_ERROR)

if not is_runtime_environment(re_name, configuration):
    o.client("'%s' is not a valid runtime environment!" % re_name)
    o.reply_and_exit(o.CLIENT_ERROR)

resource_config = unpickle(configuration.resource_home
                            + unique_resource_name + '/config',
                           configuration.logger)
if not resource_config:
    logger.error('error unpickling resource config')
    o.reply_and_exit(o.ERROR)

if not resource_config.has_key('RUNTVERIFICATION'):
    o.client('Resource has not executed any runtime environment testprocedures with its current configuration!'
             )
else:
    runt_dict = resource_config['RUNTVERIFICATION']
    if not runt_dict.has_key(re_name):
        o.client('Resource has not executed any testprocedures for the specified runtime environment with its current configuration!'
                 )
    else:
        jobs = runt_dict[re_name]
        if jobs == []:
            o.client('Resource has not executed any testprocedures for the specified runtime environment with its current configuration!'
                     )
        else:
            try:

                for (job_id, submitter_cert_name_no_spaces) in jobs:

            # print info about the single testjob

                    mrslfilepath = configuration.mrsl_files_dir\
                         + cert_name_no_spaces + '/' + job_id + '.mRSL'
                    job_dict = unpickle(mrslfilepath,
                            configuration.logger)
                    if not job_dict:
                        o.out('Error getting details for job_id %s'
                               % job_id)
                        continue

                    o.client('Job id: %s\n' % job_id)
                    o.client_html('<BR>', printhtml)

                    o.client('Job status: %s\n' % job_dict['STATUS'])
                    o.client_html('<BR>', printhtml)

                    if job_dict.has_key('VERIFIED'):
                        o.client_html('<I>', printhtml)
                        o.client('Verified: %s\n' % job_dict['VERIFIED'
                                 ])
                        o.client_html('</I><BR>', printhtml)

                    if job_dict.has_key('VERIFIED_TIMESTAMP'):
                        o.client('Verified at: %s\n'
                                  % time.asctime(job_dict['VERIFIED_TIMESTAMP'
                                 ]))
                        o.client_html('<BR>', printhtml)

                    o.client('''

''')
                    o.client_html('<BR><BR>', printhtml)
            except Exception, ex:

                o.out('Exception looping testprocedure jobs!', ex)
                o.reply_and_exit(o.ERROR)

o.client(get_cgi_html_footer("<p><a href='resadmin.py'>Back to resource administration page.</a>"
         , printhtml))
o.reply_and_exit(o.OK)
