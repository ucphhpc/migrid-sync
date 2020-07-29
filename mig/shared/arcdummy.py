#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
#
# arcdummy - [optionally add short module description on this line]
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

#
# arcdummy: debug module providing arcwrapper interface
#
# (C) 2009 Jost Berthold, grid.dk
#  adapted to usage inside a MiG framework
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

"""ARC dummy interface module."""
from __future__ import absolute_import

import os
import sys
import string
import commands
import threading
import tempfile

# MiG utilities:
from .shared.conf import get_configuration_object
config = get_configuration_object()
logger = config.logger


class ARCLibError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def what(self):
        return self.msg

# (trivially inheriting) exception class of our own


class ARCWrapperError(ARCLibError):

    def __init__(self, msg):
        ARCLibError.__init__(self, msg)


class NoProxyError(ARCLibError):

    """ A special error which can occur in this setting:
        The user did not provide a valid proxy certificate, or the one
        she provided is expired. We need to treat this error case
        specially (advise to update, or create a new proxy)."""

    def __init(self, msg):
        ARCLibError.__init__(self, ('No proxy available: %s' % msg))


class DummyProxy:

    """Proxy management class.

    This class handles a X509 proxy certificate."""

    def __init__(self, filename):
        """Class constructor.

        @type  filename: string
        @param filename: Proxy filename"""
        self.__filename = filename

        logger.debug('Dummy Proxy Certificate from %s'
                     % filename)

    def getFilename(self):
        """Return the proxy filename."""
        logger.debug('proxy filename')
        return self.__filename

    def getTimeleft(self):
        """Return the amount of time left on the proxy certificate (int)."""
        logger.debug('proxy timeleft')
        return 0

# helper dummies:

# splitting up an ARC job ID


def splitJobId(jobId):
    """ Splits off the last part of the path from an ARC Job ID.
        Reason: The job ID is a valid URL to the job directory on the
        ARC resource, and all jobs have a common URL prefix. In addition,
        job information on the ARC resource is usually obtained by
        inspecting files at URL <JobID-prefix>/info/<JobID-last-part>
        (see ARC/arclib/jobinfo.cpp)."""

    if jobId.endswith('/'):
        jobId = jobId[:-1]
    return os.path.split(jobId)

# asking the user for a proxy. This will be called from many places,
# thus centralised here (though too specific ).


def askProxy():
        output_objects = []
        output_objects.append({'object_type': 'sectionheader',
                               'text': 'Proxy upload'})
        output_objects.append({'object_type': 'html_form',
                              'text': """
<form method="post" action="upload.py"
enctype="multipart/form-data">
<p>
Please specify a proxy file to upload:<br>
Such a proxy file can be created using the command-line tool
voms-proxy-init, and can be found in /tmp/x509up_u&lt;your UID&gt;.<br>
<input type="file" name="fileupload" size="40">
<input type="hidden" name="path" value=""" +
                               '"' + '<DUMMY_PROXY>' + '"' +
                               """>
<input type="hidden" name="restrict" value="true">
&nbsp;
<input type="submit" value="Send file">
</form>
                              """})
        return output_objects


class Ui:

    """ARC middleware user interface class."""

    def __init__(self, userdir):
        """Class constructor"""

        try:
            if not os.path.isdir(userdir):
                raise ARCWrapperError('Given user directory ' + userdir
                                      + ' does not exist.')
            self._userdir = userdir
            self._proxy = DummyProxy(userdir + '/dummyproxy')

        except ARCLibError as err:
            logger.error('Cannot initialise: %s' % err.what())
            raise err
        except Exception as other:
            logger.error(
                'Unexpected error during initialisation.\n %s' % other)
            raise ARCWrapperError(other.__str__())

    def getProxy(self):
        """ returns the proxy interface used"""
        return self._proxy

    def getQueues(self):
        """ returns the queues we discovered for the clusters."""
        return []

    def submitFile(self, xrslFilename, jobName=''):
        """Submit xrsl file as job to available ARC resources.

        @type  xrslFilename: string
        @param xrslFilename: Filename containing a job description in XRSL.
        @rtype list:
        @return: list containing [resultVal, jobIds] resultVal is the return
        code of the ARC command, jobIds is a list of jobID strings."""

        logger.debug('Submitting a job from file %s...' % xrslFilename)

        # Convert XRSL file into a string

        f = open(xrslFilename, 'rb')
        xrslString = f.read()
        f.close()
        logger.debug('XRSL-file: %s', xrslString)
        return (-1, [])

    def submit(self, xrslAll, jobName=''):
        """Submit xrsl object as job to available ARC resources.
        The method expects an arclib.Xrsl object and its current
        working directory to contain the referenced files (rel. paths).

        @type  xrslAll: arclib.Xrsl
        @param xrslAll: job description in XRSL (arclib object).
        @rtype list:
        @return: (resultVal, list of jobIds) resultVal is a return
        code (0 for success), jobIds is a list of jobID strings.

        Exceptions are forwarded to the caller."""

        logger.debug('Ui: Submitting job  .')
        raise Exception("Dummy module")

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
        return jobList

    def jobStatus(self, jobId):
        """Retrieve status of a particular job.

           returns: dictionary containing keys name, status, error...
           (see allJobStatus)."""

        logger.debug('Requesting job status for %s.' % jobId)

        jobInfo = {'name': 'UNKNOWN', 'status': 'NOT FOUND', 'error': -1}

        return jobInfo

    def cancel(self, jobID):
        """Kill a (running?) job.

        If this fails, complain, and retrieve the job status.
        @type  jobID: string
        @param jobID: jobId URL identifier."""

        logger.debug('Trying to stop job %s' % jobID)
        success = False

        return success

    def clean(self, jobId):
        """Removes a (finished?) job from a remote cluster.

        If this fails, just remove it from our list (forget it).
        @type  jobID: string
        @param jobID: jobId URL identifier."""

        logger.debug('Cleaning up job %s' % jobId)

    def getResults(self, jobId, downloadDir=''):
        """Download results from grid job.

        @type  jobId: string
        @param jobID: jobId URL identifier.
        @type  downloadDir: string
        @param downloadDir: Download results to specified directory.
        @rtype: list
        @return: list of downloaded files (strings)"""

        logger.debug('Downloading files from job %s' % jobId)
        # return
        raise Exception("dummy module")

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

        logger.debug('ls in JobDir for job %s' % jobId)
        return []


# stdout of a job can be found directly in its job directory, but might have
# a different name (user can give the name). For a "live output request",
# we download the xrsl description from the info directory and look for
# the respective names.
# For jobs with "joined" stdout and stderr, we get an error when retrieving
# the latter, and fall back to retrieving stdout instead.

    def getStandardOutput(self, jobId):
        """Get the standard output of a running job.

        @type  jobID: string
        @param jobID: jobId URL identifier.
        @rtype: string
        @return: output from the job"""

        logger.debug('get std. output for %s' % jobId)
        return 'DUMMY'

    def getStandardError(self, jobId):
        """Get the standard error of a running job.

        @type  jobID: string
        @param jobID: jobId URL identifier.
        @rtype: list
        @return: list of return value from ARC and output from job."""

        logger.debug('get stderr output for %s' % jobId)
        return 'DUMMY'
