#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ucphoidlogin - sample selenium-based web client for basic ucph openid login
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

"""Example UCPH OpenID login using selenium and a webdriver of choice"""

import getpass
import sys
import time
import traceback

from migcore import init_driver, ucph_login

def main():
    """Main"""
    argc = len(sys.argv)-1
    if argc < 3:
        print "USAGE: %s browser url login [password]" % sys.argv[0]
        return 1

    browser = sys.argv[1]
    url = sys.argv[2]
    login = sys.argv[3]
    if argc > 3:
        passwd = sys.argv[4]
    else:
        passwd = getpass.getpass()

    driver = init_driver(browser)
    try:
        driver.get(url)
        status = ucph_login(driver, url, login, passwd)
        if not status:
            print "UCPH OpenID login FAILED!"
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
