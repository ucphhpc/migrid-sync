#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# configsupp - configuration helpers for unit tests
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Configuration related details within the test support library."""

from tests.support.loggersupp import FakeLogger


class FakeConfiguration:
    """A simple helper to pretend we have a real Configuration object with any
    required attributes explicitly passed.
    Automatically attaches a FakeLogger instance if no logger is provided in
    kwargs.
    """

    def __init__(self, **kwargs):
        """Initialise instance attributes to be any named args provided and a
        FakeLogger instance attached if not provided.
        """
        self.__dict__.update(kwargs)
        if not 'logger' in self.__dict__:
            dummy_logger = FakeLogger()
            self.__dict__.update({'logger': dummy_logger})
