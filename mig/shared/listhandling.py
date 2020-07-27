#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# listhandling - [insert a few words of module description on this line]
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

"""List functions"""
from __future__ import absolute_import

from .shared.fileio import pickle, unpickle


def frange(start, stop, jump, inc=False, limit=None):
    """
    Helper function to create a list from the given float values in the same
    manner as pythons default 'range' function, only using floats.

    Optional parameter 'inc' will include the final value in the list
    inclusively as this may be more intuitive to users. Standard non inclusive
    behaviour is default.
    """

    if not isinstance(start, float) and not isinstance(start, int):
        raise TypeError("Incorrect type provided for 'start'. May be either "
                        "'int' or 'float' but received: %s" % type(start))
    if not isinstance(stop, float) and not isinstance(stop, int):
        raise TypeError("Incorrect type provided for 'stop'. May be either "
                        "'int' or 'float' but received: %s" % type(stop))
    if not isinstance(jump, float) and not isinstance(jump, int):
        raise TypeError("Incorrect type provided for 'jump'. May be either "
                        "'int' or 'float' but received: %s" % type(jump))
    if jump > 0:
        if stop <= start:
            raise ValueError("Invalid values. With a positive 'jump' value, "
                             "stop (%s) should be bigger than start (%s)."
                             % (stop, start))
    elif jump == 0:
        raise TypeError("Invalid 'jump' value. Must be non-zero.")
    if jump < 0:
        if start <= stop:
            raise ValueError("Invalid values. With a negative 'jump' value, "
                             "stop (%s) should be smaller than start (%s)."
                             % (stop, start))

    value = start
    values = []
    while True:
        values.append(value)
        value += jump
        if jump > 0:
            if inc:
                if value > stop:
                    break
            else:
                if value >= stop:
                    break
        else:
            if inc:
                if value < stop:
                    break
            else:
                if value <= stop:
                    break
        if limit:
            if len(values) >= limit:
                raise ValueError("Invalid range. Is longer than defined "
                                 "limit '%s'" % limit)

    return values


def add_item_to_pickled_list(path, item, logger):
    list_ = unpickle(path, logger)
    output = ''
    if list_ == []:
        pass
    elif not list_:
        output += 'Failure: could not unpickle current list'
        return (False, output)

    # Check if the item already is in the list

    if item in list_:
        output += '%s is already in the list' % item
        return (False, output)

    # ok, lets add the new item and pickle and save the new list

    list_.append(item)
    status = pickle(list_, path, logger)
    if not status:
        output += 'pickle error'
        return (False, output)

    return (True, '')


def list_items_in_pickled_list(path, logger, allow_missing=False):

    # list items

    _list = unpickle(path, logger, allow_missing)
    if _list is False:
        return (False, 'Failure: could not unpickle list')
    return (True, _list)


def remove_item_from_pickled_list(
    path,
    item,
    logger,
    allow_empty_list=True,
    ):

    list_ = unpickle(path, logger)
    output = ''
    if list_ == []:

        # OK, if the list is empty

        pass
    elif not list_:

        output += 'Failure: could not unpickle current list'
        return (False, output)

    # Check if the item is in the list

    item = item.strip()
    if not item in list_:
        output += '%s not found in list' % item
        return (False, output)

    if not allow_empty_list:
        if len(list_) <= 1:
            output += 'You cannot remove the last item'
            return (False, output)

    # ok, lets remove the item and pickle and save the new list

    try:
        list_.remove(item)
    except:
        output += \
            'Strange error, %s could not be removed, but it seems to be in the list'\
             % item
        return (False, output)

    status = pickle(list_, path, logger)
    if not status:
        output += 'Error pickling new owners file'
        return (False, output)

    return (True, output)


def is_item_in_pickled_list(path, item, logger):
    list_ = unpickle(path, logger)
    if not list_:
        return False

    if len(list_) == 0:
        return False

    if item in list_:
        return True
    else:
        return False


