#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mig_xsss - [insert a few words of module description on this line]
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

import os
import sys
import time

# MiG SSS imports

import jobmanager
import jobexecuter
import logger

G_EXPECTED_TIME_FACTOR = 0.10
G_XSCREENSAVER_COMMAND = '/usr/X11R6/bin/xscreensaver-command -watch'

G_PGIDFILE = '/tmp/mig_xsss_job.gpid'


def SSS():

    # xscreensaver-command -watch dies when user logs out
    # and xscreensaver is respawned as nobody,
    # therefore we loop forever, to make sure its respawned.

    while 1:
        bScreenSaverActive = 0

        logger.write("Waiting 60 secs before staring: '"
                      + G_XSCREENSAVER_COMMAND + "'")
        time.sleep(60)

        fd = os.popen(G_XSCREENSAVER_COMMAND)
        xscreensaver_output = fd.readline()
        while len(xscreensaver_output) != 0:

        # writeToLog( "xscreensaver-command -watch: " + str )

            if (xscreensaver_output[0:5] == 'BLANK'
                 or xscreensaver_output[0:4] == 'LOCK')\
                 and bScreenSaverActive == 0:

        # writeToLog( "ACTIVATED")

                bScreenSaverActive = 1
                tActivatedTime = jobmanager.getTimeTuppel()

                pid = jobexecuter.startJob(tActivatedTime, G_PGIDFILE)

                if 0 != pid:
                    os._exit(0)
            elif xscreensaver_output[0:7] == 'UNBLANK'\
                 and bScreenSaverActive == 1:

        # writeToLog( "DEACTIVATED")

                bScreenSaverActive = 0
                tDeActivatedTime = jobmanager.getTimeTuppel()
                jobexecuter.killJob(G_PGIDFILE)

                jobmanager.logTimeActive(tActivatedTime,
                        tDeActivatedTime, G_EXPECTED_TIME_FACTOR)

            xscreensaver_output = fd.readline()

        logger.write("'" + G_XSCREENSAVER_COMMAND + "' <- DIED!.")


def main():

    # Remove previous logfile, if exists.

    if os.path.exists(logger.LOGFILE):
        os.remove(logger.LOGFILE)

    iPID = os.fork()
    if iPID == 0:

    # We want to get our own processgroup,
    # such that it is possible to kill us by GID,
    # without killing others in our original group.....

        os.setpgrp()

        SSS()


if __name__ == '__main__':
    main()
