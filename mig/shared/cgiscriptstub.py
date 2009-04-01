#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgiscriptstub - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

""" Interface between CGI and functionality """

import cgi
import cgitb
cgitb.enable()

from shared.cgiinput import fieldstorage_to_dict
from shared.cgishared import init_cgi_script_with_cert, \
    init_cgiscript_possibly_with_cert

from shared.output import do_output


def run_cgi_script(main):
    """ Get needed information and run the function received as argument """

    (logger, configuration, cert_name_no_spaces, o) = \
        init_cgi_script_with_cert()
    fieldstorage = cgi.FieldStorage()

    user_arguments_dict = fieldstorage_to_dict(fieldstorage)
    (out_obj, (ret_code, ret_msg)) = main(cert_name_no_spaces,
                                          user_arguments_dict)

    # default to html

    output_format = 'html'
    if user_arguments_dict.has_key('output_format'):
        output_format = user_arguments_dict['output_format'][0]

    if not do_output(ret_code, ret_msg, out_obj, output_format):

        # Error occured during output print

        print 'Return object was _not_ successfully printed!'


def run_cgi_script_possibly_with_cert(main):
    """ Get needed information and run the function received as argument """

    (logger, configuration, cert_name_no_spaces, o) = \
        init_cgiscript_possibly_with_cert()
    fieldstorage = cgi.FieldStorage()

    user_arguments_dict = fieldstorage_to_dict(fieldstorage)
    (out_obj, (ret_code, ret_msg)) = main(cert_name_no_spaces,
            user_arguments_dict)

    # default to html

    output_format = 'html'
    if user_arguments_dict.has_key('output_format'):
        output_format = user_arguments_dict['output_format'][0]

    if not do_output(ret_code, ret_msg, out_obj, output_format):

        # Error occured during output print

        print 'Return object was _not_ successfully printed!'


