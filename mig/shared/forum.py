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
# TODO: can we add sticky posts somehow? add priority field for admins?
# TODO: should we anonymize user IDs?

### Constants
# File lock to avoid races on writes
LOCK_NAME = 'forum.lock'

# Thread index file name
INDEX_NAME = 'index.txt'

# Thread helper file name
THREAD_NAME = 'thread'
SUBSCRIBER_NAME = 'subscribe'
VISITED_NAME = 'visited'

# How dates are stored (see python time module for details)
DATE_FORMAT = '%d %b %Y %H:%M:%S'

# Maximum lengths for subjects and message bodies.
# (currently we chop them off without warning)
MAX_SUBJECT_LEN = 100
MAX_BODY_LEN = 10000

HASH_LENGTH = len(md5_hash('dummy').hexdigest())

ERR_INVALID_THREAD = 'Invalid Thread Specified'
ERR_NO_SUBJECT = 'No Subject Given'
ERR_NO_BODY = 'No body text!'


def get_thread_path(data_dir, hash_string):
    """build thread path from data_dir and hash_string"""
    return os.path.join(data_dir, "%s-%s" % (THREAD_NAME, hash_string))

def get_visited_path(data_dir, hash_string):
    """build visited path from data_dir and hash_string"""
    return os.path.join(data_dir, "%s-%s" % (VISITED_NAME, hash_string))

def get_subscriber_path(data_dir, hash_string=''):
    """build index path from data_dir and optional hash_string"""
    if hash_string:
        suffix = hash_string
    else:
        suffix = 'index'
    return os.path.join(data_dir, "%s-%s" % (SUBSCRIBER_NAME, suffix))

def get_index_path(data_dir):
    """build index path from data_dir"""
    return os.path.join(data_dir, INDEX_NAME)

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
    if len(hash_string) != HASH_LENGTH:
        return False
    if not os.path.exists(get_thread_path(data_dir, hash_string)):
        return False
    return True

def read_common(path):
    """Load list of common single line entries"""
    try:
        common_file = file(path, 'r')
        common = [i.strip() for i in common_file.readlines()]
        common_file.close()
    except:
        common = []
    return common

def read_visited(data_dir, author):
    """Load list of thread visits for author"""
    path = get_visited_path(data_dir, md5_hash(author).hexdigest())
    return read_common(path)

def read_subscribers(data_dir, thread_hash):
    """Load list of subscribers to index or thread identified by thread_hash.
    If thread_hash is empty it means entire thread index.
    """
    return read_common(get_subscriber_path(data_dir, thread_hash))

def read_threads(data_dir):
    """Load list of threads"""
    return read_common(get_index_path(data_dir))

def read_messages(data_dir, thread_hash):
    """Load list of messages in thread identified by thread_hash"""
    return read_common(get_thread_path(data_dir, thread_hash))

def write_common(path, lines):
    """Save list of lines to common flat file in path"""
    common_file = file(path, 'w')
    common_file.write('\n'.join(lines))
    common_file.close()

def write_visited(data_dir, author, visited):
    """Write list of thread visits to for author"""
    path = get_visited_path(data_dir, md5_hash(author).hexdigest())
    return write_common(path, visited)

def write_subscribers(data_dir, thread_hash, subscribers):
    """Write list of subscribers to the subscribers file for index or
    thread_hash. If thread_hash is empty it means thread index.
    """
    path = get_subscriber_path(data_dir, thread_hash)
    return write_common(path, subscribers)

def write_threads(data_dir, threads):
    """Write list of threads to index file"""
    path = get_index_path(data_dir)
    return write_common(path, threads)

def write_messages(data_dir, thread_hash, messages):
    """Write list of messages to thread file"""
    path = get_thread_path(data_dir, thread_hash)
    return write_common(path, messages)

def append_common(path, line):
    """Append line to common flat file in path. Includes file creation if path
    doesn't exits already.
    """
    try:
        common_file = file(path, 'a')
    except:
        common_file = file(path, 'w')
    common_file.write(line)
    common_file.close()


def update_timestamp(visited, thread_hash):
    """Update visited time stamp on thread identified by thread_hash"""
    found = False
    new_entry = "%s\t%s" % (thread_hash, time.strftime(DATE_FORMAT))
    for i in range(len(visited)):
        if visited[i].startswith(thread_hash):
            visited[i] = new_entry
            found = True
    if not found:
        visited.append(new_entry)
    return visited

def parse_visited(visited):
    """Create a dictionary mapping thread_hash values to time stamps by
    parsing the lines in visited list.
    """
    visit_map = {}
    for line in visited:
        parts = line.strip().split('\t')
        if len(parts) != 2:
            continue
        visit_map[parts[0]] = parts[1]
    return visit_map

def check_new_messages(visit_map, thread_hash, last_update):
    """Check if thread identified by thread_hash contains new messages.
    I.e. if visit_map time stamp for the thread is older than last_update.
    """
    if thread_hash in visit_map:
        last_visit_time = time.strptime(visit_map[thread_hash],
                                        DATE_FORMAT)
    else:
        last_visit_time = 0
    last_update_time = time.strptime(last_update, DATE_FORMAT)
    if last_update_time <= last_visit_time:
        return False
    else:
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
    threads = read_threads(data_dir)
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
    write_threads(data_dir, new_threads)

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
    messages = read_messages(data_dir, key)
    if not messages:
        messages.append('%s\t%s' % (key, subject))
    messages.append('%s\t%s\t%s' % (date, author, body))
    write_messages(data_dir, key, messages)

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
    subscribers = read_subscribers(data_dir, key)
    return [line.strip() for line in subscribers]

def toggle_subscribe(data_dir, author, key=''):
    """Toggle notification about new messages for author, by updating the
    corresponding subscriber file.

    author, key - Strings
    """
    subscribers = read_subscribers(data_dir, key)
    if key:
        subscribe_type = 'thread'
    else:
        subscribe_type = 'forum'
    if author in subscribers:
        subscribers.remove(author)
        out = 'Succesfully unsubscribed from %s updates' % subscribe_type
    else:
        subscribers.append(author)
        out = '''Succesfully subscribed any addresses from your personal
settings to %s updates''' % subscribe_type
    write_subscribers(data_dir, key, subscribers)
    return out

def list_threads(data_dir, author):
    """List the existing threads."""
    thread_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    threads = read_threads(data_dir)
    visited = read_visited(data_dir, author)
    lock_handle.close()

    visit_map = parse_visited(visited)
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
        new_messages = check_new_messages(visit_map, thread_hash, last_update)
        entry = {'subject': subject, 'link': url, 'author': author, 'date':
                 date, 'replies': num_replies, 'last': last_update, 'new':
                 new_messages}
        thread_list.append(entry)
    return thread_list


def list_single_thread(data_dir, thread_hash, author):
    """Output the HTML for a given thread id"""
    message_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    messages = read_messages(data_dir, thread_hash)
    visited = read_visited(data_dir, author)
    visit_map = parse_visited(visited)
    update_timestamp(visited, thread_hash)
    write_visited(data_dir, author, visited)
    lock_handle.close()

    if not messages:
        raise ValueError(ERR_INVALID_THREAD)
    # The first item in the file is actually the hash and the subject. But we
    # don't need it really.
    _, subject = messages.pop(0).split('\t')
    for line in messages:
        split_line = line.split('\t')
        if len(split_line) != 3:
            continue

        date, author, body = split_line
        new_message = check_new_messages(visit_map, thread_hash, date)
        entry = {'subject': subject, 'author': author, 'date': date, 'body':
                 body.decode('string_escape'), 'new': new_message}
        message_list.append(entry)
    return message_list

def search_threads(data_dir, subject, body, author=""):
    """Search the existing threads."""
    thread_list = []
    lock_handle = open(get_lock_path(data_dir), 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
    threads = read_threads(data_dir)
    visited = read_visited(data_dir, author)
    lock_handle.close()

    visit_map = parse_visited(visited)
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
        new_messages = check_new_messages(visit_map, thread_hash, last_update)
        entry = {'subject': subject, 'link': url, 'author': author, 'date':
                 date, 'replies': num_replies, 'last': last_update, 'new':
                 new_messages}
        thread_list.append(entry)
    return thread_list
