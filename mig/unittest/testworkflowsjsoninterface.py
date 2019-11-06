#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# testworkflowsjsoninterface.py - Set of unittests for
# workflowsjsoninterface.py
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

"""Unittest functions for the Workflow JSON interface"""

import unittest
import os
import nbformat
from shared.pwhash import generate_random_ascii
from shared.conf import get_configuration_object
from shared.fileio import makedirs_rec, remove_rec
from shared.validstring import possible_workflow_session_id
from shared.workflows import touch_workflow_sessions_db, \
    load_workflow_sessions_db, create_workflow_session_id, \
    delete_workflow_sessions_db, new_workflow_session_id, \
    delete_workflow_session_id, reset_workflows, get_workflow_with, \
    WORKFLOW_PATTERN, WORKFLOW_RECIPE, WORKFLOW_ANY
from shared.functionality.workflowsjsoninterface import workflow_api_create, \
    workflow_api_delete, workflow_api_read, workflow_api_update

this_path = os.path.dirname(os.path.abspath(__file__))


class WorkflowJSONInterfaceSessionIDTest(unittest.TestCase):

    def setUp(self):
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        self.configuration = get_configuration_object()
        self.configuration.workflows_db = os.path.join(this_path,
                                                       'test_sessions_db')
        # Ensure workflows are enabled
        self.configuration.site_enable_workflows = True

    def tearDown(self):
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = os.path.join(
                os.sep, 'home', 'mig', 'mig', 'server', 'MiGserver.conf')
        configuration = get_configuration_object()
        configuration.workflows_db = os.path.join(this_path,
                                                  'test_sessions_db')
        delete_workflow_sessions_db(configuration)
        configuration.site_enable_workflows = False

    def test_workflow_session_id(self):
        wrong_session_id = generate_random_ascii(64, 'ghijklmn')
        self.assertFalse(possible_workflow_session_id(self.configuration,
                                                      wrong_session_id))
        session_id = new_workflow_session_id()
        self.assertTrue(possible_workflow_session_id(self.configuration,
                                                     session_id))

    def test_create_session_id(self):
        self.assertTrue(touch_workflow_sessions_db(self.configuration,
                                                   force=True
                                                   ))
        self.assertDictEqual(load_workflow_sessions_db(self.configuration), {})
        client_id = 'FooBar'
        workflow_session_id = create_workflow_session_id(self.configuration,
                                                         client_id)
        new_state = {workflow_session_id: {'owner': client_id}}
        new_db = load_workflow_sessions_db(self.configuration)
        self.assertEqual(new_db, new_state)
        self.assertTrue(delete_workflow_sessions_db(self.configuration))

    def test_delete_session_id(self):
        # Create
        self.assertTrue(touch_workflow_sessions_db(self.configuration,
                                                   force=True))
        client_id = 'FooBar'
        workflow_session_id = create_workflow_session_id(self.configuration,
                                                         client_id)
        new_state = {workflow_session_id: {'owner': client_id}}
        new_db = load_workflow_sessions_db(self.configuration)
        self.assertEqual(new_db, new_state)

        # Fail to remove non existing id
        self.assertFalse(delete_workflow_session_id(self.configuration,
                                                    new_workflow_session_id()))
        # Delete new_state
        self.assertTrue(delete_workflow_session_id(self.configuration,
                                                   workflow_session_id))
        self.assertEqual(load_workflow_sessions_db(self.configuration), {})
        # Delete the DB
        self.assertTrue(delete_workflow_sessions_db(self.configuration))


class WorkflowJSONInterfaceAPIFunctionsTest(unittest.TestCase):

    def setUp(self):
        self.created_workflows = []
        self.username = 'FooBar'
        self.test_vgrid = 'Generic'
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = '/home/mig/mig/server/MiGserver.conf'
        self.configuration = get_configuration_object()
        self.logger = self.configuration.logger
        # Ensure that the vgrid_files_home exist
        vgrid_file_path = os.path.join(self.configuration.vgrid_files_home,
                                       self.test_vgrid)
        if not os.path.exists(vgrid_file_path):
            self.assertTrue(makedirs_rec(vgrid_file_path, self.configuration,
                                         accept_existing=True))
        self.assertTrue(os.path.exists(vgrid_file_path))

        self.configuration.workflows_db = os.path.join(this_path,
                                                       'test_sessions_db')
        # Ensure workflows are enabled
        self.configuration.site_enable_workflows = True
        self.assertTrue(reset_workflows(self.configuration,
                                        vgrid=self.test_vgrid))
        touch_workflow_sessions_db(self.configuration, force=True)
        self.session_id = create_workflow_session_id(self.configuration,
                                                     self.username)
        self.assertIsNot(self.session_id, False)
        self.assertIsNotNone(self.session_id)

        self.workflow_sessions_db = load_workflow_sessions_db(
            self.configuration)
        self.assertIn(self.session_id, self.workflow_sessions_db)
        self.workflow_session = self.workflow_sessions_db.get(self.session_id,
                                                              None)
        self.assertIsNotNone(self.workflow_session)

    def tearDown(self):
        if not os.environ.get('MIG_CONF', False):
            os.environ['MIG_CONF'] = '/home/mig/mig/server/MiGserver.conf'
        configuration = get_configuration_object()
        test_vgrid = 'Generic'
        # Remove tmp vgrid_file_home
        vgrid_file_path = os.path.join(configuration.vgrid_files_home,
                                       test_vgrid)
        if os.path.exists(vgrid_file_path):
            self.assertTrue(remove_rec(vgrid_file_path, self.configuration))
        self.assertFalse(os.path.exists(vgrid_file_path))

        configuration.workflows_db = os.path.join(this_path,
                                                  'test_sessions_db')
        self.assertTrue(delete_workflow_sessions_db(configuration))
        # Also clear vgrid_dir of any patterns and recipes
        self.assertTrue(reset_workflows(configuration, vgrid=test_vgrid))
        configuration.site_enable_workflows = False

    def test_create_workflow(self):
        notebook = nbformat.v4.new_notebook()
        pattern_name = 'test_pattern'
        recipe_name = 'test_recipe'
        recipe = {'name': recipe_name,
                  'vgrid': self.test_vgrid,
                  'recipe': notebook}

        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        pattern = {'name': pattern_name,
                   'vgrid': self.test_vgrid,
                   'input_paths': ['input_dir/*hdf5'],
                   'input_file': 'hdf5_input',
                   'output': {
                       'output_dir': 'pattern_0_output_variable_name'},
                   'recipes': [recipe_name],
                   'variables': {}}

        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **pattern)

        self.assertTrue(created)

    def test_create_workflow_pattern(self):
        pattern_name = 'test_pattern_0'
        recipe_name = 'test_recipe_0'
        minimum_pattern_attributes = {'name': pattern_name,
                                      'vgrid': self.test_vgrid,
                                      'input_paths': ['input_dir/*.hdf5'],
                                      'input_file': 'hdf5_input',
                                      'output': {},
                                      'recipes': [recipe_name]}

        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **minimum_pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **{'persistence_id': pattern_id})

        self.logger.warning("Workflow returned '%s'" % workflow)
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'],
                         minimum_pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'],
                         minimum_pattern_attributes['vgrid'])
        # TODO, update input_paths and recipe testing

        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

        pattern_name = 'test_pattern_1'
        full_pattern_attributes = {
            'name': pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'output_dir': 'pattern_0_output_variable_name'},
            'recipes': [recipe_name],
            'variables': {'iterations': 20}}

        created, pattern_id_1 = workflow_api_create(self.configuration,
                                                    self.workflow_session,
                                                    WORKFLOW_PATTERN,
                                                    **full_pattern_attributes)
        self.logger.info(pattern_id_1)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **{'persistence_id': pattern_id_1})
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id_1)
        self.assertEqual(workflow[0]['name'],
                         full_pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'],
                         full_pattern_attributes['vgrid'])
        # TODO, update input_paths and recipe testing

    def test_create_workflow_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_name = 'test_recipe_0'
        recipe_attributes = {'name': recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}

        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     workflow_type=WORKFLOW_RECIPE,
                                     **{'persistence_id': recipe_id})
        self.assertIsNotNone(workflow)
        self.logger.info(workflow)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(workflow[0][k], v)

    def test_create_read_delete_pattern(self):
        pattern_name = 'test_pattern_0'
        recipe_name = 'test_recipe_0'
        pattern_attributes = {
            'name': pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['initial_data/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'output_dir': 'pattern_0_output_variable_name'},
            'recipes': [recipe_name],
            'variables': {'iterations': 20}}

        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'],
                         pattern_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'],
                         pattern_attributes['vgrid'])
        # TODO, update input_paths and recipe testing

        # TODO, validate it has the expected attributes
        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': pattern_id}

        deleted, deleted_id = workflow_api_delete(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **delete_attributes)
        self.logger.info(deleted_id)
        self.assertTrue(deleted)

        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_PATTERN,
                                     **{'persistence_id': deleted_id})
        self.assertEqual(workflow, [])

    def test_create_read_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_name = 'test_recipe_0'
        recipe_attributes = {'name': recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}

        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)
        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_RECIPE,
                                     **{'persistence_id': recipe_id})
        self.assertIsNot(workflow, False)
        self.assertEqual(len(workflow), 1)
        # Strip internal attributes
        for k, v in recipe_attributes.items():
            self.assertEqual(workflow[0][k], v)

        # TODO, validate it has the expected attributes
        delete_attributes = {'vgrid': self.test_vgrid,
                             'persistence_id': recipe_id}

        deleted, msg = workflow_api_delete(self.configuration,
                                           self.workflow_session,
                                           WORKFLOW_RECIPE,
                                           **delete_attributes)
        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_RECIPE,
                                     **{'persistence_id': msg})
        self.assertEqual(workflow, [])

    def test_update_pattern(self):
        pattern_name = 'test_pattern'
        recipe_name = 'test_recipe'
        pattern_attributes = {
            'name': pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*.hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'output_dir': 'pattern_0_output_variable_name'},
            'recipes': [recipe_name],
            'variables': {'iterations': 20}}

        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)
        pattern_new_name = 'test_updated_pattern'
        new_attributes = {'name': pattern_new_name,
                          'vgrid': self.test_vgrid,
                          'persistence_id': pattern_id}

        # TODO Try update without persistence_id
        updated, pattern_id = workflow_api_update(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **new_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(updated)
        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_PATTERN,
                                     **{'persistence_id': pattern_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['persistence_id'], pattern_id)
        self.assertEqual(workflow[0]['name'], new_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], new_attributes['vgrid'])

    def test_update_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_name = 'test_recipe'
        recipe_attributes = {'name': recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}

        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe_attributes)
        self.assertTrue(created)
        recipe_new_name = 'test_updated_recipe'
        new_attributes = {'name': recipe_new_name,
                          'vgrid': self.test_vgrid,
                          'persistence_id': recipe_id}
        # TODO Try update without persistence_id
        updated, recipe_id = workflow_api_update(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **new_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(updated)

        workflow = workflow_api_read(self.configuration,
                                     self.workflow_session,
                                     WORKFLOW_RECIPE,
                                     **{'persistence_id': recipe_id})
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]['persistence_id'], recipe_id)
        self.assertEqual(workflow[0]['name'], new_attributes['name'])
        self.assertEqual(workflow[0]['vgrid'], new_attributes['vgrid'])

    def test_clear_user_worklows(self):
        pattern_name = 'test_pattern'
        recipe_name = 'test_recipe'
        pattern_attributes = {
            'name': pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['input_dir/*hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'output_dir': 'pattern_0_output_variable_name'},
            'recipes': [recipe_name],
            'variables': {'iterations': 20}}
        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        notebook = nbformat.v4.new_notebook()
        recipe_name = 'test_update_recipe'
        recipe_attributes = {'name': recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}
        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        # Get every workflow in vgrid
        workflows = workflow_api_read(self.configuration,
                                      self.workflow_session,
                                      WORKFLOW_ANY,
                                      **{'vgrid': self.test_vgrid})
        self.assertIsNotNone(workflows)
        # Verify that the created objects exist
        self.assertEqual(len(workflows), 2)
        for workflow in workflows:
            if workflow['object_type'] == WORKFLOW_PATTERN:
                self.assertEqual(workflow['persistence_id'], pattern_id)
                self.assertEqual(workflow['name'], pattern_attributes['name'])
                self.assertEqual(workflow['vgrid'],
                                 pattern_attributes['vgrid'])
                self.assertEqual(workflow['variables'],
                                 pattern_attributes['variables'])
                continue

            if workflow['object_type'] == WORKFLOW_RECIPE:
                self.assertEqual(workflow['persistence_id'], recipe_id)
                for k, v in recipe_attributes.items():
                    self.assertEqual(workflow[k], v)
        self.assertTrue(reset_workflows(self.configuration,
                                        client_id=self.username))

        no_workflows = workflow_api_read(self.configuration,
                                         self.workflow_session,
                                         WORKFLOW_ANY,
                                         **{'vgrid': self.test_vgrid})
        self.assertEqual(no_workflows, [])

    def test_delete_pattern(self):
        pattern_name = 'test_pattern'
        recipe_name = 'test_recipe'
        pattern_attributes = {
            'name': pattern_name,
            'vgrid': self.test_vgrid,
            'input_paths': ['initial_data/*hdf5'],
            'input_file': 'hdf5_input',
            'output': {
                'output_dir': 'pattern_0_output_variable_name'},
            'recipes': [recipe_name],
            'variables': {'iterations': 20}}

        created, pattern_id = workflow_api_create(self.configuration,
                                                  self.workflow_session,
                                                  WORKFLOW_PATTERN,
                                                  **pattern_attributes)
        self.logger.info(pattern_id)
        self.assertTrue(created)

        deletion_attributes = {
            'persistence_id': pattern_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = workflow_api_delete(self.configuration,
                                           self.workflow_session,
                                           workflow_type=WORKFLOW_PATTERN,
                                           **deletion_attributes)

        self.logger.info(msg)
        self.assertTrue(deleted)
        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)

        self.assertEqual(workflow, [])

    def test_delete_recipe(self):
        notebook = nbformat.v4.new_notebook()
        recipe_name = 'test_recipe'
        recipe_attributes = {'name': recipe_name,
                             'vgrid': self.test_vgrid,
                             'recipe': notebook,
                             'source': ''}

        created, recipe_id = workflow_api_create(self.configuration,
                                                 self.workflow_session,
                                                 WORKFLOW_RECIPE,
                                                 **recipe_attributes)
        self.logger.info(recipe_id)
        self.assertTrue(created)

        deletion_attributes = {
            'persistence_id': recipe_id,
            'vgrid': self.test_vgrid
        }

        deleted, msg = workflow_api_delete(self.configuration,
                                           self.workflow_session,
                                           workflow_type=WORKFLOW_RECIPE,
                                           **deletion_attributes)

        self.logger.info(msg)
        self.assertTrue(deleted)

        workflow = get_workflow_with(self.configuration,
                                     client_id=self.username,
                                     user_query=True,
                                     **deletion_attributes)

        self.assertEqual(workflow, [])


if __name__ == '__main__':
    unittest.main()
