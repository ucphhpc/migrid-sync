#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reset2fakey - (Re)set user 2FA key
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

"""(Re)set user 2FA key"""

import getopt
import os
import sys
import base64
import datetime
import tempfile
import pyotp


from shared.auth import reset_twofactor_key, valid_otp_window
from shared.base import client_id_dir
from shared.defaults import twofactor_filename, twofactor_key_name, \
    twofactor_interval_name
from shared.conf import get_configuration_object
from shared.fileio import delete_file
from shared.settings import load_twofactor, parse_and_save_twofactor
from shared.twofactorkeywords import get_keywords_dict as twofactor_keywords


def enable2fa(configuration, user_id, verbose, force=False):
    """Check if twofactor is enabled and if not enable for all
    services"""
    if verbose:
        print "Enabling 2FA setup for %r" % user_id
    if not force:
        current_twofactor_dict = load_twofactor(user_id, configuration)
        if current_twofactor_dict:
            return True
    keywords_dict = twofactor_keywords(configuration)
    topic_mrsl = ''
    for keyword, _ in keywords_dict.iteritems():
        topic_mrsl += '''::%s::
%s

''' % (keyword.upper(), 'True')

    try:
        (filehandle, tmptopicfile) = tempfile.mkstemp(text=True)
        os.write(filehandle, topic_mrsl)
        os.close(filehandle)
    except Exception, exc:
        msg = "Error: Problem writing temporary topic file on server."
        print "%s : %s" % (msg, exc)
        return False
    (parse_status, _) = parse_and_save_twofactor(tmptopicfile, user_id,
                                                 configuration)
    if parse_status:
        print "Enabled all two-factor services for user: %r" % user_id
    else:
        print "Error parsing and saving two-factor dict"

    try:
        os.remove(tmptopicfile)
    except Exception, exc:
        pass  # probably deleted by parser!

    return parse_status


def remove2fa(configuration, user_id, verbose, force=False):
    """Removes two factor secrets and settings for client_id
    NOTE: Active sessions remain until logout"""
    _logger = configuration.logger
    if verbose:
        print "Removing 2FA setup for %r" % user_id
    allow_missing = False
    if force:
        allow_missing = True
    client_dir = client_id_dir(user_id)
    settings_dir = os.path.join(configuration.user_settings, client_dir)

    key_path = os.path.join(settings_dir, twofactor_key_name)
    if verbose:
        print "Removing key file: %s" % key_path
    status = delete_file(key_path, _logger, allow_missing=allow_missing)
    if not status and not force:
        return status

    interval_path = os.path.join(settings_dir, twofactor_interval_name)
    if verbose:
        print "Removing interval file: %s" % interval_path
    status = delete_file(interval_path, _logger, allow_missing=True)
    if not status and not force:
        return status

    twofactor_settings_path = os.path.join(settings_dir, twofactor_filename)
    if verbose:
        print "Removing twofactor file: %s" % twofactor_settings_path
    status = delete_file(twofactor_settings_path, _logger,
                         allow_missing=allow_missing)

    return status


def usage(name='reset2fakey.py'):
    """Usage help"""

    print """(Re)set user 2FA key.
Usage:
%(name)s [OPTIONS] -i USER_ID [SEED_FILE] [INTERVAL]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -i CERT_DN          CERT_DN of user to edit
   -a                  Enable 2fa for all services
   -r                  Remove 2fa for all services
   -v                  Verbose output
"""\
         % {'name': name}


# ## Main ###

if '__main__' == __name__:
    conf_path = None
    force = False
    verbose = False
    user_id = None
    enable_all = False
    seed = None
    seed_file = None
    interval = None
    remove = False
    opt_args = 'c:fhari:v'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError, err:
        print 'Error: ', err.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-i':
            user_id = val
        elif opt == '-a':
            enable_all = True
        elif opt == '-r':
            remove = True
        elif opt == '-v':
            verbose = True
        else:
            print 'Error: %s not supported!' % opt

    if conf_path and not os.path.isfile(conf_path):
        print 'Failed to read configuration file: %s' % conf_path
        sys.exit(1)

    if verbose:
        if conf_path:
            os.environ['MIG_CONF'] = conf_path
            print 'using configuration in %s' % conf_path
        else:
            print 'using configuration from MIG_CONF (or default)'

    configuration = get_configuration_object(skip_log=True)
    if not configuration.site_enable_twofactor:
        print 'Error: Two-factor authentication disabled for site'
        sys.exit(1)

    if not user_id:
        print 'Error: Existing user ID is required'
        usage()
        sys.exit(1)

    if remove:
        status = remove2fa(configuration, user_id, verbose, force)
        if status:
            print "Two factor setup succesfully removed"
            sys.exit(0)
        else:
            print "Failed to remove two factor setup"
            sys.exit(1)

    if not enable2fa(configuration, user_id, verbose, enable_all):
        print 'Error: Failed to enable two-factor authentication'
        sys.exit(1)

    if args:
        try:
            seed_file = args[0]
            interval = args[1]
        except IndexError:
             # Ignore missing optional arguments

            pass

    if seed_file:
        try:
            s_fd = open(seed_file, 'r')
            seed = s_fd.read().strip()
            s_fd.close()
        except Exception, exc:
            print "Failed to read sead file: %s" % (exc)
            if not force:
                sys.exit(1)

    if seed and len(seed) == 40:
        if verbose:
            print "Detected HEX seed, re-encoding to base32"
        try:
            seed = base64.b32encode(base64.b16decode(seed))
        except Exception, exc:
            print "Failed to base32 encode seed"
            if not force:
                sys.exit(1)
    elif seed and len(seed) != 32:
        print "Malformed seed, must be of length 32: %d" % len(seed)
        if not force:
            sys.exit(1)

    if interval:
        try:
            interval = int(interval)
        except:
            print "Skipping non-int interval: %s" % interval
            interval = None

    if verbose:
        if seed:
            print "using seed: %s" % seed
        else:
            print "using random seed"
        if interval:
            print "using interval: %s" % interval

    twofa_key = reset_twofactor_key(user_id, configuration,
                                    seed=seed, interval=interval)
    if verbose:
        print "New two factor key: %s" % twofa_key

    if twofa_key:
        print "Two factor key succesfully reset"
        if verbose:
            current_time = datetime.datetime.now()
            totp_default = pyotp.TOTP(twofa_key)
            totp_custom_totp = None
            if interval:
                totp_custom_totp = pyotp.TOTP(twofa_key, interval=interval)

            if valid_otp_window == 0:
                print "default interval, code: %s" \
                    % totp_default.at(current_time, 0)
                if totp_custom_totp:
                    print "interval: %d, code: %s" \
                        % (interval, totp_custom_totp.at(current_time, 0))
            else:
                for i in range(-valid_otp_window, valid_otp_window + 1):
                    print "default interval, window: %d, code: %s" \
                        % (i, totp_default.at(current_time, i))
                    if totp_custom_totp:
                        print "interval: %d, window: %d, code: %s" \
                            % (interval, i,
                                totp_custom_totp.at(current_time, i))
    else:
        print "Failed to reset two factor key"
        sys.exit(1)

    sys.exit(0)
