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

"""A collection of functions using selenium and a webdriver of choice to remote
control your browser through a number of web page interactions.

Import and use for interactive purposes in stand-alone scripts something like:
driver = init_driver(browser)
driver.get(url)
mig_login(driver, url, login, passwd)
...
"""

from selenium import webdriver

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

def save_screen(driver, path):
    """Save a screenshot of current page in path"""
    driver.save_screenshot(path)

def ucph_login(driver, url, login, passwd, callbacks={}):
    """Login through the UCPH OpenID web form and optionally execute any
    provided callbacks for ready and filled states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    """
    status = True
    do_login = False
    try:
        elem = driver.find_element_by_class_name('form-signin')
        action = elem.get_property('action')
        if action == "https://openid.ku.dk/processTrustResult":
            do_login = True
            state = 'login-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
    except Exception, exc:
        print "ERROR: failed in UCPH login: %s" % exc

    if do_login:
        print "Starting UCPH OpenID login"
        login_elem = driver.find_element_by_name("user")
        pass_elem = driver.find_element_by_name("pwd")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        driver.find_element_by_name("allow").click()
    else:
        status = False
        print "UCPH OpenID login _NOT_ found"

    print "Starting UCPH OpenID login: %s" % status
    return status

def mig_login(driver, url, login, passwd, callbacks={}):
    """Login through the MiG OpenID web form and optionally execute any
    provided callbacks for ready and filled states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    """
    status = True
    do_login = False
    try:
        elem = driver.find_element_by_class_name('openidlogin')
        form = elem.find_element_by_xpath("//form")
        action = form.get_property('action')
        if action == "%s/openid/allow" % url:
            do_login = True
            state = 'login-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
    except Exception, exc:
        print "ERROR: failed in MiG login: %s" % exc

    if do_login:
        print "Starting MiG OpenID login"
        login_elem = driver.find_element_by_name("identifier")
        pass_elem = driver.find_element_by_name("password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        driver.find_element_by_name("yes").click()
    else:
        status = False
        print "MiG OpenID login _NOT_ found"

    print "Starting MiG OpenID login: %s" % status
    return status
