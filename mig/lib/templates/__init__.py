# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# templates/__init__ - main logic for template support
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
Template support library code.
"""

import importlib
import os
from operator import itemgetter

from jinja2 import (
    Environment,
    FileSystemBytecodeCache,
    PackageLoader,
    Template,
    TemplateNotFound,
)
from jinja2 import meta as jinja2_meta
from jinja2 import (
    select_autoescape,
)


def _expand_base_packages(base_packages):
    template_packages = []
    for package_name in base_packages:
        try:
            package = importlib.import_module(package_name)
        except (ImportError, ModuleNotFoundError):
            raise UnknownTemplateError(package_name)
        template_packages.extend(package.TEMPLATE_PACKAGES)
    return template_packages


def _strip_template_ext(template_name_with_ext):
    return os.path.splitext(os.path.splitext(template_name_with_ext)[0])[0]


class _NoopContext:
    """
    Adapter class to allow templates to be directly rendered.

    Note that this is in contrast to further work making use of the
    same provisions that allows the selection of translations.
    """

    def __init__(self, *args):
        self._tmpl = None
        self._tmpl_args = None

    def extend(self, template, template_args):
        self._tmpl = template
        self._tmpl_args = template_args
        return self

    def render(self):
        return self._tmpl.render(**self._tmpl_args)


class TemplateStore:
    """
    An abstraction for interacting with an enable series of template packages.
    """

    def __init__(self, packages, cache_dir=None, extra_globals=None):
        assert cache_dir is not None

        self._packages = packages
        self._cache_dir = cache_dir
        self._template_globals = extra_globals
        self._template_env_by_package = {}

    @property
    def cache_dir(self):
        return self._cache_dir

    @property
    def context(self):
        return self._template_globals

    def _env_for_package(self, package_name):
        """
        Direct access to a jinja2 Environment for a package exposing templates.
        """

        if package_name not in self._packages:
            raise UnknownTemplateError(package_name)

        if package_name in self._template_env_by_package:
            return self._template_env_by_package[package_name]

        package_cache_key = "%s-%%s.jinja_cache" % (package_name,)
        template_env = Environment(
            loader=PackageLoader(package_name),
            bytecode_cache=FileSystemBytecodeCache(self._cache_dir, package_cache_key),
            autoescape=select_autoescape(),
        )
        self._template_env_by_package[package_name] = template_env
        return template_env

    def grab_template(
        self,
        template_name,
        template_group,
        output_format,
        template_globals=None,
        **kwargs
    ):
        """
        Directly access an enabled template.
        """

        template_env = self._env_for_package(template_group)
        template_fqname = "%s.%s.jinja" % (template_name, output_format)
        try:
            return template_env.get_template(
                template_fqname, globals=template_globals
            )
        except FileNotFoundError:
            if not os.path.exists(self.cache_dir):
                raise MissingCacheDirError(self.cache_dir)
            raise UnknownTemplateError(template_group, template_name)

    def list_templates(self):
        """
        Return a list of templates for all enabled packages.
        """

        template_and_group_pairs = []
        for template_group in self._packages:
            template_env = self._env_for_package(template_group)
            pairs = (
                (_strip_template_ext(template), template_group)
                for template in template_env.list_templates()
            )
            template_and_group_pairs.extend(pairs)
        template_and_group_pairs.sort(key=itemgetter(1, 0))
        return template_and_group_pairs

    def list_templates_groups(self):
        """
        Return the set of enabled packages that expose templates.
        """

        nonunique_template_groups = (
            template_group for _, template_group in self.list_templates()
        )
        return set(nonunique_template_groups)

    def prime_templates(self):
        """
        Precompile all templates across the enabled packages.
        """

        os.makedirs(self.cache_dir, exist_ok=True)

        primed_count = 0

        for template_name, template_group in self.list_templates():
            primed_count += 1
            self.grab_template(template_name, template_group, "html")

        return primed_count

    def extract_variables(
        self,
        template_or_name,
        template_group,
        output_format=None,
        template_globals=None,
    ):
        """
        Return the expected variables for a given template.
        """

        template_env = self._env_for_package(template_group)
        if isinstance(template_or_name, Template):
            raise NotImplementedError()
        else:
            template = self.grab_template(
                template_or_name,
                template_group,
                output_format,
                globals=template_globals,
            )
        with open(template.filename) as f:
            template_source = f.read()
        ast = template_env.parse(template_source)
        return jinja2_meta.find_undeclared_variables(ast)

    @staticmethod
    def from_configuration(configuration):
        """
        Create a TemplateStore instance for a specified configuration.
        """

        template_division = configuration.division(section_name="TEMPLATES")

        return TemplateStore.from_names(
            template_division.base_packages,
            cache_dir=template_division.cache_dir,
            context=_NoopContext(configuration),
        )

    @staticmethod
    def from_names(template_packages, *, cache_dir=None, context=None):
        """
        Create a template store from a list of package names.
        """

        assert cache_dir is not None
        if context is None:
            context = _NoopContext()

        packages = _expand_base_packages(template_packages)

        return TemplateStore(
            packages,
            cache_dir=cache_dir,
            extra_globals=context,
        )


def init_global_templates(runtime_configuration):
    """
    Make a TemplateStore available within the active request context.
    """

    store = runtime_configuration.context_get("templates")
    if store:
        return store
    store = TemplateStore.from_configuration(runtime_configuration)
    runtime_configuration.context_set("templates", store)
    return store


def render_html_template(
    runtime_configuration, template_name, template_group, template_args
):
    """
    Render a template available within the active request context.
    """

    store = init_global_templates(runtime_configuration)
    template = store.grab_template(template_name, template_group, "html")
    bound = store.context.extend(template, template_args)
    return bound.render()


class MissingCacheDirError(RuntimeError):
    def __init__(self, cache_dir):
        super().__init__(cache_dir)


class UnknownTemplateError(TemplateNotFound):
    def __init__(self, template_group, template_name="*"):
        super().__init__("%s.%s" % (template_group, template_name))
