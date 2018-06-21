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
import os
import sys
import time
import traceback

from migcore import init_driver, ucph_login, mig_login, shared_logout, \
    save_screen


def user_actions(driver, url, callbacks={}):
    """Actually run the actions documented in the user guide and create
    screenshots accordingly. Optionally execute any provided callbacks for
    ready and filled states. The callbacks dictionary should contain state
    names bound to functions accepting driver and state name like
    do_stuff(driver, state) .
    """
    status = True
    print "DEBUG: run user actions with url: %s" % url
    try:
        driver.get(url)

        navmenu = driver.find_element_by_class_name('navmenu')
        print "DEBUG: found navmenu: %s" % navmenu

        # TODO: Files

        # TODO: Workgroups

        # Archives
        link = navmenu.find_element_by_link_text('Archives')
        print "DEBUG: found archives link: %s" % link
        state = 'archives-button'
        if callbacks.get(state, None):
            print "DEBUG: callback for: %s" % state
            callbacks[state](driver, state)
        print "DEBUG: click link: %s" % link
        state = 'open-archives'
        if callbacks.get(state, None):
            print "DEBUG: callback for: %s" % state
            callbacks[state](driver, state)
        link.click()
        ajax_status = driver.find_element_by_id('ajax_status')
        print "DEBUG: found ajax_status: %s" % ajax_status
        # Wait for ajax to start and finish - spinner must come and go
        ajax_started, ajax_done = False, False
        while not ajax_done:
            try:
                driver.find_element_by_class_name('spinner')
                print "DEBUG: detected ajax started"
                ajax_started = True
            except Exception, exc:
                print "DEBUG: exception during ajax wait: %s" % exc
                if ajax_started:
                    print "DEBUG: detected ajax done"
                    ajax_done = True
            print "DEBUG: waiting for ajax to finish: %s" % ajax_status
            time.sleep(1)
        state = 'archives-ready'
        if callbacks.get(state, None):
            print "DEBUG: callback for: %s" % state
            callbacks[state](driver, state)

        create_link = driver.find_element_by_link_text(
            'Create a new freeze archive')
        print "DEBUG: found create archives link: %s" % create_link
        create_link.click()

        name_field = driver.find_element_by_name("freeze_name")
        name_field.send_keys("my-sample-archive")

        meta_field = driver.find_element_by_name("freeze_description")
        meta_field.send_keys("""Sample Archive

This is my sample freeze archive with some metadata describing the archive
contents and some files inserted.

Apart from this free text description archives also get a few fields like date
and owner automatically assigned.
""")
        state = 'create-archive'
        if callbacks.get(state, None):
            print "DEBUG: callback for: %s" % state
            callbacks[state](driver, state)

        # TODO: Settings

        # TODO: Schedule Tasks

    except Exception, exc:
        print "ERROR: failed in user actions: %s" % exc

    print "DEBUG: return: %s" % status
    return status


def main():
    """Main"""
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

    # Screenshot helpers
    mig_calls, ucph_calls, action_calls, logout_calls = {}, {}, {}, {}
    base_path = os.path.join('screenshots', browser)
    mig_path = os.path.join(base_path, 'mig-%s.png')
    ucph_path = os.path.join(base_path, 'ucph-%s.png')
    if openid.lower() == 'ucph':
        active_path = ucph_path
    elif openid.lower() == 'mig':
        active_path = mig_path
    else:
        print "No such OpenID handler: %s" % openid
        syst.exit(1)

    try:
        os.makedirs(base_path)
    except:
        # probably already there
        pass
    for name in ('login-ready', 'login-filled'):
        mig_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)
        ucph_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)

    for name in ('archives-ready', 'create-archive', 'view-archive'):
        action_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)

    for name in ('logout-ready'):
        logout_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)

    driver = init_driver(browser)
    # Make sure the screenshots have a suitable size
    driver.set_window_size(1400, 900)
    try:
        driver.get(url)
        if openid.lower() == 'ucph':
            status = ucph_login(driver, url, login, passwd, ucph_calls)
        elif openid.lower() == 'mig':
            status = mig_login(driver, url, login, passwd, mig_calls)
        else:
            print "No such OpenID handler: %s" % openid
            status = False
        if not status:
            print "%s OpenID login FAILED!" % openid
            return 1

        # Now proceed with actual actions to document in turn
        print "Run user guide actions"
        status = user_actions(driver, url, action_calls)
        print "Finished user guide actions"

        print "Proceed as you wish while logged in or request stop in console"
        while raw_input('action: ') not in ['quit', 'exit', 'stop']:
            time.sleep(1)

        print "Log out before exit"
        status = shared_logout(driver, url, logout_calls)

        print "Now you can proceed using the browser or interrupt with Ctrl-C"
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print "User interrupt requested - shutting down"
    except Exception as exc:
        print "Unexpected exception: %s" % exc
        print traceback.format_exc()


if __name__ == "__main__":
    main()
