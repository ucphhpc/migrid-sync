#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# testworkflows.py - Set of unittests for workflows.py
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

"""Unittest to verify the functionality of the workflows implementation"""

from builtins import next
import os
import shutil
import tempfile
import unittest
import nbformat

from mig.shared.conf import get_configuration_object
from mig.shared.defaults import default_vgrid
from mig.shared.events import get_path_expand_map
from mig.shared.fileio import makedirs_rec, remove_rec, unpickle
from mig.shared.job import fill_mrsl_template
from mig.shared.mrslparser import parse
from mig.shared.serial import load
from mig.shared.vgrid import vgrid_set_triggers
from mig.shared.workflows import reset_workflows, WORKFLOW_PATTERN, \
    WORKFLOW_RECIPE, WORKFLOW_ANY, get_workflow_with, \
    delete_workflow, create_workflow, update_workflow, \
    get_workflow_trigger, get_task_parameter_path


def parse_trigger_lines(trigger_lines):
    trigger_dict = {}
    key = ''
    for line in trigger_lines:
        if len(line) >= 4 and line.startswith('::') and line.endswith('::'):
            key = line.strip(':')
            continue
        elif not line:
            key = ''
        elif key:
            if key in trigger_dict:
                trigger_dict[key].append(line)
            else:
                trigger_dict[key] = [line]

    return trigger_dict


class WorkflowsFunctionsTest(unittest.TestCase):

    def setUp(self):
        self.created_workflows = []
        self.username = 'FooBar'
        self.test_vgrid = default_vgrid
        self.test_pattern_name = 'pattern_name'
        self.test_recipe_name = 'recipe_name'
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        self.configuration = get_configuration_object()
        self.logger = self.configuration.logger
        # Ensure that the vgrid_files_home exist
        vgrid_file_path = os.path.join(self.configuration.vgrid_files_home,
                                       self.test_vgrid)
        if not os.path.exists(vgrid_file_path):
            self.assertTrue(makedirs_rec(vgrid_file_path, self.configuration,
                                         accept_existing=True))
        # Ensure workflows are enabled
        self.configuration.site_enable_workflows = True
        (trigger_status, trigger_msg) = vgrid_set_triggers(self.configuration,
                                                           self.test_vgrid, [])
        self.assertTrue(trigger_status)
        # Create home for test job files
        self.mrsl_files = os.path.join(
            self.configuration.mrsl_files_dir, self.username)
        if not os.path.exists(self.mrsl_files):
            os.mkdir(self.mrsl_files)

    def tearDown(self):
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        configuration = get_configuration_object()
        test_vgrid = default_vgrid
        # Remove tmp vgrid_file_home
        vgrid_file_path = os.path.join(configuration.vgrid_files_home,
                                       test_vgrid)
        if os.path.exists(vgrid_file_path):
            self.assertTrue(remove_rec(vgrid_file_path, self.configuration))
        self.assertFalse(os.path.exists(vgrid_file_path))
        # Also clear vgrid_dir of any patterns and recipes
        self.assertTrue(reset_workflows(configuration, vgrid=test_vgrid))
        self.assertEqual(
            get_workflow_trigger(configuration, test_vgrid)[0], [])
        configuration.site_enable_workflows = False
        # Cleanup any test job files
        if os.path.exists(self.mrsl_files):
            shutil.rmtree(self.mrsl_files)

    def test_create_workflow_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])
        self.assertEqual(workflow[0]['input_file'],
                         pattern_attributes['input_file'])
        self.assertEqual(workflow[0]['output'], pattern_attributes['output'])
        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

        self.assertEqual(len(workflow[0]['trigger_recipes']), 1)
        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger_name = next(iter(list(
            workflow[0]['trigger_recipes'][trigger_id])))
        self.assertEqual(trigger_name, self.test_recipe_name)

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)

        # Expect an empty trigger template since the specified recipe doesn't
        # exist yet.
        self.assertEqual(trigger['vgrid_name'], self.test_vgrid)
        for path in pattern_attributes['input_paths']:
            self.assertEqual(trigger['path'], path)
        self.assertEqual(trigger['templates'], [])

    def test_vgrid_exists_create_workflow(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': 'foobar',
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertFalse(created)
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': 'foobar',
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}
        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_pattern_create_with_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20},
                              'persistence_id': 'persistence0123456789'}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertFalse(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertEqual(workflow, [])

        # Assert that no trigger was created
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid)
        self.assertFalse(trigger)

    def test_pattern_create_with_duplicate_name(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        recipe_name = 'recipe_name_1'
        pattern_2_attributes = {'name': self.test_pattern_name,
                                'vgrid': self.test_vgrid,
                                'input_paths': ['input_dir/*txt'],
                                'input_file': 'hdf5_input',
                                'output': {
                                    'processed_data':
                                        'pattern_1_output/{FILENAME}.hdf5'},
                                'recipes': [recipe_name],
                                'variables': {'iterations': 35}}

        created, pattern_id_1 = create_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **pattern_2_attributes)
        self.logger.info(pattern_id_1)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

    def test_pattern_create_with_duplicate_attributes(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        created, pattern_id_2 = create_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **pattern_attributes)
        self.logger.info(pattern_id_2)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])

        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

    def test_create_workflow_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(workflow[0][k], v)

    def test_recipe_create_with_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb',
                             'persistence_id': 'persistence0123456789'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertFalse(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertEqual(workflow, [])

    def test_recipe_create_with_duplicate_name(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        created, recipe_id_2 = create_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **recipe_attributes)
        self.logger.info(recipe_id_2)
        self.assertFalse(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(workflow[0][k], v)

    def test_create_read_delete_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], pattern_attributes['vgrid'])
        self.assertEqual(workflow[0]['input_file'],
                         pattern_attributes['input_file'])
        self.assertEqual(workflow[0]['output'], pattern_attributes['output'])
        self.assertEqual(workflow[0]['variables'],
                         pattern_attributes['variables'])

        # Test triggers
        self.assertEqual(len(workflow[0]['trigger_recipes']), 1)
        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger_name = next(iter(list(
            workflow[0]['trigger_recipes'][trigger_id])))
        self.assertEqual(trigger_name, self.test_recipe_name)

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)

        # Expect an empty trigger template since the specified recipe doesn't
        # exist yet.
        self.assertEqual(trigger['vgrid_name'], self.test_vgrid)
        for path in pattern_attributes['input_paths']:
            self.assertEqual(trigger['path'], path)
        self.assertEqual(trigger['templates'], [])

        delete_attributes = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertEqual(workflow, [])

        # Ensure trigger is gone
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertFalse(trigger)

    def test_create_read_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_attributes)
        self.assertEqual(workflow, [])

    def test_update_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})

        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        # Assert empty trigger
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        self.assertEqual(trigger['templates'], [])

        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid,
                          'persistence_id': pattern_id}

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_attributes)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        u_workflow = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})
        self.assertEqual(len(u_workflow), 1)
        self.assertEqual(u_workflow[0]['name'], new_attributes['name'])

        # Ensure trigger is the same
        u_trigger_id = next(iter(list(u_workflow[0]['trigger_recipes'])))
        self.assertEqual(trigger_id, u_trigger_id)
        u_trigger, msg = get_workflow_trigger(self.configuration,
                                              self.test_vgrid,
                                              u_trigger_id)

        self.assertDictEqual(trigger, u_trigger)

    def test_update_pattern_recipe_swap(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})

        trigger_id = next(iter(list(workflow[0]['trigger_recipes'])))
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        # Assert empty trigger
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        self.assertEqual(trigger['templates'], [])

        new_attributes = {'recipes': ['new_recipe'],
                          'vgrid': self.test_vgrid,
                          'persistence_id': pattern_id}

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_attributes)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        u_workflow = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})
        self.assertEqual(len(u_workflow), 1)

        self.assertEqual(len(u_workflow[0]['trigger_recipes']), 1)

        self.assertEqual(
            list(list(u_workflow[0]['trigger_recipes'].values())[0])[0],
            new_attributes['recipes'][0])

        # Ensure trigger is the same
        u_trigger_id = next(iter(list(u_workflow[0]['trigger_recipes'])))
        self.assertEqual(trigger_id, u_trigger_id)
        u_trigger, msg = get_workflow_trigger(self.configuration,
                                              self.test_vgrid,
                                              u_trigger_id)

        self.assertDictEqual(trigger, u_trigger)

    def test_update_pattern_without_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid}

        updated, msg = update_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **new_attributes)
        self.logger.info(msg)
        self.assertFalse(updated)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], pattern_attributes['name'])

    def test_update_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)

        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid,
                          'persistence_id': recipe_id}
        # Try update without persistence_id
        updated, u_recipe_id = update_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **new_attributes)
        self.logger.info(u_recipe_id)
        self.assertTrue(updated)
        self.assertEqual(recipe_id, u_recipe_id)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **{'persistence_id': u_recipe_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], new_attributes['name'])

    def test_update_recipe_without_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        new_attributes = {'name': 'Updated named',
                          'vgrid': self.test_vgrid}
        # Try update without persistence_id
        updated, u_recipe_id = update_workflow(self.configuration,
                                               self.username,
                                               workflow_type=WORKFLOW_RECIPE,
                                               **new_attributes)
        self.logger.info(u_recipe_id)
        self.assertFalse(updated)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **{'persistence_id': recipe_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['name'], recipe_attributes['name'])

    def test_clear_user_workflows(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}
        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Get every workflow in vgrid
        workflows = get_workflow_with(self.configuration,
                                      client_id=self.username,
                                      user_query=True,
                                      workflow_type=WORKFLOW_ANY,
                                      **{'vgrid': self.test_vgrid})

        self.assertIsNotNone(workflows)
        # Verify that the created objects exist
        self.assertEqual(len(workflows), 2)
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

        workflows = get_workflow_with(self.configuration,
                                      client_id=self.username,
                                      user_query=True,
                                      workflow_type=WORKFLOW_ANY,
                                      **{'vgrid': self.test_vgrid})
        self.assertEqual(workflows, [])

    def test_delete_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     self.username,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})

        self.assertEqual(len(workflow), 1)
        trigger_id = next(iter(workflow[0]['trigger_recipes']))
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)

        deletion_attributes = {'persistence_id': pattern_id,
                               'vgrid': self.test_vgrid}
        deleted, deleted_id = delete_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **deletion_attributes)
        self.logger.info(deleted_id)
        self.assertTrue(deleted)
        self.assertEqual(pattern_id, deleted_id)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)
        self.assertEqual(workflow, [])

        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertFalse(trigger)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_pattern_without_persistence_id(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        deletion_attributes = {'vgrid': self.test_vgrid}
        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertFalse(deleted)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        deletion_attributes = {'persistence_id': recipe_id,
                               'vgrid': self.test_vgrid}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)

        self.assertEqual(workflow, [])

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_delete_recipe_without_persistence_id(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        deletion_attributes = {'vgrid': self.test_vgrid}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **deletion_attributes)

        self.logger.info(msg)
        self.assertFalse(deleted)

        # Remove workflow
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

    def test_workflow_create_pattern_associate_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.logger.warning(trigger)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertNotEqual(trigger['templates'], [])
        # TODO, convert templates stings to object that we can check the
        # execute and output_files strings for each associated
        # recipe are correctly created

    def test_workflow_create_recipe_associate_pattern(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        # Validate that the trigger is empty since the recipe doesn't yet exist
        # Test that the trigger is valid
        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.logger.warning(trigger)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertEqual(trigger['templates'], [])

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        u_trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(trigger_id, u_trigger_id)
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain the parsed recipe
        self.assertNotEqual(trigger['templates'], [])
        # TODO, convert templates stings to object that we can check the
        # execute and output_files strings for each associated
        # recipe are correctly created

    def test_workflow_update_pattern_trigger_recipe(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/{FILENAME}.hdf5'},
                              'recipes': [],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # No recipe provided == None
        self.assertEqual(patterns[0]['trigger_recipes'][trigger_id], {})

        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain an empty template since no
        # recipe is associated
        self.assertEqual(trigger['templates'], [])

        # Create new recipe
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Update pattern to use the recipe, test that it is associated
        new_pattern = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid,
            'recipes': [self.test_recipe_name]
        }

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_pattern)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        # Test that the pattern is now updated with the correct recipe
        u_patterns = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})

        # Test that the trigger is correctly updated
        self.assertEqual(len(u_patterns), 1)
        self.assertEqual(len(u_patterns[0]['trigger_recipes']), 1)
        u_trigger_id = next(iter(u_patterns[0]['trigger_recipes']))

        self.assertEqual(trigger_id, u_trigger_id)
        # Get the updated trigger
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertTrue(trigger)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        self.assertNotEqual(trigger['templates'], [])

    # Test updated pattern with new input_paths and recipe.
    def test_update_pattern_paths_recipe(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['input_dir/*.hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {},
                              'recipes': ['non_existing_recipe']}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)

        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Recipe didn't exist before pattern was created == placeholder name
        # key is ready to be replaced with recipe_id
        self.assertEqual(patterns[0]['trigger_recipes'][trigger_id],
                         {'non_existing_recipe': {}})

        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])
        # Templates should contain an empty template since no
        # recipe is associated
        self.assertEqual(trigger['templates'], [])

        # Create new recipe
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {'name': self.test_recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': 'notebook.ipynb'}

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Update pattern with new input paths and existing recipe
        new_attributes = {'persistence_id': pattern_id,
                          'vgrid': self.test_vgrid,
                          'input_paths': ['new_input_path/*.hdf5'],
                          'recipes': [self.test_recipe_name]}

        # Result -> Delete trigger associated with old input_paths,
        # then delete removed recipe reference from pattern
        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                WORKFLOW_PATTERN,
                                                **new_attributes)
        self.logger.info(u_pattern_id)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)
        # Ensure that the old trigger is deleted
        u_trigger, u_msg = get_workflow_trigger(self.configuration,
                                                self.test_vgrid,
                                                trigger_id)
        self.assertFalse(u_trigger)

        u_patterns = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id})

        trigger_id = next(iter(u_patterns[0]['trigger_recipes']))
        self.assertEqual(len(u_patterns[0]['trigger_recipes']), 1)
        # Test that the new trigger is valid
        n_trigger, msg = get_workflow_trigger(self.configuration,
                                              self.test_vgrid,
                                              trigger_id)

        self.assertEqual(n_trigger['rule_id'], trigger_id)
        self.assertEqual(n_trigger['path'], new_attributes['input_paths'][0])
        self.assertEqual(n_trigger['vgrid_name'], new_attributes['vgrid'])
        # Templates should not be empty since a recipe is now associated
        self.assertNotEqual(n_trigger['templates'], [])
        # TODO, validate that the template is the correct structure

    # Test that the pattern parameter file is correctly made and updated
    def test_create_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/name.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        expected_params = {
            'hdf5_input': 'ENV_WORKFLOW_INPUT_PATH',
            'processed_data': 'Generic/pattern_0_output/name.hdf5',
            'iterations': 20
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.logger.info(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertEqual(
            parameters[pattern_attributes['input_file']],
            'ENV_WORKFLOW_INPUT_PATH')

        for k, v in pattern_attributes['variables'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

        for k, v in pattern_attributes['output'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

    def test_update_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/name.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        expected_params = {
            'hdf5_input': 'ENV_WORKFLOW_INPUT_PATH',
            'processed_data': 'Generic/pattern_0_output/name.hdf5',
            'iterations': 20
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertEqual(
            parameters[pattern_attributes['input_file']],
            'ENV_WORKFLOW_INPUT_PATH')

        for k, v in pattern_attributes['variables'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

        for k, v in pattern_attributes['output'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

        # Update workflow
        new_attributes = {'persistence_id': pattern_id,
                          'vgrid': self.test_vgrid,
                          'input_file': 'new_attribute',
                          'output': {
                              'processed_data': 'new_path/bla.npy',
                              'another_output': 'second_path/{PATH}.npy'},
                          'variables': {'iterations': 1000,
                                        'additional': 'test'}}

        new_expected_params = {
            'new_attribute': 'ENV_WORKFLOW_INPUT_PATH',
            'processed_data': 'Generic/new_path/bla.npy',
            'another_output': 'ENV_another_output',
            'iterations': 1000,
            'additional': 'test'
        }

        updated, u_pattern_id = update_workflow(self.configuration,
                                                self.username,
                                                workflow_type=WORKFLOW_PATTERN,
                                                **new_attributes)
        self.assertTrue(updated)
        self.assertEqual(pattern_id, u_pattern_id)

        u_workflow = get_workflow_with(self.configuration,
                                       client_id=self.username,
                                       user_query=True,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **{'persistence_id': u_pattern_id,
                                          'vgrid': self.test_vgrid})
        self.assertIsNotNone(u_workflow)
        self.assertEqual(len(u_workflow), 1)
        # Assert that the parameter file is updated
        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 u_workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(new_attributes['input_file'], parameters)
        self.assertEqual(
            parameters[new_attributes['input_file']],
            'ENV_WORKFLOW_INPUT_PATH')

        for k, v in new_attributes['variables'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], new_expected_params[k])

        for k, v in new_attributes['output'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], new_expected_params[k])

    def test_delete_pattern_parameter_file(self):
        pattern_attributes = {'name': self.test_pattern_name,
                              'vgrid': self.test_vgrid,
                              'input_paths': ['initial_data/*hdf5'],
                              'input_file': 'hdf5_input',
                              'output': {
                                  'processed_data':
                                      'pattern_0_output/name.hdf5'},
                              'recipes': [self.test_recipe_name],
                              'variables': {'iterations': 20}}

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertTrue(set(pattern_attributes['variables'].items())
                        .issubset(set(parameters.items())))
        self.assertTrue(set(pattern_attributes['output'])
                        .issubset(set(parameters)))

        delete_attributes = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_PATTERN,
                                       **delete_attributes)
        self.assertTrue(deleted)
        self.assertEqual(pattern_id, msg)
        self.assertFalse(os.path.exists(parameter_path))

    def test_create_pattern_substitutions(self):
        pattern_attributes = {
            'name': self.test_pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'out_path': 'dir/{PATH}.hdf5',
                'out_rel_path': 'dir/{REL_PATH}.hdf5',
                'out_dir': 'dir/{DIR}.hdf5',
                'out_rel_dir': 'dir/{REL_DIR}.hdf5',
                'out_filename': 'dir/{FILENAME}.hdf5',
                'out_prefix': 'dir/{PREFIX}.hdf5',
                'out_extension': 'dir/{EXTENSION}.hdf5',
                'out_vgrid': 'dir/{VGRID}.hdf5',
                'out_job': 'dir/{JOB}.hdf5',
                'out_unspecified': 'dir/{UNSPECIFIED}.hdf5',
                'out_lowercase': 'dir/{path}.hdf5'
            },
            'recipes': [self.test_recipe_name],
            'variables': {
                'var_path': 'dir/{PATH}.hdf5',
                'var_rel_path': 'dir/{REL_PATH}.hdf5',
                'var_dir': 'dir/{DIR}.hdf5',
                'var_rel_dir': 'dir/{REL_DIR}.hdf5',
                'var_filename': 'dir/{FILENAME}.hdf5',
                'var_prefix': 'dir/{PREFIX}.hdf5',
                'var_extension': 'dir/{EXTENSION}.hdf5',
                'var_vgrid': 'dir/{VGRID}.hdf5',
                'var_job': 'dir/{JOB}.hdf5',
                'var_unspecified': 'dir/{UNSPECIFIED}.hdf5',
                'var_lowercase': 'dir/{path}.hdf5'
            }
        }

        expected_params = {
            'hdf5_input': 'ENV_WORKFLOW_INPUT_PATH',
            'out_path': 'ENV_out_path',
            'out_rel_path': 'ENV_out_rel_path',
            'out_dir': 'ENV_out_dir',
            'out_rel_dir': 'ENV_out_rel_dir',
            'out_filename': 'ENV_out_filename',
            'out_prefix': 'ENV_out_prefix',
            'out_extension': 'ENV_out_extension',
            'out_vgrid': 'ENV_out_vgrid',
            'out_job': 'ENV_out_job',
            'out_unspecified': 'Generic/dir/{UNSPECIFIED}.hdf5',
            'out_lowercase': 'Generic/dir/{path}.hdf5',
            'var_path': 'ENV_var_path',
            'var_rel_path': 'ENV_var_rel_path',
            'var_dir': 'ENV_var_dir',
            'var_rel_dir': 'ENV_var_rel_dir',
            'var_filename': 'ENV_var_filename',
            'var_prefix': 'ENV_var_prefix',
            'var_extension': 'ENV_var_extension',
            'var_vgrid': 'ENV_var_vgrid',
            'var_job': 'ENV_var_job',
            'var_unspecified': 'dir/{UNSPECIFIED}.hdf5',
            'var_lowercase': 'dir/{path}.hdf5',
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)

        parameter_path = get_task_parameter_path(self.configuration,
                                                 self.test_vgrid,
                                                 workflow[0])
        self.assertTrue(os.path.exists(parameter_path))
        parameters = load(parameter_path, 'yaml', 'r')
        self.assertIsNotNone(parameters)
        self.logger.info(parameters)

        self.assertIn(pattern_attributes['input_file'], parameters)
        self.assertEqual(
            parameters[pattern_attributes['input_file']],
            'ENV_WORKFLOW_INPUT_PATH')

        for k, v in pattern_attributes['variables'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

        for k, v in pattern_attributes['output'].items():
            self.assertIn(k, parameters)
            self.assertEqual(parameters[k], expected_params[k])

    def test_recipe_environments(self):
        notebook = nbformat.v4.new_notebook()
        recipe_without_environment = {
            'name': self.test_recipe_name,
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb'
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_without_environment)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_without_environment)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Check internal attributes
        for k, v in recipe_without_environment.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        recipe_with_mig_environment = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '1',
                    'cpu cores': '1',
                    'wall time': '1',
                    'memory': '1',
                    'disks': '1',
                    'cpu-architecture': 'X86',
                    'fill': [
                        'CPUCOUNT'
                    ],
                    'environment variables': [
                        'VAR=42'
                    ],
                    'notification': [
                        'email: SETTINGS'
                    ],
                    'retries': '1',
                    'runtime environments': [
                        'PAPERMILL'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_mig_environment)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_with_mig_environment)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)

        # Check internal attributes
        for k, v in recipe_with_mig_environment.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        recipe_with_local_environment = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'local': {
                    'dependencies': [
                        'watchdog',
                        'mig_meow'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_local_environment)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_with_local_environment)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)

        # Check internal attributes
        for k, v in recipe_with_local_environment.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        recipe_with_both_environments = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '1',
                    'cpu cores': '1',
                    'wall time': '1',
                    'memory': '1',
                    'disks': '1',
                    'cpu-architecture': 'X86',
                    'fill': [
                        'CPUCOUNT',
                        'CPUTIME',
                        'DISK',
                        'MEMORY',
                        'NODECOUNT'
                    ],
                    'environment variables': [
                        'VAR=42'
                    ],
                    'notification': [
                        'email: SETTINGS'
                    ],
                    'retries': '1',
                    'runtime environments': [
                        'PAPERMILL'
                    ]
                },
                'local': {
                    'dependencies': [
                        'watchdog',
                        'mig_meow'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_both_environments)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_with_both_environments)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)

        # Check internal attributes
        for k, v in recipe_with_both_environments.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        # Anything other than mig dependencies aren't used on the mig, so we
        # can let them be whatever folks ask for
        recipe_with_wonky_local = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'local': {
                    'asdf': [
                        'asdf',
                        'asdf'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_wonky_local)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **recipe_with_wonky_local)
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)

        # Check internal attributes
        for k, v in recipe_with_wonky_local.items():
            self.assertEqual(workflow[0][k], v)

        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = delete_workflow(self.configuration,
                                       self.username,
                                       workflow_type=WORKFLOW_RECIPE,
                                       **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

    def test_recipe_environment_nodes(self):
        notebook = nbformat.v4.new_notebook()
        recipe_with_bad_mig_nodes_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_nodes_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_nodes_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_nodes_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_nodes_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_nodes_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_cores(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_cores_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'cpu cores': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_cores_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_cores_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'cpu cores': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_cores_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_cores_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'cpu cores': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_cores_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_wall(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_wall_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'wall time': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_wall_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_wall_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'wall time': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_wall_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_wall_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'wall time': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_wall_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_memory(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_memory_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'memory': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_memory_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_memory_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'memory': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_memory_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_memory_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'memory': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_memory_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_disks(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_disks_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'disks': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_disks_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_disks_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'disks': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_disks_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_disks_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'disks': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_disks_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_cpu(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_cpu = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'cpu-architecture': 'X87',
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_cpu)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_fill(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_fill_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'fill': 'CPUCOUNT'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_fill_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_fill_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'fill': [
                        'NOTHING'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_fill_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_env(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_env_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'environment variables': 'VAR=42'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_env_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_env_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'environment variables': [
                        'VAR:42'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_env_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_env_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'environment variables': [
                        '=VAR42'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_env_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_env_d = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'environment variables': [
                        'VAR42='
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_env_d)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_notification(self):
        notebook = nbformat.v4.new_notebook()

        # Should be expanded to also support other definitions
        recipe_with_bad_mig_notification_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'notification': [
                        'email: not_an_email'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(
            self.configuration,
            self.username,
            workflow_type=WORKFLOW_RECIPE,
            **recipe_with_bad_mig_notification_a
        )
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_notification_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'notification': [
                        'email=SETTINGS'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(
            self.configuration,
            self.username,
            workflow_type=WORKFLOW_RECIPE,
            **recipe_with_bad_mig_notification_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_notification_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'notification': 'email: SETTINGS'
                }
            }
        }

        created, recipe_id = create_workflow(
            self.configuration,
            self.username,
            workflow_type=WORKFLOW_RECIPE,
            **recipe_with_bad_mig_notification_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_retries(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_retries_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'retries': 1
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_retries_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_retries_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'retries': '-1'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_retries_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_retries_c = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'retries': '1.0'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_retries_c)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_recipe_environment_runtime(self):
        notebook = nbformat.v4.new_notebook()

        recipe_with_bad_mig_runtime_a = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'runtime environments': 'PAPERMILL'
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_runtime_a)
        self.logger.info(recipe_id)
        self.assertFalse(created)

        recipe_with_bad_mig_runtime_b = {
            'name': 'with_mig',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'runtime environments': [
                        'DOESNOTEXIST'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_with_bad_mig_runtime_b)
        self.logger.info(recipe_id)
        self.assertFalse(created)

    def test_workflow_default_job_template_pattern_first(self):
        pattern_attributes = {
            'name': self.test_pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': [self.test_recipe_name],
            'variables': {'iterations': 20}
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.assertTrue(created)

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {
            'name': self.test_recipe_name,
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb'
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        # Validate that the trigger is empty since the recipe doesn't yet exist
        # Test that the trigger is valid
        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])

        task_id = \
            patterns[0]['trigger_recipes'][trigger_id][recipe_id]['task_file']

        # Templates should contain the parsed recipe
        self.assertEqual(len(trigger['templates']), 1)

        trigger_lines = trigger['templates'][0].split('\n')
        self.logger.info(trigger_lines)

        trigger_dict = parse_trigger_lines(trigger_lines)
        self.logger.info(trigger_dict)

        self.assertEqual(len(trigger_dict), 14)

        self.assertIn('VGRID', trigger_dict)
        self.assertEqual(trigger_dict['VGRID'], ['+TRIGGERVGRIDNAME+'])

        self.assertIn('RETRIES', trigger_dict)
        self.assertEqual(trigger_dict['RETRIES'], ['0'])

        self.assertIn('EXECUTE', trigger_dict)
        self.assertEqual(len(trigger_dict['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), trigger_dict['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, trigger_dict['EXECUTE'])

        self.assertIn('OUTPUTFILES', trigger_dict)
        self.assertEqual(trigger_dict['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+JOBID'
                          '+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['RUNTIMEENVIRONMENT']), 2)
        self.assertIn('NOTEBOOK_PARAMETERIZER',
                      trigger_dict['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', trigger_dict['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', trigger_dict)
        self.assertEqual(len(trigger_dict['MAXFILL']), 5)
        self.assertIn('CPUCOUNT', trigger_dict['MAXFILL'])
        self.assertIn('CPUTIME', trigger_dict['MAXFILL'])
        self.assertIn('DISK', trigger_dict['MAXFILL'])
        self.assertIn('MEMORY', trigger_dict['MAXFILL'])
        self.assertIn('NODECOUNT', trigger_dict['MAXFILL'])

        self.assertIn('MOUNT', trigger_dict)
        self.assertEqual(trigger_dict['MOUNT'],
                         ['+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+'])

        self.assertIn('CPUTIME', trigger_dict)
        self.assertEqual(trigger_dict['CPUTIME'], ['60'])

        self.assertIn('ENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['ENVIRONMENT']), 3)
        self.assertIn('LC_ALL=en_US.utf8', trigger_dict['ENVIRONMENT'])
        self.assertIn('PYTHONPATH=+TRIGGERVGRIDNAME+',
                      trigger_dict['ENVIRONMENT'])
        self.assertIn('WORKFLOW_INPUT_PATH=+TRIGGERPATH+',
                      trigger_dict['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', trigger_dict)
        self.assertEqual(trigger_dict['CPUCOUNT'], ['1'])

        self.assertIn('NOTIFY', trigger_dict)
        self.assertEqual(trigger_dict['NOTIFY'], ['email: SETTINGS'])

        self.assertIn('MEMORY', trigger_dict)
        self.assertEqual(trigger_dict['MEMORY'], ['64'])

        self.assertIn('NODECOUNT', trigger_dict)
        self.assertEqual(trigger_dict['NODECOUNT'], ['1'])

        self.assertIn('DISK', trigger_dict)
        self.assertEqual(trigger_dict['DISK'], ['1'])

        # check that the mrsl is actually valid
        temp_dir = tempfile.mkdtemp()
        mrsl_fd = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
        mrsl_path = mrsl_fd.name

        job_template = trigger['templates'][0]
        rule = {
            'vgrid_name': self.test_vgrid,
            'run_as': self.username
        }
        rel_src = 'this/is/a/path'
        state = 'dummy event'
        expand_map = get_path_expand_map(rel_src, rule, state)
        test_job_id = '1234567890'

        status = fill_mrsl_template(
            job_template,
            mrsl_fd,
            rel_src,
            state,
            rule,
            expand_map,
            self.configuration
        )

        self.assertTrue(status)

        (parseresult, parsemsg) = parse(
            mrsl_path,
            test_job_id,
            self.username,
            False,
            outfile='AUTOMATIC',
            workflow_job=False
        )

        self.assertTrue(parseresult)
        self.assertEqual(parsemsg, '')

        mrsl_file = os.path.join(self.mrsl_files, test_job_id + '.mRSL')
        self.assertTrue(os.path.exists(mrsl_file))

        mrsl = unpickle(mrsl_file, self.logger)

        self.assertIn('VGRID', mrsl)
        self.assertEqual(mrsl['VGRID'], [self.test_vgrid])

        self.assertIn('RETRIES', mrsl)
        self.assertEqual(mrsl['RETRIES'], 0)

        self.assertIn('EXECUTE', mrsl)
        self.assertEqual(len(mrsl['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), mrsl['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, mrsl['EXECUTE'])

        self.assertIn('OUTPUTFILES', mrsl)
        self.assertEqual(mrsl['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+JOBID'
                          '+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['RUNTIMEENVIRONMENT']), 3)
        self.assertIn('NOTEBOOK_PARAMETERIZER',
                      mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('SSHFS-2.X-1', mrsl['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', mrsl)
        self.assertEqual(len(mrsl['MAXFILL']), 5)
        self.assertIn('CPUCOUNT', mrsl['MAXFILL'])
        self.assertIn('CPUTIME', mrsl['MAXFILL'])
        self.assertIn('DISK', mrsl['MAXFILL'])
        self.assertIn('MEMORY', mrsl['MAXFILL'])
        self.assertIn('NODECOUNT', mrsl['MAXFILL'])

        self.assertIn('MOUNT', mrsl)
        self.assertEqual(mrsl['MOUNT'],
                         [self.test_vgrid + ' ' + self.test_vgrid])

        self.assertIn('CPUTIME', mrsl)
        self.assertEqual(mrsl['CPUTIME'], 60)

        self.assertIn('ENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['ENVIRONMENT']), 3)
        self.assertIn(('LC_ALL', 'en_US.utf8'), mrsl['ENVIRONMENT'])
        self.assertIn(('PYTHONPATH', self.test_vgrid), mrsl['ENVIRONMENT'])
        self.assertIn(('WORKFLOW_INPUT_PATH', rel_src), mrsl['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', mrsl)
        self.assertEqual(mrsl['CPUCOUNT'], 1)

        self.assertIn('NOTIFY', mrsl)
        self.assertEqual(mrsl['NOTIFY'], ['email: SETTINGS'])

        self.assertIn('MEMORY', mrsl)
        self.assertEqual(mrsl['MEMORY'], 64)

        self.assertIn('NODECOUNT', mrsl)
        self.assertEqual(mrsl['NODECOUNT'], 1)

        self.assertIn('DISK', mrsl)
        self.assertEqual(mrsl['DISK'], 1)

    def test_workflow_default_job_template_recipe_first(self):
        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {
            'name': self.test_recipe_name,
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb'
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        pattern_attributes = {
            'name': self.test_pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': [self.test_recipe_name],
            'variables': {'iterations': 20}
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        # Validate that the trigger is empty since the recipe doesn't yet exist
        # Test that the trigger is valid
        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])

        task_id = \
            patterns[0]['trigger_recipes'][trigger_id][recipe_id]['task_file']

        # Templates should contain the parsed recipe
        self.assertEqual(len(trigger['templates']), 1)

        trigger_lines = trigger['templates'][0].split('\n')
        self.logger.info(trigger_lines)

        trigger_dict = parse_trigger_lines(trigger_lines)
        self.logger.info(trigger_dict)

        self.assertEqual(len(trigger_dict), 14)

        self.assertIn('VGRID', trigger_dict)
        self.assertEqual(trigger_dict['VGRID'], ['+TRIGGERVGRIDNAME+'])

        self.assertIn('RETRIES', trigger_dict)
        self.assertEqual(trigger_dict['RETRIES'], ['0'])

        self.assertIn('EXECUTE', trigger_dict)
        self.assertEqual(len(trigger_dict['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), trigger_dict['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, trigger_dict['EXECUTE'])

        self.assertIn('OUTPUTFILES', trigger_dict)
        self.assertEqual(trigger_dict['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+JOBID'
                          '+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['RUNTIMEENVIRONMENT']), 2)
        self.assertIn('NOTEBOOK_PARAMETERIZER',
                      trigger_dict['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', trigger_dict['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', trigger_dict)
        self.assertEqual(len(trigger_dict['MAXFILL']), 5)
        self.assertIn('CPUCOUNT', trigger_dict['MAXFILL'])
        self.assertIn('CPUTIME', trigger_dict['MAXFILL'])
        self.assertIn('DISK', trigger_dict['MAXFILL'])
        self.assertIn('MEMORY', trigger_dict['MAXFILL'])
        self.assertIn('NODECOUNT', trigger_dict['MAXFILL'])

        self.assertIn('MOUNT', trigger_dict)
        self.assertEqual(trigger_dict['MOUNT'],
                         ['+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+'])

        self.assertIn('CPUTIME', trigger_dict)
        self.assertEqual(trigger_dict['CPUTIME'], ['60'])

        self.assertIn('ENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['ENVIRONMENT']), 3)
        self.assertIn('LC_ALL=en_US.utf8', trigger_dict['ENVIRONMENT'])
        self.assertIn('PYTHONPATH=+TRIGGERVGRIDNAME+',
                      trigger_dict['ENVIRONMENT'])
        self.assertIn('WORKFLOW_INPUT_PATH=+TRIGGERPATH+',
                      trigger_dict['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', trigger_dict)
        self.assertEqual(trigger_dict['CPUCOUNT'], ['1'])

        self.assertIn('NOTIFY', trigger_dict)
        self.assertEqual(trigger_dict['NOTIFY'], ['email: SETTINGS'])

        self.assertIn('MEMORY', trigger_dict)
        self.assertEqual(trigger_dict['MEMORY'], ['64'])

        self.assertIn('NODECOUNT', trigger_dict)
        self.assertEqual(trigger_dict['NODECOUNT'], ['1'])

        self.assertIn('DISK', trigger_dict)
        self.assertEqual(trigger_dict['DISK'], ['1'])

        # check that the mrsl is actually valid
        temp_dir = tempfile.mkdtemp()
        mrsl_fd = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
        mrsl_path = mrsl_fd.name

        job_template = trigger['templates'][0]
        rule = {
            'vgrid_name': self.test_vgrid,
            'run_as': self.username
        }
        rel_src = 'this/is/a/path'
        state = 'dummy event'
        expand_map = get_path_expand_map(rel_src, rule, state)
        test_job_id = '1234567890'

        status = fill_mrsl_template(
            job_template,
            mrsl_fd,
            rel_src,
            state,
            rule,
            expand_map,
            self.configuration
        )

        self.assertTrue(status)

        (parseresult, parsemsg) = parse(
            mrsl_path,
            test_job_id,
            self.username,
            False,
            outfile='AUTOMATIC',
            workflow_job=False
        )

        self.assertTrue(parseresult)
        self.assertEqual(parsemsg, '')

        mrsl_file = os.path.join(self.mrsl_files, test_job_id + '.mRSL')
        self.assertTrue(os.path.exists(mrsl_file))

        mrsl = unpickle(mrsl_file, self.logger)

        self.assertIn('VGRID', mrsl)
        self.assertEqual(mrsl['VGRID'], [self.test_vgrid])

        self.assertIn('RETRIES', mrsl)
        self.assertEqual(mrsl['RETRIES'], 0)

        self.assertIn('EXECUTE', mrsl)
        self.assertEqual(len(mrsl['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), mrsl['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, mrsl['EXECUTE'])

        self.assertIn('OUTPUTFILES', mrsl)
        self.assertEqual(mrsl['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+JOBID'
                          '+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['RUNTIMEENVIRONMENT']), 3)
        self.assertIn('NOTEBOOK_PARAMETERIZER',
                      mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('SSHFS-2.X-1', mrsl['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', mrsl)
        self.assertEqual(len(mrsl['MAXFILL']), 5)
        self.assertIn('CPUCOUNT', mrsl['MAXFILL'])
        self.assertIn('CPUTIME', mrsl['MAXFILL'])
        self.assertIn('DISK', mrsl['MAXFILL'])
        self.assertIn('MEMORY', mrsl['MAXFILL'])
        self.assertIn('NODECOUNT', mrsl['MAXFILL'])

        self.assertIn('MOUNT', mrsl)
        self.assertEqual(mrsl['MOUNT'],
                         [self.test_vgrid + ' ' + self.test_vgrid])

        self.assertIn('CPUTIME', mrsl)
        self.assertEqual(mrsl['CPUTIME'], 60)

        self.assertIn('ENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['ENVIRONMENT']), 3)
        self.assertIn(('LC_ALL', 'en_US.utf8'), mrsl['ENVIRONMENT'])
        self.assertIn(('PYTHONPATH', self.test_vgrid), mrsl['ENVIRONMENT'])
        self.assertIn(('WORKFLOW_INPUT_PATH', rel_src), mrsl['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', mrsl)
        self.assertEqual(mrsl['CPUCOUNT'], 1)

        self.assertIn('NOTIFY', mrsl)
        self.assertEqual(mrsl['NOTIFY'], ['email: SETTINGS'])

        self.assertIn('MEMORY', mrsl)
        self.assertEqual(mrsl['MEMORY'], 64)

        self.assertIn('NODECOUNT', mrsl)
        self.assertEqual(mrsl['NODECOUNT'], 1)

        self.assertIn('DISK', mrsl)
        self.assertEqual(mrsl['DISK'], 1)

    def test_workflow_altered_job_template(self):
        pattern_attributes = {
            'name': self.test_pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': [self.test_recipe_name],
            'variables': {'iterations': 20}
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes)
        self.assertTrue(created)

        notebook = nbformat.v4.new_notebook()
        recipe_attributes = {
            'name': self.test_recipe_name,
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '10',
                    'cpu cores': '12',
                    'wall time': '14',
                    'memory': '16',
                    'disks': '18',
                    'retries': '20',
                    'cpu-architecture': 'AMD64',
                    'fill': [
                        'DISK',
                    ],
                    'environment variables': [
                        'VAR=42'
                    ],
                    'notification': [
                        'email: patch@email.com'
                    ],
                    'runtime environments': [
                        'VIRTUALBOX-3.1.X-1'
                    ]
                },
                'local': {
                    'dependencies': [
                        'watchdog',
                        'mig_meow'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)

        # Validate that the trigger is empty since the recipe doesn't yet exist
        # Test that the trigger is valid
        trigger_id = next(iter(patterns[0]['trigger_recipes']))
        self.assertEqual(len(patterns[0]['trigger_recipes']), 1)
        # Test that the trigger is valid
        trigger, msg = get_workflow_trigger(self.configuration,
                                            self.test_vgrid,
                                            trigger_id)
        self.assertEqual(trigger['rule_id'], trigger_id)
        self.assertEqual(trigger['path'], pattern_attributes['input_paths'][0])
        self.assertEqual(trigger['vgrid_name'], pattern_attributes['vgrid'])

        task_id = patterns[0]['trigger_recipes'][trigger_id][recipe_id][
            'task_file']

        # Templates should contain the parsed recipe
        self.assertEqual(len(trigger['templates']), 1)

        trigger_lines = trigger['templates'][0].split('\n')
        self.logger.info(trigger_lines)

        trigger_dict = parse_trigger_lines(trigger_lines)
        self.logger.info(trigger_dict)

        self.assertEqual(len(trigger_dict), 14)

        self.assertIn('VGRID', trigger_dict)
        self.assertEqual(trigger_dict['VGRID'], ['+TRIGGERVGRIDNAME+'])

        self.assertIn('RETRIES', trigger_dict)
        self.assertEqual(trigger_dict['RETRIES'], ['20'])

        self.assertIn('EXECUTE', trigger_dict)
        self.assertEqual(len(trigger_dict['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), trigger_dict['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, trigger_dict['EXECUTE'])

        self.assertIn('OUTPUTFILES', trigger_dict)
        self.assertEqual(trigger_dict['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+'
                          'JOBID+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['RUNTIMEENVIRONMENT']), 3)
        self.assertIn('NOTEBOOK_PARAMETERIZER',
                      trigger_dict['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', trigger_dict['RUNTIMEENVIRONMENT'])
        self.assertIn('VIRTUALBOX-3.1.X-1', trigger_dict['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', trigger_dict)
        self.assertEqual(len(trigger_dict['MAXFILL']), 1)
        self.assertIn('DISK', trigger_dict['MAXFILL'])

        self.assertIn('MOUNT', trigger_dict)
        self.assertEqual(trigger_dict['MOUNT'],
                         ['+TRIGGERVGRIDNAME+ +TRIGGERVGRIDNAME+'])

        self.assertIn('CPUTIME', trigger_dict)
        self.assertEqual(trigger_dict['CPUTIME'], ['14'])

        self.assertIn('ENVIRONMENT', trigger_dict)
        self.assertEqual(len(trigger_dict['ENVIRONMENT']), 4)
        self.assertIn('LC_ALL=en_US.utf8', trigger_dict['ENVIRONMENT'])
        self.assertIn('PYTHONPATH=+TRIGGERVGRIDNAME+',
                      trigger_dict['ENVIRONMENT'])
        self.assertIn('WORKFLOW_INPUT_PATH=+TRIGGERPATH+',
                      trigger_dict['ENVIRONMENT'])
        self.assertIn('VAR=42', trigger_dict['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', trigger_dict)
        self.assertEqual(trigger_dict['CPUCOUNT'], ['12'])

        self.assertIn('NOTIFY', trigger_dict)
        self.assertEqual(trigger_dict['NOTIFY'], ['email: patch@email.com'])

        self.assertIn('MEMORY', trigger_dict)
        self.assertEqual(trigger_dict['MEMORY'], ['16'])

        self.assertIn('NODECOUNT', trigger_dict)
        self.assertEqual(trigger_dict['NODECOUNT'], ['10'])

        self.assertIn('DISK', trigger_dict)
        self.assertEqual(trigger_dict['DISK'], ['18'])

        # check that the mrsl is actually valid
        temp_dir = tempfile.mkdtemp()
        mrsl_fd = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
        mrsl_path = mrsl_fd.name

        job_template = trigger['templates'][0]
        rule = {
            'vgrid_name': self.test_vgrid,
            'run_as': self.username
        }
        rel_src = 'this/is/a/path'
        state = 'dummy event'
        expand_map = get_path_expand_map(rel_src, rule, state)
        test_job_id = '1234567890'

        status = fill_mrsl_template(
            job_template,
            mrsl_fd,
            rel_src,
            state,
            rule,
            expand_map,
            self.configuration
        )

        self.assertTrue(status)

        (parseresult, parsemsg) = parse(
            mrsl_path,
            test_job_id,
            self.username,
            False,
            outfile='AUTOMATIC',
            workflow_job=False
        )

        self.assertTrue(parseresult)
        self.assertEqual(parsemsg, '')

        mrsl_file = os.path.join(self.mrsl_files, test_job_id + '.mRSL')
        self.assertTrue(os.path.exists(mrsl_file))

        mrsl = unpickle(mrsl_file, self.logger)

        self.assertIn('VGRID', mrsl)
        self.assertEqual(mrsl['VGRID'], [self.test_vgrid])

        self.assertIn('RETRIES', mrsl)
        self.assertEqual(mrsl['RETRIES'], 20)

        self.assertIn('EXECUTE', mrsl)
        self.assertEqual(len(mrsl['EXECUTE']), 2)
        self.assertIn(
            '${NOTEBOOK_PARAMETERIZER} Generic/.workflow_tasks_home/%s '
            'Generic/.workflow_tasks_home/%s.yaml -o +JOBID+_%s -e'
            % (task_id, pattern_id, task_id), mrsl['EXECUTE'])
        self.assertIn(
            '${PAPERMILL} +JOBID+_%s +JOBID+_recipe_name_output.ipynb'
            % task_id, mrsl['EXECUTE'])

        self.assertIn('OUTPUTFILES', mrsl)
        self.assertEqual(mrsl['OUTPUTFILES'],
                         ['+JOBID+_recipe_name_output.ipynb job_output/+'
                          'JOBID+/+JOBID+_recipe_name_output.ipynb'])

        self.assertIn('RUNTIMEENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['RUNTIMEENVIRONMENT']), 4)
        self.assertIn('NOTEBOOK_PARAMETERIZER', mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('PAPERMILL', mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('VIRTUALBOX-3.1.X-1', mrsl['RUNTIMEENVIRONMENT'])
        self.assertIn('SSHFS-2.X-1', mrsl['RUNTIMEENVIRONMENT'])

        self.assertIn('MAXFILL', mrsl)
        self.assertEqual(len(mrsl['MAXFILL']), 1)
        self.assertIn('DISK', mrsl['MAXFILL'])

        self.assertIn('MOUNT', mrsl)
        self.assertEqual(mrsl['MOUNT'],
                         [self.test_vgrid + ' ' + self.test_vgrid])

        self.assertIn('CPUTIME', mrsl)
        self.assertEqual(mrsl['CPUTIME'], 14)

        self.assertIn('ENVIRONMENT', mrsl)
        self.assertEqual(len(mrsl['ENVIRONMENT']), 4)
        self.assertIn(('LC_ALL', 'en_US.utf8'), mrsl['ENVIRONMENT'])
        self.assertIn(('PYTHONPATH', self.test_vgrid), mrsl['ENVIRONMENT'])
        self.assertIn(('WORKFLOW_INPUT_PATH', rel_src), mrsl['ENVIRONMENT'])
        self.assertIn(('VAR', '42'), mrsl['ENVIRONMENT'])

        self.assertIn('CPUCOUNT', mrsl)
        self.assertEqual(mrsl['CPUCOUNT'], 12)

        self.assertIn('NOTIFY', mrsl)
        self.assertEqual(mrsl['NOTIFY'], ['email: patch@email.com'])

        self.assertIn('MEMORY', mrsl)
        self.assertEqual(mrsl['MEMORY'], 16)

        self.assertIn('NODECOUNT', mrsl)
        self.assertEqual(mrsl['NODECOUNT'], 10)

        self.assertIn('DISK', mrsl)
        self.assertEqual(mrsl['DISK'], 18)

    def test_workflow_matching(self):
        pattern_attributes_a = {
            'name': 'pattern_a',
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': [self.test_recipe_name],
            'variables': {'iterations': 20}
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes_a)
        self.assertTrue(created)

        pattern_attributes_b = {
            'name': 'pattern_b',
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': [self.test_recipe_name],
            'variables': {
                'iterations': 20,
                'count': 100
            }
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes_b)
        self.assertTrue(created)

        pattern_attributes_c = {
            'name': 'pattern_c',
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {'processed_data': 'pattern_0_output/{FILENAME}.hdf5'},
            'recipes': ['a_different_recipe'],
            'variables': {'index': 0}
        }

        created, pattern_id = create_workflow(self.configuration,
                                              self.username,
                                              workflow_type=WORKFLOW_PATTERN,
                                              **pattern_attributes_c)
        self.assertTrue(created)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes_a)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(pattern_attributes_a['name'], patterns[0]['name'])

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes_b)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(pattern_attributes_b['name'], patterns[0]['name'])

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **pattern_attributes_c)
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(pattern_attributes_c['name'], patterns[0]['name'])

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{})
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 3)
        pattern_namelist = [p['name'] for p in patterns]
        self.assertIn(pattern_attributes_a['name'], pattern_namelist)
        self.assertIn(pattern_attributes_b['name'], pattern_namelist)
        self.assertIn(pattern_attributes_c['name'], pattern_namelist)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'recipes': [self.test_recipe_name]})
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 2)
        pattern_namelist = [p['name'] for p in patterns]
        self.assertIn(pattern_attributes_a['name'], pattern_namelist)
        self.assertIn(pattern_attributes_b['name'], pattern_namelist)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'variables': {'index': 0}})
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 1)
        pattern_namelist = [p['name'] for p in patterns]
        self.assertIn(pattern_attributes_c['name'], pattern_namelist)

        patterns = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_PATTERN,
                                     **{'variables': {'iterations': 20}})
        self.assertIsNotNone(patterns)
        self.assertEqual(len(patterns), 2)
        pattern_namelist = [p['name'] for p in patterns]
        self.assertIn(pattern_attributes_a['name'], pattern_namelist)
        self.assertIn(pattern_attributes_b['name'], pattern_namelist)

        notebook = nbformat.v4.new_notebook()
        recipe_attributes_a = {
            'name': 'recipe_a',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '10',
                    'cpu cores': '12',
                    'wall time': '14',
                    'memory': '16',
                    'disks': '18',
                    'retries': '20',
                    'cpu-architecture': 'AMD64',
                    'fill': [
                        'DISK',
                    ],
                    'environment variables': [
                        'VAR=42'
                    ],
                    'notification': [
                        'email: patch@email.com'
                    ],
                    'runtime environments': [
                        'VIRTUALBOX-3.1.X-1'
                    ]
                },
                'local': {
                    'dependencies': [
                        'watchdog',
                        'mig_meow'
                    ]
                }
            }
        }

        recipe_attributes_b = {
            'name': 'recipe_b',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '10',
                    'fill': [
                        'DISK',
                        'MEMORY'
                    ]
                }
            }
        }

        recipe_attributes_c = {
            'name': 'recipe_c',
            'vgrid': self.test_vgrid,
            'recipe': notebook,
            'source': 'notebook.ipynb',
            'environments': {
                'mig': {
                    'nodes': '100',
                    'fill': [
                        'CPUCOUNT'
                    ]
                }
            }
        }

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes_a)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes_b)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        created, recipe_id = create_workflow(self.configuration,
                                             self.username,
                                             workflow_type=WORKFLOW_RECIPE,
                                             **recipe_attributes_c)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes_a)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes_b)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_b['name'], recipe_namelist)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **recipe_attributes_c)
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 1)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_c['name'], recipe_namelist)

        recipes = get_workflow_with(self.configuration,
                                    client_id=self.username,
                                    user_query=True,
                                    workflow_type=WORKFLOW_RECIPE,
                                    **{})
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 3)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)
        self.assertIn(recipe_attributes_b['name'], recipe_namelist)
        self.assertIn(recipe_attributes_c['name'], recipe_namelist)

        recipes = get_workflow_with(
            self.configuration,
            client_id=self.username,
            user_query=True,
            workflow_type=WORKFLOW_RECIPE,
            **{'environments': {'mig': {'nodes': '10'}}})
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 2)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)

        recipes = get_workflow_with(
            self.configuration,
            client_id=self.username,
            user_query=True,
            workflow_type=WORKFLOW_RECIPE,
            **{'environments': {'mig': {'fill': ['DISK']}}})
        self.assertIsNotNone(recipes)
        self.assertEqual(len(recipes), 2)
        recipe_namelist = [p['name'] for p in recipes]
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)
        self.assertIn(recipe_attributes_a['name'], recipe_namelist)

    # def test_recipe_pattern_association_creation_pattern_first(self):
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                           'processed_data':
    #                               'pattern_0_output/{FILENAME}.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     notebook = nbformat.v4.new_notebook()
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    # def test_recipe_pattern_association_creation_recipe_first(self):
    #     notebook = nbformat.v4.new_notebook()
    #
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                           'processed_data':
    #                               'pattern_0_output/{FILENAME}.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    # def test_recipe_pattern_association_deletion(self):
    #
    #     pattern_attributes = {'name': 'association test pattern',
    #                           'vgrid': self.test_vgrid,
    #                           'input_file': 'hdf5_input',
    #                           'trigger_paths': ['initial_data/*hdf5'],
    #                           'output': {
    #                               'processed_data':
    #                                  'pattern_0_output/{FILENAME}.hdf5'},
    #                           'recipes': ['association test recipe'],
    #                           'variables': {'iterations': 20}}
    #
    #     created, pattern_id = create_workflow(self.configuration,
    #                                           self.username,
    #                                           workflow_type=WORKFLOW_PATTERN,
    #                                           **pattern_attributes)
    #     self.logger.info(pattern_id)
    #     self.assertTrue(created)
    #
    #     notebook = nbformat.v4.new_notebook()
    #     recipe_attributes = {'name': 'association test recipe',
    #                          'vgrid': self.test_vgrid,
    #                          'recipe': notebook,
    #                          'source': 'print("Hello World")'}
    #
    #     created, recipe_id = create_workflow(self.configuration,
    #                                          self.username,
    #                                          workflow_type=WORKFLOW_RECIPE,
    #                                          **recipe_attributes)
    #     self.logger.info(recipe_id)
    #     self.assertTrue(created)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 1)
    #     self.assertEqual(recipes[0]['associated_patterns'][0], pattern_id)
    #
    #     deletion_attributes = {
    #         'persistence_id': pattern_id,
    #         'vgrid': self.test_vgrid
    #     }
    #
    #     deleted, msg = delete_workflow(self.configuration,
    #                                    self.username,
    #                                    workflow_type=WORKFLOW_PATTERN,
    #                                    **deletion_attributes)
    #
    #     self.logger.info(msg)
    #     self.assertTrue(deleted)
    #
    #     recipes = get_workflow_with(self.configuration,
    #                                 client_id=self.username,
    #                                 workflow_type=WORKFLOW_RECIPE,
    #                                 **recipe_attributes)
    #     self.assertIsNotNone(recipes)
    #     self.assertEqual(len(recipes), 1)
    #     self.assertIn('associated_patterns', recipes[0])
    #     self.assertEqual(len(recipes[0]['associated_patterns']), 0)


if __name__ == '__main__':
    unittest.main()
