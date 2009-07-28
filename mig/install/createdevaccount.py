#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createdevaccount - create a MiG server development account
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

# IMPORTANT: Run script with sudo or as root

"""Add a unprivileged user with access to a personal MiG server.
Still needs some semi-automated setup of apache, sudo and iptables
afterwards...

This is very much bound to the exact setup used on the main MiG servers
where things like remote login, firewalling, home dirs and sudo are set up
for separated developer accounts. Some paths like for apache and moin moin is
similarly hard coded to the Debian defaults on those servers.
"""

import sys
import os
import random
import crypt
import socket

from generateconfs import generate_confs


def create_user(
    user,
    group,
    ssh_login_group='remotelogin',
    debug=False,
    ):
    """Create unix user with supplied user and group name"""

    # make sure not to wreak havoc if no user supplied

    if not user:
        print "no user supplied! can't continue"
        return False

    print 'groupadd %s' % group
    status = os.system('groupadd %s' % group) >> 8
    if status != 0:
        print 'Warning: exit code %d' % status

    # Don't use 'o'/'0' and 'l'/'1' since they may confuse users

    valid_chars = 'abcdefghijkmnpqrstuvwxyz'\
         + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789'
    pwlen = 8
    pw = ''
    for idx in range(pwlen):
        pw += random.choice(valid_chars)

    # TODO: python does not support md5 passwords - using DES ones
    # from crypt for now

    shell = '/bin/bash'
    enc_pw = crypt.crypt(pw, random.choice(valid_chars)
                          + random.choice(valid_chars))
    print 'useradd -m -s %s -p %s -g %s %s' % (shell, enc_pw, group,
            user)
    status = os.system('useradd -m -s %s -p %s -g %s %s' % (shell,
                       enc_pw, group, user)) >> 8
    if status != 0:
        print 'Warning: exit code %d' % status
    else:
        print '# Created %s in group %s with pw %s' % (user, group, pw)

    home = '/home/%s' % user

    print 'chmod -R g-rwx,o-rwx %s' % home
    status = os.system('chmod -R g-rwx,o-rwx %s' % home) >> 8
    if status != 0:
        print 'Warning: exit code %d' % status
    else:
        print 'Removed global access to %s' % home

    print 'addgroup %s %s' % (user, ssh_login_group)
    status = os.system('addgroup %s %s' % (user, ssh_login_group)) >> 8
    if status != 0:
        print 'Warning: exit code %d' % status
    else:
        print '# Added %s to group %s' % (user, ssh_login_group)

    out = os.popen('id -u %s' % user).readlines()
    uid_str = out[0].strip()
    out = os.popen('id -g %s' % user).readlines()
    gid_str = out[0].strip()
    try:
        uid = int(uid_str)
        gid = int(gid_str)
    except Exception, err:
        print 'Error: %s' % err
        if not debug:
            return False

    # print "uid: %d, gid: %d" % (uid, gid)

    # Historically we used three server ports, and since user
    # ports are calculated with this assumption, we just keep
    # providing three ports. Users may then use the last one for
    # other purposes, including testing extra daemons.

    http_port = 3 * uid
    https_port = http_port + 1
    extra_port = http_port + 2

    mig_dir = os.path.join(home, 'mig')
    server_dir = os.path.join(mig_dir, 'server')
    state_dir = os.path.join(home, 'state')
    apache_etc = '/etc/apache2'
    apache_dir = '%s-%s' % (apache_etc, user)
    apache_run = '%s/run' % apache_dir
    apache_log = '%s/log' % apache_dir
    cert_dir = '%s/MiG-certificates' % apache_dir
    moin_etc = '/etc/moin'
    moin_share = '/usr/share/moin'

    firewall_script = '/root/scripts/firewall'
    print '# Add the next line to %s and run the script:'\
         % firewall_script
    print 'iptables -A INPUT -p tcp --dport %d:%d -j ACCEPT # webserver: %s'\
         % (http_port, extra_port, user)

    sshd_conf = '/etc/ssh/sshd_config'
    print """# Unless 'AllowGroups %s' is already included, append %s
# to the AllowUsers line in %s and restart sshd."""\
         % (ssh_login_group, user, sshd_conf)
    print """# Add %s to the sudoers file (visudo) with privileges
# to run apache init script in %s"""\
         % (user, apache_dir)
    print """# Set disk quotas for %s using reference user quota:
edquota -u %s -p LOGIN_OF_SIMILAR_USER"""\
         % (user, user)
    print """# Attach full name of user to login:
usermod -c 'INSERT FULL NAME HERE' %s"""\
         % user
    print """# Add mount point for sandbox generator:
echo '/home/%s/state/sss_home/MiG-SSS/hda.img      /home/%s/state/sss_home/mnt  auto    user,loop       0       0' >> /etc/fstab"""\
         % (user, user)

    src = os.path.abspath(os.path.dirname(sys.argv[0]))
    dst = os.path.join(src, '%s-confs' % user)

    generate_confs(
        src,
        dst,
        socket.getfqdn(),
        user,
        group,
        apache_dir,
        apache_run,
        apache_log,
        mig_dir,
        state_dir,
        cert_dir,
        moin_etc,
        moin_share,
        http_port,
        https_port,
        'User',
        'Group',
        '#Listen',
        )
    apache_envs_conf = os.path.join(dst, 'envvars')
    apache_apache2_conf = os.path.join(dst, 'apache2.conf')
    apache_httpd_conf = os.path.join(dst, 'httpd.conf')
    apache_ports_conf = os.path.join(dst, 'ports.conf')
    apache_mig_conf = os.path.join(dst, 'MiG.conf')
    server_conf = os.path.join(dst, 'MiGserver.conf')
    apache_initd_script = os.path.join(dst, 'apache-%s' % user)

    print '# Clone %s to %s and put config files there:' % (apache_etc,
            apache_dir)
    print 'sudo cp -r -u -d -x %s %s' % (apache_etc, apache_dir)
    print 'sudo rm -f %s/envvars' % apache_dir
    print 'sudo rm -f %s/apache2.conf' % apache_dir
    print 'sudo rm -f %s/httpd.conf' % apache_dir
    print 'sudo rm -f %s/ports.conf' % apache_dir
    print 'sudo rm -f %s/sites-enabled/*' % apache_dir
    print 'sudo rm -f %s/conf.d/*' % apache_dir
    print 'sudo cp -f -d %s %s/' % (apache_envs_conf, apache_dir)
    print 'sudo cp -f -d %s %s/' % (apache_apache2_conf, apache_dir)
    print 'sudo cp -f -d %s %s/' % (apache_httpd_conf, apache_dir)
    print 'sudo cp -f -d %s %s/' % (apache_ports_conf, apache_dir)
    print 'sudo cp -f -d %s %s/conf.d/' % (apache_mig_conf, apache_dir)
    print 'sudo cp -f -d %s %s/' % (apache_initd_script, apache_dir)
    print 'sudo mkdir -p %s %s' % (apache_run, apache_log)

    # allow read access to logs

    print 'sudo chgrp -R %s %s' % (user, apache_log)
    print 'sudo chmod 2755 %s' % apache_log

    print '# Setup MiG for %s:' % user
    print 'sudo su - %s -c \'ssh-keygen -t rsa -N "" -q -f \\\n\t%s/.ssh/id_rsa\''\
         % (user, home)
    print "sudo su - %s -c 'cp -f -x \\\n\t%s/.ssh/{id_rsa.pub,authorized_keys}'"\
         % (user, home)
    print "sudo su - %s -c 'ssh -o StrictHostKeyChecking=no \\\n\t%s@`hostname -f` pwd >/dev/null'"\
         % (user, user)
    print "sudo su - %s -c 'svn checkout http://migrid.googlecode.com/svn/trunk/ %s'"\
         % (user, home)
    print 'sudo chown %s:%s %s' % (user, group, server_conf)
    print 'sudo cp -f -p %s %s/' % (server_conf, server_dir)

    # Only add non-directory paths manually and leave the rest to
    # checkconf.py below

    print "sudo su - %s -c 'mkfifo \\\n\t%s/server.stdin'" % (user,
            server_dir)
    print "sudo su - %s -c 'mkfifo \\\n\t%s/notify.stdin'" % (user,
            server_dir)
    print "sudo su - %s -c '%s/mig/server/checkconf.py'" % (user, home)

    print """
#############################################################
Created %s in group %s with pw %s
Reserved ports:
HTTP:\t\t%d
HTTPS:\t\t%d
EXTRA:\t\t%d

The EXTRA port is not used by MiG, so it can be used for
testing any additional daemons.

The dedicated apache server can be started with the command:
sudo %s/%s start

#############################################################
"""\
         % (
        user,
        group,
        pw,
        http_port,
        https_port,
        extra_port,
        apache_dir,
        os.path.basename(apache_initd_script),
        )
    return True


# ## Main ###

argc = len(sys.argv)
debug_mode = True
if argc <= 1:
    print 'Usage: %s LOGIN [LOGINS...]' % sys.argv[0]
    sys.exit(1)

for login in sys.argv[1:]:
    print '# Creating a unprivileged account for %s' % login
    create_user(login, login, debug=debug_mode)

sys.exit(0)
