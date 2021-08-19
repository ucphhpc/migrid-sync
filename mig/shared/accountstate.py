#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accountstate - various user account state helpers
# Copyright (C) 2020-2021  The MiG Project lead by Brian Vinter
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

"""This module contains various helpers used to check and update internal user
account state in relation to web and IO daemon access control.
"""

from __future__ import print_function
from __future__ import absolute_import

from past.builtins import basestring
import os
import time

from mig.shared.base import client_id_dir, client_dir_id, requested_url_base
from mig.shared.defaults import expire_marks_dir, status_marks_dir, \
    valid_account_status, oid_auto_extend_days, cert_auto_extend_days, \
    attempt_auto_extend_days, AUTH_GENERIC, AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT
from mig.shared.filemarks import get_filemark, update_filemark, reset_filemark
from mig.shared.gdp.userid import get_base_client_id
from mig.shared.userdb import load_user_dict, default_db_path, update_user_dict
from mig.shared.validstring import possible_sharelink_id, possible_job_id, \
    possible_jupyter_mount_id


def default_account_valid_days(configuration, auth_type):
    """Lookup default account valid days from configuration"""

    _valid_map = {AUTH_CERTIFICATE: configuration.cert_valid_days,
                  AUTH_OPENID_V2: configuration.oid_valid_days,
                  AUTH_OPENID_CONNECT: configuration.oidc_valid_days,
                  AUTH_GENERIC: configuration.generic_valid_days}
    valid_days = _valid_map.get(auth_type, configuration.generic_valid_days)
    return valid_days


def default_account_expire(configuration, auth_type, start_time=int(time.time())):
    """Lookup default account expire value (epoch) based on start_time"""

    valid_days = default_account_valid_days(configuration, auth_type)
    expire = int(start_time + valid_days * 24 * 60 * 60)
    return expire


def update_account_expire_cache(configuration, user_dict):
    """Create or update expire mark for account with given user_dict if it
    contains the expire field.
    """
    _logger = configuration.logger
    if not isinstance(user_dict, dict):
        _logger.error("invalid user_dict: %s" % user_dict)
        return False
    client_id = user_dict.get('distinguished_name', None)
    if not client_id:
        _logger.error("no client ID set for user: %s" % user_dict)
        return False
    expire = user_dict.get('expire', None)
    if not expire:
        _logger.info("no expire set for user: %s" % user_dict)
        return True
    elif isinstance(expire, basestring):
        _logger.warning("found string expire value for user: %s" % user_dict)
        return False
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run, expire_marks_dir)
    return update_filemark(configuration, base_dir, client_dir, expire)


def get_account_expire_cache(configuration, client_id):
    """Check if account with client_id has an expire mark in the cache and
    if so return the timestamp associated with it.
    """
    _logger = configuration.logger
    if not client_id:
        _logger.error("invalid client ID: %s" % client_id)
        return False
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run, expire_marks_dir)
    return get_filemark(configuration, base_dir, client_dir)


def reset_account_expire_cache(configuration, client_id=None):
    """Clear expire mark in the cache for one or more users as specified
    by client_id. The default value of None means all marks but it can also
    be a string or a list of strings.
    """
    _logger = configuration.logger
    res = True
    base_dir = os.path.join(configuration.mig_system_run, expire_marks_dir)
    reset_filemark(configuration, base_dir, client_id)
    return res


def update_account_status_cache(configuration, user_dict):
    """Create or update status mark for account with given user_dict if it
    contains the status field.
    """
    _logger = configuration.logger
    if not isinstance(user_dict, dict):
        _logger.error("invalid user_dict: %s" % user_dict)
        return False
    client_id = user_dict.get('distinguished_name', None)
    if not client_id:
        _logger.error("no client ID set for user: %s" % user_dict)
        return False
    # NOTE: translate status strings to integers here to encode as timestamp
    status_key = user_dict.get('status', None)
    if not status_key:
        _logger.info("no status set for user: %s" % user_dict)
        return True
    if not status_key in valid_account_status:
        _logger.error("invalid account status for user: %s" % user_dict)
        return False
    status = valid_account_status.index(status_key)
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run, status_marks_dir)
    return update_filemark(configuration, base_dir, client_dir, status)


def get_account_status_cache(configuration, client_id):
    """Check if account with client_id has an status mark in the cache and
    if so return the timestamp associated with it.
    """
    _logger = configuration.logger
    if not client_id:
        _logger.error("invalid client ID: %s" % client_id)
        return False
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run, status_marks_dir)
    # NOTE: translate status integer encoded as timestamp back to string
    status_index = get_filemark(configuration, base_dir, client_dir)
    if status_index is None:
        return status_index
    if status_index < 0 or status_index >= len(valid_account_status):
        _logger.error("invalid cached client status for %s: %s" %
                      (client_id, status_index))
        return None
    return valid_account_status[int(status_index)]


def check_account_status(configuration, client_id):
    """Check if client_id account is accessible using cache or user DB"""
    _logger = configuration.logger
    user_dict = None
    # NOTE: first check if account is active using cache or user DB
    account_status = get_account_status_cache(configuration, client_id)
    if account_status is None:
        _logger.info("no account status cache for %s - update" % client_id)
        # NOTE: read from user DB but default to active if missing to avoid
        #       repeated retries
        user_dict = load_user_dict(_logger, client_id,
                                   default_db_path(configuration))
        if not user_dict:
            _logger.warning("no such account: %s" % client_id)
            return (False, "missing", user_dict)
        account_status = user_dict['status'] = user_dict.get('status',
                                                             'active')
        update_account_status_cache(configuration, user_dict)

    # Now check actual status
    if account_status in ['active', 'temporal', 'restricted']:
        _logger.debug("user %s is enabled with status %s" %
                      (client_id, account_status))
        account_accessible = True
    else:
        _logger.warning("user account not accessible: %s" % account_status)
        account_accessible = False
    return (account_accessible, account_status, user_dict)


def check_account_expire(configuration, client_id, environ=None):
    """Check client_id account expire field in cache or user DB"""
    _logger = configuration.logger
    if not environ:
        environ = os.environ
    user_dict = None
    account_expire = get_account_expire_cache(configuration, client_id)
    if account_expire is None:
        _logger.info("no account expire cache for %s - update" % client_id)
        # NOTE: read from user DB but default to 0 if missing to avoid
        #       repeated retries
        user_dict = load_user_dict(_logger, client_id,
                                   default_db_path(configuration))
        if not user_dict:
            _logger.error("no such account: %s" % client_id)
            return (False, -42, user_dict)
        account_expire = user_dict.get('expire', 0)
        # NOTE: if e.g. editmeta is used to set expire it ends up as a string
        #       rather than int so we warn and try to let next update fix it.
        if isinstance(account_expire, basestring) and account_expire.isdigit():
            _logger.warning("found string expire value for user: %s" %
                            user_dict)
            account_expire = int(account_expire)
        user_dict['expire'] = account_expire
        update_account_expire_cache(configuration, user_dict)

    # Now check actual expire
    if account_expire and account_expire < time.time():
        _logger.info("user is marked expired at %s" % account_expire)
        pending_expire = False
    else:
        _logger.debug("user %s is still active - expire is %s" %
                      (client_id, account_expire))
        pending_expire = True
    return (pending_expire, account_expire, user_dict)


def check_update_account_expire(configuration, client_id, environ=None,
                                min_days_left=attempt_auto_extend_days):
    """Check and possibly update client_id expire field in cache and user DB
    if configured. The optional environ can be used to provide current environ
    dict instead of the default os.environ. The optional min_days_left
    argument is used to attempt renew if the account is set to expire before N
    days from now. If not provided the default is to attempt renewal some days
    before expiry and then extend for longer than that to delay next try.
    """
    _logger = configuration.logger
    if not environ:
        environ = os.environ
    # NOTE: first check if account is expired using cache or user DB
    (pending_expire, account_expire, user_dict) = check_account_expire(
        configuration, client_id, environ)
    # Now check actual expire
    if account_expire and account_expire < time.time() + min_days_left * 86400:
        try_renew = True
    else:
        try_renew = False

    if try_renew:
        _logger.debug("attempt user %s expiry %d extension" %
                      (client_id, account_expire))
        # NOTE: users who got this far obviously has a working auth method
        vhost_url = requested_url_base(environ)
        update_expire = False
        auth_type = None
        extend_days = 0
        # External certificate/openid users should auto-renew if conf allows
        # them to sign up without admin acceptance. Local users always need to
        # explicitly renew access since it may require certificate renew, etc.
        if vhost_url == configuration.migserver_https_ext_oid_url and \
                configuration.auto_add_oid_user:
            update_expire = True
            extend_days = oid_auto_extend_days
        elif vhost_url == configuration.migserver_https_ext_cert_url and \
                configuration.auto_add_cert_user:
            update_expire = True
            extend_days = cert_auto_extend_days
        else:
            _logger.debug("extend expire not enabled for %s on %s" %
                          (client_id, vhost_url))

        if update_expire and extend_days > 0:
            _logger.info("trying to update %s expire with %d days" %
                         (client_id, extend_days))
            if not user_dict:
                user_dict = load_user_dict(_logger, client_id,
                                           default_db_path(configuration))
            if not user_dict:
                _logger.error("no such account: %s" % client_id)
                return (False, -42, user_dict)
            account_status = user_dict.get('status', 'active')
            # NOTE: careful not to renew e.g. short-term users with account
            #       status set to 'temporal'.
            if account_status == 'active':
                renew = {'expire': time.time() + extend_days * 24 * 3600}
                user_dict.update(renew)
                update_account_expire_cache(configuration, user_dict)
                # NOTE: write through to user db
                update_user_dict(_logger, client_id, renew,
                                 default_db_path(configuration))
                _logger.info("account expire updated to %(expire)d" %
                             user_dict)
                pending_expire = True
            else:
                _logger.info("extend expire skipped for %s with status %r" %
                             (client_id, account_status))
        elif pending_expire:
            _logger.debug("user %s about to expire %d but no auto update" %
                          (client_id, account_expire))
        else:
            _logger.warning("user %s expired at %d" % (client_id,
                                                       account_expire))
    else:
        _logger.debug("user %s is still active - expire is %d" %
                      (client_id, account_expire))
    return (pending_expire, account_expire, user_dict)


def account_expire_info(configuration, username, environ=None,
                        min_days_left=14):
    """Helper to lookup when username account expires and details about renew
    and auto extension support in case account has less than min_days_left
    before expiry.
    """
    _logger = configuration.logger
    if not environ:
        environ = os.environ
    extend_days, renew_days = 0, 0
    (_, account_expire, _) = check_account_expire(configuration, username)
    (_, account_status, _) = check_account_status(configuration, username)
    vhost_url = requested_url_base(environ)
    expire_warn = False
    if account_expire and account_expire < time.time() + min_days_left * 86400:
        expire_warn = True
        if vhost_url == configuration.migserver_https_ext_oid_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_OPENID_V2)
            if account_status == 'active' and configuration.auto_add_oid_user:
                extend_days = oid_auto_extend_days
        elif vhost_url == configuration.migserver_https_ext_oidc_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_OPENID_CONNECT)
            if account_status == 'active' and configuration.auto_add_oid_user:
                extend_days = oid_auto_extend_days
        elif vhost_url == configuration.migserver_https_ext_cert_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_CERTIFICATE)
            if account_status == 'active' and configuration.auto_add_cert_user:
                extend_days = cert_auto_extend_days
        elif vhost_url == configuration.migserver_https_mig_oid_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_OPENID_V2)
        elif vhost_url == configuration.migserver_https_mig_oidc_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_OPENID_CONNECT)
        elif vhost_url == configuration.migserver_https_mig_cert_url:
            renew_days = default_account_valid_days(configuration,
                                                    AUTH_CERTIFICATE)
        else:
            _logger.warning("unexpected vhost in expire detection: %s" %
                            vhost_url)
    return (expire_warn, account_expire, renew_days, extend_days)


def detect_special_login(configuration, username, proto):
    """Helper to handle account accessible checks for all but the ordinary
    users. That is, sharelinks, job and jupyter mount logins.
    """
    _logger = configuration.logger
    try:
        if proto in ('sftp', 'ftps', 'davs') and \
                possible_sharelink_id(configuration, username):
            for mode in ['read-write']:
                real_path = os.path.realpath(os.path.join(
                    configuration.sharelink_home, mode, username))
                if os.path.exists(real_path):
                    _logger.info("%s sharelink %s detected - always accessible" %
                                 (mode, username))
                    return True
        if proto == 'sftp' and possible_job_id(configuration, username):
            real_path = os.path.realpath(os.path.join(
                configuration.sessid_to_mrsl_link_home, username + '.mRSL'))
            if os.path.exists(real_path):
                _logger.info(
                    "job mount %s detected - always accessible" % username)
                return True
        if proto == 'sftp' and possible_jupyter_mount_id(configuration,
                                                         username):
            real_path = os.path.realpath(os.path.join(
                configuration.sessid_to_jupyter_mount_link_home, username))
            if os.path.exists(real_path):
                _logger.info(
                    "jupyter mount %s detected - always accessible" % username)
                return True
    except Exception as exc:
        _logger.error("detect special login for %r failed: %s" %
                      (username, exc))
    _logger.debug("login for %s was detected as normal login" % username)
    return False


def check_account_accessible(configuration, username, proto, environ=None,
                             io_login=True, expand_alias=True):
    """Check username account status and expire field in cache and user DB
    if needed and return a boolean to tell if account is accessible or not.
    The proto argument is used to detect if only users are allowed or if e.g.
    sharelinks, jobs or jupyter mounts should also be checked.
    The optional environ overrides the environment dict which is otherwise
    taken from os.environ and the io_login is a boolean to decide if
    configuration.site_io_account_expire should be honored or if expire should
    be enforced only if configuration.user_openid_enforce_expire is set. The
    optional expand_alias can be used to force expansion of username from an
    alias to the full DN so that e.g. the user email address alias can be
    provided and automatically looked up. This is particularly convenient when
    called from PAM for SFTP.
    """
    _logger = configuration.logger
    if not environ:
        environ = os.environ

    # We might end up here from IO daemon logins with user, sharelink, job and
    # jupyter mounts. We should let all but actual user logins pass for now.
    # TODO: consider checking underlying user for other types eventually?
    if detect_special_login(configuration, username, proto):
        _logger.debug("found %s as special %s login" % (username, proto))
        return True

    # NOTE: now we know username must be an ordinary user to check
    client_id = username
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(configuration, client_id,
                                       expand_oid_alias=expand_alias)
    elif expand_alias:
        # Use client_id_dir to make it work even if already expanded
        home_dir = os.path.join(configuration.user_home,
                                client_id_dir(client_id))
        real_home = os.path.realpath(home_dir)
        real_id = os.path.basename(real_home)
        client_id = client_dir_id(real_id)

    (account_accessible, account_status, _) = check_account_status(
        configuration, client_id)
    if not account_accessible:
        _logger.debug("%s account %s" % (client_id, account_status))
        return False
    if io_login and not configuration.site_io_account_expire:
        _logger.debug("%s account active and no IO expire" % client_id)
        return True
    if not io_login and not configuration.user_openid_enforce_expire:
        _logger.debug("%s account active and no OpenID expire" % client_id)
        return True
    (pending_expire, account_expire, _) = check_account_expire(
        configuration, client_id, environ)
    return pending_expire


if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    active_user = '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk'
    suspended_user = '/C=DK/ST=NA/L=NA/O=FAKSEK/OU=NA/CN=Jonas Bardino/emailAddress=bardino@science.ku.dk'
    dummy_user = "No_Such_User"
    active_user_email = active_user.split('=')[-1]
    suspended_user_email = suspended_user.split('=')[-1]
    expire = time.time() + 42
    user_dict = {'distinguished_name': dummy_user, 'expire': expire}
    print("get account expire mark for %s" % dummy_user)
    print(get_account_expire_cache(conf, dummy_user))
    print("update account expire mark for %s to %s" % (dummy_user, expire))
    print(update_account_expire_cache(conf, user_dict))
    print("get account expire mark for %s" % dummy_user)
    print(get_account_expire_cache(conf, dummy_user))
    print("reset account expire mark for %s" % dummy_user)
    print(reset_account_expire_cache(conf, dummy_user))
    print("get account expire mark for %s" % dummy_user)
    print(get_account_expire_cache(conf, dummy_user))

    print("check account accessible for %s" % active_user)
    print(check_account_accessible(conf, active_user, 'sftp'))
    print("check account accessible for %s" % suspended_user)
    print(check_account_accessible(conf, suspended_user, 'sftp'))
    print("check account accessible for %s" % dummy_user)
    print(check_account_accessible(conf, dummy_user, 'sftp'))

    print("check account accessible for %s" % active_user_email)
    print(check_account_accessible(
        conf, active_user_email, 'sftp', expand_alias=True))
    print("check account accessible for %s" % suspended_user_email)
    print(check_account_accessible(
        conf, suspended_user_email, 'sftp', expand_alias=True))

    sharelink = 'JFPyQ7Gt2p'
    print("check account accessible for %s" % sharelink)
    print(check_account_accessible(conf, sharelink, 'sftp', expand_alias=True))

    job_id = 'eaeeff724b8d0d73b55b50b880a4c76873eb44cbfe1f97e67dd251d1002ad748'
    print("check account accessible for %s" % job_id)
    print(check_account_accessible(conf, job_id, 'sftp', expand_alias=True))
