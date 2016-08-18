#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

Requires wsgidav module (https://github.com/mar10/wsgidav) in a recent version
or with a minor patch (see https://github.com/mar10/wsgidav/issues/29) to allow
per-user subdir chrooting inside root_dir.
"""

import os
import signal
import sys
import threading
import time

try:
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
    # Use cherrypy bundled with wsgidav - needs module path mangling
    from wsgidav.server import __file__ as server_init_path
    sys.path.append(os.path.dirname(server_init_path))
    from cherrypy import wsgiserver
    from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter, ssl
    from wsgidav.fs_dav_provider import FileResource, FolderResource, \
         FilesystemProvider
    from wsgidav.domain_controller import WsgiDAVDomainController
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
except ImportError, ierr:
    print "ERROR: the python wsgidav module is required for this daemon"
    sys.exit(1)

                        
from shared.base import invisible_path, force_unicode
from shared.conf import get_configuration_object
from shared.defaults import dav_domain, litmus_id
from shared.griddaemons import get_fs_path, acceptable_chmod, \
     refresh_user_creds, update_login_map, login_map_lookup, hit_rate_limit, \
     update_rate_limit, expire_rate_limit, penalize_rate_limit, add_user_object
from shared.logger import daemon_logger, reopen_log
from shared.pwhash import unscramble_digest
from shared.useradm import check_password_hash, generate_password_hash, \
     generate_password_digest


configuration, logger = None, None

# TODO: can we enforce connection reuse?
#       dav clients currently hammer the login functions for every operation

def hangup_handler(signal, frame):
    """A simple signal handler to force log reopening on SIGHUP"""
    logger.info("reopening log in reaction to hangup signal")
    reopen_log(configuration)
    logger.info("reopened log after hangup signal")
    
def _handle_allowed(request, abs_path):
    """Helper to make sure ordinary handle of a COPY, MOVE or DELETE
    request is allowed on abs_path.
        
    As noted in dav_handler.py doc strings raising a DAVError here prevents all
    further handling of the request with an error to the client.

    NOTE: We prevent any direct operation on symlinks used in vgrid shares.
    This is in line with other grid_X daemons and the web interface.
    """
    if os.path.islink(abs_path):
        logger.warning("refused %s on symlink: %s" % (request, abs_path))
        raise DAVError(HTTP_FORBIDDEN)

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


class HardenedSSLAdapter(BuiltinSSLAdapter):
    """Hardened version of the BuiltinSSLAdapter. It takes optional custom
    ssl_version, ciphers and options arguments for use in setting up the socket
    security.
    This is particularly important in relation to mitigating the series of
    recent SSL attack vectors like POODLE and CRIME.
    The default is to try the most flexible security protocol negotiation, but
    with only the strong ciphers recommended by Mozilla:
    https://wiki.mozilla.org/Security/Server_Side_TLS#Apache
    just like we do in the apache conf.
    Similarly the insecure protocols, compression and client-side cipher
    degradation is disabled if possible (python 2.7.9+).

    Legacy versions of python (<2.7) support neither ciphers nor options tuning,
    so for those versions a warning is issued and unless a custom ssl_version
    is supplied the result is basically the original BuiltinSSLAdapter.
    """

    # Inherited args
    certificate = None
    private_key = None

    ssl_kwargs = {}
    # Default is same as BuiltinSSLAdapter
    ssl_version = ssl.PROTOCOL_SSLv23
    # Hardened SSL context options: limit to TLS without compression and with
    #                               forced server cipher preference if python
    #                               is recent enough (2.7.9+)
    options = 0
    options |= getattr(ssl, 'OP_NO_SSLv2', 0x1000000)
    options |= getattr(ssl, 'OP_NO_SSLv3', 0x2000000)
    options |= getattr(ssl, 'OP_NO_COMPRESSION', 0x20000)
    options |= getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000)
    
    # Mirror strong ciphers used in Apache
    ciphers = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"

    def __init__(self, certificate, private_key, certificate_chain=None,
                 ssl_version=None, ciphers=None, options=None):
        """Save ssl_version and ciphers for use in wrap method"""
        BuiltinSSLAdapter.__init__(self, certificate, private_key,
                                   certificate_chain)

        if ssl_version is not None:
            self.ssl_version = ssl_version
        if ciphers is not None:
            self.ciphers = ciphers
        if options is not None:
            self.options = options

        if sys.version_info[:3] >= (2, 7, 9):
            self.ssl_kwargs.update({"ciphers": self.ciphers})
            logger.info("enforcing strong SSL/TLS connections")
            logger.debug("using SSL/TLS ciphers: %s" % self.ciphers)
        else:
            logger.warning("Unable to enforce explicit strong TLS connections")
            logger.warning("Upgrade to python 2.7.9+ for maximum security")
        self.ssl_kwargs.update({"ssl_version": self.ssl_version})
        logger.debug("using SSL/TLS version: %s (default %s)" % \
                    (self.ssl_version, ssl.PROTOCOL_SSLv23))


    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries.
        Extended to pass the provided ssl_version and ciphers arguments to the
        wrap_socket call.
        Limits protocols and disables compression for modern python versions.
        """
        try:
            logger.debug("Wrapping socket in SSL/TLS with args: %s" % \
                         self.ssl_kwargs)
            s = ssl.wrap_socket(sock, do_handshake_on_connect=True,
                                server_side=True, certfile=self.certificate,
                                keyfile=self.private_key, **(self.ssl_kwargs))
        except ssl.SSLError:
            e = sys.exc_info()[1]
            if e.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it's connectable;
                # the 'ping' isn't SSL.
                return None, {}
            elif e.errno == ssl.SSL_ERROR_SSL:
                if e.args[1].endswith('http request'):
                    # The client is speaking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError
                elif e.args[1].endswith('unknown protocol'):
                    # The client is speaking some non-HTTP protocol.
                    # Drop the conn.
                    return None, {}
            raise

        # Futher harden connections if python is recent enough (2.7.9+)
        
        ssl_ctx = getattr(s, 'context', None)
        if sys.version_info[:3] >= (2, 7, 9) and ssl_ctx:
            logger.info("enforcing strong SSL/TLS options")
            logger.debug("SSL/TLS options: %s" % self.options)
            ssl_ctx.options |= self.options
        else:
            logger.info("can't enforce strong SSL/TLS options")
            logger.warning("Upgrade to python 2.7.9+ for maximum security")
            
        return s, BuiltinSSLAdapter.get_environ(self, s)

    
class MiGWsgiDAVDomainController(WsgiDAVDomainController):
    """Override auth database lookups to use username and password hash for
    basic auth and digest otherwise.
    
    NOTE: The username arguments are already on utf8 here so no need to force.
    """

    min_expire_delay = 120
    last_expire = time.time()

    def __init__(self, userMap):
        WsgiDAVDomainController.__init__(self, userMap)
        # Alias to CamelCase version userMap required internally
        self.user_map = self.userMap = userMap
        self.last_expire = time.time()
        self.min_expire_delay = 300        
        self.hash_cache = {}
        self.digest_cache = {}

    def _expire_rate_limit(self):
        """Expire old entries in the rate limit dictionary"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            expire_rate_limit(configuration, "davs")
        
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

    def _get_user_digests(self, address, realm, username):
        """Find the allowed digest values for supplied username - this is for
        use in the actual digest authorization.
        """
        user_list = self.user_map[realm].get(username, [])
        return [i for i in user_list if i.digest is not None]

    def _check_auth_password(self, address, realm, username, password):
        """Verify supplied username and password against user DB"""
        user_list = self.user_map[realm].get(username, [])
        for user_obj in user_list:
            # list of User login objects for username
            offered = password
            allowed = user_obj.password
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
        update_users(configuration, self.user_map, username)
        #logger.info("in authDomainUser from %s" % addr)
        success = False
        if hit_rate_limit(configuration, "davs", addr, username):
            logger.warning("Rate limiting login from %s" % addr)
        elif self._check_auth_password(addr, realmname, username, password):
            logger.info("Accepted login for %s from %s" % (username, addr))
            success = True
        else:
            logger.warning("Invalid login for %s from %s" % (username, addr))
        failed_count = update_rate_limit(configuration, "davs", addr, username,
                                         success, password)
        penalize_rate_limit(configuration, "davs", addr, username,
                            failed_count)
        return success

    def isRealmUser(self, realmname, username, environ):
        """Returns True if this username is valid for the realm, False
        otherwise.

        Please note that this is always called for digest auth so we use it to
        update creds and reject users without digest password set.
        """
        #logger.info("refresh user %s" % username)
        addr = _get_addr(environ)
        update_users(configuration, self.user_map, username)
        #logger.info("in isRealmUser from %s" % addr)
        if self._get_user_digests(addr, realmname, username):
            logger.debug("valid digest user %s from %s" % (username, addr))
            return True
        else:
            logger.warning("invalid digest user %s from %s" % (username, addr))
            return False
    
    def getRealmUserPassword(self, realmname, username, environ):
        """Return the password for the given username for the realm.
        
        Used for digest authentication and always called after isRealmUser
        so update creds is already applied. We just rate limit and check here.
        """
        #print "DEBUG: env in getRealmUserPassword: %s" % environ
        addr = _get_addr(environ)
        self._expire_rate_limit()
        #logger.info("in getRealmUserPassword from %s" % addr)
        if hit_rate_limit(configuration, "davs", addr, username):
            logger.warning("Rate limiting login from %s" % addr)
            password = None
        else:
            digest_users = self._get_user_digests(addr, realmname, username)
            #logger.info("found digest_users %s" % digest_users)
            try:
                # We expect only one - pick last
                digest = digest_users[-1].digest
                _, _, _, payload = digest.split("$")
                #logger.info("found payload %s" % payload)
                unscrambled = unscramble_digest(configuration.site_digest_salt,
                                                payload)
                _, _, password = unscrambled.split(":")
                #logger.info("found password")
            except Exception, exc:
                logger.error("failed to extract digest password: %s" % exc)
                password = None
        if password is not None:
            success = True
            # TODO: we don't have a hook to log accepted digest logins
            # this one only means that user validation makes it to digest check
            logger.info("extracted digest for valid user %s from %s" % \
                        (username, addr))
        else:
            success = False
        failed_count = update_rate_limit(configuration, "davs", addr, username,
                                         success, password)
        penalize_rate_limit(configuration, "davs", addr, username,
                            failed_count)
        return password

    
class MiGFileResource(FileResource):
    """Hide invisible files from all access.
    All file access starts with object init so it is enough to make sure we
    refuse any hidden files in the constructor.
    Parent constructor saves environ as self.environ for later use in chroot.
    """
    def __init__(self, path, environ, filePath):
        FileResource.__init__(self, path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively, but with our restrictions"""
        _handle_allowed("copy", self._filePath)
        return super(MiGFileResource, self).handleCopy(destPath, depthInfinity)
        
    def handleMove(self, destPath):
        """Handle a MOVE request natively, but with our restrictions"""
        _handle_allowed("move", self._filePath)
        return super(MiGFileResource, self).handleMove(destPath)
        
    def handleDelete(self):
        """Handle a DELETE request natively, but with our restrictions"""
        _handle_allowed("delete", self._filePath)
        return super(MiGFileResource, self).handleDelete()
                    

class MiGFolderResource(FolderResource):
    """Hide invisible files from all access.
    We must override getMemberNames to filter out hidden names and getMember
    to avoid inherited methods like getDescendants from receiving the parent
    unrestricted FileResource and FolderResource objects when doing e.g.
    directory listings.
    Parent constructor saves environ as self.environ for later use in chroot.
    """
    def __init__(self, path, environ, filePath):
        FolderResource.__init__(self, path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively, but with our restrictions"""
        _handle_allowed("copy", self._filePath)
        return super(MiGFolderResource, self).handleCopy(destPath, depthInfinity)
        
    def handleMove(self, destPath):
        """Handle a MOVE request natively, but with our restrictions"""
        _handle_allowed("move", self._filePath)
        return super(MiGFolderResource, self).handleMove(destPath)
        
    def handleDelete(self):
        """Handle a DELETE request natively, but with our restrictions"""
        _handle_allowed("delete", self._filePath)
        return super(MiGFolderResource, self).handleDelete()
                    
    def getMemberNames(self):
        """Return list of direct collection member names (utf-8 encoded).
        
        See DAVCollection.getMemberNames()

        Use parent version and filter out any invisible file names.
        """
        return [i for i in super(MiGFolderResource, self).getMemberNames() if \
                not invisible_path(i)]

    def getMember(self, name):
        """Return direct collection member (DAVResource or derived).
        
        See DAVCollection.getMember()

        The inherited getMemberList and getDescendants methods implicitly call
        self.getMember on all folder names, so we need to override here to
        avoid the FolderResource and FileResource objects being returned.

        Call parent version, filter invisible and mangle to our own
        MiGFileResource and MiGFolderResource objects.
        """

        #logger.debug("in getMember")
        res = FolderResource.getMember(self, name)
        if invisible_path(res.name):
            res = None
        #logger.debug("getMember found %s" % res)
        if res and not res.isCollection and not isinstance(res, MiGFileResource):
            res = MiGFileResource(res.path, self.environ, res._filePath)
        elif res and res.isCollection and not isinstance(res, MiGFolderResource):
            res = MiGFolderResource(res.path, self.environ, res._filePath)
        #logger.debug("getMember returning %s" % res)
        return res

    def getDescendants(self, collections=True, resources=True,
                       depthFirst=False, depth="infinity", addSelf=False):
        """Return a list _DAVResource objects of a collection (children,
        grand-children, ...).
        
        This default implementation calls self.getMemberList() recursively.
        
        This function may also be called for non-collections (with addSelf=True).
        
        :Parameters:
        depthFirst : bool
        use <False>, to list containers before content.
        (e.g. when moving / copying branches.)
        Use <True>, to list content before containers.
        (e.g. when deleting branches.)
        depth : string
        '0' | '1' | 'infinity'

        Call parent version just with debug logging added.
        """                
        #logger.debug("in getDescendantsWrap for %s" % self)
        res = FolderResource.getDescendants(self, collections, resources,
                                            depthFirst, depth, addSelf)
        #logger.debug("getDescendants wrap returning %s" % res)
        return res
    

class MiGFilesystemProvider(FilesystemProvider):
    """
    Overrides the default FilesystemProvider to include chroot support, symlink
    restrictions and hidden files like in other MiG file interfaces.
    """

    def __init__(self, directory, server_conf, dav_conf):
        """Simply call parent constructor"""
        FilesystemProvider.__init__(self, directory)
        self.daemon_conf = server_conf.daemon_conf
        self.chroot_exceptions = self.daemon_conf['chroot_exceptions']
        self.chmod_exceptions = self.daemon_conf['chmod_exceptions']
        self.readonly = self.daemon_conf['read_only']

    # Use shared daemon fs helper functions
    
    def _acceptable_chmod(self, davs_path, mode):
        """Wrap helper"""
        #logger.debug("acceptable_chmod: %s" % davs_path)
        reply = acceptable_chmod(davs_path, mode, self.chmod_exceptions)
        if not reply:
            logger.warning("acceptable_chmod failed: %s %s %s" % \
                           (davs_path, mode, self.chmod_exceptions))
        #logger.debug("acceptable_chmod returns: %s :: %s" % (davs_path,
        #                                                     reply))
        return reply

    # IMPORTANT: we need a recent/patched version of wsgidav for environ arg.
    # It is required to allow per-user chrooting inside root share folder.
    def _locToFilePath(self, path, environ=None):
        """Convert resource path to a unicode absolute file path:
        We enforce chrooted absolute unicode path in user_chroot extraction so
        just make sure user_chroot+path is not outside user_chroot when used
        for e.g. creating new files and directories.
        This function is called for all inherited file operations, so it
        enforces chrooting in general.
        Please note that we additionally generally refuse hidden file access
        and specifically employ direct symlink access prevention for a copy,
        move and delete operations on all MiGFileResource and MiGFolderResource
        objects.
        """
        if environ is None:
            raise RuntimeError("A recent/patched wsgidav is needed, see code")
        user_chroot = _user_chroot_path(environ)
        pathInfoParts = path.strip(os.sep).split(os.sep)
        abs_path = os.path.abspath(os.path.join(user_chroot, *pathInfoParts))
        try:
            abs_path = get_fs_path(path, user_chroot, self.chroot_exceptions)
        except ValueError, vae:
            raise RuntimeError("Access out of bounds: %s in %s : %s"
                               % (path, user_chroot, vae))
        abs_path = force_unicode(abs_path)           
        return abs_path

    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()

        Override to chroot and filter MiG invisible paths from content.
        """

        self._count_getResourceInst += 1
        try:
            abs_path = self._locToFilePath(path, environ)
        except RuntimeError, rte:
            logger.warning("getResourceInst: %s : %s" % (path, rte))
            raise DAVError(HTTP_FORBIDDEN)
            
        if not os.path.exists(abs_path):
            return None
        
        if os.path.isdir(abs_path):
            return MiGFolderResource(path, environ, abs_path)
        return MiGFileResource(path, environ, abs_path)
                                                            

def update_users(configuration, user_map, username):
    """Update creds dict for username and aliases"""
    daemon_conf, changed_users = refresh_user_creds(configuration, 'davs',
                                                    username)
    # Add dummy user for litmus test if enabled in conf
    litmus_pw = 'test'
    if username == litmus_id and \
           daemon_conf.get('enable_litmus', False) and \
           not login_map_lookup(daemon_conf, litmus_id):
        litmus_home = os.path.join(configuration.user_home, litmus_id)
        try:
            os.makedirs(litmus_home)
        except: 
            pass
        for auth in ('basic', 'digest'):
            if not daemon_conf.get('accept%s' % auth, False):
                continue
            logger.info("enabling litmus %s test accounts" % auth)
            changed_users.append(litmus_id)
            if auth == 'basic':
                pw_hash = generate_password_hash(litmus_pw)
                add_user_object(daemon_conf, litmus_id, litmus_home,
                                password=pw_hash)
            else:
                digest = generate_password_digest(
                    dav_domain, litmus_id, litmus_pw,
                    configuration.site_digest_salt)
                add_user_object(daemon_conf, litmus_id, litmus_home,
                                digest=digest)
    update_login_map(daemon_conf, changed_users)


def run(configuration):
    """SSL wrapped HTTP server for secure WebDAV access"""

    dav_conf = configuration.dav_cfg
    daemon_conf = configuration.daemon_conf
    # We just wrap login_map in domain user map as needed here
    user_map = {dav_domain: daemon_conf['login_map']}
    config = DEFAULT_CONFIG.copy()
    config.update(dav_conf)
    config.update(daemon_conf)
    config.update({
        "provider_mapping": {
            dav_domain: MiGFilesystemProvider(daemon_conf['root_dir'],
                                              configuration,
                                              dav_conf)
            },
        "user_mapping": user_map,
        # Use these to tweak logging target and verbosity. E.g. increase
        # verbose value to 2 to get more debug info like full XML messages.
        #"verbose": 2,
        #"enable_loggers": ["lock_manager", "property_manager", "http_authenticator", ...]
        #"debug_methods": ["COPY", "DELETE", "GET", "HEAD", "LOCK", "MOVE", "OPTIONS", "PROPFIND", "PROPPATCH", "PUT", "UNLOCK"],
        #"verbose": 2,
        #"enable_loggers": ["http_authenticator"],
        #"debug_methods": ["PROPFIND", "PUT"],
        "verbose": 1,
        "enable_loggers": [],
        "debug_methods": [],
        "propsmanager": True,      # True: use property_manager.PropertyManager
        "locksmanager": True,      # True: use lock_manager.LockManager
        # Allow last modified timestamp updates from client to support rsync -a
        "mutable_live_props": ["{DAV:}getlastmodified"],
        "domaincontroller": MiGWsgiDAVDomainController(user_map),
        })
    
    # NOTE: Briefly insert dummy user to avoid bogus warning about anon access
    #       We dynamically add users as they connect so it isn't empty.
    fake_user = 'nosuchuser-%s' % time.time()
    config['user_mapping'][dav_domain][fake_user] = None
    app = WsgiDAVApp(config)
    del config['user_mapping'][dav_domain][fake_user]
    #print('User list: %s' % config['user_mapping'])

    # Find and mangle HTTPAuthenticator in application stack
    
    #app_authenticator = _find_authenticator(app)

    #print('Config: %s' % config)
    #print('app auth: %s' % app_authenticator)

    if not config.get('nossl', False):
        cert = config['ssl_certificate'] = configuration.user_davs_key
        key = config['ssl_private_key'] = configuration.user_davs_key
        chain = config['ssl_certificate_chain'] = ''
        #wsgiserver.CherryPyWSGIServer.ssl_adapter = BuiltinSSLAdapter(cert, key, chain)
        wsgiserver.CherryPyWSGIServer.ssl_adapter = HardenedSSLAdapter(cert, key, chain)

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

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("webdavs", configuration.user_davs_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    signal.signal(signal.SIGHUP, hangup_handler)

    # Allow configuration overrides on command line
    litmus = False
    readonly = False
    nossl = False
    if sys.argv[2:]:
        configuration.user_davs_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_davs_port = int(sys.argv[3])
    if sys.argv[4:]:
        litmus = (sys.argv[4].lower() in ('1', 'true', 'yes', 'on'))
    if sys.argv[5:]:
        readonly = (sys.argv[5].lower() in ('1', 'true', 'yes', 'on'))
    if sys.argv[6:]:
        nossl = (sys.argv[6].lower() in ('1', 'true', 'yes', 'on'))
        
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
                         os.path.abspath(configuration.resource_home),
                         os.path.abspath(configuration.seafile_mount)]
    # Any extra chmod exceptions here - we already cover invisible_path check
    # in acceptable_chmod helper.
    chmod_exceptions = []
    configuration.daemon_conf = {
        'host': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'read_only': readonly,
        'allow_password': 'password' in configuration.user_davs_auth,
        'allow_digest': 'digest' in configuration.user_davs_auth,
        'allow_publickey': 'publickey' in configuration.user_davs_auth,
        'user_alias': configuration.user_davs_alias,
        # Lock needed here due to threaded creds updates
        'creds_lock': threading.Lock(),
        'users': [],
        'login_map': {},
        # NOTE: enable for litmus test (http://www.webdav.org/neon/litmus/)
        #
        # USAGE:
        # export HTTPS_URL="https://SOMEADDRESS:DAVSPORT"
        # export TESTROOT=$PWD; export HTDOCS=$PWD/htdocs
        # ./litmus -k $HTTPS_URL litmus test
        # or
        # ./configure --with-ssl
        # make URL=$HTTPS_URL CREDS="litmus test" check
        'enable_litmus': litmus,
        'time_stamp': 0,
        'logger': logger,
        }
    daemon_conf = configuration.daemon_conf
    daemon_conf['acceptbasic'] = daemon_conf['allow_password']
    daemon_conf['acceptdigest'] = daemon_conf['allow_digest']
    # Keep order of auth methods (please note the 2GB+ upload bug with digest)
    daemon_conf['defaultdigest'] = 'digest' in configuration.user_davs_auth[:1]

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
