#
# --- BEGIN_HEADER ---
#
# validation - validation of account requests api input
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

"""Implements validation functions for the account requests API."""

from mig.shared.safeinput import InputException, valid_job_id_pattern


def validate_account_request_ids(accreq_ids: list[str]) -> bool:
    """Validate all given account request IDs.

    Args:
        accreq_ids: Account request IDs to validate.
    
    Return:
        True if all account request IDs are valid, False otherwise.
    """
    return all(
        validate_account_request_id(accreq_id) for accreq_id in accreq_ids
    )


def validate_account_request_id(accreq_id: str) -> bool:
    """Validate all given account request IDs.

    Args:
        accreq_id: Account request ID to validate.
    
    Return:
        True if the account request ID is valid, False otherwise.
    """
    try:
        valid_job_id_pattern(accreq_id)
    except InputException:
        return False
    else:
        return True
