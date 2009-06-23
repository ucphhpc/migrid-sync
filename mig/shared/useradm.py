#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# useradm - User administration functions
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

"""User administration functions"""

import os
import sys
import tempfile
import fcntl
import pickle
import fnmatch

from shared.conf import get_configuration_object
from shared.configuration import Configuration
from shared.settings import css_template, get_default_css

db_name = "MiG-users.db"
cert_field_order = [('country', 'C'), ('state', 'ST'), ('locality', 'L'),
                    ('organization', 'O'), ('organizational_unit', 'OU'),
                    ('full_name', 'CN'), ('email', 'emailAddress')]
cert_field_map = dict(cert_field_order)

def init_user_adm():
    """Shared init function for all user administration scripts"""
    args = sys.argv[1:]
    app_dir = os.path.dirname(sys.argv[0])
    if not app_dir:
        app_dir = '.'
    db_path = os.path.join(app_dir, db_name)
    return (args, app_dir, db_path)

def fill_user(target):
    """Fill target user dictionary with all expected fields"""
    for (key, val) in cert_field_order:
        target[key] = target.get(key, '')
    return target

def fill_distinguished_name(user):
    """Fill distinguished_name field from other fields if not already set"""
    user['distinguished_name'] = user.get('distinguished_name', '')
    for (key, val) in cert_field_order:
        setting = user.get(key, '')
        # Hack: MiG certificates get empty fields set to NA
        if not setting:
            setting = 'NA'
        user['distinguished_name'] += '/%s=%s' % (val, setting)
    return user

def distinguished_name_to_user(distinguished_name):
    """Build user dictionary from distinguished_name string on the form:
    /X=abc/Y=def/Z=ghi
    """
    user_dict = {'distinguished_name': distinguished_name}
    parts = distinguished_name.split('/')
    for field in parts:
        if not field:
            continue
        (key, val) = field.split('=', 1)
        if not key in cert_field_map.values():
            user_dict[key] = val
        else:
            for (name, short) in cert_field_order:
                if key == short:
                    user_dict[name] = val
    return user_dict

def load_user_db(db_path):
    """Load pickled user DB"""
    db_fd = open(db_path, 'rb')
    user_db = pickle.load(db_fd)
    db_fd.close()
    return user_db

def save_user_db(user_db, db_path):
    """Save pickled user DB"""
    db_fd = open(db_path, 'wb')
    pickle.dump(user_db, db_fd)
    db_fd.close()

def delete_dir(path):
    """Recursively remove path:
    first remove all files and subdirs, then remove dir tree.
    """

    for (root, dirs, files) in os.walk(path, topdown=False):
        for name in files:
            print 'removing: ' + root + os.sep + name
            os.remove(root + os.sep + name)
        for name in dirs:
            print 'removing: ' + root + os.sep + name
            if os.path.islink(root + os.sep + name):
                os.remove(root + os.sep + name)
            else:
                os.rmdir(root + os.sep + name)
    os.removedirs(path)

def create_user(user, conf_path, db_path, force=False):
    """Add user"""
    user_db = {}
    if conf_path:
        # has been checked for accessibility above...
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    user_id = '%(full_name)s:%(organization)s:' % user
    user_id += '%(state)s:%(country)s:%(email)s' % user
    full_name = user['full_name']
    full_name_without_spaces = full_name.replace(' ', '_')

    renew = False

    print 'User name without spaces: %s\n' % full_name_without_spaces
    if os.path.exists(db_path):
        try:
            db_fd = open(db_path, 'rb')
            user_db = pickle.load(db_fd)
            db_fd.close()
            print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            print 'Failed to load user DB!'
            if not force:
                sys.exit(1)

        if user_db.has_key(user_id):
            renew_answer = \
                         raw_input('User DB entry already exists - renew? [Y/n] ')
            renew = not renew_answer.lower().startswith('n')
            if renew:
                print 'Renewing existing user'
            elif not force:
                print 'Nothing more to do for existing user'
                return

    try:
        user_db[user_id] = user
        db_fd = open(db_path, 'wb')
        pickle.dump(user_db, db_fd)
        db_fd.close()
        print 'User %s was successfully added/updated in user DB!'\
              % full_name
    except Exception, err:
        print 'Error: Failed to add %s to user DB: %s' % (full_name, err)
        if not force:
            sys.exit(1)

    home_dir = os.path.join(configuration.user_home,
                            full_name_without_spaces)
    mrsl_dir = os.path.join(configuration.mrsl_files_dir,
                            full_name_without_spaces)
    pending_dir = os.path.join(configuration.resource_pending,
                               full_name_without_spaces)
    htaccess_path = os.path.join(home_dir, '.htaccess')
    css_path = os.path.join(home_dir, css_template)
    if not renew:
        print 'Creating dirs and files for new user: %s' % full_name
        
        try:
            os.mkdir(home_dir)
        except:
            print 'Error: could not create home dir: %s' % home_dir
            if not force:
                sys.exit(1)

        try:
            os.mkdir(mrsl_dir)
        except:
            print 'Error: could not create mrsl dir: %s' % mrsl_dir
            if not force:
                sys.exit(1)

        try:
            os.mkdir(pending_dir)
        except:
            print 'Error: could not create resource dir: %s' % pending_dir
            if not force:
                sys.exit(1)
    else:

        # Allow temporary write access
        
        os.chmod(htaccess_path, 0644)

    # Always write htaccess to catch any updates
        
    try:
        filehandle = open(htaccess_path, 'w')
        
        # Match all known fields
        
        access = 'SSLRequire ('
        access += '%%{SSL_CLIENT_S_DN} eq "%(distinguished_name)s"'
        access += ')\n'
        
        filehandle.write(access % user)
        filehandle.close()

        # try to prevent further user modification

        os.chmod(htaccess_path, 0444)
    except:
        print 'Error: could not create htaccess file: %s' % htaccess_path
        if not force:
            sys.exit(1)

    # Always write default css to avoid apache error log entries

    try:
        filehandle = open(css_path, 'w')
        filehandle.write(get_default_css(css_path))
        filehandle.close()
    except:
        print 'Error: could not create custom css file: %s' % css_path
        if not force:
            sys.exit(1)

def delete_user(user, conf_path, db_path, force=False):
    """Delete user"""
    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    user_id = '%(full_name)s:%(organization)s:' % user
    user_id += '%(state)s:%(country)s:%(email)s' % user
    full_name = user['full_name']
    full_name_without_spaces = full_name.replace(' ', '_')

    print 'User name without spaces: %s\n' % full_name_without_spaces

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            print 'Failed to load user DB!'
            print err
            if not force:
                sys.exit(1)

        if not user_db.has_key(user_id):
            print "Error: User DB entry '%s' doesn't exist!" % user_id
            if not force:
                sys.exit(1)

    try:
        del user_db[user_id]
        save_user_db(user_db, db_path)
        print 'User %s was successfully removed from user DB!' % full_name
    except Exception, err:
        print 'Error: Failed to remove %s from user DB: %s' % (full_name,
                err)
        if not force:
            sys.exit(1)

    if not os.path.exists(configuration.user_home
                           + full_name_without_spaces):
        print "Error: User dir doesn't exist!"
        if not force:
            sys.exit(1)

    # Remove user dirs recursively

    try:
        delete_dir(configuration.resource_pending
                    + full_name_without_spaces)
    except:
        print 'Error: could not remove resource dir: %s'\
             % configuration.resource_pending + full_name_without_spaces
        if not force:
            sys.exit(1)

    try:
        delete_dir(configuration.mrsl_files_dir + full_name_without_spaces)
    except:
        print 'Error: could not remove mrsl dir: %s'\
             % configuration.mrsl_files_dir + full_name_without_spaces
        if not force:
            sys.exit(1)

    try:
        delete_dir(configuration.user_home + full_name_without_spaces)
    except Exception, err:
        print 'Error: could not remove home dir: %s (%s)'\
             % (configuration.user_home + full_name_without_spaces, err)
        if not force:
            sys.exit(1)

def default_search():
    """Default search filter to match all users"""
    search_filter = {}
    for (key, val) in cert_field_order:
        search_filter[key] = '*'
    return search_filter

def search_users(search_filter, conf_path, db_path):
    """Search for matching users"""
    try:
        user_db = load_user_db(db_path)
        print 'Loaded existing user DB from: %s' % db_path
    except Exception, err:
        print 'Failed to load user DB: %s' % err
        sys.exit(1)

    hits = []
    for (uid, user_dict) in user_db.items():
        match = True
        for (key, val) in search_filter.items():
            if not fnmatch.fnmatch(str(user_dict.get(key, '')), val):
                match = False
                break
        if not match:
            continue
        hits.append((uid, user_dict))
    return hits
