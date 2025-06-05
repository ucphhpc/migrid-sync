#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migcore - a library of core selenium-based web helpers
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
from builtins import range
try:
    import pyotp
except ImportError:
    pyotp = None
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
try:
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from webdriver_manager.firefox import GeckoDriverManager
except ImportError:
    FirefoxService = None
    GeckoDriverManager = None


AUTH_UNKNOWN = "Unknown"
AUTH_OPENID_V2 = "OpenID 2.0"
AUTH_OPENID_CONNECT = "OpenID Connect"

NAVMENU_ID = "sideBar"
USERMENU_ID = "userMenu"
USERMENUBUTTON_ID = "userMenuButton"


def init_driver(browser):
    """Init the requested browser driver"""
    if browser.lower() in ['chrome', 'chromium']:
        driver = webdriver.Chrome()
    elif browser.lower() == 'firefox':
        driver = webdriver.Firefox()
    elif browser.lower() == 'firefox-auto':
        if FirefoxService is None or GeckoDriverManager is None:
            print("""FATAL: FirefoxService and GeckoDriverManager are required
for the automatic firefox installer mode.
""")
            exit(1)
        webdriver_service = FirefoxService(GeckoDriverManager().install())
        webdriver_service.start()
        options = webdriver.FirefoxOptions()
        profile = webdriver.FirefoxProfile()
        driver = webdriver.Remote(webdriver_service.service_url,
                                  options=options,
                                  browser_profile=profile)
    elif browser.lower() == 'safari':
        driver = webdriver.Safari()
    elif browser.lower() == 'ie':
        driver = webdriver.Ie()
    elif browser.lower() == 'edge':
        driver = webdriver.Edge()
    elif browser.lower() == 'phantomjs':
        driver = webdriver.PhantomJS()
    else:
        print("ERROR: Browser NOT supported: %s" % browser)
        driver = None
    # Add a little slack for pages to load when finding elems
    if driver:
        driver.implicitly_wait(5)
    return driver


def by_what(name):
    """Helper to expose the new By.X helper without the mechanics"""
    return getattr(By, name.upper())


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
        elem = driver.find_element(by_what('class_name'), 'form-signin')
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
            login_elem = driver.find_element(by_what('name'), "user")
            pass_elem = driver.find_element(by_what('name'), "pwd")
        elif auth_flavor == AUTH_OPENID_CONNECT:
            login_elem = driver.find_element(by_what('id'), "inputUsername")
            pass_elem = driver.find_element(by_what('id'), "inputPassword")
        else:
            # Fall back to sane defaults
            login_elem = driver.find_element(by_what('name'), "username")
            pass_elem = driver.find_element(by_what('name'), "password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        if auth_flavor == AUTH_OPENID_V2:
            driver.find_element(by_what('name'), "allow").click()
        else:
            # Just mimic Enter key on password field to submit
            pass_elem.submit()
        # Check for login error msg to return proper status
        # NOTE: the standard request source footer is also of class alert
        #       so be specific here to avoid slow page load confusion
        try:
            error_elem = driver.find_element(by_what('class_name'),
                                             "alert-warning")
            if error_elem:
                print("UCPH %s login error: %s" %
                      (auth_flavor, error_elem.text))
                status = False
        except Exception:
            pass
    else:
        status = False
        print("UCPH %s login NOT found" % auth_flavor)

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
        elem = driver.find_element(by_what('class_name'), 'openidlogin')
        form = elem.find_element(by_what('xpath'), "//form")
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
            login_elem = driver.find_element(
                by_what('name'), "identifier")
            pass_elem = driver.find_element(by_what('name'), "password")
        else:
            login_elem = driver.find_element(by_what('name'), "username")
            pass_elem = driver.find_element(by_what('name'), "password")
        login_elem.send_keys(login)
        pass_elem.send_keys(passwd)
        state = 'login-filled'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        if auth_flavor == AUTH_OPENID_V2:
            driver.find_element(by_what('name'), "yes").click()
        else:
            # Just mimic Enter key on password field to submit
            pass_elem.submit()
        # Check for login error msg to return proper status
        try:
            error_elem = driver.find_element(by_what('class_name'),
                                             "errortext")
            if error_elem:
                print("MiG %s login error: %s" %
                      (auth_flavor, error_elem.text))
                status = False
        except Exception:
            pass
    else:
        status = False
        print("MiG %s login NOT found" % auth_flavor)

    print("MiG %s login result: %s" % (auth_flavor, status))
    return status


def shared_twofactor(driver, url, twofactor_key, callbacks={},
                     past_twofactor_class='link-logout'):
    """Login through the post-OpenID 2FA web form and optionally execute any
    provided callbacks for ready and filled states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    Requires the pyotp module to generate the current TOTP token based on
    the provided base32-encoded twofactor_key.
    The optional past_twofactor_class string can be given to skip twofactor
    token entry attempts if an element with that class is found. This is useful
    e.g. when current twofactor requirement is unknown and key is provided.
    """
    status = True
    twofactor_token = None
    past_twofactor = False
    if past_twofactor_class:
        try:
            driver.find_element(by_what('class_name'), past_twofactor_class)
            # print("DEBUG: found %s element - past twofactor login" %
            #      past_twofactor_class)
            past_twofactor = True
        except Exception as exc:
            #print("DEBUG: not past twofactor login: %s" % exc)
            pass

    if not past_twofactor:
        try:
            token_elem = driver.find_element(
                by_what('class_name'), 'tokeninput')
            if token_elem:
                state = 'twofactor-ready'
                if callbacks.get(state, None):
                    callbacks[state](driver, state)
                if pyotp is None:
                    raise Exception(
                        "2FA form found but no pyotp helper installed")
                twofactor_token = pyotp.TOTP(twofactor_key).now()
        except Exception as exc:
            print("ERROR: failed in UCPH 2FA: %s" % exc)

        if twofactor_token:
            # print "DEBUG: send token %s" % twofactor_token
            token_elem.send_keys(twofactor_token)
            state = 'twofactor-filled'
            if callbacks.get(state, None):
                callbacks[state](driver, state)
            driver.find_element(by_what('class_name'), "submit").click()
        else:
            status = False
            print("Post-OpenID 2FA NOT found")

    print("2-Factor Auth result: %s" % status)
    return status


def get_nav_link(driver, url, nav_class):
    """Find nav link in UI V3 or V2 structure"""
    link, menu = None, None
    for i in range(3):
        try:
            menu = driver.find_element(by_what('id'), NAVMENU_ID)
            link = menu.find_element(by_what('class_name'), nav_class)
            break
        except:
            link = None

    if link:
        return link

    try:
        menu = driver.find_element(by_what('id'), USERMENU_ID)
        link = menu.find_element(by_what('class_name'), nav_class)
        menubutton = driver.find_element(by_what('id'), USERMENUBUTTON_ID)
        # Make sure menu link item is visible for callee
        if menu and link and menubutton:
            menubutton.click()
    except:
        link = None

    return link


def shared_logout(driver, url, double_confirm, login, passwd, callbacks={}):
    """Logout through the shared logout navmenu entry and confirm. Optionally
    execute any provided callbacks for confirm states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    The double_confirm arg specifies if one or two confirm steps are needed.
    """
    status = True
    do_logout = False
    nav_class = "link-logout"
    print("Do logout")
    try:
        link = get_nav_link(driver, url, nav_class)
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
        confirm_elem = driver.find_element(by_what('link_text'), 'Yes')
        # print("DEBUG: found confirm elem: %s" % confirm_elem)
        state = 'logout-confirm'
        if callbacks.get(state, None):
            callbacks[state](driver, state)
        # print("DEBUG: click confirm elem: %s" % confirm_elem)
        confirm_elem.click()
        # Upstream OID(C) may have additional logout step
        if double_confirm:
            print("Confirm logout again")
            try:
                confirm_elem = driver.find_element(by_what('xpath'),
                                                   "//button[@value='Yes']")
                # print("DEBUG: found confirm elem: %s" % confirm_elem)
                state = 'logout-confirm-upstream'
                if callbacks.get(state, None):
                    callbacks[state](driver, state)
                # print("DEBUG: click confirm elem: %s" % confirm_elem)
                confirm_elem.click()
            except Exception as exc:
                print("WARNING: failed in secondary logout: %s" % exc)
    else:
        status = False
        print("Confirm login NOT found")

    print("Finished logout: %s" % status)
    return status


def mig_logout(driver, url, login, passwd, callbacks={}):
    """Logout through the shared logout navmenu entry and confirm once. Optionally
    execute any provided callbacks for confirm states. The callbacks dictionary
    should contain state names bound to functions accepting driver and state
    name like do_stuff(driver, state) .
    """
    return shared_logout(driver, url, False, login, passwd, callbacks)


def ucph_logout(driver, url, login, passwd, callbacks={}):
    """Logout through the shared logout navmenu entry and try to confirm twice.
    Optionally execute any provided callbacks for confirm states. The callbacks
    dictionary should contain state names bound to functions accepting driver
    and state name like do_stuff(driver, state) .
    """
    return shared_logout(driver, url, True, login, passwd, callbacks)
