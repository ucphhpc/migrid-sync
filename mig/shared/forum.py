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
This module is a heavily modified extension of the simple Forest forum CGI
software from
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

import fcntl
try:
    from hashlib import md5 as md5_hash
except ImportError:
    from md5 import new as md5_hash
import os
import time

# TODO: enable search in message bodies too
# TODO: enable search in dates too
# TODO: add delete thread/post to admin version
# TODO: fancy editor, html, smilies, markup, etc
# TODO: enable edits of own messages?
# TODO: can we mark new posts somehow?
# TODO: can we add sticky posts somehow? add priority field for admins?
# TODO: should we anonymize user IDs?

### Constants
# File lock to avoid races on writes
LOCK_NAME = 'forum.lock'

# Thread index file name
INDEX_NAME = 'index.txt'

# Thread index file name
SUBSCRIBER_NAME = 'subscribers.txt'

# How dates are stored (see python time module for details)
DATE_FORMAT = '%d %b %Y %H:%M:%S'

# Maximum lengths for subjects and message bodies.
# (currently we chop them off without warning)
MAX_SUBJECT_LEN = 100
MAX_BODY_LEN = 10000

ERR_INVALID_THREAD = 'Invalid Thread Specified'
ERR_NO_SUBJECT = 'No Subject Given'
ERR_NO_BODY = 'No body text!'


def get_thread_path(data_dir, hash_string):
    """build thread path from data_dir and hash_string"""
    return os.path.join(data_dir, hash_string)

def get_index_path(data_dir):
    """build index path from data_dir"""
    return os.path.join(data_dir, INDEX_NAME)

def get_subscriber_path(data_dir, key=''):
    """build index path from data_dir and optional key"""
    if key:
        return os.path.join(data_dir, key + '-' + SUBSCRIBER_NAME)
    else:
        return os.path.join(data_dir, SUBSCRIBER_NAME)

def get_lock_path(data_dir):
    """build lock path from data_dir"""
    return os.path.join(data_dir, LOCK_NAME)



def strip_html(text):
    """Remove HTML chars from the given text and replace them with HTML
       entities"""
    text = text or ''
    return text.replace('&', '&amp;') \
               .replace('>', '&gt;') \
               .replace('<', '&lt;')


def process_body(body):
    """Process the message body e.g. for escaping smilies, HTML etc.
    ready for storing. We should then just be able to print the body out"""
    import re
    url_re = re.compile('(http://[\S\.]+)')
    # Maximum body length.
    new_body = strip_html(body[:MAX_BODY_LEN])
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
        row_hash = md5_hash('%s%s%s' % (now, author, subject)).hexdigest()

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
        returns (<new subject hash string>, <status message>)
    On error:
        raises ValueError with error as message.
    """
    if not subject:
        raise ValueError(ERR_NO_SUBJECT)
    elif not body:
        raise ValueError(ERR_NO_BODY)
    subject = subject.replace('\t', ' ')
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    row_hash = update_thread(data_dir, author, subject)
    new_post(data_dir, author, subject, body, row_hash)
    lock_handle.close()
    msg = 'Succesfully created new thread: "%s"' % subject
    return (row_hash, msg)


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
        returns (<thread key string>, <status message>)
    On failure:
        raise ValueError with error message as error value.
    """
    # Check that the thread id is valid.
    if not body:
        raise ValueError(ERR_NO_BODY)
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    if not (key and is_valid_hash(data_dir, key)):
        lock_handle.close()
        raise ValueError(ERR_INVALID_THREAD)
    update_thread(data_dir, author, key=key)
    new_post(data_dir, author, '', body, key)
    lock_handle.close()
    return (key, 'Succesfully posted reply')

def list_subscribers(data_dir, key=''):
    """Load a list of authors subscribing to the forum or a specific thread if
    key is provided. The subscribers are looked up in the corresponding
    subscriber file.

    key - String
    """
    subscribers = []
    subscribe_filename = get_subscriber_path(data_dir, key)
    if not os.path.exists(subscribe_filename):
        return subscribers
    subscribe_file = file(subscribe_filename, 'r')
    subscribers = [line.strip() for line in subscribe_file]
    subscribe_file.close()
    return subscribers

def toggle_subscribe(data_dir, author, key=''):
    """Toggle notification about new messages for author, by updating the
    corresponding subscriber file.

    author, key - Strings
    """
    new_lines = []
    subscribe_filename = get_subscriber_path(data_dir, key)
    add_author = True
    if not os.path.exists(subscribe_filename):
        subscribe_file = file(subscribe_filename, 'w')
    else:
        subscribe_file = file(subscribe_filename, 'r+')
        for line in subscribe_file:
            if line.strip() == author:
                add_author = False
                continue
            new_lines.append(line)
    if add_author:
        new_lines.append('%s\n' % author)
        out = '''Succesfully subscribed any addresses from your personal
settings to forum updates'''
    else:
        out = 'Succesfully unsubscribed from forum updates'
    subscribe_file.seek(0)
    subscribe_file.truncate(0)
    subscribe_file.writelines(new_lines)
    subscribe_file.close()
    return out

def list_threads(data_dir):
    """List the existing threads."""
    thread_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    if os.path.exists(get_index_path(data_dir)):
        thread_file = file(get_index_path(data_dir), 'r')
        threads = thread_file.read().strip().split('\n')
        thread_file.close()
    else:
        threads = []
    lock_handle.close()

    for thread in threads:
        thread_items = thread.split('\t')
        if len(thread_items) != 6:
            continue

        thread_hash, date, num_replies, last_reply, author, subject = \
            thread_items

        url = "?thread=%s" % thread_hash
        #  Date Author Subject Replies Last Reply
        last_update = last_reply
        if last_reply == '-':
            last_update = date
        entry = {'subject': subject, 'link': url, 'author': author, 'date':
                 date, 'replies': num_replies, 'last': last_update}
        thread_list.append(entry)

    return thread_list


def list_single_thread(data_dir, thread_hash):
    """Output the HTMl for a given thread id"""
    message_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    if not is_valid_hash(data_dir, thread_hash):
        raise ValueError(ERR_INVALID_THREAD)

    thread_file = file(get_thread_path(data_dir, thread_hash), 'r')
    threads = thread_file.read().split('\n')
    thread_file.close()
    lock_handle.close()

    # The first item in the file is actually the hash and the subject. But we
    # don't need it really.
    _, subject = threads.pop(0).split('\t')

    for line in threads:
        split_line = line.split('\t')
        if len(split_line) != 3:
            continue

        date, author, body = split_line
        entry = {'subject': subject, 'author': author, 'date': date, 'body':
                 body.decode('string_escape')}
        message_list.append(entry)

    return message_list

def search_threads(data_dir, subject, body):
    """Search the existing threads."""
    thread_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    if os.path.exists(get_index_path(data_dir)):
        thread_file = file(get_index_path(data_dir), 'r')
        threads = thread_file.read().strip().split('\n')
        thread_file.close()
    else:
        threads = []
    lock_handle.close()

    # Filter using search terms
    threads = [i for i in threads if i.find(subject) != -1]

    for thread in threads:
        thread_items = thread.split('\t')
        if len(thread_items) != 6:
            continue

        thread_hash, date, num_replies, last_reply, author, subject = \
            thread_items

        url = '?action=show_thread&thread=%s' % thread_hash
        #  Date Author Subject Replies Last Reply
        last_update = last_reply
        if last_reply == '-':
            last_update = date
        entry = {'subject': subject, 'link': url, 'author': author, 'date':
                 date, 'replies': num_replies, 'last': last_update}
        thread_list.append(entry)

    return thread_list
