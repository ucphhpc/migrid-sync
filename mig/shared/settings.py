#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - [insert a few words of module description on this line]
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

import os
import datetime

import shared.parser as parser
from shared.base import client_id_dir
from shared.defaults import settings_filename, profile_filename, \
     widgets_filename, ssh_conf_dir, davs_conf_dir, ftps_conf_dir, \
     authkeys_filename, authpasswords_filename, keyword_unchanged
from shared.fileio import pickle, unpickle
from shared.modified import mark_user_modified
from shared.profilekeywords import get_keywords_dict as get_profile_fields
from shared.pwhash import make_hash
from shared.safeinput import valid_password
from shared.settingskeywords import get_keywords_dict as get_settings_fields
from shared.ssh import parse_pub_key
from shared.widgetskeywords import get_keywords_dict as get_widgets_fields


def parse_and_save_pickle(source, destination, keywords, client_id,
                          configuration, strip_space, strip_comments):
    """Use conf parser to parse settings in mRSL file and save resulting
    dictionary in a pickled file in user_settings.
    """
    client_dir = client_id_dir(client_id)
    result = parser.parse(source, strip_space, strip_comments)

    (status, parsemsg) = parser.check_types(result, keywords,
            configuration)

    try:
        os.remove(source)
    except Exception, err:
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
            except Exception, exc:
                raise Exception('Invalid public key: %s' % key)
        keys_fd = open(keys_path, 'wb')
        keys_fd.write(keys_content)
        keys_fd.close()
    except Exception, exc:
        status = False
        msg = 'ERROR: writing %s publickey file: %s' % (client_id, exc)
    return (status, msg)

def parse_and_save_passwords(passwords_path, passwords_content, client_id,
                             configuration):
    """Check password strength and write the hashed content to passwords_path
    using the password hashing helper.
    """
    # TODO: validate?
    status, msg = True, ''
    if passwords_content == keyword_unchanged:
        return (status, msg)
    try:
        if not passwords_content:
            password_hash = ''
        else:
            valid_password(passwords_content)
            password_hash = make_hash(passwords_content)
        passwords_fd = open(passwords_path, 'wb')
        passwords_fd.write(password_hash)
        passwords_fd.close()
    except Exception, exc:
        status = False
        msg = 'ERROR: writing %s passwords file: %s' % (client_id, exc)
    return (status, msg)

def _parse_and_save_auth_pw_keys(publickeys, password, client_id,
                                 configuration, proto, proto_conf_dir):
    """Validate and write publickey and password settings for proto
    (ssh/davs/ftps) in proto_conf_dir.
    """
    client_dir = client_id_dir(client_id)
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
                                         configuration)
    status = (key_status[0] and pw_status[0], key_status[1] + pw_status[1])
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

def load_section_helper(client_id, configuration, section_filename,
                        section_keys, include_meta=False):
    """Load settings section from pickled file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    client_dir = client_id_dir(client_id)
    section_path = os.path.join(configuration.user_settings, client_dir,
                                section_filename)
    section_dict = unpickle(section_path, configuration.logger)
    if section_dict and not include_meta:
        real_keys = section_keys
        for key in section_dict.keys():
            if not key in real_keys:
                del section_dict[key]
    return section_dict


def load_settings(client_id, configuration, include_meta=False):
    """Load settings from pickled settings file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, settings_filename,
                               get_settings_fields().keys(), include_meta)

def load_widgets(client_id, configuration, include_meta=False):
    """Load widgets from pickled widgets file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, widgets_filename,
                               get_widgets_fields().keys(), include_meta)

def load_profile(client_id, configuration, include_meta=False):
    """Load profile from pickled profile file. Optional include_meta
    controls the inclusion of meta data like creator and creation time.
    """

    return load_section_helper(client_id, configuration, profile_filename,
                               get_profile_fields().keys(), include_meta)

def _load_auth_pw_keys(client_id, configuration, proto, proto_conf_dir):
    """Helper to load  keys and password for proto (ssh/davs/ftps) from user
    proto_conf_dir.
    """
    section_dict = {}
    client_dir = client_id_dir(client_id)
    keys_path = os.path.join(configuration.user_home, client_dir,
                             proto_conf_dir, authkeys_filename)
    pw_path = os.path.join(configuration.user_home, client_dir,
                           proto_conf_dir, authpasswords_filename)
    try:
        keys_fd = open(keys_path)
        section_dict['authkeys'] = keys_fd.read()
        keys_fd.close()
    except Exception, exc:
        configuration.logger.error("load %s publickeys failed: %s" % (proto,
                                                                      exc))
    try:
        password = ''
        if os.path.exists(pw_path):
            pw_fd = open(pw_path)
            password_hash = pw_fd.read()
            if password_hash.strip():
                password = keyword_unchanged
            pw_fd.close()
        section_dict['authpassword'] = password
    except Exception, exc:
        configuration.logger.error("load %s password failed: %s" % (proto,
                                                                    exc))
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

