#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons - grid daemon helper functions
# Copyright (C) 2010-2014  The MiG Project lead by Brian Vinter
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

import glob
import logging
import os
import time

from shared.base import client_dir_id, client_alias, invisible_path
from shared.ssh import parse_pub_key
from shared.useradm import ssh_authkeys, davs_authkeys, ftps_authkeys, \
     get_authkeys, ssh_authpasswords, davs_authpasswords, ftps_authpasswords, \
     get_authpasswords, extract_field


class User(object):
    """User login class to hold a single valid login for a user"""
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None):
        self.username = username
        self.password = password
        self.chroot = chroot
        self.public_key = public_key
        if type(public_key) in (str, unicode):
            # We already checked that key is valid if we got here
            self.public_key = parse_pub_key(public_key)

        self.home = home
        if self.home is None:
            self.home = self.username

    def __str__(self):
        """String formater"""
        return 'username: %s\nhome: %s\npassword: %s\npublic_key: %s' % \
               (self.username, self.home, self.password, self.public_key)

def get_fs_path(user_path, root, chroot_exceptions):
    """Internal helper to translate path with chroot and invisible files
    in mind"""
    real_path = "%s/%s" % (root, user_path)
    real_path = real_path.replace('//', '/')
    accept_roots = [root] + chroot_exceptions

    accepted = False
    for accept_path in accept_roots:
        expanded_path = os.path.realpath(real_path)
        if expanded_path.startswith(accept_path):
            # Found matching root - check visibility
            if not invisible_path(real_path):
                accepted = True
            break        
    if not accepted:
        raise ValueError("Invalid path")
    return real_path

def strip_root(path, root, chroot_exceptions):
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
        mode = mode.replace('w', 'r+', 1)
    return mode

def acceptable_chmod(path, mode, chmod_exceptions):
    """Internal helper to check that a chmod request is safe. That is, it
    only changes permissions that does not lock out user. Furthermore anything
    inside the dirs in chmod_exceptions should be left alone to avoid users
    touching read-only files or enabling execution of custom cgi scripts with
    potentially arbitrary code.
    We require preservation of user read+write on files and user
    read+write+execute on dirs.
    Limitation to sane group/other access perms is left to the caller.
    """
    if True in [os.path.realpath(path).startswith(i + os.sep) \
                for i in chmod_exceptions]:
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


def refresh_users(configuration, protocol):
    '''Reload users from conf if it changed on disk. Add user entries for all
    active keys and passwords enabled in conf. Optionally add short ID
    username alias entries for all users if that is enabled in the conf.
    Removes all the user entries no longer active, too.
    The protocol argument specifies which auth files to use.
    '''
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    last_update = conf['time_stamp']
    old_usernames = [i.username for i in conf['users']]
    cur_usernames = []
    if protocol in ('ssh', 'sftp', 'scp', 'rsync'):
        proto_authkeys = ssh_authkeys
        proto_authpasswords = ssh_authpasswords
    elif protocol in ('dav', 'davs'):
        proto_authkeys = davs_authkeys
        proto_authpasswords = davs_authpasswords
    elif protocol in ('ftp', 'ftps'):
        proto_authkeys = ftps_authkeys
        proto_authpasswords = ftps_authpasswords
    else:
        logger.error("invalid protocol: %s" % protocol)
    authkeys_pattern = os.path.join(conf['root_dir'], '*', proto_authkeys)
    authpasswords_pattern = os.path.join(conf['root_dir'], '*',
                                         proto_authpasswords)
    short_id, short_alias = None, None
    matches = []
    if conf['allow_publickey']:
        matches += [(proto_authkeys, i) for i in glob.glob(authkeys_pattern)]
    if conf['allow_password']:
        matches += [(proto_authpasswords, i) \
                    for i in glob.glob(authpasswords_pattern)] 
    for (auth_file, path) in matches:
        logger.debug("Checking %s" % path)
        user_home = path.replace(os.sep + auth_file, '')
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        cur_usernames.append(user_alias)
        if conf['user_alias']:
            short_id = extract_field(user_id, conf['user_alias'])
            # Allow both raw alias field value and asciified alias            
            cur_usernames.append(short_id)
            logger.debug("find short_alias for %s" % short_alias)
            short_alias = client_alias(short_id)
            cur_usernames.append(short_alias)
        if last_update >= os.path.getmtime(path):
            continue
        # Create user entry for each valid key and password 
        if auth_file == proto_authkeys:
            all_keys = get_authkeys(path)
            all_passwords = []
            # Clean up all old key entries for this user
            conf['users'] = [i for i in conf['users'] \
                             if i.username != user_alias or \
                             i.public_key is None]
        else:
            all_keys = []
            all_passwords = get_authpasswords(path)
            # Clean up all old password entries for this user
            conf['users'] = [i for i in conf['users'] \
                             if i.username != user_alias or \
                             i.password is None]
        for user_key in all_keys:
            # Remove comments and blank lines
            user_key = user_key.split('#', 1)[0].strip()
            if not user_key:
                continue
            # Make sure pub key is valid
            try:
                _ = parse_pub_key(user_key)
            except Exception, exc:
                logger.warning("Skipping broken key %s for user %s (%s)" % \
                               (user_key, user_id, exc))
                continue
            logger.debug(
                "Adding user:\nname: %s\nalias: %s\nhome: %s\nkey: %s" % \
                (user_id, user_alias, user_dir, user_key))
            conf['users'].append(
                User(username=user_alias, home=user_dir, password=None,
                     public_key=user_key, chroot=True),
                )
            # Add short alias copy if user aliasing is enabled
            if short_id:
                logger.debug(
                    "Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s" % \
                    (user_id, short_id, user_dir, user_key))
                conf['users'].append(
                    User(username=short_id, home=user_dir, password=None,
                         public_key=user_key, chroot=True),
                    )
                logger.debug(
                    "Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s" % \
                    (user_id, short_alias, user_dir, user_key))
                conf['users'].append(
                    User(username=short_alias, home=user_dir, password=None,
                         public_key=user_key, chroot=True),
                    )
        for user_password in all_passwords:
            user_password = user_password.strip()
            logger.debug("Adding user:\nname: %s\nalias: %s\nhome: %s\npw: %s"\
                        % (user_id, user_alias, user_dir, user_password))
            conf['users'].append(
                User(username=user_alias, home=user_dir,
                     password=user_password, public_key=None, chroot=True))
            # Add short alias copy if user aliasing is enabled
            if short_id:
                logger.debug(
                    "Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s" % \
                    (user_id, short_id, user_dir, user_password))
                conf['users'].append(
                    User(username=short_id, home=user_dir,
                         password=user_password, public_key=None, chroot=True),
                    )
                logger.debug(
                    "Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s" % \
                    (user_id, short_alias, user_dir, user_password))
                conf['users'].append(
                    User(username=short_alias, home=user_dir,
                         password=user_password, public_key=None, chroot=True),
                    )
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d deleted users" % len(removed))
        conf['users'] = [i for i in conf['users'] if not i.username in removed]
    logger.info("Refreshed users from configuration (%d users)" % \
                len(conf['users']))
    conf['time_stamp'] = time.time()
    return conf
