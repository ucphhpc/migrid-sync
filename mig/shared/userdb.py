#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userdb - core user database handling functions
# Copyright (C) 2020-2022  The MiG Project lead by Brian Vinter
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

"""Core user database functions"""

from __future__ import print_function
from __future__ import absolute_import

import os

from mig.shared.defaults import user_db_filename
from mig.shared.fileio import acquire_file_lock, release_file_lock
from mig.shared.serial import load, dump


def default_db_path(configuration):
    """Return default site user db path.

    NOTE: for installations still storing the user database in the legacy
    mig/server/ location a warning is logged.
    Please manually move the database to the current user_db_home state dir or
    adjust your MiGserver.conf to point to the actual user database dir if you
    receive the below warning.
    """
    _logger = configuration.logger
    db_path = os.path.join(configuration.user_db_home, user_db_filename)
    legacy_path = os.path.join(configuration.mig_server_home, user_db_filename)
    if not os.path.exists(db_path) and os.path.exists(legacy_path):
        _logger.warning("user DB not found in %s - fall back to legacy %s" %
                        (db_path, legacy_path))
        return legacy_path
    return db_path


def lock_user_db(db_path, exclusive=True):
    """Lock user db"""
    db_lock_path = '%s.lock' % db_path
    return acquire_file_lock(db_lock_path, exclusive=exclusive)


def unlock_user_db(db_lock):
    """Unlock user db"""
    return release_file_lock(db_lock)


def load_user_db(db_path, do_lock=True):
    """Load pickled user DB"""

    if do_lock:
        flock = lock_user_db(db_path, exclusive=False)
    try:
        result = load(db_path)
    except Exception as exc:
        if do_lock:
            unlock_user_db(flock)
        raise
    if do_lock:
        unlock_user_db(flock)

    return result


def save_user_db(user_db, db_path, do_lock=True):
    """Save pickled user DB"""

    if do_lock:
        flock = lock_user_db(db_path)
    try:
        dump(user_db, db_path)
    except Exception as exc:
        if do_lock:
            unlock_user_db(flock)
        raise
    if do_lock:
        unlock_user_db(flock)


def load_user_dict(logger, user_id, db_path, verbose=False, do_lock=True):
    """Load user dictionary from user DB"""

    try:
        user_db = load_user_db(db_path, do_lock=do_lock)
        if verbose:
            print('Loaded existing user DB from: %s' % db_path)
    except Exception as err:
        err_msg = 'Failed to load user %s from DB: %s' % (user_id, err)
        logger.error(err_msg)
        if verbose:
            print(err_msg)
        return None
    return user_db.get(user_id, None)


def save_user_dict(logger, user_id, user_dict, db_path, verbose=False, do_lock=True):
    """Save user dictionary in user DB"""

    save_status = False
    if do_lock:
        flock = lock_user_db(db_path)
    try:
        user_db = load_user_db(db_path, do_lock=False)
        user_db[user_id] = user_dict
        save_user_db(user_db, db_path, do_lock=False)
        save_status = True
    except Exception as err:
        err_msg = 'Failed to save user %s in DB: %s' % (user_id, err)
        logger.error(err_msg)
        if verbose:
            print(err_msg)
    if do_lock:
        unlock_user_db(flock)
    return save_status


def update_user_dict(logger, user_id, changes, db_path, verbose=False, do_lock=True):
    """Load user dictionary of user_id from user DB, update it with values in
    changes dictionary and write back the updated entry to user DB.
    Keeps the entire operation under lock unless do_lock is disabled and
    returns the updated user dictionary.
    """
    user_dict = None
    if do_lock:
        flock = lock_user_db(db_path)
    try:
        user_db = load_user_db(db_path, do_lock=False)
        user_dict = user_db.get(user_id, None)
        if not user_dict:
            raise ValueError("no such user in user DB: %s" % user_id)
        if not changes:
            raise ValueError("no changes for %s: %s" % (user_id, changes))
        logger.debug("updating user %s with %s" % (user_id, changes))
        user_dict.update(changes)
        user_db[user_id] = user_dict
        save_user_db(user_db, db_path, do_lock=False)
        logger.debug("updated user %s to %s" % (user_id, user_dict))
    except Exception as err:
        err_msg = 'Failed to update user %s in DB: %s' % (user_id, err)
        logger.error(err_msg)
        if verbose:
            print(err_msg)
    if do_lock:
        unlock_user_db(flock)
    return user_dict
