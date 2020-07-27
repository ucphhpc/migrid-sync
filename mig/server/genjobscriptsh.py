#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# genjobscriptsh - helpers for sh jobs
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

from urllib import quote as urlquote
import os

from shared.defaults import job_output_dir, src_dst_sep


class GenJobScriptSh:

    """Bourne shell script generator"""

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
        self.status_log = '%s/%s.status' % (self.localjobdir, self.job_dict['JOB_ID']) 
        self.io_log = '%s.io-status' % (self.job_dict['JOB_ID'])
 

    def __curl_cmd_send(self, resource_filename, mig_server_filename, expand):
        """Upload files with optional shell expansion of file names. Live
        output requires variables in path to be expanded, ordinary job output
        must escape to support exotic characters.
        """

        upload_bw_limit = ''
        if 'MAXUPLOADBANDWIDTH' in self.resource_conf\
             and self.resource_conf['MAXUPLOADBANDWIDTH'] > 0:
            upload_bw_limit = '--limit-rate %ik'\
                 % self.resource_conf['MAXUPLOADBANDWIDTH']

        if mig_server_filename.find('://') != -1:

            # Pass URLs for external sources directly to curl

            dst_url = mig_server_filename
            sid_put_marker = ''
        else:

            # Relative paths are uploaded to the corresponding session on the server

            dst_url = self.https_sid_url_arg + '/sid_redirect/' + \
                      self.job_dict['SESSIONID'] + '/'
            # Don't encode variables to be expanded
            if expand:
                dst_url += mig_server_filename
            else:
                dst_url += urlquote(mig_server_filename)

            # MiG server needs to know that this PUT uses a session ID

            sid_put_marker = '-X SIDPUT'

        cmd = 'curl --location --connect-timeout 30 --max-time 3600 ' + \
              upload_bw_limit + ' --fail --silent --insecure ' + \
              sid_put_marker + ' --upload-file '

        # Single or double quotes depending on shell expand option

        if expand:
            cmd += '"' + resource_filename + '" "' + dst_url + '"'
        else:
            cmd += "'" + resource_filename + "' '" + dst_url + "'"
        return cmd


    def __curl_cmd_send_mqueue(self, resource_filename, queue):
        """Send message to mqueue"""

        upload_bw_limit = ''
        if 'MAXUPLOADBANDWIDTH' in self.resource_conf\
             and self.resource_conf['MAXUPLOADBANDWIDTH'] > 0:
            upload_bw_limit = '--limit-rate %ik'\
              % self.resource_conf['MAXUPLOADBANDWIDTH']

        return 'curl --location --connect-timeout 30 --max-time 3600 '\
            + upload_bw_limit + ' --fail --silent --insecure '\
            + '-F "action=send" -F "iosessionid=' + self.job_dict['SESSIONID']\
            + '" -F "queue=' + queue + '" -F "msg=<' + resource_filename\
            + '" -F "output_format=txt" ' + self.https_sid_url_arg\
            + '/cgi-sid/mqueue.py'


    def __curl_cmd_get(self, mig_server_filename, resource_filename, expand):
        """Download files with optional shell expansion of file names. Live
        input requires variables in path to be expanded, ordinary job input
        must escape to support exotic characters.
        """
        
        download_bw_limit = ''
        if 'MAXDOWNLOADBANDWIDTH' in self.resource_conf\
             and self.resource_conf['MAXDOWNLOADBANDWIDTH'] > 0:
            download_bw_limit = '--limit-rate %ik'\
                 % self.resource_conf['MAXDOWNLOADBANDWIDTH']

        cmd = ''
        if mig_server_filename.find('://') != -1:

            # Pass URLs for external sources directly to curl

            src_url = mig_server_filename
        else:

            # Relative paths are downloaded from the corresponding session on the server

            src_url = self.https_sid_url_arg + '/sid_redirect/' + \
                      self.job_dict['SESSIONID'] + '/'
            # Don't encode variables to be expanded
            if expand:
                src_url += mig_server_filename
            else:
                src_url += urlquote(mig_server_filename)

        cmd = 'curl --location --connect-timeout 30 --max-time 3600 ' + \
              download_bw_limit + ' --fail --silent --insecure --create-dirs '

        # Single or double quotes depending on shell expand option

        if expand:
            cmd += '-o "' + resource_filename + '" "' + src_url + '"'
        else:
            cmd += "-o '" + resource_filename + "' '" + src_url + "'"
        return cmd


    def __curl_cmd_get_special(self, file_extension, resource_filename):
        """Download internal job files"""

        download_bw_limit = ''
        if 'MAXDOWNLOADBANDWIDTH' in self.resource_conf\
            and self.resource_conf['MAXDOWNLOADBANDWIDTH'] > 0:
            download_bw_limit = '--limit-rate %ik'\
                 % self.resource_conf['MAXDOWNLOADBANDWIDTH']

        cmd = ''
        cmd += 'curl --location --connect-timeout 30 --max-time 3600 '\
            + download_bw_limit + ' --fail --silent --insecure --create-dirs '\
            + "-o '" + resource_filename + "' '" + self.https_sid_url_arg\
            + '/sid_redirect/' + self.job_dict['SESSIONID'] + file_extension + "'"
        return cmd


    def __curl_cmd_get_mqueue(self, queue, resource_filename):
        """Receive message from mqueue"""

        download_bw_limit = ''
        if 'MAXDOWNLOADBANDWIDTH' in self.resource_conf\
            and self.resource_conf['MAXDOWNLOADBANDWIDTH'] > 0:
            download_bw_limit = '--limit-rate %ik'\
                 % self.resource_conf['MAXDOWNLOADBANDWIDTH']

        cmd = ''
        cmd += 'curl --location --connect-timeout 30 --max-time 3600 '\
            + download_bw_limit + ' --fail --silent --insecure --create-dirs '\
            + '-o "' + resource_filename + '" -F "action=receive" '\
            + '-F "iosessionid=' + self.job_dict['SESSIONID'] + '" -F "queue='\
            + queue + '" -F "output_format=file" ' + self.https_sid_url_arg\
            + '/cgi-sid/mqueue.py'
        return cmd


    def __curl_cmd_request_interactive(self):
        """CGI request for interactive job"""

        unique_resource_name = "%(HOSTURL)s.%(HOSTIDENTIFIER)s" % self.resource_conf
        int_command = \
            "curl --location --connect-timeout 30 --max-time 3600 --fail --silent --insecure '"\
                + self.https_sid_url_arg\
                + '/cgi-sid/requestinteractivejob.py?sessionid='\
                + self.job_dict['SESSIONID'] + '&jobid=' + self.job_dict['JOB_ID']\
                + '&exe=' + self.exe + '&unique_resource_name='\
                + unique_resource_name + '&localjobname=' + self.localjobname\
                + "'\n"
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

        return '# %s\n' % string

    def script_init(self):
        """initialize script"""

        requested = {'CPUTIME': self.job_dict['CPUTIME']}
        requested['NODECOUNT'] = self.job_dict.get('NODECOUNT', 1)
        requested['CPUCOUNT'] = self.job_dict.get('CPUCOUNT', 1)
        requested['MEMORY'] = self.job_dict.get('MEMORY', 1)
        requested['DISK'] = self.job_dict.get('DISK', 1)
        requested['JOBID'] = self.job_dict.get('JOB_ID', 'UNKNOWN')
        requested['ADMINEMAIL'] = ''
        if 'ADMINEMAIL' in self.resource_conf:

            # Format to mail flag is normally user[@host][,user[@host],...]

            requested['ADMINEMAIL'] = self.resource_conf['ADMINEMAIL'
                    ].replace(' ', ',')

        # Use bash explicitly here because /bin/sh may not support echo -n , which
        # breaks e.g. $localjobname.inputfiles generation

        return '''#!/bin/bash
#
# --- BEGIN_HEADER ---
#
# ??? - one of the shell scripts running on resources
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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
             % (name, self.job_dict['JOB_ID'])

    def create_files(self, files):
        """Create supplied files"""

        cmd = ''
        for path in files:
            cmd += "touch '%s'\n" % path
        return cmd

    def init_status(self):
        """Initialize status file"""

        return 'touch %s\n' % self.status_log

    def log_status(self, status_type, result='ret'):
        """Write to status log"""

        return 'echo "%s $%s" >> %s\n' % (status_type, result, self.status_log)

    def init_io_log(self):
        """Open IO status log"""

        return 'touch %s\n' % self.io_log

    def log_io_status(self, io_type, result='ret'):
        """Write to IO status log"""

        return 'echo "%s $%s" >> %s\n' % (io_type, result, self.io_log)

    def create_job_directory(self):
        """if directory with name JOB_ID doesnt exists, then create."""

        return "[ ! -d '" + self.resource_conf['RESOURCEHOME']\
             + self.job_dict['JOB_ID'] + "' ] && mkdir '"\
             + self.resource_conf['RESOURCEHOME'] + self.job_dict['JOB_ID']\
             + "'\n"

    def cd_to_job_directory(self):
        """Enter execution directory"""

        return 'cd ' + self.resource_conf['RESOURCEHOME'] + self.job_dict['JOB_ID'
                ] + '\n'

    def get_input_files(self, result='get_input_status'):
        """Get the input files from the grid server
        Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        for infile in self.job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename%src_dst_sep)sresource_filename"

            parts = infile.split(src_dst_sep)
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

            cmd += '%s\n' % self.__curl_cmd_get(mig_server_filename,
                    resource_filename, False)
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
        cmd += '%s && \\' % self.__curl_cmd_get_special('.job', self.localjobname
                 + '.job')
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
        cmd += '%s=$?\n' % result
        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def get_executables(self, result='get_executables_status'):
        """Get the job executables from the grid server.
        Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        for executables in self.job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename%(src_dst_sep)sresource_filename"

            parts = executables.split(src_dst_sep)
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

            cmd += '%s\n' % self.__curl_cmd_get(mig_server_filename,
                    resource_filename, False)
            cmd += 'last_get_status=$?\n'
            cmd += 'if [ $last_get_status -ne 0 ]; then\n'
            cmd += '    %s=$last_get_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def get_io_files(self, result='get_io_status'):
        """Get live files from server during job execution"""

        cmd = '%s=0\n' % result
        cmd += '# First parameter is target: liveio or mqueue\n'
        cmd += 'target=$1\n'
        cmd += 'shift\n'
        cmd += '# All but last input args are sources and last is dest\n'
        cmd += 'i=0\n'
        cmd += 'last=$((${#@}-1))\n'
        cmd += 'for name in $@; do\n'
        cmd += '    if [ $i -lt $last ]; then\n'
        cmd += '        src[$i]=$name\n'
        cmd += '    else\n'
        cmd += '        dst=$name\n'
        cmd += '    fi\n'
        cmd += '    i=$((i+1))\n'
        cmd += 'done\n'
        cmd += 'for name in ${src[@]}; do\n'
        cmd += '    name_on_resource=$dst/`basename $name`\n'
        cmd += '    if [ "$target" = "mqueue" ]; then\n'
        cmd += '        %s\n' % self.__curl_cmd_get_mqueue('$name',
                                                           '$name_on_resource')
        cmd += '    else\n'
        cmd += '        %s\n' % self.__curl_cmd_get('$name',
                                                    '$name_on_resource', True)
        cmd += '    fi\n'
        cmd += '    last_get_status=$?\n'
        cmd += '    if [ $last_get_status -ne 0 ]; then\n'
        cmd += '        %s=$last_get_status\n' % result
        cmd += '    fi\n'
        cmd += 'done\n'

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

        for infile in self.job_dict['INPUTFILES']:

            # "filename" or "mig_server_filename%(src_dst_sep)sresource_filename"

            parts = infile.split(src_dst_sep)
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

            if fe_move not in fe_move_dict:
                fe_move_dict[fe_move] = True

        for executables in self.job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename%(src_dst_sep)sresource_filename"

            parts = executables.split(src_dst_sep)
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

            if fe_move not in fe_move_dict:
                fe_move_dict[fe_move] = True

        # Quote file names to protect against exotic characters
        
        cmd += 'echo -n "" > %s.inputfiles\\\n' % self.localjobname
        for file in fe_move_dict.keys():
            cmd += \
                "&& if [ -e '%s' ]; then echo -n '%s ' >> %s.inputfiles; fi\\\n"\
                 % (file, file, self.localjobname)

        # Systemfiles

        cmd += '&& echo -n "%s.user.outputfiles " >> %s.inputfiles\\\n'\
             % (self.localjobname, self.localjobname)
        cmd += \
            '&& echo -n "%s.system.outputfiles " >> %s.inputfiles\\\n'\
             % (self.localjobname, self.localjobname)
        cmd += '&& echo -n "%s.job" >> %s.inputfiles\n'\
             % (self.localjobname, self.localjobname)
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

        for outputfile in self.job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename%(src_dst_sep)smig_server_filename"

            parts = outputfile.split(src_dst_sep)
            resource_filename = str(parts[0])

            # We don't need mig_server_filename here so just skip mangling

            # Always strip leading slashes to avoid absolute paths

            resource_filename = resource_filename.lstrip('/')

            # move entire top dir if resource_filename is a nested path

            exe_move = resource_filename.split('/', 1)[0]

            if exe_move not in exe_move_dict:
                exe_move_dict[exe_move] = True

        # Quote file names to protect against exotic characters
        
        cmd += 'echo -n "" > %s.user.outputfiles\\\n' % self.localjobname
        for file in exe_move_dict.keys():
            cmd += "&& echo -n '%s ' >> %s.user.outputfiles\\\n"\
                 % (file, self.localjobname)

        cmd += '&& echo -n "" > %s.system.outputfiles\\\n'\
             % self.localjobname

        # Sleep jobs only generate .status

        if real_job:
            cmd += \
                '&& echo -n "%s.stderr " >> %s.system.outputfiles\\\n'\
                 % (self.job_dict['JOB_ID'], self.localjobname)
            cmd += \
                '&& echo -n "%s.stdout " >> %s.system.outputfiles\\\n'\
                 % (self.job_dict['JOB_ID'], self.localjobname)

        cmd += '&& echo -n "%s.status" >> %s.system.outputfiles\n'\
             % (self.job_dict['JOB_ID'], self.localjobname)
        cmd += '%s=$?\n' % result
        return cmd

    def generate_iosessionid_file(self,
                                result='generate_iosessionid_file'):
        """Generate file containing io-sessionid."""

        cmd = '# Create file used containing io-sessionid.\n'
        cmd += '%s=0\n' % result
        cmd += 'echo -n "%s" > %s.iosessionid\n'\
             % (self.job_dict['IOSESSIONID'], self.localjobname)
        cmd += '%s=$?\n' % result
        return cmd

    def generate_mountsshprivatekey_file(self, 
                                    result='generate_mountsshprivatekey_file'):
        """Generate file containing mount ssh private key in private subdir."""
        cmd = '# Create private key file used when mounting job home\n'
        cmd += '%s=0\n' % result
        # OpenSSH is rather picky about permissions on key so we tighten them
        cmd += 'mkdir -p .mount\n'
        cmd += 'chmod 700 .mount\n'
        cmd += 'echo -n "%s" > .mount/%s.key\n'\
             % (self.job_dict['MOUNTSSHPRIVATEKEY'], self.localjobname)
        cmd += 'chmod 600 .mount/%s.key\n' % self.localjobname
        cmd += '%s=$?\n' % result
        return cmd         

    def generate_mountsshknownhosts_file(self,
                                    result='generate_mountsshknownhosts_file'):
        """Generate file containing ssh mount known_hosts in private subdir."""
       
        cmd = '# Create known_hosts file used when mounting job home\n'
        cmd += '%s=0\n' % result
        cmd += 'mkdir -p .mount\n'
        cmd += 'chmod 700 .mount\n'
        cmd += 'echo -n "%s" > .mount/%s.known_hosts\n'\
             % (self.job_dict['MOUNTSSHKNOWNHOSTS'], self.localjobname)
        cmd += 'chmod 600 .mount/%s.known_hosts\n' % self.localjobname
        cmd += '%s=$?\n' % result
        return cmd

    def chmod_executables(self, result='chmod_status'):
        """Make sure EXECUTABLES are actually executable"""

        cmd = '%s=0\n' % result
        executables = []
        for line in self.job_dict['EXECUTABLES']:

            # "filename" or "mig_server_filename%(src_dst_sep)sresource_filename"

            parts = line.split(src_dst_sep)
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
        requested['JOBDIR'] =  self.localjobdir
        cmd = '''
[ -z "$MIG_JOBNODES" ] && export MIG_JOBNODES="%(NODECOUNT)s"
[ -z "$MIG_JOBNODECOUNT" ] && export MIG_JOBNODECOUNT="%(NODECOUNT)s"
[ -z "$MIG_JOBCPUTIME" ] && export MIG_JOBCPUTIME="%(CPUTIME)s"
[ -z "$MIG_JOBCPUCOUNT" ] && export MIG_JOBCPUCOUNT="%(CPUCOUNT)s"
[ -z "$MIG_JOBMEMORY" ] && export MIG_JOBMEMORY="%(MEMORY)s"
[ -z "$MIG_JOBDISK" ] && export MIG_JOBDISK="%(DISK)s"
[ -z "$MIG_JOBID" ] && export MIG_JOBID="%(JOBID)s"
[ -z "$MIG_LOCALJOBNAME" ] && export MIG_LOCALJOBNAME="%(LOCALJOBNAME)s"
[ -z "$MIG_EXEUNIT" ] && export MIG_EXEUNIT="%(EXE)s"
[ -z "$MIG_EXENODE" ] && export MIG_EXENODE="%(EXE)s"
[ -z "$MIG_JOBDIR" ] && export MIG_JOBDIR="%(JOBDIR)s"
''' % requested
        return cmd

    def set_environments(self, result='env_status'):
        """Set environments"""

        cmd = ''

        for env in self.job_dict['ENVIRONMENT']:
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

    def set_limits(self):
        """Set local resource limits to prevent fork bombs, OOM and such.
        Limits are set slightly higher to avoid overhead problems.
        """
        requested = {'CPUTIME': int(self.job_dict['CPUTIME']) + 10}
        requested['CPUCOUNT'] = int(self.job_dict.get('CPUCOUNT', 1))
        requested['MEMORY'] = int(self.job_dict.get('MEMORY', 1)) + 16
        requested['DISK'] = int(self.job_dict.get('DISK', 1)) + 1
        # Arbitrary values low enough to prevent fork bombs
        requested['MAXPROCS'] = 1024
        # Multipliers for expected units in seconds and kb
        requested['SECS'] = 1
        requested['MEGS'] = 1024
        requested['GIGS'] = 1024*1024
        # These are the supported limits in native resource setups. Just some
        # simple ulimit rules. Owners will need to set up a proper LRMS or e.g.
        # apply cgroups, firejail or virtualization for stricter control.
        all_limits = ['ULIMIT_PROCESSES', 'ULIMIT_CPUTIME', 'ULIMIT_MEMORY',
                      'ULIMIT_DISK']
        all_str = ' '.join(all_limits)
        # Default to all limits enabled
        enforce_limits = self.resource_conf.get('ENFORCELIMITS', all_str)
        for limit in all_limits:
            if limit in enforce_limits.split():
                requested[limit] = 'true'
            else:
                requested[limit] = 'false'
        cmd = '''
# Prevent fork bombs
%(ULIMIT_PROCESSES)s && ulimit -u %(MAXPROCS)d

# Actual request limits - not accurate but better than nothing
%(ULIMIT_CPUTIME)s && ulimit -t $((%(CPUTIME)d*%(CPUCOUNT)d*%(SECS)d))
%(ULIMIT_MEMORY)s && ulimit -v $((%(MEMORY)d*%(MEGS)d))
%(ULIMIT_DISK)s && ulimit -f $((%(DISK)d*%(GIGS)d))
''' % requested
        return cmd

        
        
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

    def mount(self, login, host, port, result='mount_status'):
        """Mount job home sshfs
         Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        
        for mount in self.job_dict.get('MOUNT', []):
 
            # "mount_point" or "mig_server_path%(src_dst_sep)sresource_mount_point"

            parts = mount.split(src_dst_sep)
        
            if len(parts) == 1:
                mig_home_path = ''
                resource_mount_point = str(parts[0])
            else:
                mig_home_path = str(parts[0])
                resource_mount_point = str(parts[1])
            
            # Always strip leading slashes to avoid absolute paths

            mig_home_path = mig_home_path.lstrip('/')
            resource_mount_point = resource_mount_point.lstrip('/')

            cmd += 'mkdir -p %s\n' % (resource_mount_point)
            # Auto-reconnect and use big_writes for far better write performance
            cmd += '${SSHFS_MOUNT} -oPort=%s' % (port) + \
                        ' -oIdentityFile=${PWD}/.mount/%s.key' % \
                            (self.localjobname) + \
                        ' -oUserKnownHostsFile=${PWD}/.mount/%s.known_hosts' \
                        % (self.localjobname) + \
                        ' %s@%s:%s %s ' % \
                        (login, host, mig_home_path, resource_mount_point) + \
                        ' -o uid=$(id -u) -o gid=$(id -g) -o reconnect' + \
                        ' -o big_writes\n'
            cmd += 'last_mount_status=$?\n'
            cmd += 'if [ $last_mount_status -ne 0 ]; then\n'
            cmd += '    %s=$last_mount_status\n' % result
            cmd += 'fi\n'

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

        # TODO: job_log is different from exe job log in parent dir

        exe_dict = {'job_id': self.job_dict['JOB_ID'], 
                    'job_log': '${MIG_JOBDIR}/%s.log' % self.job_dict['JOB_ID'],
                    'job_status': '${MIG_JOBDIR}/%s.status' % self.job_dict['JOB_ID']
                   }
        cmd = ''

        cmd += '''__MiG_LAST_RET=0
{
'''

        for exe in self.job_dict['EXECUTE']:

            # Make sure any apostrophes in EXECUTE do not interfere
            # with our own in logging

            exe_dict['exe_escaped'] = exe.replace("'", '`')

            exe_dict['exe'] = exe

            # Prevent missing quotes from interfering with our exit code extraction

            exe_dict['exe'] += \
                '\n    # MiG caught stray quotes in a command!'
            exe_dict['exe'] += ' #"; (exit 255)'
            exe_dict['exe'] += " #'; (exit 255)"

            # Please note that the 'EXECUTING: sleep' string is used to detect empty jobs
            # in resource scripts: Please propagate any changes!

            cmd += \
                """
    echo 'EXECUTING: %(exe_escaped)s' >> %(job_log)s
    echo -n '--Exit code: ' >> %(job_log)s
    echo -n '%(exe_escaped)s ' >> %(job_status)s
    (exit $__MiG_LAST_RET)
    %(exe)s
    __MiG_LAST_RET=$?
    echo $__MiG_LAST_RET >> %(job_status)s
    echo $__MiG_LAST_RET >> %(job_log)s
"""\
                 % exe_dict

        # Finally add the closing curly brace with IO redirection

        cmd += '''
} 1> %(job_id)s.stdout 2> %(job_id)s.stderr
'''\
             % exe_dict
        return cmd

    def umount(self, result='umount_status'):
        """Unmounts job home
	    Continue on errors but return total status."""

        cmd = '%s=0\n' % result
        cmd += 'cd ${MIG_JOBDIR}\n' 
 
        for mount in self.job_dict.get('MOUNT', []):
 
            # "resource_mount_point" or "mig_home_path%(src_dst_sep)sresource_mount_point"

            parts = mount.split(src_dst_sep)
        
            if len(parts) == 1:
                resource_mount_point = str(parts[0])
            else:
                resource_mount_point = str(parts[1])
            
            # Always strip leading slashes to avoid absolute paths

            resource_mount_point = resource_mount_point.lstrip('/')

            cmd += '${SSHFS_UMOUNT} %s\n' % (resource_mount_point)
            cmd += 'last_umount_status=$?\n'
            cmd += 'if [ $last_umount_status -ne 0 ]; then\n'
            cmd += '    %s=$last_umount_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def output_files_missing(self, result='missing_counter'):
        """Check availability of outputfiles:
        Return number of missing files.
        """

        cmd = '%s=0\n' % result
        for outputfile in self.job_dict['OUTPUTFILES']:

            # "filename" or "mig_server_filename%(src_dst_sep)sresource_filename"

            parts = outputfile.split(src_dst_sep)
            resource_filename = str(parts[0])
            try:
                mig_server_filename = str(parts[1])
            except:
                mig_server_filename = resource_filename

            # Quote file names to protect against exotic characters
        
            cmd += "[ -e '%s' ] || %s=$((%s+1))\n"\
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
        for outputfile in self.job_dict['OUTPUTFILES']:

            # "filename" or "resource_filename%(src_dst_sep)smig_server_filename"

            parts = outputfile.split(src_dst_sep)
            resource_filename = str(parts[0])
            try:
                mig_server_filename = str(parts[1])
            except:
                mig_server_filename = resource_filename

            # External destinations will always be explicit so no
            # need to mangle protocol prefix here as in get inputfiles

            # Always strip leading slashes to avoid absolute paths

            mig_server_filename = mig_server_filename.lstrip('/')

            # Quote file names to protect against exotic characters
        
            cmd += "[ ! -e '%s' ] || " % resource_filename
            cmd += '%s\n' % self.__curl_cmd_send(resource_filename,
                    mig_server_filename, False)
            cmd += 'last_send_status=$?\n'
            cmd += 'if [ $last_send_status -ne 0 ]; then\n'
            cmd += '    %s=$last_send_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def send_io_files(self, result='send_io_status'):
        """Send IO files:
        Existing files must be transferred with status 0, while
        non-existing files shouldn't lead to error.
        Only react to curl transfer errors, not MiG put errors
        since we can't handle the latter consistently anyway.
        """

        cmd = '%s=0\n' % result
        cmd += '# First parameter is target: result, liveio or mqueue\n'
        cmd += 'target=$1\n'
        cmd += 'shift\n'
        cmd += '# All but last input args are sources and last is dest\n'
        cmd += 'i=0\n'
        cmd += 'last=$((${#@}-1))\n'
        cmd += 'for name in $@; do\n'
        cmd += '    if [ $i -lt $last ]; then\n'
        cmd += '        # stored in flat structure on FE\n'
        cmd += '        src[$i]=`basename $name`\n'
        cmd += '    else\n'
        cmd += '        dst=$name\n'
        cmd += '    fi\n'
        cmd += '    i=$((i+1))\n'
        cmd += 'done\n'
        cmd += 'for name in ${src[@]}; do\n'
        cmd += '    name_on_mig_server=$dst/`basename $name`\n'
        cmd += '    if [ "$target" = "mqueue" ]; then\n'
        cmd += '        %s\n' % self.__curl_cmd_send_mqueue('$name', '$dst')
        cmd += '    else\n'

        cmd += '        [ ! -e "$name" ] || '
        cmd += '%s\n' % self.__curl_cmd_send('$name', '$name_on_mig_server',
                                             True)
        cmd += '    fi\n'
        cmd += '    last_send_status=$?\n'
        cmd += '    if [ $last_send_status -ne 0 ]; then\n'
        cmd += '        %s=$last_send_status\n' % result
        cmd += '    fi\n'
        cmd += 'done\n'

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
            name_on_mig_server = os.path.join(job_output_dir,
                                              self.job_dict['JOB_ID'], name)
            cmd += '[ -e "%s" ] && ' % name
            cmd += '%s\n' % self.__curl_cmd_send(name, name_on_mig_server,
                                                 False)
            cmd += 'last_send_status=$?\n'
            cmd += 'if [ $last_send_status -ne 0 ]; then\n'
            cmd += '    %s=$last_send_status\n' % result
            cmd += 'fi\n'

        cmd += """# Now 'return' status is available in %s

""" % result
        return cmd

    def request_interactive(self):
        """Request interactive job"""

        # return curl_cmd_request_interactive(https_sid_url_arg,
        #                                    self.job_dict, self.resource_conf,
        #                                    exe)

        return self.__curl_cmd_request_interactive()

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

    def log_on_error(
        self,
        result='ret',
        successcode='0',
        msg='ERROR: unexpected exit code!',
        ):
        """Log msg unless result contains success code"""

        cmd = 'if [ $' + result + ' -ne ' + successcode + ' ]; then\n'
        cmd += self.log_status(msg, result)
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
             + self.job_dict['JOB_ID'] + '" \nexit ' + exitcode + '\n'\
             + '### END OF SCRIPT ###\n'

    def clean_up(self):
        """Clean up"""

        # cd .. ; rm -rf --one-file-system "job id"

        cmd = ''

        cmd += 'cd ..\n'
        cmd += 'rm -rf --one-file-system ' + self.job_dict['JOB_ID'] + '\n'
        return cmd


