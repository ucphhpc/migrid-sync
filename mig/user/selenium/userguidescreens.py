#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userguidescreens - selenium-based web client to grab user guide screenshots
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Screen grabber using selenium and a webdriver of choice.

Goes through a number of steps described in the user guide and grabs the
corresponding screenshots.
"""

import getpass
import sys
import time
import traceback

from migcore import init_driver, ucph_login, mig_login

def main():
    argc = len(sys.argv)-1
    if argc < 4:
        print "USAGE: %s browser url openid login [password]" % sys.argv[0]
        return 1

    browser = sys.argv[1]
    url = sys.argv[2]
    openid = sys.argv[3]
    login = sys.argv[4]
    if argc > 4:
        passwd = sys.argv[5]
    else:
        passwd = getpass.getpass()

    driver = init_driver(browser)
    try:
        driver.get(url)
        if openid.lower() == 'ucph':
            status = ucph_login(driver, url, login, passwd)
        elif openid.lower() == 'mig':
            status = mig_login(driver, url, login, passwd)
        else:
            print "No such OpenID handler: %s" % openid
            status = False
        if not status:
            print "%s OpenID login FAILED!" % openid
            return 1
        
        print "Now you can proceed using the browser or interrupt with Ctrl-C"
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print "User interrupt requested - shutting down"
    except Exception as exc:
        traceback.format_exc()


if __name__ == "__main__":
    main()
