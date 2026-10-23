#
# --- BEGIN_HEADER ---
#
#
# permissions - Account request management permissions.
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#
"""Account request management permissions."""

from mig.shared.findtype import is_admin


def check_account_requests_permit(configuration: object, user_dn: str):
    """Check if the requesting client is permitted to manage account requests.

    Returns True if permitted, False otherwise.
    """
    return is_admin(user_dn, configuration, None)
