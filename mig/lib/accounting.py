#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accounting - helpers to support storage accounting
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
# --- END_HEADER ---
#

"""helpers to support storage accounting"""

from __future__ import absolute_import, print_function

import datetime
import locale
import math
import os
import time

from mig.shared.base import (
    client_dir_id,
    distinguished_name_to_user,
    force_native_str,
)
from mig.shared.fileio import load_json, make_symlink, pickle, unpickle
from mig.shared.useradm import get_accepted_peers
from mig.shared.vgrid import vgrid_owners, vgrid_list_vgrids


def __init_accounting_entry(
    user_bytes=0, freeze_bytes=0, vgrid_bytes=None, peers=None, ext_users=None
):
    """Return new user account dict entry"""
    if vgrid_bytes is None:
        vgrid_bytes = {}
    if peers is None:
        peers = {}
    if ext_users is None:
        ext_users = {}

    return {
        "user_bytes": user_bytes,
        "freeze_bytes": freeze_bytes,
        "vgrid_bytes": vgrid_bytes,
        "peers": peers,
        "ext_users": ext_users,
    }


def __get_owned_vgrid(configuration, verbose=False):
    """Find primary owner of vgrid and return a dictionary
    with owner client_id as key and list of owned vgrid_names as values
    NOTE: First owner of top-vgrid is primary owner"""
    logger = configuration.logger
    result = {}
    (status, vgrids) = vgrid_list_vgrids(configuration)
    if status:
        for vgrid_name in vgrids:
            # print("checking vgrid: %s" % check_vgrid_name)
            (owners_status, owners_list) = vgrid_owners(
                vgrid_name, configuration, recursive=True
            )
            # Find first non-zero owner
            # NOTE: Some owner files contain empty owners)
            owner = ""
            if owners_status and owners_list:
                owner = next(ent for ent in owners_list if ent)
            if owner:
                owned_vgrids = result.get(owner, [])
                owned_vgrids.append(vgrid_name)
                result[owner] = owned_vgrids
            else:
                msg = "Failed to find owner for vgrid: %s" % vgrid_name
                logger.warning(msg)
                if verbose:
                    print("WARNING: %s" % msg)

    # for client_id, vgrids in result.items():
    #    print("%s: %s" % (client_id, vgrids))

    return result


def __get_peers_map(configuration, verbose=False):
    """Create mapping between users and peers"""
    result = {}
    logger = configuration.logger
    with os.scandir(configuration.user_settings) as it:
        for user_entry in it:
            client_id = client_dir_id(user_entry.name)
            peer_result = result.get(client_id, {})
            accepted_peers = get_accepted_peers(configuration, client_id)
            for ext_client_id, value in accepted_peers.items():
                if not isinstance(value, dict):
                    msg = "Invalid peers format: %s: %s: %s" % (
                        client_id,
                        ext_client_id,
                        value,
                    )
                    logger.warning(msg)
                    if verbose:
                        print("WARNING: %s" % msg)
                    continue
                # Map external users to their peer
                ext_users = peer_result.get("ext_users", {})
                ext_users[ext_client_id] = value
                peer_result["ext_users"] = ext_users
                # Map peers to their external user
                ext_result = result.get(ext_client_id, {})
                peers = ext_result.get("peers", {})
                peers[client_id] = value
                ext_result["peers"] = peers
                result[ext_client_id] = ext_result
            result[client_id] = peer_result

    return result


def update_accounting(configuration, verbose=False):
    """Update user accounting information"""
    logger = configuration.logger
    retval = True
    result = {"accounting": {}, "quota": {}}
    accounting = result["accounting"]
    result["timestamp"] = int(time.time())

    # Map vgrid to their primary owner
    msg = "Creating vgrid owners map ..."
    logger.info(msg)
    if verbose:
        print(msg)
    t1 = time.time()
    owned_vgrid = __get_owned_vgrid(configuration, verbose=verbose)
    t2 = time.time()
    msg = "Created vgrid owners map in %d secs" % (t2 - t1)
    logger.info(msg)
    if verbose:
        print(msg)

    # Map peers to their "owner"

    msg = "Creating peers map ..."
    logger.info(msg)
    if verbose:
        print(msg)
    t1 = time.time()
    peers_map = __get_peers_map(configuration, verbose=verbose)
    t2 = time.time()
    msg = "Created peers map in %d secs" % (t2 - t1)
    logger.info(msg)
    if verbose:
        print(msg)

    # Create users, vgrid and freeze quota json file list

    user_quota_files = {}
    vgrid_quota_files = {}
    freeze_quota_files = {}
    with os.scandir(configuration.quota_home) as it:
        for entry in it:
            # Load quota info if it exists
            quota_info_pck = None
            quota_info_json = None
            quota_fs = None
            if entry.name.endswith(".pck"):
                quota_info_pck = entry.path
                quota_fs = entry.name.replace(".pck", "")
            elif entry.name.endswith(".json"):
                quota_info_json = entry.path
                quota_fs = entry.name.replace(".json", "")
            else:
                logger.debug("Skipping non quota info entry: %s" % entry.name)
                continue
            quota_info = None
            # Try .pck first then .json
            if quota_info_pck:
                quota_info = unpickle(quota_info_pck, configuration.logger)
            elif quota_info_json:
                quota_info = load_json(
                    quota_info_json, configuration.logger, convert_utf8=False
                )
            if not quota_info:
                msg = "Failed to load quota info for FS entry: %s" % entry.name
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue
            quota_basepath = os.path.join(configuration.quota_home, quota_fs)
            if not os.path.isdir(quota_basepath):
                msg = "Missing quota_basepath: %r" % quota_basepath
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue
            quota_mtime = quota_info.get("mtime", 0)
            quota_datestr = datetime.datetime.fromtimestamp(
                quota_mtime
            ).strftime("%x %X")
            result["quota"][quota_fs] = {"mtime": quota_mtime}

            # User quota

            user_path = os.path.join(quota_basepath, "user")
            if not os.path.isdir(user_path):
                msg = "Missing quota user path: %r" % user_path
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue

            msg = "Scanning %s user quota (%d) %s %r" % (
                quota_fs,
                quota_mtime,
                quota_datestr,
                user_path,
            )
            logger.info(msg)
            if verbose:
                print(msg)
            t1 = time.time()
            with os.scandir(user_path) as it2:
                for user_entry in it2:
                    if user_entry.name.endswith(".pck"):
                        client_id = client_dir_id(
                            user_entry.name.replace(".pck", "")
                        )
                    elif user_entry.name.endswith(".json"):
                        client_id = client_dir_id(
                            user_entry.name.replace(".json", "")
                        )
                    else:
                        logger.debug(
                            "Skipping non-user entry: %s" % user_entry.name
                        )
                        continue
                    user_quota_files[client_id] = user_entry.path

            t2 = time.time()
            msg = "Scanned %s user quota (%d) %s %r in %d secs" % (
                quota_fs,
                quota_mtime,
                quota_datestr,
                user_path,
                (t2 - t1),
            )
            logger.info(msg)
            if verbose:
                print(msg)

            # Vgrid quota

            vgrid_path = os.path.join(quota_basepath, "vgrid")
            if not os.path.isdir(vgrid_path):
                msg = "Missing quota vgrid path: %r" % vgrid_path
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue

            msg = "Scanning %s vgrid quota (%d) %s %r" % (
                quota_fs,
                quota_mtime,
                quota_datestr,
                vgrid_path,
            )
            logger.info(msg)
            if verbose:
                print(msg)
            t1 = time.time()
            with os.scandir(vgrid_path) as it2:
                for vgrid_entry in it2:
                    if vgrid_entry.name.endswith(".pck"):
                        vgrid_name = force_native_str(
                            vgrid_entry.name.replace(".pck", "")
                        )
                    elif vgrid_entry.name.endswith(".json"):
                        vgrid_name = force_native_str(
                            vgrid_entry.name.replace(".json", "")
                        )
                    else:
                        # logger.debug("Skipping non-vgrid entry: %s"
                        #              % vgrid_entry.name)
                        continue
                    # NOTE: sub-vgrids uses ':'
                    # as delimiter in 'vgrid_files_writable'
                    vgrid_name = vgrid_name.replace(":", "/")
                    # print("%s: %s" % (vgrid_name, vgrid_entry.path))
                    vgrid_quota_files[vgrid_name] = vgrid_entry.path
            t2 = time.time()
            msg = "Scanned %s vgrid quota (%d) %s %r in %d secs" % (
                quota_fs,
                quota_mtime,
                quota_datestr,
                vgrid_path,
                (t2 - t1),
            )
            logger.info(msg)
            if verbose:
                print(msg)

            # Freeze quota

            if configuration.site_enable_freeze:
                freeze_path = os.path.join(quota_basepath, "freeze")
                if not os.path.isdir(freeze_path):
                    msg = "Missing quota freeze path: %r" % freeze_path
                    logger.error(msg)
                    if verbose:
                        print("ERROR: %s" % msg)
                    retval = False
                    continue

                msg = "Scanning %s freeze quota (%d) %s %r" % (
                    quota_fs,
                    quota_mtime,
                    quota_datestr,
                    freeze_path,
                )
                logger.info(msg)
                if verbose:
                    print(msg)
                t1 = time.time()
                with os.scandir(freeze_path) as it2:
                    for freeze_entry in it2:
                        if freeze_entry.name.endswith(".pck"):
                            freeze_client_id = client_dir_id(
                                freeze_entry.name.replace(".pck", "")
                            )
                        elif freeze_entry.name.endswith(".json"):
                            freeze_client_id = client_dir_id(
                                freeze_entry.name.replace(".json", "")
                            )
                        else:
                            logger.debug(
                                "Skipping non-freeze entry: %s"
                                % freeze_entry.name
                            )
                            continue
                        freeze_quota_files[freeze_client_id] = freeze_entry.path
                t2 = time.time()
                msg = "Scanned %s freeze quota (%d) %s %r in %d secs" % (
                    quota_fs,
                    quota_mtime,
                    quota_datestr,
                    freeze_path,
                    (t2 - t1),
                )
                logger.info(msg)
                if verbose:
                    print(msg)

    # Generate accounting from user bytes, vgrid bytes and freeze bytes

    vgrids_accounted = []
    for client_id, user_quota_filepath in user_quota_files.items():
        # Init user accounting
        peers = peers_map.get(client_id, {}).get("peers", {})
        ext_users = peers_map.get(client_id, {}).get("ext_users", {})
        accounting[client_id] = __init_accounting_entry(
            peers=peers, ext_users=ext_users
        )
        # Extract user bytes
        if user_quota_filepath.endswith(".pck"):
            user_quota = unpickle(user_quota_filepath, configuration)
        elif user_quota_filepath.endswith(".json"):
            user_quota = load_json(
                user_quota_filepath, configuration.logger, convert_utf8=False
            )
        else:
            msg = "Invalid user quota file: %r" % user_quota_filepath
            logger.error(msg)
            if verbose:
                print("ERROR: %s" % msg)
            retval = False
            continue
        try:
            accounting[client_id]["user_bytes"] = user_quota["bytes"]
        except Exception as err:
            accounting[client_id]["user_bytes"] = 0
            msg = "Failed to load user quota: %r, error: %s" % (
                user_quota_filepath,
                err,
            )
            logger.error(msg)
            if verbose:
                print("ERROR: %s" % msg)
            retval = False
            continue

        # Extract vgrid bytes for user 'client_id'

        for vgrid_name in owned_vgrid.get(client_id, []):
            vgrid_quota_filepath = vgrid_quota_files.get(vgrid_name, "")
            if not os.path.exists(vgrid_quota_filepath):
                if verbose:
                    # NOTE: Legacy vgrids are accounted at by top-vgrid
                    vgrid_array = vgrid_name.split("/")
                    legacy_vgrid = os.path.join(
                        configuration.vgrid_files_home, vgrid_name
                    )
                    if not os.path.isdir(legacy_vgrid) or len(vgrid_array) == 1:
                        msg = "Missing quota for vgrid: %r" % vgrid_name
                        logger.warning(msg)
                        if verbose:
                            print("WARNING: %s" % msg)
                continue
            if vgrid_quota_filepath.endswith(".pck"):
                vgrid_quota = unpickle(vgrid_quota_filepath, configuration)
            elif vgrid_quota_filepath.endswith(".json"):
                vgrid_quota = load_json(
                    vgrid_quota_filepath,
                    configuration.logger,
                    convert_utf8=False,
                )
            else:
                msg = "Invalid vgrid quota file: %r" % vgrid_quota_filepath
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue
            try:
                accounting[client_id]["vgrid_bytes"][vgrid_name] = vgrid_quota[
                    "bytes"
                ]
            except Exception as err:
                accounting[client_id]["vgrid_bytes"][vgrid_name] = 0
                msg = "Failed to load vgrid quota: %r, error: %s" % (
                    vgrid_quota_filepath,
                    err,
                )
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue
            # NOTE: Used for verification of
            #       that all vgrids was taken into account
            vgrids_accounted.append(vgrid_name)

    # Check if all vgrids were accounted for

    for vgrid_name in vgrid_quota_files:
        if vgrid_name not in vgrids_accounted:
            vgridowner = ""
            for owner, owned_vgrids in owned_vgrid.items():
                if vgrid_name in owned_vgrids:
                    vgridowner = owner
                    break
            msg = "no accounting for vgrid: %r, missing owner?: %r" % (
                vgrid_name,
                vgridowner,
            )
            logger.warning(msg)
            if verbose:
                print("WARNING: %s" % msg)

    # Extract freeze bytes

    for freeze_name, freeze_quota_filepath in freeze_quota_files.items():
        # Extract client_id from legacy freeze archive format
        if freeze_name.startswith("archive-"):
            legacy_freeze_meta_filepath = os.path.join(
                configuration.freeze_home, freeze_name, "meta.pck"
            )
            legacy_freeze_meta = unpickle(
                legacy_freeze_meta_filepath, configuration.logger
            )
            if not legacy_freeze_meta:
                msg = "Missing metadata for archive: %r" % freeze_name
                logger.warning(msg)
                if verbose:
                    print("WARNING: %s" % msg)
                continue
            client_id = legacy_freeze_meta.get("CREATOR", "")
            if not client_id:
                msg = (
                    "Failed to extract client_id from: %r"
                    % legacy_freeze_meta_filepath
                )
                logger.error(msg)
                if verbose:
                    print("ERROR: %s" % msg)
                retval = False
                continue
        else:
            client_id = freeze_name

        # Load freeze quota

        freeze_bytes = 0
        if freeze_quota_filepath.endswith(".pck"):
            freeze_quota = unpickle(freeze_quota_filepath, configuration)
        elif freeze_quota_filepath.endswith(".json"):
            freeze_quota = load_json(
                freeze_quota_filepath, configuration.logger, convert_utf8=False
            )
        else:
            msg = "Invalid freeze quota file: %r" % freeze_quota_filepath
            logger.error(msg)
            if verbose:
                print("ERROR: %s" % msg)
            retval = False
            continue
        try:
            freeze_bytes = int(freeze_quota["bytes"])
        except Exception as err:
            freeze_bytes = 0
            msg = "Failed to fetch freeze quota: %r, error: %s" % (
                freeze_quota_filepath,
                err,
            )
            logger.error(msg)
            if verbose:
                print("ERROR: %s" % msg)
            retval = False
            continue

        if freeze_bytes > 0:
            freeze_accounting = accounting.get(client_id, None)
            if freeze_accounting is None:
                msg = "added missing archive user: %r : %d" % (
                    client_id,
                    freeze_bytes,
                )
                logger.warning(msg)
                if verbose:
                    print("WARNING: %s" % msg)
                accounting[client_id] = __init_accounting_entry()
                freeze_accounting = accounting[client_id]
            freeze_accounting["freeze_bytes"] += freeze_bytes

    # Save accounting result

    accounting_filepath = os.path.join(
        configuration.accounting_home, "%s.pck" % result["timestamp"]
    )
    status = pickle(result, accounting_filepath, configuration.logger)
    if status:
        latest = os.path.join(configuration.accounting_home, "latest")
        status = make_symlink(accounting_filepath, latest, logger, force=True)
    if not status:
        retval = False

    return retval


def human_readable_filesize(
    filesize, decimals=3, locale_format=None, si_byte_format=False
):
    """Return human readable filesize for non-negative int value below 2**90"""
    result = 0
    # NOTE: False matches 'filesize == 0' unless we are careful here
    if isinstance(filesize, bool) or isinstance(filesize, float):
        return "NaN"
    if filesize == 0:
        return "0 B"
    try:
        if locale_format:
            org_locale = locale.getlocale(locale.LC_ALL)
            locale.setlocale(locale.LC_ALL, locale_format)
        p = int(math.floor(math.log(filesize, 2) / 10))
        if si_byte_format:
            value = filesize / math.pow(1000, p)
            desc = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"][p]
        else:
            value = filesize / math.pow(1024, p)
            desc = [
                "B",
                "KiB",
                "MiB",
                "GiB",
                "TiB",
                "PiB",
                "EiB",
                "ZiB",
                "YiB",
            ][p]
        result = locale.format_string("%.*f %s", (decimals, value, desc))
        if locale_format:
            locale.setlocale(locale.LC_ALL, org_locale)
        return result
    except (ValueError, TypeError, IndexError) as err:
        return "NaN"


def get_usage(
    configuration,
    userlist=None,
    timestamp=0,
    decimals=3,
    si_byte_format=False,
    verbose=False,
):
    """Generate and return 'storage' usage"""
    # Load accounting if it exists
    logger = configuration.logger
    if userlist is None:
        userlist = []
    if timestamp == 0:
        accounting_filepath = os.path.join(
            configuration.accounting_home, "latest"
        )
    else:
        accounting_filepath = os.path.join(
            configuration.accounting_home, "%s.pck" % timestamp
        )
    data = unpickle(accounting_filepath, configuration.logger)
    if not data:
        msg = "Failed to load accounting data from: %r" % accounting_filepath
        logger.error(msg)
        if verbose:
            print("ERROR: %s" % msg)
        return None

    accounting = data.get("accounting", {})

    # Do not show external users as main accounts unless requested
    # or if the user act as both peer and external user

    ext_users = []
    peer_users = []
    skip_ext_users = []
    for values in accounting.values():
        ext_users.extend(list(values.get("ext_users", {})))
        peer_users.extend(list(values.get("peers", {})))
    skip_ext_users = [
        user
        for user in ext_users
        if user not in userlist and user not in peer_users
    ]

    # Create accounting report

    account_usage = {}
    for username, values in accounting.items():
        # NOTE: If specific users are requested
        #       then only create report for those
        # NOTE: We need to summarize usage for all users
        #       in order to map for external user account usage
        create_reports = True
        if userlist and username not in userlist:
            create_reports = False
        total_bytes = 0

        # Home usage

        home_bytes = values.get("user_bytes", 0)
        total_bytes += home_bytes
        home_report = ""
        if create_reports:
            home_bytes_human = human_readable_filesize(
                home_bytes, decimals=decimals
            )
            home_report += "Home usage: %s" % home_bytes_human
            if si_byte_format:
                home_si_bytes_human = human_readable_filesize(
                    home_bytes, decimals=decimals, si_byte_format=True
                )
                home_report += " / %s" % home_si_bytes_human

        # Freeze archive usage

        freeze_bytes = values.get("freeze_bytes", 0)
        total_bytes += freeze_bytes
        freeze_report = ""
        if create_reports and freeze_bytes > 0:
            freeze_bytes_human = human_readable_filesize(
                freeze_bytes, decimals=decimals
            )
            freeze_report += "Archive usage: %s" % freeze_bytes_human
            if si_byte_format:
                freeze_si_bytes_human = human_readable_filesize(
                    freeze_bytes, decimals=decimals, si_byte_format=True
                )
                freeze_report += " / %s" % freeze_si_bytes_human

        # Vgrid usage

        vgrid_report = ""
        vgrid_total = 0
        for vgrid_name, vgrid_bytes in values.get("vgrid_bytes", {}).items():
            vgrid_total += vgrid_bytes
            if create_reports:
                vgrid_bytes_human = human_readable_filesize(
                    vgrid_bytes, decimals=decimals
                )
                vgrid_report += "\n - %s: %s" % (vgrid_name, vgrid_bytes_human)
                if si_byte_format:
                    vgrid_si_bytes_human = human_readable_filesize(
                        vgrid_bytes,
                        decimals=decimals,
                        si_byte_format=True,
                    )
                    vgrid_report += " / %s" % vgrid_si_bytes_human

        if vgrid_report:
            vgrid_total_human = human_readable_filesize(
                vgrid_total, decimals=decimals
            )
            if not si_byte_format:
                vgrid_report_header = "%s usage (total: %s)" % (
                    configuration.site_vgrid_label,
                    vgrid_total_human,
                )
            else:
                vgrid_total_si_bytes_human = human_readable_filesize(
                    vgrid_total, decimals=decimals, si_byte_format=True
                )
                vgrid_report_header = "%s usage (total: %s / %s)" % (
                    configuration.site_vgrid_label,
                    vgrid_total_human,
                    vgrid_total_si_bytes_human,
                )
            vgrid_report = "%s%s" % (vgrid_report_header, vgrid_report)
        total_bytes += vgrid_total

        # Create account usage entry

        account_usage[username] = {
            "total_bytes": total_bytes,
            "home_total": home_bytes,
            "vgrid_total": vgrid_total,
            "freeze_total": freeze_bytes,
            "ext_users_total": 0,
            "total_report": "",
            "home_report": home_report,
            "freeze_report": freeze_report,
            "vgrid_report": vgrid_report,
            "ext_users_report": "",
            "peers_report": "",
        }

    # Create external users report
    # NOTE: We need total bytes and therefore we need the above full report
    #       generated before external users report

    for username, values in accounting.items():
        # NOTE: If specific users are requested
        #       then only create result for those
        if userlist and username not in userlist:
            continue
        # Create ext_users report
        ext_users = values.get("ext_users", {})
        peers = values.get("peers", {})
        if not ext_users:
            continue
        if ext_users and peers:
            msg = "User %r acts as both peer and external user" % username
            logger.warning(msg)
            if verbose:
                print("WARNING: %s" % msg)

        # Create external users report

        ext_users_report = ""
        ext_users_total = 0
        for ext_userid in ext_users:
            ext_user_total_bytes = account_usage.get(ext_userid, {}).get(
                "total_bytes", 0
            )
            ext_users_total += ext_user_total_bytes
            ext_user_total_bytes_human = human_readable_filesize(
                ext_user_total_bytes, decimals=decimals
            )
            if verbose:
                ext_users_report += "\n - %s" % ext_userid
            ext_user_dict = distinguished_name_to_user(ext_userid)

            ext_users_report += "\n - %s : %s : %s : %s : %s" % (
                ext_user_dict.get("full_name", ""),
                ext_user_dict.get("email", ""),
                ext_user_dict.get("organization", ""),
                ext_user_dict.get("country", ""),
                ext_user_total_bytes_human,
            )
            if si_byte_format:
                ext_user_total_si_bytes_human = human_readable_filesize(
                    ext_user_total_bytes,
                    decimals=decimals,
                    si_byte_format=True,
                )
                ext_users_report += " / %s" % ext_user_total_si_bytes_human
        if ext_users_report:
            ext_users_total_human = human_readable_filesize(
                ext_users_total, decimals=decimals
            )
            if not si_byte_format:
                ext_users_report_header = (
                    "External users usage (total: %s)" % ext_users_total_human
                )
            else:
                ext_users_total_si_bytes_human = human_readable_filesize(
                    ext_users_total,
                    decimals=decimals,
                    si_byte_format=True,
                )
                ext_users_report_header = (
                    "External users usage (total: %s / %s)"
                    % (ext_users_total_human, ext_users_total_si_bytes_human)
                )
            ext_users_report = "%s%s" % (
                ext_users_report_header,
                ext_users_report,
            )

        account_usage[username]["ext_users_total"] = ext_users_total
        account_usage[username]["ext_users_report"] = ext_users_report
        account_usage[username]["total_bytes"] += ext_users_total

        # Create peers report

        peers_report = ""
        for peer in peers:
            peers_report += "\n - %s" % peer
        if peers_report:
            peers_report = "Accepted by the following peer:%s" % peers_report
        account_usage[username]["peers_report"] = peers_report

    # Create total usage report for each user

    for usage in account_usage.values():
        usage["total_report"] = "Total usage: %s" % human_readable_filesize(
            usage["total_bytes"], decimals=decimals
        )
        if si_byte_format:
            total_si_bytes_human = human_readable_filesize(
                usage["total_bytes"],
                decimals=decimals,
                si_byte_format=True,
            )
            usage["total_report"] += " / %s" % total_si_bytes_human

    # External users are accounted for by their peer
    # unless the external user also act as a peer

    result = {}
    result["timestamp"] = data.get("timestamp", 0)
    result["quota"] = data.get("quota", {})
    result["accounting"] = {
        username: values
        for username, values in account_usage.items()
        if not userlist
        or username in userlist
        and username not in skip_ext_users
    }
    return result
