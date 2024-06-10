#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# https - Wrapper for https web page helper import
# Copyright (C) 2010-2024  The MiG Project lead by Brian Vinter
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

"""This imports all modules needed by the https web pages"""

from mig.shared.griddaemons.base import default_username_validator
from mig.shared.griddaemons.ratelimits import default_max_user_hits, \
    default_user_abuse_hits, default_proto_abuse_hits, \
    hit_rate_limit, expire_rate_limit
from mig.shared.griddaemons.auth import validate_auth_attempt
