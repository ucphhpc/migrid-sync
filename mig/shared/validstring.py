#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# validstring - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""String validation"""

import os.path

from shared.base import invisible_file

def cert_name_format(input_string):
    """ Spaces in certificate names are replaced with underscore internally """

    return input_string.title().replace(' ', '_')


def is_valid_email_address(addr, logger):
    """From http://www.secureprogramming.com/?action=view&feature=recipes&recipeid=1"""

    logger.info("verifying if '%s' is a valid email address" % addr)
    rfc822_specials = '()<>@,;:\\"[]'

    # First we validate the name portion (name@domain)

    c = 0
    while c < len(addr):
        if addr[c] == '"' and (not c or addr[c - 1] == '.' or addr[c
                                - 1] == '"'):
            c += 1
            while c < len(addr):
                if addr[c] == '"':
                    break
                if addr[c] == '\\' and addr[c + 1] == ' ':
                    c += 2
                    continue
                if ord(addr[c]) < 32 or ord(addr[c]) >= 127:
                    return False
                c += 1
            else:
                return False
            if addr[c] == '@':
                break
            if addr[c] != '.':
                return False
            c += 1
            continue
        if addr[c] == '@':
            break
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        if addr[c] in rfc822_specials:
            return False
        c += 1
    if not c or addr[c - 1] == '.':
        return False

    # Next we validate the domain portion (name@domain)

    domain = c = c + 1
    if domain >= len(addr):
        return False
    count = 0
    while c < len(addr):
        if addr[c] == '.':
            if c == domain or addr[c - 1] == '.':
                return False
            count += 1
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        if addr[c] in rfc822_specials:
            return False
        c += 1
    logger.info('%s is a valid email address' % addr)
    return count >= 1


def valid_user_path(path, home_dir, allow_equal=False):
    """This is a convenience function for making sure that users do
    not access restricted files including files outside their own file
    tree(s): Check that path is a valid path inside user home directory,
    home_dir.
    In  a few situations it may be relevant to not allow an exact
    match, e.g. to prevent users from deleting the base of their
    home directory.

    This check also rejects all 'invisible' files like htaccess files.

    NB: This check relies on the home_dir already verified from
    certificate data.
    Thus this function should *only* be used in relation to
    checking user home related paths. Other paths should be
    validated with the valid_dir_input function below.
    """

    real_path = os.path.abspath(path)

    if invisible_file(os.path.basename(real_path)):
        return False

    real_home = os.path.abspath(home_dir)
    inside = real_path.startswith(real_home + os.sep)
    if not allow_equal:

        # real_path must be real_home/X

        return inside
    else:

        # real_path must be either real_home/X or real_home

        try:
            same = os.path.samefile(real_home, real_path)
        except Exception:

            # At least one of the paths doesn't exist

            same = False
        return inside or same


def valid_dir_input(base, variable):
    """This function verifies that user supplied variable used as a directory
    in file manipulation doesn't try to illegally traverse directories by
    using e.g. '..'. The base argument is the directory that the user
    should be bound to, and the variable is the variable to be checked.
    The verification amounts to verifying that base/variable doesn't
    expand to a path outside base."""

    # Please note that base_dir must end in slash to avoid access to other
    # dirs when variable is a prefix of another dir in base

    path = os.path.abspath(base) + os.sep + variable
    if os.path.abspath(path) != path:

        # out of bounds

        return False
    return True


