#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# parsecsvusers - parse csv user file and generate user ID list for importusers
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

"""Read a csv-format list of users and output a corresponding list of
distinguished name entries for direct use in the importusers script.
The csv file must use semi-colon as a separator and include a special header
line to define the format of the remaining user lines using a subset of the
MiG user database ID field names. As an example the csv file could contain:
### full_name;email;organization;country
Jonas Bardino;bardino@nbi.ku.dk;NBI;DK

and this script would then generate the user ID list:
/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk
which could be used with importusers.py to create that user with a random
password.

Use e.g. as in
./parsecsvusers.py participants.csv > import-participants.list
then import with something like
./importusers.py [OPTIONS] import-participants.list
where OPTIONS might include things like generate password, automatic account
expire time and workgroup membership.
Afterwards one would then typically use notifymigoid and notifypassword to
inform imported users about their login.
"""
from __future__ import print_function
from __future__ import absolute_import

import fileinput

from mig.shared.base import fill_distinguished_name

if __name__ == '__main__':
    user_list = []
    # First line is header to specify field contents and order
    sep = ';'
    user_fields = None
    for line in fileinput.input():
        if user_fields is None:
            # Parse header and clean any stray white space from field names
            line = line.strip('###').strip()
            user_fields = [i.strip() for i in line.split(sep)]
            #print "DEBUG: found header fields: %s" % user_fields
            continue
        user_parts = [i.strip() for i in line.split(sep)]
        user_dict = dict(zip(user_fields, user_parts))
        # Force email to lowercase to avoid case-sensitive login issues
        if user_dict.get('email', False):
            user_dict['email'] = user_dict['email'].lower()
        #print "DEBUG: found user: %s" % user_dict
        fill_distinguished_name(user_dict)
        user_id = user_dict['distinguished_name']
        if not user_id in user_list:
            user_list.append(user_id)
    for user in user_list:
        print('%s' % user)
