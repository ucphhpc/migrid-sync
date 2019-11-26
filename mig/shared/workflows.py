#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# workflows.py - Collection of workflows related functions
#
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""A set of shared workflows functions"""

import fcntl
import os
import re
import sys
import time
try:
    import nbformat
except ImportError:
    nbformat = None
try:
    from nbconvert import PythonExporter, NotebookExporter
except ImportError:
    PythonExporter = None
    NotebookExporter = None

from shared.base import force_utf8_rec
from shared.conf import get_configuration_object
from shared.defaults import src_dst_sep, w_id_charset, \
    w_id_length, session_id_length, session_id_charset, default_vgrid
from shared.fileio import delete_file, write_file, makedirs_rec, touch
from shared.map import load_system_map
from shared.modified import check_workflow_p_modified, \
    check_workflow_r_modified, reset_workflow_p_modified, \
    reset_workflow_r_modified, mark_workflow_p_modified, \
    mark_workflow_r_modified
from shared.pwhash import generate_random_ascii
from shared.serial import dump, load
from shared.validstring import possible_workflow_session_id
from shared.vgrid import vgrid_add_triggers, vgrid_remove_triggers, \
    vgrid_triggers, vgrid_set_triggers, init_vgrid_script_add_rem, \
    init_vgrid_script_list
from shared.vgridaccess import get_vgrid_map, VGRIDS, user_vgrid_access


WRITE_LOCK = 'write.lock'
WORKFLOW_PATTERN = 'workflowpattern'
WORKFLOW_RECIPE = 'workflowrecipe'
WORKFLOW_ANY = 'any'
WORKFLOW_API_DB_NAME = 'workflow_api_db'
WORKFLOW_TYPES = [WORKFLOW_PATTERN, WORKFLOW_RECIPE, WORKFLOW_ANY]
WORKFLOW_CONSTRUCT_TYPES = [WORKFLOW_PATTERN, WORKFLOW_RECIPE]
MANUAL_TRIGGER = 'manual_trigger'
CANCEL_JOB = 'cancel_job'
RESUBMIT_JOB = 'resubmit_job'
WORKFLOW_ACTION_TYPES = [MANUAL_TRIGGER, CANCEL_JOB, RESUBMIT_JOB]
PATTERN_GRAPH = 'pattern_graph'
WORKFLOW_SEARCH_TYPES = [PATTERN_GRAPH]

WORKFLOW_PATTERNS, WORKFLOW_RECIPES, MODTIME, CONF = \
    ['__workflowpatterns__', '__workflow_recipes__', '__modtime__', '__conf__']
MAP_CACHE_SECONDS = 60

last_load = {WORKFLOW_PATTERNS: 0, WORKFLOW_RECIPES: 0}
last_refresh = {WORKFLOW_PATTERNS: 0, WORKFLOW_RECIPES: 0}
last_map = {WORKFLOW_PATTERNS: {}, WORKFLOW_RECIPES: {}}

# A persistent correct pattern
VALID_PATTERN = {
    # The type of workflow object it is.
    'object_type': str,
    # The unique identifier for the pattern.
    'persistence_id': str,
    # The user who created the pattern.
    'owner': str,
    # The owning vgrid where the pattern is stored.
    'vgrid': str,
    # The user defined name of the pattern (Must be unique within the vgrid).
    'name': str,
    # The variable name that the recipes will use to load
    # the triggered data path into.
    'input_file': str,
    # The output location where the pattern should output the results.
    'output': dict,
    # A dictionary of recipes that the pattern has created and
    # their associated triggers.
    # E.g. {'rule_id': {persistence_id: recipe, persistence_id: recipe,
    #                   persistence_id: recipe}}
    # If recipe doesn't exist at creation, it will be structured as
    # {'rule_id': {'recipe_name': {}} until the recipe is created.
    'trigger_recipes': dict,
    # Variables whose value will overwrite the matching variables
    # inside the recipes.
    'variables': dict,
    # (Optional) Global parameters which the recipes will be executed over.
    'parameterize_over': dict,
    # List of triggering paths. Only used for easy interaction with jupyter
    # widgets and initial pattern creation. Should not be relied on as
    # interal mig paths
    'input_paths': list
}

# Attributes that a request must provide
REQUIRED_PATTERN_INPUTS = {
    'vgrid': str,
    'name': str,
    'input_file': str,
    'input_paths': list,
    'output': dict,
    'recipes': list
}

ALL_PATTERN_INPUTS = {
    'variables': dict,
    'parameterize_over': dict
}
ALL_PATTERN_INPUTS.update(REQUIRED_PATTERN_INPUTS)

# Attributes that the user can provide via an update request
VALID_USER_UPDATE_PATTERN = {
    'persistence_id': str
}
VALID_USER_UPDATE_PATTERN.update(ALL_PATTERN_INPUTS)

# A persistent correct recipe
VALID_RECIPE = {
    # The type of workflow object it is.
    'object_type': str,
    # The unique identifier for the recipe.
    'persistence_id': str,
    # The user who created the recipe.
    'owner': str,
    # The owning vgrid where the recipe is stored.
    'vgrid': str,
    # The user defined name of the recipe (Must be unique within the vgrid).
    'name': str,
    # The code to be executed.
    'recipe': dict,
    # Task file associated with the recipe.
    'task_file': str,
    # Optional for the user to provide the source code itself.
    'source': str
}

# Attributes that a request must provide
REQUIRED_RECIPE_INPUTS = {
    'vgrid': str,
    'name': str,
    'recipe': dict
}

ALL_RECIPE_INPUTS = {
    'source': str
}
ALL_RECIPE_INPUTS.update(REQUIRED_RECIPE_INPUTS)

# Attributes that the user can provide via an update request
VALID_USER_UPDATE_RECIPE = {
    'persistence_id': str,
}
VALID_USER_UPDATE_RECIPE.update(ALL_RECIPE_INPUTS)

# Attributes required by an action request
VALID_ACTION_REQUEST = {
    'persistence_id': str,
    'object_type': str
}


def touch_workflow_sessions_db(configuration, force=False):
    """
    Create and save an empty workflow_sessions_db
    :param configuration: The MiG configuration object.
    :param force: Bool, if true the created database object will overwrite
    any existing database object.
    :return: (boolean) True/False based on successful creation or not.
    """
    _logger = configuration.logger
    _logger.debug('WP: touch_workflow_sessions_db, '
                  'creating empty db if it does not exist')
    _db_path = configuration.workflows_db
    _db_home = configuration.workflows_db_home
    _db_lock_path = configuration.workflows_db_lock

    if os.path.exists(_db_path) and os.path.exists(_db_lock_path) \
            and not force:
        _logger.debug("WP: touch_workflow_sessions_db, "
                      "db: '%s' already exists" % _db_path)
        return False

    # Ensure the directory path is available
    if not makedirs_rec(_db_home, configuration, accept_existing=True):
        _logger.debug("WP: touch_workflow_sessions_db, "
                      "failed to create dependent dir %s" % _db_home)
        return False

    # Create lock file.
    if not os.path.exists(_db_lock_path):
        if not touch(_db_lock_path, configuration):
            _logger.debug("WP: touch_workflow_sessions_db"
                          "failed to create dependent lock file: '%s'"
                          % configuration.workflows_db_lock)
            return False

    if not os.path.exists(_db_path):
        # Use the lock to synchronize the creation of the sessions db
        with open(_db_lock_path, 'a') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            # Create the db file
            if not touch(_db_path, configuration):
                _logger.debug("WP: touch_workflow_sessions_db, "
                              "failed to create db '%s'" % _db_path)
                return False

    return save_workflow_sessions_db(configuration, {})


def delete_workflow_sessions_db(configuration):
    """
    Removes workflow_sessions_db
    :param configuration: The MiG configuration object.
    :return: (boolean) True/False based on if database file has been deleted
    or not.
    """
    _logger = configuration.logger
    _logger.debug('WP: delete_workflow_sessions_db, '
                  'deleting the sessions db if it exists')
    result = False
    try:
        with open(configuration.workflows_db_lock, 'a') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            result = delete_file(configuration.workflows_db, _logger)
    except OSError as err:
        _logger.warning("WP: Failed to properly lock and delete '%s'" % err)
    return result


def load_workflow_sessions_db(configuration, do_lock=True):
    """
    Read the workflow DB dictionary.
    :param configuration: The MiG configuration object.
    :param do_lock: Bool, whether the function should lock via the
    configuration.workflows_db_lock file.
    :return: (dictionary) database of current workflow session ids. These are
    used by the MiG to track valid users interacting with
    workflowsjsoninterface.py. Format is {session_id: 'owner': client_id}.
    """
    _logger = configuration.logger
    lock_handle = None
    if not os.path.exists(configuration.workflows_db_lock) \
            or not os.path.exists(configuration.workflows_db):
        created = touch_workflow_sessions_db(configuration)
        _logger.info("Created %s" % created)

    if do_lock:
        try:
            lock_handle = open(configuration.workflows_db_lock, 'a')
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        except OSError as err:
            _logger.warning("Failed to set lock on load "
                            "workflow_session_db '%s'" % err)
            if lock_handle and not lock_handle.closed:
                lock_handle.close()
            return False

    db = {}
    try:
        db = load(configuration.workflows_db)
    except IOError as err:
        _logger.warning("Failed to load workflow_session_db '%s'" % err)

    if do_lock and lock_handle and not lock_handle.closed:
        lock_handle.close()
    return db


def save_workflow_sessions_db(configuration, workflow_sessions_db,
                              do_lock=True):
    """
    Write a dictionary of workflow session ids.
    :param configuration: The MiG configuration object.
    :param workflow_sessions_db: dictionary of workflow session ids. These are
    :param do_lock: Bool, whether the function should lock via the
    configuration.workflows_db_lock file.
    used by the MiG to track valid users interacting with
    workflowsjsoninterface.py. Format is {session_id: 'owner': client_id}.
    :return: (boolean) True/False dependent of if provided dictionary is
    saved or not.
    """
    _logger = configuration.logger
    lock_handle = None
    success = True
    try:
        if do_lock:
            lock_handle = open(configuration.workflows_db_lock, 'a')
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    except OSError as err:
        _logger.warning("Failed to set lock on save workflow_session_db '%s'"
                        % err)
        success = False

    if success:
        try:
            dump(workflow_sessions_db, configuration.workflows_db)
        except IOError as err:
            _logger.error("WP: save_workflow_sessions_db, Failed to open '%s', "
                          "err: '%s'" % (configuration.workflows_db, err))
            success = False

    if do_lock and lock_handle and not lock_handle.closed:
        lock_handle.close()
    if not success:
        return False
    return True


def create_workflow_session_id(configuration, client_id):
    """
    Generate a new workflow session id, allowing for a client to connect
    and interact with workflowsjsoninterface.py.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user id.
    :return: (string or boolean) session id, or False if one could not be
    created.
    """
    _logger = configuration.logger
    # Generate session id
    workflow_session_id = new_workflow_session_id()
    # Lock between load and save
    try:
        with open(configuration.workflows_db_lock, 'a') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            db = load_workflow_sessions_db(configuration, do_lock=False)
            if isinstance(db, dict) and workflow_session_id not in db:
                db[workflow_session_id] = {'owner': client_id}
                saved = save_workflow_sessions_db(configuration, db,
                                                  do_lock=False)
                if not saved:
                    _logger.error('WP: create_workflow_session_id, failed '
                                  'to add a workflow session id for '
                                  'user: %s' % client_id)
                    return False
            else:
                return False
    except OSError as err:
        _logger.warning("WP: create_workflow_session_id failed '%s'" % err)
        return False
    return workflow_session_id


def delete_workflow_session_id(configuration, client_id, workflow_session_id):
    """
    Deletes a given session id for workflow modification.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user id.
    :param workflow_session_id: A workflow session id
    :return: (bool) True/False dependent on if workflow_session_id was
    deleted or not. Will return False if workflow_session_id does not exist
    within the database
    """
    _logger = configuration.logger
    try:
        with open(configuration.workflows_db_lock, 'a') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            db = load_workflow_sessions_db(configuration, do_lock=False)
            if not isinstance(db, dict):
                _logger.error("WP: delete_workflow_session_id, "
                              "missing db: '%s'" % db)
                return False
            if workflow_session_id not in db:
                _logger.error('WP: delete_workflow_session_id, '
                              'failed to delete workflow_session_id: %s '
                              'was not found in db' % workflow_session_id)
                return False
            if db[workflow_session_id]['owner'] != client_id:
                _logger.error("WP: client_id '%s' is trying to a delete"
                              " someone elses session_id '%s'"
                              % (client_id, workflow_session_id))
                return False
            db.pop(workflow_session_id, None)
            if not save_workflow_sessions_db(configuration, db, do_lock=False):
                return False
    except OSError as err:
        _logger.warning("WP: delete_workflow_session_id failed '%s'" % err)
        return False
    return True


def get_workflow_session_id(configuration, client_id):
    """
    Gets a given users workflow_session_id.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user id.
    :return: (string or None) session if, or None if no session id currently
    exists for the given user.
    """
    _logger = configuration.logger
    db = load_workflow_sessions_db(configuration)
    if not isinstance(db, dict):
        return None

    for session_id, user_state in db.items():
        if user_state.get('owner', '') == client_id:
            return session_id
    return None


def new_workflow_session_id():
    """
    Generates a new workflow_session_id as a string of random ascii characters.
    :return: (string) workflow_session_id
    """
    return generate_random_ascii(session_id_length,
                                 session_id_charset)


def valid_session_id(configuration, workflow_session_id):
    """
    Validates that the workflow_session_id id is of the correct structure.
    Note this does not check that the session id exists in the current
    database.
    :param configuration: The MiG configuration object.
    :param workflow_session_id: The MiG workflow_session_id.
    :return: (boolean) True/False based on if provided workflow_session_id is
    a correctly structured workflow_session_id.
    """
    _logger = configuration.logger
    if not workflow_session_id:
        return False

    _logger.debug('WP: valid_session_id, checking %s'
                  % workflow_session_id)
    return possible_workflow_session_id(configuration, workflow_session_id)


def __generate_persistence_id():
    """
    Creates a new persistence id for a workflow object by creating a sting of
    random ascii characters.
    :return: (function call to 'generate_random_ascii')
    """
    return generate_random_ascii(w_id_length, charset=w_id_charset)


def __generate_task_file_name():
    """
    Creates a new task file name by creating a string of random ascii
    characters.
    :return: (function call to 'generate_random_ascii')
    """
    return generate_random_ascii(w_id_length, charset=w_id_charset)


def __correct_user_input(configuration, input, required_input=None,
                         allowed_input=None):
    """
    Validates user input against the required_input dictionary and the
    allowed_input dictionary. Checks that all mandatory input is provided by
    the user, and that any additional input is valid. All user inputs are
    checked that they are in the expected format.
    :param configuration: The MiG configuration object.
    :param input: The user provided input to validate.
    :param required_input: dictionary of the required input fields for the
    users input. Format is {parameter: type}.
    :param allowed_input: dictionary of any valid input fields for the users
    input. Format is {parameter: type}.
    :return: (Tuple (boolean, string)) First value will be True if user input
    is valid, with an empty string. If any problems are encountered first
    value with be False with an accompanying error message explaining the
    issue.
    """
    _logger = configuration.logger
    _logger.debug("WP: __correct_user_input verifying user input"
                  " '%s' type '%s'" % (input, type(input)))

    if not isinstance(required_input, dict):
        required_input = {}

    if not isinstance(allowed_input, dict):
        allowed_input = {}

    for key, value in input.items():
        if key not in allowed_input.keys():
            msg = "key: '%s' is not allowed, valid includes '%s'" \
                  % (key, ', '.join(allowed_input.keys()))
            _logger.debug(msg)
            return (False, msg)
        if not isinstance(value, allowed_input.get(key)):
            msg = "value: '%s' has an incorrect type: '%s', requires: '%s'" \
                  % (value, type(value), allowed_input.get(key))
            _logger.info(msg)
            return (False, msg)
    for key in required_input.keys():
        if key not in input:
            msg = "required key: '%s' is missing, required includes: '%s'" \
                  % (key, ', '.join(required_input.keys()))
            _logger.debug(msg)
            return (False, msg)
    return (True, "")


def __strip_input_attributes(workflow_pattern):
    """
    Removes any additional parameters the provided pattern has, that are not
    necessary for a valid pattern within the MiG.
    :param workflow_pattern: A workflow pattern dict.
    :return: (dictionary) The workflow pattern dict, with any superfluous
    keys removed.
    """
    for key in ALL_PATTERN_INPUTS.keys():
        if key not in VALID_PATTERN.keys():
            workflow_pattern.pop(key, None)

    return workflow_pattern


def __correct_persistent_wp(configuration, workflow_pattern):
    """
    Validates that the given workflow_pattern dict is correctly formatted.
    :param configuration: The MiG configuration object.
    :param workflow_pattern: A workflow pattern dict.
    :return: (Tuple (boolean, string)) First value will be True if pattern
    dict is valid, with an empty string. If any problems are encountered the
    first value with be False with an accompanying error message explaining the
    issue.
    """
    _logger = configuration.logger
    contact_msg = "please contact support at %s so that we can help resolve " \
                  "this issue" % configuration.admin_email

    if not workflow_pattern:
        msg = "A workflow pattern was not provided, " + contact_msg
        _logger.error(
            "WP: __correct_wp, workflow_pattern was not set '%s'"
            % workflow_pattern)
        return (False, msg)

    if not isinstance(workflow_pattern, dict):
        msg = "The workflow pattern was incorrectly formatted, " + contact_msg
        _logger.error(
            "WP: __correct_wp, workflow_pattern had an incorrect type '%s'"
            % workflow_pattern)
        return (False, msg)

    msg = "The workflow pattern had an incorrect structure, " + contact_msg
    for key, value in workflow_pattern.items():
        if key not in VALID_PATTERN:
            _logger.error(
                "WP: __correct_wp, workflow_pattern had an incorrect "
                "key '%s', allowed are %s" % (key, VALID_PATTERN.keys()))
            return (False, msg)
        if not isinstance(value, VALID_PATTERN.get(key)):
            _logger.error(
                "WP: __correct_wp, workflow_pattern had an incorrect "
                "value type '%s', on key '%s', valid is '%s'"
                % (type(value), key, VALID_PATTERN[key]))
            return (False, msg)
    return (True, "")


def __correct_persistent_wr(configuration, workflow_recipe):
    """
    Validates that the given workflow_recipe dict is correctly formatted
    :param configuration: The MiG configuration object.
    :param workflow_recipe: A workflow recipe dict.
    :return: (Tuple (boolean, string)) First value will be True if recipe
    dict is valid, with an empty string. If any problems are encountered the
    first value with be False with an accompanying error message explaining the
    issue.
    """

    _logger = configuration.logger
    contact_msg = "please contact support at %s so that we can help resolve " \
                  "this issue" % configuration.admin_email

    if not workflow_recipe:
        msg = "A workflow recipe was not provided, " + contact_msg
        _logger.error(
            "WR: __correct_wr, workflow_recipe was not set %s"
            % workflow_recipe)
        return (False, msg)

    if not isinstance(workflow_recipe, dict):
        msg = "The workflow recipe was incorrectly formatted, " + contact_msg
        _logger.error(
            "WR: __correct_wr, workflow_recipe had an incorrect type %s"
            % workflow_recipe)
        return (False, msg)

    msg = "The workflow recipe had an incorrect structure, " + contact_msg
    for key, value in workflow_recipe.items():
        if key not in VALID_RECIPE:
            _logger.error(
                "WR: __correct_wr, workflow_recipe had an incorrect key %s, "
                "allowed are %s" % (key, VALID_RECIPE.keys()))
            return (False, msg)
        if not isinstance(value, VALID_RECIPE.get(key)):
            _logger.error(
                "WR: __correct_wr, workflow_recipe had an incorrect "
                "value type %s, on key %s, valid is %s"
                % (type(value), key, VALID_RECIPE[key]))
            return (False, msg)
    return (True, '')


def __load_wp(configuration, wp_path):
    """
    Load a workflow pattern from the specified path
    :param configuration: The MiG configuration object.
    :param wp_path: path to an expected workflow pattern.
    :return: (dictionary) The loaded workflow pattern dict. Will be empty if
    no workflow pattern could be loaded from the given path.
    """
    _logger = configuration.logger
    _logger.debug("WP: load_wp, wp_path: %s" % wp_path)

    if not os.path.exists(wp_path):
        _logger.error("WP: %s does not exist" % wp_path)
        return {}

    workflow_pattern = None
    try:
        workflow_pattern = load(wp_path, serializer='json')
    except Exception, err:
        configuration.logger.error('WP: could not open workflow pattern %s %s'
                                   % (wp_path, err))
    if workflow_pattern and isinstance(workflow_pattern, dict):
        # Ensure string type
        workflow_pattern = force_utf8_rec(workflow_pattern)
        correct, _ = __correct_persistent_wp(configuration, workflow_pattern)
        if correct:
            return workflow_pattern
    return {}


def __load_wr(configuration, wr_path):
    """
    Load a workflow recipe from the specified path
    :param configuration: The MiG configuration object.
    :param wr_path: path to an expected workflow recipe.
    :return: (dictionary) The loaded workflow recipe dict. Will be empty if
    no workflow recipe could be loaded from the given path.
    """
    _logger = configuration.logger
    _logger.debug("WR: load_wr, wr_path: %s" % wr_path)

    if not os.path.exists(wr_path):
        _logger.error("WR: %s does not exist" % wr_path)
        return {}

    workflow_recipe = None
    try:
        workflow_recipe = load(wr_path, serializer='json')
    except Exception, err:
        configuration.logger.error('WR: could not open workflow recipe %s %s'
                                   % (wr_path, err))
    if workflow_recipe and isinstance(workflow_recipe, dict):
        # Ensure string type
        workflow_recipe = force_utf8_rec(workflow_recipe)
        correct, _ = __correct_persistent_wr(configuration, workflow_recipe)
        if correct:
            return workflow_recipe
    return {}


def __load_map(configuration, workflow_type=WORKFLOW_PATTERN, do_lock=True):
    """
    Load map of workflow patterns. Uses a pickled dictionary for efficiency.
    :param configuration: The MiG configuration object.
    :param workflow_type: A MiG workflow type.
    :param do_lock: [optional] enable and disable locking during load.
    :return: (dictionary) The system dictionary of the given workflow_type.
    """
    if workflow_type == WORKFLOW_PATTERN:
        return load_system_map(configuration, 'workflowpatterns', do_lock)
    elif workflow_type == WORKFLOW_RECIPE:
        return load_system_map(configuration, 'workflowrecipes', do_lock)


def __refresh_map(configuration, workflow_type=WORKFLOW_PATTERN,
                  client_id=None):
    """
    Refresh map of workflow objects. Uses a pickled dictionary for efficiency.
    Only update map for workflow objects that appeared, disappeared, or have
    changed after last map save.
    NOTE: Save start time so that any concurrent updates get caught next time
    :param configuration: The MiG configuration object.
    :param workflow_type: A MiG workflow type.
    :param client_id: [optional] A MiG user client. Default is None
    :return: (dictionary) The system dictionary of the given workflow_type.
    """
    _logger = configuration.logger
    start_time = time.time()
    _logger.debug("WP: __refresh_map workflow_type: %s, start_time: %s"
                  % (workflow_type, start_time))
    dirty = []

    map_path = ''
    if workflow_type == WORKFLOW_PATTERN:
        map_path = os.path.join(configuration.mig_system_files,
                                'workflowpatterns.map')
    elif workflow_type == WORKFLOW_RECIPE:
        map_path = os.path.join(configuration.mig_system_files,
                                'workflowrecipes.map')
    workflow_map = {}
    # Update the map from disk
    lock_path = map_path.replace('.map', '.lock')
    with open(lock_path, 'a') as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        workflow_map, map_stamp = __load_map(
            configuration, workflow_type, do_lock=False)

        # Find all workflow objects
        all_objects = __list_path(configuration, workflow_type=workflow_type,
                                  client_id=client_id)

        for workflow_dir, workflow_file in all_objects:
            workflow_map[workflow_file] = workflow_map.get(workflow_file, {})
            wp_mtime = os.path.getmtime(os.path.join(workflow_dir,
                                                     workflow_file))
            if CONF not in workflow_map[
                workflow_file] or wp_mtime >= map_stamp:
                workflow_object = ''
                if workflow_type == WORKFLOW_PATTERN:
                    workflow_object = __load_wp(configuration,
                                                os.path.join(workflow_dir,
                                                             workflow_file))
                elif workflow_type == WORKFLOW_RECIPE:
                    workflow_object = __load_wr(configuration,
                                                os.path.join(workflow_dir,
                                                             workflow_file))
                workflow_map[workflow_file][CONF] = workflow_object
                workflow_map[workflow_file][MODTIME] = map_stamp
                dirty.append([workflow_file])

        # Remove any missing workflow patterns from map
        missing_workflow = [workflow_file for workflow_file in
                            workflow_map.keys()
                            if workflow_file not in
                            [_workflow_file for _workflow_path, _workflow_file
                             in all_objects]]

        for workflow_file in missing_workflow:
            del workflow_map[workflow_file]
            dirty.append([workflow_file])

        if dirty:
            try:
                dump(workflow_map, map_path)
                os.utime(map_path, (start_time, start_time))
                _logger.debug('Accessed map and updated to %.10f' % start_time)
            except Exception, err:
                _logger.error('Workflows: could not save map, or %s' % err)
        if workflow_type == WORKFLOW_PATTERN:
            last_refresh[WORKFLOW_PATTERNS] = start_time
        elif workflow_type == WORKFLOW_RECIPE:
            last_refresh[WORKFLOW_RECIPES] = start_time
        fcntl.flock(lock_handle, fcntl.LOCK_UN)
    return workflow_map


def __list_path(configuration, workflow_type=WORKFLOW_PATTERN, client_id=None):
    """
    Lists the paths of individual workflow objects.
    :param configuration: The MiG configuration object.
    :param workflow_type: A MiG workflow type.
    :param client_id: [optional] A MiG user id. If provided only the vgrids
    that user has access to will be searched, otherwise all VGrids will be.
    Default is None.
    :return: (list) A list of (string, string) tuples, with one entry for
    each workflow object. First value is the path to that object, second
    value is the system object itself.
    """
    _logger = configuration.logger
    _logger.debug("Workflows: __list_path")

    objects = []
    if client_id:
        vgrid_list = user_vgrid_access(configuration, client_id)
    else:
        vgrid_map = get_vgrid_map(configuration)
        vgrid_list = [vgrid for vgrid in vgrid_map[VGRIDS]]

    for vgrid in vgrid_list:
        home = get_workflow_home(configuration, vgrid, workflow_type)
        if not home:
            # No home, skip to next
            _logger.debug("Workflows: __list_path, vgrid did not have "
                          "dir: '%s' for workflow %s" % (home, workflow_type))
            continue
        dir_content = os.listdir(home)
        for entry in dir_content:
            # Skip dot files/dirs and the write lock
            if entry.startswith('.') or entry == WRITE_LOCK:
                continue
            if os.path.isfile(os.path.join(home, entry)):
                objects.append((home, entry))
            else:
                _logger.warning('WP: %s in %s is not a plain file, '
                                'move it?' % (entry, home))
    return objects


def __query_workflow_map(configuration, client_id=None, first=False,
                         user_query=False, workflow_type=WORKFLOW_PATTERN,
                         **kwargs):
    """
    Gets all objects that a given user has access to according to the
    provided workflow_type. Additional keyword arguments can be provided to
    create a narrower search, where only those objects that match the
    provided arguments and the user has access to are returned.
    :param configuration: The MiG configuration object.
    :param client_id: [optional] The MiG user
    :param first: [optional] boolean. If True will only return the first valid
    workflow object and return that. If false will return all valid objects.
    Default is False.
    :param user_query: [optional] boolean. Flag used to show that query
    originates from user call.
    :param workflow_type: A MiG workflow type.
    :param kwargs: (dictionary) additional arguments that a user may provide
    to narrow their search of the system map to only return a subset of the
    objects they can access.
    :return: (list or dict) If first is False then a list of all matching
    workflow objects are returned. Else only the first match is returned.
    """
    _logger = configuration.logger
    _logger.debug('__query_workflow_map, client_id: %s, '
                  'workflow_type: %s, kwargs: %s' % (client_id, workflow_type,
                                                     kwargs))
    workflow_map = None
    if workflow_type == WORKFLOW_PATTERN:
        workflow_map = get_wp_map(configuration, client_id=client_id)

    if workflow_type == WORKFLOW_RECIPE:
        workflow_map = get_wr_map(configuration, client_id=client_id)

    if workflow_type == WORKFLOW_ANY:
        # Load every type into workflow_map
        workflow_map = get_wr_map(configuration, client_id=client_id)
        workflow_map.update(get_wp_map(configuration, client_id=client_id))

    if not workflow_map:
        _logger.debug("WP: __query_workflow_map, empty map retrieved: '%s'"
                      ", workflow_type: %s" % (workflow_map, workflow_type))
        if first:
            return None
        return []

    if client_id:
        workflow_map = {key: value for key, value in workflow_map.items()
                        if value.get(CONF, None) and 'owner' in value[CONF]
                        and client_id == value[CONF]['owner']}

    matches = []
    for _, workflow in workflow_map.items():
        workflow_conf = workflow.get(CONF, None)
        if not workflow_conf:
            _logger.error('WP: __query_workflow_map, no configuration '
                          'present to build the workflow object from '
                          'workflow %s' % workflow)
            continue

        workflow_obj = __build_workflow_object(configuration,
                                               user_query,
                                               workflow_conf['object_type'],
                                               **workflow_conf)
        _logger.info("WP: __build_workflow_object result '%s'" % workflow_obj)
        if not workflow_obj:
            continue

        # Search with kwargs
        if kwargs:
            match, msg = workflow_match(configuration,
                                        workflow_obj[
                                            workflow_conf['object_type']],
                                        user_query,
                                        **kwargs)
            if match:
                matches.append(workflow_obj[workflow_conf['object_type']])
            else:
                _logger.warning(msg)
        else:
            matches.append(workflow_obj[workflow_conf['object_type']])

    _logger.debug("Matches '%s'" % matches)
    if first:
        if matches:
            return matches[0]
        else:
            return None
    else:
        return matches


def __build_workflow_object(configuration, user_query=False,
                            workflow_type=WORKFLOW_PATTERN, **kwargs):
    """
    Creates a new dict of type workflow, containing a single workflow object
    of the given type, using the provided keyword arguments.
    :param configuration: The MiG configuration object.
    :param user_query: [optional] Boolean marking if the original query came
    from a user request. Default is False.
    :param workflow_type: A MiG workflow type.
    :param kwargs: (dictionary) arguments used to create the specified
    workflow object
    :return: (dictionary) A dictionary which itself contains a dictionary of
    the workflow object specified by the provided arguments.
    """
    _logger = configuration.logger
    workflow = {}
    if workflow_type == WORKFLOW_PATTERN:
        workflow_pattern, _ = __build_wp_object(configuration, user_query,
                                                **kwargs)
        if workflow_pattern:
            workflow.update({WORKFLOW_PATTERN: workflow_pattern})

    if workflow_type == WORKFLOW_RECIPE:
        workflow_recipe, _ = __build_wr_object(configuration, user_query,
                                               **kwargs)
        if workflow_recipe:
            workflow.update({WORKFLOW_RECIPE: workflow_recipe})

    if workflow:
        workflow['object_type'] = 'workflow'
    return workflow


def __build_wp_object(configuration, user_query=False, **kwargs):
    """
    Build a workflow pattern object based on keyword arguments.
    :param configuration: The MiG configuration object.
    :param user_query: [optional] Boolean marking if the original query came
    from a user request. If this is a user request then system keys are
    removed from the returned object. Default is False.
    :param kwargs: (dictionary) arguments used to create a workflow pattern
    dictionary.
    :return: (Tuple (boolean or dict, string)) if workflow pattern dict is
    successfully created it is returned as the first value, along with an empty
    string. If a problem is encountered then the first value is False and an
    accompanying error message is provided.
    """
    _logger = configuration.logger
    _logger.debug("WP: __build_wp_object, kwargs: %s" % kwargs)
    correct, msg = __correct_persistent_wp(configuration, kwargs)
    if not correct:
        return (False, msg)

    wp_obj = {
        'object_type': kwargs.get('object_type', WORKFLOW_PATTERN),
        'persistence_id': kwargs.get('persistence_id',
                                     VALID_PATTERN['persistence_id']()),
        'owner': kwargs.get('owner', VALID_PATTERN['owner']()),
        'vgrid': kwargs.get('vgrid', VALID_PATTERN['vgrid']()),
        'name': kwargs.get('name', VALID_PATTERN['name']()),
        'input_file': kwargs.get('input_file', VALID_PATTERN['input_file']),
        'output': kwargs.get('output', VALID_PATTERN['output']()),
        'trigger_recipes': kwargs.get('trigger_recipes',
                                      VALID_PATTERN['trigger_recipes']()),
        'variables': kwargs.get('variables', VALID_PATTERN['variables']()),
        'parameterize_over': kwargs.get('parameterize_over',
                                        VALID_PATTERN['parameterize_over']()),
        'input_paths': kwargs.get('input_paths',
                                  VALID_PATTERN['input_paths']())
    }

    if user_query:
        wp_obj.pop('owner', None)
    return (wp_obj, "")


def __build_wr_object(configuration, user_query=False, **kwargs):
    """
    Build a workflow recipe object based on keyword arguments.
    :param configuration: The MiG configuration object.
    :param user_query: [optional] Boolean marking if the original query came
    from a user request. If this is a user request then system keys are
    removed from the returned object. Default is False.
    :param kwargs: (dictionary) arguments used to create a workflow recipe
    dictionary.
    :return: (Tuple (boolean or dict, string)) if workflow recipe dict is
    successfully created it is returned as the first value, along with an empty
    string. If a problem is encountered then the first value is False and an
    accompanying error message is provided.
    """
    _logger = configuration.logger
    _logger.debug("WR: __build_wr_object, kwargs: %s" % kwargs)
    correct, msg = __correct_persistent_wr(configuration, kwargs)
    if not correct:
        return (False, msg)

    wr_obj = {
        'object_type': kwargs.get('object_type', WORKFLOW_RECIPE),
        'persistence_id': kwargs.get('persistence_id',
                                     VALID_RECIPE['persistence_id']()),
        'owner': kwargs.get('owner', VALID_RECIPE['owner']()),
        'vgrid': kwargs.get('vgrid', VALID_RECIPE['vgrid']()),
        'name': kwargs.get('name', VALID_RECIPE['name']()),
        'recipe': kwargs.get('recipe', VALID_RECIPE['recipe']()),
        'task_file': kwargs.get('task_file', VALID_RECIPE['task_file']()),
        'source': kwargs.get('source', VALID_RECIPE['source']())
    }

    if user_query:
        wr_obj.pop('owner', None)
        wr_obj.pop('associated_patterns', None)

    return (wr_obj, "")


def init_workflow_home(configuration, vgrid, workflow_type=WORKFLOW_PATTERN):
    """
    Creates directories in which to save workflow object data.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid
    :param workflow_type: The MiG workflow type.
    :return: (Tuple (boolean, string)) The first value is True if the required
    directory has been created or already exists, and is False if it cannot be
    created. If False, then an accompanying error message is provided in the
    second value.
    """
    vgrid_path = os.path.join(configuration.vgrid_home, vgrid)
    if not os.path.exists(vgrid_path):
        return (False, "vgrid: '%s' doesn't exist" % vgrid_path)

    path = None
    if workflow_type == WORKFLOW_PATTERN:
        path = os.path.join(vgrid_path,
                            configuration.workflows_vgrid_patterns_home)
    elif workflow_type == WORKFLOW_RECIPE:
        path = os.path.join(vgrid_path,
                            configuration.workflows_vgrid_recipes_home)

    if not path:
        return (False, "Failed to setup init workflow home '%s' in vgrid '%s'"
                % (workflow_type, vgrid_path))

    if not os.path.exists(path) and not makedirs_rec(path, configuration):
        return (False, "Failed to init workflow home: '%s'" % path)

    os.chmod(path, 0750)
    return (True, '')


def get_workflow_home(configuration, vgrid, workflow_type=WORKFLOW_PATTERN):
    """
    Gets the path of the containing directory for a specified MiG workflow type
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid
    :param workflow_type: The MiG workflow type.
    :return: (string) directory path
    """
    if workflow_type == WORKFLOW_RECIPE:
        return get_workflow_recipe_home(configuration, vgrid)
    return get_workflow_pattern_home(configuration, vgrid)


def get_workflow_pattern_home(configuration, vgrid):
    """
    Returns the path of the directory storing patterns for a given vgrid.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid.
    :return: (string or boolean) the pattern directory path or False if the
    path does not exist.
    """
    _logger = configuration.logger
    vgrid_path = os.path.join(configuration.vgrid_home, vgrid)
    if not os.path.exists(vgrid_path):
        _logger.warning("WP: vgrid '%s' doesn't exist" % vgrid_path)
        return False
    pattern_home = os.path.join(vgrid_path,
                                configuration.workflows_vgrid_patterns_home)
    if not os.path.exists(pattern_home):
        return False
    return pattern_home


def get_workflow_recipe_home(configuration, vgrid):
    """
    Returns the path of the directory storing recipes for a given vgrid.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid.
    :return: (string or boolean) the recipe directory path or False if the
    path does not exist.
    """
    _logger = configuration.logger

    vgrid_path = os.path.join(configuration.vgrid_home, vgrid)
    if not os.path.exists(vgrid_path):
        _logger.warning("WR: vgrid '%s' doesn't exist" % vgrid_path)
        return False

    recipe_home = os.path.join(vgrid_path,
                               configuration.workflows_vgrid_recipes_home)
    if not os.path.exists(recipe_home):
        return False
    return recipe_home


def init_workflow_task_home(configuration, vgrid):
    """
    Returns the path of the directory storing tasks for a given vgrid.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid.
    :return: (string or boolean) the tasks directory path or False if the
    path does not exist.
    """
    _logger = configuration.logger
    vgrid_path = os.path.join(configuration.vgrid_files_home, vgrid)
    if not os.path.exists(vgrid_path):
        _logger.warning("vgrid '%s' doesn't exist" % vgrid_path)
        return (False, '')

    task_home = os.path.join(vgrid_path,
                             configuration.workflows_vgrid_tasks_home)
    if not task_home:
        return (False, "Failed to setup tasks workflow home '%s' in grid '%s'"
                % (task_home, vgrid_path))

    if not os.path.exists(task_home) and \
            not makedirs_rec(task_home, configuration):
        return (False, "Failed to init workflow task home: '%s'" % task_home)

    _logger.debug("Created or found workflow_task_home '%s'" % task_home)
    # TODO. Ensure correct permissions.
    os.chmod(task_home, 0750)
    return (True, '')


def get_workflow_task_home(configuration, vgrid):
    """
    Returns the path of the directory storing tasks for a given vgrid.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid.
    :return: (string or boolean) the task directory path or False if the
    path does not exist.
    """
    vgrid_path = os.path.join(configuration.vgrid_files_home, vgrid)
    task_home = os.path.join(vgrid_path,
                             configuration.workflows_vgrid_tasks_home)
    if not os.path.exists(task_home):
        return False
    return task_home


def get_wp_map(configuration, client_id=None):
    """
    Returns the current map of workflow patterns. Caches the map for load
    prevention with repeated calls within a short time span.
    :param configuration: The MiG configuration object.
    :param client_id: [optional] A MiG user id.
    :return: (dictionary) all currently registered workflow patterns. Format
    is {pattern persistence id: pattern dict}.
    """
    _logger = configuration.logger
    modified_patterns, _ = check_workflow_p_modified(configuration)
    _logger.info("get_wp_map - modified_patterns: %s " % modified_patterns)

    if modified_patterns:
        map_stamp = time.time()
        workflow_p_map = __refresh_map(configuration, client_id=client_id)
        reset_workflow_p_modified(configuration)
    else:
        workflow_p_map, map_stamp = __load_map(configuration)
    last_map[WORKFLOW_PATTERNS] = workflow_p_map
    last_refresh[WORKFLOW_PATTERNS] = map_stamp
    last_load[WORKFLOW_PATTERNS] = map_stamp
    _logger.debug("WP: got: '%s' map" % workflow_p_map)
    return workflow_p_map


def get_wr_map(configuration, client_id=None):
    """
    Returns the current map of workflow recipes. Caches the map for load
    prevention with repeated calls within a short time span.
    :param configuration: The MiG configuration object.
    :param client_id: [optional] A MiG user id.
    :return: (dictionary) all currently registered workflow recipes. Format
    is {recipe persistence id: recipe dict}.
    """
    _logger = configuration.logger
    modified_recipes, _ = check_workflow_r_modified(configuration)
    _logger.info("get_wr_map - modified_recipes: %s " % modified_recipes)

    if modified_recipes:
        map_stamp = time.time()
        workflow_r_map = __refresh_map(configuration,
                                       workflow_type=WORKFLOW_RECIPE,
                                       client_id=client_id)
        reset_workflow_r_modified(configuration)
    else:
        workflow_r_map, map_stamp = __load_map(configuration,
                                               workflow_type=WORKFLOW_RECIPE)
    last_map[WORKFLOW_RECIPES] = workflow_r_map
    last_refresh[WORKFLOW_RECIPES] = map_stamp
    last_load[WORKFLOW_RECIPES] = map_stamp
    _logger.debug("WR: got: '%s' map" % workflow_r_map)
    return workflow_r_map


def get_workflow_with(configuration, client_id=None, first=False,
                      user_query=False, workflow_type=WORKFLOW_PATTERN,
                      **kwargs):
    """
    Searches workflow object databases for objects that match the provided
    keyword arguments.
    :param configuration: The MiG configuration object.
    :param client_id: [optional] A MiG user
    :param first: [optional] If True will return the first matching workflow
    object, else will return all matching workflow objects in a list. Default
    is False
    :param user_query: [optional] Boolean showing if function call originates
    from user call or not.
    :param workflow_type: A MiG workflow object type.
    :param kwargs: keyword arguments used to narrow search of workflow objects.
    :return: (None or function call to '__query_workflow_map') Will call
    '__query_workflow_map', unless a problem is encountered with input
    arguments, in which case will return None.
    """
    _logger = configuration.logger
    _logger.debug('get_workflow_with, first: %s, client_id: %s,'
                  ' workflow_type: %s, kwargs: %s' %
                  (first, client_id, workflow_type, kwargs))
    if workflow_type not in WORKFLOW_TYPES:
        _logger.error('get_workflow_with, invalid workflow_type: %s '
                      'provided' % workflow_type)
        return None
    if not isinstance(kwargs, dict):
        _logger.error('wrong format supplied for %s', type(kwargs))
        return None

    return __query_workflow_map(configuration, client_id, first,
                                user_query, workflow_type, **kwargs)


def create_workflow(configuration, client_id, workflow_type=WORKFLOW_PATTERN,
                    **kwargs):
    """
    Creates a new workflow object using the provided keyword arguments.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user
    :param workflow_type: The MiG workflow object type which will now be
    created.
    :param kwargs: keyword arguments used to define the state of the new
    workflow object
    :return: (Tuple(boolean, string) or function call to
    '__create_workflow_recipe_entry', or '__create_workflow_pattern_entry') If
    any problems are encountered with provided arguments a tuple will be return
    with the first value being the boolean False, and the second value being
    an error messsage. If there are no issues then the appropriate workflow
    object creation function is called.
    """
    _logger = configuration.logger
    vgrid = kwargs.get('vgrid', None)
    if not vgrid:
        msg = "A workflow create dependency was missing: 'vgrid'"
        _logger.error("create_workflow: 'vgrid' was not set: '%s'" % vgrid)
        return (False, msg)

    persistence_id = kwargs.get('persistence_id', None)
    if persistence_id:
        msg = "'persistence_id' cannot be manually set by a user. Are " \
              "you intending to update an existing pattern instead? "
        _logger.info("persistence_id provided by user. Aborting creation")
        return (False, msg)
    object_type = kwargs.get('object_type', None)
    if object_type:
        msg = "'object_type' cannot be manually set by a user. "
        _logger.info("object_type provided by user. Aborting creation")
        return (False, msg)

    if vgrid:
        # User is vgrid owner or member
        success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                                 configuration)
        if not success:
            return (False, msg)

    if workflow_type == WORKFLOW_RECIPE:
        return __create_workflow_recipe_entry(configuration, client_id,
                                              vgrid, kwargs)

    return __create_workflow_pattern_entry(configuration, client_id,
                                           vgrid, kwargs)


# def workflow_action(configuration, client_id, workflow_type=MANUAL_TRIGGER,
#                     **kwargs):
#     """ """
#     _logger = configuration.logger
#     vgrid = kwargs.get('vgrid', None)
#     if not vgrid:
#         msg = "A workflow create dependency was missing: 'vgrid'"
#         _logger.error("create_workflow: 'vgrid' was not set: '%s'" % vgrid)
#         return (False, msg)
#
#     if workflow_type == MANUAL_TRIGGER:
#         return __manual_trigger(configuration, client_id, vgrid, kwargs)
#     if workflow_type == CANCEL_JOB:
#         job_id = kwargs.get('JOB_ID', None)
#         if not job_id:
#             msg = "A job cancellation dependency was missing: 'JOB_ID'"
#             _logger.error(msg)
#             return (False, msg)
#
#         return __cancel_job_by_id(configuration, job_id, client_id)
#     if workflow_type == RESUBMIT_JOB:
#         return (False, "Implementation under way")
#     return (False, "Unsupported action '%s'" % workflow_type)


def delete_workflow(configuration, client_id, workflow_type=WORKFLOW_PATTERN,
                    **kwargs):
    """
    Deletes the specified workflow object.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user
    :param workflow_type: The MiG workflow object type which will now be
    deleted.
    :param kwargs: keyword arguments identifiying the workflow objects to be
    deleted. These should be the containing VGrid and the objects
    persistence_id.
    :return: (Tuple(boolean, string) or function call to
    'delete_workflow_recipe', or 'delete_workflow_pattern') If the necessary
    keyword arguments are invalid then a tuple will be returned with the first
    value being False, and the second being an error message. If no problems
    are encountered then the appropriate workflow object deletion function
    will be called.
    """
    _logger = configuration.logger
    vgrid = kwargs.get('vgrid', None)
    if not vgrid:
        msg = "A workflow removal dependency was missing: 'vgrid'"
        _logger.error("delete_workflow: 'vgrid' was not set %s" % vgrid)
        return (False, msg)

    persistence_id = kwargs.get('persistence_id', None)
    if not persistence_id:
        msg = "A workflow removal dependency was missing: 'persistence_id'"
        _logger.error("delete_workflow: 'persistence_id' was not set %s" %
                      persistence_id)
        return (False, msg)

    if vgrid:
        # User is vgrid owner or member
        success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                                 configuration)
        if not success:
            return (False, msg)

    if workflow_type == WORKFLOW_RECIPE:
        return delete_workflow_recipe(configuration, client_id, vgrid,
                                      persistence_id)
    return delete_workflow_pattern(configuration, client_id,
                                   vgrid, persistence_id)


def update_workflow(configuration, client_id, workflow_type=WORKFLOW_PATTERN,
                    **kwargs):
    """
    Updates the record of a workflow object using newly provide arguments.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user
    :param workflow_type: The MiG workflow object type which will now be
    deleted.
    :param kwargs: keyword arguments identifying the workflow objects to be
    updated, and defining the new object state. Any object argument keywords
    not present in the kwargs will not be altered.
    :return: (Tuple(boolean, string) or function call to
    '__update_workflow_recipe', or '__update_workflow_pattern') If the
    necessary keyword arguments are invalid then a tuple will be returned with
    the first value being False, and the second being an error message. If no
    problems are encountered then the appropriate workflow object update
    function will be called.
    """
    _logger = configuration.logger
    vgrid = kwargs.get('vgrid', None)
    if not vgrid:
        msg = "A workflow update dependency was missing: 'vgrid'"
        _logger.error("update_workflow: 'vgrid' was not set: '%s'" % vgrid)
        return (False, msg)

    persistence_id = kwargs.get('persistence_id', None)
    if not persistence_id:
        msg = "Missing 'persistence_id' must be provided to update " \
              "a workflow object."
        return (False, msg)

    # User is vgrid owner or member
    success, msg, _ = init_vgrid_script_list(vgrid, client_id,
                                             configuration)
    if not success:
        return (False, msg)

    if workflow_type == WORKFLOW_RECIPE:
        return __update_workflow_recipe(configuration, client_id, vgrid,
                                        kwargs)

    return __update_workflow_pattern(configuration, client_id, vgrid,
                                     kwargs)


def delete_workflow_pattern(configuration, client_id, vgrid, persistence_id):
    """
    Deletes a workflow pattern object.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user.
    :param vgrid: The VGrid containg the workflow pattern.
    :param persistence_id: The persistence_id of the workflow pattern to be
    deleted.
    :return: (Tuple(boolean, string) or function call to '__delete_workflow')
    If provided arguments are invalid, or something goes wrong with deletion
    will return a Tuple with the first value being the boolean False, and the
    second value being an error message. If no problems are encountered then
    the function '__delete_workflow' will be called.
    """

    _logger = configuration.logger
    _logger.debug("WP: delete_workflow_pattern, client_id: %s, "
                  "persistence_id: %s" % (client_id, persistence_id))

    workflow = get_workflow_with(configuration,
                                 client_id,
                                 workflow_type=WORKFLOW_PATTERN,
                                 first=True, vgrid=vgrid,
                                 persistence_id=persistence_id)

    if not workflow:
        return (False, "Could not find pattern with persistence_id: '%s' "
                       "to delete" % persistence_id)

    _logger.debug("WP: delete_workflow_pattern, vgrid '%s',"
                  "persistence_id '%s'" % (vgrid, persistence_id))

    for rule_id, _ in workflow['trigger_recipes'].items():
        deleted, _ = delete_workflow_trigger(configuration, vgrid, rule_id)
        if not deleted:
            return (False, "Failed to cleanup trigger before deleting '%s'" %
                    persistence_id)

    if not __delete_task_parameter_file(configuration, vgrid, workflow):
        return (False, "Failed to remove the patterns parameter configuration")

    return __delete_workflow(configuration, client_id, vgrid, persistence_id,
                             workflow_type=WORKFLOW_PATTERN)


def delete_workflow_recipe(configuration, client_id, vgrid, persistence_id):
    """
    Deletes a workflow recipe object.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user.
    :param vgrid: The VGrid containg the workflow recipe.
    :param persistence_id: The persistence_id of the workflow recipe to be
    deleted.
    :return: (Tuple(boolean, string) or function call to '__delete_workflow')
    If provided arguments are invalid, or something goes wrong with deletion
    will return a Tuple with the first value being the boolean False, and the
    second value being an error message. If no problems are encountered then
    the function '__delete_workflow' will be called.
    """
    _logger = configuration.logger
    _logger.debug("WR: delete_workflow_recipe:, client_id: %s, "
                  "persistence_id: %s" % (client_id, persistence_id))

    workflow = get_workflow_with(configuration, client_id, first=True,
                                 workflow_type=WORKFLOW_RECIPE,
                                 persistence_id=persistence_id)

    if not workflow:
        return (False, "Could not find recipe with persistence_id '%s'"
                       " to delete" % persistence_id)

    # Delete the associated task file
    deleted, msg = delete_workflow_task_file(configuration, vgrid,
                                             workflow['task_file'])
    if not deleted:
        return (False, msg)

    return __delete_workflow(configuration, client_id, vgrid, persistence_id,
                             workflow_type=WORKFLOW_RECIPE)


def __save_workflow(configuration, vgrid, workflow,
                    workflow_type=WORKFLOW_PATTERN, overwrite=False):
    """
    Saves a workflow object to disk. Will also mark that the object has been
    modified so that the storing map will be reloaded when next called.
    :param configuration: The MiG configuration object.
    :param vgrid: The VGrid to which data is to be saved.
    :param workflow: The workflow object to be saved.
    :param workflow_type: The Mig workflow object type.
    :param overwrite: [optional] boolean value denoting if the save process
    should overwrite existing saved data or not. Default is False.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful saving, and False showing
    that a problem has been encountered. If a problem is encountered the
    second value is an explanatory error message, else it is an empty string.
    """
    _logger = configuration.logger

    home = get_workflow_home(configuration, vgrid, workflow_type)

    if not home:
        if not makedirs_rec(home, configuration):
            msg = "Couldn't create the required dependencies for " \
                  "your '%s'" % workflow_type
            _logger.error(msg)
            return (False, msg)

    file_path = os.path.join(home, workflow['persistence_id'])
    if not overwrite:
        if os.path.exists(file_path):
            _logger.error('WP: unique filename conflict: %s '
                          % file_path)
            msg = 'A workflow save conflict was encountered, '
            'please try and resubmit the workflow'
            return (False, msg)
    else:
        if not delete_file(file_path, _logger):
            msg = "Failed to cleanup existing workflow file: '%s'" \
                  "for overwrite" % file_path
            _logger.error(msg)
            return (False, msg)

    # Save the pattern
    wrote = False
    msg = ''
    try:
        dump(workflow, file_path, serializer='json')
        mod_update_time = time.time()
        # Mark as modified
        if workflow_type == WORKFLOW_PATTERN:
            mark_workflow_p_modified(configuration, workflow['persistence_id'])
        if workflow_type == WORKFLOW_RECIPE:
            mark_workflow_r_modified(configuration, workflow['persistence_id'])
        # Ensure that the modification time is set to a value after
        # `start_time` defined by __refresh_map which is called by
        # get_workflow_with
        os.utime(file_path, (mod_update_time, mod_update_time))
        wrote = True
        _logger.debug("WP: new '%s' saved: '%s'."
                      % (workflow_type, workflow['persistence_id']))
    except Exception, err:
        _logger.error(
            "WP: failed to write: '%s' to disk: '%s'" % (file_path, err))
        msg = 'Failed to save your workflow, please try and resubmit it'

    if not wrote:
        # Ensure that the failed write does not stick around
        if not delete_file(file_path, _logger):
            msg += '\n Failed to cleanup after a failed workflow creation'
        _logger.error(msg)
        return (False, msg)
    return (True, "")


def __delete_workflow(configuration, client_id, vgrid, persistence_id,
                      workflow_type=WORKFLOW_PATTERN):
    """
    Delete a workflow object from disk. Will also mark that the object has been
    removed so that the storing map will be reloaded when next called.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user.
    :param vgrid: The VGrid from which data is to be deleted.
    :param persistence_id: The identifying characteristic of the workflow
    object to be deleted.
    :param workflow_type: A MiG workflow object type.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful deletion, and False showing
    that a problem has been encountered. If a problem is encountered the
    second value is an explanatory error message, else it is the
    persistence_id of the deleted object.
    """
    _logger = configuration.logger
    _logger.debug("__delete_workflow:, client_id: %s, "
                  "persistence_id: %s" % (client_id, persistence_id))

    workflow = get_workflow_with(configuration, client_id,
                                 workflow_type=workflow_type,
                                 user_query=True, first=True,
                                 vgrid=vgrid,
                                 persistence_id=persistence_id)

    if not workflow:
        msg = "A '%s' with persistence_id: '%s' was not found " \
              % (workflow_type, persistence_id)
        _logger.error("__delete_workflow: '%s' wasn't found" % persistence_id)
        return (False, msg)

    workflow_home = get_workflow_home(configuration, vgrid,
                                      workflow_type=workflow_type)

    if not workflow_home:
        return (False, "__delete_workflow: Could not delete: "
                       "'%s' path doesn't exist" % persistence_id)

    workflow_path = os.path.join(workflow_home, persistence_id)
    if os.path.exists(workflow_path):
        if not delete_file(workflow_path, _logger):
            msg = "Could not delete: '%s'" % persistence_id
            return (False, msg)

    if workflow_type == WORKFLOW_PATTERN:
        mark_workflow_p_modified(configuration, persistence_id)
    if workflow_type == WORKFLOW_RECIPE:
        mark_workflow_r_modified(configuration, persistence_id)

    return (True, "%s" % persistence_id)


def __create_workflow_pattern_entry(configuration, client_id, vgrid,
                                    workflow_pattern):
    """
    Creates a workflow pattern based on the passed workflow_pattern object.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user.
    :param vgrid: A MiG VGrid.
    :param workflow_pattern: A dict defining the workflow pattern object.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful pattern creation, and False
    showing that a problem has been encountered. If a problem is encountered
    the second value is an explanatory error message, else it is the
    persistence_id of the created pattern.
    """
    _logger = configuration.logger
    _logger.debug("WP: __create_workflow_pattern_entry, client_id: %s,"
                  " workflow_pattern: %s" % (client_id, workflow_pattern))

    if not isinstance(workflow_pattern, dict):
        _logger.error("WP: __create_workflow_pattern_entry, incorrect "
                      "'workflow_pattern' structure '%s'"
                      % type(workflow_pattern))
        return (False, "Internal server error due to incorrect pattern "
                       "structure")

    correct_input, msg = __correct_user_input(configuration, workflow_pattern,
                                              REQUIRED_PATTERN_INPUTS,
                                              ALL_PATTERN_INPUTS)
    if not correct_input:
        return (False, msg)

    success, msg, _ = init_vgrid_script_list(vgrid, client_id, configuration)
    if not success:
        return (False, msg)

    # If pattern folder doesn't exist, create it.
    if not get_workflow_pattern_home(configuration, vgrid):
        created, msg = init_workflow_home(configuration, vgrid,
                                          WORKFLOW_PATTERN)
        if not created:
            return (False, msg)

    existing_pattern = get_workflow_with(configuration,
                                         workflow_type=WORKFLOW_PATTERN,
                                         vgrid=vgrid,
                                         name=workflow_pattern['name'])
    if existing_pattern:
        msg = "An existing pattern in vgrid '%s' already exist with name " \
              "'%s'" % (vgrid, workflow_pattern['name'])
        _logger.info(msg)
        return (False, msg)

    persistence_id = __generate_persistence_id()
    workflow_pattern['object_type'] = WORKFLOW_PATTERN
    workflow_pattern['persistence_id'] = persistence_id
    workflow_pattern['owner'] = client_id
    workflow_pattern['trigger_recipes'] = {}

    # Create a trigger of each associated input path with an empty `template`
    for path in workflow_pattern['input_paths']:
        trigger, msg = create_workflow_trigger(configuration, client_id, vgrid,
                                               path)
        if not trigger:
            return (False, msg)

        workflow_pattern['trigger_recipes'].update({trigger['rule_id']: {}})

    # Find existing recipes with the specified names
    recipes = {}
    for recipe_name in workflow_pattern.get('recipes', []):
        recipe = get_workflow_with(configuration,
                                   workflow_type=WORKFLOW_RECIPE,
                                   first=True,
                                   vgrid=vgrid,
                                   name=recipe_name)
        if recipe:
            recipes[recipe['persistence_id']] = recipe
        else:
            recipes[recipe_name] = {}

    if recipes:
        # Associate the pattern trigger with the specified recipes
        workflow_pattern['trigger_recipes'].update({
            rule_id: recipes
            for rule_id, _ in workflow_pattern['trigger_recipes'].items()})

        # Update each trigger to associate recipe['recipe'] as the template
        # if the recipe existed already
        recipe_triggers = []
        created, msg = init_workflow_task_home(configuration, vgrid)
        if not created:
            return (False, msg)

        parameter_path = get_task_parameter_path(configuration, vgrid,
                                                 workflow_pattern,
                                                 relative=True)
        if not parameter_path:
            msg = "A valid task parameter path could not be found"
            _logger.error(msg)
            return (False, msg)

        for rule_id, recipes in workflow_pattern['trigger_recipes'].items():
            trigger, _ = get_workflow_trigger(configuration, vgrid, rule_id)
            _logger.info("Associating recipes: '%s' with trigger: '%s'"
                         % (recipes, trigger))
            if trigger:
                templates = []
                for recipe_id, recipe in recipes.items():
                    if recipe:
                        template = __prepare_recipe_template(
                            configuration, vgrid, recipe, parameter_path)
                        if template:
                            templates.append(template)

                if templates:
                    trigger['templates'] = templates
                    recipe_triggers.append(trigger)

        for trigger in recipe_triggers:
            updated, msg = update_workflow_trigger(configuration,
                                                   vgrid, trigger)
            if not updated:
                _logger.warning("Failed to associate recipe"
                                "triggers to pattern err: '%s'" % msg)
                return (False, "Failed to associate recipe to pattern")

    # Associate additional optional arguments
    workflow_pattern = __strip_input_attributes(workflow_pattern)

    pattern, msg = __build_wp_object(configuration, **workflow_pattern)
    if not pattern:
        _logger.info(msg)
        return (False, msg)

    # Create a parameter file based on the pattern
    created, msg = __create_task_parameter_file(configuration, vgrid, pattern)
    if not created:
        _logger.warning(msg)
        return (False, msg)

    saved, msg = __save_workflow(configuration, vgrid, pattern,
                                 workflow_type=WORKFLOW_PATTERN)
    if not saved:
        _logger.warning(msg)
        return (False, msg)

    return (True, "%s" % pattern['persistence_id'])


def __create_workflow_recipe_entry(configuration, client_id, vgrid,
                                   workflow_recipe):
    """
    Creates a workflow recipe based on the passed workflow_recipe object.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user.
    :param vgrid: A MiG VGrid.
    :param workflow_recipe: A dict defining the workflow recipe object.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful recipe creation, and False
    showing that a problem has been encountered. If a problem is encountered
    the second value is an explanatory error message, else it is the
    persistence_id of the created recipe.
    """
    _logger = configuration.logger
    _logger.debug(
        "WR: __create_workflow_recipe_entry, client_id: %s,"
        "workflow_recipe: %s" % (client_id, workflow_recipe))

    if not isinstance(workflow_recipe, dict):
        _logger.error(
            "WR: __create_workflow_recipe_entry, incorrect 'workflow_recipe' "
            "structure '%s'" % type(workflow_recipe))
        return (False, "Internal server error due to incorrect recipe "
                       "structure")

    correct_input, msg = __correct_user_input(configuration,
                                              workflow_recipe,
                                              REQUIRED_RECIPE_INPUTS,
                                              ALL_RECIPE_INPUTS)
    if not correct_input:
        return (False, msg)

    # If recipe folder doesn't exist, create it.
    if not get_workflow_recipe_home(configuration, vgrid):
        created, msg = init_workflow_home(configuration, vgrid,
                                          WORKFLOW_RECIPE)
        if not created:
            return (False, msg)

    persistence_id = __generate_persistence_id()
    workflow_recipe['object_type'] = WORKFLOW_RECIPE
    workflow_recipe['persistence_id'] = persistence_id
    workflow_recipe['owner'] = client_id
    workflow_recipe['vgrid'] = vgrid

    correct, msg = __correct_persistent_wr(configuration, workflow_recipe)
    if not correct:
        return (False, msg)

    # Verify that the recipe name is unique
    # Need this to ensure reasonable user friendliness of connecting recipes
    existing_recipe = get_workflow_with(configuration,
                                        workflow_type=WORKFLOW_RECIPE,
                                        vgrid=vgrid,
                                        name=workflow_recipe['name'])
    if existing_recipe:
        return (False, "An existing recipe in vgrid '%s'"
                       " already exist with name '%s'" % (
                        vgrid, workflow_recipe['name']))

    # Create an associated task file that contains the code to be executed
    converted, source_code = convert_to(configuration,
                                        workflow_recipe['recipe'])
    if not converted:
        return (False, source_code)

    wrote, msg_file_name = create_workflow_task_file(configuration, vgrid,
                                                     source_code)
    if not wrote:
        return (False, msg_file_name)
    workflow_recipe['task_file'] = msg_file_name

    recipe, msg = __build_wr_object(configuration, **workflow_recipe)
    if not recipe:
        _logger.info(msg)
        return (False, msg)

    saved, msg = __save_workflow(configuration, vgrid, recipe,
                                 workflow_type=WORKFLOW_RECIPE)
    if not saved:
        _logger.warning(msg)
        return (False, msg)

    registered, msg = __register_recipe(configuration, client_id, vgrid,
                                        recipe)
    if not registered:
        return (False, msg)

    return (True, "%s" % workflow_recipe['persistence_id'])


def __update_workflow_pattern(configuration, client_id, vgrid,
                              workflow_pattern, required_input=None,
                              allowed_input=None):
    """
    Updates an already registered pattern with new variables. Only the
    variables to be updated are passed to the function. Will automatically
    update appropriate recipe entries if necessary.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user.
    :param vgrid: A MiG VGrid.
    :param workflow_pattern: A dict on new variables to apply to an existing
    pattern. Only values to be updated should be included. Must include the
    persistence_id of the pattern to update.
    :param required_input: [optional] any mandatory arguments required for the
    update. By default this includes the persistence_id.
    :param allowed_input: [optional] any arguments possible to provide on top
    of the required_input. By default is the VALID_USER_UPDATE_PATTERN dict.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful pattern creation, and False
    showing that a problem has been encountered. If a problem is encountered
    the second value is an explanatory error message, else it is the
    persistence_id of the created pattern.
    """
    _logger = configuration.logger
    if not required_input or not isinstance(required_input, dict):
        required_input = {'persistence_id': str}

    if not allowed_input or not isinstance(allowed_input, dict):
        allowed_input = VALID_USER_UPDATE_PATTERN

    if not isinstance(workflow_pattern, dict):
        _logger.error("WP: __update_workflow_pattern, incorrect "
                      "'workflow_pattern' structure '%s'"
                      % type(workflow_pattern))
        return (False, "Internal server error due to incorrect pattern "
                       "structure")

    persistence_id = workflow_pattern.get('persistence_id', None)
    if not persistence_id:
        msg = "Missing 'persistence_id' must be provided to update " \
              "a workflow object."
        _logger.error(msg)
        return (False, msg)

    correct_input, msg = __correct_user_input(configuration, workflow_pattern,
                                              required_input=required_input,
                                              allowed_input=allowed_input)
    if not correct_input:
        return (False, msg)

    success, msg, _ = init_vgrid_script_list(vgrid, client_id, configuration)
    if not success:
        return (False, msg)

    pattern = get_workflow_with(configuration,
                                client_id,
                                first=True,
                                workflow_type=WORKFLOW_PATTERN,
                                persistence_id=workflow_pattern[
                                    'persistence_id'],
                                vgrid=vgrid)

    if not pattern:
        msg = "Could not locate pattern '%s'" % persistence_id
        _logger.warning(msg)
        return (False, msg)
    _logger.debug("WP: __update_workflow_pattern, found pattern %s to update"
                  % pattern)

    _logger.debug("__update_workflow_pattern, applying variables: %s"
                  % workflow_pattern)

    if 'input_paths' in workflow_pattern:
        # Remove triggers and associate the newly specified
        existing_paths = []
        for rule_id, recipe in pattern['trigger_recipes'].items():
            trigger, _ = get_workflow_trigger(configuration, vgrid, rule_id)
            if trigger:
                trigger_path = trigger['path']
                existing_paths.append((rule_id, trigger_path))

        # [(rule_id, path)]
        remove_paths = [rule_path for rule_path in existing_paths
                        if rule_path[1] not in workflow_pattern['input_paths']]

        # [path1, path2]
        ep = dict(map(lambda x: x, existing_paths))
        missing_paths = [np for np in workflow_pattern['input_paths']
                         if np not in ep.values()]

        for rule_path in remove_paths:
            deleted, msg = delete_workflow_trigger(configuration, vgrid,
                                                   rule_path[0])
            if not deleted:
                return (False, msg)
            pattern['trigger_recipes'].pop(rule_path[0])

        # Create empty trigger for path
        for path in missing_paths:
            trigger, msg = create_workflow_trigger(configuration, client_id,
                                                   vgrid, path)
            if not trigger:
                return (False, msg)

            pattern['trigger_recipes'].update(
                {trigger['rule_id']: {}})

    if 'recipes' in workflow_pattern:
        existing_recipes = [(recipe['name'], rule_id)
                            if 'name' in recipe
                            else (name_or_id, rule_id)
                            for rule_id, recipes in
                            pattern['trigger_recipes'].items()
                            for name_or_id, recipe in recipes.items()]

        remove_recipes = set([name for name, _ in existing_recipes]) - \
                         set(workflow_pattern['recipes'])
        missing_recipes = set(workflow_pattern['recipes']) - \
                          set([name for name, _ in existing_recipes])

        for name, rule_id in existing_recipes:
            # Remove recipe
            if name in remove_recipes:
                pattern['trigger_recipes'][rule_id].pop(name)

        for name in missing_recipes:
            # Add existing or recipe placeholder
            recipe = get_workflow_with(configuration,
                                       workflow_type=WORKFLOW_RECIPE,
                                       first=True,
                                       vgrid=vgrid,
                                       name=name)
            if recipe:
                pattern['trigger_recipes'][rule_id][
                    recipe['persistence_id']] = recipe
            else:
                pattern['trigger_recipes'][rule_id][name] = {}

        parameter_path = get_task_parameter_path(configuration, vgrid,
                                                 pattern, relative=True)
        recipe_triggers = []
        for rule_id, recipes in pattern['trigger_recipes'].items():
            trigger, _ = get_workflow_trigger(configuration, vgrid, rule_id)
            _logger.info("Associating recipes: '%s' with trigger: '%s'"
                         % (recipes, trigger))
            if trigger:
                templates = []
                for recipe_id, recipe in recipes.items():
                    if recipe:
                        template = __prepare_recipe_template(
                            configuration, vgrid, recipe, parameter_path)
                        if template:
                            templates.append(template)

                if templates:
                    trigger['templates'] = templates
                    recipe_triggers.append(trigger)

        for trigger in recipe_triggers:
            updated, msg = update_workflow_trigger(configuration, vgrid,
                                                   trigger)
            if not updated:
                _logger.warning("Failed to update recipe triggers"
                                " to pattern: '%s'" % msg)
                return (False, "Failed to associate recipe to pattern")

    # Recipes have to be prepared in trigger_recipes before this point
    workflow_pattern = __strip_input_attributes(workflow_pattern)

    for k in pattern.keys():
        if k not in workflow_pattern:
            workflow_pattern[k] = pattern[k]

    prepared_pattern, msg = __build_wp_object(configuration,
                                              **workflow_pattern)
    if not prepared_pattern:
        _logger.debug(msg)
        return (False, msg)

    # Update a parameter file based on the pattern
    updated, msg = __update_task_parameter_file(configuration, vgrid,
                                                prepared_pattern)
    if not updated:
        _logger.warning(msg)

    saved, msg = __save_workflow(configuration, vgrid, prepared_pattern,
                                 workflow_type=WORKFLOW_PATTERN,
                                 overwrite=True)
    if not saved:
        _logger.warning(msg)
        return (False, msg)

    return (True, "%s" % prepared_pattern['persistence_id'])


def __update_workflow_recipe(configuration, client_id, vgrid, workflow_recipe,
                             valid_keys=None):
    """
    Updates an already registered recipe with new variables. Only the
    variables to be updated are passed to the function. Will automatically
    update appropriate pattern entries if necessary.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user.
    :param vgrid: A MiG VGrid.
    :param workflow_recipe:
    :param valid_keys: [optional] any arguments possible to provide for
    updating. By default is the VALID_USER_UPDATE_RECIPE dict.
    :return: (Tuple(boolean, string)) Returns a tuple with the first value
    being a boolean, with True showing successful recipe creation, and False
    showing that a problem has been encountered. If a problem is encountered
    the second value is an explanatory error message, else it is the
    persistence_id of the created recipe.
    """

    _logger = configuration.logger
    _logger.debug("WR: update_workflow_recipe, client_id: %s, recipe: %s"
                  % (client_id, workflow_recipe))

    if not valid_keys or not isinstance(valid_keys, dict):
        valid_keys = VALID_USER_UPDATE_RECIPE

    if not isinstance(workflow_recipe, dict):
        _logger.error(
            "WR: __update_workflow_recipe, incorrect 'workflow_recipe' "
            "structure '%s'" % type(workflow_recipe))
        return (False, "Internal server error due to incorrect recipe "
                       "structure.")

    for key, value in workflow_recipe.items():
        if key not in valid_keys:
            msg = "key: '%s' is not allowed, valid includes '%s'" % \
                  (key, ', '.join(valid_keys.keys()))
            _logger.error(msg)
            return (False, msg)

        if not isinstance(value, valid_keys.get(key)):
            msg = "value: '%s' has an incorrect type: '%s', requires: '%s'" \
                  % (value, type(value), valid_keys.get(key))
            _logger.error(msg)
            return (False, msg)

    persistence_id = workflow_recipe.get('persistence_id', None)
    if not persistence_id:
        msg = "Missing 'persistence_id' must be provided to update " \
              "a workflow object."
        _logger.error(msg)
        return (False, msg)

    recipe = get_workflow_with(configuration,
                               client_id,
                               first=True,
                               workflow_type=WORKFLOW_RECIPE,
                               persistence_id=workflow_recipe[
                                   'persistence_id'],
                               vgrid=vgrid)

    for variable in workflow_recipe.keys():
        recipe[variable] = workflow_recipe[variable]

    recipe, msg = __build_wr_object(configuration, **recipe)
    if not recipe:
        _logger.debug(msg)
        return (False, msg)

    saved, msg = __save_workflow(configuration, vgrid, recipe,
                                 workflow_type=WORKFLOW_RECIPE,
                                 overwrite=True)
    if not saved:
        _logger.warning(msg)
        return (False, msg)

    return (True, "%s" % recipe['persistence_id'])


def workflow_match(configuration, workflow_object, user_query=False, **kwargs):
    """
    Checks if a given workflow object has matching arguments to those provided.
    :param configuration: The MiG configuration object.
    :param workflow_object: The workflow object whose parameters will be
    checked for matches.
    :param user_query: [optional] If True, then a single argument match will
    return True. If False, then all provided kwargs must match for a return of
    True.
    :param kwargs: keyword arguments used to query workflow object. Only the
    keys provided in kwargs are checked against.
    :return: (Tuple (boolean, string)) First value is True if the workflow
    object matches the provided kwargs, and False if not. Second value is an
    appropriate error message if a problem is not encountered and an empty
    string if not.
    """
    _logger = configuration.logger
    _logger.debug("WP: searching '%s' with '%s'" % (workflow_object, kwargs))

    if user_query:
        if 'persistence_id' not in kwargs:
            for _k, _v in kwargs.items():
                if _k in workflow_object:
                    if re.match(kwargs[_k], workflow_object[_k]):
                        return (True, "")
                    if kwargs[_k] in workflow_object[_k]:
                        return (True, "")
        else:
            if kwargs['persistence_id'] == workflow_object['persistence_id']:
                return (True, "")
    else:
        # Exact match for all attributes
        num_matches = 0
        for key, value in kwargs.items():
            if key in workflow_object:
                if workflow_object[key] == value:
                    num_matches += 1
        if num_matches == len(kwargs.keys()):
            return (True, "")
    return (False, "Failed to find an exact matching between '%s' and '%s'"
            % (workflow_object, kwargs))


def __prepare_template(configuration, template, **kwargs):
    """
    Prepares the job mrsl template string.
    :param configuration: The MiG configuration object.
    :param template: Mandatory arguments for a mrsl template. Must contain
    'execute' and 'output_files'
    :param kwargs: Additional input arguments. Currently does nothing.
    :return: (string) The mrsl template as a single string.
    """
    # TODO, add option to provide optional kwargs for RETRIES, MEMORY etc
    _logger = configuration.logger
    _logger.debug("preparing trigger template '%s' with arguments '%s'"
                  % (template, kwargs))

    template['sep'] = src_dst_sep
    required_keys = ['execute', 'output_files']

    for r_key in required_keys:
        if r_key not in kwargs:
            kwargs[r_key] = ''

    # Prepare job executable
    template_mrsl = \
        """
::EXECUTE::
%(execute)s

::OUTPUTFILES::
%(output_files)s%(sep)sjob_output/+JOBID+/%(output_files)s

::RETRIES::
0

::MEMORY::
0

::DISK::
0

::CPUTIME::
0

::CPUCOUNT::
0

::NODECOUNT::
0

::VGRID::
+TRIGGERVGRIDNAME+

::MOUNT::
+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+

::ENVIRONMENT::
LC_ALL=en_US.utf8
PYTHONPATH=+TRIGGERVGRIDNAME+
WORKFLOW_INPUT_PATH=+TRIGGERPATH+

::RUNTIMEENVIRONMENT::
NOTEBOOK_PARAMETERIZER
PAPERMILL
""" % template
    return template_mrsl


def __prepare_recipe_template(configuration, vgrid, recipe,
                              parameter_path=None):
    """
    Makes initial preparations for job mrsl template according to a provided
    recipe.
    :param configuration: The MiG configuration object.
    :param vgrid: A MiG VGrid.
    :param recipe: A workflow recipe used to
    :param parameter_path: [optional] Path to yaml file to be used to
    parameterise the recipe. Default is None.
    :return: (Boolean or function call to '__prepare_template') Will return
    False if no template can be prepared, or calls '__prepare_template'.
    """
    _logger = configuration.logger
    _logger.debug("__prepare_recipe_template %s %s %s"
                  % (vgrid, recipe, parameter_path))

    # Prepare for output notebook
    task_output = "%s_" + recipe['name'] + "_output.ipynb"
    task_output = task_output % "+JOBID+"

    executes = []
    if recipe:
        # Get task path and prepare execute arguments
        exists, task_path = __recipe_get_task_path(
            configuration, vgrid, recipe, relative=True)
        if exists:
            # TODO, Use jupyter kernel to discover the env to execute
            # the task with
            # If parameters, preprocess file file before scheduling
            if parameter_path:
                param_task_path = "+JOBID+_" + os.path.basename(task_path)
                executes.append("${NOTEBOOK_PARAMETERIZER} %s %s -o %s -e" %
                                (task_path, parameter_path, param_task_path))
                executes.append("${PAPERMILL} %s %s" % (param_task_path,
                                                        task_output))
            else:
                executes.append("${PAPERMILL} %s %s" % (task_path,
                                                        task_output))

    if executes:
        # Associate executables as templates to triggers
        template_input = {'execute': '\n'.join(executes),
                          'output_files': task_output}
        return __prepare_template(configuration,
                                  template_input)
    return False


def __register_recipe(configuration, client_id, vgrid, workflow_recipe):
    """
    Registers a recipe within a given VGrid. Will automatically update
    workflow triggers and patterns as necessary.
    :param configuration: The MiG configuration object.
    :param client_id: A MiG user.
    :param vgrid: The MiG VGrid in which the recipe is to be registered.
    :param workflow_recipe: The workflow recipe to be registered.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if recipe is successfully register, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise and empty string.
    """

    _logger = configuration.logger
    patterns = get_workflow_with(configuration,
                                 workflow_type=WORKFLOW_PATTERN,
                                 vgrid=vgrid)

    failed_register = []
    name = workflow_recipe['name']
    for pattern in patterns:
        missing_recipe = [(rule_id, name_or_id)
                          for rule_id, recipes in
                          pattern['trigger_recipes'].items()
                          for name_or_id, recipe in recipes.items()
                          if name_or_id == name]

        updates = []
        if missing_recipe:
            parameter_path = get_task_parameter_path(configuration, vgrid,
                                                     pattern, relative=True)

            for rule_id, recipe_name in missing_recipe:
                trigger, msg = get_workflow_trigger(configuration, vgrid,
                                                    rule_id)
                if not trigger:
                    failed_register.append(recipe_name)
                    continue
                template = __prepare_recipe_template(configuration,
                                                     vgrid, workflow_recipe,
                                                     parameter_path)
                if not template:
                    failed_register.append(recipe_name)
                    continue

                trigger['templates'].append(template)
                updated, _ = update_workflow_trigger(configuration, vgrid,
                                                     trigger)
                if not updated:
                    failed_register.append(recipe_name)
                    continue

                updates.append((rule_id, recipe_name))
                pattern['trigger_recipes'][rule_id][
                    workflow_recipe['persistence_id']] = workflow_recipe
        if updates:
            _ = [pattern['trigger_recipes'][rule_id].pop(recipe_name)
                 for rule_id, recipe_name in updates]
            updated, msg = __update_workflow_pattern(
                configuration, client_id, vgrid, pattern,
                required_input=VALID_PATTERN, allowed_input=VALID_PATTERN)
            if not updated:
                _logger.warning("Failed to update workflow pattern for the "
                                "registered recipe trigger: '%s'" % msg)

    if failed_register:
        return (False, "Failed to register recipes '%s'" % failed_register)

    return (True, "")


def __recipe_get_task_path(configuration, vgrid, recipe, relative=False):
    """
    Gets the path to the appropriate task file from a recipe.
    :param configuration: The MiG configuration object.
    :param vgrid: A MiG VGrid
    :param recipe: The recipe used as a base for the task file.
    :param relative: [optional] boolean showing if returned path should be
    relative to vgrid or not. Default is False.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if task path could be identified, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise the identified path.
    """
    _logger = configuration.logger
    _logger.info("Recipe '%s' loading tasks" % recipe)

    correct, msg = __correct_user_input(configuration, recipe,
                                        {'task_file': str},
                                        VALID_RECIPE)
    if not correct:
        return (False, msg)

    task_home = get_workflow_task_home(configuration, vgrid)
    if not task_home:
        return (False, "Task home: '%s' doesn't exist")

    task_path = os.path.join(task_home, recipe['task_file'])
    if not os.path.exists(task_path):
        return (False, "Could not find task file '%s' for recipe '%s'"
                % (task_path, recipe))

    if relative:
        rel_vgrid_path = configuration.workflows_vgrid_tasks_home
        return (True, os.path.join(vgrid, rel_vgrid_path, recipe['task_file']))

    return (True, task_path)


def reset_workflows(configuration, vgrid=None, client_id=None):
    """
    Either removes all workflow objects from a given VGrid, or all workflow
    objects owned by a given user. One of either vgrid or client_id must be
    provided, and if both are provided the vgrid will be used over the
    client_id.
    :param configuration: The MiG configuration object.
    :param vgrid: [optional] A MiG VGrid to empty. If provided all contents
    will be deleted but the VGrid itself will remain. Default is None.
    :param client_id: [optional] A MiG User to empty. If provided all workflow
    objects owned by the user will be deleted. Default is None.
    :return: (Boolean) True/False based on if all specified VGrid or Client
    data has been deleted.
    """
    _logger = configuration.logger
    _logger.debug("Resetting workflows, vgrid: '%s' client_id: '%s'" %
                  (vgrid, client_id))

    if not vgrid and not client_id:
        return False

    if vgrid:
        workflows = get_workflow_with(configuration,
                                      workflow_type=WORKFLOW_ANY,
                                      vgrid=vgrid)
    else:
        workflows = get_workflow_with(configuration,
                                      workflow_type=WORKFLOW_ANY,
                                      client_id=client_id)
    if not workflows:
        return True

    for workflow in workflows:
        deleted, msg = delete_workflow(configuration, workflow['owner'],
                                       workflow['object_type'], **workflow)
        if not deleted:
            _logger.warning(msg)
            continue
        _logger.debug(msg)

    # Inelegant way of refreshing map
    _ = get_workflow_with(configuration, workflow_type=WORKFLOW_ANY)
    return True


# If we don't want users to combine recipes, then remove this
# functionality as it is just replication of data for no reason
def create_workflow_task_file(configuration, vgrid, source_code,
                              extension='.ipynb'):
    """
    Creates a task file. This is the actual notebook to be run on the
    resource. A new notebook is required as users can potentially combine
    multiple notebooks into one 'super notebook', and may in future define
    recipes not within notebooks.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the task file.
    :param source_code: Notebook definiton code.
    :param extension: File extension used for the task file. Currently only
    'ipynb' is supported. Default is 'ipynb'.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if task file could be created, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise the name of the created file.
    """

    _logger = configuration.logger

    created, msg = init_workflow_task_home(configuration, vgrid)
    if not created:
        return (False, msg)
    task_home = get_workflow_task_home(configuration, vgrid)
    if not task_home:
        msg = "Task home in vgrid: '%s' does not exist" % vgrid
        return (False, msg)
    # placeholder for unique name generation.
    file_name = __generate_task_file_name()
    task_file_path = os.path.join(task_home, file_name)
    while os.path.exists(task_file_path):
        file_name = __generate_task_file_name() + extension
        task_file_path = os.path.join(task_home, file_name)

    wrote = write_file(source_code, task_file_path, _logger,
                       make_parent=False)

    if not wrote:
        msg = "Failed to create task file '%s'" % task_file_path
        # Ensure that the failed write does not stick around
        if not delete_file(task_file_path, _logger):
            msg += "Failed to cleanup after a failed workflow creation"
        return (False, msg)

    return (True, file_name)


def delete_workflow_task_file(configuration, vgrid, task_name):
    """
    Deleted the workflow task file with a given name.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the task file.
    :param task_name: Name of the task file to delete.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if task file could be created, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise the name of the created file.
    """

    _logger = configuration.logger
    _logger.debug("deleting workflow task_file '%s'" % task_name)

    task_home = get_workflow_task_home(configuration, vgrid)
    if not task_home:
        return (True, "Task home: '%s' doesn't exist, no '%s' to delete" %
                (task_home, task_name))

    task_path = os.path.join(task_home, task_name)
    if not os.path.exists(task_path):
        return (True, "Task file: '%s' doesn't exist, nothing to delete" %
                task_name)

    if not delete_file(task_path, _logger):
        return (False, "Failed to delete '%s'" % task_path)

    return (True, "")


def get_task_parameter_path(configuration, vgrid, pattern, extension='.yaml',
                            relative=False):
    """
    Gets path to a parameter file based on a given pattern.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the parameter file.
    :param pattern: Workflow pattern used to generate parameter file.
    :param extension: [optional] parameter file extension. Currently only
    supports '.yaml'. Default is .'yaml'.
    :param relative: boolean for if path is relative to VGrid.
    :return: (string) returns parameter file path.
    """
    _logger = configuration.logger
    if relative:
        rel_vgrid_path = configuration.workflows_vgrid_tasks_home
        return os.path.join(vgrid, rel_vgrid_path,
                            pattern['persistence_id'] + extension)

    task_home = get_workflow_task_home(configuration, vgrid)
    if not task_home:
        _logger.warning("Could not find task home in vgrid '%s' "
                       "for paramater path" % vgrid)
        return False
    return os.path.join(task_home, pattern['persistence_id'] + extension)


def __create_task_parameter_file(configuration, vgrid, pattern,
                                 serializer='yaml'):
    """
    Create a yaml task parameter file that can be used by the executed task.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the parameter file.
    :param pattern: Workflow pattern used to generate parameter file.
    :param serializer: [optional] serialiser used for parameter file creation.
    Currently only '.yaml' are supported. Default is .'yaml'.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if parameter file could be created, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise an emtpy string.
    """
    _logger = configuration.logger

    created, msg = init_workflow_task_home(configuration, vgrid)
    if not created:
        return (False, msg)

    path = get_task_parameter_path(configuration, vgrid, pattern)
    if not path:
        msg = "A valid task parameter path could not be found"
        _logger.error(msg)
        return (False, msg)

    input_file = pattern.get('input_file', VALID_PATTERN['input_file'])
    parameter_dict = {}
    if input_file:
        parameter_dict.update({input_file: "ENV_WORKFLOW_INPUT_PATH"})
    # Ensure that output variables are based of the vgrid root dir
    output = pattern.get('output', VALID_PATTERN['output'])
    parameter_dict.update(
        {key: os.path.join(vgrid, value) for key, value in output.items()}
    )
    parameter_dict.update(pattern.get('variables', VALID_PATTERN['variables']))
    try:
        dump(parameter_dict, path, serializer=serializer, mode='w',
             **{'default_flow_style': False})
    except Exception as err:
        msg = "Failed to create the task parameter " \
              "file: %s, data: %s, err: %s" % (path, parameter_dict, err)
        _logger.warn(msg)
        return (False, msg)

    return (True, '')


def __update_task_parameter_file(configuration, vgrid, pattern,
                                 serializer='yaml'):
    """
    Updates a task parameter file by deleting the old version and creating a
    new one.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the parameter file.
    :param pattern: Workflow pattern used to generate parameter file.
    :param serializer: [optional] serialiser used for parameter file creation.
    Currently only '.yaml' are supported. Default is .'yaml'.
    :return: (Tuple (boolean, string) or function call to
    '__create_task_parameter_file') If a problem is encountered whilst deleting
    a previous parameter file then a tuple is returned with the first value
    being False, and an explanatory error message in the second value.
    Otherwise, the '__create_task_parameter_file' function is called.
    """
    if not __delete_task_parameter_file(configuration, vgrid, pattern):
        return False, "Failed to update the patterns parameter configuration"
    return __create_task_parameter_file(configuration, vgrid, pattern,
                                        serializer)


def __delete_task_parameter_file(configuration, vgrid, pattern):
    """
    Deletes a task parameter file based on the given pattern.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the parameter file.
    :param pattern: The workflow pattern object used to create the parameter
    file.
    :return: (function call to 'delete_file') Calls function 'delete_file' on
    the identified parameter file path.
    """
    _logger = configuration.logger
    path = get_task_parameter_path(configuration, vgrid, pattern)
    if not path:
        msg = "Skipping deletion of task parameter file for: '%s' " \
              "since it does not exist" % (pattern)
        _logger.info(msg)
        return True
    return delete_file(path, _logger, allow_missing=True)


def create_workflow_trigger(configuration, client_id, vgrid, path,
                            arguments=None, templates=None):
    """
    Creates a workflow trigger for a given path.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user to own the trigger.
    :param vgrid: The MiG VGrid containing trigger.
    :param path: Path against which events will be tested to determine if
    trigger fires or not. Paths are relative to the containing VGrid.
    :param arguments: [optional] (list) list of additional trigger arguments.
    :param templates: [optional] (list) list of additional trigger templates.
    :return: (Tuple (boolean or dict, string)) A tuple is returned. If a
    problem is encountered whilst creating a trigger the first value is False,
    with an explanatory error message in the second value. Otherwise the first
    value is the dictionary expressing the state of the created trigger and
    the sceond is an empty string.
    """
    _logger = configuration.logger
    if not arguments or not isinstance(arguments, list):
        arguments = []

    if not templates or not isinstance(templates, list):
        templates = []

    rule_id = "%d" % (time.time() * 1E8)
    ret_val, msg, ret_variables = \
        init_vgrid_script_add_rem(vgrid, client_id, rule_id, 'trigger',
                                  configuration)
    if not ret_val:
        return (False, msg)

    if get_workflow_trigger(configuration, vgrid, rule_id)[0]:
        _logger.warning("WP: A conflicting trigger rule already exists: '%s'"
                        % rule_id)
        return (False, "Failed to create trigger, conflicting rule_id")

    # See addvgridtrigger.py#86 NOTE about normalizing trigger path
    norm_path = os.path.normpath(path.strip()).lstrip(os.sep)
    # TODO, for now set the settle_time to 1s
    # To avoid double scheduling of triggered create/modified
    # events on the same operation (E.g. copy a file into the dir)
    rule_dict = {
        'rule_id': rule_id,
        'vgrid_name': vgrid,
        'path': norm_path,
        'changes': ['created', 'modified'],
        'run_as': client_id,
        'action': 'submit',
        'arguments': arguments,
        'rate_limit': '',
        'settle_time': '1s',
        'match_files': True,
        'match_dirs': False,
        'match_recursive': False,
        'templates': templates
    }
    add_status, add_msg = vgrid_add_triggers(configuration, vgrid, [rule_dict])
    if not add_status:
        _logger.warning("WP: Failed to add trigger '%s' to vgrid '%s' err "
                        "'%s'" % (rule_dict, vgrid, add_msg))
        return (False, add_msg)
    return (rule_dict, "")


def delete_workflow_trigger(configuration, vgrid, rule_id):
    """
    Deleters a workflow trigger with the given id.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing trigger.
    :param rule_id: Identifying characteristic of the trigger to be deleted.
    :return: (Tuple (boolean, string)) Returns a tuple with the first value
    being True if trigger could be deleted, and False otherwise. If a
    problem is encountered an explanatory error message is provided in the
    second value which is otherwise an emtpy string. In the unexpected event
    that we attempt to delete a file that does not exist, True is returned
    along with an explanatory message.
    """
    _logger = configuration.logger
    _logger.info("WP: delete_workflow_trigger")
    trigger, msg = get_workflow_trigger(configuration, vgrid, rule_id)
    _logger.info("WP: delete_workflow_trigger, trigger: '%s'" % trigger)

    if not trigger:
        return (True, "workflow trigger '%s' can't be deleted because it"
                      " does not exist" % rule_id)

    removed, msg = vgrid_remove_triggers(configuration, vgrid, rule_id)
    if not removed:
        _logger.warning("WP: Failed to remove trigger '%s' from vgrid '%s'"
                        " err '%s'" % (rule_id, vgrid, msg))
        return (False, msg)
    return (True, '')


def get_workflow_trigger(configuration, vgrid, rule_id=None, recursive=False):
    """
    Gets either an individual trigger if a rule_id is provided, or a list of
    all triggers in the given vgrid.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the trigger.
    :param rule_id: [optional] Identifier of an individual trigger. If
    provided only that trigger is returned. If not provided a list of all
    triggers in the given VGrid are returned instead.
    :param recursive: [optional] boolean stating if recursive search through
    sub_vgrids should be performed, or just the top level vgrid. Default is
    False.
    :return: (Tuple (boolean or list or dict, string)) A tuple is returned. If
    a problem is encountered whilst retrieving a trigger the first value is
    False, with an explanatory error message in the second value. Otherwise
    the first value is either the list of all returned triggers ir no rule_id
    is specified, or only the dict expressing the trigger which matches the
    given rule_id. In either case the second value is an empty string.
    """
    _logger = configuration.logger
    status, triggers = vgrid_triggers(vgrid, configuration,
                                      recursive=recursive)
    if not status:
        msg = "Failed to find triggers in vgrid '%s', err '%s'" % (vgrid,
                                                                   triggers)
        _logger.warn(msg)
        return (False, msg)

    if rule_id:
        for trigger in triggers:
            if trigger['rule_id'] == rule_id:
                return (trigger, '')

        msg = "No trigger found with id '%s'" % rule_id
        _logger.debug(msg)
        return (False, msg)

    return (triggers, '')


def update_workflow_trigger(configuration, vgrid, trigger):
    """
    Updates a workflow trigger.
    :param configuration: The MiG configuration object.
    :param vgrid: The MiG VGrid containing the trigger.
    :param trigger: Trigger dictionary to update. Must contain the key
    'rule_id'.
    :return: (Tuple (boolean, string) or function call to 'vgrid_set_triggers')
    If a problem is encountered returns a tuple with the first value being
    False, and an explanatory string in the second value. Otherwise will call
    the function 'vgrid_set_triggers'
    """
    _logger = configuration.logger

    if 'rule_id' not in trigger:
        return (False, "can't update trigger without the "
                       "required key rule_id %s" % trigger)

    triggers, msg = get_workflow_trigger(configuration, vgrid)
    if not triggers:
        return (False, msg)

    for current_trigger in triggers:
        if current_trigger['rule_id'] == trigger['rule_id']:
            current_trigger.update(trigger)

    return vgrid_set_triggers(configuration, vgrid, id_list=triggers)


def convert_to(configuration, notebook, exporter='notebook',
               return_resources=False):
    """
    Converts a notebook dictionary using a specified exporter.
    :param configuration: The MiG configuration object.
    :param notebook: The notebook to be exported.
    :param exporter: [optional] Exporter to be used. Currently only supports
    'notebook' and 'python'. Default is notebook.
    :param return_resources: [optional] Boolean specifying if export resources
    should be returned or not. Default is False.
    :return: (Tuple (boolean, dictionary or Tuple(dictionary, dictionary)
    Returns a tuple, with the first value being a boolean with True meaning
    the conversion was successful, and False anything else. If
    return_resources is True the second value is a Tuple with the first value
    containing the notebook source code, and the second value containing any
    notebook resources. If return_resources is False the second value is just
    the notebook source code.
    """
    _logger = configuration.logger

    valid_exporters = ['notebook', 'python']
    if exporter not in valid_exporters:
        return (False, "lang: '%s' is not a valid exporter" % exporter)

    if not PythonExporter:
        _logger.error("The required python package 'nbconvert' for "
                      "workflows is missing")
        return (False, "Missing the nbconvert python package")

    if not NotebookExporter:
        _logger.error("The required python package 'nbconvert' for "
                      "workflows is missing")
        return (False, "Missing the nbconvert python package")

    if exporter == 'python':
        ex = PythonExporter()
    else:
        ex = NotebookExporter()

    # Validate format of the provided notebook
    if not nbformat:
        _logger.error("The required python package 'nbformat' for "
                      "workflows is missing")
        return (False, "Missing the nbformat python package")
    try:
        nbformat.validate(notebook, version=4)
    except nbformat.ValidationError as err:
        _logger.error("Validation of notebook failed: '%s'" % err)
        return (False, "The provided notebook was incorrectly formatted: '%s'"
                % err)

    nb_node = nbformat.notebooknode.from_dict(notebook)
    (body, resources) = ex.from_notebook_node(nb_node)

    if return_resources:
        return (True, (body, resources))

    return (True, body)


def search_workflow(configuration, client_id,
                    workflow_search_type=PATTERN_GRAPH, **kwargs):
    """
    Searches a VGrid for workflow definitions. Currently only supports
    emergent pattern based workflows.
    :param configuration: The MiG configuration object.
    :param client_id: The MiG user
    :param workflow_search_type: type of search to be conducted. Currently
    only supported search is 'pattern_graph'.
    :param kwargs: keyword arguments for workflow search. Must contain key
    'vgrid'. All other arguments are currently unsupported.
    :return:
    """
    _logger = configuration.logger
    vgrid = kwargs.get('vgrid', None)
    if not vgrid:
        msg = "A workflow create dependency was missing: 'vgrid'"
        _logger.error("search_workflow: 'vgrid' was not set: '%s'" % vgrid)
        return (False, msg)

    success, msg, _ = init_vgrid_script_list(vgrid, client_id, configuration)
    if not success:
        return (False, msg)

    if workflow_search_type == PATTERN_GRAPH:
        return __search_workflow_p_graph(configuration, vgrid)


def __search_workflow_p_graph(configuration, vgrid):
    """
    Identifies emergent workflow from defined workflow patterns in a given
    VGrid.
    :param configuration: The MiG configuration object.
    :param vgrid: A MiG VGrid to search
    :return: (dictionary) Identified emergent Workflow. Format is {'nodes':
    dict of workflow nodes, 'edges': list of workflow edges}
    """
    _logger = configuration.logger
    workflows = get_workflow_with(configuration,
                                  user_query=True,
                                  workflow_type=WORKFLOW_PATTERN,
                                  **{'vgrid': vgrid})
    if not workflows:
        return (False, "Failed to find any workflows you own")

    wp_graph = {'nodes': {},
                'edges': []}
    for workflow in workflows:
        w_id = workflow['persistence_id']
        if w_id not in wp_graph['nodes']:
            wp_graph['nodes'][w_id] = workflow

        if 'output' not in workflow:
            continue

        for neighbour in workflows:
            n_id = neighbour['persistence_id']
            if w_id == n_id:
                continue
            # Have matching output/input paths?
            if not bool(set(workflow['output'].values()) &
                        set(neighbour['input_paths'])):
                continue

            for output in workflow['output'].values():
                if output in neighbour['input_paths']:
                    wp_graph['edges'].append({'from': w_id,
                                              'to': n_id})
    return (True, wp_graph)


if __name__ == '__main__':
    conf = get_configuration_object()
    args = sys.argv[1:]
    if args:
        if args[0] == 'create_workflow_session_id':
            created = touch_workflow_sessions_db(conf, force=True)
            print("Created sessions db %s" % created)
            client_id = "/C=dk/ST=dk/L=NA/O=org/OU=NA/CN=" \
                        "devuser/emailAddress=dev@dev.dk"
            if not get_workflow_session_id(conf, client_id):
                sid = create_workflow_session_id(conf, client_id)
                if not sid:
                    print("Failed to create session_id '%s'" % sid)
                else:
                    print("Created session_id '%s' for user '%s'"
                          % (sid, client_id))
        if args[0] == 'workflow_sessions':
            sessions_db = load_workflow_sessions_db(conf)
            print(sessions_db)
        if args[0] == 'delete_workflow_sessions':
            delete_workflow_sessions_db(conf)
        if args[0] == 'reset_test_workflows':
            reset_workflows(conf, default_vgrid)
