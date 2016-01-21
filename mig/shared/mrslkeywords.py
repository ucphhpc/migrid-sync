#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mrslkeywords - Mapping of available mRSL keywords and specs
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

"""Keywords in the mRSL language:
Works as a combined specification of and source of information about keywords.
"""

from shared.defaults import default_vgrid, any_vgrid, src_dst_sep

# This is the main location for defining job keywords. All other job handling
# functions should only operate on keywords defined here.


def get_job_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    sep_helper = {'sep': src_dst_sep, 'short': configuration.short_title}
    specs = []
    specs.append(('EXECUTE', {
        'Title': 'Execute Commands',
        'Description': 'One or more commands to execute',
        'Example': '''
::EXECUTE::
uname -a
echo text >> file
ls

Executes the commands sequentially in a simple shell script environment on the resource.
Thus changes to the environment are preserved for the entire job session, so e.g.
::EXECUTE::
cd mydir
pwd

will change to mydir and run the pwd command from there.

All string fields including EXECUTE support automatic expansion of the variables +JOBID+ and +JOBNAME+ to the actual ID and name of the job. This may be useful in relation to e.g. Monte Carlo simulations where a lot of identical job descriptions are submitted which need to deliver their unique results without interference from other jobs.

Please note that our command exit code extraction for the JOBID.status file may interfere
with some advanced shell features. Thus if you experience problems with e.g. Job Control
(also known as backgrounding of processes), you should wrap up your commands in your own
script instead of putting them directly in the EXECUTE field.
''',
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('INPUTFILES', {
        'Title': 'Input Files',
        'Description': '''Files to be copied to the resource before job execution.
Relative paths like plain file names are automatically taken from the user home on the %(short)s server.
External sources are also allowed as long as they can be downloaded with the "curl" client without user interaction. This means that HTTP, HTTPS, FTP, FTPS, SCP, SFTP, TFTP, DICT, TELNET or even LDAP are at least technically supported. External data sources obviously require the executing resource to have outbound network access to the data source. Thus HTTP and HTTPS are the most likely to generally work even on network restricted resources.
Inputfiles may be specified as a single name per line or as lines of source and destination path separated by a "%(sep)s". In the single name format the file will be called the same on the destination as on the source.
Supports the same variable expansion as described in the EXECUTE field documentation, but neither directories nor wild cards are supported!
''' % sep_helper,
        'Example': '''
::INPUTFILES::
somefile
another_file%(sep)sanother_file_renamed

Copies somefile and another_file from your %(short)s server home to the resource, but another_file is renamed to another_file_renamed on the resource.

::INPUTFILES::
some_url%(sep)ssome_file

Downloads the contents from some_url (e.g. https://myhost.org/inputfile.txt) to a file called some_file on the resource.
''' % sep_helper,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('OUTPUTFILES', {
        'Title': 'Output Files',
        'Description': '''Files to be copied from the resource after job execution.
Relative paths like plain file names are automatically sent to the user home on the %(short)s server. External destinations are also allowed as long as they can be uploaded with the "curl" client without user interaction. This means that HTTP, HTTPS, FTP, FTPS, SCP, SFTP, TFTP, DICT, TELNET or even LDAP are at least technically supported. External data destinations obviously require the executing resource to have outbound network access to the data destination. Thus HTTP or HTTPS are the most likely to be allowed even on network restricted resources. Please note however, that HTTP upload requires the destination HTTP server to support the PUT operation, which is not generally enabled on all servers.
Outputfiles may be specified as a single name per line or as lines of source and destination path separated by a "%(sep)s". In the single name format the file will be called the same on the destination as on the source.
Supports the same variable expansion as described in the EXECUTE field documentation, but neither directories nor wild cards are supported!
''' % sep_helper,
        'Example': '''
::OUTPUTFILES::
file
another_file_renamed%(sep)sanother_file

Copies file and another_file_renamed from the resource to your %(short)s home, but another_file_renamed is renamed to another_file on the server.

::OUTPUFILES::
some_file%(sep)ssome_url

Uploads some_file on the resource to some_url (e.g. ftp://myuser:mypw@myhost.org/outputfile.txt).
''' % sep_helper,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('EXECUTABLES', {
        'Title': 'Executable Files',
        'Description': '''Executables to be copied to the resource before the job execution.
These files are exactly like the INPUTFILES, but the files are made executable (chmod +x) after they are copied to the resource.
Supports the same variable expansion as described in the EXECUTE field documentation, but neither directories nor wild cards are supported!
''',
        'Example': '''
::EXECUTABLES::
myscript
myfile_or_url%(sep)ssome_name

Copies myscript and myfile_or_url from your %(short)s home to the resource, but myfile_or_url is renamed to the executable some_name on the resource.
''' % sep_helper,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('MOUNT', {
        'Title': 'Mount',
        'Description': '''Mounts your %s home on resource before job execution.''' % configuration.short_title,
        'Example': '''
:::MOUNT:::
home_path%(sep)sresource_mount_point

Mounts your %(short)s home_path on resource_mount_point, the mount is disabled when the job finishes.
''' % sep_helper,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('RESOURCE', {
        'Title': 'Target Resources',
        'Description': '''A list of resources allowed to execute the job (default is unset which means any resource).
Each entry can be a full resource ID or a pattern with wild card support to match multiple resources or execution nodes.''',
        'Example': '''
::RESOURCE::
6ad933abfde57855d45fd805654508f9_*
f92dc607c8d1bc4710fad44f89cfd40b_localhost

To submit with execution on any executor under the resource with ID 6ad933abfde57855d45fd805654508f9 or on the localhost exe node under the resource with ID f92dc607c8d1bc4710fad44f89cfd40b.

Leave unset or empty to submit with execution on the first suitable resource.
''',
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('VGRID', {
        'Title': 'VGrid Order',
        'Description': '''A prioritized list of the VGRIDs allowed to execute the job (default value is %s).
During job submit the keyword %s is replaced by a list of all the VGrids that you can access.
''' % (default_vgrid, any_vgrid),
        'Example': '''
::VGRID::
Dalton

To submit with execution on the Dalton VGrid only.

::VGRID::
%s

To submit with execution on the first suitable and allowed VGrid.
''' % any_vgrid,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('NODECOUNT', {
        'Title': 'Number of Nodes',
        'Description': 'Number of nodes.',
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('CPUCOUNT', {
        'Title': 'Number of CPU Cores',
        'Description': "Number of CPU's the job requires on each node.",
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('CPUTIME', {
        'Title': 'CPU/Wall Time (s)',
        'Description': 'The time required to execute the job. The time is specified in seconds',
        'Example': '60',
        'Type': 'int',
        'Value': 600,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('MEMORY', {
        'Title': 'Memory (MB)',
        'Description': 'Amount of memory required to execute the job. The amount is specified in megabytes ',
        'Example': '128',
        'Type': 'int',
        'Value': 64,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('DISK', {
        'Title': 'Disk (GB)',
        'Description': 'Amount of disk space required to execute the job. The amount is specified in gigabytes and the default is zero.',
        'Example': '10',
        'Type': 'int',
        'Value': 0,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('ARCHITECTURE', {
        'Title': 'CPU Architecture',
        'Description': 'CPU architecture required for execution',
        'Example': '''
::ARCHITECTURE::
X86

This particular server supports the following values:
%s
'''\
             % ', '.join(configuration.architectures),
        'Type': 'string',
        'Value': '',
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('ENVIRONMENT', {
        'Title': 'Environment Variables',
        'Description': 'Sets the environments specified before job execution',
        'Example': 'myenv=/home/user/dir',
        'Type': 'multiplekeyvalues',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('RUNTIMEENVIRONMENT', {
        'Title': 'Runtime Environments',
        'Description': 'Runtime environments like e.g. software packages that the job requires',
        'Example': '''
::RUNTIMEENVIRONMENT::
POVRAY3-6

The job will only be executed on resources that advertize the same runtime environment(s).
''',
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('NOTIFY', {
        'Title': 'Job Status Notification',
        'Description': '''Email and/or Instant Messenger account to notify when the job is done or if it fails.
If you have configured your %s settings you may leave the address part empty or set it to "SETTINGS" to use the saved setting.
''' % configuration.short_title ,
        'Example': '''
::NOTIFY::
myemail@mailserver.org
jabber: myaccount@jabberserver.org
yahoo: 
msn: SETTINGS

Sends email to myemail@mailserver.org, jabber message to myaccount@jabberserver.org and MSN message to any MSN addresses saved on the Settings page.
''',
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('VERIFYFILES', {
        'Title': 'Result Verification Files',
        'Description': 'Files to verify job execution results and output against',
        'Example': '''
::VERIFYFILES::
EXPECTED.status
EXPECTED.stdout
EXPECTED.stderr

Compares JOB_ID.status from the job against the file called EXPECTED.status from the %s home directory and similarly for JOB_ID.stdout and JOB_ID.stderr. For each supplied verify file, EXPECTED.X, the corresponding JOB_ID.X file will be verified line by line using regular expression matching. If any verification fails, the VERIFIED field of the job will be set to FAILURE with the reason appended. If all verification succeeds the VERIFIED field will be set to SUCCESS with a list of the checks appended. If VERIFYFILES is left unset the VERIFIED field will simply be set to NO. In all cases the VERIFIED field is shown as a part of the job status.
''' % configuration.short_title ,
        'Type': 'multiplestrings',
        'Value': [],
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('RETRIES', {
        'Title': 'Job Retries',
        'Description': 'Specifies the maximum number of automatic retries if the job does not finish within the requested time. E.g. if the resource dies or just does not provide enough speed to deliver results in time. If not set the server default of %s is used. It may be a good idea to increase the number of retries for e.g. long sandbox jobs where the risk of the resource going offline is higher. Similarly it is recommended to lower it for experimental jobs where a broken specification will otherwise cause repeated job failures and resulting forced empty jobs on the resources.'\
             % configuration.job_retries,
        'Example': '5',
        'Type': 'int',
        'Value': configuration.job_retries,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('JOBTYPE', {
        'Title': 'Job Type',
        'Description': '''Specifies the type of a job:
A job can be of type "interactive", "batch" or "bulk". Interactive jobs are executed on a resource but with the graphical display forwarded to the MiG display of the user. Batch jobs are executed in a headless mode and can not use graphical output. Bulk jobs are like batch jobs, but additionally allows concurrent execution of your other jobs on the same resource as long as the resource can provide the requested job resources (cpucpunt, nodecount, memory, disk). Set to "interactive" for jobs that use a display, set to bulk for high throughput jobs and leave unset or set to batch for the rest.

This particular server supports the following values:
%s
'''\
             % ', '.join(configuration.jobtypes),
        'Example': 'interactive',
        'Type': 'string',
        'Value': 'batch',
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('JOBNAME', {
        'Title': 'Job Name',
        'Description': 'Name identifying the job (white space is not allowed)',
        'Example': 'JOB23',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('PROJECT', {
        'Title': 'Project',
        'Description': '''Mark this job as part of a project.
This makes is possible to get a total statistic for all jobs in a project.
''',
        'Example': 'myprojectname',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('SANDBOX', {
        'Title': 'Allow Sandbox Execution',
        'Description': 'Specifies whether the job may run in a sandbox. If 0 or false it may not, if 1 or true it may.',
        'Example': 'True',
        'Type': 'boolean',
        'Value': False,
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('PLATFORM', {
        'Title': 'Platform',
        'Description': 'Specifies the platform architecture used for the execution of the job.',
        'Example': 'ONE-CLICK',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('MAXPRICE', {
        'Title': 'Maximum Allowed Price',
        'Description': '''Maximum price to pay for the execution of the job.
The economy is not yet enforced, so this is a proof of concept option only.
''',
        'Example': '40',
        'Type': 'string',
        'Value': '0',
        'Editor': 'invisible',
        'Required': False,
        }))
    return specs

def get_keywords_dict(configuration):
    """Return mapping between job keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_job_specs(configuration))


