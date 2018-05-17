#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gdp - helper functions related to GDP actions
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""GDP specific helper functions"""

import os
import time
import hashlib
import inspect
import logging
import logging.handlers
try:
    import pdfkit
except:
    pdfkit = None
from datetime import datetime
try:
    from xvfbwrapper import Xvfb
except:
    Xvfb = None

from shared.base import client_id_dir, valid_dir_input
from shared.defaults import default_vgrid, all_vgrids, any_vgrid, \
    user_db_filename as mig_user_db_filename
from shared.fileio import touch, make_symlink, write_file, remove_rec, \
    acquire_file_lock, release_file_lock
from shared.notification import send_email
from shared.serial import load, dump
from shared.useradm import create_user, delete_user, expand_openid_alias, \
    get_full_user_map, get_short_id
from shared.vgrid import vgrid_is_owner, vgrid_set_owners, \
    vgrid_set_members, vgrid_set_settings, vgrid_create_allowed, \
    vgrid_restrict_write_support, vgrid_flat_name
from shared.vgridkeywords import get_settings_keywords_dict

template_filename = 'notifycreate.txt'
notify_filename = 'notifyemails.txt'
user_db_filename = 'gdp-users.db'
client_id_project_postfix = '/GDP='

skip_client_id_rewrite = [
    'adminvgrid.py',
    'autocreate.py',
    'autologout.py',
    'gdpman.py',
    'rmvgridmember.py',
    'vgridman.py',
    'viewvgrid.py',
]

valid_scripts = [
    'autocreate.py',
    'autologout.py',
    'cat.py',
    'cp.py',
    'fileman.py',
    'gdpman.py',
    'logout.py',
    'ls.py',
    'mkdir.py',
    'mv.py',
    'rm.py',
    'rmvgridmember.py',
    'settings.py',
    'settingsaction.py',
    'uploadchunked.py',
]

valid_log_actions = [
    'accessed',
    'accept_invite',
    'auto_logged_out',
    'copied',
    'created',
    'deleted',
    'invite',
    'logged_in',
    'logged_out',
    'moved',
]

valid_project_states = ['invite', 'invited', 'accepted']

valid_account_states = ['active', 'suspended', 'removed']

valid_protocols = ['https', 'davs', 'sftp']


def __user_db_filepath(configuration):
    """Generate GDP user_db filepath"""

    db_filepath = os.path.join(configuration.gdp_home, user_db_filename)
    db_lock_filepath = '%s.lock' % db_filepath

    return (db_filepath, db_lock_filepath)


def __client_id_from_project_client_id(configuration,
                                       project_client_id):
    """Extract client_id from *project_client_id"""

    _logger = configuration.logger
    _logger.debug('project_client_id: %s' % project_client_id)
    result = None

    try:
        if project_client_id.find(client_id_project_postfix) > -1:
            result = \
                project_client_id.split(client_id_project_postfix)[0]
        else:
            _logger.warning(
                "'%s' is _NOT_ a GDP project client id" % project_client_id)
    except Exception, exc:
        _logger.error(
            "GDP:__client_id_from_project_client_id failed:"
            + "'%s', error: %s" % (project_client_id, exc))

    return result


def __project_name_from_project_client_id(configuration,
                                          project_client_id):
    """Extract project name from *project_client_id*"""

    _logger = configuration.logger
    _logger.debug('project_client_id: %s' % project_client_id)
    result = None

    try:
        if project_client_id.find(client_id_project_postfix) > -1:
            result = \
                project_client_id.split(
                    client_id_project_postfix)[1].split('/')[0]
        else:
            _logger.warning("'%s' is _NOT_ a GDP project client id"
                            % project_client_id)
    except Exception, exc:
        _logger.error("GDP:__project_name_from_project_client_id failed:"
                      + "'%s', error: %s" % (project_client_id, exc))

    return result


def __short_id_from_client_id(configuration, client_id):
    """Extract login handle (email address) from *client_id*"""

    _logger = configuration.logger
    _logger.debug('client_id: %s' % client_id)

    user_alias = configuration.user_openid_alias
    result = get_short_id(configuration, client_id, user_alias)

    return result


def __project_short_id_from_project_client_id(configuration,
                                              project_client_id):
    """Extract project short id (email@projectname)
    from *project_client_id*"""

    _logger = configuration.logger
    _logger.debug('project_client_id: %s' % project_client_id)

    user_alias = configuration.user_openid_alias
    result = get_short_id(configuration, project_client_id, user_alias)

    return result


def __client_id_from_project_short_id(configuration, project_short_id):
    """Extract client_id from *project_short_id*"""

    _logger = configuration.logger
    _logger.debug('project_short_id: %s' % project_short_id)
    result = None

    user_id_array = project_short_id.split('@')
    user_id = "@".join(user_id_array[:-1])
    client_id = expand_openid_alias(user_id, configuration)
    home_path = os.path.join(configuration.user_home, client_id)
    if os.path.exists(home_path):
        result = client_id
    else:
        _logger.error("GDP:__client_id_from_project_short_id failed:"
                      + " no home path user: '%s'" % project_short_id)

    return result


def __client_id_from_user_id(configuration, user_id):
    """Extract client_id from *user_id*
    *user_id* is either a client_id, project_client_id, short_id
    or project_user_id"""

    _logger = configuration.logger
    _logger.debug('user_id: %s' % user_id)
    result = None

    # Extract client_id from user_id

    client_id = expand_openid_alias(user_id, configuration)
    possible_client_id = __client_id_from_project_client_id(
        configuration, client_id)

    if possible_client_id is None:
        result = client_id
    else:
        result = possible_client_id

    return result


def __project_client_id_from_user_id(configuration, user_id):
    """Extract project_client_id from *user_id*
    *user_id* is either a project_client_id or project_short_id"""

    _logger = configuration.logger
    _logger.debug('user_id: %s' % user_id)
    result = None

    # Extract client_id from user_id

    result = expand_openid_alias(user_id, configuration)

    return result


def __project_name_from_user_id(configuration, user_id):
    """Extract project name *user_id*
    *user_id* is either a project_client_id or project_short_id"""

    result = None

    project_client_id = __project_client_id_from_user_id(
        configuration, user_id)
    if project_client_id is not None:
        result = __project_name_from_project_client_id(configuration,
                                                       project_client_id)

    return result


def __create_gdp_user_db_entry(configuration):
    """Create empty GDP user db entry"""

    result = {
        'projects': {},
        'account': {
            'state': valid_account_states[0]
        }
    }

    for protocol in valid_protocols:
        result['account'][protocol] = {
            'role': '',
            'last_login': {
                'timestamp': 0,
                'ip': '',
            }
        }

    return result


def __validate_user_db(configuration, client_id, user_db=None):
    """Validate the GDP user database,
    it's expected to have the folling structure:
    {CLIENT_ID: {
            'projects': {
                PROJECT_NAME: {
                    'state': str,
                    'client_id': str,
                }
            }
            'account': {
                'state': str
                PROTOCOL: {
                    'role': str
                    'last_login': {
                        'timestamp': int
                        'ip': str
                    }
                }
            }
        }
    }
    """

    _logger = configuration.logger
    _logger.debug("client_id: '%s', user_db: %s" % (client_id, user_db))
    status = True

    msg = ""
    user = None
    projects = None
    account = None

    if user_db is None:
        user_db = __load_user_db(configuration)

    # Validate user

    user = user_db.get(client_id, None)
    if user is None:
        status = False
        msg = "No such GDP user: '%s'" % client_id
        _logger.error(msg)
    elif not isinstance(user, dict):
        status = False
        msg = "GDP database format error:" \
            + " '%s' is _NOT_ a dictionary" % (user)
        _logger.error(msg)

    # Validate projects

    if status:
        projects = user.get('projects', None)
        if projects is None:
            status = False
            msg = "GDP database format error:" \
                + " missing 'projects' for user: '%s'" % (client_id)
            _logger.error(msg)
        elif not isinstance(projects, dict):
            status = False
            msg = "GDP database format error:" \
                + " 'projects' is _NOT_ a dictionary"
            _logger.error(msg)

    if status:
        for (key, value) in projects.iteritems():
            if not 'client_id' in value.keys():
                status = False
                msg = "GDP database format error: missing 'client_id'" \
                    + " for project: '%s', user: '%s'" % (key, client_id)
                _logger.error(msg)
                break
            if not 'state' in value.keys():
                status = False
                msg = "GDP database format error: missing 'state'" \
                    + " for project: '%s', user: '%s'" % (key, client_id)
                _logger.error(msg)
                break

    # Validate account

    if status:
        account = user.get('account', None)
        if account is None:
            status = False
            msg = "GDP database format error: missing 'account'" \
                + " for user: '%s'" % (client_id)
            _logger.error(msg)
        elif not isinstance(account, dict):
            status = False
            msg = "GDP database format error:" \
                + " 'account' is _NOT_ a dictionary"
            _logger.error(msg)

    # Validate account state

    if status and not 'state' in account:
        status = False
        msg = "GDP database format error: missing 'account -> state'" \
            + " for user '%s'" % (client_id)
        _logger.error(msg)

    # Validate account protocol

    if status:
        for protocol in valid_protocols:
            account_protocol = account.get(protocol, None)
            if account_protocol is None:
                status = False
                msg = "GDP database format error:" \
                    + " missing 'account -> protocol'" \
                    + " for user: '%s'" % (client_id)
                _logger.error(msg)
            elif not isinstance(account_protocol, dict):
                status = False
                msg = "GDP database format error:" \
                    + " 'account -> protocol' is _NOT_ a dictionary"
                _logger.error(msg)

            # Validate account protocol role

            if status:
                role = account_protocol.get('role', None)
                if role is None:
                    status = False
                    msg = "GDP database format error:" \
                        + " missing 'account -> %s -> role'" % protocol \
                        + " for user: '%s'" % client_id
                    _logger.error(msg)

            # Validate account protocol last login

            if status:
                protocol_last_login = account_protocol.get('last_login', None)
                if protocol_last_login is None:
                    status = False
                    msg = "GDP database format error:" \
                        + " missing 'account -> protocol -> last_login'" \
                        + " for user: '%s'" % client_id
                    _logger.error(msg)
                elif not isinstance(protocol_last_login, dict):
                    status = False
                    msg = "GDP database format error:" \
                        + " 'account -> last_login' is _NOT_ a dictionary"
                    _logger.error(msg)

            # Validate account protocol last login timestamp

            if status and not 'timestamp' in protocol_last_login:
                status = False
                msg = "GDP database format error: " \
                    + " missing 'account -> %s" % account_protocol \
                    + " -> last_login -> timestamp'" \
                    + " for user: '%s'" % client_id
                _logger.error(msg)

            # Validate account last login ip

            if status and not 'ip' in protocol_last_login:
                status = False
                msg = "GDP database format error:" \
                    + " missing 'account -> %s " % account_protocol \
                    + " last_login -> ip'" % account_protocol \
                    + " for user: '%s'" % (client_id)
                _logger.error(msg)

    return (status, msg)


def __load_user_db(configuration, locked=False):
    """Load pickled GDP user database"""

    _logger = configuration.logger

    (db_filepath, db_lock_filepath) = __user_db_filepath(configuration)
    if not locked:
        flock = acquire_file_lock(db_lock_filepath)

    if os.path.exists(db_filepath):
        result = load(db_filepath)
    else:
        _logger.error("Missing GDP user DB: '%s'" % db_filepath)
        result = {}

    if not locked:
        release_file_lock(flock)

    return result


def __save_user_db(configuration, user_db, locked=False):
    """Save GDP user database"""

    _logger = configuration.logger

    (db_filepath, db_lock_filepath) = __user_db_filepath(configuration)

    if not locked:
        flock = acquire_file_lock(db_lock_filepath)

    if not os.path.exists(db_filepath):
        touch(db_filepath)

    dump(user_db, db_filepath)

    if not locked:
        release_file_lock(flock)


def __send_project_create_confirmation(configuration,
                                       login,
                                       project_name):
    """Send project create confirmation to *login* and GDP admins"""

    _logger = configuration.logger
    _logger.debug("login: '%s', project_name: '%s'" % (login,
                                                       project_name))
    status = True
    template = None

    # Check for PDF generation packages

    if pdfkit is None:
        status = False
        _logger.error("Missing python pdfkit package")

    if Xvfb is None:
        status = False
        _logger.error("Missing python xvfbwrapper package")

    if status:

        # Load notification emails

        notify_filepath = os.path.join(configuration.gdp_home,
                                       notify_filename)
        notify = []
        if os.path.isfile(notify_filepath):
            fh = open(notify_filepath)
            notifyline = fh.readline()
            while notifyline:
                email_idx = notifyline.find('<')
                entry = {'name': notifyline[:email_idx].strip(' \t\n\r'),
                         'email': notifyline[email_idx:].strip(' \t\n\r')}
                notify.append(entry)
                notifyline = fh.readline()
            fh.close()
            if not notify:
                _logger.warning("GDP: No notify emails found in file: '%s'"
                                % notify_filepath)
        else:
            _logger.warning("GDP: Missing notify emails file: '%s'"
                            % notify_filepath)

    if status:

        # Check for project home dir

        project_home = os.path.join(configuration.gdp_home, project_name)
        if status and not os.path.isdir(project_home):
            status = False
            _logger.error("GDP: Missing project home dir: '%s'"
                          % project_home)

    if status:

        # Check for project create template

        template_filepath = os.path.join(configuration.gdp_home,
                                         template_filename)
        if status:
            if os.path.isfile(template_filepath):
                fh = open(template_filepath)
                template = fh.read()
                fh.close()
            else:
                status = False
                _logger.error("GDP: Missing project create template file: '%s'"
                              % template_filepath)

    # Generate project create PDF

    if status:
        pdf_filename = '%s.pdf' % project_name
        pdf_filepath = os.path.join(project_home, pdf_filename)
        pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
        }

        timestamp = datetime.fromtimestamp(time.time())
        date = timestamp.strftime('%d/%m/%Y %H:%M:%S')
        fill_entries = {'title': configuration.short_title,
                        'date': date,
                        'project_name': project_name,
                        'creator': login}
        template = template % fill_entries
        template.encode('utf8')

        vdisplay = None
        try:
            # NOTE: we force disable network listen for security
            vdisplay = Xvfb(nolisten='tcp')
            vdisplay.start()
        except Exception, exc:
            status = False
            vdisplay = None
            _logger.error('GPD: failed to initialize vdisplay, error: %s'
                          % exc)

        if status:
            try:
                env = os.environ
                env['DISPLAY'] = ':%s' % vdisplay.vdisplay_num
                pdfkit_conf = pdfkit.configuration(environ=env)
                pdfkit.from_string(template, pdf_filepath,
                                   configuration=pdfkit_conf,
                                   options=pdf_options)
            except Exception, exc:
                status = False
                _logger.error('GDP: pdfkit failed, error: %s' % exc)

        if vdisplay is not None:
            try:
                vdisplay.stop()
            except Exception, exc:
                status = False
                _logger.error('GPD: failed to stop vdisplay, error: %s'
                              % exc)

        if not status:
            _logger.error(
                "GPD: failed generate project create PDF"
                + " for: '%s' created by: '%s'" % (project_name, login))

    # Send project create mail

    if status:
        recipients = login
        for admin in notify:
            recipients = '%s, %s %s' % (recipients, admin['name'],
                                        admin['email'])
        subject = "SIF project create: '%s'" % project_name
        message = ''
        status = send_email(
            recipients,
            subject,
            message,
            _logger,
            configuration,
            [pdf_filepath],
        )

    return status


def get_project_from_client_id(configuration, project_client_id):
    """Returns project name from *project_client_id*"""

    return __project_name_from_project_client_id(configuration,
                                                 project_client_id)


def get_project_from_short_id(configuration, project_short_id):
    """Returns project name from *project_short_id*"""

    _logger = configuration.logger
    result = None
    _logger.debug("project_short_id: %s" % project_short_id)

    try:
        result = project_short_id.split('@')[2]
    except Exception:
        _logger.error(
            "GDP: get_project_from_short_id failed:"
            + "'%s' is _NOT_ a project short id" % project_short_id)

    return result


def get_project_from_user_id(configuration, user_id):
    """Returns project name from *user_id*"""

    return __project_name_from_user_id(configuration, user_id)


def get_active_project_client_id(configuration, user_id, protocol):
    """Returns active project_client_id for *user_id* with *protocol*"""

    _logger = configuration.logger
    _logger.debug("user_id: '%s', protocol: '%s'"
                  % (user_id, protocol))
    result = None
    client_id = __client_id_from_user_id(configuration, user_id)

    if client_id is not None:
        user_db = __load_user_db(configuration)
        (status, _) = __validate_user_db(configuration, client_id,
                                         user_db)
        # Retrieve active project client id
        if status:
            result = user_db.get(client_id,
                                 {}).get('account',
                                         {}).get(protocol,
                                                 {}).get('role', '')

    return result


def get_active_project_short_id(configuration, user_id, protocol):
    """Returns active project_short_id for *user_id* with *protocol*"""

    _logger = configuration.logger
    _logger.debug("user_id: '%s', protocol: '%s'"
                  % (user_id, protocol))
    result = None

    project_client_id = get_active_project_client_id(
        configuration, user_id, protocol)
    result = __project_short_id_from_project_client_id(
        configuration, project_client_id)

    return result


def project_log(
        configuration,
        protocol,
        user_id,
        action,
        details,
        project_name=None,
        user_addr=None):
    """Log project actions, each project has a distinct logfile"""

    _logger = configuration.logger
    status = True

    # Validate action

    action = action.lower()
    if action not in valid_log_actions:
        status = False
        _logger.error(
            "GDP: project_log action: '%s':" % action
            + " is _NOT_ in valid_log_actions %s" % valid_log_actions)

    # Validate protocol

    if protocol not in valid_protocols:
        status = False
        _logger.error(
            "GDP: project_log : protocol: '%s'" % protocol
            + " is _NOT_ in valid_protocols: %s" % valid_protocols)

    # Get client_id and project_client_id from user_id

    if status:
        possible_project_client_id = expand_openid_alias(
            user_id, configuration)
        possible_client_id = __client_id_from_project_client_id(
            configuration, possible_project_client_id)
        if possible_client_id is not None:
            client_id = possible_client_id
            project_client_id = possible_project_client_id
        else:
            client_id = possible_project_client_id
            project_client_id = None

    # Generate user hash for log

    if status:
        user_hash = hashlib.sha256(client_id).hexdigest()

    # Get project name

    if status and project_name is None:
        project_name = \
            __project_name_from_project_client_id(configuration,
                                                  project_client_id)

    # Validate project name

    if status and project_name is None:
        status = False
        _logger.error(
            "GDP: project_log missing project name for: '%s'" % client_id)

    if status:

        # Initialize logger each project got its own logfile
        # TODO: cache GDP log initialization ?

        log_name = '%s.log' % project_name
        log_path = os.path.join(configuration.gdp_home,
                                os.path.join(project_name, log_name))
        header = False
        if not os.path.exists(log_path):
            header = True
        flock_path = '%s.lock' % log_path
        flock = acquire_file_lock(flock_path)
        logger = logging.getLogger('GDP')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_path, mode='a+',
                                      encoding=None, delay=False)
        formatter = \
            logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if user_addr is None:
            user_addr = 'UNKNOWN'

        # Generate log message and log to project log

        if header:
            msg_header = \
                ': PROJECT : USER : IP : PROTOCOL : ACTION : MESSAGE'
            logger.info(msg_header)

        msg = ": %s : %s : %s : %s : %s : %s" % (
            project_name,
            user_hash,
            user_addr,
            protocol,
            action,
            details,
        )
        logger.info(msg)
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
        release_file_lock(flock)

        # Log message to MiG log with caller details:

        frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
        module_name = inspect.getmodulename(frameinfo[0])
        revision = 1
        function_name = frameinfo[2]
        lineno = frameinfo[1]

        _logger.info('GDP:%s:%s:%s:%s: %s' % (module_name, revision,
                                              function_name, lineno, msg))

    return status


def validate_user(configuration, user_id, user_addr, protocol):
    """Validate user:
    Log every validation
    Validate user database format
    Check if user is active
    Check for Geo ip (TODO)
    Check for ip change between logins
    """

    _logger = configuration.logger
    _logger.debug("user_id: '%s', user_addr: '%s', protocol: '%s'"
                  % (user_id, user_addr, protocol))

    flock = None
    timestamp = time.time()
    min_ip_change_time = 600
    user = None
    account = None
    account_state = None

    client_id = __client_id_from_user_id(configuration, user_id)
    _logger.debug("client_id: '%s'" % client_id)

    (_, db_lock_filepath) = __user_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, locked=True)
    (status, msg) = __validate_user_db(configuration, client_id,
                                       user_db)

    if status:

        # Retrieve user account info

        user = user_db.get(client_id)
        account = user.get('account')
        account_state = account.get('state')
        account_protocol = account.get(protocol)
        protocol_last_login = account_protocol.get('last_login')
        protocol_last_timestamp = protocol_last_login.get('timestamp')
        protocol_last_ip = protocol_last_login.get('ip')

        # Check if user account is active

        if account_state == 'suspended':
            status = False
            msg = \
                'Account suspended, please contact the system administrators'
            _logger.info("User account: '%s' is suspended" % client_id)
        elif account_state == 'removed':
            status = False
            msg = \
                'Account removed, please contact the system administrators'
            _logger.info("User account: '%s' is removed" % client_id)
        elif protocol_last_ip \
                and protocol_last_ip != user_addr:

            # Check if IP changed since last login
            # TODO: Put GeoIP check here
            _logger.info(
                "GDP: User '%s', protocol: %s, changed ip: %s -> %s" %
                (client_id, protocol, protocol_last_ip, user_addr))

            # Reject login if IP changed within min_ip_change_time

            if protocol_last_timestamp and timestamp \
                    - protocol_last_timestamp < min_ip_change_time:
                status = False
                remaining_block = (min_ip_change_time -
                                   (timestamp - protocol_last_timestamp))

                msg = "IP changed from %s to %s, try again in %0.f seconds" \
                    % (protocol_last_ip, user_addr, remaining_block)
                _logger.info(
                    "GDP: Login REJECTED, user '%s', protocol: %s : %s" %
                    (client_id, protocol, msg))

        # Generate last login message

        if status and protocol_last_ip:
            lastlogin = datetime.fromtimestamp(protocol_last_timestamp)
            lastloginstr = lastlogin.strftime('%d/%m/%Y %H:%M:%S')

            msg = "Last %s access: %s from %s" % (protocol, lastloginstr,
                                                  protocol_last_ip)

        if status:

            # Update last login info

            protocol_last_login['ip'] = user_addr
            protocol_last_login['timestamp'] = timestamp

            __save_user_db(configuration, user_db, locked=True)

    if flock is not None:
        release_file_lock(flock)

    log_msg = "GDP:"
    if status:
        log_msg += " Validated"
    else:
        log_msg += " Rejected"
    _logger.info(log_msg
                 + " user: '%s', protocol: %s, from ip: %s" %
                 (client_id, protocol, user_addr))

    return (status, msg)


def get_users(configuration, locked=False):
    """Return list of GDP users"""

    _logger = configuration.logger
    user_db = __load_user_db(configuration, locked)

    return user_db.keys()


def get_projects(configuration, client_id, state):
    """Return list of GDP projects for user *client_id* with *state*"""

    _logger = configuration.logger
    _logger.debug("client_id: '%s', state: '%s'" % (client_id, state))
    status = True
    result = None

    # Check state

    if not state in valid_project_states:
        status = False
        _logger.error("Project state: '%s' _NOT_ in valid_states: %s"
                      % valid_project_states)

    # Retrieve user

    if status:
        user_db = __load_user_db(configuration)
        user = user_db.get(client_id, None)
        if user is None:
            status = False
            _logger.error("Mo such GDP user : '%s'" % client_id)

    # Retrieve projects

    if status:
        user_projects = user.get('projects', None)
        if user_projects is None:
            status = False
            _logger.error(
                "GDP: User DB is missing 'projects' entry for user: '%s'"
                % client_id)

    # Generate project list

    if status:
        result = []
        for (key, value) in user_projects.iteritems():
            project_state = value.get('state', '')
            if state == project_state or state == 'invite' \
                and project_state == 'accepted' \
                and vgrid_is_owner(key,
                                   client_id,
                                   configuration,
                                   recursive=False):
                result.append(key)

    return result


def get_project_client_id(client_id, project_name):
    """Generate project client id from *client_id* and *project_name*"""

    return '%s%s%s' % (client_id, client_id_project_postfix,
                       project_name)


def get_project_user_dn(configuration, requested_script, client_id, protocol):
    """Return project client id for user *client_id*.
    If user *client_id* is not logged into a project '' is returned.
    If *requested_script* is not a valid GDP page '' is returned.
    If *requested_script* is in skip_rewrite *client_id* is returned
    """

    _logger = configuration.logger
    _logger.debug("requested_script: '%s', client_id: '%s', protocol: '%s'"
                  % (requested_script, client_id, protocol))
    result = ''
    user_db = __load_user_db(configuration)

    # Check for valid GDP script

    valid = False
    for script in valid_scripts:
        if requested_script.find(script) > -1:
            valid = True
            break

    if not valid:
        _logger.error(
            "GDP: REJECTED: '%s', requested script: '%s'"
            % (client_id, requested_script)
            + " is _NOT_ in valid_scripts: %s" % valid_scripts)
    else:

        # Check if requested_script operates with original client_id
        # or project client_id

        for skip_rewrite in skip_client_id_rewrite:
            if requested_script.find(skip_rewrite) > -1:
                result = client_id
                break

        # Get active project for user client_id and protocol

        if not result:
            result = user_db.get(client_id,
                                 {}).get('account',
                                         {}).get(protocol,
                                                 {}).get('role', '')

        if not result:
            _logger.error(
                "GDP: REJECTED requested_script: '%s'" % requested_script
                + ", no active project for: '%s'" % client_id)

    return result


def ensure_user(configuration, client_addr, client_id):
    """Ensure GDP user db entry for *client_id*"""

    _logger = configuration.logger
    _logger.debug("client_addr: '%s', client_id: '%s'"
                  % (client_addr, client_id))
    (_, db_lock_filepath) = __user_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, locked=True)
    user = user_db.get(client_id, None)
    if user is None:
        user_db[client_id] = __create_gdp_user_db_entry(configuration)
        __save_user_db(configuration, user_db, locked=True)
        _logger.info("Created GDP user: '%s'" % client_id)

    release_file_lock(flock)

    return True


def project_invite(
        configuration,
        inviting_client_addr,
        inviting_client_id,
        invited_client_id,
        project_name):
    """User *inviting_client_id* invites user *invited_client_id*
    to *project_name"""

    _logger = configuration.logger
    _logger.debug(
        "inviting_client_addr: '%s', inviting_client_id: '%s'"
        % (inviting_client_addr, inviting_client_id)
        + ", invited_client_id: '%s', project_name: '%s'"
        % (invited_client_id, project_name))

    status = True

    # Get login handle (email) from client_id

    invited_login = __short_id_from_client_id(configuration,
                                              invited_client_id)
    msg = "User '%s' invited to project '%s'" % (invited_login,
                                                 project_name)
    (_, db_lock_filepath) = __user_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)

    # Retrieve user and project info

    user_db = __load_user_db(configuration, locked=True)
    user = user_db.get(invited_client_id, None)
    user_projects = user_db.get(invited_client_id, {}).get('projects',
                                                           None)
    if user is None:
        status = False
        msg = "Missing GDP user for client_id: '%s'" % invited_client_id
        _logger.error(msg)
    elif user_projects is None:
        status = False
        msg = "Missing GDP user projects for client_id: '%s'" \
            % invited_client_id
        _logger.error(msg)
    elif user_projects.get(project_name, None) is None:

        # Create a project entry for *invited_client_id*
        # and set state to 'invited'

        user_projects[project_name] = {'state': 'invited',
                                       'client_id': get_project_client_id(
                                           invited_client_id,
                                           project_name)}
        __save_user_db(configuration, user_db, locked=True)

        # Log invitation details to project log

        log_msg = "User id: %s" % hashlib.sha256(invited_client_id).hexdigest()
        project_log(
            configuration,
            'https',
            inviting_client_id,
            'invite',
            log_msg,
            project_name=project_name,
            user_addr=inviting_client_addr,
        )
    else:
        status = False
        msg = "User: '%s' already registred with project: '%s'" \
            % (invited_login, project_name)
        _logger.info('GDP: %s' % msg)

    release_file_lock(flock)

    return (status, msg)


def create_project_user(
        configuration,
        client_addr,
        client_id,
        project_name,
        project):
    """Create new project user"""

    _logger = configuration.logger
    _logger.debug("client_addr: '%s', client_id: '%s', project_name: '%s'"
                  % (client_addr, client_id, project_name))
    status = True
    msg = ""

    # Get vgrid_files_home dir for project

    project_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                     project_name)) + os.sep

    # Create project client id

    project_client_id = project['client_id'] = \
        get_project_client_id(client_id, project_name)

    # Create aliases for supported services (openid, davs and sftp)

    aliases = []
    for user_alias in [configuration.user_openid_alias,
                       configuration.user_davs_alias,
                       configuration.user_sftp_alias]:
        alias = get_short_id(configuration, project_client_id, user_alias)
        if not alias in aliases:
            aliases.append(alias)

    # Create new MiG user for project

    mig_user_map = get_full_user_map(configuration)
    mig_user_dict = mig_user_map.get(client_id, None)
    mig_user_dict['distinguished_name'] = project_client_id
    mig_user_dict['comment'] = "GDP autocreated user for project: '%s'" \
        % project_name
    mig_user_dict['openid_names'] = aliases
    mig_user_dict['auth'] = ['']
    mig_user_dict['short_id'] = ''
    mig_user_dict['old_password'] = ''
    mig_user_dict['password'] = ''
    mig_user_db_path = os.path.join(configuration.mig_server_home,
                                    mig_user_db_filename)
    try:
        create_user(mig_user_dict, configuration.config_file,
                    mig_user_db_path, ask_renew=False,
                    default_renew=True)
    except Exception, exc:
        status = False
        msg = "Failed to create user: '%s'" % project_client_id
        _logger.error('GDP: %s, error: %s' % (msg, exc))

    # Create symlink from project dir to newly created MiG user dir

    if status:
        project_client_dir = client_id_dir(project_client_id)
        project_files_link = os.path.join(configuration.user_home,
                                          project_client_dir, project_name)
        src = project_files_dir
        if not make_symlink(src, project_files_link, _logger):
            _logger.error("Failed to create symlink: '%s' -> '%s'"
                          % (src, project_files_link))
            msg = "Could not create link to GDP project files!"
            status = False

    return (status, msg)


def project_accept(
        configuration,
        client_addr,
        client_id,
        project_name):
    """Accept project invitation"""

    _logger = configuration.logger
    _logger.debug("client_addr: '%s', client_id: '%s', project_name: '%s'"
                  % (client_addr, client_id, project_name))
    status = True

    (_, db_lock_filepath) = __user_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, locked=True)

    # Retrieve user

    user = user_db.get(client_id, None)
    if user is None:
        status = False
        _logger.error("Missing GDP user for client_id: '%s'"
                      % client_id)
        msg = "No such user: %s" % client_id

    # Retrieve project

    if status:
        project = user.get('projects', {}).get(project_name, None)
        if project is None:
            status = False
            _logger.error(
                "GDP: Missing GDP project for"
                + " client_id: '%s' project_name: '%s'"
                % (client_id, project_name))
            msg = "No such project: '%s' for user: '%s'" \
                % (project_name, client_id)

    # Retrieve project state

    if status:
        project_state = project.get('state', '')
        if project_state != 'invited':
            status = False
            _logger.error(
                "GDP: Project accept failed for user: '%s'"
                % client_id
                + ", project: '%s'" % project_name
                + ", expected state='invited', got state='%s'" % project_state)
            msg = "No project: '%s' invitation found for user: '%s'" \
                % (project_name, client_id)

    # Create new project user

    if status:
        (status, msg) = create_project_user(configuration,
                                            client_addr,
                                            client_id,
                                            project_name,
                                            project)

    # Mark project as accepted

    if status:
        msg = "Accepted invitation to project %s" % project_name

        project['state'] = 'accepted'
        __save_user_db(configuration, user_db, locked=True)

        # Log Accept details to distinct project log

        log_msg = "Accepted invitation"
        project_log(
            configuration,
            'https',
            client_id,
            'accept_invite',
            log_msg,
            project_name=project_name,
            user_addr=client_addr,
        )

    release_file_lock(flock)

    return (status, msg)


def project_login(
        configuration,
        client_addr,
        protocol,
        user_id,
        project_name=None):
    """Log *client_id* into project_name"""

    _logger = configuration.logger
    _logger.debug("user_id: '%s', client_addr: '%s', project_name: '%s'"
                  % (user_id, client_addr, project_name))
    result = None
    status = True
    flock = None

    client_id = __client_id_from_user_id(configuration, user_id)

    if project_name is None:
        project_name = get_project_from_user_id(configuration, user_id)
        if project_name is None:
            status = False
            _logger.error(
                "GDP: Missing project name in user_id: '%s'" % user_id)

    # Make sure user with 'client_id' is logged out from all projects
    # NOTE: This should be the case already if system is consistent

    if status:
        (_, db_lock_filepath) = __user_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)

        # Retrieve user and project info

        user_db = __load_user_db(configuration, locked=True)
        user = user_db.get(client_id, None)
        if user is None:
            status = False
            _logger.error("GDP: Missing user: '%s'" % client_id)
        else:
            user_project = user.get('projects', {}).get(project_name, None)
            if user_project is None:
                status = False
                _logger.error(
                    "GDP: Missing user project: '%s' : '%s'"
                    % (client_id, project_name)
                    + ", supposed to be added at project create"
                    + " or invite / accept")

    # Retrieve project state

    if status:
        project_state = user_project.get('state', '')
        if project_state != 'accepted':
            status = False
            _logger.error(
                "GDP: Project login failed for user: '%s', project: '%s'"
                % (client_id, project_name)
                + ", expected state='accepted', got state='%s'"
                % user_project['state'])

    # Retrieve user account info

    if status:
        user_account = user.get('account', None)
        if user_account is None:
            status = False
            _logger.error("GDP: Missing account info for user: '%s'"
                          % client_id)

    # Check if user is already logged into a another project

    if status:
        if protocol not in valid_protocols:
            status = False
            _logger.error(
                "GDP: protocol: '%s'" % protocol
                + " is _NOT_ in valid_protocols: %s" % valid_protocols)

        role = user_account.get(protocol,
                                {}).get('role', '')
        if role:
            status = False
            project_name = \
                __project_name_from_project_client_id(configuration,
                                                      role)
            _logger.error(
                "GDP: User: '%s', protocol: '%s'" % (client_id, protocol)
                + " is already logged into project: '%s'" % project_name)

    # Get project client id and mark it as active

    if status:
        project_client_id = \
            user_account[protocol]['role'] = \
            user_project['client_id'] = get_project_client_id(client_id,
                                                              project_name)
        __save_user_db(configuration, user_db, locked=True)

    if flock is not None:
        release_file_lock(flock)

    # Generate log message and log to project log

    if status:
        log_msg = "Project user id: %s" % hashlib.sha256(
            project_client_id).hexdigest()
        status = project_log(
            configuration,
            protocol,
            project_client_id,
            'logged_in',
            log_msg,
            project_name=project_name,
            user_addr=client_addr,
        )

    if status:
        result = project_client_id

    return result


def project_logout(
        configuration,
        client_addr,
        protocol,
        user_id,
        autologout=False):
    """Logout user *client_id* from active project
    If *client_id* is None then *project_client_id* must not be None
    Returns True if *client_id* got and active project and is logged out if it
    False otherwise
    """

    _logger = configuration.logger
    _logger.debug("user_id: '%s', protocol: '%s', client_addr: '%s'"
                  % (user_id, protocol, client_addr))
    status = True
    result = False
    project_name = None
    role = None

    client_id = __client_id_from_user_id(configuration, user_id)
    project_client_id = __project_client_id_from_user_id(
        configuration, user_id)

    (_, db_lock_filepath) = __user_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, locked=True)

    # Retrieve user

    if status:
        user = user_db.get(client_id, None)
        if user is None:
            status = False
            _logger.error("GDP: Missing user: '%s'" % client_id)

    # Retrieve user account

    if status:
        user_account = user.get('account', None)
        if user_account is None:
            status = False
            _logger.error("GDP: Missing user account: '%s'" % client_id)

    # Retrieve and set user account role

    if status:
        role = user_account.get(protocol,
                                {}).get('role', '')
        if project_client_id == client_id:
            project_client_id = role
        if not role:
            status = False
            _logger.warning(
                "GDP: User: '%s' is _NOT_ logged in" % client_id
                + " with protocol '%s'" % protocol
                + " to project: '%s'" % project_name)
        elif project_client_id is not None and role != project_client_id:
            status = False
            _logger.warning(
                "GDP: User: '%s' is logged in to project: '%s'" % (
                    client_id, role)
                + " with protocol: '%s'" % protocol
                + ", trying to log out of project: '%s'" % project_client_id)
        else:
            project_name = \
                __project_name_from_project_client_id(configuration,
                                                      project_client_id)
            user_account[protocol]['role'] = ''

            __save_user_db(configuration, user_db, locked=True)

    release_file_lock(flock)

    if status:
        if autologout:
            action = 'auto_logged_out'
        else:
            action = 'logged_out'

        # Generate log message and log to project log

        log_msg = "Project user id: %s" % hashlib.sha256(
            project_client_id).hexdigest()
        status = project_log(
            configuration,
            protocol,
            project_client_id,
            action,
            log_msg,
            project_name=project_name,
            user_addr=client_addr,
        )

    if status:
        result = True

    return result


def project_create(
        configuration,
        client_addr,
        client_id,
        project_name):
    """Create new project with *project_name* and owner *client_id*"""

    _logger = configuration.logger
    _logger.debug(
        "project_create: client_id: '%s'"
        + ", project_name: '%s'", client_id, project_name)

    status = True
    msg = ""
    project_client_id = None
    mig_user_dict = None
    rollback_dirs = {}
    vgrid_label = '%s' % configuration.site_vgrid_label

    # Create vgrid
    # This is done explicitly here as not all operations from
    # shared.functionality.createvgrid apply to GDP
    # TODO:
    # Move vgridcreate functions from shared.functionality.createvgrid
    # to a commen helper module

    if project_name.find('/') != -1:
        status = False
        msg = "'/' _NOT_ allowed in project name'"
        _logger.error('GDP: %s' % msg)

    # No owner check here so we need to specifically check for illegal
    # directory status

    if status:
        reserved_names = (default_vgrid, any_vgrid, all_vgrids)
        if project_name in reserved_names \
            or not valid_dir_input(configuration.vgrid_home,
                                   project_name):
            status = False
            msg = "Illegal project_name: '%s'" % project_name
            _logger.warning(
                "GDP: createvgrid possible illegal directory status"
                + ", attempt by '%s': vgrid_name '%s'"
                % client_id, project_name)

    # Optional limitation of create vgrid permission

    if status:
        mig_user_map = get_full_user_map(configuration)
        mig_user_dict = mig_user_map.get(client_id, None)

        if not mig_user_dict or not vgrid_create_allowed(configuration,
                                                         mig_user_dict):
            status = False
            msg = "GDP: Only privileged users can create %ss" \
                % vgrid_label
            _logger.warning("GDP: User '%s' is not allowed to create vgrids!"
                            % client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    if status:
        vgrid_home_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_home,
                                         project_name)) + os.sep
        vgrid_files_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                         project_name)) + os.sep

        if vgrid_restrict_write_support(configuration):
            flat_vgrid = vgrid_flat_name(project_name, configuration)
            vgrid_writable_dir = \
                os.path.abspath(os.path.join(
                    configuration.vgrid_files_writable,
                    flat_vgrid)) + os.sep
            vgrid_readonly_dir = \
                os.path.abspath(os.path.join(
                    configuration.vgrid_files_readonly,
                    flat_vgrid)) + os.sep
        else:
            vgrid_writable_dir = None
            vgrid_readonly_dir = None

        # Does vgrid exist?

        if os.path.exists(vgrid_home_dir):
            status = False
            msg = \
                "%s '%s' cannot be created because it already exists!" \
                % (vgrid_label, project_name)
            _logger.error("GDP: user '%s' can't create vgrid '%s' - it exists!"
                          % (client_id, project_name))

    # Make sure all dirs can be created (that a file or directory with the same
    # name do not exist prior to the vgrid creation)

    if status and os.path.exists(vgrid_files_dir):
        status = False
        msg = \
            """%s '%s' cannot be created, a file or directory exists with the same
name, please try again with a new name!""" \
            % (vgrid_label, project_name)
        _logger.error('GDP: %s' % msg)

    # Create directory to store vgrid files

    if status:
        try:
            os.mkdir(vgrid_home_dir)
            rollback_dirs['vgrid_home_dir'] = vgrid_home_dir
        except Exception, exc:
            status = False
            msg = "Could not create %s base directory" % vgrid_label \
                + " for project: '%s'" % (project_name)
            _logger.error('GDP: %s, error: %s' % (msg, exc))

    # Create directory in vgrid_files_home or vgrid_files_writable to contain
    # shared files for the new vgrid.

    if status:
        try:
            if vgrid_writable_dir:
                os.mkdir(vgrid_writable_dir)
                make_symlink(vgrid_writable_dir.rstrip('/'),
                             vgrid_files_dir.rstrip('/'), _logger)
                rollback_dirs['vgrid_writable_dir'] = vgrid_writable_dir
            else:
                os.mkdir(vgrid_files_dir)
            rollback_dirs['vgrid_files_dir'] = vgrid_files_dir
            share_readme = os.path.join(vgrid_files_dir, 'README')
            if not os.path.exists(share_readme):
                write_file("""= Private Share =
This directory is used for hosting private files for the '%s' '%s'.
""" % (vgrid_label, project_name), share_readme, _logger, make_parent=False)
        except Exception, exc:
            status = False
            msg = "Could not create %s files directory" % vgrid_label \
                + " for project '%s'" % project_name
            _logger.error('GDP: %s, error: %s' % (msg, exc))

    # Create owners list with client_id as owner

    if status:
        owner_list = [client_id]

        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name, owner_list)
        if not owner_status:
            status = False
            msg = "Could not save owner list: '%s'" % owner_msg
            _logger.error('GDP: %s' % msg)

    # Create member list with project_client_id as member

    if status:
        project_client_id = get_project_client_id(client_id,
                                                  project_name)
        member_list = [project_client_id]

        (member_status, member_msg) = vgrid_set_members(configuration,
                                                        project_name,
                                                        member_list)
        if not member_status:
            status = False
            msg = "Could not save member list: '%s'" % member_msg
            _logger.error('GDP: %s' % msg)

    # Create default pickled settings list with only required values set to
    # leave all other fields for inheritance by default.

    if status:
        init_settings = {}
        settings_specs = get_settings_keywords_dict(configuration)
        for (key, spec) in settings_specs.items():
            if spec['Required']:
                init_settings[key] = spec['Value']
        init_settings['vgrid_name'] = project_name
        (settings_status, settings_msg) = \
            vgrid_set_settings(configuration, project_name,
                               init_settings.items())
        if not settings_status:
            status = False
            msg = "Could not save settings list: '%s'" % settings_msg
            _logger.error('GDP: %s' % msg)

    # Create directory to store gdp project files

    if status:
        project_home = os.path.join(configuration.gdp_home,
                                    project_name)
        if not os.path.isdir(project_home):
            try:
                os.mkdir(project_home)
                rollback_dirs['project_home'] = project_home
            except Exception, exc:
                status = False
                msg = "Could not create home directory" \
                    + " for project: '%s'" % project_name
                _logger.error('GDP: %s, error: %s' % (msg, exc))
        else:
            status = False
            msg = "Home dir already exists for project: '%s'" \
                % project_name
            _logger.error("GDP: %s, '%s'" % (msg, project_home))

    # 'Invite' and 'accept' to enable owner login

    if status and not project_invite(configuration, client_addr,
                                     client_id, client_id, project_name):
        status = False
        msg = "Automatic invite failed for project: '%s'" % project_name
        _logger.error("GDP: %s, owner '%s'" % (msg, client_id))

    if status and not project_accept(configuration, client_addr,
                                     client_id, project_name):
        status = False
        msg = "Automatic accept failed for project: '%s'" % project_name
        _logger.error("GDP: %s, owner '%s'" % (msg, client_id))

    # Send create info to GDP admin

    if status:
        login = __short_id_from_client_id(configuration, client_id)
        status = __send_project_create_confirmation(configuration,
                                                    login, project_name)
        if not status:
            msg = "Failed to send project create confirmation email" \
                + " for project: '%s'" % project_name
            _logger.error('GDP: %s' % msg)

    # Roll back if something went wrong

    if not status:
        _logger.info(
            "GDP: project_create failed for project: '%s'" % project_name
            + ", rolling back")

        # Remove project directories

        for (key, path) in rollback_dirs.iteritems():
            _logger.info(
                "GDP: project_create : roll back :"
                + " Recursively removing : '%s' -> '%s'" % (key, path))
            remove_rec(path, configuration)

        # Remove project mig user

        if project_client_id is not None:
            _logger.info(
                "GDP: project_create : roll back :"
                + " Deleting mig user: '%s'" % project_client_id)
            mig_user_db_path = \
                os.path.join(configuration.mig_server_home,
                             mig_user_db_filename)
            mig_user_map = get_full_user_map(configuration)
            mig_user_dict = mig_user_map.get(project_client_id, None)
            if mig_user_dict is not None:
                delete_user(mig_user_dict, configuration.config_file,
                            mig_user_db_path, force=True)

         # Remove project from user in gdp user database

        _logger.info(
            "GDP: project_create : roll back:"
            + " Deleting gdp user db project: '%s' -> '%s'"
            % (client_id, project_name))

        (_, db_lock_filepath) = __user_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)
        user_db = __load_user_db(configuration, locked=True)
        try:
            del user_db[client_id]['projects'][project_name]
        except Exception, exc:
            _logger.error(
                "GDP: project_create : roll back :"
                + " failed for gdp user db: '%s' -> '%s'"
                % (client_id, project_name))
        __save_user_db(configuration, user_db, locked=True)
        release_file_lock(flock)

        if not msg:
            msg = "Failed to create project: '%s'" % project_name

    if status:
        msg = "Created project: '%s'" % project_name

        # Update log for project

        log_msg = "Project: '%s'" % project_name
        project_log(
            configuration,
            'https',
            client_id,
            'created',
            log_msg,
            project_name=project_name,
            user_addr=client_addr,
        )

    return (status, msg)
