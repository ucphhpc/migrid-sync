#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Provides secure WebDAV access to MiG user homes using wsgidav.

Replaces the old pywebdav-based grid_davs daemon with similar functionality,
but bad performance and limited platform support.

Requires wsgidav module (https://github.com/mar10/wsgidav).
"""

import logging
import os
import sys
import time

try:
    #from wsgiref.simple_server import make_server
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
    #from wsgidav.server import ext_wsgiutils_server
    # Use cherrypy bundled with wsgidav - needs module path mangling
    from wsgidav.server import __file__ as server_init_path
    sys.path.append(os.path.dirname(server_init_path))
    from cherrypy import wsgiserver
    from cherrypy.wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
    from OpenSSL import SSL
    from wsgidav.fs_dav_provider import FileResource, FolderResource, \
         FilesystemProvider
    from wsgidav.domain_controller import WsgiDAVDomainController
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
except ImportError, ierr:
    print "ERROR: the python wsgidav module is required for this daemon"
    sys.exit(1)


                        
from shared.base import invisible_path, force_unicode
from shared.defaults import dav_domain
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, acceptable_chmod, refresh_users, \
     refresh_user_creds, hit_rate_limit, update_rate_limit, expire_rate_limit
from shared.logger import daemon_logger
from shared.pwhash import unscramble_digest
from shared.useradm import check_password_hash, generate_password_hash, \
     generate_password_digest


configuration, logger = None, None

# TODO: can we enforce connection reuse?
#       dav clients currently hammer the login functions for every operation

def _user_chroot_path(environ):
    """Extract user credentials from environ dicionary to build chroot
    directory path for user.
    """
    username = environ.get("http_authenticator.username", None)
    if username is None:
        raise Exception("No authenticated username!")
    # Expand symlinked homes for aliases
    user_chroot = os.path.realpath(os.path.join(configuration.user_home,
                                                username))
    return user_chroot

def _get_addr(environ):
    """Extract client address from environ dict"""
    return environ['REMOTE_ADDR']

def _find_authenticator(application):
    """Find and return handle to HTTPAuthenticator in application stack.
    The application object nests application stack layers by repeatedly
    calling constructors on application and saving the child in the
    application._application attribute so we need to traverse until we find
    the target.
    """
    if not getattr(application, '_application', None):
        raise Exception("No HTTPAuthenticator found in wsgidav stack!")
    elif isinstance(application, HTTPAuthenticator):
        return application
    else:
        return _find_authenticator(application._application)
    
    
class MiGWsgiDAVDomainController(WsgiDAVDomainController):
    """Override auth database lookups to use username and password hash for
    basic auth and digest otherwise.
    """

    def __init__(self, userMap):
        super(MiGWsgiDAVDomainController, self).__init__(userMap)
        self.userMap = userMap
        self.last_expire = time.time()
        self.min_expire_delay = 300        
        self.hash_cache = {}
        self.digest_cache = {}

    def _expire_rate_limit(self):
        """Expire old entries in the rate limit dictionary"""
        expired = expire_rate_limit(configuration, "davs")
        logger.debug("Expired rate limit entries: %s" % expired)
        
    def _expire_caches(self):
        """Expire old entries in the hash and digest caches"""
        self.hash_cache.clear()
        self.digest_cache.clear()
        logger.debug("Expired hash and digest caches")
        
    def _expire_volatile(self):
        """Expire old entries in the volatile helper dictionaries"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            self._expire_rate_limit()
            self._expire_caches()

    def _check_auth_password(self, address, realm, username, password):
        """Verify supplied username and password against user DB"""
        user = self.userMap[realm].get(username, None)
        if user is not None:
            # list of User login objects for username
            offered = password
            allowed = user.get('password_hash', None)
            if allowed is not None:
                #logger.debug("Password check for %s" % username)
                if check_password_hash(offered, allowed, self.hash_cache):
                    return True
        return False

    def authDomainUser(self, realmname, username, password, environ):
        """Returns True if this username/password pair is valid for the realm,
        False otherwise. Used for basic authentication.
        
        We explicitly compare against saved hash rather than password value.
        """
        #print "DEBUG: env in authDomainUser: %s" % environ
        addr = _get_addr(environ)
        self._expire_rate_limit()
        #logger.info("refresh user %s" % username)
        update_users(configuration, self.userMap, username)
        #logger.info("in authDomainUser from %s" % addr)
        success = False
        if hit_rate_limit(configuration, "davs", addr, username):
            logger.warning("Rate limiting login from %s" % addr)
        elif self._check_auth_password(addr, realmname, username, password):
            logger.info("Accepted login for %s from %s" % (username, addr))
            success = True
        else:
            logger.warning("Invalid login for %s from %s" % (username, addr))
        update_rate_limit(configuration, "davs", addr, username, success)
        logger.info("valid digest user %s" % username)
        return success

    def isRealmUser(self, realmname, username, environ):
        """Returns True if this username is valid for the realm, False otherwise.

        Please not that this is only called for digest auth so we use it to
        reject users without digest password set.
        """
        #logger.info("refresh user %s" % username)
        update_users(configuration, self.userMap, username)
        #logger.info("in isRealmUser from %s" % addr)
        orig = super(MiGWsgiDAVDomainController, self).isRealmUser(realmname,
                                                                   username,
                                                                   environ)
        if orig and self.userMap[realmname][username].get('password',
                                                          None) is not None:
            logger.info("valid digest user %s" % username)
            return True
        else:
            logger.warning("invalid digest user %s" % username)
            return False
                    

    def getRealmUserPassword(self, realmname, username, environ):
        """Return the password for the given username for the realm.
        
        Used for digest authentication.
        """
        #print "DEBUG: env in getRealmUserPassword: %s" % environ
        addr = _get_addr(environ)
        self._expire_rate_limit()
        #logger.info("refresh user %s" % username)
        update_users(configuration, self.userMap, username)
        #logger.info("in getRealmUserPassword from %s" % addr)
        if hit_rate_limit(configuration, "davs", addr, username):
            logger.warning("Rate limiting login from %s" % addr)
            password = None
        else:
            digest = super(MiGWsgiDAVDomainController,
                            self).getRealmUserPassword(realmname, username,
                                                       environ)
            #logger.info("found digest %s" % digest)
            try:
                _, _, _, payload = digest.split("$")
                #logger.info("found payload %s" % payload)
                unscrambled = unscramble_digest(configuration.site_digest_salt,
                                                payload)
                _, _, password = unscrambled.split(":")
                #logger.info("found password")
            except Exception, exc:
                logger.error("failed to extract digest password: %s" % exc)
                password = None
        success = (password is not None)
        update_rate_limit(configuration, "davs", addr, username, success)
        return password

    
class MiGFileResource(FileResource):
    """Hide invisible files from all access"""
    def __init__(self, path, environ, filePath):
        super(MiGFileResource, self).__init__(path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)
        self._user_chroot = _user_chroot_path(environ)

        # Replace native _locToFilePath method with our chrooted version
        
        def wrapLocToFilePath(path):
            """Wrap native _locToFilePath method in chrooted version"""
            return self.provider._chroot_locToFilePath(self._user_chroot, path)
        self.provider._locToFilePath = wrapLocToFilePath

    # TODO: override access on more methods?

    
class MiGFolderResource(FolderResource):
    """Hide invisible files from all access"""
    def __init__(self, path, environ, filePath):
        super(MiGFolderResource, self).__init__(path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)
        self._user_chroot = _user_chroot_path(environ)

        # Replace native _locToFilePath method with our chrooted version
        
        def wrapLocToFilePath(path):
            """Wrap native _locToFilePathmethod in chrooted version"""
            return self.provider._chroot_locToFilePath(self._user_chroot, path)
        self.provider._locToFilePath = wrapLocToFilePath

    # TODO: override access on more methods?
    
    def getMemberNames(self):
        """Return list of direct collection member names (utf-8 encoded).
        
        See DAVCollection.getMemberNames()
        """
        return [i for i in super(MiGFolderResource, self).getMemberNames() if \
                not invisible_path(i)]


class MiGFilesystemProvider(FilesystemProvider):
    """
    Overrides the default FilesystemProvider to include chroot support and
    hidden files like in other MiG file interfaces.
    """

    def __init__(self, directory, server_conf, dav_conf):
        """Simply call parent constructor"""
        super(MiGFilesystemProvider, self).__init__(directory)
        self.daemon_conf = server_conf.daemon_conf
        self.chroot_exceptions = self.daemon_conf['chroot_exceptions']
        self.chmod_exceptions = self.daemon_conf['chmod_exceptions']

    # Use shared daemon fs helper functions
    
    def _acceptable_chmod(self, davs_path, mode):
        """Wrap helper"""
        #logger.debug("acceptable_chmod: %s" % davs_path)
        reply = acceptable_chmod(davs_path, mode, self.chmod_exceptions)
        logger.debug("acceptable_chmod returns: %s :: %s" % (davs_path, reply))
        return reply

    def _locToFilePath(self, path):
        """Make sure any references to the original helper are caught"""
        raise RuntimeError("Not allowed!")

    def _chroot_locToFilePath(self, user_chroot, path):
        """Convert resource path to a unicode absolute file path:
        We already enforced chrooted absolute unicode path on user_chroot so
        just make sure user_chroot+path is not outside user_chroot when used
        for e.g. creating new files and directories.
        """
        pathInfoParts = path.strip(os.sep).split(os.sep)
        real_path = os.path.abspath(os.path.join(user_chroot, *pathInfoParts))
        try:
            real_path = get_fs_path(path, user_chroot, self.chroot_exceptions)
        except ValueError, vae:
            raise RuntimeError("Security exception: access out of bounds: %s/%s"
                               % (user_chroot, path))
        real_path = force_unicode(real_path)           
        return real_path

    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()

        Override to chroot and filter MiG invisible paths from content.
        """

        self._count_getResourceInst += 1
        user_chroot = _user_chroot_path(environ)
        try:
            real_path = self._chroot_locToFilePath(user_chroot, path)
        except RuntimeError, rte:
            logger.warning("getResourceInst: %s : %s" % (path, rte))
            raise DAVError(HTTP_FORBIDDEN)
            
        if not os.path.exists(real_path):
            return None
        
        if os.path.isdir(real_path):
            return MiGFolderResource(path, environ, real_path)
        return MiGFileResource(path, environ, real_path)
                                                            

def update_users(configuration, user_map, username=None):
    """Update dict with username password pairs. The optional username
    argument limits the update to that particular user with aliases.
    """
    if username is not None:
        refresh_user_creds(configuration, 'davs', username)
    else:
        refresh_users(configuration, 'davs')
    domain_map = user_map.get(dav_domain, {})
    for user_obj in configuration.daemon_conf['users']:
        # print "DEBUG: user %s : %s" % (user_obj.username, user_obj.digest)
        user_dict = domain_map.get(user_obj.username, {})
        if user_obj.password:
            user_dict['password_hash'] = user_obj.password
        if user_obj.digest:
            user_dict['password'] = user_obj.digest
        domain_map[user_obj.username] = user_dict

    daemon_conf = configuration.daemon_conf
    if username is None and daemon_conf.get('enable_litmus', False):
        litmus_name = 'litmus'
        litmus_user = {}
        litmus_home = os.path.join(configuration.user_home, litmus_name)
        try:
            os.makedirs(litmus_home)
        except: 
            pass
        for auth in ('basic', 'digest'):
            if not daemon_conf.get('accept%s' % auth, False):
                continue
            logger.info("enabling litmus %s test accounts" % auth)
            if auth == 'basic':
                litmus_user['password_hash'] = generate_password_hash('test')
            else:
                litmus_user['password'] = generate_password_digest(
                    dav_domain, litmus_name, 'test',
                    configuration.site_digest_salt)
        domain_map[litmus_name] = litmus_user

    user_map[dav_domain] = domain_map

def run(configuration):
    """SSL wrapped HTTP server for secure WebDAV access"""

    dav_conf = configuration.dav_cfg
    daemon_conf = configuration.daemon_conf
    config = DEFAULT_CONFIG.copy()
    config.update(dav_conf)
    config.update(daemon_conf)
    user_map = {}
    update_users(configuration, user_map)
    config.update({
        "provider_mapping": {
            dav_domain: MiGFilesystemProvider(daemon_conf['root_dir'],
                                              configuration,
                                              dav_conf)
            },
        "user_mapping": user_map,
        "enable_loggers": [],
        "propsmanager": True,      # True: use property_manager.PropertyManager
        "locksmanager": True,      # True: use lock_manager.LockManager
        "domaincontroller": MiGWsgiDAVDomainController(user_map),
        })
    
    #print('User list: %s' % config['user_mapping'])
    app = WsgiDAVApp(config)

    # Find and mangle HTTPAuthenticator in application stack
    
    #app_authenticator = _find_authenticator(app)

    #print('Config: %s' % config)
    #print('app auth: %s' % app_authenticator)

    if not config.get('nossl', False):
        config['ssl_certificate'] = configuration.user_davs_key
        config['ssl_private_key'] = configuration.user_davs_key
        config['ssl_certificate_chain'] = ''

        # Important: disable SSLv2/SSLv3 and weak ciphers like we do in Apache
        # http://roadha.us/2014/10/disable-sslv3-avoid-poodle-attack-web-py/
        cert = config['ssl_certificate']
        key = config['ssl_private_key']
        chain = config['ssl_certificate_chain']
        wsgiserver.CherryPyWSGIServer.ssl_adapter = pyOpenSSLAdapter(cert, key, chain)
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context = SSL.Context(SSL.SSLv23_METHOD)
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context.set_options(SSL.OP_NO_SSLv2)
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context.set_options(SSL.OP_NO_SSLv3)
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context.use_certificate_file(cert)
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context.use_privatekey_file(key)
        if chain:
            wsgiserver.CherryPyWSGIServer.ssl_adapter.context.use_certificate_chain_file(chain)
        # Mirror Apache ciphers
        ciphers = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"
        wsgiserver.CherryPyWSGIServer.ssl_adapter.context.set_cipher_list(ciphers)

    # Use bundled CherryPy WSGI Server to support SSL
    version = "%s WebDAV" % configuration.short_title
    server = wsgiserver.CherryPyWSGIServer((config["host"], config["port"]),
                                           app, server_name=version)

    logger.info('Listening on %(host)s (%(port)s)' % config)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        # forward KeyboardInterrupt to main thread
        raise

if __name__ == "__main__":
    configuration = get_configuration_object()
    nossl = False

    # Use separate logger - cherrypy hijacks root logger

    logger = daemon_logger("webdavs", configuration.user_davs_log, "DEBUG")

    # Allow configuration overrides on command line
    if sys.argv[1:]:
        nossl = bool(sys.argv[1])
    if sys.argv[2:]:
        configuration.user_davs_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_davs_port = int(sys.argv[3])

    # Web server doesn't allow empty string alias for all interfaces
    if configuration.user_davs_address == '':
        configuration.user_davs_address = '0.0.0.0'

    configuration.dav_cfg = {
        'nossl': nossl,
        'verbose': 1,
        }

    if not configuration.site_enable_davs:
        err_msg = "WebDAVS access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)
    print """
Running grid webdavs server for user webdavs access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    print __doc__
    address = configuration.user_davs_address
    port = configuration.user_davs_port

    chroot_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base),
                         os.path.abspath(configuration.vgrid_files_home),
                         os.path.abspath(configuration.resource_home)]
    # Don't allow chmod in dirs with CGI access as it introduces arbitrary
    # code execution vulnerabilities
    chmod_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base)]

    configuration.daemon_conf = {
        'host': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_davs_auth,
        'allow_digest': 'digest' in configuration.user_davs_auth,
        'allow_publickey': 'publickey' in configuration.user_davs_auth,
        'user_alias': configuration.user_davs_alias,
        'users': [],
        # NOTE: enable for litmus test (http://www.webdav.org/neon/litmus/)
        #
        # USAGE:
        # export TESTROOT=$PWD; export HTDOCS=$PWD/htdocs
        # ./litmus -k $HTTPS_URL litmus test
        'enable_litmus': True,
        'time_stamp': 0,
        'logger': logger,
        }
    daemon_conf = configuration.daemon_conf
    daemon_conf['acceptbasic'] = daemon_conf['allow_password']
    daemon_conf['acceptdigest'] = daemon_conf['allow_digest']
    daemon_conf['defaultdigest'] = daemon_conf['allow_digest']        

    logger.info("Starting WebDAV server")
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print info_msg
    try:
        run(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
    except Exception, exc:
        logger.error("exiting on unexpected exception: %s" % exc)
