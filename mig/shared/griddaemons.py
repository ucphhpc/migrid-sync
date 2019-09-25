#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons - grid daemon helper functions
# Copyright (C) 2010-2019  The MiG Project lead by Brian Vinter
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

"""General MiG daemon functions"""

import fnmatch
import glob
import logging
import os
import sys
import socket
import time
import traceback
import threading
import re

from shared.auth import active_twofactor_session
from shared.base import client_dir_id, client_id_dir, client_alias, \
    invisible_path, force_utf8
from shared.defaults import dav_domain, io_session_timeout, \
    CRACK_USERNAME_REGEX
from shared.fileio import unpickle
from shared.gdp import get_client_id_from_project_client_id, \
    get_project_from_user_id
from shared.notification import send_system_notification
from shared.safeinput import valid_path
from shared.settings import load_twofactor
from shared.sharelinks import extract_mode_id
from shared.ssh import parse_pub_key
from shared.twofactorkeywords import get_keywords_dict as twofactor_defaults
from shared.useradm import expand_openid_alias, \
    ssh_authkeys, davs_authkeys, ftps_authkeys, \
    https_authkeys, get_authkeys, ssh_authpasswords, davs_authpasswords, \
    ftps_authpasswords, https_authpasswords, get_authpasswords, \
    ssh_authdigests, davs_authdigests, ftps_authdigests, https_authdigests, \
    generate_password_hash, generate_password_digest, load_user_dict, \
    get_short_id
from shared.validstring import possible_user_id, possible_gdp_user_id, \
    possible_sharelink_id, possible_job_id, possible_jupyter_mount_id, \
    valid_user_path, is_valid_email_address

default_max_user_hits, default_fail_cache = 5, 120
default_user_abuse_hits = 25
default_proto_abuse_hits = 25
default_max_secret_hits = 10

# NOTE: auth keys file may easily contain only blank lines, so we decide to
#       consider any such file of less than a 100 bytes invalid.

min_pub_key_bytes = 100

_rate_limits = {}
_rate_limits_lock = threading.Lock()
_active_sessions = {}
_sessions_lock = threading.Lock()


def accepting_username_validator(configuration, username):
    """A simple username validator which accepts everything"""
    return True


def default_username_validator(configuration, username, force_email=True):
    """The default username validator restricted to only accept usernames that
    are valid in grid daemons, namely a possible user, sharelink, job or
    jupyter mount ID.
    The optional and default enabled force_email option is used to further
    limit user_id values to actual email addresses, as always required in grid
    daemons.
    """
    logger = configuration.logger
    # logger.debug("username: %s, force_email: %s" % (username, force_email))

    if possible_gdp_user_id(configuration, username):
        return True
    elif possible_user_id(configuration, username):
        if not force_email:
            return True
        elif is_valid_email_address(username, configuration.logger):
            return True
    if possible_sharelink_id(configuration, username):
        return True
    if possible_job_id(configuration, username):
        return True
    if possible_jupyter_mount_id(configuration, username):
        return True
    return False


class Login(object):
    """Login class to hold a single valid login for a user, job or share.

    The login method can be one of password, password digest or public key.
    The optional chroot marks the login for chrooting to the user home.
    The optional ip_addr argument can be used to limit login source to a single
    IP address. This is particularly useful in relation to job sshfs mounts.
    """

    def __init__(self,
                 configuration,
                 username,
                 home,
                 password=None,
                 digest=None,
                 public_key=None,
                 chroot=True,
                 ip_addr=None,
                 user_dict=None):
        self.username = username
        self.password = password
        self.digest = digest
        self.public_key = public_key
        self.chroot = chroot
        self.ip_addr = ip_addr
        self.user_dict = user_dict
        self.last_update = time.time()
        if type(public_key) in (str, unicode):
            # We already checked that key is valid if we got here
            self.public_key = parse_pub_key(public_key)
        self.home = home
        if self.home is None:
            self.home = self.username

    def __str__(self):
        """Byte string formater - username is already forced to utf8 so other
        strings are converted here as well.
        """
        out = '''username: %s
home: %s''' % (self.username, self.home)
        if self.password:
            out += '''
password: %s''' % force_utf8(self.password)
        if self.digest:
            out += '''
digest: %s''' % force_utf8(self.digest)
        if self.public_key:
            out += '''
pubkey: %s''' % force_utf8(self.public_key.get_base64())
        out += '''
last_update: %s''' % self.last_update
        return out


def get_fs_path(configuration, abs_path, root, chroot_exceptions):
    """Internal helper to translate path with chroot and invisible files
    in mind. Also assures general path character restrictions are applied.
    Automatically expands to abs path to avoid traversal issues with e.g.
    MYVGRID/../bla that would expand to vgrid_files_home/bla instead of bla
    in user home if left as is.
    """
    try:
        valid_path(abs_path)
    except:
        raise ValueError("Invalid path characters")

    if not valid_user_path(configuration, abs_path, root, True,
                           chroot_exceptions):
        raise ValueError("Illegal path access attempt")
    return abs_path


def strip_root(configuration, path, root, chroot_exceptions):
    """Internal helper to strip root prefix for chrooted locations"""
    accept_roots = [root] + chroot_exceptions
    for root in accept_roots:
        if path.startswith(root):
            return path.replace(root, '')
    return path


def flags_to_mode(flags):
    """Internal helper to convert bitmask of os.O_* flags to open-mode.

    It only handles read, write and append with and without truncation.
    Append and write always creates the file if missing, so checking for
    missing file creation flag should generally be handled separately.
    The same goes for handling of invalid flag combinations.

    This function is inspired by the XMP example in the fuse-python code
    http://sourceforge.net/apps/mediawiki/fuse/index.php?title=Main_Page
    but we need to prevent truncation unless explicitly requested.
    """
    # Truncate per default when enabling write - disable later if needed
    main_modes = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    mode = main_modes[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags & os.O_APPEND:
        mode = mode.replace('w', 'a', 1)
    # Disable truncation unless explicitly requested
    if not (flags & os.O_TRUNC):
        mode = mode.replace('w+', 'r+', 1)
        mode = mode.replace('w', 'r+', 1)
    return mode


def acceptable_chmod(path, mode, chmod_exceptions):
    """Internal helper to check that a chmod request is safe. That is, it
    only changes permissions that does not lock out user. Furthermore anything
    we deem invisible_path or inside the dirs in chmod_exceptions should be
    left alone to avoid users touching read-only files or enabling execution
    of custom cgi scripts with potentially arbitrary code.
    We require preservation of user read+write on files and user
    read+write+execute on dirs.
    Limitation to sane group/other access perms is left to the caller.
    """

    if invisible_path(path) or \
        True in [os.path.realpath(path).startswith(i) for i in
                 chmod_exceptions]:
        return False
    # Never touch special leading bits (suid, sgid, etc.)
    if mode & 07000 != 00000:
        return False
    if os.path.isfile(path) and mode & 0600 == 0600:
        return True
    elif os.path.isdir(path) and mode & 0700 == 0700:
        return True
    else:
        return False


def get_creds_changes(conf, username, authkeys_path, authpasswords_path,
                      authdigests_path):
    """Check if creds changed for username using the provided auth files and
    the saved time stamp from users embedded in conf.
    Returns a list of changed auth files with the empty list if none changed.
    """
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    old_users = [i for i in conf['users'] if i.username == username]
    if creds_lock:
        creds_lock.release()
    old_key_users = [i for i in old_users if i.public_key]
    old_pw_users = [i for i in old_users if i.password]
    old_digest_users = [i for i in old_users if i.digest]
    # We do not save user entry for key files without proper pub keys, so to
    # avoid repeatedly refreshing keys for such users we check against any
    # other last update marker in case of no matching key users.
    any_last_update = -1
    if old_users:
        any_last_update = old_users[0].last_update
    changed_paths = []
    if conf["allow_publickey"]:
        if old_key_users:
            first = old_key_users[0]
            if not os.path.exists(authkeys_path):
                changed_paths.append(authkeys_path)
            elif os.path.getmtime(authkeys_path) > first.last_update:
                first.last_update = os.path.getmtime(authkeys_path)
                changed_paths.append(authkeys_path)
        elif os.path.exists(authkeys_path) and \
                os.path.getsize(authkeys_path) >= min_pub_key_bytes and \
                os.path.getmtime(authkeys_path) > any_last_update:
            # logger.debug("found changed pub keys for %s" % username)
            changed_paths.append(authkeys_path)

    if conf["allow_password"]:
        if old_pw_users:
            first = old_pw_users[0]
            if not os.path.exists(authpasswords_path):
                changed_paths.append(authpasswords_path)
            elif os.path.getmtime(authpasswords_path) > first.last_update:
                first.last_update = os.path.getmtime(authpasswords_path)
                changed_paths.append(authpasswords_path)
        elif os.path.exists(authpasswords_path) and \
                os.path.getsize(authpasswords_path) > 0:
            changed_paths.append(authpasswords_path)

    if conf["allow_digest"]:
        if old_digest_users:
            first = old_digest_users[0]
            if not os.path.exists(authdigests_path):
                logger.info("no authdigests_path %s" % authdigests_path)
                changed_paths.append(authdigests_path)
            elif os.path.getmtime(authdigests_path) > first.last_update:
                logger.info("outdated authdigests_path %s (%s)" %
                            (authdigests_path, first.last_update))
                first.last_update = os.path.getmtime(authdigests_path)
                changed_paths.append(authdigests_path)
        elif os.path.exists(authdigests_path) and \
                os.path.getsize(authdigests_path) > 0:
            logger.info("no old digest users and found authdigests_path %s" %
                        authdigests_path)
            logger.info("old users: %s" % ["%s" % i for i in old_users])
            changed_paths.append(authdigests_path)

    return changed_paths


def get_job_changes(conf, username, mrsl_path):
    """Check if job mount changed for username using the provided mrsl_path
    file and the saved time stamp from jobs embedded in conf.
    Returns a list of changed mrsl files with the empty list if none changed.
    """
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    old_users = [i for i in conf['jobs'] if i.username == username]
    if creds_lock:
        creds_lock.release()
    changed_paths = []
    if old_users:
        first = old_users[0]
        if not os.path.exists(mrsl_path):
            changed_paths.append(mrsl_path)
        elif os.path.getmtime(mrsl_path) > first.last_update:
            first.last_update = os.path.getmtime(mrsl_path)
            changed_paths.append(mrsl_path)
    elif os.path.exists(mrsl_path) and \
            os.path.getsize(mrsl_path) > 0:
        changed_paths.append(mrsl_path)
    return changed_paths


def get_share_changes(conf, username, sharelink_path):
    """Check if sharelink changed for username using the provided
    sharelink_path file and the saved time stamp from shares embedded in conf.
    Returns a list of changed sharelink files with the empty list if none
    changed.
    """
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    old_users = [i for i in conf['shares'] if i.username == username]
    if creds_lock:
        creds_lock.release()
    changed_paths = []
    if old_users:
        first = old_users[0]
        if not os.path.exists(sharelink_path):
            changed_paths.append(sharelink_path)
        elif os.path.getmtime(sharelink_path) > first.last_update:
            first.last_update = os.path.getmtime(sharelink_path)
            changed_paths.append(sharelink_path)
    elif os.path.exists(sharelink_path) and \
            os.path.isdir(sharelink_path):
        changed_paths.append(sharelink_path)
    return changed_paths


def add_user_object(configuration,
                    login,
                    home,
                    password=None,
                    digest=None,
                    pubkey=None,
                    chroot=True,
                    user_dict=None):
    """Add a single Login object to active user list"""
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    user = Login(configuration,
                 username=login,
                 home=home,
                 password=password,
                 digest=digest,
                 public_key=pubkey,
                 chroot=chroot,
                 user_dict=user_dict)
    # logger.debug("Adding user login:\n%s" % user)
    if creds_lock:
        creds_lock.acquire()
    conf['users'].append(user)
    if creds_lock:
        creds_lock.release()


def add_job_object(configuration,
                   login,
                   home,
                   password=None,
                   digest=None,
                   pubkey=None,
                   chroot=True,
                   ip_addr=None):
    """Add a single Login object to active jobs list"""
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    job = Login(configuration,
                username=login,
                home=home,
                password=password,
                digest=digest,
                public_key=pubkey,
                chroot=chroot,
                ip_addr=ip_addr)
    # logger.debug("Adding job login:\n%s" % job)
    if creds_lock:
        creds_lock.acquire()
    conf['jobs'].append(job)
    if creds_lock:
        creds_lock.release()


def add_share_object(configuration, login, home, password=None, digest=None,
                     pubkey=None, chroot=True, ip_addr=None):
    """Add a single Login object to active shares list"""
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    share = Login(configuration,
                  username=login,
                  home=home,
                  password=password,
                  digest=digest,
                  public_key=pubkey,
                  chroot=chroot,
                  ip_addr=ip_addr)
    # logger.debug("Adding share login:\n%s" % share)
    if creds_lock:
        creds_lock.acquire()
    conf['shares'].append(share)
    if creds_lock:
        creds_lock.release()


def add_jupyter_object(configuration, login, home, password=None, digest=None,
                       pubkey=None, chroot=True, ip_addr=None):
    """Add a single Login object to active jupyter mount list"""
    conf = configuration.daemon_conf
    logger = conf.get('logger', logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    jupyter_mount = Login(configuration,
                          username=login,
                          home=home,
                          password=password,
                          digest=digest,
                          public_key=pubkey,
                          chroot=chroot,
                          ip_addr=ip_addr)
    # logger.debug("Adding jupyter login:\n%s" % jupyter_mount)
    if creds_lock:
        creds_lock.acquire()
    conf['jupyter_mounts'].append(jupyter_mount)
    if creds_lock:
        creds_lock.release()


def update_user_objects(configuration, auth_file, path, user_vars, auth_protos,
                        private_auth_file):
    """Update login objects for auth_file with path to conf users dict. Remove
    any old entries for user and add the current ones.
    If private_auth_file is false we have to treat auth_file as a MiG user DB
    rather than the private credential files in user homes.
    """
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    proto_authkeys, proto_authpasswords, proto_authdigests = auth_protos
    user_id, user_alias, user_dir, short_id, short_alias = user_vars
    user_logins = (user_alias, short_id, short_alias)
    user_dict = None

    # Create user entry for each valid key and password
    if creds_lock:
        creds_lock.acquire()
    if not private_auth_file:
        user_dict = load_user_dict(logger, user_id, conf['db_path'])
    if auth_file == proto_authkeys:
        if private_auth_file:
            all_keys = get_authkeys(path)
        elif user_dict and user_dict.get('keys', ''):
            # NOTE: already a list
            all_keys = user_dict['keys']
        else:
            all_keys = []
        all_passwords = []
        all_digests = []
        # Clean up all old key entries for this user
        conf['users'] = [i for i in conf['users']
                         if not i.username in user_logins or
                         i.public_key is None]
    elif auth_file == proto_authpasswords:
        all_keys = []
        if private_auth_file:
            all_passwords = get_authpasswords(path)
        # Prefer password hash if available, otherwise fall back to scrambled
        elif user_dict and user_dict.get('password_hash', ''):
            all_passwords = [user_dict['password_hash']]
        elif user_dict and user_dict.get('password', ''):
            all_passwords = [user_dict['password']]
        else:
            all_passwords = []
        all_digests = []
        # Clean up all old password entries for this user
        conf['users'] = [i for i in conf['users']
                         if not i.username in user_logins or
                         i.password is None]
    else:
        all_keys = []
        all_passwords = []
        if private_auth_file:
            all_digests = get_authpasswords(path)
        elif user_dict and user_dict.get('digest', ''):
            all_digests = [user_dict['digest']]
        else:
            all_digests = []
        # Clean up all old digest entries for this user
        conf['users'] = [i for i in conf['users']
                         if not i.username in user_logins or
                         i.digest is None]
    # logger.debug("after clean up old users list is:\n%s" % \
    #             '\n'.join(["%s" % i for i in conf['users']]))
    if creds_lock:
        creds_lock.release()
    for user_key in all_keys:
        # Remove comments and blank lines
        user_key = user_key.split('#', 1)[0].strip()
        if not user_key:
            continue
        # Make sure pub key is valid
        try:
            _ = parse_pub_key(user_key)
        except Exception, exc:
            logger.warning("Skipping broken key %s for user %s (%s)" %
                           (user_key, user_id, exc))
            continue
        add_user_object(configuration, user_alias, user_dir, pubkey=user_key)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(configuration,
                            short_id,
                            user_dir,
                            pubkey=user_key,
                            user_dict=user_dict)
            add_user_object(configuration,
                            short_alias,
                            user_dir,
                            pubkey=user_key,
                            user_dict=user_dict)
    for user_password in all_passwords:
        user_password = user_password.strip()
        add_user_object(configuration,
                        user_alias,
                        user_dir,
                        password=user_password,
                        user_dict=user_dict)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(configuration,
                            short_id,
                            user_dir,
                            password=user_password,
                            user_dict=user_dict)
            add_user_object(configuration,
                            short_alias,
                            user_dir,
                            password=user_password,
                            user_dict=user_dict)
    for user_digest in all_digests:
        user_digest = user_digest.strip()
        add_user_object(configuration,
                        user_alias,
                        user_dir,
                        digest=user_digest,
                        user_dict=user_dict)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(configuration,
                            short_id,
                            user_dir,
                            digest=user_digest,
                            user_dict=user_dict)
            add_user_object(configuration,
                            short_alias,
                            user_dir,
                            digest=user_digest,
                            user_dict=user_dict)
    # logger.debug("after update users list is:\n%s" % \
    #             '\n'.join(["%s" % i for i in conf['users']]))


def refresh_user_creds(configuration, protocol, username):
    """Reload user credentials for username if they changed on disk. That is,
    add user entries in configuration.daemon_conf['users'] for all active keys
    and passwords enabled in configuration. Optionally add short ID username
    alias entries for user if that is enabled in the configuration.
    Removes all aliased user entries if the user is no longer active, too.
    The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed user
    IDs.

    NOTE: username must be the direct username used in home dir or an OpenID
    alias with associated symlink there. Encoded username aliases must be
    decoded before use here.
    """
    changed_users = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    private_auth_file = True
    if protocol in ('ssh', 'sftp', 'scp', 'rsync'):
        proto_authkeys = ssh_authkeys
        proto_authpasswords = ssh_authpasswords
        proto_authdigests = ssh_authdigests
    elif protocol in ('dav', 'davs'):
        proto_authkeys = davs_authkeys
        proto_authpasswords = davs_authpasswords
        proto_authdigests = davs_authdigests
    elif protocol in ('ftp', 'ftps'):
        proto_authkeys = ftps_authkeys
        proto_authpasswords = ftps_authpasswords
        proto_authdigests = ftps_authdigests
    elif protocol in ('https', 'openid'):
        private_auth_file = False
        proto_authkeys = https_authkeys
        proto_authpasswords = https_authpasswords
        proto_authdigests = https_authdigests
    else:
        logger.error("Invalid protocol: %s" % protocol)
        return (conf, changed_users)

    auth_protos = (proto_authkeys, proto_authpasswords, proto_authdigests)

    # We support direct and symlinked usernames for now
    # NOTE: entries are gracefully removed if user no longer exists
    if private_auth_file:
        authkeys_path = os.path.realpath(os.path.join(conf['root_dir'],
                                                      username,
                                                      proto_authkeys))
        authpasswords_path = os.path.realpath(os.path.join(
            conf['root_dir'], username, proto_authpasswords))
        authdigests_path = os.path.realpath(os.path.join(conf['root_dir'],
                                                         username,
                                                         proto_authdigests))
    else:
        authkeys_path = authpasswords_path = authdigests_path = conf['db_path']

    # logger.debug("Updating user creds for %s" % username)

    changed_paths = get_creds_changes(conf, username, authkeys_path,
                                      authpasswords_path, authdigests_path)
    if not changed_paths:
        # logger.debug("No user creds changes for %s" % username)
        return (conf, changed_users)

    short_id, short_alias = None, None
    matches = []
    if conf['allow_publickey']:
        matches += [(proto_authkeys, authkeys_path)]
    if conf['allow_password']:
        matches += [(proto_authpasswords, authpasswords_path)]
    if conf['allow_digest']:
        matches += [(proto_authdigests, authdigests_path)]
    for (auth_file, path) in matches:
        if not path in changed_paths:
            # logger.debug("Skipping %s without changes" % path)
            continue
        # Missing alias symlink - should be fixed for user instead
        if not os.path.exists(path):
            logger.warning("Skipping non-existant auth path %s" % path)
            continue
        # logger.debug("Checking %s" % path)
        if private_auth_file:
            user_home = path.replace(os.sep + auth_file, '')
            user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        else:
            # Expand actual user home from alias
            user_home = os.path.realpath(os.path.join(configuration.user_home,
                                                      username))
            user_dir = os.path.basename(user_home)

        # Check that user home exists
        if not os.path.exists(user_home):
            logger.warning("Skipping user without home %s" % user_home)
            continue

        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        if conf['user_alias']:
            short_id = get_short_id(configuration, user_id, conf['user_alias'])
            # Allow both raw alias field value and asciified alias
            # logger.debug("find short_alias for %s" % short_id)
            short_alias = client_alias(short_id)
        # In GDP-mode user must be chrooted to project home for IO daemons
        # but obviously not for the OpenID login prior to project login.
        if configuration.site_enable_gdp and private_auth_file and \
                protocol != 'openid':
            project_name = get_project_from_user_id(configuration, user_id)
            if not project_name:
                logger.warning("Skipping invalid GDP user %s" % user_id)
                continue
            user_dir = os.path.join(user_dir, project_name)
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(configuration,
                            auth_file,
                            path,
                            user_vars,
                            auth_protos,
                            private_auth_file)
    if changed_paths:
        logger.info("Refreshed user %s from configuration: %s" %
                    (username, changed_paths))
        changed_users.append(username)
    return (conf, changed_users)


def refresh_users(configuration, protocol):
    """Reload all users from auth confs if they changed on disk.
    Add user entries to configuration.daemon_conf['users']
    for all active keys and passwords enabled in configuration.
    Optionally add short ID username alias entries for all users
    if that is enabled in the configuration.
    Removes all the user entries no longer active, too.
    The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed user
    IDs.
    NOTE: Deprecated due to severe system load, use refresh_user_creds instead
    """
    changed_users = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    last_update = conf['time_stamp']
    if creds_lock:
        creds_lock.acquire()
    old_usernames = [i.username for i in conf['users']]
    if creds_lock:
        creds_lock.release()
    cur_usernames = []
    private_auth_file = True
    if protocol in ('ssh', 'sftp', 'scp', 'rsync'):
        proto_authkeys = ssh_authkeys
        proto_authpasswords = ssh_authpasswords
        proto_authdigests = ssh_authdigests
    elif protocol in ('dav', 'davs'):
        proto_authkeys = davs_authkeys
        proto_authpasswords = davs_authpasswords
        proto_authdigests = davs_authdigests
    elif protocol in ('ftp', 'ftps'):
        proto_authkeys = ftps_authkeys
        proto_authpasswords = ftps_authpasswords
        proto_authdigests = ftps_authdigests
    elif protocol in ('https', 'openid'):
        private_auth_file = False
        proto_authkeys = https_authkeys
        proto_authpasswords = https_authpasswords
        proto_authdigests = https_authdigests
    else:
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_users)

    auth_protos = (proto_authkeys, proto_authpasswords, proto_authdigests)

    authkeys_pattern = os.path.join(conf['root_dir'], '*', proto_authkeys)
    authpasswords_pattern = os.path.join(conf['root_dir'], '*',
                                         proto_authpasswords)
    authdigests_pattern = os.path.join(conf['root_dir'], '*',
                                       proto_authdigests)
    short_id, short_alias = None, None
    # TODO: support private_auth_file == False here?
    matches = []
    if conf['allow_publickey']:
        matches += [(proto_authkeys, i) for i in glob.glob(authkeys_pattern)]
    if conf['allow_password']:
        matches += [(proto_authpasswords, i)
                    for i in glob.glob(authpasswords_pattern)]
    if conf['allow_digest']:
        matches += [(proto_authdigests, i)
                    for i in glob.glob(authdigests_pattern)]
    for (auth_file, path) in matches:
        user_home = path.replace(os.sep + auth_file, '')
        # Skip OpenID alias symlinks
        if os.path.islink(user_home):
            continue
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        # we always accept asciified distinguished name
        cur_usernames.append(user_alias)
        if conf['user_alias']:
            short_id = get_short_id(configuration, user_id, conf['user_alias'])
            # Allow both raw alias field value and asciified alias
            cur_usernames.append(short_id)
            # logger.debug("find short_alias for %s" % short_id)
            short_alias = client_alias(short_id)
            cur_usernames.append(short_alias)
        if last_update >= os.path.getmtime(path):
            continue
        # In GDP-mode user must be chrooted to project home for IO daemons
        # but obviously not for the OpenID login prior to project login.
        if configuration.site_enable_gdp and private_auth_file and \
                protocol != 'openid':
            project_name = get_project_from_user_id(configuration, user_id)
            user_dir = os.path.join(user_dir, project_name)
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(configuration,
                            auth_file,
                            path,
                            user_vars,
                            auth_protos,
                            private_auth_file)
        changed_users += [user_id, user_alias]
        if short_id is not None:
            changed_users += [short_id, short_alias]
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d deleted users" % len(removed))
        if creds_lock:
            creds_lock.acquire()
        conf['users'] = [i for i in conf['users'] if not i.username in removed]
        if creds_lock:
            creds_lock.release()
        changed_users += removed
    logger.info("Refreshed users from configuration (%d users)" %
                len(cur_usernames))
    conf['time_stamp'] = time.time()
    return (conf, changed_users)


def refresh_job_creds(configuration, protocol, username):
    """Reload job credentials for username (SESSIONID) if they changed on disk.
    That is, add user entries in configuration.daemon_conf['jobs'] for any
    corresponding active job keys.
    Removes all job login entries if the job is no longer active, too.
    The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed job
    IDs.
    """
    changed_jobs = []
    conf = configuration.daemon_conf
    last_update = conf['time_stamp']
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if not protocol in ('sftp',):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_jobs)
    if not possible_job_id(configuration, username):
        # logger.debug("ruled out %s as a possible job ID" % username)
        return (conf, changed_jobs)

    link_path = os.path.join(configuration.sessid_to_mrsl_link_home,
                             "%s.mRSL" % username)
    # logger.debug("Updating job creds for %s" % username)
    changed_paths = get_job_changes(conf, username, link_path)
    if not changed_paths:
        # logger.debug("No job creds changes for %s" % username)
        return (conf, changed_jobs)

    job_dict = None
    if os.path.islink(link_path) and os.path.exists(link_path) and \
            last_update < os.path.getmtime(link_path):
        sessionid = username
        job_dict = unpickle(link_path, logger)

    # We only allow connections from executing jobs that
    # has a public key
    if job_dict is not None and isinstance(job_dict, dict) and \
            job_dict.has_key('STATUS') and \
            job_dict['STATUS'] == 'EXECUTING' and \
            job_dict.has_key('SESSIONID') and \
            job_dict['SESSIONID'] == sessionid and \
            job_dict.has_key('USER_CERT') and \
            job_dict.has_key('MOUNT') and \
            job_dict.has_key('MOUNTSSHPUBLICKEY'):
        user_alias = sessionid
        user_dir = client_id_dir(job_dict['USER_CERT'])
        user_key = job_dict['MOUNTSSHPUBLICKEY']
        user_ip = None

        # Use frontend proxy if available otherwise use hosturl to resolve IP
        user_url = job_dict['RESOURCE_CONFIG'].get('FRONTENDPROXY', '')
        if user_url:
            user_url = job_dict['RESOURCE_CONFIG'].get('HOSTURL', '')
        try:
            user_ip = socket.gethostbyname_ex(user_url)[2][0]
        except Exception, exc:
            user_ip = None
            logger.warning("Skipping key, unresolvable ip for user %s (%s)" %
                           (user_alias, exc))

        # Make sure pub key is valid
        valid_pubkey = True
        try:
            _ = parse_pub_key(user_key)
        except Exception, exc:
            valid_pubkey = False
            logger.warning("Skipping broken key '%s' for user %s (%s)" %
                           (user_key, user_alias, exc))

        if user_ip is not None and valid_pubkey:
            add_job_object(configuration,
                           user_alias,
                           user_dir,
                           pubkey=user_key,
                           ip_addr=user_ip)
            changed_jobs.append(user_alias)

    # Job inative: remove from logins and mark as changed
    if not changed_jobs:
        logger.info("Removing login(s) for inactive job %s" % username)
        if creds_lock:
            creds_lock.acquire()
        conf['jobs'] = [i for i in conf['jobs'] if i.username != username]
        if creds_lock:
            creds_lock.release()
        changed_jobs.append(username)
    logger.info("Refreshed jobs from configuration")
    return (conf, changed_jobs)


def refresh_jobs(configuration, protocol):
    """Refresh job keys based on the job state.
    Add user entries for all active job keys.
    Removes all the user entries for jobs no longer active.
    Returns a tuple with the daemon_conf and the list of changed job IDs.
    NOTE: Deprecated due to severe system load, use refresh_job_creds instead
    """
    changed_jobs = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    old_usernames = [i.username for i in conf['jobs']]
    if creds_lock:
        creds_lock.release()
    cur_usernames = []
    if not protocol in ('sftp', ):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_jobs)

    for link_name in os.listdir(configuration.sessid_to_mrsl_link_home):
        link_path = os.path.join(configuration.sessid_to_mrsl_link_home,
                                 link_name)

        job_dict = None
        if os.path.islink(link_path) and link_path.endswith('.mRSL') and \
                os.path.exists(link_path):
            sessionid = link_name[:-5]
            job_dict = unpickle(link_path, logger)

        # We only allow connections from executing jobs that
        # has a public key
        if job_dict is not None and isinstance(job_dict, dict) and \
                job_dict.has_key('STATUS') and \
                job_dict['STATUS'] == 'EXECUTING' and \
                job_dict.has_key('SESSIONID') and \
                job_dict['SESSIONID'] == sessionid and \
                job_dict.has_key('USER_CERT') and \
                job_dict.has_key('MOUNT') and \
                job_dict.has_key('MOUNTSSHPUBLICKEY'):
            user_alias = sessionid
            user_dir = client_id_dir(job_dict['USER_CERT'])
            user_key = job_dict['MOUNTSSHPUBLICKEY']
            user_ip = None

            # Use frontend proxy if available
            # otherwise use hosturl to resolve IP
            user_url = job_dict['RESOURCE_CONFIG'].get('FRONTENDPROXY', '')
            if user_url:
                user_url = job_dict['RESOURCE_CONFIG'].get('HOSTURL', '')
            try:
                user_ip = socket.gethostbyname_ex(user_url)[2][0]
            except Exception, exc:
                user_ip = None
                msg = "Skipping key due to unresolvable ip" \
                    + " for user %s (%s)" % (user_alias, exc)
                logger.warning(msg)

            # Make sure pub key is valid
            valid_pubkey = True
            try:
                _ = parse_pub_key(user_key)
            except Exception, exc:
                valid_pubkey = False
                logger.warning("Skipping broken key '%s' for user %s (%s)" %
                               (user_key, user_alias, exc))

            if user_ip is not None and valid_pubkey:
                add_job_object(configuration,
                               user_alias,
                               user_dir,
                               pubkey=user_key,
                               ip_addr=user_ip)
                cur_usernames.append(user_alias)
                changed_jobs.append(user_alias)

    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d finished jobs" % len(removed))
        if creds_lock:
            creds_lock.acquire()
        conf['jobs'] = [i for i in conf['jobs'] if not i.username in removed]
        if creds_lock:
            creds_lock.release()
        changed_jobs += removed
    logger.info("Refreshed jobs from configuration (%d jobs)" %
                len(cur_usernames))
    return (conf, changed_jobs)


def refresh_share_creds(configuration, protocol, username,
                        share_modes=['read-write']):
    """Reload sharelink credentials for username (SHARE_ID) if they changed on
    disk. That is, add user entries in configuration.daemon_conf['shares'] for
    any corresponding active sharelinks.
    Removes all sharelink login entries if the sharelink is no longer active,
    too. The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed share
    IDs.
    NOTE: we limit share_modes to read-write sharelinks for now since we don't
    have guards in place to support read-only or write-only mode in daemons.
    NOTE: we further limit to directory sharelinks for chroot'ing.
    """
    # Must end in sep
    base_dir = configuration.user_home.rstrip(os.sep) + os.sep
    changed_shares = []
    conf = configuration.daemon_conf
    last_update = conf['time_stamp']
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if not protocol in ('sftp', 'davs', 'ftps', ):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_shares)
    if [kind for kind in share_modes if kind != 'read-write']:
        logger.error("invalid share_modes: %s" % share_modes)
        return (conf, changed_shares)
    if not possible_sharelink_id(configuration, username):
        # logger.debug("ruled out %s as a possible sharelink ID" % username)
        return (conf, changed_shares)

    try:
        (mode, _) = extract_mode_id(configuration, username)
    except ValueError, err:
        logger.error('refresh share creds called with invalid username %s: %s'
                     % (username, err))
        mode = 'INVALID-SHARELINK'
    if not mode in share_modes:
        logger.error("invalid share mode %s for %s" % (mode, username))
        return (conf, changed_shares)

    # logger.debug("Updating share creds for %s" % username)
    link_path = os.path.join(configuration.sharelink_home, mode, username)
    changed_paths = get_share_changes(conf, username, link_path)
    if not changed_paths:
        # logger.debug("No share creds changes for %s" % username)
        return (conf, changed_shares)

    try:
        link_dest = os.readlink(link_path)
        if not link_dest.startswith(base_dir):
            raise ValueError("Invalid base for share: %s" % link_dest)
        if not os.path.isdir(link_dest):
            raise ValueError("Unsupported single-file share: %s" % link_dest)
    except Exception, err:
        link_dest = None
        # IMPORTANT: log but don't return as we need to remove user below
        logger.error("invalid share %s: %s" % (username, err))

    share_dict = None
    if os.path.islink(link_path) and link_dest and \
            last_update < os.path.getmtime(link_path):
        share_id = username
        # NOTE: share link points inside user home of owner so we extract here.
        #       We strip leading AND trailing slashes to make get_fs_path work.
        #       Otherwise it would choke on shares with trailing slash in path.
        share_root = link_dest.replace(base_dir, '').strip(os.sep)
        # NOTE: just use share_id as password/digest for now
        share_pw_hash = generate_password_hash(configuration, share_id)
        share_pw_digest = generate_password_digest(
            configuration, dav_domain, share_id, share_id,
            configuration.site_digest_salt)
        # TODO: load pickle from user_settings of owner (from link_dest)?
        share_dict = {'share_id': share_id, 'share_root': share_root,
                      'share_pw_hash': share_pw_hash,
                      'share_pw_digest': share_pw_digest}

    # We only allow access to active shares
    if share_dict is not None and isinstance(share_dict, dict) and \
            share_dict.has_key('share_id') and \
            share_dict.has_key('share_root') and \
            share_dict.has_key('share_pw_hash') and \
            share_dict.has_key('share_pw_digest'):
        user_alias = share_dict['share_id']
        user_dir = share_dict['share_root']
        user_password = share_dict['share_pw_hash']
        user_digest = share_dict['share_pw_digest']
        logger.info("Adding login for share %s" % user_alias)
        add_share_object(configuration,
                         user_alias,
                         user_dir,
                         password=user_password,
                         digest=user_digest)
        changed_shares.append(user_alias)

    # Share was removed: remove from logins and mark as changed
    if not changed_shares:
        logger.info("Removing login(s) for inactive share %s" % username)
        if creds_lock:
            creds_lock.acquire()
        conf['shares'] = [i for i in conf['shares'] if i.username != username]
        if creds_lock:
            creds_lock.release()
        changed_shares.append(username)
    logger.info("Refreshed shares from configuration")
    return (conf, changed_shares)


def refresh_shares(configuration, protocol, share_modes=['read-write']):
    """Refresh shares keys based on the sharelink state.
    Add user entries for all active sharelinks.
    Removes all the user entries for sharelinks no longer active.
    Returns a tuple with the daemon_conf and the list of changed sharelink IDs.
    NOTE: we limit share_modes to read-write sharelinks for now since we don't
    have guards in place to support read-only or write-only mode in daemons.
    NOTE: we further limit to directory sharelinks for chroot'ing.
    NOTE: Deprecated due to severe system load, use refresh_share_creds instead
    """
    # Must end in sep
    base_dir = configuration.user_home.rstrip(os.sep) + os.sep
    changed_shares = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    old_usernames = [i.username for i in conf['shares']]
    if creds_lock:
        creds_lock.release()
    cur_usernames = []
    if not protocol in ('sftp', 'davs', 'ftps', ):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_shares)
    if [kind for kind in share_modes if kind != 'read-write']:
        logger.error("invalid share_modes: %s" % share_modes)
        return (conf, changed_shares)

    for link_name in os.listdir(configuration.sharelink_home):
        link_path = os.path.join(configuration.sharelink_home, link_name)
        try:
            link_dest = os.readlink(link_path)
            if not link_dest.startswith(base_dir):
                raise ValueError("Invalid base for share %s" % link_name)
        except Exception, err:
            logger.error("invalid share %s: %s" % (link_name, err))
            continue
        (mode, _) = extract_mode_id(configuration, link_name)
        if not mode in share_modes:
            logger.info("invalid share mode %s for %s" % (mode, link_name))
            continue
        share_dict = None
        if os.path.islink(link_path) and os.path.isdir(link_dest):
            share_id = link_name
            # NOTE: share link points inside user home of owner so extract here
            share_root = link_dest.replace(base_dir, '').lstrip(os.sep)
            # NOTE: just use share_id as password/digest for now
            share_pw_hash = generate_password_hash(configuration, share_id)
            share_pw_digest = generate_password_digest(
                configuration, dav_domain, share_id, share_id,
                configuration.site_digest_salt)
            # TODO: load pickle from user_settings of owner (from link_dest)?
            share_dict = {'share_id': share_id, 'share_root': share_root,
                          'share_pw_hash': share_pw_hash,
                          'share_pw_digest': share_pw_digest}

        # We only allow access to active shares
        if share_dict is not None and isinstance(share_dict, dict) and \
            share_dict.has_key('share_id') and \
                share_dict.has_key('share_root') and \
                share_dict.has_key('share_pw_hash') and \
                share_dict.has_key('share_pw_digest'):
            user_alias = share_id
            user_dir = share_dict['share_root']
            user_password = share_dict['share_pw_hash']
            user_digest = share_dict['share_pw_digest']
            logger.info("Adding login for share %s" % user_alias)
            add_share_object(configuration, user_alias, user_dir,
                             password=user_password,
                             digest=user_digest)
            cur_usernames.append(user_alias)
            changed_shares.append(user_alias)

    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d inactive shares" % len(removed))
        if creds_lock:
            creds_lock.acquire()
        conf['shares'] = [i for i in conf['shares'] if not i.username in
                          removed]
        if creds_lock:
            creds_lock.release()
        changed_shares += removed
    logger.info("Refreshed shares from configuration (%d shares)" %
                len(cur_usernames))
    return (conf, changed_shares)


def refresh_jupyter_creds(configuration, protocol, username):
    """Loads the active ssh keyset for username (SESSIONID).
    The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed
    jupyter IDs.
    """
    active_jupyter_creds = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    if not protocol in ('sftp',):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, active_jupyter_creds)
    if not possible_jupyter_mount_id(configuration, username):
        # logger.debug("ruled out %s as a possible jupyter_mount ID" \
        #   % username)
        return (conf, active_jupyter_creds)

    logger.info("Getting active jupuyter mount creds")
    link_path = os.path.join(configuration.sessid_to_jupyter_mount_link_home,
                             "%s" % username + ".jupyter_mount")
    # logger.debug("jupyter linkpath: " + str(os.path.islink(link_path))
    #              + " jupyter path exists: " + str(os.path.exists(link_path)))

    jupyter_dict = None
    if os.path.islink(link_path) and os.path.exists(link_path):
        sessionid = username
        jupyter_dict = unpickle(link_path, logger)
        # logger.debug("loaded jupyter dict: " + str(jupyter_dict))

    # We only allow connections from active jupyter credentials
    if jupyter_dict is not None and isinstance(jupyter_dict, dict) and \
            jupyter_dict.has_key('SESSIONID') and \
            jupyter_dict['SESSIONID'] == sessionid and \
            jupyter_dict.has_key('USER_CERT') and \
            jupyter_dict.has_key('MOUNTSSHPUBLICKEY'):
        user_alias = sessionid
        user_dir = client_id_dir(jupyter_dict['USER_CERT'])
        user_key = jupyter_dict['MOUNTSSHPUBLICKEY']

        # Make sure pub key is valid
        valid_pubkey = True
        try:
            _ = parse_pub_key(user_key)
        except Exception, exc:
            valid_pubkey = False
            logger.warning("Skipping broken key '%s' for user %s (%s)" %
                           (user_key, user_alias, exc))
        if valid_pubkey:
            # Purge memory of any legacy keys that gives access to the
            # same user_dir
            if creds_lock:
                creds_lock.acquire()
            conf['jupyter_mounts'] = [i for i in conf['jupyter_mounts']
                                      if i.home != user_dir]
            if creds_lock:
                creds_lock.release()

            # Add the new valid keyset that gives access to user_dir
            add_jupyter_object(configuration, user_alias,
                               user_dir, pubkey=user_key)
            active_jupyter_creds.append(user_alias)

    if creds_lock:
        creds_lock.acquire()
    logger.info("Active jupyter_mounts: " +
                str([(i.username, i.home) for i in
                     conf['jupyter_mounts']]))
    if creds_lock:
        creds_lock.release()
    logger.info("Refreshed active jupyter creds")
    return (conf, active_jupyter_creds)


def update_login_map(daemon_conf, changed_users, changed_jobs=[],
                     changed_shares=[], changed_jupyter=[]):
    """Update internal login_map from contents of 'users', 'jobs' and
    'shares' in daemon_conf. This is done considering Login objects matching
    changed_users, changed_jobs, and changed_shares.
    The login_map is a dictionary for fast lookup and we create a list of
    matching Login objects since each user/job/share may have multiple logins
    (e.g. public keys).
    """
    login_map = daemon_conf['login_map']
    creds_lock = daemon_conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    for username in changed_users:
        login_map[username] = [i for i in daemon_conf['users'] if username ==
                               i.username]
    for username in changed_jobs:
        login_map[username] = [i for i in daemon_conf['jobs'] if username ==
                               i.username]
    for username in changed_shares:
        login_map[username] = [i for i in daemon_conf['shares'] if username ==
                               i.username]
    for username in changed_jupyter:
        login_map[username] = [i for i in daemon_conf['jupyter_mounts']
                               if username == i.username]
    if creds_lock:
        creds_lock.release()


def login_map_lookup(daemon_conf, username):
    """Get creds associated with username in login_map in a thread-safe
    fashion. Returns a list of credential objects, which is empty if username
    is not found in login_map.
    """
    login_map = daemon_conf['login_map']
    creds_lock = daemon_conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    creds = login_map.get(username, [])
    if creds_lock:
        creds_lock.release()
    return creds


def hit_rate_limit(configuration, proto, client_address, client_id,
                   max_user_hits=default_max_user_hits):
    """Check if proto login from client_address with client_id should be
    filtered due to too many recently failed login attempts.
    The rate limit check lookup in rate limit cache.
    The rate limit cache is a set of nested dictionaries with
    client_address, protocol, client_id and secret as keys,
    the structure is shown in the 'update_rate_limit' doc-string.
    The rate limit cache maps the number of fails/hits for each
    IP, protocol, username and secret and helps distinguish e.g.
    any other users coming from the same gateway address.
    We always allow up to max_user_hits failed login attempts for a given username
    from a given address. This is in order to make it more difficult to
    effectively lock out another user with impersonating or random logins even
    from the same (gateway) address.

    NOTE: Use expire_rate_limit to remove old rate limit entries from the cache
    """
    logger = configuration.logger
    refuse = False

    _rate_limits_lock.acquire()

    _address_limits = _rate_limits.get(client_address, {})
    _proto_limits = _address_limits.get(proto, {})
    _user_limits = _proto_limits.get(client_id, {})
    proto_hits = _proto_limits.get('hits', 0)
    user_hits = _user_limits.get('hits', 0)
    if user_hits >= max_user_hits:
        refuse = True

    _rate_limits_lock.release()

    if refuse:
        logger.warning("%s reached hit rate limit %d"
                       % (proto, max_user_hits)
                       + ", found %d of %d hit(s) "
                       % (user_hits, proto_hits)
                       + " for %s from %s"
                       % (client_id, client_address))

    return refuse


def update_rate_limit(configuration, proto, client_address, client_id,
                      login_success,
                      secret=None,
                      ):
    """Update rate limit database after proto login from client_address with
    client_id and boolean login_success status.
    The optional secret can be used to save the hash or similar so that
    repeated failures with the same credentials only count as one error.
    Otherwise some clients will retry on failure and hit the limit easily.
    The rate limit database is a set of nested dictionaries with
    client_address, protocol, client_id and secret as keys
    mapping the number of fails/hits for each IP, protocol, username and secret
    This helps distinguish e.g. any other users coming from the same
    gateway address.
    Example of rate limit database entry:
    {'127.0.0.1': {
        'fails': int (Total IP fails)
        'hits': int (Total IP fails)
        'sftp': {
            'fails': int (Total protocol fails)
            'hits': int (Total protocol hits)
            'user@some-domain.org: {
                'fails': int (Total user fails)
                'hits': int (Total user hits)
                'XXXYYYZZZ': {
                    'timestamp': float (Last updated)
                    'hits': int (Total secret hits)
                }
            }
        }
    }
    Returns tuple with updated hits:
    (address_hits, proto_hits, user_hits, secret_hits)
    """
    logger = configuration.logger
    status = {True: "success", False: "failure"}
    address_fails = old_address_fails = 0
    address_hits = old_address_hits = 0
    proto_fails = old_proto_fails = 0
    proto_hits = old_proto_hits = 0
    user_fails = old_user_fails = 0
    user_hits = old_user_hits = 0
    secret_hits = old_secret_hits = 0
    timestamp = time.time()
    if not secret:
        secret = timestamp

    _rate_limits_lock.acquire()
    try:
        # logger.debug("update rate limit db: %s" % _rate_limits)
        _address_limits = _rate_limits.get(client_address, {})
        if not _address_limits:
            _rate_limits[client_address] = _address_limits
        _proto_limits = _address_limits.get(proto, {})
        if not _proto_limits:
            _address_limits[proto] = _proto_limits
        _user_limits = _proto_limits.get(client_id, {})

        address_fails = old_address_fails = _address_limits.get('fails', 0)
        address_hits = old_address_hits = _address_limits.get('hits', 0)
        proto_fails = old_proto_fails = _proto_limits.get('fails', 0)
        proto_hits = old_proto_hits = _proto_limits.get('hits', 0)
        user_fails = old_user_fails = _user_limits.get('fails', 0)
        user_hits = old_user_hits = _user_limits.get('hits', 0)
        if login_success:
            if _user_limits:
                address_fails -= user_fails
                address_hits -= user_hits
                proto_fails -= user_fails
                proto_hits -= user_hits
                user_fails = user_hits = 0
                del _proto_limits[client_id]
        else:
            if not _user_limits:
                _proto_limits[client_id] = _user_limits
            _secret_limits = _user_limits.get(secret, {})
            if not _secret_limits:
                _user_limits[secret] = _secret_limits
            secret_hits = old_secret_hits = _secret_limits.get('hits', 0)
            if secret_hits == 0:
                address_hits += 1
                proto_hits += 1
                user_hits += 1
            address_fails += 1
            proto_fails += 1
            user_fails += 1
            secret_hits += 1
            _secret_limits['timestamp'] = timestamp
            _secret_limits['hits'] = secret_hits
            _user_limits['fails'] = user_fails
            _user_limits['hits'] = user_hits
        _address_limits['fails'] = address_fails
        _address_limits['hits'] = address_hits
        _proto_limits['fails'] = proto_fails
        _proto_limits['hits'] = proto_hits
    except Exception, exc:
        logger.error("update %s Rate limit failed: %s" % (proto, exc))
        logger.info(traceback.format_exc())

    _rate_limits_lock.release()

    """
    logger.debug("update %s rate limit %s for %s\n"
                 % (proto, status[login_success], client_address)
                 + "old_address_fails: %d -> %d\n"
                 % (old_address_fails, address_fails)
                 + "old_address_hits: %d -> %d\n"
                 % (old_address_hits, address_hits)
                 + "old_proto_fails: %d -> %d\n"
                 % (old_proto_fails, proto_fails)
                 + "old_proto_hits: %d -> %d\n"
                 % (old_proto_hits, proto_hits)
                 + "old_user_fails: %d -> %d\n"
                 % (old_user_fails, user_fails)
                 + "old_user_hits: %d -> %d\n"
                 % (old_user_hits, user_hits)
                 + "secret_hits: %d -> %d\n"
                 % (old_secret_hits, secret_hits))
    """

    if user_hits != old_user_hits:
        logger.info("update %s rate limit" % proto
                    + " %s for %s" % (status[login_success], client_address)
                    + " from %d to %d hits" % (old_user_hits, user_hits))

    return (address_hits, proto_hits, user_hits, secret_hits)


def expire_rate_limit(configuration, proto='*',
                      fail_cache=default_fail_cache):
    """Remove rate limit cache entries older than fail_cache seconds.
    Only entries in proto list will be touched,
    If proto list is empty all protocols are checked.
    Returns tuple with updated hits and expire count
    (address_hits, proto_hits, user_hits, expired)
    """
    logger = configuration.logger
    now = time.time()
    address_hits = proto_hits = user_hits = expired = 0
    # logger.debug("expire entries older than %ds at %s" % (fail_cache, now))
    _rate_limits_lock.acquire()
    try:
        for _client_address in _rate_limits.keys():
            # debug_msg = "expire addr: %s" % _client_address
            _address_limits = _rate_limits[_client_address]
            address_fails = old_address_fails = _address_limits['fails']
            address_hits = old_address_hits = _address_limits['hits']
            for _proto in _address_limits.keys():
                if _proto in ['hits', 'fails'] \
                        or not fnmatch.fnmatch(_proto, proto):
                    continue
                _proto_limits = _address_limits[_proto]
                # debug_msg += ", proto: %s" % _proto
                proto_fails = old_proto_fails = _proto_limits['fails']
                proto_hits = old_proto_hits = _proto_limits['hits']
                for _user in _proto_limits.keys():
                    if _user in ['hits', 'fails']:
                        continue
                    # debug_msg += ", user: %s" % _user
                    _user_limits = _proto_limits[_user]
                    user_fails = old_user_fails = _user_limits['fails']
                    user_hits = old_user_hits = _user_limits['hits']
                    for _secret in _user_limits.keys():
                        if _secret in ['hits', 'fails']:
                            continue
                        _secret_limits = _user_limits[_secret]
                        if _secret_limits['timestamp'] + fail_cache < now:
                            secret_hits = _secret_limits['hits']
                            # debug_msg += \
                            #"\ntimestamp: %s, secret_hits: %d" \
                            #    % (_secret_limits['timestamp'], secret_hits) \
                            #    + ", secret: %s" % _secret
                            address_fails -= secret_hits
                            address_hits -= 1
                            proto_fails -= secret_hits
                            proto_hits -= 1
                            user_fails -= secret_hits
                            user_hits -= 1
                            del _user_limits[_secret]
                            expired += 1
                    _user_limits['fails'] = user_fails
                    _user_limits['hits'] = user_hits
                    # debug_msg += "\nold_user_fails: %d -> %d" \
                    # % (old_user_fails, user_fails) \
                    #    + "\nold_user_hits: %d -> %d" \
                    #    % (old_user_hits, user_hits)
                    if user_fails == 0:
                        # debug_msg += "\nRemoving expired user: %s" % _user
                        del _proto_limits[_user]
                _proto_limits['fails'] = proto_fails
                _proto_limits['hits'] = proto_hits
                # debug_msg += "\nold_proto_fails: %d -> %d" \
                # % (old_proto_fails, proto_fails) \
                #    + "\nold_proto_hits: %d -> %d" \
                #    % (old_proto_hits, proto_hits)

            _address_limits['fails'] = address_fails
            _address_limits['hits'] = address_hits
            # debug_msg += "\nold_address_fails: %d -> %d" \
            # % (old_address_fails, address_fails) \
            #    + "\nold_address_hits: %d -> %d" \
            #    % (old_address_hits, address_hits)
            # logger.debug(debug_msg)

    except Exception, exc:
        logger.error("expire rate limit failed: %s" % exc)
        logger.info(traceback.format_exc())

    _rate_limits_lock.release()

    if expired:
        logger.info("expire %s rate limit expired %d items" % (proto,
                                                               expired))
        # logger.debug("expire %s rate limit expired %s" % (proto, expired))

    return (address_hits, proto_hits, user_hits, expired)


def penalize_rate_limit(configuration, proto, client_address, client_id,
                        user_hits, max_user_hits=default_max_user_hits):
    """Stall client for a while based on the number of rate limit failures to
    make sure dictionary attackers don't really load the server with their
    repeated force-failed requests. The stall penalty is a linear function of
    the number of failed attempts.
    """
    logger = configuration.logger
    sleep_secs = 3 * (user_hits - max_user_hits)
    if sleep_secs > 0:
        logger.info("stall %s rate limited user %s from %s for %ds" %
                    (proto, client_id, client_address, sleep_secs))
        time.sleep(sleep_secs)
    return sleep_secs


def track_open_session(configuration,
                       proto,
                       client_id,
                       client_address,
                       client_port,
                       session_id=None,
                       authorized=False,
                       prelocked=False,
                       blocking=True):
    """Track that client_id opened a new session from
    client_address and client_port.
    If session_id is _NOT_ set then client_ip:client_port
    is used as session_id.
    Returns dictionary with new session"""

    logger = configuration.logger
    # msg = "track open session for %s" % client_id \
    #     + " from %s:%s with session_id: %s" % \
    #     (client_address, client_port, session_id)
    # logger.debug(msg)
    result = None
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    try:
        _cached = _active_sessions.get(client_id, {})
        if not _cached:
            _active_sessions[client_id] = _cached
        _proto = _cached.get(proto, {})
        if not _proto:
            _cached[proto] = _proto
        _session = _proto.get(session_id, {})
        if not _session:
            _proto[session_id] = _session
        _session['session_id'] = session_id
        _session['client_id'] = client_id
        _session['ip_addr'] = client_address
        _session['tcp_port'] = client_port
        _session['authorized'] = authorized
        _session['timestamp'] = time.time()
        result = _session
    except Exception, exc:
        result = None
        logger.error("track open session failed: %s" % exc)

    if not prelocked:
        _sessions_lock.release()

    return result


def get_active_session(configuration,
                       proto,
                       client_id,
                       session_id,
                       prelocked=False,
                       blocking=True):
    """Returns active session if it exists
    for proto, client_id and session_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, session_id: %s," \
    #              % (proto, client_id) \
    #              + " prelocked: %s, blocking: %s" \
    #              % (prelocked, blocking))
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = _active_sessions.get(client_id, {}).get(
        proto, {}).get(session_id, {})

    if not prelocked:
        _sessions_lock.release()

    return result


def get_open_sessions(configuration,
                      proto,
                      client_id=None,
                      prelocked=False,
                      blocking=True):
    """Returns dictionary {session_id: session}
    with open proto sessions for client_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, prelocked: %s, blocking: %s"
    #              % (proto, client_id, prelocked, blocking))
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    # logger.debug("_active_sessions: %s" % _active_sessions)
    if client_id is not None:
        result = _active_sessions.get(client_id, {}).get(
            proto, {})
    else:
        result = {}
        for (_, open_sessions) in _active_sessions.iteritems():
            open_proto_session = open_sessions.get(proto, {})
            if open_proto_session:
                result.update(open_proto_session)

    if not prelocked:
        _sessions_lock.release()

    return result


def track_close_session(configuration,
                        proto,
                        client_id,
                        client_address,
                        client_port,
                        session_id=None,
                        prelocked=False,
                        blocking=True):
    """Track that proto session for client_id is closed,
    returns closed session dictionary"""
    logger = configuration.logger
    # msg = "track close session for proto: '%s'" % proto \
    #     + " from %s:%s with session_id: %s, client_id: %s, prelocked: %s" % \
    #     (client_address, client_port, session_id, client_id, prelocked)
    # logger.debug(msg)
    result = None
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, prelocked=True)
    # logger.debug("_sessions : %s" % _sessions)
    if open_sessions and open_sessions.has_key(session_id):
        try:
            result = open_sessions[session_id]
            del open_sessions[session_id]
        except Exception, exc:
            result = None
            msg = "track close session failed for client: %s" % client_id \
                + "with session id: %s" % session_id \
                + ", error: %s" % exc
            logger.error(msg)
    else:
        msg = "track close session: '%s' _NOT_ found for proto: '%s'" \
            % (session_id, proto) \
            + ", client: '%s'" % client_id
        logger.warning(msg)

    if not prelocked:
        _sessions_lock.release()

    return result


def track_close_expired_sessions(
        configuration,
        proto,
        client_id=None,
        prelocked=False,
        blocking=True):
    """Track expired sessions and close them.
    Returns dictionary of closed sessions {session_id: session}"""
    logger = configuration.logger
    # msg = "track close sessions for proto: '%s'" % proto \
    #     + " with client_id: %s, prelocked: %s, blocking: %s" % \
    #     (client_id, prelocked, blocking)
    # logger.debug(msg)
    result = None
    session_timeout = io_session_timeout.get(proto, 0)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, prelocked=True)
    # logger.debug("open_sessions: %s" % open_sessions)
    current_timestamp = time.time()
    # logger.debug("current_timestamp: %s" % (current_timestamp))
    for open_session_id in open_sessions.keys():
        timestamp = open_sessions[open_session_id]['timestamp']
        # logger.debug("current_timestamp - timestamp: %s / %s"
        #              % (current_timestamp - timestamp, session_timeout))
        if current_timestamp - timestamp > session_timeout:
            cur_session = open_sessions[open_session_id]
            cur_session_id = cur_session['session_id']
            closed_session = \
                track_close_session(configuration,
                                    proto,
                                    cur_session['client_id'],
                                    cur_session['ip_addr'],
                                    cur_session['tcp_port'],
                                    session_id=cur_session_id,
                                    prelocked=True)
            if closed_session is not None:
                result[cur_session_id] = closed_session
    if not prelocked:
        _sessions_lock.release()

    return result


def active_sessions(configuration,
                    proto,
                    client_id,
                    prelocked=False,
                    blocking=True):
    """Look up how many active proto sessions client_id has running"""
    logger = configuration.logger
    result = None

    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    try:
        _cached = _active_sessions.get(client_id, {})
        _active = _cached.get(proto, {})
        result = len(_active.keys())
    except Exception, exc:
        result = None
        logger.error("active sessions failed: %s" % exc)

    if not prelocked:
        _sessions_lock.release()

    return result


def valid_twofactor_session(configuration, client_id, addr=None):
    """Check if *client_id* has a valid 2FA session.
    NOTE:
    1) In this first version 2FA sessions are solely activated
       through HTTPS 2FA AUTH.
    2) All daemons share the same 2FA session key, validated by timestamp
    3) If a more fine-grained 2FA auth is needed along with the details
       stored in the session_key file, then add twofa to the Login class
       and merge this function with the existing 'refresh_X_creds' framework
    """
    logger = configuration.logger
    session_data = active_twofactor_session(configuration, client_id, addr)
    if session_data is None:
        logger.warning("no 2FA session found for %s (%s)" % (client_id, addr))
        return False
    else:
        logger.debug("valid 2FA session found for %s (%s): %s" %
                     (client_id, addr, session_data))
        return True


def check_twofactor_session(configuration, username, addr, proto):
    """Run any required 2-factor authentication checks for given username and
    proto.
    First check if site enables twofactor at all and in that case if the user
    actually requires it for given proto. Finally check the validity of the
    corresponding 2FA session file if so.
    """
    logger = configuration.logger
    if not configuration.site_enable_twofactor:
        logger.debug("twofactor support disabled site-wide")
        return True
    client_id = expand_openid_alias(username, configuration)
    if configuration.site_enable_gdp:
        client_id = get_client_id_from_project_client_id(
            configuration, client_id)
    twofactor_dict = load_twofactor(client_id, configuration,
                                    allow_missing=True)
    # logger.debug("found twofactor_dict for %s : %s" %
    #              (client_id, twofactor_dict))
    if not twofactor_dict:
        # logger.debug("fall back to twofactor defaults for %s" % client_id)
        twofactor_dict = dict([(i, j['Value']) for (i, j) in
                               twofactor_defaults(configuration).items()])

    if proto in ('ssh-pw', 'sftp-pw', 'scp-pw', 'rsync-pw'):
        proto_field = 'SFTP_PASSWORD'
    elif proto in ('ssh-key', 'sftp-key', 'scp-key', 'rsync-key'):
        proto_field = 'SFTP_KEY'
    elif proto in ('dav', 'davs'):
        proto_field = 'WEBDAVS'
    elif proto in ('ftp', 'ftps'):
        proto_field = 'FTPS'
    else:
        logger.error("Invalid protocol: %s" % proto)
        return False
    proto_field += "_TWOFACTOR"
    if not twofactor_dict.get(proto_field, False):
        if configuration.site_enable_gdp:

            # GDP require twofactor settings for all protocols

            msg = "Missing GDP twofactor settings for user: %s, protocol: %s" \
                % (client_id, proto)
            logger.error(msg)
            return False
        else:
            # logger.debug("user %s does not require twofactor for %s" \
            #   % (client_id, proto))
            return True
    # logger.debug("check required 2FA session in %s for %s" % (proto, username))
    return valid_twofactor_session(configuration, client_id, addr)


def authlog(configuration,
            log_lvl,
            proto,
            user_id,
            user_addr,
            log_msg,
            notify=True):
    """Log auth messages to auth logger.
    Notify user when log_lvl != 'DEBUG'"""
    logger = configuration.logger
    auth_logger = configuration.auth_logger
    status = True
    category = None

    if log_lvl == 'INFO':
        category = [proto.upper(), log_lvl]
        _auth_logger = auth_logger.info
    elif log_lvl == 'WARNING':
        category = [proto.upper(), log_lvl]
        _auth_logger = auth_logger.warning
    elif log_lvl == 'ERROR':
        category = [proto.upper(), log_lvl]
        _auth_logger = auth_logger.error
    elif log_lvl == 'CRITICAL':
        category = [proto.upper(), log_lvl]
        _auth_logger = auth_logger.critical
    elif log_lvl == 'DEBUG':
        _auth_logger = auth_logger.debug
    else:
        logger.error("Invalid authlog level: %s" % log_lvl)
        return False

    if notify and category:
        user_msg = "IP: %s, User: %s, Message: %s" % \
            (user_addr, user_id, log_msg)
        status = send_system_notification(user_id, category,
                                          user_msg, configuration)
        if not status:
            logger.error("Failed to send notification to: %s" % user_id)

    log_message = "IP: %s, Protocol: %s, User: %s, Message: %s" \
        % (user_addr, proto, user_id, log_msg)
    _auth_logger(log_message)

    return status


def handle_auth_attempt(configuration,
                        protocol,
                        username,
                        ip_addr,
                        tcp_port=0,
                        secret=None,
                        invalid_username=False,
                        invalid_user=False,
                        skip_twofa_check=False,
                        valid_twofa=False,
                        key_enabled=False,
                        valid_key=False,
                        password_enabled=False,
                        valid_password=False,
                        digest_enabled=False,
                        valid_digest=False,
                        exceeded_rate_limit=False,
                        exceeded_max_sessions=False,
                        user_abuse_hits=default_user_abuse_hits,
                        proto_abuse_hits=default_proto_abuse_hits,
                        max_secret_hits=default_max_secret_hits,
                        ):
    """Log auth attempt to daemon-logger and auth log.
    Update/check rate limits and log abuses to auth log.

    Returns tuple of booleans: (authorized, disconnect)
    authorized: True if authorization succeded
    disconnect: True if caller is adviced to disconnect
    """

    logger = configuration.logger

    """
    logger.debug("\n-----------------------------------------------------\n"
                 + "protocol: %s\n"
                 % protocol
                 + "username: %s\n"
                 % username
                 + "ip_addr: %s, tcp_port: %s\n"
                 % (ip_addr, tcp_port)
                 + "secret: %s\n"
                 % secret
                 + "invalid_username: %s\n"
                 % invalid_username
                 + "invalid_user: %s\n"
                 % invalid_user
                 + "skip_twofa_check: %s\n"
                 % skip_twofa_check
                 + "valid_twofa: %s\n"
                 % valid_twofa
                 + "key_enabled: %s, valid_key: %s\n"
                 % (key_enabled, valid_key)
                 + "password_enabled: %s, valid_password: %s\n"
                 % (password_enabled, valid_password)
                 + "digest_enabled: %s, valid_digest: %s\n"
                 % (digest_enabled, valid_digest)
                 + "exceeded_rate_limit: %s\n"
                 % exceeded_rate_limit
                 + "exceeded_max_sessions: %s\n"
                 % exceeded_max_sessions
                 + "-----------------------------------------------------")
    """

    authorized = False
    disconnect = False
    twofa_passed = valid_twofa
    if skip_twofa_check:
        twofa_passed = True

    # Log auth attempt and set (authorized, disconnect) return values

    if (valid_key or valid_password or valid_digest) and twofa_passed:
        authorized = True
        if configuration.site_enable_gdp:
            notify = True
        else:
            notify = False
        if valid_key:
            info_msg = "Accepted key"
        elif valid_password:
            info_msg = "Accepted password"
        elif valid_digest:
            info_msg = "Accepted digest"
        authlog(configuration, 'INFO', protocol,
                username, ip_addr, info_msg, notify=notify)
        info_msg += " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            info_msg += ":%s" % tcp_port
        logger.info(info_msg)
    elif exceeded_rate_limit:
        disconnect = True
        warn_msg = "Rate limit reached"
        authlog(configuration, 'WARNING', protocol,
                username, ip_addr, warn_msg, notify=True)
        warn_msg += " for %s from %s" % (username, ip_addr)
        logger.warning(warn_msg)
    elif exceeded_max_sessions:
        disconnect = True
        active_count = active_sessions(configuration, protocol, username)
        warn_msg = "Too many open sessions"
        authlog(configuration, 'WARNING', protocol,
                username, ip_addr, warn_msg, notify=True)
        warn_msg += " %d for %s" \
            % (active_count, username)
        logger.warning(warn_msg)
    elif invalid_username:
        disconnect = True
        if re.match(CRACK_USERNAME_REGEX, username) is not None:
            log_msg = "Crack username detected"
            log_func = logger.critical
            authlog_lvl = 'CRITICAL'
        else:
            log_msg = "Invalid username"
            log_func = logger.error
            authlog_lvl = 'ERROR'
        authlog(configuration, authlog_lvl, protocol,
                username, ip_addr, log_msg, notify=False)
        log_msg += " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        log_func(log_msg)
    elif invalid_user:
        disconnect = True
        err_msg = "Missing user and/or credentials"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr,
                err_msg, notify=False)
        err_msg += " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    elif not (key_enabled or password_enabled or digest_enabled):
        disconnect = True
        err_msg = "No valid credentials"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    elif (valid_key or valid_password or valid_digest) and not twofa_passed:
        disconnect = True
        err_msg = "No valid two factor session"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    elif key_enabled and not valid_key:
        err_msg = "Failed key"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    elif password_enabled and not valid_password:
        err_msg = "Failed password"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    elif digest_enabled and not valid_digest:
        err_msg = "Failed digest"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.error(err_msg)
    else:
        disconnect = True
        err_msg = "Unknown auth error"
        authlog(configuration, 'ERROR', protocol,
                username, ip_addr, err_msg, notify=True)
        err_msg += " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            err_msg += ":%s" % tcp_port
        logger.warning(err_msg)

    # Update and check rate limits

    (_, proto_hits, user_hits, secret_hits) = \
        update_rate_limit(configuration, protocol, ip_addr,
                          username, authorized,
                          secret=secret)

    # If we hit max_secret_hits then add a unique secret to force
    # address, proto and user hits to increase

    if max_secret_hits > 0 and secret_hits > max_secret_hits:
        logger.debug("max secret hits reached: %d / %d" %
                     (secret_hits, max_secret_hits))
        max_secret = "%f_max_secret_hits_%s" % (time.time(), secret)
        (_, proto_hits, user_hits, _) = \
            update_rate_limit(configuration, protocol, ip_addr,
                              username, authorized,
                              secret=max_secret)

    # Check if we should log abuse messages for use by eg. fail2ban

    if user_abuse_hits > 0 and user_hits > user_abuse_hits:
        crit_msg = "Abuse limit reached"
        authlog(configuration, 'CRITICAL', protocol,
                username, ip_addr, crit_msg)
        crit_msg += " user hits %d for %s from %s" \
            % (user_abuse_hits, username, ip_addr)
        if tcp_port > 0:
            crit_msg += ":%s" % tcp_port
        logger.warning(crit_msg)
    elif proto_abuse_hits > 0 and proto_hits > proto_abuse_hits:
        crit_msg = "Abuse limit reached"
        authlog(configuration, 'CRITICAL', protocol,
                username, ip_addr, crit_msg)
        crit_msg += " proto hits %d for %s from %s" \
            % (proto_abuse_hits, username, ip_addr)
        if tcp_port > 0:
            crit_msg += ":%s" % tcp_port
        logger.warning(crit_msg)

    return (authorized, disconnect)


if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    conf.logger = logging
    test_proto, test_address, test_port, test_id, test_session_id = \
        'DUMMY', '127.0.0.42', 42000, \
        'user@some-domain.org', 'DUMMY_SESSION_ID'
    test_pw = "T3stp4ss"
    invalid_id = 'root'
    print "Running unit test on rate limit functions"
    print "Force expire all"
    (_, _, _, expired) = expire_rate_limit(conf, test_proto, fail_cache=0)
    print "Expired: %s" % expired
    this_pw = test_pw
    print "Emulate rate limit"
    for i in range(default_max_user_hits-1):
        hit = hit_rate_limit(conf, test_proto, test_address, test_id)
        print "Blocked: %s" % hit
        update_rate_limit(conf, test_proto, test_address, test_id, False,
                          this_pw)
        print "Updated fail for %s:%s from %s" % \
              (test_id, this_pw, test_address)
        this_pw += 'x'
        time.sleep(1)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with original user and password again"
    update_rate_limit(conf, test_proto, test_address, test_id, False, test_pw)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with original user and new password again to hit limit"
    update_rate_limit(conf, test_proto, test_address, test_id, False, this_pw)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    other_proto, other_address = "BOGUS", '127.10.20.30'
    other_id, other_pw = 'other@some.org', "0th3rP4ss"
    print "Update with other proto"
    update_rate_limit(conf, other_proto, test_address, test_id, False, test_pw)
    print "Update with other address"
    update_rate_limit(conf, test_proto, other_address, test_id, False, test_pw)
    print "Update with other user"
    update_rate_limit(conf, test_proto, test_address, other_id, False, test_pw)
    print "Check with same user from other address"
    hit = hit_rate_limit(conf, test_proto, other_address, test_id)
    print "Blocked: %s" % hit
    print "Check with other user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, other_id)
    print "Blocked: %s" % hit
    time.sleep(2)
    print "Force expire some entries"
    (_, _, _, expired) = expire_rate_limit(conf, test_proto,
                                           fail_cache=default_max_user_hits)
    print "Expired: %s" % expired
    print "Test reset on success"
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    update_rate_limit(conf, test_proto, test_address, test_id, True, test_pw)
    print "Updated success for %s from %s" % (test_id, test_address)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with same user from other address"
    hit = hit_rate_limit(conf, test_proto, other_address, test_id)
    print "Blocked: %s" % hit
    print "Check with other user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, other_id)
    print "Blocked: %s" % hit
    print "Check with invalid user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, invalid_id)
    print "Blocked: %s" % hit
    print "Test active session counting"
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address, test_port)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address, test_port+1)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address, test_port, )
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address, test_port+1, )
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Test session tracking functions"
    expected_session_keys = ['ip_addr',
                             'tcp_port',
                             'session_id',
                             'authorized',
                             'client_id',
                             'timestamp']
    print "Track open session #1"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id,
                                      test_address,
                                      test_port,
                                      test_session_id,
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #2"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id,
                                      test_address,
                                      test_port+1,
                                      test_session_id+"_1",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #3"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id+"_1",
                                      test_address,
                                      test_port+2,
                                      test_session_id+"_2",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #4"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id+"_1",
                                      test_address,
                                      test_port+3,
                                      test_session_id+"_3",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
    print "Track get open sessions #1"
    cur_open_sessions = get_open_sessions(conf, 'INVALID')
    if isinstance(cur_open_sessions, dict):
        if not cur_open_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % cur_open_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #2"
    cur_open_sessions = get_open_sessions(conf, test_proto, 'INVALID')
    if isinstance(cur_open_sessions, dict):
        if not cur_open_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % cur_open_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #3"
    cur_open_sessions = get_open_sessions(conf, test_proto)
    if isinstance(cur_open_sessions, dict):
        if len(cur_open_sessions.keys()) != 4:
            print "ERROR: Expected dictionary #keys: 4" \
                + ", found: %s, %s" % (len(cur_open_sessions.keys()),
                                       cur_open_sessions.keys())
            sys.exit(1)
        status = True
        for (key, val) in cur_open_sessions.iteritems():
            if not isinstance(val, dict) \
                    or val.keys() != expected_session_keys:
                status = False
                print "ERROR: Invalid session dictionary: '%s'" \
                    % (val)
                sys.exit(1)
        if status:
            print "OK"
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #4"
    cur_open_sessions = get_open_sessions(conf,
                                          test_proto,
                                          client_id=test_id)
    if isinstance(cur_open_sessions, dict):
        if len(cur_open_sessions.keys()) != 2:
            print "ERROR: Expected dictionary #keys: 2" \
                + ", found: %s, %s" % (len(cur_open_sessions.keys()),
                                       cur_open_sessions.keys())
            sys.exit(1)
        status = True
        for (key, val) in cur_open_sessions.iteritems():
            if not isinstance(val, dict) \
                    or val.keys() != expected_session_keys:
                status = False
                print "ERROR: Invalid session dictionary: '%s'" \
                    % (val)
                sys.exit(1)
        if status:
            print "OK"
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get active session #1"
    active_session = get_active_session(conf,
                                        'INVALID',
                                        test_id,
                                        test_session_id)
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #2"
    active_session = get_active_session(conf,
                                        test_proto,
                                        'INVALID',
                                        test_session_id)
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #3"
    active_session = get_active_session(conf,
                                        test_proto,
                                        test_id,
                                        'INVALID')
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #4"
    active_session = get_active_session(conf,
                                        test_proto,
                                        test_id,
                                        test_session_id)
    if isinstance(active_session, dict):
        if active_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (active_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track close session #1"
    close_session = track_close_session(conf,
                                        'INVALID',
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #2"
    close_session = track_close_session(conf,
                                        test_proto,
                                        'INVALID',
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #3"
    close_session = track_close_session(conf,
                                        test_proto,
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=None)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #4"
    close_session = track_close_session(conf,
                                        test_proto,
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if close_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (close_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close expired sessions #1"
    expired_sessions = track_close_expired_sessions(conf,
                                                    'INVALID')
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if not expired_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % expired_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #2"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto,
                                                    'INVALID')
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if not expired_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % expired_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #3"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto,
                                                    client_id=test_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if len(expired_sessions.keys()) == 1:
            status = True
            for (key, val) in expired_sessions.iteritems():
                if not isinstance(val, dict) \
                        or val.keys() != expected_session_keys:
                    status = False
                    print "ERROR: Invalid session dictionary: '%s'" \
                        % (val)
                    sys.exit(1)
            if status:
                print "OK"
        else:
            print "ERROR: Expected 1 expired session, found: %s" \
                % len(expired_sessions.keys())
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #4"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if len(expired_sessions.keys()) == 2:
            status = True
            for (key, val) in expired_sessions.iteritems():
                if not isinstance(val, dict) \
                        or val.keys() != expected_session_keys:
                    status = False
                    print "ERROR: Invalid session dictionary: '%s'" \
                        % (val)
                    sys.exit(1)
            if status:
                print "OK"
        else:
            print "ERROR: Expected 2 expired session, found: %s" \
                % len(expired_sessions.keys())
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
