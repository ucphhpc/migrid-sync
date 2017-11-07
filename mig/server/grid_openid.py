#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_openid - openid server authenticating users against user database
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

#
# This code is a heavily modified version of the server example from the
# python-openid package
# https://pypi.python.org/pypi/python-openid/
#
# = Original copyright notice follows =

# Python OpenID - OpenID consumer and server library

# Copyright (C) 2005-2008 Janrain, Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.

# = End of original copyright notice =

"""OpenID server to let users authenticate with username and password from
our local user DB.

Requires OpenID module (https://github.com/openid/python-openid).
"""

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urlparse import urlparse

import Cookie
import cgi
import cgitb
import os
import ssl
import signal
import sys
import time

try:
    import openid
except ImportError:
    print "ERROR: the python openid module is required for this daemon"
    sys.exit(1)

from openid.extensions import sreg
from openid.server import server
from openid.store.filestore import FileOpenIDStore
from openid.consumer import discover

from shared.base import client_id_dir, cert_field_map
from shared.conf import get_configuration_object
from shared.defaults import user_db_filename
from shared.griddaemons import refresh_user_creds, update_login_map, \
     login_map_lookup, hit_rate_limit, update_rate_limit, expire_rate_limit, \
     penalize_rate_limit
from shared.logger import daemon_logger, reopen_log
from shared.safeinput import valid_distinguished_name, valid_password, \
     valid_path, valid_ascii, valid_job_id, valid_base_url, valid_url, \
     valid_complex_url, InputException
from shared.tlsserver import hardened_ssl_context
from shared.useradm import get_openid_user_dn, check_password_scramble

configuration, logger = None, None

# Update with extra fields
cert_field_map.update({'role': 'ROLE', 'timezone': 'TZ', 'nickname': 'NICK',
                       'fullname': 'CN', 'o': 'O', 'ou': 'OU'})
cert_field_names = cert_field_map.keys()
cert_field_values = cert_field_map.values()
cert_field_aliases = {}

def hangup_handler(signal, frame):
    """A simple signal handler to force log reopening on SIGHUP"""
    logger.info("reopening log in reaction to hangup signal")
    reopen_log(configuration)
    logger.info("reopened log after hangup signal")
    
def quoteattr(val):
    """Escape string for safe printing"""
    esc = cgi.escape(val, 1)
    return '"%s"' % (esc,)

def valid_mode_name(arg):
    """Make sure only valid mode names are allowed"""
    valid_job_id(arg)

def valid_cert_dir(arg):
    """Make sure only valid cert dir names are allowed"""
    valid_distinguished_name(arg, extra_chars='+_')

def valid_cert_fields(arg):
    """Make sure only valid cert field names are allowed"""
    valid_job_id(arg, extra_chars=',')
    if [i for i in arg.split(',') if not i in cert_field_names]:
        invalid_argument(arg)

def valid_identity_url(arg):
    """Make sure only valid url followed by cert dir names are allowed"""
    valid_distinguished_name(arg, extra_chars=':+_')

def valid_session_hash(arg):
    """Make sure only valid session hashes are allowed"""
    valid_password(arg, extra_chars='=', max_length=512)

def invalid_argument(arg):
    """Always raise exception to mark argument invalid"""
    raise ValueError("Unexpected query variable: %s" % quoteattr(arg))

def lookup_full_user(username):
    """Look up the full user identity for username consisting of e.g. just an
    email address.
    The method to extract the full identity depends on the back end database.
    If username matches either the openid link, the full ID or the dir version
    from it, a tuple with the expanded username and the full user dictionary
    is returned.
    On no match a tuple with the unchanged username and an empty dictionary
    is returned.
    """
    # print "DEBUG: lookup full user for %s" % username
    
    login_url = os.path.join(configuration.user_mig_oid_provider, username)
    distinguished_name = get_openid_user_dn(configuration, login_url)

    # print "DEBUG: compare against %s" % full_id
    entries = login_map_lookup(configuration.daemon_conf, username)
    for entry in entries:
        if entry and entry.user_dict:
            url_friendly = client_id_dir(distinguished_name)
            return (url_friendly, entry.user_dict)
    return (username, {})

def lookup_full_identity(username):
    """Look up the full identity for username consisting of e.g. just an email
    address.
    The method to extract the full identity depends on the back end database
    and the format of the ID can be overriden here as well.
    If username matches either the full ID or the configured alias field from
    it, the full ID is returned on a URL-friendly form. On no match the
    original username is returned in unchanged form.
    """
    # print "DEBUG: lookup full ID for %s" % username
    
    return lookup_full_user(username)[0]


class OpenIDHTTPServer(HTTPServer):
    """
    http(s) server that contains a reference to an OpenID Server and
    knows its base URL.
    Extended to fork on requests to avoid one slow or broken login stalling
    the rest.
    """

    min_expire_delay = 120
    last_expire = time.time()
    # NOTE: We do not enable scramble_cache here since it is hardly any gain
    #       and it potentially introduces a race
    scramble_cache = None

    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)

        fqdn = self.server_name
        port = self.server_port
        # Masquerading if needed
        if configuration.daemon_conf['show_address']:
            fqdn = configuration.daemon_conf['show_address']
        if configuration.daemon_conf['show_port']:
            port = configuration.daemon_conf['show_port']
        if configuration.daemon_conf['nossl']:
            proto = 'http'
            proto_port = 80
        else:
            proto = 'https'
            proto_port = 443
        if port != proto_port:
            self.base_url = '%s://%s:%s/' % (proto, fqdn, port)
        else:
            self.base_url = '%s://%s/' % (proto, fqdn)

        # We serve from sub dir to ease targeted proxying
        self.server_base = 'openid'
        self.base_url += "%s/" % self.server_base

        self.openid = None
        self.approved = {}
        self.lastCheckIDRequest = {}

        # Add our own SReg fields to list of valid fields from sreg 1.1 spec
        for (key, val) in cert_field_map.items():
            if not key in sreg.data_fields:
                sreg.data_fields[key] = key.replace('_', ' ').title()
        # print "DEBUG: sreg fields: %s" % sreg.data_fields
        for name in cert_field_names:
            cert_field_aliases[name] = []
            for target in [i for i in cert_field_names if name != i]:
                if cert_field_map[name] == cert_field_map[target]:
                    cert_field_aliases[name].append(target) 
        # print "DEBUG: cert field aliases: %s" % cert_field_aliases

    def expire_volatile(self):
        """Expire old entries in the volatile helper dictionaries"""
        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            expire_rate_limit(configuration, "openid")
            if self.scramble_cache:
                self.scramble_cache.clear()
            logger.debug("Expired old rate limits and scramble cache")
            
    def setOpenIDServer(self, oidserver):
        """Override openid attribute"""
        self.openid = oidserver


class ThreadedOpenIDHTTPServer(ThreadingMixIn, OpenIDHTTPServer):
    """Multi-threaded version of the OpenIDHTTPServer"""
    pass


class ServerHandler(BaseHTTPRequestHandler):
    """Override BaseHTTPRequestHandler to handle OpenID protocol"""

    # Input validation helper which must hold validators for all valid query
    # string variables. Any other variables must trigger a client error.

    validators = {
        'username': valid_cert_dir,
        'login_as': valid_cert_dir,
        'identifier': valid_cert_dir,
        'user': valid_cert_dir,
        'password': valid_password,
        'yes': valid_ascii,
        'no': valid_ascii,
        'err': valid_ascii,
        'remember': valid_ascii,
        'cancel': valid_ascii,
        'submit': valid_distinguished_name,
        'logout': valid_ascii,
        'success_to': valid_url,
        'fail_to': valid_url,
        'return_to': valid_complex_url,
        'openid.assoc_handle': valid_password,
        'openid.assoc_type': valid_password,
        'openid.dh_consumer_public': valid_session_hash,
        'openid.dh_gen': valid_password,
        'openid.dh_modulus': valid_session_hash,
        'openid.session_type': valid_mode_name,
        'openid.claimed_id': valid_identity_url,
        'openid.identity': valid_identity_url,
        'openid.mode': valid_mode_name,
        'openid.ns': valid_base_url,
        'openid.realm': valid_base_url,
        'openid.success_to': valid_url,
        'openid.return_to': valid_complex_url,
        'openid.trust_root': valid_base_url,
        'openid.ns.sreg': valid_base_url,
        'openid.sreg.required': valid_cert_fields,
        'openid.sreg.optional': valid_ascii,
        'openid.sreg.policy_url': valid_base_url,
        }
    
    def __init__(self, *args, **kwargs):
        if configuration.daemon_conf['session_ttl'] > 0:
            self.session_ttl = configuration.daemon_conf['session_ttl']
        else:
            self.session_ttl = 48 * 3600

        self.clearUser()
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def clearUser(self):
        """Reset all saved user variables"""
        self.user = None
        self.user_dn = None
        self.user_dn_dir = None
        self.password = None
        self.login_expire = None

    def do_GET(self):
        """Handle all HTTP GET requests"""
        # Make sure key is always available for exception handler
        key = 'UNSET'
        try:
            self.parsed_uri = urlparse(self.path)
            self.query = {}
            for (key, val) in cgi.parse_qsl(self.parsed_uri[4]):
                # print "DEBUG: checking input arg %s: '%s'" % (key, val)
                validate_helper = self.validators.get(key, invalid_argument)
                # Let validation errors pass to general exception handler below
                validate_helper(val)
                self.query[key] = val
 
            self.setUser()

            # print "DEBUG: checking path '%s'" % self.parsed_uri[2]
            valid_path(self.parsed_uri[2])
            path = self.parsed_uri[2]

            # Strip server_base before testing location
            path = path.replace("%s/" % self.server.server_base, '', 1)

            if path == '/':
                self.showMainPage()
            elif path.startswith('/ping'):
                self.showPingPage()
            elif path == '/openidserver':
                self.serverEndPoint(self.query)

            elif path == '/login':
                self.showLoginPage('/%s/' % self.server.server_base,
                                   '/%s/' % self.server.server_base,
                                   query=self.query)
            elif path == '/loginsubmit':
                self.doLogin()
            elif path == '/logout':
                self.doLogout()
            elif path.startswith('/id/'):
                self.showIdPage(path)
            elif path.startswith('/yadis/'):
                self.showYadis(path[7:])
            elif path == '/serveryadis':
                self.showServerYadis()
            else:
                self.send_response(404)
                self.end_headers()

        except (KeyboardInterrupt, SystemExit):
            raise
        except InputException, err:
            logger.error("Input error:\n%s" % cgitb.text(sys.exc_info(),
                                                         context=10))
            print "ERROR:\n%s" % cgitb.text(sys.exc_info(), context=10)
            err_msg = """<p class='leftpad'>
Invalid '%s' input: %s
</p>
<p>
<a href='javascript:history.back(-1);'>Back</a>
</p>""" % (key, err)
            self.showErrorPage(err_msg)
        except Exception, err:
            # Do not disclose internal details in production
            logger.error("Internal error:\n%s" % cgitb.text(sys.exc_info(),
                                                            context=10))
            print "ERROR:\n%s" % cgitb.text(sys.exc_info(), context=10)
            err_msg = """<p class='leftpad'>
Internal error while handling your request - please contact the system owners
if this persistently happens.
</p>
<p>
<a href='javascript:history.back(-1);'>Back</a>
</p>"""
            self.showErrorPage(err_msg, error_code=500)

    def do_POST(self):
        """Handle all HTTP POST requests"""
        try:
            self.parsed_uri = urlparse(self.path)

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            self.query = {}
            for (key, val) in cgi.parse_qsl(post_data):
                # print "DEBUG: checking post input arg %s: '%s'" % (key, val)
                validate_helper = self.validators.get(key, invalid_argument)
                # Let validation errors pass to general exception handler below
                validate_helper(val)
                self.query[key] = val

            self.setUser()

            # print "DEBUG: checking path '%s'" % self.parsed_uri[2]
            valid_path(self.parsed_uri[2])
            path = self.parsed_uri[2]

            # Strip server_base before testing location
            path = path.replace("%s/" % self.server.server_base, '', 1)

            if path == '/openidserver':
                self.serverEndPoint(self.query)
            elif path == '/allow':
                self.handleAllow(self.query)
            elif path == '/loginsubmit':
                self.doLogin()
            elif path == '/logout':
                self.doLogout()
            else:
                self.send_response(404)
                self.end_headers()

        except (KeyboardInterrupt, SystemExit):
            raise
        except InputException, err:
            logger.error(cgitb.text(sys.exc_info(), context=10))
            print "ERROR: %s" % cgitb.text(sys.exc_info(), context=10)
            err_msg = """<p class='leftpad'>
Invalid '%s' input: %s
</p>
<p>
<a href='javascript:history.back(-1);'>Back</a>
</p>""" % (key, err)
            self.showErrorPage(err_msg)
        except:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(cgitb.html(sys.exc_info(), context=10))
            logger.error(cgitb.text(sys.exc_info(), context=10))
            print "ERROR: %s" % cgitb.text(sys.exc_info(), context=10)

    def handleAllow(self, query):
        """Handle requests to allow authentication:
        Must verify user is already logged in or validate username/password
        pair against user DB.
        """
        request = self.server.lastCheckIDRequest.get(self.user)
        # NOTE: last request may be None here e.g. on back after illegal char!
        if not request:
            request = self.server.openid.decodeRequest(query)

        logger.debug("handleAllow with last request %s from user %s" % \
                     (request, self.user))
        # print "DEBUG: full query %s" % query

        # Old IE 8 does not send contents of submit buttons thus only the
        # fields login_as and password are set with the allow requests. We
        # manually add a yes here if so to avoid the else case.
        if not 'yes' in query and not 'no' in query:
            query['yes'] = 'yes'
        
        if 'yes' in query:
            if 'login_as' in query:
                self.user = self.query['login_as']
                #print "handleAllow set user %s" % self.user
            elif 'identifier' in query:
                self.user = self.query['identifier']

            if request.idSelect():
                # Do any ID expansion to a specified format
                if configuration.daemon_conf['expandusername']:
                    user_id = lookup_full_identity(query.get('identifier', ''))
                else:
                    user_id = query.get('identifier', '')
                identity = self.server.base_url + 'id/' + user_id
            else:
                identity = request.identity

            logger.debug("handleAllow with identity %s" % identity)

            if 'password' in self.query:
                logger.debug("setting password")
                self.password = self.query['password']
            else:
                logger.debug("no password in query")
                self.password = None

            if not hit_rate_limit(configuration, "openid",
                                  self.client_address[0], self.user) and \
                                  self.checkLogin(self.user, self.password):
                logger.debug("handleAllow validated login %s" % identity)
                trust_root = request.trust_root
                if self.query.get('remember', 'no') == 'yes':
                    self.server.approved[(identity, trust_root)] = 'always'
                
                self.login_expire = int(time.time() + self.session_ttl)
                logger.info("handleAllow approving login %s" % identity)
                response = self.approved(request, identity)
                update_rate_limit(configuration, "openid",
                                  self.client_address[0], self.user, True,
                                  self.password)
            else:
                logger.warning("handleAllow rejected login %s" % identity)
                #logger.debug("full query: %s" % self.query)
                #logger.debug("full headers: %s" % self.headers)
                fail_user, fail_pw = self.user, self.password
                self.clearUser()
                failed_count = update_rate_limit(configuration, "openid",
                                                 self.client_address[0],
                                                 fail_user, False,
                                                 fail_pw)
                penalize_rate_limit(configuration, "openid",
                                    self.client_address[0], fail_user,
                                    failed_count)
                # Login failed - return to refering page to let user try again
                retry_url = self.headers.get('Referer')
                # Add error message to display 
                if retry_url.find('?') == -1:
                    retry_url += '?'
                else:
                    retry_url += '&'
                retry_url += 'err=loginfail' 
                self.redirect(retry_url)
                return
        elif 'no' in query:
            response = request.answer(False)
        else:
            assert False, 'strange allow post.  %r' % (query,)

        self.displayResponse(response)


    def setUser(self):
        """Read any saved user value from cookie"""
        cookies = self.headers.get('Cookie')
        # print "found cookies: %s" % cookies
        if cookies:
            morsel = Cookie.BaseCookie(cookies).get('user')
            # Added morsel value check here since IE sends empty string from
            # cookie after initial user=;expire is sent. Others leave it out.
            if morsel and morsel.value != '':
                self.user = morsel.value

            expire = int(time.time() + self.session_ttl)
            morsel = Cookie.BaseCookie(cookies).get('session_expire')
            if morsel and morsel.value != '':
                # print "found user session_expire value: %s" % morsel.value
                if morsel.value.isdigit() and int(morsel.value) <= expire:
                    # print "using saved session expire: %s" % morsel.value
                    expire = int(morsel.value)
                else:
                    logger.warning("invalid session_expire %s" % morsel.value)
            self.login_expire = expire

    def isAuthorized(self, identity_url, trust_root):
        """Check if user is authorized"""
        if self.user is None:
            return False

        if identity_url != self.server.base_url + 'id/' + self.user:
            return False

        key = (identity_url, trust_root)
        return self.server.approved.get(key) is not None

    def serverEndPoint(self, query):
        """End-point handler"""
        try:
            request = self.server.openid.decodeRequest(query)
            # Pass any errors from previous login attempts on for display
            request.error = query.get('err', '')
        except server.ProtocolError, why:
            self.displayResponse(why)
            return

        if request is None:
            # Display text indicating that this is an endpoint.
            self.showAboutPage()
            return

        if request.mode in ["checkid_immediate", "checkid_setup"]:
            self.handleCheckIDRequest(request)
        else:
            response = self.server.openid.handleRequest(request)
            self.displayResponse(response)

    def addSRegResponse(self, request, response):
        """SReg extended attributes handler"""
        if not self.user:
            return 
        sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)

        (username, user) = lookup_full_user(self.user)

        if not user:
            logger.warning("addSRegResponse user lookup failed!")
            return
        
        sreg_data = {}
        for field in cert_field_names:
            # Skip fields already set by alias
            if sreg_data.has_key(field):
                continue
            # Backends choke on empty fields 
            found = user.get(field, None)
            if found:
                val = found
            else:
                val = 'NA'
            # Add both the field and any alias values for now if found
            sreg_data[field] = val
            if found:
                for alias in cert_field_aliases[field]:
                    sreg_data[alias] = val
        # print "DEBUG: addSRegResponse added data:\n%s\n%s\n%s" % \
        #      (sreg_data, sreg_req.required, request)
        sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
        # print "DEBUG: addSRegResponse send response:\n%s" % sreg_resp.data
        response.addExtension(sreg_resp)

    def approved(self, request, identifier=None):
        """Accept helper"""
        response = request.answer(True, identity=identifier)
        self.addSRegResponse(request, response)
        return response

    def rejected(self, request, identifier=None):
        """Reject helper"""
        response = request.answer(False, identity=identifier)
        return response

    def handleCheckIDRequest(self, request):
        """Check ID handler"""
        logger.debug("handleCheckIDRequest with req %s" % request)
        is_authorized = self.isAuthorized(request.identity, request.trust_root)
        if is_authorized:
            response = self.approved(request)
            self.displayResponse(response)
        elif request.immediate:
            response = request.answer(False)
            self.displayResponse(response)
        else:
            # print "DEBUG: adding user request to last dict: %s : %s" % (self.user, request)
            self.server.lastCheckIDRequest[self.user] = request
            self.showDecidePage(request)

    def displayResponse(self, response):
        """Response helper"""
        try:
            webresponse = self.server.openid.encodeResponse(response)
        except server.EncodingError, why:
            text = why.response.encodeToKVForm()
            self.showErrorPage('<pre>%s</pre>' % cgi.escape(text))
            return

        self.send_response(webresponse.code)
        for header, value in webresponse.headers.iteritems():
            self.send_header(header, value)
        self.writeUserHeader()
        self.end_headers()

        if webresponse.body:
            self.wfile.write(webresponse.body)

    def checkLogin(self, username, password):
        """Check username and password stored in MiG user DB""" 

        # Only need to update users here
        daemon_conf, changed_users = refresh_user_creds(configuration,
                                                        'openid',
                                                        username)
        update_login_map(daemon_conf, changed_users, [], [])

        # username may be None here
        login_url = os.path.join(configuration.user_mig_oid_provider,
                                 username or '')
        distinguished_name = get_openid_user_dn(configuration, login_url)
        entries = login_map_lookup(daemon_conf, username)
        for entry in entries:
            allowed = entry.password
            if allowed is None or not password:
                continue            
            # print "DEBUG: Check password against allowed %s" % allowed
            # NOTE: We refuse weak legacy passwords here
            if check_password_scramble(configuration, 'openid', username,
                                       password, allowed,
                                       configuration.site_password_salt,
                                       self.server.scramble_cache):
                logger.info("Correct password for user %s" % username)
                self.user_dn = distinguished_name
                self.user_dn_dir = client_id_dir(distinguished_name)
                self.login_expire = int(time.time() + self.session_ttl)
                return True
            else:
                logger.warning("Failed password check for user %s" % username)
        logger.error("Invalid login for user %s" % username)
        return False
                
    def doLogin(self):
        """Login handler"""
        if 'submit' in self.query:
            if 'user' in self.query:
                self.user = self.query['user']
            else:
                self.clearUser()
                self.redirect(self.query['success_to'])
                return
            if 'password' in self.query:
                self.password = self.query['password']
            else:
                self.password = None
            if not hit_rate_limit(configuration, "openid",
                                  self.client_address[0], self.user) and \
                                  self.checkLogin(self.user, self.password):
                if not self.query['success_to']:
                    self.query['success_to'] = '%s/id/' % self.server.base_url
                update_rate_limit(configuration, "openid",
                                  self.client_address[0], self.user, True,
                                  self.password)
                # print "doLogin succeded: redirect to %s" % self.query['success_to']
                self.redirect(self.query['success_to'])
            else:
                logger.warning("login failed for %s" % self.user)
                logger.debug("full query: %s" % self.query)
                fail_user, fail_pw = self.user, self.password
                self.clearUser()
                failed_count = update_rate_limit(configuration, "openid",
                                                 self.client_address[0],
                                                 fail_user, False,
                                                 fail_pw)
                penalize_rate_limit(configuration, "openid",
                                    self.client_address[0], fail_user,
                                    failed_count)
                # Login failed - return to refering page to let user try again
                retry_url = self.headers.get('Referer', self.server.base_url)
                # Add error message to display 
                if retry_url.find('?') == -1:
                    retry_url += '?'
                else:
                    retry_url += '&'
                retry_url += 'err=loginfail' 
                self.redirect(retry_url)
                return
        elif 'cancel' in self.query:
            self.redirect(self.query['fail_to'])
        else:
            assert 0, 'strange login %r' % (self.query,)

    def doLogout(self):
        """Logout handler"""
        logger.debug("logout clearing user %s" % self.user)
        self.clearUser()
        if 'return_to' in self.query:
            # print "logout redirecting to %(return_to)s" % self.query
            self.redirect(self.query['return_to'])

    def redirect(self, url):
        """Redirect helper"""
        self.send_response(302)
        self.send_header('Location', url)
        self.writeUserHeader()

        self.end_headers()

    def writeUserHeader(self):
        """Response helper"""
        # NOTE: we added secure and httponly flags as suggested by OpenVAS

        # NOTE: we need to set empty user cookie for logout to work
        if self.user is None or self.login_expire is None:
            session_expire = 0
        else:
            # print "found login_expire %s" % self.login_expire
            session_expire = self.login_expire
        expire = time.strftime(
            'Expires=%a, %d-%b-%y %H:%M:%S GMT', time.gmtime(session_expire))
        if self.user is None:
            logger.debug("setting empty user and session_expire cookie")
            self.send_header('Set-Cookie', 'user=;secure;httponly')
            self.send_header('Set-Cookie', 'session_expire=;secure;httponly')
        else:
            logger.debug("sending %s user cookie with expire %s" % (self.user,
                                                                    expire))
            self.send_header('Set-Cookie', 'user=%s;%s;secure;httponly' % \
                             (self.user, expire))
            self.send_header('Set-Cookie',
                             'session_expire=%s;%s;secure;httponly' % \
                             (session_expire, expire))
        # Set Content-Security-Policy: frame-ancestors to prevent clickjacking
        # as recommended by W3C and security scans.
        logger.debug("setting CSP: frame-ancestors header")
        self.send_header('Content-Security-Policy', "frame-ancestors 'self'")

    def showAboutPage(self):
        """About page provider"""
        endpoint_url = self.server.base_url + 'openidserver'

        def link(url):
            url_attr = quoteattr(url)
            url_text = cgi.escape(url)
            return '<a href=%s><code>%s</code></a>' % (url_attr, url_text)

        def term(url, text):
            return '<dt>%s</dt><dd>%s</dd>' % (link(url), text)

        resources = [
            (self.server.base_url, "This OpenID server's home page"),
            ('http://www.openidenabled.com/',
             'An OpenID community Web site, home of this library'),
            ('http://www.openid.net/', 'the official OpenID Web site'),
            ]

        resource_markup = ''.join([term(url, text) for url, text in resources])

        self.showPage(200, 'This is an OpenID server', msg="""\
        <p>%s is an OpenID server endpoint.<p>
        <p>For more information about OpenID, see:</p>
        <dl>
        %s
        </dl>
        """ % (link(endpoint_url), resource_markup,))

    def showPingPage(self):
        """Basic server availability test page provider"""

        # TODO: consider simple user lookup test to set status

        ready = True

        def link(url):
            url_attr = quoteattr(url)
            url_text = cgi.escape(url)
            return '<a href=%s><code>%s</code></a>' % (url_attr, url_text)

        # IMPORTANT: This is the format availability checker looks for.
        # Do not change unless you know what you're doing!

        status = "<h1>%s</h1>" % ready

        self.showPage(200, 'Ping', msg='''\
        <h1>Ping</h1>
        <p>This is a server availability page for %s.</p>
        %s
        ''' % (link(self.server.base_url), status,))

    def showErrorPage(self, error_message, error_code=400):
        """Error page provider"""
        self.showPage(error_code, 'Error Processing Request', err='''\
        <p>%s</p>
        <!--

        This is a large comment.  It exists to make this page larger.
        That is unfortunately necessary because of the "smart"
        handling of pages returned with an error code in IE.

        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************
        *************************************************************

        -->
        ''' % error_message)

    def showDecidePage(self, request):
        """Decide page provider"""
        id_url_base = self.server.base_url+'id/'
        # XXX: This may break if there are any synonyms for id_url_base,
        # such as referring to it by IP address or a CNAME.
        assert (request.identity.startswith(id_url_base) or 
                request.idSelect()), repr((request.identity, id_url_base))
        expected_user = request.identity[len(id_url_base):]

        if request.error == 'loginfail':
            err_msg = '<p class="errortext">Authentication failed!</p>'
        elif request.error:
            err_msg = '<p class="errortext">Error: %s</p>' % request.error
        else:
            err_msg = ''

        if request.idSelect(): # We are being asked to select an ID
            user_alias = configuration.user_openid_alias

            msg = '''\
            <h1>%(short_title)s OpenID Login</h1>
            ''' % {'short_title': configuration.short_title}
            if user_alias:
                alias_hint = ' (%s)' % user_alias
            else:
                alias_hint = ''
            fdata = {
                'id_url_base': id_url_base,
                'trust_root': request.trust_root,
                'server_base': self.server.server_base,
                'alias_hint': alias_hint,
                'err_msg': err_msg,
                }
            form = '''\
            <div class="openidlogin">
            <form method="POST" action="/%(server_base)s/allow">
            <fieldset>
            <label for="identifier">Username %(alias_hint)s:</label>
            <input id="id_select" class="singlefield" name="identifier"
                   autofocus />
            <label for="password">Password:</label>
            <input class="singlefield" type="password" name="password"
                   />
            <label for="remember">Remember Trust:</label><br />
            <input class="" type="checkbox" id="remember"
                   name="remember" value="yes" checked="checked" /><br />
            <label for="yes">Proceed:</label>
            <input class="" type="submit" name="yes" value="yes" />
            <input class="" type="submit" name="no" value="no" />
            </fieldset>
            </form>
            </div>
            <div class="openidlogin">
            <p>The site %(trust_root)s has requested verification of your
            OpenID.
            </p>
            %(err_msg)s
            </div>
            '''
            form = form % fdata
        elif expected_user == self.user:
            msg = '''\
            <p>A new site has asked to confirm your identity.  If you
            approve, the site represented by the trust root below will
            be told that you control identity URL listed below. (If
            you are using a delegated identity, the site will take
            care of reversing the delegation on its own.)</p>'''

            fdata = {
                'identity': request.identity,
                'trust_root': request.trust_root,
                'server_base': self.server.server_base,
                'err_msg': err_msg,
                }
            form = '''\
            <table>
              <tr><td>Identity:</td><td>%(identity)s</td></tr>
              <tr><td>Trust Root:</td><td>%(trust_root)s</td></tr>
            </table>
            <p>Allow this authentication to proceed?</p>
            <form method="POST" action="/%(server_base)s/allow">
              <input type="checkbox" id="remember" name="remember" value="yes"
                  /><label for="remember">Remember this
                  decision</label><br />
              Password: <input type="password" name="password" autofocus /><br />
              <input type="submit" name="yes" value="yes" />
              <input type="submit" name="no" value="no" />
            </form>
            <div class="openidlogin">
            %(err_msg)s
            </div>
            ''' % fdata
        else:
            mdata = {
                'expected_user': expected_user,
                'user': self.user,
                'err_msg': err_msg,
                }
            msg = '''\
            <p>A site has asked for an identity belonging to
            %(expected_user)s, but you are logged in as %(user)s.  To
            log in as %(expected_user)s and approve the login request,
            hit OK below.  The "Remember this decision" checkbox
            applies only to the trust root decision.</p>''' % mdata

            fdata = {
                'identity': request.identity,
                'trust_root': request.trust_root,
                'expected_user': expected_user,
                'server_base': self.server.server_base,
                }
            form = '''\
            <table>
              <tr><td>Identity:</td><td>%(identity)s</td></tr>
              <tr><td>Trust Root:</td><td>%(trust_root)s</td></tr>
            </table>
            <p>Allow this authentication to proceed?</p>
            <form method="POST" action="/%(server_base)s/allow">
              <input type="checkbox" id="remember" name="remember" value="yes"
                  /><label for="remember">Remember this
                  decision</label><br />
              <input type="hidden" name="login_as" value="%(expected_user)s"
                  autofocus />
              Password: <input type="password" name="password"><br />
              <input type="submit" name="yes" value="yes" />
              <input type="submit" name="no" value="no" />
            </form>
            <div class="openidlogin">
            %(err_msg)s
            </div>
            ''' % fdata

        self.showPage(200, 'Approve OpenID request?', msg=msg, form=form)

    def showIdPage(self, path):
        """User info page provider"""
        link_tag = '<link rel="openid.server" href="%sopenidserver">' % \
              self.server.base_url
        yadis_loc_tag = '<meta http-equiv="x-xrds-location" content="%s"/>' % \
            (self.server.base_url+'yadis/'+path[4:])
        disco_tags = link_tag + yadis_loc_tag
        ident = self.server.base_url + path[1:]

        approved_trust_roots = []
        # Don't disclose information about other active login sessions
        ident_user = path.split('/')[-1]
        if self.user == ident_user:
            for (aident, trust_root) in self.server.approved.keys():
                if aident == ident:
                    trs = '<li><span class="verbatim">%s</span></li>\n' % \
                          cgi.escape(trust_root)
                    approved_trust_roots.append(trs)
        else:
            logger.debug("Not disclosing trust roots for %s (active user %s)" \
                         % (ident_user, self.user))

        if approved_trust_roots:
            prepend = '<p>Approved trust roots:</p>\n<ul>\n'
            approved_trust_roots.insert(0, prepend)
            approved_trust_roots.append('</ul>\n')
            msg = ''.join(approved_trust_roots)
        else:
            msg = ''

        self.showPage(200, 'An Identity Page', head_extras=disco_tags, msg='''\
        <p>This is a very basic identity page for %s.</p>
        %s
        ''' % (ident, msg))
        

    def showYadis(self, user):
        """YADIS page provider"""
        self.send_response(200)
        self.send_header('Content-type', 'application/xrds+xml')
        self.end_headers()

        endpoint_url = self.server.base_url + 'openidserver'
        user_url = self.server.base_url + 'id/' + user
        self.wfile.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS
    xmlns:xrds="xri://$xrds"
    xmlns="xri://$xrd*($v*2.0)">
  <XRD>

    <Service priority="0">
      <Type>%s</Type>
      <Type>%s</Type>
      <URI>%s</URI>
      <LocalID>%s</LocalID>
    </Service>

  </XRD>
</xrds:XRDS>
"""%(discover.OPENID_2_0_TYPE, discover.OPENID_1_0_TYPE,
     endpoint_url, user_url))

    def showServerYadis(self):
        """Server YADIS page provider"""
        self.send_response(200)
        self.send_header('Content-type', 'application/xrds+xml')
        self.end_headers()

        endpoint_url = self.server.base_url + 'openidserver'
        self.wfile.write("""\
<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS
    xmlns:xrds="xri://$xrds"
    xmlns="xri://$xrd*($v*2.0)">
  <XRD>

    <Service priority="0">
      <Type>%s</Type>
      <URI>%s</URI>
    </Service>

  </XRD>
</xrds:XRDS>
"""%(discover.OPENID_IDP_2_0_TYPE, endpoint_url,))

    def showMainPage(self):
        """Main page provider"""
        yadis_tag = '<meta http-equiv="x-xrds-location" content="%s"/>' % \
            (self.server.base_url + 'serveryadis')
        if self.user:
            openid_url = self.server.base_url + 'id/' + self.user
            user_message = """\
            <p>You are logged in as %s. Your OpenID identity URL is
            <span class='verbatim'><a href=%s>%s</a></span>.
            Enter that URL at an OpenID consumer to test this server.</p>
            """ % (self.user, quoteattr(openid_url), openid_url)
        else:
            user_message = """\
            <p>This server uses a cookie to remember who you are in
            order to simulate a standard Web user experience. You are
            not <a href='/%s/login'>logged in</a>.</p>""" % \
            self.server.server_base

        self.showPage(200, 'Main Page', head_extras = yadis_tag, msg=''' \
        <p>This is a simple OpenID server implemented using the <a
        href="http://openid.schtuff.com/">Python OpenID
        library</a>.</p>

        %s

        <p>To use this server with a consumer, the consumer must be
        able to fetch HTTP pages from this web server. If this
        computer is behind a firewall, you will not be able to use
        OpenID consumers outside of the firewall with it.</p>

        <p>The URL for this server is
        <a href=%s><span class="verbatim">%s</span></a>.</p>
        ''' % (user_message, quoteattr(self.server.base_url), self.server.base_url))

    def showLoginPage(self, success_to, fail_to, query):
        """Login page provider"""
        if query.get('err', '') == 'loginfail':
            err_msg = '<p class="errortext">Authentication failed!</p>'
        elif query.get('err', ''):
            err_msg = '<p class="errortext">Error: %(err)s</p>' % query
        else:
            err_msg = ''
        self.showPage(200, 'Login Page', form='''\
        <h2>OpenID Login</h2>
        <p>Please enter your %s username and password to prove your identify
        to this OpenID service.</p>
        <form method="GET" action="/%s/loginsubmit">
          <input type="hidden" name="success_to" value="%s" />
          <input type="hidden" name="fail_to" value="%s" />
          Username: <input type="text" name="user" value="" autofocus /><br />
          Password: <input type="password" name="password"><br />
          <input type="submit" name="submit" value="Log In" />
          <input type="submit" name="cancel" value="Cancel" />
        </form>
        <div class="openiderror">
        %s
        </div>
        ''' % (configuration.short_title, self.server.server_base,
               success_to, fail_to, err_msg))

    def showPage(self, response_code, title,
                 head_extras='', msg=None, err=None, form=None):
        """Show page helper"""
        if self.user is None:
            user_link = '<a href="/%s/login">not logged in</a>.' % \
                        self.server.server_base
        else:
            user_link = '''logged in as <a href="/%s/id/%s">%s</a>.<br />
<a href="/%s/logout?return_to=/%s/login">Log out</a>''' % \
         (self.server.server_base, self.user, self.user,
          self.server.server_base, self.server.server_base)

        body = ''

        if err is not None:
            body +=  '''\
            <div class="error">
              %s
            </div>
            ''' % err

        if msg is not None:
            body += '''\
            <div class="message">
              %s
            </div>
            ''' % msg

        if form is not None:
            body += '''\
            <div class="form">
              %s
            </div>
            ''' % form

        default_css = os.path.join(configuration.migserver_https_sid_url,
                                   configuration.site_default_css.lstrip('/'))
        static_css = os.path.join(configuration.migserver_https_sid_url,
                                  configuration.site_static_css.lstrip('/'))
        custom_css = os.path.join(configuration.migserver_https_sid_url,
                                  configuration.site_custom_css.lstrip('/'))
        skin_base = os.path.join(configuration.migserver_https_sid_url,
                                 configuration.site_skin_base.lstrip('/'))
        fav_icon = os.path.join(configuration.migserver_https_sid_url,
                                configuration.site_fav_icon.lstrip('/'))
        site_logo_left = os.path.join(configuration.migserver_https_sid_url,
                                      configuration.site_logo_left.lstrip('/'))
        site_logo_right = os.path.join(configuration.migserver_https_sid_url,
                                       configuration.site_logo_right.lstrip('/'))
        creds_logo = os.path.join(configuration.migserver_https_sid_url,
                                  configuration.site_credits_image.lstrip('/'))
        contents = {
            'title': configuration.short_title + ' OpenID Server - ' + title,
            'short_title': configuration.short_title,
            'head_extras': head_extras,
            'body': body,
            'user_link': user_link,
            'root_url': '/%s/' % self.server.server_base,
            'site_default_css': default_css,
            'site_static_css': static_css,
            'site_custom_css': custom_css,
            'site_skin_base': skin_base,
            'site_fav_icon': fav_icon,
            'site_logo_left': site_logo_left,
            'site_logo_right': site_logo_right,
            'credits_logo': creds_logo,
            'credits_text': configuration.site_credits_text,
            }

        self.send_response(response_code)
        self.writeUserHeader()
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write('''<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8"/>
    <title>%(title)s</title>
    %(head_extras)s

<!-- site default style -->
<link rel="stylesheet" type="text/css" href="%(site_default_css)s" media="screen"/>

<!-- site basic skin style -->
<link rel="stylesheet" type="text/css" href="%(site_static_css)s" media="screen"/>

<!-- override with any site-specific styles -->
<link rel="stylesheet" type="text/css" href="%(site_custom_css)s" media="screen"/>

<!-- site skin style -->
<link rel="stylesheet" type="text/css" href="%(site_skin_base)s/ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%(site_skin_base)s/ui-theme.custom.css" media="screen"/>

<link rel="icon" type="image/vnd.microsoft.icon" href="%(site_fav_icon)s"/>
  </head>
  <body class="staticpage openid">
<div id="topspace">
</div>
<div id="toplogo" class="staticpage">
<div id="toplogoleft" class="staticpage">
<a href="%(root_url)s"><img src="%(site_logo_left)s" id="logoimageleft"
    alt="site logo left"/>
</a>
</div>
<div id="toplogocenter" class="staticpage">
<img src="%(site_skin_base)s/banner-logo.jpg" id="logoimagecenter"
     class="staticpage" alt="site logo center"/>
<span id="logotitle" class="staticpage">
%(short_title)s OpenID Server
</span>
</div>
<div id="toplogoright" class="staticpage">
<img src="%(site_logo_right)s" id="logoimageright" alt="site logo right"/>
</div>
</div>

<div class="contentblock staticpage" id="nomenu">
<div class="precontentwidgets">
<!-- begin user supplied pre content widgets -->
<!-- empty -->
<!-- end user supplied pre content widgets -->
</div>
<div id="migheader">

</div>
    <div id="content" class="staticpage">
    <div class="banner staticpage">
      <div class="container righttext staticpage">
          You are %(user_link)s
      </div>
    </div>
%(body)s
  </div>
</div>
<div id="bottomlogo">
<img src="%(credits_logo)s" id="creditsimage" alt=""/>
<span id="credits">
%(credits_text)s
</span>
</div>
<div id="bottomspace">
</div>
</body>
</html>
''' % contents)


def start_service(configuration):
    """Service launcher"""
    host = configuration.user_openid_address
    port = configuration.user_openid_port
    data_path = configuration.openid_store
    daemon_conf = configuration.daemon_conf
    nossl = daemon_conf['nossl']
    addr = (host, port)
    # TODO: is this threaded version robust enough (thread safety)?
    #OpenIDServer = OpenIDHTTPServer
    OpenIDServer = ThreadedOpenIDHTTPServer
    httpserver = OpenIDServer(addr, ServerHandler)

    # Instantiate OpenID consumer store and OpenID consumer.  If you
    # were connecting to a database, you would create the database
    # connection and instantiate an appropriate store here.
    store = FileOpenIDStore(data_path)
    oidserver = server.Server(store, httpserver.base_url + 'openidserver')

    httpserver.setOpenIDServer(oidserver)

    # Wrap in SSL if enabled
    if nossl:
        logger.warning('Not wrapping connections in SSL - only for testing!')
    else:
        # Use best possible SSL/TLS args for this python version
        key_path = cert_path = configuration.user_openid_key
        dhparams_path = configuration.user_shared_dhparams
        if not os.path.isfile(cert_path):
            logger.error('No such server key: %s' % cert_path)
            sys.exit(1)
        logger.info('Wrapping connections in SSL')
        ssl_ctx = hardened_ssl_context(configuration, key_path, cert_path,
                                       dhparams_path)
        httpserver.socket = ssl_ctx.wrap_socket(httpserver.socket,
                                                server_side=True)
        
    serve_msg = 'Server running at: %s' % httpserver.base_url
    logger.info(serve_msg)
    print serve_msg
    min_expire_delay = 300
    last_expire = time.time()
    while True:
        httpserver.handle_request()
        if last_expire + min_expire_delay < time.time():
            httpserver.expire_volatile()
            

if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("openid", configuration.user_openid_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    signal.signal(signal.SIGHUP, hangup_handler)

    # For masquerading
    show_address = configuration.user_openid_show_address
    show_port = configuration.user_openid_show_port
    
    # Allow configuration overrides on command line
    nossl = False
    expandusername = False
    if sys.argv[2:]:
        configuration.user_openid_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_openid_port = int(sys.argv[3])
    if sys.argv[4:]:
        nossl = (sys.argv[4].lower() in ('1', 'true', 'yes', 'on'))
    if sys.argv[5:]:
        expandusername = (sys.argv[5].lower() in ('1', 'true', 'yes', 'on'))

    if not configuration.site_enable_openid:
        err_msg = "OpenID service is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)
    print """
Running grid openid server for user authentication against MiG user DB.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    print __doc__
    address = configuration.user_openid_address
    port = configuration.user_openid_port
    session_store = configuration.openid_store
    default_host_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEA404IBMReHOdvhhJ5YtgquY3DNi0v0QwfPUk+EcH/CxFW8UCC
SUJe85up6lEQmOE9yKvrh+3yJgIjdV/ASOw9bd/u0NgNoPwl6A6P8GzHp94vz7UP
nTp+PEUbA8gwqXnzzdeuF3dLDSXuGHdcv8qQEVRBwj/haecO0fgZcfd4fmLDAG53
e/Vwc4lVIp4xx+OQowm9RW3nsAZge1DUoxlStD1/rEzBq1DvVx1Wu8pWS48f2ABH
fHt2Z4ozypMB+a4B56jervcZCNkV/fN2bdGZ8z07hNbn/EkaH2tPw/d62zdHddum
u7Pi0tYwMZz9GN3t18r9qi5ldUJuJNeNvNc7swIBIwKCAQBuZ7rAfKK9lPunhVDm
3gYfnKClSSXakNv5MjQXQPg4k2S+UohsudZZERgEGL7rK5MJspb44Um6sJThPSLh
l1EJe2VeH8wa/iEKUDdI5GD5w7DSmcXBZY3FgKa4sbE8X84wx9g3SJIq9SqA6YTS
LzAIasDasVA6wK9tTJ6lEczPq2VkxkzpKauDMgI6SpaBV+7Un3OM7VJEbWeaJVoZ
9I/2AHfp1hDpIfmaYBCnn2Ky70PBGA8DqAnHUKiid2dfZr8jKLu287LaUHxzIZXz
qSzS6Vg1K0kc5FrgTgrjaXAGNtMenXZdw2/7PMuBDaNuNUApFUlAP5LGvPQ9IRCt
YggDAoGBAP7z3lm74yxrzSa7HRASO2v3vp7jsbaYl4jPCc+6UruBFJlmUUdIQ2fh
8i2S1M5mAvZiJ/PKLQ3r6RXxWZOeh4Vw479HFCVHr5GstSfLolJ5svY8iWEoEGdN
D8aQTQrVAJwAPbLbF4eH5lgSokjOZcWMKsekk4vX2WmCMKWCMms/AoGBAOQ9Fffg
B8TMc1b+jTcj1Py5TiFsxIe3usYjn8Pgg8kpoGfdBoS/TxwoR0MbJdrPgXDKLlLn
A4GG6/7lFmxagCAfUyR2wAsOwAugcaFwS3K4QHGPiv9cgKxt9xhuhhDqXGI2lgAu
oJLcRYBvomPQ+3cGGgifclETTWgkzD5dNVaNAoGBAMStf6RPHPZhyiUxQk4581NK
FrUWDMAPUFOYZqePvCo/AUMjC4AhzZlH5rVxRRRAEOnz8u9EMWKCycB4Wwt6S0mu
25OOmoMorAKpzZO6WKYGHFeNyRBvXRx9Rq8e3FjQM6uLKEglW0tLlG/T3EbLG09A
PkI9IV1AHL8bShlHLjV5AoGBAJyBqKn4tN64FJNsuJrWve8f+w+bCmuxL53PSPtY
H9plr9IxKQqRz9jLKY0Z7hJiZ2NIz07KS4wEvxUvX9VFXyv4OQMPmaEur5LxrQD8
i4HdbgS6M21GvqIfhN2NncJ00aJukr5L29JrKFgSCPP9BDRb9Jgy0gu1duhTv0C0
8V/rAoGAEUheXHIqv9n+3oXLvHadC3aApiz1TcyttDM0AjZoSHpXoBB3AIpPdU8O
0drRG9zJTyU/BC02FvsGAMo0ZpGQRVMuN1Jj7sHsPaUdV38P4G0EaSQJDNxwFKVN
3stfzMDGtKM9lntAsfFQ8n4yvvEbn/quEWad6srf1yxt9B4t5JA=
-----END RSA PRIVATE KEY-----
"""
    try:
        host_key_fd = open(configuration.user_openid_key, 'r')
        host_rsa_key = host_key_fd.read()
        host_key_fd.close()
    except IOError:
        logger.info("No valid host key provided - using default")
        host_rsa_key = default_host_key
    configuration.daemon_conf = {
        'address': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'db_path': os.path.abspath(os.path.join(configuration.mig_server_home,
                                                user_db_filename)),
        'session_store': os.path.abspath(configuration.openid_store),
        'session_ttl': 24*3600,
        'allow_password': 'password' in configuration.user_openid_auth,
        'allow_digest': 'digest' in configuration.user_openid_auth,
        'allow_publickey': 'publickey' in configuration.user_openid_auth,
        'user_alias': configuration.user_openid_alias,
        'host_rsa_key': host_rsa_key,
        'users': [],
        'login_map': {},
        'time_stamp': 0,
        'logger': logger,
        'nossl': nossl,
        'expandusername': expandusername,
        'show_address': show_address,
        'show_port': show_port,
        }
    logger.info("Starting OpenID server")
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print info_msg
    try:
        start_service(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print info_msg
