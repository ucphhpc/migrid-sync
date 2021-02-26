#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userguidescreens - selenium-based web client to grab user guide screenshots
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
from __future__ import print_function

import getpass
import os
import sys
import time
import traceback
from urlparse import urlparse

from migcore import init_driver, ucph_login, mig_login, shared_twofactor, \
    shared_logout, save_screen, scroll_to_elem, doubleclick_elem, \
    select_item_by_index, get_nav_link

# Which Setup sections to include on SIF (where 2FA is moved to gdpman)
setup_sections = [('sftp', 'SFTP'), ('webdavs', 'WebDAVS')]
# Additional setup sections on non-SIF hosts
extra_setup_sections = [('ftps', 'FTPS'), ('twofactor', '2-Factor Auth'),
                        ('duplicati', 'Duplicati'), ('seafile', 'Seafile')]


def ajax_wait(driver, name, class_name="spinner"):
    """Wait for AJAX request to finish"""
    # Wait for ajax to start and finish - spinner must come and go
    ajax_started, ajax_done = False, False
    while not ajax_done:
        try:
            driver.find_element_by_class_name(class_name)
            if not ajax_started:
                # print "DEBUG: detected ajax started"
                ajax_started = True
                continue
        except Exception as exc:
            if ajax_started:
                # print "DEBUG: detected ajax done"
                break
            else:
                print("Warning: exception during ajax wait: %s" % exc)
        print("DEBUG: waiting for ajax to finish: %s" % name)
        time.sleep(1)
    return True


def management_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    # Go through all manager tabs in turn
    manage_tabs = ["Open Project",
                   "Project Info",
                   "Create Project",
                   "Invite Participant",
                   "Accept Invitation",
                   "Remove Participant",
                   "Await Invitation",
                   "Two-Factor Auth"]
    sample_category = "personal_data"
    sample_workzone = "123-4567/00-1234",
    sample_project = "X-Ray_Tissue_Scans"
    sample_int_part = "vinter@nbi.ku.dk"
    sample_ext_part = "bardino@migrid.org"
    for nav_name in manage_tabs:
        navmenu = driver.find_element_by_id('project-tabs')
        # Try to find manage tab (availability depends on state and role)
        try:
            link = navmenu.find_element_by_link_text(nav_name)
        except Exception as exc:
            print("Warning: no %r tab found - might be okay" % nav_name)
            continue
        # print "DEBUG: found %s link: %s" % (nav_name, link)
        link.click()
        # ajax_wait(driver, nav_name, "ui-progressbar")
        state = '%s-ready' % nav_name.lower().replace(' ', '-')
        if callbacks.get(state, None):
            print("INFO: callback for: %s" % state)
            callbacks[state](driver, state)

    # Additional concrete project manipulation unless on SIF
    if not url.startswith('https://sif'):
        # Go to Create project tab and create a project
        nav_name = "Create Project"
        try:
            navmenu = driver.find_element_by_id('project-tabs')
            link = navmenu.find_element_by_link_text(nav_name)
            # print "DEBUG: found %s link: %s" % (nav_name, link)
            link.click()
            # ajax_wait(driver, nav_name, "ui-progressbar")
            # NOTE: locate the relevant workzone in category ref section
            active_tab = driver.find_element_by_id('create_project_tab')
            # NOTE: project name field is shared for all categories
            workzone_entry = active_tab.find_element_by_id(
                'create_project_%s_workzone_id' % sample_category)
            workzone_entry.send_keys(sample_workzone)
            proj_entry = active_tab.find_element_by_name(
                'create_project_base_vgrid_name')
            proj_entry.send_keys(sample_project)
            state = '%s-filled' % nav_name.lower().replace(' ', '-')
            if callbacks.get(state, None):
                print("INFO: callback for: %s" % state)
                callbacks[state](driver, state)

            create_button = active_tab.find_element_by_id(
                'create_project_button')
            # TODO: actually submit form to create project?
            # create_button.click()
        except Exception as exc:
            print("Warning: could not test %r tab: %s" % (nav_name, exc))

        # Go to Invite project tab and invite a colleague to project
        nav_name = "Invite Participant"
        try:
            navmenu = driver.find_element_by_id('project-tabs')
            link = navmenu.find_element_by_link_text(nav_name)
            # print "DEBUG: found %s link: %s" % (nav_name, link)
            link.click()
            # ajax_wait(driver, nav_name, "ui-progressbar")
            active_tab = driver.find_element_by_id('invite_user_tab')
            dropdown_container = active_tab.find_element_by_class_name(
                'gm_select')
            proj_dropdown = navmenu.find_element_by_name(
                'invite_user_base_vgrid_name')
            # NOTE: we expect first real project to match sample category
            select_item_by_index(driver, proj_dropdown, 2)
            # ajax_wait(driver, nav_name, "ui-progressbar")
            active_tab = driver.find_element_by_id('invite_user_tab')
            terms_checkbox = active_tab.find_element_by_id(
                'invite_user_%s_user_terms' % sample_category)
            terms_checkbox.click()
            workzone_entry = active_tab.find_element_by_id(
                'invite_user_%s_workzone_id' % sample_category)
            # NOTE: user id field is shared for all categories
            invite_entry = active_tab.find_element_by_name(
                'invite_user_short_id')
            for (label, email) in [('int', sample_int_part),
                                   ('ext', sample_ext_part)]:
                invite_entry.clear()
                invite_entry.send_keys(email)
                workzone_entry.clear()
                workzone_entry.send_keys(sample_workzone)
                state = '%s-%s-filled' % (
                    nav_name.lower().replace(' ', '-'), label)
                if callbacks.get(state, None):
                    print("INFO: callback for: %s" % state)
                    callbacks[state](driver, state)

                invite_button = active_tab.find_element_by_id(
                    'invite_user_button')
                # TODO: actually submit form to invite to project?
                # invite_button.click()
        except Exception as exc:
            print("Warning: could not test %r tab: %s" % (nav_name, exc))


def open_project_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    # Go to open project tab and open first project
    nav_name = "Open Project"
    navmenu = driver.find_element_by_id('project-tabs')
    link = navmenu.find_element_by_link_text(nav_name)
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name, "ui-progressbar")
    dropdown_container = navmenu.find_element_by_class_name('gm_select')
    proj_dropdown = navmenu.find_element_by_name(
        'access_project_base_vgrid_name')
    select_item_by_index(driver, proj_dropdown, 2)
    link = driver.find_element_by_link_text('Open')
    link.click()
    ajax_wait(driver, nav_name, "ui-progressbar")


def home_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Home"
    nav_class = "link-home"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    ajax_wait(driver, nav_name, "tips-loading")
    state = 'home-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def files_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Files"
    nav_class = "link-files"
    link = get_nav_link(driver, url, nav_class)
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    ajax_wait(driver, nav_name, "ui-progressbar")
    state = 'files-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def workgroups_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Workgroups"
    nav_class = "link-vgrids"
    link = get_nav_link(driver, url, nav_class)
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    ajax_wait(driver, nav_name)
    state = 'workgroups-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def archives_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Archives"
    nav_class = "link-archives"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    ajax_wait(driver, nav_name)
    state = 'archives-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    create_link = driver.find_element_by_link_text(
        'Create a new freeze archive')
    # print "DEBUG: found create archives link: %s" % create_link
    create_link.click()

    state = 'archive-empty'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    archive_name = "Article Data %s" % time.ctime().replace(':', '.')
    name_field = driver.find_element_by_name("freeze_name")
    name_field.send_keys(archive_name)

    meta_field = driver.find_element_by_name("freeze_description")
    meta_field.send_keys("""Article Data Archive

This is my sample freeze archive with some metadata describing the archive
contents and a file inserted from my ERDA home.

Apart from this free text description archives also get a few fields like date
and owner automatically assigned.
""")

    # Open fileman popup
    add_button = driver.find_element_by_id("addfilebutton")
    add_button.click()
    # Wait for fileman popup to accept click handlers
    ajax_wait(driver, nav_name + " file select", "ui-progressbar")
    state = 'archive-fileman'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    # Select first txt file (at least welcome.txt is always there)
    files_area = driver.find_element_by_class_name("fm_files")
    select_file = files_area.find_element_by_class_name("ext_txt")
    # print "DEBUG: scroll to file elem: %s" % select_file
    scroll_to_elem(driver, select_file)

    # TODO: figure out how to get this dclick working
    # NOTE: dclick on same target hits a dir here after scroll!?
    # select_file = files_area.find_element_by_class_name("ext_txt")
    # print "DEBUG: double click file elem: %s" % select_file
    # doubleclick_elem(driver, select_file)

    # NOTE: as a workaround we save path, cancel and manually fill for now
    file_path = select_file.text
    print("DEBUG: found file path: %s" % file_path)
    dialog_buttons = driver.find_element_by_class_name("ui-dialog-buttonset")
    action_buttons = driver.find_elements_by_class_name("ui-button")
    for button in action_buttons:
        if button.text == 'Cancel':
            button.click()
        # else:
        #    print "DEBUG: ignore action button: %s" % button.text
    add_field = driver.find_element_by_id("freeze_copy_0")
    add_field.send_keys(file_path)

    # Choose publish
    publish_yes = driver.find_element_by_name("freeze_publish")
    publish_yes.click()

    time.sleep(1)

    state = 'archive-filled'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    submit_button = driver.find_element_by_xpath(
        "//input[@type='submit' and @value='Save and Preview']")
    print("DEBUG: click submit: %s" % submit_button)
    submit_button.click()

    state = 'archive-submitted'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    # TODO: open preview (in new tab) like this
    # preview_button = driver.find_element_by_class_name("previewarchivelink")
    # print "DEBUG: found preview button: %s" % preview_button
    # preview_button.click()

    finalize_button = driver.find_element_by_class_name(
        "finalizearchivelink")
    print("DEBUG: click finalize button: %s" % finalize_button)
    finalize_button.click()

    dialog_buttons = driver.find_element_by_class_name("ui-dialog-buttonset")
    confirm_buttons = driver.find_elements_by_class_name("ui-button")
    for button in confirm_buttons:
        if button.text == 'Yes':
            button.click()
        # else:
        #    print "DEBUG: ignore confirm button: %s" % button.text

    state = 'archive-finalized'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    view_button = driver.find_element_by_class_name(
        "viewarchivelink")
    print("DEBUG: click view button: %s" % view_button)
    view_button.click()
    ajax_wait(driver, nav_name)
    state = 'archive-view'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    register_button = driver.find_element_by_class_name(
        "registerarchivelink")
    print("DEBUG: click register button: %s" % register_button)
    register_button.click()

    dialog_buttons = driver.find_element_by_class_name("ui-dialog-buttonset")
    confirm_buttons = driver.find_elements_by_class_name("ui-button")
    for button in confirm_buttons:
        if button.text == 'Yes':
            button.click()
        # else:
        #    print "DEBUG: ignore confirm button: %s" % button.text

    # Redirecting to KU-IT DOI service where login may be required
    login_done, popup_found, popup_done = False, False, False
    while True:

        # Maybe need KU-IT DOI service login if requested
        try:
            logon_button = driver.find_element_by_id("cmdLogon")
            print("DEBUG: click logon: %s" % logon_button)
            logon_button.click()
        except Exception as exc:
            pass

        try:
            user_field = driver.find_element_by_id("userNameInput")
            user_field.send_keys(login)
            password_field = driver.find_element_by_id("passwordInput")
            password_field.send_keys(passwd)
            submit_button = driver.find_element_by_id("submitButton")
            print("DEBUG: click submit: %s" % submit_button)
            time.sleep(1)
            submit_button.click()
            login_done = True
        except Exception as exc:
            if not login_done:
                print("Warning: no login form found: %s" % exc)

        time.sleep(1)

        # Then detect and confirm DOI usage dialog
        try:
            popup_dialog = driver.find_element_by_class_name("popupcontent")
            # print "DEBUG: found popup dialog: %s" % popup_dialog
            # Wait for display popup
            for _ in range(10):
                if not popup_dialog.is_displayed():
                    # print "DEBUG: waiting for popup dialog: %s" %
                    # popup_dialog
                    time.sleep(1)
                else:
                    # If still not shown we consider it done
                    popup_done = True
                    break
            # Then find and click accept button
            if popup_dialog.is_displayed():
                print("DEBUG: found visible popup dialog")
                popup_found = True
                popup_buttons = popup_dialog.find_elements_by_class_name("btn")
                for button in popup_buttons:
                    # print "DEBUG: inspect popup button: %s" % button.text
                    if button.text.upper() == 'UNDERSTOOD':
                        button.click()
                        popup_done = True
                    # else:
                    #    print "DEBUG: ignore button: %s" % button.text
            # else:
            #    print "DEBUG: popup dialog invisible"
            if popup_found and not popup_done:
                raise Exception("Warning: no UNDERSTOOD button")
        except Exception as exc:
            # print "DEBUG: popup accept dialog: %s" % exc
            if popup_found:
                print("ERROR: popup accept dialog failed: %s" % exc)
                # Try again since popup WAS found
                time.sleep(1)
                continue

        # Check if DOI form is there and ready
        try:
            doi_idenfier = driver.find_element_by_id("IdentifierType")
            # print "DEBUG: found DOI identifier: %s" % doi_idenfier
            break
        except Exception as exc:
            print("DEBUG: DOI page not ready: %s" % exc)

        # Keep trying until we get through login and usage accept
        print("INFO: waiting for access to DOI service")
        time.sleep(1)

    time.sleep(1)

    state = 'archive-register'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    time.sleep(1)
    # Return to our own main page to continue
    driver.get(url)


def settings_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Settings"
    nav_class = "link-settings"
    link = get_nav_link(driver, url, nav_class)
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'settings-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def setup_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Setup"
    nav_class = "link-setup"
    link = get_nav_link(driver, url, nav_class)
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'setup-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)

    for (key, name) in setup_sections:
        # Search inside page content to avoid Seafile nav menu interference
        content_anchor = driver.find_element_by_id("content")
        sub_link = content_anchor.find_element_by_link_text(name)
        sub_link = driver.find_element_by_id(
            "content").find_element_by_link_text(name)
        # print "DEBUG: found webdaws link: %s" % webdaws
        sub_link.click()
        # Wait for Seafile server status lookup
        if key == 'seafile':
            ajax_wait(driver, nav_name)

        state = 'setup-%s-ready' % key
        if callbacks.get(state, None):
            print("INFO: callback for: %s" % state)
            callbacks[state](driver, state)


def jupyter_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Jupyter"
    nav_class = "link-jupyter"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'jupyter-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def cloud_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Cloud"
    nav_class = "link-cloud"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'cloud-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def people_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "People"
    nav_class = "link-people"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    ajax_wait(driver, nav_name)
    state = 'people-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def peers_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Peers"
    nav_class = "link-peers"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    #ajax_wait(driver, nav_name)
    state = 'peers-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def crontab_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Schedule Tasks"
    nav_class = "link-crontab"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'crontab-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def datatransfer_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Data Transfers"
    nav_class = "link-transfers"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'datatransfer-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def sharelink_actions(driver, url, login, passwd, callbacks):
    """Run user actions for section of same name"""
    nav_name = "Share Links"
    nav_class = "link-sharelinks"
    try:
        link = get_nav_link(driver, url, nav_class)
    except:
        print("INFO: no %r link found, probably not enabled" % nav_name)
        return
    # print "DEBUG: found %s link: %s" % (nav_name, link)
    link.click()
    # ajax_wait(driver, nav_name)
    state = 'sharelink-ready'
    if callbacks.get(state, None):
        print("INFO: callback for: %s" % state)
        callbacks[state](driver, state)


def user_actions(driver, url, login, passwd, sections, callbacks={}):
    """Actually run the actions documented in the user guide and create
    screenshots accordingly. Optionally execute any provided callbacks for
    ready and filled states. The callbacks dictionary should contain state
    names bound to functions accepting driver and state name like
    do_stuff(driver, state) .
    """
    status = True
    print("INFO: run user actions with url: %s" % url)
    for name, actions in sections:
        try:
            actions(driver, url, login, passwd, callbacks)
        except Exception as exc:
            print("ERROR: failed in user actions: %s" % exc)
            status = False

    # print "DEBUG: return: %s" % status
    return status


def main():
    """Main"""
    argc = len(sys.argv) - 1
    if argc < 4:
        print(
            "USAGE: %s browser url openid login [password] [2FAkey]" % sys.argv[0])
        return 1

    reopen_stdin = False
    browser = sys.argv[1]
    url = sys.argv[2]
    openid = sys.argv[3]
    login = sys.argv[4]
    if argc > 4:
        if sys.argv[5] == '-':
            passwd = sys.stdin.readline().strip()
            reopen_stdin = True
        else:
            passwd = sys.argv[5]
    else:
        passwd = getpass.getpass()
    if argc > 5:
        if sys.argv[6] == '-':
            twofactor_key = sys.stdin.readline().strip()
            reopen_stdin = True
        else:
            twofactor_key = sys.argv[6]
    else:
        twofactor_key = getpass.getpass("2FA *key*: ")

    if reopen_stdin:
        sys.stdin = open('/dev/tty')

    # Screenshot helpers
    mig_calls, ucph_calls, action_calls, logout_calls = {}, {}, {}, {}
    sys_prefix = urlparse(url).netloc.split('.', 1)[0]
    base_path = os.path.join('screenshots', browser)
    mig_path = os.path.join(base_path, 'mig-' + sys_prefix + '_%s.png')
    ucph_path = os.path.join(base_path, 'ucph-' + sys_prefix + '_%s.png')
    if openid.lower() == 'ucph':
        active_path = ucph_path
    elif openid.lower() == 'mig':
        active_path = mig_path
    else:
        print("No such OpenID handler: %s" % openid)
        sys.exit(1)

    try:
        os.makedirs(base_path)
    except:
        # probably already there
        pass

    if url.find('sif') != -1:
        active_setup_sections = [] + setup_sections
        all_sections = [
            ('Management', management_actions),
            ('Open Project', open_project_actions),
            ('Files', files_actions),
            ('Setup', setup_actions)
        ]
    else:

        # TODO: add more (sub-)sections ?

        # Enable additional setup sections on non-SIF hosts
        active_setup_sections = setup_sections + extra_setup_sections

        all_sections = [
            ('Home', home_actions),
            ('Files', files_actions),
            ('Workgroups', workgroups_actions),
            #('Archives', archives_actions),
            ('Settings', settings_actions),
            ('Setup', setup_actions),
            ('Jupyter', jupyter_actions),
            ('Cloud', cloud_actions),
            ('People', people_actions),
            ('Peers', peers_actions),
            ('Schedule Tasks', crontab_actions),
            ('Share Links', sharelink_actions),
            ('Data Transfers', datatransfer_actions),
        ]

    for name in ('login-ready', 'login-filled'):
        mig_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)
        ucph_calls[name] = lambda driver, name: save_screen(
            driver, active_path % name)

    callback_targets = ['home-ready', 'twofactor-ready', 'twofactor-filled',
                        'files-ready', 'workgroups-ready', 'archives-ready',
                        'archive-empty', 'archive-fileman', 'archive-filled',
                        'archive-submitted', 'archive-finalized', 'archive-view',
                        'archive-register', 'settings-ready', 'setup-ready']
    callback_targets += ['setup-%s-ready' %
                         sub for (sub, _) in active_setup_sections]
    callback_targets += ['jupyter-ready', 'cloud-ready', 'people-ready',
                         'peers-ready', 'crontab-ready', 'datatransfer-ready',
                         'sharelink-ready']
    callback_targets += ['open-project-ready', 'project-info-ready',
                         'create-project-ready', 'create-project-filled',
                         'invite-participant-ready',
                         'invite-participant-int-filled',
                         'invite-participant-ext-filled',
                         'accept-invitation-ready',
                         'remove-participant-ready',
                         'await-invitation',
                         'two-factor-auth-ready']
    for name in callback_targets:
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
            print("No such OpenID handler: %s" % openid)
            status = False
        if not status:
            print("%s OpenID login FAILED!" % openid)
            return 1

        if twofactor_key:
            status = shared_twofactor(driver, url, twofactor_key, action_calls)
        if not status:
            print("2FA after %s OpenID login FAILED!" % openid)
            return 2

        # Now proceed with actual actions to document in turn

        section_names = [name for (name, _) in all_sections]
        print("Run user guide actions for: %s" % ', '.join(section_names))
        status = user_actions(driver, url, login, passwd,
                              all_sections, action_calls)
        print("Finished user guide actions")

        print("Proceed as you wish while logged in or request stop in console")
        action = None
        stop_actions = ['quit', 'exit', 'stop']
        while action not in stop_actions:
            action = raw_input('action: ')
            # Prevent IndexError
            action_args = action.split()[1:]
            if action.startswith('save'):
                if not action_args:
                    print("You need to provide a file name argument for save")
                    continue
                save_screen(driver, active_path % action_args[0])
            elif action not in stop_actions:
                print("Unknown action: %r" % action)
            else:
                time.sleep(1)

        print("Log out before exit")
        status = shared_logout(driver, url, login, passwd, logout_calls)

        print("Now you can proceed using the browser or interrupt with Ctrl-C")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("User interrupt requested - shutting down")
    except Exception as exc:
        print("Unexpected exception: %s" % exc)
        print(traceback.format_exc())

    # Needed to clean up e.g. rust_mozprofile.* tmp dirs
    try:
        driver.quit()
    except Exception as exc:
        print("Unexpected exception in quit: %s" % exc)


if __name__ == "__main__":
    main()
