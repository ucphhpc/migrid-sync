#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reseditaction - Resource editor action handler back end
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

# Martin Rehr martin@rehr.dk August 2005

"""Handle resource editor actions"""

import os
import time

import shared.confparser as confparser
import shared.returnvalues as returnvalues
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.notification import send_resource_create_request_mail
from shared.resource import prepare_conf, write_resource_config, \
     create_resource
from shared.useradm import client_id_dir


def signature():
    """Signature of the main function"""

    defaults = {'HOSTURL': REJECT_UNSET, 'HOSTIDENTIFIER': ['']}
    return ['html_form', defaults]


def update_resource(configuration, client_id, resource_id, user_vars,
                    output_objects, new_resource=False):
    """Update existing resource configuration from request"""

    logger = configuration.logger
    client_dir = client_id_dir(client_id)
    tmp_id = "%s.%s" % (user_vars['HOSTURL'], time.time())
    pending_file = os.path.join(configuration.resource_pending, client_dir,
                                tmp_id)
    conf_file = os.path.join(configuration.resource_home, resource_id,
                             'config.MiG')
    output = ''
    try:
        logger.info('write to file: %s' % pending_file)
        write_resource_config(configuration, user_vars, pending_file)
    except Exception, err:
        logger.error('Resource conf %s could not be written: %s' % \
                     (pending_file, err))
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not write configuration!'})
        return False

    logger.info('Parsing conf %s for %s' % (pending_file, resource_id))
    if new_resource:
        destination = ''
    else:
        destination = 'AUTOMATIC'
    (status, msg) = confparser.run(pending_file, resource_id, destination)
    if not status:
        logger.error(msg)
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to parse new configuration: %s' % msg})
        try:
            os.remove(pending_file)
        except:
            pass
        return False

    if not new_resource:
        logger.info('Updating conf %s for %s' % (conf_file, resource_id))
        try:
            os.rename(pending_file, conf_file)
        except:
            return False
        unique_resource_name = '(HOSTURL)s.%(HOSTIDENTIFIER)s' % user_vars
        output_objects.append({'object_type': 'text', 'text':
                               'Updated %s resource configuration: %s' % \
                               (unique_resource_name, msg)})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'resadmin.py?unique_resource_name=%s' % \
                               unique_resource_name,
                               'class': 'adminlink',
                               'title': 'Administrate resource',
                               'text': 'Manage resource',
                               })
        return True
    elif configuration.auto_add_resource:
        resource_name = user_vars['HOSTURL']
        logger.info('Auto creating resource %s from %s' % (resource_id,
                                                           pending_file))
        (create_status, msg) = create_resource(configuration, client_id,
                                               resource_name, pending_file)
        if not create_status:
            output_objects.append({'object_type': 'text', 'error_text':
                               'Resource creation failed: %s' % msg})
            return False
        output += '''Your resource was added as %s.%s
<hr />''' % (resource_name, msg)
    else:
        logger.info('Sending create request for %s to admins' % resource_id)
        (status, msg) = send_resource_create_request_mail(client_id,
                                                          user_vars['HOSTURL'],
                                                          pending_file, logger,
                                                          configuration)
        logger.info(msg)
        if not status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   '''Failed to send request with ID "%s" to
the %s administrator(s):
%s
Please manually contact the %s server administrator(s) (%s)
and provide this information''' % (tmp_id, msg, 
                                   configuration.short_title, 
                                   configuration.short_title,
                                   configuration.admin_email )
                               })
            return False
        output += """Your creation request of the resource: <b>%s</b>
has been sent to the %s server administration and will be processed as
soon as possible.
<hr />""" % (user_vars['HOSTURL'], configuration.short_title) \


    public_key_file_content = ''
    try:
        key_fh = open(configuration.public_key_file, 'r')
        public_key_file_content = key_fh.read()
        key_fh.close()
    except:
        public_key_file_content = None

    # Avoid line breaks in displayed key
    if public_key_file_content:
        public_key_info = '''
The public key you must add:<br />
***BEGIN KEY***<br />
%s<br />
***END KEY***<br />
<br />''' % public_key_file_content.replace(' ', '&nbsp;')
    else:
        public_key_info = '''<br />
Please request an SSH public key from the %s administrator(s) (%s)<br />
<br />''' % (configuration.short_title, configuration.admin_email)

    output += """
Please make sure the %s server can SSH to your resource without a passphrase.
The %s server's public key should be in ~/.ssh/authorized_keys for the MiG
user on the resource frontend. %s
<br />
Also, please note that %s resources require the curl command line tool from
<a href="http://www.curl.haxx.se">cURL</a>. 
<br />
<a href='resadmin.py'>View existing resources</a> where your new resource 
will also eventually show up.
""" % (configuration.short_title, configuration.short_title, public_key_info,
       configuration.short_title)

    output_objects.append({'object_type': 'html_form', 'text': output})

    return True



def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]

    ### IMPORTANT: we can not validate input completely here!
    # We validate the parts used in the path manipulation and only use
    # the remaining variables directly in the generated config file that
    # is then handed to the parser for full validation.

    critical_arguments = {}
    critical_fields = defaults.keys()
    for field in critical_fields:
        critical_arguments[field] = user_arguments_dict.get(field, [''])
    
    (validate_status, accepted) = validate_input_and_cert(
        critical_arguments,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    hosturl = accepted['HOSTURL'][-1]
    hostidentifier = accepted['HOSTIDENTIFIER'][-1]
    if hostidentifier:
        action = 'update'
    else:
        action = 'create'
        hostidentifier = '$HOSTIDENTIFIER'
        accepted['HOSTIDENTIFIER'] = [hostidentifier]
    resource_id = "%s.%s" % (hosturl, hostidentifier)

    # Override original critical values with the validated ones

    for field in critical_fields:
        user_arguments_dict[field] = accepted[field]

    status = returnvalues.OK

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource edit actions'
    output_objects.append({'object_type': 'header', 'text':
                           'Resource edit actions'})
    conf = prepare_conf(configuration, user_arguments_dict, resource_id)
    if 'create' == action:
        logger.info('%s is trying to create resource %s (%s)' % \
                    (client_id, hosturl, conf))
        output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Creating resource configuration'})

        # We only get here if hostidentifier is dynamic so no access control

        if not update_resource(configuration, client_id, resource_id, conf,
                               output_objects, True):
            status = returnvalues.SYSTEM_ERROR
    elif 'update' == action:
        logger.info('%s is trying to update resource %s (%s)' % \
                    (client_id, resource_id, conf))
        output_objects.append({'object_type': 'sectionheader', 'text'
                               : 'Updating existing resource configuration'})

        # Prevent unauthorized access to existing resources

        owners_path = os.path.join(configuration.resource_home, resource_id,
                                   'owners')
        owner_list = unpickle(owners_path, logger)
        if not owner_list:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : "Could not look up '%s' owners - no such resource?" % \
                 resource_id})
            status = returnvalues.SYSTEM_ERROR
        elif client_id in owner_list:
            if not update_resource(configuration, client_id, resource_id, conf,
                                   output_objects, False):
                status = returnvalues.SYSTEM_ERROR
        else:
            status = returnvalues.CLIENT_ERROR
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'You can only update your own resources!'
                                   })
    else:
        status = returnvalues.CLIENT_ERROR
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Unknown action request!'
                               })

    return (output_objects, status)
