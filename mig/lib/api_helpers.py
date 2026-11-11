#
# --- BEGIN_HEADER ---
#
# api_helpers - General helper function for REST-like API handlers
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

"""General helper functions that can be used by REST-like API handlers."""


from typing import Any, TypedDict


class HandlerExitResponse(TypedDict):
    """A definition of the non-data part of the JSON response."""

    status: int
    message: str | None
    error: str | None


HandlerResponse = tuple[HandlerExitResponse, dict[str, Any]]


def create_handler_response(
    status: int,
    message: str | None = None,
    error: str | None = None,
    **ui_response_kwargs: Any,
) -> HandlerResponse:
    """Utility function to format request handler JSON response.

    :param status: An HTTP status code.
    :param message: A message to return in the response.
    :param error: An error to return in the response.
    :param ui_response_kwargs: Key-value arguments that will be available in the
        response object under the 'data' key.
    """
    return (
        {"status": status, "message": message, "error": error},
        ui_response_kwargs,
    )
