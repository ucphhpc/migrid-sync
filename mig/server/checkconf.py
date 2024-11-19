#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# checkconf - check MiGserver.conf file
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""Check MiGserver.conf either in specified path, pointed to in MIG_CONF or in
default mig/server/ location.
Currently mainly checks that required files and dirs exist, but may be extended
to include other variable checks.
"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import input
from past.builtins import basestring
import os
import re
import sys
import types

from mig.shared.configuration import Configuration, ConfigParser
from mig.shared.configuration import fix_missing

YES = 0
NO = 1
ALWAYS = 2


def usage():
    """Print usage help"""

    return """Usage: checkconf.py [server_conf]
The script checks the default MiG server configuration or server_conf for errors."""


def ask_reply(question):
    """Read user input"""

    return input(question)


def ask_confirm(question, allow_always=False):
    """Ask question and parse result. If allow_always is set the
    parsing inludes an always target. An empty input defaults to
    a yes, whereas any unexpected input results in a no.
    """

    answer = ask_reply(question)
    if not answer or answer.upper() == 'Y':
        return YES
    elif allow_always and answer.upper() == 'A':
        return ALWAYS
    return NO


def touch_file(path):
    """Make sure that file exists"""

    open(path, 'w').close()


def check_conf(conf_file):
    """Verify conf_file to be complete and have all referenced paths"""
    conf = None
    if not os.path.isfile(conf_file):
        if YES == ask_confirm('Configuration file %s does not exist! %s' %
                              (conf_file, 'create it? [Y/n] ')):
            try:
                touch_file(conf_file)
                print('created empty configuration file: %s' % conf_file)
            except Exception as err:
                print('could not create %s: %s' % (conf_file, err))
        else:
            return 2
    else:
        try:
            conf = Configuration(conf_file)
        except Exception as err:
            print('configuration file %s is incomplete! %s' % (conf_file, err))

    if not conf:
        if YES == ask_confirm('Add missing configuration options? [Y/n] '):
            fix_missing(conf_file)
            try:
                conf = Configuration(conf_file)
            except Exception as err:
                print('configuration file %s is still incomplete! %s' %
                      (conf_file, err))
            return 1
        else:
            return 2

    # Search object attributes for possible paths

    attrs = []
    ignore_attrs = ['__class__', '__doc__', '__module__']
    path_re = re.compile('(' + os.sep + "[\w\._-]*)+$")

    _logger = conf.logger
    _logger.info('Checking configuration paths in %s ...', conf_file)
    print('Checking configuration paths in %s ...' % conf_file)
    warnings = 0
    missing_paths = []
    conf_parser = ConfigParser()
    conf_parser.read([conf_file])
    for (name, val) in conf_parser.items('GLOBAL'):
        if not isinstance(val, basestring):

            # ignore non-string values

            continue
        elif not val:

            # ignore empty string values

            continue
        elif name.endswith('_url') or val.find('://') != -1:

            # ignore url values

            continue
        elif val.find('/emailAddress=') != -1:

            # ignore x509 DN values

            continue
        elif path_re.match(val):
            path = os.path.normpath(val)
            if os.path.isdir(path):
                _logger.info('%s OK: %s is a dir', name, val)
            elif os.path.isfile(path):
                _logger.info('%s OK: %s is a file', name, val)
            elif os.path.exists(path):
                _logger.info('%s OK: %s exists', name, val)
            else:
                _logger.warning('%s: %s does not exist!', name, val)
                print('* WARNING *: %s: %s does not exist!' % (name, val))
                if not path in missing_paths:
                    missing_paths.append(path)
                warnings += 1

    _logger.info('Found %d configuration problem(s)', warnings)
    print('Found %d configuration problem(s)' % warnings)

    if warnings > 0:
        answer = ask_confirm('Add missing path(s)? [Y/n/a]: ',
                             allow_always=True)
        if answer != NO:

            # Sort missing paths to avoid overlaps resulting in errors

            missing_paths.sort()

            for path in missing_paths:
                if ALWAYS == answer:

                    # 'always' answer reults in default type for all missing entries

                    path_type = None
                elif YES == answer:
                    path_type = \
                        ask_reply('Create %s as a (d)irectory, (f)ile or (p)ipe? [D/f/p] '
                                  % path)
                if not path_type or 'D' == path_type.upper():
                    try:
                        os.makedirs(path)
                        print('created directory %s' % path)
                    except Exception as err:
                        print('could not create directory %s: %s' %
                              (path, err))
                elif 'F' == path_type.upper():
                    try:
                        dirname = os.path.dirname(path)
                        if dirname and not os.path.exists(dirname):
                            os.makedirs(dirname)
                            print('created directory %s' % dirname)
                        touch_file(path)
                        print('created file %s' % path)
                    except Exception as err:
                        print('could not create file %s: %s' % (path, err))
                elif 'P' == path_type.upper():
                    try:
                        dirname = os.path.dirname(path)
                        if dirname and not os.path.exists(dirname):
                            os.makedirs(dirname)
                            print('created directory %s' % dirname)
                        os.mkfifo(path)
                        print('created pipe %s' % path)
                    except Exception as err:
                        print('could not create file %s: %s' % (path, err))
    print('completed check of %s: %d warning(s)' % (conf_file, warnings))
    return warnings


if __name__ == "__main__":
    if sys.argv[1:]:
        file_list = sys.argv[1:]
    else:
        env_conf = os.environ.get('MIG_CONF', '')
        if env_conf:
            conf_file = env_conf
        else:
            # We may be called from MIG_ROOT/mig/server or from MIG_ROOT/bin
            current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            parent_dir = os.path.dirname(current_dir)
            if os.path.basename(current_dir) == 'bin':
                base_dir = parent_dir
            else:
                base_dir = os.path.dirname(parent_dir)

            conf_file = os.path.join(base_dir, "mig", "server",
                                     'MiGserver.conf')
        if not os.path.isfile(conf_file):
            print(usage())
            sys.exit(2)
        file_list = [conf_file]

    retval = 0
    for conf_file in file_list:
        retval += check_conf(conf_file)
    sys.exit(retval)
