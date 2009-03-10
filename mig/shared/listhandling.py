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

from shared.fileio import pickle, unpickle


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


def list_items_in_pickled_list(path, logger):

    # list items

    list_ = unpickle(path, logger)
    if list_ == []:
        pass
    elif not list_:
        return (False, 'Failure: could not unpickle list')
    return (True, list_)


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


