#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ls - emulate ls command
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Script to provide users with a means of listing files and directories in
their home directories. This script tries to mimic GNU ls behaviour.
"""

import os
import time
import glob
import stat
from urllib import quote

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, invisible_path
from shared.defaults import seafile_ro_dirname, trash_destdir, csrf_field
from shared.functional import validate_input
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, fancy_upload_js, fancy_upload_html, \
    confirm_js, confirm_html, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import all, long_list, recursive, file_info
from shared.sharelinks import extract_mode_id
from shared.userio import GDPIOLogError, gdp_iolog
from shared.validstring import valid_user_path
from shared.vgrid import in_vgrid_share, in_vgrid_priv_web, in_vgrid_pub_web, \
    in_vgrid_readonly, in_vgrid_writable, in_vgrid_store_res


def signature():
    """Signature of the main function"""
    defaults = {'flags': [''], 'path': ['.'], 'share_id': [''],
                'current_dir': ['.']}
    return ['dir_listings', defaults]


def select_all_javascript():
    """javascript to select all html checkboxes"""
    return """
function toggleChecked() {
   var doCheck = $('#checkall_box').prop('checked');
   $('td input[type=checkbox]').prop('checked', doCheck);
}
    """


def selected_file_actions_javascript():
    """javascript  to dynamically select action for marked items"""
    return """
function selectedFilesAction() {
    if (document.pressed == 'cat') {
       document.fileform.action = 'cat.py';
    }
    else if (document.pressed == 'head') {
       document.fileform.action = 'head.py';
    }
    else if (document.pressed == 'rm') {
       document.fileform.action = 'rm.py';
       document.fileform.flags.value = 'rv';
    }
    else if (document.pressed == 'rmdir') {
       document.fileform.action = 'rmdir.py';
    }
    else if (document.pressed == 'stat') {
       document.fileform.action = 'statpath.py';
    }
    else if (document.pressed == 'submit') {
       document.fileform.action = 'submit.py';
    }
    else if (document.pressed == 'tail') {
       document.fileform.action = 'tail.py';
    }
    else if (document.pressed == 'touch') {
       document.fileform.action = 'touch.py';
    }
    else if (document.pressed == 'truncate') {
       document.fileform.action = 'truncate.py';
    }
    else if (document.pressed == 'wc') {
       document.fileform.action = 'wc.py';
    }
    return true;
}
    """


def fileinfo_stat(path):
    """Additional stat information for file manager"""
    file_information = {'size': 0, 'created': 0, 'modified': 0, 'accessed': 0,
                        'ext': ''}
    if os.path.exists(path):
        ext = 'dir'
        if not os.path.isdir(path):
            ext = os.path.splitext(path)[1].lstrip('.')
        file_information['ext'] = ext
        try:
            file_information['size'] = os.path.getsize(path)
            file_information['created'] = os.path.getctime(path)
            file_information['modified'] = os.path.getmtime(path)
            file_information['accessed'] = os.path.getatime(path)
        except OSError, ose:
            pass
    return file_information


def long_format(path):
    """output extra info like filesize about the file located at path"""
    format_line = ''
    perms = ''

    # Make a single stat call and extract all info from it

    try:
        stat_info = os.stat(path)
    except Exception:
        return 'Internal error: stat failed!'

    mode = stat_info.st_mode
    if stat.S_ISDIR(mode):
        perms = 'd'
    elif stat.S_ISREG(mode):
        perms = '-'

    mode = stat.S_IMODE(mode)

    for entity in ('USR', 'GRP', 'OTH'):
        for permission in ('R', 'W', 'X'):

            # lookup attribute at runtime using getattr

            if mode & getattr(stat, 'S_I' + permission + entity):
                perms = perms + permission.lower()
            else:
                perms = perms + '-'

    format_line += perms + ' '
    size = str(stat_info.st_size)
    format_line += size + ' '
    atime = time.asctime(time.gmtime(stat_info.st_mtime))
    format_line += atime + ' '

    return format_line


def handle_file(
    configuration,
    listing,
    filename,
    file_with_dir,
    actual_file,
    flags='',
):
    """handle a file"""

    # Build entire line before printing to avoid newlines

    # Recursion can get here when called without explicit invisible files

    if invisible_path(file_with_dir):
        return
    special = ''
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
        'special': special,
    }
    if long_list(flags):
        file_obj['long_format'] = long_format(actual_file)

    if file_info(flags):
        file_obj['file_info'] = fileinfo_stat(actual_file)

    listing.append(file_obj)


def handle_dir(
    configuration,
    listing,
    dirname,
    dirname_with_dir,
    actual_dir,
    flags='',
):
    """handle a dir"""

    # Recursion can get here when called without explicit invisible files

    if invisible_path(dirname_with_dir):
        return
    special = ''
    extra_class = ''
    real_dir = os.path.realpath(actual_dir)
    abs_dir = os.path.abspath(actual_dir)
    # If we followed a symlink it is not a plain dir
    if real_dir != abs_dir:
        access_type = configuration.site_vgrid_label
        parent_dir = os.path.basename(os.path.dirname(actual_dir))
        # configuration.logger.debug("checking link %s type (%s)" % \
        #                           (dirname_with_dir, real_dir))
        # Separate vgrid special dirs from plain ones
        if in_vgrid_share(configuration, actual_dir) == dirname_with_dir:
            dir_type = 'shared files'
            extra_class = 'vgridshared'
        elif in_vgrid_readonly(configuration, actual_dir) == dirname_with_dir:
            access_type = 'read-only'
            dir_type = 'shared files'
            extra_class = 'vgridshared readonly'
        elif in_vgrid_pub_web(configuration, actual_dir) == \
                dirname_with_dir[len('public_base/'):]:
            dir_type = 'public web page'
            extra_class = 'vgridpublicweb'
        elif in_vgrid_priv_web(configuration, actual_dir) == \
                dirname_with_dir[len('private_base/'):]:
            dir_type = 'private web page'
            extra_class = 'vgridprivateweb'
        # NOTE: in_vgrid_X returns None on miss, so don't use replace directly
        elif (in_vgrid_store_res(configuration, actual_dir) or '').replace(
                os.sep, '_') == os.path.basename(dirname_with_dir):
            dir_type = 'storage resource files'
            if os.path.islink(actual_dir):
                extra_class = 'vgridstoreres'
        elif real_dir.startswith(configuration.seafile_mount):
            access_type = 'read-only'
            dir_type = 'Seafile library access'
            if os.path.islink(actual_dir):
                extra_class = 'seafilereadonly'
        elif real_dir.find(trash_destdir) != -1:
            access_type = 'recently deleted data'
            dir_type = 'sub'
        else:
            dir_type = 'sub'
        # TODO: improve this greedy matching here?
        # configuration.logger.debug("check real_dir %s vs %s" % (real_dir,
        #                                                        trash_destdir))
        if real_dir.endswith(trash_destdir):
            dir_type = ''
            extra_class = 'trashbin'
        special = ' - %s %s directory' % (access_type, dir_type)
    dir_obj = {
        'object_type': 'direntry',
        'type': 'directory',
        'name': dirname,
        'rel_path': dirname_with_dir,
        'rel_path_enc': quote(dirname_with_dir),
        'rel_dir_enc': quote(dirname_with_dir),
        # NOTE: dirname_with_dir is kept for backwards compliance
        'dirname_with_dir': dirname_with_dir,
        'flags': flags,
        'special': special,
        'extra_class': extra_class,
    }

    if long_list(flags):
        dir_obj['actual_dir'] = long_format(actual_dir)

    if file_info(flags):
        dir_obj['file_info'] = fileinfo_stat(actual_dir)

    listing.append(dir_obj)


def handle_ls(
    configuration,
    output_objects,
    listing,
    base_dir,
    real_path,
    flags='',
    depth=0,
):
    """Recursive function to emulate GNU ls (-R)"""

    # Sanity check

    if depth > 255:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error: file recursion maximum exceeded!'
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
        handle_file(configuration, listing, base_name, relative_path,
                    real_path, flags)
    else:
        try:
            contents = os.listdir(real_path)
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Failed to list contents of %s: %s'
                                   % (base_name, exc)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # Filter out dot files unless '-a' is used

        if not all(flags):
            contents = [i for i in contents if not i.startswith('.')]
        contents.sort()

        if not recursive(flags) or depth < 0:

            # listdir does not include '.' and '..' - add manually
            # to ease navigation

            if all(flags):
                handle_dir(configuration, listing, '.', relative_path,
                           real_path, flags)
                handle_dir(configuration, listing, '..',
                           os.path.dirname(relative_path),
                           os.path.dirname(real_path), flags)
            for name in contents:
                path = real_path + os.sep + name
                rel_path = path.replace(base_dir, '')
                if os.path.isfile(path):
                    handle_file(configuration, listing, name, rel_path, path,
                                flags)
                else:
                    handle_dir(configuration, listing, name, rel_path, path,
                               flags)
        else:

            # Force pure content listing first by passing a negative depth

            handle_ls(
                configuration,
                output_objects,
                listing,
                base_dir,
                real_path,
                flags,
                -1,
            )

            for name in contents:
                path = real_path + os.sep + name
                rel_path = path.replace(base_dir, '')
                if os.path.isdir(path):
                    handle_ls(
                        configuration,
                        output_objects,
                        listing,
                        base_dir,
                        path,
                        flags,
                        depth + 1,
                    )


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

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

    status = returnvalues.OK

    read_mode, write_mode = True, True
    # Either authenticated user client_id set or sharelink ID
    if client_id:
        user_id = client_id
        target_dir = client_id_dir(client_id)
        base_dir = configuration.user_home
        redirect_name = configuration.site_user_redirect
        redirect_path = redirect_name
        id_args = ''
        root_link_name = 'USER HOME'
        main_id = "user_ls"
        page_title = 'User Files'
        userstyle = True
        widgets = True
        visibility_mods = '''
            #%(main_id)s .disable_read { display: none; }
            #%(main_id)s .disable_write { display: none; }
            '''
    elif share_id:
        try:
            (share_mode, _) = extract_mode_id(configuration, share_id)
        except ValueError, err:
            logger.error('%s called with invalid share_id %s: %s' %
                         (op_name, share_id, err))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Invalid sharelink ID: %s' % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # TODO: load and check sharelink pickle (currently requires client_id)
        # then include shared by %(owner)s on page header
        user_id = 'anonymous user through share ID %s' % share_id
        target_dir = os.path.join(share_mode, share_id)
        base_dir = configuration.sharelink_home
        redirect_name = 'share_redirect'
        redirect_path = os.path.join(redirect_name, share_id)
        id_args = 'share_id=%s;' % share_id
        root_link_name = '%s' % share_id
        main_id = "sharelink_ls"
        page_title = 'Shared Files'
        userstyle = False
        widgets = False
        # default to include file info
        if flags == '':
            flags += 'f'
        if share_mode == 'read-only':
            write_mode = False
            visibility_mods = '''
            #%(main_id)s .enable_write { display: none; }
            #%(main_id)s .disable_read { display: none; }
            '''
        elif share_mode == 'write-only':
            read_mode = False
            visibility_mods = '''
            #%(main_id)s .enable_read { display: none; }
            #%(main_id)s .disable_write { display: none; }
            '''
        else:
            visibility_mods = '''
            #%(main_id)s .disable_read { display: none; }
            #%(main_id)s .disable_write { display: none; }
            '''
    else:
        logger.error('%s called without proper auth: %s' % (op_name, accepted))
        output_objects.append({'object_type': 'error_text', 'text':
                               'Authentication is missing!'
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
        output_objects.append({'object_type': 'error_text', 'text':
                               'No such %s!' % page_title.lower()
                               })
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = page_title
    title_entry['skipwidgets'] = not widgets
    title_entry['skipuserstyle'] = not userstyle

    open_button_id = 'open_fancy_upload'
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'dest_dir': current_dir + os.sep, 'share_id': share_id,
                    'flags': flags, 'tmp_flags': flags, 'long_set':
                    long_list(flags), 'recursive_set': recursive(flags),
                    'all_set': all(flags), 'fancy_open': open_button_id,
                    'fancy_dialog': fancy_upload_html(configuration),
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'uploadchunked'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    (cf_import, cf_init, cf_ready) = confirm_js(configuration)
    (fu_import, fu_init, fu_ready) = fancy_upload_js(
        configuration, 'function() { location.reload(); }', share_id,
        csrf_token)
    add_import = '''
%s
%s
    ''' % (cf_import, fu_import)
    add_init = '''
%s
%s
%s
%s
    ''' % (cf_init, fu_init, select_all_javascript(),
           selected_file_actions_javascript())
    add_ready = '''
%s
%s
    /* wrap openFancyUpload in function to avoid event data as argument */
    $("#%s").click(function() { openFancyUpload(); });
    $("#checkall_box").click(toggleChecked);
    ''' % (cf_ready, fu_ready, open_button_id)
    styles = themed_styles(configuration, base=['jquery.fileupload.css',
                                                'jquery.fileupload-ui.css'],
                           skin=['fileupload-ui.custom.css'])
    styles['advanced'] += '''
    %s
    ''' % visibility_toggle
    title_entry['style'] = styles
    title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                             add_init, add_ready)
    title_entry['bodyfunctions'] += ' id="%s"' % main_id
    output_objects.append({'object_type': 'header', 'text': page_title})

    # TODO: move to output html handler
    output_objects.append({'object_type': 'html_form',
                           'text': confirm_html(configuration)})

    # Shared URL helpers
    ls_url_template = 'ls.py?%scurrent_dir=%%(rel_dir_enc)s;flags=%s' % \
                      (id_args, flags)
    csrf_token = make_csrf_token(configuration, form_method, 'rm', client_id,
                                 csrf_limit)
    rm_url_template = 'rm.py?%spath=%%(rel_path_enc)s;%s=%s' % \
                      (id_args, csrf_field, csrf_token)
    rmdir_url_template = 'rm.py?%spath=%%(rel_path_enc)s;flags=r;%s=%s' % \
        (id_args, csrf_field, csrf_token)
    editor_url_template = 'editor.py?%spath=%%(rel_path_enc)s' % id_args
    redirect_url_template = '/%s/%%(rel_path_enc)s' % redirect_path

    location_pre_html = """
<div class='files'>
<table class='files'>
<tr class=title><td class=centertext>
Working directory:
</td></tr>
<tr><td class='centertext'>
"""
    output_objects.append(
        {'object_type': 'html_form', 'text': location_pre_html})
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
                          'destination': ls_url_template %
                          {'rel_dir_enc': quote(prefix)}})
        output_objects.append(
            {'object_type': 'multilinkline', 'links': links, 'sep': ' %s ' %
             os.sep})
    location_post_html = """
</td></tr>
</table>
</div>
<br />
"""

    output_objects.append(
        {'object_type': 'html_form', 'text': location_post_html})

    more_html = """
<div class='files if_full'>
<form method='%(form_method)s' name='fileform' onSubmit='return selectedFilesAction();'>
<table class='files'>
<tr class=title><td class=centertext colspan=2>
Advanced file actions
</td></tr>
<tr><td>
Action on paths selected below
(please hold mouse cursor over button for a description):
</td>
<td class=centertext>
<input type='hidden' name='output_format' value='html' />
<input type='hidden' name='flags' value='v' />
<input type='submit' title='Show concatenated contents (cat)' onClick='document.pressed=this.value' value='cat' />
<input type='submit' onClick='document.pressed=this.value' value='head' title='Show first lines (head)' />
<input type='submit' onClick='document.pressed=this.value' value='tail' title='Show last lines (tail)' />
<input type='submit' onClick='document.pressed=this.value' value='wc' title='Count lines/words/chars (wc)' />
<input type='submit' onClick='document.pressed=this.value' value='stat' title='Show details (stat)' />
<input type='submit' onClick='document.pressed=this.value' value='touch' title='Update timestamp (touch)' />
<input type='submit' onClick='document.pressed=this.value' value='truncate' title='truncate! (truncate)' />
<input type='submit' onClick='document.pressed=this.value' value='rm' title='delete! (rm)' />
<input type='submit' onClick='document.pressed=this.value' value='rmdir' title='Remove directory (rmdir)' />
<input type='submit' onClick='document.pressed=this.value' value='submit' title='Submit file (submit)' />
</td></tr>
</table>    
</form>
</div>
""" % {'form_method': form_method}

    output_objects.append({'object_type': 'html_form', 'text': more_html})
    dir_listings = []
    output_objects.append({
        'object_type': 'dir_listings',
        'dir_listings': dir_listings,
        'flags': flags,
        'redirect_name': redirect_name,
        'redirect_path': redirect_path,
        'share_id': share_id,
        'ls_url_template': ls_url_template,
        'rm_url_template': rm_url_template,
        'rmdir_url_template': rmdir_url_template,
        'editor_url_template': editor_url_template,
        'redirect_url_template': redirect_url_template,
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

        # Never show any ls output in write-only mode (css hide is not enough!)
        if not read_mode:
            continue

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
            try:
                gdp_iolog(configuration,
                          client_id,
                          environ['REMOTE_ADDR'],
                          'accessed',
                          [relative_path])
            except GDPIOLogError, exc:
                output_objects.append({'object_type': 'error_text',
                                       'text': "%s: '%s': %s"
                                       % (op_name, relative_path, exc)})
                logger.error("%s: failed on '%s': %s"
                             % (op_name, relative_path, exc))
                continue
            handle_ls(configuration, output_objects, entries, base_dir,
                      abs_path, flags, 0)
            dir_listings.append(dir_listing)

    output_objects.append({'object_type': 'html_form', 'text': """<br/>
    <div class='files disable_read'>
    <p class='info icon'>"""})
    # Shared message for text (e.g. user scripts) and html-format
    if not read_mode:
        # Please note that we use verbatim to get info icon right in html
        output_objects.append({'object_type': 'verbatim', 'text': """
This is a write-only share so you do not have access to see the files, only
upload data and create directories.
    """})
    output_objects.append({'object_type': 'html_form', 'text':
                           """
    </p>
    </div>
    <div class='files enable_read'>
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
        htmlform += "<input type='hidden' name='path' value='%s' />" % entry
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
        htmlform += "<input type='hidden' name='path' value='%s' />" % entry
    htmlform += """
    <input type='submit' value='Off' /><br />
    </form>
    </td></tr>
    </table>
    """

    # show flag buttons after contents to limit clutter

    output_objects.append({'object_type': 'html_form', 'text': htmlform})

    # create additional action forms

    if first_match:
        htmlform = """
<br />
<div class='files disable_write'>
<p class='info icon'>
This is a read-only share so you do not have access to edit or add files, only
view data.
</p>
</div>
<table class='files enable_write if_full'>
<tr class=title><td class=centertext colspan=3>
Edit file
</td></tr>
<tr><td>
Fill in the path of a file to edit and press 'edit' to open that file in the<br />
online file editor. Alternatively a file can be selected for editing through<br />
the listing of personal files. 
</td><td colspan=2 class=righttext>
<form name='editor' method='get' action='editor.py'>
<input type='hidden' name='output_format' value='html' />
<input type='hidden' name='share_id' value='%(share_id)s' />
<input name='current_dir' type='hidden' value='%(dest_dir)s' />
<input type='text' name='path' size=50 value='' required />
<input type='submit' value='edit' />
</form>
</td></tr>
</table>
<br />""" % fill_helpers
        target_op = 'mkdir'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        htmlform += """
<table class='files enable_write'>
<tr class=title><td class=centertext colspan=4>
Create directory
</td></tr>
<tr><td>
Name of new directory to be created in current directory (%(dest_dir)s)
</td><td class=righttext colspan=3>
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type='hidden' name='share_id' value='%(share_id)s' />
<input name='current_dir' type='hidden' value='%(dest_dir)s' />
<input name='path' size=50 required />
<input type='submit' value='Create' name='mkdirbutton' />
</form>
</td></tr>
</table>
<br />
""" % fill_helpers
        target_op = 'textarea'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        htmlform += """
<form enctype='multipart/form-data' method='%(form_method)s'
    action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<input type='hidden' name='share_id' value='%(share_id)s' />
<table class='files enable_write if_full'>
<tr class='title'><td class=centertext colspan=4>
Upload file
</td></tr>
<tr><td colspan=4>
Upload file to current directory (%(dest_dir)s)
</td></tr>
<tr class='if_full'><td colspan=2>
Extract package files (.zip, .tar.gz, .tar.bz2)
</td><td colspan=2>
<input type=checkbox name='extract_0' />
</td></tr>
<tr class='if_full'><td colspan=2>
Submit mRSL files (also .mRSL files included in packages)
</td><td colspan=2>
<input type=checkbox name='submitmrsl_0' />
</td></tr>
<tr><td>    
File to upload
</td><td class=righttext colspan=3>
<input name='fileupload_0_0_0' type='file'/>
</td></tr>
<tr><td>
Optional remote filename (extra useful in windows)
</td><td class=righttext colspan=3>
<input name='default_remotefilename_0' type='hidden' value='%(dest_dir)s'/>
<input name='remotefilename_0' type='text' size='50' value='%(dest_dir)s'/>
<input type='submit' value='Upload' name='sendfile'/>
</td></tr>
</table>
</form>
%(fancy_dialog)s
<table class='files enable_write'>
<tr class='title'><td class='centertext'>
Upload files efficiently (using chunking).
</td></tr>
<tr><td class='centertext'>
<button id='%(fancy_open)s'>Open Upload dialog</button>
</td></tr>
</table>
<script type='text/javascript' >
    setUploadDest('%(dest_dir)s');
</script>
    """ % fill_helpers
        output_objects.append({'object_type': 'html_form', 'text': htmlform})
    return (output_objects, status)
