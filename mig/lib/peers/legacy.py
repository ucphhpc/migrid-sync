# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# legacy - legacy functions for the pre USER_INTERFACE V4 peers feature
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

"""Legacy functions for the pre USER_INTERFACE V4 peers feature."""

import os

from mig.lib.peers.permissions import peers_permit_allowed
from mig.lib.peers.storage import (
    add_pending_peers_to_client,
    remove_pending_peers_from_client,
)
from mig.shared.base import (
    canonical_user,
    distinguished_name_to_user,
    fill_distinguished_name,
    fill_user,
    mask_creds,
)
from mig.shared.defaults import (
    gdp_distinguished_field,
    keyword_auto,
    peers_fields,
)
from mig.shared.fileio import load
from mig.shared.notification import notify_user
from mig.shared.safeinput import REJECT_UNSET, html_escape, validated_input
from mig.shared.useradm import default_search, search_users, user_account_notify
from mig.shared.userdb import default_db_path
from mig.shared.validstring import valid_email_addresses


def manage_pending_peers(configuration, client_id, action, change_list):
    """
    Helper to manage changes to pending peers list of client_id

    change_list: [(peer_dn, peer_dict)]
    """
    if action not in ["add", "remove"]:
        raise ValueError(
            "unsupported action in manage pending peers: %s" % action
        )

    if action == "add":
        return add_pending_peers_to_client(
            configuration, client_id, change_list
        )

    # Remove only needs a list of peer_dns
    remove_list = [change[0] for change in change_list]
    return remove_pending_peers_from_client(
        configuration, client_id, remove_list
    )


def parse_peers_form(configuration, raw_lines, csv_sep):
    """Parse CSV form of peers into a list of peers"""
    _logger = configuration.logger
    header = None
    peers = []
    err = []
    for line in raw_lines.split("\n"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [i.strip() for i in line.split(csv_sep)]
        if not header:
            missing = [i for i in peers_fields if i not in parts]
            if missing:
                err.append(
                    "Parsed peers did NOT contain required field(s): %s"
                    % ", ".join(missing)
                )
            header = parts
            continue
        if len(header) != len(parts):
            _logger.warning(
                "skip peers line with mismatch in field count: %s" % line
            )
            err.append(
                "Skip peers line not matching header format: %s"
                % html_escape(line + " vs " + csv_sep.join(header))
            )
            continue
        raw_user = dict(zip(header, parts))
        # IMPORTANT: extract ONLY peers fields and validate to avoid abuse
        peer_user = dict([(i, raw_user.get(i, "")) for i in peers_fields])
        defaults = dict([(i, REJECT_UNSET) for i in peer_user])
        accepted, rejected = validated_input(
            peer_user, defaults, list_wrap=True
        )
        if rejected:
            _logger.warning(
                "skip peer with invalid value(s): %s (%s)" % (line, rejected)
            )
            unsafe_err = " , ".join(
                ["%s=%r" % pair for pair in peer_user.items()]
            )
            unsafe_err += ". Rejected values: " + ", ".join(rejected)
            err.append(
                "Skip peer user with invalid value(s): %s"
                % html_escape(unsafe_err)
            )
            continue
        peers.append(canonical_user(configuration, peer_user, peers_fields))
    _logger.debug("parsed form into peers: %s" % peers)
    return (peers, err)


def parse_peers(configuration, peers_content, peers_format, csv_sep=";"):
    """Parse provided peer formats into a list of peer users.
    Please note that peers_content is the accepted list of input values.
    """
    _logger = configuration.logger
    if "userid" == peers_format:
        # NOTE: Enter Peers packs fields into full DNs handled here
        raw_peers = peers_content
        return parse_peers_userid(configuration, raw_peers)
    elif "csvform" == peers_format:
        # NOTE: first merge the individual textarea(s) from Import Peers
        raw_peers = "\n".join(peers_content)
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "csvupload" == peers_format:
        # TODO: extract upload
        raw_peers = ""
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "csvurl" == peers_format:
        # TODO: fetch URL contents
        raw_peers = ""
        return parse_peers_form(configuration, raw_peers, csv_sep)
    elif "fields" == peers_format:
        # TODO: extract fields
        raw_peers = []
        return parse_peers_userid(configuration, raw_peers)
    else:
        _logger.error("unknown peers format: %s" % peers_format)
        return ([], "unknown peers format: %s" % peers_format)


def parse_peers_userid(configuration, raw_entries):
    """Parse list of user IDs into a list of peers"""
    _logger = configuration.logger
    peers = []
    err = []
    for entry in raw_entries:
        raw_user = distinguished_name_to_user(entry.strip())
        missing = [i for i in peers_fields if i not in raw_user]
        if missing:
            err.append(
                "Parsed peers did NOT contain required field(s): %s"
                % ", ".join(missing)
            )
            continue
        # IMPORTANT: extract ONLY peers fields and validate to avoid abuse
        peer_user = dict(
            [(i, raw_user.get(i, "").strip()) for i in peers_fields]
        )
        defaults = dict([(i, REJECT_UNSET) for i in peer_user])
        accepted, rejected = validated_input(
            peer_user, defaults, list_wrap=True
        )
        if rejected:
            _logger.warning(
                "skip peer with invalid value(s): %s : %s" % (entry, rejected)
            )
            unsafe_err = " , ".join(
                ["%s=%r" % pair for pair in peer_user.items()]
            )
            unsafe_err += ". Rejected values: " + ", ".join(rejected)
            err.append(
                "Skip peer user with invalid value(s): %s"
                % html_escape(unsafe_err)
            )
            continue
        peers.append(canonical_user(configuration, peer_user, peers_fields))
    _logger.debug("parsed user id into peers: %s" % peers)
    return (peers, err)


def peer_account_req(
    req_id,
    configuration,
    target_id,
    admin_copy=True,
    user_copy=False,
    include_auto_email=True,
    auth_type="oid",
    _notify_user=notify_user,
):
    """Helper to request peer accept for a pending account request"""
    # TODO: enable user_copy if it can be clearly marked only CC?
    _logger = configuration.logger
    _logger.info(
        "request account peer for %s with peer %s" % (req_id, target_id)
    )
    # NOTE: conf_path accepts configuration object
    conf_path = configuration
    db_path = default_db_path(configuration)
    req_path = os.path.join(configuration.user_pending, req_id)
    regex_keys = []
    search_filter = default_search()
    # IMPORTANT: Default to nobody to avoid spam if called without target_id
    search_filter["distinguished_name"] = ""
    try:
        req_dict = load(req_path)
    except Exception as err:
        err_msg = "peer account request %s extraction failed: %s" % (
            req_id,
            err,
        )
        _logger.error(err_msg)
        return (False, err_msg)
    # IMPORTANT: do NOT log credentials
    _logger.debug("peer account request: %s" % mask_creds(req_dict))
    if "distinguished_name" not in req_dict:
        fill_distinguished_name(req_dict)
    fill_user(req_dict)
    peer_id = req_dict["distinguished_name"]
    if target_id == keyword_auto:
        if "email" in configuration.site_peers_explicit_fields:
            # Try peers_email with fallback to comment
            target_str = req_dict.get("peers_email", req_dict["comment"])
        else:
            target_str = req_dict["comment"]
    else:
        target_str = target_id
    peer_emails = valid_email_addresses(configuration, target_str)
    if peer_emails[1:]:
        regex_keys.append("email")
        search_filter["email"] = "(" + "|".join(peer_emails) + ")"
    elif peer_emails:
        search_filter["email"] = peer_emails[0]
    elif search_filter["distinguished_name"]:
        search_filter["email"] = "*"
    else:
        search_filter["email"] = ""

    # If email is provided or detected DN may be almost anything
    if search_filter["email"] and not search_filter["distinguished_name"]:
        search_filter["distinguished_name"] = "*emailAddress=*"

    # Use email from user DB by default
    raw_targets = {}
    if include_auto_email:
        raw_targets["email"] = [keyword_auto]

    extra_copies = []
    if user_copy and req_dict.get("email", ""):
        extra_copies.append(req_dict["email"])

    _logger.debug(
        "handling peer %s request to users matching %s"
        % (peer_id, search_filter)
    )

    # Lookup users to request formal acceptance from
    _, hits = search_users(
        search_filter, conf_path, db_path, False, regex_match=regex_keys
    )
    gdp_prefix = "%s=" % gdp_distinguished_field
    if len(hits) < 1:
        # IMPORTANT: do NOT log credentials
        _logger.error(
            "no target users to request peer acceptance from: %s"
            % mask_creds(req_dict)
        )
        return (False, "no valid target peer acceptance users")
    elif len(hits) > 3:
        # IMPORTANT: do NOT log credentials
        _logger.error(
            "refuse to request peer acceptance from %d users for %s"
            % (len(hits), mask_creds(req_dict))
        )
        return (False, "too many requested peer acceptance users")
    else:
        _logger.debug(
            "request peer acceptance from users: %s"
            % "\n".join([i[0] for i in hits])
        )

    notify_count, all_sent, all_errors = 0, True, []
    for user_id, user_dict in hits:
        _logger.debug("request peer - check for %s" % user_id)
        if configuration.site_enable_gdp and user_id.split("/")[-1].startswith(
            gdp_prefix
        ):
            _logger.debug(
                "skip peer request for GDP project account: %s" % user_id
            )
            continue
        if peer_id == user_id:
            _logger.warning("skip peer request for self: %s" % user_id)
            continue
        if not peers_permit_allowed(configuration, user_dict):
            _logger.warning(
                "skip peer request for %s without permission" % user_id
            )
            continue
        if not manage_pending_peers(
            configuration, user_id, "add", [(peer_id, req_dict)]
        ):
            _logger.error(
                "Failed to forward accept peer %s to %s" % (peer_id, user_id)
            )
            continue

        _logger.info("added peer request from %s to %s" % (peer_id, user_id))

        _, _, full_name, _, addresses, errors = user_account_notify(
            user_id,
            raw_targets,
            conf_path,
            db_path,
            False,
            admin_copy,
            extra_copies,
        )
        if errors:
            _logger.warning(
                "peer accept address lookup errors for %s: %s"
                % (user_id, "\n".join(errors))
            )
            continue

        notify_dict = {"JOB_ID": "NOJOBID", "USER_CERT": user_id, "NOTIFY": []}
        for proto, address_list in addresses.items():
            for address in address_list:
                notify_dict["NOTIFY"].append("%s: %s" % (proto, address))

        # Don't actually send unless requested
        if not raw_targets and not admin_copy:
            _logger.warning(
                "no targets for request accept peer %s from %s"
                % (peer_id, user_id)
            )
            continue
        _logger.info(
            "send request accept peer message for '%s' to:\n%s"
            % (peer_id, "\n".join(notify_dict["NOTIFY"]))
        )
        notify_count += 1
        peers_details = ""
        for peers_field in configuration.site_peers_explicit_fields:
            field_name = "peers_%s" % peers_field
            peers_details += """Peers contact %s(s): %s
""" % (peers_field.replace("_", " "), req_dict.get(field_name, ""))
        peers_details += """Comment: %(comment)s
""" % req_dict
        send_status, send_errors = _notify_user(
            notify_dict,
            [
                peer_id,
                configuration.short_title,
                "peeraccount",
                peers_details,
                req_dict["email"],
                user_id,
            ],
            "SENDREQUEST",
            _logger,
            "",
            configuration,
        )

        if send_status:
            _logger.debug(
                "sent accept peer request for '%s' to:\n%s"
                % (user_id, req_dict["email"])
            )
        else:
            _logger.warning(
                "notify failed for peer request recipient(s): %s"
                % "\n".join(send_errors)
            )
            all_sent = False
            all_errors += send_errors

    had_email_to_send = len(raw_targets)

    if had_email_to_send and notify_count < 1:
        err_msg = "no valid actual peers found for %s" % req_path
        _logger.warning(err_msg)
        return (False, err_msg)
    elif all_sent:
        _logger.info(
            "sent %d accept peer requests for %s" % (notify_count, req_path)
        )
        return (True, "")
    else:
        err_msg = "one or more accept peer requests failed for %s" % req_path
        _logger.warning(err_msg)
        return (False, err_msg)
