#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# useradm - user administration functions
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

from builtins import zip
from builtins import input
from past.builtins import basestring

from email.utils import parseaddr
import datetime
import fnmatch
import os
import re
import sqlite3
import sys
import time

from mig.shared.accountstate import update_account_expire_cache, \
    update_account_status_cache
from mig.shared.base import client_id_dir, client_dir_id, client_alias, \
    get_client_id, extract_field, fill_user, fill_distinguished_name, \
    is_gdp_user, mask_creds, sandbox_resource, force_native_str, \
    force_native_str_rec, native_str_escape, native_args
from mig.shared.conf import get_configuration_object
from mig.shared.configuration import Configuration
from mig.shared.defaults import user_db_filename, keyword_auto, ssh_conf_dir, \
    davs_conf_dir, ftps_conf_dir, htaccess_filename, welcome_filename, \
    settings_filename, profile_filename, default_css_filename, \
    widgets_filename, seafile_ro_dirname, authkeys_filename, \
    authpasswords_filename, authdigests_filename, cert_field_order, \
    twofactor_filename, peers_filename, gdp_distinguished_field, \
    unique_id_length, unique_id_charset, X509_USER_ID_FORMAT, \
    UUID_USER_ID_FORMAT, valid_user_id_formats, user_id_alias_dir, \
    expire_marks_dir, status_marks_dir
from mig.shared.fileio import filter_pickled_list, filter_pickled_dict, \
    make_symlink, delete_symlink, read_file, write_file, remove_dir, \
    remove_rec, makedirs_rec, listdir, move
from mig.shared.filemarks import reset_filemark
from mig.shared.modified import mark_user_modified
from mig.shared.refunctions import list_runtime_environments, \
    update_runtimeenv_owner
from mig.shared.pwcrypto import make_safe_hash, make_hash, check_hash, \
    make_digest, check_digest, make_scramble, check_scramble, \
    unscramble_password, unscramble_digest, verify_reset_token, \
    assure_password_strength, generate_random_ascii
from mig.shared.resource import resource_add_owners, resource_remove_owners
from mig.shared.serial import load, dump
from mig.shared.settings import update_settings, update_profile, update_widgets
from mig.shared.sharelinks import load_share_links, update_share_link, \
    get_share_link, mode_chars_map
from mig.shared.twofactorkeywords import get_twofactor_specs
from mig.shared.userdb import lock_user_db, unlock_user_db, load_user_db, \
    load_user_dict, save_user_db, default_db_path
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


def init_user_adm(dynamic_db_path=True):
    """Shared init function for all user administration scripts.
    The optional dynamic_db_path argument toggles dynamic user db path lookup
    in the sense that if disabled the user adm script dir is used as db base
    dir and otherwise an AUTO marker is returned and the path only looked up
    later from the loaded configuration.
    """

    # NOTE: keep app name on default string format but force rest to term enc
    raw_args = force_native_str_rec(native_args(sys.argv))
    args = raw_args[1:]
    app_dir = os.path.dirname(raw_args[0])
    if not app_dir:
        app_dir = '.'
    if dynamic_db_path:
        db_path = keyword_auto
    else:
        db_path = os.path.join(app_dir, user_db_filename)
    return (args, app_dir, db_path)


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
    if os.path.islink(link_path):
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


def get_accepted_peers(configuration, client_id):
    """Helper to get the list of peers accepted by client_id"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        accepted_peers = load(peers_path)
    except Exception as exc:
        if os.path.exists(peers_path):
            _logger.warning("could not load peers from %s: %s" %
                            (peers_path, exc))
        accepted_peers = {}
    return accepted_peers


def sync_gdp_users(configuration,
                   user_db,
                   user,
                   client_id):
    """Update status and expire data for GDP users"""
    if not configuration.site_enable_gdp:
        return user_db

    gdp_client_id = "%s/%s=" % (client_id, gdp_distinguished_field)
    for (key, _) in user_db.items():
        if key.startswith(gdp_client_id):
            if user.get('expire', None):
                user_db[key]['expire'] = user['expire']
                update_account_expire_cache(configuration, user_db[key])
            if user.get('status', None):
                user_db[key]['status'] = user['status']
                update_account_status_cache(configuration, user_db[key])

    return user_db


def _get_required_user_dir_links(configuration, real_dir, link_dir):
    """Build and return a list of tuples listing all user state dirs and their
    required ID symlinks. E.g for state/user_home the tuple is
    (state/user_home/REAL_ID, state/user_home/LINK_ID)
    """
    home_dir = os.path.join(configuration.user_home, real_dir)
    settings_dir = os.path.join(configuration.user_settings, real_dir)
    cache_dir = os.path.join(configuration.user_cache, real_dir)
    mrsl_dir = os.path.join(configuration.mrsl_files_dir, real_dir)
    user_pending_dir = os.path.join(configuration.user_pending, real_dir)
    res_pending_dir = os.path.join(configuration.resource_pending, real_dir)
    if link_dir:
        home_link = os.path.join(configuration.user_home, link_dir)
        settings_link = os.path.join(configuration.user_settings, link_dir)
        cache_link = os.path.join(configuration.user_cache, link_dir)
        mrsl_link = os.path.join(configuration.mrsl_files_dir, link_dir)
        res_pending_link = os.path.join(configuration.resource_pending,
                                        link_dir)
    else:
        home_link = settings_link = cache_link = mrsl_link = False
        res_pending_link = False

    # No link in user pending as that is before user has UUID
    user_pending_link = None
    dir_links = [(home_dir, home_link), (settings_dir, settings_link),
                 (cache_dir, cache_link), (mrsl_dir, mrsl_link),
                 (user_pending_dir, user_pending_link),
                 (res_pending_dir, res_pending_link)]
    return dir_links


def _get_required_user_alias_links(configuration, real_dir, link_dir):
    """Build and return a list of tuples listing all user alias symlink source
    and destination paths. E.g for state/mig_system_run/user_id_alias the tuple
    is (state/mig_system_run/user_id_alias/REAL_ID,
     state/mig_system_run/user_id_alias/LINK_ID)
    """
    if link_dir:
        # NOTE: see explanation of this reverse link below
        id_alias_link = os.path.join(configuration.mig_system_run,
                                     user_id_alias_dir, real_dir)
        # Lazy init of mig_system_run subdir always recreated on demand
        makedirs_rec(os.path.dirname(id_alias_link), configuration)
    else:
        id_alias_link = False
    # NOTE: id_alias_link should point to link_dir and not real_dir in order
    #       to allow (reverse) user ID alias lookup.
    alias_links = [(link_dir, id_alias_link)]
    return alias_links


def lookup_client_id(configuration, user_id):
    """Lookup the X509 format client_id linked to user_id based on the helper
    symlink in user_id_alias_dir in configured mig_system_run location.
    """
    _logger = configuration.logger
    alias_link = os.path.join(configuration.mig_system_run, user_id_alias_dir,
                              user_id)
    _logger.debug("looking for alias link %r" % alias_link)
    # NOTE: use islink rather than exists here because it is a dead link if so
    if os.path.islink(alias_link):
        target_path = os.path.realpath(alias_link)
        client_dir = os.path.basename(target_path)
        _logger.debug("found linked alias %r for %r" % (client_dir, user_id))
    else:
        # Try a reverse lookup directly in user_home with writeback to
        # mig_system_run, which is only scratch space.
        client_dir = False
        for name in listdir(configuration.user_home):
            link_path = os.path.join(configuration.user_home, name)
            if os.path.islink(link_path):
                target = os.path.basename(os.path.realpath(link_path))
                if target == user_id:
                    client_dir = name
                    _logger.debug("reverse lookup found link %r to %r" %
                                  (client_dir, user_id))
                    makedirs_rec(os.path.dirname(alias_link), configuration)
                    make_symlink(client_dir, alias_link, _logger)
                    break
        if not client_dir:
            _logger.warning("found no alias %r" % user_id)
            return user_id
    client_id = client_dir_id(client_dir)
    return client_id


def verify_user_peers(configuration, db_path, client_id, user, now, verify_peer,
                      peer_expire_slack, force, verbose):
    """Handle peer verification during create_user operations. If verify_peer
    is set any matching users in the user database are tried in turn as
    possible peers for user.
    A list of acceptable peers is returned if any are found and verified to
    accept user as their peer.
    """
    _logger = configuration.logger
    now_dt = datetime.datetime.fromtimestamp(now)
    accepted_peer_list = []
    verify_pattern = verify_peer.strip()
    if not verify_pattern:
        _logger.warning("no peers for %s to verify %r" % (client_id,
                                                          verify_pattern))
        raise Exception("No peers for %s to verify: %r" % (client_id,
                                                           verify_pattern))

    if verify_pattern == keyword_auto:
        _logger.debug('auto-detect peers for %s' % client_id)
        peer_email_list = []
        # Extract email of peers contact from explicit peers field or comment
        # We don't try peers full name here as it is far too tricky to match
        peers_email = user.get('peers_email', '')
        comment = user.get('comment', '')
        peers_source = "%s\n%s" % (peers_email, comment)
        all_matches = valid_email_addresses(configuration, peers_source)
        for i in all_matches:
            peer_email = "%s" % i
            if not possible_user_id(configuration, peer_email):
                _logger.warning('skip invalid peer: %s' % peer_email)
                continue
            peer_email_list.append(peer_email)

        if not peer_email_list:
            _logger.warning("requested peer auto-detect failed for %s" %
                            client_id)
            raise Exception("Failed auto-detect peers in request for %s: %r"
                            % (client_id, peers_source))
        verify_pattern = '|'.join(['.*emailAddress=%s' %
                                   i for i in peer_email_list])

    _logger.debug('verify peers for %s with %s' % (client_id,
                                                   verify_pattern))
    search_filter = default_search()
    search_filter['distinguished_name'] = verify_pattern
    if verify_peer == keyword_auto or verify_pattern.find('|') != -1:
        regex_patterns = ['distinguished_name']
    else:
        regex_patterns = []
    (_, hits) = search_users(search_filter, configuration, db_path, force, verbose,
                             regex_match=regex_patterns)
    peer_notes = []
    if not hits:
        peer_notes.append("no match for peers")
    # Request can ask for expire with fall-back cap to highest peer value
    # in case the original expire is not satisfied by any peer contacts.
    # TODO: migrate this cap expire choice to a conf option?
    cap_expire = user.get('cap_expire', True)
    client_expire = user['expire']
    client_expire_dt = datetime.datetime.fromtimestamp(client_expire)
    # Latest expire value accepted by any peers contact (init to now)
    effective_expire_dt = now_dt
    for (contact_id, contact_dict) in hits:
        if configuration.site_enable_gdp and is_gdp_user(configuration,
                                                         contact_id):
            _logger.debug(
                "skip gdp project user %s as peers contact" % contact_id)
            continue
        _logger.debug("check %s in peers contacts for %s" % (client_id,
                                                             contact_id))
        if client_id == contact_id:
            warn_msg = "users cannot invite themselves as peer: %s vs %s" \
                % (client_id, contact_id)
            _logger.warning(warn_msg)
            continue
        # Check that peers contact account is not suspended or similar
        contact_status = contact_dict.get('status', 'active')
        if contact_status not in ['active', 'temporal']:
            warn_msg = "status %s prevents %s as peer, including for %s" \
                % (contact_status, contact_id, client_id)
            _logger.warning(warn_msg)
            peer_notes.append(warn_msg)
            continue
        # Check that peers contact account is not expired (with slack)
        contact_expire = contact_dict.get('expire', -1)
        # Only allow slack if not temporal account
        allowed_slack = 0
        if contact_status == 'active':
            allowed_slack = peer_expire_slack
        if contact_expire >= 0 and now > contact_expire + allowed_slack:
            warn_msg = "expire %s (slack %d) prevents %s as peer for %s" \
                % (contact_expire, allowed_slack, contact_id,
                   client_id)
            _logger.warning(warn_msg)
            peer_notes.append(warn_msg)
            continue
        # TODO: make sure peers contact can (still) have peers at all
        #       Checks in reqacceptpeer and on peer creation may be stale
        #       by now upon any conf changes.
        #       May require move of peers_permit_allowed to separate module
        #       to avoid circular imports.
        # Check if among accepted peers
        accepted_peers = get_accepted_peers(configuration, contact_id)
        peer_entry = accepted_peers.get(client_id, None)
        if not peer_entry:
            _logger.warning("%s has not (yet) accepted %s as peer" %
                            (contact_id, client_id))
            continue
        # Found a potential peers contact, check contact vs client expire
        # NOTE: adjust given peer contact expire date to the end of that day
        peer_expire_dt = datetime.datetime.strptime(
            peer_entry.get('expire', 0), '%Y-%m-%d') + \
            datetime.timedelta(days=1, microseconds=-1)
        if peer_expire_dt < client_expire_dt:
            if cap_expire and peer_expire_dt > now_dt:
                info_msg = "%s accepts %s as peer with expire cap %s" % \
                    (contact_id, client_id, peer_expire_dt)
                _logger.info(info_msg)
                peer_notes.append(info_msg)
                # NOTE: only allow effective expire to increase
                if peer_expire_dt > effective_expire_dt:
                    _logger.info("bump effective expire to %s" %
                                 peer_expire_dt)
                    effective_expire_dt = peer_expire_dt
            else:
                warn_msg = "expire %s vs %s prevents %s as peer for %s" % \
                    (peer_expire_dt, client_expire_dt, contact_id,
                     client_id)
                _logger.warning(warn_msg)
                peer_notes.append(warn_msg)
                continue
        else:
            _logger.info("%s accepts %s as peer with requested expire %s"
                         % (contact_id, client_id, client_expire_dt))
            effective_expire_dt = client_expire_dt

        _logger.debug("validated %s accepts %s as peers contact" %
                      (contact_id, client_id))
        accepted_peer_list.append(contact_id)

    if not accepted_peer_list:
        _logger.warning("requested peer validation with %r for %s failed" %
                        (verify_pattern, client_id))
        raise Exception("Failed verify peers for %s using pattern %r: %s" %
                        (client_id, verify_pattern, '\n'.join(peer_notes)))

    # Enforce effective_expire_dt as highest actual account expire value
    effective_expire = int(time.mktime(effective_expire_dt.timetuple()))
    _logger.info("accept create user %s (expire %s) with contact(s): %s" %
                 (client_id, effective_expire_dt,
                  ', '.join(accepted_peer_list)))

    return accepted_peer_list, effective_expire


def create_user_in_db(configuration, db_path, client_id, user, now, authorized,
                      reset_token, reset_auth_type, accepted_peer_list, force,
                      verbose, ask_renew, default_renew, do_lock,
                      from_edit_user, ask_change_pw, auto_create_db,
                      create_backup):
    """Handle all the parts of user creation or renewal relating to the user
    datatbase.
    """
    _logger = configuration.logger
    flock = None
    user_db = {}
    renew = default_renew
    if do_lock:
        flock = lock_user_db(db_path)

    if not os.path.exists(db_path):
        # Auto-create missing user DB if either auto_create_db or force is set
        if auto_create_db or force:
            create_answer = 'y'
        else:
            print('User DB in %s does not exist - okay if first user' % db_path)
            create_answer = input('Create new user DB? [Y/n] ')
        if create_answer.lower().startswith('n'):
            if do_lock:
                unlock_user_db(flock)
            raise Exception("Missing user DB: '%s'" % db_path)

        _logger.info('create missing user DB in: %s' % db_path)
        if verbose:
            print('Creating missing user DB in: %s' % db_path)
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

    # Prevent alias clashes by refusing addition of new users with same
    # alias. We only allow renew of existing user.

    # NOTE: careful to skip GDP project users here
    if configuration.user_openid_providers and \
            configuration.user_openid_alias:
        if not configuration.site_enable_gdp:
            user_aliases = dict([(key, val[configuration.user_openid_alias])
                                 for (key, val) in user_db.items()])
            alias = user[configuration.user_openid_alias]
        elif not is_gdp_user(configuration, client_id):
            user_aliases = dict([(key, val[configuration.user_openid_alias])
                                 for (key, val) in user_db.items() if not
                                 is_gdp_user(configuration, key)])
            alias = user[configuration.user_openid_alias]
        else:
            user_aliases = {}
            alias = None

        if alias in user_aliases.values() and \
                user_aliases.get(client_id, None) != alias:
            if do_lock:
                unlock_user_db(flock)
            if verbose:
                print('Attempting create user with conflicting alias %s'
                      % alias)
            raise Exception(
                'A conflicting user with alias %s already exists' % alias)

    if client_id not in user_db:
        _logger.debug('add new user %r in user DB' % client_id)
        user['created'] = now
    else:
        _logger.debug('update existing user %r in user DB' % client_id)
        new_expire = user.get('expire', False)
        account_status = user_db[client_id].get('status', 'active')
        # Only allow renew if account is active or if temporal with peer list
        if account_status == 'active':
            _logger.debug("proceed with %s account" % account_status)
        elif account_status == 'temporal' and accepted_peer_list:
            _logger.debug("proceed with %s account and accepted peers %s" %
                          (account_status, accepted_peer_list))
        elif account_status == 'temporal' and reset_token and not new_expire:
            _logger.debug("proceed with %s account password reset (token %s)" %
                          (account_status, reset_token))
        elif from_edit_user:
            _logger.debug("proceed with %s account during edit user" %
                          account_status)
        else:
            raise Exception('refusing to renew %s account! (%s)' %
                            (account_status, accepted_peer_list))
        if reset_token and not new_expire:
            renew = True
        elif ask_renew:
            print('User DB entry for "%s" already exists' % client_id)
            renew_answer = input('Renew existing entry? [Y/n] ')
            renew = not renew_answer.lower().startswith('n')
        else:
            renew = default_renew
        if renew:
            user['old_password'] = user_db[client_id]['password']
            user['old_password_hash'] = user_db[client_id].get('password_hash',
                                                               '')
            # MiG OpenID users without password recovery have empty
            # password value and on renew we then leave any saved cert
            # password alone.
            # External OpenID users do not provide a password so again any
            # existing password should be left alone on renewal.
            # The password_hash field is not guaranteed to exist.
            if not user['password']:
                user['password'] = user['old_password']
            if not user.get('password_hash', ''):
                user['password_hash'] = user['old_password_hash']
            password_changed = (user['old_password'] != user['password'] or
                                user['old_password_hash'] != user['password_hash'])
            if password_changed:
                # Allow password change if it's directly authorized with login
                # or authorized through a simple reset challenge (reset_token).
                if not authorized and reset_token:
                    # NOTE: use timestamp from saved request file if available
                    req_timestamp = user.get('accepted_terms', time.time())
                    valid_reset = verify_reset_token(configuration,
                                                     user_db[client_id],
                                                     reset_token,
                                                     reset_auth_type,
                                                     req_timestamp)
                    if valid_reset:
                        _logger.info("%r requested and authorized password reset"
                                     % client_id)
                        if verbose:
                            print("User requested and authorized password reset")
                        authorized = True
                    else:
                        _logger.warning("%r requested password reset with bad token"
                                        % client_id)
                        if verbose:
                            print("User requested password reset with bad token")

                if authorized:
                    _logger.info("%r authorized password update" % client_id)
                    if verbose:
                        print("User authorized password update")
                elif not user['old_password'] and not user['old_password_hash']:
                    _logger.info("%r requested password - previously disabled"
                                 % client_id)
                    if verbose:
                        print("User requested password - previously disabled")
                else:
                    _logger.warning("%r exists with *different* password!" %
                                    client_id)
                    if ask_change_pw:
                        print("""User %r exists with *different* password!
Generally users with an existing account should sign up again through Xgi-bin
using their existing credentials to authorize password changes or use the reset
password mechanism to confirm their ownership of the registered account email.
""" % client_id)
                        accept_answer = input('Accept password change? [y/N] ')
                    else:
                        accept_answer = 'no'

                    authorized = accept_answer.lower().startswith('y')
                    if not authorized:
                        if do_lock:
                            unlock_user_db(flock)
                        if verbose:
                            print("""Renewal request supplied a different
password and you didn't accept change anyway - nothing more to do""")
                        err = """Cannot renew account using a new password!
Please tell user to use the original password, request password reset or go
through renewal using Xgi-bin with proper authentication to authorize the
change."""
                        raise Exception(err)
            _logger.debug('Renew/update existing user %s' % client_id)
            if verbose:
                print('Renewing or updating existing user')
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
            user['renewed'] = now
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

    # NOTE: careful to skip GDP project users in openid and unique_id setup
    if not configuration.site_enable_gdp or \
            not is_gdp_user(configuration, client_id):
        if configuration.user_openid_providers and \
                configuration.user_openid_alias:
            add_names.append(user[configuration.user_openid_alias])

        # Make sure unique_id is really unique in user DB
        all_unique = [i['unique_id'] for (_, i) in user_db.items() if
                      i.get('unique_id', None) and
                      i['distinguished_name'] != client_id]
        found_unique = False
        for _ in range(4):
            user['unique_id'] = user.get('unique_id', False)
            if user['unique_id'] and user['unique_id'] not in all_unique:
                _logger.debug("validated unique_id %(unique_id)s" %
                              mask_creds(user))
                found_unique = True
                break
            if not user['unique_id']:
                _logger.debug('Adding missing unique_id to user %s' %
                              mask_creds(user))
            elif renew:
                # NOTE: bail out here on edit/renewal as IDs are not unique
                raise ValueError("unique ID for %s (%r) has a collission!" %
                                 (client_id, user['unique_id']))
            else:
                _logger.warning("retry unique ID for %s (%r) - collission" %
                                (client_id, user['unique_id']))
            user['unique_id'] = generate_random_ascii(unique_id_length,
                                                      unique_id_charset)
        if not found_unique:
            if verbose:
                print('Failed to generate a unique id for %s - bailing out!' %
                      client_id)
            raise Exception('Failed to generate a unique id for %s - bail out!'
                            % client_id)

    # Now update possibly extended openid_names
    user['openid_names'] = list(dict([(name, 0) for name in add_names +
                                      openid_names]))

    try:
        if create_backup:
            # Backup user db before applying any changes to allow roll-back
            db_backup_path = default_db_path(configuration) + '.bck'
            save_user_db(user_db, db_backup_path, do_lock=False)

        user_db[client_id] = user
        sync_gdp_users(configuration, user_db, user, client_id)
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

    return user


def create_user_in_fs(configuration, client_id, user, now, renew, force, verbose):
    """Handle all the parts of user creation or renewal relating to making
    directories and writing default files.
    """
    _logger = configuration.logger
    x509_dir = client_dir = client_id_dir(client_id)
    uuid_dir = unique_id = user.get('unique_id', None)
    # TODO: migrate to use unique_id as actual user dirname everywhere
    #       Symlink old client_dir to unique_id for new users
    #       Symlink unique_id to old client_dir for existing users
    if configuration.site_user_id_format == X509_USER_ID_FORMAT:
        real_dir = x509_dir
        link_dir = uuid_dir
    elif configuration.site_user_id_format == UUID_USER_ID_FORMAT:
        if uuid_dir is None:
            _logger.warning("UUID requested but user lacks unique_id: %s" %
                            mask_creds(user))
        real_dir = uuid_dir
        link_dir = x509_dir
    else:
        raise ValueError("invalid user ID format requested: %s" %
                         configuration.site_user_id_format)
    home_dir = os.path.join(configuration.user_home, real_dir)
    settings_dir = os.path.join(configuration.user_settings, real_dir)
    ssh_dir = os.path.join(home_dir, ssh_conf_dir)
    davs_dir = os.path.join(home_dir, davs_conf_dir)
    ftps_dir = os.path.join(home_dir, ftps_conf_dir)
    htaccess_path = os.path.join(home_dir, htaccess_filename)
    welcome_path = os.path.join(home_dir, welcome_filename)
    settings_path = os.path.join(settings_dir, settings_filename)
    profile_path = os.path.join(settings_dir, profile_filename)
    widgets_path = os.path.join(settings_dir, widgets_filename)
    css_path = os.path.join(home_dir, default_css_filename)
    required_alias_links = _get_required_user_alias_links(configuration,
                                                          real_dir, link_dir)
    required_dir_links = _get_required_user_dir_links(configuration, real_dir,
                                                      link_dir)
    required_dirs = [path[0] for path in required_dir_links] + [ssh_dir,
                                                                davs_dir, ftps_dir]

    # Make sure we set permissions tight enough for e.g. ssh auth keys to work
    os.umask(0o22)

    if not renew:
        if verbose:
            print('Creating dirs and files for new user: %s' % client_id)
        for dir_path in required_dirs:
            try:
                os.mkdir(dir_path)
            except:
                if not force:
                    raise Exception('could not create required dir: %s' %
                                    dir_path)

    else:
        if os.path.exists(htaccess_path):
            # Allow temporary write access
            os.chmod(htaccess_path, 0o644)
        for dir_path in required_dirs:
            try:
                os.makedirs(dir_path)
            except Exception as exc:
                pass

    # Make any missing home links
    for (target_dir, target_link) in required_dir_links:
        if not target_link:
            continue
        _logger.debug("handling link to %s in %s" % (target_dir,
                                                     target_link))
        if os.path.islink(target_link):
            _logger.debug("remove old link in %s" % target_link)
            delete_symlink(target_link, _logger)
        else:
            _logger.debug("make link to %s in %s" % (target_dir, target_link))

        try:
            os.symlink(target_dir, target_link)
        except:
            if not force:
                raise Exception('could not create link to %s in %s' %
                                (target_dir, target_link))

    # Make any missing alias links
    for (target_name, target_link) in required_alias_links:
        if not target_link:
            continue
        _logger.debug("handling aliaslink to %s in %s" % (target_name,
                                                          target_link))
        if os.path.islink(target_link):
            _logger.debug("remove old alias link in %s" % target_link)
            delete_symlink(target_link, _logger)
        else:
            _logger.debug("make alias link to %s in %s" % (target_name,
                                                           target_link))

        try:
            os.symlink(target_name, target_link)
        except:
            if not force:
                raise Exception('could not create alias link to %s in %s' %
                                (target_name, target_link))

    # Always write/update any openid symlinks

    for name in user.get('openid_names', []):
        # short_id is client_id for cert users - skip them
        if name == client_id or name.find(' ') != -1:
            continue
        create_alias_link(name, client_id, configuration.user_home)

    # Always write htaccess to catch any updates

    try:

        # Match certificate or OpenID distinguished name

        info = user.copy()

        # utf8 chars like the \xc3\xb8 are returned as \\xC3\\xB8 in Apache's
        # SSL_CLIENT_S_DN variable, thus we allow both direct dn and mangled
        # match in htaccess

        dn_plain = info['distinguished_name']
        dn_enc = force_native_str(native_str_escape(dn_plain))

        def upper_repl(match):
            """Translate hex codes to upper case form"""
            return '\\x' + match.group(1).upper()

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

        if not write_file(access % info, htaccess_path, _logger, umask=0o033):
            _logger.error("failed to write %s in %s" %
                          (access % info, htaccess_path))
            raise Exception("write htaccess failed!")

        # try to prevent further user modification

        os.chmod(htaccess_path, 0o444)
    except Exception as exc:
        _logger.error("createuser failed to write htaccess: %s" % exc)
        if not force:
            raise Exception('could not create htaccess file: %s'
                            % htaccess_path)

    # Always write welcome message to catch any updates

    welcome_msg = '''Welcome to %(short_title)s!

You should have received information about documentation and various guides to
introduce you to the basic use of the site. The integrated support facilities
link to that material, too.

Feel free to contact our support (%(support_email)s) if you have any questions.

Kind regards,
The %(short_title)s site operators
''' % {'short_title': configuration.short_title,
       'support_email': configuration.support_email}
    _logger.info("write welcome msg in %s" % welcome_path)
    if not write_file(welcome_msg, welcome_path, _logger):
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
    if not renew:
        settings_defaults['USER_INTERFACE'] = configuration.new_user_default_ui
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

    if not os.path.exists(css_path) and not \
            write_file(get_default_css(css_path, _logger, True), css_path, _logger):
        _logger.error("could not write %s" % css_path)
        if not force:
            raise Exception('could not create custom css file: %s' % css_path)


def create_user(user, conf_path, db_path, force=False, verbose=False,
                ask_renew=True, default_renew=False, do_lock=True,
                verify_peer=None, peer_expire_slack=0, from_edit_user=False,
                ask_change_pw=False, auto_create_db=True, create_backup=True):
    """Add user in database and in file system. Distinguishes on the user ID
    format as a first step.
    """

    if conf_path:
        if isinstance(conf_path, basestring):

            # has been checked for accessibility above...

            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

    fill_distinguished_name(user)
    client_id = get_client_id(user)

    # Requested with existing valid account login?
    # Used in order to authorize password change
    authorized = False
    if 'authorized' in user:
        authorized = user['authorized']
        # Always remove any authorized fields before DB insert
        del user['authorized']
    reset_token, reset_auth_type = '', 'UNKNOWN'
    if 'reset_token' in user:
        reset_token = user['reset_token']
        # NOTE: reqX backend saves auth_type in auth list of user dict
        reset_auth_type = user.get('auth', ['UNKNOWN'])[-1]
        # Always remove any reset_token fields before DB insert
        del user['reset_token']

    _logger.info('trying to create or renew user %r' % client_id)
    if verbose:
        print('User ID: %s\n' % client_id)
    now = time.time()
    accepted_peer_list = []
    # NOTE: skip peer check and leave expire alone if valid password reset
    if reset_token:
        _logger.info('skip peer verification and renew in %s password update'
                     % client_id)
        if user.get('peer_pattern', None):
            del user['peer_pattern']
        if user.get('expire', None):
            del user['expire']
    elif verify_peer:
        accepted_peer_list, effective_expire = verify_user_peers(
            configuration, db_path, client_id, user, now, verify_peer,
            peer_expire_slack, force, verbose)
        user['expire'] = effective_expire
        # Save peers in user DB for updates etc. but ignore peer search pattern
        user['peers'] = accepted_peer_list
        if user.get('peer_pattern', None):
            del user['peer_pattern']
    else:
        _logger.info('skip peer verification for %s' % client_id)

    created = create_user_in_db(configuration, db_path, client_id, user, now,
                                authorized, reset_token, reset_auth_type,
                                accepted_peer_list, force, verbose, ask_renew,
                                default_renew, do_lock, from_edit_user,
                                ask_change_pw, auto_create_db, create_backup)
    # Mark user updated for all logins
    update_account_expire_cache(configuration, created)
    update_account_status_cache(configuration, created)

    renew = False
    if created.get('renewed', -1) == now:
        renew = True
    create_user_in_fs(configuration, client_id, created, now, renew, force,
                      verbose)
    mark_user_modified(configuration, client_id)
    _logger.info("created/renewed user %s" % client_id)
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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


def edit_user(client_id, changes, removes, conf_path, db_path, force=False,
              verbose=False, meta_only=False, do_lock=True):
    """Edit user: updates client_id in user DB and on disk with key/val pairs
    from changes dict and deletes any existing dict keys in removes list.
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
    _logger = configuration.logger
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

    client_dir = client_id_dir(client_id)

    _logger.info('trying to edit user %r' % client_id)
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
        for del_field in removes:
            if del_field in user_dict:
                del user_dict[del_field]
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
            _logger.info("Force old user renew to fix any missing files")
            create_user(old_user, conf_path, db_path, force, verbose,
                        ask_renew=False, default_renew=True, do_lock=False,
                        from_edit_user=True, create_backup=True)
            del user_db[client_id]
        elif new_id != client_id:
            if do_lock:
                unlock_user_db(flock)
            raise Exception("Edit aborted: illegal meta_only ID change! %s %s"
                            % (client_id, new_id))
        else:
            _logger.info("Only updating metadata for %s: %s" %
                         (client_id, mask_creds(changes)))

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

    # Make sure new_arch_home doesn't exist already as it'd interfere with move
    if os.path.exists(new_arch_home):
        if os.path.islink(new_arch_home):
            # A previous edit_user created a new_arch_home symlink - clean it
            _logger.info("remove %s link from previous edit" % new_arch_home)
            delete_symlink(new_arch_home, _logger)
        elif os.path.isdir(new_arch_home):
            # A previous sign up probably created a conflicting new_arch_home
            # Merge contents of new_arch_home into old_arch_home before rename
            _logger.info("merging existing %s and %s to avoid conflicts" %
                         (old_arch_home, new_arch_home))
            for name in listdir(new_arch_home):
                sub_src = os.path.join(new_arch_home, name)
                sub_dst = os.path.join(old_arch_home, name)
                move(sub_src, sub_dst)
            # Now remove new_arch_home to avoid old_arch_home ending up inside
            remove_dir(new_arch_home, configuration)
    else:
        _logger.debug("no pending clean up for %s" % new_arch_home)

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
            move(old_path, new_path)
        except Exception as exc:
            if not force:
                raise Exception('could not rename %s to %s: %s'
                                % (old_path, new_path, exc))
    if verbose:
        print('User dirs for %s were successfully renamed!'
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
    # NOTE: only backup user DB here if we didn't already do so in call above
    create_user(user_dict, conf_path, db_path, force, verbose,
                ask_renew=False, default_renew=True, from_edit_user=True,
                create_backup=meta_only)
    _logger.info("Force access map updates to avoid web stall")
    _logger.info("Force update user map")
    force_update_user_map(configuration)
    if configuration.site_enable_resources:
        _logger.info("Force update resource map")
        force_update_resource_map(configuration)
    _logger.info("Force update vgrid map")
    force_update_vgrid_map(configuration)
    return user_dict


def delete_user_in_db(configuration, db_path, client_id, user, force, verbose,
                      do_lock, create_backup):
    """Handle all the parts of user deletion relating to removing database
    entries.
    """
    _logger = configuration.logger
    flock = None
    user_db = {}

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
            _logger.warning("failed to load user db: %s" % err)
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception('Failed to load user DB: %s' % err)

        if client_id not in user_db:
            _logger.warning("user %r not found in user db" % client_id)
            if not force:
                if do_lock:
                    unlock_user_db(flock)
                raise Exception("User DB entry '%s' doesn't exist!"
                                % client_id)

    try:
        if create_backup:
            # Backup user db before applying any changes to allow roll-back
            db_backup_path = default_db_path(configuration) + '.bck'
            save_user_db(user_db, db_backup_path, do_lock=False)

        user_dict = user_db.get(client_id, user)
        del user_db[client_id]
        save_user_db(user_db, db_path, do_lock=False)
        if verbose:
            print('User %s was successfully removed from user DB!' % client_id)
    except Exception as err:
        _logger.error("failed to remove %r from user db: %s" %
                      (client_id, err))
        if not force:
            if do_lock:
                unlock_user_db(flock)
            raise Exception('Failed to remove %s from user DB: %s'
                            % (client_id, err))

    if do_lock:
        unlock_user_db(flock)

    return user_dict


def delete_user_in_fs(configuration, client_id, user, force, verbose):
    """Handle all the parts of user deletion relating to removing directories
    and files.
    """
    _logger = configuration.logger
    x509_dir = client_dir = client_id_dir(client_id)
    uuid_dir = unique_id = user.get('unique_id', None)
    # TODO: migrate to use unique_id as actual user dirname everywhere
    #       Symlink old client_dir to unique_id for new users
    #       Symlink unique_id to old client_dir for existing users
    if configuration.site_user_id_format == X509_USER_ID_FORMAT:
        real_dir = x509_dir
        link_dir = uuid_dir
    elif configuration.site_user_id_format == UUID_USER_ID_FORMAT:
        if uuid_dir is None:
            _logger.warning("UUID requested but user lacks unique_id: %s" %
                            mask_creds(user))
        real_dir = uuid_dir
        link_dir = x509_dir
    else:
        raise ValueError("invalid user ID format requested: %s" %
                         configuration.site_user_id_format)

    required_alias_links = _get_required_user_alias_links(configuration,
                                                          real_dir, link_dir)
    required_dir_links = _get_required_user_dir_links(configuration, real_dir,
                                                      link_dir)
    required_dirs = [path[0] for path in required_dir_links]

    # Remove any OpenID symlinks

    for name in user.get('openid_names', []):
        remove_alias_link(name, configuration.user_home)

    for (_, target_link) in required_alias_links:
        if not target_link:
            continue
        if os.path.islink(target_link):
            delete_symlink(target_link, _logger)

    for (target_dir, target_link) in required_dir_links:
        if not target_link:
            continue
        if os.path.islink(target_link):
            delete_symlink(target_link, _logger)

    # Remove user dirs recursively

    for user_path in required_dirs:
        try:
            remove_rec(user_path, configuration)
        except Exception as exc:
            _logger.error("could not delete %s: %s" % (user_path, exc))
            if not force:
                raise Exception('could not remove %s: %s'
                                % (user_path, exc))

    if verbose:
        print('User dirs for %s were successfully removed!' % client_id)


def delete_user(user, conf_path, db_path, force=False, verbose=False,
                do_lock=True, create_backup=True):
    """Remove user in database and in file system. Distinguishes on the user ID
    format as a first step.
    """

    if conf_path:
        if isinstance(conf_path, basestring):
            configuration = Configuration(conf_path)
        else:
            configuration = conf_path
    else:
        configuration = get_configuration_object()
    _logger = configuration.logger
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

    fill_distinguished_name(user)
    client_id = get_client_id(user)
    if verbose:
        print('User DN: %s\n' % client_id)

    if not force:
        delete_answer = input(
            "Really PERMANENTLY delete %r including user home data? [y/N] " %
            client_id)
        if not delete_answer.lower().startswith('y'):
            raise Exception("Aborted removal of %s from user DB" % client_id)

    _logger.info('trying to delete user %r and all user data' % client_id)

    removed = delete_user_in_db(configuration, db_path, client_id, user, force,
                                verbose, do_lock, create_backup)
    # Mark user deleted for all logins
    update_account_expire_cache(configuration, removed, delete=True)
    update_account_status_cache(configuration, removed, delete=True)

    delete_user_in_fs(configuration, client_id, removed, force, verbose)
    mark_user_modified(configuration, client_id)
    _logger.info("deleted user %r including user dirs" % client_id)
    return removed


def get_openid_user_map(configuration, do_lock=True):
    """Translate user DB to OpenID mapping between a verified login URL and a
    pseudo certificate DN.
    """
    _logger = configuration.logger
    id_map = {}
    db_path = default_db_path(configuration)
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
    _logger.debug('extracting openid dn from %s' % [login_url])
    found_openid_prefix = False
    for oid_provider in configuration.user_openid_providers:
        oid_prefix = oid_provider.rstrip('/') + '/'
        if login_url.startswith(oid_prefix):
            found_openid_prefix = force_native_str(oid_prefix)
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
    _logger.debug("trying openid raw login: %s" % [raw_login])
    # Lookup native user_home from openid user symlink
    link_path = os.path.join(configuration.user_home, raw_login)
    if os.path.islink(link_path):
        native_path = os.path.realpath(link_path)
        native_dir = os.path.basename(native_path)
        _logger.debug("checking native dir %r for login %s" %
                      (native_dir, raw_login))
        if configuration.site_user_id_format == UUID_USER_ID_FORMAT:
            user_id = native_dir
            distinguished_name = lookup_client_id(configuration, user_id)
        elif configuration.site_user_id_format == X509_USER_ID_FORMAT:
            distinguished_name = client_dir_id(native_dir)
        _logger.debug('found full ID %s from %s link'
                      % (distinguished_name, raw_login))
        return distinguished_name
    elif configuration.user_openid_alias:
        db_path = default_db_path(configuration)
        user_map = load_user_db(db_path, do_lock=do_lock)
        user_alias = configuration.user_openid_alias
        # _logger.debug('user_map')
        for (distinguished_name, user) in user_map.items():
            if user[user_alias] in (raw_login, client_alias(raw_login)):
                _logger.debug('found full ID %s from %s alias'
                              % (distinguished_name, raw_login))
                return distinguished_name

    # Fall back to try direct DN (possibly on cert dir form)
    _logger.debug('fall back to direct ID %s from %s' % (raw_login,
                                                         raw_login))
    # Force to dir format and check if user home exists
    cert_dir = client_id_dir(raw_login)
    base_path = os.path.join(configuration.user_home, cert_dir)
    if os.path.isdir(base_path):
        distinguished_name = client_dir_id(cert_dir)
        _logger.debug('accepting direct user %s from %s'
                      % (distinguished_name, raw_login))
        return distinguished_name
    elif not user_check:
        _logger.debug('accepting raw user %s from %s' % (raw_login,
                                                         raw_login))
        return raw_login
    else:
        _logger.error('no such openid user %s: %s' % (cert_dir, raw_login))
        return ''


def get_full_user_map(configuration, do_lock=True):
    """Load complete user map including any OpenID aliases"""
    db_path = default_db_path(configuration)
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
    """Find active OpenID 2.0 session(s) for user with given identity. Queries
    the Apache mod auth openid sqlite database directly.
    """
    query = 'SELECT * FROM sessionmanager WHERE identity=?'
    args = (identity, )
    return __oid_sessions_execute(configuration, db_name, query, args, False)


def expire_oid_sessions(configuration, db_name, identity):
    """Expire active OpenID 2.0 session(s) for user with given identity.
    Modifies the Apache mod auth openid sqlite database directly.
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
                move(old_path, new_path)
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)
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
                        admin_copy=False, extra_copies=False):
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
    if extra_copies:
        addresses['email'] += extra_copies
    return (configuration, fields['username'], fields['full_name'], addresses,
            errors)


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
                        override_policy=None, allow_legacy=False, do_lock=True):
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)
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
            assure_password_strength(configuration, password, allow_legacy)
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
            assure_password_strength(configuration, password, allow_legacy)
        except Exception as exc:
            errors.append('digest for %s does not satisfy local policy: %s'
                          % (user_id, exc))

    return (configuration, errors)


def req_password_check(req_path, conf_path, db_path, verbose=False,
                       override_policy=None, allow_legacy=False):
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)

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
        assure_password_strength(configuration, password, allow_legacy)
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
    if db_path == keyword_auto:
        db_path = default_db_path(configuration)
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


def get_default_mrsl(template_path, logger, allow_missing=True):
    """Return the default mRSL template from template_path"""

    default_mrsl = read_file(template_path, logger,
                             allow_missing=allow_missing)
    if default_mrsl is None:
        # Use default hello grid example
        default_mrsl = """::EXECUTE::
echo 'hello grid!'
echo '...each line here is executed'

::NOTIFY::
email: SETTINGS
jabber: SETTINGS

::INPUTFILES::

::OUTPUTFILES::

::EXECUTABLES::

::MEMORY::
64

::DISK::
1

::CPUTIME::
30

::RUNTIMEENVIRONMENT::

"""
    return default_mrsl


def get_default_css(template_path, logger, allow_missing=True):
    """Return the default css template from template_path"""

    default_css = read_file(template_path, logger, allow_missing=allow_missing)
    if default_css is None:
        # Use default style - i.e. do not override anything

        default_css = '/* No changes - use default */'

    return default_css


def get_authkeys(authkeys_path):
    """Return the authorized keys from authkeys_path"""

    # TODO: use read_file instead
    try:
        authkeys_fd = open(authkeys_path, 'r')
        authorized_keys = authkeys_fd.readlines()
        authkeys_fd.close()
        # Remove extra space / comments and skip blank lines
        authorized_keys = [i.split('#', 1)[0].strip() for i in authorized_keys]
        authorized_keys = [i.strip() for i in authorized_keys if i.strip()]
    except:
        authorized_keys = []
    return authorized_keys


def get_authpasswords(authpasswords_path):
    """Return the non-empty authorized passwords from authpasswords_path"""

    # TODO: use read_file instead
    try:
        authpasswords_fd = open(authpasswords_path, 'r')
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
                        stored_hash, hash_cache=None, strict_policy=True,
                        allow_legacy=False):
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
                          stored_hash, hash_cache, strict_policy, allow_legacy)
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
                            strict_policy=True, allow_legacy=False):
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
                              strict_policy, allow_legacy)
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
                          strict_policy=True, allow_legacy=False):
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
                            stored_digest, salt, digest_cache, strict_policy,
                            allow_legacy)
    except Exception as exc:
        _logger.warning("in check_password_digest: %s" % exc)
        return False
