#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genjobscriptpython - helpers for python jobs
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Python job script generator and functions"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import object
import os

from mig.shared.defaults import job_output_dir


class GenJobScriptPython(object):
    """Python job script generator"""

    def __init__(
        self,
        job_dictionary,
        resource_config,
        exe_unit,
        https_sid_url,
        localjobname,
        filename_without_ext,
    ):

        self.job_dict = job_dictionary
        self.resource_conf = resource_config
        self.exe = exe_unit
        self.https_sid_url_arg = https_sid_url
        self.filename_without_extension = filename_without_ext
        self.localjobname = localjobname

        exe_dir = ''
        exe_list = self.resource_conf.get('EXECONFIG', [])
        for exe_conf in exe_list:
            if exe_conf['name'] == self.exe:
                localexedir = exe_conf['execution_dir']
                break

        self.localjobdir = "%s/job-dir_%s" % (localexedir, self.localjobname)
        self.status_log = '%s/%s.status' % (self.localjobdir,
                                            self.job_dict['JOB_ID'])
        self.io_log = '%s.io-status' % self.job_dict['JOB_ID']

        print("""Python resource scripts are *not* fully supported!
Please use Sh as SCRIPTLANGUAGE on your resources if this fails!""")

    def __curl_cmd_send(self, resource_filename, mig_server_filename):
        """Upload files"""

        return "curl --location --fail --silent --insecure --upload-file '" + \
               resource_filename + "' -X SIDPUT '" + self.https_sid_url_arg + \
               '/sid_redirect/' + self.job_dict['SESSIONID'] + '/' + \
               mig_server_filename + "'"

    def __curl_cmd_get(self, mig_server_filename, resource_filename):
        """Download files"""

        dest_path = os.path.split(resource_filename)[0]
        cmd = ''
        if dest_path != '':
            cmd += "mkdir -p '%s' && \\" % dest_path
            cmd += '\n'
        cmd += "curl --location --fail --silent --insecure -o '" + \
               resource_filename + "' '" + self.https_sid_url_arg + \
               '/sid_redirect/' + self.job_dict['SESSIONID'] + '/' + \
               mig_server_filename + "'"
        return cmd

    def __curl_cmd_get_special(self, file_extension, resource_filename):
        """Download internal job files"""

        dest_path = os.path.split(resource_filename)[0]
        cmd = ''
        if dest_path != '':
            cmd += 'mkdir -p %s && \\' % dest_path
            cmd += '\n'
        cmd += "curl --location --fail --silent --insecure -o '" + \
               resource_filename + "' '" + self.https_sid_url_arg + \
               '/sid_redirect/' + self.job_dict['SESSIONID'] + \
               file_extension + "'"
        return cmd

    def __curl_cmd_request_interactive(self):
        """CGI request for interactive job"""

        int_command = "curl --location --fail --silent --insecure '" + \
                      self.https_sid_url_arg + \
                      '/cgi-sid/requestinteractivejob.py?sessionid=' + \
                      self.job_dict['SESSIONID'] + '&jobid=' + \
                      self.job_dict['JOB_ID'] + '&exe=' + self.exe + \
                      '&unique_resource_name=' + \
                      self.resource_conf['RESOURCE_ID'] + \
                      '&self.localjobname=' + self.localjobname + "'\n"
        int_command += '# wait until interactive command is done\n'
        int_command += 'while [ 1 ]; do\n'
        int_command += '   if [ -f .interactivejobfinished ]; then\n'
        int_command += '        break\n'
        int_command += '   else\n'
        int_command += '        sleep 3\n'
        int_command += '   fi\n'
        int_command += 'done\n'
        return int_command

    def comment(self, string):
        """Insert comment"""

        return '""" ' + string + ' """ \n'

    def script_init(self):
        """initialize script"""

        return '''#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ??? - one of the python scripts running on resources
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
#
# -- END_HEADER ---
#

import os
import stat
import subprocess
from os.path import join, getsize
'''

    def print_start(self, name='job'):
        """print 'starting new job'"""

        return "print 'Starting new %s with JOB_ID: %s'\n" % \
               (name, self.job_dict['JOB_ID'])

    def create_files(self, files):
        """Create supplied files"""

        cmd = ''
        for path in files:

            # Create/truncate files by opening in 'w' mode

            cmd += "open('%s', 'w').close()\n" % path
        return cmd

    def init_status(self):
        """Initialize status file"""

        return "status_log = open(%s, 'w')" % self.status_log

    def log_status(self, status_type, result='ret'):
        """Write to status log"""

        return '''status_log.write("%s " + %s)
status_log.flush()''' % (status_type, result)

    def init_io_log(self):
        """Open IO status log"""

        return "io_log = open(%s, 'w')" % self.io_log

    def log_io_status(self, io_type, result='ret'):
        """Write to IO status log"""

        return '''io_log.write("%s " + %s)
io_log.flush()''' % (io_type, result)

    def create_job_directory(self):
        """if directory with name JOB_ID doesnt exists, then create.
        cd into it."""

        cmd = 'if os.path.isdir("' + self.job_dict['JOB_ID'] + '")==False:\n'
        cmd += '   os.mkdir("' + self.job_dict['JOB_ID'] + '")\n'
        return cmd

    def cd_to_job_directory(self):
        """Enter execution directory"""

        return 'os.chdir("' + self.job_dict['JOB_ID'] + '")'

    def get_input_files(self, result='get_input_status'):
        """get the inputfiles from the grid server"""

        cmd = ''

        for infile in self.job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = infile.split()
            mig_server_filename = "%s" % parts[0]
            try:
                resource_filename = "%s" % parts[1]
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs
            # attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external
                # sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            cmd += 'subprocess.call("%s")\n' % \
                   self.__curl_cmd_get(mig_server_filename, resource_filename)
        return cmd

    def get_special_input_files(self, result='get_special_status'):
        """get the internal job files from the grid server"""

        cmd = ''
        cmd += self.__curl_cmd_get_special(
            '.job', self.localjobname + '.job') + ' && \\' + '\n'

        cmd += '''
%s
''' % self.__curl_cmd_get_special('.getupdatefiles',
                                  self.localjobname + '.getupdatefiles')
        cmd += '''
%s
''' % self.__curl_cmd_get_special('.sendupdatefiles',
                                  self.localjobname + '.sendupdatefiles')
        cmd += '''
%s
''' % self.__curl_cmd_get_special('.sendoutputfiles',
                                  self.localjobname + '.sendoutputfiles')
        return cmd

    def get_executables(self, result='get_executables_status'):
        """Get EXECUTABLES (inputfiles and +x)"""

        cmd = ''
        for executables in self.job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = executables.split()
            mig_server_filename = "%s" % parts[0]
            try:
                resource_filename = "%s" % parts[1]
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs
            # attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external
                # sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # NOTE: for security we do not invoke shell here
            cmd += 'subprocess.call("%s")\n' % \
                   self.__curl_cmd_get(mig_server_filename, resource_filename)
        return cmd

    def get_io_files(self, result='get_io_status'):
        """Get live files from server during job execution"""

        cmd = ''
        cmd += 'dst = sys.argv[-1]\n'
        cmd += 'for name in sys.argv[1:-1]:\n'
        cmd += '  name_on_resource = os.path.join(dst, os.path.basename(name))\n'
        # NOTE: for security we do not invoke shell here
        cmd += '  subprocess.call("%s")\n' % \
               self.__curl_cmd_get('name', 'name_on_resource')
        return cmd

    def generate_input_filelist(self, result='generate_input_filelist'):
        """Generate filelist (user/system) of which files 
        should be transfered from FE to EXE before job execution."""

        cmd = '# Create files used by master_node_script ' + \
              '(input/executables/systemfiles)\n'
        fe_move_dict = {}

        for infile in self.job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = infile.split()
            mig_server_filename = "%s" % parts[0]
            try:
                resource_filename = "%s" % parts[1]
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs
            # extra attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefix in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            fe_move = resource_filename.split('/', 1)[0]

            if fe_move not in fe_move_dict:
                fe_move_dict[fe_move] = True

        for executables in self.job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = executables.split()
            mig_server_filename = "%s" % parts[0]
            try:
                resource_filename = "%s" % parts[1]
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs
            # extra attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefix in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            fe_move = resource_filename.split('/', 1)[0]

            if fe_move not in fe_move_dict:
                fe_move_dict[fe_move] = True

        cmd += 'input_fd = open("%s.inputfiles", "w")\n' % self.localjobname
        for filename in fe_move_dict:
            cmd += '''
if os.path.isfile("%s"):
    input_fd.write("%s ")
''' % (filename, filename)
        cmd += 'input_fd.close()\n'

        # Systemfiles

        cmd += 'output_fd = open("%s.outputfiles", "w")\n' % self.localjobname
        cmd += 'output_fd.write("%s.user.outputfiles ")\n' % self.localjobname
        cmd += 'output_fd.write("%s.system.outputfiles ")\n' % \
               self.localjobname
        cmd += 'output_fd.write("%s.job")\n' % self.localjobname
        cmd += 'output_fd.close()\n'
        return cmd

    def generate_output_filelists(self, real_job,
                                  result='generate_output_filelists'):
        """Generate filelists (user/system) of which files
        should be transfered from EXE to FE upon job finish."""

        exe_move_dict = {}
        cmd = '# Create files used by master_node_script to determine ' + \
              'which output files to transfer to FE\n'

        cmd += 'output_fd = open("%s.user.outputfiles", "w")\n' % \
               self.localjobname
        for outputfile in self.job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename mig_server_filename"

            parts = outputfile.split()
            resource_filename = "%s" % parts[0]

            # We don't need mig_server_filename here so just skip mangling

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            exe_move = resource_filename.split('/', 1)[0]

            if exe_move not in exe_move_dict:
                exe_move_dict[exe_move] = True

        for filename in exe_move_dict:
            cmd += 'output_fd.write("%s ")\n' % filename
        cmd += 'output_fd.close()\n'
        cmd += 'output_fd = open("%s.system.outputfiles", "w")\n' % \
               self.localjobname

        # Sleep jobs only generate .status

        if real_job:
            cmd += 'output_fd.write("%s.stderr ")\n' % self.job_dict['JOB_ID']
            cmd += 'output_fd.write("%s.stdout ")\n' % self.job_dict['JOB_ID']
            cmd += 'output_fd.write("%s.status ")\n' % self.job_dict['JOB_ID']
        cmd += 'output_fd.close()\n'
        return cmd

    def generate_iosessionid_file(self,
                                  result='generate_iosessionid_file'):
        """Generate file containing io-sessionid."""

        cmd = '# Create file used containing io-sessionid.\n'
        cmd += 'iosid_fd = open("%s.iosessionid", "w")\n' % self.localjobname
        cmd += 'iosid_fd.write("%s")\n' % self.job_dict['IOSESSIONID']
        cmd += 'iosid_fd.close()\n'
        return cmd

    def generate_mountsshprivatekey_file(self,
                                         result='generate_mountsshprivatekey_file'):
        """Generate file containing mount ssh private key."""

        cmd = '# Create file used containing mount private key.\n'
        cmd += 'mountprivkey_fd = open("%s.mount.key", "w")\n' % self.localjobname
        cmd += 'mountprivKey_fd.write("%s")\n' % \
               self.job_dict['MOUNTSSHPRIVATEKEY']
        cmd += 'mountprivkey_fd.close()\n'
        return cmd

    def generate_mountsshknownhosts_file(
            self, result='generate_mountsshknownhosts_file'):
        """Generate file containing mount ssh known_hosts."""

        cmd = '# Create known_hosts file used when mounting job home.\n'
        cmd += 'mountknownhosts_fd = open("%s.mount.known_host", "w")\n' % \
               self.localjobname
        cmd += 'mountknownhosts_fd.write("%s")\n' % \
               self.job_dict['MOUNTSSHKNOWNHOSTS']
        cmd += 'mountknownhosts_fd.close()\n'
        return cmd

    def chmod_executables(self, result='chmod_status'):
        """Make sure EXECUTABLES are actually executable"""

        cmd = ''
        for executables in self.job_dict['EXECUTABLES']:
            cmd += 'os.chmod("' + executables + '", stat.S_IRWXU)'
        return cmd

    def set_core_environments(self):
        """Set missing core environments: LRMS may strip them during submit"""
        requested = {'CPUTIME': self.job_dict['CPUTIME']}
        requested['NODECOUNT'] = self.job_dict.get('NODECOUNT', 1)
        requested['CPUCOUNT'] = self.job_dict.get('CPUCOUNT', 1)
        requested['MEMORY'] = self.job_dict.get('MEMORY', 1)
        requested['DISK'] = self.job_dict.get('DISK', 1)
        requested['JOBID'] = self.job_dict.get('JOB_ID', 'UNKNOWN')
        requested['LOCALJOBNAME'] = self.localjobname
        requested['EXE'] = self.exe
        requested['EXECUTION_DIR'] = ''
        exe_list = self.resource_conf.get('EXECONFIG', [])
        for exe_conf in exe_list:
            if exe_conf['name'] == self.exe:
                requested['EXECUTION_DIR'] = exe_conf['execution_dir']
                break
        requested['JOBDIR'] = '%(EXECUTION_DIR)s/job-dir_%(LOCALJOBNAME)s' % \
                              requested
        cmd = '''
if not os.environ.get("MIG_JOBNODES", ""):
  os.putenv("MIG_JOBNODES", "%(NODECOUNT)s")
if not os.environ.get("MIG_JOBNODECOUNT", ""):
  os.putenv("MIG_JOBNODECOUNT", "%(NODECOUNT)s")
if not os.environ.get("MIG_JOBCPUTIME", ""):
  os.putenv("MIG_JOBCPUTIME", "%(CPUTIME)s")
if not os.environ.get("MIG_JOBCPUCOUNT", ""):
  os.putenv("MIG_JOBCPUCOUNT", "%(CPUCOUNT)s")
if not os.environ.get("MIG_JOBMEMORY", ""):
  os.putenv("MIG_JOBMEMORY", "%(MEMORY)s")
if not os.environ.get("MIG_JOBDISK", ""):
  os.putenv("MIG_JOBDISK", "%(DISK)s")
if not os.environ.get("MIG_JOBID", ""):
  os.putenv("MIG_JOBID", "%(JOBID)s")
if not os.environ.get("MIG_LOCALJOBNAME", ""):
  os.putenv("MIG_LOCALJOBNAME", "%(LOCALJOBNAME)s")
if not os.environ.get("MIG_EXEUNIT", ""):
  os.putenv("MIG_EXEUNIT", "%(EXE)s")
if not os.environ.get("MIG_EXENODE", ""):
  os.putenv("MIG_EXENODE", "%(EXE)s")
if not os.environ.get("MIG_JOBDIR", ""):
  os.putenv("MIG_JOBDIR", "%(JOBDIR)s")
''' % requested
        return cmd

    def set_environments(self, result='env_result'):
        """Set environments"""

        cmd = ''

        for env in self.job_dict['ENVIRONMENT']:
            key_and_value = env.split('=', 1)
            cmd += 'os.putenv("' + key_and_value[0] + '","' + \
                   key_and_value[1] + '")\n'

        return cmd

    def set_limits(self):
        """Set local resource limits to prevent fork bombs, OOM and such"""
        # TODO: implement limits!
        return ''

    def set_runtime_environments(self, resource_runtimeenvironment,
                                 result='re_result'):
        """Set Runtimeenvironments"""

        cmd = ''

        # loop the runtimeenvs that the job require

        for env in self.job_dict['RUNTIMEENVIRONMENT']:

            # set the envs as specified in the resources config file

            for res_env in resource_runtimeenvironment:

                # check if this is the right env in resource config

                (res_env_name, res_env_val) = res_env
                if env == res_env_name:

                    # this is the right list of envs. Loop the entire list and
                    # set all the envs

                    for single_env in res_env_val:
                        (key, value) = single_env

                        cmd += 'os.putenv("' + key + '","' + value + '")\n'

        return cmd

    def mount(self, login, host, port, result='mount_status'):
        print("WARNING: genjobscriptpython.mount NOT implemented")

        return '# TODO: Implement MiG home mount\n'

    def execute(self, pretext, posttext):
        """Command execution"""

        stdout = self.job_dict['JOB_ID'] + '.stdout'
        stderr = self.job_dict['JOB_ID'] + '.stderr'
        status = self.job_dict['JOB_ID'] + '.status'
        cmd = ''

        cmd += 'status_handle = open("' + status + '","w")\n'

        for exe in self.job_dict['EXECUTE']:
            exe = exe.replace('"', '\\"')
            cmd += 'print "' + pretext + exe + '"\n'

            cmd += 'if "' + exe + '".find(" >> ") != -1:\n'
            cmd += '   filehandle = subprocess.Popen("' + exe + ' 2>> ' + \
                   stdout + '", stdout=subprocess.PIPE).stdout\n'
            cmd += 'else:\n'
            cmd += '   filehandle = subprocess.Popen("' + exe + ' >> ' + \
                   stdout + ' 2>> ' + stderr + \
                   '", stdout=subprocess.PIPE).stdout\n'
            cmd += 'status = filehandle.close()\n'
            cmd += 'if status == None:\n'
            cmd += '  status = "0"\n'
            cmd += 'else:\n'
            cmd += '  status = "%s" % status\n'
            cmd += 'status_handle.write("' + exe + ' %s\\n" % status)\n'
            cmd += 'print "' + posttext + '%s" % status\n'

        cmd += 'status_handle.close()\n'

        return cmd

    def umount(self, status='umount_status'):
        print("WARNING: genjobscriptpython.umount NOT implemented")

        return '# TODO: Implement MiG home umount\n'

    def output_files_missing(self, result='missing_counter'):
        """Check availability of outputfiles:
        Return number of missing files.
        """

        cmd = '%s = 0\n' % result
        for outputfile in self.job_dict['OUTPUTFILES']:
            cmd += 'if not os.path.isfile("' + outputfile + '":\n'
            cmd += '  %s += 1\n' % result
        return cmd

    def send_output_files(self, result='send_output_status'):
        """Send outputfiles"""

        cmd = ''

        for outputfile in self.job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename mig_server_filename"

            parts = outputfile.split()
            resource_filename = "%s" % parts[0]
            try:
                mig_server_filename = "%s" % parts[1]
            except:
                mig_server_filename = resource_filename

            # External destinations will always be explicit so no
            # need to mangle protocol prefix here as in get inputfiles

            # Always strip leading slashes to avoid absolute paths

            mig_server_filename = mig_server_filename.lstrip('/')

            cmd += 'if (os.path.isfile("' + resource_filename + \
                   '") and os.path.getsize("' + resource_filename + \
                   '") > 0):\n'
            # NOTE: for security we do not invoke shell here
            cmd += '  subprocess.call("%s")\n' % \
                   self.__curl_cmd_send(resource_filename, mig_server_filename)
        return cmd

    def send_io_files(self, result='send_io_status'):
        """Send IO files:
        Existing files must be transferred with status 0, while
        non-existing files shouldn't lead to error.
        Only react to curl transfer errors, not MiG put errors
        since we can't handle the latter consistently anyway.
        """

        cmd = ''
        cmd += 'dst = sys.argv[-1]\n'
        cmd += 'for src in sys.argv[1:-1]:\n'
        cmd += '  # stored in flat structure on FE\n'
        cmd += '  name = os.path.basename(src)\n'
        cmd += '  name_on_mig_server = os.path.join(dst, name)\n'
        cmd += '  if (os.path.isfile(name) and os.path.getsize(name) > 0):\n'
        # NOTE: for security we do not invoke shell here
        cmd += '    subprocess.call("%s")\n' % \
               self.__curl_cmd_send('name', 'name_on_mig_server')
        return cmd

    def send_status_files(self, files, result='send_status_status'):
        """Send .status"""

        # Missing files must raise an error status

        cmd = ''
        for name in files:
            name_on_mig_server = os.path.join(job_output_dir,
                                              self.job_dict['JOB_ID'], name)

            # NOTE: for security we do not invoke shell here
            cmd += 'subprocess.call("%s")\n' % \
                   self.__curl_cmd_send(name, name_on_mig_server)
        return cmd

    def request_interactive(self):
        """Request interactive job"""

        return self.__curl_cmd_request_interactive()

    def save_status(self, result='ret'):
        """Save exit code"""

        return '''
%s = status >> 8
''' % result

    def total_status(self, variables, result='total_status'):
        """Logically 'and' variables and save result"""

        cmd = '''
%s = True
''' % result
        for var in variables:
            cmd += 'if %s:\n' % var
            cmd += '  %s = False\n' % result
        return cmd

    def print_on_error(
        self,
        result='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
    ):
        """Print msg unless last command exitted with successcode"""

        cmd = 'if ' + result + ' != ' + successcode + ':\n'
        cmd += '\tprint "WARNING: ' + msg + "\(\" + " + result + " + \"\)\"\n"
        cmd += '\n'
        return cmd

    def log_on_error(
        self,
        result='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
    ):
        """Log msg unless result contains success code"""
        cmd = 'if ' + result + ' != ' + successcode + ':\n'
        cmd += self.log_status(msg, result)
        cmd += '\n'
        return cmd

    def exit_on_error(
        self,
        result='ret',
        successcode='0',
        exitcode='ret',
    ):
        """exit with exitcode unless last command exitted with
        success code"""

        cmd = 'if ' + result + ' != ' + successcode + ':\n'
        cmd += '\tsys.exit(' + exitcode + ')\n'
        cmd += '\n'
        return cmd

    def exit_script(self, exitcode='0', name=''):
        """Please note that frontend_script relies on the
        '### END OF SCRIPT ###' string to check that getinputfiles
        script is fully received. Thus changes here should be
        reflected in frontend_script!
        """

        return 'print "' + name + ' script end reached ' + \
               self.job_dict['JOB_ID'] + '" \nsys.exit(' + exitcode + ')\n' + \
               '### END OF SCRIPT ###\n'

    def clean_up(self):
        """Clean up"""

        # cd .. ; rm -rf --one-file-system "job id"

        # TODO: really skip mount points and contents!!!

        cmd = 'os.chdir("..")\n'
        cmd += 'top = "' + self.job_dict['JOB_ID'] + '"\n'
        cmd += 'for root, dirs, files in os.walk(top, topdown=False):\n'
        cmd += '  for name in files:\n'
        cmd += '     os.remove(join(root, name))\n'
        cmd += '  for name in dirs:\n'
        cmd += '     os.rmdir(join(root, name))\n'
        cmd += 'os.rmdir(top)'
        return cmd
