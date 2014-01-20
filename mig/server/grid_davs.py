#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_davs - secure DAV server providing access to MiG user homes
# Copyright (C) 2014  The MiG Project lead by Brian Vinter
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

"""Provide secure DAV access to MiG user homes"""

import BaseHTTPServer
#import SimpleHTTPServer
import SocketServer
#import base64
#import glob
#import logging
import ssl
import os
#import socket
import shutil
import sys
#import threading
#import time
#from StringIO import StringIO

#import pywebdav.lib
from pywebdav.server.fileauth import DAVAuthHandler
#from pywebdav.server.mysqlauth import MySQLAuthHandler
from pywebdav.server.fshandler import FilesystemHandler
#from pywebdav.server.daemonize import startstop

#from pywebdav.lib.INI_Parse import Configuration
#from pywebdav.lib import VERSION, AUTHOR


from shared.base import client_dir_id, client_alias, invisible_path
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, strip_root, \
     flags_to_mode, acceptable_chmod, refresh_users
from shared.useradm import check_password_hash


configuration, logger = None, None


class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

    pass


def setup_dummy_config(**kw):
    """DAV config object helper"""

    class DummyConfigDAV:
        """Dummy DAV config"""
        def __init__(self, **kw):
            self.__dict__.update(**kw)

        def getboolean(self, name):
            """Get boolean value from config"""
            return (str(getattr(self, name, 0)) in ('1', "yes", "true", "on",
                                                    "True"))

    class DummyConfig:
        """Dummy config"""
        DAV = DummyConfigDAV(**kw)

    return DummyConfig()


def init_filesystem_handler(handler, directory, host, port, verbose):
    """Setup up file system handler to take data from user home"""

    dav_conf_dict = handler.server_conf.dav_cfg
    
    # dispatch directory and host to the filesystem handler
    # This handler is responsible from where to take the data
    handler.IFACE_CLASS = FilesystemHandler(directory, 'http://%s:%s/' % \
                                            (host, port), verbose)

    if not handler._config.DAV.getboolean('lockemulation'):
        logger.info('Deactivated LOCK, UNLOCK (WebDAV level 2) support')

    handler.IFACE_CLASS.mimecheck = True
    if not handler._config.DAV.getboolean('mimecheck'):
        handler.IFACE_CLASS.mimecheck = False
        logger.info('Disabled mimetype sniffing (All files will have type '
                    'application/octet-stream)')

    if dav_conf_dict['baseurl']:
        logger.info('Using %(baseurl)s as base url for PROPFIND requests' % \
                     dav_conf_dict)
    handler.IFACE_CLASS.baseurl = dav_conf_dict['baseurl']


class MiGDAVAuthHandler(DAVAuthHandler):
    """
    Provides MiG specific authentication based on parameters. The calling
    class has to inject password and username into this.
    (Variables: auth_user and auth_pass)

    Override simple static user/password auth with a simple password lookup in
    the MiG user DB.
    """

    # Do not forget to set IFACE_CLASS by caller
    # ex.: IFACE_CLASS = FilesystemHandler('/tmp', 'http://localhost/')
    verbose = False
    users = None
    authenticated_user = None

    def _log(self, message):
        print "in _log"
        if self.verbose:
            logger.info(message)

    def get_userinfo(self, username, password, command):
        """authenticate user against user DB"""

        refresh_users(configuration)
        usermap = {}
        for user_obj in self.server_conf.daemon_conf['users']:
            if not usermap.has_key(user_obj.username):
                usermap[user_obj.username] = []
            usermap[user_obj.username].append(user_obj)
        self.users = usermap
        logger.debug("get_userinfo found users: %s" % self.users)

        host = self.server_conf.user_davs_address.strip()
        port = self.server_conf.user_davs_port
        verbose = self._config.DAV.getboolean('verbose')
        
        # TODO: add pubkey support

        offered = None
        if 'password' in self.server_conf.user_davs_auth and \
               self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = password
            for entry in entries:
                if entry.password is not None:
                    allowed = entry.password
                    logger.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        logger.info("Authenticated %s" % username)
                        self.authenticated_user = username
                        # dispatch directory and host to the filesystem handler
                        # responsible for deciding where to take the data from

                        # list of User login objects for user_name
                        entries = usermap[self.authenticated_user]
                        for entry in entries:
                            if entry.chroot:
                                directory = os.path.join(
                                    self.server_conf.user_home, entry.home)
                                logger.info("switching to user home %s" % \
                                            directory)
                                init_filesystem_handler(self, directory, host,
                                                        port, verbose)
                                break
                        return 1
        err_msg = "Password authentication failed for %s" % username
        logger.error(err_msg)
        print err_msg
        return 0


def run(configuration):
    """SSL wrap HTTP server for secure DAV access"""

    handler = MiGDAVAuthHandler

    # Pass conf options to DAV handler in required object format

    dav_conf_dict = configuration.dav_cfg
    dav_conf_dict['host'] = configuration.user_davs_address
    dav_conf_dict['port'] = configuration.user_davs_port
    dav_conf = setup_dummy_config(**dav_conf_dict)
    # inject options
    handler.server_conf = configuration
    handler._config = dav_conf

    server = ThreadedHTTPServer

    directory = dav_conf_dict['directory'].strip().rstrip('/')
    verbose = dav_conf.DAV.getboolean('verbose')
    noauth = dav_conf.DAV.getboolean('noauth')
    host = dav_conf_dict['host'].strip()
    port = dav_conf_dict['port']

    if not os.path.isdir(directory):
        logger.error('%s is not a valid directory!' % directory)
        return sys.exit(233)

    # basic checks against wrong hosts
    if host.find('/') != -1 or host.find(':') != -1:
        logger.error('Malformed host %s' % host)
        return sys.exit(233)

    # no root directory
    if directory == '/':
        logger.error('Root directory not allowed!')
        sys.exit(233)

    # put some extra vars
    handler.verbose = verbose
    if noauth:
        logger.warning('Authentication disabled!')
        handler.DO_AUTH = False

    logger.info('Serving data from %s' % directory)

    init_filesystem_handler(handler, directory, host, port, verbose)

    # initialize server on specified port
    runner = server((host, port), handler)
    # Wrap in SSL

    cert_path = configuration.user_davs_key
    if not os.path.isfile(cert_path):
        logger.error('No such server key: %s' % cert_path)
        sys.exit(1)
    runner.socket = ssl.wrap_socket(runner.socket,
                                   certfile=cert_path,
                                   server_side=True)
    print('Listening on %s (%i)' % (host, port))

    try:
        runner.serve_forever()
    except KeyboardInterrupt:
        logger.info('Killed by user')


if __name__ == "__main__":
    configuration = get_configuration_object()
    logger = configuration.logger
    # TODO: dynamically switch to user home directory
    configuration.dav_cfg = {
               'verbose': False,
               'directory': configuration.user_home,
               'no_auth': False,
               'user': '',
               'password': '',
               'daemonize': False,
               'daemonaction': 'start',
               'counter': 0,
               'mysql': False,
               'lockemulation': True,
               'http_response_use_iterator':  True,
               'chunked_http_response': True,
               'mimecheck': True,
               'baseurl': '',
        }

    logger = configuration.logger
    if not configuration.site_enable_davs:
        err_msg = "DAVS access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)

    chroot_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base),
                         os.path.abspath(configuration.vgrid_files_home),
                         os.path.abspath(configuration.resource_home)]
    # Don't allow chmod in dirs with CGI access as it introduces arbitrary
    # code execution vulnerabilities
    chmod_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base)]
    configuration.daemon_conf = {
        'address': configuration.user_davs_address,
        'port': configuration.user_davs_port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_davs_auth,
        'allow_publickey': 'publickey' in configuration.user_davs_auth,
        'user_alias': configuration.user_davs_alias,
        'users': [],
        'time_stamp': 0,
        'logger': logger,
        }

    print """
Running grid davs server for user dav access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    logger.info("starting DAV server")
    try:
        run(configuration)
    except KeyboardInterrupt:
        logger.info("received interrupt - shutting down")
    except Exception, exc:
        logger.error("exiting on unexpected exception: %s" % exc)
