#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - helpers for handling user settings
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import datetime
import os
from binascii import hexlify

from mig.shared.base import client_id_dir
from mig.shared.defaults import settings_filename, profile_filename, \
    widgets_filename, twofactor_filename, duplicati_filename, ssh_conf_dir, \
    davs_conf_dir, ftps_conf_dir, seafile_conf_dir, duplicati_conf_dir, \
    cloud_conf_dir, authkeys_filename, authpasswords_filename, \
    authdigests_filename, keyword_unchanged, dav_domain
from mig.shared.duplicatikeywords import get_keywords_dict as get_duplicati_fields, \
    extract_duplicati_helper, duplicati_conf_templates
from mig.shared.fileio import pickle, unpickle
from mig.shared.modified import mark_user_modified
from mig.shared.parser import parse, check_types
from mig.shared.profilekeywords import get_keywords_dict as get_profile_fields
from mig.shared.pwhash import make_hash, make_digest, assure_password_strength
from mig.shared.safeinput import valid_password
from mig.shared.settingskeywords import get_keywords_dict as get_settings_fields
from mig.shared.ssh import parse_pub_key, tighten_key_perms
from mig.shared.twofactorkeywords import get_keywords_dict as get_twofactor_fields, \
    check_twofactor_deps
from mig.shared.widgetskeywords import get_keywords_dict as get_widgets_fields


def parse_and_save_pickle(source, destination, keywords, client_id,
                          configuration, strip_space, strip_comments):
    """Use conf parser to parse settings in mRSL file and save resulting
    dictionary in a pickled file in user_settings.
    """
    client_dir = client_id_dir(client_id)
    result = parse(source, strip_space, strip_comments)

    (status, parsemsg) = check_types(result, keywords, configuration)

    try:
        os.remove(source)
    except Exception as err:
        msg = 'Exception removing temporary file %s, %s'\
            % (source, err)

        # should we exit because of this? o.reply_and_exit(o.ERROR)

    if not status:
        msg = 'Parse failed (typecheck) %s' % parsemsg
        return (False, msg)

    new_dict = {}

    # move parseresult to a dictionary

    for (key, value_dict) in keywords.iteritems():
        new_dict[key] = value_dict['Value']

    new_dict['CREATOR'] = client_id
    new_dict['CREATED_TIMESTAMP'] = datetime.datetime.now()

    # Create settings dir for any old users
    try:
        settings_dir = os.path.join(configuration.user_settings, client_dir)
        os.mkdir(settings_dir)
    except:
        pass

    pickle_filename = os.path.join(configuration.user_settings, client_dir,
                                   destination)

    if not pickle(new_dict, pickle_filename, configuration.logger):
        msg = 'Error saving pickled data!'
        return (False, msg)

    # everything ok

    return (True, '')


def parse_and_save_settings(filename, client_id, configuration):
    """Validate and write settings entries from filename"""
    status = parse_and_save_pickle(filename, settings_filename,
                                   get_settings_fields(), client_id,
                                   configuration, True, True)
    if status[0]:
        mark_user_modified(configuration, client_id)
    return status


def parse_and_save_widgets(filename, client_id, configuration):
    """Validate and write widget entries from filename"""
    return parse_and_save_pickle(filename, widgets_filename,
                                 get_widgets_fields(), client_id,
                                 configuration, False, False)


def parse_and_save_profile(filename, client_id, configuration):
    """Validate and write profile entries from filename"""
    status = parse_and_save_pickle(filename, profile_filename,
                                   get_profile_fields(), client_id,
                                   configuration, False, False)
    if status[0]:
        mark_user_modified(configuration, client_id)
    return status


def parse_and_save_duplicati(filename, client_id, configuration):
    """Validate and write duplicati entries from filename. Generate JSON conf
    files for import in Duplicati client.
    """
    _logger = configuration.logger
    status = parse_and_save_pickle(filename, duplicati_filename,
                                   get_duplicati_fields(), client_id,
                                   configuration, False, False)
    if status[0]:
        mark_user_modified(configuration, client_id)
        saved_values = load_duplicati(client_id, configuration)
        if not saved_values:
            _logger.error('loading just saved %s duplicati settings failed!'
                          % client_id)
            return (False, 'could not load saved Duplicati settings!')
        fill_helper = extract_duplicati_helper(configuration, client_id,
                                               saved_values)
        client_dir = client_id_dir(client_id)
        duplicati_dir = os.path.join(configuration.user_home, client_dir,
                                     duplicati_conf_dir)
        saved_protocol = saved_values.get('PROTOCOL', None)
        if saved_protocol.lower() in ['webdavs', 'davs']:
            saved_creds = load_davs(client_id, configuration)
        elif saved_protocol.lower() in ['ssh', 'sftp']:
            saved_creds = load_ssh(client_id, configuration)
        elif saved_protocol.lower() in ['ftps']:
            saved_creds = load_ftps(client_id, configuration)
        else:
            return (False, 'could not load credentials for verification!')
        _logger.debug('found saved creds: %s' % saved_creds)
        if not saved_creds.get('authpassword', None):
            warn = '''Warning: you need to enable password login on your %s
Settings page before you can use it directly with Duplicati.''' % saved_protocol
            saved_keys = saved_creds.get('authkeys', [])
            saved_keys = [i for i in saved_keys if i.strip()]
            if saved_keys:
                warn += ''' It <emph>does</emph> support ssh keys but for that
you need to manually configure the key through the Advanced options on the
Backup destination page during import.'''
            status = (status[0], status[1] + warn)
            _logger.warning('no saved %s creds for %s' % (saved_protocol,
                                                          client_id))

        for backup_name in saved_values['BACKUPS']:
            fill_helper['backup_name'] = backup_name
            fill_helper['backup_dir'] = os.path.join(duplicati_conf_dir,
                                                     backup_name)
            inner_json = []
            for (section_name, section) in duplicati_conf_templates.items():
                # Skip schedule section if disabled
                if section_name == 'schedule' and \
                        not fill_helper['schedule_freq']:
                    continue
                inner_json.append(duplicati_conf_templates[section_name] %
                                  fill_helper)
            filled_json = '{\n%s\n}' % ',\n'.join(inner_json)
            backup_dst = os.path.join(duplicati_dir, backup_name)
            try:
                os.makedirs(backup_dst)
            except:
                # probably exists
                pass
            json_name = "%s.json" % backup_name
            json_path = os.path.join(duplicati_dir, json_name)
            json_fd = open(json_path, "w")
            json_fd.write(filled_json)
            json_fd.close()
    return status


def parse_and_save_twofactor(filename, client_id, configuration):
    """Validate and write twofactor entries from filename. The 2FA user key
    and any required auth files need to be handled separately.
    After saving we check and warn if primary 2FA settings aren't enabled and
    any of the depending secondary ones are. I.e. web 2FA is needed for reuse
    in I/O daemons.
    """
    _logger = configuration.logger
    status = parse_and_save_pickle(filename, twofactor_filename,
                                   get_twofactor_fields(configuration),
                                   client_id, configuration, False, False)
    if status[0]:
        saved_values = load_twofactor(client_id, configuration)
        if not saved_values:
            _logger.error('loading just saved %s twofactor settings failed!'
                          % client_id)
            return (False, 'could not load saved 2FA settings!')
        if not check_twofactor_deps(configuration, client_id, saved_values):
            warn = '''IMPORTANT: twofactor auth for the efficient data access
protocols like SFTP, FTPS and WebDAVS <emph>requires</emph> twofactor auth to
be enabled for one or more basic web login methods, because they share the same
twofactor session. I.e. only enable twofactor for SFTP, FTPS or WebDAVS with
twofactor enabled for your web login.'''
            status = (status[0], status[1] + warn)
    return status


def parse_and_save_publickeys(keys_path, keys_content, client_id,
                              configuration):
    """Validate and write the contents to the keys_path"""
    status, msg = True, ''
    try:
        # Verify all keys to avoid e.g. stray line splits or missing key type
        for key in keys_content.splitlines():
            key = key.split('#', 1)[0]
            if not key.strip():
                continue
            try:
                parse_pub_key(key)
            except Exception as exc:
                raise Exception('Invalid public key: %s' % key)
        keys_fd = open(keys_path, 'wb')
        keys_fd.write(keys_content)
        keys_fd.close()
        tighten_key_perms(configuration, client_id)
    except Exception as exc:
        status = False
        msg = 'ERROR: writing %s publickey file: %s' % (client_id, exc)
    return (status, msg)


def parse_and_save_passwords(passwords_path, passwords_content, client_id,
                             configuration, check_valid=True):
    """Check password strength and write the hashed content to passwords_path
    using the password hashing helper.
    The optional check_valid can be used to disable password check for basic
    validity as well as compliance with configured site policy. No need to do
    that again if already done in parse_and_save_digests call.
    """
    status, msg = True, ''
    if passwords_content == keyword_unchanged:
        return (status, msg)
    try:
        if not passwords_content:
            password_hash = ''
        else:
            if check_valid:
                # Make sure password is valid and complies with site policy
                valid_password(passwords_content)
                assure_password_strength(configuration, passwords_content)
            password_hash = make_hash(passwords_content)
        passwords_fd = open(passwords_path, 'wb')
        passwords_fd.write(password_hash)
        passwords_fd.close()
    except ValueError as vae:
        status = False
        msg = 'invalid password: %s' % vae
    except Exception as exc:
        status = False
        msg = 'ERROR: writing %s passwords file: %s' % (client_id, exc)
    return (status, msg)


def parse_and_save_digests(digests_path, passwords_content, client_id,
                           configuration, check_valid=True):
    """Check password strength and write the digest content to passwords_path
    using the credential digest helper.
    The optional check_valid can be used to disable password check for basic
    validity as well as compliance with configured site policy. No need to do
    that again if already done in parse_and_save_passwords call.
    """
    status, msg = True, ''
    if passwords_content == keyword_unchanged:
        return (status, msg)
    try:
        if not passwords_content:
            password_digest = ''
        else:
            if check_valid:
                # Make sure password is valid and complies with site policy
                valid_password(passwords_content)
                assure_password_strength(configuration, passwords_content)
            password_digest = make_digest(dav_domain, client_id,
                                          passwords_content,
                                          configuration.site_digest_salt)
        digests_fd = open(digests_path, 'wb')
        digests_fd.write(password_digest)
        digests_fd.close()
    except ValueError as vae:
        status = False
        msg = 'invalid password: %s' % vae
    except Exception as exc:
        status = False
        msg = 'ERROR: writing %s digests file: %s' % (client_id, exc)
    return (status, msg)


def _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                 configuration, proto, proto_conf_dir):
    """Validate and write publickey and password settings for proto
    (ssh/davs/ftps/seafile) in proto_conf_dir.
    """
    client_dir = client_id_dir(client_id)
    # Make sure permissions are tight enough for e.g. ssh auth keys to work
    os.umask(0o22)
    proto_conf_path = os.path.join(configuration.user_home, client_dir,
                                   proto_conf_dir)
    # Create proto conf dir for any old users
    try:
        os.mkdir(proto_conf_path)
    except:
        pass
    keys_path = os.path.join(proto_conf_path, authkeys_filename)
    key_status = parse_and_save_publickeys(keys_path, publickeys, client_id,
                                           configuration)
    pw_path = os.path.join(proto_conf_path, authpasswords_filename)
    pw_status = parse_and_save_passwords(pw_path, password, client_id,
                                         configuration, check_valid=True)
    digest_path = os.path.join(proto_conf_path, authdigests_filename)
    if proto == 'davs':
        # NOTE: we already checked password validity above
        digest_status = parse_and_save_digests(digest_path, password, client_id,
                                               configuration, check_valid=False)
    else:
        digest_status = (True, '')
    status = (key_status[0] and pw_status[0] and digest_status[0],
              key_status[1] + ' ' + pw_status[1] + ' ' + digest_status[1])
    if status[0]:
        mark_user_modified(configuration, client_id)
    return status


def parse_and_save_ssh(publickeys, password, client_id, configuration):
    """Validate and write ssh entries"""
    return _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                        configuration, 'ssh', ssh_conf_dir)


def parse_and_save_davs(publickeys, password, client_id, configuration):
    """Validate and write davs entries"""
    return _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                        configuration, 'davs', davs_conf_dir)


def parse_and_save_ftps(publickeys, password, client_id, configuration):
    """Validate and write ftps entries"""
    return _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                        configuration, 'ftps', ftps_conf_dir)


def parse_and_save_seafile(password, client_id, configuration):
    """Validate and write seafile entries"""
    return _parse_and_save_auth_pw_keys('', password, client_id,
                                        configuration, 'seafile',
                                        seafile_conf_dir)


def parse_and_save_cloud(publickeys, password, client_id, configuration):
    """Validate and write cloud entries"""
    return _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                        configuration, 'cloud', cloud_conf_dir)


def load_section_helper(client_id, configuration, section_filename,
                        section_keys, include_meta=False, allow_missing=False):
    """Load settings section from pickled file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    Optional allow_missing is used to avoid log errors for sections that may
    or may not already exist.
    """

    client_dir = client_id_dir(client_id)
    section_path = os.path.join(configuration.user_settings, client_dir,
                                section_filename)
    section_dict = unpickle(section_path, configuration.logger, allow_missing)
    if section_dict and not include_meta:
        real_keys = section_keys
        # NOTE: force list copy here as we delete inline below
        for key in list(section_dict):
            if not key in real_keys:
                del section_dict[key]
    return section_dict


def load_settings(client_id, configuration, include_meta=False):
    """Load settings from pickled settings file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, settings_filename,
                               list(get_settings_fields()), include_meta)


def load_widgets(client_id, configuration, include_meta=False,
                 allow_missing=True):
    """Load widgets from pickled widgets file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, widgets_filename,
                               list(get_widgets_fields()), include_meta,
                               allow_missing)


def load_profile(client_id, configuration, include_meta=False,
                 allow_missing=True):
    """Load profile from pickled profile file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, profile_filename,
                               list(get_profile_fields()), include_meta,
                               allow_missing)


def load_twofactor(client_id, configuration, include_meta=False,
                   allow_missing=True):
    """Load twofactor from pickled twofactor file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, twofactor_filename,
                               get_twofactor_fields(list(configuration)),
                               include_meta, allow_missing)


def load_duplicati(client_id, configuration, include_meta=False,
                   allow_missing=True):
    """Load backup sets from pickled duplicati file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, duplicati_filename,
                               list(get_duplicati_fields()), include_meta,
                               allow_missing)


def _load_auth_pw_keys(client_id, configuration, proto, proto_conf_dir,
                       allow_missing=True):
    """Helper to load  keys and password for proto (ssh/davs/ftps/seafile)
    from user proto_conf_dir. Optional allow_missing is used to toggle the log
    errors about missing pw/keys files, which may not already exist.
    """
    section_dict = {}
    client_dir = client_id_dir(client_id)
    keys_path = os.path.join(configuration.user_home, client_dir,
                             proto_conf_dir, authkeys_filename)
    pw_path = os.path.join(configuration.user_home, client_dir,
                           proto_conf_dir, authpasswords_filename)
    digest_path = os.path.join(configuration.user_home, client_dir,
                               proto_conf_dir, authdigests_filename)
    try:
        keys_fd = open(keys_path)
        section_dict['authkeys'] = keys_fd.read()
        keys_fd.close()
    except Exception as exc:
        if not allow_missing:
            configuration.logger.error("load %s publickeys failed: %s" %
                                       (proto, exc))
    try:
        password = ''
        if os.path.exists(pw_path):
            pw_fd = open(pw_path)
            password_hash = pw_fd.read()
            if password_hash.strip():
                password = keyword_unchanged
            pw_fd.close()
        section_dict['authpassword'] = password
    except Exception as exc:
        if not allow_missing:
            configuration.logger.error("load %s password failed: %s" %
                                       (proto, exc))
    try:
        digest = ''
        if os.path.exists(digest_path):
            digest_fd = open(digest_path)
            password_digest = digest_fd.read()
            if password_digest.strip():
                digest = keyword_unchanged
            digest_fd.close()
        section_dict['authdigests'] = digest
    except Exception as exc:
        if not allow_missing:
            configuration.logger.error("load %s digest failed: %s" %
                                       (proto, exc))
    return section_dict


def load_ssh(client_id, configuration):
    """Load ssh keys and password from user ssh_conf_dir"""
    return _load_auth_pw_keys(client_id, configuration, 'ssh', ssh_conf_dir)


def load_davs(client_id, configuration):
    """Load davs keys and password from user davs_conf_dir"""
    return _load_auth_pw_keys(client_id, configuration, 'davs', davs_conf_dir)


def load_ftps(client_id, configuration):
    """Load ftps keys and password from user ftps_conf_dir"""
    return _load_auth_pw_keys(client_id, configuration, 'ftps', ftps_conf_dir)


def load_seafile(client_id, configuration):
    """Load seafile keys and password from user seafile_conf_dir"""
    return _load_auth_pw_keys(client_id, configuration, 'seafile', seafile_conf_dir)


def load_cloud(client_id, configuration):
    """Load cloud keys and password from user cloud_conf_dir"""
    return _load_auth_pw_keys(client_id, configuration, 'cloud', cloud_conf_dir)


def update_section_helper(client_id, configuration, section_filename, changes,
                          defaults, create_missing=True):
    """Update settings section in pickled file with values from changes
    dictionary. Optional create_missing can be used if the pickle should be
    created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    client_dir = client_id_dir(client_id)
    section_path = os.path.join(configuration.user_settings, client_dir,
                                section_filename)
    if not os.path.exists(section_path):
        if create_missing:
            section_dict = {}
        else:
            raise Exception('no %s file to update!' % section_filename)
    else:
        section_dict = unpickle(section_path, configuration.logger)
    for (key, val) in defaults.items():
        section_dict[key] = section_dict.get(key, val)
    section_dict.update(changes)
    if not pickle(section_dict, section_path, configuration.logger):
        raise Exception('could not save updated %s file!' % section_filename)
    return section_dict


def update_settings(client_id, configuration, changes, defaults,
                    create_missing=True):
    """Update settings in pickled settings file with values from changes
    dictionary. Optional create_missing can be used if the settings pickle
    should be created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    return update_section_helper(client_id, configuration, settings_filename,
                                 changes, defaults, create_missing)


def update_widgets(client_id, configuration, changes, defaults,
                   create_missing=True):
    """Update widgets in pickled widgets file with values from changes
    dictionary. Optional create_missing can be used if the widgets pickle
    should be created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    return update_section_helper(client_id, configuration, widgets_filename,
                                 changes, defaults, create_missing)


def update_profile(client_id, configuration, changes, defaults,
                   create_missing=True):
    """Update profile in pickled profile file with values from changes
    dictionary. Optional create_missing can be used if the profile pickle
    should be created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    return update_section_helper(client_id, configuration, profile_filename,
                                 changes, defaults, create_missing)


def update_duplicati(client_id, configuration, changes, defaults,
                     create_missing=True):
    """Update backup sets in pickled duplicati file with values from changes
    dictionary. Optional create_missing can be used if the backups pickle
    should be created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    return update_section_helper(client_id, configuration, duplicati_filename,
                                 changes, defaults, create_missing)


def update_twofactor(client_id, configuration, changes, defaults,
                     create_missing=True):
    """Update twofactor in pickled twofactor file with values from changes
    dictionary. Optional create_missing can be used if the twofactor pickle
    should be created if not already there.
    The defaults dictionary is used to set any missing values.
    """

    return update_section_helper(client_id, configuration, twofactor_filename,
                                 changes, defaults, create_missing)
