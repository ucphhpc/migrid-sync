#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
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
import traceback

try:
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
    # Use cherrypy bundled with wsgidav < 2.0 - needs module path mangling
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
    print "You may need to install cherrypy if your wsgidav does not bundle it"
    sys.exit(1)

from shared.base import invisible_path, force_unicode
from shared.conf import get_configuration_object
from shared.defaults import dav_domain, litmus_id, io_session_timeout
from shared.fileio import check_write_access, user_chroot_exceptions
from shared.griddaemons import get_fs_path, acceptable_chmod, \
    refresh_user_creds, refresh_share_creds, update_login_map, \
    login_map_lookup, hit_rate_limit, update_rate_limit, expire_rate_limit, \
    penalize_rate_limit, add_user_object, track_open_session, \
    track_close_expired_sessions, get_active_session, validate_session
from shared.sslsession import SSL_MASTER_KEY_LENGTH, get_ssl_session_id,\
    get_ssl_master_key
from shared.tlsserver import hardened_ssl_context
from shared.logger import daemon_logger, reopen_log
from shared.pwhash import unscramble_digest, assure_password_strength, \
    make_digest
from shared.useradm import check_password_hash, generate_password_hash, \
    check_password_digest, generate_password_digest
from shared.validstring import possible_user_id, possible_sharelink_id


configuration, logger = None, None


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
    elif invisible_path(abs_path):
        logger.warning("refused %s on hidden path: %s" % (request, abs_path))
        raise DAVError(HTTP_FORBIDDEN)
    elif not check_write_access(abs_path):
        logger.warning("refused %s read-only path: %s" % (request, abs_path))
        raise DAVError(HTTP_FORBIDDEN)


def _username_from_env(environ):
    """Extract authenticated user credentials from environ dicionary"""
    username = environ.get("http_authenticator.username", None)
    if username is None:
        raise Exception("No authenticated username!")
    return username


def _get_addr(environ):
    """Extract client address from environ dict"""
    addr = environ.get('HTTP_X_FORWARDED_FOR', '')
    if not addr:
        addr = environ['REMOTE_ADDR']
    return addr


def _get_port(environ):
    """Extract client port from environ dict"""
    port = environ.get('HTTP_X_FORWARDED_FOR_PORT', '')
    if not port:
        port = environ['REMOTE_PORT']
    return port


def _get_ssl_session_token(environ):
    """Extract SSL session token from environ dict"""
    ssl_session_token = environ.get('HTTP_X_SSL_SESSION_TOKEN', '')
    if not ssl_session_token:
        ssl_session_token = environ.get('SSL_SESSION_TOKEN', '')

    return ssl_session_token


def _get_digest(environ):
    """Extract client digest response from environ dict"""
    return environ.get('RESPONSE', 'UNKNOWN')


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
    """Hardened version of the BuiltinSSLAdapter using a shared ssl context
    initializer which defaults to hardened values for ssl_version, ciphers and
    options arguments for use in setting up the socket security.
    This is particularly important in relation to mitigating a number of
    popular SSL attack vectors like POODLE and CRIME.
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

    def __init__(self, certificate, private_key, certificate_chain=None):
        """Initialize with parent constructor and set up a shared hardened SSL
        context to use in all future connections in the wrap method.
        """
        BuiltinSSLAdapter.__init__(self, certificate, private_key,
                                   certificate_chain)
        # Set up hardened SSL context once and for all
        dhparams = configuration.user_shared_dhparams
        self.ssl_ctx = hardened_ssl_context(configuration, self.private_key,
                                            self.certificate, dhparams)

    def __force_close(self, socket_list):
        """Force close each socket in socket_list ignoring any errors"""
        for clean_sock in socket_list:
            if clean_sock is None:
                continue
            try:
                clean_sock.close()
            except Exception, exc:
                pass

    def get_environ(self, ssl_sock):
        """Update SSL environ with SSL session token used for internal 
        WebDAVS session tracing
        """

        (client_addr, _) = ssl_sock.getpeername()
        ssl_environ = BuiltinSSLAdapter.get_environ(self, ssl_sock)
        ssl_master_key = get_ssl_master_key(configuration, ssl_sock)
        if ssl_master_key is not None:
                        ssl_environ['SSL_SESSION_TOKEN'] = make_digest(
                            'webdavs',
                            client_addr,
                            ssl_master_key,
                            configuration.site_digest_salt)
        return ssl_environ

    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries.
        Note the previously initialized SSL context is tuned to pass hardened
        ssl_version and ciphers arguments to the wrap_socket call. It also
        limits protocols, key reuse and disables compression for modern python
        versions to avoid a set of popular attack vectors.
        """
        _socket_list = [sock]
        try:
            # logger.debug("Wrapping socket in SSL/TLS: 0x%x : %s" %
            #             (id(sock), sock.getpeername()))
            logger.info("SSL/TLS session stats: %s" %
                        self.ssl_ctx.session_stats())
            ssl_sock = self.ssl_ctx.wrap_socket(sock, server_side=True)
            _socket_list.append(ssl_sock)
            ssl_env = self.get_environ(ssl_sock)
            logger.info("wrapped sock from %s with ciphers %s" %
                        (ssl_sock.getpeername(), ssl_sock.cipher()))

            (client_addr, client_port) = ssl_sock.getpeername()
            # logger.debug("system ssl_sock timeout: %s" % ssl_sock.gettimeout())
            session_timeout = io_session_timeout.get('davs', 0)
            if session_timeout > 0:
                ssl_sock.settimeout(float(session_timeout))
            # logger.debug("new ssl_sock timeout: %s" % ssl_sock.gettimeout())
        except ssl.SSLError:
            exc = sys.exc_info()[1]
            if exc.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it's connectable;
                # the 'ping' isn't SSL.
                return None, {}
            elif exc.errno == ssl.SSL_ERROR_SSL:
                logger.warning("SSL/TLS wrap failed: %s" % exc)
                if exc.args[1].find('http request') != -1:
                    # The client is speaking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError
                elif exc.args[1].find('unknown protocol') != -1:
                    # Drop clients speaking some non-HTTP protocol.
                    return None, {}
                elif exc.args[1].find('wrong version number') != -1 or \
                        exc.args[1].find('no shared cipher') != -1 or \
                        exc.args[1].find('inappropriate fallback') != -1 or \
                        exc.args[1].find('ccs received early') != -1:
                    # Drop clients trying banned protocol, cipher or operation
                    return None, {}
                else:
                    # Make sure we clean up before we forward
                    # unexpected SSL errors
                    self.__force_close(_socket_list)
            logger.error("unexpected SSL/TLS wrap failure: %s" % exc)
            raise exc

        return ssl_sock, ssl_env


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
        # logger.debug("Expired hash and digest caches")

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
        # Only sharelinks should be excluded from strict password policy
        if possible_sharelink_id(configuration, username):
            strict_policy = False
        else:
            strict_policy = True
        for user_obj in user_list:
            # list of User login objects for username
            offered = password
            allowed = user_obj.password
            if allowed is not None:
                # logger.debug("Password check for %s" % username)
                if check_password_hash(configuration, 'webdavs', username,
                                       offered, allowed, self.hash_cache,
                                       strict_policy):
                    return True
        return False

    def authDomainUser(self, realmname, username, password, environ):
        """Returns True if session is already authorized or
        the username / password pair is valid for the realm,
        False otherwise. Used for basic authentication.

        We explicitly compare against saved hash rather than password

        """
        ip_addr = _get_addr(environ)
        tcp_port = _get_port(environ)
        session_id = _get_ssl_session_token(environ)
        # logger.debug("session_id: %s" % session_id)
        success = False
        if session_id \
                and is_authorized_session(configuration,
                                          username,
                                          session_id):
            # logger.debug("found authorized session for: %s from %s:%s:%s" \
            #             % (username, ip_addr, tcp_port, session_id))
            success = True
        elif validate_session(configuration,
                              'davs',
                              username,
                              ip_addr,
                              tcp_port):
            # logger.debug("validated session: %s:%s:%s" %
            #              (ip_addr, tcp_port, session_id))
            logger.info("refresh user %s" % username)
            update_users(configuration, self.user_map, username)
            logger.info("in authDomainUser from %s:%s" % (ip_addr, tcp_port))
            offered = password
            if hit_rate_limit(configuration, "davs", ip_addr, username):
                logger.warning("Rate limiting login from %s" % ip_addr)
            elif self._check_auth_password(ip_addr,
                                           realmname,
                                           username,
                                           password):
                logger.info("Accepted login for %s from %s" %
                            (username, ip_addr))
                success = True
            else:
                logger.warning("Invalid login for %s from %s" %
                               (username, ip_addr))
            failed_count = update_rate_limit(configuration,
                                             "davs",
                                             ip_addr,
                                             username,
                                             success,
                                             offered)
            penalize_rate_limit(configuration, "davs", ip_addr, username,
                                failed_count)

            # Track newly authorized session

            if success and session_id:
                # logger.debug("auth passed for session: %s:%s -> %s" %
                #              (ip_addr, tcp_port, session_id))
                status = track_open_session(configuration,
                                            'davs',
                                            username,
                                            ip_addr,
                                            tcp_port,
                                            session_id=session_id,
                                            authorized=True)
                # logger.debug("track_open_session: %s" % status)
        # else:
        #    logger.debug("rejected session: %s:%s -> %s" \
        #        % (ip_addr, tcp_port, session_id))

        return success

    def isRealmUser(self, realmname, username, environ):
        """Returns True if session is already authorized or
        this username is valid for the realm, False otherwise.
        Used for basic authentication.

        Please note that this is always called for digest auth so we use it to
        update creds and reject users without digest password set.
        """
        ip_addr = _get_addr(environ)
        tcp_port = _get_port(environ)
        session_id = _get_ssl_session_token(environ)
        # logger.debug("session_id: %s" % session_id)
        success = False
        if session_id \
                and is_authorized_session(configuration,
                                          username,
                                          session_id):
            # logger.debug("found authorized session for: %s from %s:%s:%s" \
            #             % (username, ip_addr, tcp_port, session_id))
            success = True
        elif validate_session(configuration,
                              'davs',
                              username,
                              ip_addr,
                              tcp_port):
            # logger.debug("validated session: %s:%s:%s" %
            #              (ip_addr, tcp_port, session_id))
            update_users(configuration, self.user_map, username)

            if self._get_user_digests(ip_addr, realmname, username):
                # logger.debug("valid digest user %s from %s:%s" %
                #              (username, ip_addr, tcp_port))
                success = True
            else:
                logger.warning("invalid digest user %s from %s:%s" %
                               (username, ip_addr, tcp_port))

            # Track newly authorized session

            if success and session_id:
                # logger.debug("auth passed for session: %s:%s -> %s" %
                #              (ip_addr, tcp_port, session_id))
                status = track_open_session(configuration,
                                            'davs',
                                            username,
                                            ip_addr,
                                            tcp_port,
                                            session_id=session_id,
                                            authorized=True)
                # logger.debug("track_open_session: %s" % status)
        # else:
        #    logger.debug("rejected session: %s:%s -> %s" \
        #        % (ip_addr, tcp_port, session_id))

        return success

    def getRealmUserPassword(self, realmname, username, environ):
        """Return the password for the given username for the realm.

        Used for digest authentication and always called after isRealmUser
        so update creds is already applied. We just rate limit and check here.
        """

        # TODO: consider digest caching here!
        #       we should really use something like check_password_digest,
        #       but we need to return password to caller here.

        # print "DEBUG: env in getRealmUserPassword: %s" % environ
        addr = _get_addr(environ)
        offered = _get_digest(environ)
        # Only sharelinks should be excluded from strict password policy
        if possible_sharelink_id(configuration, username):
            strict_policy = False
        else:
            strict_policy = True
        self._expire_rate_limit()
        # logger.info("in getRealmUserPassword from %s" % addr)
        digest_users = self._get_user_digests(addr, realmname, username)
        # logger.info("found digest_users %s" % digest_users)
        try:
            # We expect only one - pick last
            digest = digest_users[-1].digest
            _, _, _, payload = digest.split("$")
            # logger.info("found payload %s" % payload)
            unscrambled = unscramble_digest(configuration.site_digest_salt,
                                            payload)
            _, _, password = unscrambled.split(":")
            # logger.info("found password")
            # TODO: we don't have a hook to log accepted digest logins
            # this one only means that user validation makes it to digest check
            logger.info("extracted digest for valid user %s from %s" %
                        (username, addr))
            # Mimic password policy compliance from check_password_digest here
            success = True
            try:
                assure_password_strength(configuration, password)
            except Exception, exc:
                if strict_policy:
                    msg = "%s password for %s" % ('webdavs', username) \
                        + "does not satisfy local policy: %s" % exc
                    logger.warning(msg)
                    success = False
        except Exception, exc:
            logger.error("failed to extract digest password: %s" % exc)
            success = False
        if hit_rate_limit(configuration, "davs", addr, username):
            logger.warning("Rate limiting login from %s" % addr)
            success = False
        failed_count = update_rate_limit(configuration, "davs", addr, username,
                                         success, offered)
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
        return super(MiGFolderResource, self).handleCopy(destPath,
                                                         depthInfinity)

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
        return [i for i in super(MiGFolderResource, self).getMemberNames() if
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

        # logger.debug("in getMember")
        res = FolderResource.getMember(self, name)
        if invisible_path(res.name):
            res = None
        # logger.debug("getMember found %s" % res)
        if res and not res.isCollection and \
                not isinstance(res, MiGFileResource):
            res = MiGFileResource(res.path, self.environ, res._filePath)
        elif res and res.isCollection and \
                not isinstance(res, MiGFolderResource):
            res = MiGFolderResource(res.path, self.environ, res._filePath)
        # logger.debug("getMember returning %s" % res)
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
        # logger.debug("in getDescendantsWrap for %s" % self)
        res = FolderResource.getDescendants(self, collections, resources,
                                            depthFirst, depth, addSelf)
        # logger.debug("getDescendants wrap returning %s" % res)
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
        # logger.debug("acceptable_chmod: %s" % davs_path)
        reply = acceptable_chmod(davs_path, mode, self.chmod_exceptions)
        if not reply:
            logger.warning("acceptable_chmod failed: %s %s %s" %
                           (davs_path, mode, self.chmod_exceptions))
        # logger.debug("acceptable_chmod returns: %s :: %s" % (davs_path,
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
        # logger.debug("_locToFilePath: %s" % path)
        username = _username_from_env(environ)
        # logger.debug("_locToFilePath %s: find chroot for %s" % (path, username))
        entries = login_map_lookup(self.daemon_conf, username)
        for entry in entries:
            if entry.chroot:
                user_chroot = os.path.join(configuration.user_home,
                                           entry.home)
                # Expand symlinked homes for aliases
                if os.path.islink(user_chroot):
                    try:
                        user_chroot = os.readlink(user_chroot)
                    except Exception, exc:
                        logger.error("could not expand link %s" % user_chroot)
                        continue
                break
        pathInfoParts = path.strip(os.sep).split(os.sep)
        abs_path = os.path.abspath(os.path.join(user_chroot, *pathInfoParts))
        try:
            abs_path = get_fs_path(configuration, abs_path, user_chroot,
                                   self.chroot_exceptions)
        except ValueError, vae:
            raise RuntimeError("Access out of bounds: %s in %s : %s"
                               % (path, user_chroot, vae))
        abs_path = force_unicode(abs_path)
        # logger.debug("_locToFilePath on %s: %s" % (path, abs_path))
        return abs_path

    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()

        Override to chroot and filter MiG invisible paths from content.
        """

        # logger.debug("getResourceInst: %s" % path)
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


def is_authorized_session(configuration, username, session_id):
    """Returns True if user session is open
    and authorized and within expire timestamp"""

    # logger.debug("session_id: %s, user_sessions: %s" %
    #             (session_id, user_sessions))
    result = False
    session_timeout = io_session_timeout.get('davs', 0)
    session = get_active_session(configuration,
                                 'davs',
                                 client_id=username,
                                 session_id=session_id)
    if session:
        authorized = session.get('authorized', False)
        timestamp = session.get('timestamp', 0)
        cur_timestamp = time.time()
        if authorized \
                and cur_timestamp - timestamp < session_timeout:
            result = True

    return result


def update_users(configuration, user_map, username):
    """Update creds dict for username and aliases"""
    # Only need to update users and shares here, since jobs only use sftp
    changed_users, changed_shares = [], []
    if possible_user_id(configuration, username):
        daemon_conf, changed_users = refresh_user_creds(configuration, 'davs',
                                                        username)
    if possible_sharelink_id(configuration, username):
        daemon_conf, changed_shares = refresh_share_creds(configuration,
                                                          'davs', username)
    # Add dummy user for litmus test if enabled in conf
    litmus_pw = daemon_conf.get('litmus_password', None)
    if username == litmus_id and litmus_pw and \
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
                pw_hash = generate_password_hash(configuration, litmus_pw)
                add_user_object(daemon_conf, litmus_id, litmus_home,
                                password=pw_hash)
            else:
                digest = generate_password_digest(
                    configuration, dav_domain, litmus_id, litmus_pw,
                    configuration.site_digest_salt)
                add_user_object(daemon_conf, litmus_id, litmus_home,
                                digest=digest)
    update_login_map(daemon_conf, changed_users, changed_jobs=[],
                     changed_shares=changed_shares)


class SessionExpire(threading.Thread):
    """Track expired sessions in a user thread"""

    def __init__(self):
        """Init session expire thread"""
        threading.Thread.__init__(self)

        self.session_timeout = io_session_timeout.get('davs', 0)
        self.shutdown = threading.Event()

    def _close_expired_sessions(self):
        "Check and close expired session"

        logger = configuration.logger
        closed_sessions = track_close_expired_sessions(configuration, 'davs')
        for (_, session) in closed_sessions.iteritems():
            msg = "closed expired session for: %s from %s:%s:%s" \
                % (session['client_id'],
                   session['ip_addr'],
                   session['tcp_port'],
                   session['session_id'])
            logger.info(msg)

        return closed_sessions

    def run(self):
        """Start session expire thread"""
        logger = configuration.logger
        logger.info("Starting SessionExpire thread: #%s" % self.ident)
        sleeptime = 1
        elapsed = 0
        while not self.shutdown.is_set():
            time.sleep(sleeptime)
            elapsed += sleeptime
            if elapsed > self.session_timeout:
                # logger.debug("session cleanup: %s" % time.time())
                self._close_expired_sessions()
                elapsed = 0

    def stop(self):
        """Stop session expire thread"""
        logger = configuration.logger
        logger.info("Stopping SessionExpire Thread: #%s" % self.ident)
        self.shutdown.set()
        self.join()
        # logger.info("debug SessionExpire Thread: #%s" % self.ident)


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
        # "verbose": 2,
        # "enable_loggers": ["lock_manager", "property_manager", "http_authenticator", ...]
        # "debug_methods": ["COPY", "DELETE", "GET", "HEAD", "LOCK", "MOVE", "OPTIONS", "PROPFIND", "PROPPATCH", "PUT", "UNLOCK"],
        # "verbose": 2,
        # "enable_loggers": ["http_authenticator"],
        # "debug_methods": ["PROPFIND", "PUT"],
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
    # print('User list: %s' % config['user_mapping'])

    # Find and mangle HTTPAuthenticator in application stack

    # app_authenticator = _find_authenticator(app)

    # print('Config: %s' % config)
    # print('app auth: %s' % app_authenticator)

    wsgiserver.CherryPyWSGIServer.ssl_adapter = None
    nossl = config.get('nossl', False)
    if not nossl:
        cert = config['ssl_certificate'] = configuration.user_davs_key
        key = config['ssl_private_key'] = configuration.user_davs_key
        chain = config['ssl_certificate_chain'] = ''
        # wsgiserver.CherryPyWSGIServer.ssl_adapter = BuiltinSSLAdapter(
        #     cert, key, chain)
        wsgiserver.CherryPyWSGIServer.ssl_adapter = HardenedSSLAdapter(
            cert, key, chain)

    # Use bundled CherryPy WSGI Server to support SSL
    version = "%s WebDAV" % configuration.short_title
    server = wsgiserver.CherryPyWSGIServer((config["host"], config["port"]),
                                           app, server_name=version)

    logger.info('Listening on %(host)s (%(port)s)' % config)

    sessionexpiretracker = SessionExpire()
    try:
        sessionexpiretracker.start()
        server.start()
    except KeyboardInterrupt:
        server.stop()
        sessionexpiretracker.stop()
        # forward KeyboardInterrupt to main thread
        raise
    except Exception:
        sessionexpiretracker.stop()
        # forward error to main thread
        raise


if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("webdavs", configuration.user_davs_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    signal.signal(signal.SIGHUP, hangup_handler)

    # Allow configuration overrides on command line
    litmus_password = None
    readonly = False
    nossl = False
    if sys.argv[2:]:
        configuration.user_davs_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_davs_port = int(sys.argv[3])
    if sys.argv[4:]:
        litmus_password = sys.argv[4]
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

    # Lookup chroot exceptions once and for all
    chroot_exceptions = user_chroot_exceptions(configuration)
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
        'shares': [],
        'login_map': {},
        # NOTE: enable for litmus test (http://www.webdav.org/neon/litmus/)
        #
        # USAGE:
        # export HTTPS_URL="https://SOMEADDRESS:DAVSPORT"
        # export TESTROOT=$PWD; export HTDOCS=$PWD/htdocs
        # ./litmus -k $HTTPS_URL litmus test
        # or
        # ./configure --with-ssl
        # make URL=$HTTPS_URL CREDS="%(litmus_id)s %(litmus_password)s" check
        'litmus_password': litmus_password,
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
        logger.info(traceback.format_exc())
