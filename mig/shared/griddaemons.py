#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons - grid daemon helper functions
# Copyright (C) 2010-2018  The MiG Project lead by Brian Vinter
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
import socket
import time
import threading

from shared.base import client_dir_id, client_id_dir, client_alias, \
    invisible_path, force_utf8
from shared.defaults import dav_domain, io_session_timeout
from shared.fileio import unpickle
from shared.gdp import project_login, project_logout, \
    get_active_project_short_id, validate_user
from shared.safeinput import valid_path
from shared.sharelinks import extract_mode_id
from shared.ssh import parse_pub_key
from shared.useradm import ssh_authkeys, davs_authkeys, ftps_authkeys, \
    https_authkeys, get_authkeys, ssh_authpasswords, davs_authpasswords, \
    ftps_authpasswords, https_authpasswords, get_authpasswords, \
    ssh_authdigests, davs_authdigests, ftps_authdigests, https_authdigests, \
    generate_password_hash, generate_password_digest, load_user_dict, \
    get_short_id
from shared.validstring import possible_user_id, possible_gdp_user_id, \
    possible_sharelink_id, possible_job_id, possible_jupyter_mount_id, \
    valid_user_path, is_valid_email_address

default_max_fails, default_fail_cache = 5, 120

# NOTE: auth keys file may easily contain only blank lines, so we decide to
#       consider any such file of less than a 100 bytes invalid.

min_pub_key_bytes = 100

_rate_limits = {}
_rate_limits_lock = threading.Lock()
_active_sessions = {}
_sessions_lock = threading.Lock()


def __validate_gdp_session(configuration,
                           proto,
                           client_id,
                           client_address,
                           client_port):
    """Returns True if GDP user session is valid.
    GDP only allow one session per user"""
    logger = configuration.logger
    # msg = "proto: %s, client_id: %s" % (proto, client_id) \
    #     + " client_address: %s, client_port: %s" \
    #    % (client_address, client_port)
    # logger.debug(msg)
    result = False
    status = False
    (status, msg) = validate_user(
        configuration, client_id, client_address, proto)
    if not status:
        logger.warning(msg)
    else:
        active_user_id = get_active_project_short_id(configuration,
                                                     client_id,
                                                     proto)

    # GDP only allows one active user at any time
    # 'active_user_id' is registered as the active user in the GDP database
    # NOTE: If the daemon is killed without a proper session cleanup
    # Then the 'active' user field in the GDP database is not reset

    if status and active_user_id is not None:
        _sessions_lock.acquire()

        open_sessions = get_open_sessions(
            configuration, proto, client_id=active_user_id, prelocked=True)
        auth_sessions = {session_id: session for (session_id, session)
                         in open_sessions.iteritems()
                         if session.get('authorized')}
        if not auth_sessions:

            # No open sessions, reset GDP active user

            status = project_logout(configuration,
                                    client_address,
                                    proto,
                                    active_user_id,
                                    autologout=True)
        else:

            # Close all active sessions from client_id
            # before accepting new sessions
            # NOTE: track_close_session trigger 'project_logout'
            # TODO: Consider skipping session close if:
            #       active_user_id == client_id and IP is the same

            for session_id in auth_sessions.keys():
                # logger.debug("closing session: %s for active_user_id: %s" \
                #     % (session_id, client_id))
                if not track_close_session(configuration,
                                           proto,
                                           active_user_id,
                                           client_address,
                                           client_port,
                                           session_id=session_id,
                                           prelocked=True):
                    status = False
                    logger.error("Failed to close session: %s for: %s"
                                 % (session_id, active_user_id))
        _sessions_lock.release()

    if status:
        result = True

    return result


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

    def __init__(self, username, home, password=None, digest=None,
                 public_key=None, chroot=True, ip_addr=None, user_dict=None):
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


def add_user_object(conf, login, home, password=None, digest=None, pubkey=None,
                    chroot=True, user_dict=None):
    """Add a single Login object to active user list"""
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    user = Login(username=login, home=home, password=password,
                 digest=digest, public_key=pubkey, chroot=chroot,
                 user_dict=user_dict)
    # logger.debug("Adding user login:\n%s" % user)
    if creds_lock:
        creds_lock.acquire()
    conf['users'].append(user)
    if creds_lock:
        creds_lock.release()


def add_job_object(conf, login, home, password=None, digest=None, pubkey=None,
                   chroot=True, ip_addr=None):
    """Add a single Login object to active jobs list"""
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    job = Login(username=login, home=home, password=password, digest=digest,
                public_key=pubkey, chroot=chroot, ip_addr=ip_addr)
    # logger.debug("Adding job login:\n%s" % job)
    if creds_lock:
        creds_lock.acquire()
    conf['jobs'].append(job)
    if creds_lock:
        creds_lock.release()


def add_share_object(conf, login, home, password=None, digest=None,
                     pubkey=None, chroot=True, ip_addr=None):
    """Add a single Login object to active shares list"""
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    share = Login(username=login, home=home, password=password, digest=digest,
                  public_key=pubkey, chroot=chroot, ip_addr=ip_addr)
    # logger.debug("Adding share login:\n%s" % share)
    if creds_lock:
        creds_lock.acquire()
    conf['shares'].append(share)
    if creds_lock:
        creds_lock.release()


def add_jupyter_object(conf, login, home, password=None, digest=None,
                       pubkey=None, chroot=True, ip_addr=None):
    """Add a single Login object to active jupyter mount list"""
    logger = conf.get('logger', logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    jupyter_mount = Login(username=login,
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


def update_user_objects(conf, auth_file, path, user_vars, auth_protos,
                        private_auth_file):
    """Update login objects for auth_file with path to conf users dict. Remove
    any old entries for user and add the current ones.
    If private_auth_file is false we have to treat auth_file as a MiG user DB
    rather than the private credential files in user homes.
    """
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
        add_user_object(conf, user_alias, user_dir, pubkey=user_key)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, pubkey=user_key,
                            user_dict=user_dict)
            add_user_object(conf, short_alias, user_dir, pubkey=user_key,
                            user_dict=user_dict)
    for user_password in all_passwords:
        user_password = user_password.strip()
        add_user_object(conf, user_alias, user_dir, password=user_password,
                        user_dict=user_dict)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, password=user_password,
                            user_dict=user_dict)
            add_user_object(conf, short_alias, user_dir,
                            password=user_password, user_dict=user_dict)
    for user_digest in all_digests:
        user_digest = user_digest.strip()
        add_user_object(conf, user_alias, user_dir, digest=user_digest,
                        user_dict=user_dict)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, digest=user_digest,
                            user_dict=user_dict)
            add_user_object(conf, short_alias, user_dir, digest=user_digest,
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
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(conf, auth_file, path, user_vars, auth_protos,
                            private_auth_file)
    if changed_paths:
        logger.info("Refreshed user %s from configuration: %s" %
                    (username, changed_paths))
        changed_users.append(username)
    return (conf, changed_users)


def refresh_users(configuration, protocol):
    """Reload all users from auth confs if they changed on disk. Add user entries
    to configuration.daemon_conf['users'] for all active keys and passwords
    enabled in configuration. Optionally add short ID username alias entries
    for all users if that is enabled in the configuration.
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
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(conf, auth_file, path, user_vars, auth_protos,
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
            add_job_object(conf, user_alias, user_dir, pubkey=user_key,
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
                add_job_object(conf, user_alias, user_dir, pubkey=user_key,
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
        add_share_object(conf, user_alias, user_dir, password=user_password,
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
    last_update = conf['time_stamp']
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
            add_share_object(conf, user_alias, user_dir,
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
        # logger.debug("ruled out %s as a possible jupyter_mount ID" % username)
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
            add_jupyter_object(conf, user_alias, user_dir, pubkey=user_key)
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
                   max_fails=default_max_fails,
                   fail_cache=default_fail_cache,
                   username_validator=default_username_validator):
    """Check if proto login from client_address with client_id should be
    filtered due to too many recently failed login attempts or invalid username
    format. Returns True if so and False otherwise. The username_validator
    function is first called as username_validator(configuration, client_id)
    to check if the username is on the expected format - and hit rate limit
    always kicks in unless that call returns True. This is mainly to throttle
    automated dictionary attacks. Otherwise the rate limit check proceeds with
    a lookup in rate limit cache. Rate limit decisions only take login attempts
    within the last fail_cache seconds into account.
    The rate limit cache is a dictionary with client_address as key and
    dictionaries mapping proto to list of failed attempts. The latter contains
    credential info to distinguish them.
    We always allow up to max_fails failed login attempts for a given username
    from a given address. This is in order to make it more difficult to
    effectively lock out another user with impersonating or random logins even
    from the same (gateway) address.
    """
    logger = configuration.logger
    refuse = False
    client_hits, all_hits = 0, 0
    now = time.time()

    # Early refuse on invalid username: eases filter of 'root', 'admin', etc.
    if not username_validator(configuration, client_id):
        logger.warning("hit rate limit on invalid username %s from %s" %
                       (client_id, client_address))
        return True

    _rate_limits_lock.acquire()

    try:
        _cached = _rate_limits.get(client_address, {})
        if _cached:
            _failed = _cached.get(proto, [])
            # logger.debug("hit rate limit found failed history: %s" % _failed)
            for (time_stamp, failed_id, _) in _failed:
                if time_stamp + fail_cache < now:
                    continue
                if failed_id == client_id:
                    client_hits += 1
                all_hits += 1
            if client_hits >= max_fails:
                refuse = True
    except Exception, exc:
        logger.error("hit rate limit failed: %s" % exc)

    _rate_limits_lock.release()

    if all_hits > 0:
        logger.info("%s hit rate limit got %d of %d hit(s) for %s from %s" %
                    (proto, client_hits, all_hits, client_id, client_address))
    return refuse


def update_rate_limit(configuration, proto, client_address, client_id,
                      login_success, secret=None):
    """Update rate limit database after proto login from client_address with
    client_id and boolean login_success status.
    The optional secret can be used to save the hash or similar so that
    repeated failures with the same credentials only count as one error.
    Otherwise some clients will retry on failure and hit the limit easily.
    The rate limit database is a dictionary with client_address as key and
    dictionaries mapping proto to list of failed attempts holding credential
    info. This helps distinguish e.g. any other users coming from the same
    gateway address.
    We simply append new failed attempts to the list and update the time stamp
    for logins with the same credentials already registered there. On success
    we clear failed logins for that particular address and user combination.
    """
    logger = configuration.logger
    _failed = []
    cur = {}
    failed_count, cache_fails = 0, 0
    status = {True: "success", False: "failure"}

    _rate_limits_lock.acquire()
    try:
        # logger.debug("update rate limit db: %s" % _rate_limits)
        _cached = _rate_limits.get(client_address, {})
        cur.update(_cached)
        _failed = _cached.get(proto, [])
        cache_fails = len(_failed)
        if login_success:
            # Remove all tuples with matching username
            _failed = [i for i in _failed if i[1] != client_id]
            failed_count = 0
        else:
            fail_entry = (time.time(), client_id, secret)
            # Remove any matching tuple first to effectively update time stamp
            _failed = [i for i in _failed if i[1:] != fail_entry[1:]]
            _failed.append(fail_entry)
            failed_count = len(_failed)

        cur[proto] = _failed
        _rate_limits[client_address] = cur
    except Exception, exc:
        logger.error("update %s rate limit failed: %s" % (proto, exc))

    _rate_limits_lock.release()

    if failed_count != cache_fails:
        logger.info("update %s rate limit %s for %s from %d to %d hits" %
                    (proto, status[login_success], client_address, cache_fails,
                     failed_count))
        # logger.debug("update %s rate limit to %s" % (proto, _failed))
    return failed_count


def expire_rate_limit(configuration, proto='*', fail_cache=default_fail_cache):
    """Remove rate limit database entries older than fail_cache seconds. Only
    entries with protocol matching proto pattern will be touched.
    Returns a list of expired entries.
    """
    logger = configuration.logger
    now = time.time()
    expired = []

    # logger.debug("expire entries older than %ds at %s" % (fail_cache, now))

    _rate_limits_lock.acquire()

    try:
        for _client_address in _rate_limits.keys():
            cur = {}
            for _proto in _rate_limits[_client_address]:
                if not fnmatch.fnmatch(_proto, proto):
                    continue
                _failed = _rate_limits[_client_address][_proto]
                _keep = []
                for (time_stamp, client_id, secret) in _failed:
                    if time_stamp + fail_cache < now:
                        expired.append((_client_address, _proto, time_stamp,
                                        client_id))
                    else:
                        _keep.append((time_stamp, client_id, secret))
                cur[proto] = _keep
            _rate_limits[_client_address] = cur
    except Exception, exc:
        logger.error("expire rate limit failed: %s" % exc)

    _rate_limits_lock.release()

    if expired:
        logger.info("expire %s rate limit expired %d items" % (proto,
                                                               len(expired)))
        # logger.debug("expire %s rate limit expired %s" % (proto, expired))

    return expired


def penalize_rate_limit(configuration, proto, client_address, client_id, hits,
                        max_fails=default_max_fails):
    """Stall client for a while based on the number of rate limit failures to
    make sure dictionary attackers don't really load the server with their
    repeated force-failed requests. The stall penalty is a linear function of
    the number of failed attempts.
    """
    logger = configuration.logger
    sleep_secs = 3 * (hits - max_fails)
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
    If session_id is _NOT_ set the client_ip:client_port
    is used as session_id.
    """
    logger = configuration.logger
    # msg = "track open session for %s" % client_id \
    #     + " from %s:%s with session_id: %s" % \
    #     (client_address, client_port, session_id)
    # logger.debug(msg)
    result = None
    status = False
    prev_authorized = False
    if session_id is None:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = ''
    try:
        status = True
        result = session_id
        _cached = _active_sessions.get(client_id, {})
        if not _cached:
            _active_sessions[client_id] = _cached
        _proto = _cached.get(proto, {})
        if not _proto:
            _cached[proto] = _proto
        _session = _cached[proto].get(session_id, {})
        if not _session:
            _cached[proto][session_id] = _session
        prev_authorized = _session.get('authorized', False)
        _session['session_id'] = session_id
        _session['client_id'] = client_id
        _session['ip_addr'] = client_address
        _session['tcp_port'] = client_port
        _session['authorized'] = authorized
        _session['timestamp'] = time.time()
    except Exception, exc:
        status = False
        session_id = None
        logger.error("track open session failed: %s" % exc)

    if not prelocked:
        _sessions_lock.release()

    # If GDP and changed from NOT authorized to authorized
    # perform GDP project login
    # TODO : Move GDP project login away from session tracking ?
    # TODO: Consider skipping 'project_logout + login' if an
    #       active session exists.
    #       Automatic 'project_logout' in '__validate_gdp_session'

    if configuration.site_enable_gdp \
            and status and authorized and not prev_authorized:
        project_login(
            configuration,
            client_address,
            proto,
            client_id)

    return result


def get_open_sessions(configuration,
                      proto,
                      client_id=None,
                      prelocked=False,
                      blocking=True):
    """Return active proto sessions for client_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, prelocked: %s, blocking: %s"
    #              % (proto, client_id, prelocked, blocking))
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    # logger.debug("_active_sessions: %s" % _active_sessions)
    if client_id is None:
        result = {}
        for (_, open_sessions) in _active_sessions.iteritems():
            open_proto_session = open_sessions.get(proto, {})
            if open_proto_session:
                result.update(open_proto_session)
    else:
        result = _active_sessions.get(client_id, {}).get(
            proto, {})
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
    """Track that client_id closed one proto session,
    returns dictionary with closed session"""
    logger = configuration.logger
    # msg = "track close session for proto: '%s'" % proto \
    #     + " from %s:%s with session_id: %s, client_id: %s, prelocked: %s" % \
    #     (client_address, client_port, session_id, client_id, prelocked)
    # logger.debug(msg)
    result = None
    status = False
    if session_id is None:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, prelocked=True)
    # logger.debug("_sessions : %s" % _sessions)
    if open_sessions and open_sessions.has_key(session_id):
        try:
            status = True
            closed_session = open_sessions[session_id]
            del open_sessions[session_id]
        except Exception, exc:
            status = False
            closed_session = None
            msg = "track close session failed for client: %s" % client_id \
                + "with session id: %s" % session_id \
                + ", error: %s" % exc
            logger.error(msg)
    else:
        msg = "track close session: %s _NOT_ found for client: %s" \
            % (session_id, client_id)
        logger.warning(msg)

    if not prelocked:
        _sessions_lock.release()

    # TODO: Move GDP project logout away from session tracking ?

    if status and configuration.site_enable_gdp \
            and closed_session.get('authorized', False):
        # logger.debug("track_close_project_logout: %s, %s" \
        #              % (_client_id, _session.keys()))
        # TODO: Should we raise an exception if project_logout fails ?
        project_logout(
            configuration,
            client_address,
            proto,
            closed_session['client_id'],
            autologout=True)

    if status:
        result = closed_session

    return result


def track_close_multiple_sessions(configuration,
                                  proto,
                                  session_ids,
                                  prelocked=False,
                                  blocking=True):
    """Close multiple sessions based on session_ids list,
    returns dictionary with closed sessions"""

    logger = configuration.logger
    # msg = "track close multiple sessions for proto: '%s'" % proto \
    #     + " with session_ids: %s, prelocked: %s" % \
    #     (session_ids, prelocked)
    # logger.debug(msg)
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, prelocked=True)
    # logger.debug("open_sessions: %s" % open_sessions)
    for cur_id in open_sessions.keys():
        if open_session_id in session_ids:
            cur_session = open_sessions[cur_id]
            closed_session = \
                track_close_session(configuration,
                                    proto,
                                    cur_session['client_id'],
                                    cur_session['ip_addr'],
                                    cur_session['tcp_port'],
                                    session_id=cur_id,
                                    prelocked=True)
            if closed_session is not None:
                result.update(closed_session)
    if not prelocked:
        _sessions_lock.release()

    return result


def track_close_expired_sessions(
        configuration,
        proto,
        client_id=None,
        prelocked=False,
        blocking=True):
    """Track expired sessions and close them,]
    returns dictionary with closed sessions"""

    logger = configuration.logger
    # msg = "track close sessions for proto: '%s'" % proto \
    #     + " with client_id: %s, prelocked: %s, blocking: %s" % \
    #     (client_id, prelocked, blocking)
    # logger.debug(msg)
    result = None
    status = False
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
        # logger.debug("current_timestamp - timestamp: %s"
        #              % (current_timestamp - timestamp))
        if current_timestamp - timestamp > session_timeout:
            cur_session = open_sessions[open_session_id]
            closed_session = \
                track_close_session(configuration,
                                    proto,
                                    cur_session['client_id'],
                                    cur_session['ip_addr'],
                                    cur_session['tcp_port'],
                                    session_id=cur_session['session_id'],
                                    prelocked=True)
            if closed_session is not None:
                result.update(closed_session)
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


def validate_session(configuration,
                     proto,
                     client_id,
                     client_address,
                     client_port):
    """Returns True if user session is valid."""
    logger = configuration.logger
    # msg = "proto: %s, client_id: %s" % (proto, client_id) \
    #     + " client_address: %s, client_port: %s" \
    #    % (client_address, client_port)
    # logger.debug(msg)
    result = True
    if configuration.site_enable_gdp:
        result = __validate_gdp_session(configuration,
                                        proto,
                                        client_id,
                                        client_address,
                                        client_port)

    return result


if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    conf.logger = logging
    test_proto, test_address, test_port, test_id = 'DUMMY', '127.0.0.42', 42000, 'user@some-domain.org'
    test_pw = "T3stp4ss"
    invalid_id = 'root'
    print "Running unit test on rate limit functions"
    print "Force expire all"
    expired = expire_rate_limit(conf, test_proto, fail_cache=0)
    print "Expired: %s" % expired
    this_pw = test_pw
    print "Emulate rate limit"
    for i in range(default_max_fails-1):
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
    print "Test for same user and address with emulated cache timeout"
    hit = hit_rate_limit(conf, test_proto, test_address, test_id,
                         fail_cache=1)
    print "Blocked: %s" % hit
    print "Force expire some entries"
    expired = expire_rate_limit(conf, test_proto,
                                fail_cache=default_max_fails)
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
