# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqinfo - common code for structured requests
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


"""
The reqinfo library file contains common types and routines for handling
of structured requests which are identified by a type/operation pair.

These pair of values are used to identify the request and the resulting
type can be used as the basis for dispatching such requests to handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from mig.shared.base import distinguished_name_to_user
from mig.shared.defaults import keyword_none
from mig.shared.safeinput import (
    REJECT_UNSET,
    valid_request_operation,
    valid_request_type,
    validated_input,
)

REQUEST_INFO_FIELDS = {
    "type": REJECT_UNSET,
    "operation": REJECT_UNSET,
}
REQUEST_INFO_FIELDS_TYPE = {
    "type": valid_request_type,
    "operation": valid_request_operation,
}
REQUEST_INFO_FIELDS_VALUE = {
    "operation": valid_request_operation,
}
REQUEST_INFO_METHOD_BY_OPERATION = {
    "create": "POST",
    "read": "GET",
    "update": "PUT",
    "delete": "POST",  # opt to process deletions via a POST to a suffixed route
}


class RequestInfoCreateError(Exception):
    """Raised when RequestInfo.create fails."""

    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__(msg)


class RequestDataRejectedError(Exception):
    """Raised when input validation for request data fails, and rejects parts
    of the request data. The rejected entries are stored in the error instance.
    """

    def __init__(self, rejected: dict[str, Any]) -> None:
        self.rejected = rejected
        super().__init__(rejected)


T = TypeVar("T")


@dataclass
class RequestInfo:
    """A named type representing a request to an endpoint."""

    method: str
    route: str
    full_route: str
    csrf_token: str | None
    client_id: str
    client_email: str | None
    request_type: str
    request_package: str
    request_data: dict[str, Any]
    normalized_request_data: dict[str, Any] | None = None

    @property
    def args(self) -> dict[str, Any]:
        """Property that returns the normalized request data if it exists,
        otherwise it returns the unnormalized request data.
        """

        if self.normalized_request_data is None:
            return self.request_data
        else:
            return self.normalized_request_data

    def arg_value(self, arg: str, type_of_value: type[T]) -> T:
        """
        Return the value for a particular argument forced to a particular type.
        """

        args = self.normalized_request_data
        if args is None:
            args = self.request_data

        if arg not in args:
            return type_of_value()
        value = args[arg]
        assert isinstance(value, type_of_value)
        return value

    @classmethod
    def create(
        cls,
        client_id: str,
        operation: str,
        sent_type: str,
        request_data: dict[str, Any],
    ):
        """
        Creates and returns a RequestInfo instance from the supplied arguments
        that can be used to discover the requested endpoint handler and deliver
        the supplied payload from the given client to said handler.

        Args:
            client_id: The distinguished name of the authenticated client.
            operation: is expected to specify which type of request the client
                made from the available REQUEST_INFO_METHOD_BY_OPERATION.
            sent_type: specifies the expected lookup package key and the associated
                route handler path that is associated with the request.

                An example of this could be a sent_type that is set to
                `migux_apps_peers__new` that is then transformed into
                the RequestInfo constructor values:

                request_package = 'migux_apps_peers'
                request_type = '/new'

                These can then be used to lookup the expected request
                handler function via the package name and the type of request.
            request_data: the request payload from the client
        Returns:
            The created request info object.
        Raises:
            RequestInfoCreateError: if an error occurred during creation.

        """
        # convert payload supplied type and operation values that are used as
        # a compromise for allowing multiple routes to be handled by a single
        # endpoint into a more modern style route
        method = REQUEST_INFO_METHOD_BY_OPERATION.get(operation, keyword_none)
        try:
            request_package_unconverted, *request_types = sent_type.split("__")
        except ValueError as exc:
            raise RequestInfoCreateError(
                "could not parse request package and request types"
            ) from exc

        request_package = request_package_unconverted.replace("_", ".")
        if request_package == "":
            local_package_name = request_types.pop(0)
            request_package = ".%s" % (local_package_name,)
        request_type = "/".join(request_types)

        # Extract csrf token from request data if present
        csrf_token = request_data.pop("csrf_token", None)
        if isinstance(csrf_token, list):
            csrf_token = csrf_token[0]

        user = distinguished_name_to_user(client_id)
        return cls(
            method=method,
            route="{} /{}".format(method, request_type),
            full_route="/{}/{}".format(request_package, request_type),
            csrf_token=csrf_token,
            client_id=client_id,
            client_email=user.get("email"),
            request_type=request_type,
            request_package=request_package,
            request_data=request_data,
        )


def coalesce_request(
    request_data: dict[str, Any], *, client_id: str
) -> RequestInfo:
    """Takes a raw input requests and bundles it into a named type.

    Raises:
        RequestInfoCreateError: if an error occurred during request info
            creation.
        RequestDataRejectedError: if any request data is rejected.
    """
    # Exclude output_format from the data we pass on to handlers - however,
    # the output path later reads that hint so we will operate on a copy and
    # leave the original input dictionary (which is the only way of hinting
    # the output format to the output path) unchanged.
    request_data = dict(request_data)
    try:
        del request_data["output_format"]
    except KeyError:
        pass

    data = {
        "type": unlistify(request_data.pop("type", "")),
        "operation": unlistify(request_data.pop("operation", "")),
    }
    accepted, rejected = validated_input(
        data,
        REQUEST_INFO_FIELDS,
        type_override=REQUEST_INFO_FIELDS_TYPE,
        value_override=REQUEST_INFO_FIELDS_VALUE,
        list_wrap=True,
    )
    if rejected:
        raise RequestDataRejectedError(rejected)

    # Use the "operation" and "type" keys from accepted given
    # values may have been altered by the validation logic.
    operation = accepted["operation"][0]
    sent_type = accepted["type"][0]

    # What remains now in request_data are key/value pairs that make up the
    # rest of the structured payload. It is up to individual handlers to
    # validate this payload, so move to bundle the request information
    # and optionally post-process-the request data (note due to the way
    # user_arguments_dict is handled values will be wrapped in lists and
    # any type information about the values themselves must be remade.

    return RequestInfo.create(client_id, operation, sent_type, request_data)


def unwrap_coalesce_request_exceptions(err: Exception) -> Any:
    """Unwraps known exceptions from coalesce_request for error formatting."""

    if isinstance(err, RequestInfoCreateError):
        return err.msg
    elif isinstance(err, RequestDataRejectedError):
        return err.rejected
    else:
        return err


def booleanify(value):
    """
    Convert a string representing a bool to a boolean type.
    """

    return str(value).lower() in ("true", "1", "yes")


def uncommaify(value):
    """
    Convert a comma separated string to individual items.
    """
    return unconcatify(value, ",")


def unconcatify(value, sep):
    """
    Convert a delimited string to individual items.
    """

    assert isinstance(value, str)
    result = value.split(sep)
    if len(result) == 1 and result[0] == "":
        return []
    return result


def unlistify(value):
    """
    Convert a possibly array wrapped value to a simple value.
    """

    if isinstance(value, list):
        return value[0]
    return value


def unlistify_dict(value):
    """
    Bulk convert a dictionary that might contain array wrapped values.
    """

    for k, v in value.items():
        value[k] = unlistify(v)
    return value
