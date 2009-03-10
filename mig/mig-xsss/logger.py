#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logger - [insert a few words of module description on this line]
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
from datetime import datetime

LOGFILE = './log/debug.log'


def get_output(fd):
    output = ''
    try:
        output = ''
        readline = fd.readline()
        while len(readline) > 0:
            output = output + readline
            readline = fd.readline()
    except:

    # Couldnt read fd

        output = 'N/A'

    return output


def getLogTimeStr():
    log_time = datetime.now()
    log_time_str = str(log_time.year) + '-'

    if 1 == len(str(log_time.month)):
        log_time_str = log_time_str + '0'

    log_time_str = log_time_str + str(log_time.month) + '-'

    if 1 == len(str(log_time.day)):
        log_time_str = log_time_str + '0'

    log_time_str = log_time_str + str(log_time.day) + ' '

    if 1 == len(str(log_time.hour)):
        log_time_str = log_time_str + '0'

    log_time_str = log_time_str + str(log_time.hour) + ':'

    if 1 == len(str(log_time.minute)):
        log_time_str = log_time_str + '0'

    log_time_str = log_time_str + str(log_time.minute) + ':'

    if 1 == len(str(log_time.second)):
        log_time_str = log_time_str + '0'

    log_time_str = log_time_str + str(log_time.second)

    return log_time_str


def write(param_sLogEntry):
    if os.path.exists(LOGFILE):
        fh = open(LOGFILE, 'a')
    else:
        fh = open(LOGFILE, 'w')
    fh.write(getLogTimeStr() + ' -> ' + str(param_sLogEntry) + '\n')
    fh.close()


# Main only for debug
# def main():
#  write( "this is a log string")

# if __name__ == '__main__' : main()
