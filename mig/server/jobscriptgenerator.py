#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobscriptgenerator - [insert a few words of module description on this line]
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

"""Job script generator"""

import os
import time
from binascii import hexlify

import genjobscriptpython
import genjobscriptsh
import genjobscriptjava
from shared.confparser import get_resource_config_dict
from shared.ssh import copy_file_to_resource
from shared.fileio import write_file, pickle, make_symlink


def create_empty_job(
    unique_resource_name,
    exe,
    request_cputime,
    sleep_factor,
    localjobname,
    execution_delay,
    configuration,
    logger,
    ):

    job_dict = {'': ''}
    helper_dict_filename = configuration.resource_home\
         + unique_resource_name + '/empty_job_helper_dict.' + exe

    max_cputime = int(request_cputime)
    scaled_cputime = int(float(configuration.cputime_for_empty_jobs)
                          * sleep_factor)
    if scaled_cputime > max_cputime:
        cputime = max_cputime
        sleep_time = int(0.8 * cputime)
    else:
        cputime = scaled_cputime
        sleep_time = \
            int(float(configuration.sleep_period_for_empty_jobs)
                 * sleep_factor)

    logger.info('request_cputime: %d, sleep_factor: %.1f, cputime: %d, sleep time: %d'
                , max_cputime, sleep_factor, cputime, sleep_time)
    job_id = configuration.empty_job_name + '.' + unique_resource_name\
         + '.' + exe + '.' + localjobname

    job_dict['JOB_ID'] = job_id

    # sessionid = configuration.empty_job_name

    sleep_cmd = 'sleep ' + str(sleep_time)
    job_dict['EXECUTE'] = [sleep_cmd]
    job_dict['INPUTFILES'] = []
    job_dict['OUTPUTFILES'] = ''
    job_dict['ARGUMENTS'] = ''
    job_dict['EXECUTABLES'] = ''
    job_dict['CPUTIME'] = str(cputime)
    job_dict['EXECUTION_DELAY'] = str(execution_delay)
    job_dict['ENVIRONMENT'] = ''
    job_dict['RUNTIMEENVIRONMENT'] = []
    job_dict['MAXPRICE'] = '0'
    job_dict['JOBNAME'] = 'empty job'
    user_cert = configuration.empty_job_name
    job_dict['USER_CERT'] = user_cert

    # create mRSL file only containing the unique_resource_name.
    # This is used when the .status file from the empty job is
    # uploaded, to find the unique name of the resource to be able
    # to start the exe again if continuous is True
    # if not os.path.isfile(helper_dict_filename):

    helper_dict = {}
    helper_dict['JOB_ID'] = job_id
    helper_dict['UNIQUE_RESOURCE_NAME'] = unique_resource_name
    helper_dict['EXE'] = exe
    helper_dict['IS_EMPTY_JOB_HELPER_DICT'] = True
    helper_dict['LOCALJOBNAME'] = localjobname

    pickle(helper_dict, helper_dict_filename, logger)

    return job_dict


def create_restart_job(
    unique_resource_name,
    exe,
    request_cputime,
    sleep_factor,
    localjobname,
    execution_delay,
    configuration,
    logger,
    ):
    """Wrapper to create a dummy job for forcing repeated restart of dead exes"""

    empty_job = create_empty_job(
        unique_resource_name,
        exe,
        request_cputime,
        sleep_factor,
        localjobname,
        execution_delay,
        configuration,
        logger,
        )
    empty_job['UNIQUE_RESOURCE_NAME'] = unique_resource_name
    empty_job['EXE'] = exe
    empty_job['LOCALJOBNAME'] = localjobname
    empty_job['STATUS'] = 'Restart exe failed dummy'
    empty_job['EXECUTING_TIMESTAMP'] = time.gmtime()
    empty_job['RESOURCE_CONFIG'] = None
    empty_job['SESSIONID'] = 'RESTARTFAILEDDUMMYID'
    empty_job['IOSESSIONID'] = 'RESTARTFAILEDDUMMYID'
    empty_job['EMPTY_JOB'] = True
    return empty_job


# Returns sessionid if successfull, None if NON-successfull


def create_job_script(
    unique_resource_name,
    exe,
    job,
    resource_config,
    localjobname,
    configuration,
    logger,
    ):

    job_dict = {'': ''}
    sessionid = hexlify(open('/dev/urandom').read(32))
    iosessionid = hexlify(open('/dev/urandom').read(32))
    helper_dict_filename = configuration.resource_home\
         + unique_resource_name + '/empty_job_helper_dict.' + exe

    # TODO: What decides that only these fields should be copied???
    #  Since job_dict is used to generate the job script we may very
    #  well loose some job fields here!

    job_dict['JOB_ID'] = job['JOB_ID']
    job_dict['EXECUTE'] = job['EXECUTE']
    job_dict['INPUTFILES'] = job['INPUTFILES']
    job_dict['OUTPUTFILES'] = job['OUTPUTFILES']
    job_dict['EXECUTABLES'] = job['EXECUTABLES']
    job_dict['CPUTIME'] = job['CPUTIME']
    job_dict['JOBNAME'] = job['JOBNAME']
    job_dict['ENVIRONMENT'] = job['ENVIRONMENT']
    job_dict['RUNTIMEENVIRONMENT'] = job['RUNTIMEENVIRONMENT']
    job_dict['MIGSESSIONID'] = sessionid
    job_dict['MIGIOSESSIONID'] = iosessionid

    if job.has_key('JOBTYPE'):
        job_dict['JOBTYPE'] = job['JOBTYPE']

    # ... Recently added missing fields here, but others may still be missing!
    # -Jonas

    for field in ['CPUCOUNT', 'NODECOUNT', 'MEMORY', 'DISK']:
        if job.has_key(field):
            job_dict[field] = job[field]

    if job_dict.has_key('MAXPRICE'):
        job_dict['MAXPRICE'] = job['MAXPRICE']
    else:
        job_dict['MAXPRICE'] = '0'
    user_cert = str(job['USER_CERT'])

    # if not job:

    if user_cert == configuration.empty_job_name:

        # create link to empty job

        linkdest_empty_job = helper_dict_filename
        linkloc_empty_job = configuration.sessid_to_mrsl_link_home\
             + sessionid + '.mRSL'
        make_symlink(linkdest_empty_job, linkloc_empty_job, logger)
    else:

        # link sessionid to mrsl file

        linkdest1 = configuration.mrsl_files_dir + user_cert + '/'\
             + str(job_dict['JOB_ID']) + '.mRSL'
        linkloc1 = configuration.sessid_to_mrsl_link_home + sessionid\
             + '.mRSL'
        make_symlink(linkdest1, linkloc1, logger)

    # link sessionid to job owners home directory

    linkdest2 = configuration.user_home + user_cert
    linkloc2 = configuration.webserver_home + sessionid
    make_symlink(linkdest2, linkloc2, logger)

    # link iosessionid to job owners home directory

    linkdest3 = configuration.user_home + user_cert
    linkloc3 = configuration.webserver_home + iosessionid
    make_symlink(linkdest3, linkloc3, logger)

    # link sessionid to .job file

    linkdest4 = configuration.mig_system_files + str(job_dict['JOB_ID'])\
         + '.job'
    linkloc4 = configuration.webserver_home + sessionid + '.job'
    make_symlink(linkdest4, linkloc4, logger)

    # link sessionid to .sendoutputfiles file

    linkdest4 = configuration.mig_system_files + str(job_dict['JOB_ID'])\
         + '.sendoutputfiles'
    linkloc4 = configuration.webserver_home + sessionid\
         + '.sendoutputfiles'
    make_symlink(linkdest4, linkloc4, logger)

    # link sessionid to .sendupdatefiles file

    linkdest5 = configuration.mig_system_files + str(job_dict['JOB_ID'])\
         + '.sendupdatefiles'
    linkloc5 = configuration.webserver_home + sessionid\
         + '.sendupdatefiles'
    make_symlink(linkdest5, linkloc5, logger)

    path_without_extension = configuration.resource_home\
         + unique_resource_name + '/' + localjobname
    job = gen_job_script(
        job_dict,
        resource_config,
        configuration,
        localjobname,
        path_without_extension,
        user_cert,
        exe,
        logger,
        )
    if not job:
        msg = \
            'job scripts were not generated. Perhaps you have specified an invalid SCRIPTLANGUAGE ? '
        print msg
        logger.error(msg)
        return (msg, None)

    inputfiles_path = path_without_extension + '.getinputfiles'

    # hack to ensure that a resource has a sandbox keyword

    if resource_config.has_key('SANDBOX'):
        if resource_config['SANDBOX'] == 1:

            # Copy file to webserver_home

            try:
                src = open(inputfiles_path, 'r')

                # RA TODO: change filename to something that
                # includes sessionid

                dest = open(configuration.webserver_home + localjobname
                             + '.getinputfiles', 'w')
                dest.write(src.read())
                src.close()
                dest.close()

                # ########## ATTENTION HACK TO MAKE JVM SANDBOXES WORK ########################################
                # This should be changed to use the (to be developed) RE pre/post processing framework       #
                # For now the user must have a jvm dir in his home dir where the classfiles is located       #
                # this should be changed so that the execution homepath can be specified in the mRSL jobfile #
                #                                                                                            #
                # Martin Rehr 08/09/06                                                                       #

                # If this is a oneclick job link the users jvm dir to
                # webserver_home/sandboxkey.oneclick
                # This is done because the client applet uses the
                # codebase from which it is originaly loaded
                # Therefore the codebase must be dynamicaly changed
                # for every job

                if resource_config.has_key('PLATFORM')\
                     and resource_config['PLATFORM'] == 'ONE-CLICK':

                    # A two step link is made.
                    # First sandboxkey.oneclick is made to point to
                    # sessiondid.jvm
                    # Second sessionid.jvm is set to point to
                    # USER_HOME/jvm
                    # This is done for security and easy cleanup,
                    # sessionid.jvm is cleaned up
                    # by the server upon job finish/timeout and
                    # thereby leaving no open entryes to the users
                    # jvm dir.

                    linkintermediate = configuration.webserver_home\
                         + sessionid + '.jvm'

                    if user_cert == configuration.empty_job_name:
                        linkdest = \
                            os.path.abspath(configuration.javabin_home)
                    else:
                        linkdest = configuration.user_home + user_cert\
                             + os.sep + 'jvm'

                    # Make link sessionid.jvm -> USER_HOME/jvm

                    make_symlink(linkdest, linkintermediate, logger)

                    linkloc = configuration.webserver_home\
                         + resource_config['SANDBOXKEY'] + '.oneclick'

                    # Remove previous symlink
                    # This must be done in a try/catch as the symlink,
                    # may be a dead link and 'if os.path.exists(linkloc):'
                    # will then return false, even though the link exists.

                    try:
                        os.remove(linkloc)
                    except:
                        pass

                    # Make link sandboxkey.oneclick -> sessionid.jvm

                    make_symlink(linkintermediate, linkloc, logger)
            except Exception, err:

                    # ######### End JVM SANDBOX HACK ###########

                msg = "File '%s' was not copied to the webserver home."\
                     % inputfiles_path
                print '\nERROR: ' + str(err)
                logger.error(msg)
                return (msg, None)

            return (sessionid, iosessionid)

    # Copy file to the resource

    if not copy_file_to_resource(inputfiles_path,
                                 os.path.basename(inputfiles_path),
                                 resource_config, logger):
        logger.error('File was not copied to the resource: '
                      + inputfiles_path)
    else:

        # file was sent, delete it

        try:
            os.remove(inputfiles_path)
        except:
            logger.error('could not remove ' + inputfiles_path)
    return (sessionid, iosessionid)


def gen_job_script(
    job_dictionary,
    resource_config,
    configuration,
    localjobname,
    path_without_extension,
    user_cert,
    exe,
    logger,
    ):

    script_language = resource_config['SCRIPTLANGUAGE']
    if not script_language in configuration.scriptlanguages:
        print 'Unknown script language! (conflict with configuration.scriptlanguages?) %s not in %s'\
             % (script_language, configuration.scriptlanguages)
        return False

    if script_language == 'python':
        generator = genjobscriptpython.GenJobScriptPython(
            job_dictionary,
            resource_config,
            exe,
            configuration.migserver_https_url,
            localjobname,
            path_without_extension,
            )
    elif script_language == 'sh':
        generator = genjobscriptsh.GenJobScriptSh(
            job_dictionary,
            resource_config,
            exe,
            configuration.migserver_https_url,
            localjobname,
            path_without_extension,
            )
    elif script_language == 'java':
        generator = genjobscriptjava.GenJobScriptJava(job_dictionary,
                resource_config, configuration.migserver_https_url,
                localjobname, path_without_extension)
    else:
        print 'Unknown script language! (is in configuration.scriptlanguages but not in jobscriptgenerator) %s '\
             % script_language
        return False

    # String concatenation in python: [X].join is much faster
    # than repeated use of s += strings

    getinputfiles_array = []
    getinputfiles_array.append(generator.script_init())
    getinputfiles_array.append(generator.comment('print start'))
    getinputfiles_array.append(generator.print_start('get input files'))
    getinputfiles_array.append(generator.comment('init log'))
    getinputfiles_array.append(generator.init_io_log())
    getinputfiles_array.append(generator.comment('get special inputfiles'
                               ))
    getinputfiles_array.append(generator.get_special_input_files('get_special_status'
                               ))
    getinputfiles_array.append(generator.log_io_status('get_special_input_files'
                               , 'get_special_status'))
    getinputfiles_array.append(generator.print_on_error('get_special_status'
                               , '0',
                               'failed to fetch special input files!'))
    getinputfiles_array.append(generator.comment('get input files'))
    getinputfiles_array.append(generator.get_input_files('get_input_status'
                               ))
    getinputfiles_array.append(generator.log_io_status('get_input_files'
                               , 'get_input_status'))
    getinputfiles_array.append(generator.print_on_error('get_input_status'
                               , '0', 'failed to fetch input files!'))
    getinputfiles_array.append(generator.comment('get executables'))
    getinputfiles_array.append(generator.get_executables('get_executables_status'
                               ))
    getinputfiles_array.append(generator.log_io_status('get_executables'
                               , 'get_executables_status'))
    getinputfiles_array.append(generator.print_on_error('get_executables_status'
                               , '0',
                               'failed to fetch executable files!'))
    # user_cert equals empty_job_name for sleep jobs
    getinputfiles_array.append(generator.generate_output_filelists(
        (user_cert == configuration.empty_job_name), 'generate_output_filelists'))
    getinputfiles_array.append(generator.print_on_error('generate_output_filelists'
                               , '0',
                               'failed to generate output filelists!'))
    getinputfiles_array.append(generator.generate_input_filelist('generate_input_filelist'
                               ))
    getinputfiles_array.append(generator.print_on_error('generate_input_filelist'
                               , '0',
                               'failed to generate input filelist!'))
    getinputfiles_array.append(generator.generate_iosessionid_file('generate_iosessionid_file'
                               ))
    getinputfiles_array.append(generator.print_on_error('generate_iosessionid_file'
                               , '0',
                               'failed to generate iosessionid file!'))

    getinputfiles_array.append(generator.total_status(['get_special_status'
                               , 'get_input_status',
                               'get_executables_status',
                               'generate_output_filelists'],
                               'total_status'))
    getinputfiles_array.append(generator.exit_on_error('total_status',
                               '0', 'total_status'))
    getinputfiles_array.append(generator.comment('exit script'))
    getinputfiles_array.append(generator.exit_script('0',
                               'get input files'))

    job_array = []
    job_array.append(generator.script_init())
    job_array.append(generator.print_start('job'))
    job_array.append(generator.comment('TODO: switch to job directory here'
                     ))
    job_array.append(generator.comment('make sure job status files exist'
                     ))
    job_array.append(generator.create_files([job_dictionary['JOB_ID']
                      + '.stdout', job_dictionary['JOB_ID'] + '.stderr'
                     , job_dictionary['JOB_ID'] + '.status']))
    job_array.append(generator.init_status())
    job_array.append(generator.comment('chmod +x'))
    job_array.append(generator.chmod_executables('chmod_status'))
    job_array.append(generator.print_on_error('chmod_status', '0',
                     'failed to make one or more EXECUTABLES executable'
                     ))
    job_array.append(generator.comment('set environments'))
    job_array.append(generator.set_environments('env_status'))
    job_array.append(generator.print_on_error('env_status', '0',
                     'failed to initialize one or more ENVIRONMENTs'))
    job_array.append(generator.comment('set runtimeenvironments'))
    job_array.append(generator.set_runtime_environments(resource_config['RUNTIMEENVIRONMENT'
                     ], 're_status'))
    job_array.append(generator.print_on_error('re_status', '0',
                     'failed to initialize one or more RUNTIMEENVIRONMENTs'
                     ))
    job_array.append(generator.comment('execute!'))
    job_array.append(generator.execute('EXECUTING: ', '--Exit code:'))
    job_array.append(generator.comment('exit script'))
    job_array.append(generator.exit_script('0', 'job'))

    sendoutputfiles_array = []

    # We need to make sure that curl failures lead to retry while
    # missing output (from say a failed job) is logged but
    # ignored in relation to sendoutputfiles success.

    sendoutputfiles_array.append(generator.print_start('send output files'
                                 ))
    sendoutputfiles_array.append(generator.init_io_log())
    sendoutputfiles_array.append(generator.comment('check output files'
                                 ))
    sendoutputfiles_array.append(generator.output_files_missing('missing_counter'
                                 ))
    sendoutputfiles_array.append(generator.log_io_status('output_files_missing'
                                 , 'missing_counter'))
    sendoutputfiles_array.append(generator.print_on_error('missing_counter'
                                 , '0', 'missing output files'))
    sendoutputfiles_array.append(generator.comment('send output files'))
    sendoutputfiles_array.append(generator.send_output_files('send_output_status'
                                 ))
    sendoutputfiles_array.append(generator.log_io_status('send_output_files'
                                 , 'send_output_status'))
    sendoutputfiles_array.append(generator.print_on_error('send_output_status'
                                 , '0',
                                 'failed to send one or more outputfiles'
                                 ))
    sendoutputfiles_array.append(generator.exit_on_error('send_output_status'
                                 , '0', 'send_output_status'))

    sendoutputfiles_array.append(generator.comment('send io files'))
    sendoutputfiles_array.append(generator.send_io_files([job_dictionary['JOB_ID'
                                 ] + '.stdout', job_dictionary['JOB_ID']
                                  + '.stderr'], 'send_io_status'))
    sendoutputfiles_array.append(generator.log_io_status('send_io_files'
                                 , 'send_io_status'))
    sendoutputfiles_array.append(generator.print_on_error('send_io_status'
                                 , '0',
                                 'failed to send one or more IO files'))
    sendoutputfiles_array.append(generator.exit_on_error('send_io_status'
                                 , '0', 'send_io_status'))
    sendoutputfiles_array.append(generator.comment('send status files'))
    sendoutputfiles_array.append(generator.send_status_files([job_dictionary['JOB_ID'
                                 ] + '.io-status'],
                                 'send_io_status_status'))
    sendoutputfiles_array.append(generator.print_on_error('send_io_status_status'
                                 , '0', 'failed to send io-status file'
                                 ))
    sendoutputfiles_array.append(generator.exit_on_error('send_io_status_status'
                                 , '0', 'send_io_status_status'))

    # Please note that .status upload marks the end of the
    # session and thus it must be the last uploaded file.

    sendoutputfiles_array.append(generator.send_status_files([job_dictionary['JOB_ID'
                                 ] + '.status'], 'send_status_status'))
    sendoutputfiles_array.append(generator.print_on_error('send_status_status'
                                 , '0', 'failed to send status file'))
    sendoutputfiles_array.append(generator.exit_on_error('send_status_status'
                                 , '0', 'send_status_status'))

    # Note that ID.sendouputfiles is called from frontend_script
    # so exit on failure can be handled there.

    sendoutputfiles_array.append(generator.comment('exit script'))
    sendoutputfiles_array.append(generator.exit_script('0',
                                 'send output files'))

    sendupdatefiles_array = []

    # We need to make sure that curl failures lead to retry while
    # missing output (from say a failed job) is logged but
    # ignored in relation to sendupdatefiles success.

    sendupdatefiles_array.append(generator.print_start('send update files'
                                 ))
    sendupdatefiles_array.append(generator.init_io_log())

    sendupdatefiles_array.append(generator.comment('send io files'))
    sendupdatefiles_array.append(generator.send_io_files([job_dictionary['JOB_ID'
                                 ] + '.stdout', job_dictionary['JOB_ID']
                                  + '.stderr', job_dictionary['JOB_ID']
                                  + '.io-status'], 'send_io_status'))
    sendupdatefiles_array.append(generator.log_io_status('send_io_files'
                                 , 'send_io_status'))
    sendupdatefiles_array.append(generator.print_on_error('send_io_status'
                                 , '0',
                                 'failed to send one or more IO files'))
    sendupdatefiles_array.append(generator.exit_on_error('send_io_status'
                                 , '0', 'send_io_status'))

    sendupdatefiles_array.append(generator.comment('exit script'))
    sendupdatefiles_array.append(generator.exit_script('0',
                                 'send update files'))

    # clean up must be done with SSH (when the .status file
    # has been uploaded): Job script can't safely/reliably clean up
    # after itself because of possible user interference.

    if job_dictionary.has_key('JOBTYPE') and job_dictionary['JOBTYPE'
            ].lower() == 'interactive':

        # interactive jobs have a .job file just containing a curl
        # call to the MiG servers cgi-sid/requestinteractivejob
        # and the usual .job is instead called .interactivejob and
        # is SCP'ed and started by SSH in the requestinteractive.py
        # script

        logger.error('jobtype: interactive')
        interactivejobfile = generator.script_init() + '\n'\
             + generator.request_interactive() + '\n'\
             + generator.exit_script('0', 'interactive job')

        # write the small file containing the requestinteractivejob.py
        # call as .job

        write_file(interactivejobfile, configuration.mig_system_files
                    + job_dictionary['JOB_ID'] + '.job', logger)

        # write the usual .job file as .interactivejob

        write_file('\n'.join(job_array), configuration.mig_system_files
                    + job_dictionary['JOB_ID'] + '.interactivejob',
                   logger)
        print interactivejobfile
    else:

        # write files

        write_file('\n'.join(job_array), configuration.mig_system_files
                    + job_dictionary['JOB_ID'] + '.job', logger)

    write_file('\n'.join(getinputfiles_array),
               path_without_extension + '.getinputfiles', logger)
    write_file('\n'.join(sendoutputfiles_array),
               configuration.mig_system_files + job_dictionary['JOB_ID']
                + '.sendoutputfiles', logger)
    write_file('\n'.join(sendupdatefiles_array),
               configuration.mig_system_files + job_dictionary['JOB_ID']
                + '.sendupdatefiles', logger)

    return True


