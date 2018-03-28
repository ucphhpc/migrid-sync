#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migcore - a library of core selenium-based web helpers
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

"""A collection of functions using selenium and a webdriver of choice.

Import and use for interactive purposes in stand-alone scripts something like:
driver = init_driver(browser)
mig_login(driver, url, login, passwd)
...
"""

import sys
import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def init_driver(browser):
    """Init the requested browser driver"""
    if browser.lower() == 'chrome':
        driver = webdriver.Chrome()
    elif browser.lower() == 'firefox':
        driver = webdriver.Firefox()
    elif browser.lower() == 'safari':
        driver = webdriver.Safari()
    elif browser.lower() == 'ie':
        driver = webdriver.Ie()
    elif browser.lower() == 'edge':
        driver = webdriver.Edge()
    elif browser.lower() == 'phantomjs':
        driver = webdriver.PhantomJS()
    else:
        print "ERROR: Browser _NOT_ supported: %s" % browser
        driver = None
    return driver
    
def ucph_login(driver, url, login, passwd):
    """Login through the UCPH OpenID web form"""
    status = True
    do_login = False
    try:
        elem = driver.find_element_by_class_name('form-signin')
        action = elem.get_property('action') 
        if action == "https://openid.ku.dk/processTrustResult":
            do_login = True
    except Exception, exc:
        print "ERROR: failed in UCPH login: %s" % exc

    if do_login:
        print "Starting UCPH OpenID login"
        login_elem = driver.find_element_by_name("user")
        pass_elem = driver.find_element_by_name("pwd")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        driver.find_element_by_name("allow").click()
    else:
        status = False
        print "UCPH OpenID login _NOT_ found"

    print "Starting UCPH OpenID login: %s" % status
    return status

def mig_login(driver, url, login, passwd):
    status = True
    do_login = False
    try:
        elem = driver.find_element_by_class_name('openidlogin')
        form = elem.find_element_by_xpath("//form")
        action = form.get_property('action') 
        if action == "%s/openid/allow" % url:
            do_login = True
    except Exception, exc:
        print "ERROR: failed in MiG login: %s" % exc

    print "DEBUG: do login is %s" % do_login
    if do_login:
        print "Starting MiG OpenID login"
        login_elem = driver.find_element_by_name("identifier")
        pass_elem = driver.find_element_by_name("password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        driver.find_element_by_name("yes").click()
    else:
        status = False
        print "MiG OpenID login _NOT_ found"

    print "Starting MiG OpenID login: %s" % status
    return status
