# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# storage - data layer for peers management
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""Data layer for peers management: load, save and update peers."""

import copy
import os

from mig.shared.base import client_id_dir
from mig.shared.defaults import peers_filename, pending_peers_filename
from mig.shared.fileio import (
    acquire_lock_for_path,
    load_db_with_lock,
    pickle,
    release_file_lock,
    unpickle,
)
from mig.shared.logger import null_logger


def list_peers_requested(configuration, client_id):
    """
    Return the requested peers corresponding to a particular user.
    """

    pending_peers = load_peers_pending(configuration, client_id)
    if not pending_peers:
        return []
    return [peer_dict for _, peer_dict in pending_peers]


def list_peers_accepted(configuration, client_id):
    """
    Return the accepted peers corresponding to a particular user.
    """
    accepted_peers = load_peers_accepted(configuration, client_id)
    if not accepted_peers:
        return {}
    return accepted_peers


def peer_already_exists(configuration, client_id, peer_email):
    """Validate that an identical existing requested/accepted peer does not exist already"""
    requested_peers = list(list_peers_requested(configuration, client_id))
    if peer_email in [
        requested_peer["email"] for requested_peer in requested_peers
    ]:
        return True, "you already have a requested peer with that email"

    accepted_peers = list_peers_accepted(configuration, client_id)
    if peer_email in [
        accepted_peer["email"] for accepted_peer in accepted_peers.values()
    ]:
        return True, "you already have an accepted peer with that email"
    return False, "you do not have a peer with that email"


def load_peers_pending(configuration, client_id):
    """Loads the pending peers for the client"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    peers_path = os.path.join(
        configuration.user_settings, client_dir, pending_peers_filename
    )

    pending_peers = load_db_with_lock(
        peers_path, logger=_logger, exclusive=True
    )
    if not pending_peers and os.path.exists(peers_path):
        _logger.warning(
            "failed to load the pending peers from: %s that does exist"
            % peers_path
        )
    return pending_peers


def load_peers_accepted(configuration, client_id):
    """Loads the accepted peers for the client"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    peers_path = os.path.join(
        configuration.user_settings, client_dir, peers_filename
    )

    accepted_peers = load_db_with_lock(
        peers_path, logger=_logger, exclusive=True
    )
    if not accepted_peers and os.path.exists(peers_path):
        _logger.warning(
            "failed to load accepted peers from: %s that does exist"
            % peers_path
        )
    return accepted_peers


def update_peers_accepted(configuration, client_id, update_peer_dicts):
    """Update the accepted peers for the client"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)

    peers_path = os.path.join(
        configuration.user_settings, client_dir, peers_filename
    )
    with acquire_lock_for_path(peers_path, exclusive=True) as _lock_handle:
        try:
            peers_db = unpickle(peers_path, _logger, allow_missing=True)
            if not peers_db:
                _logger.info(
                    "found no peers db at %s to update the peer %s from for %s"
                    % (peers_path, update_peer_dicts, client_id)
                )
                return True

            copy_peers_db = copy.deepcopy(peers_db)
            for peer_dn, peer_update_dict in update_peer_dicts.items():
                if peer_dn not in copy_peers_db:
                    continue
                copy_peers_db[peer_dn].update(**peer_update_dict)

            if pickle(copy_peers_db, peers_path, _logger):
                _logger.info(
                    "updating accepted peer(s) %s from %s for %s"
                    % (update_peer_dicts, peers_path, client_id)
                )
                return True

            _logger.error(
                "updating accepted peer(s) %s from %s for %s failed"
                % (update_peer_dicts, peers_path, client_id)
            )
            return False
        finally:
            release_file_lock(_lock_handle)


def remove_pending_peers_from_client(configuration, client_id, peers_dns):
    """
    Remove a specified pending peer from the client.
    Expects peers_dns to be a list of tuples, this is used to maintain the order
    of the peers in the list when a user has to approve them.

    peers_dns: [x509_peer_dn_string]
    """

    _logger = configuration.logger
    client_dir = client_id_dir(client_id)

    peers_path = os.path.join(
        configuration.user_settings, client_dir, pending_peers_filename
    )
    with acquire_lock_for_path(peers_path, exclusive=True) as _lock_handle:
        try:
            peers_db = unpickle(peers_path, _logger, allow_missing=True)
            if not peers_db:
                _logger.info(
                    "found no pending peers db at %s to delete the peer %s from for %s"
                    % (peers_path, peers_dns, client_id)
                )
                return True

            new_peers_db = [
                (peer_dn, peer_dict)
                for peer_dn, peer_dict in peers_db
                if peer_dn not in peers_dns
            ]
            if pickle(new_peers_db, peers_path, _logger):
                _logger.info(
                    "removed pending peer(s) %s from %s for %s"
                    % (peers_dns, peers_path, client_id)
                )
                return True

            _logger.error(
                "deleting pending peer(s) %s from %s for %s failed"
                % (peers_dns, peers_path, client_id)
            )
            return False
        finally:
            release_file_lock(_lock_handle)


def add_pending_peers_to_client(configuration, client_id, peers):
    """
    Add a specified pending peer from the client.
    Expects peers to be a list of tuples, this is used to maintain the order
    of the peers in the list when a user has to approve them.

    peers: [(x509_peer_dn_string, dict_of_peer_fields)]
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)

    peers_path = os.path.join(
        configuration.user_settings, client_dir, pending_peers_filename
    )
    with acquire_lock_for_path(peers_path, exclusive=True) as _lock_handle:
        try:
            peers_db = unpickle(peers_path, _logger, allow_missing=True)
            if not peers_db:
                peers_db = []
                _logger.warning(
                    "found no pending peers db at %s to add peer(s) %s to for %s"
                    % (peers_path, peers, client_id)
                )
                _logger.info(
                    "creating a new pending peers db at %s" % peers_path
                )

            change_peers = dict(peers)
            # NOTE: always remove old first to replace any existing and move them last
            peers_db = [
                (peer_dn, peer_dict)
                for (peer_dn, peer_dict) in peers_db
                if peer_dn not in change_peers
            ]

            peers_db += peers
            if pickle(peers_db, peers_path, _logger):
                _logger.info(
                    "added pending peer(s) %s to %s for %s"
                    % (peers, peers_path, client_id)
                )
                return True

            _logger.error(
                "adding pending peer(s) %s to %s for %s failed"
                % (peers, peers_path, client_id)
            )
            return False
        finally:
            release_file_lock(_lock_handle)


def remove_accepted_peers_from_client(configuration, client_id, peers_dns):
    """
    Remove accepted peers from the client.
    Expects peers_dns to be a list of x509 distinguished names to identify the peer.

    peers_dns: [x509_peer_dn_string]
    """

    _logger = configuration.logger
    client_dir = client_id_dir(client_id)

    peers_path = os.path.join(
        configuration.user_settings, client_dir, peers_filename
    )
    with acquire_lock_for_path(peers_path, exclusive=True) as _lock_handle:
        try:
            peers_db = unpickle(peers_path, _logger, allow_missing=True)
            if not peers_db:
                _logger.info(
                    "found no peers db at %s to delete the peer %s from for %s"
                    % (peers_path, peers_dns, client_id)
                )
                return True

            for peer_dn in peers_dns:
                if peer_dn in peers_db:
                    del peers_db[peer_dn]

            if pickle(peers_db, peers_path, _logger):
                _logger.info(
                    "removed peer(s) %s from %s for %s"
                    % (peers_dns, peers_path, client_id)
                )
                return True

            _logger.error(
                "deleting %s peer(s) from %s for %s failed"
                % (peers_dns, peers_path, client_id)
            )
            return False
        finally:
            release_file_lock(_lock_handle)


def add_accepted_peers_to_client(configuration, client_id, peers_dict):
    """
    Remove accepted peers from the client.
    Expects peers to be a dictionary

    peers: {x509_peer_dn_string, dict_of_peer_fields}
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)

    peers_path = os.path.join(
        configuration.user_settings, client_dir, peers_filename
    )
    with acquire_lock_for_path(peers_path, exclusive=True) as _lock_handle:
        try:
            peers_db = unpickle(peers_path, _logger, allow_missing=True)
            if not peers_db:
                peers_db = {}
                _logger.warning(
                    "found no peers db at %s to add peer(s) %s to for %s"
                    % (peers_path, peers_dict, client_id)
                )
                _logger.info("creating a new peers db at %s" % peers_path)

            for peer_dn, peer_dict in peers_dict.items():
                peers_db[peer_dn] = peer_dict

            if pickle(peers_db, peers_path, _logger):
                _logger.info(
                    "added peer(s) %s to %s for %s"
                    % (peers_dict, peers_path, client_id)
                )
                return True

            _logger.error(
                "adding peer(s) %s to %s for %s failed"
                % (peers_dict, peers_path, client_id)
            )
            return False
        finally:
            release_file_lock(_lock_handle)
