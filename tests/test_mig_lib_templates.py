# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_templates - unit tests of core templates logic
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
# --- END_HEADER ---
#

import importlib
import os
import shutil
import sys
from types import SimpleNamespace

from jinja2 import Template

from mig.lib.templates import (
    TemplateStore,
    MissingCacheDirError,
    UnknownTemplateError,
    init_global_templates,
)
from mig.shared.conf import get_configuration_object
from tests.support import (
    MIG_BASE,
    TEST_DATA_DIR,
    TEST_OUTPUT_DIR,
    MigTestCase,
    testmain,
)

TEST_BASE_PACKAGES = ["testplugin"]
TEST_TEMPLATE_CACHE_DIR = os.path.join(TEST_OUTPUT_DIR, "__template_cache__")


def noop(*args):
    pass


class TestMigSharedTemplates_instance(MigTestCase):

    def before_each(self):
        # make template cache directory
        os.makedirs(TEST_TEMPLATE_CACHE_DIR)

        # allow the dummy plugin to be loaded
        sys.path.append(TEST_DATA_DIR)
        self._register_check(lambda: sys.path.pop())

    def _provide_configuration(self):
        return "testconfig"

    def test_creation_of_a_template_store(self):
        store = TemplateStore.from_names(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )
        self.assertIsInstance(store, TemplateStore)

    def test_creation_of_a_template_store_should_expand_packages(self):
        store = TemplateStore.from_names(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )
        self.assertEqual(store._packages, ["testplugin", "testplugin.inner"])

    def test_grab_template(self):
        store = TemplateStore.from_names(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )
        template = store.grab_template(
            "inner_template", "testplugin.inner", "html"
        )
        self.assertIsInstance(template, Template)

    def test_extract_variables(self):
        store = TemplateStore.from_names(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )
        template_vars = store.extract_variables(
            "inner_template", "testplugin.inner", "html"
        )
        self.assertEqual(template_vars, set(["inner_variable"]))

    def test_extract_variables_empty(self):
        store = TemplateStore.from_names(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )
        template_vars = store.extract_variables(
            "test_empty", "testplugin", "html"
        )
        self.assertEqual(template_vars, set())

    def test_extract_variables_umprimed(self):
        store = TemplateStore(
            TEST_BASE_PACKAGES, cache_dir=TEST_TEMPLATE_CACHE_DIR
        )

        with self.assertRaises(UnknownTemplateError) as raised:
            store.extract_variables(
                "inner_template", "testplugin.inner", "html"
            )
        theexception = raised.exception
        self.assertEqual(str(theexception), "testplugin.inner.*")


class TestMigSharedTemplates_instance_with_configuration(MigTestCase):

    def test_specified_base_packages(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--templates.conf"
        )
        configuration = get_configuration_object(
            test_conf_file, skip_log=True, disable_auth_log=True
        )

        store = init_global_templates(configuration)

        self.assertEqual(
            store.list_templates(),
            [
                ("test_empty", "testplugin"),
                ("test_other", "testplugin"),
                ("test_something", "testplugin"),
                ("inner_template", "testplugin.inner"),
            ],
        )

    def test_specified_cache_dir(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--templates.conf"
        )
        configuration = get_configuration_object(
            test_conf_file, skip_log=True, disable_auth_log=True
        )

        store = init_global_templates(configuration)

        self.assertEqual(store.cache_dir, TEST_TEMPLATE_CACHE_DIR)

    def test_configuration_from_generate_confs(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--default_templates.conf"
        )
        configuration = get_configuration_object(
            test_conf_file, skip_log=True, disable_auth_log=True
        )

        store = init_global_templates(configuration)

        self.assertEqual(
            store.list_templates(), []
        )


class TestMigSharedTemplates_cli(MigTestCase):

    TEMPLATES_CLI = importlib.import_module("mig.lib.templates.__main__")

    def before_each(self):
        # allow the dummy plugin to be loaded
        sys.path.append(TEST_DATA_DIR)
        self._register_check(lambda: sys.path.pop())

    def after_each(self):
        # clean up the configuration file specified cache directory
        shutil.rmtree(TEST_TEMPLATE_CACHE_DIR, ignore_errors=True)
        pass

    def test_command_cache(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--templates.conf"
        )
        args = SimpleNamespace(config_file=test_conf_file, command="cache")
        last_printed_line = None

        def _print(value):
            nonlocal last_printed_line
            last_printed_line = value

        self.TEMPLATES_CLI.main(args, _print=_print)

        self.assertEqual(last_printed_line, TEST_TEMPLATE_CACHE_DIR)

    def test_command_prime(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--templates.conf"
        )
        args = SimpleNamespace(config_file=test_conf_file, command="prime")
        lines_printed = []

        def _print(value):
            nonlocal lines_printed
            lines_printed.append(value)

        self.TEMPLATES_CLI.main(args, _print=_print)

        self.assertTrue(len(os.listdir(TEST_TEMPLATE_CACHE_DIR)) > 0)

    def test_command_vars_missing_cache_dir(self):
        test_conf_file = os.path.join(
            TEST_DATA_DIR, "MiGserver--templates.conf"
        )
        args = SimpleNamespace(config_file=test_conf_file, command="vars")

        def _print(value):
            pass

        with self.assertRaises(MissingCacheDirError) as raised:
            self.TEMPLATES_CLI.main(args, _print=_print)


if __name__ == "__main__":
    testmain()
