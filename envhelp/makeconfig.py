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

from mig.shared.install import generate_confs

_ENVHELP_OUTPUT_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "output"))
_MAKECONFIG_ALLOWED = ["local", "test"]
_PYTHON_MAJOR = os.environ.get('PY', '3')


def _at(sequence, index=-1, default=None):
    assert index > -1
    try:
        return sequence[index]
    except IndexError:
        return default


def write_testconfig(env_name, is_py2=False):
    confs_name = 'confs' if env_name == 'local' else '%sconfs' % (env_name,)
    overrides = {
        'destination': os.path.join(_ENVHELP_OUTPUT_DIR, confs_name),
        'destination_suffix': "-py%s" % ('2' if is_py2 else '3',),
    }
    if is_py2:
        overrides.update(**{
            'mig_code': '/usr/src/app/mig',
            'mig_certs': '/usr/src/app/envhelp/output/certs',
            'mig_state': '/usr/src/app/envhelp/output/state',
        })
    generate_confs(_ENVHELP_OUTPUT_DIR, **overrides)


def main_(argv):
    env_name = _at(argv, index=1, default='')
    arg_is_py2 = '--python2' in argv

    if env_name == '':
        raise RuntimeError(
            'expected the environment name as a single argument')
    if env_name not in _MAKECONFIG_ALLOWED:
        raise RuntimeError('environment must be one of %s' %
                           (_MAKECONFIG_ALLOWED,))

    write_testconfig(env_name, is_py2=arg_is_py2)


def main(argv=sys.argv):
    try:
        main_(argv)
    except RuntimeError as e:
        print('makeconfig: %s' % (str(e),))
        exit(1)


if __name__ == '__main__':
    main()
