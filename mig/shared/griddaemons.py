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

import fnmatch
import glob
import logging
import os
import shelve
import socket
import time

from shared.base import client_dir_id, client_alias, invisible_path
from shared.fileio import unpickle, acquire_file_lock, release_file_lock
from shared.ssh import parse_pub_key
from shared.useradm import ssh_authkeys, davs_authkeys, ftps_authkeys, \
     get_authkeys, ssh_authpasswords, davs_authpasswords, ftps_authpasswords, \
     get_authpasswords, extract_field

default_max_hits, default_fail_cache = 5, 120

class User(object):
    """User login class to hold a single valid login for a user"""
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None, ip_addr=None):
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

        self.ip_addr = ip_addr

    def __str__(self):
        """String formater"""
        return 'username: %s\nhome: %s\npassword: %s\npublic_key: %s' % \
               (self.username, self.home, self.password, self.public_key)


def force_utf8(val):
    """Internal helper to encode unicode strings to utf8 version"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, unicode):
        return val
    return val.encode("utf8")

def force_unicode(val):
    """Internal helper to decode unicode strings from utf8 version"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, unicode):
        return val.decode("utf8")
    return val

def get_fs_path(user_path, root, chroot_exceptions):
    """Internal helper to translate path with chroot and invisible files
    in mind"""
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
        # Skip OpenID alias symlinks
        if os.path.islink(user_home):
            continue
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        # we always accept both dir formatted and asciified distinguished name
        cur_usernames.append(user_dir)
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


def refresh_jobs(configuration, protocol):
    conf = configuration.daemon_conf
    logger = conf.get("logger", logging.getLogger())
    old_usernames = [i.username for i in conf['jobs']]
    cur_usernames = []
    if protocol in ('sftp'):
        proto_authkeys = ssh_authkeys
        proto_authpasswords = None
    else:
        logger.error("invalid protocol: %s" % protocol)

    for (_, _, filenames) in os.walk(configuration.sessid_to_mrsl_link_home):
        for filename in filenames:
            filepath = os.path.join(configuration.sessid_to_mrsl_link_home, filename)
            if os.path.islink(filepath) and filepath.endswith('.mRSL'):
                sessionid = filename[:-5]
                job_dict = unpickle(filepath, logger)
                
                # We only allow connections from executing jobs that
                # has a public key
                if job_dict and \
                        job_dict.has_key('STATUS') and \
                        job_dict['STATUS'] == 'EXECUTING' and \
                        job_dict.has_key('SESSIONID') and \
                        job_dict['SESSIONID'] == sessionid and \
                        job_dict.has_key('USER_CERT') and \
                        job_dict.has_key('MOUNT') and \
                        job_dict.has_key('MOUNTSSHPUBLICKEY'):
                    user_alias = sessionid
                    user_dir = job_dict['USER_CERT'].replace(' ', '_').replace('/', '+')
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
                    
                    conf['jobs'].append(User(username=user_alias, 
                                home=user_dir, password=None,
                                public_key=user_key, chroot=True, ip_addr=user_ip))
                    cur_usernames.append(user_alias)
                
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d finished jobs" % len(removed))
        conf['jobs'] = [i for i in conf['jobs'] if not i.username in removed]
    logger.info("Refreshed jobs from configuration (%d jobs)" % \
                len(conf['jobs']))

    return conf


def hit_rate_limit(configuration, proto, client_address, client_id,
                   max_fails=default_max_hits,
                   fail_cache=default_fail_cache):
    """Check if proto login from client_address with client_id should be
    filtered due to too many recently failed login attempts. Returns True if
    so and False otherwise based on a lookup in rate limit database defined in
    configuration.
    The rate limit database is a shelve with client_address as key and
    dictionaries mapping proto to list of failed attempts.
    We allow up to max_fails failed logins within the last fail_cache seconds.
    """
    logger = configuration.logger
    refuse = False
    hits = 0
    now = time.time()
    lock_path = configuration.rate_limit_db + '.lock'
    
    lock_handle = acquire_file_lock(lock_path, False)

    try:
        rate_limits = shelve.open(configuration.rate_limit_db)
        _cached = rate_limits.get(client_address, {})
        if _cached:
            _failed = _cached.get(proto, [])
            for (time_stamp, client_id) in _failed:
                if time_stamp + fail_cache < now:
                    continue
                hits += 1
            if hits >= max_fails:
                refuse = True 
        rate_limits.close()
    except Exception, exc:
        logger.error("hit rate limit failed: %s" % exc)

    release_file_lock(lock_handle)

    logger.info("hit rate limit found %d hit(s) for %s on %s from %s" % \
                (hits, client_id, proto, client_address))
    return refuse

def update_rate_limit(configuration, proto, client_address, client_id,
                      success):
    """Update rate limit database after proto login from client_address with
    client_id and login success status.
    The rate limit database is a shelve with client_address as key and
    dictionaries mapping proto to list of failed attempts.
    We simply append failed attempts and success results in the list getting
    cleared for that proto and address combination.
    Please note that we have to explicitly update root values because we use
    shelves without writeback.
    """
    logger = configuration.logger
    lock_path = configuration.rate_limit_db + '.lock'
    _failed = []
    cur = {}
    status = {True: "success", False: "failure"}

    lock_handle = acquire_file_lock(lock_path, True)

    try:
        rate_limits = shelve.open(configuration.rate_limit_db)
        logger.debug("update rate limit db: %s" % rate_limits)
        _cached = rate_limits.get(client_address, {})
        cur.update(_cached)
        if not _cached or success:
            cur[proto] = []
        else:
            _failed = _cached.get(proto, [])
            _failed.append((time.time(), client_id))
            cur[proto] = _failed
        rate_limits[client_address] = cur
        rate_limits.close()
    except Exception, exc:
        logger.error("update rate limit failed: %s" % exc)

    release_file_lock(lock_handle)
    
    logger.info("update rate limit %s for %s from %s on %s to %s" % \
                (status[success], client_id, client_address, proto, _failed))
        

def expire_rate_limit(configuration, proto='*', fail_cache=default_fail_cache):
    """Remove rate limit database entries older than fail_cache seconds. Only
    entries with protocol matching proto pattern will be touched.
    Returns a list of expired entries.
    Please note that we have to explicitly update root values because we use
    shelves without writeback.
    """
    logger = configuration.logger
    lock_path = configuration.rate_limit_db + '.lock'
    now = time.time()
    expired = []
    
    lock_handle = acquire_file_lock(lock_path, True)

    logger.debug("expire entries older than %ds at %s" % (fail_cache, now))
    try:
        rate_limits = shelve.open(configuration.rate_limit_db)
        for _client_address in rate_limits.keys():
            cur = {}
            for _proto in rate_limits[_client_address]:
                if not fnmatch.fnmatch(_proto, proto):
                    continue
                _failed = rate_limits[_client_address][_proto]
                _keep = []
                for (time_stamp, client_id) in _failed:
                    if time_stamp + fail_cache < now:
                        expired.append((_client_address, _proto, time_stamp,
                                        client_id))
                    else:
                        _keep.append((time_stamp, client_id))
                cur[proto] = _keep
            rate_limits[_client_address] = cur
        rate_limits.close()
    except Exception, exc:
        logger.error("expire rate limit failed: %s" % exc)
        
    release_file_lock(lock_handle)

    logger.info("expire rate limit on proto %s expired %s" % (proto, expired))

    return expired

if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    conf.logger = logging
    test_proto, test_address, test_id = 'DUMMY', '127.0.0.42', 'mylocaluser'
    print "Running unit test on rate limit functions"
    print "Force expire all"
    expired = expire_rate_limit(conf, test_proto, fail_cache=0)
    print "Expired: %s" % expired
    print "Emulate rate limit"
    for i in range(default_max_hits + 1):
        hit = hit_rate_limit(conf, test_proto, test_address, test_id)
        print "Blocked: %s" % hit
        update_rate_limit(conf, test_proto, test_address, test_id, False)
        print "Updated fail for %s from %s" % (test_id, test_address)
        time.sleep(1)
    other_proto, other_address, other_id = "BOGUS", '127.10.20.30', 'otheruser'
    print "Update with other proto"
    update_rate_limit(conf, other_proto, test_address, test_id, False)
    print "Update with other address"
    update_rate_limit(conf, test_proto, other_address, test_id, False)
    print "Update with other user"
    update_rate_limit(conf, test_proto, test_address, other_id, False)
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
    update_rate_limit(conf, test_proto, test_address, test_id, True)
    print "Updated success for %s from %s" % (test_id, test_address)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with same user from other address"
    hit = hit_rate_limit(conf, test_proto, other_address, test_id)
    print "Blocked: %s" % hit

    
