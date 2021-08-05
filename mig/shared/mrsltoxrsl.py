#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# mrsltoxrsl - [optionally add short module description on this line]
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
# mrsltoxrsl: translate MiG job to ARC job
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

"""translate a 'job' from MiG format to ARC format"""

from __future__ import print_function
from __future__ import absolute_import

from string import ascii_letters
import math
import random
import os
import sys

# MiG utilities:
from mig.shared.conf import get_configuration_object
config = get_configuration_object()
logger = config.logger

# to make this succeed:
# install nordugrid-arc-client and nordugrid-arc-python
# set LD_LIBRARY_PATH="$NORDUGRID_LOCATION/lib:$GLOBUS_LOCATION/lib
#     PYTHONPATH="$NORDUGRID_LOCATION/lib/python2.4/site-packages"
try:
    import arclib
except:
    logger.error('problems importing arclib... trying workaround')
    try:
        logger.debug('Current sys.path is %s' % sys.path)
        sys.path.append(os.environ['NORDUGRID_LOCATION']
                        + '/lib/python2.4/site-packages')
        import arclib
    except:
        raise Exception('arclib not found - no problem unless using ARC')


def format_xrsl(xrsl):
    """An indenter for xrsl files.
       Rules:
       0) remove original indentation (strip lines, remove \\n)
       1) indent every line by 2 spaces for every open bracket '('
       2) insert \\n before the opening bracket (unless there is one)
       3) insert \\n after a closing bracket ')' (unless there is one)
    """

    # raw string, without old indentation and newlines
    raw = ''.join([i.strip() for i in ("%s" % xrsl).split('\n')])

    def indent(acc, n, s):
        if not s:
            return acc
        if s[0] == '(':
            start = '\n' + ' ' * n
            return(indent(acc + start + '(', n + 2, s[1:]))
        elif s[0] == ')':
            return(indent(acc + ')', n - 2, s[1:]))

        return(indent(acc + s[0], n, s[1:]))

    return(indent('', 0, raw))


# translate :: (checked Dictionary, session_ID)
#              -> (Xrsl,Job Script,name for Job script)
def translate(mrsl_dict, session_id=None):
    """Translate an (already checked) mRSL dictionary into xRSL,
       suitable for submitting to an ARC resource.

       Returns arclib.Xrsl object.
       Throws exception if errors in the xRSL generation occur."""

    logger.debug('to translate:\n%s\n using session ID %s'
                 % (mrsl_dict, session_id))

    try:
        # every xrsl-specified job is a conjunction at the top level

        xrsl = arclib.Xrsl(arclib.operator_and)

        # First action: include inner OR of ANDs for targetting
        # specific ARC queues.

        # queues can be given in the 'RESOURCE' field, in the format
        # <queue.name>:<queue.cluster.hostname> (separated by ":",
        # see arcresources.py and safeinput.py). Example:
        # ['daughter:benedict.grid.aau.dk','other:fyrgrid.grid.aau.dk']
        # Each entry leads to a cluster/queue combination, and all
        # entries will be disjoint for the resulting xrsl.

        # Why we do it first: the arclib Xrsl API does not allow to
        # construct relations with inner AND and OR, only relations
        # like =,<,<= to specify fields are supported (globus was more
        # clever here... XrslRelation being the same as Xrsl).

        if 'RESOURCE' in mrsl_dict:

            # we build a string containing Xrsl, which will replace
            # the "xrsl" above (if it contains anything)

            tmp_str = ''

            # this is a list. iterate through all entries (if any)
            for targetstring in mrsl_dict['RESOURCE']:
                l = targetstring.rsplit(':', 1)
                if len(l) == 2:
                    tmp_str += '(&(cluster=%s)(queue=%s))' % (l[1], l[0])

                    logger.debug("added to targets: %s" % tmp_str)
                else:
                    logger.debug("ignoring malformed target %s" % l)

            # did we add something at all? (might be all malformed)
            if tmp_str != '':

                xrsl = arclib.Xrsl('&(|%s)' % tmp_str)

        logger.debug('starting with this Xrsl:\n%s' % xrsl)

        if 'JOB_ID' in mrsl_dict:
            j_name = mrsl_dict['JOB_ID']
        else:
            # random string. should not happen anyway...
            j_name = ''.join(random.choice(ascii_letters)
                             for i in xrange(12))
#        j_name = mrsl_dict.get('JOB_ID',
#                               ''.join(random.choice(ascii_letters) \
#                                       for i in xrange(12)))

        # use JOBID as ARC jobname to avoid presenting only ARC IDs
        addRel(xrsl, 'jobname',
               ''.join([mrsl_dict.get('JOBNAME', ''), '(', j_name, ')']))

        # inputfiles + executables, outputfiles
        if session_id:
            # we have been given a destination to put output files. Insert
            # MiG server URL (automatic output download, will use PUT)
            destination = '/'.join([config.migserver_https_sid_url,
                                    'sid_redirect', session_id, ''])
        else:
            destination = ''

        # make double lists, 2nd part perhaps empty
        # output files, always including stdout
        tmpoutfiles = [file_mapping(i)
                       for i in mrsl_dict.get('OUTPUTFILES', [])]
        outfiles = []
        for [f, target] in tmpoutfiles:
            if target == '':
                target = f  # same file name if none given
            if -1 == target.find('://'):  # not remote target, should copy
                # (ARC does not allow local file names as target)
                target = ''.join([destination, target])
                # means: automatic upload to jobdir on MiG server.
            outfiles.append([f, target])

        # job output, maybe transfer automatically to MiG server
        destination = destination + '/'.join(['job_output', j_name, ''])
        stdout = '.'.join([j_name, 'stdout'])
        stderr = '.'.join([j_name, 'stderr'])

        # do not merge stdout and stderr
        addRel(xrsl, 'join', 'no')

        addRel(xrsl, 'stdout', stdout)
        outfiles.append([stdout, ''.join([destination, stdout])])
        addRel(xrsl, 'stderr', stderr)
        outfiles.append([stderr, ''.join([destination, stderr])])

        addRel(xrsl, 'outputfiles', outfiles)

        # what we want to do: EXECUTE (should be there)
        scriptlines = mrsl_dict['EXECUTE']
        script = '\n'.join(['# generated script from mRSL EXECUTE']
                           + scriptlines)
        # the script is expected to be present as an input file,
        # and to have a certain name which we return.
        addRel(xrsl, 'executable', '/bin/sh')
        # HEADS UP: this is the script name we wire in.
        script_name = '.'.join([j_name, 'sh'])
        addRel(xrsl, 'arguments', script_name)

        # executable input files, always including the execute script
        execfiles = [file_mapping(i) for i in mrsl_dict.get('EXECUTABLES', [])]

        # HEADS UP: the script name again!
        execfiles.append([script_name, ''])

        # (non-executable) input files
        infiles = [file_mapping(i) for i in mrsl_dict.get('INPUTFILES', [])]

        # both execfiles and infiles are inputfiles for ARC
        addRel(xrsl, 'inputfiles', [flip_for_input(i)
                                    for i in execfiles + infiles])

        # execfiles are made executable
        # (specified as the remote name, relative to the session dir)
        def fst(list):
            return list[0]
        addRel(xrsl, 'executables', [fst(i) for i in execfiles])

        # more stuff...

        # requested runtime, given in minutes in (user) xrsl ...
        time = mrsl_dict.get('CPUTIME')
        if time:
            addRel(xrsl, 'cputime', "%d" % int(math.ceil(float(time) / 60)))

        # simply copy the values for these:
        copy_items = ['MEMORY', 'DISK', 'NODECOUNT']
        xrsl_name = {'MEMORY': 'memory', 'DISK': 'disk', 'NODECOUNT': 'count'}
        # NB: we have to ignore CPUCOUNT, not supported by ARC xrsl

        for x in copy_items:  # we ignore the ones which are not there
            if x in mrsl_dict:
                addRel(xrsl, xrsl_name[x], mrsl_dict[x])
                # and these are all single values

        if 'ARCHITECTURE' in mrsl_dict:
            addRel(xrsl, 'architecture',
                   translate_arch(mrsl_dict['ARCHITECTURE']))

        if 'ENVIRONMENT' in mrsl_dict:

            # these have already been mangled into pairs (name,value) before
            #            var_val = []
            #            for definition in mrsl_dict['ENVIRONMENT']:
            #                vv = definition.strip().split('=')
            #                var_val.append(vv.strip())
            #            addRel(xrsl,'environment',var_val)

            addRel(xrsl, 'environment', [list(i)
                                         for i in mrsl_dict['ENVIRONMENT']])

        if 'RUNTIMEENVIRONMENT' in mrsl_dict:
            for line in mrsl_dict['RUNTIMEENVIRONMENT']:
                addRel(xrsl, 'runTimeEnvironment', line.strip())

        if 'NOTIFY' in mrsl_dict:
            addresses = []
            # NOTE: max 3
            for line in [i for i in mrsl_dict['NOTIFY'] if is_mail(i)][:3]:
                # remove whites before, then "email:" prefix, then strip
                address = line.lstrip()[6:].strip()
                if address != 'SETTINGS':
                    addresses.append(address)
#                else:
# this should be replaced already, but...
# FIXME: get it from the settings :-P
#                    addresses.append('*FROM THE SETTINGS*')
            if addresses:
                addRel(xrsl, 'notify', 'ec ' + ' '.join(addresses))

        logger.debug('XRSL:\n%s\nScript (%s):\n%s\n)' %
                     (xrsl, script_name, script))
    except arclib.XrslError as err:
        logger.error('Error generating Xrsl: %s' % err)
        raise err
    return (xrsl, script, script_name)

# helper functions and constants used:

# write_pair :: (String,a)       -> arclib.XrslRelation
# and is polymorphic in a: a = String, a = List(String), a = List(List(String))
# the C version of XrslRelation is... so we emulate it here:


def write_pair(name, values):
    if isinstance(values, list):
        if isinstance(values[0], list):
            con = arclib.XrslRelationDoubleList
            val = values  # should cast all to strings, but only used with them
        else:
            con = arclib.XrslRelationList
            val = values  # should cast all to strings, but only used with them
    else:
        con = arclib.XrslRelation
        val = values.__str__()
    return con(name, arclib.operator_eq, val)

# used all the time... shortcut.


def addRel(xrsl, name, values):
    # sometimes we receive empty stuff from the caller.
    # No point writing it out at all.
    if isinstance(values, list) and len(values) == 0:
        return
    if values == '':
        return
    xrsl.AddRelation(write_pair(name, values))


# architectures
architectures = {'X86': 'i686', 'AMD64': 'x86-64', 'IA64': 'ia64',
                 'SPARC': 'sparc64', 'SPARC64': 'sparc64',
                 # 'ITANIUM':'???ia64???',
                 'SUN4U': 'sun4u', 'SPARC-T1': 'sparc64', 'SPARC-T2': 'sparc64',
                 # 'PS3':'??unknown??',
                 'CELL': 'cell'}


def translate_arch(mig_arch):

    if mig_arch in architectures:
        return architectures[mig_arch]
    else:
        return ''


def is_mail(str):
    return str.lstrip().startswith('email:')


def file_mapping(line):
    """Splits the given line of the expected format
          local_name <space> remote_name
    into a 2-element list [local_name,remote_name]
    If remote_name is empty, the empty string is returned as the 2nd part.
    No additional checks are performed.
    TODO: should perhaps also check for valid path characters.
    """
    line = line.strip()
    parts = line.split()
    local = parts[0]
    if len(parts) < 2:
        remote = ''
    else:
        remote = parts[1]
    return [local, remote]


def flip_for_input(list):
    if list[1] == '':
        return[list[0], '']
    else:
        return [list[1], list[0]]


if __name__ == '__main__':
    print('starting translation test. Args: ', len(sys.argv))
    logger.debug('translation for file ' + sys.argv[1] + ' starts')
    if len(sys.argv) > 1:
        fname = sys.argv[1]
        parsed = '.'.join([fname, 'parsed'])
        translated = '.'.join([parsed, 'xrsl'])

        try:
            from mig.shared import mrslparser
            from mig.shared import fileio

            (presult, errors) = mrslparser.parse(fname, 'test-id',
                                                 '+No+Client+Id', None, parsed)
            if not presult:
                print('Errors:\n%s' % errors)
            else:
                print('Parsing OK, now translating')
                mrsl_dict = fileio.unpickle(parsed, logger)
                (xrsl, script, name) = translate(mrsl_dict, 'test-name')
                print('\n'.join(['Job name', name, 'script', script, 'XRSL']))
                fileio.write_file(script, "test-id.sh", logger)
                print (format_xrsl(xrsl))
                fileio.write_file("%s" % xrsl, translated, logger)
                print('done')
        except Exception as err:
            print('Error.')
            print(err.__str__())
