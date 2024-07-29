#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# transferfunctions - data transfer helper functions
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""Data transfer functions"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import range
import datetime
import re
import os
import time

from mig.shared.base import client_id_dir, mask_creds
from mig.shared.defaults import datatransfers_filename, user_keys_dir, \
    transfer_output_dir
from mig.shared.fileio import makedirs_rec, delete_file, acquire_file_lock, \
    release_file_lock, remove_rec
from mig.shared.safeeval import subprocess_popen, subprocess_pipe
from mig.shared.serial import load, dump

default_key_type = 'rsa'
default_key_bits = 2048


def get_transfers_path(configuration, client_id):
    """Build the default transfers file path for client_id"""
    return os.path.join(configuration.user_settings, client_id_dir(client_id),
                        datatransfers_filename)


def get_status_dir(configuration, client_id, transfer_id=''):
    """Lookup the status directory for transfers on behalf of client_id.
    The optional transfer_id is used to get the explicit status dir for that
    particular transfer rather than the parent status directory.
    This is used for writing the global transfer log as well as individual
    status, stdout, stderr and possibly transfer.log files for the transfers.
    """
    return os.path.join(configuration.user_home, client_id_dir(client_id),
                        transfer_output_dir, transfer_id).rstrip(os.sep)


def blind_pw(transfer_dict):
    """Returns a copy of transfer_dict with password blinded out"""
    hide_pw = '**HIDDEN**'
    replace_map = {}
    # NOTE: lftp commands inline credentials for various reasons (see S3 note)
    for target in ('lftp_src', 'lftp_dst'):
        if transfer_dict.get(target, ''):
            replace_map[target] = (
                r'(.*://[^:]*):[^@]+@(.*)', r'\1:%s@\2' % hide_pw)
    blinded = mask_creds(
        transfer_dict, masked_value=hide_pw, subst_map=replace_map)
    return blinded


def build_transferitem_object(configuration, transfer_dict):
    """Build a data transfer object based on input transfer_dict"""

    created_timestamp = transfer_dict['created_timestamp']
    created_timetuple = created_timestamp.timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    # Update timestamp was added later and thus may not be set
    transfer_dict['updated_timestamp'] = transfer_dict.get('updated_timestamp',
                                                           created_timestamp)
    updated_timestamp = transfer_dict['updated_timestamp']
    updated_timetuple = updated_timestamp.timetuple()
    updated_asctime = time.asctime(updated_timetuple)
    updated_epoch = time.mktime(updated_timetuple)
    transfer_obj = {
        'object_type': 'datatransfer',
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        'updated': "<div class='sortkey'>%d</div>%s" % (updated_epoch,
                                                        updated_asctime),
    }
    transfer_obj.update(blind_pw(transfer_dict))
    # NOTE: datetime is not json-serializable so we force to string
    for field in ['created_timestamp', 'updated_timestamp']:
        transfer_obj[field] = "%s" % transfer_obj[field]
    return transfer_obj


def build_keyitem_object(configuration, key_dict):
    """Build a transfer key object based on input key_dict"""

    # map file timestamp on epoch format to human-friendly version
    created_epoch = key_dict.get('created_epoch', 0)
    created_asctime = time.asctime(time.gmtime(created_epoch))
    key_obj = {
        'object_type': 'transferkey',
        'created': "<div class='sortkey'>%d</div>%s" %
        (created_epoch, created_asctime),
    }
    key_obj.update(key_dict)
    return key_obj


def lock_data_transfers(transfers_path, exclusive=True, blocking=True):
    """Lock per-user transfers index"""
    transfers_lock_path = '%s.lock' % transfers_path
    return acquire_file_lock(transfers_lock_path, exclusive=exclusive,
                             blocking=blocking)


def unlock_data_transfers(transfers_lock):
    """Unlock per-user transfers index"""
    return release_file_lock(transfers_lock)


def load_data_transfers(configuration, client_id, do_lock=True, blocking=True):
    """Find all data transfers owned by user with optional locking support
    for synchronized access.
    """
    logger = configuration.logger
    logger.debug("load transfers for %s" % client_id)
    transfers_path = get_transfers_path(configuration, client_id)
    if do_lock:
        flock = lock_data_transfers(transfers_path, exclusive=False,
                                    blocking=blocking)
        if not blocking and not flock:
            return (False, "could not lock+load saved data transfers for %s" %
                    client_id)
    try:
        logger.debug("load transfers from %s" % transfers_path)
        if os.path.isfile(transfers_path):
            transfers = load(transfers_path)
        else:
            transfers = {}
    except Exception as exc:
        if do_lock:
            unlock_data_transfers(flock)
        return (False, "could not load saved data transfers: %s" % exc)
    if do_lock:
        unlock_data_transfers(flock)
    return (True, transfers)


def get_data_transfer(configuration, client_id, transfer_id, transfers=None,
                      do_lock=True, blocking=True):
    """Helper to extract all details for a data transfer. The optional
    transfers argument can be used to pass an already loaded dictionary of
    saved transfers to avoid reloading. In that case the caller might want to
    hold the corresponding lock during the handling here to avoid races.
    Locking is also generally supported for synchronized access.
    """
    if transfers is None:
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id, do_lock,
                                                       blocking)
        if not load_status:
            return (load_status, transfers)
    transfer_dict = transfers.get(transfer_id, None)
    if transfer_dict is None:
        return (False, 'No such transfer in saved data transfers: %s' %
                transfer_id)
    return (True, transfer_dict)


def modify_data_transfers(configuration, client_id, transfer_dict, action,
                          transfers=None, do_lock=True, blocking=True):
    """Modify data transfers with given action and transfer_dict for client_id.
    In practice this a shared helper to add or remove transfers from the saved
    data transfers. The optional transfers argument can be used to pass an
    already loaded dictionary of saved transfers to avoid reloading. In that
    case the caller might want to hold the corresponding lock during the
    handling here to avoid races. Locking is also generally supported for
    synchronized access.
    """
    logger = configuration.logger
    transfer_id = transfer_dict['transfer_id']
    transfers_path = get_transfers_path(configuration, client_id)
    # Lock during entire load and save
    if do_lock:
        flock = lock_data_transfers(transfers_path, exclusive=True,
                                    blocking=blocking)
        if not blocking and not flock:
            return (False, "could not lock+update data transfers for %s" %
                    client_id)

    if transfers is None:
        # Load without repeated lock
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id,
                                                       do_lock=False)
        if not load_status:
            if do_lock:
                unlock_data_transfers(flock)
            logger.error("modify_data_transfers failed in load: %s" %
                         transfers)
            return (load_status, transfers)

    if action == "create":
        now = datetime.datetime.now()
        transfer_dict.update({
            'created_timestamp': now,
            'updated_timestamp': now,
            'owner': client_id,
        })
        transfers[transfer_id] = transfer_dict
    elif action == "modify":
        transfer_dict['updated_timestamp'] = datetime.datetime.now()
        transfers[transfer_id].update(transfer_dict)
    elif action == "delete":
        del transfers[transfer_id]
    else:
        if do_lock:
            unlock_data_transfers(flock)
        return (False, "Invalid action %s on data transfer %s" % (action,
                                                                  transfer_id))

    try:
        dump(transfers, transfers_path)
        res_dir = get_status_dir(configuration, client_id, transfer_id)
        makedirs_rec(res_dir, configuration)
    except Exception as err:
        if do_lock:
            unlock_data_transfers(flock)
        logger.error("modify_data_transfers failed: %s" % err)
        return (False, 'Error updating data transfers: %s' % err)
    if do_lock:
        unlock_data_transfers(flock)
    return (True, transfer_id)


def create_data_transfer(configuration, client_id, transfer_dict,
                         transfers=None, do_lock=True, blocking=True):
    """Create a new data transfer for client_id. The optional
    transfers argument can be used to pass an already loaded dictionary of
    saved transfers to avoid reloading. In that case the caller might want to
    hold the corresponding lock during the handling here to avoid races.
    Locking is also generally supported for synchronized access.
    """
    return modify_data_transfers(configuration, client_id, transfer_dict,
                                 "create", transfers, do_lock, blocking)


def update_data_transfer(configuration, client_id, transfer_dict,
                         transfers=None, do_lock=True, blocking=True):
    """Update existing data transfer for client_id. The optional transfers
    argument can be used to pass an already loaded dictionary of saved
    transfers to avoid reloading. In that case the caller might want to
    hold the corresponding lock during the handling here to avoid races.
    Locking is also generally supported for synchronized access.
    """
    return modify_data_transfers(configuration, client_id, transfer_dict,
                                 "modify", transfers, do_lock, blocking)


def delete_data_transfer(configuration, client_id, transfer_id,
                         transfers=None, do_lock=True, blocking=True):
    """Delete an existing data transfer without checking ownership. The
    optional transfers argument can be used to pass an already loaded
    dictionary of saved transfers to avoid reloading. In that case the caller
    might want to hold the corresponding lock during the handling here to avoid
    races.
    Locking is also generally supported for synchronized access.
    """
    transfer_dict = {'transfer_id': transfer_id}
    return modify_data_transfers(configuration, client_id, transfer_dict,
                                 "delete", transfers, do_lock, blocking)


def load_user_keys(configuration, client_id):
    """Load a list of generated/imported keys from settings dir. Each item is
    a dictionary with key details and the public key.
    """
    logger = configuration.logger
    user_keys = []
    keys_dir = os.path.join(configuration.user_settings,
                            client_id_dir(client_id), user_keys_dir)
    try:
        hits = os.listdir(keys_dir)
    except Exception as exc:
        # This is common for users without transfer keys
        logger.debug("could not find user keys in %s: %s" % (keys_dir, exc))
        return user_keys
    for key_filename in hits:
        if key_filename.endswith('.pub'):
            continue
        pubkey_path = os.path.join(keys_dir, key_filename + '.pub')
        pubkey, created_timestamp = '', ''
        try:
            pub_fd = open(pubkey_path)
            pubkey = pub_fd.read().strip()
            pub_fd.close()
            created_epoch = os.path.getctime(pubkey_path)
        except Exception as exc:
            logger.warning("load user key did not find a pub key for %s: %s"
                           % (key_filename, exc))
            continue
        # TODO: don't assume key was necessarily made with defaults type/bits.
        #       maybe we can query that with paramiko key handling?
        key_dict = {'key_id': key_filename, 'created_epoch': created_epoch,
                    'type': default_key_type, 'bits': default_key_bits,
                    'public_key': pubkey}
        user_keys.append(key_dict)
    return user_keys


def generate_user_key(configuration, client_id, key_filename, truncate=False):
    """Generate a new key and save it as key_filename in settings dir"""
    # TODO: switch to paramiko key generation?
    logger = configuration.logger
    key_dir = os.path.join(configuration.user_settings,
                           client_id_dir(client_id),
                           user_keys_dir)
    key_path = os.path.join(key_dir, key_filename)
    makedirs_rec(key_dir, configuration)
    if os.path.exists(key_path) and not truncate:
        logger.error("user key %s already exists!" % key_path)
        return (False, 'user key %s already exists!' % key_filename)
    logger.debug("generating user key %s" % key_path)
    gen_proc = subprocess_popen(['ssh-keygen', '-t', default_key_type, '-b',
                                 '%d' % default_key_bits, '-f', key_path,
                                 '-N', '', '-C', key_filename],
                                stdout=subprocess_pipe, stderr=subprocess_pipe)
    exit_code = gen_proc.wait()
    out, err = gen_proc.communicate()
    if exit_code != 0:
        logger.error("user key generation in %s failed: %s %s (%s)" %
                     (key_path, out, err, exit_code))
        return (False, "user key generation in %s failed!" % key_filename)
    logger.info('done generating user key %s: %s : %s (%s)' %
                (key_path, out, err, exit_code))
    pub_key = ''
    try:
        pub_fd = open(key_path + '.pub')
        pub_key = pub_fd.read()
        pub_fd.close()
    except Exception as exc:
        logger.error("user key generation %s did not create a pub key: %s" %
                     (key_path, exc))
        return (False, "user key generation in %s failed!" % key_filename)
    return (True, pub_key)


def delete_user_key(configuration, client_id, key_filename):
    """Delete the user key key_filename in settings dir"""
    key_dir = os.path.join(configuration.user_settings,
                           client_id_dir(client_id),
                           user_keys_dir)
    pub_filename = "%s.pub" % key_filename
    status, msg = True, ""
    for filename in (key_filename, pub_filename):
        path = os.path.join(key_dir, filename)
        if not delete_file(path, configuration.logger):
            msg += "removal of user key '%s' failed! \n" % filename
            status = False
    return (status, msg)


# IMPORTANT: We can't use nested dicts because it is not supported by our
#       multiprocessing.manager.dict shared object. Merge IDs into one instead
#       to get a single flat key-space.
#       Furthermore mutable objects in such dicts can not be directly operated
#       upon for proxy safety reasons, and instead require full reassignment
#       every time!
__id_sep = '#'


def __merge_transfer_id(client_id, transfer_id):
    """Helper to merge a client_id and a transfer_id into a single key for our
    dictionaries. We can't use nested dicts because it is not supported by
    multiprocessing.manager.dict .
    """
    return "%s%s%s" % (client_id, __id_sep, transfer_id)


def __split_transfer_id(merged_id):
    """Helper to split a previosuly merged client_id and transfer_id key into
    the two original parts.
    """
    return merged_id.split(__id_sep, 1)


def all_worker_transfers(configuration, all_workers):
    """Extract the list of [client_id, transfer_id, worker] lists for all
    transfers with workers associated.
    """
    return [__split_transfer_id(i) + [j] for (i, j) in all_workers.items()]


def add_worker_transfer(configuration, all_workers, client_id, transfer_id,
                        worker):
    """Add worker for transfer_id owned by client_id"""
    full_id = __merge_transfer_id(client_id, transfer_id)
    all_workers[full_id] = worker
    return True


def get_worker_transfer(configuration, all_workers, client_id, transfer_id):
    """Return any worker associated with transfer_id owned by client_id, or
    None if no worker is associated.
    """
    full_id = __merge_transfer_id(client_id, transfer_id)
    return all_workers.get(full_id, None)


def del_worker_transfer(configuration, all_workers, client_id, transfer_id,
                        worker=None):
    """Remove worker for transfer owned by client_id. If worker is provided
    only a matching worker will succeed, otherwise any worker will be removed.
    """
    full_id = __merge_transfer_id(client_id, transfer_id)
    if worker is None or all_workers.get(full_id, None) == worker:
        del all_workers[full_id]
        return True
    else:
        return False

# NOTE: Please refer to IMPORTANT note above about reassignments


def sub_pid_list(configuration, pid_map, client_id, transfer_id):
    """Extract the list of subprocess PIDs from pid_map for transfer_id
    owned by client_id. Returns a (possibly empty) list of PIDs.
    """
    full_id = __merge_transfer_id(client_id, transfer_id)
    return pid_map.get(full_id, [])


def add_sub_pid(configuration, pid_map, client_id, transfer_id, sub_pid):
    """Add sub_pid to the list of subprocess PIDs from pid_map for transfer_id
    owned by client_id.
    Please note that we have to reassign dict values in full here for
    multiprocessing.manager.dict support.
    """
    full_id = __merge_transfer_id(client_id, transfer_id)
    pid_map[full_id] = pid_map.get(full_id, [])
    pid_map[full_id] = pid_map[full_id] + [sub_pid]
    return True


def del_sub_pid(configuration, pid_map, client_id, transfer_id, sub_pid):
    """Remove sub_pid from the list of subprocess PIDs from pid_map for
    transfer_id owned by client_id.
    Please note that we have to reassign dict values in full here for
    multiprocessing.manager.dict support.
    """
    logger = configuration.logger
    full_id = __merge_transfer_id(client_id, transfer_id)
    pid_map[full_id] = pid_map.get(full_id, [])
    if not sub_pid in pid_map[full_id]:
        logger.error('could not remove %s %s child process %d' %
                     (client_id, transfer_id, sub_pid))
        return False
    else:
        tmp = pid_map[full_id]
        tmp.remove(sub_pid)
        pid_map[full_id] = tmp
        return True


def kill_sub_pid(configuration, client_id, transfer_id, sub_pid, sig=9):
    """Send signal sig to the subprocess with process ID sub_pid from transfer
    with transfer_id and owned by client_id.
    """
    logger = configuration.logger
    try:
        os.kill(sub_pid, sig)
        return True
    except Exception as exc:
        logger.error('could not kill %s %s child process %d' %
                     (client_id, transfer_id, sub_pid))
        return False


if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    print("Unit testing transfer functions")
    # NOTE: use /tmp for testing
    orig_user_settings = conf.user_settings
    client, transfer = "testuser", "testtransfer"
    conf.user_settings = '/tmp/transferstest'
    dummy_transfers_dir = os.path.join(conf.user_settings, client)
    dummy_transfers_file = os.path.join(dummy_transfers_dir,
                                        datatransfers_filename)
    makedirs_rec(dummy_transfers_dir, conf)
    transfer_dict = {'transfer_id': transfer}
    dummypw = 'NotSoSecretDummy'
    transfer_dict.update(
        {'password': dummypw,
         'lftp_src': 'sftp://john.doe:%s@nowhere.org/README' % dummypw,
         'lftp_dst': 'https://john.doe:%s@outerspace.org/' % dummypw,
         })
    print("=== user transfers dict mangling ===")
    (status, transfers) = load_data_transfers(conf, client)
    print("initial transfers before create : %s" % transfers)
    create_data_transfer(conf, client, transfer_dict)
    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after create: %s" % transfers)
    transfer_dict['password'] += "-UPDATED-NOW"
    update_data_transfer(conf, client, transfer_dict)
    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after update: %s" % transfers)
    delete_data_transfer(conf, client, transfer)
    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after delete: %s" % transfers)

    print("lock transfers file for testing prevented create access")
    dummy_lock = lock_data_transfers(dummy_transfers_file, exclusive=True)
    for i in range(3):
        print("try creating transfer while locked (%d)" % i)
        transfer_dict['transfer_id'] = '%s-%s' % (transfer, i)
        (create_status, created_id) = \
            create_data_transfer(conf, client, transfer_dict,
                                 blocking=False)
        print("create transfer while locked status: %s" % create_status)
        time.sleep(1)
    print("unlock transfers file for testing restored create access")
    unlock_data_transfers(dummy_lock)
    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after locked create attempts: %s" % transfers)
    for i in range(3):
        print("try creating transfer while unlocked (%d)" % i)
        transfer_dict['transfer_id'] = '%s-%s' % (transfer, i)
        (create_status, created_id) = \
            create_data_transfer(conf, client, transfer_dict,
                                 blocking=False)
        print("create transfer while unlocked status: %s" % create_status)
        time.sleep(1)

    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after unlocked create attempts: %s" % transfers)
    print("lock transfers file for testing prevented delete access")
    dummy_lock = lock_data_transfers(dummy_transfers_file, exclusive=True)
    for i in range(3):
        print("try deleting transfer while locked (%d)" % i)
        transfer_id = transfer_dict['transfer_id'] = '%s-%s' % (transfer, i)
        (delete_status, delete_id) = \
            delete_data_transfer(conf, client, transfer_id,
                                 blocking=False)
        print("delete transfer while locked status: %s" % delete_status)
        time.sleep(1)

    print("unlock transfers file for testing restored delete access")
    unlock_data_transfers(dummy_lock)
    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after locked delete attempts: %s" % transfers)
    for i in range(3):
        print("try deleting transfer while unlocked (%d)" % i)
        transfer_id = transfer_dict['transfer_id'] = '%s-%s' % (transfer, i)
        (delete_status, delete_id) = \
            delete_data_transfer(conf, client, transfer_id,
                                 blocking=False)
        print("delete transfer while unlocked status: %s" % delete_status)
        time.sleep(1)

    (status, transfers) = load_data_transfers(conf, client)
    print("transfers after unlocked delete attempts: %s" % transfers)

    remove_rec(dummy_transfers_dir, conf)

    print("=== sub pid functions ===")
    import multiprocessing
    manager = multiprocessing.Manager()
    sub_procs_map = manager.dict()
    sub_procs = sub_pid_list(conf, sub_procs_map, client, transfer)
    print("initial sub pids: %s" % sub_procs)
    for pid in range(3):
        print("add sub pid: %s" % pid)
        add_sub_pid(conf, sub_procs_map, client, transfer, pid)
        sub_procs = sub_pid_list(conf, sub_procs_map, client, transfer)
        print("current sub pids: %s" % sub_procs)
    for pid in range(3):
        print("del sub pid: %s" % pid)
        del_sub_pid(conf, sub_procs_map, client, transfer, pid)
        sub_procs = sub_pid_list(conf, sub_procs_map, client, transfer)
        print("current sub pids: %s" % sub_procs)
    print("=== workers functions ===")
    workers_map = {}
    transfer_workers = all_worker_transfers(conf, workers_map)
    print("initial transfer workers: %s" % transfer_workers)
    for i in range(3):
        transfer_id = "%s-%d" % (transfer, i)
        worker = "dummy-worker-%d" % i
        print("add %s %s %s " % (client, transfer_id, worker))
        add_worker_transfer(conf, workers_map, client, transfer_id, worker)
        verify_worker = get_worker_transfer(conf, workers_map, client,
                                            transfer_id)
        print("verify latest transfer worker: %s" % verify_worker)
    transfer_workers = all_worker_transfers(conf, workers_map)
    print("all transfer workers: %s" % transfer_workers)
    for i in range(3):
        transfer_id = "%s-%d" % (transfer, i)
        worker = "dummy-worker-%d" % i
        print("remove %s %s %s " % (client, transfer_id, worker))
        del_worker_transfer(conf, workers_map, client,
                            transfer_id, worker)
        verify_worker = get_worker_transfer(conf, workers_map, client,
                                            transfer_id)
        print("verify transfer worker is no longer found: %s" % verify_worker)
    transfer_workers = all_worker_transfers(conf, workers_map)
    print("final transfer workers: %s" % transfer_workers)

    print("raw transfer dict:\n%s\nis blinded into:\n%s" %
          (transfer_dict, blind_pw(transfer_dict)))
