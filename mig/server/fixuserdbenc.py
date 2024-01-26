#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# fixuserdbenc - fix all entries in user DB to be UTF8
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Convert any old iso-8859-1 encoded strings in user DB comments to utf8.

On purpose does NOT rely on any migrid code so that it can be used outside
actual site deployments e.g. before migration to more current system or
container environment.
"""

from __future__ import print_function
from __future__ import absolute_import

import os
import pickle
import sys

from past.builtins import basestring


def is_unicode(val):
    """Return boolean indicating if val is a unicode string. We avoid
    `isinstance(val, unicode)`
    and the like since it breaks when combined with python-future and futurize.
    """
    return (type(u"") == type(val))


def force_encoding(val, encoding, stringify=False):
    """Internal helper to encode unicode strings to specified encoding"""
    # We run into all kind of nasty encoding problems if we mix
    if not isinstance(val, basestring):
        if stringify:
            val = "%s" % val
        else:
            return val
    if not is_unicode(val):
        return val
    return b"%s" % val.encode(encoding)


if __name__ == "__main__":
    orig_user_db = None
    expected_enc, alternative_enc = "utf8", "iso-8859-1"
    cmd_path = os.path.abspath(sys.argv[0])
    cmd_parent = os.path.dirname(cmd_path)
    cmd_grandparent = os.path.dirname(cmd_parent)
    migrid_base = os.path.dirname(cmd_grandparent)
    db_base = os.path.join(migrid_base, "state", "user_db_home")
    orig_db_path = os.path.join(db_base, "MiG-users.db")
    fixed_db_path = os.path.join(db_base, "fixed-MiG-users.db")
    if sys.argv[1:]:
        orig_db_path = sys.argv[1]
    if sys.argv[2:]:
        fixed_db_path = sys.argv[2]

    if orig_db_path == fixed_db_path:
        print("ERROR: cannot fix user DB in %s inline - use new dst" %
              orig_db_path)
        sys.exit(1)

    print("INFO: fix user DB in %s and save in %s" % (orig_db_path,
                                                      fixed_db_path))

    orig_db_fd = open(orig_db_path, "rb")
    try:
        orig_user_db = pickle.load(orig_db_fd, encoding=expected_enc)
        fix_needed = False
    except UnicodeDecodeError as ude:
        fix_needed = True
        print("INFO: failed to load user db in %s with expected %s encoding" %
              (orig_db_path, expected_enc))
        #print("DEBUG: error is: %s" % ude)
        print("INFO: rewind and retry alternative %s encoding" % alternative_enc)
        try:
            orig_db_fd.seek(0)
            orig_user_db = pickle.load(orig_db_fd, encoding=alternative_enc)
        except UnicodeDecodeError as ude:
            print("ERROR: also failed to load %s with alternative %s encoding" %
                  (orig_db_path, alternative_enc))
            print("ERROR: unexpected exception details: %s" % ude)
    orig_db_fd.close()

    if orig_user_db is None:
        print("giving up fixing encoding - unsupported encoding!")
        sys.exit(1)

    print("INFO: read original user DB with %d entries in %s" % (len(orig_user_db),
                                                                 orig_db_path))

    if not fix_needed:
        print("INFO: user db in %s already has expected encoding" % orig_db_path)
        sys.exit(0)

    print("INFO: fixing wrong encoding of user db loaded from %s" % orig_db_path)
    fixed_user_db = {}
    for orig_user_id in orig_user_db:
        orig_user_dict = orig_user_db[orig_user_id]
        fixed_user_id = force_encoding(orig_user_id, expected_enc)
        fixed_user_dict = {}
        for id_field in orig_user_dict:
            fixed_field = force_encoding(id_field, expected_enc)
            fixed_val = force_encoding(orig_user_dict[id_field], expected_enc)
            fixed_user_dict[fixed_field] = fixed_val
        fixed_user_db[fixed_user_id] = fixed_user_dict
        #print("DEBUG: added fixed user %s:\n%s" % (fixed_user_id, fixed_user_dict))

    print("INFO: writing fixed user DB with %d entries in %s" % (len(fixed_user_db),
                                                                 fixed_db_path))
    fixed_db_fd = open(fixed_db_path, "wb")
    pickle.dump(fixed_user_db, fixed_db_fd)
    fixed_db_fd.close()

    print("INFO: you might want to replace old user DB in %s with fixed in %s" %
          (orig_db_path, fixed_db_path))
