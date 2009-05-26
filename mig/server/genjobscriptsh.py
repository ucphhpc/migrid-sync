#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genjobscriptsh - [insert a few words of module description on this line]
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

"""Bourne shell job script generator and functions"""

import os


def curl_cmd_send(resource_filename, mig_server_filename,
                  migserver_https_url_arg):
    """Upload files"""

    upload_bw_limit = ''
    if resource_conf.has_key('MAXUPLOADBANDWIDTH')\
         and resource_conf['MAXUPLOADBANDWIDTH'] > 0:
        upload_bw_limit = '--limit-rate %ik'\
             % resource_conf['MAXUPLOADBANDWIDTH']

    if mig_server_filename.find('://') != -1:

        # Pass URLs for external sources directly to curl

        dst_url = mig_server_filename
        sid_put_marker = ''
    else:

        # Relative paths are uploaded to the corresponding session on the server

        dst_url = migserver_https_url_arg + '/sid_redirect/'\
             + job_dict['MIGSESSIONID'] + '/' + mig_server_filename

        # MiG server needs to know that this PUT uses a session ID

        sid_put_marker = '-X SIDPUT'

    return 'curl --connect-timeout 30 --max-time 3600 '\
         + upload_bw_limit + ' --fail --silent --insecure '\
         + " --upload-file '" + resource_filename + "' "\
         + sid_put_marker + " '" + dst_url + "'"


def curl_cmd_get(mig_server_filename, resource_filename,
                 migserver_https_url_arg):
    """Download files"""

    download_bw_limit = ''
    if resource_conf.has_key('MAXDOWNLOADBANDWIDTH')\
         and resource_conf['MAXDOWNLOADBANDWIDTH'] > 0:
        download_bw_limit = '--limit-rate %ik'\
             % resource_conf['MAXDOWNLOADBANDWIDTH']

    dest_path = os.path.dirname(resource_filename)
    cmd = ''
    if dest_path:
        cmd += "mkdir -p '%s' && \\" % dest_path
        cmd += '\n'
    if mig_server_filename.find('://') != -1:

        # Pass URLs for external sources directly to curl

        src_url = mig_server_filename
    else:

        # Relative paths are downloaded from the corresponding session on the server

        src_url = migserver_https_url_arg + '/sid_redirect/'\
             + job_dict['MIGSESSIONID'] + '/' + mig_server_filename

    cmd += 'curl --connect-timeout 30 --max-time 3600 '\
         + download_bw_limit + ' --fail --silent --insecure ' + " -o '"\
         + resource_filename + "' '" + src_url + "'"
    return cmd


def curl_cmd_get_special(file_extension, resource_filename,
                         migserver_https_url_arg):
    """Download internal job files"""

    download_bw_limit = ''
    if resource_conf.has_key('MAXDOWNLOADBANDWIDTH')\
         and resource_conf['MAXDOWNLOADBANDWIDTH'] > 0:
        download_bw_limit = '--limit-rate %ik'\
             % resource_conf['MAXDOWNLOADBANDWIDTH']

    dest_path = os.path.dirname(resource_filename)
    cmd = ''
    if dest_path:
        cmd += "mkdir -p '%s' && \\" % dest_path
        cmd += '\n'
    cmd += 'curl --connect-timeout 30 --max-time 3600 '\
         + download_bw_limit + ' --fail --silent --insecure ' + " -o '"\
         + resource_filename + "' '" + migserver_https_url_arg\
         + '/sid_redirect/' + job_dict['MIGSESSIONID'] + file_extension\
         + "'"
    return cmd


def curl_cmd_request_interactive(migserver_https_url_arg):
    """CGI request for interactive job"""

    int_command = \
        "curl --connect-timeout 30 --max-time 3600 --fail --silent --insecure '"\
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


class GenJobScriptSh:

    """Bourne shell script generator"""

    def __init__(
        self,
        job_dictionary,
        resource_config,
        exe_unit,
        migserver_https_url,
        localjobnam,
        filename_without_ext,
        ):

        # TODO: this is damn ugly! why not use self.X instead of global?

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

    def comment(self, string):
        """Insert comment"""

        return '# %s\n' % string

    def script_init(self):
        """initialize script"""

        requested = {'CPUTIME': job_dict['CPUTIME']}
        requested['NODECOUNT'] = job_dict.get('NODECOUNT', 1)
        requested['CPUCOUNT'] = job_dict.get('CPUCOUNT', 1)
        requested['MEMORY'] = job_dict.get('MEMORY', 1)
        requested['DISK'] = job_dict.get('DISK', 1)
        requested['JOBID'] = job_dict.get('JOB_ID', 'UNKNOWN')
        requested['ADMINEMAIL'] = ''
        if resource_conf.has_key('ADMINEMAIL'):

            # Format to mail flag is normally user[@host][,user[@host],...]

            requested['ADMINEMAIL'] = resource_conf['ADMINEMAIL'
                    ].replace(' ', ',')

        # Use bash explicitly here because /bin/sh may not support echo -n , which
        # breaks e.g. $localjobname.inputfiles generation

        return '''#!/bin/bash
#
# --- BEGIN_HEADER ---
#
# ??? - one of the shell scripts running on resources
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
### Strict fill LRMS resources need actual resource requests for submit - insert
### them as MiG clauses here and extract and set environment for submit to use.
#MIG_JOBNODES %(NODECOUNT)s
#MIG_JOBNODECOUNT %(NODECOUNT)s
#MIG_JOBCPUTIME %(CPUTIME)s
#MIG_JOBCPUCOUNT %(CPUCOUNT)s
#MIG_JOBMEMORY %(MEMORY)s
#MIG_JOBDISK %(DISK)s
#MIG_JOBID %(JOBID)s
#MIG_ADMINEMAIL %(ADMINEMAIL)s
### End of additional data
#
'''\
             % requested

    def print_start(self, name='job'):
        """print 'starting new name script ...'"""

        return "echo 'Starting new %s script with JOB_ID: %s'\n"\
             % (name, job_dict['JOB_ID'])

    def create_files(self, files):
        """Create supplied files"""

        cmd = ''
        for path in files:
            cmd += "touch '%s'\n" % path
        return cmd

    def init_status(self):
        """Initialize status file"""

        return "echo 'Internal job setup failed!' > %s.status\n"\
             % job_dict['JOB_ID']

    def init_io_log(self):
        """Open IO status log"""

        return 'touch %s\n' % io_log

    def log_io_status(self, io_type, result='ret'):
        """Write to IO status log"""

        return 'echo "%s $%s" >> %s\n' % (io_type, result, io_log)

    def create_job_directory(self):
        """if directory with name JOB_ID doesnt exists, then create."""

        return "[ ! -d '" + resource_conf['RESOURCEHOME']\
             + job_dict['JOB_ID'] + "' ] && mkdir '"\
             + resource_conf['RESOURCEHOME'] + job_dict['JOB_ID']\
             + "'\n"

    def cd_to_job_directory(self):
        """Enter execution directory"""

        return 'cd ' + resource_conf['RESOURCEHOME'] + job_dict['JOB_ID'
                ] + '\n'

    def get_input_files(self, result='get_input_status'):
        """Get the input files from the grid server
        Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        for infile in job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = infile.split()
            mig_server_filename = str(parts[0])
            try:
                resource_filename = str(parts[1])
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            cmd += '%s\n' % curl_cmd_get(mig_server_filename,
                    resource_filename, migserver_https_url_arg)
            cmd += 'last_get_status=$?\n'
            cmd += 'if [ $last_get_status -ne 0 ]; then\n'
            cmd += '    %s=$last_get_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result

        return cmd

    def get_special_input_files(self, result='get_special_status'):
        """get the internal job files from the grid server"""

        cmd = ''
        cmd += '%s && \\' % curl_cmd_get_special('.job', localjobname
                 + '.job', migserver_https_url_arg)
        cmd += '''
%s
''' % curl_cmd_get_special('.sendupdatefiles',
                localjobname + '.sendupdatefiles',
                migserver_https_url_arg)
        cmd += '''
%s
''' % curl_cmd_get_special('.sendoutputfiles',
                localjobname + '.sendoutputfiles',
                migserver_https_url_arg)
        cmd += '%s=$?\n' % result
        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def get_executables(self, result='get_executables_status'):
        """Get the job executables from the grid server.
        Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        for executables in job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = executables.split()
            mig_server_filename = str(parts[0])
            try:
                resource_filename = str(parts[1])
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            cmd += '%s\n' % curl_cmd_get(mig_server_filename,
                    resource_filename, migserver_https_url_arg)
            cmd += 'last_get_status=$?\n'
            cmd += 'if [ $last_get_status -ne 0 ]; then\n'
            cmd += '    %s=$last_get_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result

        return cmd

    def generate_input_filelist(self, result='generate_input_filelist'):
        """Generate filelist (user/system) of which files 
        should be transfered from FE to EXE before job execution."""

        cmd = \
            '# Create files used by master_node_script (input/executables/systemfiles)\n'
        cmd += '%s=0\n' % result
        fe_move_dict = {}

        for infile in job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = infile.split()
            mig_server_filename = str(parts[0])
            try:
                resource_filename = str(parts[1])
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            fe_move = resource_filename.split('/', 1)[0]

            if not fe_move_dict.has_key(fe_move):
                fe_move_dict[fe_move] = True

        for executables in job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = executables.split()
            mig_server_filename = str(parts[0])
            try:
                resource_filename = str(parts[1])
            except:
                resource_filename = mig_server_filename

            # Source may be external in which case implicit destination needs attention

            if resource_filename.find('://') != -1:

                # Strip any protocol prefixes in destination for external sources

                resource_filename = resource_filename.split('://', 1)[1]

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            fe_move = resource_filename.split('/', 1)[0]

            if not fe_move_dict.has_key(fe_move):
                fe_move_dict[fe_move] = True

        cmd += 'echo -n "" > %s.inputfiles\\\n' % localjobname
        for file in fe_move_dict.keys():
            cmd += \
                '&& if [ -e %s ]; then echo -n "%s " >> %s.inputfiles; fi\\\n'\
                 % (file, file, localjobname)

        # Systemfiles

        cmd += '&& echo -n "%s.user.outputfiles " >> %s.inputfiles\\\n'\
             % (localjobname, localjobname)
        cmd += \
            '&& echo -n "%s.system.outputfiles " >> %s.inputfiles\\\n'\
             % (localjobname, localjobname)
        cmd += '&& echo -n "%s.job" >> %s.inputfiles\n'\
             % (localjobname, localjobname)
        cmd += '%s=$?\n' % result
        return cmd

    def generate_output_filelists(self, real_job,
                                  result='generate_output_filelists'):
        """Generate filelists (user/system) of which files
        should be transfered from EXE to FE upon job finish."""

        exe_move_dict = {}
        cmd = \
            '# Create files used by master_node_script to determine which output files to transfer to FE\n'
        cmd += '%s=0\n' % result

        cmd += 'echo -n "" > %s.user.outputfiles\\\n' % localjobname
        for outputfile in job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename mig_server_filename"

            parts = outputfile.split()
            resource_filename = str(parts[0])

            # We don't need mig_server_filename here so just skip mangling

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            exe_move = resource_filename.split('/', 1)[0]

            if not exe_move_dict.has_key(exe_move):
                exe_move_dict[exe_move] = True

        for file in exe_move_dict.keys():
            cmd += '&& echo -n "%s " >> %s.user.outputfiles\\\n'\
                 % (file, localjobname)

        cmd += '&& echo -n "" > %s.system.outputfiles\\\n'\
             % localjobname

        # Sleep jobs only generate .status

        if real_job:
            cmd += \
                '&& echo -n "%s.stderr " >> %s.system.outputfiles\\\n'\
                 % (job_dict['JOB_ID'], localjobname)
            cmd += \
                '&& echo -n "%s.stdout " >> %s.system.outputfiles\\\n'\
                 % (job_dict['JOB_ID'], localjobname)

        cmd += '&& echo -n "%s.status" >> %s.system.outputfiles\n'\
             % (job_dict['JOB_ID'], localjobname)
        cmd += '%s=$?\n' % result
        return cmd

    def generate_iosessionid_file(self,
                                  result='generate_iosessionid_file'):
        """Generate file containing io-sessionid."""

        cmd = '# Create file used containing io-sessionid.\n'
        cmd += '%s=0\n' % result
        cmd += 'echo -n "%s" > %s.iosessionid\n'\
             % (job_dict['MIGIOSESSIONID'], localjobname)
        cmd += '%s=$?\n' % result
        return cmd

    def chmod_executables(self, result='chmod_status'):
        """Make sure EXECUTABLES are actually executable"""

        cmd = '%s=0\n' % result
        executables = []
        for line in job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = line.split()
            mig_server_filename = str(parts[0])
            try:
                resource_filename = str(parts[1])
            except:
                resource_filename = mig_server_filename
            executables.append(resource_filename)

        if executables:
            cmd += 'chmod +x %s\n' % ' '.join(executables)

        cmd += '%s=$?\n' % result
        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def set_environments(self, result='env_status'):
        """Set environments"""

        cmd = ''

        for env in job_dict['ENVIRONMENT']:
            if cmd:

                # combine all commands into one AND'ed command line to allow single
                # return value

                cmd += ' && \\' + '\n'
            (key, value) = env
            cmd += 'export ' + key + '=' + value

        cmd += '''
%s=$?
''' % result
        cmd += """# Now 'return' status is available in %s

""" % result

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

                (res_env_name, res_env_val) = res_env
                if env == res_env_name:

                    # this is the right list of envs. Loop the entire list and set all the envs

                    for single_env in res_env_val:
                        if cmd:

                            # combine all commands into one AND'ed command line to allow single
                            # return value

                            cmd += ' && \\' + '\n'
                        (key, value) = single_env
                        cmd += 'export ' + key + '=' + value

        cmd += '''
%s=$?
''' % result
        cmd += """# Now 'return' status is available in %s

""" % result

        return cmd

    def execute(self, pretext, posttext):
        """Command execution:
        We want to catch each exit code without interfering with
        the flow. Thus we immediately catch the exit code and do
        the required accounting before finally 'restoring' the
        saved exit code.
        Furthermore we wan't to save any uncaught output without
        preventing ordinary IO redirection in jobs.
        Thus we wrap all commands from EXECUTE in a single set of curly
        braces to allow execution in the current shell environment
        while retaining the ability to redirect uncaught IO to
        JOB_ID.stdout and JOB_ID.stderr
        """

        exe_dict = {'job_id': job_dict['JOB_ID'], 'job_log': 'joblog'}
        cmd = ''

        # Truncate setup error message in .status file now that
        # we're past job init

        cmd += "echo -n '' > %(job_id)s.status\n" % exe_dict
        cmd += '''__MiG_LAST_RET=0
{
'''

        for exe in job_dict['EXECUTE']:
            exe_dict['job_id'] = job_dict['JOB_ID']
            exe_dict['exe'] = exe

            # Make sure any apostrophes in EXECUTE do not interfere
            # with our own

            exe = exe.replace("'", "\\'")

            # Please note that the 'EXECUTING: sleep' string is used to detect empty jobs
            # in resource scripts: Please propagate any changes!

            cmd += \
                """
    echo 'EXECUTING: %(exe)s' >> %(job_log)s
    echo -n '--Exit code: ' >> %(job_log)s
    echo -n '%(exe)s ' >> %(job_id)s.status
    (exit $__MiG_LAST_RET)
    %(exe)s
    __MiG_LAST_RET=$?
    echo $__MiG_LAST_RET >> %(job_id)s.status
    echo $__MiG_LAST_RET >> %(job_log)s
"""\
                 % exe_dict

        # Finally add the closing curly brace with IO redirection

        cmd += '''
} 1> %(job_id)s.stdout 2> %(job_id)s.stderr
'''\
             % exe_dict

        return cmd

    def output_files_missing(self, result='missing_counter'):
        """Check availability of outputfiles:
        Return number of missing files.
        """

        cmd = '%s=0\n' % result
        for outputfile in job_dict['OUTPUTFILES']:

            # "filename" or "mig_server_filename resource_filename"

            parts = outputfile.split()
            resource_filename = str(parts[0])
            try:
                mig_server_filename = str(parts[1])
            except:
                mig_server_filename = resource_filename

            cmd += '[ -e "%s" ] || %s=$((%s+1))\n'\
                 % (resource_filename, result, result)

        cmd += """# Now 'return' status is available in %s

""" % result

        return cmd

    def send_output_files(self, result='send_output_status'):
        """Send outputfiles:
        Existing files must be transferred with status 0, while
        non-existing files shouldn't lead to error.
        We can't expect users to only specify existing files!
        Only react to curl transfer errors, not MiG put errors
        since we can't handle the latter consistently anyway.
        """

        cmd = '%s=0\n' % result
        for outputfile in job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename mig_server_filename"

            parts = outputfile.split()
            resource_filename = str(parts[0])
            try:
                mig_server_filename = str(parts[1])
            except:
                mig_server_filename = resource_filename

            # External destinations will always be explicit so no
            # need to mangle protocol prefix here as in get inputfiles

            # Always strip leading slashes to avoid absolute paths

            mig_server_filename = mig_server_filename.lstrip('/')

            cmd += '[ ! -e "%s" ] || ' % resource_filename
            cmd += '%s\n' % curl_cmd_send(resource_filename,
                    mig_server_filename, migserver_https_url_arg)
            cmd += 'last_send_status=$?\n'
            cmd += 'if [ $last_send_status -ne 0 ]; then\n'
            cmd += '    %s=$last_send_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def send_io_files(self, files, result='send_io_status'):
        """Send IO files:
        Existing files must be transferred with status 0, while
        non-existing files shouldn't lead to error.
        Only react to curl transfer errors, not MiG put errors
        since we can't handle the latter consistently anyway.
        """

        cmd = '%s=0\n' % result
        for name in files:
            name_on_mig_server = 'job_output/' + job_dict['JOB_ID']\
                 + '/' + name
            cmd += '[ ! -e "%s" ] || ' % name
            cmd += '%s\n' % curl_cmd_send(name, name_on_mig_server,
                    migserver_https_url_arg)
            cmd += 'last_send_status=$?\n'
            cmd += 'if [ $last_send_status -ne 0 ]; then\n'
            cmd += '    %s=$last_send_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def send_status_files(self, files, result='send_status_status'):
        """Send status files:
        All files must exist and be transferred with curl status 0
        in order to return success.
        Only react to curl transfer errors, not MiG put errors
        since we can't handle the latter consistently anyway.
        """

        cmd = '%s=0\n' % result
        for name in files:
            name_on_mig_server = 'job_output/' + job_dict['JOB_ID']\
                 + '/' + name
            cmd += '[ -e "%s" ] && ' % name
            cmd += '%s\n' % curl_cmd_send(name, name_on_mig_server,
                    migserver_https_url_arg)
            cmd += 'last_send_status=$?\n'
            cmd += 'if [ $last_send_status -ne 0 ]; then\n'
            cmd += '    %s=$last_send_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def request_interactive(self):
        """Request interactive job"""

        # return curl_cmd_request_interactive(migserver_https_url_arg,
        #                                    job_dict, resource_conf,
        #                                    exe)

        return curl_cmd_request_interactive(migserver_https_url_arg)

    def save_status(self, result='ret'):
        """Save exit code in supplied result"""

        return '''
%s=$?
''' % result

    def total_status(self, variables, result='total_status'):
        """Logically 'and' variables and save result"""

        cmd = '%s=0\n' % result
        for var in variables:
            cmd += '[ $%s -eq 0 ] || %s=1\n' % (var, result)
        return cmd

    def print_on_error(
        self,
        result='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
        ):
        """Print msg unless result contains success code"""

        cmd = 'if [ $' + result + ' -ne ' + successcode + ' ]; then\n'
        cmd += '\techo "WARNING: ' + msg + "\($" + result + "\)\"\n"
        cmd += 'fi\n'
        return cmd

    def exit_on_error(
        self,
        result='ret',
        successcode='0',
        exitcode='ret',
        ):
        """exit with $exitcode unless result contains success code"""

        cmd = 'if [ $' + result + ' -ne ' + successcode + ' ]; then\n'
        cmd += '\texit $' + exitcode + '\n'
        cmd += 'fi\n'
        return cmd

    def exit_script(self, exitcode='0', name='job'):
        """Please note that frontend_script relies on the
        '### END OF SCRIPT ###' string to check that getinputfiles
        script is fully received. Thus changes here should be
        reflected in frontend_script!
        """

        return 'echo "' + name + ' script end reached '\
             + job_dict['JOB_ID'] + '" \nexit ' + exitcode + '\n'\
             + '### END OF SCRIPT ###\n'

    def clean_up(self):
        """Clean up"""

        # cd .., rm -rf "job id"

        cmd = ''

        cmd += 'cd ..\n'
        cmd += 'rm -rf ' + job_dict['JOB_ID'] + '\n'
        return cmd


