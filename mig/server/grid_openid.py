#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_openid - openid server authenticating users against user database
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

"""Interface between CGI and functionality"""


from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from urlparse import urlparse

import base64
import Cookie
import cgi
import cgitb
import os
import ssl
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

from shared.base import client_alias, client_id_dir
from shared.conf import get_configuration_object
from shared.safeinput import valid_distinguished_name, valid_password, \
     valid_path, valid_ascii, valid_job_id, valid_base_url, valid_url
from shared.useradm import load_user_db, extract_field

configuration, logger = None, None

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

def valid_identity_url(arg):
    """Make sure only valid url followed by cert dir names are allowed"""
    valid_distinguished_name(arg, extra_chars=':+_')

def valid_session_hash(arg):
    """Make sure only valid session hashes are allowed"""
    valid_password(arg, extra_chars='=', max_length=512)

def invalid_argument(arg):
    """Always raise exception to mark argument invalid"""
    raise ValueError("Unexpected query variable: %s" % quoteattr(arg))

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
    
    db_path = os.path.join(configuration.mig_code_base, 'server', 
                           'MiG-users.db')
    # print "DEBUG: Loading user DB"
    id_map = load_user_db(db_path)
    user_alias = configuration.user_openid_alias

    # Loop through all full IDs in user DB and check if username
    # matches either a full ID or the shorter alias form of the full ID
    for full_id in id_map.keys():
        # print "DEBUG: compare against %s" % full_id
        alias_value = None
        url_friendly = client_id_dir(full_id)
        # Fetch the optional single attribute alias used for username
        if user_alias:
            alias_value = extract_field(full_id, user_alias)
        # print "DEBUG: check %s and %s" % (full_id, alias_value)
        if username in (full_id, url_friendly, alias_value):
            # Translate raw ID on the form
            # /C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk
            # to the URL-friendly form
            # +C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Jonas_Bardino+emailAddress=bardino@nbi.ku.dk
            return url_friendly
    return username


class OpenIDHTTPServer(HTTPServer):
    """
    http(s) server that contains a reference to an OpenID Server and
    knows its base URL.
    Extended to fork on requests to avoid one slow or broken login stalling
    the rest.
    """
    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)

        if configuration.daemon_conf['nossl']:
            proto = 'http'
            proto_port = 80
        else:
            proto = 'https'
            proto_port = 443
        if self.server_port != proto_port:
            self.base_url = ('%s://%s:%s/' %
                             (proto, self.server_name, self.server_port))
        else:
            self.base_url = '%s://%s/' % (proto, self.server_name,)

        # We serve from sub dir to ease targeted proxying
        self.server_base = 'openid'
        self.base_url += "%s/" % self.server_base

        self.openid = None
        self.approved = {}
        self.lastCheckIDRequest = {}

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
        'remember': valid_ascii,
        'cancel': valid_ascii,
        'submit': valid_distinguished_name,
        'success_to': valid_url,
        'fail_to': valid_url,
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
        'openid.return_to': valid_url,
        'openid.trust_root': valid_base_url,
        }

    def __init__(self, *args, **kwargs):
        self.clearUser()
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def clearUser(self):
        """Reset all saved user variables"""
        self.user = None
        self.user_dn = None
        self.user_dn_dir = None
        self.password = None
        
    def do_GET(self):
        """Handle all HTTP GET requests"""
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
            elif path == '/openidserver':
                self.serverEndPoint(self.query)

            elif path == '/login':
                self.showLoginPage('/%s/' % self.server.server_base,
                                   '/%s/' % self.server.server_base)
            elif path == '/loginsubmit':
                self.doLogin()
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
        except:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(cgitb.html(sys.exc_info(), context=10))
            print "ERROR: %s" % cgitb.html(sys.exc_info(), context=10)

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
            else:
                self.send_response(404)
                self.end_headers()

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(cgitb.html(sys.exc_info(), context=10))
            print "ERROR: %s" % cgitb.html(sys.exc_info(), context=10)

    def handleAllow(self, query):
        """Handle requests to allow authentication:
        Must verify user is already logged in or validate username/password
        pair against user DB.
        """
        request = self.server.lastCheckIDRequest.get(self.user)

        print "handleAllow with last request %s from user %s" % \
              (request, self.user)
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
                identity = self.server.base_url + 'id/' + \
                           lookup_full_identity(query.get('identifier', ''))
            else:
                identity = request.identity

            print "handleAllow with identity %s" % identity

            if 'password' in self.query:
                print "setting password"
                self.password = self.query['password']
            else:
                print "no password in query"
                self.password = None

            if self.checkLogin(self.user, self.password):
                print "handleAllow validated login %s" % identity
                trust_root = request.trust_root
                if self.query.get('remember', 'no') == 'yes':
                    self.server.approved[(identity, trust_root)] = 'always'

                print "handleAllow approving login %s" % identity
                response = self.approved(request, identity)
            else:
                print "handleAllow rejected login %s" % identity
                self.clearUser()
                response = self.rejected(request, identity)    
        elif 'no' in query:
            response = request.answer(False)

        else:
            assert False, 'strange allow post.  %r' % (query,)

        self.displayResponse(response)


    def setUser(self):
        """Read any saved user value from cookie"""
        cookies = self.headers.get('Cookie')
        if cookies:
            morsel = Cookie.BaseCookie(cookies).get('user')
            # Added morsel value check here since IE sends empty string from
            # cookie after initial user=;expire is sent. Others leave it out.
            if morsel and morsel.value != '':
                self.user = morsel.value

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
        sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)

        # In a real application, this data would be user-specific,
        # and the user should be asked for permission to release
        # it.
        sreg_data = {
            'nickname': self.user,
            # TODO: load real user data from DB
            'fullname': 'Some One',
            'email': 'someone@nowhere.org',
            'country': 'DK',
            # Unofficial fields
            'org': 'Some Organization'
            }

        sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
        response.addExtension(sreg_resp)

    def approved(self, request, identifier=None):
        """Accept helper"""
        response = request.answer(True, identity=identifier)
        # TODO: re-enable this SReg data?
        #self.addSRegResponse(request, response)
        return response

    def rejected(self, request, identifier=None):
        """Reject helper"""
        response = request.answer(False, identity=identifier)
        return response

    def handleCheckIDRequest(self, request):
        """Check ID handler"""
        print "handleCheckIDRequest with req %s" % request
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
        """Check username and password in MiG user DB""" 
        db_path = os.path.join(configuration.mig_code_base, 'server',
                               'MiG-users.db')
        # print "Loading user DB"
        id_map = load_user_db(db_path)
        user_alias = configuration.user_openid_alias
        for cert_id in id_map.keys():
            cert_dir = client_id_dir(cert_id)
            user_match = [cert_id, cert_dir, client_alias(cert_id)]
            if user_alias:
                short_id = extract_field(cert_id, user_alias)
                # Allow both raw alias field value and asciified alias
                user_match.append(short_id)
                user_match.append(client_alias(short_id))
                # print "DEBUG: short alias for %s: %s" % (short_id, client_alias(short_id))
            if username in user_match:
                user = id_map[cert_id]
                print "looked up user %s in DB: %s" % (username, user)
                enc_pw = user.get('password', None)
                print "DEBUG: Check password against enc %s" % enc_pw
                if password and base64.b64encode(password) == user['password']:
                    print "Correct password for user %s" % username
                    self.user_dn = cert_id
                    self.user_dn_dir = cert_dir
                    return True
                else:
                    print "Failed password check for user %s" % username
                    break
        print "Invalid login for user %s" % username
        return False
                
    def doLogin(self):
        """Login handler"""
        if 'submit' in self.query:
            if 'user' in self.query:
                self.user = self.query['user']
            else:
                self.clearUser()
            if 'password' in self.query:
                self.password = self.query['password']
            else:
                self.password = None
            if self.checkLogin(self.user, self.password):
                if not self.query['success_to']:
                    self.query['success_to'] = '%s/id/' % self.server.base_url
                print "doLogin succeded: redirect to %s" % self.query['success_to']
                self.redirect(self.query['success_to'])
            else:
                # TODO: Login failed - is this correct behaviour?
                print "doLogin failed for %s!" % self.user
                #print "doLogin full query: %s" % self.query
                self.clearUser()
                self.redirect(self.query['success_to'])
        elif 'cancel' in self.query:
            self.redirect(self.query['fail_to'])
        else:
            assert 0, 'strange login %r' % (self.query,)

    def redirect(self, url):
        """Redirect helper"""
        self.send_response(302)
        self.send_header('Location', url)
        self.writeUserHeader()

        self.end_headers()

    def writeUserHeader(self):
        """Response helper"""
        if self.user is None:
            t1970 = time.gmtime(0)
            expires = time.strftime(
                'Expires=%a, %d-%b-%y %H:%M:%S GMT', t1970)
            self.send_header('Set-Cookie', 'user=;%s' % expires)
        else:
            self.send_header('Set-Cookie', 'user=%s' % self.user)

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

    def showErrorPage(self, error_message):
        """Error page provider"""
        self.showPage(400, 'Error Processing Request', err='''\
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

        if request.idSelect(): # We are being asked to select an ID
            user_alias = configuration.user_openid_alias

            msg = '''\
            <p>A site has asked for your identity. Please select your
            ID in the list and enter your password to login.
            </p>
            '''
            if user_alias:
                alias_mark = '[...]'
            else:
                alias_mark = ''
            fdata = {
                'id_url_base': id_url_base,
                'trust_root': request.trust_root,
                'server_base': self.server.server_base,
                'alias_mark': alias_mark,
                }
            form = '''\
            <form method="POST" action="/%(server_base)s/allow">
            <table>
              <tr><td>Identity:</td>
                 <td>%(id_url_base)s%(alias_mark)s<input id="id_select"
                     name="identifier" />
              </td></tr>
              <tr><td>Password:</td>
                 <td><input type="password" name="password"></td></tr>
              <tr><td>Trust Root:</td><td>%(trust_root)s</td></tr>
            </table>
            <p>Allow this authentication to proceed?</p>
            <input type="checkbox" id="remember" name="remember" value="yes"
                /><label for="remember">Remember this
                decision</label><br />
            <input type="submit" name="yes" value="yes" />
            <input type="submit" name="no" value="no" />
            </form>
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
              Password: <input type="password" name="password"><br />
              <input type="submit" name="yes" value="yes" />
              <input type="submit" name="no" value="no" />
            </form>''' % fdata
        else:
            mdata = {
                'expected_user': expected_user,
                'user': self.user,
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
              <input type="hidden" name="login_as" value="%(expected_user)s"/>
              Password: <input type="password" name="password"><br />
              <input type="submit" name="yes" value="yes" />
              <input type="submit" name="no" value="no" />
            </form>''' % fdata

        self.showPage(200, 'Approve OpenID request?', msg=msg, form=form)

    def showIdPage(self, path):
        """User info page provider"""
        link_tag = '<link rel="openid.server" href="%sopenidserver">' % \
              self.server.base_url
        yadis_loc_tag = '<meta http-equiv="x-xrds-location" content="%s">' % \
            (self.server.base_url+'yadis/'+path[4:])
        disco_tags = link_tag + yadis_loc_tag
        ident = self.server.base_url + path[1:]

        approved_trust_roots = []
        # Don't disclose information about other active login sessions
        ident_user = path.split('/')[-1]
        if self.user == ident_user:
            for (aident, trust_root) in self.server.approved.keys():
                if aident == ident:
                    trs = '<li><tt>%s</tt></li>\n' % cgi.escape(trust_root)
                    approved_trust_roots.append(trs)
        else:
            print "Not disclosing trust roots for %s (active login %s)" % \
                  (ident_user, self.user)

        if approved_trust_roots:
            prepend = '<p>Approved trust roots:</p>\n<ul>\n'
            approved_trust_roots.insert(0, prepend)
            approved_trust_roots.append('</ul>\n')
            msg = ''.join(approved_trust_roots)
        else:
            msg = ''

        self.showPage(200, 'An Identity Page', head_extras=disco_tags, msg='''\
        <p>This is an identity page for %s.</p>
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
        yadis_tag = '<meta http-equiv="x-xrds-location" content="%s">' % \
            (self.server.base_url + 'serveryadis')
        if self.user:
            openid_url = self.server.base_url + 'id/' + self.user
            user_message = """\
            <p>You are logged in as %s. Your OpenID identity URL is
            <tt><a href=%s>%s</a></tt>. Enter that URL at an OpenID
            consumer to test this server.</p>
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

        <p>The URL for this server is <a href=%s><tt>%s</tt></a>.</p>
        ''' % (user_message, quoteattr(self.server.base_url), self.server.base_url))

    def showLoginPage(self, success_to, fail_to):
        """Login page provider"""
        self.showPage(200, 'Login Page', form='''\
        <h2>Login</h2>
        <p>Please enter your %s username and password to prove your identify
        to this OpenID service.</p>
        <form method="GET" action="/%s/loginsubmit">
          <input type="hidden" name="success_to" value="%s" />
          <input type="hidden" name="fail_to" value="%s" />
          Username: <input type="text" name="user" value="" /><br />
          Password: <input type="password" name="password"><br />
          <input type="submit" name="submit" value="Log In" />
          <input type="submit" name="cancel" value="Cancel" />
        </form>
        ''' % (configuration.short_title, self.server.server_base,
               success_to, fail_to))

    def showPage(self, response_code, title,
                 head_extras='', msg=None, err=None, form=None):
        """Show page helper"""
        if self.user is None:
            user_link = '<a href="/%s/login">not logged in</a>.' % \
                        self.server.server_base
        else:
            user_link = 'logged in as <a href="/%s/id/%s">%s</a>.<br /><a href="/%s/loginsubmit?submit=true&success_to=/%s/login">Log out</a>' % \
                        (self.server.server_base, self.user, self.user, self.server.server_base, self.server.server_base)

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

        contents = {
            'title': configuration.short_title + ' OpenID Server - ' + title,
            'short_title': configuration.short_title,
            'head_extras': head_extras,
            'body': body,
            'user_link': user_link,
            'root_url': '/%s/' % self.server.server_base,
            }

        self.send_response(response_code)
        self.writeUserHeader()
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write('''<html>
  <head>
    <title>%(title)s</title>
    %(head_extras)s
  </head>
  <style type="text/css">
      h1 a:link {
          color: black;
          text-decoration: none;
      }
      h1 a:visited {
          color: black;
          text-decoration: none;
      }
      h1 a:hover {
          text-decoration: underline;
      }
      body {
        font-family: verdana,sans-serif;
        width: 50em;
        margin: 1em;
      }
      div {
        padding: .5em;
      }
      table {
        margin: none;
        padding: none;
      }
      .banner {
        padding: none 1em 1em 1em;
        width: 100%%;
      }
      .leftbanner {
        text-align: left;
      }
      .rightbanner {
        text-align: right;
        font-size: smaller;
      }
      .error {
        border: 1px solid #ff0000;
        background: #ffaaaa;
        margin: .5em;
      }
      .message {
        border: 1px solid #2233ff;
        background: #eeeeff;
        margin: .5em;
      }
      .form {
        border: 1px solid #777777;
        background: #ddddcc;
        margin: .5em;
        margin-top: 1em;
        padding-bottom: 0em;
      }
      dd {
        margin-bottom: 0.5em;
      }
  </style>
  <body>
    <table class="banner">
      <tr>
        <td class="leftbanner">
          <h1><a href="%(root_url)s">%(short_title)s OpenID Server</a></h1>
        </td>
        <td class="rightbanner">
          You are %(user_link)s
        </td>
      </tr>
    </table>
%(body)s
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
        cert_path = configuration.user_openid_key
        if not os.path.isfile(cert_path):
            logger.error('No such server key: %s' % cert_path)
            sys.exit(1)
        logger.info('Wrapping connections in SSL')
        httpserver.socket = ssl.wrap_socket(httpserver.socket,
                                            certfile=cert_path,
                                            server_side=True)
        
    print 'Server running at:'
    print httpserver.base_url
    httpserver.serve_forever()


if __name__ == '__main__':
    configuration = get_configuration_object()
    logger = configuration.logger
    nossl = False

    # Allow configuration overrides on command line
    if sys.argv[1:]:
        nossl = sys.argv[1].lower() in ('yes', 'true', '1')
    if sys.argv[2:]:
        configuration.user_openid_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_openid_port = int(sys.argv[3])

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
        'session_store': os.path.abspath(configuration.openid_store),
        'allow_password': 'password' in configuration.user_openid_auth,
        'allow_publickey': 'publickey' in configuration.user_openid_auth,
        'user_alias': configuration.user_openid_alias,
        'host_rsa_key': host_rsa_key,
        'users': [],
        'time_stamp': 0,
        'logger': logger,
        'nossl': nossl,
        }
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
