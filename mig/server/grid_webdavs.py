#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
import sys
import threading
import time
import traceback
from functools import wraps

try:
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
    # Use cherrypy bundled with wsgidav < 2.0 - needs module path mangling
    from wsgidav.server import __file__ as server_init_path
    sys.path.append(os.path.dirname(server_init_path))
    from cherrypy import wsgiserver
    from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter, ssl
    from wsgidav.debug_filter import WsgiDavDebugFilter
    from wsgidav.dir_browser import WsgiDavDirBrowser
    from wsgidav.error_printer import ErrorPrinter
    from wsgidav.fs_dav_provider import FileResource, FolderResource, \
        FilesystemProvider
    from wsgidav.domain_controller import WsgiDAVDomainController
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
    from wsgidav.util import getRfc1123Time
except ImportError, ierr:
    print "ERROR: the python wsgidav module is required for this daemon"
    print "You may need to install cherrypy if your wsgidav does not bundle it"
    sys.exit(1)

from shared.base import invisible_path, force_unicode
from shared.conf import get_configuration_object
from shared.defaults import dav_domain, litmus_id, io_session_timeout
from shared.fileio import check_write_access, user_chroot_exceptions
from shared.gdp import project_open, project_close, project_log
from shared.griddaemons import get_fs_path, acceptable_chmod, \
    default_max_user_hits, default_user_abuse_hits, \
    default_proto_abuse_hits, default_max_secret_hits, \
    default_username_validator, refresh_user_creds, refresh_share_creds, \
    update_login_map, login_map_lookup, hit_rate_limit, expire_rate_limit, \
    add_user_object, track_open_session, track_close_session, \
    track_close_expired_sessions, get_active_session, \
    check_twofactor_session, handle_auth_attempt
from shared.pwhash import make_scramble
from shared.sslsession import ssl_session_token
from shared.tlsserver import hardened_ssl_context
from shared.logger import daemon_logger, daemon_gdp_logger, \
    register_hangup_handler
from shared.notification import send_system_notification
from shared.pwhash import unscramble_digest, assure_password_strength
from shared.useradm import check_password_hash, generate_password_hash, \
    generate_password_digest
from shared.validstring import possible_user_id, possible_sharelink_id

configuration, logger = None, None


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
    token = environ.get('HTTP_X_SSL_SESSION_TOKEN', '')
    if not token:
        token = environ.get('SSL_SESSION_TOKEN', '')

    return token


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


def _open_session(username, ip_addr, tcp_port, session_id):
    """Keep track of new session"""
    # logger.debug("auth succeeded for %s from %s:%s with session: %s" %
    #             (username, ip_addr, tcp_port, session_id))

    status = track_open_session(configuration,
                                'davs',
                                username,
                                ip_addr,
                                tcp_port,
                                session_id=session_id,
                                authorized=True)

    if status and configuration.site_enable_gdp:
        (status, msg) = project_open(configuration,
                                     'davs',
                                     ip_addr,
                                     username)
        if not status:
            track_close_session(configuration,
                                'davs',
                                username,
                                ip_addr,
                                tcp_port,
                                session_id=session_id)

            send_system_notification(username, ['DAVS', 'ERROR'],
                                     msg, configuration)

    return status


def _close_session(username, ip_addr, tcp_port, session_id):
    """Mark session as closed"""
    # logger.debug("_close_session for %s from %s:%s with session: %s" %
    #              (username, ip_addr, tcp_port, session_id))

    track_close_session(configuration,
                        'davs',
                        username,
                        ip_addr,
                        tcp_port,
                        session_id=session_id)

    if configuration.site_enable_gdp:
        project_close(
            configuration,
            'davs',
            ip_addr,
            user_id=username)


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
        ssl_environ = BuiltinSSLAdapter.get_environ(self, ssl_sock)
        token = ssl_session_token(configuration,
                                  ssl_sock,
                                  'davs')
        if token is not None:
            ssl_environ['SSL_SESSION_TOKEN'] = token

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
            # logger.debug("SSL/TLS session stats: %s" %
            #             self.ssl_ctx.session_stats())
            ssl_sock = self.ssl_ctx.wrap_socket(sock, server_side=True)
            _socket_list.append(ssl_sock)
            ssl_env = self.get_environ(ssl_sock)
            # logger.debug("wrapped sock from %s with ciphers %s" %
            #             (ssl_sock.getpeername(), ssl_sock.cipher()))
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


class MiGHTTPAuthenticator(HTTPAuthenticator):
    """
    Override the default HTTPAuthenticator to include support for:
    1) Auth logging
    2) Auth statistics
    3) SSL session based auth
    4) Rate limit auth throtteling
    """
    __application = None
    min_expire_delay = 0
    last_expire = 0

    def __init__(self, application, config):
        self.min_expire_delay = 300
        self.last_expire = time.time()
        self.__application = application
        self._init_stats(config['enable_stats'])
        super(MiGHTTPAuthenticator, self).__init__(
            self._application_wrapper, config)

    def _application_wrapper(self, environ, start_response):
        """Prevent HTTPAuthenticator (parent) from sending response
        to client while auth is being processed
        by  MiGHTTPAuthenticator.authRequest
        """
        result = None
        # If _NOT_ in authorization mode then allow
        # HTTPAuthenticator to call _application
        if not "HTTP_AUTHORIZATION" in environ:
            result = self.__application(environ, start_response)

        return result

    def _init_stats(self, enabled):
        """Init statistics cache"""
        self.stats = {
            'enabled': enabled,
            'total': lambda s:
            s['total_accepted'](s)
            + s['total_rejected'](s),
            'total_accepted': lambda s:
            s['session']
            + s['password_accepted']
            + s['digest_accepted'],
            'total_rejected': lambda s:
            s['invalid_twofa']
            + s['invalid_user']
            + s['invalid_username']
            + s['hit_rate_limit']
            + s['digest_failed']
            + s['password_failed'],
            'session': 0,
            'invalid_twofa': 0,
            'invalid_user': 0,
            'invalid_username': 0,
            'hit_rate_limit': 0,
            'digest_accepted': 0,
            'digest_failed': 0,
            'password_accepted': 0,
            'password_failed': 0,
        }

    def _update_stats(self,
                      valid_session,
                      invalid_username,
                      invalid_user,
                      valid_twofa,
                      digest_auth,
                      valid_digest,
                      password_auth,
                      valid_password,
                      exceeded_rate_limit):
        """Update statistics cache"""
        if self.stats['enabled']:
            stats = self.stats
            if valid_session:
                stats['session'] += 1
            elif exceeded_rate_limit:
                stats['hit_rate_limit'] += 1
            elif invalid_username:
                stats['invalid_username'] += 1
            elif invalid_user:
                stats['invalid_user'] += 1
            elif digest_auth:
                if valid_digest and valid_twofa:
                    stats['digest_accepted'] += 1
                elif valid_digest and not valid_twofa:
                    stats['invalid_twofa'] += 1
                else:
                    stats['digest_failed'] += 1
            elif password_auth:
                if valid_password and valid_twofa:
                    stats['password_accepted'] += 1
                elif valid_password and not valid_twofa:
                    stats['invalid_twofa'] += 1
                else:
                    stats['password_failed'] += 1

    def _expire_rate_limit(self):
        """Expire old entries in the rate limit dictionary"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            expire_rate_limit(configuration, "davs")

    def _authheader(self, environ):
        """Returns dict with HTTP AUTH REQUEST header
        This code is blended/modified version of
        HTTPAuthenticator.authBasicAuthRequest and
        HTTPAuthenticator.authDigestAuthRequest"""
        authheaderdict = dict([])
        authheaders = environ.get("HTTP_AUTHORIZATION", '')

        if authheaders.startswith("Basic "):
            authvalue = authheaders[len("Basic "):]
            authvalue = authvalue.strip().decode("base64")
            authheaderdict['username'], password = authvalue.split(":", 1)
            if password:
                password = make_scramble(password, None)
            authheaderdict['password'] = password
        else:
            authheaders += ","
            # Hotfix for Windows file manager and OSX Finder:
            # Some clients don't urlencode paths in auth header, so uri value may
            # contain commas, which break the usual regex headerparser. Example:
            # Digest username="user",realm="/",uri="a,b.txt",nc=00000001, ...
            # -> [..., ('uri', '"a'), ('nc', '00000001'), ...]
            # Override any such values with carefully extracted ones.
            authheaderlist = self._headerparser.findall(authheaders)
            authheaderfixlist = self._headerfixparser.findall(authheaders)
            if authheaderfixlist:
                # _logger.debug("Fixing authheader comma-parsing: extend %s with %s" \
                #              % (authheaderlist, authheaderfixlist))
                authheaderlist += authheaderfixlist
            for authheader in authheaderlist:
                authheaderkey = authheader[0]
                authheadervalue = authheader[1].strip().strip("\"")
                authheaderdict[authheaderkey] = authheadervalue

        return authheaderdict

    def authBasicAuthRequest(self, environ, start_response):
        """Overrides HTTPAuthenticator.authBasicAuthRequest"""
        return self.authRequest(environ, start_response, password_auth=True)

    def authDigestAuthRequest(self, environ, start_response):
        """Overrides HTTPAuthenticator.authDigestAuthRequest"""
        return self.authRequest(environ, start_response, digest_auth=True)

    def authRequest(self, environ, start_response,
                    password_auth=False, digest_auth=False):
        """Overrides HTTPAuthenticator.authRequest
        Authorize users and log auth attempts.
        When auth is granted the session is tracked
        based on the SSL-session-id for reuse in future requests
        from the same client on the same socket.

        The following is checked before granting auth:
        1) Valid username
        2) Valid user (Does user exist and enabled WebDAVS)
        3) Valid 2FA session (if 2FA is enabled)
        4) Hit rate limit (To many auth attempts)
        5) Valid pre-authorized SSL session
        6) Valid password (if password enabled)
        7) Valid digest (if digest enabled)
        """
        result = None
        response_ok = False
        pre_authorized = False
        secret = None
        authorized = False
        disconnect = False
        valid_session = False
        valid_password = False
        valid_digest = False
        valid_twofa = False
        exceeded_rate_limit = False
        invalid_username = False
        invalid_user = False
        ip_addr = _get_addr(environ)
        tcp_port = _get_port(environ)
        daemon_conf = configuration.daemon_conf
        max_user_hits = daemon_conf['auth_limits']['max_user_hits']
        user_abuse_hits = daemon_conf['auth_limits']['user_abuse_hits']
        proto_abuse_hits = daemon_conf['auth_limits']['proto_abuse_hits']
        max_secret_hits = daemon_conf['auth_limits']['max_secret_hits']
        authtype = ''
        if password_auth:
            authtype = 'password'
        elif digest_auth:
            authtype = 'digest'

        # For e.g. GDP we require all logins to match active 2FA session IP,
        # but otherwise user may freely switch net during 2FA lifetime.
        if configuration.site_twofactor_strict_address:
            enforce_address = ip_addr
        else:
            enforce_address = None

        session_id = _get_ssl_session_token(environ)
        authheader = self._authheader(environ)
        username = authheader.get('username', None)
        if session_id and is_authorized_session(configuration,
                                                username,
                                                session_id):
            valid_session = authorized = pre_authorized = True
            environ['http_authenticator.username'] = username
            environ['http_authenticator.realm'] = '/'
        elif hit_rate_limit(configuration, 'davs', ip_addr, username,
                            max_user_hits=max_user_hits):
            exceeded_rate_limit = True
        elif not default_username_validator(configuration, username):
            invalid_username = True
        elif password_auth or digest_auth:
            if password_auth:
                result = super(MiGHTTPAuthenticator, self) \
                    .authBasicAuthRequest(environ, start_response)
            elif digest_auth:
                result = super(MiGHTTPAuthenticator, self) \
                    .authDigestAuthRequest(environ, start_response)
            auth_username = environ.get('http_authenticator.username', None)
            auth_realm = environ.get('http_authenticator.realm', None)
            print "auth_username: %s" % auth_username
            print "auth_realm: %s" % auth_realm
            if auth_username and auth_username == username and auth_realm:
                if password_auth:
                    valid_password = True
                elif digest_auth:
                    valid_digest = True
                if check_twofactor_session(configuration, username,
                                           enforce_address, 'davs'):
                    valid_twofa = True
                    valid_session = \
                        _open_session(username, ip_addr, tcp_port, session_id)
            elif not environ.get('http_authenticator.valid_user', False):
                invalid_user = True
        else:
            logger.error(
                "Neither password NOR digest enabled for %s from %s:%s"
                % (username, ip_addr, tcp_port))

        if not pre_authorized:
            self._expire_rate_limit()

            # For digest auth we use SSL_SESSION_TOKEN as secret
            # because some clients uses a new digest token for every requerst
            # and therefore we do not have any other unique identifiers

            if password_auth:
                secret = authheader.get('password', '')
            if not secret:
                secret = environ.get('SSL_SESSION_TOKEN', None)

            # Update rate limits and write to auth log

            password_enabled = environ.get('http_authenticator.password_enabled', False)
            digest_enabled = environ.get('http_authenticator.digest_enabled', False)
            (authorized, disconnect) = handle_auth_attempt(
                configuration,
                'davs',
                authtype,
                username,
                ip_addr,
                tcp_port,
                secret=secret,
                invalid_username=invalid_username,
                invalid_user=invalid_user,
                valid_twofa=valid_twofa,
                authtype_enabled=(password_enabled or digest_enabled),
                valid_auth=(valid_password or valid_digest),
                exceeded_rate_limit=exceeded_rate_limit,
                user_abuse_hits=user_abuse_hits,
                proto_abuse_hits=proto_abuse_hits,
                max_secret_hits=max_secret_hits,
            )

        if authorized and valid_session:
            result = self.__application(environ, start_response)
            if result:
                response_ok = True
            else:
                _close_session(username, ip_addr, tcp_port, session_id)
                logger.error(
                    "MiGHTTPAuthenticator.authRequest failed for %s from %s:%s"
                    % (username, ip_addr, tcp_port))
        elif authorized and not valid_session:
            response_ok = True
            logger.error("Authorized but no valid session for %s from %s:%s"
                         % (username, ip_addr, tcp_port))
            # logger.debug("503 Service Unavailable")
            start_response("503 Service Unavailable",
                           [("Content-Length", "0"),
                            ("Date", getRfc1123Time()),
                            ])
            result = ['']
        elif disconnect:
            response_ok = True
            # logger.debug("403 Forbidden for %s from %s:%s" \
            #   % (username, ip_addr, tcp_port))
            start_response("403 Forbidden", [("Content-Length", "0"),
                                             ("Date", getRfc1123Time()),
                                             ])
            result = ['']
        else:
            result = self.sendDigestAuthResponse(environ, start_response)
            if result:
                response_ok = True
            else:
                logger.error(
                    "MiGHTTPAuthenticator.sendDigestAuthResponse failed"
                    + " for %s from %s:%s"
                    % (username, ip_addr, tcp_port))

        if not response_ok:
            logger.error("MiGHTTPAuthenticator: 400 Bad Request"
                         + " for %s from %s:%s"
                         % (username, ip_addr, tcp_port))
            start_response("400 Bad Request", [("Content-Length", "0"),
                                               ("Date", getRfc1123Time()),
                                               ])
            result = ['']

        self._update_stats(
            pre_authorized,
            invalid_username,
            invalid_user,
            valid_twofa,
            digest_auth,
            valid_digest,
            password_auth,
            valid_password,
            exceeded_rate_limit)

        return result


class MiGWsgiDAVDomainController(WsgiDAVDomainController):
    """Override auth database lookups to use username and password hash for
    basic auth and digest otherwise.

    NOTE: The username arguments are already on utf8 here so no need to force.
    """

    root_dir = None
    min_expire_delay = 0
    last_expire = 0

    def __init__(self, root_dir, userMap):
        WsgiDAVDomainController.__init__(self, userMap)
        # Alias to CamelCase version userMap required internally
        self.root_dir = root_dir
        self.user_map = self.userMap = userMap
        self.last_expire = time.time()
        self.min_expire_delay = 300
        self.hash_cache = {}
        self.digest_cache = {}

    def _expire_caches(self):
        """Expire old entries in the hash and digest caches"""
        self.hash_cache.clear()
        self.digest_cache.clear()
        # logger.debug("Expired hash and digest caches")

    def _expire_volatile(self):
        """Expire old entries in the volatile helper dictionaries"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            self._expire_caches()

    def _get_user_digests(self, realm, username):
        """Find the allowed digest values for supplied username - this is for
        use in the actual digest authorization.
        """
        user_list = self.user_map[realm].get(username, [])
        return [i for i in user_list if i.digest is not None]

    def authDomainUser(self, realmname, username, password, environ):
        """Returns True if username / password pair is valid for the realm,
        False otherwise.
        This method is only used for the 'basic' auth method, while
        'digest' auth takes another code path.

        NOTE: We explicitly compare against saved hash rather than password.

        NOTE: Set environ['http_authenticator.valid_user'] for use in
              MiGHTTPAuthenticator.authRequest
        """

        # logger.debug("auth:authDomainUser: " \
        #     + "realmname: %s, username: %s, password: %s" \
        #     % (realmname, username, password))
        success = False
        password_auth = False
        # logger.debug("refresh user %s" % username)
        update_users(configuration, self.user_map, username)
        user_list = self.user_map[realmname].get(username, [])
        if not user_list \
            and not os.path.islink(
                os.path.join(self.root_dir, username)):
            environ['http_authenticator.valid_user'] = False
        else:
            environ['http_authenticator.valid_user'] = True

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
                password_auth = True
                # logger.debug("Password check for %s" % username)
                if check_password_hash(configuration, 'webdavs', username,
                                       offered, allowed, self.hash_cache,
                                       strict_policy):
                    success = True

        if password_auth:
            environ['http_authenticator.password_enabled'] = True
        else:
            environ['http_authenticator.password_enabled'] = False

        return success

    def isRealmUser(self, realmname, username, environ):
        """Returns True if this username is valid for the realm,
        False otherwise.

        Please note that this is always called for digest auth so we use it to
        update creds and reject users without digest password set.

        NOTE: Set environ['http_authenticator.valid_user'] for use in
              MiGHTTPAuthenticator.authRequest
        """
        # logger.debug("auth:isRealmUser: realmname: %s, username: %s" \
        #     % (realmname, username))
        success = False
        # logger.debug("refresh user %s" % username)
        update_users(configuration, self.user_map, username)
        if not self._get_user_digests(realmname, username) \
            and not os.path.islink(
                os.path.join(self.root_dir, username)):
            success = environ['http_authenticator.valid_user'] = False
        else:
            success = environ['http_authenticator.valid_user'] = True

        return success

    def getRealmUserPassword(self, realmname, username, environ):
        """Return the password for the given username for the realm.

        Used only for 'digest' auth and always called after isRealmUser, so
        update creds is already applied.
        """
        # TODO: consider digest caching here!
        #       we should really use something like check_password_digest,
        #       but we need to return password to caller here.

        # print "DEBUG: env in getRealmUserPassword: %s" % environ
        # traceback.print_stack()
        # logger.debug("auth:getRealmUserPassword: " \
        #      + "realmname: %s, username: %s" \
        #     % (realmname, username))
        # Only sharelinks should be excluded from strict password policy
        digest_enabled = False
        if possible_sharelink_id(configuration, username):
            strict_policy = False
        else:
            strict_policy = True
        digest_users = self._get_user_digests(realmname, username)
        # logger.debug("found digest_users %s" % digest_users)
        try:
            # We expect only one - pick last
            digest = digest_users[-1].digest
            _, _, _, payload = digest.split("$")
            # logger.debug("found payload %s" % payload)
            unscrambled = unscramble_digest(configuration.site_digest_salt,
                                            payload)
            _, _, password = unscrambled.split(":")
            # Mimic password policy compliance from check_password_digest here
            try:
                assure_password_strength(configuration, password)
            except Exception, exc:
                if strict_policy:
                    msg = "%s password for %s" % ('webdavs', username) \
                        + "does not satisfy local policy: %s" % exc
                    logger.warning(msg)
                    password = ''
            digest_enabled = True
        except Exception, exc:
            digest_enabled = False
            logger.error("failed to extract digest password: %s" % exc)
            password = ''

        if digest_enabled:
            environ['http_authenticator.digest_enabled'] = True
        else:
            environ['http_authenticator.digest_enabled'] = False
        return password


class MiGFileResource(FileResource):
    """Hide invisible files from all access.
    All file access starts with object init so it is enough to make sure we
    refuse any hidden files in the constructor.
    Parent constructor saves environ as self.environ for later use in chroot.
    """

    def __init__(self, path, environ, filePath):
        self.username = _username_from_env(environ)
        self.ip_addr = _get_addr(environ)
        FileResource.__init__(self, path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    def __allow_handle(method):
        """Decorator wrapper for _handle_allowed"""
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if method.__name__ == 'handleCopy':
                _handle_allowed("copy", self._filePath)
            elif method.__name__ == 'handleMove':
                _handle_allowed("move", self._filePath)
            elif method.__name__ == 'handleDelete':
                _handle_allowed("delete", self._filePath)
            else:
                _handle_allowed("unknown", self._filePath)
            return method(self, *method_args, **method_kwargs)
        return _impl

    def __gdp_log(method):
        """Decorator used for GDP logging"""
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if not configuration.site_enable_gdp:
                return method(self, *method_args, **method_kwargs)
            operation = method.__name__
            src_path = self.path
            dst_path = None
            log_src_path = None
            log_dst_path = None
            if operation == "handleCopy":
                dst_path = method_args[0]
                log_action = "copied"
                log_src_path = src_path.strip('/')
                log_dst_path = dst_path.strip('/')
            elif operation == "handleMove":
                dst_path = method_args[0]
                log_action = "moved"
                log_src_path = src_path.strip('/')
                log_dst_path = dst_path.strip('/')
            elif operation == "handleDelete":
                log_action = "deleted"
                log_src_path = src_path.strip('/')
            elif operation == "getContent":
                log_action = "accessed"
                log_src_path = src_path.strip('/')
            elif operation == "beginWrite":
                log_action = "modified"
                log_src_path = src_path.strip('/')
            else:
                logger.warning("GDP log for '%s' _NOT_ implemented"
                               % operation)
                raise DAVError(HTTP_FORBIDDEN)
            if not project_log(configuration,
                               'davs',
                               self.username,
                               self.ip_addr,
                               log_action,
                               path=log_src_path,
                               dst_path=log_dst_path,
                               ):
                raise DAVError(HTTP_FORBIDDEN)
            try:
                result = method(self, *method_args, **method_kwargs)
            except Exception, exc:
                result = None
                logger_msg = "%s failed: '%s'" % (operation, src_path)
                if dst_path is not None:
                    logger_msg += " -> '%s'" % dst_path
                logger_msg += ": %s" % exc
                logger.error(logger_msg)
                project_log(configuration,
                            'davs',
                            self.username,
                            self.ip_addr,
                            log_action,
                            failed=True,
                            path=log_src_path,
                            dst_path=log_dst_path,
                            details=exc,
                            )
                raise
            return result
        return _impl

    @__allow_handle
    @__gdp_log
    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively, but with our restrictions"""
        return super(MiGFileResource, self).handleCopy(
            destPath, depthInfinity)

    @__allow_handle
    @__gdp_log
    def handleMove(self, destPath):
        """Handle a MOVE request natively, but with our restrictions"""
        return super(MiGFileResource, self).handleMove(destPath)

    @__allow_handle
    @__gdp_log
    def handleDelete(self):
        """Handle a DELETE request natively, but with our restrictions"""
        return super(MiGFileResource, self).handleDelete()

    @__gdp_log
    def getContent(self):
        """Handle a GET request natively and log for GDP"""
        return super(MiGFileResource, self).getContent()

    @__gdp_log
    def beginWrite(self, contentType=None):
        """Handle a PUT request natively and log for GDP"""
        return super(MiGFileResource, self).beginWrite()


class MiGFolderResource(FolderResource):
    """Hide invisible files from all access.
    We must override getMemberNames to filter out hidden names and getMember
    to avoid inherited methods like getDescendants from receiving the parent
    unrestricted FileResource and FolderResource objects when doing e.g.
    directory listings.
    Parent constructor saves environ as self.environ for later use in chroot.
    """

    def __init__(self, path, environ, filePath):
        self.username = _username_from_env(environ)
        self.ip_addr = _get_addr(environ)
        FolderResource.__init__(self, path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    def __allow_handle(method):
        """Decorator wrapper for _handle_allowed"""
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if method.__name__ == 'handleCopy':
                _handle_allowed("copy", self._filePath)
            elif method.__name__ == 'handleMove':
                _handle_allowed("move", self._filePath)
            elif method.__name__ == 'handleDelete':
                _handle_allowed("delete", self._filePath)
            else:
                _handle_allowed("unknown", self._filePath)
            return method(self, *method_args, **method_kwargs)
        return _impl

    def __gdp_log(method):
        """Decorator used for GDP logging"""
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if not configuration.site_enable_gdp:
                return method(self, *method_args, **method_kwargs)
            operation = method.__name__
            src_path = self.path
            dst_path = None
            log_src_path = None
            log_dst_path = None
            if operation == "handleCopy":
                dst_path = method_args[0]
                log_action = "copied"
                log_src_path = src_path.strip('/')
                log_dst_path = dst_path.strip('/')
            elif operation == "handleMove":
                dst_path = method_args[0]
                log_action = "moved"
                log_src_path = src_path.strip('/')
                log_dst_path = dst_path.strip('/')
            elif operation == "handleDelete":
                log_action = "deleted"
                log_src_path = src_path.strip('/')
            elif operation == "createCollection":
                log_action = "created"
                dst_path = method_args[0]
                relpath = "%s%s" % (src_path, dst_path)
                log_src_path = relpath.strip('/')
            elif operation == "createEmptyResource":
                log_action = "created"
                dst_path = method_args[0]
                relpath = "%s%s" % (src_path, dst_path)
                log_src_path = relpath.strip('/')
            elif operation == "getMemberNames":
                log_action = "accessed"
                log_src_path = src_path.strip('/')
            else:
                logger.warning("GDP log for '%s' _NOT_ implemented"
                               % operation)
                raise DAVError(HTTP_FORBIDDEN)
            if not log_src_path:
                log_src_path = '.'
            if not project_log(configuration,
                               'davs',
                               self.username,
                               self.ip_addr,
                               log_action,
                               path=log_src_path,
                               dst_path=log_dst_path,
                               ):
                raise DAVError(HTTP_FORBIDDEN)
            try:
                result = method(self, *method_args, **method_kwargs)
            except Exception, exc:
                result = None
                logger_msg = "%s failed: '%s'" % (operation, src_path)
                if dst_path is not None:
                    logger_msg += " -> '%s'" % dst_path
                logger_msg += ": %s" % exc
                logger.error(logger_msg)
                project_log(configuration,
                            'davs',
                            self.username,
                            self.ip_addr,
                            log_action,
                            failed=True,
                            path=log_src_path,
                            dst_path=log_dst_path,
                            details=exc,
                            )
                raise
            return result
        return _impl

    @__allow_handle
    @__gdp_log
    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively, but with our restrictions"""
        return super(MiGFolderResource, self).handleCopy(
            destPath, depthInfinity)

    @__allow_handle
    @__gdp_log
    def handleMove(self, destPath):
        """Handle a MOVE request natively, but with our restrictions"""
        return super(MiGFolderResource, self).handleMove(destPath)

    @__allow_handle
    @__gdp_log
    def handleDelete(self):
        """Handle a DELETE request natively, but with our restrictions"""
        return super(MiGFolderResource, self).handleDelete()

    @__gdp_log
    def createCollection(self, name):
        """Handle a MKCOL request natively, but with our restrictions"""
        return super(MiGFolderResource, self).createCollection(name)

    @__gdp_log
    def createEmptyResource(self, name):
        """Handle operation of same name, but with our restrictions"""
        return super(MiGFolderResource, self).createEmptyResource(name)

    @__gdp_log
    def getMemberNames(self):
        """Return list of direct collection member names (utf-8 encoded).

        See DAVCollection.getMemberNames()

        Use parent version and filter out any invisible file names.
        """
        # logger.debug("in getMemberNames: %s" % self.path)
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
        # logger.debug("in getMember: %s" % name)
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
        if path is None:
            raise RuntimeError("Invalid path: %s" % path)
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
        pathInfoParts = path.strip('/').split('/')
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
        # logger.debug("SessionExpire Thread: #%s" % self.ident)


class LogStats(threading.Thread):
    """Log server and auth statistics """

    def __init__(self, config, server,
                 interval=60, idle_only=False, change_only=False):
        """Init LogStats thread"""
        threading.Thread.__init__(self)
        self.config = config
        if not self.config['enable_stats']:
            logger.info("stats _NOT_ enabled")
            return
        self.server = server
        self.shutdown = threading.Event()
        self.interval = interval
        self.idle_only = idle_only
        self.change_only = change_only
        self.last_http_requests = 0
        self.stats = {'server': server.stats}
        try:
            self.stats['auth'] = \
                (_find_authenticator(self.server.wsgi_app)).stats
        except Exception:
            self.stats['auth'] = None
            logger.warning("Failed to retreive auth stats")

    def _log_stats(self, force=False):
        """Perform actual logging"""
        try:
            server_stats = self.stats['server']
            auth_stats = self.stats['auth']
            queue = int(server_stats['Queue'](server_stats))
            threads = int(server_stats['Threads'](server_stats))
            threads_idle = int(server_stats['Threads Idle'](server_stats))
            http_requests = int(server_stats['Requests'](server_stats))
            if force \
                    or ((not self.change_only
                         or self.last_http_requests != http_requests)
                        and (not self.idle_only or threads_idle == threads)):
                socket_connections = int(server_stats['Accepts'])
                bytes_read = \
                    float(server_stats['Bytes Read'](server_stats))
                bytes_written = \
                    float(server_stats['Bytes Written'](server_stats))
                socket_connections_sec = \
                    float(server_stats['Accepts/sec'](server_stats))
                read_throughput = \
                    float(server_stats['Read Throughput'](server_stats))
                write_throughput = \
                    float(server_stats['Write Throughput'](server_stats))
                runtime = \
                    float(server_stats['Run time'](server_stats))
                worktime = \
                    float(server_stats['Work Time'](server_stats))
                socket_errors = \
                    int(server_stats['Socket Errors'])
                msg = "\n------------------------------------------------\n" \
                    + "\t\tServer\n" \
                    + "------------------------------------------------\n" \
                    + "Connection queue:\t\t %d\n" \
                    % queue \
                    + "Active Threads:\t\t\t %d/%d\n" \
                    % (threads-threads_idle, threads) \
                    + "Total Socket connections:\t %d\n" \
                    % socket_connections \
                    + "Total Socket Errors:\t\t %d\n" \
                    % socket_errors \
                    + "Total HTTP Requests:\t\t %d\n" \
                    % http_requests \
                    + "Total Bytes Read (MB):\t\t %.4f\n" \
                    % (bytes_read/1024**2) \
                    + "Total Bytes Written (MB):\t %.4f\n" \
                    % (bytes_written/1024**2) \
                    + "Socket connections/sec:\t\t %.4f\n" \
                    % socket_connections_sec \
                    + "Read Throughput (MB/sec):\t %.4f\n" \
                    % (read_throughput/1024**2) \
                    + "Write Throughput (MB/sec):\t %.4f\n" \
                    % (write_throughput/1024**2) \
                    + "Total Run time (secs):\t\t %.4f\n" % runtime \
                    + "Total Work Time (secs):\t\t %.4f\n" % worktime \
                    + "------------------------------------------------\n"
                if auth_stats:
                    msg += "\t\tAUTHORIZATION\n" \
                        + "------------------------------------------------\n" \
                        + "Total attempts:\t\t %d\n" \
                        % auth_stats['total'](auth_stats) \
                        + "Total accepts:\t\t %d\n" \
                        % auth_stats['total_accepted'](auth_stats) \
                        + "Total sessions accepts:\t %d\n" \
                        % auth_stats['session'] \
                        + "Total digest accepts:\t %d\n" \
                        % auth_stats['digest_accepted'] \
                        + "Total password accepts:\t %d\n" \
                        % auth_stats['password_accepted'] \
                        + "Total Rejects:\t\t %d\n" \
                        % auth_stats['total_rejected'](auth_stats) \
                        + "Total digest rejects:\t %d\n" \
                        % auth_stats['digest_failed'] \
                        + "Total password rejects:\t %d\n" \
                        % auth_stats['password_failed'] \
                        + "Total username rejects:\t %d\n" \
                        % auth_stats['invalid_username'] \
                        + "Total user rejects :\t %d\n" \
                        % auth_stats['invalid_user'] \
                        + "Total 2fa rejects:\t %d\n" \
                        % auth_stats['invalid_twofa'] \
                        + "Total hit rate rejects:\t %d\n" \
                        % auth_stats['hit_rate_limit'] \
                        + "------------------------------------------------\n"
                logger.info(msg)
                self.last_http_requests = http_requests
        except Exception, exc:
            logger.error("Failed to log statistics: %s" % exc)
            logger.info(traceback.format_exc())

    def run(self):
        """Start LogStats thread"""
        if not self.config['enable_stats']:
            return
        logger = configuration.logger
        logger.info("Starting LogStats thread: #%s" % self.ident)
        sleeptime = 1
        elapsed = 0
        while not self.shutdown.is_set():
            time.sleep(sleeptime)
            elapsed += sleeptime
            if self.interval <= elapsed:
                self._log_stats()
                elapsed = 0

    def stop(self):
        """Stop LogStats thread"""
        if not self.config['enable_stats']:
            return
        logger = configuration.logger
        logger.info("Stopping LogStats Thread: #%s" % self.ident)
        self.shutdown.set()
        self._log_stats(force=True)
        self.join()
        # logger.debug("LogStats Thread: #%s" % self.ident)


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
        "verbose": 0,
        "enable_loggers": [],
        "debug_methods": [],
        "propsmanager": True,      # True: use property_manager.PropertyManager
        "locksmanager": True,      # True: use lock_manager.LockManager
        # Allow last modified timestamp updates from client to support rsync -a
        "mutable_live_props": ["{DAV:}getlastmodified"],
        "domaincontroller": MiGWsgiDAVDomainController(daemon_conf['root_dir'], user_map),
        "middleware_stack": [WsgiDavDirBrowser, MiGHTTPAuthenticator, ErrorPrinter, WsgiDavDebugFilter],
        "enable_stats": False
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
    server.stats['Enabled'] = config['enable_stats']

    logger.info('Listening on %(host)s (%(port)s)' % config)

    sessionexpiretracker = SessionExpire()
    logstats = LogStats(config, server, interval=60,
                        idle_only=False, change_only=True)

    try:
        sessionexpiretracker.start()
        logstats.start()
        server.start()
    except KeyboardInterrupt:
        server.stop()
        sessionexpiretracker.stop()
        logstats.stop()
        # forward KeyboardInterrupt to main thread
        raise
    except Exception:
        sessionexpiretracker.stop()
        logstats.stop()
        # forward error to main thread
        raise


if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = configuration.loglevel = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("webdavs",
                           level=log_level,
                           path=configuration.user_davs_log)
    configuration.logger = logger
    if configuration.site_enable_gdp:
        gdp_logger = daemon_gdp_logger("webdavs-gdp",
                                       level=log_level)
        configuration.gdp_logger = gdp_logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

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
        # TODO: Add the following to configuration:
        # max_davs_user_hits
        # max_davs_user_abuse_hits
        # max_davs_proto_abuse_hits
        # max_davs_secret_hits
        'auth_limits':
            {'max_user_hits': default_max_user_hits,
             'user_abuse_hits': default_user_abuse_hits,
             'proto_abuse_hits': default_proto_abuse_hits,
             'max_secret_hits': default_max_secret_hits,
             },
    }
    daemon_conf = configuration.daemon_conf
    daemon_conf['acceptbasic'] = daemon_conf['allow_password']
    daemon_conf['acceptdigest'] = daemon_conf['allow_digest']
    # Keep order of auth methods (please note the 2GB+ upload bug with digest)
    daemon_conf['defaultdigest'] = 'digest' in configuration.user_davs_auth[:1]
    print "daemon_conf['defaultdigest']: %s" % daemon_conf['defaultdigest']
    if configuration.site_enable_gdp:
        # Close projects marked as open due to NON-clean exits
        project_close(configuration, 'davs',
                      address, user_id=None)
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
