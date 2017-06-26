#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# expand - emulate shell wild card expansion
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Script to provide users with a means of expanding patterns to files and
directories in their home directories. This script tries to mimic basic shell
wild card expansion.
"""

import os
import glob
from urllib import quote

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, invisible_path
from shared.functional import validate_input
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import all, long_list, recursive
from shared.sharelinks import extract_mode_id
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""
    defaults = {'flags': [''], 'path': ['.'], 'share_id': [''],
                'current_dir': ['.'],'with_dest': ['false']}
    return ['dir_listings', defaults]


def handle_file(
    configuration,
    listing,
    filename,
    file_with_dir,
    actual_file,
    flags='',
    dest='',
    show_dest=False,
    ):
    """handle a file"""

    # Build entire line before printing to avoid newlines

    # Recursion can get here when called without explicit invisible files
    
    if invisible_path(file_with_dir):
        return
    file_obj = {
        'object_type': 'direntry',
        'type': 'file',
        'name': filename,
        'rel_path': file_with_dir,
        'rel_path_enc': quote(file_with_dir),
        'rel_dir_enc': quote(os.path.dirname(file_with_dir)),
        # NOTE: file_with_dir is kept for backwards compliance
        'file_with_dir': file_with_dir,
        'flags': flags,
        }

    if show_dest:
        file_obj['file_dest'] = dest

    listing.append(file_obj)


def handle_expand(
    configuration,
    output_objects,
    listing,
    base_dir,
    real_path,
    flags='',
    dest='',
    depth=0,
    show_dest=False,
    ):
    """Recursive function to expand paths in a way not unlike ls, but only
    files are interesting in this context. The order of recursively expanded
    paths is different from that in ls since it simplifies the code and
    doesn't really matter to the clients.
    """

    # Sanity check

    if depth > 255:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error: file recursion maximum exceeded!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # references to '.' or similar are stripped by abspath

    if real_path + os.sep == base_dir:
        base_name = relative_path = '.'
    else:
        base_name = os.path.basename(real_path)
        relative_path = real_path.replace(base_dir, '')

    # Recursion can get here when called without explicit invisible files
    
    if invisible_path(relative_path):
        return

    if os.path.isfile(real_path):
        handle_file(configuration, listing, relative_path, relative_path,
                    real_path, flags, dest, show_dest)
    else:
        try:
            contents = os.listdir(real_path)
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Failed to list contents of %s: %s'
                                   % (base_name, exc)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # Filter out dot files unless '-a' is used

        if not all(flags):
            contents = [i for i in contents if not i.startswith('.')]
        contents.sort()

        if not recursive(flags) or depth < 0:

            for name in contents:
                path = real_path + os.sep + name
                rel_path = path.replace(base_dir, '')
                if os.path.isfile(path):
                    handle_file(configuration, listing, rel_path, rel_path,
                                path, flags, 
                                os.path.join(dest, os.path.basename(rel_path)),
                                show_dest)
        else:

            # Force pure content listing first by passing a negative depth

            handle_expand(
                configuration,
                output_objects,
                listing,
                base_dir,
                real_path,
                flags,
                dest,
                -1,
                show_dest,
                )

            for name in contents:
                path = real_path + os.sep + name
                rel_path = path.replace(base_dir, '')
                if os.path.isdir(path):
                    handle_expand(
                        configuration,
                        output_objects,
                        listing,
                        base_dir,
                        path,
                        flags,
                        os.path.join(dest, name),
                        depth + 1,
                        show_dest,
                        )


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    pattern_list = accepted['path']
    current_dir = accepted['current_dir'][-1].lstrip('/')
    share_id = accepted['share_id'][-1]
    show_dest = accepted['with_dest'][0].lower() == 'true'

    status = returnvalues.OK

    # NOTE: in contrast to 'ls' we never include write operations here
    read_mode, write_mode = True, False
    visibility_mods = '''
            #%(main_id)s .enable_write { display: none; }
            #%(main_id)s .disable_read { display: none; }
            #%(main_id)s .if_full { display: none; }
    '''
    # Either authenticated user client_id set or sharelink ID
    if client_id:
        user_id = client_id
        target_dir = client_id_dir(client_id)
        base_dir = configuration.user_home
        redirect_name = configuration.site_user_redirect
        redirect_path = redirect_name
        id_args = ''
        root_link_name = 'USER HOME'
        main_id = "user_expand"
        page_title = 'User Files - Path Expansion'
    elif share_id:
        (share_mode, _) = extract_mode_id(configuration, share_id)
        # TODO: load and check sharelink pickle (currently requires client_id)
        # then include shared by %(owner)s on page header
        user_id = 'anonymous user through share ID %s' % share_id
        target_dir = os.path.join(share_mode, share_id)
        base_dir = configuration.sharelink_home
        redirect_name = 'share_redirect'
        redirect_path = os.path.join(redirect_name, share_id)
        id_args = 'share_id=%s;' % share_id
        root_link_name = '%s' % share_id
        main_id = "sharelink_expand"
        page_title = 'Shared Files - Path Expansion'
    else:
        logger.error('%s called without proper auth: %s' % (op_name, accepted))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Authentication is missing!'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)
            
    visibility_toggle = '''
        <style>
        %s
        </style>
        ''' % (visibility_mods % {'main_id': main_id})
    
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(base_dir, target_dir)) + os.sep

    if not os.path.isdir(base_dir):
        logger.error('%s called on missing base_dir: %s' % (op_name, base_dir))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No such %s!' % page_title.lower()
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = page_title

    fill_helpers = {'dest_dir': current_dir + os.sep, 'share_id': share_id,
                   'flags': flags, 'tmp_flags': flags, 'long_set':
                   long_list(flags), 'recursive_set': recursive(flags),
                   'all_set': all(flags)}
    styles = themed_styles(configuration)
    styles['advanced'] += '''
    %s
    ''' % visibility_toggle
    title_entry['style'] = styles
    title_entry['javascript'] = jquery_ui_js(configuration, '', '', '')
    title_entry['bodyfunctions'] += ' id="%s"' % main_id
    output_objects.append({'object_type': 'header', 'text': page_title})

    # Shared URL helpers 
    ls_url_template = 'ls.py?%scurrent_dir=%%(rel_dir_enc)s;flags=%s' % \
                      (id_args, flags)
    redirect_url_template = '/%s/%%(rel_path_enc)s' % redirect_path

    location_pre_html = """
<div class='files'>
<table class='files'>
<tr class=title><td class=centertext>
Working directory:
</td></tr>
<tr><td class='centertext'>
"""
    output_objects.append({'object_type': 'html_form', 'text'
                          : location_pre_html})
    # Use current_dir nav location links
    for pattern in pattern_list[:1]:
        links = []
        links.append({'object_type': 'link', 'text': root_link_name,
                      'destination': ls_url_template % {'rel_dir_enc': '.'}})
        prefix = ''
        parts = os.path.normpath(current_dir).split(os.sep)
        for i in parts:
            if i == ".":
                continue
            prefix = os.path.join(prefix, i)
            links.append({'object_type': 'link', 'text': i,
                         'destination': ls_url_template % \
                          {'rel_dir_enc': quote(prefix)}})
        output_objects.append({'object_type': 'multilinkline', 'links'
                              : links, 'sep': ' %s ' % os.sep})
    location_post_html = """
</td></tr>
</table>
</div>
<br />
"""

    output_objects.append({'object_type': 'html_form', 'text'
                          : location_post_html})

    dir_listings = []
    output_objects.append({
        'object_type': 'dir_listings',
        'dir_listings': dir_listings,
        'flags': flags,
        'redirect_name': redirect_name,
        'redirect_path': redirect_path,
        'share_id': share_id,
        'ls_url_template': ls_url_template,
        'rm_url_template': '',
        'rmdir_url_template': '',
        'editor_url_template': '',
        'redirect_url_template': redirect_url_template,
        'show_dest': show_dest,
        })

    first_match = None
    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        current_path = os.path.normpath(os.path.join(base_dir, current_dir))
        unfiltered_match = glob.glob(current_path + os.sep + pattern)
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):
                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (user_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)
            if not first_match:
                first_match = abs_path

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            if abs_path + os.sep == base_dir:
                relative_path = '.'
            else:
                relative_path = abs_path.replace(base_dir, '')
            entries = []
            dir_listing = {
                'object_type': 'dir_listing',
                'relative_path': relative_path,
                'entries': entries,
                'flags': flags,
                }

            dest = ''
            if show_dest:
                if os.path.isfile(abs_path):
                    dest = os.path.basename(abs_path)
                elif recursive(flags):

                    # references to '.' or similar are stripped by abspath

                    if abs_path + os.sep == base_dir:
                        dest = ''
                    else:

                        # dest = os.path.dirname(abs_path).replace(base_dir, "")

                        dest = os.path.basename(abs_path) + os.sep

            handle_expand(configuration, output_objects, entries, base_dir,
                          abs_path, flags, dest, 0, show_dest)
            dir_listings.append(dir_listing)

    output_objects.append({'object_type': 'html_form', 'text': """
    <div class='files disable_read'>
    <form method='get' action='ls.py'>
    <table class='files'>
    <tr class=title><td class=centertext>
    Filter paths (wildcards like * and ? are allowed)
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    <input type='text' name='path' value='' />
    <input type='submit' value='Filter' />
    </td></tr>
    </table>    
    </form>
    </div>
    """ % fill_helpers})

    # Short/long format buttons

    fill_helpers['tmp_flags'] = flags + 'l'
    htmlform = """
    <table class='files if_full'>
    <tr class=title><td class=centertext colspan=4>
    File view options
    </td></tr>
    <tr><td colspan=4><br /></td></tr>
    <tr class=title><td>Parameter</td><td>Setting</td><td>Enable</td><td>Disable</td></tr>
    <tr><td>Long format</td><td>
    %(long_set)s</td><td>
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers

    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />" % entry
    fill_helpers['tmp_flags'] = flags.replace('l', '')
    htmlform += """
    <input type='submit' value='On' /><br />
    </form>
    </td><td>
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers
    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />" % entry
    htmlform += """
    <input type='submit' value='Off' /><br />
    </form>
    </td></tr>
    """

    # Recursive output

    fill_helpers['tmp_flags'] = flags + 'r'
    htmlform += """
    <!-- Non-/recursive list buttons -->
    <tr><td>Recursion</td><td>
    %(recursive_set)s</td><td>""" % fill_helpers
    htmlform += """
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers
    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />"% entry
    fill_helpers['tmp_flags'] = flags.replace('r', '')
    htmlform += """
    <input type='submit' value='On' /><br />
    </form>
    </td><td>
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers
                                  
    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />"\
                    % entry
        htmlform += """
    <input type='submit' value='Off' /><br />
    </form>
    </td></tr>
    """

    htmlform += """
    <!-- Show dot files buttons -->
    <tr><td>Show hidden files</td><td>
    %(all_set)s</td><td>""" % fill_helpers
    fill_helpers['tmp_flags'] = flags + 'a'
    htmlform += """
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers
    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />" % entry
    fill_helpers['tmp_flags'] = flags.replace('a', '')
    htmlform += """
    <input type='submit' value='On' /><br />
    </form>
    </td><td>
    <form method='get' action='ls.py'>
    <input type='hidden' name='output_format' value='html' />
    <input type='hidden' name='flags' value='%(tmp_flags)s' />
    <input type='hidden' name='share_id' value='%(share_id)s' />
    <input name='current_dir' type='hidden' value='%(dest_dir)s' />
    """ % fill_helpers
    for entry in pattern_list:
        htmlform += "<input type='hidden' name='path' value='%s' />"% entry
    htmlform += """
    <input type='submit' value='Off' /><br />
    </form>
    </td></tr>
    </table>
    """

    # show flag buttons after contents to limit clutter

    output_objects.append({'object_type': 'html_form', 'text'
                          : htmlform})

    return (output_objects, status)
