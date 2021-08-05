#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobmanager - [insert a few words of module description on this line]
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

import time
import pickle
import os

G_WEEKDICTFILE = './data/weekdict.dat'
G_ACTIVELOGFILE = './log/active'

# Returns Tuppel of the form: ("Year", "Month", "MonthDay", "WeekNr", "WeekDay", "Hour", "Minutes")


def getTimeTuppel():

    year = time.strftime('%Y', time.localtime())
    month = time.strftime('%m', time.localtime())
    monthday = time.strftime('%d', time.localtime())
    weeknr = time.strftime('%U', time.localtime())
    weekday = time.strftime('%w', time.localtime())
    hour = time.strftime('%H', time.localtime())
    minutes = time.strftime('%M', time.localtime())

    return (
        year,
        month,
        monthday,
        weeknr,
        weekday,
        hour,
        minutes,
    )


# Get the dictionary with estimated times


def getWeekDict():
    input = open(G_WEEKDICTFILE, 'r')
    weekDict = pickle.load(input)
    input.close()

    return weekDict


# Write the dictionary with estimated times


def writeWeekDict(param_WeekDict):
    output = open(G_WEEKDICTFILE, 'w')
    pickle.dump(param_WeekDict, output)
    output.close()


# Log when screensaver was activited,
# how long it was expected to be active and how long it actually was active.
# log syntax: YEAR MONTH MONTHDAY WEEKNR WEEKDAY HOURS MINUTES ACTIVE_MINUTES EXPECTED_ACTIVE_MINUTES


def writeActiveLog(param_tStartTime, param_iNumOfMinutes,
                   param_iExpectedTime):
    logline = '' + param_tStartTime[0] + '\t' + param_tStartTime[1]\
        + '\t' + param_tStartTime[2] + '\t' + param_tStartTime[3]\
        + '\t' + param_tStartTime[4] + '\t' + param_tStartTime[5]\
        + '\t' + param_tStartTime[6] + '\t' + "%s" % param_iNumOfMinutes \
        + '\t' + "%s" % param_iExpectedTime + '\n'

    output = open(G_ACTIVELOGFILE, 'a')
    output.write(logline)
    output.close()


# Returns the expected number of minutes screensaver will
# be active.
#
# param_tActivated[4]: Weekday
# param_tActivated[5]: Hour


def getExpectedActiveMinutes(param_tActivated):
    weekDict = getWeekDict()

    return weekDict[int(param_tActivated[4])][int(param_tActivated[5])]


# Get the timedifference in minutes betewen the
# timetuppel param_tStartTime and param_tEndTime


def getTimeDiff(param_tStartTime, param_tEndTime):

    iNumOfWeeks = int(param_tEndTime[3]) - int(param_tStartTime[3])
    iNumOfDays = int(param_tEndTime[4]) - int(param_tStartTime[4])
    iNumOfHours = int(param_tEndTime[5]) - int(param_tStartTime[5])
    iNumOfMinutes = int(param_tEndTime[6]) - int(param_tStartTime[6])

    if iNumOfWeeks < 0:
        iNumOfWeeks = 53 + iNumOfWeeks

    if iNumOfDays < 0:
        iNumOfWeeks = iNumOfWeeks - 1
        iNumOfDays = 7 + iNumOfDays

    if iNumOfHours < 0:
        iNumOfDays = iNumOfDays - 1
        iNumOfHours = 24 + iNumOfHours

    if iNumOfMinutes < 0:
        iNumOfHours = iNumOfHours - 1
        iNumOfMinutes = 60 + iNumOfMinutes

    iNumOfMinutes = ((iNumOfWeeks * 7 + iNumOfDays) * 24 + iNumOfHours)\
        * 60 + iNumOfMinutes

    return iNumOfMinutes


# Log the time the screensaver has been active


def logTimeActive(param_tActivated, param_tDeActivated,
                  param_fExpectedTimeFactor):

    iNumOfMinutes = getTimeDiff(param_tActivated, param_tDeActivated)

    weekDict = getWeekDict()

    iLastExpectedTime = \
        weekDict[int(param_tActivated[4])][int(param_tActivated[5])]

    writeActiveLog(param_tActivated, iNumOfMinutes, iLastExpectedTime)

    iThisExpectedTime = param_fExpectedTimeFactor * iNumOfMinutes + (1
                                                                     - param_fExpectedTimeFactor) * iLastExpectedTime

    weekDict[int(param_tActivated[4])][int(param_tActivated[5])] = \
        iThisExpectedTime

    writeWeekDict(weekDict)
