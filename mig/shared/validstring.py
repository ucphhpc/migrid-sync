#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# validstring - string validators
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

from shared.base import invisible_path
from shared.conf import get_configuration_object
from shared.defaults import keyword_auto, session_id_length, \
     session_id_charset, share_id_charset, share_mode_charset, \
     user_id_charset, user_id_min_length, user_id_max_length
from shared.fileio import user_chroot_exceptions, untrusted_store_res_symlink

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

def possible_user_id(configuration, user_id):
    """Check if user_id is a possible user ID based on knowledge about
    contents. We always use email or hexlified version of cert DN.
    """
    if len(user_id) < user_id_min_length or len(user_id) > user_id_max_length:
        return False
    for i in user_id:
        if not i in user_id_charset:
            return False
    return True

def possible_job_id(configuration, job_id):
    """Check if job_id is a possible job ID based on knowledge about contents
    and length. We use hexlify on a random string of session_id_bytes, which
    results in session_id_length characters."""
    if len(job_id) != session_id_length:
        return False
    for i in job_id:
        if not i in session_id_charset:
            return False
    return True

def possible_sharelink_id(configuration, share_id):
    """Check if share_id is a possible sharelink ID based on contents and
    length.
    """
    if len(share_id) != configuration.site_sharelink_length:
        return False
    if not share_id[0] in share_mode_charset:
        return False
    for i in share_id[1:]:
        if not i in share_id_charset:
            return False
    return True


def possible_jupyter_mount_id(configuration, jupyter_mount_id):
    """Check if the jupyter_mount_id is a possible ID based on the contents and the length"""
    if len(jupyter_mount_id) != session_id_length:
        return False
    for i in jupyter_mount_id:
        if not i in share_id_charset:
            return False
    return True


def valid_user_path(configuration, path, home_dir, allow_equal=False,
                    chroot_exceptions=keyword_auto, apache_scripts=False):
    """This is a convenience function for making sure that users do
    not access restricted files including files outside their own file
    tree(s): Check that path is a valid path inside user home directory,
    home_dir and it does not map to an invisible file or dir.
    In  a few situations it may be relevant to not allow an exact
    match, e.g. to prevent users from deleting or sharing the base of their
    home directory.

    IMPORTANT: it is still essential to always ONLY operate on explicitly
               abs-expanded paths in backends to avoid MYVGRID/../bla silently
               mapping to vgrid_files_home/bla rather than bla in user home.
    We include a check to make sure that path is already abspath expanded to
    help make sure this essential step is always done in backend.

    This check also rejects all 'invisible' files like htaccess files.

    NB: This check relies on the home_dir already verified from
    certificate data.
    Thus this function should *only* be used in relation to
    checking user home related paths. Other paths should be
    validated with the valid_dir_input from shared.base instead.

    IMPORTANT: additionally uses a chroot_exceptions list to follow symlinks
    e.g. into vgrid shared folders and verify their validity. This should be
    the case based on the symlink availability, but we check to avoid the
    attack vector. Otherwise it would be possible for users to access out of
    bounds data if they could somehow sneak in a symlink pointing to such
    locations. In particular this may be possible for users setting up their
    own storage resource where they have unrestricted symlink control. Thus,
    we explicitly check any such links and refuse them if they point outside
    the mount in question.
    If left to keyword_auto the list of chroot_exceptions is automatically
    extracted based on the configuration.
    The optional apache_scripts argument can be used to exclude the vgrid
    collaboration scripts when checking for invisible files. In that way we
    can allow the apache chroot checker exclusively to accept access to those
    scripts as needed for Xgi execution of them.
    """

    # We allow None value to support the few call points without one
    if configuration is None:
        configuration = get_configuration_object()

    _logger = configuration.logger

    #_logger.debug("valid_user_path on %s %s" % (path, home_dir))

    # Make sure caller has explicitly forced abs path
    
    if path != os.path.abspath(path):
        return False

    if invisible_path(path, apache_scripts):
        return False
    
    abs_home = os.path.abspath(home_dir)

    if chroot_exceptions == keyword_auto:
        chroot_exceptions = user_chroot_exceptions(configuration)

    # IMPORTANT: verify proper chrooting inside home_dir or chroot_exceptions

    real_path = os.path.realpath(path)
    real_home = os.path.realpath(abs_home)
    accept_roots = [real_home] + chroot_exceptions
    #_logger.debug("check that path %s (%s) is inside %s" % (path, real_path, accept_roots))
    accepted = False
    for accept_path in accept_roots:
        if real_path == accept_path or \
                real_path.startswith(accept_path + os.sep):
            accepted = True
            #_logger.debug("path %s is inside chroot %s" % (real_path, accept_path))
            break
    if not accepted:
        _logger.error("%s is outside chroot boundaries!" % path)
        return False

    # IMPORTANT: make sure path is not a symlink on a storage res mount
    # We cannot prevent users from creating arbitrary symlinks on resources
    # they have direct access to, so *don't ever* trust such symlinks unless
    # they point inside the storage resource mount itself.

    #_logger.debug("check that path %s is not inside store res" % path)
    if path != real_path and untrusted_store_res_symlink(configuration, path):
        _logger.error("untrusted symlink on a storage resource: %s" % path)
        return False

    # NOTE: abs_home may be e.g. email alias for real home so we test that
    # path either starts with abs_home or real_home to make sure it is really
    # a path in user home in addition to being in home or (general) chroots.
    inside = (path.startswith(abs_home + os.sep) or \
              path.startswith(real_home + os.sep))
    #_logger.debug("path %s is inside " % path)
    if not allow_equal:

        # path must be abs_home/X

        return inside
    else:

        # path must be either abs_home/X or abs_home

        try:
            same = os.path.samefile(abs_home, path)
        except Exception:

            # At least one of the paths doesn't exist

            same = False
        return inside or same
