#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migcore - a library of core selenium-based web helpers
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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
from __future__ import print_function

# Robust import - only fail if used without being available
try:
    import pyotp
except ImportError:
    pyotp = None
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

AUTH_UNKNOWN = "Unknown"
AUTH_OPENID_V2 = "OpenID 2.0"
AUTH_OPENID_CONNECT = "OpenID Connect"


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
        print("ERROR: Browser _NOT_ supported: %s" % browser)
        driver = None
    # Add a little slack for pages to load when finding elems
    if driver:
        driver.implicitly_wait(5)
    return driver


def scroll_to_elem(driver, elem):
    """Scroll elem into view"""
    action_chains = ActionChains(driver)
    # NOTE: move_to_element fails if outside viewport - try this workaround
    # action_chains.move_to_element(elem).perform()
    elem.send_keys(Keys.ARROW_DOWN)


def select_item_by_index(driver, elem, index):
    """Pick item with index in elem select drop-down"""
    select_box = Select(elem)
    select_box.select_by_index(index)


def doubleclick_elem(driver, elem):
    """Trigger a double-click on elem"""
    action_chains = ActionChains(driver)
    action_chains.double_click(elem).perform()


def save_screen(driver, path):
    """Save a screenshot of current page in path"""
    driver.save_screenshot(path)


def ucph_login(driver, url, login, passwd, callbacks={}):
    """Login through the UCPH OpenID 2.0 or Connect web form and optionally
    execute any provided callbacks for ready and filled states. The callbacks
    dictionary should contain state names bound to functions accepting driver
    and state name like do_stuff(driver, state) .
    """
    status = True
    do_login = False
    auth_flavor = AUTH_UNKNOWN
    try:
        elem = driver.find_element_by_class_name('form-signin')
        action = elem.get_property('action')
        if action in ["https://openid.ku.dk/processTrustResult",
                      "https://t-openid.ku.dk/processTrustResult"]:
            do_login = True
            auth_flavor = AUTH_OPENID_V2
            state = 'login-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
        elif action in ["https://id.ku.dk/nidp/app/login?sid=0&sid=0",
                        "https://t-id.ku.dk/nidp/app/login?sid=0&sid=0"]:
            do_login = True
            auth_flavor = AUTH_OPENID_CONNECT
            state = 'login-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
    except Exception as exc:
        print("ERROR: failed in UCPH login: %s" % exc)

    if do_login:
        print("Starting UCPH %s login" % auth_flavor)
        if auth_flavor == AUTH_OPENID_V2:
            login_elem = driver.find_element_by_name("user")
            pass_elem = driver.find_element_by_name("pwd")
        elif auth_flavor == AUTH_OPENID_CONNECT:
            login_elem = driver.find_element_by_id("inputUsername")
            pass_elem = driver.find_element_by_id("inputPassword")
        else:
            # Fall back to sane defaults
            login_elem = driver.find_element_by_name("username")
            pass_elem = driver.find_element_by_name("password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        if auth_flavor == AUTH_OPENID_V2:
            driver.find_element_by_name("allow").click()
        else:
            # Just mimic Enter key on password field to submit
            pass_elem.submit()
        # Check for login error msg to return proper status
        try:
            error_elem = driver.find_element_by_class_name("alert")
            if error_elem:
                print("UCPH %s login error: %s" %
                      (auth_flavor, error_elem.text))
                status = False
        except Exception:
            pass
    else:
        status = False
        print("UCPH %s login _NOT_ found" % auth_flavor)

    print("UCPH %s login result: %s" % (auth_flavor, status))
    return status


def mig_login(driver, url, login, passwd, callbacks={}):
    """Login through the MiG OpenID 2.0 web form and optionally execute any
    provided callbacks for ready and filled states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    """
    status = True
    do_login = False
    auth_flavor = AUTH_UNKNOWN
    try:
        elem = driver.find_element_by_class_name('openidlogin')
        form = elem.find_element_by_xpath("//form")
        action = form.get_property('action')
        if action == "%s/openid/allow" % url:
            do_login = True
            auth_flavor = AUTH_OPENID_V2
            state = 'login-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
    except Exception as exc:
        print("ERROR: failed in MiG login: %s" % exc)

    if do_login:
        print("Starting MiG %s login" % auth_flavor)
        if auth_flavor == AUTH_OPENID_V2:
            login_elem = driver.find_element_by_name("identifier")
            pass_elem = driver.find_element_by_name("password")
        else:
            login_elem = driver.find_element_by_name("username")
            pass_elem = driver.find_element_by_name("password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        if auth_flavor == AUTH_OPENID_V2:
            driver.find_element_by_name("yes").click()
        else:
            # Just mimic Enter key on password field to submit
            pass_elem.submit()
        # Check for login error msg to return proper status
        try:
            error_elem = driver.find_element_by_class_name("errortext")
            if error_elem:
                print("MiG %s login error: %s" %
                      (auth_flavor, error_elem.text))
                status = False
        except Exception:
            pass
    else:
        status = False
        print("MiG %s login _NOT_ found" % auth_flavor)

    print("MiG %s login result: %s" % (auth_flavor, status))
    return status


def shared_twofactor(driver, url, twofactor_key, callbacks={}):
    """Login through the post-OpenID 2FA web form and optionally execute any
    provided callbacks for ready and filled states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    Requires the pyotp module to generate the current TOTP token based on
    the provided base32-encoded twofactor_key.
    """
    status = True
    twofactor_token = None
    try:
        token_elem = driver.find_element_by_class_name('tokeninput')
        if token_elem:
            state = 'twofactor-ready'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
            if pyotp is None:
                raise Exception("2FA form found but no pyotp helper installed")
            twofactor_token = pyotp.TOTP(twofactor_key).now()
    except Exception as exc:
        print("ERROR: failed in UCPH 2FA: %s" % exc)

    if twofactor_token:
        # print "DEBUG: send token %s" % twofactor_token
        token_elem.send_keys(twofactor_token)
        state = 'twofactor-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        driver.find_element_by_class_name("submit").click()
    else:
        status = False
        print("Post-OpenID 2FA _NOT_ found")

    print("2-Factor Auth result: %s" % status)
    return status


def shared_logout(driver, url, login, passwd, callbacks={}):
    """Logout through the shared logout navmenu entry and confirm. Optionally
    execute any provided callbacks for confirm states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    """
    status = True
    do_logout = False
    print("Do logout")
    try:
        link = driver.find_element_by_link_text('Logout')
        # print "DEBUG: found link: %s" % link
        if link:
            # print "DEBUG: use link: %s" % link
            do_logout = True
            state = 'logout-ready'
            if callbacks.get(state, None):
                # print "DEBUG: callback for: %s" % state
                callbacks[state](driver, state)
            # print "DEBUG: click link: %s" % link
            link.click()
    except Exception as exc:
        print("ERROR: failed in logout: %s" % exc)

    if do_logout:
        print("Confirm logout")
        confirm_elem = driver.find_element_by_link_text("Yes")
        # print "DEBUG: found confirm elem: %s" % confirm_elem
        state = 'logout-confirm'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        # print "DEBUG: click confirm elem: %s" % confirm_elem
        confirm_elem.click()
    else:
        status = False
        print("Confirm login _NOT_ found")

    print("Finished logout: %s" % status)
    return status
