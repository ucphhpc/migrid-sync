#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resconfkeywords - [insert a few words of module description on this line]
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

"""Keywords in the resource configuration files"""


def get_resource_keywords(configuration):
    scriptlanguage = {
        'Description': 'The language the MiG server should use to create the job scripts. Valid languages: %s'\
             % configuration.scriptlanguages,
        'Example': 'sh',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    memory = {
        'Description': 'Amount of memory available on each node on the resource. The amount is specified in megabytes ',
        'Example': '128',
        'Type': 'int',
        'Value': 1,
        'Required': True,
        }
    disk = {
        'Description': 'Amount of disk space available on each node on the resource. The amount is specified in gigabytes and the default is zero.',
        'Example': '10',
        'Type': 'int',
        'Value': 0,
        'Required': True,
        }
    cpucount = {
        'Description': "Number of CPU's on each node.",
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Required': True,
        }
    nodecount = {
        'Description': 'Number of total nodes.',
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Required': True,
        }
    sandbox = {
        'Description': 'Specifies whether resource is a sandbox. If 0, the resource is not a sandbox, if 1, the resource is a sandbox.',
        'Example': '0',
        'Type': 'int',
        'Value': 0,
        'Required': False,
        }
    sandboxkey = {
        'Description': 'Specifies the secret sandboxkey for a sandbox.',
        'Example': '2AD32342423421111',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    jobtype = {
        'Description': "Specifies which types of jobs the resource accepts. A job can be of type 'interactive', 'batch' or 'bulk' and the keyword 'all' is provided to allow all types. Interactive jobs are executed on a resource but with the graphical display forwarded to the MiG display of the user. Batch jobs are executed in a headless mode and can not use graphical output. Bulk jobs are like batch jobs, but additionally allow concurrent execution of other bulk jobs belonging to the same user. I.e. a bulk of multiple jobs running on the same resource at the same time, as long as the resource can provide the requested job resources (cpucount, nodecount, memory, disk). This particular MiG server supports the following jobtypes: %s"\
             % ', '.join(configuration.jobtypes),
        'Example': 'all',
        'Type': 'string',
        'Value': 'batch',
        'Required': False,
        }
    architecture = {
        'Description': "The resource's CPU architecture.",
        'Example': 'Valid architectures: %s'\
             % configuration.architectures,
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    adminemail = {
        'Description': 'A space separated list of email addresses of resource administrators - used to notify about internal errors.',
        'Example': 'admin@yourdomain.org',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    minprice = {
        'Description': 'Minimum price. Jonas...',
        'Example': '40',
        'Type': 'string',
        'Value': '0',
        'Required': False,
        }
    miguser = {
        'Description': 'The username on the resource that MiG jobs are run as.',
        'Example': 'mig',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    hosturl = {
        'Description': 'The Fully Qualified Domain Name of the resource. Must be available from the Internet.',
        'Example': 'www.myresource.com',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    hostidentifier = {
        'Description': 'The Identity of the Resource.',
        'Example': '0',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    resourcehome = {
        'Description': 'The home directory of miguser.',
        'Example': '/home/mig/mighome/',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    hostkey = {
        'Description': 'The public hostkey of the resource (content of /etc/ssh/ssh_host_rsa_key.pub)',
        'Example': 'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEA00hFE4OiIzcRBFowx9Li5giPwh5Z6ni2Zo256pZwg3IjYeiudeqam6E8MuVaZ6NerrkDRdY6JaN8KZ47YNRNP6iuoI9K9eqYOZ08MzEGytRf5fyWEpAnRQjgk/jJygM2BM2ImtxbT+IOwIkCuX6ekL7E+r7tfrd3uOG7RdVox2E=',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    runtimeenvironment = {
        'Description': 'Runtimeenvironments available on the resource.\nInformation about all available runtime environments and their required variables are available at the Runtime Envs page.',
        'Example': '''name: LOCALDISK
name: GENERECON-2.1.3
GENERECON_HOME=/home/mig/GeneRecon
GUILE_LOAD_PATH=$GENERECON_HOME''',
        'Type': 'configruntimeenvironment',
        'Value': [],
        'Required': False,
        }
    frontendnode = {
        'Description': 'The name of the frontend node seen from the execution nodes. This can be the FQDN of the frontend, but often the frontend can be accessed easier from the nodes than using the FQDN.',
        'Example': 'roadrunner',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    curllog = {
        'Description': 'Name of the logfile for the curl commands.',
        'Example': '/home/mig/curllog',
        'Type': 'string',
        'Value': '/dev/null',
        'Required': False,
        }
    frontendlog = {
        'Description': 'Name of the logfile for the frontend.',
        'Example': '/home/mig/frontendlog',
        'Type': 'string',
        'Value': '/dev/null',
        'Required': False,
        }
    execonfig = {
        'Description': 'Configuration for the execution resources: please refer to the Execution node section.',
        'Example': 'Example not available',
        'Type': 'execonfig',
        'Value': [],
        'Required': True,
        'Sublevel': True,
        'Sublevel_required': [
            'name',
            'nodecount',
            'cputime',
            'execution_precondition',
            'prepend_execute',
            'exehostlog',
            'joblog',
            'execution_user',
            'execution_node',
            'execution_dir',
            'start_command',
            'status_command',
            'stop_command',
            'clean_command',
            'continuous',
            'shared_fs',
            'vgrid',
            ],
        'Sublevel_optional': [],
        }
    sshport = {
        'Description': 'The SSH port on the frontend.',
        'Example': '22',
        'Type': 'int',
        'Value': 22,
        'Required': False,
        }
    sshmultiplex = {
        'Description': 'Enable sharing of multiple ssh sessions over a single network connection. This can significantly speed up MiG communication with the resource, if the resource supports session multiplexing. If unset or 0 multiplexing is disabled, otherwise it will be attempted (Just leave it unset if in doubt).',
        'Example': '1',
        'Type': 'int',
        'Value': 0,
        'Required': False,
        }
    lrmstype = {
        'Description': 'Specifies the type of Local Resource Management System (LRMS). Simple resources generally use native execution to simply fork a new job subprocess whereas clusters and super computers tend to rely on a batch system like PBS or SGE to manage job processes. The type setting is used to decide if the remaining LRMS* settings are used to manage jobs. The default is Native execution where they are ignored because jobs are only running in the foreground, completely eliminating the need to submit or query progress. For each type there is a plain version and an X-execution-leader version: The former uses a model where each execution node on the resource is handled by a dedicated process. As the number of execution nodes grows this may become a resource bottleneck, and in that case the X-execution-leader version may be more efficient, because it handles all execution nodes in a single leader process. This is known to severely lessen the load on cluster frontends where the user home directories are located on a NFS mounted file system. Please note that the PBS and SGE flavors are now deprecated because they are no longer handled differently from the replacement general Batch flavors. So simply use one of the Batch modes instead of PBS or SGE flavors and request/download the appropriate LRMS helper scripts from mig/resource/lrms-scripts/ directory in the MiG source code.',
        'Example': 'Batch',
        'Type': 'string',
        'Value': 'Native',
        'Required': False,
        }
    lrmsdelaycommand = {
        'Description': 'Specifies the command used to find and print the batch job execution delay estimate (only used if the resource uses a batch system). The specified command is called right before requesting a new job. Three helper environment variables MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER are available. It should return (print) only the expected number of seconds a job with MIG_MAXNODES nodes, MIG_MAXSECONDS seconds of walltime and submitted by MIG_SUBMITUSER will have to wait in the queue before execution. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/queue_delay.sh',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    lrmssubmitcommand = {
        'Description': 'Specifies the command used to submit batch jobs (only if the resource uses a batch system). All job requirements are available in environment variables, so that the command can submit the job with appropriate resources. Thus the variables MIG_JOBNODECOUNT, MIG_JOBCPUCOUNT, MIG_JOBCPUTIME, MIG_JOBMEMORY and MIG_JOBDISK hold the requested nodecount, cpucount, cputime in seconds, memory in MB and disk in GB for the submit command to use. Furthermore the MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER will always hold a unique name for the job, the path to the job files, the name of the execution node and the local username. In case the local LRMS requires additional flags to schedule the jobs only to suitable nodes, those options can also be included here (e.g. qsub -l arch=i686). In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/submit_job.sh',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    lrmsremovecommand = {
        'Description': 'Specifies the command used to remove submitted batch jobs (only used if the resource uses a batch system). To help locating the correct job the MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER will always hold a unique name for the job, the path to the job files, the name of the execution node and the local username. If the submit command includes flags to label jobs with MIG_JOBNAME and they are submitted by MIG_SUBMITUSER, those fields can be used to identify the job again here. Any additional LRMS flags (e.g. qdel -l arch=i686) for finer control over scheduling can be added here, too. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/remove_job.sh',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    lrmsdonecommand = {
        'Description': 'Specifies the command used to query if a submitted batch job is done (only used if the resource uses a batch system). The specified command is called repeatedly after submitting the MiG job to the LRMS and should return 0 only when the job is done and the result can be delivered. The usual helper environment variables MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER are available to help querying the status of the right job. If the submit command includes flags to label jobs with MIG_JOBNAME and they are submitted by MIG_SUBMITUSER, those fields can be used to identify the job again here. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/query_done.sh',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }
    maxdownloadbandwidth = {
        'Description': 'Specifies the max download bandwidth (in kB) the resource is allowed to use. If 0 or unset, there is no limit.',
        'Example': '2048',
        'Type': 'int',
        'Value': 0,
        'Required': False,
        }
    maxuploadbandwidth = {
        'Description': 'Specifies the max upload bandwidth (in kB) the resource is allowed to use. If 0 or unset, there is no limit.',
        'Example': '512',
        'Type': 'int',
        'Value': 0,
        'Required': False,
        }
    platform = {
        'Description': 'Specifies a platform architecture this resource supports.',
        'Example': 'ONE-CLICK',
        'Type': 'string',
        'Value': '',
        'Required': False,
        }

    # create the keywords in a single dictionary

    keywords_dict = {
        'SCRIPTLANGUAGE': scriptlanguage,
        'MEMORY': memory,
        'DISK': disk,
        'CPUCOUNT': cpucount,
        'NODECOUNT': nodecount,
        'SANDBOX': sandbox,
        'SANDBOXKEY': sandboxkey,
        'JOBTYPE': jobtype,
        'ARCHITECTURE': architecture,
        'ADMINEMAIL': adminemail,
        'MINPRICE': minprice,
        'MIGUSER': miguser,
        'HOSTURL': hosturl,
        'HOSTIDENTIFIER': hostidentifier,
        'RESOURCEHOME': resourcehome,
        'HOSTKEY': hostkey,
        'RUNTIMEENVIRONMENT': runtimeenvironment,
        'FRONTENDNODE': frontendnode,
        'CURLLOG': curllog,
        'FRONTENDLOG': frontendlog,
        'EXECONFIG': execonfig,
        'SSHPORT': sshport,
        'SSHMULTIPLEX': sshmultiplex,
        'LRMSTYPE': lrmstype,
        'LRMSDELAYCOMMAND': lrmsdelaycommand,
        'LRMSSUBMITCOMMAND': lrmssubmitcommand,
        'LRMSREMOVECOMMAND': lrmsremovecommand,
        'LRMSDONECOMMAND': lrmsdonecommand,
        'MAXDOWNLOADBANDWIDTH': maxdownloadbandwidth,
        'MAXUPLOADBANDWIDTH': maxuploadbandwidth,
        'PLATFORM': platform,
        }
    return keywords_dict


# TODO: replace all get_keywords_dict() calls with get_resource_keywords and drop


def get_keywords_dict(configuration):
    """Legacy function now handled by get_resource_keywords"""

    return get_resource_keywords(configuration)


def get_exenode_keywords(configuration):
    name = {
        'Description': 'Execution node names are symbolic names to identify MiG execution nodes. This can be any text string as long as it is unique among the execution nodes of the resource. The MiG execution nodes do not necessarily have to map to physical hosts in a one-to-one way.',
        'Example': 'exe0',
        'Type': 'string',
        'Value': 'localhost',
        'Required': True,
        }
    cputime = {
        'Description': 'The maximum number of seconds of walltime each MiG job is allowed to use on an execution node.',
        'Example': '86400',
        'Type': 'int',
        'Value': '3600',
        'Required': True,
        }
    nodecount = {
        'Description': 'The number of actual computation nodes associated with a MiG execution node. For simple resources or clusters exposing each node individually this is just one. However, the resource can map multiple physical nodes to a single MiG execution node through an LRMS or a cluster frontend, so it may bind more than one actual node to each MiG execution node.',
        'Example': '128',
        'Type': 'int',
        'Value': '1',
        'Required': True,
        }
    execution_precondition = {
        'Description': "Command used to decide if execution node should request a job or wait for later. This can be used to delay the job request for execution nodes under heavy load. If the command returns a non-zero exit code the node will run a sleep job before trying again. Otherwise it will request a job as usual. An example is to only request a job if the load average is below 1.0 . Please note that this command is not allowed to contain single quotes (') because it will interfere with the way it is called.",
        'Example': 'uptime | grep "load average: 0"',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    prepend_execute = {
        'Description': "If the execution node should perform a task before the execution of the MiG job or prefix the job command with another command, it should be specified here. This can be used to run jobs with a modified scheduling priority ('nice').",
        'Example': 'nice',
        'Type': 'string',
        'Value': '',
        'Required': True,
        }
    exehostlog = {
        'Description': 'Name of the main log file for the execution node.',
        'Example': '/home/mig/exehostlog',
        'Type': 'string',
        'Value': '~${MIG_USER}/MiG/mig_exe/${MIG_RESOURCE}/${MIG_EXENODE}/exehostlog',
        'Required': True,
        }
    joblog = {
        'Description': 'Name of the job log file for the execution node.',
        'Example': '/home/mig/exehostlog',
        'Type': 'string',
        'Value': '~${MIG_USER}/MiG/mig_exe/${MIG_RESOURCE}/${MIG_EXENODE}/joblog',
        'Required': True,
        }
    execution_user = {
        'Description': 'The local user to login as on the node(s) associated with this MiG execution node. In most cases this is identical to the global resource MiG user.',
        'Example': 'miguser',
        'Type': 'string',
        'Value': '${MIG_USER}',
        'Required': True,
        }
    execution_node = {
        'Description': 'The local user to login as on the node(s) associated with this MiG execution node. In most cases this is identical to the global resource MiG user.',
        'Example': 'miguser',
        'Type': 'string',
        'Value': '${MIG_USER}',
        'Required': True,
        }
    execution_dir = {
        'Description': 'Path to the working directory of the execution node.',
        'Example': '/home/miguser/MiG/mig_exe/myresource.org.0/localhost/',
        'Type': 'string',
        'Value': '~${MIG_USER}/MiG/${MIG_RESOURCE}/${MIG_EXENODE}/',
        'Required': True,
        }
    start_command = {
        'Description': "The command which is used to start the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through ssh to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Required': True,
        }
    status_command = {
        'Description': "The command which is used to query status of the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through ssh to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Required': True,
        }
    stop_command = {
        'Description': "The command which is used to stop the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through ssh to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Required': True,
        }
    clean_command = {
        'Description': "The command which is used to clean the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through ssh to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Required': True,
        }
    continuous = {
        'Description': 'If the execution node should continuously take jobs (i.e. True) or only run a single job when started (i.e. False). The default setting is to run in continuous mode, but some applications such as The MiG ScreenSaver Science require single run mode.',
        'Example': 'False',
        'Type': 'boolean',
        'Value': 'True',
        'Required': True,
        }
    shared_fs = {
        'Description': 'If the frontend and execution node shares the same file system (i.e. True), so that frontend and execution management processes can communicate directly through files in the MiG user home directory. If this is not the case (i.e. False) the communication will use ssh to communicate, but this is slightly less efficient and requires additional setup of local login access without password. To be more precise the frontend must be able to login as the execution user on the execution node and vice versa without any user input (e.g. by using ssh keys with an empty passphrase).',
        'Example': 'False',
        'Type': 'boolean',
        'Value': 'True',
        'Required': True,
        }
    vgrid = {
        'Description': 'Which VGrids should the resource accept jobs from? Please note that the corresponding VGrid owners must add the resource to the VGrid first. The raw format is a comma separated list of VGrid names.',
        'Example': 'Generic, MyVGrid',
        'Type': 'list of strings',
        'Value': 'Generic',
        'Required': True,
        }

    # create the keywords in a single dictionary

    keywords_dict = {
        'NAME': name,
        'CPUTIME': cputime,
        'NODECOUNT': nodecount,
        'EXECUTION_PRECONDITION': execution_precondition,
        'PREPEND_EXECUTE': prepend_execute,
        'EXEHOSTLOG': exehostlog,
        'JOBLOG': joblog,
        'EXECUTION_USER': execution_user,
        'EXECUTION_NODE': execution_node,
        'EXECUTION_DIR': execution_dir,
        'START_COMMAND': start_command,
        'STATUS_COMMAND': status_command,
        'STOP_COMMAND': stop_command,
        'CLEAN_COMMAND': clean_command,
        'CONTINUOUS': continuous,
        'SHARED_FS': shared_fs,
        'VGRID': vgrid,
        }
    return keywords_dict


