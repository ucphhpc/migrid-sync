#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migoidlogin - sample selenium-based web client for basic mig openid login
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Example MiG OpenID login using selenium and a webdriver of choice"""

from __future__ import absolute_import
from __future__ import print_function

import getpass
import sys
import time
import traceback

from mig.user.selenium.migcore import init_driver, mig_login, shared_twofactor


def main():
    """Main"""
    argc = len(sys.argv) - 1
    if argc < 3:
        print("USAGE: %s browser url login [password]" % sys.argv[0])
        return 1

    browser = sys.argv[1]
    url = sys.argv[2]
    login = sys.argv[3]
    if argc > 3:
        passwd = sys.argv[4]
    else:
        passwd = getpass.getpass()
    if argc > 4:
        twofactor_key = sys.argv[5]
    else:
        twofactor_key = getpass.getpass("2FA *key*: ")

    driver = init_driver(browser)
    try:
        driver.get(url)
        status = mig_login(driver, url, login, passwd)
        if not status:
            print("MiG OpenID login FAILED!")
            return 1

        if twofactor_key:
            status = shared_twofactor(driver, url, twofactor_key)
            if not status:
                print("Post-OpenID 2FA FAILED!")
                return 2

        print("Now you can proceed using the browser or interrupt with Ctrl-C")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("User interrupt requested - shutting down")
    except Exception as exc:
        print("Unexpected exception:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
