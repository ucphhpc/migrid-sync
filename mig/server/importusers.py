#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# importusers - Import users from XML file in provided URL 
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Import any missing users from provided URL into user DB and in file system"""

import sys
import getopt
import urllib

from shared.useradm import init_user_adm, fill_user, distinguished_name_to_user, \
     create_user, search_users

def usage(name='importusers.py'):
    """Usage help"""
    print """Usage:
%(name)s [OPTIONS] URL [URL [...]]
Where OPTIONS may be one or more of:
   -C CERT_PATH        Use CERT_PATH as client certificate
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -h                  Show this help
   -K KEY_PATH         Use KEY_PATH as client key
"""\
         % {'name': name}

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
    """Extract users from data dump"""
    users = []
    for line in user_data.split('\n'):
        line = line.strip()
        if not line or line.find('<item>') == -1:
            continue
        line = line.split('<item>', 1)[-1]
        line = line.split('</item>', 1)[0]
        user_dict = distinguished_name_to_user(line)
        users.append(user_dict)
    return users


# ## Main ###
if "__main__" == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    key_path = None
    cert_path = None
    opt_args = 'C:c:d:hK:'
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
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-C':
            cert_path = val
        elif opt == '-K':
            key_path = val
        else:
            print 'Error: %s not supported!' % opt
            sys.exit(1)

    if not args:
        print 'Must provide one or more URLs to import from'
        usage()
        sys.exit(1)

    users = []
    for url in args:
        url_dump = dump_contents(url, key_path, cert_path)
        users += parse_contents(url_dump)

    new_users = []
    for user_dict in users:    
        if search_users(user_dict, conf_path, db_path):
            print "Not adding existing user: %s" % user_dict['distinguished_name']
            continue
        new_users.append(user_dict)
        
    for user_dict in new_users:    
        fill_user(user_dict)
        user_dict['comment'] = 'imported from external URL'
        print "creating user: %s" % user_dict['distinguished_name']
        create_user(user_dict, conf_path, db_path, False)
        
    print '%d new users imported' % len(new_users)
