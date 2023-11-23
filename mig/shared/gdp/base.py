#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - gdp base helper functions related to GDP actions
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

"""GDP specific helper functions"""

from __future__ import print_function

import copy
import datetime
import os
import time

try:
    import pdfkit
except:
    pdfkit = None
try:
    from xvfbwrapper import Xvfb
except:
    Xvfb = None

from mig.shared.base import client_id_dir, valid_dir_input, extract_field, \
    fill_distinguished_name, expand_openid_alias, get_short_id, \
    force_native_str
from mig.shared.defaults import default_vgrid, all_vgrids, any_vgrid, \
    keyword_auto, gdp_distinguished_field, io_session_timeout, \
    valid_gdp_auth_scripts as valid_auth_scripts
from mig.shared.fileio import touch, make_symlink, write_file, remove_rec, \
    acquire_file_lock, release_file_lock, copy_file, move_rec, makedirs_rec
from mig.shared.gdp.userid import __validate_user_id, \
    __client_id_from_project_client_id, \
    __project_name_from_project_client_id, \
    __short_id_from_client_id, __project_short_id_from_project_client_id, \
    __client_id_from_user_id, __project_client_id_from_user_id, \
    __project_short_id_from_user_id, __scramble_user_id, \
    get_project_from_user_id, get_project_client_id
from mig.shared.notification import send_email
from mig.shared.pwcrypto import make_simple_hash, make_safe_hash, make_encrypt
from mig.shared.serial import load, dump
from mig.shared.useradm import create_user, delete_user, edit_user, \
    get_full_user_map, lock_user_db
from mig.shared.userdb import default_db_path
from mig.shared.vgrid import vgrid_flat_name, vgrid_owners, vgrid_is_owner, \
    vgrid_is_member, vgrid_set_owners, vgrid_add_members, vgrid_set_settings, \
    vgrid_members, vgrid_create_allowed, vgrid_remove_members, vgrid_remove_owners, \
    vgrid_restrict_write_support, vgrid_rm_files, vgrid_rm_entry
from mig.shared.vgridaccess import force_update_user_map, \
    force_update_vgrid_map, force_update_resource_map
from mig.shared.vgridkeywords import get_settings_keywords_dict

gdp_db_filename = 'gdp-users.db'
gdp_user_log_filename = 'gdp-users.log'
notify_home_dirname = 'notify'
notify_attic_dirname = 'notify_attic'

skip_client_id_rewrite = [
    'adminvgrid.py',
    'autocreate.py',
    'autologout.py',
    'gdpman.py',
    # NOTE: we allow authenticated semi-automatic cert/oid renew
    'reqcert.py',
    'reqcertaction.py',
    'reqoid.py',
    'reqoidaction.py',
    'rmvgridmember.py',
    'twofactor.py',
    'vgridman.py',
    'viewvgrid.py',
    'rmvgridowner.py',
]

valid_log_actions = [
    'accessed',
    'accept_user',
    'auto_logged_out',
    'copied',
    'created',
    'removed',
    'modified',
    'truncated',
    'deleted',
    'invited_user',
    'removed_user',
    'logged_in',
    'logged_out',
    'moved',
    'promoted_to_owner',
    'demoted_owner'
]

valid_project_states = ['invited', 'accepted', 'removed']

valid_account_states = ['active', 'suspended', 'removed']

valid_protocols = ['https', 'davs', 'sftp']


def __scramble_path(configuration, path):
    """A simple helper to optionally scramble paths e.g. in gdp logs as
    specified in configuration.
    """
    _logger = configuration.logger

    result = None
    try:
        algo = configuration.gdp_path_scramble
        if algo in ['false']:
            result = path
        elif algo in ['simple_hash', 'md5']:
            result = make_simple_hash(path)
        elif algo in ['safe_hash', 'sha256']:
            result = make_safe_hash(path)
        elif algo in ['safe_encrypt', 'fernet', 'aes256_encrypt', 'aesgcm',
                      'simple_encrypt', 'aesgcm_static']:
            # NOTE: emulate same None-handling as for hash scramblers
            if path is None:
                result = None
            else:
                result = make_encrypt(configuration, path, algo=algo)
        else:
            raise ValueError("unsupported gdp_path_scramble conf value: %s" %
                             algo)
        result = force_native_str(result)
    except Exception as exc:
        _logger.error("GDP: __scramble_path failed for path: %r: %s"
                      % (path, exc))
        result = None

    return result


def __gdp_db_filepath(configuration, db_path=None):
    """Generate GDP user_db filepath"""

    if db_path:
        db_filepath = db_path
    else:
        db_filepath = os.path.join(
            configuration.gdp_home, gdp_db_filename)
    db_lock_filepath = '%s.lock' % db_filepath

    return (db_filepath, db_lock_filepath)


def __gdp_user_log_filepath(configuration):
    """Generate GDP user_db filepath"""

    log_filepath = os.path.join(configuration.gdp_home, gdp_user_log_filename)
    log_lock_filepath = '%s.lock' % log_filepath

    return (log_filepath, log_lock_filepath)


def __create_gdp_user_db_entry(configuration):
    """Create empty GDP user db entry"""

    result = {
        'projects': {},
        'account': {
            'state': valid_account_states[0],
        }
    }

    for protocol in valid_protocols:
        result['account'][protocol] = {
            'role': '',
            'last_login': {
                'timestamp': 0,
                'ip': '',
            }
        }

    return result


def __validate_user_db(configuration, client_id, user_db=None):
    """Validate the GDP user database,
    it's expected to have the folling structure:
    {CLIENT_ID: {
            'projects': {
                PROJECT_NAME: {
                    'state': basestring,
                    'client_id': basestring,
                    'category_meta': {
                        'category_id': basestring,
                        'actions': [{
                            'date: basestring,
                            'source': basestring,
                            'user': basestring,
                            'action': basestring,
                            'references': [{
                                'ref_id': basestring,
                                'ref_help': basestring,
                                'ref_name': basestring,
                                'ref_pattern: basestring,
                                'value': basestring,
                            }, ...]
                        }],
                    }
                }
            }
            'account': {
                'state': basestring
                PROTOCOL: {
                    'role': basestring
                    'last_login': {
                        'timestamp': int
                        'ip': basestring
                    }
                }
            }
        }
    }
    """

    _logger = configuration.logger
    # _logger.debug("client_id: %r, user_db: %s" % (client_id, user_db))

    status = True
    user = None
    projects = None
    account = None
    err_msg = "Database format error for user: %r" % client_id
    warn_msg = "Database format warning for user: %r" % client_id
    log_err_msg = "GDP: " + err_msg

    if user_db is None:
        user_db = __load_user_db(configuration)

    # Validate user

    user = user_db.get(client_id, None)
    if user is None:
        status = False
        template = ": Missing user entry in GDP DB"
        err_msg += template
        _logger.error(log_err_msg + template)
    elif not isinstance(user, dict):
        status = False
        template = ": User entry is NOT a dictionary instance"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Validate projects

    if status:
        projects = user.get('projects', None)
        if projects is None:
            status = False
            template = ": Missing 'projects' entry in GDP DB"
            err_msg += template
            _logger.error(log_err_msg + template)
        elif not isinstance(projects, dict):
            status = False
            template = ": 'projects' entry is NOT a dictionary instance"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:
        for (key, value) in projects.items():
            if not 'client_id' in value:
                status = False
                template = ": Missing 'client_id' entry for project: %r" \
                    % key
                err_msg += template
                _logger.error(log_err_msg + template)
                break
            if not 'state' in value:
                status = False
                template = ": Missing 'state' entry" + " for project: %r" \
                    % key
                err_msg += template
                _logger.error(log_err_msg + template)
                break
            # TODO: enable this is noisy log or just fix?
            # NOTE: category and references were added later: some may lack it
            # if not 'category_meta' in value:
            #    template = ": Missing 'category_meta' entry" + " for project: %r" \
            #        % key
            #    warn_msg += template
            #    _logger.warning(warn_msg + template)
            #    continue

    # Validate account

    if status:
        account = user.get('account', None)
        if account is None:
            status = False
            template = ": Missing 'account' entry in GDP DB"
            err_msg += template
            _logger.error(log_err_msg + template)
        elif not isinstance(account, dict):
            status = False
            template = ": 'account' is NOT a dictionary instance"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Validate account state

    if status and not 'state' in account:
        status = False
        template = ": Missing 'account -> state' entry in GDP DB"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Validate account protocol

    if status:
        for protocol in valid_protocols:
            account_protocol = account.get(protocol, None)

            if account_protocol is None:
                status = False
                template = ": Missing 'account -> %s' entry in GDP DB" \
                    % protocol
                err_msg += template
                _logger.error(log_err_msg + template)
            elif not isinstance(account_protocol, dict):
                status = False
                template = ": 'account -> %s' is NOT a dictionary instance" \
                    % protocol
                err_msg += template
                _logger.error(log_err_msg + template)

            # Validate account protocol role

            if status:
                role = account_protocol.get('role', None)
                if role is None:
                    status = False
                    template = ": Missing 'account -> %s -> role'" % protocol \
                        + " entry in GDP DB"
                    err_msg += template
                    _logger.error(log_err_msg + template)

            # Validate account protocol last login

            if status:
                protocol_last_login = account_protocol.get(
                    'last_login', None)
                if protocol_last_login is None:
                    status = False
                    template = ": Missing 'account -> %s" % protocol \
                        + " -> last_login' entry in GDP DB"
                    err_msg += template
                    _logger.error(log_err_msg + template)
                elif not isinstance(protocol_last_login, dict):
                    status = False
                    template = ": 'account -> %s -> last_login'" % protocol \
                        + " is NOT a dictionary instance"
                    err_msg += template
                    _logger.error(log_err_msg + template)

            # Validate account protocol last login timestamp

            if status and not 'timestamp' in protocol_last_login:
                status = False
                template = ": Missing 'account -> %s" % protocol \
                    + " -> last_login -> timestamp' entry in GDP DB"
                err_msg += template
                _logger.error(log_err_msg + template)

            # Validate account last login ip

            if status and not 'ip' in protocol_last_login:
                status = False
                template = ": missing 'account -> %s ->" % protocol \
                    + " last_login -> ip' entry in GDP DB"
                err_msg += template
                _logger.error(log_err_msg + template)

            if not status:
                break

    ret_msg = ""
    if not status:
        ret_msg = err_msg

    return (status, ret_msg)


def __load_user_db(configuration,
                   do_lock=True, allow_missing=False, db_path=None):
    """Load pickled GDP user database"""

    _logger = configuration.logger

    (db_filepath, db_lock_filepath) = __gdp_db_filepath(configuration,
                                                        db_path=db_path)
    if do_lock:
        flock = acquire_file_lock(db_lock_filepath, exclusive=False)
    result = {}
    if os.path.exists(db_filepath):
        try:
            result = load(db_filepath)
        except Exception as exc:
            err = "%s" % exc
            result = {}
            msg = "Failed to load GDP user DB"
            if err:
                msg += ": %s" % err
            _logger.error(msg)
            raise Exception(msg)
    elif not allow_missing:
        _logger.error("Missing GDP user DB: %r" % db_filepath)
    if do_lock:
        release_file_lock(flock)

    return result


def __save_user_db(configuration, user_db, do_lock=True, db_path=None):
    """Save GDP user database"""

    _logger = configuration.logger

    (db_filepath, db_lock_filepath) = __gdp_db_filepath(configuration,
                                                        db_path=db_path)

    if do_lock:
        flock = acquire_file_lock(db_lock_filepath)

    if not os.path.exists(db_filepath):
        touch(db_filepath, configuration)

    dump(user_db, db_filepath)

    if do_lock:
        release_file_lock(flock)


def __send_project_action_confirmation(configuration,
                                       action,
                                       login,
                                       target,
                                       project_name,
                                       category_dict):
    """Send project *action* confirmation possibly with target to *login* and
    GDP admins.
    """

    _logger = configuration.logger
    # _logger.debug("login: %r, project_name: %r" % (login,
    #                                                    project_name))
    status = True
    target_dict = {}
    if action == "create_project":
        target_dict['registrant'] = login
    elif action == "remove_project":
        target_dict['registrant'] = login
        if isinstance(target, list):
            target_dict['participants'] = ", ".join(target)
        else:
            target_dict['participants'] = target
    elif action == "invite_user":
        target_dict['registrant'] = login
        target_dict['target_user'] = target
    elif action == "remove_user":
        target_dict['registrant'] = login
        target_dict['target_user'] = target
    elif action == "accept_user":
        target_dict['target_user'] = login
    elif action == "demote_owner":
        target_dict['registrant'] = login
        target_dict['target_user'] = target
    elif action == "promote_to_owner":
        target_dict['registrant'] = login
        target_dict['target_user'] = target
    else:
        _logger.error("unexpected action: %s" % action)
        return False

    log_ok_msg = "GDP: Send project %s confirmation email" % action
    ref_pairs = [(i['ref_id'], i['value']) for i in
                 category_dict.get('references', {}).get(action, [])]
    # _logger.debug("ref_pairs: %s" % ref_pairs)
    log_ok_msg += " for targets: %r, project: %r, %s %s" % \
                  (target_dict, project_name, target, ref_pairs)
    log_err_msg = "GDP: Failed to send project %s confirmation email" % action
    log_err_msg += " for targets: %r, project: %r, %s %s" % \
                   (target_dict, project_name, target, ref_pairs)
    template = None
    notify = []
    notify_filename = 'notifyemails.txt'
    template_filename = category_dict.get('templates', {}).\
        get('%s' % action, {}).get('notify', '')
    # _logger.debug("template_filename: %s: %r" % (action, template_filename))
    if not template_filename:
        _logger.info("No %s notification email configured for %s projects" %
                     (action, category_dict.get('category_id', '')))
        return True

    # Check for PDF generation packages

    if pdfkit is None:
        status = False
        _logger.error("%s: Missing python pdfkit package" % log_err_msg)

    if Xvfb is None:
        status = False
        _logger.error("%s: Missing python xvfbwrapper package" %
                      log_err_msg)

    # NON-registrant notifications are only sent for projects with ref value(s)

    if status and ref_pairs:

        # Load notification emails

        notify_filepath = os.path.join(configuration.gdp_home,
                                       notify_filename)
        try:
            fh = open(notify_filepath)
            for line in fh:
                # Ignore comments and empty lines
                notifyline = line.split('#', 1)[0]
                if not notifyline:
                    continue
                email_idx = notifyline.find('<')
                entry = {'name': notifyline[:email_idx].strip(' \t\n\r'),
                         'email': notifyline[email_idx:].strip(' \t\n\r')}
                notify.append(entry)
            fh.close()
            if not notify:
                status = False
                _logger.error("%s: No notify emails found in file: %r"
                              % (log_err_msg, notify_filepath))
        except Exception as exc:
            status = False
            _logger.error("%s: Failed to open notify emails file: %s"
                          % (log_err_msg, exc))

    if status:

        # Check for project home dir

        project_home = os.path.join(configuration.gdp_home,
                                    os.path.join(notify_home_dirname,
                                                 project_name))
        if status and not os.path.isdir(project_home):
            status = False
            _logger.error("%s: Missing project home dir: %r"
                          % (log_err_msg, project_home))

    if status:

        # Check for project action template

        template_filepath = os.path.join(configuration.gdp_home,
                                         template_filename)
        # _logger.debug("template_filepath: %r" % template_filepath)
        if status:
            try:
                fh = open(template_filepath)
                template = fh.read()
                fh.close()
            except Exception as exc:
                status = False
                _logger.error("%s: Failed to open template file: %s"
                              % (log_err_msg, exc))

    # Generate project action PDF

    if status:
        timestamp = time.time()
        pdf_filename = '%s.%d.pdf' % (action, int(timestamp))
        pdf_filepath = os.path.join(project_home, pdf_filename)
        # _logger.debug("pdf_filepath: %r" % pdf_filepath)
        # NOTE: quiet is needed to avoid stdout breaking cgi
        pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'quiet': '',
        }
        current_datetime = datetime.datetime.fromtimestamp(timestamp)
        date = current_datetime.strftime('%d/%m/%Y %H:%M:%S')
        fill_entries = {'site_title': configuration.site_title,
                        'short_title': configuration.short_title,
                        'server_fqdn': configuration.server_fqdn,
                        'date': date,
                        'project_name': project_name,
                        'category_title': category_dict['category_title'],
                        }
        fill_entries.update(target_dict)

        for ref_entry in category_dict.get('references', {}).get(action, []):
            ref_id = ref_entry['ref_id']
            fill_entries[ref_id+'_name'] = ref_entry['ref_name']
            fill_entries[ref_id+'_value'] = ref_entry['value']
        template = template % fill_entries
        template.encode('utf8')

        vdisplay = None
        try:
            # NOTE: we force disable network listen for security
            vdisplay = Xvfb(nolisten='tcp')
            vdisplay.start()
        except Exception as exc:
            status = False
            vdisplay = None
            _logger.error("%s: Failed to initialize vdisplay: %s"
                          % (log_err_msg, exc))
        if status:
            try:
                env = os.environ
                # NOTE: vdisplay_num changed to new_display at some point
                if 'vdisplay_num' in dir(vdisplay):
                    env['DISPLAY'] = ':%s' % vdisplay.vdisplay_num
                else:
                    env['DISPLAY'] = ':%s' % vdisplay.new_display
                pdfkit_conf = pdfkit.configuration(environ=env)
                pdfkit.from_string(template, pdf_filepath,
                                   configuration=pdfkit_conf,
                                   options=pdf_options)
            except Exception as exc:
                status = False
                _logger.error("%s: pdfkit failed: %s"
                              % (log_err_msg, exc))
        if vdisplay is not None:
            try:
                vdisplay.stop()
            except Exception as exc:
                status = False
                _logger.error("%s: Failed to stop vdisplay: %s"
                              % (log_err_msg, exc))

    # Send project action mail

    if status and not configuration.gdp_email_notify:
        _logger.warning("Skipping GDP email notification, disabled in conf")
    elif status:
        mail_fill = {'short_title': configuration.short_title, 'action':
                     action, 'project_name': project_name}
        recipients = "%s" % login
        if target:
            if isinstance(target, str):
                recipients += ", %s" % target
            elif isinstance(target, list):
                recipients += ", %s" % ", ".join(target)
        for admin in notify:
            recipients += ", %s" % " ".join(admin.values())
        mail_fill['recipients'] = recipients
        subject = "%(short_title)s project %(action)s: %(project_name)r" % \
                  mail_fill
        message = """*** IMPORTANT: direct replies to this automated message will NOT be read! ***

This message from %(short_title)s is sent to %(recipients)s
in reaction to the %(action)s for %(project_name)s .

Attached you'll find the details registered in relation to the operation.
        """ % mail_fill
        status = send_email(
            recipients,
            subject,
            message,
            _logger,
            configuration,
            files=[pdf_filepath],
        )
        if status:
            log_ok_msg + ": Recipients: %s" % recipients
        else:
            _logger.error("%s: send_email failed" % log_err_msg)

    if status:
        _logger.info(log_ok_msg)

    return status


def __send_project_create_confirmation(configuration,
                                       login,
                                       project_name,
                                       category_dict):
    """Send project create confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "create_project",
                                              login, '',
                                              project_name, category_dict)


def __send_project_remove_confirmation(configuration,
                                       login,
                                       participants,
                                       project_name,
                                       category_dict):
    """Send project create confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "remove_project",
                                              login, participants,
                                              project_name, category_dict)


def __send_project_invite_user_confirmation(configuration,
                                            login,
                                            user,
                                            project_name,
                                            category_dict):
    """Send project invite *user* confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "invite_user",
                                              login, user, project_name,
                                              category_dict)


def __send_project_accept_user_confirmation(configuration,
                                            login,
                                            owner_login,
                                            project_name,
                                            category_dict):
    """Send project invite accept confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "accept_user",
                                              login, owner_login, project_name,
                                              category_dict)


def __send_project_remove_user_confirmation(configuration,
                                            login,
                                            user,
                                            project_name,
                                            category_dict):
    """Send project remove *user* confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "remove_user",
                                              login, user, project_name,
                                              category_dict)


def __send_project_demote_owner_confirmation(configuration,
                                             login,
                                             user,
                                             project_name,
                                             category_dict):
    """Send project demote *user* confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "demote_owner",
                                              login, user, project_name,
                                              category_dict)


def __send_project_promote_to_owner_confirmation(configuration,
                                                 login,
                                                 user,
                                                 project_name,
                                                 category_dict):
    """Send project promote *user* confirmation to *login* and GDP admins"""
    return __send_project_action_confirmation(configuration,
                                              "promote_to_owner",
                                              login, user, project_name,
                                              category_dict)


def __delete_mig_user(configuration,
                      client_id,
                      allow_missing=False):
    """Helper to delete MiG user"""

    _logger = configuration.logger
    status = False
    missing = False
    ok_msg = "Deleted MiG user: %r" % client_id
    missing_msg = "Skipped missing MiG user: %r" % client_id
    err_msg = "Failed to delete MiG user: %r" % client_id
    log_ok_msg = "GDP: %s" % ok_msg
    log_missing_msg = "GDP: %s" % missing_msg
    log_err_msg = "GDP: %s" % err_msg
    mig_user_db_path = default_db_path(configuration)
    mig_user_map = get_full_user_map(configuration)
    mig_user_dict = mig_user_map.get(client_id, None)
    if mig_user_dict is None:
        if allow_missing:
            status = True
            missing = True
        else:
            template = ": Missing MiG user"
            err_msg += template
            _logger.error(log_err_msg)
    else:
        try:
            # _logger.debug("Deleting MiG user: %r" %
            #               project_client_id)
            delete_user(mig_user_dict, configuration.config_file,
                        mig_user_db_path, force=True)
            status = True
        except Exception as exc:
            status = False
            _logger.error(log_err_msg
                          + ": %s" % (exc))
    ret_msg = err_msg
    if status:
        if missing:
            ret_msg = missing_msg
            log_msg = log_missing_msg
        else:
            ret_msg = ok_msg
            log_msg = log_ok_msg
        _logger.info(log_msg)

    return (status, ret_msg)


def __get_gdp_user_log_entry(configuration,
                             client_id,
                             match_client_id=True,
                             match_scrambled_client_id=True,
                             do_lock=True):
    """Returns (client_id, scrambled_client_id) user log entry for *client_id*
    """
    _logger = configuration.logger

    result = None
    (log_filepath, log_lock_filepath) = __gdp_user_log_filepath(configuration)
    scrambled_client_id = __scramble_user_id(configuration, client_id)
    if scrambled_client_id is None:
        return result
    if do_lock:
        flock = acquire_file_lock(log_lock_filepath)
    try:
        if not os.path.exists(log_filepath):
            touch(log_filepath, configuration)
        fh = open(log_filepath, 'rb')
        for line in fh:
            line_arr = [i.strip() for i in line.split(':')]
            if (match_client_id and client_id == line_arr[1]) \
                    or (match_scrambled_client_id
                        and scrambled_client_id == line_arr[2]):
                result = (line_arr[1], line_arr[2])
        fh.close()
    except Exception as exc:
        _logger.error("GDP: __get_gdp_user_log_entry failed: %s" % exc)
        result = None
    if do_lock:
        release_file_lock(flock)

    return result


def __update_gdp_user_log(configuration, client_id, do_lock=True):
    """Add *client_id* and it's scrambled version to GDP users log"""
    _logger = configuration.logger

    retval = False
    flock = None
    (log_filepath, log_lock_filepath) = __gdp_user_log_filepath(configuration)
    if do_lock:
        flock = acquire_file_lock(log_lock_filepath)

    gdp_user_log_entry = __get_gdp_user_log_entry(configuration,
                                                  client_id,
                                                  match_client_id=True,
                                                  do_lock=False)
    if gdp_user_log_entry:
        retval = True
        _logger.info("User: %r already exists in GDP user log" % client_id)
    else:
        timestamp = time.time()
        current_datetime = datetime.datetime.fromtimestamp(timestamp)
        date = current_datetime.strftime('%d-%m-%Y_%H-%M-%S')
        scrambled_client_id = __scramble_user_id(configuration, client_id)
        content = "%s : %s : %s :\n" \
                % (date, client_id, scrambled_client_id)
        retval = write_file(content, log_filepath, _logger, mode='ab')
        if not retval:
            _logger.error("GDP: __update_gdp_user_log failed")
            result = False
    if do_lock:
        release_file_lock(flock)

    return retval


def __active_project(configuration, user_id, protocol, do_lock=True):
    """Returns dictionary with active project info for
    *user_id* with *protocol*"""

    _logger = configuration.logger
    # _logger.debug("user_id: %r, protocol: %r"
    #               % (user_id, protocol))

    result = None
    user_id = __validate_user_id(configuration, user_id)
    if user_id is not None:
        client_id = __client_id_from_user_id(configuration, user_id)

        if client_id is not None:
            user_db = __load_user_db(configuration, do_lock=do_lock)
            (status, _) = __validate_user_db(configuration, client_id,
                                             user_db)
            # Retrieve active project client id
            if status:
                result = {}
                user = user_db.get(client_id)
                account = user.get('account', {})
                account_protocol = account.get(protocol, {})
                role = account_protocol.get('role', '')
                protocol_last_login = account_protocol.get(
                    'last_login', {})
                protocol_last_timestamp = protocol_last_login.get(
                    'timestamp', '')
                protocol_last_ip = protocol_last_login.get('ip', '')
                if role:
                    result['user_id'] = user_id
                    result['protocol'] = protocol
                    result['client_id'] = client_id
                    result['project_client_id'] = role
                    result['project_short_id'] = \
                        __project_short_id_from_project_client_id(
                            configuration, role)
                    result['last_timestamp'] = protocol_last_timestamp
                    result['last_ip'] = protocol_last_ip
                    result['name'] = \
                        __project_name_from_project_client_id(configuration,
                                                              role)
    return result


def get_active_project_client_id(configuration, user_id, protocol):
    """Returns active project_client_id for *user_id* with *protocol*"""

    result = None
    active_project = __active_project(configuration, user_id, protocol)
    if active_project is not None:
        result = active_project.get('project_client_id', '')

    return result


def get_active_project_short_id(configuration, user_id, protocol):
    """Returns active project_short_id for *user_id* with *protocol*"""

    _logger = configuration.logger
    # _logger.debug("user_id: %r, protocol: %r"
    #               % (user_id, protocol))

    result = None
    project_client_id = get_active_project_client_id(
        configuration, user_id, protocol)
    result = __project_short_id_from_project_client_id(
        configuration, project_client_id)

    return result


def fill_category_meta(configuration, category_id, action, ref_dict):
    """Fill a data category meta dict for *category_id* based on configuration
    categories for *action* and actual reference values in *ref_dict*.
    Raises ValueError if one or more required category reference fields are
    missing from ref_dict or if category doesn't exist in data categories.
    """
    _logger = configuration.logger
    _logger.debug('fill %s dict from %s with %s values' % (category_id, action,
                                                           ref_dict))
    category_dict = {'category_id': category_id}
    category_map = dict([(i['category_id'], i) for i in
                         configuration.gdp_data_categories])
    if category_id not in category_map:
        raise ValueError('no such data category: %s' % category_id)
    category_dict.update(category_map[category_id])
    for ref_fill in category_dict.get('references', {}).get(action, []):
        key = ref_fill['ref_id']
        if key not in ref_dict:
            _logger.error('no %s with %s value in ref dict: %s' %
                          (category_id, key, ref_dict))
            raise ValueError('no %s value' % key)
        ref_fill['value'] = ref_dict[key]

    return category_dict


def update_category_meta(configuration, client_id, project, category_dict,
                         action, source=None, user=None):
    """Update *project* category meta dict with one or more category and
    *action* references from *category_dict* on behalf of *client_id*.
    """
    _logger = configuration.logger
    # Lazy fill missing entries
    meta = project['category_meta'] = project.get('category_meta', {})
    meta['category_id'] = meta.get('category_id', '')
    if not meta['category_id']:
        meta['category_id'] = category_dict['category_id']
    meta['actions'] = meta.get('actions', [])
    save_entry = {'date': "%s" % datetime.datetime.now(), 'user': client_id,
                  'action': action, 'references': []}
    if source:
        save_entry['source'] = source
    if user:
        save_entry['user'] = user
    action_refs = category_dict.get('references', {}).get(action, [])
    _logger.debug("action: %s, refs: %s" % (action, action_refs))
    for ref_entry in action_refs:
        if ref_entry and ref_entry.get('value', None):
            save_entry['references'].append(ref_entry)
    meta['actions'].append(save_entry)
    return project


def project_log(
        configuration,
        protocol,
        user_id,
        user_addr,
        action,
        failed=False,
        path=None,
        dst_path=None,
        details=None,
        project_name=None,
):
    """Log project actions, each project has a distinct logfile"""

    _logger = configuration.logger
    _gdp_logger = configuration.gdp_logger
    status = True
    scrambled_path = '-'
    scrambled_dst_path = '-'
    log_err_msg = "GDP: project_log: user_id: %r, protocol: %r" \
        % (user_id, protocol) \
        + ", action: %r, project_name: %r, ip: %r" \
        % (action, project_name, user_addr)

    # Validate action

    action = action.lower()
    if action not in valid_log_actions:
        status = False
        _logger.error(log_err_msg
                      + ": Action is NOT in valid_log_actions %s"
                      % valid_log_actions)

    # Validate protocol

    if protocol not in valid_protocols:
        status = False
        _logger.error(log_err_msg
                      + ": Protocol is NOT in valid_protocols: %s"
                      % valid_protocols)

    # Get client_id and project_client_id from user_id

    if status:
        possible_project_client_id = expand_openid_alias(
            user_id, configuration)
        possible_client_id = __client_id_from_project_client_id(
            configuration, possible_project_client_id)
        if possible_client_id is not None:
            client_id = possible_client_id
            project_client_id = possible_project_client_id
        else:
            client_id = possible_project_client_id
            project_client_id = None

    # Generate scrambled user id for log

    if status:
        scrambled_user = __scramble_user_id(configuration, client_id)

    # Get project name

    if status and project_name is None:
        project_name = \
            __project_name_from_project_client_id(configuration,
                                                  project_client_id)

    # Validate project name

    if status and project_name is None:
        status = False
        _logger.error(log_err_msg
                      + ": Missing project name")

    # Validate user ip addr

    if status and user_addr is None:
        status = False
        _logger.error(log_err_msg
                      + ": Missing ip addr")

    if status:
        if details is None:
            details = '-'
        else:

            # Make sure that no user details are revealed in GDP log

            try:
                details = "%s" % details
                # _logger.debug("user_id: %s" % user_id)
                details = details.replace(user_id, scrambled_user)

                # Scramble project_client_id and associated short_id and dirs

                project_client_id = \
                    __project_client_id_from_user_id(
                        configuration, user_id)
                # _logger.debug("project_client_id: %s" % project_client_id)
                if project_client_id:
                    scrambled_project_client_id = \
                        __scramble_user_id(configuration, project_client_id)
                    details = details.replace(
                        project_client_id, scrambled_project_client_id)
                    project_dir = client_id_dir(project_client_id)
                    # _logger.debug("project_dir: %s" % project_dir)
                    scrambled_project_dir = __scramble_user_id(
                        configuration, project_client_id)
                    details = details.replace(
                        project_dir, scrambled_project_dir)
                    project_short_id = __short_id_from_client_id(configuration,
                                                                 client_id)
                    # _logger.debug("project_short_id: %s" % project_short_id)
                    scrambled_project_short_id = __scramble_user_id(
                        configuration, project_short_id)
                    details = details.replace(
                        project_short_id, scrambled_project_short_id)

                # Scramble client_id and associated short_id and dirs

                client_id = __client_id_from_user_id(
                    configuration, user_id)
                # _logger.debug("client_id: %s" % client_id)
                if client_id:
                    scrambled_client_id = __scramble_user_id(
                        configuration, client_id)
                    details = details.replace(client_id, scrambled_client_id)
                    client_dir = client_id_dir(client_id)
                    # _logger.debug("client_dir: %s" % client_dir)
                    scrambled_client_dir = __scramble_user_id(
                        configuration, client_dir)
                    details = details.replace(client_dir, scrambled_client_dir)
                    short_id = __short_id_from_client_id(configuration,
                                                         client_id)
                    # _logger.debug("short_id: %s" % short_id)
                    scrambled_short_id = __scramble_user_id(
                        configuration, short_id)
                    details = details.replace(short_id, scrambled_short_id)
                else:
                    raise ValueError(
                        "Missing client_id for user_id: %s" % user_id)
            except Exception as exc:
                status = False
                _logger.error(log_err_msg + ": %s" % exc)

    if status:
        if path is not None:
            scrambled_path = __scramble_path(configuration, path)
            details = details.replace(path, scrambled_path)
        if dst_path is not None:
            scrambled_dst_path = __scramble_path(configuration, dst_path)
            details = details.replace(dst_path, scrambled_dst_path)

    if status:
        if not failed:
            status_msg = "OK"
        else:
            status_msg = "FAILED"

    if status:
        msg = ": %s : %s : %s : %s : %s : %s : %s : %s : %s :" % (
            project_name,
            scrambled_user,
            user_addr,
            protocol,
            action,
            status_msg,
            scrambled_path,
            scrambled_dst_path,
            details
        )
        _gdp_logger.info(msg)

        # Log message to MiG log with caller details:
        # import inspect
        # frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
        # module_name = inspect.getmodulename(frameinfo[0])
        # revision = 1
        # function_name = frameinfo[2]
        # lineno = frameinfo[1]
        # _logger.debug('GDP:%s:%s:%s:%s: %s' % (module_name, revision,
        #                                       function_name, lineno, msg))

    return status


def validate_user(configuration, user_id, user_addr, protocol, do_lock=True):
    """Validate user:
    Log every validation
    Validate user database format
    Check if user is active
    Check for Geo ip (TODO)
    Check for ip change between logins
    """

    _logger = configuration.logger
    # _logger.debug("user_id: %r, user_addr: %r, protocol: %r"
    #               % (user_id, user_addr, protocol))

    user = None
    account = None
    account_state = None

    client_id = __client_id_from_user_id(configuration, user_id)

    ok_msg = ""
    err_msg = ""
    log_ok_msg = "GDP: Validated user: %r, ip: %s, protocol: %r" % (
        client_id, user_addr, protocol)
    log_err_msg = "GDP: Rejected user: %r, ip: %s, protocol: %r" % (
        client_id, user_addr, protocol)

    # _logger.debug("client_id: %r" % client_id)

    user_db = __load_user_db(configuration, do_lock=do_lock)
    (status, validate_msg) = __validate_user_db(configuration, client_id,
                                                user_db)
    if not status:
        err_msg = validate_msg
    else:

        # Retrieve user account info

        user = user_db.get(client_id)
        account = user.get('account')
        account_state = account.get('state')
        account_protocol = account.get(protocol)
        protocol_last_login = account_protocol.get('last_login')
        protocol_login_timestamp = protocol_last_login.get('timestamp')
        protocol_login_ip = protocol_last_login.get('ip')

        # Check if user account is active
        if account_state == 'suspended':
            status = False
            template = "Account is suspended"
            err_msg += template
            _logger.error(log_err_msg
                          + ": " + err_msg)
        elif account_state == 'removed':
            status = False
            template = "Account is removed"
            err_msg += template
            _logger.error(log_err_msg
                          + ": " + template)

        # Generate last login message

        if status and protocol_login_ip:
            lastlogin = datetime.datetime.fromtimestamp(
                protocol_login_timestamp)
            lastloginstr = lastlogin.strftime('%d/%m/%Y %H:%M:%S')
            ok_msg = "Last %s project login: %s from %s" \
                % (protocol, lastloginstr, protocol_login_ip)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def get_users(configuration, do_lock=True):
    """Returns a dict of GDP users on the form:
    {short_id: client_id}"""

    _logger = configuration.logger
    user_db = __load_user_db(configuration, do_lock=do_lock)

    result = {}
    for client_id in user_db:
        short_id = __short_id_from_client_id(configuration,
                                             client_id)
        result[short_id] = client_id

    return result


def get_projects(configuration, client_id, state, owner_only=False):
    """Return dictionary of GDP projects for user *client_id* with *state*"""

    _logger = configuration.logger
    # _logger.debug("client_id: %r, state: %r" % (client_id, state))

    status = True
    result = None
    log_err_msg = "Failed to get projects for user: %r, state: %r" % (
        client_id, state)

    # Check state

    if not state in valid_project_states:
        status = False
        _logger.error(log_err_msg
                      + ": State NOT in valid_states: %s"
                      % valid_project_states)

    # Retrieve user

    if status:
        user_db = __load_user_db(configuration)
        (status, _) = __validate_user_db(
            configuration, client_id, user_db=user_db)
        if not status:
            _logger.error(log_err_msg
                          + ": Invalid GDP DB format")

    # Generate project list

    if status:
        user_projects = user_db.get(client_id, {}).get('projects', {})
        result = {}
        for (key, value) in user_projects.items():
            # Implicit fill once and for all for backwards compatibility
            project_state = value['state'] = value.get('state', '')
            project_category_meta = value['category_meta'] = \
                value.get('category_meta', {})
            project_category = project_category_meta['category_id'] = \
                project_category_meta.get('category_id', '')
            project_actions = project_category_meta['actions'] = \
                project_category_meta.get('actions', [])
            if state == project_state:
                if not owner_only or owner_only and \
                    vgrid_is_owner(key,
                                   client_id,
                                   configuration,
                                   recursive=False):
                    result[key] = value

    return result


def get_project_info(configuration,
                     owner_client_id,
                     project_name,
                     do_lock=True):
    """Extract project information including list of participants.
    """
    _logger = configuration.logger
    # _logger.debug("owner_client_id: %r, project_name: %r, do_lock: %s" %
    #               (owner_client_id, project_name, do_lock))

    result = {
        'name': '',
        'owner': {
            'name': '',
            'email': '',
            'short_id': '',
            'client_id': '',
            'project_client_id': '',
            'state': '',
        },
        'create': {
            'date': '',
            'category': '',
            'references': [],
        },
        'users': [],
    }
    mig_user_map = get_full_user_map(configuration)
    user_db = __load_user_db(configuration, do_lock=do_lock)
    owner_project = user_db.get(owner_client_id, {}).get(
        'projects', {}).get(project_name, '')
    if not owner_project:
        _logger.warning("Missing project: %s for user: %s"
                        % (project_name, owner_client_id))
        return result

    category_map = dict([(i['category_id'], i) for i in
                         configuration.gdp_data_categories])
    owner_project_meta = owner_project.get('category_meta', {})
    category_id = owner_project_meta.get('category_id', '')
    if category_id not in category_map:
        _logger.error("Missing data category: %s used by project: %s"
                      % (category_id, project_name))
        return result

    # Fill result dict

    result['name'] = project_name

    # Fill owner info

    result['owner'] = {
        'name': extract_field(owner_client_id, 'full_name'),
        'email': extract_field(owner_client_id, 'email'),
        'short_id': __short_id_from_client_id(configuration, owner_client_id),
        'client_id': owner_client_id,
        'project_client_id': owner_project.get('client_id', ''),
        'state': owner_project.get('state', ''),
    }

    # Fill info from project create

    owner_project_meta = owner_project.get('category_meta', {})
    result['create']['category'] = category_map.get(
        category_id, {}).get('category_title', '')
    created_meta = {}
    for ent in owner_project_meta.get('actions', []):
        if ent.get('action', '') == 'create_project':
            created_meta = ent
            break
    if created_meta:
        # TODO: Format date to EPOC timestamp ?
        result['create']['date'] = created_meta.get('date', '')
        result['create']['references'] = created_meta.get('references', [])

    # Fill users associated with project

    for client_id in user_db:
        if client_id == owner_client_id:
            continue
        mig_user_dict = mig_user_map.get(client_id, None)
        user_projects = user_db.get(client_id, {}).get('projects', {})
        project = user_projects.get(project_name, {})
        # _logger.debug("client: %s, project: %s" % (client_id, project))
        if project:
            result['users'].append({
                'name': extract_field(client_id, 'full_name'),
                'email': extract_field(client_id, 'email'),
                'short_id':
                __short_id_from_client_id(configuration, client_id),
                'client_id': client_id,
                'project_client_id': project.get('client_id', ''),
                'state': project.get('state', ''),
                'allowed_owner':
                vgrid_create_allowed(configuration, mig_user_dict)
            })
    return result


def get_project_user_dn(configuration, requested_script, client_id, protocol):
    """Return project client id for user *client_id*.
    If user *client_id* is not logged into a project '' is returned.
    If *requested_script* is not a valid GDP page '' is returned.
    If *requested_script* is in skip_rewrite *client_id* is returned
    """

    _logger = configuration.logger
    # _logger.debug("requested_script: %r, client_id: %r, protocol: %r"
    #               % (requested_script, client_id, protocol))

    result = ''
    log_err_msg = "GDP: REJECTED user: " \
        + "%r, protocol: %r, requested_script: %r" \
        % (client_id, protocol, requested_script)

    # Check for valid GDP script

    valid = False
    for script in valid_auth_scripts:
        if requested_script.find(script) > -1:
            valid = True
            break
    if not valid:
        _logger.error(log_err_msg
                      + ": NOT in valid_auth_scripts: %s" %
                      valid_auth_scripts)
    else:

        # Check if requested_script operates with original client_id
        # or project client_id

        for skip_rewrite in skip_client_id_rewrite:
            if requested_script.find(skip_rewrite) > -1:
                result = client_id
                break

        # Get active project for user client_id and protocol

        if not result:
            user_db = __load_user_db(configuration)
            result = user_db.get(client_id,
                                 {}).get('account',
                                         {}).get(protocol,
                                                 {}).get('role', '')
        if not result:
            _logger.error(log_err_msg
                          + ": No active project for user")

    return result


def ensure_gdp_user(configuration, client_addr, client_id):
    """Ensure GDP user db entry for *client_id*"""

    _logger = configuration.logger
    # _logger.debug("client_addr: %r, client_id: %r"
    #               % (client_addr, client_id))

    status = False
    (_, db_lock_filepath) = __gdp_db_filepath(configuration)

    user_db = __load_user_db(configuration, allow_missing=True)
    user = user_db.get(client_id, None)
    err_msg = "Failed to ensure user: %r from ip: %s" \
        % (client_id, client_addr)
    log_err_msg = "GDP: " + err_msg
    if user is not None:
        status = True
    else:
        (_, log_lock_filepath) = __gdp_user_log_filepath(configuration)
        log_flock = acquire_file_lock(log_lock_filepath)
        gdp_user_log_entry = __get_gdp_user_log_entry(configuration,
                                                      client_id,
                                                      match_client_id=False,
                                                      do_lock=False)
        if gdp_user_log_entry and gdp_user_log_entry[0] != client_id:
            err_msg += ": Scrambled user already exists in user log"
            _logger.error(log_err_msg + ": Scrambled user: %r"
                          % gdp_user_log_entry[1]
                          + " already exists in user log for user: %r"
                          % gdp_user_log_entry[0])
        elif gdp_user_log_entry and gdp_user_log_entry[0] == client_id:
            template = ": User already exists in user log"
            err_msg += template
            _logger.error(log_err_msg + template)
        else:
            db_flock = acquire_file_lock(db_lock_filepath)
            user_db = __load_user_db(configuration,
                                     do_lock=False, allow_missing=True)
            user_db[client_id] = __create_gdp_user_db_entry(configuration)
            update_status = __update_gdp_user_log(
                configuration, client_id, do_lock=False)
            if update_status:
                __save_user_db(configuration, user_db, do_lock=False)
                _logger.info("GDP: Created GDP DB entry for user: %r"
                             % client_id
                             + " from IP: %s" % client_addr)
                status = True
            else:
                template = ": Failed to create GDP DB entry"
                err_msg += template
                _logger.error(log_err_msg + template)
            release_file_lock(db_flock)
        release_file_lock(log_flock)

    ret_msg = ""
    if not status:
        ret_msg = err_msg

    return (status, ret_msg)


def project_remove_user(
        configuration,
        owner_client_addr,
        owner_client_id,
        client_id,
        project_name,
        allow_owner=False,
        send_notify=True):
    """User *owner_client_id* removed user *client_id* from *project_name"""

    _logger = configuration.logger
    # _logger.debug(
    #     "owner_client_addr: %r, owner_client_id: %r"
    #     % (owner_client_addr, owner_client_id)
    #     + ", client_id: %r, project_name: %r"
    #     % (client_id, project_name))

    status = True
    category_dict = {}

    # Get login handle (email) from client_id

    login = __short_id_from_client_id(configuration,
                                      client_id)

    project_client_id = get_project_client_id(
        client_id,
        project_name)

    ok_msg = "Removed user: %r from project %r" % (login, project_name)
    err_msg = "Failed to remove user: %r from project %r" % (
        login, project_name)
    log_ok_msg = "GDP: Owner: %r from ip: %s" \
        % (owner_client_id, owner_client_addr) \
        + ", removed user (%s): %r from project %r" \
        % (login, project_client_id, project_name)
    log_err_msg = "GDP: Owner: %r from ip: %s" \
        % (owner_client_id, owner_client_addr) \
        + ", failed to remove user (%s): %r from project %r" \
        % (login, project_client_id, project_name)

    # Check if owner_client_id is in owners

    if not vgrid_is_owner(project_name,
                          owner_client_id,
                          configuration,
                          recursive=False):
        status = False
        template = ": Invalid project owner"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Check if client_id is in owners

    if status \
        and not allow_owner \
        and vgrid_is_owner(project_name,
                           client_id,
                           configuration,
                           recursive=False):
        status = False
        template = ": The project owner can't be removed from project"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Update user project actions, remove from vgrid members
    # and delete

    if status:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)

        # Retrieve user and project info

        user_db = __load_user_db(configuration, do_lock=False)
        user_projects = user_db.get(client_id, {}).get('projects', {})
        project = user_projects.get(project_name, {})
        project_state = project.get('state', '')
        if not project:
            status = False
            template = ": Provided user is NOT registered with the project"
            err_msg += template
            _logger.error(log_err_msg + template)
        elif project_state == 'removed':
            status = False
            template = ": Provided user is already removed from the project"
            err_msg += template
            _logger.error(log_err_msg + template)
        elif project_state == 'invited':
            project['state'] = 'removed'
        elif project_state == 'accepted':
            _logger.info("GDP: Removing member: %r from vgrid: %r" %
                         (project_client_id, project_name))
            # Remove user as vgrid member
            (status, vgrid_msg) = vgrid_remove_members(configuration,
                                                       project_name,
                                                       [project_client_id],
                                                       allow_empty=allow_owner)
            if not status:
                _logger.error(log_err_msg
                              + ": %s" % vgrid_msg)
            else:
                # Delete MiG user
                (status, delete_msg) \
                    = __delete_mig_user(configuration, project_client_id)
                if not status:
                    template = ": Failed to remove user"
                    err_msg += template
                    _logger.error(log_err_msg
                                  + "%s: %s" % (template, delete_msg))
            project['state'] = 'removed'
        else:
            status = False
            _logger.error(log_err_msg
                          + ": Unexpected project state: %r" % project_state)

    # Log removed user

    if status:
        project_log_msg = "User id: %s" \
            % __scramble_user_id(configuration, client_id)

        status = project_log(
            configuration,
            'https',
            owner_client_id,
            owner_client_addr,
            'removed_user',
            details=project_log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")

    # Update owner project actions

    if status:
        # Always register remove with owner
        owner_projects = user_db.get(owner_client_id, {}).get('projects',
                                                              {})
        owner_project = owner_projects[project_name]
        owner_project_category_meta = owner_project.get('category_meta', {})
        owner_project_category_id = owner_project_category_meta.get(
            'category_id', '')
        owner_project_actions = owner_project_category_meta.get('actions', [])

        # Find references for last owner action
        # Fist look for an 'invite_user' action
        category_status = False
        for opa in reversed(owner_project_actions):
            _logger.debug("opa: %s" % opa)
            opa_action = opa.get('action', '')
            opa_user = opa.get('user', '')
            if opa_user == client_id and opa_action == 'invite_user':
                category_dict = {i['ref_id']: i['value'] for i in
                                 opa.get('references', [])}
                category_status = True
                break
        if not category_status:
            status = False
            template = ": Could not find any valid reference in owner actions"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:
        _logger.debug("category_dict: %s" % category_dict)
        category_entry = fill_category_meta(configuration,
                                            owner_project_category_id,
                                            'remove_user', category_dict)
        _logger.debug("category_entry: %s" % category_entry)
        # Update owner actions
        update_category_meta(configuration,
                             owner_client_id, owner_project,
                             category_dict,
                             'remove_user',
                             source=owner_client_id,
                             user=client_id)
        # Update user actions
        update_category_meta(configuration,
                             client_id, project,
                             category_dict,
                             'remove_user',
                             source=owner_client_id,
                             user=client_id)
        __save_user_db(configuration, user_db, do_lock=False)
    release_file_lock(flock)

    if status and send_notify:
        _logger.info("handle remove notify")
        owner_login = __short_id_from_client_id(
            configuration, owner_client_id)
        status = __send_project_remove_user_confirmation(configuration,
                                                         owner_login,
                                                         login,
                                                         project_name,
                                                         category_entry)
        if not status:
            template = ": Failed to send project remove confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_invite_user(
        configuration,
        owner_client_addr,
        owner_client_id,
        client_id,
        project_name,
        category_dict,
        in_create=False):
    """User *owner_client_id* invites user *client_id* to *project_name.
    Register additional reference tracking with *category_dict*.
    If in_create is set it means that the invite is a part of project_create so
    that the notification and references handling should be fitted accordingly.
    """

    _logger = configuration.logger
    # _logger.debug(
    #    "owner_client_addr: %r, owner_client_id: %r"
    #    % (owner_client_addr, owner_client_id)
    #    + ", client_id: %r, project_name: %r"
    #    % (client_id, project_name))

    # Get login handle (email) from client_id

    login = __short_id_from_client_id(configuration,
                                      client_id)
    project_client_id = get_project_client_id(
        client_id,
        project_name)

    status = True
    ok_msg = "Invited user: %r to project %r" % (login, project_name)
    err_msg = "Failed to invite user: %r to project: %r" % (
        login, project_name)
    log_ok_msg = "GDP: Owner: %r from ip: %s" \
        % (owner_client_id, owner_client_addr) \
        + ", invited user (%s): %r to project %r" \
        % (login, project_client_id, project_name)
    log_err_msg = "GDP: Owner: %r from ip: %s" \
        % (owner_client_id, owner_client_addr) \
        + ", failed to invite user (%s): %r to project %r" \
        % (login, project_client_id, project_name)

    # Resolve category metadata, if in create then resolve for both
    # 'invite_user' and 'create_project'
    category_id = category_dict.get('category_id', '')
    if not in_create:
        project_category_dict = None
        invite_category_dict = category_dict
        ref_pairs = [(i['ref_id'], i['value']) for i in
                     invite_category_dict.get('references', {}).get('invite_user', [])]
    else:
        project_category_dict = category_dict
        _logger.debug("project_category_dict: %s" % project_category_dict)
        ref_pairs_create = [(i['ref_id'], i['value']) for i in
                            project_category_dict.get('references', {}).get('create_project', [])]
        _logger.debug("ref_pairs_create: %s" % ref_pairs_create)
        try:
            # Generate 'fake' invite ref pairs if in_create
            default_category_dict = [i
                                     for i in configuration.gdp_data_categories
                                     if i['category_id'] == category_id][0]
            _logger.debug("default_category_dict: %s" % default_category_dict)
            ref_pairs = [(i['ref_id'], 'AUTO') for i in
                         default_category_dict.get('references', {}).get('invite_user', [])]
            # _logger.debug("ref_pairs: %s" % ref_pairs)
            ref_dict = dict(ref_pairs)
            # Update with values from create action
            ref_dict.update(dict(ref_pairs_create))
            invite_category_dict = fill_category_meta(configuration,
                                                      category_id, 'invite_user',
                                                      ref_dict)
            _logger.debug("project_category_dict: %s" % project_category_dict)
            _logger.debug("invite_category_dict: %s" % invite_category_dict)
        except Exception as exc:
            template = ": failed to fill category meta for 'invite_user'"
            err_msg += template
            _logger.error("%s%s, err: %s" % (log_err_msg, template, exc))
            return (False, err_msg)

    # Check ownership

    if not vgrid_is_owner(project_name,
                          owner_client_id,
                          configuration,
                          recursive=False):
        status = False
        template = ": Invalid project owner"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Create invitation

    if status:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)

        # Retrieve project info

        user_db = __load_user_db(configuration, do_lock=False)
        user_projects = user_db.get(client_id, {}).get('projects', {})
        project = user_projects.get(
            project_name,
            {'state': '',
             'client_id': project_client_id,
             'category_meta': {
                 'category_id': category_id,
                 'actions': []},
             })
        project_state = project.get('state', '')
        if not project_state or project_state == 'removed':

            # Log invitation details to project log

            log_msg = "User id: %s" \
                % __scramble_user_id(configuration, client_id)
            if ref_pairs:
                log_parts = ["%s: %r" % pair for pair in ref_pairs]
                log_msg += " with references: " + ', '.join(log_parts)
            else:
                log_msg += " without required references"
            status = project_log(
                configuration,
                'https',
                owner_client_id,
                owner_client_addr,
                'invited_user',
                details=log_msg,
                project_name=project_name,
            )
            if not status:
                _logger.error(log_err_msg
                              + ": Project log failed")
        else:
            status = False
            template = ": User already registered with project"
            err_msg += template
            _logger.error(log_err_msg + template)

        if status:
            # Always register create and invite with owner
            if in_create:
                owner_project = project
            else:
                owner_projects = user_db.get(owner_client_id, {}).get(
                    'projects', {})
                owner_project = owner_projects[project_name]
            # If in create then register 'create_project' action with owner
            if in_create:

                _logger.debug("updating create meta: %s" %
                              project_category_dict)
                update_category_meta(configuration, owner_client_id, owner_project,
                                     project_category_dict, 'create_project',
                                     source=owner_client_id,
                                     user=owner_client_id
                                     )
                # Register fake 'invite_user' action with owner
                update_category_meta(configuration, owner_client_id, owner_project,
                                     invite_category_dict, 'invite_user',
                                     source=owner_client_id,
                                     user=owner_client_id)
            else:
                # Register 'invite_user' action with owner
                update_category_meta(configuration, owner_client_id, owner_project,
                                     invite_category_dict, 'invite_user',
                                     source=owner_client_id,
                                     user=client_id)
                # Register 'invite_user' action with user
                update_category_meta(configuration, client_id, project,
                                     invite_category_dict, 'invite_user',
                                     source=owner_client_id,
                                     user=client_id)

            project['state'] = 'invited'
            user_projects[project_name] = project
            __save_user_db(configuration, user_db, do_lock=False)
        release_file_lock(flock)

    if status:
        owner_login = __short_id_from_client_id(
            configuration, owner_client_id)
        if in_create:
            _logger.info("handle implicit create notify inside invite")
            status = __send_project_create_confirmation(configuration,
                                                        owner_login,
                                                        project_name,
                                                        category_dict)
        else:
            _logger.info("handle proper invite notify")
            status = __send_project_invite_user_confirmation(configuration,
                                                             owner_login,
                                                             login,
                                                             project_name,
                                                             category_dict)
        if not status:
            template = ": Failed to send project invite user confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def reset_account_roles(
        configuration,
        client_id,
        gdp_db_path=None,
        verbose=False):
    """Force reset GDP user account role for all protocols"""

    _logger = configuration.logger

    status = True
    flock = None
    gdp_user = None
    ok_msg = "Account roles reset"
    err_msg = "Failed reset account roles"
    log_ok_msg = "GDP: User: %r" % client_id \
        + ", reset account roles"

    log_err_msg = "GDP: User: %r" % client_id \
        + ", failed to reset account roles"

    if status:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration,
                                                  db_path=gdp_db_path)
        flock = acquire_file_lock(db_lock_filepath)
        gdp_db = __load_user_db(
            configuration, do_lock=False, db_path=gdp_db_path)
        gdp_user = gdp_db.get(client_id, {})

        if not gdp_user:
            status = False
            template = ", invalid GDP user"
            err_msg += "%s: %r" % (template, client_id)
            _logger.error(log_err_msg + template)

    if status:
        ok_msg = ""
        for protocol in valid_protocols:
            gdp_account_protocol = gdp_user.get(
                'account', {}).get(protocol, {})
            if gdp_account_protocol:
                role = gdp_account_protocol.get('role', '')
                gdp_account_protocol['role'] = ''
                template = "current role: %r for protocol: %r" \
                    % (role, protocol)
                ok_msg += ", " + template
                if verbose:
                    msg = "Resetting " + template
                    print(msg)
                    _logger.debug("GDP: " + msg)
            else:
                status = False
                template += ", malformed GDP user DB"
                err_msg += template
                _logger.error(err_msg + template)
                break
    if status:
        __save_user_db(configuration, gdp_db,
                       do_lock=False, db_path=gdp_db_path)
        ok_msg += " for user: %r" % client_id
        _logger.info(log_ok_msg)

    if flock:
        release_file_lock(flock)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg

    return(status, ret_msg)


def set_account_state(
        configuration,
        client_id,
        account_state,
        gdp_db_path=None):
    """Change GDP user account state"""

    _logger = configuration.logger

    status = True
    flock = None
    gdp_user = None
    ok_msg = "Changed account state to: %r" % account_state
    err_msg = "Failed change account state to: %r" % account_state
    log_ok_msg = "GDP: User: %r" % client_id \
        + ", changed account state to: %r" % account_state

    log_err_msg = "GDP: User: %r" % client_id \
        + ", failed to change account state to: %r" % account_state

    if not account_state or account_state not in valid_account_states:
        status = False
        template = ", not in valid_account_states: %s" \
            % valid_account_states
        err_msg += template
        _logger.error(log_err_msg + template)

    if status:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration,
                                                  db_path=gdp_db_path)
        flock = acquire_file_lock(db_lock_filepath)
        gdp_db = __load_user_db(
            configuration, do_lock=False, db_path=gdp_db_path)
        gdp_user = gdp_db.get(client_id, {})

        if not gdp_user:
            status = False
            template = ", invalid GDP user"
            err_msg += "%s: %r" % (template, client_id)
            _logger.error(log_err_msg + template)

    if status:
        gdp_account_state = gdp_user.get('account', {}).get('state', '')
        if gdp_account_state:
            status = True
            gdp_user['account']['state'] = account_state
            __save_user_db(configuration, gdp_db,
                           do_lock=False, db_path=gdp_db_path)
            template = " from account state: %r" % gdp_account_state
            ok_msg += "%s for user: %r" % (template, client_id)
            _logger.info(log_ok_msg + template)
        else:
            status = False
            template = ", malformed GDP user DB"
            err_msg += template
            _logger.error(err_msg + template)
    if flock:
        release_file_lock(flock)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg

    return(status, ret_msg)


def edit_gdp_user(
        configuration,
        user_id,
        changes,
        conf_path,
        mig_db_path,
        gdp_db_path=None,
        force=False,
        verbose=False,
):
    """Edit user in GDP user database, MiG userdatabase
    and filesystem. In case of failure system is rolled back to
    orginal state.
    NOTE: We do _NOT_ lock databases and logs through the entire
          process as the useradm.edit_user file OPS might take a long time
          and thereby block auto signup.
    NOTE: 'force==True' disables rollback"""

    _logger = configuration.logger

    ok_msg = ""
    log_prefix = "GDP: edit user: %r, " % user_id
    rollback = False
    mig_user_map = get_full_user_map(configuration)
    gdp_user_rollback = None
    mig_edit_transactions = []
    new_user_id = None
    new_user_ids = []
    (db_filepath, db_lock_filepath) = __gdp_db_filepath(configuration,
                                                        db_path=gdp_db_path)
    (log_filepath, log_lock_filepath) = __gdp_user_log_filepath(configuration)

    # NOTE: we need explicit mig_db_path lookup here for direct calls
    if mig_db_path == keyword_auto:
        mig_db_path = default_db_path(configuration)

    if verbose:
        print(log_prefix)

    if force:
        msg = "force enabled, rollback DISABLED !!!"
        if verbose:
            print(msg)
        _logger.warning(log_prefix + msg)

    if verbose:
        msg = "Using MiG DB: %r" % mig_db_path
        print(msg)
        _logger.debug(msg)

        msg = "Using GDP DB: %s" % gdp_db_path
        print(msg)
        _logger.debug(msg)

    if verbose:
        msg = "Update GDP and MiG DB entry and dirs for %r: %s" \
            % (user_id, changes)
        _logger.debug(msg)
        print(msg)

    # Check if user is logged in on any of the valid protocols

    for protocol in valid_protocols:
        project_client_id = get_active_project_client_id(configuration,
                                                         user_id,
                                                         protocol)
        if project_client_id:
            project_name = \
                __project_name_from_project_client_id(configuration,
                                                      project_client_id)
            msg = "user currently logged in to project: %r with protocol: %r" \
                % (project_name, protocol)
            if verbose:
                print(msg)
            _logger.error(log_prefix + msg)
            if not force:
                return (False, msg)

    # Force clean rebuild of vgrid maps,
    # this should be done before copy/locking of database
    # and log files as it migth take some time

    msg = "rebuilding user, vgrid and resource maps to ensure consistency"
    if verbose:
        print(msg)
    _logger.info(log_prefix + msg)

    force_update_user_map(configuration, clean=True)
    force_update_vgrid_map(configuration, clean=True)
    if configuration.site_enable_resources:
        force_update_resource_map(configuration, clean=True)

    # Backup MiG user DB

    flock_mig_db = lock_user_db(mig_db_path)
    bck_mig_db_path = "%s.edituser.bck.%s" % (mig_db_path, time.time())
    try:
        copy_file(mig_db_path, bck_mig_db_path, configuration)
    except Exception as exc:
        msg = "failed to backup MiG user database: %r -> %r" % (
            mig_db_path, bck_mig_db_path)
        if verbose:
            print(msg)
        _logger.error(log_prefix + msg)
        release_file_lock(flock_mig_db)
        return (False, msg)
    release_file_lock(flock_mig_db)

    # Backup GDP user log

    flock_log = acquire_file_lock(log_lock_filepath)
    bck_log_filepath = "%s.edituser.bck.%s" % (log_filepath, time.time())
    try:
        copy_file(log_filepath, bck_log_filepath, configuration)
    except Exception as exc:
        msg = "failed to backup GDP users log: %r -> %r" % (
            log_filepath, bck_log_filepath)
        if verbose:
            print(msg)
        _logger.error(log_prefix + msg)
        release_file_lock(flock_log)
        return (False, msg)
    release_file_lock(flock_log)

    # Lock GDP database

    flock_gdp_db = acquire_file_lock(db_lock_filepath)

    # Backup GDP database

    bck_db_filepath = "%s.edituser.bck.%s" % (db_filepath, time.time())
    try:
        copy_file(db_filepath, bck_db_filepath, configuration)
    except Exception as exc:
        msg = "failed to backup GDP database: %r -> %r" % (
            db_filepath, bck_db_filepath)
        if verbose:
            print(msg)
        _logger.error(log_prefix + msg)
        release_file_lock(flock_gdp_db)
        return (False, msg)

    # Load GDP database

    gdp_db = __load_user_db(
        configuration, do_lock=False, db_path=gdp_db_path)
    gdp_user = gdp_db.get(user_id, {})
    gdp_user_rollback = copy.deepcopy(gdp_user)
    if not gdp_user:
        template = "invalid GDP user"
        msg = template + ": %r" % user_id
        if verbose:
            print("ERROR: " + msg)
        _logger.error(log_prefix + template)
        release_file_lock(flock_gdp_db)
        return (False, msg)

    # Release GDP database lock

    release_file_lock(flock_gdp_db)

    # Change MiG DB and GDP DB for project users

    user_projects = gdp_user.get('projects', {})
    for project_name, project_dict in user_projects.items():
        project_user_id = project_dict.get('client_id', {})
        if not project_user_id:
            msg = "missing user_id for project: %r" % project_name
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            if not force:
                rollback = True
                break

        # Pending project invitations require no further action
        # NOTE: if accept invite checks client_id it must be changed here, too
        if project_dict.get("state", None) == "invited":
            template = "transfer project invitation: %r" % project_name
            if verbose:
                print(template)
            _logger.info(log_prefix + template)
            continue

        new_changes = copy.deepcopy(changes)

        # Update changes dict with project name

        new_changes[gdp_distinguished_field] = project_name

        # Generate open id aliases based on changes dict

        aliases = []
        for user_alias in [configuration.user_openid_alias,
                           configuration.user_davs_alias,
                           configuration.user_sftp_alias]:
            if user_alias in new_changes:
                project_user_alias = "%s@%s" \
                    % (new_changes[user_alias], project_name)
                if not project_user_alias in aliases:
                    aliases.append(project_user_alias)
        new_changes['openid_names'] = aliases

        if verbose:
            msg = "updating MiG DB entry and dirs for %r: %s" \
                % (project_user_id, project_dict)
            print(msg)
            _logger.debug(msg)

        # Generate transaction information needed by rollback

        mig_user_dict = mig_user_map.get(project_user_id, None)
        if not mig_user_dict:
            msg = "missing user entry: %r in MiG DB" % project_user_id
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            if not force:
                rollback = True
                break
        fill_distinguished_name(mig_user_dict)
        fill_distinguished_name(new_changes)
        mig_edit_transactions.append({'source': copy.deepcopy(mig_user_dict),
                                      'target': copy.deepcopy(new_changes)})

        # Change project user in MiG user database and on filesystem

        try:
            new_project_user = edit_user(project_user_id, new_changes,
                                         conf_path, mig_db_path,
                                         force, verbose)
            new_project_user_id = new_project_user['distinguished_name']
            new_user_ids.append(new_project_user_id)
            project_dict['client_id'] = new_project_user_id

            template = "project user:\n%r" % project_user_id \
                + "\nchanged to:\n%r" % new_project_user_id
            if verbose:
                print(template)
            _logger.info(log_prefix + template)
        except Exception as exc:
            msg = "failed to edit user: %r: %s" \
                % (project_user_id, exc)
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            if not force:
                rollback = True
                break

    # Update main user

    new_changes = copy.deepcopy(changes)

    if not rollback:
        if verbose:
            msg = "updating MiG DB entry and dirs for %r: %s" \
                % (user_id, changes)
            print(msg)
            _logger.debug(msg)

        # Generate open id aliases based on changes dict

        aliases = []
        for user_alias in [configuration.user_openid_alias,
                           configuration.user_davs_alias,
                           configuration.user_sftp_alias]:
            if user_alias in new_changes:
                new_user_alias = new_changes[user_alias]
                if not new_user_alias in aliases:
                    aliases.append(new_user_alias)
        new_changes['openid_names'] = aliases

        # Generate transaction information needed by rollback

        mig_user_dict = mig_user_map.get(user_id, None)
        if not mig_user_dict:
            msg = "missing user entry %r in MiG DB" % user_id
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            if not force:
                rollback = True
        else:
            fill_distinguished_name(mig_user_dict)
            fill_distinguished_name(new_changes)
            mig_edit_transactions.append(
                {'source': copy.deepcopy(mig_user_dict),
                 'target': copy.deepcopy(new_changes)})

    if not rollback:
        try:

            # Change main user in MiG user database and on filesystem

            user = edit_user(user_id, new_changes,
                             conf_path, mig_db_path,
                             force, verbose)
            new_user_id = user['distinguished_name']
            new_user_ids.append(new_user_id)

            # Lock GDP DB

            flock_gdp_db = acquire_file_lock(db_lock_filepath)

            # Reload GDP DB

            gdp_db = __load_user_db(configuration,
                                    do_lock=False, db_path=gdp_db_path)

            # Rename user in GDP database

            gdp_db[new_user_id] = gdp_user
            del gdp_db[user_id]

            # Save GDP data base

            __save_user_db(configuration, gdp_db,
                           do_lock=False, db_path=gdp_db_path)

            # Release lock

            release_file_lock(flock_gdp_db)

            template = "user:\n%r" % user_id \
                + "\nchanged to:\n%r" % new_user_id

            ok_msg = template + "\n" \
                + "in GDP / MiG user database and file system"

            if verbose:
                print(ok_msg)
            _logger.info(log_prefix + template)

        except Exception as exc:
            msg = "failed to edit user: %r: %s" % (user_id, exc)
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            if not force:
                rollback = True

    if not rollback:

        # Update GDP users log file

        if verbose:
            msg = "updating GDP users log"
            print(msg)
            _logger.debug(msg)

        flock_log = acquire_file_lock(log_lock_filepath)
        for log_user_id in new_user_ids:
            status = __update_gdp_user_log(
                configuration, log_user_id, do_lock=False)
            if not status:
                msg = "Error: Failed to update GDP users log" \
                    + ", manual action is NEEDED !!!"
                print("ERROR: %s" % msg)
                _logger.error(msg)
                if not force:
                    rollback = True
                    break
        release_file_lock(flock_log)

    if rollback:

        # Roll back in case of failure

        msg = "Rolling back due to errors"
        if verbose:
            print(msg)
        _logger.info(log_prefix + msg)
        try:

            # Rollback entries in the MiG user database and on filesystem

            for transaction in mig_edit_transactions:
                rollback_org_id = transaction['source']['distinguished_name']
                rollback_id = transaction['target']['distinguished_name']
                rollback_dict = transaction['source']
                msg = "rolling back MiG DB user %r to %r: %s" % (
                    rollback_id, rollback_org_id, rollback_dict)
                if verbose:
                    print(msg)
                _logger.info(msg)
                user = edit_user(rollback_id, rollback_dict,
                                 conf_path, mig_db_path,
                                 True, verbose)
        except Exception as exc:
            msg = "failed to rollback: %s" % exc
            if verbose:
                print("ERROR: %s" % msg)
            _logger.error(log_prefix + msg)
            return (False, msg)

        # Roll back GDP DB entry

        msg = "rolling back GDP DB user: %r to %r" % \
            (new_user_id, user_id)
        if verbose:
            print(msg)
        _logger.info(log_prefix + msg)

        flock_gdp_db = acquire_file_lock(db_lock_filepath)
        gdp_db = __load_user_db(configuration,
                                do_lock=False, db_path=gdp_db_path)

        # Delete new_user_id from GDP DB if it was added

        if new_user_id and new_user_id in gdp_db:
            msg = "removing user: %r from GDP DB" % new_user_id
            if verbose:
                print(msg)
            _logger.info(log_prefix + msg)
            del gdp_db[new_user_id]

        # Restore original GDP user dict

        msg = "restoring original user: %r: %s" % (
            user_id, gdp_user_rollback)
        if verbose:
            print(msg)
        _logger.info(msg)
        gdp_db[user_id] = gdp_user_rollback
        __save_user_db(configuration, gdp_db,
                       do_lock=False, db_path=gdp_db_path)
        release_file_lock(flock_gdp_db)

    if not rollback:
        result = True
        ret_msg = ok_msg
    else:
        result = False
        msg = "Failed to edit user: %r" % (user_id)
        if verbose:
            print(msg)
        _logger.error(log_prefix + msg + ": %s" % changes)
        ret_msg = msg

    return (result, ret_msg)


def project_promote_to_owner(
        configuration,
        client_addr,
        client_id,
        promotee_client_id,
        project_name,
        category_dict):
    """Promote a project user to project owner"""

    flock = None
    status = True

    _logger = configuration.logger
    # _logger.debug("client_addr: %r, client_id: %r"
    #               + ", promotee_client_id: %r, project_name: %s"
    #               % (client_addr, client_id,
    #                  promotee_client_id, project_name))

    ok_msg = "Promote to project owner"
    err_msg = "Failed to promote to project owner"
    log_ok_msg = "GDP: Promote to project owner: %r" \
        % (promotee_client_id, ) \
        + " for project: %r, by owner: %r from ip: %s" \
        % (project_name, client_id, client_addr)
    log_err_msg = "GDP: Failed to promote to project owner: %r" \
        % (promotee_client_id) \
        + " for project: %r, by owner: %r from ip: %s" \
        % (project_name, client_id, client_addr)

    # Get owners list

    (owner_status, vgrid_owners_list) = vgrid_owners(project_name,
                                                     configuration,
                                                     recursive=False)
    if not owner_status:
        status = False
        template = ": Could not retrieve owners list"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %s" % vgrid_owners_list)

    # Check for promoter ownership

    if status and not vgrid_is_owner(project_name,
                                     client_id,
                                     configuration,
                                     recursive=False):
        status = False
        template = ": not project owner"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %r" % client_id)

    # Check for promotee ownership

    if status and vgrid_is_owner(project_name,
                                 promotee_client_id,
                                 configuration,
                                 recursive=False):
        status = False
        template = ": already project owner"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %r" % promotee_client_id)

    # Check if promotee is allowed as owner

    mig_user_map = get_full_user_map(configuration)
    mig_user_dict = mig_user_map.get(promotee_client_id, None)
    if not vgrid_create_allowed(configuration, mig_user_dict):
        status = False
        template = ": not allowed as owner"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %r" % promotee_client_id)

    if status:

        # Get promotee project client id

        project_promotee_client_id = get_project_client_id(
            promotee_client_id, project_name)

        # Check if user is a registred project member

        if not vgrid_is_member(project_name,
                               project_promotee_client_id,
                               configuration,
                               recursive=False):
            status = False
            template = ": project member not found"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %r" % project_promotee_client_id)

    if status:

        # Retrieve promoter project entry

        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)
        user_db = __load_user_db(configuration, do_lock=False)

        project = user_db.get(client_id, {}).get(
            'projects', {}).get(project_name, {})
        if not project:
            status = False
            template = ": missing project"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": for %r" % client_id)

    if status:

        # Retrieve promotee project entry

        promotee_project = user_db.get(promotee_client_id, {}).get(
            'projects', {}).get(project_name, {})
        if not promotee_project:
            status = False
            template = ": missing project for promotee"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": for %r" % client_id)

    if status:

        # Get owners list

        (owner_status, vgrid_owners_list) = vgrid_owners(project_name,
                                                         configuration,
                                                         recursive=False)
        if not owner_status:
            status = False
            template = ": Could not retrieve owners list"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % vgrid_owners_list)

    if status:

        # Change owner list

        new_vgrid_owners_list = copy.deepcopy(vgrid_owners_list)
        new_vgrid_owners_list.append(promotee_client_id)
        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name,
                                                     new_vgrid_owners_list)
        if not owner_status:
            status = False
            template = ": Could not save owner list"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % owner_msg)

    # Add promote user to project owner actions

    if status:

        # retrieve project actions

        category_meta = project.get('category_meta', {})
        project_actions = category_meta.get('actions', [])
        if not project_actions:
            status = False
            template = ": No project actions found"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:

        # Find create or promote_to_owner action

        project_action = ""
        user_invites = []
        for ent in project_actions:
            value = ent.get('action', '')
            if value == 'create_project' or value == 'promote_to_owner':
                project_action = ent
            elif value == 'invite_user':
                user_invites.append(copy.deepcopy(ent))

        if not project_action:
            status = False
            template = ": no valid project action found"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % project_actions)

    if status:

        # Fill promote_to_owner action with references
        # from project create action or last promote action

        ref_dict = {i['ref_id']: i['value'] for i in
                    project_action.get('references', [])}

        # Update last create/promote dict with current values

        ref_dict.update(category_dict)

        # Update promoter action list

        update_category_meta(configuration, client_id, project,
                             ref_dict, 'promote_to_owner',
                             source=client_id,
                             user=promotee_client_id)

        # Update promotee action list

        promotee_ref_dict = copy.deepcopy(ref_dict)
        update_category_meta(configuration,
                             promotee_client_id, promotee_project,
                             promotee_ref_dict, 'promote_to_owner',
                             source=client_id,
                             user=promotee_client_id)

        # Append all old invites to new owner actions
        # to preserve category information

        promotee_category_meta = promotee_project.get('category_meta', {})
        promotee_actions = promotee_category_meta.get('actions', [])
        if not promotee_actions:
            status = False
            template = ": No promotee project actions found"
            err_msg += template
            _logger.error(log_err_msg + template)

        for invite in user_invites:
            # _logger.debug("Adding original invite: %s" % invite)
            promotee_actions.append(invite)

        __save_user_db(configuration, user_db, do_lock=False)

    if flock:
        release_file_lock(flock)
        flock = None

    if status:

        # Write change to GDP log

        log_msg = "User id: %s" \
            % __scramble_user_id(configuration, promotee_client_id)

        log_status = project_log(
            configuration,
            'https',
            client_id,
            client_addr,
            'promoted_to_owner',
            details=log_msg,
            project_name=project_name,
        )

        if not log_status:
            status = False
            _logger.error(log_err_msg
                          + ": Promote user project log failed ")

    if status:

        # Send notification

        _logger.info("handle promote notify")
        login = __short_id_from_client_id(configuration, client_id)
        promotee_login = __short_id_from_client_id(
            configuration, promotee_client_id)

        send_status = \
            __send_project_promote_to_owner_confirmation(configuration,
                                                         login,
                                                         promotee_login,
                                                         project_name,
                                                         ref_dict)
        if not send_status:
            status = False
            template = ": Failed to send promote user confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    if flock is not None:
        release_file_lock(flock)

    # If errors occurred then roll back to original vgrid owners

    if not status:

        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name,
                                                     vgrid_owners_list)
        if not owner_status:
            template = ": Failed to roll back to original vgrid owners"
            _logger.error(log_err_msg + template + ": %s" % owner_msg)

    # Return

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_demote_owner(
        configuration,
        client_addr,
        client_id,
        demotee_client_id,
        project_name,
        category_dict):
    """Demote a project owner to member"""
    flock = None
    status = True

    _logger = configuration.logger
    _logger.debug("client_addr: %r, client_id: %r"
                  % (client_addr, client_id)
                  + ", demotee_client_id: %r, project_name: %s"
                  % (demotee_client_id, project_name))
    _logger.debug("category_dict: %s" % category_dict)

    ok_msg = "Demoted project owner"
    err_msg = "Failed to demote project owner"
    log_ok_msg = "GDP: Demoted user: %r for project: %r" \
        % (demotee_client_id, project_name) \
        + ", by owner: %r from ip: %s" \
        % (client_id, client_addr)
    log_err_msg = "GDP: Failed to demote user: %r for project: %r" \
        % (demotee_client_id, project_name) \
        + ", by owner: %r from ip: %s" \
        % (client_id, client_addr)

    # Get owners list

    (owner_status, vgrid_owners_list) = vgrid_owners(project_name,
                                                     configuration,
                                                     recursive=False)
    if not owner_status:
        status = False
        template = ": Could not retrieve owners list"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %s" % vgrid_owners_list)

    # Check if last owner

    elif len(vgrid_owners_list) == 1:
        status = False
        template = ": Demote of last owner NOT allowed"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %s" % vgrid_owners_list)

    # Check for demoter ownership

    if status and not vgrid_is_owner(project_name,
                                     client_id,
                                     configuration,
                                     recursive=False):
        status = False
        template = ": not project owner"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %r" % client_id)

    # Check for demotee ownership

    if status and not vgrid_is_owner(project_name,
                                     demotee_client_id,
                                     configuration,
                                     recursive=False):
        status = False
        template = ": not project owner"
        err_msg += template
        _logger.error(log_err_msg + template
                      + ": %r" % demotee_client_id)

    if status:

        # Retrieve demoter project entry

        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)
        user_db = __load_user_db(configuration, do_lock=False)

        project = user_db.get(client_id, {}).get(
            'projects', {}).get(project_name, {})
        if not project:
            status = False
            template = ": missing project for demoter"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": for %r" % client_id)

    if status:

        # Retrieve demotee project entry

        demotee_project = user_db.get(demotee_client_id, {}).get(
            'projects', {}).get(project_name, {})
        if not demotee_project:
            status = False
            template = ": missing project for demotee"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": for %r" % demotee_client_id)

    if status:

        # Set new owners list

        new_vgrid_owners_list = copy.deepcopy(vgrid_owners_list)
        new_vgrid_owners_list.remove(demotee_client_id)
        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name,
                                                     new_vgrid_owners_list)
        if not owner_status:
            status = False
            template = ": Could not save owner list"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % owner_msg)

    # Add demote owner to project owner actions

    if status:

        # retrieve project actions

        category_meta = project.get('category_meta', {})
        project_actions = category_meta.get('actions', [])
        if not project_actions:
            status = False
            template = ": No project actions found"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:

        # Find create project action

        project_action = ""
        for ent in project_actions:
            value = ent.get('action', '')
            if value == 'create_project' or value == 'promote_to_owner':
                project_action = ent

        if not project_action:
            status = False
            template = ": no valid project action is found"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % project_actions)

    if status:

        # Fill demote_owner action with references from project create action

        category_id = category_meta.get('category_id', '')
        ref_dict = {i['ref_id']: i['value'] for i in
                    project_action.get('references', [])}

        # Update last create/promote dict with current values

        ref_dict.update(category_dict)
        update_category_meta(configuration, client_id, project,
                             ref_dict, 'demote_owner',
                             source=client_id,
                             user=demotee_client_id)

        # Do not log redundant action entries

        if client_id != demotee_client_id:
            demotee_ref_dict = copy.deepcopy(ref_dict)
            update_category_meta(configuration, demotee_client_id,
                                 demotee_project,
                                 demotee_ref_dict, 'demote_owner',
                                 source=client_id,
                                 user=demotee_client_id)

        __save_user_db(configuration, user_db, do_lock=False)
        release_file_lock(flock)
        flock = None

    if status:

        # Write change to GDP log

        log_msg = "User id: %s" \
            % __scramble_user_id(configuration, demotee_client_id)

        log_status = project_log(
            configuration,
            'https',
            client_id,
            client_addr,
            'demoted_owner',
            details=log_msg,
            project_name=project_name,
        )

        if not log_status:
            status = False
            _logger.error(log_err_msg
                          + ": Demote user project log failed ")

    if status:

        # Send notification

        _logger.info("handle demote notify")
        login = __short_id_from_client_id(configuration, client_id)

        demotee_login = login
        if client_id != demotee_client_id:
            demotee_login = __short_id_from_client_id(
                configuration, demotee_client_id)

        send_status = __send_project_demote_owner_confirmation(configuration,
                                                               login,
                                                               demotee_login,
                                                               project_name,
                                                               ref_dict)
        if not send_status:
            status = False
            template = ": Failed to send demote user confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    if flock is not None:
        release_file_lock(flock)

    # If errors occurred then roll back to original vgrid owners

    if not status:

        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name,
                                                     vgrid_owners_list)
        if not owner_status:
            template = ": Failed to roll back to original vgrid owners"
            _logger.error(log_err_msg + template + ": %s" % owner_msg)

    # Return

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def create_project_user(
        configuration,
        client_addr,
        client_id,
        project_name,
        project):
    """Create new project user"""

    status = True

    _logger = configuration.logger
    # _logger.debug("client_addr: %r, client_id: %r, project_name: %r"
    #               % (client_addr, client_id, project_name))

    status = True

    # Get vgrid_files_home dir for project

    project_files_dir = os.path.abspath(os.path.join(
        configuration.vgrid_files_home, project_name)) + os.sep

    # Create project client id

    project_client_id = project['client_id'] = get_project_client_id(
        client_id, project_name)

    ok_msg = "Created new project user"
    err_msg = "Failed to create project user"
    log_ok_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", created project_user: %r" % project_client_id
    log_err_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", failed to create project_user: %r" % project_client_id

    gdp_user_log_entry = __get_gdp_user_log_entry(configuration,
                                                  project_client_id,
                                                  match_client_id=False)
    if gdp_user_log_entry and gdp_user_log_entry[0] != project_client_id:
        status = False
        _logger.error("GDP: Scrambled project user: %r" % gdp_user_log_entry[1]
                      + " is already used for user: %r" % gdp_user_log_entry[0])

    if status:

        # Create aliases for supported services (openid, davs and sftp)

        aliases = []
        for user_alias in [configuration.user_openid_alias,
                           configuration.user_davs_alias,
                           configuration.user_sftp_alias]:
            alias = get_short_id(
                configuration, project_client_id, user_alias)
            if not alias in aliases:
                aliases.append(alias)

        # Create new MiG user for project

        mig_user_map = get_full_user_map(configuration)
        mig_user_dict = mig_user_map.get(client_id, None)
        mig_user_dict['distinguished_name'] = project_client_id
        mig_user_dict['comment'] = "GDP autocreated user for project: %r" \
            % project_name
        mig_user_dict['openid_names'] = aliases
        mig_user_dict['auth'] = ['']
        mig_user_dict['short_id'] = ''
        mig_user_dict['old_password'] = ''
        mig_user_dict['password'] = ''
        mig_user_db_path = default_db_path(configuration)
        try:
            create_user(mig_user_dict, configuration.config_file,
                        mig_user_db_path, ask_renew=False,
                        default_renew=True)
        except Exception as exc:
            status = False
            _logger.error(log_err_msg
                          + ": Failed to create user: %s" % (exc))

    # Create symlink from project dir to newly created MiG user dir

    if status:
        project_client_dir = client_id_dir(project_client_id)
        project_files_link = os.path.join(configuration.user_home,
                                          project_client_dir, project_name)
        src = project_files_dir
        if not make_symlink(src, project_files_link, _logger):
            status = False
            _logger.error(log_err_msg
                          + ": Failed to create symlink: %r -> %r"
                          % (src, project_files_link))

    # Update user log if project_client_id not yet in it

    if status and not gdp_user_log_entry:
        status = __update_gdp_user_log(configuration, project_client_id)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_accept_user(
        configuration,
        client_addr,
        client_id,
        project_name,
        category_dict,
        in_create=False):
    """Accept project invitation.
    If in_create is set it means that the accept is a part of project_create so
    that the notification and references handling should be fitted accordingly.
    """

    _logger = configuration.logger
    # _logger.debug("client_addr: %r, client_id: %r, project_name: %r"
    #               % (client_addr, client_id, project_name))

    status = True
    project_client_id = None
    add_member_status = False
    add_user_status = False

    # Get login handle (email) from client_id

    login = __short_id_from_client_id(configuration,
                                      client_id)

    ok_msg = "Accepted invitation to project: %r" % project_name
    err_msg = "Failed to accept invitation for project: %r" \
        % project_name
    log_ok_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", accepted invite to project: %r" % project_name
    log_err_msg = "GDP: User: %r from ip: %s"\
        % (client_id, client_addr) \
        + ", failed to accept invite to project: %r" % project_name
    project_client_id = get_project_client_id(client_id,
                                              project_name)
    (_, db_lock_filepath) = __gdp_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, do_lock=False)

    # Resolve category metadata, if in create then resolve for both
    # 'accept_user' and 'create_project'
    category_id = category_dict.get('category_id', '')
    if not in_create:
        accept_category_dict = category_dict
        ref_pairs = [(i['ref_id'], i['value']) for i in
                     accept_category_dict.get('references', {}).get('accept_user', [])]
    else:
        ref_pairs_create = [(i['ref_id'], i['value']) for i in
                            category_dict.get('references', {}).get('create_project', [])]
        _logger.debug("ref_pairs_create: %s" % ref_pairs_create)
        try:
            # Generate 'fake' invite ref pairs if in_create
            default_category_dict = [i
                                     for i in configuration.gdp_data_categories
                                     if i['category_id'] == category_id][0]
            _logger.debug("default_category_dict: %s" % default_category_dict)
            ref_pairs = [(i['ref_id'], 'AUTO') for i in
                         default_category_dict.get('references', {}).get('accept_user', [])]
            _logger.debug("ref_pairs: %s" % ref_pairs)
            ref_dict = dict(ref_pairs)
            # Update with values from create action
            ref_dict.update(dict(ref_pairs_create))
            accept_category_dict = fill_category_meta(configuration,
                                                      category_id, 'accept_user',
                                                      ref_dict)
            _logger.debug("accept_category_dict: %s" % accept_category_dict)
        except Exception as exc:
            template = ": failed to fill category meta for 'accept_user'"
            err_msg += template
            _logger.error("%s%s, err: %s" % (log_err_msg, template, exc))
            return (False, err_msg)

    # Retrieve user

    user = user_db.get(client_id, None)
    if user is None:
        status = False
        _logger.error(log_err_msg
                      + ": Missing user entry in GDP DB")

    # Retrieve project

    if status:
        project = user.get('projects', {}).get(project_name, None)
        if project is None:
            status = False
            _logger.error(log_err_msg
                          + ": Missing project entry in GDP DB")

    # Retrieve project state

    if status:
        project_state = project.get('state', '')
        if project_state != 'invited':
            status = False
            _logger.error(log_err_msg
                          + ": Expected state='invited', got state=%r"
                          % project_state)

    # Create new project user

    if status:
        (add_user_status, _) = create_project_user(configuration,
                                                   client_addr,
                                                   client_id,
                                                   project_name,
                                                   project)
        if not add_user_status:
            status = False
            template = ": Failed to create project user: %r" \
                % project_client_id
            err_msg += template
            _logger.error(log_err_msg + template)

    # Add new project user to vgrid member list

    if status:
        member_list = [project_client_id]
        (add_member_status, add_member_msg) \
            = vgrid_add_members(configuration, project_name, member_list)
        if not add_member_status:
            status = False
            _logger.error(log_err_msg
                          + ": %s" % add_member_msg)

    # Mark project as accepted

    if status:

        # Log Accept details to distinct project log

        log_msg = "Accepted invitation"
        status = project_log(
            configuration,
            'https',
            client_id,
            client_addr,
            'accept_user',
            details=log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")

    # Roll back if something went wrong

    if not status:
        template = "GDP: project_accept_user : roll back :"
        if add_member_status:
            _logger.info(template
                         + " Removing member: %r from vgrid: %r"
                         % (project_client_id, project_name))
            member_list = [project_client_id]
            (remove_status, remove_msg) = vgrid_remove_members(configuration,
                                                               project_name,
                                                               member_list)
            if not remove_status:
                _logger.error(template
                              + " Failed : %s" % (remove_msg))
        if add_user_status:
            _logger.info(template
                         + " Deleting MiG user: %r" % project_client_id)
            (delete_status, delete_msg) = \
                __delete_mig_user(configuration, project_client_id)
            if not delete_status:
                _logger.error(template
                              + " Failed : %s" % (delete_msg))
    else:
        # Register accepted invitation for invited user
        update_category_meta(configuration, client_id, project,
                             accept_category_dict, 'accept_user',
                             source=client_id,
                             user=client_id)
        project['state'] = 'accepted'
        __save_user_db(configuration, user_db, do_lock=False)
        release_file_lock(flock)

    if status and not in_create:
        _logger.info("handle accept notify")
        project_actions = project.get('category_meta', {}).get('actions', [])
        # Find inviting owner
        owner_login = ''
        owner_client_id = ''
        for ent in reversed(project_actions):
            _logger.debug("action: %s" % ent.get('action', ''))
            if ent.get('action', '') == 'invite_user':
                owner_client_id = ent.get('source', '')
                break
        if owner_client_id:
            owner_login = __short_id_from_client_id(
                configuration, owner_client_id)
        _logger.debug("owner_client_id: %s" % owner_client_id)
        _logger.debug("owner_login: %s" % owner_login)
        status = __send_project_accept_user_confirmation(configuration, login,
                                                         owner_login,
                                                         project_name,
                                                         accept_category_dict)
        if not status:
            template = ": Failed to send project accept confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_login(
        configuration,
        protocol,
        client_addr,
        user_id,
        project_name=None,
        do_lock=True):
    """Log *client_id* into project_name"""

    _logger = configuration.logger
    # _logger.debug("protocol: %r, user_id: %r, \
    #               client_addr: %r, project_name: %r"
    #               % (protocol, user_id, client_addr, project_name))

    result = None
    status = True
    flock = None
    client_id = __client_id_from_user_id(configuration, user_id)

    if project_name is None:
        project_name = get_project_from_user_id(configuration, user_id)
        if project_name is None:
            status = False
            _logger.error(
                "GDP: Missing project name in user_id: %r" % user_id)

    log_ok_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", logged in to project: %r with protocol: %r" \
        % (project_name, protocol)
    log_err_msg = "GDP: Project login failed for user: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", project: %r with protocol: %r" \
        % (project_name, protocol)

    # Make sure user with 'client_id' is logged out from all projects
    # NOTE: This should be the case already if system is consistent

    if status:
        if do_lock:
            (_, db_lock_filepath) = __gdp_db_filepath(configuration)
            flock = acquire_file_lock(db_lock_filepath)

        # Retrieve user and project info

        user_db = __load_user_db(configuration, do_lock=False)
        user = user_db.get(client_id, None)
        if user is None:
            status = False
            _logger.error(log_err_msg
                          + ": Missing user entry in GDP DB")
        else:
            user_project = user.get('projects', {}).get(project_name, None)
            if user_project is None:
                status = False
                _logger.error(log_err_msg
                              + ": Missing project entry in GDP DB")

    # Retrieve project state

    if status:
        project_state = user_project.get('state', '')
        if project_state != 'accepted':
            status = False
            _logger.error(log_err_msg
                          + ": Expected state='accepted', got state=%r"
                          % project_state)

    # Retrieve user account info

    if status:
        user_account = user.get('account', None)
        if user_account is None:
            status = False
            _logger.error(log_err_msg
                          + ": Missing 'account' entry in GDP DB")

    # Check if user is already logged into a another project

    if status:
        if protocol not in valid_protocols:
            status = False
            _logger.error(log_err_msg
                          + ": Protocol is NOT in valid_protocols: %s"
                          % valid_protocols)

        role = user_account.get(protocol,
                                {}).get('role', '')
        if role:
            status = False
            _logger.error(log_err_msg
                          + ": User is already logged into project")

    # Generate log message and log to project log

    if status:
        project_client_id = get_project_client_id(client_id,
                                                  project_name)
        log_msg = "Project user id: %s" \
            % __scramble_user_id(configuration, project_client_id)
        status = project_log(
            configuration,
            protocol,
            project_client_id,
            client_addr,
            'logged_in',
            details=log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")
    if status:
        user_account[protocol]['role'] = \
            user_project['client_id'] = project_client_id
        user_account[protocol]['last_login']['timestamp'] = time.time()
        user_account[protocol]['last_login']['ip'] = client_addr
        __save_user_db(configuration, user_db, do_lock=False)

    if flock is not None:
        release_file_lock(flock)

    if status:
        result = project_client_id
        _logger.info(log_ok_msg)

    return result


def project_logout(
        configuration,
        protocol,
        client_addr,
        user_id,
        autologout=False,
        do_lock=True):
    """Logout user *client_id* from active project
    If *client_id* is None then *project_client_id* must not be None
    Returns True if *client_id* got and active project and is logged out if it
    False otherwise
    """

    _logger = configuration.logger
    # _logger.debug("user_id: %r, protocol: %r, client_addr: %r"
    #               % (user_id, protocol, client_addr))

    status = True
    result = False
    flock = None
    project_name = None
    role = None
    client_id = __client_id_from_user_id(configuration, user_id)
    project_client_id = __project_client_id_from_user_id(
        configuration, user_id)
    log_ok_msg = "GDP: Project logout for user: %r from ip: %s" \
        % (client_id, client_addr) \
        + " with protocol: %r" % protocol
    log_err_msg = "GDP: Project logout failed for user: %r from ip: %s" \
        % (client_id, client_addr) \
        + " with protocol: %r" % protocol
    if project_client_id:
        project_name = \
            __project_name_from_project_client_id(configuration,
                                                  project_client_id)
        log_ok_msg += ", project: %r" % project_name
        log_err_msg += ", project: %r" % project_name

    if do_lock:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)
    user_db = __load_user_db(configuration, do_lock=False)

    # Retrieve user

    if status:
        user = user_db.get(client_id, None)
        if user is None:
            status = False
            _logger.error(log_err_msg
                          + ": Missing user entry in GDP DB")

    # Retrieve user account

    if status:
        user_account = user.get('account', None)
        if user_account is None:
            status = False
            _logger.error(log_err_msg
                          + ": Missing 'account' entry in GDP DB")

    # Retrieve and set user account role

    if status:
        role = user_account.get(protocol,
                                {}).get('role', '')
        if not role:
            status = False
            _logger.error(log_err_msg +
                          ": User is NOT logged in")
        elif project_client_id and role != project_client_id:
            status = False
            _logger.error(log_err_msg +
                          ": User is currently logged in"
                          + " to another project: %r"
                          % get_project_from_user_id(configuration, role))
        elif not project_client_id:
            project_client_id = role
            project_name = \
                __project_name_from_project_client_id(configuration,
                                                      project_client_id)
            log_ok_msg += ", project: %r" % project_name
            log_err_msg += ", project: %r" % project_name

    if status:
        if autologout:
            action = 'auto_logged_out'
        else:
            action = 'logged_out'

        # Generate log message and log to project log

        log_msg = "Project user id: %s" \
            % __scramble_user_id(configuration, project_client_id)
        status = project_log(
            configuration,
            protocol,
            project_client_id,
            client_addr,
            action,
            details=log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")

    if status:
        user_account[protocol]['role'] = ''
        __save_user_db(configuration, user_db, do_lock=False)

    if flock is not None:
        release_file_lock(flock)

    if status:
        result = True
        _logger.info(log_ok_msg)

    return result


def project_open(
        configuration,
        protocol,
        client_addr,
        user_id):
    """Open project for *user_id* with *protocol*
    if user is logged into another project, then autologout before login
    if user is already logged into the current project
    then skip logout/login"""

    _logger = configuration.logger
    # _logger.debug("protocol: %r, client_addr: %r, user_id: %r"
    #               % (protocol, client_addr, user_id))

    status = True
    skiplogin = False
    active_short_id = ''
    project_short_id = __project_short_id_from_user_id(
        configuration, user_id)
    client_id = __client_id_from_user_id(configuration, user_id)
    project_name = get_project_from_user_id(configuration, user_id)
    if project_name is None:
        msg = "Missing project name in user_id: %r" % user_id
        _logger.error("GDP: " + msg)
        return (False, msg)

    ok_msg = "Opened project: %r" % project_name
    err_msg = "Failed to open project: %r" % project_name
    log_ok_msg = "GDP: User: %r from ip: %s, protocol: %r" \
        % (user_id, client_addr, protocol) \
        + ", opened project: %r" % project_name
    log_err_msg = "GDP: User: %r from ip: %s, protocol: %r" \
        % (user_id, client_addr, protocol) \
        + ", failed to open project: %r" % project_name

    (_, db_lock_filepath) = __gdp_db_filepath(configuration)
    flock = acquire_file_lock(db_lock_filepath)

    # NOTE: validate_user updates timestamp, extract active_project first
    active_project = __active_project(configuration,
                                      client_id,
                                      protocol,
                                      do_lock=False)
    if active_project is None:
        status = False
        template = ": Failed to extract active project"
        err_msg += template
        _logger.error(log_err_msg + template)

    if status:
        (status, validate_msg) = validate_user(
            configuration, client_id, client_addr, protocol, do_lock=False)
        if not status:
            _logger.error(log_err_msg + ": %s" % validate_msg)

    if status and active_project:
        active_short_id = active_project.get('project_short_id', '')
        template = ": Project close required for: %r" \
            % active_project.get('name', '')
        if active_short_id:
            if protocol == 'davs':
                cur_timestamp = time.time()
                project_timestamp = active_project.get('last_timestamp', 0)
                project_change_time = io_session_timeout.get(protocol, 0)
                time_to_autologout = (
                    project_timestamp + project_change_time) - cur_timestamp
                autologout = False
                if active_short_id == project_short_id:
                    autologout = True
                elif active_short_id != project_short_id:
                    if time_to_autologout < 0:
                        autologout = True
                    else:
                        status = False
                        template += ": Wait %d seconds for autologout" \
                            % time_to_autologout
                if autologout:
                    status = project_logout(
                        configuration,
                        protocol,
                        client_addr,
                        active_short_id,
                        autologout=True,
                        do_lock=False)
            elif active_short_id == project_short_id:
                skiplogin = True
            else:
                status = False

        if not status:
            err_msg += template
            _logger.error(log_err_msg + template)

    if status and not skiplogin \
        and project_login(
            configuration,
            protocol,
            client_addr,
            client_id,
            project_name,
            do_lock=False) is None:
        status = False

    release_file_lock(flock)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_close(
        configuration,
        protocol,
        client_addr,
        user_id=None):
    """Close project for *user_id* with *protocol*
    if *user_id* is None close all project for *protocol*"""

    _logger = configuration.logger
    # _logger.debug("protocol: %r, client_addr: %r, user_id: %r"
    #                % (protocol, client_addr, user_id))

    result = True
    active_user_ids = []
    if user_id is not None:
        autologout = False
        active_user_ids.append(user_id)
    else:
        autologout = True
        user_db = __load_user_db(configuration)
        for (_, user_dict) in user_db.items():
            role = user_dict.get('account', {}).get(
                protocol, {}).get('role', '')
            if role:
                active_user_ids.append(role)
    for active_user in active_user_ids:
        status = project_logout(
            configuration,
            protocol,
            client_addr,
            active_user,
            autologout=autologout)
        if not status:
            result = False

    return result


def project_create(
        configuration,
        client_addr,
        client_id,
        project_name,
        category_dict):
    """Create new project with *project_name* and owner *client_id*. Register
    additional reference tracking with *category_dict*.
    """

    _logger = configuration.logger
    # _logger.debug(
    #     "project_create: client_id: %r"
    #     + ", project_name: %r", client_id, project_name)

    status = True
    mig_user_dict = None
    rollback = {}
    rollback_dirs = {}
    vgrid_label = '%s' % configuration.site_vgrid_label
    ref_pairs = [(i['ref_id'], i['value']) for i in
                 category_dict.get('references', {}).get("create_project", [])]
    ok_msg = "Created project: %r" % project_name
    err_msg = "Failed to create project: %r" % project_name
    log_ok_msg = "GDP: User: %r from ip: %s, created project: %r" % (
        client_id, client_addr, project_name)
    log_err_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", failed to create project: %r" % project_name

    # Create vgrid
    # This is done explicitly here as not all operations from
    # shared.functionality.createvgrid apply to GDP
    # TODO:
    # Move vgridcreate functions from mig.shared.functionality.createvgrid
    # to a commen helper module

    if project_name.find('/') != -1:
        status = False
        template = ": '/' NOT allowed in project name"
        err_msg += template
        _logger.error(log_err_msg + template)

    # No owner check here so we need to specifically check for illegal
    # directory status

    if status:
        reserved_names = (default_vgrid, any_vgrid, all_vgrids)
        if project_name in reserved_names \
            or not valid_dir_input(configuration.vgrid_home,
                                   project_name):
            status = False
            template = ": Illegal project name"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Optional limitation of create vgrid permission

    if status:
        mig_user_map = get_full_user_map(configuration)
        mig_user_dict = mig_user_map.get(client_id, None)
        if not mig_user_dict or not vgrid_create_allowed(configuration,
                                                         mig_user_dict):
            status = False
            template = ": User is not allowed to create projects"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    if status:
        vgrid_home_dir = os.path.abspath(os.path.join(
            configuration.vgrid_home,
            project_name)) + os.sep
        vgrid_files_dir = os.path.abspath(os.path.join(
            configuration.vgrid_files_home,
            project_name)) + os.sep

        if vgrid_restrict_write_support(configuration):
            flat_vgrid = vgrid_flat_name(project_name, configuration)
            vgrid_writable_dir = os.path.abspath(os.path.join(
                configuration.vgrid_files_writable,
                flat_vgrid)) + os.sep
            vgrid_readonly_dir = os.path.abspath(os.path.join(
                configuration.vgrid_files_readonly,
                flat_vgrid)) + os.sep
        else:
            vgrid_writable_dir = None
            vgrid_readonly_dir = None

    # Make sure all dirs can be created (that a file or directory with the same
    # name do not exist prior to the vgrid creation)

    if status:
        if os.path.exists(vgrid_home_dir) \
                or os.path.exists(vgrid_files_dir):
            status = False
            template = ": Project already exists"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Create directory to store vgrid files

    if status:
        try:
            os.mkdir(vgrid_home_dir)
            rollback_dirs['vgrid_home_dir'] = vgrid_home_dir
        except Exception as exc:
            status = False
            template = ": Could not create base directory"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %r: %s" % (vgrid_home_dir, exc))

    # Create directory in vgrid_files_home or vgrid_files_writable to contain
    # shared files for the new vgrid.

    if status:
        try:
            if vgrid_writable_dir:
                os.mkdir(vgrid_writable_dir)
                make_symlink(vgrid_writable_dir.rstrip('/'),
                             vgrid_files_dir.rstrip('/'), _logger)
                rollback_dirs['vgrid_writable_dir'] = vgrid_writable_dir
            else:
                os.mkdir(vgrid_files_dir)
            rollback_dirs['vgrid_files_dir'] = vgrid_files_dir
            share_readme = os.path.join(vgrid_files_dir, 'README')
            if not os.path.exists(share_readme):
                write_file("""= Private Share =
This directory is used for hosting private files for the %r %r.
""" % (vgrid_label, project_name), share_readme, _logger, make_parent=False)
        except Exception as exc:
            status = False
            template = ": Could not create files directory"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %r: %s" % (vgrid_files_dir, exc))

    # Create owners list with client_id as owner

    if status:
        owner_list = [client_id]
        (owner_status, owner_msg) = vgrid_set_owners(configuration,
                                                     project_name, owner_list)
        if not owner_status:
            status = False
            template = ": Could not save owner list"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % owner_msg)

    # Create default pickled settings list with only required values set to
    # leave all other fields for inheritance by default.

    if status:
        init_settings = {}
        settings_specs = get_settings_keywords_dict(configuration)
        for (key, spec) in settings_specs.items():
            if spec['Required']:
                init_settings[key] = spec['Value']
        init_settings['vgrid_name'] = project_name
        (settings_status, settings_msg) = vgrid_set_settings(
            configuration, project_name,
            list(init_settings.items()))
        if not settings_status:
            status = False
            template = ": Could not save settings list"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % settings_msg)

    # Create directory to store GDP project files

    if status:
        project_home_base = os.path.join(configuration.gdp_home,
                                         notify_home_dirname)
        # Ensure project home base dir
        makedirs_rec(project_home_base, configuration)
        project_home = os.path.join(project_home_base,
                                    project_name)
        if not os.path.isdir(project_home):
            try:
                os.mkdir(project_home)
                rollback_dirs['project_home'] = project_home
            except Exception as exc:
                status = False
                template = ": Could not create home directory"
                err_msg += template
                _logger.error(log_err_msg + template
                              + ": %r: %s" % (project_home, exc))
        else:
            status = False
            template = ": Home dir already exists"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %r" % project_home)

    # Fake 'invite_user' and 'accept_user' to enable owner login

    if status:
        rollback['project'] = True
        (status, _) = project_invite_user(configuration, client_addr,
                                          client_id, client_id, project_name,
                                          category_dict, in_create=True)
        if not status:
            template = ": Automatic invite failed"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:
        rollback['user'] = True
        (status, _) = project_accept_user(configuration, client_addr,
                                          client_id, project_name,
                                          category_dict, in_create=True)
        if not status:
            template = ": Automatic accept failed"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:

        # Update log for project

        log_msg = "Created project"

        if ref_pairs:
            log_parts = ["%s: %r" % pair for pair in ref_pairs]
            log_msg += " with references: " + ', '.join(log_parts)
        else:
            log_msg += " without required references"

        status = project_log(
            configuration,
            'https',
            client_id,
            client_addr,
            'created',
            details=log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")

    # Roll back if something went wrong

    if not status:
        _logger.info("GDP: Rolling back project_create for: %r" %
                     project_name)

        # Remove project directories

        for (key, path) in rollback_dirs.items():
            _logger.info(
                "GDP: project_create : roll back :"
                + " Recursively removing : %r -> %r" % (key, path))
            remove_rec(path, configuration)

        # Remove project MiG user

        if rollback.get('user', False):
            project_client_id = get_project_client_id(
                client_id, project_name)
            _logger.info(
                "GDP: project_create : roll back :"
                + " Deleting MiG user: %r" % project_client_id)
            __delete_mig_user(configuration, project_client_id,
                              allow_missing=True)

        # Remove project from user in GDP user database

        if rollback.get('project', False):
            _logger.info(
                "GDP: project_create : roll back :"
                + " Deleting GDP user: %r, project: %r from GDP database"
                % (client_id, project_name))

            (_, db_lock_filepath) = __gdp_db_filepath(configuration)
            flock = acquire_file_lock(db_lock_filepath)
            user_db = __load_user_db(configuration, do_lock=False)
            if user_db.get(client_id, {}).get(
                'projects', {}).get(
                    project_name, None) is not None:
                del user_db[client_id]['projects'][project_name]
            else:
                _logger.warning(
                    "GDP: project_create : roll back :"
                    + " GDP user: %r, project: %r"
                    % (client_id, project_name)
                    + " NOT found in GDP database")
            __save_user_db(configuration, user_db, do_lock=False)
            release_file_lock(flock)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)


def project_remove(
        configuration,
        client_addr,
        client_id,
        project_name):
    """Remove project with *project_name* and owner *client_id*.
    Removes all owners, participants and data.
    """

    _logger = configuration.logger
    # _logger.debug(
    #    "project_remove: client_id: %r"
    #     + ", project_name: %r", client_id, project_name)

    status = True

    ok_msg = "Removed project: %r" % project_name
    err_msg = "Failed to remove project: %r" % project_name
    log_ok_msg = "GDP: User: %r from ip: %s, removed project: %r" % (
        client_id, client_addr, project_name)
    log_err_msg = "GDP: User: %r from ip: %s" \
        % (client_id, client_addr) \
        + ", failed to remove project: %r" % project_name

    # Get GDP project info

    (_, db_lock_filepath) = __gdp_db_filepath(configuration)
    user_db = __load_user_db(configuration)
    project = user_db.get(client_id, {}).get(
        'projects', {}).get(project_name, {})
    if not project:
        status = False
        template = ": Could not retrieve project: %r from GDP database" \
            % project_name
        err_msg += template
        _logger.error(log_err_msg + template)

    # retrieve project meta

    if status:
        category_meta = project.get('category_meta', {})
        if not category_meta:
            status = False
            template = ": No project meta found"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:
        category_id = category_meta.get('category_id', '')
        if not category_id:
            status = False
            template = ": No project category id found"
            err_msg += template
            _logger.error(log_err_msg + template)

    if status:
        project_actions = category_meta.get('actions', [])
        if not project_actions:
            status = False
            template = ": No project actions found"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Find create or promote_to_owner action

    if status:
        ref_action = {}
        for ent in project_actions:
            value = ent.get('action', '')
            if value == 'create_project' or value == 'promote_to_owner':
                ref_action = ent

        if not ref_action:
            status = False
            template = ": no project create or promote action found"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % project_actions)

    # Fill remove action with references
    # from project create action or last promote action

    if status:
        project_ref_dict = {i['ref_id']: i['value'] for i in
                            ref_action.get('references', [])}
        # _logger.debug("project_ref_dict: %s" % project_ref_dict)
        try:
            project_remove_category_entry = fill_category_meta(configuration,
                                                               category_id, 'remove_project',
                                                               project_ref_dict)
        except ValueError as err:
            status = False
            template = ": Failed to fill category meta"
            err_msg += template
            _logger.error(log_err_msg + template
                          + ": %s" % err)

    # Get owners list

    if status:
        (status, vgrid_owners_list) = vgrid_owners(project_name,
                                                   configuration,
                                                   recursive=False)
        if not status:
            template = ": Could not retrieve owners list"
            err_msg += template
            _logger.error(log_err_msg + template)
        elif not client_id in vgrid_owners_list:
            # Check is client_id is owner
            status = False
            template = ": not project owner"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Get members list

    (status, vgrid_members_list) = vgrid_members(project_name,
                                                 configuration,
                                                 recursive=False)
    if not status:
        template = ": Could not retrieve members list"
        err_msg += template
        _logger.error(log_err_msg + template)

    # Remove project participants

    if status:
        _logger.debug("vgrid_members_list: %s" % vgrid_members_list)
        for vgrid_member in vgrid_members_list:
            base_client_id = __client_id_from_project_client_id(configuration,
                                                                vgrid_member)
            (remove_status, msg) = project_remove_user(
                configuration,
                client_addr,
                client_id,
                base_client_id,
                project_name,
                allow_owner=True,
                send_notify=False)
            if not remove_status:
                status = False
                template = ": Failed to remove project member: %s" % vgrid_member
                err_msg += ": %s" % msg
                _logger.error(log_err_msg + template)
                break

    # Remove project owners

    if status:
        (remove_status, msg) = vgrid_remove_owners(configuration,
                                                   project_name,
                                                   vgrid_owners_list,
                                                   allow_empty=True)
        if not remove_status:
            status = False
            template = ": Failed to remove project owners"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Remove vgrid files

    if status:
        (remove_status, msg) = vgrid_rm_files(configuration, project_name)
        if not remove_status:
            status = False
            template = ": Failed to remove project files"
            err_msg += template
            _logger.error("%s%s: %s" % (log_err_msg, template, msg))

    # Remove vgrid home entry

    if status:
        (remove_status, msg) = vgrid_rm_entry(configuration, project_name)
        if not remove_status:
            status = False
            template = ": Failed to remove project entry"
            err_msg += template
            _logger.error("%s%s: %s" % (log_err_msg, template, msg))

    # Log project removed

    if status:
        log_msg = "Removed project"

        status = project_log(
            configuration,
            'https',
            client_id,
            client_addr,
            'removed',
            details=log_msg,
            project_name=project_name,
        )
        if not status:
            _logger.error(log_err_msg
                          + ": Project log failed")

    # Send notification

    if status:
        _logger.info("handle remove project notify")
        owner_login = __short_id_from_client_id(
            configuration, client_id)
        participants = []
        for vgrid_member in vgrid_members_list:
            _logger.debug("vgrid_member: %s" % vgrid_member)
            base_client_id = __client_id_from_project_client_id(configuration,
                                                                vgrid_member)
            _logger.debug("vgrid_member base_client_id: %s" % vgrid_member)
            participant_login = __short_id_from_client_id(configuration,
                                                          base_client_id)
            _logger.debug("vgrid_member participant_login: %s" %
                          participant_login)
            if participant_login != owner_login:
                participants.append(participant_login)
            _logger.debug("vgrid_member participants: %s" % participants)

        status = __send_project_remove_confirmation(configuration,
                                                    owner_login,
                                                    participants,
                                                    project_name,
                                                    project_remove_category_entry)
        if not status:
            template = ": Failed to send project remove confirmation email"
            err_msg += template
            _logger.error(log_err_msg + template)

    # Move GDP project home entry to the attic
    # NOTE: Must be done after send notification to preserve move notifications

    if status:
        project_home = os.path.join(configuration.gdp_home,
                                    os.path.join(notify_home_dirname,
                                                 project_name))
        if not os.path.isdir(project_home):
            status = False
            template = ": Invalid project home: %s" % project_home
            err_msg += ": %s" % msg
            _logger.error(log_err_msg + template)
        else:
            project_attic = os.path.join(configuration.gdp_home,
                                         os.path.join(notify_attic_dirname,
                                                      "%s.%d" % (project_name,
                                                                 int(time.time()))))
            (status, move_msg) = move_rec(project_home,
                                          project_attic,
                                          configuration)
            if not status:
                template = ": Could not move project to attic"
                err_msg += template
                _logger.error(log_err_msg + template
                              + ": %r -> %r: %s"
                              % (project_home, project_attic, move_msg))

    # Remove project from GDP database
    # NOTE: Traverse complete database to catch pending invites

    if status:
        (_, db_lock_filepath) = __gdp_db_filepath(configuration)
        flock = acquire_file_lock(db_lock_filepath)
        user_db = __load_user_db(configuration, do_lock=False)
        for user in user_db.keys():
            user_projects = user_db.get(user, {}).get('projects', {})
            if project_name in user_projects:
                try:
                    del user_projects[project_name]
                except Exception as err:
                    status = False
                    err_msg += ": %s" % err
                    _logger.error(err_msg)
        __save_user_db(configuration, user_db, do_lock=False)
        release_file_lock(flock)

    ret_msg = err_msg
    if status:
        ret_msg = ok_msg
        _logger.info(log_ok_msg)

    return (status, ret_msg)
