#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# all - gdp wrapper for public helper functions related to GDP actions
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""GDP wrapper for specific public helper functions"""

from shared.gdp.base import skip_client_id_rewrite, valid_log_actions, \
    valid_project_states, valid_account_states, valid_protocols, \
    get_active_project_client_id, get_active_project_short_id, \
    update_category_meta, project_log, validate_user,  get_users, \
    get_projects, get_project_info, get_project_user_dn, ensure_user, \
    project_remove_user, project_invite_user, reset_account_roles, \
    set_account_state, edit_gdp_user, create_project_user, \
    project_accept_user, project_login, project_logout, project_open, \
    project_close, project_create
from shared.gdp.userid import client_id_project_postfix, \
    get_project_client_id, get_base_client_id, \
    get_client_id_from_project_client_id, \
    get_project_from_client_id, get_project_from_short_id, \
    get_project_from_user_id, get_short_id_from_user_id
