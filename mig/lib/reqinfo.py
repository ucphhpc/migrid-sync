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

from types import SimpleNamespace

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


def _passthrough(value):
    """Returns its single input value unchanged."""
    return value


class _RequestInfo(SimpleNamespace):
    """A named type representing a request to an endpoint."""

    @property
    def args(self):
        """
        Return the request arguments. If previously overridden (by virtue of
        being converted) return the value that was set, otherwise return the
        request data unchanged.
        """

        _args = getattr(self, "_args", None)
        if _args is None:
            self._args = self._request_data
        return self._args

    @property
    def client_email(self):
        """
        Lazily provide the email address of the client for which this
        request is being processed.
        """

        _unpacked_client = getattr(self, "_unpacked_client", None)
        if not _unpacked_client:
            self._unpacked_client = distinguished_name_to_user(self.client_id)
        return self._unpacked_client.get("email")

    @property
    def route(self):
        """
        Provide the method qualified path of the resource being requested.
        """

        return "%s /%s" % (self.method, self.request_type)

    def _arg_string(self, arg, fallback=None):
        """
        Return a particular value as a string regardless of whether the
        input data is passed to it in list wrapped form.
        """

        value = self.args[arg]
        if isinstance(value, str):
            return value
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        if fallback:
            return fallback
        raise ValueError()

    def arg_value(self, arg, type_of_value):
        """
        Return the value for a particular argument forced to a particular type.
        """

        if arg not in self.args:
            return type_of_value()
        value = self._args[arg]
        assert isinstance(value, type_of_value)
        return value

    def set_args(self, args):
        """
        Explicitly set the values that will be made available as request args.
        """
        setattr(self, "_args", args)

    @classmethod
    def create(cls, client_id, operation, sent_type, request_data):
        """
        Creates and returns a _RequestInfo instance from the supplied arguments
        that can be used to discover the requested endpoint handler and deliver the supplied payload
        from the given client to said handler.

        operation: is expected to specify which type of request the client made
        from the available REQUEST_INFO_METHOD_BY_OPERATION.
        sent_type: specifies the expected lookup package key and the associated route handler path that is associated with the request.
            An example of this could be a sent_type that is set to `migux_apps_peers__new` that is then transformed into the _RequestInfo constructor values:

            request_package = 'migux_apps_peers'
            request_type = '/new'

            These can then be used to lookup the expected request handler function via the package name and the type of request.

        request_data: the request payload from the client
        """
        # convert payload supplied type and operation values that are used as
        # a compromise for allowing multiple routes to be handled by a single
        # endpoint into a more modern style route
        method = REQUEST_INFO_METHOD_BY_OPERATION.get(operation, keyword_none)
        try:
            request_package_unconverted, *request_types = sent_type.split("__")
        except ValueError as exc:
            return None

        request_package = request_package_unconverted.replace("_", ".")
        if request_package == "":
            local_package_name = request_types.pop(0)
            request_package = ".%s" % (local_package_name,)
        request_type = "/".join(request_types)

        kwargs = {}
        kwargs["method"] = method
        kwargs["client_id"] = client_id
        kwargs["request_type"] = request_type
        kwargs["request_package"] = request_package
        kwargs["_request_data"] = request_data
        kwargs["_convert_data"] = _passthrough
        kwargs["_unpacked_client"] = None
        kwargs["_args"] = None

        return cls(**kwargs)


def coalesce_request(request_data, client_id=None):
    """Takes a raw input requests and bundles it into a named type."""

    assert isinstance(request_data, dict)

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
        return rejected, None

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

    request_info = _RequestInfo.create(
        client_id, operation, sent_type, request_data
    )
    if not request_info:
        return {"type": "the request type is invalid"}, None
    return None, request_info


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
