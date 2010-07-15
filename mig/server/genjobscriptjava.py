#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genjobscriptjava - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""In java the script is just a configuration file for telling
the remote java mechanism where to retrieve the executable 
 and corresponding files.
"""

from shared.job import output_dir


class GenJobScriptJava:

    def __init__(
        self,
        job_dictionary,
        resource_config,
        https_sid_url,
        localjobnam,
        filename_without_ext,
        ):

        global job_dict
        job_dict = job_dictionary
        global resource_conf
        resource_conf = resource_config
        global https_sid_url_arg
        https_sid_url_arg = https_sid_url
        global filename_without_extension
        filename_without_extension = filename_without_ext
        global localjobname
        localjobname = localjobnam

    def comment(self, string):
        return '# ' + string + '\n'

    def script_init(self):
        """Initialize script"""

        init = \
            '''# Java resource configuration file
#
# --- BEGIN_HEADER ---
#
# ??? - one of the java helper files used on resources
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

'''
        init = init + 'mig_session_id: ' + job_dict['MIGSESSIONID']\
             + '\n'
        init = init + 'mig_iosession_id: ' + job_dict['MIGIOSESSIONID']\
             + '\n'
        init = init + 'job_id: ' + job_dict['JOB_ID'] + '\n'
        return init

    def print_start(self, name='job'):
        return 'info: Starting new %s with JOB_ID: %s\n' % (name,
                job_dict['JOB_ID'])

    def create_files(self, files):
        """Create supplied files"""

        return ''

    def init_status(self):
        return ''

    def init_io_log(self):
        return ''

    def log_io_status(self, io_type, result='ret'):
        return ''

    def create_job_directory(self):
        return ''

    def cd_to_job_directory(self):
        return ''

    def get_input_files(self, result='get_input_status'):
        return ''

    def get_special_input_files(self, result='get_special_status'):
        return ''

    def generate_input_filelist(self, result='generate_input_filelist'):
        return ''

    def generate_output_filelists(self, user_cert,
                                  result='generate_output_filelists'):
        return ''

    def get_executables(self, result='get_executables_status'):
        cmd = ''
        for executables in job_dict['EXECUTABLES']:
            parts = executables.split()
            mig_server_filename = str(parts[0])
            cmd += 'executables: ' + '/sid_redirect/'\
                 + mig_server_filename + '\n'

        return cmd

    def get_io_files(self, result='get_io_status'):
        return ''

    def generate_iosessionid_file(self,
                                  result='generate_iosessionid_file'):
        return ''

    def chmod_executables(self, result='chmod_status'):
        return ''

    def set_core_environments(self):
        return

    def set_environments(self, result='env_result'):
        return ''

    def set_runtime_environments(self, resource_runtimeenvironment,
                                 result='re_result'):
        return ''

    def execute(self, pretext, posttext):
        cmd = ''
        for exe in job_dict['EXECUTE']:
            cmd += 'execute: ' + exe + '\n'

        return cmd

    def output_files_missing(self, result='missing_counter'):
        return ''

    def send_output_files(self, result='send_output_status'):
        return ''

    def send_io_files(self, result='send_io_status'):
        cmd = ''

        cmd += 'stdout: ' + https_sid_url_arg\
               + '/sid_redirect/' + job_dict['MIGSESSIONID'] + '/'\
               + output_dir + '/' + job_dict['JOB_ID'] + '/'\
               + job_dict['JOB_ID'] + '.stdout\n'
        cmd += 'stderr: ' + https_sid_url_arg\
               + '/sid_redirect/' + job_dict['MIGSESSIONID'] + '/'\
               + output_dir + '/' + job_dict['JOB_ID'] + '/'\
               + job_dict['JOB_ID'] + '.stderr\n'
        cmd += 'io-status: ' + https_sid_url_arg\
               + '/sid_redirect/' + job_dict['MIGSESSIONID'] + '/'\
               + output_dir + '/' + job_dict['JOB_ID'] + '/'\
               + job_dict['JOB_ID'] + '.io-status\n'
        return cmd

    def send_status_files(self, files, result='send_status_status'):
        cmd = ''
        for name in files:
            if name.count('status') > 0:
                cmd += 'status: ' + https_sid_url_arg\
                     + '/sid_redirect/' + job_dict['MIGSESSIONID'] + '/'\
                     + output_dir + '/' + job_dict['JOB_ID'] + '/'\
                     + name + '\n'
        return cmd

    def save_status(self, result='ret'):
        return ''

    def total_status(self, variables, result='total_status'):
        return ''

    def print_on_error(
        self,
        result='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
        ):

        return ''

    def exit_on_error(
        self,
        result='ret',
        successcode='0',
        exitcode='$ret',
        ):

        return ''

    def exit_script(self, exitcode='0', name=''):
        return ''

    def clean_up(self):
        return ''


