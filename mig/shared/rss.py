#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rss - RSS feed generator functions
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

"""RSS generator helper functions"""


import datetime
try:
    import PyRSS2Gen as rssgen
except ImportError:
    rssgen = None


rss_defaults = {'title': 'no title', 'link': '', 'description': '',
                'css_url': 'rss.css', 'docs': 'no docs',
                'publish_date': datetime.datetime.now(), 'guid': None,
                'build_date': datetime.datetime.now(), 'entries': []}

def append_rss_items(rss_feed, items):
    """Append items to rss feed object"""
    if not rssgen:
        return None
    for raw_entry in items:
        entry = rss_defaults.copy()
        entry.update(raw_entry)
        item = rssgen.RSSItem(
            title=entry["title"],
            link=entry["link"],
            description=entry["description"],
            guid=rssgen.Guid(entry["guid"]),
            pubDate=entry["publish_date"])
        rss_feed.items.append(item)
    return rss_feed

def create_rss_feed(contents):
    """Create rss feed object from contents dictionary"""
    if not rssgen:
        return None

    filled = rss_defaults.copy()
    filled.update(contents)
    filled['items'] = []
    rss = rssgen.RSS2(
        title=filled["title"],
        link=filled["link"],
        description=filled["description"],
        lastBuildDate=filled["build_date"],
        items=filled["items"],
        docs=filled["docs"])
    append_rss_items(rss, contents['entries'])
    return rss

def write_rss_feed(rss_feed, destination, insert_header=''):
    """Write rss feed object in destination file"""
    if not rssgen:
        return None

    feed = open(destination, 'w+')
    rss_feed.write_xml(feed)
    if insert_header:
        # Insert header right after initial xml declaration line
        feed.seek(0)
        output = []
        output.append(feed.readline())
        css = insert_header
        output.append(css)
        output += feed.readlines()
        feed.truncate(0)
        feed.seek(0)
        feed.writelines(output)
    feed.close()
    return rss_feed


if __name__ == "__main__":
    feed_base = "demofeed"
    feed_raw = "%s.xml" % feed_base
    feed_css_style = "%s.css" % feed_base
    feed_page = "%s.html" % feed_base
    entries = [{'title': 'Dashboard page',
                'link': 'https://dk.migrid.org/cgi-bin/dashboard.py',
                'guid': 'https://dk.migrid.org/cgi-bin/dashboard.py',
                'description': 'MiG user dashboard page'},
               {'title': 'Docs page',
                'link': 'https://dk.migrid.org/cgi-bin/docs.py',
                'guid': 'https://dk.migrid.org/cgi-bin/docs.py',
                'description': 'MiG user docs page'}]
    data = {'title': 'Demo feed', 'link': 'demofeed.xml', 'docs': 'Demo output',
            'css_url': feed_css_style, 'description': 'MiG demo feed',
            'entries': entries}
    rss_feed = create_rss_feed(data)
    #css_header = '<?xml-stylesheet href="%(css_url)s" type="text/css" media="screen"?>\n' % data
    css_header = ''
    write_rss_feed(rss_feed, feed_raw, insert_header=css_header)
    css_stylesheet = '''
rss {
display: block;
font-family: verdana, arial;
}
title {
display: block;
margin: 5px;
padding: 2px;
color: gray;
border-bottom: 1px solid silver;
}
link {
display: block;
font-size: small;
padding-left: 10px;
}
item {
display: block;
padding: 2px 30px 2px 30px;
}
docs {
display: block;
background-color: #ffffe6;
margin: 20px;
text-align: center;
padding: 5px;
color: #7f7f7f;
border: 1px solid silver;
}
/* all hidden elements */
language, lastBuildDate, ttl, guid, category, description, pubDate, generator {
display: none;
}
'''
    css_style = open(feed_css_style, "w")
    css_style.write(css_stylesheet)
    css_style.close()
    html = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<link rel="alternate" type="application/rss+xml" title="Demo RSS Feed" href="%s" />
</head>
<body>
<h1>A simple demo page</h1>
Used to display demo rss feed through the browser location bar.
</body>
</html>
''' % feed_raw
    page = open(feed_page, "w")
    page.write(html)
    page.close()
