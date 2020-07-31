#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createbackup - back end for one-shot backup archive creation
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""One-shot creation of final backup archives for write-once files"""
from __future__ import absolute_import

from mig.shared.functionality.createfreeze import main as createfreeze_main, \
    signature as createfreeze_signature, keyword_final


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    # Mimic call to createfreeze with finalized backup fields set
    args_dict = createfreeze_signature()[1]
    args_dict.update(user_arguments_dict)
    args_dict['flavor'] = ['backup']
    args_dict['freeze_state'] = [keyword_final]
    return createfreeze_main(client_id, args_dict)
