#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons - grid daemon helper functions
# Copyright (C) 2010-2016  The MiG Project lead by Brian Vinter
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
from shared.defaults import dav_domain
from shared.fileio import unpickle
from shared.safeinput import valid_path
from shared.sharelinks import extract_mode_id
from shared.ssh import parse_pub_key
from shared.useradm import ssh_authkeys, davs_authkeys, ftps_authkeys, \
    get_authkeys, ssh_authpasswords, ssh_authdigests, davs_authpasswords, \
    davs_authdigests, ftps_authpasswords, ftps_authdigests, \
    get_authpasswords, extract_field, generate_password_hash, \
    generate_password_digest

default_max_hits, default_fail_cache = 5, 120

_rate_limits = {}
_rate_limits_lock = threading.Lock()
_active_sessions = {}
_sessions_lock = threading.Lock()

class Login(object):
    """Login class to hold a single valid login for a user, job or share.

    The login method can be one of password, password digest or public key.
    The optional chroot marks the ulogin for chrooting to the user home.
    The optional ip_addr argument can be used to limit login source to a single
    IP address. This is particularly useful in relation to job sshfs mounts.
    """
    def __init__(self, username, home, password=None, digest=None,
                 public_key=None, chroot=True, ip_addr=None):
        self.username = username
        self.password = password
        self.digest = digest
        self.public_key = public_key
        self.chroot = chroot
        self.ip_addr = ip_addr
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

def get_fs_path(user_path, root, chroot_exceptions):
    """Internal helper to translate path with chroot and invisible files
    in mind. Also assures general path character restrictions are applied.
    """
    try:
        valid_path(user_path)
    except:
        raise ValueError("Invalid path characters")
    # Make sure leading slashes in user_path don't throw away root
    real_path = os.path.normpath(os.path.join(root, user_path.strip(os.sep)))
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
           True in [os.path.realpath(path).startswith(i) for i in \
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
                 os.path.getsize(authkeys_path) > 0:
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
                logger.info("outdated authdigests_path %s (%s)" % \
                            (authdigests_path, first.last_update))
                first.last_update = os.path.getmtime(authdigests_path)
                changed_paths.append(authdigests_path)
        elif os.path.exists(authdigests_path) and \
                 os.path.getsize(authdigests_path) > 0:
            logger.info("no old digest users and found authdigests_path %s" % \
                        authdigests_path)
            logger.info("old users: %s" % ["%s" %i for i in old_users])
            changed_paths.append(authdigests_path)

    return changed_paths

def get_job_changes(conf, username, mrsl_path):
    """Check if job mount changed for username using the provided mrsl_path
    file and the saved time stamp from jobs embedded in conf.
    Returns a list of changed mrsl files with the empty list if none changed.
    """
    logger = conf.get("logger", logging.getLogger())
    old_users = [i for i in conf['jobs'] if i.username == username]
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
    old_users = [i for i in conf['shares'] if i.username == username]
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
    logging.debug("changed shares: %s" % changed_paths)
    return changed_paths

def add_user_object(conf, login, home, password=None, digest=None, pubkey=None,
                    chroot=True):
    """Add a single Login object to active user list"""
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    user = Login(username=login, home=home, password=password,
                 digest=digest, public_key=pubkey, chroot=chroot)
    logger.debug("Adding user login:\n%s" % user)
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
    logger.debug("Adding job login:\n%s" % job)
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
    logger.debug("Adding share login:\n%s" % share)
    if creds_lock:
        creds_lock.acquire()
    conf['shares'].append(share)
    if creds_lock:
        creds_lock.release()


def update_user_objects(conf, auth_file, path, user_vars, auth_protos):
    """Update login objects for auth_file with path to conf users dict. Remove
    any old entries for user and add the current ones.
    """
    logger = conf.get("logger", logging.getLogger())
    creds_lock = conf.get('creds_lock', None)
    proto_authkeys, proto_authpasswords, proto_authdigests = auth_protos
    user_id, user_alias, user_dir, short_id, short_alias = user_vars
    user_logins = (user_alias, short_id, short_alias)

    # Create user entry for each valid key and password 
    if creds_lock:
        creds_lock.acquire()
    if auth_file == proto_authkeys:
        all_keys = get_authkeys(path)
        all_passwords = []
        all_digests = []
        # Clean up all old key entries for this user
        conf['users'] = [i for i in conf['users'] \
                         if i.username not in user_logins or \
                         i.public_key is None]
    elif auth_file == proto_authpasswords:
        all_keys = []
        all_passwords = get_authpasswords(path)
        all_digests = []
        # Clean up all old password entries for this user
        conf['users'] = [i for i in conf['users'] \
                         if i.username not in user_logins or \
                         i.password is None]
    else:
        all_keys = []
        all_passwords = []
        all_digests = get_authpasswords(path)
        # Clean up all old digest entries for this user
        conf['users'] = [i for i in conf['users'] \
                         if i.username not in user_logins or \
                         i.digest is None]
    #logger.debug("after clean up old users list is:\n%s" % \
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
            logger.warning("Skipping broken key %s for user %s (%s)" % \
                           (user_key, user_id, exc))
            continue
        add_user_object(conf, user_alias, user_dir, pubkey=user_key)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, pubkey=user_key)
            add_user_object(conf, short_alias, user_dir, pubkey=user_key)
    for user_password in all_passwords:
        user_password = user_password.strip()
        add_user_object(conf, user_alias, user_dir, password=user_password)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, password=user_password)
            add_user_object(conf, short_alias, user_dir,
                            password=user_password)
    for user_digest in all_digests:
        user_digest = user_digest.strip()
        add_user_object(conf, user_alias, user_dir, digest=user_digest)
        # Add short alias copy if user aliasing is enabled
        if short_id:
            add_user_object(conf, short_id, user_dir, digest=user_digest)
            add_user_object(conf, short_alias, user_dir, digest=user_digest)
    #logger.debug("after update users list is:\n%s" % \
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
    else:
        logger.error("Invalid protocol: %s" % protocol)
        return (conf, changed_users)

    auth_protos = (proto_authkeys, proto_authpasswords, proto_authdigests)

    # We support direct and symlinked usernames for now
    # NOTE: entries are gracefully removed if user no longer exists
    authkeys_path = os.path.realpath(os.path.join(conf['root_dir'], username,
                                                  proto_authkeys))
    authpasswords_path = os.path.realpath(os.path.join(conf['root_dir'],
                                                       username,
                                                       proto_authpasswords))
    authdigests_path = os.path.realpath(os.path.join(conf['root_dir'],
                                                     username,
                                                     proto_authdigests))

    logger.debug("Updating user creds for %s" % username)

    changed_paths = get_creds_changes(conf, username, authkeys_path,
                                      authpasswords_path, authdigests_path)
    if not changed_paths:
        logger.debug("No user creds changes for %s" % username)
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
        if path not in changed_paths:
            logger.debug("Skipping %s without changes" % path)
            continue
        # Missing alias symlink - should be fixed for user instead
        if not os.path.exists(path):
            logger.warning("Skipping non-existant home %s" % path)
            continue
        logger.debug("Checking %s" % path)
        user_home = path.replace(os.sep + auth_file, '')
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        if conf['user_alias']:
            short_id = extract_field(user_id, conf['user_alias'])
            # Allow both raw alias field value and asciified alias            
            logger.debug("find short_alias for %s" % short_alias)
            short_alias = client_alias(short_id)
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(conf, auth_file, path, user_vars, auth_protos)
    if changed_paths:
        logger.info("Refreshed user %s from configuration: %s" % \
                    (username, changed_paths))
        changed_users.append(username)
    return (conf, changed_users)


def refresh_users(configuration, protocol):
    """Reload users from auth confs if they changed on disk. Add user entries
    to configuration.daemon_conf['users'] for all active keys and passwords
    enabled in configuration. Optionally add short ID username alias entries
    for all users if that is enabled in the configuration.
    Removes all the user entries no longer active, too.
    The protocol argument specifies which auth files to use.
    Returns a tuple with the updated daemon_conf and the list of changed user
    IDs.
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
    matches = []
    if conf['allow_publickey']:
        matches += [(proto_authkeys, i) for i in glob.glob(authkeys_pattern)]
    if conf['allow_password']:
        matches += [(proto_authpasswords, i) \
                    for i in glob.glob(authpasswords_pattern)] 
    if conf['allow_digest']:
        matches += [(proto_authdigests, i) \
                    for i in glob.glob(authdigests_pattern)] 
    for (auth_file, path) in matches:
        logger.debug("Checking %s" % path)
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
            short_id = extract_field(user_id, conf['user_alias'])
            # Allow both raw alias field value and asciified alias            
            cur_usernames.append(short_id)
            logger.debug("find short_alias for %s" % short_alias)
            short_alias = client_alias(short_id)
            cur_usernames.append(short_alias)
        if last_update >= os.path.getmtime(path):
            continue
        user_vars = (user_id, user_alias, user_dir, short_id, short_alias)
        update_user_objects(conf, auth_file, path, user_vars, auth_protos)
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
    logger.info("Refreshed users from configuration (%d users)" % \
                len(conf['users']))
    conf['time_stamp'] = time.time()
    return (conf, changed_users)


def refresh_job_creds(configuration, protocol, username):
    """Reload job credentials for username (SID) if they changed on disk.
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
    old_usernames = [i.username for i in conf['jobs']]
    cur_usernames = []
    if not protocol in ('sftp',):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_jobs)

    link_path = os.path.join(configuration.sessid_to_mrsl_link_home,
                            "%s.mRSL" % username)

    logger.debug("Updating job creds for %s" % username)

    changed_paths = get_job_changes(conf, username, link_path)
    if not changed_paths:
        logger.debug("No job creds changes for %s" % username)
        return (conf, changed_jobs)

    job_dict = None
    if os.path.islink(link_path) and os.path.exists(link_path) and \
           last_update < os.path.getmtime(link_path):
        sessionid = username
        job_dict = unpickle(link_path, logger)
            
    # We only allow connections from executing jobs that
    # has a public key
    if not job_dict is None and type(job_dict) == dict and \
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
        user_url = job_dict['RESOURCE_CONFIG']['HOSTURL']
        user_ip = socket.gethostbyname_ex(user_url)[2][0]

        # Make sure pub key is valid
        valid_pubkey = True
        try:    
            _ = parse_pub_key(user_key)
        except Exception, exc:
            valid_pubkey = False
            logger.warning("Skipping broken key '%s' for user %s (%s)" % \
                           (user_key, user_alias, exc))

        if valid_pubkey:
            add_job_object(conf, user_alias, user_dir, pubkey=user_key,
                           ip_addr=user_ip)
            cur_usernames.append(user_alias)
            changed_jobs.append(user_alias)
                
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d finished jobs" % len(removed))
        conf['jobs'] = [i for i in conf['jobs'] if not i.username in removed]
        changed_jobs += removed
    logger.info("Refreshed jobs from configuration (%d jobs)" % \
                len(conf['jobs']))
    return (conf, changed_jobs)

def refresh_jobs(configuration, protocol):
    """Refresh job keys based on the job state.
    Add user entries for all active job keys. 
    Removes all the user entries for jobs no longer active.
    Returns a tuple with the daemon_conf and the list of changed job IDs.
    """
    changed_jobs = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    old_usernames = [i.username for i in conf['jobs']]
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
        if not job_dict is None and type(job_dict) == dict and \
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
            user_url = job_dict['RESOURCE_CONFIG']['HOSTURL']
            user_ip = socket.gethostbyname_ex(user_url)[2][0]

            # Make sure pub key is valid
            try:    
                _ = parse_pub_key(user_key)
            except Exception, exc:
                logger.warning("Skipping broken key '%s' for user %s (%s)" % \
                               (user_key, user_alias, exc))
                continue 
                    
            add_job_object(conf, user_alias, user_dir, pubkey=user_key,
                           ip_addr=user_ip)
            cur_usernames.append(user_alias)
            changed_jobs.append(user_alias)
                
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d finished jobs" % len(removed))
        conf['jobs'] = [i for i in conf['jobs'] if not i.username in removed]
        changed_jobs += removed
    logger.info("Refreshed jobs from configuration (%d jobs)" % \
                len(conf['jobs']))
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
    old_usernames = [i.username for i in conf['shares']]
    cur_usernames = []
    if not protocol in ('sftp', ):
        logger.error("invalid protocol: %s" % protocol)
        return (conf, changed_shares)
    if [kind for kind in share_modes if kind != 'read-write']:
        logger.error("invalid share_modes: %s" % share_modes)
        return (conf, changed_shares)
    (mode, _) = extract_mode_id(configuration, username)
    if not mode in share_modes:
        logger.error("invalid share mode %s for %s" % (mode, username))
        return (conf, changed_shares)

    logger.debug("Updating share creds for %s" % username)

    link_path = os.path.join(configuration.sharelink_home, mode, username)
    try:
        link_dest = os.readlink(link_path)
        if not link_dest.startswith(base_dir):
            raise ValueError("Invalid base for share %s" % username)
    except Exception, err:
        logger.error("invalid share %s: %s" % (username, err))
        return (conf, changed_shares)

    logger.debug("inspecting link %s pointing at %s" % (link_path, link_dest))

    changed_paths = get_share_changes(conf, username, link_path)
    if not changed_paths:
        logger.debug("No share creds changes for %s" % username)
        return (conf, changed_shares)

    share_dict = None
    if os.path.islink(link_path) and os.path.isdir(link_dest) and \
           last_update < os.path.getmtime(link_path):
        share_id = username
        # NOTE: share link points inside user home of owner so extract here
        share_root = link_dest.replace(base_dir, '').lstrip(os.sep)
        # NOTE: just use share_id as password/digest for now
        share_pw_hash = generate_password_hash(share_id)
        share_pw_digest = generate_password_digest(
            dav_domain, share_id, share_id,
            configuration.site_digest_salt)
        # TODO: load pickle from user_settings of owner (from link_dest)?
        share_dict = {'share_id': share_id, 'share_root': share_root,
                      'share_pw_hash': share_pw_hash,
                      'share_pw_digest': share_pw_digest}
    
    # We only allow access to active shares
    if not share_dict is None and type(share_dict) == dict and \
           share_dict.has_key('share_id') and \
           share_dict.has_key('share_root') and \
           share_dict.has_key('share_pw_hash') and \
           share_dict.has_key('share_pw_digest'):
        user_alias = share_id
        user_dir = share_dict['share_root']
        user_password = share_dict['share_pw_hash']
        user_digest = share_dict['share_pw_digest']
        logger.info("Adding login for share %s" % user_alias)
        add_share_object(conf, user_alias, user_dir, password=user_password,
                         digest=user_digest)
        cur_usernames.append(user_alias)
        changed_shares.append(user_alias)
    
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d inactive shares" % len(removed))
        conf['shares'] = [i for i in conf['shares'] if not i.username in removed]
        changed_shares += removed
    logger.info("Refreshed shares from configuration (%d shares)" % \
                len(conf['shares']))
    return (conf, changed_shares)

def refresh_shares(configuration, protocol, share_modes=['read-write']):
    """Refresh shares keys based on the sharelink state.
    Add user entries for all active sharelinks. 
    Removes all the user entries for sharelinks no longer active.
    Returns a tuple with the daemon_conf and the list of changed sharelink IDs.
    NOTE: we limit share_modes to read-write sharelinks for now since we don't
    have guards in place to support read-only or write-only mode in daemons.
    NOTE: we further limit to directory sharelinks for chroot'ing.
    """
    # Must end in sep
    base_dir = configuration.user_home.rstrip(os.sep) + os.sep
    changed_shares = []
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    old_usernames = [i.username for i in conf['shares']]
    cur_usernames = []
    if not protocol in ('sftp', ):
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
            share_pw_hash = generate_password_hash(share_id)
            share_pw_digest = generate_password_digest(
                dav_domain, share_id, share_id,
                configuration.site_digest_salt)
            # TODO: load pickle from user_settings of owner (from link_dest)?
            share_dict = {'share_id': share_id, 'share_root': share_root,
                          'share_pw_hash': share_pw_hash,
                          'share_pw_digest': share_pw_digest}
            
        # We only allow access to active shares
        if not share_dict is None and type(share_dict) == dict and \
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
        logger.info("Removing login for %d finished shares" % len(removed))
        conf['shares'] = [i for i in conf['shares'] if not i.username in removed]
        changed_shares += removed
    logger.info("Refreshed shares from configuration (%d shares)" % \
                len(conf['shares']))
    return (conf, changed_shares)

def update_login_map(daemon_conf, changed_users, changed_jobs=[],
                     changed_shares=[]):
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
        login_map[username] = [i for i in daemon_conf['users'] if username == \
                               i.username]
    for username in changed_jobs:
        login_map[username] = [i for i in daemon_conf['jobs'] if username == \
                               i.username]
    for username in changed_shares:
        login_map[username] = [i for i in daemon_conf['shares'] if username == \
                               i.username]
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
                   max_fails=default_max_hits,
                   fail_cache=default_fail_cache):
    """Check if proto login from client_address with client_id should be
    filtered due to too many recently failed login attempts. Returns True if
    so and False otherwise based on a lookup in rate limit database defined in
    configuration.
    The rate limit database is a dictionary with client_address as key and
    dictionaries mapping proto to list of failed attempts.
    We allow up to max_fails failed logins within the last fail_cache seconds.
    """
    logger = configuration.logger
    refuse = False
    hits = 0
    now = time.time()

    _rate_limits_lock.acquire()

    try:
        _cached = _rate_limits.get(client_address, {})
        if _cached:
            _failed = _cached.get(proto, [])
            for (time_stamp, client_id, _) in _failed:
                if time_stamp + fail_cache < now:
                    continue
                hits += 1
            if hits >= max_fails:
                refuse = True 
    except Exception, exc:
        logger.error("hit rate limit failed: %s" % exc)

    _rate_limits_lock.release()

    if hits > 0:
        logger.info("hit rate limit found %d hit(s) on %s from %s" % \
                    (hits, proto, client_address))
    return refuse

def update_rate_limit(configuration, proto, client_address, client_id,
                      success, secret=None):
    """Update rate limit database after proto login from client_address with
    client_id and login success status.
    The optional secret can be used to save the hash or similar so that
    repeated failures with the same credentials only count as one error.
    Otherwise some clients will retry on failure and hit the limit easily.
    The rate limit database is a dictionary with client_address as key and
    dictionaries mapping proto to list of failed attempts.
    We simply append failed attempts and success results in the list getting
    cleared for that proto and address combination.
    """
    logger = configuration.logger
    _failed = []
    cur = {}
    failed_count = 0
    status = {True: "success", False: "failure"}

    _rate_limits_lock.acquire()
    try:
        #logger.debug("update rate limit db: %s" % _rate_limits)
        _cached = _rate_limits.get(client_address, {})
        cur.update(_cached)
        if not success:
            _failed = _cached.get(proto, [])
            if not secret or (client_id, secret) not in [(i[1], i[2]) for i in _failed]:
                _failed.append((time.time(), client_id, secret))
            failed_count = len(_failed)
            
        cur[proto] = _failed
        _rate_limits[client_address] = cur
    except Exception, exc:
        logger.error("update rate limit failed: %s" % exc)

    _rate_limits_lock.release()

    if failed_count > 0:
        logger.info("update rate limit %s for %s from %s on %s to %d hits" % \
                    (status[success], client_id, client_address, proto,
                     len(_failed)))
        logger.debug("update rate limit to %s" % _failed)
    return failed_count

def expire_rate_limit(configuration, proto='*', fail_cache=default_fail_cache):
    """Remove rate limit database entries older than fail_cache seconds. Only
    entries with protocol matching proto pattern will be touched.
    Returns a list of expired entries.
    """
    logger = configuration.logger
    now = time.time()
    expired = []
    
    #logger.debug("expire entries older than %ds at %s" % (fail_cache, now))

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
        logger.info("expire rate limit on proto %s expired %d items" % \
                    (proto, len(expired)))
        logger.debug("expire rate limit on proto %s expired %s" % \
                    (proto, expired))

    return expired

def penalize_rate_limit(configuration, proto, client_address, client_id, hits,
                        max_fails=default_max_hits):
    """Stall client for a while based on the number of rate limit failures to
    make sure dictionary attackers don't really load the server with their
    repeated force-failed requests. The stall penalty is a linear function of
    the number of failed attempts.
    """
    logger = configuration.logger
    sleep_secs = 3 * (hits - max_fails)
    if sleep_secs > 0:
        logger.info("stall rate limited %s user %s from %s for %ds" % \
                    (proto, client_id, client_address, sleep_secs))
        time.sleep(sleep_secs)
    return sleep_secs

def track_open_session(configuration, proto, client_id, client_address):
    """Track that client_id opened a new session from client_address"""
    logger = configuration.logger
    logger.info("track open session for %s from %s" % (client_id,
                                                       client_address))
    _sessions_lock.acquire()
    try:
        _cached = _active_sessions.get(client_id, {})
        if not _cached:
            _active_sessions[client_id] = _cached
        _active = _cached.get(proto, [])
        if not _active:
            _cached[proto] = _active 
        _active.append(client_address)
    except Exception, exc:
        logger.error("track open session failed: %s" % exc)
    _sessions_lock.release()

def track_close_session(configuration, proto, client_id, client_address):
    """Track that client_id opened a new session from client_address"""
    logger = configuration.logger
    logger.info("track close session for %s from %s" % (client_id,
                                                        client_address))
    _sessions_lock.acquire()
    try:
        _cached = _active_sessions.get(client_id, {})
        _active = _cached.get(proto, [])
        first_match = _active.index(client_address)
        del _active[first_match]
    except Exception, exc:
        logger.error("track close session failed: %s" % exc)
    _sessions_lock.release()

def active_sessions(configuration, proto, client_id):
    """Look up how many active proto sessions client_id has running"""
    logger = configuration.logger
    active_count = 0
    _sessions_lock.acquire()
    try:
        logger.debug("active sessions: %s" % _active_sessions)
        _cached = _active_sessions.get(client_id, {})
        _active = _cached.get(proto, [])
        active_count = len(_active)
    except Exception, exc:
        logger.error("active sessions failed: %s" % exc)
    _sessions_lock.release()
    return active_count
    

if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    conf.logger = logging
    test_proto, test_address, test_id = 'DUMMY', '127.0.0.42', 'mylocaluser'
    test_pw = "T3stp4ss"
    print "Running unit test on rate limit functions"
    print "Force expire all"
    expired = expire_rate_limit(conf, test_proto, fail_cache=0)
    print "Expired: %s" % expired
    this_pw = test_pw
    print "Emulate rate limit"
    for i in range(default_max_hits-1):
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
    other_proto, other_address, other_id = "BOGUS", '127.10.20.30', 'otheruser'
    other_pw = "0th3rP4ss"
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
    time.sleep(1)
    print "Emulate cache time out"
    hit = hit_rate_limit(conf, test_proto, test_address, test_id,
                         fail_cache=1)
    print "Blocked: %s" % hit
    print "Force expire some entries"
    expired = expire_rate_limit(conf, test_proto,
                                fail_cache=default_max_hits)
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

    print "Test active session counting"
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" %  active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" %  active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" %  active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" %  active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" %  active_count
