
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jupyter - Launch an interactive Jupyter session
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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
This backend makes two requests to the target url specified by the
configuration.jupyter_url variable the first requests authenticates against the
jupyterhub server, it passes the Remote-User header with the client_id's email.
The second request takes the newly instantiated ssh keyset and passes it to the
jupyterhub server via the Mount header.
Subsequently any potentially old keysets for this user is removed and the new
keyset is commited to the users configuration.jupyter_mount_files_dir
directory. Finally this active keyset is linked to the directory where the sftp
will check for a valid keyset and the users homedrive is linked to the same
location.

Finally the user is redirected to the jupyterhub home page where a new notebook
server can be instantiated and mount the users linked homedrive with the passed
keyset.
"""

import os
import socket
import sys
import time
import shutil
import requests

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.conf import get_configuration_object
from shared.defaults import session_id_bytes
from shared.fileio import make_symlink, pickle, unpickle, write_file
from shared.functional import validate_input_and_cert
from shared.httpsclient import unescape
from shared.init import initialize_main_variables
from shared.pwhash import generate_random_ascii
from shared.ssh import generate_ssh_rsa_key_pair, tighten_key_perms


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


def mig_to_mount_adapt(mig):
    """
    :param mig: expects a dictionary containing mig state keys including,
    MOUNT_HOST, SESSIONID, MOUNTSSHPRIVATEKEY and TARGET_MOUNT_ADDR
    :return: returns a dictionary
    """
    mount = {
        'HOST': mig['MOUNT_HOST'],
        'USERNAME': mig['SESSIONID'],
        'PRIVATEKEY': mig['MOUNTSSHPRIVATEKEY'],
        'PATH': mig['TARGET_MOUNT_ADDR']
    }
    return mount


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
            os.remove(os.path.join(link_home, link))

    # Remove subsys sftp files
    if configuration.site_enable_sftp_subsys:
        auth_dir = os.path.join(configuration.mig_system_files,
                                'jupyter_mount')
        for auth_file in os.listdir(auth_dir):
            if auth_file.split('.authorized_keys')[0] in filename:
                os.remove(os.path.join(auth_dir, auth_file))

    # Remove old pickle state file
    os.remove(jupyter_mount_path)


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


def jupyter_host(configuration, output_objects, user):
    """
    Returns the users jupyterhub host
    :param configuration: the MiG Configuration object
    :param output_objects:
    :param user: the user identifier used in the Remote-User header to
    authenticate against the jupyterhub server
    :return: output_objects and a 200 OK status for the webserver to return
    to the client
    """
    configuration.logger.info(
        "User: %s finished, redirecting to the jupyter host" % user)
    status = returnvalues.OK
    home = configuration.jupyter_base_url + '/home'
    headers = [('Location', home), ('Remote-User', user)]
    output_objects.append({'object_type': 'start', 'headers': headers})
    return (output_objects, status)


def reset():
    """
    Helper function to clean up all jupyter directories and mounts
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


def signature():
    """Signature of the main function"""
    return ['', {}]


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

    logger.debug("User: %s executing %s", client_id, op_name)
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

    # Test target jupyter url
    session = requests.session()
    try:
        session.get(configuration.jupyter_url)
    except requests.ConnectionError as err:
        logger.error("Failed to establish connection to %s error %s",
                     configuration.jupyter_url, err)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Failed to establish connection to the Jupyter service'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    username = unescape(os.environ.get('REMOTE_USER', '')).strip()
    # TODO, activate admin info
    # remote_user = {'USER': username, 'IS_ADMIN': is_admin(client_id,
    #                                                      configuration,
    # logger)}

    remote_user = username
    if remote_user == '':
        logger.error("Can't connect to jupyter with an empty REMOTE_USER "
                     "environment variable")
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Failed to establish connection to the Jupyter service'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    # Ensure the remote_user dict can be http posted
    remote_user = str(remote_user)

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

    url_jup = configuration.jupyter_url
    url_base = configuration.jupyter_base_url
    url_auth = url_jup + url_base + '/hub/home'
    url_mount = url_jup + url_base + '/hub/mount'

    # Does the client home dir contain an active mount key
    # If so just keep on using it.
    jupyter_mount_files = [os.path.join(mnt_path, jfile) for jfile in
                           os.listdir(mnt_path)
                           if jfile.endswith('.jupyter_mount')]

    logger.info("User: %s mount files: %s", client_id,
                "\n".join(jupyter_mount_files))
    logger.debug("Remote-User %s", remote_user)
    active_mounts = []
    for jfile in jupyter_mount_files:
        jupyter_dict = unpickle(jfile, logger)
        if not jupyter_dict:
            # Remove failed unpickle
            logger.error("Failed to unpickle %s removing it", jfile)
            remove_jupyter_mount(jfile, configuration)
        else:
            # Mount has been timed out
            if not is_active(jupyter_dict):
                remove_jupyter_mount(jfile, configuration)
            else:
                # Valid mount
                active_mounts.append({'path': jfile, 'state': jupyter_dict})

    logger.debug("User: %s active keys: %s", client_id,
                 "\n".join([mount['path'] for mount in active_mounts]))

    # If multiple are active, remove oldest
    active_mount, old_mounts = get_newest_mount(active_mounts)
    for mount in old_mounts:
        remove_jupyter_mount(mount['path'], configuration)

    # A valid active key is already present redirect straight to the jupyter
    # service, pass most recent mount information
    if active_mount is not None:
        mount_dict = mig_to_mount_adapt(active_mount['state'])
        logger.debug("Existing keys %s", mount_dict)
        auth_mount_header = {'Remote-User': remote_user, 'Mount': str(
            mount_dict)}

        session = requests.session()
        # Authenticate
        session.get(url_auth, headers=auth_mount_header)
        # Provide the active homedrive mount information
        session.post(url_mount, headers=auth_mount_header)

        # Redirect client to jupyterhub
        return jupyter_host(configuration, output_objects, remote_user)

    # Create a new keyset
    # Create login session id
    session_id = generate_random_ascii(2*session_id_bytes,
                                       charset='0123456789abcdef')

    # Generate private/public keys
    (mount_private_key, mount_public_key) = generate_ssh_rsa_key_pair()

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
                                + '.authorized_keys'), logger, umask=027)

    logger.debug("User: %s - Creating a new jupyter mount keyset - "
                 "private_key: %s public_key: %s ", client_id,
                 mount_private_key, mount_public_key)

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
        'TARGET_MOUNT_ADDR': "@" + sftp_addresses[0] + ":"
    }

    # Only post the required keys, adapt to API expectations
    mount_dict = mig_to_mount_adapt(jupyter_dict)
    logger.debug("User: %s Mount header: %s", client_id, mount_dict)

    # Auth and pass a new set of valid mount keys
    auth_mount_header = {'Remote-User': remote_user,
                         'Mount': str(mount_dict)}

    # First login
    session = requests.session()
    session.get(url_auth, headers=auth_mount_header)
    # Provide homedrive mount information
    session.post(url_mount, headers=auth_mount_header)

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

    return jupyter_host(configuration, output_objects, remote_user)


if __name__ == "__main__":
    if not os.environ.get('MIG_CONF', ''):
        conf_path = os.path.join(os.path.dirname(sys.argv[0]),
                                 '..', '..', 'server', 'MiGserver.conf')
        os.environ['MIG_CONF'] = conf_path
    request_uri = "/dag/user/rasmus.munk@nbi.ku.dk"
    if sys.argv[1:]:
        if sys.argv[1] == 'reset':
            reset()
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
    print main(client_id, {})
