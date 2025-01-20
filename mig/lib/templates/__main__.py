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

from mig.lib.templates import init_global_templates
from mig.shared.conf import get_configuration_object


def warn(message):
    print(message, file=sys.stderr, flush=True)


def main(args, _print=print):
    configuration = get_configuration_object(config_file=args.config_file)
    template_store = init_global_templates(configuration)

    command = args.command
    if command == 'show':
        print(template_store.list_templates())
    elif command == 'prime':
        try:
            os.mkdir(template_store.cache_dir)
        except FileExistsError:
            pass

        for template_fqname in template_store.list_templates():
            template_store._get_template(template_fqname)
    elif command == 'vars':
        for template_ref in template_store.list_templates():
            _print("<%s>" % (template_ref,))
            for var in template_store.extract_variables(template_ref):
                _print("  {{%s}}" % (var,))
            _print("</%s>" % (template_ref,))
    else:
        raise RuntimeError("unknown command: %s" % (command,))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest='config_file', default=None)
    parser.add_argument('command')
    args = parser.parse_args()

    try:
        main(args)
        sys.exit(0)
    except Exception as exc:
        warn(str(exc))
        sys.exit(1)
