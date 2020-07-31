#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# auth - grid daemon auth helper functions
# Copyright (C) 2010-2020  The MiG Project lead by Brian Vinter
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

""" MiG daemon auth functions"""

import time
import re

from mig.shared.auth import active_twofactor_session
from mig.shared.base import extract_field, expand_openid_alias
from mig.shared.defaults import CRACK_USERNAME_REGEX
from mig.shared.gdp.all import get_client_id_from_project_client_id
from mig.shared.griddaemons.ratelimits import default_user_abuse_hits, \
    default_proto_abuse_hits, default_max_secret_hits, update_rate_limit
from mig.shared.griddaemons.sessions import active_sessions
from mig.shared.notification import send_system_notification
from mig.shared.settings import load_twofactor
from mig.shared.twofactorkeywords import get_keywords_dict as twofactor_defaults


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
            protocol,
            authtype,
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
        category = [protocol.upper(), log_lvl]
        _auth_logger = auth_logger.info
    elif log_lvl == 'WARNING':
        category = [protocol.upper(), log_lvl]
        _auth_logger = auth_logger.warning
    elif log_lvl == 'ERROR':
        category = [protocol.upper(), log_lvl]
        _auth_logger = auth_logger.error
    elif log_lvl == 'CRITICAL':
        category = [protocol.upper(), log_lvl]
        _auth_logger = auth_logger.critical
    elif log_lvl == 'DEBUG':
        _auth_logger = auth_logger.debug
    else:
        logger.error("Invalid authlog level: %s" % log_lvl)
        return False

    log_message = "IP: %s, Protocol: %s, Type: %s, Username: %s, Message: %s" \
        % (user_addr, protocol, authtype, user_id, log_msg)
    _auth_logger(log_message)

    if notify and category:
        # Check for valid user before issuing notification
        client_id = expand_openid_alias(user_id, configuration)
        if client_id and extract_field(client_id, 'email'):
            user_msg = "IP: %s, User: %s, Message: %s" % \
                (user_addr, user_id, log_msg)
            status = send_system_notification(user_id, category,
                                              user_msg, configuration)
        # else:
        #     logger.debug("Skipped send_system_notification to user: %r" \
        #         % user_id)
        
    return status


def validate_auth_attempt(configuration,
                          protocol,
                          authtype,
                          username,
                          ip_addr,
                          tcp_port=0,
                          secret=None,
                          invalid_username=False,
                          invalid_user=False,
                          account_accessible=True,
                          skip_twofa_check=False,
                          valid_twofa=False,
                          authtype_enabled=False,
                          valid_auth=False,
                          exceeded_rate_limit=False,
                          exceeded_max_sessions=False,
                          user_abuse_hits=default_user_abuse_hits,
                          proto_abuse_hits=default_proto_abuse_hits,
                          max_secret_hits=default_max_secret_hits,
                          skip_notify=False,
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
                 + "authtype: %s\n"
                 % authtype
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
                 + "account_accessible: %s\n"
                 % account_accessible
                 + "skip_twofa_check: %s\n"
                 % skip_twofa_check
                 + "valid_twofa: %s\n"
                 % valid_twofa
                 + "authtype_enabled: %s, valid_auth: %s\n"
                 % (authtype_enabled, valid_auth)
                 + "exceeded_rate_limit: %s\n"
                 % exceeded_rate_limit
                 + "exceeded_max_sessions: %s\n"
                 % exceeded_max_sessions
                 + "max_secret_hits: %s\n"
                 % max_secret_hits
                 + "skip_notify: %s\n"
                 % skip_notify
                 + "-----------------------------------------------------")
    """

    authorized = False
    disconnect = False
    twofa_passed = valid_twofa
    notify = True

    if skip_notify or invalid_username or invalid_user \
            or ip_addr in configuration.site_security_scanners:
        notify = False

    if skip_twofa_check:
        twofa_passed = True

    if protocol == 'davs' \
            and authtype in configuration.user_davs_auth:
        pass
    elif protocol == 'ftps' \
            and authtype in configuration.user_ftps_auth:
        pass
    elif protocol == 'sftp' \
            and authtype in configuration.user_sftp_auth:
        pass
    elif protocol == 'sftp-subsys' \
            and authtype in configuration.user_sftp_auth:
        pass
    elif protocol == 'openid' \
            and authtype in configuration.user_openid_auth:
        pass
    elif not protocol in ['davs', 'ftps', 'sftp', 'sftp-subsys', 'openid']:
        logger.error("Invalid protocol: %r" % protocol)
        return (authorized, disconnect)
    else:
        logger.error("Invalid auth type: %r for protocol: %r"
                     % (authtype, protocol))
        return (authorized, disconnect)

    # Log auth attempt and set (authorized, disconnect) return values

    if exceeded_rate_limit:
        disconnect = True
        auth_msg = "Exceeded rate limit"
        log_msg = auth_msg + " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.warning(log_msg)
        authlog(configuration, 'WARNING', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif exceeded_max_sessions:
        disconnect = True
        active_count = active_sessions(configuration, protocol, username)
        auth_msg = "Too many open sessions"
        log_msg = auth_msg + " %d for %s" \
            % (active_count, username)
        logger.warning(log_msg)
        authlog(configuration, 'WARNING', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif invalid_username:
        disconnect = True
        if re.match(CRACK_USERNAME_REGEX, username) is not None:
            auth_msg = "Crack username detected"
            log_func = logger.critical
            authlog_lvl = 'CRITICAL'
        else:
            auth_msg = "Invalid username"
            log_func = logger.error
            authlog_lvl = 'ERROR'
        log_msg = auth_msg + " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        log_func(log_msg)
        authlog(configuration, authlog_lvl, protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif invalid_user:
        disconnect = True
        auth_msg = "Invalid user"
        log_msg = auth_msg + " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.error(log_msg)
        authlog(configuration, 'ERROR', protocol, authtype,
                username, ip_addr,
                auth_msg, notify=notify)
    elif not account_accessible:
        disconnect = True
        auth_msg = "Account disabled or expired"
        log_msg = auth_msg + " %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.error(log_msg)
        authlog(configuration, 'ERROR', protocol, authtype,
                username, ip_addr,
                auth_msg, notify=notify)
    elif not authtype_enabled:
        disconnect = True
        auth_msg = "%s auth disabled or %s not set" % (authtype, authtype)
        log_msg = auth_msg + " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.error(log_msg)
        authlog(configuration, 'ERROR', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif valid_auth and not twofa_passed:
        disconnect = True
        auth_msg = "No valid two factor session"
        log_msg = auth_msg + " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.error(log_msg)
        authlog(configuration, 'WARNING', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif authtype_enabled and not valid_auth:
        auth_msg = "Failed %s" % authtype
        log_msg = auth_msg + " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.error(log_msg)
        authlog(configuration, 'ERROR', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    elif valid_auth and twofa_passed:
        authorized = True
        notify = False
        auth_msg = "Accepted %s" % authtype
        log_msg = auth_msg + " login for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.info(log_msg)
        authlog(configuration, 'INFO', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)
    else:
        disconnect = True
        auth_msg = "Unknown auth error"
        log_msg = auth_msg + " for %s from %s" % (username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.warning(log_msg)
        authlog(configuration, 'ERROR', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)

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
        auth_msg = "Abuse limit reached"
        log_msg = auth_msg + " user hits %d for %s from %s" \
            % (user_abuse_hits, username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.critical(log_msg)
        authlog(configuration, 'CRITICAL', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)

    elif proto_abuse_hits > 0 and proto_hits > proto_abuse_hits:
        auth_msg = "Abuse limit reached"
        log_msg = auth_msg + " proto hits %d for %s from %s" \
            % (proto_abuse_hits, username, ip_addr)
        if tcp_port > 0:
            log_msg += ":%s" % tcp_port
        logger.critical(log_msg)
        authlog(configuration, 'CRITICAL', protocol, authtype,
                username, ip_addr, auth_msg, notify=notify)

    return (authorized, disconnect)
