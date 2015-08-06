#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# useradm - user administration functions
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

"""User administration functions"""

import base64
import datetime
import fnmatch
import os
import re
import shutil
import sqlite3
import sys

from shared.base import client_id_dir, client_dir_id, client_alias, \
     sandbox_resource
from shared.conf import get_configuration_object
from shared.configuration import Configuration
from shared.defaults import user_db_filename, keyword_auto, ssh_conf_dir, davs_conf_dir, \
     ftps_conf_dir, htaccess_filename, welcome_filename, settings_filename, \
     profile_filename, default_css_filename, widgets_filename, \
     authkeys_filename, authpasswords_filename, authdigests_filename
from shared.fileio import filter_pickled_list, filter_pickled_dict
from shared.modified import mark_user_modified
from shared.refunctions import list_runtime_environments, \
     update_runtimeenv_owner
from shared.pwhash import make_hash, check_hash, make_digest, check_digest
from shared.resource import resource_add_owners, resource_remove_owners
from shared.serial import load, dump
from shared.settings import update_settings, update_profile, update_widgets
from shared.vgrid import vgrid_add_owners, vgrid_remove_owners, \
     vgrid_add_members, vgrid_remove_members
from shared.vgridaccess import get_resource_map, get_vgrid_map, \
     refresh_user_map, refresh_resource_map, refresh_vgrid_map, VGRIDS, \
     OWNERS, MEMBERS

ssh_authkeys = os.path.join(ssh_conf_dir, authkeys_filename)
ssh_authpasswords = os.path.join(ssh_conf_dir, authpasswords_filename)
ssh_authdigests = os.path.join(ssh_conf_dir, authdigests_filename)
davs_authkeys = os.path.join(davs_conf_dir, authkeys_filename)
davs_authpasswords = os.path.join(davs_conf_dir, authpasswords_filename)
davs_authdigests = os.path.join(davs_conf_dir, authdigests_filename)
ftps_authkeys = os.path.join(ftps_conf_dir, authkeys_filename)
ftps_authpasswords = os.path.join(ftps_conf_dir, authpasswords_filename)
ftps_authdigests = os.path.join(ftps_conf_dir, authdigests_filename)
cert_field_order = [
    ('country', 'C'),
    ('state', 'ST'),
    ('locality', 'L'),
    ('organization', 'O'),
    ('organizational_unit', 'OU'),
    ('full_name', 'CN'),
    ('email', 'emailAddress'),
    ]
cert_field_map = dict(cert_field_order)

def init_user_adm():
    """Shared init function for all user administration scripts"""

    args = sys.argv[1:]
    app_dir = os.path.dirname(sys.argv[0])
    if not app_dir:
        app_dir = '.'
    db_path = os.path.join(app_dir, user_db_filename)
    return (args, app_dir, db_path)


def fill_user(target):
    """Fill target user dictionary with all expected fields"""

    for (key, _) in cert_field_order:
        target[key] = target.get(key, '')
    return target


def fill_distinguished_name(user):
    """Fill distinguished_name field from other fields if not already set.

    Please note that MiG certificates get empty fields set to NA, so this
    is translated here, too.
    """

    if user.get('distinguished_name', ''):
        return user
    else:
        user['distinguished_name'] = ''
    for (key, val) in cert_field_order:
        setting = user.get(key, '')
        if not setting:
            setting = 'NA'
        user['distinguished_name'] += '/%s=%s' % (val, setting)
    return user


def distinguished_name_to_user(distinguished_name):
    """Build user dictionary from distinguished_name string on the form:
    /X=abc/Y=def/Z=ghi

    Please note that MiG certificates get empty fields set to NA, so this
    is translated back here, too.
    """

    user_dict = {'distinguished_name': distinguished_name}
    parts = distinguished_name.split('/')
    for field in parts:
        if not field:
            continue
        (key, val) = field.split('=', 1)
        if 'NA' == val:
            val = ''
        if not key in cert_field_map.values():
            user_dict[key] = val
        else:
            for (name, short) in cert_field_order:
                if key == short:
                    user_dict[name] = val
    return user_dict


def extract_field(distinguished_name, field_name):
    """Extract field_name value from client_id if included"""
    user = distinguished_name_to_user(distinguished_name)
    return user.get(field_name, None)


def load_user_db(db_path):
    """Load pickled user DB"""

    return load(db_path)


def load_user_dict(user_id, db_path, verbose=False):
    """Load user dictionary from user DB"""

    try:
        user_db = load_user_db(db_path)
        if verbose:
            print 'Loaded existing user DB from: %s' % db_path
    except Exception, err:
        print 'Failed to load user DB: %s' % err
        return None
    return user_db.get(user_id, None)


def save_user_db(user_db, db_path):
    """Save pickled user DB"""

    dump(user_db, db_path)


def delete_dir(path, verbose=False):
    """Recursively remove path:
    first remove all files and subdirs, then remove dir tree.
    """

    if verbose:
        print 'removing: %s' % path
    shutil.rmtree(path)

def rename_dir(src, dst, verbose=False):
    """Rename src to dst"""

    if verbose:
        print 'renaming: %s -> %s ' % (src, dst)
    shutil.move(src, dst)

def remove_alias_link(username, user_home):
    """Remove user alias if it exists"""
    link_path = os.path.join(user_home, username)
    if not os.path.islink(link_path):
        return True
    try:
        os.remove(link_path)
    except:
        raise Exception('could not remove symlink: %s' % link_path)
    return True

def create_alias_link(username, client_id, user_home):
    """Create alias link if missing"""
    client_dir = client_id_dir(client_id)
    home_dir = os.path.join(user_home, client_dir)
    link_path = os.path.join(user_home, username)
    if os.path.exists(link_path):
        return True
    try:
        os.symlink(client_dir, link_path)
    except:
        raise Exception('could not symlink alias: %s' % link_path)
    return True    


def create_seafile_mount_link(client_id, configuration):
    """Create link to fuse mounted seafile library for client_id"""
    client_dir = client_id_dir(client_id)
    mount_link = os.path.join(configuration.user_home, client_dir, 'seafile-readonly')
    user_alias = configuration.user_seafile_alias
    short_id = extract_field(client_id, user_alias)
    seafile_home = os.path.join(configuration.seafile_mount, short_id)
    logger = configuration.logger
    if os.path.isdir(seafile_home) and not os.path.islink(mount_link):
        try:
            os.symlink(seafile_home, mount_link)
        except Exception, exc:
            logger.error("failed to link seafile mount %s to %s: %s" \
                         % (seafile_home, mount_link, exc))
            raise

def remove_seafile_mount_link(client_id, configuration):
    """Remove link to fuse mounted seafile library for client_id"""
    client_dir = client_id_dir(client_id)
    mount_link = os.path.join(configuration.user_home, client_dir, 'seafile-readonly')
    logger = configuration.logger
    if os.path.islink(mount_link):
        try:
            os.remove(mount_link)
        except Exception, exc:
            logger.error("failed to unlink seafile mount from %s: %s" \
                         % (mount_link, exc))
            raise

    
def create_user(
    user,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ask_renew=True,
    default_renew=False
    ):
    """Add user"""

    user_db = {}
    if conf_path:

        # has been checked for accessibility above...

        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    fill_distinguished_name(user)
    client_id = user['distinguished_name']
    client_dir = client_id_dir(client_id)

    renew = default_renew
    # Requested with existing valid certificate?
    # Used in order to authorize password change
    authorized = user.get('authorized', False)

    if verbose:
        print 'User ID: %s\n' % client_id
    if os.path.exists(db_path):
        try:
            user_db = load(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB!')

        # Prevent alias clashes by preventing addition of new users with same
        # alias. We only allow renew of existing user.
        if configuration.user_openid_providers and \
               configuration.user_openid_alias:
            user_aliases = dict([(key, val[configuration.user_openid_alias]) \
                                 for (key, val) in user_db.items()])
            alias = user[configuration.user_openid_alias]
            if alias in user_aliases.values() and \
                   user_aliases.get(client_id, None) != alias:
                if verbose:
                    print 'Attempting create_user with conflicting alias %s' % \
                          alias
                raise Exception(
                    'A conflicting user with alias %s already exists' % alias)

        if user_db.has_key(client_id):
            if ask_renew:
                print 'User DB entry for "%s" already exists' % client_id
                renew_answer = raw_input('Renew existing entry? [Y/n] ')
                renew = not renew_answer.lower().startswith('n')
            else:
                renew = default_renew
            if renew:
                user['old_password'] = user_db[client_id]['password']
                # OpenID users do not provide a password
                if not user['password']:
                    user['password'] = user['old_password']
                password_changed = (user['old_password'] != user['password'])
                if password_changed:
                    if authorized:
                        del user['authorized']
                        print "User authorized password update"
                    else:
                        if verbose:
                            print """Renewal request supplied a different
password:
Please re-request with the original password or use existing cert to assure
authenticity!"""
                        err = """Cannot renew account using a new password!
Please tell user to use the original password or request renewal using a
certificate that is still valid."""
                        raise Exception(err)
                if verbose:
                    print 'Renewing existing user'
            elif not force:
                if verbose:
                    print 'Nothing more to do for existing user %s' % client_id
                raise Exception('Nothing more to do for existing user %s' % \
                                client_id)

    # Add optional OpenID usernames to user (pickle may include some already)
    
    openid_names = user.get('openid_names', [])
    add_names = []
    if configuration.user_openid_providers and configuration.user_openid_alias:
        add_names.append(user[configuration.user_openid_alias])
    user['openid_names'] = dict([(name, 0) for name in add_names + \
                                 openid_names]).keys()
    
    try:
        user_db[client_id] = user
        dump(user_db, db_path)
        if verbose:
            print 'User %s was successfully added/updated in user DB!'\
                  % client_id
    except Exception, err:
        if not force:
            raise Exception('Failed to add %s to user DB: %s' % \
                            (client_id, err))

    home_dir = os.path.join(configuration.user_home, client_dir)
    settings_dir = os.path.join(configuration.user_settings, client_dir)
    cache_dir = os.path.join(configuration.user_cache, client_dir)
    mrsl_dir = os.path.join(configuration.mrsl_files_dir, client_dir)
    pending_dir = os.path.join(configuration.resource_pending,
                               client_dir)
    ssh_dir = os.path.join(home_dir, ssh_conf_dir)
    davs_dir = os.path.join(home_dir, davs_conf_dir)
    ftps_dir = os.path.join(home_dir, ftps_conf_dir)
    htaccess_path = os.path.join(home_dir, htaccess_filename)
    welcome_path = os.path.join(home_dir, welcome_filename)
    settings_path = os.path.join(settings_dir, settings_filename)
    profile_path = os.path.join(settings_dir, profile_filename)
    widgets_path = os.path.join(settings_dir, widgets_filename)
    css_path = os.path.join(home_dir, default_css_filename)
    required_dirs = (settings_dir, cache_dir, mrsl_dir, pending_dir, ssh_dir,
                     davs_dir, ftps_dir)
            
    if not renew:
        if verbose:
            print 'Creating dirs and files for new user: %s' % client_id
        try:
            os.mkdir(home_dir)
        except:
            if not force:
                raise Exception('could not create home dir: %s' % \
                                home_dir)
        for dir_path in required_dirs:
            try:
                os.mkdir(dir_path)
            except:
                if not force:
                    raise Exception('could not create required dir: %s' % \
                                    dir_path)

    else:
        if os.path.exists(htaccess_path):
            # Allow temporary write access
            os.chmod(htaccess_path, 0644)
        for dir_path in required_dirs:
            try:
                os.makedirs(dir_path)
            except Exception, exc:
                pass
            
    # Always write/update any openid symlinks

    for name in user.get('openid_names', []):
        create_alias_link(name, client_id, configuration.user_home)
    
    # Always write htaccess to catch any updates

    try:
        filehandle = open(htaccess_path, 'w')

        # Match certificate or OpenID distinguished name

        info = user.copy()

        # utf8 chars like the \xc3\xb8 are returned as \\xC3\\xB8 in Apache's
        # SSL_CLIENT_S_DN variable, thus we allow both direct dn and mangled
        # match in htaccess
        
        dn_enc = info['distinguished_name'].encode('string_escape')

        def upper_repl(match):
            """Translate hex codes to upper case form"""
            return '\\\\x' + match.group(1).upper()
        
        info['distinguished_name_enc'] = re.sub(r'\\x(..)', upper_repl, dn_enc)

        access = 'SSLRequire ('
        access += '%%{SSL_CLIENT_S_DN} eq "%(distinguished_name)s" or '
        access += '%%{SSL_CLIENT_S_DN} eq "%(distinguished_name_enc)s"'
        access += ')\n'
        for name in user.get('openid_names', []):
            for oid_provider in configuration.user_openid_providers:
                oid_url = os.path.join(oid_provider, name)
                access += 'require user %s\n' % oid_url
        access += 'Satisfy any\n'

        filehandle.write(access % info)
        filehandle.close()

        # try to prevent further user modification

        os.chmod(htaccess_path, 0444)
    except:
        if not force:
            raise Exception('could not create htaccess file: %s' % \
                            htaccess_path)

    # Always write welcome message to catch any updates

    welcome_msg = '''Welcome to %(short_title)s!

You should have received a user guide to introduce you to the basic use of the
site.

Feel free to contact us if you have any questions.

Kind regards,
The %(short_title)s admins
%(admin_email)s
''' % {'short_title': configuration.short_title,
       'admin_email': configuration.admin_email}
    configuration.logger.info("write welcome msg in %s" % welcome_path)
    try:
        filehandle = open(welcome_path, 'w')
        filehandle.write(welcome_msg)
        filehandle.close()
    except:
        if not force:
            raise Exception('could not create welcome file: %s' % \
                            welcome_path)

    # Always write/update basic settings with email to support various mail
    # requests and to avoid log errors.

    settings_dict, settings_defaults = {}, {}
    user_email = user.get('email', '')
    if user_email:
        settings_defaults['EMAIL'] = [user_email]
    settings_defaults['CREATOR'] = client_id
    settings_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        settings_dict = update_settings(client_id, configuration,
                                        settings_dict, settings_defaults)
    except:
        if not force:
            raise Exception('could not write settings file: %s' % \
                            settings_path)
        
    # Always write default profile to avoid error log entries

    profile_dict, profile_defaults = {}, {}
    profile_defaults['CREATOR'] = client_id
    profile_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        profile_dict = update_profile(client_id, configuration, profile_dict,
                                      profile_defaults)
    except:
        if not force:
            raise Exception('could not write profile file: %s' % \
                            profile_path)

    # Always write default widgets to avoid error log entries

    widgets_dict, widgets_defaults = {}, {}
    widgets_defaults['CREATOR'] = client_id
    widgets_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        widgets_dict = update_widgets(client_id, configuration, widgets_dict,
                                      widgets_defaults)
    except:
        if not force:
            raise Exception('could not create widgets file: %s' % \
                            widgets_path)
        
    # Write missing default css to avoid apache error log entries

    if not os.path.exists(css_path):
        try:
            filehandle = open(css_path, 'w')
            filehandle.write(get_default_css(css_path))
            filehandle.close()
        except:
            
            if not force:
                raise Exception('could not create custom css file: %s' % \
                                css_path)

    mark_user_modified(configuration, client_id)
    return user

def edit_user(
    client_id,
    changes,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ):
    """Edit user"""

    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    client_dir = client_id_dir(client_id)

    if verbose:
        print 'User ID: %s\n' % client_id

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

        if not user_db.has_key(client_id):
            if not force:
                raise Exception("User DB entry '%s' doesn't exist!" % \
                                client_id)

    user_dict = {}
    new_id = ''
    try:
        old_user = user_db[client_id]
        user_dict.update(old_user)
        user_dict.update(changes)
        fill_user(user_dict)
        # Force distinguished_name update
        del user_dict["distinguished_name"]
        fill_distinguished_name(user_dict)
        new_id = user_dict["distinguished_name"]
        if user_db.has_key(new_id):
            raise Exception("Edit aborted: new user already exists!")
        configuration.logger.info("Force old user renew to fix missing files")
        create_user(old_user, conf_path, db_path, force, verbose,
                    ask_renew=False, default_renew=True)
        del user_db[client_id]
        user_db[new_id] = user_dict
        save_user_db(user_db, db_path)
        if verbose:
            print 'User %s was successfully edited in user DB!'\
                  % client_id
    except Exception, err:
        import traceback
        print traceback.format_exc()
        if not force:
            raise Exception('Failed to edit %s with %s in user DB: %s'\
                            % (client_id, changes, err))

    new_client_dir = client_id_dir(new_id)
    
    # Rename user dirs recursively

    for base_dir in (configuration.user_home,
                     configuration.user_settings,
                     configuration.user_cache,
                     configuration.mrsl_files_dir,
                     configuration.resource_pending):

        old_path = os.path.join(base_dir, client_dir)
        new_path = os.path.join(base_dir, new_client_dir)
        try:
            rename_dir(old_path, new_path)
        except Exception, exc:
            if not force:
                raise Exception('could not rename %s to %s: %s' % \
                                (old_path, new_path, exc))
    if verbose:
        print 'User dirs for %s was successfully renamed!'\
                  % client_id

    # Update any OpenID symlinks

    for name in old_user.get('openid_names', []):
        remove_alias_link(name, configuration.user_home)

    for name in user_dict.get('openid_names', []):
        create_alias_link(name, new_id, configuration.user_home)
        
    # Loop through resource map and update user resource ownership
    
    res_map = get_resource_map(configuration)
    for (res_id, res) in res_map.items():
        if client_id in res[OWNERS]:
            (add_status, err) = resource_add_owners(configuration, res_id,
                                                    [new_id])
            if not add_status:
                if verbose:
                    print 'Could not add new %s owner of %s: %s' \
                          % (new_id, res_id, err)
                continue
            (del_status, err) = resource_remove_owners(configuration, res_id,
                                                       [client_id])
            if not del_status:
                if verbose:
                    print 'Could not remove old %s owner of %s: %s' \
                          % (client_id, res_id, err)
                continue
            if verbose:
                print 'Updated %s owner from %s to %s' % (res_id, client_id,
                                                          new_id)

    # Loop through vgrid map and update user owner/membership
    # By using the high level add/remove API the corresponding vgrid components
    # get properly updated, too

    vgrid_map = get_vgrid_map(configuration, recursive=False)
    for (vgrid_name, vgrid) in vgrid_map[VGRIDS].items():
        if client_id in vgrid[OWNERS]:
            (add_status, err) = vgrid_add_owners(configuration, vgrid_name,
                                                 [new_id])
            if not add_status:
                if verbose:
                    print 'Could not add new %s owner of %s: %s' \
                          % (new_id, vgrid_name, err)
                continue
            (del_status, err) = vgrid_remove_owners(configuration, vgrid_name,
                                                       [client_id])
            if not del_status:
                if verbose:
                    print 'Could not remove old %s owner of %s: %s' \
                          % (client_id, vgrid_name, err)
                continue
            if verbose:
                print 'Updated %s owner from %s to %s' % (vgrid_name,
                                                          client_id,
                                                          new_id)
        elif client_id in vgrid[MEMBERS]:
            (add_status, err) = vgrid_add_members(configuration, vgrid_name,
                                                  [new_id])
            if not add_status:
                if verbose:
                    print 'Could not add new %s member of %s: %s' \
                          % (new_id, vgrid_name, err)
                continue
            (del_status, err) = vgrid_remove_members(configuration, vgrid_name,
                                                     [client_id])
            if not del_status:
                if verbose:
                    print 'Could not remove old %s member of %s: %s' \
                          % (client_id, vgrid_name, err)
                continue
            if verbose:
                print 'Updated %s member from %s to %s' % (vgrid_name,
                                                           client_id,
                                                           new_id)

    # Loop through runtime envs and update ownership

    (re_status, re_list) = list_runtime_environments(configuration)
    if re_status:
        for re_name in re_list:
            (re_status, err) = update_runtimeenv_owner(re_name, client_id,
                                                     new_id, configuration)
            if verbose:
                if re_status:
                    print 'Updated %s owner from %s to %s' % (re_name,
                                                              client_id,
                                                              new_id)
                elif err:
                    print 'Could not change owner of %s: %s' % (re_name, err)
    else:
        if verbose:
            print 'Could not load runtime env list: %s' % re_list

    # TODO: update remaining user credentials in various locations?
    # * queued and active jobs (tricky due to races)
    # * user settings files?
    # * mrsl files?
    # * user stats?

    configuration.logger.info("Renamed user %s to %s" % (client_id, new_id))
    mark_user_modified(configuration, new_id)
    configuration.logger.info("Force new user renew to fix access")
    create_user(user_dict, conf_path, db_path, force, verbose,
                ask_renew=False, default_renew=True)
    configuration.logger.info("Force access map updates to avoid web stall")
    configuration.logger.info("Force update user map")
    refresh_user_map(configuration)
    configuration.logger.info("Force update resource map")
    refresh_resource_map(configuration)
    configuration.logger.info("Force update vgrid map")
    refresh_vgrid_map(configuration)
    return user_dict


def delete_user(
    user,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ):
    """Delete user"""

    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    fill_distinguished_name(user)
    client_id = user['distinguished_name']
    client_dir = client_id_dir(client_id)

    if verbose:
        print 'User ID: %s\n' % client_id

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

        if not user_db.has_key(client_id):
            if not force:
                raise Exception("User DB entry '%s' doesn't exist!" % \
                                client_id)

    
    try:
        user_dict = user_db.get(client_id, user)
        del user_db[client_id]
        save_user_db(user_db, db_path)
        if verbose:
            print 'User %s was successfully removed from user DB!'\
                  % client_id
    except Exception, err:
        if not force:
            raise Exception('Failed to remove %s from user DB: %s'\
                            % (client_id, err))

    # Remove any OpenID symlinks

    for name in user_dict.get('openid_names', []):
        remove_alias_link(name, configuration.user_home)

    # Remove user dirs recursively

    for base_dir in (configuration.user_home,
                     configuration.user_settings,
                     configuration.user_cache,
                     configuration.mrsl_files_dir,
                     configuration.resource_pending):

        user_path = os.path.join(base_dir, client_dir)
        try:
            delete_dir(user_path)
        except Exception, exc:
            if not force:
                raise Exception('could not remove %s: %s' % \
                                (user_path, exc))
    if verbose:
        print 'User dirs for %s was successfully removed!'\
                  % client_id
    mark_user_modified(configuration, client_id)


def expand_openid_alias(alias_id, configuration):
    """Expand openid alias to full certificate DN from symlink"""
    home_path = os.path.join(configuration.user_home, alias_id)
    if os.path.islink(home_path):
        real_home = os.path.realpath(home_path)
        client_dir = os.path.basename(real_home)
        client_id = client_dir_id(client_dir)
    else:
        client_id = alias_id
    return client_id

def get_openid_user_map(configuration):
    """Translate user DB to OpenID mapping between a verified login URL and a
    pseudo certificate DN.
    """
    id_map = {}
    db_path = os.path.join(configuration.mig_server_home, user_db_filename)
    user_map = load_user_db(db_path)
    user_alias = configuration.user_openid_alias
    for cert_id in user_map.keys():
        for oid_provider in configuration.user_openid_providers:
            full = oid_provider + client_id_dir(cert_id)
            id_map[full] = cert_id
            alias = oid_provider + client_alias(cert_id)
            id_map[alias] = cert_id
            if user_alias:
                short_id = extract_field(cert_id, user_alias)
                # Allow both raw alias field value and asciified alias
                raw = oid_provider + short_id
                enc = oid_provider + client_alias(short_id)
                id_map[raw] = cert_id
                id_map[enc] = cert_id
    return id_map
    
def get_openid_user_dn(configuration, login_url, user_check=True):
    """Translate OpenID user identified by login_url into a distinguished_name
    on the cert format.
    We first lookup the login_url suffix in the user_home to find a matching
    symlink from the simple ID to the cert-style user home and translate that
    into the corresponding distinguished name.
    If we don't succeed we try looking up the user from an optional openid
    login alias from the configuration and return the corresponding
    distinguished name. 
    As a last resort we check if login_url (suffix) is already on the cert
    distinguished name or cert dir format and return the distinguished name
    format if so.
    If the optional user_check flag is set to False the user dir check is
    skipped resulting in the openid name being returned even for users not
    yet signed up.
    """
    logger = configuration.logger
    logger.info('extracting openid dn from %s' % login_url)
    found_openid_prefix = False
    for oid_provider in configuration.user_openid_providers:
        oid_prefix = oid_provider.rstrip('/') + '/'
        if login_url.startswith(oid_prefix):
            found_openid_prefix = oid_prefix
            break
    if not found_openid_prefix:
        logger.error("openid login from invalid provider: %s" % login_url)
        return ''
    raw_login = login_url.replace(found_openid_prefix, '')
    logger.info("trying openid raw login: %s" % raw_login)
    # Lookup native user_home from openid user symlink
    link_path = os.path.join(configuration.user_home, raw_login)
    if os.path.islink(link_path):
        native_path = os.path.realpath(link_path)
        native_dir = os.path.basename(native_path)
        distinguished_name = client_dir_id(native_dir)
        logger.info('found full ID %s from %s link' % \
                                  (distinguished_name, login_url))
        return distinguished_name
    elif configuration.user_openid_alias:
        db_path = os.path.join(configuration.mig_server_home, user_db_filename)
        user_map = load_user_db(db_path)
        user_alias = configuration.user_openid_alias
        for (distinguished_name, user) in user_map.items():
            if user[user_alias] in (raw_login, client_alias(raw_login)):
                logger.info('found full ID %s from %s alias' % \
                                          (distinguished_name, login_url))
                return distinguished_name

    # Fall back to try direct DN (possibly on cert dir form)
    logger.info('fall back to direct ID %s from %s' % \
                              (raw_login, login_url))
    # Force to dir format and check if user home exists
    cert_dir = client_id_dir(raw_login)
    base_path = os.path.join(configuration.user_home, cert_dir)
    if os.path.isdir(base_path):
        distinguished_name = client_dir_id(cert_dir)
        logger.info('accepting direct user %s from %s' % \
                    (distinguished_name, login_url))
        return distinguished_name
    elif not user_check:
        logger.info('accepting raw user %s from %s' % \
                    (raw_login, login_url))
        return raw_login
    else:
        logger.error('no such openid user %s: %s' % \
                     (cert_dir, login_url))
        return ''

def get_full_user_map(configuration):
    """Load complete user map including any OpenID aliases"""
    db_path = os.path.join(configuration.mig_server_home, user_db_filename)
    user_map = load_user_db(db_path)
    oid_aliases = get_openid_user_map(configuration)
    for (alias, cert_id) in oid_aliases.items():
        user_map[alias] = user_map.get(cert_id, {})
    return user_map

def __oid_sessions_execute(configuration, query, query_vars, commit=False):
    """Execute query on Apache mod auth OpenID sessions DB from configuration
    with sql query_vars inserted.
    Use the commit flag to specify if the query should be followed by a db
    commit to save any changes.
    """
    logger = configuration.logger
    sessions = []
    if not configuration.user_openid_providers or \
           not configuration.openid_store:
        logger.error("no openid configuration")
        return (False, sessions)
    session_db_path = os.path.join(configuration.openid_store,
                                   'mod_auth_openid-users.db')
    if not os.path.exists(session_db_path):
        logger.error("could not find openid session db: %s" % session_db_path)
        return (False, sessions)
    try:
        conn = sqlite3.connect(session_db_path)
        cur = conn.cursor()
        logger.info("execute query %s with args %s on openid sessions" % \
                    (query, query_vars))
        cur.execute(query, query_vars)
        sessions = cur.fetchall()
        if commit:
            conn.commit()
        conn.close()
    except Exception, exc:
        logger.error("failed to execute query %s with args %s: %s" % \
                     (query, query_vars, exc))
        return (False, sessions)
    logger.info("got openid sessions out for %s" % sessions)
    return (True, sessions)

def find_oid_sessions(configuration, identity):
    """Find active OpenID session(s) for user with OpenID identity. Queries the
    Apache mod auth openid sqlite database directly.
    """
    query = 'SELECT * FROM sessionmanager WHERE identity=?'
    args = (identity, )
    return __oid_sessions_execute(configuration, query, args, False)

def expire_oid_sessions(configuration, identity):
    """Expire active OpenID session(s) for user with OpenID identity. Modifies
    the Apache mod auth openid sqlite database directly.
    """
    query = 'DELETE FROM sessionmanager WHERE identity=?'
    args = (identity, )
    return __oid_sessions_execute(configuration, query, args, True)
        
    
def migrate_users(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    prune_dupes=False,
    ):
    """Migrate all user data for possibly old format users to new format:

    update entry in user DB
    move user_home dir and symlink
    move mrsl_files_dir dir and symlink
    move resource_pending dir and symlink
    update USER_CERT field in all jobs
    update CREATOR field in all REs
    update owner files for all owned resources
    update owner files for all owned vgrids
    update member files for all membership vgrids
    """

    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

    targets = {}
    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = user['full_name']
        new_id = user['distinguished_name']
        if client_id == new_id:
            if verbose:
                print 'user %s is already updated to new format' % client_id
            continue
        targets[client_id] = user

    # Make sure there are no collisions in old user IDs

    latest = {}
    for (client_id, user) in targets.items():
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']        
        if new_id in user_db.keys():
            if not prune_dupes:
                if not force:
                    raise Exception('new ID %s already exists in user DB!' % \
                                    new_id)
            else:
                if verbose:
                    print 'Pruning old duplicate user %s from user DB' % \
                          client_id
                del user_db[client_id]
        elif old_id in latest.keys():
            if not prune_dupes:
                if not force:
                    raise Exception('old ID %s is not unique in user DB!' % \
                                    old_id)
            else:
                (latest_id, latest_user) = latest[old_id]
                # expire may be int, unset or None: try with fall back
                try:
                    latest_expire = int(latest_user['expire'])
                except:
                    latest_expire = 0
                try:
                    current_expire = int(user['expire'])
                except:
                    current_expire = 0
                if latest_expire < current_expire:
                    prune_id = latest_id
                    latest[old_id] = (client_id, user)
                else:
                    prune_id = client_id
                if verbose:
                    print 'Pruning duplicate user %s from user DB' % prune_id
                del user_db[prune_id]
        else:
            latest[old_id] = (client_id, user)
    save_user_db(user_db, db_path)

    # Now update the remaining users, i.e. those in latest
    for (client_id, user) in latest.values():
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']        
        if verbose:
            print 'updating user %s on old format %s to new format %s' % \
                  (client_id, old_id, new_id)

        old_name = client_id_dir(old_id)
        new_name = client_id_dir(new_id)

        # Move user dirs

        for base_dir in (configuration.user_home,
                         configuration.mrsl_files_dir,
                         configuration.resource_pending):

            try:
                old_path = os.path.join(base_dir, old_name)
                new_path = os.path.join(base_dir, new_name)
                shutil.move(old_path, new_path)
            except Exception, exc:

                # os.symlink(new_path, old_path)

                if not force:
                    raise Exception('could not move %s to %s: %s' % \
                                    (old_path, new_path, exc))

        mrsl_base = os.path.join(configuration.mrsl_files_dir, new_name)
        for mrsl_name in os.listdir(mrsl_base):
            try:
                mrsl_path = os.path.join(mrsl_base, mrsl_name)
                if not os.path.isfile(mrsl_path):
                    continue
                filter_pickled_dict(mrsl_path, {old_id: new_id})
            except Exception, exc:
                if not force:
                    raise Exception('could not update saved mrsl in %s: %s' \
                                    % (mrsl_path, exc))

        re_base = configuration.re_home
        for re_name in os.listdir(re_base):
            try:
                re_path = os.path.join(re_base, re_name)
                if not os.path.isfile(re_path):
                    continue
                filter_pickled_dict(re_path, {old_id: new_id})
            except Exception, exc:
                if not force:
                    raise Exception('could not update RE user in %s: %s' \
                                    % (re_path, exc))

        for base_dir in (configuration.resource_home,
                         configuration.vgrid_home):
            for entry_name in os.listdir(base_dir):
                for kind in ('members', 'owners'):
                    kind_path = os.path.join(base_dir, entry_name, kind)
                    if not os.path.isfile(kind_path):
                        continue
                    try:
                        filter_pickled_list(kind_path, {old_id: new_id})
                    except Exception, exc:
                        if not force:
                            raise Exception('could not update %s in %s: %s' \
                                            % (kind, kind_path, exc))

        # Finally update user DB now that file system was updated

        try:
            del user_db[client_id]
            user_db[new_id] = user
            save_user_db(user_db, db_path)
            if verbose:
                print 'User %s was successfully updated in user DB!'\
                      % client_id
        except Exception, err:
            if not force:
                raise Exception('Failed to update %s in user DB: %s' % \
                                (client_id, err))


def fix_entities(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ):
    """Update owners/members for all resources and vgrids to use new format IDs
    where possible"""

    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']        
        if verbose:
            print 'updating user %s on old format %s to new format %s' % \
                  (client_id, old_id, new_id)

        for base_dir in (configuration.resource_home,
                         configuration.vgrid_home):
            for entry_name in os.listdir(base_dir):
                for kind in ('members', 'owners'):
                    kind_path = os.path.join(base_dir, entry_name, kind)
                    if not os.path.isfile(kind_path):
                        continue
                    if sandbox_resource(entry_name):
                        continue
                    if verbose:
                        print 'updating %s in %s' % (client_id, kind_path)
                    try:
                        filter_pickled_list(kind_path, {old_id: new_id})
                    except Exception, exc:
                        if not force:
                            raise Exception('could not update %s in %s: %s' % \
                                            (kind, kind_path, exc))


def fix_userdb_keys(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ):
    """Fix any old leftover colon separated keys in user DB by replacing them
    with the new DN form from the associated user dict.
    """

    user_db = {}
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    if os.path.exists(db_path):
        try:
            user_db = load_user_db(db_path)
            if verbose:
                print 'Loaded existing user DB from: %s' % db_path
        except Exception, err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = client_id
        new_id = user['distinguished_name']        
        if old_id == new_id:
            continue
        if verbose:
            print 'updating user on old format %s to new format %s' % \
                  (old_id, new_id)

        try:
            del user_db[client_id]
            user_db[new_id] = user
            save_user_db(user_db, db_path)
            if verbose:
                print 'User %s was successfully updated in user DB!'\
                      % client_id
        except Exception, err:
            if not force:
                raise Exception('Failed to update %s in user DB: %s' % \
                                (client_id, err))


def default_search():
    """Default search filter to match all users"""

    search_filter = {}
    for (key, _) in cert_field_order:
        search_filter[key] = '*'
    return search_filter


def search_users(search_filter, conf_path, db_path, verbose=False):
    """Search for matching users"""

    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()

    try:
        user_db = load_user_db(db_path)
        if verbose:
            print 'Loaded existing user DB from: %s' % db_path
    except Exception, err:
        print 'Failed to load user DB: %s' % err
        return []

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


def user_password_reminder(user_id, targets, conf_path, db_path,
                           verbose=False):
    """Find notification addresses for user_id and targets"""

    errors = []
    if conf_path:
        configuration = Configuration(conf_path)
    else:
        configuration = get_configuration_object()
    try:
        user_db = load_user_db(db_path)
        if verbose:
            print 'Loaded existing user DB from: %s' % db_path
    except Exception, err:
        print 'Failed to load user DB: %s' % err
        return []

    if not user_db.has_key(user_id):
        errors.append('No such user: %s' % user_id)
    else:
        password = user_db[user_id].get('password', '')
        password = base64.b64decode(password)
        addresses = dict(zip(configuration.notify_protocols,
                             [[] for _ in configuration.notify_protocols]))
        addresses['email'] = []
        for (proto, address_list) in targets.items():
            if not proto in configuration.notify_protocols + ['email']:
                errors.append('unsupported protocol: %s' % proto)
                continue
            for address in address_list:
                if proto == 'email' and address == keyword_auto:
                    address = user_db[user_id].get('email', '')
                    if not address:
                        errors.append('missing email address in db!')
                        continue
                addresses[proto].append(address)
    return (configuration, password, addresses, errors)


def get_default_mrsl(template_path):
    """Return the default mRSL template from template_path"""

    try:
        template_fd = open(template_path, 'rb')
        default_mrsl = template_fd.read()
        template_fd.close()
    except:

        # Use default hello grid example

        default_mrsl = \
            """::EXECUTE::
echo 'hello grid!'
echo '...each line here is executed'

::NOTIFY::
email: SETTINGS
jabber: SETTINGS

::INPUTFILES::

::OUTPUTFILES::

::EXECUTABLES::

::MEMORY::
1

::DISK::
1

::CPUTIME::
30

::RUNTIMEENVIRONMENT::

"""
    return default_mrsl


def get_default_css(template_path):
    """Return the default css template template_path"""

    try:
        template_fd = open(template_path, 'rb')
        default_css = template_fd.read()
        template_fd.close()
    except:

        # Use default style - i.e. do not override anything

        default_css = '/* No changes - use default */'

    return default_css

def get_authkeys(authkeys_path):
    """Return the authorized keys from authkeys_path"""

    try:
        authkeys_fd = open(authkeys_path, 'rb')
        authorized_keys = authkeys_fd.readlines()
        authkeys_fd.close()
        # Remove extra space and skip blank lines
        authorized_keys = [i.strip() for i in authorized_keys if i.strip()]
    except:
        authorized_keys = []
    return authorized_keys

def get_authpasswords(authpasswords_path):
    """Return the non-empty authorized passwords from authpasswords_path"""

    try:
        authpasswords_fd = open(authpasswords_path, 'rb')
        authorized_passwords = authpasswords_fd.readlines()
        authpasswords_fd.close()
        # Remove extra space and skip blank lines
        authorized_passwords = [i.strip() for i in authorized_passwords \
                                if i.strip()]
    except:
        authorized_passwords = []
    return authorized_passwords

def generate_password_hash(password):
    """Return a hash data string for saving provided password. We use PBKDF2 to
    help with the hash comparison later and store the data in a form close to
    the one recommended there:
    (algorithm$hashfunction$salt$costfactor$hash).
    """
    try:
        return make_hash(password)
    except Exception, exc:
        print "ERROR: in generate_password_hash: %s" % exc
        return password

def check_password_hash(password, stored_hash, hash_cache=None):
    """Return a boolean indicating if offered password matches stored_hash
    information. We use PBKDF2 to help with the hash comparison and store the
    data in a form close to the one recommended there:
    (algorithm$hashfunction$salt$costfactor$hash).
    
    More information about sane password handling is available at:
    https://exyr.org/2011/hashing-passwords/

    The optional hash_cache dictionary argument can be used to cache lookups
    and speed up repeated use.
    """
    try:
        return check_hash(password, stored_hash, hash_cache)
    except Exception, exc:
        print "ERROR: in check_password_hash: %s" % exc
        return False

def generate_password_digest(realm, username, password, salt):
    """Return a digest data string for saving provided password"""
    try:
        return make_digest(realm, username, password, salt)
    except Exception, exc:
        print "ERROR: in generate_password_digest: %s" % exc
        return password

def check_password_digest(realm, username, password, stored_digest, salt,
                          digest_cache=None):
    """Return a boolean indicating if offered password matches stored_digest
    information.

    The optional digest_cache dictionary argument can be used to cache lookups
    and speed up repeated use.
    """
    try:
        return check_digest(realm, username, password, stored_digest, salt,
                            digest_cache)
    except Exception, exc:
        print "ERROR: in check_password_digest: %s" % exc
        return False
