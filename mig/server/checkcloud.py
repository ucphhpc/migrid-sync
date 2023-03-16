#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# checkcloud - Check cloud access and instance status for users
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Check cloud instances allowed and running for users"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import pickle
import sys

from mig.shared.defaults import keyword_auto, keyword_all
from mig.shared.useradm import init_user_adm, search_users, default_search
from mig.shared.cloud import lookup_user_service_value, cloud_load_instance, \
    status_all_cloud_instances


def usage(name='checkcloud.py'):
    """Usage help"""

    print("""Check cloud access and instance status for users.
Usage:
%(name)s [CHECK_OPTIONS]
Where CHECK_OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_PATH          Use DB_PATH as user data base file path
   -h                  Show this help
   -I CERT_DN          Check only for user with ID (distinguished name)
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    fields = keyword_auto
    verbose = False
    user_file = None
    search_filter = default_search()
    opt_args = 'c:d:hf:I:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            fields = val.split()
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            search_filter['distinguished_name'] = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(0)

    if args:
        print('Error: Non-option arguments are not supported - missing quotes?')
        usage()
        sys.exit(1)

    uid = 'unknown'
    (configuration, hits) = search_users(search_filter, conf_path, db_path,
                                         verbose)
    services = configuration.cloud_services
    if not hits:
        print("No matching users in user DB")
    else:
        # Reuse conf and hits as a sparse user DB for speed
        conf_path, db_path = configuration, dict(hits)
        print("Cloud status:")
        for (uid, user_dict) in hits:
            if verbose:
                print("Checking %s" % uid)
            for service in services:
                cloud_id = service['service_name']
                cloud_title = service['service_title']
                cloud_flavor = service.get(
                    "service_provider_flavor", "openstack")
                max_instances = lookup_user_service_value(
                    configuration, uid, service, 'service_max_user_instances')
                max_user_instances = int(max_instances)
                print('%s cloud instances allowed for %s: %d' %
                      (cloud_title, uid, max_user_instances))
                # Load all user instances and show status
                saved_instances = cloud_load_instance(configuration, uid,
                                                      cloud_id, keyword_all)
                instance_fields = ['public_fqdn', 'status']
                status_map = status_all_cloud_instances(
                    configuration, uid, cloud_id, cloud_flavor,
                    list(saved_instances), instance_fields)
                for (instance_id, instance_dict) in saved_instances.items():
                    instance_label = instance_dict.get('INSTANCE_LABEL',
                                                       instance_id)
                    print('%s cloud instance %s (%s) for %s at %s status: %s' %
                          (cloud_title, instance_label, instance_id, uid,
                           status_map[instance_id]['public_fqdn'],
                           status_map[instance_id]['status']))
