#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# defaults - default constant values used in many locations
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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
keyword_unchanged = 'UNCHANGED'

default_vgrid = 'Generic'
any_vgrid = keyword_any
all_vgrids = keyword_all

all_jobs = keyword_all

any_protocol = keyword_any
any_state = keyword_any

sandbox_names = ['sandbox', 'oneclick', 'ps3live']

email_keyword_list = ['mail', 'email']

pending_states = ['PARSE', 'QUEUED', 'EXECUTING', 'RETRY', 'FROZEN']
final_states = ['FINISHED', 'CANCELED', 'EXPIRED', 'FAILED']

mqueue_prefix = 'message_queues'
default_mqueue = 'default'
mqueue_empty = 'NO MESSAGES'

default_pager_entries = 25

default_http_port = 80
default_https_port = 443

cert_valid_days = 365
oid_valid_days = 365

exe_leader_name = "execution-leader"

htaccess_filename = '.htaccess'
welcome_filename = 'welcome.txt'
default_mrsl_filename = '.default.mrsl'
default_css_filename = '.default.css'
spell_dictionary_filename = '.personal_dictionary'
ssh_conf_dir = '.ssh'
davs_conf_dir = '.davs'
ftps_conf_dir = '.ftps'
authkeys_filename = 'authorized_keys'
authpasswords_filename = 'authorized_passwords'
settings_filename = 'settings'
widgets_filename = 'widgets'
profile_filename = 'userprofile'
freeze_meta_filename = 'meta.pck'
# The htaccess file prevents illegal http access to user files. We completely
# hide it to not confuse users and to prevent all modification. It is 'only'
# a matter of users not accidentally giving away file privacy, though.
_dot_vgrid = ['.vgrid%s' % i for i in ['wiki', 'scm', 'tracker', 'forum']]
user_invisible_files = [htaccess_filename] + _dot_vgrid

profile_img_max_kb = 128
profile_img_extensions = ['png', 'jpg']

max_software_entries = 40
max_environment_entries = 40
max_freeze_files = 100
max_upload_files = 100
max_upload_chunks = 10

upload_block_size = 64 * 1024 * 1024
upload_tmp_dir = '.upload-cache'
wwwpublic_alias = 'public'
public_archive_dir = 'archives'
public_archive_index = 'published-archive.html'

edit_lock_suffix = '.editor_lock__'
edit_lock_timeout = 600

# Valid trigger actions - with the first one as default action

valid_trigger_changes = ['created', 'modified', 'deleted', 'moved']
valid_trigger_actions = ['submit'] + ['trigger-%s' % i for i in \
                                      valid_trigger_changes]

workflows_log_name = 'workflow-triggers.log'
workflows_log_size = 1024*1024
workflows_log_cnt = 2
