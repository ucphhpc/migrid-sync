#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# projcode - simple helpers for transforming or searching project code
# Copyright (C) 2009-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Helpers to transform or search project code files."""

from mig.shared.defaults import keyword_all

# TODO: phase out lowercase names once all scripts switched to list_code_files

# Top dir with all code
code_root = "mig"
CODE_ROOT = code_root

# Ignore backup and dot files in wild card match
PLAIN = "[a-zA-Z0-9]*.py"
py_code_files = [
    # a few scripts are in parent dir of code_root
    "../%s" % PLAIN,
    "../bin/%s" % PLAIN,
    "../sbin/%s" % PLAIN,
    "%s" % PLAIN,
    "lib/%s" % PLAIN,
    "cgi-bin/%s" % PLAIN,
    "cgi-sid/%s" % PLAIN,
    "install/%s" % PLAIN,
    "migfs-fuse/%s" % PLAIN,
    "resource/bin/%s" % PLAIN,
    "resource/image-scripts/%s" % PLAIN,
    "resource/keepalive-scripts/%s" % PLAIN,
    "server/%s" % PLAIN,
    "shared/%s" % PLAIN,
    "shared/functionality/%s" % PLAIN,
    "shared/distos/%s" % PLAIN,
    "shared/gdp/%s" % PLAIN,
    "shared/griddaemons/%s" % PLAIN,
    "simulation/%s" % PLAIN,
    "user/%s" % PLAIN,
    "vm-proxy/%s" % PLAIN,
    "webserver/%s" % PLAIN,
    "wsgi-bin/%s" % PLAIN,
]
py_code_files += [
    "cgi-sid/%s" % name for name in ["requestnewjob", "putrespgid"]
]

py_code_files += [
    "cgi-bin/%s" % name
    for name in [
        "listdir",
        "mkdir",
        "put",
        "remove",
        "rename",
        "rmdir",
        "stat",
        "walk",
        "getrespgid",
    ]
]
PY_CODE_FILES = py_code_files

sh_code_files = [
    "resource/frontend_script.sh",
    "resource/master_node_script.sh",
    "resource/leader_node_script.sh",
    "resource/dummy_node_script.sh",
]
SH_CODE_FILES = sh_code_files

js_code_files = [
    "images/js/jquery.accountform.js",
    "images/js/jquery.ajaxhelpers.js",
    "images/js/jquery.confirm.js",
    "images/js/jquery.filemanager.js",
    "images/js/jquery.jobmanager.js",
    "images/js/jquery.migtools.js",
    "images/js/jquery.prettyprint.js",
    "images/js/preview-caman.js",
    "images/js/preview.js",
    "images/js/preview-paraview.js",
    "assets/js/shared/ui-dynamic.js",
    "assets/js/V3/ui-global.js",
    "assets/js/V3/ui-extra.js",
]
JS_CODE_FILES = js_code_files

code_files = py_code_files + sh_code_files + js_code_files
CODE_FILES = code_files

PYTHON, SHELL, JAVASCRIPT = "PYTHON", "SHELL", "JAVASCRIPT"
LANG_MAP = {
    keyword_all: CODE_FILES,
    PYTHON: PY_CODE_FILES,
    JAVASCRIPT: JS_CODE_FILES,
    SHELL: SH_CODE_FILES,
}


def list_code_files(code_langs=[keyword_all]):
    """Get list of all code files."""
    match = []
    for lang in code_langs:
        if lang not in LANG_MAP:
            print("Warning: no such code lang: %s" % lang)
        else:
            match += LANG_MAP[lang]
    return match
