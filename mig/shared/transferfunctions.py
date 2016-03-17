#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# transferfunctions - data transfer helper functions
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

import datetime
import os
import time

from shared.defaults import datatransfers_filename
from shared.serial import load, dump
from shared.useradm import client_id_dir


def build_transferitem_object(configuration, transfer_dict):
    """Build a data transfer object based on input transfer_dict"""

    # TODO: add timestamp and creator?
    #created_timetuple = transfer_dict['created_timestamp'].timetuple()
    #created_asctime = time.asctime(created_timetuple)
    #created_epoch = time.mktime(created_timetuple)
    transfer_obj = {
        'object_type': 'datatransfer',
        #'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
        #                                                created_asctime),
        }
    transfer_obj.update(transfer_dict)
    return transfer_obj


def load_data_transfers(configuration, client_id):
    """Find all data transfers owned by user"""
    logger = configuration.logger
    try:
        transfers_path = os.path.join(configuration.user_settings,
                                      client_id_dir(client_id),
                                      datatransfers_filename)
        if os.path.isfile(transfers_path):
            transfers = load(transfers_path)
        else:
            transfers = {}
    except Exception:
        return (False, "could not load saved data transfers")
    return (True, transfers)

def get_data_transfer(transfer_id, client_id, configuration, transfers=None):
    """Helper to extract all details for a date transfer. The optional
    transfers argument can be used to pass an already loaded dictionary of
    saved transfers to avoid reloading.
    """
    if transfers is None:
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id)
        if not load_status:
            return (load_status, transfers)
    transfer_dict = transfers.get(transfer_id, None)
    if transfer_dict is None:
        return (False, 'No such transfer in saved data transfers: %s' % \
                transfer_id)
    return (True, transfer_dict)


def modify_data_transfers(action, transfer_dict, client_id, configuration,
                          transfers=None):
    """Modify data transfers with given action and transfer_dict for client_id.
    In practice this a shared helper to add or remove transfers from the saved
    data transfers. The optional transfers argument can be used to pass an
    already loaded dictionary of saved transfers to avoid reloading.
    """
    logger = configuration.logger
    transfer_id = transfer_dict['transfer_id']
    if transfers is None:
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id)
        if not load_status:
            return (load_status, transfers)

    if action == "create":
        transfer_dict.update({
            'created_timestamp': datetime.datetime.now(),
            'owner': client_id,
            })
        transfers[transfer_id] = transfer_dict
    elif action == "delete":
        del transfers[transfer_id]
    else:
        return (False, "Invalid action %s on data transfers" % action)
        
    try:
        transfers_path = os.path.join(configuration.user_settings,
                                      client_id_dir(client_id),
                                      datatransfers_filename)
        dump(transfers, transfers_path)
    except Exception, err:
        logger.error("modify_data_transfers failed: %s" % err)
        return (False, 'Error updating data transfers: %s' % err)
    return (True, transfer_id)


def create_data_transfer(transfer_dict, client_id, configuration,
                         transfers=None):
    """Create a new data transfer for client_id. The optional
    transfers argument can be used to pass an already loaded dictionary of
    saved transfers to avoid reloading.
    """
    return modify_data_transfers("create", transfer_dict, client_id,
                                 configuration, transfers)

def delete_data_transfer(transfer_id, client_id, configuration,
                         transfers=None):
    """Delete an existing frozen archive without checking ownership or
    persistance of frozen archives. The optional transfers argument can be
    used to pass an already loaded dictionary of
    saved transfers to avoid reloading.    """
    transfer_dict = {'transfer_id': transfer_id}
    return modify_data_transfers("delete", transfer_dict, client_id,
                                 configuration, transfers)
