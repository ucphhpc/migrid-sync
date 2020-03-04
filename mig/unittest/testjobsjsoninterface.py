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

import os
import unittest
import nbformat

from shared.conf import get_configuration_object
from shared.defaults import default_vgrid
from shared.fileio import makedirs_rec, remove_rec
from shared.functionality.jobsjsoninterface import job_api_create, \
    job_api_read, job_api_update
from shared.job import JOB, QUEUE
from shared.workflows import touch_workflow_sessions_db, \
    load_workflow_sessions_db, create_workflow_session_id, \
    delete_workflow_sessions_db, reset_workflows

this_path = os.path.dirname(os.path.abspath(__file__))


class JobJSONInterfaceAPIFunctionsTest(unittest.TestCase):

    def setUp(self):
        self.created_workflows = []
        self.username = 'FooBar'
        self.test_vgrid = default_vgrid
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
        # Ensure that the mrsl_files home exists
        mrsl_file_path = os.path.join(self.configuration.mrsl_files_dir,
                                      self.username)
        if not os.path.exists(mrsl_file_path):
            self.assertTrue(
                makedirs_rec(mrsl_file_path, self.configuration,
                             accept_existing=True))
        self.assertTrue(os.path.exists(vgrid_file_path))

        self.configuration.workflows_db_home = this_path
        self.configuration.workflows_db = \
            os.path.join(this_path, 'test_sessions_db.pickle')
        self.configuration.workflows_db_lock = \
            os.path.join(this_path, 'test_sessions_db.lock')
        self.assertTrue(reset_workflows(self.configuration,
                                        vgrid=self.test_vgrid))
        created = touch_workflow_sessions_db(self.configuration, force=True)
        self.assertTrue(created)
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
        test_vgrid = default_vgrid
        # Remove tmp vgrid_file_home
        vgrid_file_path = os.path.join(configuration.vgrid_files_home,
                                       test_vgrid)
        if os.path.exists(vgrid_file_path):
            self.assertTrue(remove_rec(vgrid_file_path, self.configuration))
        self.assertFalse(os.path.exists(vgrid_file_path))
        # Remove tmp mrsl_files
        mrsl_file_path = os.path.join(configuration.mrsl_files_dir,
                                      self.username)
        if os.path.exists(mrsl_file_path):
            self.assertTrue(remove_rec(mrsl_file_path, self.configuration))
        self.assertFalse(os.path.exists(mrsl_file_path))
        configuration.workflows_db_home = this_path
        configuration.workflows_db = \
            os.path.join(this_path, 'test_sessions_db.pickle')
        configuration.workflows_db_lock = \
            os.path.join(this_path, 'test_sessions_db.lock')

        self.assertTrue(delete_workflow_sessions_db(configuration))
        # Also clear vgrid_dir of any patterns and recipes
        self.assertTrue(reset_workflows(configuration, vgrid=test_vgrid))
        configuration.site_enable_workflows = False

    def test_job_create(self):
        job = {'EXECUTE': "echo 'hello world",
               'MEMORY': '1',
               'DISK': '1',
               'CPUTIME': '1',
               'vgrid': self.test_vgrid}

        created, job_id = job_api_create(self.configuration,
                                         self.workflow_session,
                                         JOB,
                                         **job)
        self.logger.info(job_id)
        self.assertTrue(created)

    def test_job_read(self):
        job_attributes = {'EXECUTE': "echo 'hello world",
               'MEMORY': '1',
               'DISK': '1',
               'CPUTIME': '1',
               'vgrid': self.test_vgrid}

        created, job_id = job_api_create(self.configuration,
                                         self.workflow_session,
                                         JOB,
                                         **job_attributes)
        self.logger.info(job_id)
        self.assertTrue(created)

        read_attributes = {
            'job_id': job_id,
            'vgrid': self.test_vgrid
         }

        status, job = job_api_read(self.configuration,
                                self.workflow_session,
                                JOB,
                                **read_attributes)

        self.assertTrue(status)
        self.assertIsInstance(job, dict)
        # Check internal attributes
        self.assertEqual(job['JOB_ID'], job_id)
        self.assertEqual(job['EXECUTE'], ["echo 'hello world"])
        self.assertEqual(job['MEMORY'], 1)
        self.assertEqual(job['DISK'], 1)
        self.assertEqual(job['CPUTIME'], 1)

    def test_job_update(self):
        job_attributes = {'EXECUTE': "echo 'hello world",
                          'MEMORY': '1',
                          'DISK': '1',
                          'CPUTIME': '1',
                          'vgrid': self.test_vgrid}

        created, job_id = job_api_create(self.configuration,
                                         self.workflow_session,
                                         JOB,
                                         **job_attributes)
        self.logger.info(job_id)
        self.assertTrue(created)

        new_attributes = {'JOB_ID': job_id,
                          'STATUS': 'CANCELED',
                          'vgrid': self.test_vgrid}

        status, updated = job_api_update(self.configuration,
                                      self.workflow_session,
                                      JOB,
                                      **new_attributes)

        self.assertTrue(status)


if __name__ == '__main__':
    unittest.main()
