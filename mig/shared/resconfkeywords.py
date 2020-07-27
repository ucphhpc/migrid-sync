#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resconfkeywords - Resource configuration keywords and specs
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

"""Keywords in the resource configuration files"""
from __future__ import absolute_import

from .shared.defaults import default_vgrid


# This is the main location for defining resource keywords. All other resource
# configuration functions should only operate on keywords defined here.


def get_resource_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('HOSTURL', {
        'Title': 'Host FQDN or IP',
        'Description': 'The Fully Qualified Domain Name or IP address of the resource. Must be accessible from the Internet!',
        'Example': 'www.myresource.com',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('HOSTIDENTIFIER', {
        'Title': 'Unique Host Identifier',
        'Description': 'An identifier which combined with the Host FQDN or IP assures a unique identity for the Resource. Automatically generated for uniqueness.',
        'Example': '0',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('ANONYMOUS', {
        'Title': 'Anonymize ID in grid',
        'Description': 'Enable anonymous resource ID for this resource in all grid interfaces. When enabled the unique resource name will be hashed to a long string of apparently random characters. Default vlaue is True.',
        'Example': 'False',
        'Type': 'boolean',
        'Value': True,
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('HOSTKEY', {
        'Title': 'SSH Public Host Key',
        'Description': 'The public SSH host key of the resource (content of e.g. /etc/ssh/ssh_host_rsa_key.pub). Can be left empty to disable host key validation, but that is not recommended as it weakens the trust model.',
        'Example': 'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEA00hFE4OiIzcRBFowx9Li5giPwh5Z6ni2Zo256pZwg3IjYeiudeqam6E8MuVaZ6NerrkDRdY6JaN8KZ47YNRNP6iuoI9K9eqYOZ08MzEGytRf5fyWEpAnRQjgk/jJygM2BM2ImtxbT+IOwIkCuX6ekL7E+r7tfrd3uOG7RdVox2E=',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('SSHPORT', {
        'Title': 'SSH Port',
        'Description': 'The SSH port on the frontend.',
        'Example': '22',
        'Type': 'int',
        'Value': 22,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('MIGUSER', {
        'Title': '%s SSH User' % configuration.short_title,
        'Description': 'The %s SSH login user on the resource frontend node.'\
                       % configuration.short_title,
        'Example': 'miguser',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('RESOURCEHOME', {
        'Title': '%s Frontend Working Directory' % configuration.short_title,
        'Description': 'The working directory for the %s user on the resource frontend.'\
                        % configuration.short_title,
        'Example': '/home/miguser',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('FRONTENDNODE', {
        'Title': 'Frontend Node',
        'Description': 'The name of the frontend node seen from the execution nodes. This can be the FQDN of the frontend, but often the frontend can be accessed easier from the nodes than using the FQDN.',
        'Example': 'roadrunner',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('FRONTENDPROXY', {
        'Title': 'Frontend Proxy',
        'Description': 'The optional name of a NAT-proxy that the grid server sees as the source of all network connections coming from the resource frontend. This should be an FQDN of such a proxy, and it is ONLY relevant in special cases like if the resource is behind a transparent NAT-gateway rather than on a public IP. Leave blank unless connections from the frontend appear to come from another IP address than one matching the Frontend Node FQDN. NB: you may have to leave HOSTKEY blank if you use FRONTENDPROXY since the ssh hostkey check may fail in the proxy setup.',
        'Example': 'gateway.mydomain.org',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('SCRIPTLANGUAGE', {
        'Title': 'Script Language',
        'Description': "The language the %s server will use to create the control and job scripts to be executed on the resource. Please note that bourne compatible shell, 'sh', is the only fully supported language for dedicated resources at the moment. So you should not use any other value unless you really know what you are doing! Valid languages: %s"\
             % (configuration.short_title, ', '.join(configuration.scriptlanguages)),
        'Example': 'sh',
        'Type': 'string',
        'Value': configuration.scriptlanguages[0],
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('JOBTYPE', {
        'Title': 'Job Type',
        'Description': "Specifies which types of jobs the resource accepts. A job can be of type 'interactive', 'batch' or 'bulk' and the keyword 'all' is provided to allow all types. Interactive jobs are executed on a resource but with the graphical display forwarded to the MiG display of the user. Batch jobs are executed in a headless mode and can not use graphical output. Bulk jobs are like batch jobs, but additionally allow concurrent execution of other bulk jobs belonging to the same user. I.e. a bulk of multiple jobs running on the same resource at the same time, as long as the resource can provide the requested job resources (cpucount, nodecount, memory, disk). This particular server supports the following jobtypes: %s"\
             % ', '.join(configuration.jobtypes),
        'Example': 'all',
        'Type': 'string',
        'Value': configuration.jobtypes[0],
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('ENFORCELIMITS', {
        'Title': 'Enforce Job Limits',
        'Description': 'An optional space-separated list of job limits to explicitly enforce in the job execution environment. Each entry is a method and limit like e.g. ULIMIT_CPUTIME to enable ulimit to terminate the job if it reaches the requested CPUTIME (i.e. CPUTIME * CPUCOUNT seconds of CPU use). Similarly limits on MEMORY and DISK can be enforced with ULIMIT_MEMORY and ULIMIT_DISK respectively. Finally ULIMIT_PROCESSES puts a cap on the number of proceses the job may spawn. All four limits are enabled by default, so set to a string without one or more of them to disable enforcement of some limits.',
        'Example': 'ULIMIT_PROCESSES ULIMIT_CPUTIME',
        'Type': 'string',
        'Value': 'ULIMIT_PROCESSES ULIMIT_CPUTIME ULIMIT_MEMORY ULIMIT_DISK',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('NODECOUNT', {
        'Title': 'Total Node Count',
        'Description': 'Number of total nodes on the resource.',
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('CPUCOUNT', {
        'Title': 'CPU Count per Node',
        'Description': "Number of CPU's on each execution node.",
        'Example': '4',
        'Type': 'int',
        'Value': 1,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('MEMORY', {
        'Title': 'Memory per Node (MB)',
        'Description': 'Amount of memory available on each execution node on the resource. The amount is specified in megabytes ',
        'Example': '2048',
        'Type': 'int',
        'Value': 1024,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('DISK', {
        'Title': 'Disk per Node (GB)',
        'Description': 'Amount of disk space available on each node on the resource. The amount is specified in gigabytes and the default is zero.',
        'Example': '10',
        'Type': 'int',
        'Value': 0,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('ARCHITECTURE', {
        'Title': 'CPU Architecture of the Nodes',
        'Description': "The CPU architecture of the execution nodes.",
        'Example': 'Valid architectures: %s'\
             % configuration.architectures,
        'Type': 'string',
        'Value': configuration.architectures[0],
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('RUNTIMEENVIRONMENT', {
        'Title': 'Runtime Environments on the Nodes',
        'Description': 'Runtimeenvironments available on the resource.\nInformation about all available runtime environments and their required variables are available at the Runtime Envs page.',
        'Example': '''name: LOCALDISK
name: GENERECON-2.1.3
GENERECON_HOME=/home/miguser/GeneRecon
GUILE_LOAD_PATH=$GENERECON_HOME''',
        'Type': 'configruntimeenvironment',
        'Value': [],
        'Editor': 'custom',
        'Required': False,
        }))
    specs.append(('FRONTENDLOG', {
        'Title': '%s Frontend Log File' % configuration.short_title,
        'Description': 'Name of the %s log file for the frontend.'\
                        % configuration.short_title,
        'Example': '/home/miguser/frontend.log',
        'Type': 'string',
        'Value': 'frontend.log',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('CURLLOG', {
        'Title': '%s cURL Log File' % configuration.short_title,
        'Description': 'Name of the %s log file for the cURL commands on the frontend.'\
                        % configuration.short_title,
        'Example': '/home/miguser/curllog',
        'Type': 'string',
        'Value': '/dev/null',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('SSHMULTIPLEX', {
        'Title': 'SSH Connection Sharing',
        'Description': 'Enable sharing of multiple SSH sessions over a single network connection. This can significantly speed up communication with the resource, if the resource supports session multiplexing. If unset or 0 multiplexing is disabled, otherwise it will be attempted (Just leave it unset if in doubt).',
        'Example': 'True',
        'Type': 'boolean',
        'Value': False,
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('LRMSTYPE', {
        'Title': 'Type of Local Resource Management System (LRMS)',
        'Description': 'Specifies the type of Local Resource Management System (LRMS). Simple resources generally use native execution to simply fork a new job subprocess whereas clusters and super computers tend to rely on a batch system like PBS or SGE to manage job processes. The type setting is used to decide if the remaining LRMS* settings are used to manage jobs. The default is Native execution where they are ignored because jobs are only running in the foreground, completely eliminating the need to submit or query progress. For each type there is a plain version and an X-execution-leader version: The former uses a model where each execution node on the resource is handled by a dedicated process. As the number of execution nodes grows this may become a resource bottleneck, and in that case the X-execution-leader version may be more efficient, because it handles all execution nodes in a single leader process. This is known to severely lessen the load on cluster frontends where the user home directories are located on a NFS mounted file system. Please note that the PBS and SGE flavors are now deprecated because they are no longer handled differently from the replacement general Batch flavors. So simply use one of the Batch modes instead of PBS or SGE flavors and request/download the appropriate LRMS helper scripts from mig/resource/lrms-scripts/ directory in the source code.',
        'Example': 'Batch',
        'Type': 'string',
        'Value': 'Native',
        'Editor': 'select',
        'Required': False,
        }))
    specs.append(('LRMSDELAYCOMMAND', {
        'Title': 'LRMS Execution Delay Command',
        'Description': 'Specifies the command used to find and print the batch job execution delay estimate (only used if the resource uses a batch system). The specified command is called right before requesting a new job. Three helper environment variables MIG_MAXNODES, MIG_MAXSECONDS and MIG_SUBMITUSER are available. It should return (print) only the expected number of seconds a job with MIG_MAXNODES nodes, MIG_MAXSECONDS seconds of walltime and submitted by MIG_SUBMITUSER will have to wait in the queue before execution. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/queue_delay.sh',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('LRMSSUBMITCOMMAND', {
        'Title': 'LRMS Submit Job Command',
        'Description': 'Specifies the command used to submit batch jobs (only if the resource uses a batch system). All job requirements are available in environment variables, so that the command can submit the job with appropriate resources. Thus the variables MIG_JOBNODECOUNT, MIG_JOBCPUCOUNT, MIG_JOBCPUTIME, MIG_JOBMEMORY and MIG_JOBDISK hold the requested nodecount, cpucount, cputime in seconds, memory in MB and disk in GB for the submit command to use. Furthermore the MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER will always hold a unique name for the job, the path to the job files, the name of the execution node and the local username. In case the local LRMS requires additional flags to schedule the jobs only to suitable nodes, those options can also be included here (e.g. qsub -l arch=i686). In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/submit_job.sh',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('LRMSREMOVECOMMAND', {
        'Title': 'LRMS Remove Job Command',
        'Description': 'Specifies the command used to remove submitted batch jobs (only used if the resource uses a batch system). To help locating the correct job the MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER will always hold a unique name for the job, the path to the job files, the name of the execution node and the local username. If the submit command includes flags to label jobs with MIG_JOBNAME and they are submitted by MIG_SUBMITUSER, those fields can be used to identify the job again here. Any additional LRMS flags (e.g. qdel -l arch=i686) for finer control over scheduling can be added here, too. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.',
        'Example': '/path/to/remove_job.sh',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('LRMSDONECOMMAND', {
        'Title': 'LRMS Query Job Command',
        'Description': 'Specifies the command used to query if a submitted batch job is done (only used if the resource uses a batch system). The specified command is called repeatedly after submitting the %s job to the LRMS and should return 0 only when the job is done and the result can be delivered. The usual helper environment variables MIG_JOBNAME, MIG_JOBDIR, MIG_EXENODE and MIG_SUBMITUSER are available to help querying the status of the right job. If the submit command includes flags to label jobs with MIG_JOBNAME and they are submitted by MIG_SUBMITUSER, those fields can be used to identify the job again here. In most cases this is easier to wrap in a script on the resource and thus only supply the absolute path to the (read-only) script here.'\
                        % configuration.short_title,
        'Example': '/path/to/query_done.sh',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('PUBLICNAME', {
        'Title': 'Public Name',
        'Description': 'Specifies a public name or alias to display along with the resource identity in monitors and in verbose job status for finished jobs executed there.',
        'Example': 'EightByEight',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('PUBLICINFO', {
        'Title': 'Public Information',
        'Description': 'Optional extra free text information describing the resource.',
        'Example': 'Eight core host with OpenCL capable GPU',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('SANDBOX', {
        'Title': 'Sandbox',
        'Description': 'Specifies whether resource is a sandbox. If 0 or false, the resource is not a sandbox, if 1 or true, the resource is a sandbox. Sandbox resources are less trusted and thus can only handle explicitly allowed sandbox jobs.',
        'Example': '0',
        'Type': 'boolean',
        'Value': False,
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('SANDBOXKEY', {
        'Title': 'Sandbox Identifier',
        'Description': 'Specifies the secret sandboxkey for a sandbox.',
        'Example': '2AD32342423421111',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('MAXDOWNLOADBANDWIDTH', {
        'Title': 'Maximum Download Bandwidth (KB/s)',
        'Description': 'Specifies the max download bandwidth (in kB) the resource is allowed to use. If 0 or unset, there is no limit.',
        'Example': '2048',
        'Type': 'int',
        'Value': 0,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('MAXUPLOADBANDWIDTH', {
        'Title': 'Maximum Upload Bandwidth (KB/s)',
        'Description': 'Specifies the max upload bandwidth (in kB) the resource is allowed to use. If 0 or unset, there is no limit.',
        'Example': '512',
        'Type': 'int',
        'Value': 0,
        'Editor': 'input',
        'Required': False,
        }))
    specs.append(('PLATFORM', {
        'Title': 'Platform',
        'Description': 'Specifies a platform architecture this resource supports.',
        'Example': 'ONE-CLICK',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('ADMINEMAIL', {
        'Title': 'Administrator E-mail',
        'Description': 'A space separated list of email addresses of resource administrators - used to notify about internal errors.',
        'Example': 'admin@yourdomain.org',
        'Type': 'string',
        'Value': '',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('MINPRICE', {
        'Title': 'Minimum Job Price Function',
        'Description': 'Minimum price specifies a function of multiple variables for calculatint the minimum acceptable price for executing a particular job at a particular point in time. This is only used if full job accounting is enabled.',
        'Example': '40',
        'Type': 'string',
        'Value': '0',
        'Editor': 'invisible',
        'Required': False,
        }))
    specs.append(('EXECONFIG', {
        'Title': 'Execution Units',
        'Description': 'Configuration for the execution resources: please refer to the Execution node section.',
        'Example': 'Example not available',
        'Type': 'execonfig',
        'Value': [],
        'Editor': 'invisible',
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
        }))
    specs.append(('STORECONFIG', {
        'Title': 'Storage Units',
        'Description': 'Configuration for the storage resources: please refer to the Storage node section.',
        'Example': 'Example not available',
        'Type': 'storeconfig',
        'Value': [],
        'Editor': 'invisible',
        'Required': False,
        'Sublevel': True,
        'Sublevel_required': [
            'name',
            'storage_disk',
            'storage_protocol',
            'storage_port',
            'storage_user',
            'storage_node',
            'storage_dir',
            'start_command',
            'status_command',
            'stop_command',
            'clean_command',
            'shared_fs',
            'vgrid',
            ],
        'Sublevel_optional': [],
        }))
    return specs

def get_exenode_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """
    
    specs = []
    specs.append(('name', {
        'Title': 'Execution Node Identifier',
        'Description': 'Execution node names are symbolic names to identify %(site)s execution nodes. This can be any text string as long as it is unique among the execution nodes of the resource. The %(site)s execution nodes do not necessarily have to map to physical hosts in a one-to-one way.'\
                        % { 'site' : configuration.short_title },
        'Example': 'node01',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('cputime', {
        'Title': 'CPU/Wall Time (s)',
        'Description': 'The maximum number of seconds of walltime each %s job is allowed to use on an execution node.'\
                        % configuration.short_title,
        'Example': '86400',
        'Type': 'int',
        'Value': 3600,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('nodecount', {
        'Title': 'Node Count',
        'Description': 'The number of actual computation nodes associated with a %(site)s execution node. For simple resources or clusters exposing each node individually this is just one. However, the resource can map multiple physical nodes to a single %(site)s execution node through an LRMS or a cluster frontend, so it may bind more than one actual node to each %(site)s execution node.'\
                        % { 'site' : configuration.short_title} ,
        'Example': '128',
        'Type': 'int',
        'Value': 1,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('execution_precondition', {
        'Title': 'Precondition for Job Execution',
        'Description': "Command used to decide if execution node should request a job or wait for later. This can be used to delay the job request for execution nodes under heavy load. If the command returns a non-zero exit code the node will run a sleep job before trying again. Otherwise it will request a job as usual. An example is to only request a job if the load average is below 1.0 . Please note that this command is not allowed to contain single quotes (') because it will interfere with the way it is called.",
        'Example': 'uptime | grep "load average: 0"',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('prepend_execute', {
        'Title': 'Job Setup',
        'Description': "If the execution node should perform a task before the execution of the %s job or prefix the job command with another command, it should be specified here. This can be used to run jobs with a modified scheduling priority ('nice')."\
                        % configuration.short_title,
        'Example': 'nice',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('exehostlog', {
        'Title': '%s Execution Log File' % configuration.short_title,
        'Description': 'Name of the main log file for the execution node.',
        'Example': '/home/miguser/exehost.log',
        'Type': 'string',
        'Value': 'exehost.log',
        'Editor': 'invisible',
        'Required': True,
        }))
    specs.append(('joblog', {
        'Title': '%s Job Log File' % configuration.short_title,
        'Description': 'Name of the job log file for the execution node.',
        'Example': '/home/miguser/job.log',
        'Type': 'string',
        'Value': 'job.log',
        'Editor': 'invisible',
        'Required': True,
        }))
    specs.append(('execution_user', {
        'Title': 'Execution Node %s User' % configuration.short_title,
        'Description': 'The local user to login as on the node(s) associated with this %(site)s execution node. In most cases this is identical to the global resource %(site)s user. When using the local start/status/stop/clean commands this field is ignored.'\
                        % { 'site' : configuration.short_title },
        'Example': 'miguser',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('execution_node', {
        'Title': 'Execution Node',
        'Description': 'The local node associated with this %s execution unit. For clusters exposed as single nodes and NAT firewalled resources this field contains the hostname of one of the actual hosts behind the frontend. When using the local start/status/stop/clean commands this field is ignored.'\
                        % configuration.short_title,
        'Example': 'node01',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('execution_dir', {
        'Title': 'Execution Node Working Directory',
        'Description': 'Path to the working directory of the execution node.',
        'Example': '/home/miguser/MiG/mig_exe/myresource.org.0/node01/',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('start_command', {
        'Title': 'Start Execution Node',
        'Description': "The command which is used to start the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through SSH to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('status_command', {
        'Title': 'Query Execution Node',
        'Description': "The command which is used to query status of the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through SSH to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('stop_command', {
        'Title': 'Stop Execution Node',
        'Description': "The command which is used to stop the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through SSH to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('clean_command', {
        'Title': 'Clean Execution Node',
        'Description': "The command which is used to clean the resource execution node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the execution node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the execution node management process is executed through SSH to the host specified in the execution node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('continuous', {
        'Title': 'Continuous Execution',
        'Description': 'If the execution node should continuously take jobs (i.e. True) or only run a single job when started (i.e. False). The default setting is to run in continuous mode, but some applications such as The %s ScreenSaver Science require single run mode.'\
                        % configuration.short_title,
        'Example': 'False',
        'Type': 'boolean',
        'Value': True,
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('shared_fs', {
        'Title': 'Shared File System',
        'Description': 'If the frontend and execution node shares the same file system (i.e. True), so that frontend and execution management processes can communicate directly through files in the %s user home directory. If this is not the case (i.e. False) the communication will use SSH to communicate, but this is slightly less efficient and requires additional setup of local login access without password. To be more precise the frontend must be able to login as the execution user on the execution node and vice versa without any user input (e.g. by using SSH keys with an empty passphrase).'\
                        % configuration.short_title,
        'Example': 'False',
        'Type': 'boolean',
        'Value': True,
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('vgrid', {
        'Title': 'VGrid Participation',
        'Description': 'Which VGrids should the resource accept jobs from? Please note that the corresponding VGrid owners must add the resource to the VGrid first. The raw format is a comma separated list of VGrid names.',
        'Example': 'Generic, MyVGrid',
        'Type': 'multiplestrings',
        'Value': [default_vgrid],
        'Editor': 'select',
        'Required': True,
        }))
    return specs

def get_storenode_specs(configuration):
    """Return an ordered list of (keywords, spec) tuples. The order is
    used for configuration order consistency.
    """

    specs = []
    specs.append(('name', {
        'Title': 'Storage Node Identifier',
        'Description': 'Storage node names are symbolic names to identify %(site)s storage nodes. This can be any text string as long as it is unique among the storage nodes of the resource. The %(site)s storage nodes do not necessarily have to map to physical hosts in a one-to-one way.'\
                        % { 'site' : configuration.short_title },
        'Example': 'node01',
        'Type': 'string',
        'Value': 'localhost',
        'Editor': 'custom',
        'Required': True,
        })) 
    specs.append(('storage_disk', {
        'Title': 'Storage Node Disk (GB)',
        'Description': 'Amount of disk space available on the storage node. The amount is specified in gigabytes and the default is 10.',
        'Example': '1000',
        'Type': 'int',
        'Value': 10,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('storage_protocol', {
        'Title': 'Access Protocol',
        'Description': 'Which protocol to use for accessing the storage on the node. Currently only supports sftp.',
        'Example': 'sftp',
        'Type': 'string',
        'Value': 'sftp',
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('storage_port', {
        'Title': 'Access Port',
        'Description': 'Which port to use for accessing the storage on the node.',
        'Example': '2222',
        'Type': 'int',
        'Value': 22,
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('storage_user', {
        'Title': 'Storage Node %s User' % configuration.short_title,
        'Description': 'The local user to login as on the node(s) associated with this %(site)s storage node. In most cases this is identical to the global resource %(site)s user.'\
                        % { 'site' : configuration.short_title },
        'Example': 'miguser',
        'Type': 'string',
        'Value': '',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('storage_node', {
        'Title': 'Storage Node',
        'Description': 'The local node associated with this %s storage unit. For clusters exposed as single nodes and NAT firewalled resources this field contains the hostname of one of the actual hosts behind the frontend. When using the local start/status/stop/clean commands this field is ignored.'\
                        % configuration.short_title,
        'Example': 'node01',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('storage_dir', {
        'Title': 'Export Directory',
        'Description': 'Path to export to selected VGrids on the %s server.'\
                        % configuration.short_title,
        'Example': '/home/miguser/MiG/mig_exe/myresource.org.0/node01/',
        'Type': 'string',
        'Value': '',
        'Editor': 'custom',
        'Required': True,
        }))
    specs.append(('start_command', {
        'Title': 'Start Storage Node',
        'Description': "The command which is used to start the resource storage node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the storage node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the storage node management process is executed through SSH to the host specified in the storage node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('status_command', {
        'Title': 'Query Storage Node',
        'Description': "The command which is used to query status of the resource storage node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the storage node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the storage node management process is executed through SSH to the host specified in the storage node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('stop_command', {
        'Title': 'Stop Storage Node',
        'Description': "The command which is used to stop the resource storage node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the storage node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the storage node management process is executed through SSH to the host specified in the storage node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('clean_command', {
        'Title': 'Clean Storage Node',
        'Description': "The command which is used to clean the resource storage node. If unsure use either of the keywords 'local' or 'default'. The 'local' keyword means that the storage node management process runs locally on the frontend host and it should be used if the resource is a single host or if it is a cluster or super computer where all jobs are managed by an LRMS from the frontend. The 'default' keyword on the other hand means that the storage node management process is executed through SSH to the host specified in the storage node setting, which allows the actual executing resources to be located behind a firewall or gateway frontend.",
        'Example': 'local',
        'Type': 'string',
        'Value': 'default',
        'Editor': 'input',
        'Required': True,
        }))
    specs.append(('shared_fs', {
        'Title': 'Shared File System',
        'Description': 'If the frontend and storage node shares the same file system (i.e. True), so that frontend and storage management processes can communicate directly through files in the %s user home directory. If this is not the case (i.e. False) the communication will use SSH to communicate, but this is slightly less efficient and requires additional setup of local login access without password. To be more precise the frontend must be able to login as the storage user on the storage node and vice versa without any user input (e.g. by using SSH keys with an empty passphrase).'\
                        % configuration.short_title,
        'Example': 'False',
        'Type': 'boolean',
        'Value': True,
        'Editor': 'select',
        'Required': True,
        }))
    specs.append(('vgrid', {
        'Title': 'VGrid Participation',
        'Description': 'Which VGrids should the resource accept jobs from? Please note that the corresponding VGrid owners must add the resource to the VGrid first. The raw format is a comma separated list of VGrid names.',
        'Example': 'Generic, MyVGrid',
        'Type': 'multiplestrings',
        'Value': [default_vgrid],
        'Editor': 'select',
        'Required': True,
        }))
    return specs


def get_resource_keywords(configuration):
    """Return mapping between resource keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_resource_specs(configuration))


# TODO: replace all get_keywords_dict() calls with get_resource_keywords and drop

def get_keywords_dict(configuration):
    """Legacy function now handled by get_resource_keywords"""

    return get_resource_keywords(configuration)

def get_exenode_keywords(configuration):
    """Return mapping between execution node keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_exenode_specs(configuration))

def get_storenode_keywords(configuration):
    """Return mapping between storage node keywords and their specs"""

    # create the keywords in a single dictionary

    return dict(get_storenode_specs(configuration))

