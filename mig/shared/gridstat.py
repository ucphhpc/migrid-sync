#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gridstat - [insert a few words of module description on this line]
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

"""Grid stats by Martin Rehr"""
from __future__ import print_function
from __future__ import absolute_import

import os
import fcntl
import datetime

from mig.shared.defaults import default_vgrid, pending_states
from mig.shared.fileio import pickle, unpickle, touch
from mig.shared.serial import pickle as py_pickle
from mig.shared.vgrid import validated_vgrid_list, job_fits_res_vgrid


class GridStat:

    """Stat class"""

    # Stat types

    VGRID = 'VGRID'
    RESOURCE_TOTAL = 'RESOURCE_TOTAL'
    RESOURCE_NODE = 'RESOURCE_EXE'

    __gridstat_dict = None
    __logger = None
    __configuration = None

    def __init__(self, configuration, logger):
        self.__gridstat_dict = {}
        self.__logger = logger
        self.__configuration = configuration

    def __check_dict(self, stattype_key, stattype_value):
        """Checking if dict exists on disk and loads it into memory"""

        # If stattype doesn't exist create it

        if stattype_key not in self.__gridstat_dict:
            self.__gridstat_dict[stattype_key] = {}

        # If stattype not in memory, check if pickled file exists

        if stattype_value not in self.__gridstat_dict[stattype_key]:
            filename = self.__configuration.gridstat_files_dir\
                 + stattype_key + os.sep + stattype_value.upper()\
                 + '.pck'
            if os.path.exists(filename):
                stat_dict = unpickle(filename, self.__logger)
            else:
                stat_dict = None
            if stat_dict:
                self.__gridstat_dict[stattype_key][stattype_value] = \
                    stat_dict
            else:
                self.__gridstat_dict[stattype_key][stattype_value] = {}

    def __add(
        self,
        stattype_key,
        stattype_value,
        key,
        value,
        ):
        """Add value to the statistics"""

        self.__check_dict(stattype_key, stattype_value)

        if key in self.__gridstat_dict[stattype_key][stattype_value]:
            self.__gridstat_dict[stattype_key][stattype_value][key] += \
                value
        else:
            self.__gridstat_dict[stattype_key][stattype_value][key] = \
                value

    def __addre(
        self,
        stattype_key,
        stattype_value,
        key,
        value,
        ):
        """Add runtimeenvironment to the statistics"""

        self.__check_dict(stattype_key, stattype_value)

        if 'RUNTIMEENVIRONMENT' not in self.__gridstat_dict[stattype_key][stattype_value]:

            self.__gridstat_dict[stattype_key][stattype_value]['RUNTIMEENVIRONMENT'
                    ] = {}

        if key in self.__gridstat_dict[stattype_key][stattype_value]['RUNTIMEENVIRONMENT'
                ]:

            self.__gridstat_dict[stattype_key][stattype_value]['RUNTIMEENVIRONMENT'
                    ][key] += value
        else:

            self.__gridstat_dict[stattype_key][stattype_value]['RUNTIMEENVIRONMENT'
                    ][key] = value

    def __add_resource(
        self,
        unique_resource_name,
        resource_id,
        key,
        value,
        ):
        """Add resource node to the statistics"""

        # Old mRSL files lack the UNIQUE_RESOURCE_NAME field

        if unique_resource_name:
            self.__add(self.RESOURCE_TOTAL, unique_resource_name, key,
                       value)

        # Old mRSL files lack the RESOURCE_ID field
        # Old mRSL files has resource_id == unique_resource_name

        if resource_id and resource_id != unique_resource_name:
            self.__add(self.RESOURCE_NODE, resource_id, key, value)

    def __set(
        self,
        stattype_key,
        stattype_value,
        key,
        value,
        ):
        """Set a specific value"""

        self.__check_dict(stattype_key, stattype_value)

        if key in self.__gridstat_dict[stattype_key][stattype_value]:
            self.__gridstat_dict[stattype_key][stattype_value][key] = \
                value

    def __flush(self):
        """Dumps the statistics to disk and clears memory"""

        # Flush dict to file in the statistics

        for stat_type in self.__gridstat_dict.keys():
            for stat_value in self.__gridstat_dict[stat_type].keys():
                filename = self.__configuration.gridstat_files_dir\
                     + stat_type + os.sep + stat_value + '.pck'
                filedir = os.path.dirname(filename)

                if not os.path.exists(filedir):
                    os.makedirs(filedir)
                pickle(self.__gridstat_dict[stat_type][stat_value],
                       filename, self.__logger)

        # When dict has been flushed, clear it to prevent heavy memory load

        self.__gridstat_dict = {}

    def get_dict(self, stattype_key, stattype_value):
        """Get dict containing data about the stattype requested"""

        result = {}

        self.__check_dict(stattype_key, stattype_value)

        if stattype_key in self.__gridstat_dict\
             and stattype_value in self.__gridstat_dict[stattype_key]:
            result = self.__gridstat_dict[stattype_key][stattype_value]

        return result

    def get_value(
        self,
        stattype_key,
        stattype_value,
        key,
        default_value=0,
        ):
        """Get value from the statistic"""

        result = default_value

        self.__check_dict(stattype_key, stattype_value)

        if stattype_key in self.__gridstat_dict\
             and stattype_value in self.__gridstat_dict[stattype_key]\
             and key in self.__gridstat_dict[stattype_key][stattype_value]:
            result = \
                self.__gridstat_dict[stattype_key][stattype_value][key]

        return result

    def get_cachetime(self):
        """Returns a datetime object containing info about last update"""

        buildtimestamp_file = self.__configuration.gridstat_files_dir\
             + 'buildcache.timestamp'
        timestamp = os.path.getmtime(buildtimestamp_file)
        return datetime.datetime.fromtimestamp(timestamp)

    def __update_statistics_from_job(
        self,
        job_id,
        job_vgrid_name,
        buildcache_dict,
        job_dict,
        ):
        """The dirty details of what jobinfo is used in the
        statistics and buildcache"""

        # Fix legacy VGRIDs

        job_dict['VGRID'] = validated_vgrid_list(self.__configuration,
                                                    job_dict)

        # If the mRSL file was modified and this is the first time
        # we have seen it, add the request info to the statistics.

        if job_id not in buildcache_dict:
            self.__add(self.VGRID, job_vgrid_name, 'NODECOUNT_REQ',
                       int(job_dict['NODECOUNT']))
            self.__add(self.VGRID, job_vgrid_name, 'CPUTIME_REQ',
                       int(job_dict['CPUTIME']))
            self.__add(self.VGRID, job_vgrid_name, 'CPUCOUNT_REQ',
                       int(job_dict['CPUCOUNT']))
            self.__add(self.VGRID, job_vgrid_name, 'DISK_REQ',
                       int(job_dict['DISK']))
            self.__add(self.VGRID, job_vgrid_name, 'MEMORY_REQ',
                       int(job_dict['MEMORY']))
            self.__add(self.VGRID, job_vgrid_name, 'RUNTIMEENVIRONMENT_REQ',
                       len(job_dict['RUNTIMEENVIRONMENT']))

        unique_resource_name = None
        resource_id = None
        if 'RESOURCE_CONFIG' in job_dict:
            if 'UNIQUE_RESOURCE_NAME' in job_dict:
                unique_resource_name = job_dict['UNIQUE_RESOURCE_NAME'
                        ].upper()

            if 'RESOURCE_ID' in job_dict['RESOURCE_CONFIG']:
                resource_id = job_dict['RESOURCE_CONFIG']['RESOURCE_ID'
                        ].upper()

        if job_dict['STATUS'] == 'PARSE':
            self.__add(self.VGRID, job_vgrid_name, 'PARSE', 1)
        elif job_dict['STATUS'] == 'QUEUED':
            self.__add(self.VGRID, job_vgrid_name, 'QUEUED', 1)
        elif job_dict['STATUS'] == 'EXECUTING':
            self.__add(self.VGRID, job_vgrid_name, 'EXECUTING', 1)
        elif job_dict['STATUS'] == 'FAILED':
            self.__add(self.VGRID, job_vgrid_name, 'FAILED', 1)
            self.__add_resource(unique_resource_name, resource_id,
                                'FAILED', 1)
        elif job_dict['STATUS'] == 'RETRY':
            self.__add(self.VGRID, job_vgrid_name, 'RETRY', 1)
            self.__add_resource(unique_resource_name, resource_id,
                                'RETRY', 1)
        elif job_dict['STATUS'] == 'EXPIRED':
            self.__add(self.VGRID, job_vgrid_name, 'EXPIRED', 1)
        elif job_dict['STATUS'] == 'FROZEN':
            self.__add(self.VGRID, job_vgrid_name, 'FROZEN', 1)
        elif job_dict['STATUS'] == 'CANCELED':
            self.__add(self.VGRID, job_vgrid_name, 'CANCELED', 1)
        elif job_dict['STATUS'] == 'FINISHED':

            # Recent jobs have the scheduled resource vgrid available in
            # the RESOURCE_VGRID field. However, that vgrid may be a parent of
            # the requested job vgrid due to inheritance.
            # We repeat the vgrid match up to find the actual job vgrid here.
            # Fall back to saved resource prioritized vgrid list for old jobs.
            
            active_res_vgrid = job_dict.get('RESOURCE_VGRID', None)
            if active_res_vgrid:
                search_vgrids = [active_res_vgrid]
            else:
                print("WARNING: no RESOURCE_VGRID for job %(JOB_ID)s" % \
                      job_dict)
                resource_config = job_dict['RESOURCE_CONFIG']

                # Fix legacy VGRIDs

                resource_config['VGRID'] = validated_vgrid_list(
                    self.__configuration, resource_config)
                search_vgrids = resource_config['VGRID']
            (match, active_job_vgrid, _) = job_fits_res_vgrid(
                job_dict['VGRID'], search_vgrids)

            if not match:

                # This should not happen - scheduled job to wrong vgrid!
            
                print("ERROR: %s no match for vgrids: %s vs %s" % \
                      (job_dict['JOB_ID'], job_dict['VGRID'], search_vgrids))
                active_job_vgrid = '__NO_SUCH_JOB_VGRID__'
                
            active_vgrid = active_job_vgrid.upper()
            if active_vgrid == job_vgrid_name:

                # Compute used wall time

                finished_timestamp = job_dict['FINISHED_TIMESTAMP']
                finished_datetime = datetime.datetime(
                    finished_timestamp.tm_year,
                    finished_timestamp.tm_mon,
                    finished_timestamp.tm_mday,
                    finished_timestamp.tm_hour,
                    finished_timestamp.tm_min,
                    finished_timestamp.tm_sec,
                    )

                starting_timestamp = job_dict['EXECUTING_TIMESTAMP']
                starting_datetime = datetime.datetime(
                    starting_timestamp.tm_year,
                    starting_timestamp.tm_mon,
                    starting_timestamp.tm_mday,
                    starting_timestamp.tm_hour,
                    starting_timestamp.tm_min,
                    starting_timestamp.tm_sec,
                    )

                used_walltime = finished_datetime - starting_datetime

                # VGrid stats
                
                self.__add(self.VGRID, job_vgrid_name, 'FINISHED', 1)
                self.__add(self.VGRID, job_vgrid_name, 'NODECOUNT_DONE',
                           int(job_dict['NODECOUNT']))
                self.__add(self.VGRID, job_vgrid_name, 'CPUTIME_DONE',
                           int(job_dict['CPUTIME']))
                
                self.__add(self.VGRID, job_vgrid_name, 'USED_WALLTIME',
                           used_walltime)
                
                self.__add(self.VGRID, job_vgrid_name, 'CPUCOUNT_DONE',
                           int(job_dict['CPUCOUNT']))
                self.__add(self.VGRID, job_vgrid_name, 'DISK_DONE',
                           int(job_dict['DISK']))
                self.__add(self.VGRID, job_vgrid_name, 'MEMORY_DONE',
                           int(job_dict['MEMORY']))
                self.__add(self.VGRID, job_vgrid_name, 'RUNTIMEENVIRONMENT_DONE',
                           len(job_dict['RUNTIMEENVIRONMENT']))
                
                # Resource stats
                
                self.__add_resource(unique_resource_name, resource_id,
                                    'FINISHED', 1)
                
                self.__add_resource(unique_resource_name, resource_id,
                                    'USED_WALLTIME', used_walltime)
                
                # RE stats

                for runtime_env in job_dict['RUNTIMEENVIRONMENT']:
                    self.__addre(self.VGRID, job_vgrid_name, runtime_env, 1)

                    # Old mRSL files lack the UNIQUE_RESOURCE_NAME field

                    if unique_resource_name:
                        self.__addre(self.RESOURCE_TOTAL,
                                     unique_resource_name, runtime_env, 1)

                    # Old mRSL files lack the RESOURCE_ID field
                    # Old mRSL files has resource_id == unique_resource_name

                    if resource_id and resource_id != unique_resource_name:
                        self.__addre(self.RESOURCE_NODE, resource_id,
                                     runtime_env, 1)

        else:

            print('Unknown status: ' + job_dict['STATUS'])

        # Check and update cache for previous status'

        if job_id in buildcache_dict and \
               buildcache_dict[job_id] in pending_states:
            self.__add(self.VGRID, job_vgrid_name, buildcache_dict[job_id], -1)

        # Cache current status for use in next iteration.
        # Note that status: CANCELED, FAILED, EXPIRED or FINISHED are
        # final stages and therefore none of thoose should occur in
        # the cache, as the mRSL file should not be modified once it
        # reaches one of thoose stages.

        if job_dict['STATUS'] in pending_states:
            buildcache_dict[job_id] = job_dict['STATUS']
        elif job_id in buildcache_dict:
            del buildcache_dict[job_id]

    def update(self):
        """Updates the statistics and cache from the mRSL files"""

        self.__gridstat_dict = {}

        # Cache and timestamp dirs

        root_dir = self.__configuration.mrsl_files_dir
        buildcache_file = self.__configuration.gridstat_files_dir\
             + 'buildcache.pck'
        buildtimestamp_file = self.__configuration.gridstat_files_dir\
             + 'buildcache.timestamp'

        # We lock the buildcache, to make sure that only one vgrid is
        # updated at a time

        if os.path.exists(buildcache_file):
            try:
                file_handle = open(buildcache_file, 'r+w')
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
                buildcache_dict = py_pickle.load(file_handle)
            except Exception as err:
                msg = 'gridstat::update(): %s could not be loaded! %s'\
                     % (buildcache_file, err)
                print(msg)
                self.__logger.error(msg)
                return False
        else:
            buildcache_dict = {}
            try:
                file_handle = open(buildcache_file, 'w')
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
            except Exception as err:
                msg = \
                    'gridstat::update(): %s could not be opened/locked! %s'\
                     % (buildcache_file, err)
                self.__logger.error(msg)
                return False

        # Get timestamp for last build and create timestamp for this
        # build.
        # This is done here to avoid races in the cache
        # between mRSL files that are being modified while cache is
        # being build.

        last_buildtime = 0
        if os.path.exists(buildtimestamp_file):
            last_buildtime = os.path.getmtime(buildtimestamp_file)

        # Touch buildtimestamp file, so the modified time of it is
        # updated

        touch(buildtimestamp_file, self.__configuration)

        # Traverse mRSL dir and update cache

        for (root, _, files) in os.walk(root_dir, topdown=True):

            # skip all dot dirs - they are from repos etc and _not_ jobs

            if root.find(os.sep + '.') != -1:
                continue
            for name in files:
                filename = os.path.join(root, name)

                # Only files modified since last update is checked

                if os.path.getmtime(filename) > last_buildtime:
                    job_dict = unpickle(filename, self.__logger)
                    if not job_dict:
                        msg = 'gridstat::update() could not load: %s '\
                             % filename
                        self.__logger.error(msg)
                        continue

                    job_vgrids = validated_vgrid_list(self.__configuration,
                                                      job_dict)

                    for job_vgrid_name in job_vgrids:

                        # Update the statistics and cache
                        # from the job details

                        job_vgrid_name = job_vgrid_name.upper()
                        self.__update_statistics_from_job(name,
                                job_vgrid_name, buildcache_dict,
                                job_dict)

        # Flush cache and unlock files

        try:
            file_handle.seek(0, 0)
            py_pickle.dump(buildcache_dict, file_handle, 0)
            self.__flush()
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            file_handle.close()
        except Exception as err:
            self.__gridstat_dict = {}
            msg = 'gridstat::update(): %s could not be pickled! %s'\
                 % (buildcache_file, err)
            self.__logger.error(msg)
            return False

        return True

if __name__ == '__main__':
    import sys
    import fnmatch
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    root_dir = configuration.mrsl_files_dir
    job_id = '*_2012_*'
    search_runtime = "GAP-4.5.X-1"
    if sys.argv[1:]:
        job_id = sys.argv[1]
    if sys.argv[2:]:
        search_runtime = sys.argv[2]
    matches = []
    for (root, _, files) in os.walk(root_dir, topdown=True):

        # skip all dot dirs - they are from repos etc and _not_ jobs

        if root.find(os.sep + '.') != -1:
            continue
        for name in fnmatch.filter(files, job_id+'.mRSL'):
            filename = os.path.join(root, name)
            job_dict = unpickle(filename, configuration.logger)
            if not job_dict:
                print("could not load %s" % filename)
                continue

            runtime_envs = job_dict["RUNTIMEENVIRONMENT"]
            if not search_runtime in runtime_envs:
                continue

            job_vgrids = validated_vgrid_list(configuration, job_dict)
            #print "DEBUG: found matching job %s with vgrids: %s" % (filename,
            #                                                        job_vgrids)
            matches.append(job_dict)
    print("DEBUG: found %d matching jobs" % len(matches))
    finished_count = 0
    default_vgrid_count = 0
    resource_vgrid_map = {}
    job_vgrid_map = {}
    explicit_vgrids = {}
    implicit_vgrids = {}
    parent_vgrids = {}
    for job_dict in matches:
        job_id = job_dict['JOB_ID']
        job_vgrid = job_dict['VGRID']
        job_vgrid_string = str(job_vgrid)
        if job_dict['STATUS'] == 'FINISHED':
            finished_count += 1

            active_res_vgrid = job_dict.get('RESOURCE_VGRID', None)
            if active_res_vgrid:
                search_vgrids = [active_res_vgrid]
            else:
                search_vgrids = job_dict['RESOURCE_CONFIG']['VGRID']
            (match, active_job_vgrid, _) = job_fits_res_vgrid(
                job_dict['VGRID'], search_vgrids)

            resource_vgrid_map[active_res_vgrid] = resource_vgrid_map.get(
                active_res_vgrid, 0) + 1
            job_vgrid_map[active_job_vgrid] = job_vgrid_map.get(
                active_job_vgrid, 0) + 1
            if active_res_vgrid not in job_vgrid:
                implicit_vgrids[active_res_vgrid] = implicit_vgrids.get(
                    active_res_vgrid, 0) + 1
                parent_vgrids[job_vgrid_string] = parent_vgrids.get(
                    job_vgrid_string, 0) + 1
            else:
                explicit_vgrids[active_res_vgrid] = explicit_vgrids.get(
                    active_res_vgrid, 0) + 1

    
    print("DEBUG: found %d finished jobs" % \
          finished_count)
    print("resource vgrid distribution:")
    for (key, val) in resource_vgrid_map.items():
        print("\t%s: %d" % (key, val))
    print(" * explicit:")
    for (key, val) in explicit_vgrids.items():
        print("\t%s: %d" % (key, val))
    print(" * implicit:")
    for (key, val) in implicit_vgrids.items():
        print("\t%s: %d" % (key, val))
    print(" * parent:")
    for (key, val) in parent_vgrids.items():
        print("\t%s: %d" % (key, val))
    print("job vgrid distribution:")
    for (key, val) in job_vgrid_map.items():
        print("\t%s: %d" % (key, val))
        
