#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# forum - helper functions related to VGrid forums
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""VGrid forum specific helper functions:
This module builds on the Forest forum CGI software from
http://www.triv.org.uk/~nelis/forest/
Original description and credits follow here:

Script: Forest, a simple Python forum script.
Author: Andrew Nelis (andrew.nelis@gmail.com)
OnTheWeb: http://www.triv.org.uk/~nelis/forest
Date: Jun 2010
Version: 1.0.3

A Python CGI script for a basic flat-file based forum.

... basic use information removed ...

Copyright (c) 2010 Andrew Nelis

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import md5
import os
import time

# ============================================================================
# Configuration
# ============================================================================

# Where the main stylesheet is kept (as a URL).
CSS_PATH = '/images/css/forum.css'
# How dates are stored (see python time module for details)
DATE_FORMAT = '%d %b %Y %H:%M:%S'

# How many entries to show on the index?
INDEX_PAGE_SIZE = 20
# How many entries to show on the thread page?
THREAD_PAGE_SIZE = 20

# Maximum lengths for subjects and message bodies.
# (currently we chop them off without warning)
MAX_SUBJECT_LEN = 100
MAX_BODY_LEN = 10000

# ============================================================================
# HTML Elements.
# ============================================================================
HTML_THREADS_TOP = '''<table width="95%" class="threads_table">
 <tr class="threads_header">
  <th width="60%">Subject</th><th>Author</th><th>Date</th><th>Replies</th><th>Last Reply</th>
 </tr>
'''
HTML_THREADS_ROW = '''
 <tr class="%s">
  <td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>
 </tr>
'''
HTML_NEW_THREAD = '''
<div id="new_link">
<a href="javascript:toggle_new('hidden_form', 'new_link');">
Start a new thread</a>
</div>
<div id="hidden_form">
<form method="post" action="?action=new_thread">
%%s
<p>Subject: <input name="msg_subject" maxlength="%s" size="80"/></p>
<p><textarea name="msg_body" rows="10" cols="80"></textarea></p>
<p>
<input class="submit_button" type="submit" value="New Thread"/>
<input class="submit_button" type="reset" value="Clear"/>
<input class="submit_button" type="submit" value="Cancel"
onclick="javascript:toggle_new('hidden_form', 'new_link'); return false;"/>
</p>
</form>
</div>
''' % MAX_SUBJECT_LEN

HTML_NEW_REPLY = '''
<p>
<div id="new_link">
<a href="javascript:toggle_new('hidden_form', 'new_link')">
Reply to this thread</a></p>
</div>
<div id="hidden_form">
<form method="post" action="?action=reply&amp;thread=%s">
%%s
<p><textarea name="msg_body" rows="10" cols="80"></textarea></p>
<p>
<input class="submit_button" type="submit" value="Post"/>
<input class="submit_button" type="reset" value="Clear"/>
<input class="submit_button" type="submit" value="Cancel"
onclick="javascript:toggle_new('hidden_form', 'new_link'); return false;"/>
</p>
</form>
</div>
'''

HTML_THREADS_BOTTOM = '</table>'
HTML_THREAD_TOP = '''
<table width="95%%" class="threads_table">
 <col width="15%%" />
 <col width="85%%" />
 <tr><td colspan="2"><a href="?%s">&lt;&lt; Main</a></td></tr>
 <tr class="thread_header"><td colspan="2">%s</td></tr>
'''
HTML_THREAD_ROW = '''
 <tr class="%s">
  <td valign="top"><b>%s</b><br/><small>%s</small></td>
  <td>%s</td>
 </tr>
'''
HTML_THREAD_BOTTOM = '''
</table>
'''

# ============================================================================
# Error messages
# ============================================================================

ERR_INVALID_THREAD = 'Invalid Thread Specified'
ERR_NO_SUBJECT = 'No Subject Given'
ERR_NO_BODY = 'No body text!'

# ============================================================================
# Misc. globals
# ============================================================================

# No need to fiddle with these though.
ROW_STYLES = {0: 'thread_row', 1: 'thread_row_alt'}

# ============================================================================
# Function definitions
# ============================================================================

def get_thread_path(data_dir, hash_string):
    """build thread path from data_dir and hash_string"""
    return os.path.join(data_dir, hash_string)

def get_index_path(data_dir):
    """build index path from data_dir"""
    return os.path.join(data_dir, 'index.txt')

def add_extra_fields(form_template, extra_fields):
    """Add each of the key/value pairs in extra_fields dictionary as hidden
    form input to form_template with a single expandable string variable.
    """
    hidden = ''
    for (key, val) in extra_fields.items():
        hidden += '<input type="hidden" name="%s" value="%s"/>\n' % (key, val)
    return form_template % hidden

def add_extra_args(url, extra_fields):
    """Append each of the key/value pairs in extra_fields dictionary to url
    with query arguments.
    """
    hidden = ''
    for (key, val) in extra_fields.items():
        hidden += '&%s=%s' % (key, val)
    return url + hidden


def strip_html( text ):
    """Remove HTML chars from the given text and replace them with HTML
       entities"""
    text = text or ''
    return text.replace( '&', '&amp;' ) \
               .replace( '>', '&gt;' ) \
               .replace( '<', '&lt;' )


def process_body(body):
    """Process the message body e.g. for escaping smilies, HTML etc.
    ready for storing. We should then just be able to print the body out"""
    import re
    url_re = re.compile('(http://[\S\.]+)')
    # Maximum body length.
    new_body = strip_html( body[:MAX_BODY_LEN] )
    new_body = new_body.replace('\n', '<br/>\n')
    # Turn (obvious) URLs into links.
    new_body = url_re.sub(r'<a href="\1">\1</a>', new_body)
    return new_body.encode('string_escape')


def process_subject(subject):
    """Clean the subject line"""
    return subject[:MAX_SUBJECT_LEN]


def is_valid_hash(data_dir, hash_string):
    """Ensure that <hash_string> is a proper hash representing an existing
    thread"""
    # Should be a string comprising of hex digits
    if not hash_string.isalnum():
        return False
    if not os.path.exists(get_thread_path(data_dir, hash_string)):
        return False
    return True


def update_thread(data_dir, author, subject=None, key=None):
    """Update the thread, creating a new thread if key is None. Returns the
    key (hash).

    author  - String, the ID of the author.
    subject - String, the title of the thread.
    key     - String, the key to an existing thread to update.

    If <subject> is given, then it's assumed that we're starting a new thread
    and if <key> is given, then we should be updating an existing thread.
    """
    now = time.strftime(DATE_FORMAT)

    if key:
        row_hash = key
    else:
        row_hash = md5.new('%s%s%s' % (now, author, subject)).hexdigest()

    # Read the index of threads in.
    try:
        threads = file(get_index_path(data_dir), 'r').readlines()
    except IOError:
        # The file gets (re)created later on so there's no problem.
        threads = []

    new_threads = []

    # Index format:
    # hash, date, num_replies, last_reply, author, subject
    if not key:
        # A new thread, put at the top.
        new_threads.append('\t'.join(
                (row_hash, now, '0', '-', author, subject)))

    for thread in threads:
        if thread.startswith(row_hash):
            # insert the updated thread at the beginning.
            # (_ ignore last reply - we're setting it to now)
            _, date, num_replies, _, author, subject = \
                    thread.strip().split('\t')
            num_replies = str(int(num_replies) + 1)
            new_threads.insert(0, '\t'.join(
                (row_hash, date, num_replies, now, author, subject)))
        else:
            new_threads.append(thread.strip())

    # Overwrite the existing index with the updated index.
    threads = file(get_index_path(data_dir), 'w')
    threads.write('\n'.join(new_threads))
    threads.close()

    return row_hash


def new_subject(data_dir, author, subject, body):
    """Add a new subject to the list of threads.

    author - ID of posting user
    subject - message subject
    body - message body

    On success:
        returns <new subject hash string>
    On error:
        raises ValueError with error as message.
    """
    if not subject:
        raise ValueError( ERR_NO_SUBJECT )
    elif not body:
        raise ValueError( ERR_NO_BODY )
    subject = subject.replace('\t', ' ')
    row_hash = update_thread(data_dir, author, subject )
    new_post(data_dir, author, subject, body, row_hash )
    return row_hash


def new_post(data_dir, author, subject, body, key):
    """Create a new post, either by creating or appending to a post file.

    author, subject, body, key - Strings
    """
    subject = process_subject(subject)
    body = process_body(body)

    date = time.strftime(DATE_FORMAT)
    post_filename = get_thread_path(data_dir, key)
    if not os.path.exists(post_filename):
        post_file = file(post_filename, 'w')
        post_file.write('%s\t%s\n' % (key, subject))
    else:
        post_file = file(post_filename, 'a')
    post_file.write('%s\t%s\t%s\n' % (date, author, body))
    post_file.close()

def reply(data_dir, author, body, key):
    """Reply to an existing post.

    data_dir - path to data directory
    author - user ID of poster
    body - message body of reply
    key - String, the id of the thread we're replying to.

    On success:
        return <thread key string>
    On failure:
        raise ValueError with error message as error value.
    """
    # Check that the thread id is valid.
    if not (key and is_valid_hash(data_dir, key)):
        raise ValueError( ERR_INVALID_THREAD )
    if not body:
        raise ValueError( ERR_NO_BODY )
    update_thread(data_dir, author, key=key)
    new_post(data_dir, author, '', body, key)
    return key


def display_paging_links(extra_fields, current_offset, num_items, page_length,
                         thread=None):
    """Display a list of links to go to a given page number"""
    pages = num_items / page_length
    # Any left over pages?
    if (num_items % page_length):
        pages += 1

    if pages < 2:
        # Only one page. Don't bother showing links.
        return ''

    links = []
    if thread:
        url = '?thread=%s&offset=%%d' % thread
    else:
        url = '?offset=%d'
    url = add_extra_args(url, extra_fields)
    for page_number in range(pages):
        offset = page_number * page_length
        if offset != current_offset:
            links.append( '<a href="%s">%s</a>' % \
                    (url % offset, page_number + 1) )
        else:
            links.append( str( page_number + 1 ) )

    return ' | '.join(links)


def list_threads(data_dir, extra_input, offset=0):
    """List the existing threads."""
    lines = []
    if os.path.exists(get_index_path(data_dir)):
        thread_file = file(get_index_path(data_dir), 'r')
        threads = thread_file.read().strip().split('\n')
        thread_file.close()
    else:
        threads = []

    num_threads = len(threads)

    lines.append(display_paging_links(extra_input, offset, num_threads,
                                  INDEX_PAGE_SIZE))

    lines.append(HTML_THREADS_TOP)

    thread_index = -1

    for thread in threads[offset:offset + INDEX_PAGE_SIZE]:
        thread_index += 1

        thread_items = thread.split('\t')
        if len(thread_items) != 6:
            continue

        thread_hash, date, num_replies, last_reply, author, subject = \
            thread_items

        url = add_extra_args('?thread=%s' % thread_hash, extra_input)
        link = '<a href="%s">%s</a>' % (url, subject)

        #  Date Author Subject Replies Last Reply
        lines.append(HTML_THREADS_ROW % (ROW_STYLES[thread_index % 2], link,
                                         author, date, num_replies,
                                         last_reply))

    lines.append(HTML_THREADS_BOTTOM)
    lines.append(add_extra_fields(HTML_NEW_THREAD, extra_input))
    return lines


def list_single_thread(data_dir, extra_input, thread_hash, offset=0):
    """Output the HTMl for a given thread id"""
    lines = []
    if not is_valid_hash(data_dir, thread_hash):
        lines.append(ERR_INVALID_THREAD)
        return lines

    # TODO: add file locking!
    thread_file = file(get_thread_path(data_dir, thread_hash), 'r')
    threads = thread_file.read().split('\n')
    thread_file.close()

    # The first item in the file is actually the hash and the subject. But we
    # don't need it really.
    _, subject = threads.pop(0).split('\t')
    num_posts = len(threads)
    # Show last page if offset is negative (e.g. after reply)
    if offset < 0:
        offset = THREAD_PAGE_SIZE * ((num_posts - 2) / THREAD_PAGE_SIZE)
    lines.append(display_paging_links(extra_input, offset, num_posts,
                                  THREAD_PAGE_SIZE, thread_hash))
    url = add_extra_args('', extra_input)
    lines.append(HTML_THREAD_TOP % (url, subject.strip()))

    row_index = -1
    for line in threads[offset : offset + THREAD_PAGE_SIZE]:
        row_index += 1
        split_line = line.split('\t')
        if len(split_line) != 3:
            continue

        date, author, body = split_line
        lines.append(HTML_THREAD_ROW % (ROW_STYLES[row_index % 2], author, date,
                                        body.decode('string_escape')))

    lines.append(HTML_THREAD_BOTTOM)
    lines.append(add_extra_fields(HTML_NEW_REPLY % thread_hash, extra_input))
    return lines
