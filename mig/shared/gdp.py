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
import inspect
import logging
import logging.handlers
from datetime import datetime

from shared.base import client_id_dir, valid_dir_input
from shared.defaults import default_vgrid, all_vgrids, any_vgrid, \
    user_db_filename as mig_user_db_filename
from shared.fileio import touch, make_symlink, write_file, remove_rec, \
    acquire_file_lock, release_file_lock
from shared.serial import load, dump
from shared.useradm import get_full_user_map
from shared.useradm import create_user, delete_user

from shared.vgrid import vgrid_is_owner, vgrid_set_owners, \
    vgrid_set_members, vgrid_set_settings, vgrid_create_allowed, \
    vgrid_restrict_write_support, vgrid_flat_name
from shared.vgridkeywords import get_settings_keywords_dict

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
    'adminvgrid.py',
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
    'uploadchunked.py',
    'viewvgrid.py',
    'vgridman.py',
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

valid_account_states = ['active', 'suspended']


def __user_db_filepath(configuration):
    """Generate GDP user_db filepath"""

    db_filepath = os.path.join(configuration.gdp_home, user_db_filename)
    db_lock_filepath = '%s.lock' % db_filepath

    return (db_filepath, db_lock_filepath)


def __client_id_from_project_client_id(configuration,
        project_client_id):
    """Extract MiG client_id from *project_client_id"""

    _logger = configuration.logger
    _logger.debug('project_client_id: %s' % project_client_id)
    result = None

    try:
        if project_client_id.find(client_id_project_postfix) > -1:
            result = \
                project_client_id.split(client_id_project_postfix)[0]
        else:
            _logger.warning("'%s' is _NOT_ a GDP project client id"
                            % project_client_id)
    except Exception, exc:
        msg = 'GDP:__client_id_from_project_client_id failed:'
        msg = "%s '%s', error: %s" % (msg, project_client_id, exc)
        _logger.error(msg)

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
                project_client_id.split(client_id_project_postfix)[1].split('/'
                    )[0]
        else:
            _logger.warning("'%s' is _NOT_ a GDP project client id"
                            % project_client_id)
    except Exception, exc:
        msg = 'GDP:__project_name_from_project_client_id failed:'
        msg = "%s '%s', error: %s" % (msg, project_client_id, exc)
        _logger.error(msg)

    return result


def __login_from_client_id(configuration, client_id):
    """Extract login handle (email address) from *client_id*"""

    _logger = configuration.logger
    _logger.debug('client_id: %s' % client_id)
    login = None

    try:
        login = client_id.split('emailAddress=')[1].split('/')[0]
    except Exception, exc:
        _logger.error("GDP:__login_from_client_id failed: '%s', error: %s"
                       % (client_id, exc))

    return login


def __create_gdp_user_db_entry(configuration):
    """Create empty GDP user db entry"""

    result = {}

    last_login = {}
    last_login['timestamp'] = 0
    last_login['ip'] = None

    account = {}
    account['state'] = None
    account['role'] = None
    account['last_login'] = last_login

    result['projects'] = {}
    result['account'] = account

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
                'role': str
                'last_login': {
                    'timestamp': int
                    'ip': str
                }
            }
        }
    }
    """

    _logger = configuration.logger
    _logger.debug("client_id: '%s', user_db: %s" % (client_id, user_db))
    status = True

    msg = ''
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

    # Validate projects

    if status:
        projects = user.get('projects', None)
        if projects is None:
            status = False
            msg = \
                "GDP database format error: missing 'projects' for user: '%s'" \
                % client_id
            _logger.error(msg)

    if status:
        for (key, value) in projects.iteritems():
            if not 'client_id' in value.keys():
                status = False
                msg = "GDP database format error: missing 'client_id'"
                msg = "%s for project: '%s', user: '%s'" % (msg, key,
                        client_id)
                _logger.error(msg)
                break
            if not 'state' in value.keys():
                status = False
                msg = "GDP database format error: missing 'state'"
                msg = "%s for project: '%s', user: '%s'" % (msg, key,
                        client_id)
                _logger.error(msg)
                break

    # Validate account

    if status:
        account = user.get('account', None)
        if account is None:
            status = False
            msg = "GDP database format error: missing 'account'"
            msg = "%s for user: '%s'" % (msg, client_id)
            _logger.error(msg)

    # Validate account state

    if status and not 'state' in account:
        status = False
        msg = "GDP database format error: missing 'account -> state'"
        msg = "%s for user '%s'" % (msg, client_id)
        _logger.error(msg)

    # Validate account role

    if status and not 'role' in account:
        status = False
        msg = "GDP database format error: missing 'account -> role'"
        msg = "%s for user: '%s'" % (msg, client_id)
        _logger.error(msg)

    # Validate account last login

    if status:
        account_last_login = account.get('last_login', None)
        if account_last_login is None:
            status = False
            msg = \
                "GDP database format error: missing 'account -> last_login'"
            msg = "%s for user: '%s'" % (msg, client_id)
            _logger.error(msg)

    # Validate account last login timestamp

    if status and not 'timestamp' in account_last_login:
        status = False
        msg = "GDP database format error: missing 'account ->"
        msg = "%s last_login -> timestamp' for user: '%s'" % (msg,
                client_id)
        _logger.error(msg)

    # Validate account last login ip

    if status and not 'ip' in account_last_login:
        status = False
        msg = \
            "GDP database format error: missing 'account -> last_login"
        msg = "%s -> ip' for user: '%s'" % (msg, client_id)
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


def get_active_project(configuration, project_client_id):
    """Returns project name from *project_client_id*"""

    return __project_name_from_project_client_id(configuration,
            project_client_id)


def project_log(
    configuration,
    client_id,
    action,
    details,
    project_name=None,
    client_ip=None,
    ):
    """Log project actions, each project has a distinct logfile"""

    _logger = configuration.logger
    status = True

    # Validate action

    action = action.lower()
    if action not in valid_log_actions:
        _logger.error("GDP: log action: '%s' _NOT_ in valid_log_actions: %s"
                       % (action, valid_log_actions))
        status = False

    # Get project name

    if status and project_name is None:
        project_name = \
            __project_name_from_project_client_id(configuration,
                client_id)

    # Validate project name

    if status and project_name is None:
        msg = "Missing GDP project name for: '%s'" % client_id
        _logger.error(msg)
        status = False

    if status:

        # Initialize logger each project got its own logfile
        # TODO: cache GDP log initialization ?

        log_name = '%s.log' % project_name
        log_path = os.path.join(configuration.gdp_home,
                                os.path.join('log', log_name))
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
        if client_ip is None:
            client_ip = 'UNKNOWN'

        # Generate log message and log to project log

        if header:
            msg_header = \
                ': PROJECT : IP : LOGIN : ID : ACTION : MESSAGE'
            logger.info(msg_header)

        login = __login_from_client_id(configuration, client_id)
        msg = ': %s : %s : %s : %s : %s : %s' % (
            project_name,
            client_ip,
            login,
            client_id,
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


def validate_user(configuration, client_id, client_ip):
    """Validate user:
    Log every validation
    Validate user database format
    Check if user is suspended
    Check for Geo ip
    Check for ip change between logins
    """

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s'" % (client_ip,
                  client_id))

    timestamp = time.time()
    min_ip_change_time = 1000
    user = None
    account = None
    account_state = None

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
        account_last_login = account.get('last_login')
        user_last_timestamp = account_last_login.get('timestamp', None)
        user_last_ip = account_last_login.get('ip', None)

        # Check if user account is active

        if account_state == 'suspended':
            status = False
            msg = \
                'Account suspended, please contact the system administrators'
            _logger.info("User account: '%s' is suspended" % client_id)
        elif user_last_ip is not None and user_last_ip != client_ip:

        # Check if IP changed since last login
        # TODO: Put GeoIP check here

            _logger.info("User '%s' changed ip: %s -> %s" % (client_id,
                         user_last_ip, client_ip))

            # Suspend account if IP changed within min_ip_change_time

            if user_last_timestamp is not None and timestamp \
                - user_last_timestamp < min_ip_change_time:
                status = False
                msg = 'ip changed from %s to %s within %s seconds' \
                    % (user_last_ip, client_ip, min_ip_change_time)
                _logger.info("GDP: User '%s' %s" % (client_id, msg)
                             % (client_id, msg))
                _logger.info("Suspending account: '%s'" % client_id)
                account['state'] = 'suspended'

        # Generate last login message

        if status and user_last_timestamp is not None and user_last_ip \
            is not None:
            lastlogin = datetime.fromtimestamp(user_last_timestamp)
            lastloginstr = lastlogin.strftime('%d/%m/%Y %H:%M:%S')

            msg = 'Last login: %s from %s' % (lastloginstr,
                    user_last_ip)

        # Update last login info

        account_last_login['timestamp'] = timestamp
        account_last_login['ip'] = client_ip
        __save_user_db(configuration, user_db, locked=True)

    release_file_lock(flock)

    if status:
        _logger.info("Validated user: '%s' from ip: %s" % (client_id,
                     client_ip))
    else:
        _logger.info("Rejected user: '%s' from ip: %s" % (client_id,
                     client_ip))

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
            msg = \
                "GDP: User DB is missing 'projects' entry for user: '%s'" \
                % client_id
            _logger.error(msg)

    # Generate project list

    if status:
        result = []
        for (key, value) in user_projects.iteritems():
            project_state = value.get('state', '')
            if state == project_state or state == 'invite' \
                and project_state == 'accepted' and vgrid_is_owner(key,
                    client_id, configuration, recursive=False):
                result.append(key)

    return result


def get_project_client_id(client_id, project_name):
    """Generate project client id from *client_id* and *project_name*"""

    return '%s%s%s' % (client_id, client_id_project_postfix,
                       project_name)


def get_project_user_dn(configuration, requested_script, client_id):
    """Return project client id for user *client_id*.
    If user *client_id* is not logged into a project '' is returned.
    If *requested_script* is not a valid GDP page '' is returned.
    If *requested_script* is in skip_rewrite *client_id* is returned
    """

    _logger = configuration.logger
    _logger.debug("requested_script: '%s', client_id: '%s'"
                  % (requested_script, client_id))
    result = ''
    user_db = __load_user_db(configuration)

    # Check for valid GDP script

    valid = False
    for script in valid_scripts:
        if requested_script.find(script) > -1:
            valid = True
            break

    if not valid:
        msg = "GDP: REJECTED: '%s', requested script: '%s'" \
            % (client_id, requested_script)
        msg = '%s is _NOT_ in valid_scripts: %s' % (msg, valid_scripts)
        _logger.error(msg)
    else:

        # Check if requested_script operates with original client_id
        # or project client_id

        for skip_rewrite in skip_client_id_rewrite:
            if requested_script.find(skip_rewrite) > -1:
                result = client_id
                break

        # Get active project for user client_id

        if not result:
            result = user_db.get(client_id, {}).get('account',
                    {}).get('role', '')

        if not result:
            msg = "GDP: REJECTED requested_script: '%s'" \
                % requested_script
            msg = "%s, no active project for '%s'" % (msg, client_id)
            _logger.error(msg)

    return result


def ensure_user(configuration, client_ip, client_id):
    """Ensure GDP user db entry for *client_id*"""

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s'" % (client_ip,
                  client_id))
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
    inviter_client_ip,
    inviter_client_id,
    invited_client_id,
    project_name,
    ):
    """User *inviter_client_ip* invites user *invited_client_id*
    to *project_name"""

    _logger = configuration.logger
    msg = "client_ip: '%s', inviter_client_id: '%s'" \
        % (inviter_client_ip, inviter_client_id)
    msg = "%s, invited_client_id: '%s', project_name: '%s'" % (msg,
            invited_client_id, project_name)
    _logger.debug(msg)
    status = True

    # Get login handle (email) from client_id

    invited_login = __login_from_client_id(configuration,
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

        # Create a project entry for *invited_client_id* and set state to 'invited'

        user_projects[project_name] = {'state': 'invited',
                'client_id': get_project_client_id(invited_client_id,
                project_name)}
        __save_user_db(configuration, user_db, locked=True)

        # Log invitation details to project log

        log_msg = '%s' % invited_client_id
        project_log(
            configuration,
            inviter_client_id,
            'invite',
            log_msg,
            project_name=project_name,
            client_ip=inviter_client_ip,
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
    project,
    client_ip,
    client_id,
    project_name,
    ):
    """Create new project user"""

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s', project_name: '%s'"
                   % (client_ip, client_id, project_name))
    status = True
    msg = ''

    # Get vgrid_files_home dir for project

    project_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        project_name)) + os.sep

    # Create project client id

    project_client_id = project['client_id'] = \
        get_project_client_id(client_id, project_name)

    # Create new MiG user for project

    mig_user_map = get_full_user_map(configuration)
    mig_user_dict = mig_user_map.get(client_id, None)
    mig_user_dict['distinguished_name'] = project_client_id
    mig_user_dict['comment'] = "GDP autocreated user for project: '%s'" \
        % project_name
    mig_user_dict['openid_names'] = ['']
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
    except Exception, err:
        status = False
        _logger.error("create failed for '%s': '%s'"
                      % (project_client_id, err))
        msg = "Failed to create user: '%s'" % project_client_id

    # Create symlink from project dir to newly created MiG user dir

    if status:
        project_client_dir = client_id_dir(project_client_id)
        project_files_link = os.path.join(configuration.user_home,
                project_client_dir, project_name)
        src = project_files_dir
        if not make_symlink(src, project_files_link, _logger):
            _logger.error("Failed to create symlink: '%s' -> '%s'"
                          % (src, project_files_link))
            msg = 'Could not create link to GDP project files!'
            status = False

    return (status, msg)


def project_accept(
    configuration,
    client_ip,
    client_id,
    project_name,
    ):
    """Accept project invitation"""

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s', project_name: '%s'"
                   % (client_ip, client_id, project_name))
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
        msg = 'No such user: %s' % client_id

    # Retrieve project

    if status:
        project = user.get('projects', {}).get(project_name, None)
        if project is None:
            status = False
            log_msg = 'GDP: Missing GDP project for'
            log_msg = "%s client_id: '%s' project_name: '%s'" \
                % (log_msg, client_id, project_name)
            _logger.error(log_msg)
            msg = "No such project: '%s' for user: '%s'" \
                % (project_name, client_id)

    # Retrieve project state

    if status:
        project_state = project.get('state', '')
        if project_state != 'invited':
            status = False
            log_msg = "GDP: Project accept failed for user: '%s'" \
                % client_id
            log_msg = "%s, project: '%s'" % (log_msg, project_name)
            log_msg = "%s, expected state='invited', got state='%s'" \
                % (log_msg, project_state)
            _logger.error(log_msg)
            msg = "No project: '%s' invitation found for user: '%s'" \
                % (project_name, client_id)

    # Create new project user

    if status:
        (status, msg) = create_project_user(configuration, project,
                client_ip, client_id, project_name)

    # Mark project as accepted

    if status:
        msg = 'Accepted invitation to project %s' % project_name

        project['state'] = 'accepted'
        __save_user_db(configuration, user_db, locked=True)

        # Log Accept details to distinct project log

        log_msg = 'Accepted invitation'
        project_log(
            configuration,
            client_id,
            'accept_invite',
            log_msg,
            project_name=project_name,
            client_ip=client_ip,
            )

    release_file_lock(flock)

    return (status, msg)


def project_login(
    configuration,
    client_ip,
    client_id,
    project_name,
    ):
    """Log *client_id* into project_name"""

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s', project_name: '%s'"
                   % (client_ip, client_id, project_name))
    result = None
    status = True

    # Make sure user with 'client_id' is logged out from all projects
    # NOTE: This should be the case already if system is consistent

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
            msg = \
                "GDP: Missing user project: '%s' : '%s', supposed to be added" \
                % (client_id, project_name)
            msg = '%s at project create or invite / accept' % msg
            _logger.error(msg)

    # Retrieve project state

    if status:
        project_state = user_project.get('state', '')
        if project_state != 'accepted':
            status = False
            msg = \
                "GDP: Project login failed for user: '%s', project: '%s'" \
                % (client_id, project_name)
            msg = "%s, expected state='accepted', got state='%s'" \
                % (msg, user_project['state'])
            _logger.error(msg)

    # Retrieve user account info

    if status:
        user_account = user.get('account', None)
        if user_account is None:
            status = False
            _logger.error("GDP: Missing account info for user: '%s'"
                          % client_id)

    # Check if user is already logged into a another project

    if status:
        role = user_account.get('role')
        if role is not None:
            status = False
            project_name = \
                __project_name_from_project_client_id(configuration,
                    role)
            _logger.error("GDP: User: '%s' is already logged into project: '%s'"
                           % (client_id, project_name))

    # Get project client id

    if status:
        result = user_account['role'] = user_project['client_id'] = \
            get_project_client_id(client_id, project_name)
        __save_user_db(configuration, user_db, locked=True)

    release_file_lock(flock)

    # Generate log message and log to project log

    if status:
        log_msg = '%s' % result
        project_log(
            configuration,
            client_id,
            'logged_in',
            log_msg,
            project_name=project_name,
            client_ip=client_ip,
            )

    return result


def project_logout(
    configuration,
    client_ip,
    client_id=None,
    project_client_id=None,
    autologout=False,
    ):
    """Logout user *client_id* from active project
    If *client_id* is None then *project_client_id* must not be None
    Returns True if *client_id* got and active project and is logged out if it
    False otherwise
    """

    _logger = configuration.logger
    _logger.debug("client_ip: '%s', client_id: '%s', project_client_id: '%s'"
                   % (client_ip, client_id, project_client_id))
    status = True
    result = False
    project_name = None
    role = None

    (_, db_lock_filepath) = __user_db_filepath(configuration)
    _logger.debug('db_lock_filepath: %s' % db_lock_filepath)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, locked=True)

    # Extract client_id from project_client_id if necessary

    if client_id is None:
        client_id = __client_id_from_project_client_id(configuration,
                project_client_id)
    if client_id is None:
        status = False
        msg = 'GDP: Logout failed to extract client_id'
        msg = "%s from project_client_id: '%s'" % project_client_id
        _logger.error(msg)

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
        role = user_account.get('role', None)
        if role is not None:
            result = True
            project_name = \
                __project_name_from_project_client_id(configuration,
                    role)
            user_account['role'] = None

        __save_user_db(configuration, user_db, locked=True)

    release_file_lock(flock)

    if result:
        if autologout:
            action = 'auto_logged_out'
        else:
            action = 'logged_out'

        # Generate log message and log to project log

        log_msg = '%s' % role
        project_log(
            configuration,
            client_id,
            action,
            log_msg,
            project_name=project_name,
            client_ip=client_ip,
            )

    return result


def project_create(
    configuration,
    client_ip,
    client_id,
    project_name,
    ):
    """Create new project with *project_name* and owner *client_id*"""

    _logger = configuration.logger
    _logger.debug("project_create: client_id: '%s', project_name: '%s'"
                  , client_id, project_name)
    status = True
    msg = ''
    project_client_id = None
    mig_user_dict = None
    rollback_dirs = {}
    vgrid_label = '%s' % configuration.site_vgrid_label

    # Create vgrid
    # This is done explisitly here as not all operations from
    # shared.functionality.createvgrid apply to GDP
    # TODO:
    # Move vgridcreate functions from shared.functionality.createvgrid
    # to a commen helper module

    vgrid_name = project_name
    if vgrid_name.find('/') != -1:
        status = False
        msg = "'/' _NOT_ allowed in project name'"
        _logger.error('GDP: %s' % msg)

    # No owner check here so we need to specifically check for illegal
    # directory status

    if status:
        reserved_names = (default_vgrid, any_vgrid, all_vgrids)
        if vgrid_name in reserved_names \
            or not valid_dir_input(configuration.vgrid_home,
                                   vgrid_name):
            status = False
            msg = "Illegal project_name: '%s'" % vgrid_name
            log_msg = \
                'GDP: createvgrid possible illegal directory status'
            log_msg = "%s, attempt by '%s': vgrid_name '%s'" \
                % (log_msg, client_id, vgrid_name)
            _logger.warning(msg)

    # Optional limitation of create vgrid permission

    if status:
        mig_user_map = get_full_user_map(configuration)
        mig_user_dict = mig_user_map.get(client_id, None)

        if not mig_user_dict or not vgrid_create_allowed(configuration,
                mig_user_dict):
            status = False
            msg = 'GDP: Only privileged users can create %ss' \
                % vgrid_label
            _logger.warning("GDP: User '%s' is not allowed to create vgrids!"
                             % client_id)

    # Please note that base_dir must end in slash to avoid status to other
    # user dirs when own name is a prefix of another user name

    if status:
        vgrid_home_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_home,
                            vgrid_name)) + os.sep
        vgrid_files_dir = \
            os.path.abspath(os.path.join(configuration.vgrid_files_home,
                            vgrid_name)) + os.sep

        if vgrid_restrict_write_support(configuration):
            flat_vgrid = vgrid_flat_name(vgrid_name, configuration)
            vgrid_writable_dir = \
                os.path.abspath(os.path.join(configuration.vgrid_files_writable,
                                flat_vgrid)) + os.sep
            vgrid_readonly_dir = \
                os.path.abspath(os.path.join(configuration.vgrid_files_readonly,
                                flat_vgrid)) + os.sep
        else:
            vgrid_writable_dir = None
            vgrid_readonly_dir = None

        # does vgrid exist?

        if os.path.exists(vgrid_home_dir):
            status = False
            msg = \
                "%s: '%s' cannot be created because it already exists!" \
                % (vgrid_label, vgrid_name)
            _logger.error("GDP: user '%s' can't create vgrid '%s' - it exists!"
                           % (client_id, vgrid_name))

    # make sure all dirs can be created (that a file or directory with the same
    # name do not exist prior to the vgrid creation)

    if status and os.path.exists(vgrid_files_dir):
        status = False
        msg = \
            """'%s' cannot be created, a file or directory exists with the same
name, please try again with a new name!""" \
            % vgrid_label
        _logger.error('GDP: %s' % msg)

    # create directory to store vgrid files

    if status:
        try:
            os.mkdir(vgrid_home_dir)
            rollback_dirs['vgrid_home_dir'] = vgrid_home_dir
        except Exception, exc:
            status = False
            msg = 'Could not create %s directory' % vgrid_label
            _logger.error("GDP: Could not create vgrid base directory: '%s'"
                           % exc)

    # create directory in vgrid_files_home or vgrid_files_writable to contain
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
            rollback_dirs['vgrid_files_dir'] = vgrid_writable_dir
            share_readme = os.path.join(vgrid_files_dir, 'README')
            if not os.path.exists(share_readme):
                write_file("""= Private Share =
    This directory is used for hosting private files for the '%s' '%s'.
    """
                           % (vgrid_label, vgrid_name), share_readme,
                           _logger, make_parent=False)
        except Exception, exc:
            status = False
            msg = 'Could not create %s files directory.' % vgrid_label
            _logger.error("Could not create vgrid files directory: '%s'"
                           % exc)

    # Create owners list with client_id as owner

    if status:
        owner_list = [client_id]

        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                vgrid_name, owner_list)
        if not owner_status:
            status = False
            msg = "Could not save owner list: '%s'" % owner_msg
            _logger.error('GDP: %s' % msg)

    # create member list with project_client_id as member

    if status:
        project_client_id = get_project_client_id(client_id, vgrid_name)
        member_list = [project_client_id]

        (member_status, member_msg) = vgrid_set_members(configuration,
                vgrid_name, member_list)
        if not member_status:
            status = False
            msg = "Could not save member list: '%s'" % member_msg
            _logger.error('GDP: %s' % msg)

    # create default pickled settings list with only required values set to
    # leave all other fields for inheritance by default.

    if status:
        init_settings = {}
        settings_specs = get_settings_keywords_dict(configuration)
        for (key, spec) in settings_specs.items():
            if spec['Required']:
                init_settings[key] = spec['Value']
        init_settings['vgrid_name'] = vgrid_name
        (settings_status, settings_msg) = \
            vgrid_set_settings(configuration, vgrid_name,
                               init_settings.items())
        if not settings_status:
            status = False
            msg = "Could not save settings list: '%s'" % settings_msg
            _logger.error('GDP: %s' % msg)

    # 'Invite' and 'accept' to enable owner login

    if status and not project_invite(configuration, client_ip,
            client_id, client_id, project_name):
        status = False
        msg = 'Project invite failed'
        log_msg = 'GDP: Automatic project invite FAILED'
        log_msg = "%s for: '%s', owner: '%s'" % (log_msg, project_name,
                client_id)
        _logger.error(log_msg)

    if status and not project_accept(configuration, client_ip,
            client_id, project_name):
        status = False
        msg = 'Project accept failed'
        log_msg = 'GDP: Automatic project accept FAILED'
        log_msg = "%s for: '%s', owner: '%s'" % (log_msg, project_name,
                client_id)
        _logger.error(log_msg)

    # Roll back if something went wrong

    if not status:
        _logger.info("GDP: project_create for: '%s' failed, rolling back"
                      % vgrid_name)
        for (key, path) in rollback_dirs.iteritems():
            log_msg = 'GDP: project_create'
            log_msg = "%s : Recursively removing : '%s' -> '%s'" \
                % (log_msg, key, path)
            _logger.info(log_msg)
            remove_rec(path, configuration)

        if project_client_id is not None:
            _logger.info("GDP: project_create : Deleting user: '%s'"
                         % project_client_id)
            mig_user_db_path = os.path.join(configuration.mig_server_home,
                                    mig_user_db_filename)
            mig_user_map = get_full_user_map(configuration)
            mig_mig_user_dict = mig_user_map.get(project_client_id, None)
            delete_user(mig_mig_user_dict, configuration.config_file,
                        mig_user_db_path, force=True)

        if not msg:
            msg = "Failed to create project: '%s'" % vgrid_name

    if status:
        msg = "Created project: '%s'" % project_name

        # Update log for project

        log_msg = "Project: '%s'" % project_name
        project_log(
            configuration,
            client_id,
            'created',
            log_msg,
            project_name=project_name,
            client_ip=client_ip,
            )

    return (status, msg)

