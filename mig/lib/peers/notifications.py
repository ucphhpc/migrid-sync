# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# notifications - email/notification helpers for peers
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

"""Email/notification helpers for peers management."""

import os

from mig.shared.defaults import keyword_auto, peers_fields
from mig.shared.url import urlencode


def create_peers_notify_msg(
    header_title, header_action, header_from, body_identifer, peers
):
    """A helper function to create a peers notification mesage"""
    notify_header = "%s %s by %s" % (
        header_title,
        header_action,
        header_from,
    )

    notify_peers = [
        """
            Peer: %s
            Expire: %s
        """ % (peer_dn, peer_dict["expire"])
        for peer_dn, peer_dict in peers.items()
    ]
    notify_dict = {
        "action": header_action,
        "body_identifer": body_identifer,
        "peers": "".join(notify_peers),
    }
    notify_msg = """
        Received %(action)s from %(body_identifer)s

        Peers:
        %(peers)s
    """ % notify_dict

    return {"header": notify_header, "msg": notify_msg}


def create_peer_invitation_msg(
    configuration, client_name, client_email, peer_user, kind
):
    """Create an invitation email message (header + body) for a single peer.

    Returns a dict with 'header' and 'msg' keys containing the email header
    and body respectively.
    """
    _logger = configuration.logger
    short_title = configuration.short_title
    admin_email = configuration.admin_email
    email_header = "%s Invitation" % short_title

    peer_url = os.path.join(
        configuration.migserver_https_sid_url, "cgi-sid", "reqoid.py"
    )

    peer_req = {}
    for field in peers_fields:
        peer_req[field] = peer_user.get(field, "")

    for explicit_field in configuration.site_peers_explicit_fields:
        field_name = "peers_%s" % explicit_field
        if explicit_field == "full_name":
            peer_req[field_name] = client_name
        elif explicit_field == "email":
            peer_req[field_name] = client_email
        else:
            _logger.warning(
                "unhandled explicit peers field: %s" % explicit_field
            )
            continue

    peer_req["comment"] = "Invited by %s (%s) for %s purposes" % (
        client_name,
        client_email,
        kind,
    )
    peer_req["ro_fields"] = keyword_auto
    peer_url += "?%s" % urlencode(peer_req)

    peer_name = peer_user.get("full_name", "")
    email_msg_template = """Hi %%s,
This is an automatic email sent on behalf of %s who vouched for you to get a
user account on %s. You can accept the invitation by going to
%%s
entering a password of your choice and submitting the form.
If you do not want a user account you can safely ignore this email.

We would be grateful if you report any abuse of the invitation system to the
site administrators (%s).
""" % (client_name, short_title, admin_email)

    email_msg = email_msg_template % (peer_name, peer_url)
    return {"header": email_header, "msg": email_msg}
