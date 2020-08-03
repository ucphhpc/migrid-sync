#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# projcode - simple helpers for transforming or searching project code
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

"""Helpers to transform or search project code files"""

# Top dir with all code
code_root = 'mig'

# Ignore backup and dot files in wild card match
plain = '[a-zA-Z0-9]*.py'
py_code_files = [
    # a few scripts are in parent dir of code_root
    '../%s' % plain,
    '%s' % plain,
    'cgi-bin/%s' % plain,
    'cgi-sid/%s' % plain,
    'wsgi-bin/%s' % plain,
    'install/%s' % plain,
    'migfs-fuse/%s' % plain,
    'resource/bin/%s' % plain,
    'resource/image-scripts/%s' % plain,
    'resource/keepalive-scripts/%s' % plain,
    'server/%s' % plain,
    'shared/%s' % plain,
    'shared/functionality/%s' % plain,
    'shared/distos/%s' % plain,
    'simulation/%s' % plain,
    'user/%s' % plain,
    'vm-proxy/%s' % plain,
    'webserver/%s' % plain,
    'wsgi-bin/%s' % plain,
]
py_code_files += ['cgi-sid/%s' % name for name in ['requestnewjob',
                                                   'putrespgid']]

py_code_files += ['cgi-bin/%s' % name for name in [
    'listdir',
    'mkdir',
    'put',
    'remove',
    'rename',
    'rmdir',
    'stat',
    'walk',
    'getrespgid',
]]
sh_code_files = [
    'resource/frontend_script.sh',
    'resource/master_node_script.sh',
    'resource/leader_node_script.sh',
    'resource/dummy_node_script.sh',
]
js_code_files = [
    'images/js/jquery.accountform.js',
    'images/js/jquery.ajaxhelpers.js',
    'images/js/jquery.confirm.js',
    'images/js/jquery.filemanager.js',
    'images/js/jquery.jobmanager.js',
    'images/js/jquery.migtools.js',
    'images/js/jquery.prettyprint.js',
    'images/js/preview-caman.js',
    'images/js/preview.js',
    'images/js/preview-paraview.js',
    'assets/js/shared/ui-dynamic.js',
    'assets/js/V3/ui-global.js',
    'assets/js/V3/ui-extra.js',
]
code_files = py_code_files + sh_code_files + js_code_files
