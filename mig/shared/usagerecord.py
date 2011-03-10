#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# usagerecord - generating Usage Records from mRSLs, and XSL conversion helpers
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# -- END_HEADER ---
#
# usagerecord.py, 05/2009 by Jost Berthold, grid.dk
#
# inspired by script arc-ur-logger, (author: Henrik
# Thostrup Jensen <htj@ndgf.org>) from project SGAS
# http://www.cs.umu.se/research/grid/sgas/
#
# SGAS is licensed under the Apache License, Version 2.0
# (the "License"); http://www.apache.org/licenses/LICENSE-2.0
#
# Extended 10/2010 by Jesper Rude Selknæs, to include VGRID information
# in the xml records.

# infrastructure imports

import os
import sys
import datetime
# from xml.etree import ElementTree as ET

# in order to construct our own XML DOMs
from xml.dom import getDOMImplementation,XMLNS_NAMESPACE

# MiG-specific imports

from shared.configuration import Configuration
from shared.fileio import unpickle,write_file

# Description of the Usage Record XML format:

# The following xsl types are used throughout:
#
# String, Integer, Float, Boolean - straightforward
#
# Token: string without newline or tab, and
#       without two spaces in sequence

# XML time/date types:

# dateTime: YYYY-MM-DDThh:mm:ss([+-]n:n|Z)?
#  (with obvious meaning...) All required, including(!) the suffix in
#  brackets, which defines the time zone.


def xsl_datetime(timestamp=None):
    """format the given datetime (or \"now\") as xslDatetime"""

    if timestamp == None:
        timestamp = datetime.datetime.now()
    iso = timestamp.isoformat()

    # add a 'Z' if we do not have a time zone

    if timestamp.tzinfo == None:
        iso = iso + 'Z'
    return iso


# TimeDuration: PnnYnnMnnDTnnHnnMn.nS
# (encoding year,month, day, hour, minute, second with 2 digits each)
# The P is mandatory, as well as the T if a time follows (to
# disambiguate the double "M" :P ). Other parts (nn[YMDHS]) optional,
# but the whole should not be empty after the P.
# values are not restricted but can be arbitrary integer.
# seconds can include any number of decimal fraction digits.
# A preceeding "-" indicates negative duration.
#


def xsl_duration(start, end=None):
    """calc. and return difference between start and end 
       (or now) as an xslDuration"""

    if end == None:
        end = datetime.datetime.now()
    delta = end - start  # type timedelta

    # timedelta has days, seconds, microseconds

    # negative durations are normalised to negative days, rest positive
    # (which is not what we want :( ). We invert and prepend a minus.

    if delta.days < 0:
        delta = -delta
        sign = '-'
    else:
        sign = ''

    # zeros do not hurt us, the xsl type allows arbitrary values.
    # so we just write out any number of days, but normalise the time.
    # hours, minutes, seconds:

    hours = delta.seconds / 3600
    mins = (delta.seconds % 3600) / 60
    secs = delta.seconds % 60

    deltastr = sign + 'P%dD' % delta.days + 'T%02dH%02dM%02d.%06dS'\
         % (hours, mins, secs, delta.microseconds)

    return deltastr


# job usage structure and element/attribute names

# All elements may have an attribute "description" (string). This, and
# some other attributes are left out here, since we do not use it.

# 'JobUsageRecord'
    # these single elements/subelements come first
#   'RecordIdentity'           # mandatory, KeyInfo
#        attribute 'recordId'  # mandatory, Token
#        attribute 'createTime'# when record was written
#      can contain a KeyInfo element
#   'JobIdentity'
#     'GlobalJobId'  # String
#     'LocalJobId'   # String
#     'ProcessId'    # many, String
#   'UserIdentity'
#     'LocalUserId'    # String
#     'GlobalUserName' # String
#     can contain a KeyInfo element
#   'JobName'   # String
#   'Charge'    # float
#      attribute: 'formula' # optional, string
#   'Status'    # mandatory, Token extending a minimal set:
                # aborted,completed,failed,held,queued,started,suspended
                # for mapping MiG<->UsageRecord see __state_map__ below
    # each of the following elements can appear multiple times,
    # but must differ in their "metric" attribute.
#   'Disk'  # positive integer
#   'Memory'  # positive integer
#   'Swap'  # positive integer
#   'Network'  # positive integer
#   'TimeDuration'  # xsl time duration
#   'TimeInstant'  # xsl time duration
#   'ServiceLevel'  # Token
    # the following elements may appear many times.
    # We use them only once, or not at all.
#   'WallDuration'  # xsl time duration
#   'CpuDuration'  # xsd time duration
#     attribute 'usageType'  # mandatory, Token: user | system
#     CpuDuration allowed to appear twice, with different usageType
#   'NodeCount'  # positive integer
#   'Processors'  # positive integer
#   'StartTime'  # xsd dateTime
#   'EndTime'  # xsd dateTime
#   'MachineName'  # host/domain name
#   'SubmitHost'  # host/domain name
#   'Queue'  # String
#   'ProjectName'  # String, can be repeated many times
#   'Host'  # host/domain name
#      attribute 'primary'  # mandatory (default: "false"), boolean
#   'PhaseResource'  # float
#      attribute 'phaseUnit'  # xsl duration
#   'VolumeResource'  # float
#      attribute 'storageUnit'  # bits and bytes: [KMGPE]?[bB]
#   'Resource'  # String
#   'ConsumableResource'  # float

# mapping to/from MiG states to Usage record status:
# WHERE IS THIS DOCUMENTED ?!?

__state_map__ = {
    'CANCELED': 'aborted',
    'FINISHED': 'completed',
    'FAILED': 'failed',
    'PARSE': 'held',
    'QUEUED': 'queued',
    'EXECUTING': 'started',
    'RETRY': 'suspended',
    }

# grep -r STATUS mig/shared/ yields (mostly) this:
# shared/gridscript.py:            if job_dict['STATUS'] == 'PARSE':
# shared/gridscript.py:            elif job_dict['STATUS'] == 'QUEUED'\
# shared/gridscript.py:            elif job_dict['STATUS'] == 'EXECUTING'\
# shared/gridscript.py:            job_dict['STATUS'] = 'QUEUED'
# shared/gridscript.py:            job_dict['STATUS'] = 'FAILED'
# shared/gridstat.py:        if job_dict['STATUS'] == 'PARSE':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'QUEUED':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'EXECUTING':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'FAILED':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'RETRY':
# shared/gridstat.p:        elif job_dict['STATUS'] == 'EXPIRED':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'CANCELED':
# shared/gridstat.py:        elif job_dict['STATUS'] == 'FINISHED':


# static: minidom implementation, used to create XML documents

ET = getDOMImplementation()
namespace_ogf = 'http://schema.ogf.org/urf/2003/09/urf'
namespace_prefix= 'ur:'

SGAS_VO_NAMESPACE   = "http://www.sgas.se/namespaces/2009/05/ur/vo"
SGAS_VO_PREFIX = "vo:"

class UsageRecord:

    """
    Provides a usage record data structure and writing it out to xml.
    """

# constructor, empty record:

    def __init__(self, config, logger):
        """ Construct an empty usage record """

        self.__logger = logger
        self.__configuration = config
        self.__doc = ET.createDocument(namespace_ogf,
                                       namespace_prefix + 'JobUsageRecord',
                                       None)
        # we keep the document around from the beginning...
        self.__doc.documentElement.setAttributeNS(XMLNS_NAMESPACE, 
                          'xmlns:' + namespace_prefix[:-1],
                          namespace_ogf)

        self.__doc.documentElement.setAttributeNS(XMLNS_NAMESPACE, 
                          'xmlns:' + SGAS_VO_PREFIX[:-1],
                          SGAS_VO_NAMESPACE)
        

        # XML data which we intend to use:

        self.record_id = None
        self.create_time = None
        self.global_job_id = None
        self.local_job_id = None
        self.global_user_name = None
        self.local_user_id = None
        self.status = None
        self.charge = None
        self.charge_formula = None
        self.wall_duration = None
        self.node_count = None
        self.start_time = None
        self.end_time = None
        self.project_name = None
        self.vgrid = None
        self.machine_name = None
        self.host = None

# currently not used, but prepared:

        self.cpu_duration_user = None
        self.cpu_duration_system = None
        self.queue = None
        self.submit_host = None

    def generate_tree(self):
        """
        Generates the XML tree for usage record.
        """

        def set_element(parent, name, text, namespace=namespace_ogf, prefix=namespace_prefix):
            """ utility function, adds a child node with text content"""

            # DOM implementation:

            element = self.__doc.createElementNS(namespace,
                                                 prefix + name)
            element.appendChild(self.__doc.createTextNode(str(text)))
            parent.appendChild(element)
            return element  # in case we want to add attributes...

        # temporary element storage in some following if clauses

        temp = None

        # begin method

        self.__logger.debug('Writing out usage record, ID %s'
                             % self.record_id)

        record = self.__doc.documentElement

        if self.record_id == None:
            self.__logger.error('No recordId specified, '
                                 + 'cannot generate usage record')
            return None
        record_id = self.__doc.createElementNS(namespace_ogf,
                                               namespace_prefix + 
                                               'RecordIdentity')
        record_id.setAttributeNS(namespace_ogf,
                                 namespace_prefix + 'recordId', 
                                 self.record_id)
        if self.create_time:
            record_id.setAttributeNS(namespace_ogf,
                                     namespace_prefix + 'createTime', 
                                     self.create_time)
        else:
            record_id.setAttributeNS(namespace_ogf,
                                     namespace_prefix + 'createTime', 
                                     xsl_datetime())
        record.appendChild(record_id)

        if self.global_job_id or self.local_job_id:
            job_identity = self.__doc.createElementNS(namespace_ogf,
                                                      namespace_prefix + 
                                                      'JobIdentity')
            if self.global_job_id:
                set_element(job_identity, 'GlobalJobId',
                            self.global_job_id)
            if self.local_job_id:
                set_element(job_identity, 'LocalJobId',
                            self.local_job_id)
            record.appendChild(job_identity)

        if self.global_user_name or self.local_job_id:
            user_identity = self.__doc.createElementNS(namespace_ogf,
                                                       namespace_prefix +
                                                       'UserIdentity')
            if self.global_user_name:
                set_element(user_identity, 'GlobalUserName',
                            self.global_user_name)
            if self.local_user_id:
                set_element(user_identity, 'LocalUserId',
                            self.local_user_id)

                #If the VGRID property is set, the VO
                #element in the tree is set according to the SGAS
                #definition.
                if self.vgrid:
                    vo = self.__doc.createElementNS(SGAS_VO_NAMESPACE, \
                                            SGAS_VO_PREFIX + 'VO')

                    vo.setAttributeNS(SGAS_VO_NAMESPACE,\
                                      SGAS_VO_PREFIX + 'type', "vgrid")
            
                    set_element(vo, 'Name', self.vgrid, \
                                SGAS_VO_NAMESPACE,SGAS_VO_PREFIX )

            user_identity.appendChild(vo)
            record.appendChild(user_identity)
            

        if self.charge:
            temp = set_element(record, 'Charge', text=self.charge)
            if self.charge_formula:
                temp.setAttributeNS(namespace_ogf,
                                    namespace_prefix + 'formula', 
                                    self.charge_formula)

        if self.status == None:
            self.__logger.error('No status specified, '
                                 + 'cannot generate usage record')
            return None
        set_element(record, 'Status', text=self.status)

        # we should have a machine name...
        if self.machine_name:
            set_element(record, 'MachineName', text=self.machine_name)

        if self.queue:
            set_element(record, 'Queue', text=self.queue)
        if self.node_count:
            set_element(record, 'NodeCount', text=self.node_count)
        if self.host:
            set_element(record, 'Host', text=self.host)
        if self.submit_host:
            set_element(record, 'SubmitHost', text=self.submit_host)
        if self.project_name:
            set_element(record, 'ProjectName', text=self.project_name)
        if self.start_time:
            set_element(record, 'StartTime', text=self.start_time)
        if self.end_time:
            set_element(record, 'EndTime', text=self.end_time)
        if self.wall_duration:
            set_element(record, 'WallDuration', text=self.wall_duration)
        if self.cpu_duration_user:
            temp = set_element(record, 'CpuDuration',
                               text=self.cpu_duration_user)
            temp.setAttributeNS(namespace_ogf,
                                namespace_prefix + 'usageType', 
                                'user')
        if self.cpu_duration_system:
            temp = set_element(record, 'CpuDuration',
                               text=self.cpu_duration_system)
            temp.setAttributeNS(namespace_ogf,
                                namespace_prefix + 'usageType', 
                                'system')

        
        

        return self.__doc.toxml()

    def write_xml(self, filename):
        """ Writes the Usage Record to a file as XML """

        try:
            xml = self.generate_tree()
            result = write_file(xml, filename, self.__logger)
        except Exception, err:
            self.__logger.error('Unable to write XML file: %s' % err)

    def fill_from_mrsl(self, job_data):
        """Read a pickled mRSL file and fill in the contained data"""

        # jobData supposed to be a pickled file or  a dictionary.
        # add a solid type later!

        self.__logger.debug('filling in job data from file %s'
                             % job_data)
        try:
            if os.path.exists(job_data):
                job = unpickle(job_data, self.__logger)
                self.fill_from_dict(job)
            else:
                self.__logger.error('file %s does not exist.'
                                     % job_data)
        except Exception, err:
            self.__logger.error('while filling in data from %s: %s'
                                 % (job_data, err))

    def fill_from_dict(self, job):
        """Fill in data from mRSL, given as a dictionary"""

        # helpers: lookup with exception


        class NotHere(Exception):

            """Catching cases where fields are missing"""

            def __init__(self, name):
                self.name = name

            def __str__(self):
                return self.name


        def lookup(name):
            """search job dict for a given name"""

            if job.has_key(name) and job[name] != '':
                return job[name]
            else:
                raise NotHere(name + ' not found.')

        self.__logger.debug('filling in job data from dictionary: %s'
                             % job )
        # set all fields we can get from mRSL easily:

        # these are required, give up if not there:

        try:
            self.record_id = lookup('JOB_ID')
            status = lookup('STATUS')
            if not __state_map__.has_key(status):
                raise NotHere('Unknown status ' + status + '.')
            self.status = __state_map__[status]
        except NotHere, err:
            self.__logger.error('Job data missing mandatory fields: %s'
                                 % err)
            return

        # createTime: when the record was written (filled)

        self.create_time = xsl_datetime()  # i.e. Now!

        # fields directly used (lookup not needed):

        self.global_user_name = job.get('USER_CERT',None)

        self.project_name = job.get('PROJECT',None)

        self.node_count = job.get('NODECOUNT', None)

        # Nota bene: use the VGrid that actually executed the job, as 
        # opposed to job['VGRID'] which contains a list of potential ones.
        # see http://code.google.com/p/migrid/issues/detail?id=32

        if job.has_key('RESOURCE_VGRID'):
            self.vgrid = job['RESOURCE_VGRID']

        # global JOB_ID should always be there if we get here...
        self.global_job_id = job.get('JOB_ID', None)

        self.local_job_id = job.get('LOCALJOBNAME', None)

        # compute timing values:
        # QUEUED_TIMESTAMP - Start time (???)
        # not used yet, could be added ("deisa extension" to UR in SGAS)

        try:

            # wall execution time, start and end:
            # FINISHED_TIMESTAMP - EndTime
            # EXECUTING_TIMESTAMP - StartTime
            # EXECUTING - FINISHED = WallDuration

            start_ = lookup('EXECUTING_TIMESTAMP')
            start_time = datetime.datetime(*start_[:6])
            self.start_time = xsl_datetime(start_time)

            # FINISHED_TIMESTAMP is not there for failed jobs.
            # Question is how to account them, when 
            # they have spent resources (e.g. failed due 
            # to timeout, several retries,...)

            end_ = lookup('FINISHED_TIMESTAMP')
            end_time = datetime.datetime(*end_[:6])
            self.end_time = xsl_datetime(end_time)

            self.wall_duration = xsl_duration(start_time, end_time)

            # charge is computed as wall time * node count:

            if self.node_count:

                charge_delta = self.node_count * (end_time - start_time)
                self.charge = charge_delta.days * 86400\
                     + charge_delta.seconds + charge_delta.microseconds\
                     / 1000000.0

                              # We currently do not get microseconds because
                              # startT and endT only have second precision
                              # However, the ".0" forces float type.

                self.charge_formula = 'nodes * wall_duration(sec)'
        except NotHere:
            pass  
                # nevermind... if something is not found, we jump out, 
                # but we have set all available fields before.

        # executing host, should always be there:
        self.host = job.get('EXE',None)
        
        # machine name = executing resource ID
        try: 
            self.machine_name = lookup('UNIQUE_RESOURCE_NAME')
        except NotHere: 
            # might be a failed job, try execution history
            if 'EXECUTION_HISTORY' in job:
                hist = job['EXECUTION_HISTORY']
                self.machine_name = hist[-1].get('UNIQUE_RESOURCE_NAME',None)

        # local user on the resource, if available
        if job.has_key('RESOURCE_CONFIG'):
            resCfg = job['RESOURCE_CONFIG']
            self.local_user_id = resCfg.get('MIGUSER',None)
            # self.host  = resCfg.get('RESOURCE_ID',None)

        # could be used, but unreliable:
        # (scheduling req.ments given by user)
        # DISK - ? (requested)
        # CPUTIME - / (requested)
        # CPUCOUNT - ? (requested)
        # MEMORY - ? (requested)

        
        return


# end usage record

# called from outside: write out XMl if directory configured
    # first of all, write out the usage record (if configured)

def write_usage_record_from_dict(jobdict, config):

#    if not configuration:
#        configuration = get_configuration_object

    ur_destination = config.usage_record_dir
    if ur_destination and jobdict:

        config.logger.debug('XML Usage Record directory %s' % ur_destination)
        usage_record = UsageRecord(config, config.logger)
        usage_record.fill_from_dict(jobdict)

        # we use the job_id as a file name (should be unique)

        usage_record.write_xml(ur_destination + os.sep
                                + jobdict['JOB_ID'] + '.xml')

# testing

if __name__ == '__main__':
    print len(sys.argv)
    if len(sys.argv) > 1:
        fname = sys.argv[1]

        conf = Configuration('MiGserver.conf')

        usage_record = UsageRecord(conf, conf.logger)

        #make sure we can write out something...

        usage_record.record_id = 'uninitialised'
        usage_record.status = 'unknown'
        usage_record.fill_from_mrsl(fname)


        if len(sys.argv) > 2:
            target = sys.argv[2]
        else:
            target = '.'.join([fname,'xml'])

            
        usage_record.write_xml(target)
