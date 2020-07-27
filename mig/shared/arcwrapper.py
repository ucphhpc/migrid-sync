#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# arcwrapper: main ARC middleware wrapper module
# Copyright (C) 2009-2015  The MiG Project lead by Brian Vinter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# -- END_HEADER ---
#

# Original copyright notice follows:
# Copyright (C) 2006-2009 Jonas Lindemann
#
# this version:
# (C) 2009 Jost Berthold, grid.dk
#  adapted to usage inside a MiG framework
#


"""ARC middleware interface module."""
from __future__ import absolute_import

import os
import sys
import string
import commands
import threading
import tempfile

from .shared.safeeval import subprocess_popen, subprocess_pipe

# MiG utilities:
from .shared.conf import get_configuration_object
config = get_configuration_object()
logger = config.logger

# Avoid massive log spam when unconditionally importing arcwrapper in other
# modules like jobstatus and jobscriptgenerator
if not config.arc_clusters:
    raise Exception('ignoring arcwrapper import without ARC enabled!')

# to make this succeed: 
# install nordugrid-arc-client and nordugrid-arc-python
# set LD_LIBRARY_PATH="$NORDUGRID_LOCATION/lib:$GLOBUS_LOCATION/lib
#     PYTHONPATH="$NORDUGRID_LOCATION/lib/python2.4/site-packages"
try:
    import arclib
except:
    logger.error('problems importing arclib... trying workaround')
    try:
        logger.debug('Current sys.path is %s' % sys.path )
        sys.path.append(os.environ['NORDUGRID_LOCATION'] 
                        + '/lib/python2.4/site-packages')
        import arclib
    except:
        raise Exception('arclib not found - no problem unless using ARC')

# (trivially inheriting) exception class of our own
class ARCWrapperError(arclib.ARCLibError):
    def __init__(self,msg):
        arclib.ARCLibError.__init__(self, msg)

class NoProxyError(arclib.ARCLibError):
    """ A special error which can occur in this setting:
        The user did not provide a valid proxy certificate, or the one
        she provided is expired. We need to treat this error case
        specially (advise to update, or create a new proxy)."""

    def __init(self,msg):
        arclib.ARCLibError.__init__(self,('No proxy available: %s' % msg))

class Proxy(arclib.Certificate):
    """Proxy management class.
    
    This class handles a X509 proxy certificate."""
    def __init__(self, filename):
        """Class constructor.
        
        @type  filename: string
        @param filename: Proxy filename"""

        self.__filename = os.path.abspath(filename)
        if not os.path.isfile(self.__filename):
            raise NoProxyError('Proxy file ' + filename + ' does not exist.')

        try:
            arclib.Certificate.__init__(self,arclib.PROXY,self.__filename)
        except arclib.CertificateError as err:
            raise NoProxyError(err.what())
        # just testing...
        logger.debug('Proxy Certificate %s from %s' \
                     % (self.GetSN(), self.getFilename()))
        logger.debug('time left in seconds: %d' % self.getTimeleft())

    def getFilename(self):
        """Return the proxy filename."""
        return self.__filename

    def getTimeleft(self):
        """Return the amount of time left on the proxy certificate (int)."""
        
        timeleft = 0
        if not self.IsExpired():
            timeLeftStr = self.ValidFor()
            factor = {'days':24*60*60,'day':24*60*60
                     ,'hours':60*60, 'hour':60*60
                      ,'minutes':60, 'minute':60
                      ,'seconds':1, 'second':1}
            timeLeftParts = timeLeftStr.split(',')
            for part in timeLeftParts:
                [val,item] = part.split()
                f = factor[item]
                if f: 
                    timeleft = timeleft + int(val)*f
        return timeleft

# small helpers: 

# splitting up an ARC job ID
def splitJobId(jobId):
    """ Splits off the last part of the path from an ARC Job ID.
        Reason: The job ID is a valid URL to the job directory on the
        ARC resource, and all jobs have a common URL prefix. In addition,
        job information on the ARC resource is usually obtained by 
        inspecting files at URL <JobID-prefix>/info/<JobID-last-part>
        (see ARC/arclib/jobinfo.cpp).

        This function can trigger an arclib.URLError exception.
    """
    if not jobId.endswith('/'):
        jobId = jobId + '/'
    jobURL = arclib.URL(jobId)
    path = os.path.split(jobURL.Path())[0]
    return (jobURL.Protocol() + '://' + jobURL.Host() + ':' 
            + str(jobURL.Port()) + os.path.dirname(path) + '/'
           , os.path.basename(path))

# hack: issue a command line, return output and exit code
def getstatusoutput(cmd, env=None, startDir=""):
    
    variableDefs = ""
    
    if env:
        for variableName in env.keys():
            variableDefs = variableDefs + "%s=%s " % \
                            (variableName, env[variableName])
    
    execCmd = variableDefs + cmd

    if startDir == "":
        resultVal, result = commands.getstatusoutput(execCmd)
    else:
        resultVal, result = commands.getstatusoutput('cd "%s";set;%s' % (startDir, execCmd))
    
    resultLines = result.split('\n')
    
    logger.debug("Executing: %s, result = %d" % (execCmd, resultVal))
    
    if logger.getLogLevel() == 'DEBUG':
        if len(resultLines)<200:
            i = 0
            for line in resultLines:
                logger.debug("\t"+str(i)+": "+line.strip())
                i = i + 1
    
    return resultVal, resultLines


# asking the user for a proxy. This will be called from many places, 
# thus centralised here (though too specific ).
def askProxy():
        output_objects = []
        output_objects.append({'object_type':'sectionheader',
                               'text':'Proxy upload'})
        output_objects.append({'object_type':'html_form',
                              'text':"""
<form action="upload.py"
enctype="multipart/form-data" method="post">
<p>
Please specify a proxy file to upload:<br>
Such a proxy file can be created using the command-line tool 
voms-proxy-init, and can be found in /tmp/x509up_u&lt;your UID&gt;.<br>
<input type="file" name="fileupload" size="40">
<input type="hidden" name="path" value=""" + \
                                     '"' + Ui.proxy_name + '"' + \
                                     """>
<input type="hidden" name="restrict" value="true">
&nbsp;
<input type="submit" value="Send file">
</form>
                              """})
        return output_objects


def create_grid_proxy(cert_path, key_path, proxy_path):
    """
    Create a default proxy cert. Uses grid-proxy-init. 
    In this way no additional voms information is added.  
    
    Returns the absolute path of the generated proxy. By standard placed in
    the /tmp/ folder.
    """
    try:
        command_list = ["../java-bin/generate_proxy", cert_path, key_path,
                        proxy_path]
        # NOTE: we use command list to avoid the need for shell
        proc = subprocess_popen(command_list, stdout=subprocess_pipe,
                                stderr=subprocess_pipe)
        (out, _) = proc.communicate()
        logger.info(out.replace("\n", "."))
    except Exception as exc: 
        logger.error("Could not generate a proxy certificate: \n%s" % exc)
        raise
    
class Ui:

    """ARC middleware user interface class."""

    # static information: 
    # service URL (Danish resources)
    giis=arclib.URL('ldap://gridsrv4.nbi.dk:2135/O=Grid/Mds-Vo-Name=Denmark')
    #  and benedict cluster URL... for first tests
    benedict =\
      arclib.URL('ldap://benedict.grid.aau.dk:2135/o=grid/mds-vo-name=local')
    fyrgrid =\
      arclib.URL('ldap://fyrgrid.grid.aau.dk:2135/o=grid/mds-vo-name=local')
    # hard-wired: expected proxy name
    proxy_name = '.proxy.pem'

    def __init__(self, userdir, require_user_proxy=False):
        """Class constructor"""

        # would be nice to hold the Ui instance and have the resources 
        # set up on instantiation. but several problems arise: 
        # - A stateless web interface cannot carry over the Ui object
        #  between several calls. We cannot pickle this information if
        #  it contains SWIG proxy objects. userdir, proxy and lock can
        #  be pickled, but _clusters and _queues are the interesting ones.
        # - Different users should not share the same Ui! So running the
        #  whole server with just one Ui will not work either.
        #  Allowed _clusters and _queues might depend on the user's 
        #  permissions, but we can work with a superset and rely on
        #  ConstructTargets to filter out the allowed ones.
        self._clusters = None # SWIG
        self._queues = None   # SWIG

        self._userdir = None  # holds user config, job cache, and proxy file
        self._proxy = None    # determines user permissions

        self._arclibLock = threading.Lock()
        proxy_path = os.path.join(userdir, self.proxy_name)
        
        try:
                
            if not os.path.isdir(userdir):
                raise ARCWrapperError('Given user directory ' + userdir
                                          + ' does not exist.')
            self._userdir = userdir
        
            # if a proxy is not explicitly required and the user does not have a valid one 
            # then use the shared default proxy cert        
            if not require_user_proxy and \
                ( not os.path.exists(proxy_path) or Proxy(proxy_path).IsExpired() ):
                
                logger.info("Using default proxy certificate.")
                                               
                # Check if there is already a default proxy certificate and get its location
                proxy_path = config.nordugrid_proxy
                
                # it there is no default proxy or it is expired
                if not os.path.exists(proxy_path) or Proxy(proxy_path).IsExpired():
                    cert_path = config.nordugrid_cert
                    key_path = config.nordugrid_key
                    # generate a new one
                    create_grid_proxy(cert_path, key_path, proxy_path)
            else:
                logger.info("Using personal proxy certificate.")
                
            # proxy constructor might raise an exception as well
            self._proxy = Proxy(proxy_path)
            if self._proxy.IsExpired(): # should not happen
                raise NoProxyError('Expired.')
    
        except NoProxyError as err:
            logger.error('Proxy error: %s' % err.what())
            raise err
        except arclib.ARCLibError as err:
            logger.error('Cannot initialise: %s' % err.what())
            raise ARCWrapperError(err.what())
        except Exception as other:
            logger.error('Unexpected error during initialisation.\n %s' % other)
            raise ARCWrapperError(other.__str__())

            
    def __initQueues(self):
        """ Initialises possible queues for a job submission."""

        logger.debug('init queues (for job submission/resource display)')

        try:
            # init data: cluster information (obtained per user) 
            self.__lockArclib()

            # this takes ages:
            # self._clusters = arclib.GetResources(Ui.giis)
            self._clusters = []
            logger.debug(config.arc_clusters)
            for url_str in config.arc_clusters:
                if url_str.startswith('ldap://'):
                    self._clusters.append(arclib.URL(url_str))
                elif url_str in ['benedict','fyrgrid']:
                    self._clusters.append(eval('Ui.' + url_str))
            logger.debug('clusters: ')
            for c in self._clusters:
                logger.debug('\t %s' % c)
            
            self._queues = []
            for cl in self._clusters:
                qs = arclib.GetQueueInfo(cl)
                self._queues = self._queues + list(qs)
            self.__unlockArclib()
            logger.debug('ARC Init, discovered queues are')
            for q in self._queues:
                logger.debug('\t %s' % q)

        except NoProxyError as err:
            self.__unlockArclib()
            logger.error('Proxy error during queue initialisation: %s' % err )
            raise err
        except Exception as err:
            self.__unlockArclib()
            logger.error('ARC queue initialisation error: %s' % err )
            self._clusters = []
            self._queues = []
            raise ARCWrapperError(err.__str__())

    def __lockArclib(self):
        """ ensures exclusive access to the interface and sets the environment
            so that the user's proxy and home are used. 
            Locking is perhaps not needed in our setup, where anyway users 
            cannot share the same Ui (needed if _arclib.so not thread-safe, 
            though).""" 

        self._arclibLock.acquire()
        self.__setupEnviron()
        return

    def __unlockArclib(self):
        """ Releases the mutex lock of the interface. 
            Perhaps not needed."""

        self._arclibLock.release()
        return

    def __setupEnviron(self):
        """Make sure the API acts on behalf of the calling user. 
           Called by __lockArclib. 
        """
        os.environ['X509_USER_PROXY'] = self._proxy.getFilename()
        os.environ['HOME'] = self._userdir
        return

    def getProxy(self):
        """ returns the proxy interface used"""
        return self._proxy

    def getQueues(self):
        """ returns the queues we discovered for the clusters.
            TODO: should only return _allowed_ queues 
            (__initQueues to change).""" 
        self.__initQueues()
        return self._queues
    
    def submitFile(self, xrslFilename, jobName=''):
        """Submit xrsl file as job to available ARC resources.
        
        @type  xrslFilename: string
        @param xrslFilename: Filename containing a job description in XRSL.
        @rtype list:
        @return: list containing ARC jobIds (strings).
        Throws an ARCWrapperError if unsuccessful."""

        logger.debug( 'Submitting a job from file %s...' % xrslFilename )
        currDir = os.getcwd()
        try:

                # Convert XRSL file into a string

                f = file(xrslFilename, 'r')
                xrslString = f.read()
                f.close()
                xrslAll = arclib.Xrsl(xrslString)

                [jobDir, filename] = os.path.split(xrslFilename)
                os.chdir(jobDir)

                result = (self.submit(xrslAll, jobName))
                os.chdir(currDir)
                return result
        except arclib.XrslError as err:
            logger.error('Ui: XrslError: ' + err.what())
            os.chdir(currDir)
            raise ARCWrapperError('XrslError: ' + err.what())

    def submit(self, xrslAll, jobName=''):
        """Submit xrsl object as job to available ARC resources.
        The method expects an arclib.Xrsl object and its current
        working directory to contain the referenced files (rel. paths).
        
        @type  xrslAll: arclib.Xrsl
        @param xrslAll: job description in XRSL (arclib object).
        @rtype list:
        @return: list of jobIds(strings).

        Any error is raised as an exception to the caller, as 
        ARCWrapperError or NoProxyError."""

        try:
                # Check for multiple xrsl
                xrslSplit = xrslAll.SplitMulti()

                # retrieve clusters and their queues
                # might throw a NoProxyError, leading us to the end
                self.__initQueues()

                # Construct submission targets

                logger.debug('Ui: Constructing targets:')
                allTargets = arclib.ConstructTargets(self._queues, xrslAll)
                targets = arclib.PerformStandardBrokering(allTargets)
                for t in targets:
                    logger.debug('\t %s' % t)

                # Submit job

                jobIds = []

                logger.debug('Ui: Submitting job  .')
                if len(targets) > 0:
                    self.__lockArclib()
                    for xrsl in xrslSplit:
                        jobId = arclib.SubmitJob(xrsl, targets)
                        jobIds.append(jobId)
                        logger.debug('Ui:' + jobId + 'submitted.')

                        jobName = xrsl.GetRelation('jobName'
                                ).GetSingleValue()

                        arclib.AddJobID(jobId, jobName)
                    self.__unlockArclib()
                    return jobIds
                else:
                    # len(targets) == 0, thus:
                    raise ARCWrapperError("No matching resource for submission.")

        except NoProxyError as err:
            logger.error('Proxy error during job submission: ' + err.what())
            if self._arclibLock.locked(): 
                # should not happen!
                # we come here from initQueues
                logger.error('submit: still locked???')
                self.__unlockArclib()
            raise err
        except arclib.XrslError as message:
            logger.error('Ui,XRSL' + message.what())
            if self._arclibLock.locked(): # should not happen!
                self.__unlockArclib()
            raise ARCWrapperError('XrslError: ' + message.what())
        except arclib.JobSubmissionError as message:
            logger.error('Ui,Submit: ' + message.what())
            self.__unlockArclib()
            raise ARCWrapperError('JobSubmissionError: ' + message.what())
        except arclib.TargetError as message:
            logger.error('Ui,Target: ' + str(message))
            if self._arclibLock.locked(): # should not be...
                self.__unlockArclib()
            raise ARCWrapperError('TargetError: ' + str(message))
        except Exception as err:
            if self._arclibLock.locked(): # ...
                self.__unlockArclib()
            logger.error('Unexpected error: %s' % err )
            raise ARCWrapperError(err.__str__())

    def AllJobStatus(self):
        """Query status of jobs in joblist.
        
        The command returns a dictionary of jobIDs. Each item
        in the dictionary consists of an additional dictionary with the
        attributes:
        
            name = Job name
            status = ARC job states, ACCPTED, SUBMIT, INLRMS etc
            error = Error status
            sub_time = string(submission_time)
            completion = string(completion_time)
            cpu_time = string(used_cpu_time)
            wall_time = string(used_wall_time)

        If there was an error, an empty dictionary is returned.
            
        Example:
        
            jobList = ui.jobStatus()
        
            print jobList['gsiftp://...3217']['name']
            print jobList['gsiftp://...3217']['status']
            
        @rtype: dict
        @return: job status dictionary."""

        logger.debug('Requesting job status for all jobs.')

        jobList = {}

# GetJobIDs returns a multimap, mapping job names to JobIDs...
        self.__lockArclib()
        try:
            # ATTENTION: GetJobIDs does not throw an exception 
            # if the .ngjobs file is not found. Instead, it 
            # only complains on stderr and returns {}.
            if not os.path.isfile( \
                        os.path.join(self._userdir, '.ngjobs')):
                logger.debug('No Job file found, skipping')
                return jobList
            else: 
                jobIds = arclib.GetJobIDs()
        except Exception as err:
            logger.error('could not get job IDs: %s', err)
            self.__unlockArclib()
            return jobList

        self.__unlockArclib()

        # use an iterator over the multimap elements
        # do not call iter.next() at the end (segfaults!)
        iter = jobIds.begin()
        i = 0
        while i < jobIds.size():
            i = i + 1
            (jobName,jobId) = next(iter)
# this is what GetJobIDs really does when called with no arguments
#        jobListFile = file(os.path.join(self._userdir,
#                               '.ngjobs'), 'r')
#        lines = jobListFile.readlines()
#        jobListFile.close()
#        for line in lines:
#            (jobId, jobName) = line.strip().split('#')
            logger.debug('Querying job %s (%s)' % (jobId, jobName))
            jobList[jobId] = {}
            jobList[jobId]['name'] = jobName
            status = None
            exitCode = None
            sub_time = None

            self.__lockArclib()
            try:
                # jobInfo = arclib.GetJobInfoDirect(jobId)
                jobInfo  = arclib.GetJobInfo(jobId)
                status   = jobInfo.status
                exitCode = jobInfo.exitcode
                sub_time = jobInfo.submission_time.__str__()
                completed= jobInfo.completion_time.__str__()
                # cpu_time = jobInfo.used_cpu_time.__str__()
                # wall_time= jobInfo.used_wall_time.__str__()

            except arclib.FTPControlError:
                logger.error('Failed to query job %s' % jobName)
                status = 'REMOVED'
                exitCode = -1
                completed = None
                cpu_time = None
                wall_time = None
            self.__unlockArclib()

            jobList[jobId]['status'] = status
            jobList[jobId]['error' ] = exitCode
            jobList[jobId]['submitted'] = sub_time
            jobList[jobId]['completed'] = completed
            # jobList[jobId]['cpu_time' ] = sub_time
            # jobList[jobId]['wall_time'] = sub_time
            logger.debug(' %s: %s' % (jobId, jobList[jobId]))

        return jobList

    def jobStatus(self, jobId):
        """Retrieve status of a particular job.
        
           returns: dictionary containing keys name, status, error...
           (see allJobStatus)."""

        logger.debug('Requesting job status for %s.' % jobId)

        jobInfo = { 'name':'UNKNOWN','status':'NOT FOUND','error':-1 }

        # check if we know this job at all:
        self.__lockArclib()
        job_ = arclib.GetJobIDs([jobId])
        self.__unlockArclib()
        
        # ugly! GetJobIDs return some crap if not found...
        jobName = [ j for j in job_ ][0]
        if jobName == '': # job not found
            logger.debug('Job %s was not found.' % jobId)
        else:
            jobInfo['name'] =jobName
            # ASSERT(jobId = jobs[jobName])

            self.__lockArclib()   
            try: 
                logger.debug('Querying job %s (%s)' % (jobId,jobName))
                info = arclib.GetJobInfo(jobId)
                jobInfo['status'] = info.status
                jobInfo['error']  = info.exitcode
                jobInfo['submitted'] = info.submission_time.__str__()
                jobInfo['completed'] = info.completion_time.__str__()
                # jobInfo['cpu_time' ] = info.used_cpu_time.__str__() 
                # jobInfo['wall_time'] = info.used_wall_time.__str__()

            except arclib.ARCLibError as err:
                logger.error('Could not query: %s' % err.what())
                jobInfo['status'] = 'UNABLE TO RETRIEVE: ' + err.what(),
                jobInfo['error'] = 255
                jobInfo['submitted'] = 'unknown'
            self.__unlockArclib()
        logger.debug(' Returned %s' % jobInfo)
        return jobInfo

    def cancel(self, jobID):
        """Kill a (running?) job.
        
        If this fails, complain, and retrieve the job status.
        @type  jobID: string
        @param jobID: jobId URL identifier."""

        logger.debug('Trying to stop job %s' % jobID )
        success = False

        self.__lockArclib()
        try:
            arclib.CancelJob(jobID)
            success = True
        except arclib.FTPControlError as err:
            logger.error('Error canceling job %s: %s' % (jobID, err.what()))
            if logger.getLogLevel == 'DEBUG':
                try:
                    info = arclib.GetJobInfoDirect(jobID)
                    logger.debug('Job status: %s' % info.status)
                except arclib.ARCLibError as err:
                    logger.debug('No job status known')
        self.__unlockArclib()
        return success

    def clean(self, jobId):
        """Removes a (finished?) job from a remote cluster.

        If this fails, just remove it from our list (forget it).
        @type  jobID: string
        @param jobID: jobId URL identifier."""

        logger.debug('Cleaning up job %s' % jobId )
        self.__lockArclib()
        try:
            arclib.CleanJob(jobId)
        except arclib.FTPControlError as err:
                logger.error('Failed to clean job %s: %s' % (jobId, err.what()))
                arclib.RemoveJobID(jobId)
        self.__unlockArclib()

    def getResults(self, jobId, downloadDir=''):
        """Download results from grid job.
        
        @type  jobId: string
        @param jobID: jobId URL identifier.
        @type  downloadDir: string
        @param downloadDir: Download results to specified directory.
        @rtype: list
        @return: list of downloaded files (strings)"""

        logger.debug('Downloading files from job %s' % jobId )
        complete = []
        currDir = os.getcwd()

        # jobID is a valid URL for the job directory.
        # we chop off the final number (should be unique enough)
        # and use it as a directory name to download (emulates behaviour
        # of ngget: downloaddir  _prefixes_ the dir to which we download).

        try:
            (jobPath,jobBasename) = splitJobId(jobId)
            jobInfoDir= jobPath + '/info/' + jobBasename
            jobDir    = jobPath + '/' + jobBasename

            os.chdir(self._userdir)
            if not downloadDir == '':
                if not os.path.exists(downloadDir):
                    os.mkdir(downloadDir) 
                elif not os.path.isdir(downloadDir):
                    raise ARCWrapperError(downloadDir 
                                          + ' exists, not a directory.')
                os.chdir(downloadDir)
            if not os.path.exists(jobBasename):
                os.mkdir(jobBasename)
            else:
                if not os.path.isdir(jobBasename):
                    raise ARCWrapperError('Cannot create job directory,'
                                          +' existing file %s in the way.'\
                                          % jobBasename)
            os.chdir(jobBasename)
        except Exception as err:
            logger.error('Error creating job directory: %s' % err)
            os.chdir(currDir)
            raise ARCWrapperError(err.__str__())

        logger.debug('downloading output summary file')
        self.__lockArclib()
        try:
            ftp = arclib.FTPControl()

            # We could just download the whole directory.
            # But better use the contents of "output" in 
            # the info-directory... (specified by user)
            # to avoid downloading large input files.
            # ftp.DownloadDirectory(jobURL, jobBasename)
            #
            # We use a temp file to get this information first

            (tmp,tmpname) = tempfile.mkstemp(prefix='output', text=True)
            os.close(tmp)
            ftp.Download(arclib.URL(jobInfoDir + '/output'), tmpname)
            lines = file(tmpname).readlines()
            os.remove(tmpname)
            files = [ l.strip().strip('/') for l in lines ]

            # also get the entire directory listing from the server
            dir = ftp.ListDir(arclib.URL(jobDir),True)
            basenames = [os.path.basename(x.filename) for x in dir ]

            if '' in files:
                logger.debug('downloading _all_ files')
                # TODO for files which are already there?
                ftp.DownloadDirectory(arclib.URL(jobDir),'.')
                complete = basenames
            else:
                for f in files:
                    if f in basenames:
                        # we should download this one
                        try:
                            if x.isdir:
                                logger.debug('DownloadDir %s' % f )
                                ftp.DownloadDirectory(\
                                    arclib.URL(jobDir + '/' + f), f)
                                # ... which operates recursively
                                complete.append( f + '/ (dir)')
                            else:
                                logger.debug('Download %s' % f )
                                ftp.Download(arclib.URL(jobDir + '/' + f), f)
                                complete.append( f )
                        except arclib.ARCLibError as err: 
                            logger.error('Error downloading %s: %s' \
                                         % (f,err.what()))
        except arclib.ARCLibError as err:
            logger.error('ARCLib error while downloading: %s' % err.what())
            self.__unlockArclib()
            os.chdir(currDir)
            raise ARCWrapperError(err.what())
        except Exception as err:
            logger.error('Error while downloading.\n %s' % err)
            self.__unlockArclib()
            os.chdir(currDir)
            raise ARCWrapperError(err.__str__())

        # return
        logger.debug(string.join(['downloaded:'] + complete, ' '))
        os.chdir(currDir)
        return complete

    def lsJobDir(self, jobId):
        """List files at a specific URL.
        
        @type  jobId: string
        @param jobId: jobId, which is URL location of job dir.
        @rtype: list
        @return: list of FileInfo
        """

        # the jobID is a valid URL to the job directory. We can use it to 
        # inspect its contents.
        #
        # For other directories (gmlog or other), using FTPControl, we do 
        # not get accurate file sizes, only for the real output 
        # and for scripts/files in the proper job directory. 

        logger.debug('ls in JobDir for job %s' % jobId )
        ftp = arclib.FTPControl()
        url = arclib.URL(jobId)

        self.__lockArclib()
        try:
            files = ftp.ListDir(url)
        except arclib.ARCLibError as err:
            logger.debug('Error during file listing: %s' % err.what())
            errmsg = arclib.FileInfo()
            errmsg.filename = err.what
            errmsg.size = 0
            errmsg.isDir = False
            files = [ errmsg ]

        self.__unlockArclib()

        # filter out the gmlog if present
        def notGmlog(file):
            return ((not file.isDir) or (file.filename != 'gmlog')) 

        return (filter(notGmlog, files))


# stdout of a job can be found directly in its job directory, but might have
# a different name (user can give the name). For a "live output request", 
# we download the xrsl description from the info directory and look for 
# the respective names.
# For jobs with "joined" stdout and stderr, we get an error when retrieving 
# the latter, and fall back to retrieving stdout instead.

    def recoverXrsl(self, jobId):
        """ retrieves the xrsl for a job (from the server), if possible"""

        logger.debug('Trying to obtain xRSL for job %s' % jobId)
        xrsl = arclib.Xrsl('')
        self.__lockArclib()
        try:
            (jobPath,jobBasename) = splitJobId(jobId)
            xrslURL = arclib.URL(jobPath + '/info/' 
                                 + jobBasename + '/description')
            ftp = arclib.FTPControl()
            ftp.Download(xrslURL, 'tmp')
            str = file('tmp').read()
            xrsl = arclib.Xrsl(str)
            os.remove('tmp')
        except arclib.ARCLibError as err: 
            logger.error('Failed to get Xrsl: %s' % err.what()) 
        self.__unlockArclib()
        logger.debug('Obtained %s' % xrsl)
        return xrsl

    def getStandardOutput(self, jobId):
        """Get the standard output of a running job.
        
        @type  jobID: string
        @param jobID: jobId URL identifier.
        @rtype: string
        @return: output from the job"""

        logger.debug('get std. output for %s' % jobId)
        try:
            xrsl = self.recoverXrsl(jobId)
            try:
                outname = xrsl.GetRelation('stdout').GetSingleValue()
            except arclib.XrslError as err:
                outname = 'stdout' # try default if name not found
            logger.debug('output file name: %s' % outname)
            try:
                self.__lockArclib()
                ftp = arclib.FTPControl()
                ftp.Download(arclib.URL(jobId + '/' + outname))
            except Exception as err:
                self.__unlockArclib()
                raise ARCWrapperError(err.__str__())
            self.__unlockArclib()
            logger.debug('output downloaded')
            result = file(outname).read()
            os.remove(outname)
        except arclib.ARCLibError as err:
            result = 'failed to retrieve job output stdout: %s' % err.what()
            logger.error('%s' % result)
        logger.debug('output retrieved')
        return result

        # (resultVal, result) = utils.getstatusoutput('ngcat -o %s'
        #          % jobId, self._env)
        #
        # return result

    def getStandardError(self, jobId):
        """Get the standard error of a running job.
        
        @type  jobID: string
        @param jobID: jobId URL identifier.
        @rtype: list
        @return: list of return value from ARC and output from job."""

        logger.debug('get stderr output for %s' % jobId)
        try:
            xrsl = self.recoverXrsl(jobId)
            try:
                outname = xrsl.GetRelation('stderr').GetSingleValue()
            except arclib.XrslError as err:
                outname = 'stderr' # try default if name not found
            logger.debug('output file name: %s' % outname)
            try:
                self.__lockArclib()
                ftp = arclib.FTPControl()
                ftp.Download(arclib.URL(jobId + '/' + outname))
            except Exception as err:
                self.__unlockArclib()
                raise ARCWrapperError(err.__str__())
            self.__unlockArclib()
            logger.debug('output downloaded')
            result = file(outname).read()
            os.remove(outname)
        except arclib.ARCLibError as err:
            result = 'failed to retrieve job output stderr: %s' % err.what()
            logger.error('%s' % result)
        logger.debug('output retrieved')
        return result

#        (resultVal, result) = utils.getstatusoutput('ngcat -e %s'
#                 % jobId, self._env)
#
#        return result

######################### old code:

    def getGridLog(self, jobId):
        """Get the grid log of a running job.
        
        @type  jobID: string
        @param jobID: jobId URL identifier.
        @rtype: list
        @return: list of return value from ARC and output from job."""

        (resultVal, result) = getstatusoutput('ngcat -l %s'
                 % jobId, self._env)

        return result

    def copy(self, source, dest=''):
        """Copy file from source URL to dest URL.
        
        @type  source: string
        @param source: URL of file to copy from.
        @type  dest: string
        @param dest: destination file name on server."""

        (resultVal, result) = getstatusoutput('ngcp %s %s'
                 % (source, dest), self._env)

        return resultVal

    def pcopy(self, source):
        """Open the ngcp command as a popen process, redirecting output
        to stdout and return process file handle.
        
        @type  source: string
        @param source: URL to open"""

        # NOTE: I replaced a possibly unsafe call
        # f = popen('ngcp %s /dev/stdout' % source, self._env)
        # and haven't tested afterwards
        # -Jonas
        
        command_list = ['ngcp', source, '/dev/stdout']
        # NOTE: we use command list to avoid the need for shell
        return subprocess_popen(command_list, stdout=subprocess_pipe,
                                env=self._env).stdout

    def sync(self):
        """Query grid for jobs and update job list.
        
        @rtype: list
        @return: list of [resultVal, result], where resultVal is the return value
        from the ARC command and result is a list of command output."""

        (resultVal, result) = \
            getstatusoutput('ngsync -f -d %d'
                 % self._debugLevel, self._env)

