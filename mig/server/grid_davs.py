#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_davs - secure DAV server providing access to MiG user homes
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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
import SocketServer
import logging
import os
import ssl
import sys
import time
import urlparse

try:
    from pywebdav.server.fileauth import DAVAuthHandler
    from pywebdav.server.fshandler import FilesystemHandler
    # from pywebdav.server.daemonize import startstop
    from pywebdav.lib.errors import DAV_NotFound
except ImportError:
    print "ERROR: the python pywebdav module is required for this daemon"
    sys.exit(1)

from shared.base import invisible_path
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, strip_root, \
     acceptable_chmod, refresh_users, hit_rate_limit, update_rate_limit, \
     expire_rate_limit
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
    handler.IFACE_CLASS = MiGFilesystemHandler(directory, 'http://%s:%s/' % \
                                               (host, port),
                                               handler.server_conf,
                                               handler._config, verbose)

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


class MiGFilesystemHandler(FilesystemHandler):
    """
    Overrides the default FilesystemHandler to include chroot support and
    hidden files like in other MiG file interfaces.
    """

    def __init__(self, directory, uri, server_conf, dav_conf, verbose=False):
        """Simply call parent constructor"""
        FilesystemHandler.__init__(self, directory, uri, verbose)
        self.root = directory
        self.daemon_conf = server_conf.daemon_conf
        self.chroot_exceptions = self.daemon_conf['chroot_exceptions']
        self.chmod_exceptions = self.daemon_conf['chmod_exceptions']

    # Use shared daemon fs helper functions
    
    def _get_fs_path(self, davs_path):
        """Wrap helper"""
        #logger.debug("get_fs_path: %s" % davs_path)
        reply = get_fs_path(davs_path, self.root, self.chroot_exceptions)
        logger.debug("get_fs_path returns: %s :: %s" % (davs_path, reply))
        return reply

    def _strip_root(self, davs_path):
        """Wrap helper"""
        #logger.debug("strip_root: %s" % davs_path)
        reply = strip_root(davs_path, self.root, self.chroot_exceptions)
        logger.debug("strip_root returns: %s :: %s" % (davs_path, reply))
        return reply
    
    def _acceptable_chmod(self, davs_path, mode):
        """Wrap helper"""
        #logger.debug("acceptable_chmod: %s" % davs_path)
        reply = acceptable_chmod(davs_path, mode, self.chmod_exceptions)
        logger.debug("acceptable_chmod returns: %s :: %s" % (davs_path, reply))
        return reply

    def uri2local(self, uri):
        """map uri in baseuri and local part"""

        uparts = urlparse.urlparse(uri)
        fileloc = uparts[2][1:]
        rel_path = os.path.join(fileloc)
        try:
            filename = self._get_fs_path(rel_path)
        except ValueError, vae:
            logger.warning("illegal path requested: %s :: %s" % (rel_path,
                                                                 vae))
            raise DAV_NotFound
        return filename

    def get_childs(self, uri, filter=None):
        """return the child objects as self.baseuris for the given URI.
        We override the listing to hide invisible_path hits.
        """
        
        fileloc = self.uri2local(uri)
        filelist = []        
        if os.path.exists(fileloc):
            if os.path.isdir(fileloc):
                try:
                    files = os.listdir(fileloc)
                except:
                    logger.warning("could not listfiles in %s" % uri)
                    raise DAV_NotFound
                
                for filename in files:
                    if invisible_path(filename):
                        continue
                    newloc = os.path.join(fileloc, filename)
                    filelist.append(self.local2uri(newloc))
                    
        logger.info('get_childs: Childs %s' % filelist)
        return filelist
                
    def get_data(self, uri, range=None):
        """return the content of an object"""
        reply = FilesystemHandler.get_data(self, uri, range)
        logger.info("returning get_data reply: %s" % reply)
        return reply

                
class MiGDAVAuthHandler(DAVAuthHandler):
    """
    Provides MiG specific authentication based on parameters. The calling
    class has to inject password and username into this.
    (Variables: auth_user and auth_pass)

    Override simple static user/password auth with a simple password lookup in
    the MiG user DB.
    """

    # TODO: add actual pubkey auth

    # Do not forget to set IFACE_CLASS by caller
    # ex.: IFACE_CLASS = FilesystemHandler('/tmp', 'http://localhost/')
    verbose = False
    users = None
    authenticated_user = None

    def _log(self, message):
        print "in _log"
        if self.verbose:
            logger.info(message)

    def _check_auth_password(self, username, password):
        """Verify supplied username and password against user DB"""
        offered = None
        if hit_rate_limit(configuration, "davs", self.client_address[0],
                          username):
            logger.warning("Rate limiting login from %s" % \
                           self.client_address[0])
        elif self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = password
            for entry in entries:
                if entry.password is not None:
                    allowed = entry.password
                    logger.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        self.authenticated_user = username
                        update_rate_limit(configuration, "davs",
                                          self.client_address[0], username,
                                          True)
                        return True
        update_rate_limit(configuration, "davs", self.client_address[0],
                          username, False)                    
        return False


    def _check_auth_publickey(self, username, key):
        """Verify supplied username and public key against user DB"""
        offered = None
        if hit_rate_limit(configuration, "davs", self.client_address[0],
                          username):
            logger.warning("Rate limiting login from %s" % \
                           self.client_address[0])
        elif self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = key.get_base64()
            for entry in entries:
                if entry.public_key is not None:
                    allowed = entry.public_key.get_base64()
                    logger.debug("Public key check for %s" % username)
                    if allowed == offered:
                        logger.info("Public key match for %s" % username)
                        self.authenticated_user = username
                        update_rate_limit(configuration, "davs",
                                          self.client_address[0], username,
                                          True)
                        return True
        update_rate_limit(configuration, "davs", self.client_address[0],
                          username, False)                    
        return False

    def _chroot_user(self, username, host, port, verbose):
        """Swith to user home"""
        # list of User login objects for user_name
        entries = self.users[self.authenticated_user]
        for entry in entries:
            if entry.chroot:
                directory = os.path.join(self.server_conf.user_home,
                                         entry.home)
                logger.info("switching to user home %s" % directory)
                init_filesystem_handler(self, directory, host, port, verbose)
                return
        logger.info("leaving root directory alone")
        
    def send_header(self, keyword, value):
        """Override default send_header method of
        DAVRequestHandler and thus DAVAuthHandler:
        Mangle requests to send custom 'WWW-Authenticate' header instead of
        the hard-coded 'PyWebDAV' value.
        """
        if keyword == 'WWW-Authenticate':
            value = value.replace("PyWebDAV", self.server_conf.short_title)
            
        DAVAuthHandler.send_header(self, keyword, value)

    def send_body_chunks_if_http11(self, DATA, code, msg=None, desc=None,
                                   ctype='text/xml; encoding="utf-8"',
                                   headers={}):
        """Override default send_body_chunks_if_http11 method of
        DAVRequestHandler and thus DAVAuthHandler:
        The native version takes the chunking approach if possible, but that
        causes trouble for empty files. Force single send_body in that case.
        Without this fix opening of empty files hangs until connection times
        out for all clients.
        """
        if (not DATA or self.request_version == 'HTTP/1.0' or
            not self._config.DAV.getboolean('chunked_http_response')):
            self.send_body(DATA, code, msg, desc, ctype, headers)
        else:
            self.send_body_chunks(DATA, code, msg, desc, ctype, headers)
        
    def send_body(self, DATA, code=None, msg=None, desc=None,
                  ctype='application/octet-stream', headers={}):
        """Override default send_body method of DAVRequestHandler and thus
        DAVAuthHandler:
        For some silly reason pywebdav sometimes calls send_body with str code
        but back-end send_response from BaseHTTPServer.py expects int. Force
        conversion if needed.
        Without this fix locking/writing of files fails with mapped network
        drives on Windows.
        """
        if isinstance(code, basestring) and code.isdigit():
            code = int(code)
        DAVAuthHandler.send_body(self, DATA, code, msg, desc, ctype, headers)
        
    def get_userinfo(self, username, password, command):
        """Authenticate user against user DB. Returns 1 on success and None
        otherwise.
        """

        refresh_users(configuration, 'davs')
        usermap = {}
        for user_obj in self.server_conf.daemon_conf['users']:
            if not usermap.has_key(user_obj.username):
                usermap[user_obj.username] = []
            usermap[user_obj.username].append(user_obj)
        self.users = usermap
        logger.debug("get_userinfo found users: %s" % self.users)

        host = configuration.daemon_conf.get('address')
        port = configuration.daemon_conf.get('port')
        verbose = self._config.DAV.getboolean('verbose')

        if 'password' in self.server_conf.user_davs_auth and \
                 self._check_auth_password(username, password):
            logger.info("Authenticated %s" % username)
            # dispatch directory and host to the filesystem handler
            # responsible for deciding where to take the data from
            self._chroot_user(username, host, port, verbose)
            return 1
        else:
            err_msg = "Password authentication failed for %s" % username
            logger.error(err_msg)
            print err_msg
        return None


def run(configuration):
    """SSL wrap HTTP server for secure DAV access"""

    handler = MiGDAVAuthHandler

    # Force AuthRequestHandler to HTTP/1.1 to allow persistent connections

    handler.protocol_version = 'HTTP/1.1'

    # Extract server address for daemon and DAV URIs

    host = configuration.user_davs_address.strip()
    port = configuration.user_davs_port

    # Pass conf options to DAV handler in required object format.
    # Server accepts empty address to mean all available IPs but URIs need
    # a real FQDN

    dav_conf_dict = configuration.dav_cfg
    if host:
        dav_conf_dict['host'] = host
    else:
        from socket import getfqdn
        dav_conf_dict['host'] = getfqdn()        
    dav_conf_dict['port'] = port
    dav_conf = setup_dummy_config(**dav_conf_dict)
    # inject options
    handler.server_conf = configuration
    handler._config = dav_conf

    server = ThreadedHTTPServer

    directory = dav_conf_dict['directory'].strip().rstrip('/')
    verbose = dav_conf.DAV.getboolean('verbose')
    noauth = dav_conf.DAV.getboolean('noauth')
    nossl = dav_conf.DAV.getboolean('nossl')

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

    # initialize server on specified address and port
    runner = server((host, port), handler)

    # Wrap in SSL if enabled
    if nossl:
        logger.warning('Not wrapping connections in SSL - only for testing!')
    else:
        cert_path = configuration.user_davs_key
        if not os.path.isfile(cert_path):
            logger.error('No such server key: %s' % cert_path)
            sys.exit(1)
        logger.info('Wrapping connections in SSL')
        runner.socket = ssl.wrap_socket(runner.socket,
                                        certfile=cert_path,
                                        server_side=True)
        
    print('Listening on %s (%i)' % (host, port))

    min_expire_delay = 300
    last_expire = time.time()
    try:
        while True:
            runner.handle_request()
            if last_expire + min_expire_delay < time.time():
                last_expire = time.time()
                expired = expire_rate_limit(configuration, "davs")
                logger.debug("Expired rate limit entries: %s" % expired)
    except KeyboardInterrupt:
        # forward KeyboardInterrupt to main thread
        raise


if __name__ == "__main__":
    configuration = get_configuration_object()
    nossl = False

    # Use separate logger
    logging.basicConfig(filename=configuration.user_davs_log,
                        level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s %(message)s")
    logger = logging

    # Allow configuration overrides on command line
    if sys.argv[1:]:
        nossl = bool(sys.argv[1])
    if sys.argv[2:]:
        configuration.user_davs_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_davs_port = int(sys.argv[3])

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
               'nossl': nossl,
        }

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
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
    except Exception, exc:
        logger.error("exiting on unexpected exception: %s" % exc)
