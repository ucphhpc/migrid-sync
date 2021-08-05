#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# accessrequests - access request helper functions
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Access request link functions"""

from __future__ import print_function
from __future__ import absolute_import

from binascii import hexlify
import datetime
import glob
import os
import time

from mig.shared.defaults import request_prefix, request_ext
from mig.shared.fileio import make_temp_file, delete_file
from mig.shared.serial import dumps, load


def build_accessrequestitem_object(configuration, request_dict):
    """Build a access request object based on input request_dict"""

    created_timetuple = request_dict['created_timestamp'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    request_item = {
        'object_type': 'accessrequest',
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
    }
    request_item.update(request_dict)
    # NOTE: datetime is not json-serializable so we force to string
    for field in ['created_timestamp']:
        request_item[field] = "%s" % request_item[field]
    return request_item


def list_access_requests(configuration, request_dir):
    """List all access requests with predefined file extension for given
    request_dir.
    """
    requests = []
    for req_path in glob.glob("%s/%s*%s" % (request_dir, request_prefix,
                                            request_ext)):
        requests.append(req_path.replace(request_dir, '').strip(os.sep))
    return requests


def load_access_request(configuration, request_dir, req_name):
    """Load request req_name with predefined file extension for given
    request_dir.
    """
    request = None
    req_path = os.path.join(request_dir, req_name)
    try:
        if not req_name.startswith(request_prefix) or \
                not req_name.endswith(request_ext):
            raise ValueError("invalid request name: %s" % req_name)
        request = load(req_path)
    except Exception as err:
        configuration.logger.error("could not load request in %s: %s" %
                                   (req_path, err))
    return request


def save_access_request(configuration, request_dir, request):
    """Save the request dictionary as a pickle in request_dir with random
    filename stem and predefined request file extension.
    Returns the nameof the file on success.
    """
    request['created_timestamp'] = datetime.datetime.now()
    try:
        (filehandle, tmpfile) = make_temp_file(suffix=request_ext,
                                               prefix=request_prefix,
                                               dir=request_dir)
        # Prevent exotic characters causing trouble between scripts
        request['request_name'] = os.path.basename(tmpfile)
        os.write(filehandle, dumps(request))
        os.close(filehandle)
    except Exception as err:
        configuration.logger.error("could not save request %s in %s: %s" %
                                   (request, request_dir, err))
        return False
    return os.path.basename(tmpfile)


def delete_access_request(configuration, request_dir, req_name):
    """Delete the request file matching req_name with predefined request file
    extension in request_dir.
    """
    req_path = os.path.join(request_dir, req_name)
    if not req_name.startswith(request_prefix) or \
            not req_name.endswith(request_ext):
        raise ValueError("invalid request name: %s" % req_name)
    return delete_file(req_path, configuration.logger)


if __name__ == "__main__":
    print("Unit testing fileio")
    import sys
    from mig.shared.conf import get_configuration_object
    target = 'abc.0'
    if len(sys.argv) > 1:
        target = sys.argv[1]
    conf = get_configuration_object()
    dummy_req = {"request_type": "resourceowner", "entity": "John Doe",
                 "target": target, "request_text": "Please add me..."}
    res_home = os.path.join(conf.resource_home, target)
    all_reqs = list_access_requests(conf, res_home)
    print("found reqs: %s" % ' , '.join(all_reqs))
    for req_name in all_reqs:
        req = load_access_request(conf, res_home, req_name)
        print("Req: %s" % req)
    print("Saving dummy req: %s" % dummy_req)
    dummy_name = save_access_request(conf, res_home, dummy_req)
    all_reqs = list_access_requests(conf, res_home)
    print("found reqs: %s" % ' , '.join(all_reqs))
    for req_name in all_reqs:
        req = load_access_request(conf, res_home, req_name)
        print("Req: %s" % req)
    print("Deleting dummy req %s again" % dummy_name)
    delete_access_request(conf, res_home, dummy_name)
    all_reqs = list_access_requests(conf, res_home)
    print("found reqs: %s" % ' , '.join(all_reqs))
