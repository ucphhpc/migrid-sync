#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - grid daemon base helper functions
# Copyright (C) 2010-2020  The MiG Project lead by Brian Vinter
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

"""General MiG daemon functions"""

import os

from shared.base import invisible_path
from shared.safeinput import valid_path
from shared.validstring import possible_user_id, possible_gdp_user_id, \
    possible_sharelink_id, possible_job_id, possible_jupyter_mount_id, \
    valid_user_path, is_valid_email_address


def accepting_username_validator(configuration, username):
    """A simple username validator which accepts everything"""
    return True


def default_username_validator(configuration, username, force_email=True):
    """The default username validator restricted to only accept usernames that
    are valid in grid daemons, namely a possible user, sharelink, job or
    jupyter mount ID.
    The optional and default enabled force_email option is used to further
    limit user_id values to actual email addresses, as always required in grid
    daemons.
    """
    logger = configuration.logger
    # logger.debug("username: %s, force_email: %s" % (username, force_email))

    if possible_gdp_user_id(configuration, username):
        return True
    elif possible_user_id(configuration, username):
        if not force_email:
            return True
        elif is_valid_email_address(username, configuration.logger):
            return True
    if possible_sharelink_id(configuration, username):
        return True
    if possible_job_id(configuration, username):
        return True
    if possible_jupyter_mount_id(configuration, username):
        return True
    return False


def get_fs_path(configuration, abs_path, root, chroot_exceptions):
    """Internal helper to translate path with chroot and invisible files
    in mind. Also assures general path character restrictions are applied.
    Automatically expands to abs path to avoid traversal issues with e.g.
    MYVGRID/../bla that would expand to vgrid_files_home/bla instead of bla
    in user home if left as is.
    """
    try:
        valid_path(abs_path)
    except:
        raise ValueError("Invalid path characters")

    if not valid_user_path(configuration, abs_path, root, True,
                           chroot_exceptions):
        raise ValueError("Illegal path access attempt")
    return abs_path


def strip_root(configuration, path, root, chroot_exceptions):
    """Internal helper to strip root prefix for chrooted locations"""
    accept_roots = [root] + chroot_exceptions
    for root in accept_roots:
        if path.startswith(root):
            return path.replace(root, '')
    return path


def flags_to_mode(flags):
    """Internal helper to convert bitmask of os.O_* flags to open-mode.

    It only handles read, write and append with and without truncation.
    Append and write always creates the file if missing, so checking for
    missing file creation flag should generally be handled separately.
    The same goes for handling of invalid flag combinations.

    This function is inspired by the XMP example in the fuse-python code
    http://sourceforge.net/apps/mediawiki/fuse/index.php?title=Main_Page
    but we need to prevent truncation unless explicitly requested.
    """
    # Truncate per default when enabling write - disable later if needed
    main_modes = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    mode = main_modes[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags & os.O_APPEND:
        mode = mode.replace('w', 'a', 1)
    # Disable truncation unless explicitly requested
    if not (flags & os.O_TRUNC):
        mode = mode.replace('w+', 'r+', 1)
        mode = mode.replace('w', 'r+', 1)
    return mode


def acceptable_chmod(path, mode, chmod_exceptions):
    """Internal helper to check that a chmod request is safe. That is, it
    only changes permissions that does not lock out user. Furthermore anything
    we deem invisible_path or inside the dirs in chmod_exceptions should be
    left alone to avoid users touching read-only files or enabling execution
    of custom cgi scripts with potentially arbitrary code.
    We require preservation of user read+write on files and user
    read+write+execute on dirs.
    Limitation to sane group/other access perms is left to the caller.
    """

    if invisible_path(path) or \
        True in [os.path.realpath(path).startswith(i) for i in
                 chmod_exceptions]:
        return False
    # Never touch special leading bits (suid, sgid, etc.)
    if mode & 0o7000 != 00000:
        return False
    if os.path.isfile(path) and mode & 0o600 == 0o600:
        return True
    elif os.path.isdir(path) and mode & 0o700 == 0o700:
        return True
    else:
        return False
