#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# quota - helpers to support storage quota
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""helpers to support storage quota"""

from mig.lib.lustrequota import update_lustre_quota

supported_quota_backends = ["lustre", "lustre-gocryptfs"]


def update_quota(configuration):
    """Update quota for users and vgrids"""
    retval = False
    logger = configuration.logger
    if (
        configuration.quota_backend == "lustre"
        or configuration.quota_backend == "lustre-gocryptfs"
    ):
        retval = update_lustre_quota(configuration)
    else:
        logger.error(
            "quota_backend: %r not in supported_quota_backends: %r"
            % (configuration.quota_backend, supported_quota_backends)
        )

    return retval
