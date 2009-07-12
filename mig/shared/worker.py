#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# worker - Background worker threads
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

"""Execute functions in a background thread with support for return values"""

import time
from threading import Thread


def dummy_test(delay):
    """Dummy function for testing: sleep for delay seconds and return True"""

    time.sleep(delay)
    return True


class Worker(Thread):

    """Worker threads with return value support"""

    def __init__(
        self,
        group=None,
        target=None,
        name=None,
        args=(),
        kwargs={},
        ):

        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        self.__result = None
        self.__exception = None
        Thread.__init__(self, group=group, target=target, args=args,
                        kwargs=kwargs)

    def run(self):
        """Start execution of this worker thread"""

        try:
            self.__result = self.__target(*self.__args, **self.__kwargs)
        except Exception, exc:
            self.__exception = exc

    def finish(self):
        """Wait for the worker thread and return result"""

        self.join()
        if self.__exception:
            raise self.__exception
        return self.__result


if '__main__' == __name__:
    print 'creating dummy test worker'
    task = Worker(target=dummy_test, args=(10, ))
    task.start()
    print 'dummy test worker running...'
    result = task.finish()
    print 'dummy test returned: %s' % result
