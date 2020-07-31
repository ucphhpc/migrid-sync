#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# importsharelink - back end for one-shot import of sharelink contents
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""One-shot import of contents from sharelink"""
from __future__ import absolute_import

from mig.shared.functionality.cp import main as importsharelink_main, \
    signature as importsharelink_signature


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    # Mimic call to cp with import sharelink fields set
    args_dict = importsharelink_signature()[1]
    # Remove unused src and freeze_id fields to avoid parsing errors
    del args_dict['src']
    del args_dict['freeze_id']
    args_dict.update(user_arguments_dict)
    return importsharelink_main(client_id, args_dict)
