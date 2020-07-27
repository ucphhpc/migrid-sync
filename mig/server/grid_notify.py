#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_notify - Notify users about relevant system events
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

"""Notify users about relevant system events and use bulking to avoid message
flooding.
"""
from __future__ import print_function

import os
import multiprocessing
import signal
import sys
import time
from datetime import datetime

from shared.base import extract_field, expand_openid_alias
from shared.conf import get_configuration_object
from shared.fileio import unpickle, delete_file
from shared.logger import daemon_logger, \
    register_hangup_handler
from shared.notification import send_email


stop_running = multiprocessing.Event()
notify_interval = 60
received_notifications = {}


def stop_handler(sig, frame):
    """A simple signal handler to quit on Ctrl+C (SIGINT) in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print('')
    stop_running.set()


def cleanup_notify_home(configuration, notified_users=[], timestamp=None):
    """Delete notification files based on either *notified_users* and/or
    file created timestamp"""

    logger = configuration.logger
    # logger.debug("cleanup_notify_home: %s, %s"
    #              % (notified_users, timestamp))

    # Remove notification files for notified users

    for client_id in notified_users:
        cleanup_files = received_notifications.get(
            client_id, {}).get('files', [])
        if not cleanup_files:
            logger.error(
                "Expected _NON_ empty files list for client_id: '%s'"
                % client_id)
        for filepath in cleanup_files:
            # logger.debug("Removing notification file: '%s'" % filepath)
            delete_file(filepath, logger)

    # Remove notification files based on timestamp

    if timestamp is not None:
        notify_home = configuration.notify_home
        now_timestamp = time.time()
        cleanuptime = now_timestamp - timestamp
        for direntry in os.listdir(notify_home):
            filepath = os.path.join(notify_home, direntry)
            ctime = os.path.getctime(filepath)
            if ctime > cleanuptime:
                # logger.debug("Removing OLD notification file: '%s'"
                #              + ", ctime: %s, cleanuptime: %s"
                #              % (filepath, ctime, cleanuptime))
                delete_file(filepath, logger)


def send_notifications(configuration):
    """Generate message and send notification to users"""
    logger = configuration.logger
    # logger.debug("send_notifications")
    result = []
    for (client_id, client_dict) in received_notifications.iteritems():
        timestamp = client_dict.get('timestamp', 0)

        timestr = (datetime.fromtimestamp(timestamp)
                   ).strftime('%d/%m/%Y %H:%M:%S')
        client_name = extract_field(client_id, 'full_name')
        client_email = extract_field(client_id, 'email')
        recipient = "%s <%s>" % (client_name,
                                 client_email)
        total_events = 0
        notify_message = ""
        messages_dict = client_dict.get('messages', {})
        for (header, value) in messages_dict.iteritems():
            if notify_message:
                notify_message += "\n\n"
            notify_message += "= %s =\n" % header
            for (message, events) in value.iteritems():
                notify_message += "#%s : %s\n" % (events, message)
                total_events += events
        subject = "System notification: %s new events" % total_events
        notify_message = "Found %s new events since: %s\n\n" \
            % (total_events, timestr) \
            + notify_message
        status = send_email(
            recipient,
            subject,
            notify_message,
            logger,
            configuration)
        if status:
            logger.info("Send email with %s events to: %s"
                        % (total_events, recipient))
            result.append(client_id)
        else:
            logger.error("Failed to send email to: '%s', '%s'" %
                         (recipient, client_id))

    return result


def recv_notification(configuration, path):
    """Read notification event from file"""
    logger = configuration.logger
    # logger.debug("read_notification: %s" % file)
    status = True
    new_notification = unpickle(path, logger)
    if not new_notification:
        logger.error("Failed to unpickle: %s" % path)
        return False
    user_id = new_notification.get('user_id', '')
    # logger.debug("Received user_id: '%s'" % user_id)
    if not user_id:
        status = False
        logger.error("Missing user_id in notification: %s" % path)
    else:
        client_id = expand_openid_alias(user_id, configuration)
        # logger.debug("resolved client_id: '%s'" % client_id)
        if not client_id or not extract_field(client_id, 'email'):
            status = False
            logger.error("Failed to resolve client_id from user_id: '%s'"
                         % user_id)
    if status:
        category = new_notification.get('category', [])
        # logger.debug("Received category: %s" % category)
        if not isinstance(category, list):
            status = False
            logger.error("Received category: %s must be a list" % category)
    if status:
        logger.info("Received event: %s, from: '%s'"
                    % (category, client_id))
        new_timestamp = new_notification.get('timestamp')
        message = new_notification.get('message', '')
        # logger.debug("Received message: %s" % message)
        client_dict = received_notifications.get(client_id, {})
        if not client_dict:
            received_notifications[client_id] = client_dict
        files_list = client_dict.get('files', [])
        if not files_list:
            client_dict['files'] = files_list
        if path in files_list:
            logger.warning(
                "Skipping previously received notification: '%s'" % path)
        else:
            files_list.append(path)
            client_dict['timestamp'] = min(
                client_dict.get('timestamp', sys.maxsize),
                new_timestamp)
            messages_dict = client_dict.get('messages', {})
            if not messages_dict:
                client_dict['messages'] = messages_dict
            header = " ".join(category)
            if not header:
                header = '* UNKNOWN *'
            body_dict = messages_dict.get(header, {})
            if not body_dict:
                messages_dict[header] = body_dict
            message_count = body_dict.get(message, 0)
            body_dict[message] = message_count + 1

    return status


def handle_notifications(configuration):
    """Main handler for notification events"""
    logger = configuration.logger
    # logger.debug("handle_events")
    notify_home = configuration.notify_home
    if not notify_home or not os.path.exists(notify_home):
        err_msg = "Missing notify_home: '%s'" % notify_home
        return (1, err_msg)

    try:
        while not stop_running.is_set():
            for direntry in os.listdir(notify_home):
                abspath = os.path.join(notify_home, direntry)
                if os.path.isfile(abspath):
                    recv_notification(configuration, abspath)
            notified_users = send_notifications(configuration)
            last_notification = time.time()
            cleanup_notify_home(configuration,
                                notified_users=notified_users,
                                timestamp=last_notification - 84600)
            received_notifications.clear()
            logger.debug("----- Sleeping %s seconds -----" % notify_interval)
            time.sleep(notify_interval)
    except Exception as err:
        err_msg = "handle_notifications failed: %s" % err
        return (1, err_msg)

    # We received stop signal

    ok_msg = "Stopping handle_notifications"

    return (0, ok_msg)


def unittest(configuration, emailaddr, delay):
    """Unit test for grid_notify.py"""
    signal.signal(signal.SIGINT, stop_handler)
    from shared.notification import send_system_notification
    print("Starting unittest: emailaddr: %s" % emailaddr \
        + ", delay: %s" % delay)
    if delay > 0:
        print("Waiting %s secs before executing unit test" % delay)
        time.sleep(delay)
    if stop_running.is_set():
        return
    nr_debug_users = 2
    client_ids = []
    for i in xrange(nr_debug_users):
        client_ids.append(
            "/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Grid Notify %i/emailAddress=%s"
            % (i, emailaddr))
    print("=============================")
    print("======= Starting test =======")
    print("=============================")
    for client_id in client_ids:
        for i in xrange(5):
            for protocol in ['SFTP', 'WebDAVS']:
                if stop_running.is_set():
                    return
                category = [protocol]
                msg = "__UNITTEST__: %s" % protocol
                print("unittest: Sending notification: %s" \
                    ", category: %s: %s" % (i, category, client_id))
                send_system_notification(client_id,
                                         category,
                                         msg,
                                         configuration)
                for event in ['Invalid password', 'Expired 2FA session']:
                    if stop_running.is_set():
                        return
                    category = [protocol, event]
                    msg = "__UNITTEST__: %s" % client_id
                    print("unittest: Sending notification: %s" % i \
                        + ", category: %s: %s" % (category, client_id))
                    send_system_notification(client_id,
                                             category,
                                             msg,
                                             configuration)


if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    emailaddr = None
    delay = 0
    argpos = 1
    if sys.argv[argpos:] and sys.argv[argpos] \
            in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[argpos]
        argpos += 1
    if sys.argv[argpos:] and len(sys.argv[argpos].split('@')) == 2:
        emailaddr = sys.argv[argpos]
        argpos += 1
    if sys.argv[argpos:]:
        try:
            delay = int(sys.argv[argpos])
        except Exception as err:
            print("Invalid delay arg: %s" % (sys.argv[argpos]))
            sys.exit(1)

    # Use separate logger

    logger = daemon_logger("notify", configuration.user_notify_log, log_level)
    configuration.logger = logger

    # Start unittest if requested

    if emailaddr:
        unittest_proc = multiprocessing.Process(target=unittest,
                                                args=(configuration,
                                                      emailaddr,
                                                      delay))
        unittest_proc.start()
        info_msg = "Starting unit test process: email: %s, delay: %s" \
            % (emailaddr, delay)
        print(info_msg)
        logger.info("(%s) %s" % (unittest_proc.pid, info_msg))

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow clean shutdown on SIGINT only to main process
    signal.signal(signal.SIGINT, stop_handler)

    if not configuration.site_enable_notify:
        err_msg = "System notify helper is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print('''This is the MiG system notify daemon which notify users about system events.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
''')

    main_pid = os.getpid()
    print("Starting notify daemon - Ctrl-C to quit")
    logger.info("(%s) Starting notify daemon" % main_pid)
    (exit_code, exit_msg) = handle_notifications(configuration)
    stop_msg = "Stopping notify daemon"
    if exit_code == 0:
        print(stop_msg)
        logger.info("(%s) %s"
                    % (main_pid, stop_msg))
    else:
        stop_msg += ", exit_code: %s, %s" % (exit_code, exit_msg)
        print(stop_msg)
        logger.error("(%s) %s" % (main_pid, stop_msg))

    sys.exit(exit_code)
