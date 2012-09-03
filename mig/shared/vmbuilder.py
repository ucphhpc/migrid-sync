#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vmbuilder - shared virtual machine builder functions and script
#
# Copyright (C) 2003-2012  The MiG Project lead by Brian Vinter
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

"""A collection of functions for building virtual machines for grid use and a
simple handler for invocation as a command line vm build script.
"""

import getopt
import os
import subprocess
import sys
from tempfile import mkdtemp

from shared.conf import get_configuration_object


configuration = get_configuration_object()
logger = configuration.logger
# Packages needed for basic desktop with vnc proxy (using vboxguest module)
default_adds = ['iptables', 'acpid', 'x11vnc', 'xorg', 'gdm', 'xfce4', 'gcc',
                'make', 'python-openssl', 'zenity']
# Packages installed by recommends but not needed
default_removes = ['gnome-session', 'compiz', 'metacity', 'xscreensaver',
                   'nautilus', 'yelp', 'rhythmbox']
default_specs = {'distro': 'ubuntu', 'hypervisor': 'vbox', 'memory': 1024,
                 'cpu_count': 1, 'suite': 'lucid', 'mig_code_base':
                 configuration.mig_code_base, 'working_dir':
                 configuration.vms_builder_home, 'architecture': 'i386',
                 'mirror': 'http://127.0.0.1:9999/ubuntu', 'add_packages':
                 default_adds, 'remove_packages': default_removes,
                 'late_adds': [], 'late_removes': [], 'vmbuilder_opts':
                 '--vbox-disk-format=vmdk'}

def fill_template(src, dst, vm_specs):
    """Fills template in src with values from specs and writes it to dst. All
    fields used in template should be provided in vm_specs.
    """
    src_fd = open(src, 'r')
    template = src_fd.read()
    src_fd.close()
    filled_conf = template % vm_specs
    dst_fd = open(dst, 'w')
    dst_fd.write(filled_conf)
    dst_fd.close()
    logger.info("filled %s in %s:\n%s" % (src, dst, filled_conf))

def build_vm(vm_specs):
    """Use vmbuilder to build an OS image with settings from the vm_specs
    dictionary.
    """
    build_specs = {}
    build_specs.update(default_specs)
    build_specs.update(vm_specs)
    # Recent suites added unused unity package(s)
    if build_specs['suite'] in ('precise', ):
        build_specs['remove_packages'].append('unity')
    # Make sure basic package adds and removes are done
    build_specs['postinst_adds'] = ' '.join(build_specs['add_packages'] + \
                                            build_specs['late_adds'])
    build_specs['postinst_removes'] = ' '.join(build_specs['remove_packages'] \
                                               + build_specs['late_removes'])
    # Fill conf template (currently just copies it since all args are explicit)
    tmp_dir = mkdtemp()
    conf_path = os.path.join(tmp_dir, '%(distro)s.cfg' % build_specs)
    conf_template_path = os.path.join(configuration.vms_builder_home,
                                 '%(distro)s.cfg' % build_specs)
    bundle_path = os.path.join(tmp_dir, 'bundle-%(suite)s' % build_specs)
    bundle_template_path = os.path.join(configuration.vms_builder_home,
                                 'bundle-%(suite)s.in' % build_specs)
    # Install late_adds and purge late_removes in post-install to avoid
    # early install problems and clean up
    postinst_path = os.path.join(tmp_dir, 'post-install-%(suite)s.sh' % \
                                 build_specs)
    postinst_template_path = os.path.join(configuration.vms_builder_home,
                                 'post-install-%(suite)s.sh.in' % build_specs)
    # destdir option in conf does not work - keep most on cli
    # reserve 3G for tmpfs for way faster build (and enough for sys disk)
    opts_string = "%(vmbuilder_opts)s"
    opts_string += " -c %s --copy %s --exec %s --tmpfs 3072 -o" % \
                   (conf_path, bundle_path, postinst_path)
    opts_string += " -d %(working_dir)s/%(hypervisor)s-%(distro)s-%(suite)s-%(architecture)s"
    opts_string += " --suite %(suite)s --arch %(architecture)s"
    opts_string += " --mem %(memory)d --cpus %(cpu_count)d --mirror %(mirror)s"
    opts_string += " --part %(working_dir)s/%(suite)s.partition"
    opts_string += " --firstboot %(working_dir)s/boot-%(suite)s.sh"
    for name in build_specs["add_packages"]:
        opts_string += " --addpkg %s" % name
    for name in build_specs["remove_packages"]:
        opts_string += " --removepkg %s" % name
        
    build_specs["vmbuilder_opts"] = opts_string % build_specs
    try:
        fill_template(conf_template_path, conf_path, build_specs)
        fill_template(bundle_template_path, bundle_path, build_specs)
        fill_template(postinst_template_path, postinst_path, build_specs)
        os.chmod(postinst_path, 0755)
        cmd_base = "sudo /usr/bin/vmbuilder"
        cmd_args = "%(hypervisor)s %(distro)s %(vmbuilder_opts)s" % build_specs
        cmd_string = "%s %s" % (cmd_base, cmd_args)
        cmd = cmd_string.split()
        logger.info("building vm with: %s" % cmd_string)
        subprocess.check_call(cmd)
        logger.info("built vm in %(working_dir)s" % build_specs)
    except Exception, exc:
        logger.error("vm built failed: %s" % exc)
    finally:
        os.remove(conf_path)
        os.remove(bundle_path)
        os.remove(postinst_path)
        os.rmdir(tmp_dir)

def usage():
    """Script usage help"""
    print "%s OPTIONS [EXTRA_PACKAGES]" % sys.argv[0]
    print "where OPTIONS include the names:"
    for name in default_specs.keys():
        if name in ('add_packages', 'late_adds', 'remove_packages',
                    'late_removes'):
            continue
        print "    %s (default: %s)" % (name.replace('_', '-'),
                                        default_specs[name])

if __name__ == '__main__':
    specs = {}
    specs.update(default_specs)

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'h', [
            'help',
            'distro=',
            'hypervisor=',
            'memory=',
            'cpu_count=',
            'architecture=',
            'working-dir=',
            'suite=',
            'mirror=',
            'blacklist=',
            'vmbuilder-opts=',
            ])
    except getopt.GetoptError, exc:
        logger.error('option parsing failed: %s' % exc)
        sys.exit(1)
        
    for (opt, val) in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('--blacklist', ):
            specs["late_removes"] = val.split()
        elif opt in ('--distro', ):
            specs["distro"] = val
        elif opt in ('--hypervisor', ):
            specs["hypervisor"] = val
        elif opt in ('--memory', ):
            specs["memory"] = int(val)
        elif opt in ('--cpu-count', ):
            specs["cpu_count"] = int(val)
        elif opt in ('--architecture', ):
            specs["architecture"] = val
        elif opt in ('--working-dir', ):
            specs["working_dir"] = val
        elif opt in ('--suite', ):
            specs["suite"] = val
        elif opt in ('--mirror', ):
            specs["mirror"] = val
        elif opt in ('--vmbuilder-opts', ):
            specs["vmbuilder_opts"] = val
        else:
            logger.error("Unknown option: %s" % opt)
            usage()
            sys.exit(1)

    if args:
        specs['late_adds'] = args
    build_vm(specs)
