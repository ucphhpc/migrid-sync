#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# install - MiG server install helpers
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Install helpers:

Generate the configurations for a custom MiG server installation.
Creates MiG server and Apache configurations to fit the provided settings.

Create MiG developer account with dedicated web server and daemons.
"""

import base64
import crypt
import datetime
import hashlib
import os
import re
import random
import socket
import sys

from shared.defaults import default_http_port, default_https_port
from shared.safeeval import subprocess_call, subprocess_popen, subprocess_pipe

def fill_template(template_file, output_file, settings, eat_trailing_space=[]):
    """Fill a configuration template using provided settings dictionary"""
    try:
        template = open(template_file, 'r')
        contents = template.read()
        template.close()
    except Exception, err:
        print 'Error: reading template file %s: %s' % (template_file,
                err)
        return False

    # print "template read:\n", output

    for (variable, value) in settings.items():
        suffix = ''
        if variable in eat_trailing_space:
            suffix = '\s{0,1}'
        contents = re.sub(variable + suffix, value, contents)

    # print "output:\n", contents

    # print "writing specific contents to %s" % (output_file)

    try:
        output = open(output_file, 'w')
        output.write(contents)
        output.close()
    except Exception, err:
        print 'Error: writing output file %s: %s' % (output_file, err)
        return False
    return True

def generate_confs(
    generateconfs_command=' '.join(sys.argv),
    source=os.path.dirname(sys.argv[0]),
    destination=os.path.dirname(sys.argv[0]),
    base_fqdn='localhost',
    public_fqdn='localhost',
    cert_fqdn='localhost',
    oid_fqdn='localhost',
    sid_fqdn='localhost',
    io_fqdn='localhost',
    user='mig',
    group='mig',
    apache_version='2.2',
    apache_etc='/etc/apache2',
    apache_run='/var/run',
    apache_lock='/var/lock',
    apache_log='/var/log/apache2',
    mig_code='/home/mig/mig',
    mig_state='/home/mig/state',
    mig_certs='/home/mig/certs',
    enable_sftp='True',
    enable_davs='True',
    enable_ftps='True',
    enable_wsgi='True',
    wsgi_procs='10',
    enable_sandboxes='True',
    enable_vmachines='True',
    enable_sharelinks='True',
    enable_transfers='True',
    enable_freeze='True',
    enable_preview='False',
    enable_hsts='',
    enable_vhost_certs='',
    enable_seafile='False',
    enable_duplicati='False',
    enable_imnotify='False',
    enable_dev_accounts='False',
    enable_openid='True',
    openid_providers='',
    daemon_keycert='',
    daemon_pubkey='',
    daemon_show_address='',
    alias_field='',
    signup_methods='extcert',
    login_methods='extcert',
    hg_path='',
    hgweb_scripts='',
    trac_admin_path='',
    trac_ini_path='',
    public_port=default_http_port,
    cert_port=default_https_port,
    oid_port=default_https_port+1,
    sid_port=default_https_port+2,
    user_clause='User',
    group_clause='Group',
    listen_clause='#Listen',
    serveralias_clause='#ServerAlias',
    distro='Debian',
    landing_page='/cgi-bin/dashboard.py',
    skin='migrid-basic',
    ):
    """Generate Apache and MiG server confs with specified variables"""

    # Read out dictionary of args with defaults and overrides
    
    expanded = locals()

    user_dict = {}
    user_dict['__GENERATECONFS_COMMAND__'] = generateconfs_command
    user_dict['__BASE_FQDN__'] = base_fqdn
    user_dict['__PUBLIC_FQDN__'] = public_fqdn
    user_dict['__CERT_FQDN__'] = cert_fqdn
    user_dict['__OID_FQDN__'] = oid_fqdn
    user_dict['__SID_FQDN__'] = sid_fqdn
    user_dict['__IO_FQDN__'] = io_fqdn
    user_dict['__USER__'] = user
    user_dict['__GROUP__'] = group
    user_dict['__PUBLIC_PORT__'] = str(public_port)
    user_dict['__CERT_PORT__'] = str(cert_port)
    user_dict['__OID_PORT__'] = str(oid_port)
    user_dict['__SID_PORT__'] = str(sid_port)
    user_dict['__MIG_BASE__'] = os.path.dirname(mig_code.rstrip(os.sep))
    user_dict['__MIG_CODE__'] = mig_code
    user_dict['__MIG_STATE__'] = mig_state
    user_dict['__MIG_CERTS__'] = mig_certs
    user_dict['__APACHE_VERSION__'] = apache_version
    user_dict['__APACHE_ETC__'] = apache_etc
    user_dict['__APACHE_RUN__'] = apache_run
    user_dict['__APACHE_LOCK__'] = apache_lock
    user_dict['__APACHE_LOG__'] = apache_log
    user_dict['__ENABLE_SFTP__'] = enable_sftp
    user_dict['__ENABLE_DAVS__'] = enable_davs
    user_dict['__ENABLE_FTPS__'] = enable_ftps
    user_dict['__ENABLE_WSGI__'] = enable_wsgi
    user_dict['__WSGI_PROCS__'] = wsgi_procs
    user_dict['__ENABLE_SANDBOXES__'] = enable_sandboxes
    user_dict['__ENABLE_VMACHINES__'] = enable_vmachines
    user_dict['__ENABLE_SHARELINKS__'] = enable_sharelinks
    user_dict['__ENABLE_TRANSFERS__'] = enable_transfers
    user_dict['__ENABLE_FREEZE__'] = enable_freeze
    user_dict['__ENABLE_PREVIEW__'] = enable_preview
    user_dict['__ENABLE_HSTS__'] = enable_hsts
    user_dict['__ENABLE_VHOST_CERTS__'] = enable_vhost_certs
    user_dict['__ENABLE_SEAFILE__'] = enable_seafile
    user_dict['__ENABLE_DUPLICATI__'] = enable_duplicati
    user_dict['__ENABLE_IMNOTIFY__'] = enable_imnotify
    user_dict['__ENABLE_DEV_ACCOUNTS__'] = enable_dev_accounts
    user_dict['__ENABLE_OPENID__'] = enable_openid
    # Default to first OpenID provider
    openid_provider_list = openid_providers.split() or ['']
    user_dict['__OPENID_PROVIDER_BASE__'] = openid_provider_list[0]
    user_dict['__OPENID_PROVIDER_ID__'] = openid_provider_list[0]
    user_dict['__OPENID_ALL_PROVIDER_IDS__'] = openid_providers
    user_dict['__DAEMON_KEYCERT__'] = daemon_keycert
    user_dict['__DAEMON_PUBKEY__'] = daemon_pubkey
    user_dict['__DAEMON_KEYCERT_SHA256__'] = ''
    user_dict['__DAEMON_PUBKEY_MD5__'] = ''
    user_dict['__DAEMON_PUBKEY_SHA256__'] = ''
    user_dict['__DAEMON_SHOW_ADDRESS__'] = daemon_show_address
    user_dict['__ALIAS_FIELD__'] = alias_field
    user_dict['__SIGNUP_METHODS__'] = signup_methods
    user_dict['__LOGIN_METHODS__'] = login_methods
    user_dict['__HG_PATH__'] = hg_path
    user_dict['__HGWEB_SCRIPTS__'] = hgweb_scripts
    user_dict['__TRAC_ADMIN_PATH__'] = trac_admin_path
    user_dict['__TRAC_INI_PATH__'] = trac_ini_path
    user_dict['__USER_CLAUSE__'] = user_clause
    user_dict['__GROUP_CLAUSE__'] = group_clause
    user_dict['__LISTEN_CLAUSE__'] = listen_clause
    user_dict['__SERVERALIAS_CLAUSE__'] = serveralias_clause
    user_dict['__DISTRO__'] = distro
    user_dict['__LANDING_PAGE__'] = landing_page
    user_dict['__SKIN__'] = skin

    # Apache fails on duplicate Listen directives so comment in that case
    port_list = [cert_port, oid_port, sid_port]
    fqdn_list = [cert_fqdn, oid_fqdn, sid_fqdn]
    same_port = (len(port_list) != len(dict(zip(port_list, port_list)).keys()))
    same_fqdn = (len(fqdn_list) != len(dict(zip(fqdn_list, fqdn_list)).keys()))
    user_dict['__IF_SEPARATE_PORTS__'] = '#'
    if not same_port:
        user_dict['__IF_SEPARATE_PORTS__'] = ''

    if same_fqdn and same_port:
        print """
WARNING: you probably have to use either different fqdn or port settings for
cert, oid and sid based https!
"""

    user_dict['__IF_SEPARATE_PORTS__'] = '#'

    # Switch between apache 2.2 and 2.4 directives to match requested version
    user_dict['__APACHE_RECENT_ONLY__'] = 'Only for apache>=2.4'
    user_dict['__APACHE_PRE2.4_ONLY__'] = 'Only for apache<2.4'
    # We use raw string comparison here which seems to work alright for X.Y.Z
    if user_dict['__APACHE_VERSION__'] >= "2.4":
        user_dict['__APACHE_RECENT__'] = ''
        user_dict['__APACHE_PRE2.4__'] = '#'
    else:
        user_dict['__APACHE_PRE2.4__'] = ''
        user_dict['__APACHE_RECENT__'] = '#'

    # Enable mercurial module in trackers if Trac is available
    user_dict['__HG_COMMENTED__'] = '#'
    if user_dict['__HG_PATH__']:
        user_dict['__HG_COMMENTED__'] = ''

    # Enable WSGI web interface only if explicitly requested
    if user_dict['__ENABLE_WSGI__'].lower() == 'true':
        user_dict['__WSGI_COMMENTED__'] = ''
    else:
        user_dict['__WSGI_COMMENTED__'] = '#'

    # Enable HSTS security improvement only if explicitly requested
    if user_dict['__ENABLE_HSTS__'].lower() == 'true':
        user_dict['__HSTS_COMMENTED__'] = ''
    else:
        user_dict['__HSTS_COMMENTED__'] = '#'

    # Enable vhost-specific certificates only if explicitly requested
    if user_dict['__ENABLE_VHOST_CERTS__'].lower() == 'true':
        user_dict['__VHOSTCERTS_COMMENTED__'] = ''
    else:
        user_dict['__VHOSTCERTS_COMMENTED__'] = '#'

    # Enable Seafile integration only if explicitly requested
    if user_dict['__ENABLE_SEAFILE__'].lower() == 'true':
        user_dict['__SEAFILE_COMMENTED__'] = ''
    else:
        user_dict['__SEAFILE_COMMENTED__'] = '#'

    # Enable Duplicati integration only if explicitly requested
    if user_dict['__ENABLE_DUPLICATI__'].lower() == 'true':
        user_dict['__DUPLICATI_COMMENTED__'] = ''
    else:
        user_dict['__DUPLICATI_COMMENTED__'] = '#'

    # Enable Paraview integration only if explicitly requested
    if user_dict['__ENABLE_PREVIEW__'].lower() == 'true':
        user_dict['__PREVIEW_COMMENTED__'] = ''
    else:
        user_dict['__PREVIEW_COMMENTED__'] = '#'

    dev_suffix = '$(echo ${APACHE_CONFDIR} | sed "s@/etc/${APACHE_DAEMON}@@")'
    if user_dict['__ENABLE_DEV_ACCOUNTS__'].lower() == "true":
        user_dict['__APACHE_SUFFIX__'] = dev_suffix
    else:
        user_dict['__APACHE_SUFFIX__'] = ""

    # Enable OpenID auth module only if openid_providers is given
    if user_dict['__OPENID_PROVIDER_BASE__'].strip():
        user_dict['__OPENID_COMMENTED__'] = ''
    else:
        user_dict['__OPENID_COMMENTED__'] = '#'

    # Enable alternative daemon show address only if explicitly requested
    if user_dict['__DAEMON_SHOW_ADDRESS__']:
        user_dict['__SHOW_ADDRESS_COMMENTED__'] = ''
    else:
        user_dict['__SHOW_ADDRESS_COMMENTED__'] = '#'

    # Auto-fill fingerprints if daemon key is set
    if user_dict['__DAEMON_KEYCERT__']:
        key_path = os.path.expanduser(user_dict['__DAEMON_KEYCERT__'])
        openssl_cmd = ["openssl", "x509", "-noout", "-fingerprint", "-sha256",
                       "-in", key_path]
        try:
            openssl_proc = subprocess_popen(openssl_cmd, stdout=subprocess_pipe)
            raw_sha256 = openssl_proc.stdout.read().strip()
            daemon_keycert_sha256 = raw_sha256.replace("SHA256 Fingerprint=",
                                                       "")
        except Exception, exc:
            print "ERROR: failed to extract sha256 fingerprint of %s: %s" % \
                  (key_path, exc)
        user_dict['__DAEMON_KEYCERT_SHA256__'] = daemon_keycert_sha256
    if user_dict['__DAEMON_PUBKEY__']:
        pubkey_path = os.path.expanduser(user_dict['__DAEMON_PUBKEY__'])
        try:
            pubkey_fd = open(pubkey_path)
            pubkey = pubkey_fd.read()
            pubkey_fd.close()
        except Exception, exc:
            print "Failed to read provided daemon key: %s" % exc
        # The desired values are hashes of the base64 encoded actual key 
        try:
            b64_key = base64.b64decode(pubkey.strip().split()[1].encode('ascii'))
            raw_md5 = hashlib.md5(b64_key).hexdigest()
            # reformat into colon-spearated octets
            daemon_pubkey_md5 = ':'.join(a+b for a, b in zip(raw_md5[::2],
                                                             raw_md5[1::2]))
            raw_sha256 = hashlib.sha256(b64_key).digest()
            daemon_pubkey_sha256 = base64.b64encode(raw_sha256).rstrip('=')
        except Exception, exc:
            print "ERROR: failed to extract fingerprints of %s : %s" % \
                  (pubkey_path, exc)
        user_dict['__DAEMON_PUBKEY_MD5__'] = daemon_pubkey_md5
        user_dict['__DAEMON_PUBKEY_SHA256__'] = daemon_pubkey_sha256
        
    # Enable Debian/Ubuntu specific lines only there
    if user_dict['__DISTRO__'].lower() in ('ubuntu', 'debian'):
        user_dict['__NOT_DEB_COMMENTED__'] = ''
        user_dict['__IS_DEB_COMMENTED__'] = '#'
        user_dict['__APACHE_DAEMON__'] = 'apache2'
    else:
        user_dict['__NOT_DEB_COMMENTED__'] = '#'
        user_dict['__IS_DEB_COMMENTED__'] = ''
        user_dict['__APACHE_DAEMON__'] = 'httpd'
        

    # Only set ID sub url if openid_providers is set - trailing slash matters
    if user_dict['__OPENID_PROVIDER_BASE__']:
        user_dict['__OPENID_PROVIDER_ID__'] = os.path.join(openid_providers[0],
                                                           'id') + os.sep
        user_dict['__OPENID_ALL_PROVIDER_IDS__'] = ' '.join(
            [os.path.join(oid_provider, 'id') + os.sep for oid_provider in \
             openid_providers.split()])
        
    try:
        os.makedirs(destination)
    except OSError:
        pass

    # Implicit ports if they are standard: cleaner and removes double hg login
    user_dict['__PUBLIC_URL__'] = 'http://%(__PUBLIC_FQDN__)s' % user_dict
    if str(public_port) != str(default_http_port):
        print "adding explicit public port (%s)" % [public_port,
                                                    default_http_port]
        user_dict['__PUBLIC_URL__'] += ':%(__PUBLIC_PORT__)s' % user_dict
    user_dict['__CERT_URL__'] = 'https://%(__CERT_FQDN__)s' % user_dict
    if str(cert_port) != str(default_https_port):
        print "adding explicit cert port (%s)" % [cert_port, default_https_port]
        user_dict['__CERT_URL__'] += ':%(__CERT_PORT__)s' % user_dict
    user_dict['__OID_URL__'] = 'https://%(__OID_FQDN__)s' % user_dict
    if str(oid_port) != str(default_https_port):
        print "adding explicit oid port (%s)" % [oid_port, default_https_port]
        user_dict['__OID_URL__'] += ':%(__OID_PORT__)s' % user_dict
    user_dict['__SID_URL__'] = 'https://%(__SID_FQDN__)s' % user_dict
    if str(sid_port) != str(default_https_port):
        print "adding explicit sid port (%s)" % [sid_port, default_https_port]
        user_dict['__SID_URL__'] += ':%(__SID_PORT__)s' % user_dict

    # Generate random hex salt for scrambling saved digest credentials
    digest_salt = base64.b16encode(os.urandom(16))
    user_dict['__DIGEST_SALT__'] = digest_salt

    # Greedy match trailing space for all the values to uncomment stuff
    strip_trailing_space = ['__IF_SEPARATE_PORTS__', '__APACHE_PRE2.4__',
                            '__APACHE_RECENT__']
    for key in user_dict.keys():
        if key.endswith('_COMMENTED__'):
            strip_trailing_space.append(key)

    # Collect final variable values for log
    sorted_keys = user_dict.keys()
    sorted_keys.sort()
    variable_lines = '\n'.join(["%s : %s" % (i.strip('_'), user_dict[i]) \
                                for i in sorted_keys])
    user_dict['__GENERATECONFS_VARIABLES__'] = variable_lines
        
    # modify this list when adding/removing template->target  
    replacement_list = [
        ("generateconfs-template.log", "generateconfs.log"),
        ("apache-envs-template.conf", "envvars"),
        ("apache-apache2-template.conf", "apache2.conf"),
        ("apache-httpd-template.conf", "httpd.conf"),
        ("apache-ports-template.conf", "ports.conf"),
        ("apache-MiG-template.conf", "MiG.conf"),
        ("apache-mimic-deb-template.conf", "mimic-deb.conf"),
        ("apache-init.d-deb-template", "apache-%s" % user),
        ("apache-MiG-template.conf", "MiG.conf"),
        ("apache-service-template.conf", "apache2.service"),
        ("trac-MiG-template.ini", "trac.ini"),
        ("logrotate-MiG-template", "logrotate-migrid"),
        ("MiGserver-template.conf", "MiGserver.conf"),
        ("static-skin-template.css", "static-skin.css"),
        ("index-template.html", "index.html"),
        # service script for MiG daemons
        ("migrid-init.d-rh-template", "migrid-init.d-rh"),
        ("migrid-init.d-deb-template", "migrid-init.d-deb"),
        # cron helpers
        ("migerrors-template.sh.cronjob", "migerrors"),
        ("migsftpmon-template.sh.cronjob", "migsftpmon"),
        ("migstateclean-template.sh.cronjob", "migstateclean"),
        ("migcheckssl-template.sh.cronjob", "migcheckssl"),
        ]
    for (in_name, out_name) in replacement_list:
        in_path = os.path.join(source, in_name)
        out_path = os.path.join(destination, out_name)
        if os.path.exists(in_path):
            fill_template(in_path, out_path, user_dict, strip_trailing_space)
            # Sync permissions
            os.chmod(out_path, os.stat(in_path).st_mode)
        else:
            print "Skipping missing template: %s" % in_path
    return expanded

def create_user(
    user,
    group,
    ssh_login_group='remotelogin',
    debug=False,
    base_fqdn=socket.getfqdn(),
    public_fqdn=socket.getfqdn(),
    cert_fqdn=socket.getfqdn(),
    oid_fqdn=socket.getfqdn(),    
    sid_fqdn=socket.getfqdn(),
    io_fqdn=socket.getfqdn(),
    ):
    """Create MiG unix user with supplied user and group name and show
    commands to make it a MiG developer account.
    If oid_fqdn and sid_fqdn are set to a fqdn different from the default fqdn
    of this host the apache web server configuration will use the same port for
    cert, oid and sid https access but on diffrent IP adresses. Otherwise it
    will use three different ports on the same address.
    """

    # make sure not to wreak havoc if no user supplied

    if not user:
        print "no user supplied! can't continue"
        return False

    groupadd_cmd = ['groupadd', group]
    print groupadd_cmd
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(groupadd_cmd)
    if status != 0:
        print 'Warning: groupadd exit code %d' % status

    # Don't use 'o'/'0' and 'l'/'1' since they may confuse users

    valid_chars = 'abcdefghijkmnpqrstuvwxyz'\
         + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789'
    pwlen = 8
    pw = ''
    for _ in range(pwlen):
        pw += random.choice(valid_chars)

    # TODO: python does not support md5 passwords - using DES ones
    # from crypt for now

    shell = '/bin/bash'
    enc_pw = crypt.crypt(pw, random.choice(valid_chars)
                          + random.choice(valid_chars))
    useradd_cmd = ['useradd', '-m', '-s %s' % shell, '-p %s' % enc_pw,
                   '-g %s' % group, user]
    print useradd_cmd
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(useradd_cmd)
    if status != 0:
        print 'Warning: useradd exit code %d' % status
    else:
        print '# Created %s in group %s with pw %s' % (user, group, pw)

    home = '/home/%s' % user

    chmod_cmd = ['chmod', '-R', 'g-rwx,o-rwx', home]
    print chmod_cmd
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(chmod_cmd)
    if status != 0:
        print 'Warning: chmod exit code %d' % status
    else:
        print 'Removed global access to %s' % home

    addgroup_cmd = ['addgroup', user, ssh_login_group]
    print addgroup_cmd
    # NOTE: we use command list here to avoid shell requirement
    status = subprocess_call(addgroup_cmd)
    if status != 0:
        print 'Warning: login addgroup exit code %d' % status
    else:
        print '# Added %s to login group %s' % (user, ssh_login_group)

    # NOTE: we use command list here to avoid shell requirement
    idu_proc = subprocess_popen(['id', '-u %s' % user], stdout=subprocess_pipe)
    idu_proc.wait()
    out = idu_proc.stdout.readlines()
    uid_str = out[0].strip()
    # NOTE: we use command list here to avoid shell requirement
    idg_proc = subprocess_popen(['id', '-g %s' % user], stdout=subprocess_pipe)
    idg_proc.wait()
    out = idg_proc.stdout.readlines()
    gid_str = out[0].strip()
    try:
        uid = int(uid_str)
        gid = int(gid_str)
    except Exception, err:
        print 'Error: %s' % err
        if not debug:
            return False

    # print "uid: %d, gid: %d" % (uid, gid)

    reserved_ports = range(4 * uid, 4 * uid + 4)
    public_port, cert_port, oid_port, sid_port = reserved_ports[:4]

    mig_dir = os.path.join(home, 'mig')
    server_dir = os.path.join(mig_dir, 'server')
    state_dir = os.path.join(home, 'state')
    apache_version = '2.2'
    apache_etc = '/etc/apache2'
    apache_dir = '%s-%s' % (apache_etc, user)
    apache_run = '%s/run' % apache_dir
    apache_lock = '%s/lock' % apache_dir
    apache_log = '%s/log' % apache_dir
    cert_dir = '%s/MiG-certificates' % apache_dir
    # We don't necessarily have free ports for daemons
    enable_sftp = 'False'
    enable_davs = 'False'
    enable_ftps = 'False'
    enable_openid = 'False'
    enable_wsgi = 'True'
    wsgi_procs = '5'
    enable_sandboxes = 'True'
    enable_vmachines = 'True'
    enable_sharelinks = 'True'
    enable_transfers = 'True'
    enable_freeze = 'True'
    enable_preview = 'False'
    enable_hsts = 'False'
    enable_vhost_certs = 'False'
    enable_seafile = 'False'
    enable_duplicati = 'False'
    enable_imnotify = 'False'
    enable_dev_accounts = 'False'
    openid_providers = ''
    daemon_keycert = ''
    daemon_pubkey = ''
    daemon_show_address = ''
    alias_field = 'email'
    hg_path = '/usr/bin/hg'
    hgweb_scripts = '/usr/share/doc/mercurial-common/examples/'
    trac_admin_path = '/usr/bin/trac-admin'
    trac_ini_path = '%s/trac.ini' % server_dir

    firewall_script = '/root/scripts/firewall'
    print '# Add the next line to %s and run the script:'\
         % firewall_script
    print 'iptables -A INPUT -p tcp --dport %d:%d -j ACCEPT # webserver: %s'\
         % (reserved_ports[0], reserved_ports[-1], user)

    sshd_conf = '/etc/ssh/sshd_config'
    print """# Unless 'AllowGroups %s' is already included, append %s
# to the AllowUsers line in %s and restart sshd."""\
         % (ssh_login_group, user, sshd_conf)
    print """# Add %s to the sudoers file (visudo) with privileges
# to run apache init script in %s
visudo""" % (user, apache_dir)
    print """# Set disk quotas for %s using reference user quota:
edquota -u %s -p LOGIN_OF_SIMILAR_USER"""\
         % (user, user)
    expire = datetime.date.today()
    expire = expire.replace(year=expire.year + 1)
    print """# Optionally set account expire date for user:
chage -E %s %s"""\
         % (expire, user)
    print """# Attach full name of user to login:
usermod -c 'INSERT FULL NAME HERE' %s"""\
         % user
    print """# Add mount point for sandbox generator:
echo '/home/%s/state/sss_home/MiG-SSS/hda.img      /home/%s/state/sss_home/mnt  auto    user,loop       0       0' >> /etc/fstab"""\
         % (user, user)

    src = os.path.abspath(os.path.dirname(sys.argv[0]))
    dst = os.path.join(src, '%s-confs' % user)

    server_alias = '#ServerAlias'
    if socket.gethostbyname(sid_fqdn) != socket.gethostbyname(oid_fqdn) != \
           socket.gethostbyname(cert_fqdn):
        sid_port = oid_port = cert_port
        server_alias = 'ServerAlias'
    generate_confs(
        ' '.join(sys.argv),
        src,
        dst,
        base_fqdn,
        public_fqdn,
        cert_fqdn,
        oid_fqdn,
        sid_fqdn,
        io_fqdn,
        user,
        group,
        apache_version,
        apache_dir,
        apache_run,
        apache_lock,
        apache_log,
        mig_dir,
        state_dir,
        cert_dir,
        enable_sftp,
        enable_davs,
        enable_ftps,
        enable_wsgi,
        wsgi_procs,
        enable_sandboxes,
        enable_vmachines,
        enable_sharelinks,
        enable_transfers,
        enable_freeze,
        enable_preview,
        enable_hsts,
        enable_vhost_certs,
        enable_seafile,
        enable_duplicati,
        enable_imnotify,
        enable_dev_accounts,
        enable_openid,
        openid_providers,
        daemon_keycert,
        daemon_pubkey,
        daemon_show_address,
        alias_field,
        hg_path,
        hgweb_scripts,
        trac_admin_path,
        trac_ini_path,
        public_port,
        cert_port,
        oid_port,
        sid_port,
        'User',
        'Group',
        '#Listen',
        server_alias,
        )
    apache_envs_conf = os.path.join(dst, 'envvars')
    apache_apache2_conf = os.path.join(dst, 'apache2.conf')
    apache_httpd_conf = os.path.join(dst, 'httpd.conf')
    apache_ports_conf = os.path.join(dst, 'ports.conf')
    apache_mig_conf = os.path.join(dst, 'MiG.conf')
    server_conf = os.path.join(dst, 'MiGserver.conf')
    trac_ini = os.path.join(dst, 'trac.ini')
    apache_initd_script = os.path.join(dst, 'apache-%s' % user)

    settings = {'user': user, 'group': group, 'server_conf': server_conf,
                'trac_ini': trac_ini, 'home': home, 'server_dir': server_dir,
                'base_fqdn': base_fqdn, 'public_fqdn': public_fqdn}
    settings['sudo_cmd'] = 'sudo su - %(user)s -c' % settings

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
    print 'sudo mkdir -p %s %s %s ' % (apache_run, apache_lock, apache_log)

    # allow read access to logs

    print 'sudo chgrp -R %s %s' % (user, apache_log)
    print 'sudo chmod 2755 %s' % apache_log

    print """# Setup MiG for %(user)s:
%(sudo_cmd)s 'ssh-keygen -t rsa -N \"\" -q -f \\
    %(home)s/.ssh/id_rsa'
%(sudo_cmd)s 'cp -f -x \\
    %(home)s/.ssh/{id_rsa.pub,authorized_keys}'
%(sudo_cmd)s 'ssh -o StrictHostKeyChecking=no \\
    %(user)s@%(base_fqdn)s pwd >/dev/null'
%(sudo_cmd)s 'svn checkout https://svn.code.sf.net/p/migrid/code/trunk/ %(home)s'
sudo chown %(user)s:%(group)s %(server_conf)s %(trac_ini)s
sudo cp -f -p %(server_conf)s %(trac_ini)s %(server_dir)s/
""" % settings
        
    # Only add non-directory paths manually and leave the rest to
    # checkconf.py below

    print """%(sudo_cmd)s 'mkfifo %(server_dir)s/server.stdin'
%(sudo_cmd)s 'mkfifo %(server_dir)s/notify.stdin'
%(sudo_cmd)s '%(server_dir)s/checkconf.py'
""" % settings

    used_ports = [public_port, cert_port, oid_port, sid_port]
    extra_ports = [port for port in reserved_ports if not port in used_ports]
    print """
#############################################################
Created %s in group %s with pw %s
Reserved ports:
HTTP:\t\t%d
HTTPS certificate users:\t\t%d
HTTPS openid users:\t\t%d
HTTPS resources:\t\t%d
Extra ports:\t\t%s

The dedicated apache server can be started with the command:
sudo %s/%s start

#############################################################
"""\
         % (
        user,
        group,
        pw,
        public_port,
        cert_port,
        oid_port,
        sid_port,
        ', '.join(["%d" % port for port in extra_ports]),
        apache_dir,
        os.path.basename(apache_initd_script),
        )
    return True
