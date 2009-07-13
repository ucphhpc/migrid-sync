#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genjobscriptpython - [insert a few words of module description on this line]
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

"""Python job script generator and functions"""

import os

from shared.job import output_dir

def curl_cmd_send(resource_filename, mig_server_filename,
                  migserver_https_url_arg):
    """Upload files"""

    return "curl --fail --silent --insecure --upload-file '"\
         + resource_filename + "' -X SIDPUT '" + migserver_https_url_arg\
         + '/sid_redirect/' + job_dict['MIGSESSIONID'] + '/'\
         + mig_server_filename + "'"


def curl_cmd_get(mig_server_filename, resource_filename,
                 migserver_https_url_arg):
    """Download files"""

    dest_path = os.path.split(resource_filename)[0]
    cmd = ''
    if dest_path != '':
        cmd += "mkdir -p '%s' && \\" % dest_path
        cmd += '\n'
    cmd += "curl --fail --silent --insecure -o '" + resource_filename\
         + "' '" + migserver_https_url_arg + '/sid_redirect/'\
         + job_dict['MIGSESSIONID'] + '/' + mig_server_filename + "'"
    return cmd


def curl_cmd_get_special(file_extension, resource_filename,
                         migserver_https_url_arg):
    """Download internal job files"""

    dest_path = os.path.split(resource_filename)[0]
    cmd = ''
    if dest_path != '':
        cmd += 'mkdir -p %s && \\' % dest_path
        cmd += '\n'
    cmd += "curl --fail --silent --insecure -o '" + resource_filename\
         + "' '" + migserver_https_url_arg + '/sid_redirect/'\
         + job_dict['MIGSESSIONID'] + file_extension + "'"
    return cmd


def curl_cmd_request_interactive(migserver_https_url_arg):
    """CGI request for interactive job"""

    int_command = "curl --fail --silent --insecure '"\
         + migserver_https_url_arg\
         + '/cgi-sid/requestinteractivejob.py?sessionid='\
         + job_dict['MIGSESSIONID'] + '&jobid=' + job_dict['JOB_ID']\
         + '&exe=' + exe + '&unique_resource_name='\
         + resource_conf['RESOURCE_ID'] + '&localjobname='\
         + localjobname + "'\n"
    int_command += '# wait until interactive command is done\n'
    int_command += 'while [ 1 ]; do\n'
    int_command += '   if [ -f .interactivejobfinished ]; then\n'
    int_command += '        break\n'
    int_command += '   else\n'
    int_command += '        sleep 3\n'
    int_command += '   fi\n'
    int_command += 'done\n'
    return int_command


class GenJobScriptPython:

    """Python job script generator"""

    def __init__(
        self,
        job_dictionary,
        resource_config,
        exe_unit,
        migserver_https_url,
        localjobnam,
        filename_without_ext,
        ):

        # TODO: this is damn ugly!

        global job_dict
        job_dict = job_dictionary
        global resource_conf
        resource_conf = resource_config
        global exe
        exe = exe_unit
        global migserver_https_url_arg
        migserver_https_url_arg = migserver_https_url
        global filename_without_extension
        filename_without_extension = filename_without_ext
        global localjobname
        localjobname = localjobnam
        global io_log
        io_log = '%s.io-status' % job_dict['JOB_ID']

        print """Python resource scripts are *not* fully supported!
Please use Sh as SCRIPTLANGUAGE on your resources if this fails!"""

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

import os
import stat
from os.path import join, getsize
'''

    def print_start(self, name='job'):
        """print 'starting new job'"""

        return "print 'Starting new %s with JOB_ID: %s'\n" % (name,
                job_dict['JOB_ID'])

    def create_files(self, files):
        """Create supplied files"""

        cmd = ''
        for path in files:

            # Create/truncate files by opening in 'w' mode

            cmd += "open('%s', 'w').close()\n" % path
        return cmd

    def init_status(self):
        """Initialize status file"""

        return """status_fd = open('%s.status', 'r+')
status_fd.write('Internal job setup failed!
')
status_fd.close()
"""\
             % job_dict['JOB_ID']

    def init_io_log(self):
        """Open IO status log"""

        return "io_log = open(%s, 'w')" % io_log

    def log_io_status(self, io_type, result='ret'):
        """Write to IO status log"""

        return '''io_log.write("%s " + %s)
io_log.flush()'''\
             % (io_type, result)

    def create_job_directory(self):
        """if directory with name JOB_ID doesnt exists, then create.
        cd into it."""

        cmd = 'if os.path.isdir("' + job_dict['JOB_ID'] + '")==False:\n'
        cmd += '   os.mkdir("' + job_dict['JOB_ID'] + '")\n'
        return cmd

    def cd_to_job_directory(self):
        """Enter execution directory"""

        return 'os.chdir("' + job_dict['JOB_ID'] + '")'

    def get_input_files(self, result='get_input_status'):
        """get the inputfiles from the grid server"""

        cmd = ''

        for infile in job_dict['INPUTFILES']:
            cmd += 'os.popen("' + curl_cmd_get(infile) + '", "r")'
        return cmd

    def get_special_input_files(self, result='get_special_status'):
        """get the internal job files from the grid server"""

        cmd = ''
        cmd += curl_cmd_get_special('.job', localjobname + '.job',
                                    migserver_https_url_arg) + ' && \\'\
             + '\n'
        cmd += curl_cmd_get_special('.sendoutputfiles', localjobname
                                     + '.sendoutputfiles',
                                    migserver_https_url_arg) + '\n'
        return cmd

    def get_executables(self, result='get_executables_status'):
        """Get EXECUTABLES (inputfiles and +x)"""

        cmd = ''
        for executables in job_dict['EXECUTABLES']:
            cmd += 'os.popen("' + curl_cmd_get(executables)\
                 + '", "r")\n'
        return cmd

    def chmod_executables(self, result='chmod_status'):
        """Make sure EXECUTABLES are actually executable"""

        cmd = ''
        for executables in job_dict['EXECUTABLES']:
            cmd += 'os.chmod("' + executables + '", stat.S_IRWXU)'
        return cmd

    def set_environments(self, result='env_result'):
        """Set environments"""

        cmd = ''

        for env in job_dict['ENVIRONMENT']:
            key_and_value = env.split('=', 1)
            cmd += 'os.putenv("' + key_and_value[0] + '","'\
                 + key_and_value[1] + '")\n'

        return cmd

    def set_runtime_environments(self, resource_runtimeenvironment,
                                 result='re_result'):
        """Set Runtimeenvironments"""

        cmd = ''

        # loop the runtimeenvs that the job require

        for env in job_dict['RUNTIMEENVIRONMENT']:

            # set the envs as specified in the resources config file

            for res_env in resource_runtimeenvironment:

                # check if this is the right env in resource config

                if env == res_env[0]:

                    # this is the right list of envs. Loop the entire list and set all the envs

                    for single_env in res_env[1]:
                        key_and_value = single_env.split('=', 1)
                        cmd += 'os.putenv("' + key_and_value[0] + '","'\
                             + key_and_value[1] + '")\n'

        return cmd

    def execute(self, pretext, posttext):
        """Command execution"""

        stdout = job_dict['JOB_ID'] + '.stdout'
        stderr = job_dict['JOB_ID'] + '.stderr'
        status = job_dict['JOB_ID'] + '.status'
        cmd = ''

        cmd += 'status_handle = open("' + status + '","w")\n'

        for exe in job_dict['EXECUTE']:
            exe = exe.replace('"', '\\"')
            cmd += 'print "' + pretext + exe + '"\n'

            cmd += 'if "' + exe + '".find(" >> ") != -1:\n'
            cmd += '   filehandle = os.popen("' + exe + ' 2>> ' + stdout\
                 + '", "r")\n'
            cmd += 'else:\n'
            cmd += '   filehandle = os.popen("' + exe + ' >> ' + stdout\
                 + ' 2>> ' + stderr + '", "r")\n'
            cmd += 'status = filehandle.close()\n'
            cmd += 'if status == None:\n'
            cmd += '  status = "0"\n'
            cmd += 'else:\n'
            cmd += '  status = str(status)\n'
            cmd += 'status_handle.write("' + exe\
                 + ' " + str(status) + "\\n")\n'
            cmd += 'print "' + posttext + '" + str(status)\n'

        cmd += 'status_handle.close()\n'

        return cmd

    def output_files_missing(self, result='missing_counter'):
        """Check availability of outputfiles:
        Return number of missing files.
        """

        cmd = '%s = 0\n' % result
        for outputfile in job_dict['OUTPUTFILES']:
            cmd += 'if not os.path.isfile("' + outputfile + '":\n'
            cmd += '  %s += 1\n' % result
        return cmd

    def send_output_files(self, result='send_output_status'):
        """Send outputfiles"""

        # call Kristens code and get outputfiles destination

        cmd = ''

        for outputfile in job_dict['OUTPUTFILES']:
            cmd += 'if (os.path.isfile("' + outputfile\
                 + '") and os.path.getsize("' + outputfile\
                 + '") > 0):\n'
            cmd += '  os.popen("' + curl_cmd_send(outputfile) + '")\n'
        return cmd

    def send_io_files(self, files, result='send_io_status'):
        """Send .io-status, .stderr, .stdout"""

        # Existing files must be transferred with status 0, while
        # non-existing files shouldn't lead to error.

        cmd = ''
        for name in files:
            name_on_mig_server = os.path.join(output_dir, job_dict['JOB_ID'],
                                              name)
            cmd += 'if (os.path.isfile("' + name\
                 + '") and os.path.getsize("' + name + '") > 0):\n'

            # cmd += "  os.popen(\"" + curl_cmd_send(name) + "\")\n"

            cmd += '  os.popen("' + curl_cmd_send(name,
                    name_on_mig_server, migserver_https_url_arg)\
                 + '")\n'
        return cmd

    def send_status_files(self, files, result='send_status_status'):
        """Send .status"""

        # Missing files must raise an error status

        cmd = ''
        for name in files:
            name_on_mig_server = os.path.join(output_dir, job_dict['JOB_ID'],
                                              name)

            # cmd += "os.popen(\"%s\")\n" % curl_cmd_send(name)

            cmd += 'os.popen("' + curl_cmd_send(name,
                    name_on_mig_server, migserver_https_url_arg)\
                 + '")\n'
        return cmd

    def request_interactive(self):
        """Request interactive job"""

        # return curl_cmd_request_interactive(migserver_https_url_arg, job_dict, resource_conf, exe)

        return curl_cmd_request_interactive(migserver_https_url_arg)

    def save_status(self, variable='ret'):
        """Save exit code"""

        return '''
%s = status >> 8
''' % variable

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
        variable='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
        ):
        """Print msg unless last command exitted with successcode"""

        cmd = 'if ' + variable + ' != ' + successcode + ':\n'
        cmd += '\tprint "WARNING: ' + msg + "\(\" + " + variable\
             + " + \"\)\"\n"
        cmd += '\n'
        return cmd

    def exit_on_error(
        self,
        variable='ret',
        successcode='0',
        exitcode='ret',
        ):
        """exit with exitcode unless last command exitted with
        success code"""

        cmd = 'if ' + variable + ' != ' + successcode + ':\n'
        cmd += '\tsys.exit(' + exitcode + ')\n'
        cmd += '\n'
        return cmd

    def exit_script(self, exitcode='0', name=''):
        """Please note that frontend_script relies on the
        '### END OF SCRIPT ###' string to check that getinputfiles
        script is fully received. Thus changes here should be
        reflected in frontend_script!
        """

        return 'print "' + name + ' script end reached '\
             + job_dict['JOB_ID'] + '" \nsys.exit(' + exitcode + ')\n'\
             + '### END OF SCRIPT ###\n'

    def clean_up(self):
        """Clean up"""

        # cd .., rm -rf "job id"

        cmd = 'os.chdir("..")\n'
        cmd += 'top = "' + job_dict['JOB_ID'] + '"\n'
        cmd += 'for root, dirs, files in os.walk(top, topdown=False):\n'
        cmd += '  for name in files:\n'
        cmd += '     os.remove(join(root, name))\n'
        cmd += '  for name in dirs:\n'
        cmd += '     os.rmdir(join(root, name))\n'
        cmd += 'os.rmdir(top)'
        return cmd


