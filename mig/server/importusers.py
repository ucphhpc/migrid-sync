#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# importusers - Import users from text or xml file in provided uri
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

"""Import any missing users from provided URI"""

import os
import sys
import getopt
import re
import time
import urllib

import shared.returnvalues as returnvalues
from shared.base import fill_user, distinguished_name_to_user
from shared.conf import get_configuration_object
from shared.defaults import csrf_field, keyword_auto, cert_valid_days
from shared.functionality.sendrequestaction import main
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.pwhash import generate_random_password, unscramble_password, \
    scramble_password
from shared.safeinput import valid_password_chars
from shared.useradm import init_user_adm, default_search, create_user, \
    search_users


def usage(name='importusers.py'):
    """Usage help"""

    print """Import users from an external plain text or XML source URI.
Creates a local MiG user identified by DISTINGUISHED_NAME for each
new <item>DISTINGUISHED_NAME</item> in the XML or for each DISTINGUISHED_NAME
line in the text file.

Usage:
%(name)s [OPTIONS] URI [URI [...]]
Where URI may be an URL or local file and OPTIONS may be one or more of:
   -C CERT_PATH        Use CERT_PATH as client certificate
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -K KEY_PATH         Use KEY_PATH as client key
   -m VGRID            Make user a member of VGRID (multiple occurences allowed)
   -p PASSWORD         Optional PASSWORD to set for user (AUTO to generate one)
   -v                  Verbose output
""" % {'name': name}


def dump_contents(url, key_path=None, cert_path=None):
    """dump list of data lines from provided URL.
    Optional client key and certificate is supported.
    """

    # allow file dump at least until we get certificate based access

    browser = urllib.FancyURLopener(key_file=key_path,
                                    cert_file=cert_path)
    pipe = browser.open(url)
    data = pipe.read()
    browser.close()

    return data


def parse_contents(user_data):
    """Extract users from data dump - We simply catch all occurences of
    anything looking like a DN (/ABC=bla bla/DEF=more words/...) either in
    tags or in plain text line.
    """

    users = []
    for user_creds in re.findall('/[a-zA-Z]+=[^<\n]+', user_data):
        #print "DEBUG: handling user %s" % user_creds
        user_dict = distinguished_name_to_user(user_creds.strip())
        users.append(user_dict)
    return users


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    key_path = None
    cert_path = None
    force = False
    password = False
    verbose = False
    vgrids = []
    opt_args = 'C:c:d:fhK:m:p:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-C':
            cert_path = val
        elif opt == '-K':
            key_path = val
        elif opt == '-m':
            vgrids.append(val)
        elif opt == '-p':
            password = val
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt
            sys.exit(1)

    if not args:
        print 'Must provide one or more URIs to import from'
        usage()
        sys.exit(1)

    users = []
    for url in args:
        url_dump = dump_contents(url, key_path, cert_path)
        users += parse_contents(url_dump)

    new_users = []
    for user_dict in users:
        id_search = default_search()
        id_search['distinguished_name'] = user_dict['distinguished_name']
        if search_users(id_search, conf_path, db_path, verbose):
            if verbose:
                print 'Not adding existing user: %s'\
                      % user_dict['distinguished_name']
            continue
        new_users.append(user_dict)

    configuration = get_configuration_object()
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'sendrequestaction'
    for user_dict in new_users:
        fill_user(user_dict)
        client_id = user_dict['distinguished_name']
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        user_dict['comment'] = 'imported from external URI'
        if password == keyword_auto:
            print 'Auto generating password for user: %s' % client_id
            user_dict['password'] = generate_random_password(configuration)
        elif password:
            print 'Setting provided password for user: %s' % client_id
            user_dict['password'] = password
        else:
            print 'Setting empty password for user: %s' % client_id
            user_dict['password'] = ''

        # Encode password if set but not already encoded
        if user_dict['password']:
            if verbose:
                print 'Scrambling password for user: %s' % client_id
            user_dict['password'] = scramble_password(
                configuration.site_password_salt, user_dict['password'])

        if not user_dict.has_key('expire'):
            user_dict['expire'] = int(
                time.time() + cert_valid_days * 24 * 60 * 60)

        try:
            create_user(user_dict, conf_path, db_path, force, verbose)
        except Exception, exc:
            print exc
            continue
        print 'Created %s in user database and in file system' % client_id
        # Needed for CSRF check in safe_handler
        os.environ.update({'SCRIPT_URL': '%s.py' % target_op,
                           'REQUEST_METHOD': form_method})
        for name in vgrids:
            request = {'cert_id': client_id, 'vgrid_name': [name],
                       'request_type': ['vgridmember'],
                       'request_text':
                       ['automatic request from importusers script'],
                       csrf_field: [csrf_token]}
            (output, status) = main(client_id, request)
            if status == returnvalues.OK:
                print 'Request for %s membership in %s sent to owners' % \
                      (client_id, name)
            else:
                print 'Request for %s membership in %s failed: %s' % \
                      (name, client_id, output)

    print '%d new users imported' % len(new_users)
