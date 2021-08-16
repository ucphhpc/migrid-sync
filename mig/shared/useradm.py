#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# useradm - user administration functions
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from __future__ import print_function
from __future__ import absolute_import

from email.utils import parseaddr
import datetime
import fnmatch
import os
import re
import shutil
import sqlite3
import sys
import time

from mig.shared.accountreq import get_accepted_peers
from mig.shared.accountstate import update_account_expire_cache, \
    update_account_status_cache
from mig.shared.base import client_id_dir, client_dir_id, client_alias, \
    sandbox_resource, fill_user, fill_distinguished_name, extract_field, \
    is_gdp_user
from mig.shared.conf import get_configuration_object
from mig.shared.configuration import Configuration
from mig.shared.defaults import user_db_filename, keyword_auto, ssh_conf_dir, \
    davs_conf_dir, ftps_conf_dir, htaccess_filename, welcome_filename, \
    settings_filename, profile_filename, default_css_filename, \
    widgets_filename, seafile_ro_dirname, authkeys_filename, \
    authpasswords_filename, authdigests_filename, cert_field_order, \
    twofactor_filename
from mig.shared.fileio import filter_pickled_list, filter_pickled_dict, \
    make_symlink, delete_symlink
from mig.shared.modified import mark_user_modified
from mig.shared.refunctions import list_runtime_environments, \
    update_runtimeenv_owner
from mig.shared.pwhash import make_hash, check_hash, make_digest, check_digest, \
    make_scramble, check_scramble, unscramble_password, unscramble_digest, \
    assure_password_strength
from mig.shared.resource import resource_add_owners, resource_remove_owners
from mig.shared.serial import load, dump
from mig.shared.settings import update_settings, update_profile, update_widgets
from mig.shared.sharelinks import load_share_links, update_share_link, \
    get_share_link, mode_chars_map
from mig.shared.twofactorkeywords import get_twofactor_specs
from mig.shared.userdb import lock_user_db, unlock_user_db, load_user_db, \
    load_user_dict, save_user_db
from mig.shared.validstring import possible_user_id, valid_email_addresses
from mig.shared.vgrid import vgrid_add_owners, vgrid_remove_owners, \
    vgrid_add_members, vgrid_remove_members, in_vgrid_share, \
    vgrid_sharelinks, vgrid_add_sharelinks
from mig.shared.vgridaccess import get_resource_map, get_vgrid_map, \
    force_update_user_map, force_update_resource_map, force_update_vgrid_map, \
    VGRIDS, OWNERS, MEMBERS

ssh_authkeys = os.path.join(ssh_conf_dir, authkeys_filename)
ssh_authpasswords = os.path.join(ssh_conf_dir, authpasswords_filename)
ssh_authdigests = os.path.join(ssh_conf_dir, authdigests_filename)
davs_authkeys = os.path.join(davs_conf_dir, authkeys_filename)
davs_authpasswords = os.path.join(davs_conf_dir, authpasswords_filename)
davs_authdigests = os.path.join(davs_conf_dir, authdigests_filename)
ftps_authkeys = os.path.join(ftps_conf_dir, authkeys_filename)
ftps_authpasswords = os.path.join(ftps_conf_dir, authpasswords_filename)
ftps_authdigests = os.path.join(ftps_conf_dir, authdigests_filename)
# We lookup https/openid logins in users DB
https_authkeys = ''
https_authpasswords = user_db_filename
https_authdigests = user_db_filename


def init_user_adm():
    """Shared init function for all user administration scripts"""

    args = sys.argv[1:]
    app_dir = os.path.dirname(sys.argv[0])
    if not app_dir:
        app_dir = '.'
    db_path = os.path.join(app_dir, user_db_filename)
    return (args, app_dir, db_path)


def delete_dir(path, verbose=False):
    """Recursively remove path:
    first remove all files and subdirs, then remove dir tree.
    """

    if verbose:
        print('removing: %s' % path)
    shutil.rmtree(path)


def rename_dir(src, dst, verbose=False):
    """Rename src to dst"""

    if verbose:
        print('renaming: %s -> %s ' % (src, dst))
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
    except Exception as err:
        raise Exception('could not symlink alias %s : %s' % (link_path, err))
    return True


def create_seafile_mount_link(client_id, configuration):
    """Create link to fuse mounted seafile library for client_id"""
    client_dir = client_id_dir(client_id)
    mount_link = os.path.join(configuration.user_home,
                              client_dir, seafile_ro_dirname)
    user_alias = configuration.user_seafile_alias
    short_id = extract_field(client_id, user_alias)
    seafile_home = os.path.join(configuration.seafile_mount, short_id)
    _logger = configuration.logger
    if os.path.isdir(seafile_home) and not os.path.islink(mount_link):
        try:
            os.symlink(seafile_home, mount_link)
        except Exception as exc:
            _logger.error("failed to link seafile mount %s to %s: %s"
                          % (seafile_home, mount_link, exc))
            raise


def remove_seafile_mount_link(client_id, configuration):
    """Remove link to fuse mounted seafile library for client_id"""
    client_dir = client_id_dir(client_id)
    mount_link = os.path.join(configuration.user_home,
                              client_dir, seafile_ro_dirname)
    _logger = configuration.logger
    if os.path.islink(mount_link):
        try:
            os.remove(mount_link)
        except Exception as exc:
            _logger.error("failed to unlink seafile mount from %s: %s"
                          % (mount_link, exc))
            raise


def create_user(
    user,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    ask_renew=True,
    default_renew=False,
    do_lock=True,
    verify_peer=None,
):
    """Add user"""
    flock = None
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):

            # has been checked for accessibility above...

            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()

    _logger = configuration.logger
    fill_distinguished_name(user)
    client_id = user['distinguished_name']
    client_dir = client_id_dir(client_id)

    renew = default_renew
    # Requested with existing valid certificate?
    # Used in order to authorize password change
    if 'authorized' in user:
        authorized = user['authorized']
        # Always remove any authorized fields before DB insert
        del user['authorized']
    else:
        authorized = False

    accepted_peer_list = []
    verify_pattern = verify_peer
    if verify_peer == keyword_auto:
        _logger.debug('auto-detect peers for: %s' % client_id)
        peer_email_list = []
        # extract email of vouchee from comment if possible
        comment = user.get('comment', '')
        all_matches = valid_email_addresses(configuration, comment)
        for i in all_matches:
            peer_email = "%s" % i
            if not possible_user_id(configuration, peer_email):
                _logger.warning('skip invalid peer: %s' % peer_email)
                continue
            peer_email_list.append(peer_email)

        if not peer_email_list:
            _logger.error("requested peer auto-detect failed for %s" %
                          client_id)
            raise Exception("Failed auto-detect peers in request for %s: %r"
                            % (client_id, comment))
        verify_pattern = '|'.join(['.*emailAddress=%s' %
                                   i for i in peer_email_list])

    if verify_pattern:
        _logger.debug('verify peers for %s with %s' % (client_id,
                                                       verify_pattern))
        search_filter = default_search()
        search_filter['distinguished_name'] = verify_pattern
        if verify_peer == keyword_auto or verify_pattern.find('|') != -1:
            regex_patterns = ['distinguished_name']
        else:
            regex_patterns = []
        (_, hits) = search_users(search_filter, conf_path, db_path,
                                 verbose, regex_match=regex_patterns)
        peer_notes = []
        if not hits:
            peer_notes.append("no match for peers")
        for (sponsor_id, sponsor_dict) in hits:
            if configuration.site_enable_gdp and is_gdp_user(configuration, sponsor_id):
                _logger.debug(
                    "skip gdp project user %s as sponsor" % sponsor_id)
                continue
            _logger.debug("check %s in peers for %s" % (client_id, sponsor_id))
            if client_id == sponsor_id:
                warn_msg = "users cannot vouch for themselves: %s for %s" % \
                           (client_id, sponsor_id)
                _logger.warning(warn_msg)
                continue
            sponsor_expire = sponsor_dict.get('expire', -1)
            if sponsor_expire >= 0 and time.time() > sponsor_expire:
                warn_msg = "expire %s prevents %s as peer for %s" % \
                           (sponsor_expire, sponsor_id, client_id)
                _logger.warning(warn_msg)
                peer_notes.append(warn_msg)
                continue
            sponsor_status = sponsor_dict.get('status', 'active')
            if sponsor_status not in ['active', 'temporal']:
                warn_msg = "status %s prevents %s as peer for %s" % \
                           (sponsor_status, sponsor_id, client_id)
                _logger.warning(warn_msg)
                peer_notes.append(warn_msg)
                continue
            accepted_peers = get_accepted_peers(configuration, sponsor_id)
            peer_entry = accepted_peers.get(client_id, None)
            if not peer_entry:
                _logger.warning("could not validate %s as peer for %s" %
                                (sponsor_id, client_id))
                continue
            # NOTE: adjust expire date to mean end of that day
            peer_expire = datetime.datetime.strptime(
                peer_entry.get('expire', 0), '%Y-%m-%d') + \
                datetime.timedelta(days=1, microseconds=-1)
            client_expire = datetime.datetime.fromtimestamp(user['expire'])
            if peer_expire < client_expire:
                warn_msg = "expire %s vs %s prevents %s as peer for %s" % \
                           (peer_expire, client_expire, sponsor_id, client_id)
                _logger.warning(warn_msg)
                peer_notes.append(warn_msg)
                continue
            _logger.debug("validated %s accepts %s as peer" % (sponsor_id,
                                                               client_id))
            accepted_peer_list.append(sponsor_id)
        if not accepted_peer_list:
            _logger.error("requested peer validation with %r for %s failed" %
                          (verify_pattern, client_id))
            raise Exception("Failed verify peers for %s using pattern %r: %s" %
                            (client_id, verify_pattern, '\n'.join(peer_notes)))

        # Save peers in user DB for updates etc. but ignore peer search pattern
        user['peers'] = accepted_peer_list
        if user.get('peer_pattern', None):
            del user['peer_pattern']
        _logger.info("accept create user %s with peer validator(s): %s" %
                     (client_id, ', '.join(accepted_peer_list)))

    else:
        _logger.info('Skip peer verification for %s' % client_id)

    if verbose:
        print('User ID: %s\n' % client_id)

    if do_lock:
        flock = lock_user_db(db_path)

    if not os.path.exists(db_path):
        print('User DB in %s does not exist - okay if first user' % db_path)
        create_answer = raw_input('Create new user DB? [Y/n] ')
        if create_answer.lower().startswith('n'):
            if do_lock:
                unlock_user_db(flock)
            raise Exception("Missing user DB: '%s'" % db_path)
        # Dump empty DB
        save_user_db(user_db, db_path, do_lock=False)

    try:
        user_db = load_user_db(db_path, do_lock=False)
        if verbose:
            print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        if not force:
            if do_lock:
                unlock_user_db(flock)
            raise Exception("Failed to load user DB: '%s'" % db_path)

    # Prevent alias clashes by preventing addition of new users with same
    # alias. We only allow renew of existing user.

    # TODO: If check is required for GDP then use get_short_id instead of
    #       user[configuration.user_openid_alias]
    #       val[configuration.user_openid_alias]

    if not configuration.site_enable_gdp and \
            configuration.user_openid_providers and \
            configuration.user_openid_alias:
        user_aliases = dict([(key, val[configuration.user_openid_alias])
                             for (key, val) in user_db.items()])
        alias = user[configuration.user_openid_alias]
        if alias in user_aliases.values() and \
                user_aliases.get(client_id, None) != alias:
            if do_lock:
                unlock_user_db(flock)
            if verbose:
                print('Attempting create_user with conflicting alias %s'
                      % alias)
            raise Exception(
                'A conflicting user with alias %s already exists' % alias)

    if client_id not in user_db:
        default_ui = configuration.new_user_default_ui
        user['created'] = time.time()
    else:
        default_ui = None
        account_status = user_db[client_id].get('status', 'active')
        # Only allow renew if account is active or if temporal with peer list
        if account_status == 'active':
            _logger.debug("proceed with %s account" % account_status)
        elif account_status == 'temporal' and accepted_peer_list:
            _logger.debug("proceed with %s account and accepted peers %s" %
                          (account_status, accepted_peer_list))
        else:
            raise Exception('refusing to renew %s account! (%s)' %
                            (account_status, accepted_peer_list))
        if ask_renew:
            print('User DB entry for "%s" already exists' % client_id)
            renew_answer = raw_input('Renew existing entry? [Y/n] ')
            renew = not renew_answer.lower().startswith('n')
        else:
            renew = default_renew
        if renew:
            user['old_password'] = user_db[client_id]['password']
            # MiG OpenID users without password recovery have empty
            # password value and on renew we then leave any saved cert
            # password alone.
            # External OpenID users do not provide a password so again any
            # existing password should be left alone on renewal.
            if not user['password']:
                user['password'] = user['old_password']
            password_changed = (user['old_password'] != user['password'])
            if password_changed:
                if authorized:
                    print("User authorized password update")
                elif not user['old_password']:
                    print("User requested password - previously disabled")
                else:
                    print("""User '%s' exists with *different* password!
Generally users with an existing account should sign up again through Xgi-bin
using their existing credentials to authorize password changes.""" % client_id)
                    accept_answer = raw_input(
                        'Accept password change? [y/N] ')
                    authorized = accept_answer.lower().startswith('y')
                    if not authorized:
                        if do_lock:
                            unlock_user_db(flock)
                        if verbose:
                            print("""Renewal request supplied a different
password and you didn't accept change anyway - nothing more to do""")
                        err = """Cannot renew account using a new password!
Please tell user to use the original password or request renewal using Xgi-bin
with certificate or OpenID authentication to authorize the change."""
                        raise Exception(err)
            if verbose:
                print('Renewing existing user')
            # Take old user details and override fields with new ones but
            # ONLY if actually set. This leaves any openid_names and roles
            # alone on cert re-signup after openid signup.
            updated_user = user_db[client_id]
            for (key, val) in user.items():
                if key in ('auth', 'openid_names') and \
                        not isinstance(val, basestring) and \
                        isinstance(val, list):
                    val_list = updated_user.get(key, [])
                    val_list += [i for i in val if not i in val_list]
                    updated_user[key] = val_list
                elif val:
                    updated_user[key] = val
            user.clear()
            user.update(updated_user)
            user['renewed'] = time.time()
        elif not force:
            if do_lock:
                unlock_user_db(flock)
            if verbose:
                print('Nothing more to do for existing user %s' % client_id)
            raise Exception('Nothing more to do for existing user %s'
                            % client_id)

    # Add optional OpenID usernames to user (pickle may include some already)

    openid_names = user.get('openid_names', [])
    short_id = user.get('short_id', '')
    # For cert users short_id is the full DN so we should ignore then
    if short_id and short_id != client_id and short_id.find(' ') == -1 and \
            not short_id in openid_names:
        openid_names.append(short_id)
    add_names = []

    # TODO: If implicit append of GDP openid alias' are required then use
    #       get_short_id instead of user[configuration.user_openid_alias]

    if not configuration.site_enable_gdp and \
            configuration.user_openid_providers and \
            configuration.user_openid_alias:
        add_names.append(user[configuration.user_openid_alias])
    user['openid_names'] = list(dict([(name, 0) for name in add_names +
                                      openid_names]))

    try:
        user_db[client_id] = user
        save_user_db(user_db, db_path, do_lock=False)
        if verbose:
            print('User %s was successfully added/updated in user DB!'
                  % client_id)
    except Exception as err:
        if do_lock:
            unlock_user_db(flock)
        print(err)
        if not force:
            raise Exception('Failed to add %s to user DB: %s'
                            % (client_id, err))
    if do_lock:
        unlock_user_db(flock)

    # Mark user updated for all logins
    update_account_expire_cache(configuration, user)
    update_account_status_cache(configuration, user)

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

    # Make sure we set permissions tight enough for e.g. ssh auth keys to work
    os.umask(0o22)

    if not renew:
        if verbose:
            print('Creating dirs and files for new user: %s' % client_id)
        try:
            os.mkdir(home_dir)
        except:
            if not force:
                raise Exception('could not create home dir: %s'
                                % home_dir)
        for dir_path in required_dirs:
            try:
                os.mkdir(dir_path)
            except:
                if not force:
                    raise Exception('could not create required dir: %s'
                                    % dir_path)

    else:
        if os.path.exists(htaccess_path):
            # Allow temporary write access
            os.chmod(htaccess_path, 0o644)
        for dir_path in required_dirs:
            try:
                os.makedirs(dir_path)
            except Exception as exc:
                pass

    # Always write/update any openid symlinks

    for name in user.get('openid_names', []):
        # short_id is client_id for cert users - skip them
        if name == client_id or name.find(' ') != -1:
            continue
        create_alias_link(name, client_id, configuration.user_home)

    # Always write htaccess to catch any updates

    try:
        filehandle = open(htaccess_path, 'w')

        # Match certificate or OpenID distinguished name

        info = user.copy()

        # utf8 chars like the \xc3\xb8 are returned as \\xC3\\xB8 in Apache's
        # SSL_CLIENT_S_DN variable, thus we allow both direct dn and mangled
        # match in htaccess

        dn_plain = info['distinguished_name']
        dn_enc = dn_plain.encode('string_escape')

        def upper_repl(match):
            """Translate hex codes to upper case form"""
            return '\\\\x' + match.group(1).upper()

        info['distinguished_name_enc'] = re.sub(r'\\x(..)', upper_repl, dn_enc)

        # TODO: find out a way to avoid the use of the legacy 'Satisfy any'
        #       Attempts so far have either broken tracker access or opened up
        #       for illegal access to various files. We would like to disable
        #       the access_compat module it needs sometime in the future.

        access = '''# Access control for directly served requests.
# If user requests access through cert_redirect or explicit ID path we must
# make sure that either of the following conditions hold:
# a) access is through a cert address and user provided a matching certificate
# b) access is through an OpenID address with a matching user alias

# NOTE: this complex check and the Satisfy any clause is required along with
# server enablement of the access_compat module!
# We should eventually switch to pure "require user ID" and disable the use of
# access_compat but so far it either breaks access or allows illegal access.
SSLRequire (%%{SSL_CLIENT_S_DN} eq "%(distinguished_name)s")
'''
        if dn_enc != dn_plain:
            access += '''
SSLRequire (%%{SSL_CLIENT_S_DN} eq "%(distinguished_name_enc)s")
'''
        access += '''
# We prepare for future require user format with cert here in the hope that
# we can eventually disable the above SSLRequire check and access_compat.
require user "%(distinguished_name)s"
'''
        if dn_enc != dn_plain:
            access += '''require user "%(distinguished_name_enc)s"
'''

        # For OpenID 2.0 and OpenID Connect user IDs
        for name in user.get('openid_names', []):
            for oid_provider in configuration.user_openid_providers:
                oid_url = os.path.join(oid_provider, name)
                access += 'require user "%s"\n' % oid_url
                access += 'require user "%s"\n' % name

        access += '''
# IMPORTANT: do NOT set "all granted" for 2.3+ as it completely removes all
# login requirements!
# In apache 2.3+ RequireAny is implicit for the above "require user" lines. I.e.
# at least one of them must be fullfilled for access. With earlier versions we
# need to  use "Satisfy any" to get the same default behaviour.
<IfVersion <= 2.2>
    Satisfy any
</IfVersion>
# Similarly use Satisfy any in newer versions with the access_compat module.
<IfVersion > 2.2>
    <IfModule mod_access_compat.c>
        Satisfy any
    </IfModule>
</IfVersion>
'''

        filehandle.write(access % info)
        filehandle.close()

        # try to prevent further user modification

        os.chmod(htaccess_path, 0o444)
    except:
        if not force:
            raise Exception('could not create htaccess file: %s'
                            % htaccess_path)

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
    _logger.info("write welcome msg in %s" % welcome_path)
    try:
        filehandle = open(welcome_path, 'w')
        filehandle.write(welcome_msg)
        filehandle.close()
    except:
        _logger.error("could not write %s" % welcome_path)
        if not force:
            raise Exception('could not create welcome file: %s'
                            % welcome_path)

    # Always write/update basic settings with email to support various mail
    # requests and to avoid log errors.

    settings_dict, settings_defaults = {}, {}
    user_email = user.get('email', '')
    if user_email:
        settings_defaults['EMAIL'] = [user_email]
    if default_ui:
        settings_defaults['USER_INTERFACE'] = default_ui
    settings_defaults['CREATOR'] = client_id
    settings_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        settings_dict = update_settings(client_id, configuration,
                                        settings_dict, settings_defaults)
    except:
        _logger.error("could not write %s" % settings_path)
        if not force:
            raise Exception('could not write settings file: %s'
                            % settings_path)

    # Always write default profile to avoid error log entries

    profile_dict, profile_defaults = {}, {}
    profile_defaults['CREATOR'] = client_id
    profile_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        profile_dict = update_profile(client_id, configuration, profile_dict,
                                      profile_defaults)
    except:
        _logger.error("could not write %s" % profile_path)
        if not force:
            raise Exception('could not write profile file: %s'
                            % profile_path)

    # Always write default widgets to avoid error log entries

    widgets_dict, widgets_defaults = {}, {}
    widgets_defaults['CREATOR'] = client_id
    widgets_defaults['CREATED_TIMESTAMP'] = datetime.datetime.now()
    try:
        widgets_dict = update_widgets(client_id, configuration, widgets_dict,
                                      widgets_defaults)
    except:
        _logger.error("could not write %s" % widgets_path)
        if not force:
            raise Exception('could not create widgets file: %s'
                            % widgets_path)

    # Write missing default css to avoid apache error log entries

    if not os.path.exists(css_path):
        try:
            filehandle = open(css_path, 'w')
            filehandle.write(get_default_css(css_path))
            filehandle.close()
        except:
            _logger.error("could not write %s" % css_path)
            if not force:
                raise Exception('could not create custom css file: %s'
                                % css_path)

    _logger.info("created/renewed user %s" % client_id)
    mark_user_modified(configuration, client_id)
    return user


def fix_user_sharelinks(old_id, client_id, conf_path, db_path,
                        verbose=False, do_lock=True):
    """Update sharelinks left-over from legacy version of edit_user"""
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger

    if verbose:
        print('User ID: %s\n' % client_id)

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=do_lock)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            raise Exception('Failed to load user DB: %s' % err)

    if client_id not in user_db:
        raise Exception("User DB entry '%s' doesn't exist!" % client_id)

    # Loop through moved sharelinks map pickle and update fs paths

    (load_status, sharelinks) = load_share_links(configuration, client_id)
    if verbose:
        print('Update %d sharelinks' % len(sharelinks))
    if load_status:
        for (share_id, share_dict) in sharelinks.items():
            # Update owner and use generic update helper to replace symlink
            share_dict['owner'] = client_id
            (mod_status, err) = update_share_link(share_dict, client_id,
                                                  configuration, sharelinks)
            if verbose:
                if mod_status:
                    print('Updated sharelink %s from %s to %s' % (share_id,
                                                                  old_id,
                                                                  client_id))
                elif err:
                    print('Could not update owner of %s: %s' % (share_id, err))
    else:
        if verbose:
            print('Could not load sharelinks: %s' % sharelinks)


def fix_vgrid_sharelinks(conf_path, db_path, verbose=False, force=False):
    """Update vgrid sharelinks to include any missing ones due to the bug fixed
    in rev4168+4169.
    """
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger

    # Loop through sharelinks and check that the vgrid ones are registered

    for mode_sub in mode_chars_map:
        sharelink_base = os.path.join(configuration.sharelink_home, mode_sub)
        for share_id in os.listdir(sharelink_base):
            if share_id.startswith('.'):
                # skip dot dirs
                continue
            sharelink_path = os.path.join(sharelink_base, share_id)
            sharelink_realpath = os.path.realpath(sharelink_path)
            vgrid_name = in_vgrid_share(configuration, sharelink_realpath)
            if not vgrid_name:
                continue

            (load_status, links_list) = vgrid_sharelinks(vgrid_name,
                                                         configuration,
                                                         recursive=False)
            if load_status:
                links_dict = dict([(i['share_id'], i) for i in links_list])
            else:
                links_dict = {}

            if not share_id in links_dict:
                user_path = os.readlink(sharelink_path)
                if verbose:
                    print('Handle missing vgrid %s sharelink %s to %s (%s)' %
                          (vgrid_name, share_id, sharelink_realpath, user_path))
                client_dir = user_path.replace(configuration.user_home, '')
                client_dir = client_dir.split(os.sep)[0]
                client_id = client_dir_id(client_dir)
                (get_status, share_dict) = get_share_link(share_id, client_id,
                                                          configuration)
                if not get_status:
                    print('Error loading sharelink dict for %s of %s' %
                          (share_id, client_id))
                    continue

                print('Add missing sharelink %s to vgrid %s' % (share_id,
                                                                vgrid_name))

                (add_status, add_msg) = vgrid_add_sharelinks(
                    configuration, vgrid_name, [share_dict])
                if not add_status:
                    print('ERROR: add missing sharelink failed: %s' % add_msg)


def edit_user(
    client_id,
    changes,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    meta_only=False,
    do_lock=True,
):
    """Edit user"""

    flock = None
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger

    client_dir = client_id_dir(client_id)

    if verbose:
        print('User ID: %s\n' % client_id)

    if do_lock:
        flock = lock_user_db(db_path)

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=False)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to load user DB: %s' % err)

        if client_id not in user_db:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception("User DB entry '%s' doesn't exist!"
                                % client_id)

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
        if not meta_only:
            if new_id in user_db:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception("Edit aborted: new user already exists!")
            _logger.info("Force old user renew to fix missing files")
            create_user(old_user, conf_path, db_path, force, verbose,
                        ask_renew=False, default_renew=True, do_lock=False)
            del user_db[client_id]
        elif new_id != client_id:
            if do_lock:
                unlock_user_db(flock)
            raise Exception("Edit aborted: illegal meta_only ID change! %s %s"
                            % (client_id, new_id))
        else:
            _logger.info("Only updating metadata for %s: %s" % (client_id,
                                                                changes))

        user_db[new_id] = user_dict
        save_user_db(user_db, db_path, do_lock=False)
        if verbose:
            print('User %s was successfully edited in user DB!'
                  % client_id)
    except Exception as err:
        import traceback
        print(traceback.format_exc())
        if not force:
            if do_lock:
                unlock_user_db(flock)
            raise Exception('Failed to edit %s with %s in user DB: %s'
                            % (client_id, changes, err))

    if do_lock:
        unlock_user_db(flock)

    # Mark user updated for all logins
    update_account_expire_cache(configuration, user_dict)
    update_account_status_cache(configuration, user_dict)

    if meta_only:
        return user_dict

    new_client_dir = client_id_dir(new_id)

    # NOTE: published archives are linked to a hash based on creator ID.
    # We first remove any conflicting symlink from previous renames before
    # renaming user archive dir and creating the new legacy alias afterwards.

    old_arch_home = os.path.join(configuration.freeze_home, client_dir)
    new_arch_home = os.path.join(configuration.freeze_home, new_client_dir)
    # Make sure (lazy created) freeze home exists
    try:
        os.makedirs(old_arch_home)
    except Exception as exc:
        pass
    delete_symlink(new_arch_home, _logger, allow_missing=True)

    # Rename user dirs recursively

    user_dirs = [configuration.user_home,
                 configuration.user_settings,
                 configuration.user_cache]

    if configuration.site_enable_jobs:
        user_dirs.append(configuration.mrsl_files_dir)
    if configuration.site_enable_freeze:
        user_dirs.append(configuration.freeze_home)
    if configuration.site_enable_resources:
        user_dirs.append(configuration.resource_pending)

    for base_dir in user_dirs:
        old_path = os.path.join(base_dir, client_dir)
        new_path = os.path.join(base_dir, new_client_dir)
        # Skip rename if dir was already renamed either in partial run or on
        # a shared FS sister site.
        if os.path.exists(new_path) and not os.path.exists(old_path):
            if verbose:
                print('skip already complete rename of user dir %s to %s' %
                      (old_path, new_path))
            continue
        try:
            rename_dir(old_path, new_path)
        except Exception as exc:
            if not force:
                raise Exception('could not rename %s to %s: %s'
                                % (old_path, new_path, exc))
    if verbose:
        print('User dirs for %s was successfully renamed!'
              % client_id)

    # Now create freeze_home alias to preserve access to published archives

    make_symlink(new_arch_home, old_arch_home, _logger)

    # Update any OpenID symlinks

    for name in old_user.get('openid_names', []):
        remove_alias_link(name, configuration.user_home)

    for name in user_dict.get('openid_names', []):
        # short_id is client_id for cert users - skip them
        if name in (client_id, new_id) or name.find(' ') != -1:
            continue
        create_alias_link(name, new_id, configuration.user_home)

    # Loop through resource map and update user resource ownership

    if configuration.site_enable_resources:
        force_update_resource_map(configuration)
        res_map = get_resource_map(configuration)
        for (res_id, res) in res_map.items():
            if client_id in res[OWNERS]:
                (add_status, err) = resource_add_owners(configuration, res_id,
                                                        [new_id])
                if not add_status:
                    if verbose:
                        print('Could not add new %s owner of %s: %s'
                              % (new_id, res_id, err))
                    continue
                (del_status, err) = resource_remove_owners(configuration, res_id,
                                                           [client_id])
                if not del_status:
                    if verbose:
                        print('Could not remove old %s owner of %s: %s'
                              % (client_id, res_id, err))
                    continue
                if verbose:
                    print(
                        'Updated %s owner from %s to %s' % (res_id, client_id,
                                                            new_id))

    # Loop through vgrid map and update user owner/membership
    # By using the high level add/remove API the corresponding vgrid components
    # get properly updated, too

    force_update_vgrid_map(configuration)
    vgrid_map = get_vgrid_map(configuration, recursive=False)
    for (vgrid_name, vgrid) in vgrid_map[VGRIDS].items():
        if client_id in vgrid[OWNERS]:

            (add_status, err) = vgrid_add_owners(configuration, vgrid_name,
                                                 [new_id])
            if not add_status:
                if verbose:
                    print('Could not add new %s owner of %s: %s'
                          % (new_id, vgrid_name, err))
                continue
            (del_status, err) = vgrid_remove_owners(configuration, vgrid_name,
                                                    [client_id])
            if not del_status:
                if verbose:
                    print('Could not remove old %s owner of %s: %s'
                          % (client_id, vgrid_name, err))
                continue
            if verbose:
                print('Updated %s owner from %s to %s' % (vgrid_name,
                                                          client_id,
                                                          new_id))
        elif client_id in vgrid[MEMBERS]:
            (add_status, err) = vgrid_add_members(configuration, vgrid_name,
                                                  [new_id])
            if not add_status:
                if verbose:
                    print('Could not add new %s member of %s: %s'
                          % (new_id, vgrid_name, err))
                continue
            (del_status, err) = vgrid_remove_members(configuration, vgrid_name,
                                                     [client_id])
            if not del_status:
                if verbose:
                    print('Could not remove old %s member of %s: %s'
                          % (client_id, vgrid_name, err))
                continue
            if verbose:
                print('Updated %s member from %s to %s' % (vgrid_name,
                                                           client_id,
                                                           new_id))

    # Loop through runtime envs and update ownership

    (re_status, re_list) = list_runtime_environments(configuration)
    if re_status:
        for re_name in re_list:
            (re_status, err) = update_runtimeenv_owner(re_name, client_id,
                                                       new_id, configuration)
            if verbose:
                if re_status:
                    print('Updated %s owner from %s to %s' % (re_name,
                                                              client_id,
                                                              new_id))
                elif err:
                    print('Could not change owner of %s: %s' % (re_name, err))
    else:
        if verbose:
            print('Could not load runtime env list: %s' % re_list)

    # Loop through moved sharelinks map pickle and update fs paths

    (load_status, sharelinks) = load_share_links(configuration, new_id)
    if verbose:
        print('Update %d sharelinks' % len(sharelinks))
    if load_status:
        for (share_id, share_dict) in sharelinks.items():
            # Update owner and use generic update helper to replace symlink
            share_dict['owner'] = new_id
            (mod_status, err) = update_share_link(share_dict, new_id,
                                                  configuration, sharelinks)
            if verbose:
                if mod_status:
                    print('Updated sharelink %s from %s to %s' % (share_id,
                                                                  client_id,
                                                                  new_id))
                elif err:
                    print('Could not update owner of %s: %s' % (share_id, err))
    else:
        if verbose:
            print('Could not load sharelinks: %s' % sharelinks)

    # TODO: update remaining user credentials in various locations?
    # * queued and active jobs (tricky due to races)
    # * user settings files?
    # * mrsl files?
    # * user stats?
    # * triggers?

    _logger.info("Renamed user %s to %s" % (client_id, new_id))
    mark_user_modified(configuration, new_id)
    _logger.info("Force new user renew to fix access")
    create_user(user_dict, conf_path, db_path, force, verbose,
                ask_renew=False, default_renew=True)
    _logger.info("Force access map updates to avoid web stall")
    _logger.info("Force update user map")
    force_update_user_map(configuration)
    if configuration.site_enable_resources:
        _logger.info("Force update resource map")
        force_update_resource_map(configuration)
    _logger.info("Force update vgrid map")
    force_update_vgrid_map(configuration)
    return user_dict


def delete_user(
    user,
    conf_path,
    db_path,
    force=False,
    verbose=False,
    do_lock=True
):
    """Delete user"""

    flock = None
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()

    fill_distinguished_name(user)
    client_id = user['distinguished_name']
    client_dir = client_id_dir(client_id)

    if verbose:
        print('User ID: %s\n' % client_id)

    if not force:
        delete_answer = raw_input(
            "Really PERMANENTLY delete %r including user home data? [y/N] " %
            client_id)
        if not delete_answer.lower().startswith('y'):
            raise Exception("Aborted removal of %s from user DB" % client_id)

    if do_lock:
        flock = lock_user_db(db_path)

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=False)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to load user DB: %s' % err)

        if client_id not in user_db:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception("User DB entry '%s' doesn't exist!"
                                % client_id)

    try:
        user_dict = user_db.get(client_id, user)
        del user_db[client_id]
        save_user_db(user_db, db_path, do_lock=False)
        if verbose:
            print('User %s was successfully removed from user DB!'
                  % client_id)
    except Exception as err:
        if not force:
            if do_lock:
                unlock_user_db(flock)
            raise Exception('Failed to remove %s from user DB: %s'
                            % (client_id, err))

    if do_lock:
        unlock_user_db(flock)

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
        except Exception as exc:
            if not force:
                raise Exception('could not remove %s: %s'
                                % (user_path, exc))
    if verbose:
        print('User dirs for %s was successfully removed!'
              % client_id)
    mark_user_modified(configuration, client_id)


def get_openid_user_map(configuration, do_lock=True):
    """Translate user DB to OpenID mapping between a verified login URL and a
    pseudo certificate DN.
    """
    id_map = {}
    db_path = os.path.join(configuration.mig_server_home, user_db_filename)
    user_map = load_user_db(db_path, do_lock=do_lock)
    user_alias = configuration.user_openid_alias
    for cert_id in user_map:
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


def get_openid_user_dn(configuration, login_url,
                       user_check=True, do_lock=True):
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
    _logger = configuration.logger
    _logger.debug('extracting openid dn from %s' % login_url)
    found_openid_prefix = False
    for oid_provider in configuration.user_openid_providers:
        oid_prefix = oid_provider.rstrip('/') + '/'
        if login_url.startswith(oid_prefix):
            found_openid_prefix = oid_prefix
            break
    if not found_openid_prefix:
        _logger.error("openid login from invalid provider: %s" % login_url)
        return ''
    raw_login = login_url.replace(found_openid_prefix, '')
    return get_any_oid_user_dn(configuration, raw_login, user_check, do_lock)


def get_oidc_user_dn(configuration, login, user_check=True, do_lock=True):
    """Translate OpenID Connect user identified by login into a
    distinguished_name on the cert format.
    We first lookup the login suffix in the user_home to find a matching
    symlink from the simple ID to the cert-style user home and translate that
    into the corresponding distinguished name.
    If we don't succeed we try looking up the user from an optional oidc
    login alias from the configuration and return the corresponding
    distinguished name.
    As a last resort we check if login is already on the cert distinguished
    name or cert dir format and return the distinguished name format if so.
    If the optional user_check flag is set to False the user dir check is
    skipped resulting in the openid name being returned even for users not
    yet signed up.
    """
    _logger = configuration.logger
    _logger.debug('extracting openid dn from %s' % login)
    return get_any_oid_user_dn(configuration, login, user_check, do_lock)


def get_any_oid_user_dn(configuration, raw_login,
                        user_check=True, do_lock=True):
    """Translate OpenID or OpenID Connect user identified by raw_login into a
    distinguished_name on the cert format.
    We first lookup the raw_login in the user_home to find a matching symlink
    from the simple ID to the cert-style user home and translate that into the
    corresponding distinguished name.
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
    _logger = configuration.logger
    _logger.debug("trying openid raw login: %s" % raw_login)
    # Lookup native user_home from openid user symlink
    link_path = os.path.join(configuration.user_home, raw_login)
    if os.path.islink(link_path):
        native_path = os.path.realpath(link_path)
        native_dir = os.path.basename(native_path)
        distinguished_name = client_dir_id(native_dir)
        _logger.info('found full ID %s from %s link'
                     % (distinguished_name, raw_login))
        return distinguished_name
    elif configuration.user_openid_alias:
        db_path = os.path.join(configuration.mig_server_home, user_db_filename)
        user_map = load_user_db(db_path, do_lock=do_lock)
        user_alias = configuration.user_openid_alias
        _logger.debug('user_map')
        for (distinguished_name, user) in user_map.items():
            if user[user_alias] in (raw_login, client_alias(raw_login)):
                _logger.info('found full ID %s from %s alias'
                             % (distinguished_name, raw_login))
                return distinguished_name

    # Fall back to try direct DN (possibly on cert dir form)
    _logger.info('fall back to direct ID %s from %s'
                 % (raw_login, raw_login))
    # Force to dir format and check if user home exists
    cert_dir = client_id_dir(raw_login)
    base_path = os.path.join(configuration.user_home, cert_dir)
    if os.path.isdir(base_path):
        distinguished_name = client_dir_id(cert_dir)
        _logger.info('accepting direct user %s from %s'
                     % (distinguished_name, raw_login))
        return distinguished_name
    elif not user_check:
        _logger.info('accepting raw user %s from %s'
                     % (raw_login, raw_login))
        return raw_login
    else:
        _logger.error('no such openid user %s: %s'
                      % (cert_dir, raw_login))
        return ''


def get_full_user_map(configuration, do_lock=True):
    """Load complete user map including any OpenID aliases"""
    db_path = os.path.join(configuration.mig_server_home, user_db_filename)
    user_map = load_user_db(db_path, do_lock=do_lock)
    oid_aliases = get_openid_user_map(configuration)
    for (alias, cert_id) in oid_aliases.items():
        user_map[alias] = user_map.get(cert_id, {})
    return user_map


def __oid_sessions_execute(configuration, db_name, query, query_vars,
                           commit=False):
    """Execute query on Apache mod auth OpenID sessions DB from configuration
    and db_name with sql query_vars inserted.
    Use the commit flag to specify if the query should be followed by a db
    commit to save any changes.
    """
    _logger = configuration.logger
    sessions = []
    if not configuration.user_openid_providers or \
            not configuration.openid_store:
        _logger.error("no openid configuration")
        return (False, sessions)
    session_db_path = os.path.join(configuration.openid_store, db_name)
    if not os.path.exists(session_db_path):
        _logger.error("could not find openid session db: %s" % session_db_path)
        return (False, sessions)
    try:
        conn = sqlite3.connect(session_db_path)
        cur = conn.cursor()
        _logger.info("execute query %s with args %s on openid sessions"
                     % (query, query_vars))
        cur.execute(query, query_vars)
        sessions = cur.fetchall()
        if commit:
            conn.commit()
        conn.close()
    except Exception as exc:
        _logger.error("failed to execute query %s with args %s: %s"
                      % (query, query_vars, exc))
        return (False, sessions)
    _logger.info("got openid sessions out for %s" % sessions)
    return (True, sessions)


def find_oid_sessions(configuration, db_name, identity):
    """Find active OpenID session(s) for user with OpenID identity. Queries the
    Apache mod auth openid sqlite database directly.
    """
    query = 'SELECT * FROM sessionmanager WHERE identity=?'
    args = (identity, )
    return __oid_sessions_execute(configuration, db_name, query, args, False)


def expire_oid_sessions(configuration, db_name, identity):
    """Expire active OpenID session(s) for user with OpenID identity. Modifies
    the Apache mod auth openid sqlite database directly.
    """
    query = 'DELETE FROM sessionmanager WHERE identity=?'
    args = (identity, )
    return __oid_sessions_execute(configuration, db_name, query, args, True)


def migrate_users(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    prune_dupes=False,
    do_lock=True,
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

    flock = None
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()

    if do_lock:
        flock = lock_user_db(db_path)

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=False)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to load user DB: %s' % err)

    targets = {}
    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = user['full_name']
        new_id = user['distinguished_name']
        if client_id == new_id:
            if verbose:
                print('user %s is already updated to new format' % client_id)
            continue
        targets[client_id] = user

    # Make sure there are no collisions in old user IDs

    latest = {}
    for (client_id, user) in targets.items():
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']
        if new_id in user_db:
            if not prune_dupes:
                if not force:
                    if do_lock:
                        unlock_user_db(flock)
                    raise Exception('new ID %s already exists in user DB!'
                                    % new_id)
            else:
                if verbose:
                    print('Pruning old duplicate user %s from user DB'
                          % client_id)
                del user_db[client_id]
        elif old_id in latest:
            if not prune_dupes:
                if not force:
                    if do_lock:
                        unlock_user_db(flock)
                    raise Exception('old ID %s is not unique in user DB!'
                                    % old_id)
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
                    print('Pruning duplicate user %s from user DB' % prune_id)
                del user_db[prune_id]
        else:
            latest[old_id] = (client_id, user)
    save_user_db(user_db, db_path, do_lock=False)

    if do_lock:
        unlock_user_db(flock)
        flock = None

    # Now update the remaining users, i.e. those in latest
    for (client_id, user) in latest.values():
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']
        if verbose:
            print('updating user %s on old format %s to new format %s'
                  % (client_id, old_id, new_id))

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
            except Exception as exc:

                # os.symlink(new_path, old_path)

                if not force:
                    raise Exception('could not move %s to %s: %s'
                                    % (old_path, new_path, exc))

        mrsl_base = os.path.join(configuration.mrsl_files_dir, new_name)
        for mrsl_name in os.listdir(mrsl_base):
            try:
                mrsl_path = os.path.join(mrsl_base, mrsl_name)
                if not os.path.isfile(mrsl_path):
                    continue
                filter_pickled_dict(mrsl_path, {old_id: new_id})
            except Exception as exc:
                if not force:
                    raise Exception('could not update saved mrsl in %s: %s'
                                    % (mrsl_path, exc))

        re_base = configuration.re_home
        for re_name in os.listdir(re_base):
            try:
                re_path = os.path.join(re_base, re_name)
                if not os.path.isfile(re_path):
                    continue
                filter_pickled_dict(re_path, {old_id: new_id})
            except Exception as exc:
                if not force:
                    raise Exception('could not update RE user in %s: %s'
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
                    except Exception as exc:
                        if not force:
                            raise Exception('could not update %s in %s: %s'
                                            % (kind, kind_path, exc))

        # Finally update user DB now that file system was updated

        flock = None
        try:
            if do_lock:
                flock = lock_user_db(db_path)
            user_db = load_user_db(db_path, do_lock=False)
            del user_db[client_id]
            user_db[new_id] = user
            save_user_db(user_db, db_path, do_lock=False)
            if verbose:
                print('User %s was successfully updated in user DB!'
                      % client_id)
        except Exception as err:
            if not force:
                if do_lock and flock:
                    unlock_user_db(flock)
                raise Exception('Failed to update %s in user DB: %s'
                                % (client_id, err))
        if do_lock and flock:
            unlock_user_db(flock)


def fix_entities(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    do_lock=True,
):
    """Update owners/members for all resources and vgrids to use new format IDs
    where possible"""

    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=do_lock)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            if not force:
                raise Exception('Failed to load user DB: %s' % err)

    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = user['full_name'].replace(' ', '_')
        new_id = user['distinguished_name']
        if verbose:
            print('updating user %s on old format %s to new format %s'
                  % (client_id, old_id, new_id))

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
                        print('updating %s in %s' % (client_id, kind_path))
                    try:
                        filter_pickled_list(kind_path, {old_id: new_id})
                    except Exception as exc:
                        if not force:
                            raise Exception('could not update %s in %s: %s'
                                            % (kind, kind_path, exc))


def fix_userdb_keys(
    conf_path,
    db_path,
    force=False,
    verbose=False,
    do_lock=True,
):
    """Fix any old leftover colon separated keys in user DB by replacing them
    with the new DN form from the associated user dict.
    """
    flock = None
    user_db = {}
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()

    if do_lock:
        flock = lock_user_db(db_path)

    if os.path.exists(db_path):
        try:
            if isinstance(db_path, dict):
                user_db = db_path
            else:
                user_db = load_user_db(db_path, do_lock=False)
                if verbose:
                    print('Loaded existing user DB from: %s' % db_path)
        except Exception as err:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to load user DB: %s' % err)

    for (client_id, user) in user_db.items():
        fill_distinguished_name(user)
        old_id = client_id
        new_id = user['distinguished_name']
        if old_id == new_id:
            if verbose:
                print('user %s is already updated to new format' % client_id)
            continue
        if verbose:
            print('updating user on old format %s to new format %s'
                  % (old_id, new_id))

        try:
            del user_db[client_id]
            user_db[new_id] = user
            save_user_db(user_db, db_path, do_lock=False)
            if verbose:
                print('User %s was successfully updated in user DB!'
                      % client_id)
        except Exception as err:
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to update %s in user DB: %s'
                                % (client_id, err))
    if do_lock:
        unlock_user_db(flock)


def default_search():
    """Default search filter to match all users"""

    search_filter = {}
    for (key, _) in cert_field_order:
        search_filter[key] = '*'
    return search_filter


def search_users(search_filter, conf_path, db_path,
                 verbose=False, do_lock=True, regex_match=[]):
    """Search for matching users. The optional regex_match is a list of keys in
    search_filter to apply regular expression match rather than the usual
    fnmatch for.
    """

    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger

    try:
        if isinstance(db_path, dict):
            user_db = db_path
        else:
            user_db = load_user_db(db_path, do_lock=do_lock)
            if verbose:
                print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        err_msg = 'Failed to load user DB: %s' % err
        if verbose:
            print(err_msg)
        _logger.error(err_msg)
        return (configuration, [])

    hits = []
    for (uid, user_dict) in user_db.items():
        match = True
        for (key, val) in search_filter.items():
            if key == 'expire_after':
                if user_dict.get('expire', val) < val:
                    match = False
                    break
            elif key == 'expire_before':
                if user_dict.get('expire', 0) > val:
                    match = False
                    break
            elif key in regex_match and \
                    not re.match(val, "%s" % user_dict.get(key, '')):
                match = False
                break
            elif key not in regex_match and \
                    not fnmatch.fnmatch("%s" % user_dict.get(key, ''), val):
                match = False
                break

        if not match:
            continue
        hits.append((uid, user_dict))
    return (configuration, hits)


def _user_general_notify(user_id, targets, conf_path, db_path,
                         verbose=False, get_fields=[], do_lock=True):
    """Find notification addresses for user_id and targets"""

    password, errors = '', []
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger
    try:
        if isinstance(db_path, dict):
            user_db = db_path
        else:
            user_db = load_user_db(db_path, do_lock=do_lock)
            if verbose:
                print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        err_msg = 'Failed to load user DB: %s' % err
        if verbose:
            print(err_msg)
        _logger.error(err_msg)
        return []

    user_fields = {}
    if user_id in user_db:
        user_dict = user_db[user_id]
    else:
        user_dict = {}
        if get_fields:
            errors.append('No such user: %s' % user_id)
    # Extract username and password intelligently
    if 'username' in get_fields:
        username = user_dict.get(configuration.user_openid_alias, '')
        user_fields['username'] = username
        get_fields = [i for i in get_fields if i != 'username']
    if 'password' in get_fields:
        password = user_dict.get('password', '')
        password = unscramble_password(configuration.site_password_salt,
                                       password)
        user_fields['password'] = password
        get_fields = [i for i in get_fields if i != 'password']
    # Any other fields are extracted verbatim
    if get_fields:
        for field in get_fields:
            user_fields[field] = user_dict.get(field, None)

    addresses = dict(zip(configuration.notify_protocols,
                         [[] for _ in configuration.notify_protocols]))
    addresses['email'] = []
    for (proto, address_list) in targets.items():
        if not proto in configuration.notify_protocols + ['email']:
            errors.append('unsupported protocol: %s' % proto)
            continue
        for address in address_list:
            if proto == 'email' and address == keyword_auto:
                address = user_dict.get('email', '')
                if not address:
                    errors.append('missing email address in db!')
                    continue
            addresses[proto].append(address)
    return (configuration, user_fields, addresses, errors)


def user_password_reminder(user_id, targets, conf_path, db_path,
                           verbose=False):
    """Find notification addresses and password for user_id and targets"""

    (configuration, fields, addresses, errors) = _user_general_notify(
        user_id, targets, conf_path, db_path, verbose, ['password'])
    return (configuration, fields['password'], addresses, errors)


def user_account_notify(user_id, targets, conf_path, db_path, verbose=False,
                        admin_copy=False):
    """Find notification addresses for user_id and targets"""
    (configuration, fields, addresses, errors) = _user_general_notify(
        user_id, targets, conf_path, db_path, verbose, ['username',
                                                        'full_name'])
    # Optionally send a copy to site admins
    if admin_copy and configuration.admin_email and \
            isinstance(configuration.admin_email, basestring):
        admin_addresses = []
        # NOTE: Explicitly separated by ', ' to distinguish Name <abc> form
        parts = configuration.admin_email.split(', ')
        for addr in parts:
            (real_name, plain_addr) = parseaddr(addr.strip())
            if plain_addr:
                admin_addresses.append(plain_addr)
        addresses['email'] += admin_addresses
    return (configuration, fields['username'], fields['full_name'], addresses,
            errors)


def user_migoid_notify(user_id, targets, conf_path, db_path, verbose=False,
                       admin_copy=False):
    """Alias for user_account_notify"""
    return user_account_notify(user_id, targets, conf_path, db_path, verbose,
                               admin_copy)


def user_request_reject(user_id, targets, conf_path, db_path, verbose=False,
                        admin_copy=False):
    """Find notification addresses for user_id and targets"""

    (configuration, _, addresses, errors) = _user_general_notify(
        user_id, targets, conf_path, db_path, verbose)
    # Optionally send a copy to site admins
    if admin_copy and configuration.admin_email and \
            isinstance(configuration.admin_email, basestring):
        admin_addresses = []
        # NOTE: Explicitly separated by ', ' to distinguish Name <abc> form
        parts = configuration.admin_email.split(', ')
        for addr in parts:
            (real_name, plain_addr) = parseaddr(addr.strip())
            if plain_addr:
                admin_addresses.append(plain_addr)
        addresses['email'] += admin_addresses
    return (configuration, addresses, errors)


def user_password_check(user_id, conf_path, db_path, verbose=False,
                        override_policy=None, do_lock=True):
    """Check password policy compliance for user_id. If the optional
    override_policy is left unset the configuration policy value will be used
    otherwise the given value is used"""

    errors = []
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger
    try:
        if isinstance(db_path, dict):
            user_db = db_path
        else:
            user_db = load_user_db(db_path, do_lock=do_lock)
            if verbose:
                print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        err_msg = 'Failed to load user DB: %s' % err
        if verbose:
            print(err_msg)
        _logger.error(err_msg)
        return []

    if user_id not in user_db:
        errors.append('No such user: %s' % user_id)
        return (configuration, errors)

    if override_policy:
        configuration.site_password_policy = override_policy

    password = user_db[user_id].get('password', '') or ''
    password = unscramble_password(configuration.site_password_salt,
                                   password)
    if not password:
        errors.append('No password set for %s' % user_id)
    else:
        try:
            assure_password_strength(configuration, password)
        except Exception as exc:
            errors.append('password for %s does not satisfy local policy: %s'
                          % (user_id, exc))

    client_dir = client_id_dir(user_id)
    digest_path = os.path.join(configuration.user_home, client_dir,
                               davs_conf_dir, authdigests_filename)
    if verbose:
        print("inspecting %s" % digest_path)
    all_digests = []
    if os.path.isfile(digest_path):
        if verbose:
            print("Checking %s" % digest_path)
        all_digests = get_authpasswords(digest_path)
    if not all_digests:
        errors.append('No digest set for %s' % user_id)
    for digest in all_digests:
        digest = digest.strip()
        unscrambled = ''
        try:
            _, _, _, payload = digest.split("$")
            unscrambled = unscramble_digest(configuration.site_digest_salt,
                                            payload)
            # NOTE: password may contain ':' so limit splits
            _, _, password = unscrambled.split(":", 2)
        except Exception as exc:
            errors.append('digest for %s could not be unpacked (%s): %s'
                          % (user_id, unscrambled, exc))
            continue
        try:
            assure_password_strength(configuration, password)
        except Exception as exc:
            errors.append('digest for %s does not satisfy local policy: %s'
                          % (user_id, exc))

    return (configuration, errors)


def req_password_check(req_path, conf_path, db_path, verbose=False,
                       override_policy=None):
    """Check password policy compliance for request in req_path. If the optional
    override_policy is left unset the configuration policy value will be used
    otherwise the given value is used"""

    errors = []
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger

    try:
        user_dict = load(req_path)
        user_id = user_dict['distinguished_name']
    except Exception as exc:
        errors.append('could not load request from %s: %s' % (req_path, exc))
        return (configuration, errors)

    if override_policy:
        configuration.site_password_policy = override_policy

    password = user_dict.get('password', '') or ''
    password = unscramble_password(configuration.site_password_salt,
                                   password)
    if not password:
        errors.append('No password set for %s' % user_id)
        return (configuration, errors)

    try:
        assure_password_strength(configuration, password)
    except Exception as exc:
        errors.append('password for %s does not satisfy local policy: %s'
                      % (user_id, exc))
    return (configuration, errors)


def user_twofactor_status(user_id, conf_path, db_path, fields,
                          verbose=False, do_lock=True):
    """Check twofactor status for user_id"""

    errors = []
    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger
    try:
        if isinstance(db_path, dict):
            user_db = db_path
        else:
            user_db = load_user_db(db_path, do_lock=do_lock)
            if verbose:
                print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        err_msg = 'Failed to load user DB: %s' % err
        if verbose:
            print(err_msg)
        _logger.error(err_msg)
        return []

    if user_id not in user_db:
        errors.append('No such user: %s' % user_id)
        return (configuration, errors)

    client_dir = client_id_dir(user_id)
    twofactor_path = os.path.join(configuration.user_settings, client_dir,
                                  twofactor_filename)
    if verbose:
        print("inspecting %s" % twofactor_path)
    twofactor_dict = None
    try:
        twofactor_dict = load(twofactor_path)
    except Exception as err:
        err_msg = 'Failed to load twofactor for %s: %s' % (user_id, err)
        if verbose:
            print(err_msg)

    if not twofactor_dict:
        errors.append('No twofactor settings saved for %s' % user_id)
        return (configuration, errors)
    if keyword_auto in fields:
        fields = [pair[0] for pair in get_twofactor_specs(configuration)]
    for key in fields:
        if not twofactor_dict.get(key, False):
            errors.append('%s not enabled for: %s' % (key, user_id))
        elif verbose:
            print("%s enabled for %s" % (key, user_id))
    return (configuration, errors)


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
        authorized_passwords = [i.strip() for i in authorized_passwords
                                if i.strip()]
    except:
        authorized_passwords = []
    return authorized_passwords


def generate_password_hash(configuration, password):
    """Return a hash data string for saving provided password. We use PBKDF2 to
    help with the hash comparison later and store the data in a form close to
    the one recommended there:
    (algorithm$hashfunction$salt$costfactor$hash).
    """
    _logger = configuration.logger
    try:
        return make_hash(password)
    except Exception as exc:
        _logger.warning("in generate_password_hash: %s" % exc)
        return password


def check_password_hash(configuration, service, username, password,
                        stored_hash, hash_cache=None, strict_policy=True):
    """Return a boolean indicating if offered password matches stored_hash
    information. We use PBKDF2 to help with the hash comparison and store the
    data in a form close to the one recommended there:
    (algorithm$hashfunction$salt$costfactor$hash).

    More information about sane password handling is available at:
    https://exyr.org/2011/hashing-passwords/

    The optional hash_cache dictionary argument can be used to cache lookups
    and speed up repeated use.
    The optional boolean strict_policy argument switches password policy checks
    on/off. Should only be disabled for sharelinks and similar where policy is
    not guaranteed to apply.
    """
    _logger = configuration.logger
    try:
        return check_hash(configuration, service, username, password,
                          stored_hash, hash_cache, strict_policy)
    except Exception as exc:
        _logger.warning("in check_password_hash: %s" % exc)
        return False


def generate_password_scramble(configuration, password, salt):
    """Return a scrambled data string for saving provided password. We use a
    simple salted encoding to avoid storing passwords in the clear when we
    can't avoid saving the actual password instead of just a hash.
    """
    _logger = configuration.logger
    try:
        return make_scramble(password, salt)
    except Exception as exc:
        _logger.warning("in generate_password_scramble: %s" % exc)
        return password


def check_password_scramble(configuration, service, username, password,
                            stored_scramble, salt, scramble_cache=None,
                            strict_policy=True):
    """Return a boolean indicating if offered password matches stored_scramble
    information. We use a simple salted encoding to avoid storing passwords in
    the clear when we can't avoid saving the actual password instead of just a
    hash.

    The optional scramble_cache dictionary argument can be used to cache
    lookups and speed up repeated use.
    The optional boolean strict_policy argument switches warnings about
    password policy incompliance to fatal errors. Always enabled here since it
    is only used for real user logins, and never sharelinks.
    """
    _logger = configuration.logger
    try:
        return check_scramble(configuration, service, username, password,
                              stored_scramble, salt, scramble_cache,
                              strict_policy)
    except Exception as exc:
        _logger.warning("in check_password_scramble: %s" % exc)
        return False


def generate_password_digest(configuration, realm, username, password, salt):
    """Return a digest data string for saving provided password"""
    _logger = configuration.logger
    try:
        return make_digest(realm, username, password, salt)
    except Exception as exc:
        _logger.warning("in generate_password_digest: %s" % exc)
        return password


def check_password_digest(configuration, service, realm, username, password,
                          stored_digest, salt, digest_cache=None,
                          strict_policy=True):
    """Return a boolean indicating if offered password matches stored_digest
    information.

    The optional digest_cache dictionary argument can be used to cache lookups
    and speed up repeated use.
    The optional boolean strict_policy argument switches warnings about
    password policy incompliance to fatal errors. Should only be disabled for
    sharelinks.
    """
    _logger = configuration.logger
    try:
        return check_digest(configuration, service, realm, username, password,
                            stored_digest, salt, digest_cache, strict_policy)
    except Exception as exc:
        _logger.warning("in check_password_digest: %s" % exc)
        return False
