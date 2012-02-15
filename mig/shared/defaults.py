#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# defaults - default constant values used in many locations
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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


"""Default values for use in other modules"""


# IMPORTANT: do not import anything here - to avoid import loops


keyword_any = 'ANY'
keyword_all = 'ALL'
keyword_auto = 'AUTO'

default_vgrid = 'Generic'
any_vgrid = keyword_any
all_vgrids = keyword_all

all_jobs = keyword_all

any_protocol = keyword_any

sandbox_names = ['sandbox', 'oneclick', 'ps3live']

email_keyword_list = ['mail', 'email']

mqueue_prefix = 'message_queues'
default_mqueue = 'default'
mqueue_empty = 'NO MESSAGES'

default_pager_entries = 25

default_http_port = 80
default_https_port = 443

exe_leader_name = "execution-leader"

htaccess_filename = '.htaccess'
default_mrsl_filename = '.default.mrsl'
default_css_filename = '.default.css'
spell_dictionary_filename = '.personal_dictionary'
ssh_conf_dir = '.ssh'
settings_filename = 'settings'
widgets_filename = 'widgets'
profile_filename = 'userprofile'
# The htaccess file prevents illegal http access to user files. We completely
# hide it to not confuse users and to prevent all modification. It is 'only'
# a matter of users not accidentally giving away file privacy, though.
_dot_vgrid = ['.vgrid%s' % i for i in ['wiki', 'scm', 'tracker','forum']]
user_invisible_files = [htaccess_filename] + _dot_vgrid

profile_img_max_kb = 128
profile_img_extensions = ['png', 'jpg']
