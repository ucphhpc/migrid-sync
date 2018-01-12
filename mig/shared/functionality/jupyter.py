#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jupyter - Launch an interactive Jupyter session
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
jupyterhub server, it passes the REMOTE_USER header with the client_id's email.
The second request takes the newly instantiated ssh keyset and passes it to the
jupyterhub server via the Mig-Mount header.
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
from binascii import hexlify

import requests

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, extract_field
from shared.functional import validate_input_and_cert
from shared.defaults import session_id_bytes
from shared.init import initialize_main_variables
from shared.ssh import generate_ssh_rsa_key_pair
from shared.fileio import make_symlink, pickle


# def safeinput_encode(input_str):
#    encoded_str = base64.b32encode(input_str)
#    return encoded_str.replace('=', '')
#
#
# def safeinput_decode(input_str):
#    # Encoder removed "=" padding to satisfy validate_input
#    # Pad with "="" according to:
#    # https://tools.ietf.org/html/rfc3548 :
#    # (1) the final quantum of encoding input is an integral multiple of 40
#    # bits; here, the final unit of encoded output will be an integral
#    # multiple of 8 characters with no "=" padding,
#
#    if len(input_str) % 8 != 0:
#        padlen = 8 - (len(input_str) % 8)
#        padding = "".join('=' for i in xrange(padlen))
#        decode_str = "%s%s" % (input_str, padding)
#    else:
#        decode_str = input_str
#
#    return base64.b32decode(decode_str)


def signature():
    """Signature of the main function"""
    defaults = {}
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

    logger.debug("Jupyter entry")

    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_jupyter:
        output_objects.append({'object_type': 'error_text', 'text':
            '''The Jupyter service is not enabled on the system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # TODO: change to site_enable_sftp OR site_enable_sftp_subsys when ready
    if not configuration.site_enable_sftp:
        output_objects.append({'object_type': 'error_text', 'text':
            '''The required sftp service is not enabled on the system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Test target jupyter url
    session = requests.session()
    try:
        session.get(configuration.jupyter_url)
    except requests.ConnectionError as err:
        logger.error("Failed to establish connection to %s error %s",
                    configuration.jupyter_url, err)
        output_objects.append(
            {'object_type': 'error_text',
             'text': '''Failed to establish connection to the Jupyter service'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    status = returnvalues.OK
    # Create login session id
    sessionid = hexlify(open('/dev/urandom').read(session_id_bytes))

    # Create ssh rsa keya and known_hosts
    mount_private_key = ""
    mount_public_key = ""
    mount_known_hosts = ""

    # Generate private/public keys
    (mount_private_key, mount_public_key) = generate_ssh_rsa_key_pair()

    # Known hosts
    sftp_addresses = socket.gethostbyname_ex(
        configuration.user_sftp_show_address or socket.getfqdn())
    mount_known_hosts = "%s,[%s]:%s" % (sftp_addresses[0],
                                        sftp_addresses[0],
                                        configuration.user_sftp_show_port)

    email = extract_field(client_id, 'email')
    logger.debug("Creating a new jupyter mount keyset: " + sessionid +
                 " private_key: " + mount_private_key + " public_key: " +
                 mount_public_key + " for user: " + client_id)

    jupyter_dict = {}
    jupyter_dict['USER_CERT'] = client_id
    jupyter_dict['SESSIONID'] = sessionid
    jupyter_dict['MOUNTSSHPUBLICKEY'] = mount_public_key
    jupyter_dict['MOUNTSSHPRIVATEKEY'] = mount_private_key
    jupyter_dict['MOUNTSSHKNOWNHOSTS'] = mount_known_hosts
    # Used by the jupyterhub to know which host to mount against
    jupyter_dict['TARGET_MOUNT_ADDR'] = "@" + sftp_addresses[0] + ":"

    # Auth and pass a new set of valid mount keys
    url_mount = configuration.jupyter_url + configuration.jupyter_base_url + \
                "/hub/mount"
    auth_header = {'REMOTE_USER': email}
    mount_header = {'Mig-Mount': str(jupyter_dict)}

    session = requests.session()
    # First login
    session.get(configuration.jupyter_url, headers=auth_header)
    # Provide homedrive mount information
    session.get(url_mount, headers=mount_header)

    # Create client dir that will store the active jupyter session file
    mnt_path = os.path.join(configuration.jupyter_mount_files_dir, client_dir)
    link_home = configuration.sessid_to_jupyter_mount_link_home
    if not os.path.exists(mnt_path):
        os.makedirs(mnt_path)

    # Cleanup any old .jupyter state files and symlinks from previous sessions
    for filename in os.listdir(mnt_path):
        if filename.endswith(".jupyter_mount"):
            # Remove the old symlinks that target the old pickle state file
            for link in os.listdir(link_home):
                if link in filename:
                    os.remove(os.path.join(link_home, link))

            # Remove old pickle state file
            os.remove(os.path.join(mnt_path, filename))

    # Update pickle with the new valid key
    jupyter_mount_state_path = os.path.join(mnt_path,
                                            sessionid + '.jupyter_mount')

    pickle(jupyter_dict, jupyter_mount_state_path, logger)

    # Link jupyter pickle state file
    linkdest_new_jupyter_mount = os.path.join(mnt_path,
                                              sessionid + '.jupyter_mount')

    linkloc_new_jupyter_mount = os.path.join(link_home,
                                             sessionid + '.jupyter_mount')
    make_symlink(linkdest_new_jupyter_mount, linkloc_new_jupyter_mount, logger)

    # Link userhome
    linkdest_user_home = os.path.join(configuration.user_home, client_dir)
    linkloc_user_home = os.path.join(link_home, sessionid)
    make_symlink(linkdest_user_home, linkloc_user_home, logger)

    # Redirect client to jupyterhub
    home = configuration.jupyter_base_url + "/hub/home"
    headers = [('Location', home)]
    output_objects.append({'object_type': 'start', 'headers': headers})
    return output_objects, status


if __name__ == "__main__":
    if not os.environ.get('MIG_CONF', ''):
        conf_path = os.path.join(os.path.dirname(sys.argv[0]),
                                 '..', '..', 'server', 'MiGserver.conf')
        os.environ['MIG_CONF'] = conf_path
    request_uri = "/dag/user/rasmus.munk@nbi.ku.dk"
    if sys.argv[1:]:
        request_uri = sys.argv[1]
    os.environ['REQUEST_URI'] = request_uri
    query_string = ''
    if sys.argv[2:]:
        query_string = sys.argv[2]
    os.environ['QUERY_STRING'] = query_string
    client_id = "/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Rasmus Munk/emailAddress=rasmus.munk@nbi.ku.dk"
    if sys.argv[3:]:
        client_id = sys.argv[3]
    os.environ['SSL_CLIENT_S_DN'] = client_id
    print main(client_id, {})
