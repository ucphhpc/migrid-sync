#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# canceljob - Request cancel of a job
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

"""Forward valid cancel requests to grid_script for consistent job status
changes. Wrapper for jobaction backend kept as separate interface for
historical reasons.
"""

from shared.functionality.jobaction import main as real_main


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['changedstatusjobs', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    user_arguments_dict['action'] = ['cancel']
    return real_main(client_id, user_arguments_dict)
