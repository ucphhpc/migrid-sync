#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# useradm - user administration functions
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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
import os
import sys
import shutil
import fnmatch
import datetime

from shared.base import client_id_dir, sandbox_resource
from shared.conf import get_configuration_object
from shared.configuration import Configuration
from shared.defaults import keyword_auto, ssh_conf_dir, htaccess_filename, \
     settings_filename, profile_filename, default_css_filename, \
     widgets_filename, ssh_conf_dir, authkeys_filename, authpasswords_filename
from shared.fileio import filter_pickled_list, filter_pickled_dict
from shared.modified import mark_user_modified
from shared.refunctions import list_runtime_environments, update_runtimeenv_owner
from shared.pwhash import make_hash, check_hash
from shared.resource import resource_add_owners, resource_remove_owners
from shared.serial import load, dump
from shared.settings import update_settings, update_profile, update_widgets
from shared.vgrid import vgrid_add_owners, vgrid_remove_owners, \
     vgrid_add_members, vgrid_remove_members
from shared.vgridaccess import get_resource_map, get_vgrid_map, VGRIDS, \
     OWNERS, MEMBERS

db_name = 'MiG-users.db'
ssh_authkeys = os.path.join(ssh_conf_dir, authkeys_filename)
ssh_authpasswords = os.path.join(ssh_conf_dir, authpasswords_filename)
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
    db_path = os.path.join(app_dir, db_name)
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

        if user_db.has_key(client_id):
            if ask_renew:
                print 'User DB entry for "%s" already exists' % client_id
                renew_answer = raw_input('Renew existing entry? [Y/n] ')
                renew = not renew_answer.lower().startswith('n')
            else:
                renew = default_renew
            if renew:
                if user_db[client_id]['password'] != user['password']:
                    if verbose:
                        print 'Renewal request supplied a different password: '
                        print 'Please re-request with the original password '
                        print 'to assure authenticity!'
                    raise Exception(
                        'Cannot renew certificate with a new password')
                if verbose:
                    print 'Renewing existing user'
            elif not force:
                if verbose:
                    print 'Nothing more to do for existing user %s' % client_id
                raise Exception('Nothing more to do for existing user %s' % \
                                client_id)

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
    htaccess_path = os.path.join(home_dir, htaccess_filename)
    settings_path = os.path.join(settings_dir, settings_filename)
    profile_path = os.path.join(settings_dir, profile_filename)
    widgets_path = os.path.join(settings_dir, widgets_filename)
    css_path = os.path.join(home_dir, default_css_filename)
    required_dirs = (settings_dir, cache_dir, mrsl_dir, pending_dir, ssh_dir)
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
            
    # Always write htaccess to catch any updates

    try:
        filehandle = open(htaccess_path, 'w')

        # Match all known fields or require the client to come from a SID path.
        #
        # IMPORTANT:
        # The fall back to explicitly allow no client certificate is necessary
        # with apache2, where symlink target directories are checked against all
        # Directory directives and thus preventing SID links to user homes from
        # being used without a certificate, if htaccess doesn't explicitly allow
        # it.
        # As this is the required SID behaviour used to hand in job results, the
        # fallback is needed to avoid breaking all job handling.
        # With apache 1.x the symlink was not further checked and thus the
        # htaccess requirement was simply ignored from those SID paths.
        # It is *critical* that all other access to user homes are secured with
        # SID or cert requirement to prevent unauthorized access.

        access = 'SSLRequire ('
        access += '%%{SSL_CLIENT_S_DN} eq "%(distinguished_name)s"'
        access += ')\n'

        filehandle.write(access % user)
        filehandle.close()

        # try to prevent further user modification

        os.chmod(htaccess_path, 0444)
    except:
        if not force:
            raise Exception('could not create htaccess file: %s' % \
                            htaccess_path)

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
        configuration.logger.info("Force old user renew to fix missing files")
        create_user(old_user, conf_path, db_path, force, verbose,
                    ask_renew=False, default_renew=True)
        del user_db[client_id]
        user_dict = old_user
        user_dict.update(changes)
        fill_user(user_dict)
        # Force distinguished_name update
        del user_dict["distinguished_name"]
        fill_distinguished_name(user_dict)
        new_id = user_dict["distinguished_name"]
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

    vgrid_map = get_vgrid_map(configuration)
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
                if not re_status:
                    print 'Could not change owner of %s: %s' % (re_name, err)
                else:
                    print 'Updated %s owner from %s to %s' % (re_name,
                                                              client_id,
                                                              new_id)
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
        del user_db[client_id]
        save_user_db(user_db, db_path)
        if verbose:
            print 'User %s was successfully removed from user DB!'\
                  % client_id
    except Exception, err:
        if not force:
            raise Exception('Failed to remove %s from user DB: %s'\
                            % (client_id, err))

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

def get_ssh_authkeys(authkeys_path):
    """Return the ssh authorized keys from authkeys_path"""

    try:
        authkeys_fd = open(authkeys_path, 'rb')
        authorized_keys = authkeys_fd.readlines()
        authkeys_fd.close()
        # Remove extra space and skip blank lines
        authorized_keys = [i.strip() for i in authorized_keys if i.strip()]
    except:
        authorized_keys = []
    return authorized_keys

def get_ssh_authpasswords(authpasswords_path):
    """Return the non-empty ssh authorized passwords from authpasswords_path"""

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

def check_password_hash(password, stored_hash):
    """Return a boolean indicating if offered password matches stored_hash
    information. We use PBKDF2 to help with the hash comparison and store the
    data in a form close to the one recommended there:
    (algorithm$hashfunction$salt$costfactor$hash).
    
    More information about sane password handling is available at:
    https://exyr.org/2011/hashing-passwords/
    """
    try:
        return check_hash(password, stored_hash)
    except Exception, exc:
        print "ERROR: in check_password_hash: %s" % exc
        return False
