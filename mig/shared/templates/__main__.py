#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

from types import SimpleNamespace
import os
import sys

from mig.shared.templates import cache_dir, \
    _get_template, _grab_template_vars, _template_environment


def warn(message):
    print(message, file=sys.stderr, flush=True)


def main(args, _print=print):
    command = args.command

    if command == 'show':
        print(_template_environment.list_templates())
    elif command == 'prime':
        try:
            os.mkdir(cache_dir())
        except FileExistsError:
            pass

        for template_name in _list_templates():
            _get_template(template_name)
    elif command == 'vars':
        for template_ref in _template_environment.list_templates():
            _print("<%s>" % (template_ref,))
            for var in _grab_template_vars(template_ref):
                _print("  %s" % (var,))
    else:
        raise RuntimeError("unknown command: %s" % (command,))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        command = sys.argv[1]
    else:
        command = 'show'
    args = SimpleNamespace(command=command)

    try:
        main(args)
        sys.exit(0)
    except Exception as exc:
        warn(str(exc))
        sys.exit(1)
