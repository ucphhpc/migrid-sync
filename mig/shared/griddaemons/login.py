#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# login - grid daemon login helper functions
# Copyright (C) 2010-2021  The MiG Project lead by Brian Vinter
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

"""MiG login daemon functions"""

from past.builtins import basestring
from builtins import object
import glob
import logging
import os
import socket
import time

from mig.shared.base import client_dir_id, client_id_dir, client_alias, \
    force_utf8, get_short_id
from mig.shared.defaults import dav_domain
from mig.shared.fileio import unpickle
from mig.shared.gdp.all import get_project_from_user_id
from mig.shared.sharelinks import extract_mode_id
from mig.shared.ssh import parse_pub_key
from mig.shared.useradm import ssh_authkeys, davs_authkeys, ftps_authkeys, \
    https_authkeys, get_authkeys, ssh_authpasswords, davs_authpasswords, \
    ftps_authpasswords, https_authpasswords, get_authpasswords, \
    ssh_authdigests, davs_authdigests, ftps_authdigests, https_authdigests, \
    generate_password_hash, generate_password_digest, load_user_dict
from mig.shared.validstring import possible_sharelink_id, possible_job_id, \
    possible_jupyter_mount_id

# NOTE: auth keys file may easily contain only blank lines, so we decide to
#       consider any such file of less than a 100 bytes invalid.

min_pub_key_bytes = 100


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
        if isinstance(public_key, basestring):
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
    # logger.debug("after clean up old users list is:\n%s" %
    #              '\n'.join(["%s" % i for i in conf['users']]))
    if creds_lock:
        creds_lock.release()

    user_id_list = [user_alias]
    if short_id:
        user_id_list += [short_id, short_alias]

    # Now add all current login methods
    for user_key in all_keys:
        # Remove comments and blank lines
        user_key = user_key.split('#', 1)[0].strip()
        if not user_key:
            continue
        # Make sure pub key is valid
        try:
            _ = parse_pub_key(user_key)
        except Exception as exc:
            logger.warning("Skipping broken key %s for user %s (%s)" %
                           (user_key, user_id, exc))
            continue
        for login_id in user_id_list:
            add_user_object(configuration, login_id, user_dir, pubkey=user_key)
    for user_password in all_passwords:
        user_password = user_password.strip()
        for login_id in user_id_list:
            add_user_object(configuration, login_id, user_dir,
                            password=user_password, user_dict=user_dict)
    for user_digest in all_digests:
        user_digest = user_digest.strip()
        for login_id in user_id_list:
            add_user_object(configuration, login_id, user_dir,
                            digest=user_digest, user_dict=user_dict)
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
    # logger.debug("refresh_user_creds for %s" % username)
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

    changed_paths = get_creds_changes(conf, username, authkeys_path,
                                      authpasswords_path, authdigests_path)
    if not changed_paths:
        # logger.debug("No user creds changes for %s" % username)
        return (conf, changed_users)

    # logger.debug("Updating user creds for %s" % username)

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
        # logger.debug("refresh_user_creds updating objs for %s" % username)
        update_user_objects(configuration, auth_file, path, user_vars,
                            auth_protos, private_auth_file)

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
        update_user_objects(configuration, auth_file, path, user_vars,
                            auth_protos, private_auth_file)
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
            'STATUS' in job_dict and \
            job_dict['STATUS'] == 'EXECUTING' and \
            'SESSIONID' in job_dict and \
            job_dict['SESSIONID'] == sessionid and \
            'USER_CERT' in job_dict and \
            'MOUNT' in job_dict and \
            'MOUNTSSHPUBLICKEY' in job_dict:
        user_alias = sessionid
        user_dir = client_id_dir(job_dict['USER_CERT'])
        user_key = job_dict['MOUNTSSHPUBLICKEY']
        user_ip = None

        # Use frontend proxy if available otherwise use hosturl to resolve IP
        user_url = job_dict['RESOURCE_CONFIG'].get('FRONTENDPROXY', '')
        if not user_url:
            user_url = job_dict['RESOURCE_CONFIG'].get('HOSTURL', '')
        try:
            user_ip = socket.gethostbyname_ex(user_url)[2][0]
        except Exception as exc:
            user_ip = None
            logger.warning("Skipping key, unresolvable ip for user %s (%s)" %
                           (user_alias, exc))

        # Make sure pub key is valid
        valid_pubkey = True
        try:
            _ = parse_pub_key(user_key)
        except Exception as exc:
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
                'STATUS' in job_dict and \
                job_dict['STATUS'] == 'EXECUTING' and \
                'SESSIONID' in job_dict and \
                job_dict['SESSIONID'] == sessionid and \
                'USER_CERT' in job_dict and \
                'MOUNT' in job_dict and \
                'MOUNTSSHPUBLICKEY' in job_dict:
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
            except Exception as exc:
                user_ip = None
                msg = "Skipping key due to unresolvable ip" \
                    + " for user %s (%s)" % (user_alias, exc)
                logger.warning(msg)

            # Make sure pub key is valid
            valid_pubkey = True
            try:
                _ = parse_pub_key(user_key)
            except Exception as exc:
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
    except ValueError as err:
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
    except Exception as err:
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
            'share_id' in share_dict and \
            'share_root' in share_dict and \
            'share_pw_hash' in share_dict and \
            'share_pw_digest' in share_dict:
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
        except Exception as err:
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
            'share_id' in share_dict and \
                'share_root' in share_dict and \
                'share_pw_hash' in share_dict and \
                'share_pw_digest' in share_dict:
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
    # logger.debug("jupyter linkpath: %s jupyter path exists: %s" % \
    #                 (os.path.islink(link_path), os.path.exists(link_path)))

    jupyter_dict = None
    if os.path.islink(link_path) and os.path.exists(link_path):
        sessionid = username
        jupyter_dict = unpickle(link_path, logger)
        # logger.debug("loaded jupyter dict: %s" % jupyter_dict)

    # We only allow connections from active jupyter credentials
    if jupyter_dict is not None and isinstance(jupyter_dict, dict) and \
            'SESSIONID' in jupyter_dict and \
            jupyter_dict['SESSIONID'] == sessionid and \
            'USER_CERT' in jupyter_dict and \
            'MOUNTSSHPUBLICKEY' in jupyter_dict:
        user_alias = sessionid
        user_dir = client_id_dir(jupyter_dict['USER_CERT'])
        user_key = jupyter_dict['MOUNTSSHPUBLICKEY']

        # Make sure pub key is valid
        valid_pubkey = True
        try:
            _ = parse_pub_key(user_key)
        except Exception as exc:
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
    logger.info("Active jupyter_mounts: %s" % [(i.username, i.home) for i in
                                               conf['jupyter_mounts']])
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
    logger = daemon_conf.get("logger", logging.getLogger())
    # logger.debug("update_login_map with changed users: %s" % changed_users)
    creds_lock = daemon_conf.get('creds_lock', None)
    if creds_lock:
        creds_lock.acquire()
    for username in changed_users:
        login_map[username] = [i for i in daemon_conf['users'] if username ==
                               i.username]
    # logger.debug("update_login_map for %s: %s" %
    #                (username, '\n'.join(["%s" % i for i in login_map[username]])))
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
