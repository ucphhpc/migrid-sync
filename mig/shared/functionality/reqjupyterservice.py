#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqjupyterservice - Redirect the user to a backend jupyter service host
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

"""Automatic home drive mount from jupyter
This backend makes two requests to the targeted jupyter service host.
The first authenticates against the jupyterhub server,
it passes the Remote-User header with the client_id's email.
The second request takes the newly instantiated ssh keyset and passes it to the
jupyterhub server via the Mount header.
Subsequently any potentially old keysets for this user is removed and the new
keyset is committed to the users configuration.jupyter_mount_files_dir
directory. Finally this active keyset is linked to the directory where the sftp
will check for a valid keyset and the users homedrive is linked to the same
location.

Finally the user is redirected to the jupyterhub home page where a new notebook
server can be instantiated and mount the users linked homedrive with the passed
keyset.
"""
from __future__ import print_function
from __future__ import absolute_import

from past.builtins import basestring
import os
import re
import socket
import sys
import time
import shutil
import random
import requests
from urllib.parse import urljoin

from mig.shared import returnvalues
from mig.shared.base import client_id_dir, extract_field
from mig.shared.defaults import session_id_bytes
from mig.shared.fileio import make_symlink, pickle, unpickle, write_file, \
    delete_symlink, delete_file
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.httpsclient import unescape
from mig.shared.init import initialize_main_variables
from mig.shared.pwcrypto import generate_random_ascii
from mig.shared.ssh import generate_ssh_rsa_key_pair, tighten_key_perms
from mig.shared.workflows import create_workflow_session_id, \
    get_workflow_session_id


def is_active(pickle_state, timeout=7200):
    """
    :param pickle_state: expects a pickle object dictionary that
    contains the field 'CREATED_TIMESTAMP' with a timestamp of when the pickle
    was established
    :param timeout: seconds in which the pickle_state is considered active
    default is 2 hours -> 7200 seconds
    :return: Boolean
    """
    assert isinstance(pickle_state, dict), "pickle_state is a dictionary: %r" % \
                                           pickle_state
    assert 'CREATED_TIMESTAMP' in pickle_state

    active = True
    active_time = int(time.time())\
        - int(pickle_state['CREATED_TIMESTAMP'])
    if active_time > timeout:
        active = False
    return active


def to_unix_account(input_str):
    """
    Extracts a set of valid characters from input_str and returns a
     32 character string that can be used as a unix account name
    :param mig: A string that is used to generate a valid unix account name.
    :return: None if failed or string with a maximum length of 32 characters
    """
    if not isinstance(input_str, basestring) or not input_str:
        return None
    input_str = input_str.lower()
    valid_unix_name = "".join(re.findall('[a-z0-9_.\-]+', input_str))
    if not valid_unix_name:
        return None
    return valid_unix_name[:32]


def mig_to_mount_adapt(mig):
    """
    :param mig: expects a dictionary containing mig state keys including,
    MOUNT_HOST, SESSIONID, MOUNTSSHPRIVATEKEY, TARGET_MOUNT_ADDR and PORT
    :return: returns a dictionary
    """
    mount_string = mig["TARGET_MOUNT_ADDR"]
    target_host = ""
    target_path = ""

    if "@" in mount_string and ":" in mount_string:
        # Expects that the mount_string is in the format
        # @mount_url:mount_path
        target_host = mount_string[mount_string.index("@")+1:mount_string.index(":")]
        target_path = mount_string[mount_string.index(":")+1:]        

    mount = {
        'targetHost': target_host,
        'username': mig['SESSIONID'],
        'privateKey': mig['MOUNTSSHPRIVATEKEY'],
        'targetPath': target_path,
        'port': "%s" % mig.get('PORT', 22)
    }
    return mount


def mig_to_user_adapt(mig):
    """
    :param mig: expects a dictionary containing a USER_CERT key that defines
    the users unique x509 Distinguish Name.
    :return: a dictionary that is ready to send to a jupyterhub host
    """
    user = {
        'CERT': mig['USER_CERT']
    }
    if 'USER_EMAIL' in mig:
        unix_name = to_unix_account(['USER_EMAIL'])
        if unix_name:
            user['UNIX_NAME'] = unix_name
    return user


def mig_to_workflows_adapt(mig):
    """
    :param mig: expects a dictionary containing mig state keys including,
    WORKFLOWS_URL, WORKFLOWS_SESSIONID.
    :return: returns a dictionary
    """
    workflows = {}
    if 'WORKFLOWS_URL' in mig:
        workflows.update({'WORKFLOWS_URL': mig['WORKFLOWS_URL']})
    if 'WORKFLOWS_SESSION_ID' in mig:
        workflows.update({'WORKFLOWS_SESSION_ID': mig['WORKFLOWS_SESSION_ID']})
    return workflows


def remove_jupyter_mount(jupyter_mount_path, configuration):
    """
    :param jupyter_mount_path path to a jupyter mount pickle state file
    :param configuration the MiG configuration object
    :return: void
    """

    filename = os.path.basename(jupyter_mount_path)
    link_home = configuration.sessid_to_jupyter_mount_link_home
    # Remove jupyter mount session symlinks for the default sftp service
    for link in os.listdir(link_home):
        if link in filename:
            delete_symlink(os.path.join(link_home, link),
                           configuration.logger)

    # Remove subsys sftp files
    if configuration.site_enable_sftp_subsys:
        auth_dir = os.path.join(configuration.mig_system_files,
                                'jupyter_mount')
        for auth_file in os.listdir(auth_dir):
            if auth_file.split('.authorized_keys')[0] in filename:
                delete_file(os.path.join(auth_dir, auth_file),
                            configuration.logger)

    # Remove old pickle state file
    delete_file(jupyter_mount_path, configuration.logger)


def get_newest_mount(jupyter_mounts):
    """
    Finds the most recent jupyter mount
    :param jupyter_mounts: Expects a list of jupyter_mount
    dictionaries. Furthermore that each dictionary has a state key that contains
    the unpickled content of a jupyter state file.
    :return: (newest_mount, [older_mounts]),
    if jupyter_mounts is empty (None, []) is returned.
    """
    if not jupyter_mounts:
        return None, []

    old_mounts = []
    latest = jupyter_mounts.pop(0)
    for mount in jupyter_mounts:
        if int(latest['state']['CREATED_TIMESTAMP']) \
                < int(mount['state']['CREATED_TIMESTAMP']):
            old_mounts.append(latest)
            latest = mount
        else:
            old_mounts.append(mount)
    return latest, old_mounts


def get_host_from_service(configuration, service, base_url=None):
    """
    Returns a URL from one of the services available hosts,
    if no active host is found None is returned.
    :param configuration: The MiG Configuration object
    :param service: A service object that an active hosts should be found from
    :param base_url: An optional postfix URL path that will be appended to the selected service host
    when trying to connect to the service.
    :return: url string or None
    """
    _logger = configuration.logger
    hosts = service['service_hosts'].split(" ")
    _logger.info("hosts %s" % hosts)
    while hosts:
        if len(hosts) == 1:
            rng = 0
        else:
            rng = random.randrange(0, len(hosts) - 1)
        try:
            with requests.session() as session:
                _logger.info("requsting url: %s%s" % (hosts[rng], base_url))
                if base_url:
                    session.get(hosts[rng] + base_url)
                else:
                    session.get(hosts[rng])
                return hosts[rng]
        except requests.ConnectionError as err:
            _logger.error("Failed to establish connection to %s error %s" %
                          (hosts[rng], err))
            hosts.pop(rng)
    return None


def jupyter_host(configuration, output_objects, user, url):
    """
    Returns the users jupyterhub host
    :param configuration: the MiG Configuration object
    :param output_objects:
    :param user: the user identifier used in the Remote-User header to
    authenticate against the jupyterhub server
    :param url: the target url of the jupyter host
    :return: output_objects and a 200 OK status for the webserver to return
    to the client
    """
    _logger = configuration.logger
    _logger.info("User: %s finished, redirecting to the jupyter host at: %s"
                 % (user, url))
    headers = [('Location', url), ('Remote-User', user)]
    output_objects.append({'object_type': 'start', 'headers': headers})
    return (output_objects, returnvalues.OK)


def jupyterhub_session_post_request(session, url, params=None, **kwargs):
    """
    Sends a post request to an url
    :param session: the session object that can be used to conduct the post request
    :param url: the designated URL that the post request is sent to
    :param params: parameters to pass to the post request
    :return: the response object from the post request
    """
    if not params:
        params = {}

    if "_xsrf" in session.cookies:
        params = {"_xsrf": session.cookies['_xsrf']}

    return session.post(url, params=params, **kwargs)


def reset(configuration):
    """Helper function to clean up all jupyter directories and mounts
    :param configuration: the MiG Configuration object
    """
    configuration = get_configuration_object()
    auth_path = os.path.join(configuration.mig_system_files,
                             'jupyter_mount')
    mnt_path = configuration.jupyter_mount_files_dir
    link_path = configuration.sessid_to_jupyter_mount_link_home
    if os.path.exists(auth_path):
        shutil.rmtree(auth_path)

    if os.path.exists(mnt_path):
        shutil.rmtree(mnt_path)

    if os.path.exists(link_path):
        shutil.rmtree(link_path)


def valid_jupyter_service(configuration, service):
    """
    Function that validates that the
    passed service is correctly structured.
    :param configuration: the MiG Configuration object
    :param service: a service dictionary object that describes a jupyter service
    """
    _logger = configuration.logger
    if not isinstance(service, dict):
        _logger.error('The jupyter service %s has an incorrect structure %s,'
                      ' requires dictionary' % (service, type(service)))
        return False

    if 'service_name' not in service:
        _logger.error(
            "The jupyter service %s is missing a required service_name key"
            % service)
        return False

    if 'service_hosts' not in service:
        _logger.error(
            "The jupyter service %s is missing a required hosts key"
            % service)
        return False
    return True


def signature():
    """Signature of the main function"""
    defaults = {
        'service': REJECT_UNSET
    }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )

    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.debug("User: %s executing %s" % (client_id, op_name))
    if not configuration.site_enable_jupyter:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The Jupyter service is not enabled on the system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not configuration.site_enable_sftp_subsys and not \
            configuration.site_enable_sftp:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The required sftp service is not enabled on the system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if configuration.site_enable_sftp:
        sftp_port = configuration.user_sftp_port

    if configuration.site_enable_sftp_subsys:
        sftp_port = configuration.user_sftp_subsys_port

    requested_service = accepted['service'][-1]
    service = {k: v for options in configuration.jupyter_services
               for k, v in options.items()
               if options['service_name'] == requested_service}

    if not service:
        valid_services = [options['name']
                          for options in configuration.jupyter_services]
        output_objects.append(
            {'object_type': 'error_text',
             'text': '%s is not a valid jupyter service, '
             'allowed include %s' % (requested_service, valid_services)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    valid_service = valid_jupyter_service(configuration, service)
    if not valid_service:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'The service %s appears to be misconfigured, '
             'please contact a system administrator about this issue'
             % requested_service}
        )
        return (output_objects, returnvalues.SYSTEM_ERROR)

    host = get_host_from_service(configuration, service, base_url="/%s" % service["service_name"])
    # Get an active jupyterhost
    if not host:
        logger.error("No active jupyterhub host could be found")
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Failed to establish connection to the %s Jupyter service' %
             service['service_name']})
        output_objects.append({'object_type': 'link',
                               'destination': 'jupyter.py',
                               'text': 'Back to Jupyter services overview'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    remote_user = unescape(os.environ.get('REMOTE_USER', '')).strip()
    if not remote_user:
        logger.error("Can't connect to jupyter with an empty REMOTE_USER "
                     "environment variable")
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Failed to establish connection to the Jupyter service'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    # Ensure the remote_user dict can be http posted
    remote_user = "%s" % remote_user

    # TODO, activate admin info
    # remote_user = {'USER': username, 'IS_ADMIN': is_admin(client_id,
    #                                                      configuration,
    # logger)}

    # Regular sftp path
    mnt_path = os.path.join(configuration.jupyter_mount_files_dir, client_dir)
    # Subsys sftp path
    subsys_path = os.path.join(configuration.mig_system_files,
                               'jupyter_mount')
    # sftp session path
    link_home = configuration.sessid_to_jupyter_mount_link_home

    user_home_dir = os.path.join(configuration.user_home, client_dir)

    # Preparing prerequisites
    if not os.path.exists(mnt_path):
        os.makedirs(mnt_path)

    if not os.path.exists(link_home):
        os.makedirs(link_home)

    if configuration.site_enable_sftp_subsys:
        if not os.path.exists(subsys_path):
            os.makedirs(subsys_path)

    # Make sure ssh daemon does not complain
    tighten_key_perms(configuration, client_id)

    url_base = urljoin(host, service['service_name'])
    url_home = urljoin(url_base, '/home')
    url_auth = urljoin(url_base, '/hub/login')
    url_data = urljoin(url_base, '/hub/set-user-data')

    # Does the client home dir contain an active mount key
    # If so just keep on using it.
    jupyter_mount_files = [os.path.join(mnt_path, jfile) for jfile in
                           os.listdir(mnt_path)
                           if jfile.endswith('.jupyter_mount')]

    logger.info("User: %s mount files: %s"
                % (client_id, "\n".join(jupyter_mount_files)))
    logger.debug("Remote-User %s" % remote_user)
    active_mounts = []
    for jfile in jupyter_mount_files:
        jupyter_dict = unpickle(jfile, logger)
        if not jupyter_dict:
            # Remove failed unpickle
            logger.error("Failed to unpickle %s removing it" % jfile)
            remove_jupyter_mount(jfile, configuration)
        else:
            # Mount has been timed out
            if not is_active(jupyter_dict):
                remove_jupyter_mount(jfile, configuration)
            else:
                # Valid mount
                active_mounts.append({'path': jfile, 'state': jupyter_dict})

    logger.debug("User: %s active keys: %s" %
                 (client_id,
                  "\n".join([mount['path'] for mount in active_mounts])))

    # If multiple are active, remove oldest
    active_mount, old_mounts = get_newest_mount(active_mounts)
    for mount in old_mounts:
        remove_jupyter_mount(mount['path'], configuration)

    # A valid active key is already present redirect straight to the jupyter
    # service, pass most recent mount information
    if active_mount is not None:
        mount_dict = mig_to_mount_adapt(active_mount['state'])
        user_dict = mig_to_user_adapt(active_mount['state'])
        logger.debug("Existing header values, Mount: %s User: %s"
                     % (mount_dict, user_dict))

        auth_header = {'Remote-User': remote_user}
        user_post_data = {
            'mount_data': mount_dict,
            'user_data': user_dict
        }
        # TODO, ask David if this needed in the future?
        if configuration.site_enable_workflows:
            workflows_dict = mig_to_workflows_adapt(active_mount['state'])
            if not workflows_dict:
                # No cached workflows session could be found -> refresh with a
                # one
                workflow_session_id = get_workflow_session_id(configuration,
                                                              client_id)
                if not workflow_session_id:
                    workflow_session_id = create_workflow_session_id(configuration,
                                                                     client_id)
                # TODO get these dynamically
                workflows_url = configuration.migserver_https_sid_url + \
                    '/cgi-sid/jsoninterface.py?output_format=json'
                workflows_dict = {
                    'WORKFLOWS_URL': workflows_url,
                    'WORKFLOWS_SESSION_ID': workflow_session_id}

            logger.debug("Existing header values, Workflows: %s"
                         % workflows_dict)
            user_post_data['workflows_data'] = {'Session': workflows_dict}

        with requests.session() as session:
            # Refresh cookies
            session.get(url_base)
            # Authenticate and submit data
            response = jupyterhub_session_post_request(session, url_auth, headers=auth_header)
            if response.status_code == 200:
                for user_data_type, user_data in user_post_data.items():
                    response = jupyterhub_session_post_request(url_data, json={user_data_type: user_data})
                    if response.status_code != 200:
                        logger.error(
                            "Jupyter: User %s failed to submit data %s to %s"
                            % (client_id, user_data, url_data))
            else:
                logger.error(
                    "Jupyter: User %s failed to authenticate against %s"
                    % (client_id, url_auth))

        # Redirect client to jupyterhub
        return jupyter_host(configuration, output_objects, remote_user,
                            url_home)

    # Create a new keyset
    # Create login session id
    session_id = generate_random_ascii(2*session_id_bytes,
                                       charset='0123456789abcdef')

    # Generate private/public keys
    (mount_private_key, mount_public_key) = generate_ssh_rsa_key_pair(
        encode_utf8=True)

    # Known hosts
    sftp_addresses = socket.gethostbyname_ex(
        configuration.user_sftp_show_address or socket.getfqdn())

    # Subsys sftp support
    if configuration.site_enable_sftp_subsys:
        # Restrict possible mount agent
        auth_content = []
        restrict_opts = 'no-agent-forwarding,no-port-forwarding,no-pty,'
        restrict_opts += 'no-user-rc,no-X11-forwarding'
        restrictions = '%s' % restrict_opts
        auth_content.append('%s %s\n' % (restrictions, mount_public_key))
        # Write auth file
        write_file('\n'.join(auth_content),
                   os.path.join(subsys_path, session_id
                                + '.authorized_keys'), logger, umask=0o27)

    logger.debug("User: %s - Creating a new jupyter mount keyset - "
                 "private_key: %s public_key: %s "
                 % (client_id, mount_private_key, mount_public_key))

    jupyter_dict = {
        'MOUNT_HOST': configuration.short_title,
        'SESSIONID': session_id,
        'USER_CERT': client_id,
        # don't need fraction precision, also not all systems provide fraction
        # precision.
        'CREATED_TIMESTAMP': int(time.time()),
        'MOUNTSSHPRIVATEKEY': mount_private_key,
        'MOUNTSSHPUBLICKEY': mount_public_key,
        # Used by the jupyterhub to know which host to mount against
        'TARGET_MOUNT_ADDR': "@" + sftp_addresses[0] + ":",
        'PORT': sftp_port
    }
    client_email = extract_field(client_id, 'email')
    if client_email:
        jupyter_dict.update({'USER_EMAIL': client_email})

    if configuration.site_enable_workflows:
        workflow_session_id = get_workflow_session_id(configuration, client_id)
        if not workflow_session_id:
            workflow_session_id = create_workflow_session_id(configuration,
                                                             client_id)
        # TODO get these dynamically
        workflows_url = configuration.migserver_https_sid_url + \
            '/cgi-sid/jsoninterface.py?output_format=json'

        jupyter_dict.update({
            'WORKFLOWS_URL': workflows_url,
            'WORKFLOWS_SESSION_ID': workflow_session_id
        })

    # Only post the required keys, adapt to API expectations
    mount_dict = mig_to_mount_adapt(jupyter_dict)
    user_dict = mig_to_user_adapt(jupyter_dict)
    workflows_dict = mig_to_workflows_adapt(jupyter_dict)
    logger.debug("User: %s Mount header: %s" % (client_id, mount_dict))
    logger.debug("User: %s User header: %s" % (client_id, user_dict))
    if workflows_dict:
        logger.debug("User: %s Workflows header: %s" % (client_id,
                                                        workflows_dict))

    # Auth and pass a new set of valid mount keys
    auth_header = {'Remote-User': remote_user}
    user_post_data = {
        'mount_data': mount_dict,
        'user_data': user_dict
    }

    if workflows_dict:
        user_post_data['workflows_data'] = {'Session': workflows_dict}

    # First login
    with requests.session() as session:
        # Refresh cookies
        session.get(url_base)
        # Authenticate
        response = jupyterhub_session_post_request(session, url_auth, headers=auth_header)
        if response.status_code == 200:
            for user_data_type, user_data in user_post_data.items():
                response = jupyterhub_session_post_request(session, url_data, json={user_data_type: user_data})
                if response.status_code != 200:
                    logger.error("Jupyter: User %s failed to submit data %s to %s"
                                % (client_id, user_data, url_data))
        else:
            logger.error("Jupyter: User %s failed to authenticate against %s"
                         % (client_id, url_auth))

    # Update pickle with the new valid key
    jupyter_mount_state_path = os.path.join(mnt_path,
                                            session_id + '.jupyter_mount')

    pickle(jupyter_dict, jupyter_mount_state_path, logger)

    # Link jupyter pickle state file
    linkdest_new_jupyter_mount = os.path.join(mnt_path,
                                              session_id + '.jupyter_mount')

    linkloc_new_jupyter_mount = os.path.join(link_home,
                                             session_id + '.jupyter_mount')
    make_symlink(linkdest_new_jupyter_mount, linkloc_new_jupyter_mount, logger)

    # Link userhome
    linkloc_user_home = os.path.join(link_home, session_id)
    make_symlink(user_home_dir, linkloc_user_home, logger)

    return jupyter_host(configuration, output_objects, remote_user, url_home)


if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    if not os.environ.get('MIG_CONF', ''):
        conf_path = os.path.join(os.path.dirname(sys.argv[0]),
                                 '..', '..', 'server', 'MiGserver.conf')
        os.environ['MIG_CONF'] = conf_path
    conf = get_configuration_object()
    request_uri = "/dag/user/rasmus.munk@nbi.ku.dk"
    if sys.argv[1:]:
        if sys.argv[1] == 'reset':
            reset(conf)
            exit(0)
        request_uri = sys.argv[1]
    os.environ['REQUEST_URI'] = request_uri
    query_string = ''
    if sys.argv[2:]:
        query_string = sys.argv[2]
    os.environ['QUERY_STRING'] = query_string
    client_id = "/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=" \
                "Rasmus Munk/emailAddress=rasmus.munk@nbi.ku.dk"
    if sys.argv[3:]:
        client_id = sys.argv[3]
    os.environ['SSL_CLIENT_S_DN'] = client_id
    print(main(client_id, {}))
