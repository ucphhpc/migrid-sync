# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# makeconfig.py - standalone test configuration generation
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Standalone test configuration generation."""


from __future__ import print_function

import os
import sys

sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..")))

from mig.shared.install import MIG_BASE, generate_confs

_LOCAL_MIG_BASE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), ".."))
_LOCAL_ENVHELP_OUTPUT_DIR = os.path.join(_LOCAL_MIG_BASE, "envhelp/output")
_MAKECONFIG_ALLOWED = ["local", "test"]


def _at(sequence, index=-1, default=None):
    assert index > -1
    try:
        return sequence[index]
    except IndexError:
        return default


def write_testconfig(env_name, is_docker=False):
    is_predefined = env_name == 'test'
    confs_name = '%sconfs' % (env_name,)
    if is_predefined:
        confs_suffix = 'docker' if is_docker else 'local'
    else:
        confs_suffix = 'py3'

    overrides = {
        'destination': os.path.join(_LOCAL_ENVHELP_OUTPUT_DIR, confs_name),
        'destination_suffix': "-%s" % (confs_suffix,),
    }

    # determine the paths b which we will access the various configured dirs
    #  the tests output directory - when invoked within

    if is_predefined and is_docker:
        env_mig_base = '/usr/src/app'
    else:
        env_mig_base = _LOCAL_MIG_BASE
    conf_dir_path = os.path.join(env_mig_base, "tests/output")

    overrides.update(**{
        'mig_code': os.path.join(conf_dir_path, 'mig'),
        'mig_certs': os.path.join(conf_dir_path, 'certs'),
        'mig_state': os.path.join(conf_dir_path, 'state'),
    })

    print('generating "%s" configuration ...' % (confs_name,))

    generate_confs(_LOCAL_ENVHELP_OUTPUT_DIR, **overrides)

    confs_destination = ''.join(
        [overrides['destination'], overrides['destination_suffix']])
    print('wrote configuration for "%s" env into: %s' %
          (confs_suffix, confs_destination))


def main_(argv):
    env_name = _at(argv, index=1, default='')
    arg_is_docker = '--docker' in argv

    if env_name == '':
        raise RuntimeError(
            'expected the environment name as a single argument')
    if env_name not in _MAKECONFIG_ALLOWED:
        raise RuntimeError('environment must be one of %s' %
                           (_MAKECONFIG_ALLOWED,))

    write_testconfig(env_name, is_docker=arg_is_docker)


def main(argv=sys.argv):
    try:
        main_(argv)
    except RuntimeError as rte:
        print('makeconfig: %s' % rte)
        exit(1)


if __name__ == '__main__':
    main()
