#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# defaults - default constant values used in many locations
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


"""Default values for use in other modules"""

from string import ascii_lowercase, ascii_uppercase, digits

# IMPORTANT: do NOT import anything except native python modules/functions here
#            to avoid import loops

user_db_filename = 'MiG-users.db'

keyword_any = 'ANY'
keyword_all = 'ALL'
keyword_auto = 'AUTO'
keyword_never = 'NEVER'
keyword_none = 'NONE'
keyword_unchanged = 'UNCHANGED'
keyword_final = 'FINAL'
keyword_pending = 'PENDING'
keyword_owners = 'OWNERS'
keyword_members = 'MEMBERS'

default_vgrid = 'Generic'
any_vgrid = keyword_any
all_vgrids = keyword_all

all_jobs = keyword_all

any_protocol = keyword_any
any_state = keyword_any

cert_field_order = [
    ('country', 'C'),
    ('state', 'ST'),
    ('locality', 'L'),
    ('organization', 'O'),
    ('organizational_unit', 'OU'),
    ('full_name', 'CN'),
    ('email', 'emailAddress'),
    ]

sandbox_names = ['sandbox', 'oneclick', 'ps3live']

email_keyword_list = ['mail', 'email']

pending_states = ['PARSE', 'QUEUED', 'EXECUTING', 'RETRY', 'FROZEN']
final_states = ['FINISHED', 'CANCELED', 'EXPIRED', 'FAILED']

maxfill_fields = ['CPUTIME', 'NODECOUNT', 'CPUCOUNT', 'MEMORY', 'DISK']

mqueue_prefix = 'message_queues'
default_mqueue = 'default'
mqueue_empty = 'NO MESSAGES'

# User ID is email or hexlified version of full cert DN.
# Shortest email would have to be something like a@ku.dk 
user_id_min_length = 7
user_id_max_length = 256
user_id_charset = ascii_uppercase + ascii_lowercase + digits + '_@.'

# We hexlify 32 random bytes to get 64 character string
session_id_bytes = 32
session_id_length = session_id_bytes * 2
session_id_charset = digits + 'abcdef'

# Sharelink format helpers
# Let mode chars be aAbBcC ... xX (to make splitting evenly into 3 easy)
share_mode_charset = ''.join(['%s%s' % pair for pair in zip(
    ascii_lowercase[:-2], ascii_uppercase[:-2])])
# Let ID chars be aAbBcC ... zZ01..9 (to always yield URL friendly IDs
share_id_charset = ascii_lowercase + ascii_uppercase + digits


default_pager_entries = 25

default_http_port = 80
default_https_port = 443

cert_valid_days = 365
oid_valid_days = 365

auth_openid_mig_db = 'mod_auth_openid-mig-users.db'
auth_openid_ext_db = 'mod_auth_openid-ext-users.db'

exe_leader_name = "execution-leader"

htaccess_filename = '.htaccess'
welcome_filename = 'welcome.txt'
default_mrsl_filename = '.default.mrsl'
default_css_filename = '.default.css'
spell_dictionary_filename = '.personal_dictionary'
ssh_conf_dir = '.ssh'
davs_conf_dir = '.davs'
ftps_conf_dir = '.ftps'
seafile_conf_dir = '.seafile'
duplicati_conf_dir = '.duplicati'
job_output_dir = 'job_output'
transfer_output_dir = 'transfer_output'
cron_output_dir = 'cron_output'
authkeys_filename = 'authorized_keys'
authpasswords_filename = 'authorized_passwords'
authdigests_filename = 'authorized_digests'
settings_filename = 'settings'
widgets_filename = 'widgets'
profile_filename = 'userprofile'
duplicati_filename = 'duplicati'
freeze_meta_filename = 'meta.pck'
datatransfers_filename = 'transfers'
user_keys_dir = 'keys'
sharelinks_filename = 'sharelinks'
seafile_ro_dirname = 'seafile_readonly'
# Trash really goes to this location but only accessible through link 
trash_destdir = '.trash'
trash_linkname = 'Trash'

# The htaccess file prevents illegal http access to user files. We completely
# hide it to not confuse users and to prevent all modification. It is 'only'
# a matter of users not accidentally giving away file privacy, though.
# The .vgrid* dirs contain wsgi/cgi dirs with executable code, etc. and we
# can't let users edit them because it would result in arbitrary code execution
# holes.
#
# IMPORTANT: please use the invisible_{path,file,dir} helpers from shared.base
#            instead of using these variables directly.
_dot_vgrid = ['.vgrid%s' % i for i in ['wiki', 'scm', 'tracker', 'forum']]
_protected_dirs = [trash_destdir]
_user_invisible_dirs = _dot_vgrid + _protected_dirs
_user_invisible_files = [htaccess_filename]
_user_invisible_paths = _user_invisible_files + _user_invisible_dirs
_vgrid_xgi_scripts = ['.vgridscm/cgi-bin/hgweb.cgi',
                      '.vgridscm/wsgi-bin/hgweb.wsgi',
                      '.vgridtracker/cgi-bin/trac.cgi',
                      '.vgridtracker/wsgi-bin/trac.wsgi',
                      '.vgridwiki/cgi-bin/moin.cgi',
                      '.vgridwiki/wsgi-bin/moin.wsgi']

profile_img_max_kb = 128
profile_img_extensions = ['png', 'jpg']

max_software_entries = 40
max_environment_entries = 40
# This is an arbitrarily selected cap to prevent exhausting resources
max_freeze_files = 65535
max_upload_files = 65535
max_upload_chunks = 10
# Checksum in 32kb blocks and default to first 32 MB
default_chunk_size = 32768
default_max_chunks = 1024

# 64M = 67108864
upload_block_size = 67108864
upload_tmp_dir = '.upload-cache'
# Please read the chunk note in wsgi handler before tuning this value above 1G!
# 256M = 268435456
download_block_size = 268435456
wwwpublic_alias = 'public'
public_archive_dir = 'archives'
public_archive_index = 'published-archive.html'

edit_lock_suffix = '.editor_lock__'
edit_lock_timeout = 600

# Valid trigger actions - with the first one as default action

valid_trigger_changes = ['created', 'modified', 'deleted']
valid_trigger_actions = ['submit', 'command'] + ['trigger-%s' % i for i in \
                                                 valid_trigger_changes]
img_trigger_prefix = 'system_imagesettings'

workflows_log_name = 'workflow.log'
# 64M = 67108864
workflows_log_size = 67108864
workflows_log_cnt = 2

atjobs_name = 'atjobs'
crontab_name = 'crontab'
cron_log_name = 'cron.log'
# 64M = 67108864
cron_log_size = 67108864
cron_log_cnt = 2

# 64M = 67108864
transfers_log_size = 67108864
transfers_log_cnt = 2

dav_domain = "/"

# Interactive jobs use a password which should at least be hard to brute-force
# Yet the VNC server ignores all but the first 8 chars so it is no use with
# longer password unfortunately.
vnc_pw_len = 8

# TODO: change to something that doesn't interfere if filename contains spaces
# Seperator used in job src/dst file lines
src_dst_sep = " "

# Seperator used in file expansion - must be easily parsable by user scripts
file_dest_sep = "    ::    "

# For webdavs rfc compliance testing with litmus - use expected email format
litmus_id = 'litmus@nowhere.org'

# VGrid and resource request file name helpers
request_prefix = 'access-'
request_ext = '.req'

# CSRF helper for client scripts
CSRF_MINIMAL, CSRF_WARN = "MINIMAL", "WARN"
CSRF_MEDIUM, CSRF_FULL = "MEDIUM", "FULL"
csrf_token_header = 'HTTP_CSRF_TOKEN'

# form field
csrf_field = "_csrf"

# List of backend targets that may require a CSRF token to work
# Can be generated with the command:
# 0|~/mig > ./codegrep.py safe_handler|grep import|sort|awk '{ print $1; }'| \
#               sed 's@.*/functionality/\(.*\).py:from@\\"\1\\",@g'|xargs
csrf_backends = ["addresowner", "addvgridmember", "addvgridowner", "addvgridres", "addvgridtrigger", "autocreate", "chksum", "cleanallstores", "cleanexe", "cleanfe", "cleanstore", "cp", "createfreeze", "createre", "createvgrid", "datatransfer", "deletefreeze", "deletere", "delres", "editfile", "extcertaction", "extoidaction", "imagepreview", "jobaction", "jobfeasible", "jobobjsubmit", "jobschedule", "liveio", "mkdir", "mqueue", "mv", "pack", "rejectresreq", "rejectvgridreq", "reqcertaction", "reseditaction", "restartallexes", "restartallstores", "restartexe", "restartfe", "restartstore", "resubmit", "rmdir", "rm", "rmresowner", "rmvgridmember", "rmvgridowner", "rmvgridres", "rmvgridtrigger", "scripts", "sendrequestaction", "settingsaction", "sharelink", "sssadmin", "ssscreateimg", "stopallexes", "stopallstores", "stopexe", "stopfe", "stopstore", "submitfields", "submit", "tar", "testresupport", "textarea", "touch", "truncate", "unpack", "untar", "unzip", "updateresconfig", "updatevgrid", "uploadchunked", "upload", "vgridforum", "vgridsettings", "vmachines", "zip",
                 ]

# freeze archive flavor
# NOTE: order in states list is used to set default state for new archives
freeze_flavors = {
    'freeze': {'adminfreeze_title': 'Freeze Archive',
               'createfreeze_title': 'Create Freeze Archive',
               'showfreeze_title': 'Show Freeze Archive Details',
               'deletefreeze_title': 'Delete Freeze Archive',
               'states': [keyword_pending, keyword_final]},
    'phd': {'adminfreeze_title': 'PhD Thesis Archival',
            'createfreeze_title': 'Create Thesis Archive',
            'showfreeze_title': 'Show Thesis Archive Details',
            'deletefreeze_title': 'Delete Thesis Archive',
            'states': [keyword_pending, keyword_final]},
    'backup': {'adminfreeze_title': 'Backup Archival',
               'createfreeze_title': 'Create Backup Archive',
               'showfreeze_title': 'Show Backup Archive Details',
               'deletefreeze_title': 'Delete Backup Archive',
               'states': [keyword_final]}
    }

# Default value for ALL integer limits in vgrid settings
# NOTE: spamming more than 10 owners about reqs is rarely popular, but
# balancing participation management rights is tricky. Owners should at least
# be urged to consider security implications of allowing too many co-owners.
# TODO: split into two values and remove default limit on management rights?
default_vgrid_settings_limit = 10

# Seperator used in flat vgrid structure for read-only support
vgrid_nest_sep = ':'

# Password policy helpers
POLICY_NONE, POLICY_WEAK = "NONE", "WEAK"
POLICY_MEDIUM, POLICY_HIGH = "MEDIUM", "HIGH"

# Prioritized protocol choices and internal values
duplicati_protocol_choices = [('WebDAVS', 'davs'), ('SFTP', 'sftp'),
                              ('FTPS', 'ftps')]
# Prioritized schedule backup frequency choices and json values
duplicati_schedule_choices = [('Daily', '1D'), ('Weekly', '1W'),
                              ('Monthly', '1M'), ('Never', '')]
