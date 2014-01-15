#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_dav - DAV server providing access to MiG user homes
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

"""Provide DAV access to MiG user homes"""

import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import base64
import glob
import logging
import ssl
import os
import socket
import shutil
import sys
import threading
import time
from StringIO import StringIO

import pywebdav.lib
from pywebdav.server.fileauth import DAVAuthHandler
#from pywebdav.server.mysqlauth import MySQLAuthHandler
from pywebdav.server.fshandler import FilesystemHandler
#from pywebdav.server.daemonize import startstop

from pywebdav.lib.INI_Parse import Configuration
from pywebdav.lib import VERSION, AUTHOR


from shared.base import client_dir_id, client_alias, invisible_path
from shared.conf import get_configuration_object
from shared.useradm import ssh_authpasswords, get_ssh_authpasswords, \
     check_password_hash, extract_field, generate_password_hash


configuration, logger = None, None


class ThreadedHTTPServer(SocketServer.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

    pass


def setupDummyConfig(**kw):

    class DummyConfigDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

        def getboolean(self, name):
            return (str(getattr(self, name, 0)) in ('1', "yes", "true", "on", "True"))

    class DummyConfig:
        DAV = DummyConfigDAV(**kw)

    return DummyConfig()


class User(object):
    """User login class to hold a single valid login for a user"""
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None):
        self.username = username
        self.password = password
        self.chroot = chroot
        self.public_key = public_key
        if type(public_key) in (str, unicode):
            # We already checked that key is valid if we got here
            self.public_key = parse_pub_key(public_key)

        self.home = home
        if self.home is None:
            self.home = self.username


class MiGDAVAuthHandler(DAVAuthHandler):
    """
    Provides MiG specific authentication based on parameters. The calling
    class has to inject password and username into this.
    (Variables: auth_user and auth_pass)

    Override simple static user/password auth with a simple password lookup in
    the MiG user DB.
    """

    # TMP! load from DB
    allow_password = True
    users = {'jonas': [User('jonas', generate_password_hash('test1234'))]}

    # Do not forget to set IFACE_CLASS by caller
    # ex.: IFACE_CLASS = FilesystemHandler('/tmp', 'http://localhost/')
    verbose = False

    def _log(self, message):
        if self.verbose:
            log.info(message)

    def get_userinfo(self, user, pw, command):
        """authenticate user against user DB"""

        username, password = user, pw

        offered = None
        if self.allow_password and self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = password
            for entry in entries:
                if entry.password is not None:
                    allowed = entry.password
                    logging.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        logging.info("Authenticated %s" % username)
                        self.authenticated_user = username
                        return 1
        err_msg = "Password authentication failed for %s" % username
        logging.error(err_msg)
        print err_msg
        return 0


def run(conf):
    """SSL wrap HTTP server for secure DAV access"""

    handler = MiGDAVAuthHandler

    # Pass conf options to DAV handler in required object format

    dav_conf_dict = conf['dav_cfg']
    for name in ('host', 'port'):
        dav_conf_dict[name] = conf[name]
    dav_conf = setupDummyConfig(**dav_conf_dict)
    # injecting options
    handler._config = dav_conf

    server = ThreadedHTTPServer

    directory = dav_conf_dict['directory']
    directory = directory.strip()
    directory = directory.rstrip('/')
    verbose = dav_conf.DAV.getboolean('verbose')
    noauth = dav_conf.DAV.getboolean('noauth')
    host = conf['host']
    host = host.strip()
    port = conf['port']

    if not os.path.isdir(directory):
        logging.error('%s is not a valid directory!' % directory)
        return sys.exit(233)

    # basic checks against wrong hosts
    if host.find('/') != -1 or host.find(':') != -1:
        logging.error('Malformed host %s' % host)
        return sys.exit(233)

    # no root directory
    if directory == '/':
        logging.error('Root directory not allowed!')
        sys.exit(233)

    # dispatch directory and host to the filesystem handler
    # This handler is responsible from where to take the data
    handler.IFACE_CLASS = FilesystemHandler(directory, 'http://%s:%s/' % \
                                            (host, port), verbose)

    # put some extra vars
    handler.verbose = verbose
    if noauth:
        logging.warning('Authentication disabled!')
        handler.DO_AUTH = False

    logging.info('Serving data from %s' % directory)

    if not dav_conf.DAV.getboolean('lockemulation'):
        logging.info('Deactivated LOCK, UNLOCK (WebDAV level 2) support')

    handler.IFACE_CLASS.mimecheck = True
    if not dav_conf.DAV.getboolean('mimecheck'):
        handler.IFACE_CLASS.mimecheck = False
        logging.info('Disabled mimetype sniffing (All files will have type application/octet-stream)')

    if dav_conf_dict['baseurl']:
        logging.info('Using %(baseurl)s as base url for PROPFIND requests' % \
                     dav_conf_dict)
    handler.IFACE_CLASS.baseurl = dav_conf_dict['baseurl']

    # initialize server on specified port
    runner = server((host, port), handler)
    # Wrap in SSL
    cert_path = os.path.join(conf['cert_base'], conf['cert_file'])
    runner.socket = ssl.wrap_socket(runner.socket,
                                   certfile=cert_path,
                                   server_side=True)
    print('Listening on %s (%i)' % (host, port))

    try:
        runner.serve_forever()
    except KeyboardInterrupt:
        logging.info('Killed by user')


def main(conf):
    """Run server"""
    if conf['log_path']:
        logging.basicConfig(path=conf['log_path'], level=conf['log_level'],
                            format=conf['log_format'])
    else:
        logging.basicConfig(level=conf['log_level'],
                            format=conf['log_format'])
    logging.info("starting DAV server")
    try:
        run(conf)
    except KeyboardInterrupt:
        logging.info("received interrupt - shutting down")
    except Exception, exc:
        logging.error("exiting on unexpected exception: %s" % exc)
        

if __name__ == "__main__":
    cfg = {'log_level': logging.INFO,
           'log_path': None,
           'log_format': '%(asctime)s %(levelname)s %(message)s',
           'host': 'localhost',
           'port': 4443,
           'cert_base': '../../MiG-certificates',
           'cert_file': 'localhost.pem',
           #'configfile': '',
           'dav_cfg': {
               'verbose': False,
               'directory': '/tmp',
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
               },
           }
    main(cfg)
