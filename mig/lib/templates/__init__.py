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

import errno
from jinja2 import meta as jinja2_meta, select_autoescape, Environment, \
    FileSystemLoader, FileSystemBytecodeCache
import os
import weakref

from mig.shared.compat import PY2
from mig.shared.defaults import MIG_BASE


if PY2:
    from chainmap import ChainMap
else:
    from collections import ChainMap

TEMPLATES_DIR = os.path.join(MIG_BASE, 'mig/assets/templates')
TEMPLATES_CACHE_DIR = os.path.join(TEMPLATES_DIR, '__jinja__')

_all_template_dirs = [
    TEMPLATES_DIR,
]
_global_store = None


def _clear_global_store():
    global _global_store
    _global_store = None


def cache_dir():
    return TEMPLATES_CACHE_DIR


def template_dirs():
    return _all_template_dirs


class _BonundTemplate:
    def __init__(self, template, template_args):
        self.tmpl = template
        self.args = template_args


    def render(self):
        return self.tmpl.render(**self.args)


class _FormatContext:
    def __init__(self, configuration):
        self.output_format = None
        self.configuration = configuration
        self.script_map = {}
        self.style_map = {}

    def __getitem__(self, key):
        return self.__dict__[key]

    def __iter__(self):
        return iter(self.__dict__)

    def extend(self, template, template_args):
        return _BonundTemplate(template, ChainMap(template_args, self))


class TemplateStore:
    def __init__(self, template_dirs, cache_dir=None, extra_globals=None):
        assert cache_dir is not None

        self._cache_dir = cache_dir
        self._template_globals = extra_globals
        self._template_environment = Environment(
            loader=FileSystemLoader(template_dirs),
            bytecode_cache=FileSystemBytecodeCache(cache_dir, '%s'),
            autoescape=select_autoescape()
        )

    @property
    def cache_dir(self):
        return self._cache_dir

    @property
    def context(self):
        return self._template_globals

    def _get_template(self, template_fqname):
        return self._template_environment.get_template(template_fqname)

    def grab_template(self, template_name, template_group, output_format, template_globals=None, **kwargs):
        template_fqname = "%s_%s.%s.jinja" % (
            template_group, template_name, output_format)
        return self._template_environment.get_template(template_fqname, globals=template_globals)

    def list_templates(self):
        return [t for t in self._template_environment.list_templates() if t.endswith('.jinja')]

    def extract_variables(self, template_fqname):
        template = self._template_environment.get_template(template_fqname)
        with open(template.filename) as f:
            template_source = f.read()
        ast = self._template_environment.parse(template_source)
        return jinja2_meta.find_undeclared_variables(ast)

    @staticmethod
    def populated(template_dirs, cache_dir=None, context=None):
        assert cache_dir is not None

        try:
            os.mkdir(cache_dir)
        except OSError as direxc:
            if direxc.errno != errno.EEXIST:  # FileExistsError
                raise

        store = TemplateStore(
            template_dirs, cache_dir=cache_dir, extra_globals=context)

        for template_fqname in store.list_templates():
            store._get_template(template_fqname)

        return store


def init_global_templates(configuration, _templates_dirs=template_dirs):
    global _global_store

    if _global_store is not None:
        return _global_store

    _global_store = TemplateStore.populated(
        _templates_dirs(),
        cache_dir=cache_dir(),
        context=_FormatContext(configuration)
    )

    return _global_store
