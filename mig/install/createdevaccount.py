#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createdevaccount - [insert a few words of module description on this line]
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


"""Add a non-privileged user with access to a personal MiG server.
Still needs some manual setup of apache, sudo and iptables
afterwards...
"""

# IMPORTANT: Run script with sudo or as root

import sys
import os
import re
import whrandom
import crypt


def fill_template(template_file, output_file, dictionary):
    try:
        template = open(template_file, 'r')
        contents = template.read()
        template.close()
    except Exception, err:
        print "Error: reading template file %s: %s" % (template_file,
                                                       err)
        return False

    # print "template read:\n", output
    for variable, value in dictionary.items():
        contents = re.sub(variable, value, contents)
    # print "output:\n", contents
        
    # print "writing specific contents to %s" % (output_file)
    try:
        output = open(output_file, 'w')
        output.write(contents)
        output.close()
    except Exception, err:
        print "Error: writing output file %s: %s" % (output_file, err)
        return False

    return True

def create_user(user, group, ssh_login_group="remotelogin", debug=False):
    """Create unix user with supplied user and group name"""
    # make sure not to wreak havoc if no user supplied
    if not user:
        print "no user supplied! can't continue"
        return False
        
    print "groupadd %s" % (group)
    status = os.system("groupadd %s" % (group)) >> 8
    if status != 0:
        print "Warning: exit code %d" % (status)

    # Don't use 'o'/'0' and 'l'/'1' since they may confuse users
    valid_chars = "abcdefghijkmnpqrstuvwxyz" + \
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789"
    pwlen = 8
    pw = ""
    for idx in range(pwlen):
        pw += whrandom.choice(valid_chars)

    # TODO: python does not support md5 passwords - using DES ones
    # from crypt for now
    shell = "/bin/bash"
    enc_pw = crypt.crypt(pw, whrandom.choice(valid_chars) + \
                         whrandom.choice(valid_chars))
    print "useradd -m -s %s -p %s -g %s %s" % (shell, enc_pw, group, user)
    status = os.system("useradd -m -s %s -p %s -g %s %s" % \
                       (shell, enc_pw, group, user)) >> 8
    if status != 0:
        print "Warning: exit code %d" % (status)
    else:
        print "# Created %s in group %s with pw %s" % (user, group, pw)

    home = "/home/%s" % (user)

    print "chmod -R o-rwx %s" % (home)
    status = os.system("chmod -R o-rwx %s" % (home)) >> 8
    if status != 0:
        print "Warning: exit code %d" % (status)
    else:
        print "Removed global access to %s" % (home)

    print "addgroup %s %s" % (user, ssh_login_group)
    status = os.system("addgroup %s %s" % \
                       (user, ssh_login_group)) >> 8
    if status != 0:
        print "Warning: exit code %d" % (status)
    else:
        print "# Added %s to group %s" % (user, ssh_login_group)

    out = os.popen("id -u %s" % (user)).readlines()
    uid_str = out[0].strip()
    out = os.popen("id -g %s" % (user)).readlines()
    gid_str = out[0].strip()
    try:
        uid = int(uid_str)
        gid = int(gid_str)
    except Exception, err:
        print "Error: %s" % err
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

    mig_dir = home + "/mig"
    apache_etc = "/etc/apache"
    apache_dir = apache_etc + "-%s" % (user)
    apache_run = apache_dir + "/run"
    apache_log = apache_dir + "/log"
    cert_dir = apache_dir +"/MiG-certificates"

    firewall_script = "/root/scripts/firewall"
    print "# Add the next line to %s and run the script:" % \
          firewall_script
    print "iptables -A INPUT -p tcp --dport %d:%d -j ACCEPT # webserver: %s" % \
          (http_port, extra_port, user)

    sshd_conf = "/etc/ssh/sshd_config"
    print """# Unless 'AllowGroups %s' is already included, append %s
# to the AllowUsers line in %s and restart sshd.""" % \
          (ssh_login_group, user, sshd_conf)
    print """# Add %s to the sudoers file (visudo) with privileges
# to run apache init script in %s""" % (user, apache_dir)
    print """# Set disk quotas for %s using reference user quota:
edquota -u %s -p LOGIN_OF_SIMILAR_USER""" % (user, user)
    print """# Attach full name of user to login:
usermod -c 'INSERT FULL NAME HERE' %s""" % user
    
    user_dict = {}
    user_dict["__USER__"] = user
    user_dict["__GROUP__"] = group
    user_dict["__HTTP_PORT__"] = str(http_port)
    user_dict["__HTTPS_PORT__"] = str(https_port)
    user_dict["__EXTRA_PORT__"] = str(extra_port)
    user_dict["__HOME__"] = home
    user_dict["__MIG_HOME__"] = mig_dir
    user_dict["__APACHE_HOME__"] = apache_dir
    user_dict["__APACHE_RUN__"] = apache_run
    user_dict["__APACHE_LOG__"] = apache_log
    user_dict["__CERT_HOME__"] = cert_dir
    
    apache_mig_template = "./apache-MiG-template.conf"
    apache_mig_conf = "./MiG-%s.conf" % (user)
    fill_template(apache_mig_template, apache_mig_conf, user_dict)
    apache_httpd_template = "./apache-httpd-template.conf"
    apache_httpd_conf = "./httpd-%s.conf" % (user)
    fill_template(apache_httpd_template, apache_httpd_conf,
                  user_dict)
    apache_initd_template = "./apache-init.d-template"
    apache_initd_script = "apache-%s" % (user)
    fill_template(apache_initd_template, apache_initd_script,
                  user_dict)
    os.chmod(apache_initd_script, 0700)
    print "# Clone %s to %s and put config files there:" % \
          (apache_etc, apache_dir)
    print "sudo cp -r -u -d -x %s %s" % (apache_etc, apache_dir)
    print "sudo cp -f -d %s \\\n\t%s/httpd.conf" % (apache_httpd_conf,
                                              apache_dir)
    print "sudo rm -f %s/conf.d/*" % apache_dir
    print "sudo cp -f -d %s %s/conf.d/" % (apache_mig_conf,
                                           apache_dir)
    print "sudo cp -f -d %s %s/" % (apache_initd_script,
                                    apache_dir)
    print "sudo mkdir -p %s %s" % (apache_run, apache_log)
    # allow read access to logs
    print "sudo chgrp -R %s %s" % (user, apache_log)
    print "sudo chmod 2755 %s" % apache_log

    print "# Setup MiG for %s:" % (user)
    print "sudo su - %s -c 'ssh-keygen -t rsa -N \"\" -q -f \\\n\t%s/.ssh/id_rsa'" % (user, home)
    print "sudo su - %s -c 'cp -f -x \\\n\t%s/.ssh/{id_rsa.pub,authorized_keys}'" % (user, home)
    print "sudo su - %s -c 'ssh -o StrictHostKeyChecking=no \\\n\t%s@`hostname -f` pwd >/dev/null'" % (user, user)
    print "sudo su - %s -c 'cp -r -u -d -x ~mig/public/mig \\\n\t%s/'" % \
          (user, home)

    server_template = "MiGserver-template.conf"
    server_conf = "MiGserver-%s.conf" % (user)
    server_dir = mig_dir + "/server"
    fill_template(server_template, server_conf, user_dict)
    try:
        os.chown(server_conf, uid, gid)
    except Exception, err:
        print "Error: %s" % err
        if not debug:
            return False
        
    print "sudo cp -f -p %s %s/" % (server_conf, server_dir)
    print "sudo su - %s -c 'ln -s \\\n\t%s \\\n\t%s'" % \
          (user, server_dir + "/" + server_conf,
           server_dir + "/MiGserver.conf")
    # Only add non-directory paths manually and leave the rest to
    # checkconf.py below
    print "sudo su - %s -c 'mkfifo -m 600 \\\n\t%s/mig/server/server.stdin'" % \
          (user, home)
    print "sudo su - %s -c 'mkfifo -m 600 \\\n\t%s/mig/server/notify.stdin'" % \
          (user, home)
    print "sudo su - %s -c '%s/mig/server/checkconf.py'" % \
          (user, home)

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
""" % (user, group, pw, http_port, https_port, extra_port,
       apache_dir, apache_initd_script)
    return True


### Main ###
argc = len(sys.argv)
debug_mode = True
if argc <= 1:
	print "Usage: %s LOGIN [LOGINS...]" % (sys.argv[0])
	sys.exit(1)


for login in sys.argv[1:]:
	print "# Creating a non-privileged account for %s" % login
        create_user(login, login, debug=debug_mode)
        
sys.exit(0)
