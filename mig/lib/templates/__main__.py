#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# templates/__main__ - templates CLI
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""
Template support CLI code.
"""

import sys

from mig.lib.templates import TemplateStore
from mig.shared.conf import get_configuration_object


def warn(*messages):
    print(*messages, file=sys.stderr, flush=True)


def main(args, _print=print):
    configuration = get_configuration_object(
        config_file=args.config_file, skip_log=True, disable_auth_log=True
    )
    template_store = TemplateStore.from_configuration(configuration)

    command = args.command
    if command == "cache":
        templates_division = configuration.division(section_name="TEMPLATES")
        _print(templates_division.cache_dir)
    elif command == "show":
        _print(template_store.list_templates())
    elif command == "prime":
        primed_count = template_store.prime_templates()
        if primed_count == 0:
            _print("No templates were specified.")
    elif command == "vars":
        for template_name, template_group in template_store.list_templates():
            template_vars = template_store.extract_variables(
                template_name, template_group, "html"
            )
            _print("<%s.%s>" % (template_group, template_name))
            for var in template_vars:
                _print("  {{%s}}" % (var,))
            _print("</%s.%s>" % (template_group, template_name))
    else:
        raise RuntimeError("unknown command: %s" % (command,))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", dest="config_file", required=True)
    parser.add_argument("command")
    args = parser.parse_args()

    try:
        main(args)
        sys.exit(0)
    except Exception as exc:
        warn(type(exc).__name__, str(exc))
        sys.exit(1)
