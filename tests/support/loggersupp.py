#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# loggersupp - logging helpers for unit tests
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

"""Logger related details within the test support library."""

from collections import defaultdict
import os
import re

from tests.support.suppconst import MIG_BASE, TEST_BASE


class FakeLogger:
    """An output capturing logger suitable for being passed to the
    majority of MiG code by presenting an API compatible interface
    with the common logger module.

    An instance of this class is made available to test cases which
    can pass it down into function calls and subsequenently make
    assertions against any output strings hat were recorded during
    execution while also avoiding noise hitting the console.
    """

    RE_UNCLOSEDFILE = re.compile(
        'unclosed file <.*? name=\'(?P<location>.*?)\'( .*?)?>')

    def __init__(self):
        self.channels_dict = defaultdict(list)
        self.forgive_by_channel = defaultdict(lambda: False)
        self.unclosed_by_file = defaultdict(list)

    def _append_as(self, channel, line):
        self.channels_dict[channel].append(line)

    def check_empty_and_reset(self):
        """Make sure resulting log is really empty"""
        channels_dict = self.channels_dict
        forgive_by_channel = self.forgive_by_channel
        unclosed_by_file = self.unclosed_by_file

        # reset the record of any logged messages
        self.channels_dict = defaultdict(list)
        self.forgive_by_channel = defaultdict(lambda: False)
        self.unclosed_by_file = defaultdict(list)

        # complain loudly (and in detail) in the case of unclosed files
        if len(unclosed_by_file) > 0:
            messages = '\n'.join({' --> %s: line=%s, file=%s' % (fname, lineno, outname)
                                  for fname, (lineno, outname) in unclosed_by_file.items()})
            raise RuntimeError('unclosed files encountered:\n%s' % (messages,))

        if channels_dict['error'] and not forgive_by_channel['error']:
            raise RuntimeError('errors reported to logger:\n%s' %
                               '\n'.join(channels_dict['error']))

    def forgive_errors(self):
        """Allow log errors for cases where they are expected"""
        self.forgive_by_channel['error'] = True

    # logger interface

    def debug(self, line):
        """Mock log action of same name"""
        self._append_as('debug', line)

    def error(self, line):
        """Mock log action of same name"""
        self._append_as('error', line)

    def info(self, line):
        """Mock log action of same name"""
        self._append_as('info', line)

    def warning(self, line):
        """Mock log action of same name"""
        self._append_as('warning', line)

    def write(self, message):
        """Actual write handler"""
        channel, namespace, specifics = message.split(':', 2)

        # ignore everything except warnings sent by the python runtime
        if not (channel == 'WARNING' and namespace == 'py.warnings'):
            return

        filename_and_datatuple = FakeLogger.identify_unclosed_file(specifics)
        if filename_and_datatuple is not None:
            self.unclosed_by_file.update((filename_and_datatuple,))

    @staticmethod
    def identify_unclosed_file(specifics):
        """Warn about unclosed files"""
        filename, lineno, exc_name, message = specifics.split(':', 3)

        exc_name = exc_name.lstrip()
        if exc_name != 'ResourceWarning':
            return

        matched = FakeLogger.RE_UNCLOSEDFILE.match(message.lstrip())
        if matched is None:
            return

        relative_testfile = os.path.relpath(filename, start=MIG_BASE)
        relative_outputfile = os.path.relpath(
            matched.groups('location')[0], start=TEST_BASE)
        return (relative_testfile, (lineno, relative_outputfile))
