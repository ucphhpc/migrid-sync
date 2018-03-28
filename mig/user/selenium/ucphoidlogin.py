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

"""Example UCPH OpenID login using selenium and a webdriver of choice.

Can easily be used as a template for extending with further actions.
"""

import getpass
import sys
import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def ku_login(driver, url, login, passwd):
    status = True
    do_login = False
    try:
        elem = driver.find_element_by_class_name('form-signin')
        url = elem.get_property('action') 
        if url == "https://openid.ku.dk/processTrustResult":
            do_login = True
    except Exception as ex:
        pass

    if do_login:
        print "Starting KU OpenID login"
        login_elem = driver.find_element_by_name("user")
        pass_elem = driver.find_element_by_name("pwd")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        driver.find_element_by_name("allow").click()
    else:
        status = False
        print "KU OpenID login _NOT_ found"

    """
    if status:
        try:
            element = WebDriverWait(driver, 10).until(
                EC.url_matches(url))
        except Exception as ex:
            print "Ex: %s" % ex
            status = False
    """
    
    print "Starting KU OpenID login: %s" % status
    return status


def main():
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

    if browser.lower() == 'chrome':
        driver = webdriver.Chrome()
    elif browser.lower() == 'firefox':
        driver = webdriver.Firefox()
    elif browser.lower() == 'safari':
        driver = webdriver.Safari()
    elif browser.lower() == 'ie':
        driver = webdriver.IE()
    elif browser.lower() == 'edge':
        driver = webdriver.Edge()
    elif browser.lower() == 'phantomjs':
        driver = webdriver.PhantomJS()
    else:
        print "Browser _NOT_ supported: %s" % browser
        return 1

    try:
        driver.get(url)
        status = ku_login(driver, url, login, passwd)
        if not status:
            print "KU OpenID login FAILED !!!"
            return 1
    
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print "User interrupt requested - shutting down"
    except Exception as exc:
        traceback.format_exc()


if __name__ == "__main__":
    main()
