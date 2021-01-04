#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# setup - back end for the client access setup page
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Provide all the client access setup subpages"""
from __future__ import absolute_import

import os
import time

from mig.shared import returnvalues
from mig.shared.accountstate import account_expire_info
from mig.shared.auth import get_twofactor_secrets
from mig.shared.base import client_alias, client_id_dir, extract_field, get_xgi_bin, \
    get_short_id, requested_url_base
from mig.shared.defaults import seafile_ro_dirname, duplicati_conf_dir, csrf_field, \
    duplicati_protocol_choices, duplicati_schedule_choices, keyword_all, \
    AUTH_MIG_OID, AUTH_EXT_OID, AUTH_MIG_OIDC, AUTH_EXT_OIDC
from mig.shared.duplicatikeywords import get_duplicati_specs
from mig.shared.editing import cm_css, cm_javascript, cm_options, wrap_edit_area
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, console_log_javascript, \
    twofactor_wizard_html, twofactor_wizard_js, twofactor_token_html, \
    save_settings_js, save_settings_html
from mig.shared.httpsclient import detect_client_auth
from mig.shared.init import initialize_main_variables, find_entry, extract_menu
from mig.shared.pwhash import parse_password_policy
from mig.shared.safeinput import html_escape, password_min_len, password_max_len, \
    valid_password_chars
from mig.shared.settings import load_settings, load_ssh, load_davs, load_ftps, \
    load_seafile, load_duplicati, load_cloud, load_twofactor
from mig.shared.twofactorkeywords import get_twofactor_specs
from mig.shared.useradm import create_alias_link


ssh_edit = cm_options.copy()
davs_edit = cm_options.copy()
ftps_edit = cm_options.copy()
seafile_edit = cm_options.copy()
duplicati_edit = cm_options.copy()
duplicati_edit['mode'] = 'htmlmixed'
cloud_edit = cm_options.copy()
twofactor_edit = cm_options.copy()


def signature():
    """Signature of the main function"""

    defaults = {'topic': ['twofactor']}
    return ['html_form', defaults]


def sftp_help_snippet(configuration, topics=[keyword_all], fill_vars=None):
    """Genererates a HTML template with the corresponding help topic.
    The optional fill_vars is used to expand variables if provided.
    """
    html = ''
    if keyword_all in topics or 'drive' in topics:
        html += '''
<h3>SSHFS/SFTP Network Drive</h3>
<div class="help-entry sftp-drive-help">
<p>
SSHFS/SFTP enables secure network drive access to your remote %(site)s data
using the SFTP protocol. SSHFS is available on all popular computer platforms
and allows you to use your usual programs to work directly on your remote
%(site)s files and folders over the Internet.
</p>
<h4>SSHFS Drive on Windows</h4>
<p>
Download and install
<a href="https://github.com/billziss-gh/sshfs-win#----sshfs-win--sshfs-for-windows"
target="_blank">WinFsp and SSHFS-Win</a> as described under Installation.
Then in your Windows file manager open the Map network drive wizard. Enter
<var>%(sshfs_netloc)s</var> in the Folder field and click Finish.
Finally supply your username <var>%(username)s</var> and your chosen password
when prompted for login.
</p>
<h4>SSHFS Drive on Mac OSX</h4>
<p>
Download and install the
<a href="https://osxfuse.github.io/">macFUSE and SSHFS</a> Stable Release
packages.<br/>
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:</p>
<textarea rows=8 cols=78 class="code" readonly=readonly>Host %(sftp_server)s %(mount_name)s
Hostname %(sftp_server)s
VerifyHostKeyDNS %(hostkey_from_dns)s
User %(username)s
Port %(sftp_port)s
# Uncomment next line to use your private key in ~/.ssh/id_rsa
# IdentityFile ~/.ssh/id_rsa</textarea>
<br/>
Then you can mount with the sshfs command to access your %(site)s home:
</p>
<pre class="codeblock">
mkdir -p %(mount_dir)s && \\
  sshfs %(sftp_server)s: %(mount_dir)s -o idmap=user -o reconnect \\
    -o iosize=262144
</pre>
<p>where the iosize argument is used to tune read and write buffers for better
performance.</p>
<p>You can also integrate sshfs with ordinary mounts by adding a line like:</p>
<pre class="codeblock">
sshfs#%(username)s@%(sftp_server)s: /home/USER/%(mount_dir)s fuse noauto,user,idmap=user,reconnect,port=%(sftp_port)d,iosize=262144 0 0
</pre>
<p>
to your /etc/fstab .
</p>
<h4>SFTP Drive on Linux/UN*X</h4>
<p>
Some Linux distributions natively integrate SFTP drive access in their file
manager, so that one can connect %(site)s without installing anything. In the
file manager you can Open Location or similar (Ctrl+L), insert<br/>
<var>%(sftp_uri)s</var> in the address field and enter your username
<var>%(username)s</var> and chosen password when prompted for login.
</p>
<h4>SSHFS Drive Linux/UN*X</h4>
<p>
On Linux/UN*X it also generally possible to install and use the
low-level sshfs program to mount %(site)s as network drive.<br/>
Install <a href="https://github.com/libfuse/sshfs#sshfs">SSHFS</a> including
the FUSE and OpenSSH dependencies using your favorite software/package manager
or the downloads online.<br/>
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:</p>
<textarea rows=8 cols=78 class="code" readonly=readonly>Host %(sftp_server)s %(mount_name)s
Hostname %(sftp_server)s
VerifyHostKeyDNS %(hostkey_from_dns)s
User %(username)s
Port %(sftp_port)s
# Uncomment next line to use your private key in ~/.ssh/id_rsa
# IdentityFile ~/.ssh/id_rsa</textarea>
<br/>
Then you can mount with the sshfs command to access your %(site)s home:
</p>
<pre class="codeblock">
mkdir -p %(mount_dir)s && \\
  sshfs %(sftp_server)s: %(mount_dir)s -o idmap=user -o reconnect
</pre>
<p>For older sshfs/fuse versions you may want to add <pre>-o big_writes</pre>
to the sshfs command in case you experience very slow writes.</p>
<p>You can also integrate sshfs with ordinary mounts by adding a line like:</p>
<pre class="codeblock">
sshfs#%(username)s@%(sftp_server)s: /home/USER/%(mount_dir)s fuse noauto,user,idmap=user,reconnect,port=%(sftp_port)d 0 0
</pre>
<p>
to your /etc/fstab .
</p>
</div>
    '''
    if keyword_all in topics or 'client' in topics:
        html += '''
<h3>Graphical SFTP File Transfers</h3>
<div class="help-entry sftp-client-help">
<p>
SFTP enables basic file transfers to and from your %(site)s storage. That
is, you can use a client to upload and download files and folders.
</p>
<h4>FileZilla on Windows, Mac OSX or Linux/UN*X</h4>
<p>The FileZilla client is known to generally work for graphical access to your
%(site)s home over SFTP. It runs on all popular computer platforms and in the
<a href="http://portableapps.com/apps/internet/filezilla_portable">portable
version</a> it does not even require install privileges.</p>
<p>
Enter the following values in the FileZilla Site Manager:</p>
<ul>
<li>Host <var>%(sftp_server)s</var></li>
<li>Port <var>%(sftp_port)s</var></li>
<li>Protocol <var>SFTP</var></li>
<li>User <var>%(username)s</var></li>
<li>Password <var>[YOUR CHOSEN PASSWORD]</var> (leave empty for ssh key from key-agent)</li>
</ul>

<h4>Other Graphical Clients</h4>
<p>Other graphical clients like <a href="https://winscp.net/eng/index.php">
WinSCP</a>, <a href="https://cyberduck.io/">CyberDuck</a> and
<a href="https://www.gftp.org/">gFTP</a> should work just as well.
</p>
</div>
'''
    if keyword_all in topics or 'terminal' in topics:
        html += '''
<h3>Command-Line SFTP Access</h3>
<div class="help-entry sftp-terminal-help">
<h4>SFTP/LFTP on Windows, Mac OSX and Linux/UN*X</h4>
<p>
Install <a href="https://www.openssh.com/">OpenSSH</a> or
<a href="https://lftp.yar.ru/">LFTP</a> using your favorite package manager.
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:</p>
<textarea rows=8 cols=78 class="code" readonly=readonly>Host %(sftp_server)s %(mount_name)s
Hostname %(sftp_server)s
VerifyHostKeyDNS %(hostkey_from_dns)s
User %(username)s
Port %(sftp_port)s
# Uncomment next line to use your private key in ~/.ssh/id_rsa
# IdentityFile ~/.ssh/id_rsa</textarea>
<p>From then on you can use sftp and lftp to access your %(site)s home:</p>
<pre class="codeblock">
sftp -B 258048 %(sftp_server)s

lftp -e "set net:connection-limit %(max_sessions)d" -p %(sftp_port)s \\
  sftp://%(sftp_server)s
</pre>
<p>Other command-line SFTP clients like PuTTY (psftp) also work.</p>

<h4>Rclone on Windows, Mac OSX and Linux/UN*X</h4>
<p>Last but not least you can install and use
<a href="https://rclone.org/">Rclone</a> to e.g. synchronize files
and folders between %(site)s and your computer (like rsync) or mount your
%(site)s home as a network drive.<br/>
For recent versions you configure rclone with the command:</p>
<pre class="codeblock">
rclone config create %(mount_name)s sftp host %(sftp_server)s \\
  port %(sftp_port)s user %(username)s pass "[YOUR CHOSEN PASSWORD]"
</pre>
<p>
Whereas older versions require interactively entering the same options in the
config creator launched with:
</p>
<pre class="codeblock">
rclone config
</pre>
<p>
Once set up you can list, download, upload and sync files and folders
or even mount as network drive:</p>
<pre class="codeblock">
rclone lsl --max-depth 1 %(mount_name)s:
rclone copy %(mount_name)s:REMOTE_PATH LOCAL_PATH
rclone copy LOCAL_PATH %(mount_name)s:REMOTE_PATH
rclone sync LOCAL_PATH %(mount_name)s:REMOTE_PATH
rclone sync %(mount_name)s:REMOTE_PATH LOCAL_PATH

mkdir -p %(mount_dir)s && \\
  rclone mount %(mount_name)s: %(mount_dir)s
</pre>
<p>
More about another tried and trusted way of mounting %(site)s as a network
drive with SSHFS above.
</p>
</div>
    '''
    if fill_vars is not None and isinstance(fill_vars, dict):
        return html % fill_vars
    else:
        return html


def davs_help_snippet(configuration, topics=[keyword_all], fill_vars=None):
    """Genererates a HTML template with the corresponding help topic.
    The optional fill_vars is used to expand variables if provided.
    """
    html = ''
    if keyword_all in topics or 'drive' in topics:
        html += '''
<h3>WebDAVS Network Drive</h3>
<div class="help-entry davs-drive-help">
<p>
All common computer platforms integrate secure network drive access to your
remote %(site)s data using WebDAVS. That allows you to use your usual programs
to work directly on your remote %(site)s files and folders over the Internet.
</p>
<h4>WebDAVS Drive Integration on Windows</h4>
<p>
In your Windows file manager open the Map network drive wizard. Enter
<var>%(davs_url)s</var> in the Folder field and click Finish. Finally supply
your username <var>%(username)s</var> and your chosen password when prompted for
login.
</p>
<h4>WebDAVS Drive Integration on Mac OSX</h4>
<p>
On Mac OSX open Finder and in the menu under Go you select Connect to Server.
Then enter <var>%(davs_url)s</var> in the Server address field. Click Connect and
supply your username <var>%(username)s</var> and your chosen password when prompted
for login.
</p>
<h4>WebDAVS Drive Integration on Linux/UN*X</h4>
<p>
In your favorite file manager on Linux/UN*X find Open Location or similar (Ctrl-L).
Then insert <var>%(davs_url)s</var> in the address field. Click Connect and
supply your username <var>%(username)s</var> and your chosen password when
prompted for login. Please note that a few file managers like Thunar require
the address to use <var>davs://</var> rather than <var>https://</var> in the
address above.
</p>
</div>
    '''
    if keyword_all in topics or 'client' in topics:
        html += '''
<h3>Graphical WebDAVS File Transfers</h3>
<div class="help-entry davs-client-help">
<p>In addition to network drive integration in native file managers, various
file transfer programs like <a href="https://winscp.net/eng/index.php">WinSCP
</a> and <a href="https://cyberduck.io/">CyberDuck</a> support upload/download
to and from your %(site)s home using WebDAVS.
</p>
<p>Enter the address <var>%(davs_url)s</var> and fill in the login details when
prompted:</p>
<ul>
<li>Username <var>%(username)s</var></li>
<li>Password <var>[YOUR CHOSEN PASSWORD]</var></li>
</ul>
Most web browsers also support WebDAVS at least for downloading files.
Some web browsers also work with WebDAVS, if you navigate to the address<br/>
<var>%(davs_url)s</var> and enter your username <var>%(username)s</var> and
your chosen password when prompted for login.
</p>
</div>
    '''
    if keyword_all in topics or 'terminal' in topics:
        html += '''
<h3>Command-Line WebDAVS Access</h3>
<div class="help-entry davs-terminal-help">
<h3>Cadaver and FuseDAV on Mac OSX and Linux/UN*X</h3>
<p>Save something like the following lines in your local ~/.netrc
to avoid typing the full login details every time:</p>
<textarea rows=4 cols=78 class="code" readonly=readonly>machine %(davs_server)s
login %(username)s
password [YOUR CHOSEN PASSWORD]</textarea>
<p>Then you can install and use e.g. cadaver or fusedav to access your %(site)s
home:</p>
<pre class="codeblock">
cadaver %(davs_url)s

mkdir -p %(mount_dir)s && \\
  fusedav %(davs_url)s %(mount_dir)s -o uid=$(id -u) -o gid=$(id -g)
</pre>
</div>
'''
    if fill_vars is not None and isinstance(fill_vars, dict):
        return html % fill_vars
    else:
        return html


def ftps_help_snippet(configuration, topics=[keyword_all], fill_vars=None):
    """Genererates a HTML template with the corresponding help topic.
    The optional fill_vars is used to expand variables if provided.
    """
    html = ''
    if keyword_all in topics or 'drive' in topics:
        # NOTE: currently n o recommended drive support for FTPS
        html += ''
    if keyword_all in topics or 'client' in topics:
        html += '''
<h3>Graphical FTPS File Transfers</h3>
<div class="help-entry ftps-client-help">
<p>
FTPS enables basic file transfers to and from your %(site)s storage. That
is, you can use a client to upload and download files and folders.
</p>
<h4>FileZilla on Windows, Mac OSX or Linux/UN*X</h4>
<p>The FileZilla client is known to generally work for graphical access to your
%(site)s home over FTPS. It runs on all popular computer platforms and in the
<a href="http://portableapps.com/apps/internet/filezilla_portable">portable
version</a> it does not even require install privileges.</p>
<p>Enter the following values in the FileZilla Site Manager:</p>
<ul>
<li>Host <var>%(ftps_server)s</var></li>
<li>Port <var>%(ftps_ctrl_port)s</var></li>
<li>Protocol <var>FTP</var></li>
<li>Encryption <var>Explicit FTP over TLS</var></li>
<li>User <var>%(username)s</var></li>
<li>Password <var>[YOUR CHOSEN PASSWORD]</var></li>
</ul>
<br/>
<h4>Other Graphical Clients</h4>
<p>Other graphical clients like <a href="https://winscp.net/eng/index.php">
WinSCP</a> and <a href="https://cyberduck.io/">CyberDuck</a> should work as well.
Some web browsers also work, if you navigate to the address<br/>
<var>%(ftps_uri)s</var> and enter your username <var>%(username)s</var> and
your chosen password when prompted for login.
</p>
</div>
    '''
    if keyword_all in topics or 'terminal' in topics:
        html += '''
<h3>Command-Line FTPS Access</h3>
<div class="help-entry ftps-terminal-help">
<h4>LFTP and CurlFTPFS on Mac OSX and Linux/UN*X</h4>
<p>Save something like the following lines in your local ~/.netrc
to avoid typing the full login details every time:</p>
<textarea rows=4 cols=78 class="code" readonly=readonly>machine %(ftps_server)s
login %(username)s
password [YOUR CHOSEN PASSWORD]</textarea>
<p>Then install and use e.g. <a href="https://lftp.yar.ru/">LFTP</a> or
CurlFtpFS to access your %(site)s home:</p>
<pre class="codeblock">
lftp -e "set ftp:ssl-protect-data on; set net:connection-limit %(max_sessions)d" \\
  -p %(ftps_ctrl_port)s %(ftps_server)s

mkdir -p %(mount_dir)s && \\
  curlftpfs -o ssl %(ftps_server)s:%(ftps_ctrl_port)s %(mount_dir)s \\
  -o user=%(username)s -ouid=$(id -u) -o gid=$(id -g) -o no_verify_peer
</pre>
</div>
    '''
    if fill_vars is not None and isinstance(fill_vars, dict):
        return html % fill_vars
    else:
        return html


def cloud_help_snippet(configuration, topics=[keyword_all], fill_vars=None):
    """Genererates a HTML template with the corresponding help topic.
    The optional fill_vars is used to expand variables if provided.
    """
    html = ''
    if keyword_all in topics or 'client' in topics:
        html += '''
<h3>Graphical Cloud Login</h3>
<div class="help-entry cloud-client-help">
<p>
Cloud login is currently limited to terminal access over SSH. You can use
different graphical or command-line clients to open your remote terminal
session on %(site)s cloud instances.
</p>
<h4>PuTTY on Windows, Mac OSX or Linux</h4>
<p>The <a href="https://www.putty.org">PuTTY</a> client is known to generally
work for graphical SSH access to your %(site)s cloud instances. It runs on all
popular platforms and in the
<a href="https://portableapps.com/apps/internet/putty_portable">portable
version</a> it does not even require install privileges.</p>
<p>
<!-- TODO: is this the right naming for PuTTY? -->
Enter the following values in the PuTTY Site Manager:</p>
<ul>
<li>Host <var>%(cloud_host_pattern)s</var></li>
<li>Port <var>22</var></li>
<li>Protocol <var>SSH</var></li>
<li>User <var>%(username)s</var></li>
<li>Password <var>[YOUR CHOSEN PASSWORD]</var> (leave empty for ssh key from key-agent)</li>
</ul>

<h4>Other Graphical Clients</h4>
<p>
Other graphical clients like MindTerm, etc. should work as well using the above
login details.
</p>
</div>
'''

    if keyword_all in topics or 'terminal' in topics:
        html += '''
<h3>Command-Line Cloud Login</h3>
<div class="help-entry cloud-terminal-help">
<h4>SSH Terminal Access on Mac OSX and Linux/UN*X</h3>
<p>
Save something like the following lines in your local ~/.ssh/config
to avoid typing the full login details every time:</p>
<textarea rows=6 cols=78 class="code" readonly=readonly>Host %(cloud_host_pattern)s
Hostname %(cloud_host_pattern)s
User %(username)s
# Uncomment next line to use your private key in ~/.ssh/id_rsa
# IdentityFile ~/.ssh/id_rsa</textarea>
<p>From then on you can use ssh to access your %(site)s instance:</p>
<pre class="codeblock">
ssh %(cloud_host_pattern)s
</pre>
</div>
'''
    if fill_vars is not None and isinstance(fill_vars, dict):
        return html % fill_vars
    else:
        return html


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Setup'

    # jquery support for toggling views and popup dialog

    (add_import, add_init, add_ready) = man_base_js(configuration, [])
    (tfa_import, tfa_init, tfa_ready) = twofactor_wizard_js(configuration)
    (save_import, save_init, save_ready) = save_settings_js(configuration)
    # prepare support for toggling the views (by css/jquery)
    title_entry['style']['skin'] += '''
%s
''' % cm_css
    add_import += '''
<script type="text/javascript" src="/images/js/jquery.ajaxhelpers.js"></script>

%s

%s

%s

%s
    ''' % (cm_javascript, console_log_javascript(), tfa_import, save_import)
    add_init += '''
    /* prepare global logging from console_log_javascript */
    try {
        log_level = "info";
        init_log();
    } catch(err) {
        alert("error: "+err);
    }

%s

%s
    ''' % (tfa_init, save_init)
    add_ready += '''
              /* Init variables helper as foldable but closed and with individual
              heights */
              $(".help-accordion").accordion({
                                           collapsible: true,
                                           active: false,
                                           heightStyle: "content"
                                          });
              /* fix and reduce accordion spacing */
              $(".ui-accordion-header").css("padding-top", 0)
                                       .css("padding-bottom", 0).css("margin", 0);

%s

%s
''' % (tfa_ready, save_ready)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    active_menu = extract_menu(configuration, title_entry)

    valid_topics = []
    if configuration.site_enable_sftp or configuration.site_enable_sftp_subsys:
        valid_topics.append('sftp')
    if configuration.site_enable_davs:
        valid_topics.append('webdavs')
    if configuration.site_enable_ftps:
        valid_topics.append('ftps')
    if configuration.site_enable_seafile:
        valid_topics.append('seafile')
    if configuration.site_enable_duplicati:
        valid_topics.append('duplicati')
    if configuration.site_enable_cloud:
        valid_topics.append('cloud')
    if configuration.site_enable_twofactor \
            and not configuration.site_enable_gdp:
        valid_topics.append('twofactor')
    topic_list = accepted['topic']
    # Backwards compatibility
    if topic_list and 'ssh' in topic_list:
        topic_list.remove('ssh')
        topic_list.append('sftp')
    topic_list = [topic for topic in topic_list if topic in valid_topics]
    # Default to first valid topic if no valid topics requested
    if not topic_list:
        topic_list.append(valid_topics[0])
    topic_titles = dict([(i, i.title()) for i in valid_topics])
    for (key, val) in [('sftp', 'SFTP'), ('webdavs', 'WebDAVS'),
                       ('ftps', 'FTPS'), ('seafile', 'Seafile'),
                       ('duplicati', 'Duplicati'), ('cloud', 'Cloud'),
                       ('twofactor', '2-Factor Auth'),
                       ]:
        if key in valid_topics:
            topic_titles[key] = val

    output_objects.append({'object_type': 'header', 'text': 'Setup'})

    links = []
    for name in valid_topics:
        active_menu = ''
        if topic_list[0] == name:
            active_menu = 'activebutton'
        links.append({'object_type': 'link',
                      'destination': "setup.py?topic=%s" % name,
                      'class': '%ssettingslink settingsbutton %s'
                      % (name, active_menu),
                      'title': 'Switch to %s setup' % topic_titles[name],
                      'text': '%s' % topic_titles[name],
                      })

    output_objects.append({'object_type': 'multilinkline', 'links': links,
                           'sep': '  '})
    output_objects.append({'object_type': 'text', 'text': ''})

    if not topic_list:
        output_objects.append({'object_type': 'error_text', 'text':
                               'No valid topics!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Site policy dictates pw min length greater or equal than password_min_len
    policy_min_len, policy_min_classes = parse_password_policy(configuration)
    save_html = save_settings_html(configuration)
    (expire_warn, expire_time, renew_days, extend_days) = account_expire_info(
        configuration, client_id)
    expire_html = ''
    if expire_warn:
        expire_warn_msg = '''<p class="warningtext">
NOTE: your %s account access including efficient file service access expires on
%s. You can always repeat sign up to extend general access with another %s days.
%s
</p>'''
        auto_renew_msg = '''Alternatively simply either hit Save below now
<em>or</em> log in here again after that date to quickly extend your access for
%s days.'''
        expire_date = time.ctime(expire_time)
        logger.debug("warn about expire on %s" % expire_date)
        extend_msg = ''
        if extend_days > 0:
            extend_msg = auto_renew_msg % extend_days
        expire_html = expire_warn_msg % (configuration.short_title,
                                         expire_date, renew_days, extend_msg)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    compact_name = configuration.short_title.replace(' ', '-').lower()
    fill_helpers = {
        'site': configuration.short_title,
        'mount_name': compact_name,
        'mount_dir': "%s-home" % compact_name,
        'form_method': form_method,
        'csrf_field': csrf_field, 'csrf_limit': csrf_limit,
        'valid_password_chars': html_escape(valid_password_chars),
        'password_min_len': max(policy_min_len, password_min_len),
        'password_max_len': password_max_len,
        'password_min_classes': max(policy_min_classes, 1),
        'save_html': save_html, 'expire_html': expire_html}

    if 'sftp' in topic_list:

        # load current ssh/sftp

        current_ssh_dict = load_ssh(client_id, configuration)
        if not current_ssh_dict:

            # no current ssh found

            current_ssh_dict = {}

        default_authkeys = current_ssh_dict.get('authkeys', '')
        default_authpassword = current_ssh_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_sftp_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_sftp_alias)
            create_alias_link(username, client_id, configuration.user_home)
        sftp_server = configuration.user_sftp_show_address
        sftp_port = configuration.user_sftp_show_port
        fingerprint_info = ''
        sftp_md5 = configuration.user_sftp_key_md5
        sftp_sha256 = configuration.user_sftp_key_sha256
        sftp_trust_dns = configuration.user_sftp_key_from_dns
        fingerprints = []
        hostkey_from_dns = 'ask'
        if sftp_md5:
            fingerprints.append("<sampl>%s</sampl> (MD5)" % sftp_md5)
        if sftp_sha256:
            fingerprints.append("<sampl>%s</sampl> (SHA256)" % sftp_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint %s first time you connect.''' % ' or '.join(fingerprints)
        if sftp_trust_dns:
            hostkey_from_dns = 'yes'
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="sshaccess" class="row">
<div class="col-12">
    <form class="save_settings save_sftp" method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="topic" value="sftp" />

        <div class="vertical-spacer"></div>
        <div class="title centertext">SFTP access to your %(site)s account</div>

<p>
<p>You can enable SFTP login to your %(site)s account and use it for efficient
file and folder upload/download or even for seamless data access from your
Windows, Mac OS X and Linux/UN*X computer.
</p>
<h3>Login Details</h3>

<ul>
<li>Host <var>%(sftp_server)s</var></li>
<li>Port <var>%(sftp_port)s</var></li>
<li>Username <var>%(username)s</var></li>
<li>%(auth_methods)s <var>as you choose below</var></li>
</ul>
<p>%(fingerprint_info)s</p>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_sftp_auth:
            html += '''

<h3>Public Keys</h3>
<p>You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
</p>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ssh_edit, 'BASIC')
            html += '''
<p>(leave empty to disable sftp access with public keys)</p>

'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_sftp_auth:

            # We only want a single password and a masked input field
            html += '''

<h3>Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<!-- NOTE: we currently allow empty here to disable password login -->
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
maxlength=%(password_max_len)d pattern=".{0,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
value="%(default_authpassword)s" />
(leave empty to disable sftp access with password)
</p>
'''

        html += '''
%(expire_html)s
%(save_html)s
<input type="submit" value="Save SFTP Settings" />
</form>
'''
        # Client help fold-out
        html += '''
<hr/>
<h4>How to proceed after enabling login above ...</h4>
<br/>
<div class="help-accordion">
%s
</div>
''' % sftp_help_snippet(configuration, ['drive', 'client', 'terminal'])
        html += '''
</div>
</div>
'''
        # Hide port if same as implicit
        sftp_uri = 'sftp://%s' % sftp_server
        sshfs_netloc = '\\\\sshfs\\%s@%s' % (username, sftp_server)
        if sftp_port != 22:
            sftp_uri += ':%d' % sftp_port
            sshfs_netloc += ':%d' % sftp_port
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'sftp_server': sftp_server,
            'sftp_port': sftp_port,
            'sftp_uri': sftp_uri,
            'sshfs_netloc': sshfs_netloc,
            'hostkey_from_dns': hostkey_from_dns,
            'max_sessions': configuration.user_sftp_max_sessions,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_sftp_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'webdavs' in topic_list:

        # load current davs

        current_davs_dict = load_davs(client_id, configuration)
        if not current_davs_dict:

            # no current davs found

            current_davs_dict = {}

        default_authkeys = current_davs_dict.get('authkeys', '')
        default_authpassword = current_davs_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_davs_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_davs_alias)
            create_alias_link(username, client_id, configuration.user_home)
        davs_server = configuration.user_davs_show_address
        davs_port = configuration.user_davs_show_port
        fingerprint_info = ''
        # We do not support pretty outdated SHA1 in conf
        # davs_sha1 = configuration.user_davs_key_sha1
        davs_sha1 = ''
        davs_sha256 = configuration.user_davs_key_sha256
        fingerprints = []
        if davs_sha1:
            fingerprints.append("<sampl>%s</sampl> (SHA1)" % davs_sha1)
        if davs_sha256:
            fingerprints.append("<sampl>%s</sampl> (SHA256)" % davs_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint %s first time you connect.''' % ' or '.join(fingerprints)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="davsaccess" class="row">
<div class="col-12">
<form class="save_settings save_davs" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="webdavs" />

<div class="vertical-spacer"></div>
<div class="title centertext">WebDAVS access to your %(site)s account</div>

<p>You can enable WebDAVS login to your %(site)s account and use it for file
and folder upload/download or even for seamless data access from your Windows,
Mac OS X and Linux/UN*X computer.
</p>
<h3>Login Details</h3>
<ul>
<li>Host <var>%(davs_server)s</var></li>
<li>Port <var>%(davs_port)s</var></li>
<li>Username <var>%(username)s</var></li>
<li>%(auth_methods)s <var>as you choose below</var></li>
</ul>
<p class="wordbreak">%(fingerprint_info)s</p>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_davs_auth:
            html += '''

<h3>Public Keys</h3>
<p>You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
<br/>'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, davs_edit, 'BASIC')
            html += '''
(leave empty to disable davs access with public keys)
</p>
'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_davs_auth:
            # We only want a single password and a masked input field
            html += '''

<h3>Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<!-- NOTE: we currently allow empty here to disable password login -->
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
maxlength=%(password_max_len)d pattern="(.{0,%(password_max_len)d})?"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
value="%(default_authpassword)s" />
(leave empty to disable davs access with password)
</p>
'''

        html += '''
%(expire_html)s
%(save_html)s
<input type="submit" value="Save WebDAVS Settings" />
</form>
'''

        html += '''
<hr/>
<h4>How to proceed after enabling login above ...</h4>
<br/>
<div class="help-accordion">
%s
</div>
''' % davs_help_snippet(configuration, ['drive', 'client', 'terminal'])

        html += '''
</div>
</div>
'''
        davs_url = 'https://%s' % davs_server
        if davs_port != 443:
            davs_url += ':%d' % davs_port
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'davs_server': davs_server,
            'davs_port': davs_port,
            'davs_url': davs_url,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_davs_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'ftps' in topic_list:

        # load current ftps

        current_ftps_dict = load_ftps(client_id, configuration)
        if not current_ftps_dict:

            # no current ftps found

            current_ftps_dict = {}

        default_authkeys = current_ftps_dict.get('authkeys', '')
        default_authpassword = current_ftps_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_ftps_alias:
            username = extract_field(client_id, configuration.user_ftps_alias)
            create_alias_link(username, client_id, configuration.user_home)
        ftps_server = configuration.user_ftps_show_address
        ftps_ctrl_port = configuration.user_ftps_show_ctrl_port
        fingerprint_info = ''
        # We do not support pretty outdated SHA1 in conf
        # ftps_sha1 = configuration.user_ftps_key_sha1
        ftps_sha1 = ''
        ftps_sha256 = configuration.user_ftps_key_sha256
        fingerprints = []
        if ftps_sha1:
            fingerprints.append("<sampl>%s</sampl> (SHA1)" % ftps_sha1)
        if ftps_sha256:
            fingerprints.append("<sampl>%s</sampl> (SHA256)" % ftps_sha256)
        if fingerprints:
            fingerprint_info = '''You may be asked to verify the server key
fingerprint <sampl>%s</sampl> first time you connect.''' % ' or '.join(fingerprints)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="ftpsaccess" class="row">
<div class="col-12">
<form class="save_settings save_ftps" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="ftps" />

<div class="vertical-spacer"></div>
<div class="title centertext">FTPS access to your %(site)s account</div>

<p>You can enable FTPS login to your %(site)s account and use it for efficient
file and folder upload/download.</p>
<h3>Login Details</h3>
<ul>
<li>Host <var>%(ftps_server)s</var></li>
<li>Port <var>%(ftps_ctrl_port)s</var></li>
<li>Username <var>%(username)s</var></li>
<li>%(auth_methods)s <var>as you choose below</var></li>
</ul>
<p>%(fingerprint_info)s</p>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_ftps_auth:
            html += '''

<h3>Public Keys</h3>
<p>You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
</p>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ftps_edit, 'BASIC')
            html += '''
(leave empty to disable ftps access with public keys)

'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_ftps_auth:

            # We only want a single password and a masked input field
            html += '''

<h3>Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<!-- NOTE: we currently allow empty here to disable password login -->
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
maxlength=%(password_max_len)d pattern=".{0,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
value="%(default_authpassword)s" />
(leave empty to disable ftps access with password)
</p>
'''

        html += '''
%(expire_html)s
%(save_html)s
<input type="submit" value="Save FTPS Settings" />
</form>
'''

        html += '''
<hr/>
<h4>How to proceed after enabling login above ...</h4>
<br/>
<div class="help-accordion">
%s
</div>
''' % ftps_help_snippet(configuration, ['client', 'terminal'])

        html += '''
</div>
</div>
'''
        # Hide port if same as implicit
        ftps_uri = 'ftps://%s' % ftps_server
        if ftps_ctrl_port != 21:
            ftps_uri += ':%d' % ftps_ctrl_port
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'ftps_server': ftps_server,
            'ftps_ctrl_port': ftps_ctrl_port,
            'ftps_uri': ftps_uri,
            'max_sessions': configuration.user_sftp_max_sessions,
            'fingerprint_info': fingerprint_info,
            'auth_methods': ' / '.join(configuration.user_ftps_auth).title(),
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'seafile' in topic_list:

        # load current seafile

        current_seafile_dict = load_seafile(client_id, configuration)
        if not current_seafile_dict:

            # no current seafile found

            current_seafile_dict = {}

        keyword_password = "authpassword"
        default_authpassword = current_seafile_dict.get('authpassword', '')
        username = client_alias(client_id)
        if configuration.user_seafile_alias:
            username = extract_field(
                client_id, configuration.user_seafile_alias)
            create_alias_link(username, client_id, configuration.user_home)

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<script type="text/javascript" >
/* Helper function to open Seafile login window and fill username. Gives up
after max_tries * sleep_secs seconds if still not found.
*/
var login_window = null;
var user = '';
var try_count = 1;
var max_tries = 60;
var sleep_secs = 1;
function set_username() {
    var account_elem = login_window.document.getElementById("account");
    if (account_elem) {
        console.info("already logged in - no need to set user name");
        return true;
    }
    console.debug("set username "+user);
    var elems = login_window.document.getElementsByName("username");
    var i;
    for (i = 0; i < elems.length; i++) {
        console.debug("check elem "+i);
        if (elems[i].type == "text") {
            console.debug("found username elem "+i);
            elems[i].value = user;
            elems[i].readOnly = "readonly";
            console.info("done setting username in login form");
            return true;
        }
    }
    if (try_count >= max_tries) {
        console.warn("giving up after "+try_count+" tries to set username");
        return false;
    }
    console.debug("keep trying... ("+try_count+" of "+max_tries+")");
    try_count = try_count+1;
    setTimeout("set_username();", sleep_secs * 1000);
}
function open_login_window(url, username) {
    console.info("open login window "+url+" as "+username);
    user = username;
    login_window = window.open(url, "Seafile for "+username,
                               "width=1080, height=700, top=100, left=100");
    console.debug("call set_username");
    set_username();
}
</script>
<div id="seafileaccess">
<div id="seafileregaccess">
<form method="post" action="%(seareg_url)s" target="_blank">

<div class="vertical-spacer"></div>
<div class="title centertext">Seafile Synchronization on %(site)s</div>

<p>You can register a Seafile account on %(site)s to get synchronization and
sharing features like those known from e.g. Dropbox.<br/>
This enables you to keep one or more folders synchronized between
all your computers and to share those files and folders with other people.</p>

<fieldset>
<legend><p>Register %(site)s Seafile Account</p></legend>
<p><input type="hidden" name="csrfmiddlewaretoken" value="" />
<!-- prevent user changing email but show it as read-only input field -->
<input class="input" id="id_email" name="email" type="hidden"
    value="%(username)s" />
<label for="dummy_email">Seafile Username</label>
<input class="input" id="dummy_email" type="text" value="%(username)s"
    readonly />
<br/>
<!-- NOTE: we require password policy in this case because pw MUST be set -->
<label for="id_password1">Choose Password</label>
<input class="input" id="id_password1" name="password1"
minlength=%(password_min_len)d maxlength=%(password_max_len)d required
pattern=".{%(password_min_len)d,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
type="password" />
<br/>
<label for="id_password2">Confirm Password</label>
<input class="input" id="id_password2" name="password2"
minlength=%(password_min_len)d maxlength=%(password_max_len)d required
pattern=".{%(password_min_len)d,%(password_max_len)d}"
title="Repeat your chosen password" type="password" />
<br/>
<input id="seafileregbutton" type="submit" value="Register" class="submit" />
and wait for email confirmation before continuing below.</p>
</fieldset>

</form>

<fieldset>
<legend><p>Login and Install Clients</p></legend>
<p>Once your %(site)s Seafile account is in place
<input id="seafileloginbutton" type="submit" value="log in"
onClick="open_login_window(\'%(seahub_url)s\', \'%(username)s\'); return false"
/> to it and install the client available there on any computers where you want
folder synchronization.<br/>
Optionally also install it on any mobile device(s) from which you want easy
access.<br/>
Then return here and <input id="seafilenextbutton" type="submit" value="proceed"
onClick="select_seafile_section(\'seafilesave\'); return false" /> with the
client set up and %(site)s integration.</p>
</fieldset>

</div>
<div id="seafilesaveaccess" style="display: none;">

<div class="vertical-spacer"></div>
<div class="title centertext">Seafile Client Setup and %(site)s Integration</div>

<fieldset>
<legend><p>Seafile Client Setup Details</p></legend>
<p>You need to enter the following details to actually configure the Seafile
client(s) you installed in the previous step.</p>

<p>
<label for="id_server">Server</label>
<input id=id_server type=text value="%(seafile_url)s" %(size)s %(ro)s /><br/>
<label for="id_username">Username</label>
<input id="id_username" type=text value="%(username)s" %(size)s %(ro)s /><br/>
<label for="id_password">Password</label>
<input id="id_password" type=text value="...the Seafile password you chose..."
%(size)s %(ro)s/></p>
<p>You can always
<input id="seafilepreviousbutton" type="submit"
    value="go back"
    onClick="select_seafile_section(\'seafilereg\'); return false" />
to that registration and install step if you skipped a part of it or just want
to install more clients.<br/>
You can also directly open your
<input id="seafileloginbutton" type="submit" value="Seafile account"
onClick="open_login_window(\'%(seahub_url)s\', \'%(username)s\'); return false"
/> web page.<br/>
After the setup you can use your Seafile account as a standalone synchronization
and sharing solution.</p>
</fieldset>

'''

        if configuration.user_seafile_ro_access:
            html += '''
<form class="save_settings save_seafile" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="seafile" />
<fieldset>
<legend><p>%(site)s Seafile Integration</p></legend>
<p>If you wish you can additionally save your credentials here for Seafile
integration in your %(site)s user home.<br/>
Then your Seafile libraries will show up in a read-only mode under a new
<var>%(seafile_ro_dirname)s</var> folder e.g. on the Files page.</p>
'''

            if 'password' in configuration.user_seafile_auth:

                # We only want a single password and a masked input field
                html += '''
<p>
Please enter and save your chosen Seafile password again in the text field
below, to enable the read-only Seafile integration in your user home.
</p>
<p>
<!-- NOTE: we currently allow empty here to disable password login -->
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
maxlength=%(password_max_len)d pattern=".{0,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
value="%(default_authpassword)s" />
(leave empty to disable seafile integration)
</p>
'''

            html += '''
%(save_html)s
<input id="seafilesavebutton" type="submit" value="Save Seafile Password" />
</fieldset>
</form>
'''
        html += '''

</div>
<div id="seafileserverstatus"></div>
<!-- Dynamically fill CSRF token above and select active div if possible -->
<script type="text/javascript" >
    prepare_seafile_settings("%(seareg_url)s", "%(username)s",
                             "%(default_authpassword)s", "seafileserver",
                             "seafilereg", "seafilesave");
</script>
</div>
'''
        fill_helpers.update({
            'default_authpassword': default_authpassword,
            'keyword_password': keyword_password,
            'username': username,
            'seafile_ro_dirname': seafile_ro_dirname,
            'seahub_url': configuration.user_seahub_url,
            'seareg_url': configuration.user_seareg_url,
            'seafile_url': configuration.user_seafile_url,
            'auth_methods':
                ' / '.join(configuration.user_seafile_auth).title(),
            'ro': 'readonly=readonly',
            'size': 'size=50',
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'duplicati' in topic_list:

        # load current duplicati

        current_duplicati_dict = load_duplicati(client_id, configuration)
        if not current_duplicati_dict:

            # no current duplicati found

            current_duplicati_dict = {}

        configuration.protocol, configuration.username = [], []
        configuration.schedule = [i for (i, j) in duplicati_schedule_choices]
        # We save the pretty names in pickle but use internal ones here
        if configuration.user_duplicati_protocols:
            protocol_order = configuration.user_duplicati_protocols
        else:
            protocol_order = [j for (i, j) in duplicati_protocol_choices]
        reverse_proto_map = dict([(j, i) for (i, j) in
                                  duplicati_protocol_choices])

        enabled_map = {
            'davs': configuration.site_enable_davs,
            'sftp': configuration.site_enable_sftp or
            configuration.site_enable_sftp_subsys,
            'ftps': configuration.site_enable_ftps
        }
        username_map = {
            'davs': extract_field(client_id, configuration.user_davs_alias),
            'sftp': extract_field(client_id, configuration.user_sftp_alias),
            'ftps': extract_field(client_id, configuration.user_ftps_alias)
        }
        for proto in protocol_order:
            pretty_proto = reverse_proto_map[proto]
            if not enabled_map[proto]:
                continue
            if not pretty_proto in configuration.protocol:
                configuration.protocol.append(pretty_proto)
            if not username_map[proto] in configuration.username:
                configuration.username.append(username_map[proto])

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="duplicatiaccess">
<form class="save_settings save_duplicati" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="duplicati" />

<div class="vertical-spacer"></div>
<div class="title centertext">Duplicati Backup to %(site)s</div>

<p>You can install the <a href="https://www.duplicati.com">Duplicati</a> client on
your local machine and use it to backup arbitrary data to %(site)s.<br/>
We recommend the <a href="https://www.duplicati.com/download">
most recent version of Duplicati</a> to be able to import the generated
configurations from here directly.</p>
<h3>Configure Backup Sets</h3>
<p>You can define the backup sets here and then afterwards just download and
import the configuration file in your Duplicati client, to set up everything
for %(site)s backup use.</p>

'''

        duplicati_entries = get_duplicati_specs()
        for (keyword, val) in duplicati_entries:
            if val['Editor'] == 'hidden':
                continue
            html += """
            <h4 style="padding-top: 10px;">
            %s
            </h4>
            <p style="padding-bottom: 0;">
            %s
            </p>
            """ % (keyword.replace('_', ' ').title(), val['Description'])

            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if keyword in current_duplicati_dict:
                        current_choice = current_duplicati_dict[keyword]

                    if valid_choices:
                        html += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            html += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        html += '</div>'
                except:
                    area = """<textarea id='%s' cols=78 rows=10 name='%s'>""" \
                        % (keyword, keyword)
                    if keyword in current_duplicati_dict:
                        area += '\n'.join(current_duplicati_dict[keyword])
                    area += '</textarea>'
                    html += wrap_edit_area(keyword, area, duplicati_edit)
            elif val['Type'] == 'string':

                current_choice = ''
                if keyword in current_duplicati_dict:
                    current_choice = current_duplicati_dict[keyword]
                if val['Editor'] == 'select':
                    # get valid choices from conf

                    valid_choices = eval('configuration.%s' % keyword.lower())

                    if valid_choices:
                        html += '<select class="styled-select semi-square html-select" name="%s">' % keyword
                        for choice in valid_choices:
                            selected = ''
                            if choice == current_choice:
                                selected = 'selected'
                            html += '<option %s value="%s">%s</option>'\
                                % (selected, choice, choice)
                        html += '</select>'
                    else:
                        html += ''
                elif val['Editor'] == 'password':
                    html += '<input type="password" name="%s" value="%s"/>' \
                        % (keyword, current_choice)
                else:
                    html += '<input type="text" name="%s" value="%s"/>' \
                        % (keyword, current_choice)
                html += '<br />'
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if keyword in current_duplicati_dict:
                    current_choice = current_duplicati_dict[keyword]
                checked = ''
                if current_choice == True:
                    checked = 'checked'
                html += '<label class="switch">'
                html += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                  checked)
                html += '<span class="slider round"></span></label>'
                html += '<br /><br />'

            html += '''

        '''
        html += '''
        <br/>
        %(save_html)s
        <input type="submit" value="Save Duplicati Settings" />

</form>
'''

        html += '''

<h3>Import Backup Sets</h3>
<p>Your saved %(site)s Duplicati backup settings are available for download below:</p>
<p>
'''

        saved_backup_sets = current_duplicati_dict.get('BACKUPS', [])
        duplicati_confs_path = os.path.join(base_dir, duplicati_conf_dir)
        duplicati_confs = []
        duplicati_confs += saved_backup_sets
        for conf_name in duplicati_confs:
            conf_file = "%s.json" % conf_name
            # Check existance of conf_file
            conf_path = os.path.join(duplicati_confs_path, conf_file)
            if not os.path.isfile(conf_path):
                logger.warning(
                    "saved duplicati conf %s is missing" % conf_path)
                continue
            html += '<a href="/cert_redirect/%s/%s">%s</a><br/>' \
                % (duplicati_conf_dir, conf_file, conf_file)
        if not duplicati_confs:
            html += '<em>No backup sets configured</em>'

        html += '''
</p>
<p>After downloading you can import them directly in the most recent Duplicati
client versions from the link above.</p>

</div>
'''

        fill_helpers.update({
            'client_id': client_id,
            'size': 'size=50',
        })
        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'cloud' in topic_list:

        # load current cloud

        current_cloud_dict = load_cloud(client_id, configuration)
        if not current_cloud_dict:

            # no current cloud found

            current_cloud_dict = {}

        default_authkeys = current_cloud_dict.get('authkeys', '')
        default_authpassword = current_cloud_dict.get('authpassword', '')
        username = client_alias(client_id)
        cloud_host_pattern = '[cloud-instance-address]'
        if configuration.user_cloud_alias:
            username = get_short_id(configuration, client_id,
                                    configuration.user_cloud_alias)
            create_alias_link(username, client_id, configuration.user_home)
        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = '''
<div id="cloudaccess" class="row">
<div class="col-12">
    <form class="save_settings save_cloud" method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="topic" value="cloud" />

<div class="vertical-spacer"></div>
<div class="title centertext">SSH access to your %(site)s cloud instance(s)</div>

<p>
You can configure SSH login to your %(site)s cloud instance(s) for interactive
use.
</p>
<h3>Login Details</h3>
<p>Please refer to your <a href="cloud.py">Cloud management</a> page for
specific instance login details.
However, in general login requires the following:</p>
<ul>
<li>Host <var>%(cloud_host_pattern)s</var></li>
<li>Username <var>%(username)s</var></li>
<li>%(auth_methods)s <var>as you choose below</var></li>
</ul>
'''

        keyword_keys = "authkeys"
        if 'publickey' in configuration.user_cloud_ssh_auth:
            html += '''

<h3>Public Keys</h3>
<p>You can use any existing RSA key, or create a new one. If you signed up with a
x509 user certificate, you should also have received such an id_rsa key along with
your user certificate. In any case you need to save the contents of the
corresponding public key (id_rsa.pub) in the text area below, to be able to connect
with username and key as described in the Login Details.
</p>
'''
            area = '''
<textarea id="%(keyword_keys)s" cols=82 rows=5 name="publickeys">
%(default_authkeys)s
</textarea>
'''
            html += wrap_edit_area(keyword_keys, area, ssh_edit, 'BASIC')
            html += '''
<p>(leave empty to disable cloud access with public keys)</p>

'''

        keyword_password = "authpassword"
        if 'password' in configuration.user_cloud_ssh_auth:

            # We only want a single password and a masked input field
            html += '''

<h3>Password</h3>
<p>
Please enter and save your desired password in the text field below, to be able
to connect with username and password as described in the Login Details.
</p>
<p>
<!-- NOTE: we currently allow empty here to disable password login -->
<input class="fullwidth" type=password id="%(keyword_password)s" size=40 name="password"
maxlength=%(password_max_len)d pattern=".{0,%(password_max_len)d}"
title="Password of your choice with at least %(password_min_len)d characters
from %(password_min_classes)d classes (lowercase, uppercase, digits and other)"
value="%(default_authpassword)s" />
(leave empty to disable cloud access with password)
</p>
'''

        html += '''

%(save_html)s
<input type="submit" value="Save Cloud Settings" />
</form>
'''

        # Client help fold-out
        html += '''
<hr/>
<h4>How to proceed after enabling login above ...</h4>
<br/>
<div class="help-accordion">
%s
</div>
''' % cloud_help_snippet(configuration, ['client', 'terminal'])
        html += '''
</div>
</div>
'''
        fill_helpers.update({
            'default_authkeys': default_authkeys,
            'default_authpassword': default_authpassword,
            'keyword_keys': keyword_keys,
            'keyword_password': keyword_password,
            'username': username,
            'cloud_host_pattern': cloud_host_pattern,
            'auth_methods': ' / '.join(configuration.user_cloud_ssh_auth).title(),
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    if 'twofactor' in topic_list:

        # load current twofactor

        current_twofactor_dict = load_twofactor(client_id, configuration)
        if not current_twofactor_dict:

            # no current twofactor found

            current_twofactor_dict = {}

        target_op = 'settingsaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html = """
<div id='otp_verify_dialog' title='Verify Authenticator App Token'
   class='centertext hidden'>
"""
        # NOTE: wizard needs dialog with form outside the main settings form
        # because nested forms cause problems
        html += twofactor_token_html(configuration)
        html += '''</div>
<div id="twofactor">
<form class="save_settings save_twofactor" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="topic" value="twofactor" />
<table class="twofactor fixedlayout">
<tr><td>
<div class="vertical-spacer"></div>
<div class="title centertext">2-Factor Authentication</div>
</td></tr>
'''

        if configuration.site_enable_twofactor:
            b32_key, otp_interval, otp_uri = get_twofactor_secrets(
                configuration, client_id)
            # We limit key exposure by not showing it in clear and keeping it
            # out of backend dictionary with indirect generation only.

            # TODO: we might want to protect QR code with repeat basic login
            #       or a simple timeout since last login (cookie age).
            html += twofactor_wizard_html(configuration)
            check_url = '/%s/twofactor.py?action=check' % get_xgi_bin(
                configuration)
            fill_helpers.update({'otp_uri': otp_uri, 'b32_key': b32_key,
                                 'otp_interval': otp_interval,
                                 'check_url': check_url, 'demand_twofactor':
                                 'allow', 'enable_hint':
                                 'enable it for login below'})

        twofactor_entries = get_twofactor_specs(configuration)
        html += '''
        <tr class="otp_wizard otp_ready hidden"><td>
        </td></tr>
        <tr class="otp_wizard otp_ready hidden"><td>
        </td></tr>
        '''
        cur_url = requested_url_base()
        auth_type, auth_flavor = detect_client_auth(configuration, os.environ)
        is_mig = auth_flavor in [AUTH_MIG_OID, AUTH_MIG_OIDC]
        is_ext = auth_flavor in [AUTH_EXT_OID, AUTH_EXT_OIDC]
        # NOTE: re-order to show active access method OpenID 2.0/Connect first
        if is_ext and twofactor_entries[0][0] == 'MIG_OID_TWOFACTOR' and \
                twofactor_entries[1][0] == 'EXT_OID_TWOFACTOR' or \
                is_mig and twofactor_entries[1][0] == 'MIG_OID_TWOFACTOR' and \
                twofactor_entries[0][0] == 'EXT_OID_TWOFACTOR':
            twofactor_entries[0], twofactor_entries[1] = \
                twofactor_entries[1], twofactor_entries[0]
        for (keyword, val) in twofactor_entries:
            if val.get('Editor', None) == 'hidden':
                continue
            # Mark the dependent options to ease hiding when not relevant
            val['__extra_class__'] = ''
            if val.get('Context', None) == 'twofactor':
                val['__extra_class__'] = 'provides-twofactor-base'
                if keyword == 'MIG_OID_TWOFACTOR' and is_mig or \
                        keyword == 'EXT_OID_TWOFACTOR' and is_ext:
                    val['__extra_class__'] += ' active-openid-access'
            if val.get('Context', None) == 'twofactor_dep':
                val['__extra_class__'] = 'requires-twofactor-base manual-show'
            entry = """
            <tr class='otp_wizard otp_ready hidden %(__extra_class__)s'>
            <td class='title'>
            %(Title)s
            </td></tr>
            <tr class='otp_wizard otp_ready hidden %(__extra_class__)s'><td>
            %(Description)s
            </td></tr>
            <tr class='otp_wizard otp_ready hidden %(__extra_class__)s'><td>
            """ % val
            if val['Type'] == 'multiplestrings':
                try:

                    # get valid choices from conf. multiple selections

                    valid_choices = eval('configuration.%s' % keyword.lower())
                    current_choice = []
                    if keyword in current_twofactor_dict:
                        current_choice = current_twofactor_dict[keyword]

                    if valid_choices:
                        entry += '<div class="scrollselect">'
                        for choice in valid_choices:
                            selected = ''
                            if choice in current_choice:
                                selected = 'checked'
                            entry += '''
                <input type="checkbox" name="%s" %s value="%s">%s<br />''' \
                                % (keyword, selected, choice, choice)
                        entry += '</div>'
                    else:
                        entry += ''
                except:
                    # failed on evaluating configuration.%s

                    area = '''
                <textarea id="%s" cols=40 rows=1 name="%s">''' \
                        % (keyword, keyword)
                    if keyword in current_twofactor_dict:
                        area += '\n'.join(current_twofactor_dict[keyword])
                    area += '</textarea>'
                    entry += wrap_edit_area(keyword, area, twofactor_edit,
                                            'BASIC')

            elif val['Type'] == 'string':

                # get valid choices from conf

                valid_choices = eval('configuration.%s' % keyword.lower())
                current_choice = ''
                if keyword in current_twofactor_dict:
                    current_choice = current_twofactor_dict[keyword]

                if valid_choices:
                    entry += '<select class="styled-select semi-square html-select" name="%s">' % keyword
                    for choice in valid_choices:
                        selected = ''
                        if choice == current_choice:
                            selected = 'selected'
                        entry += '<option %s value="%s">%s</option>'\
                            % (selected, choice, choice)
                    entry += '</select><br />'
                else:
                    entry += ''
            elif val['Type'] == 'boolean':

                # get valid choice order from spec

                valid_choices = [val['Value'], not val['Value']]
                current_choice = ''
                if keyword in current_twofactor_dict:
                    current_choice = current_twofactor_dict[keyword]
                checked = ''
                if current_choice == True:
                    checked = 'checked'
                entry += '<label class="switch">'
                entry += '<input type="checkbox" name="%s" %s>' % (keyword,
                                                                   checked)
                entry += '<span class="slider round"></span></label>'
                entry += '<br /><br />'
            html += """%s
            </td></tr>
            """ % entry

        html += '''<tr class="otp_wizard otp_ready hidden"><td>
        %(save_html)s
        <input type="submit" value="Save 2-Factor Auth Settings" />
        <br/>
        <br/>
</td></tr>
</table>
</form>
</div>
'''

        if configuration.site_enable_twofactor and \
            (current_twofactor_dict.get("MIG_OID_TWOFACTOR", False) or
             current_twofactor_dict.get("EXT_OID_TWOFACTOR", False)):
            html += """<script>
    setOTPProgress(['otp_intro', 'otp_install', 'otp_import', 'otp_verify',
                    'otp_ready']);
</script>
        """

        fill_helpers.update({
            'client_id': client_id,
        })

        output_objects.append({'object_type': 'html_form', 'text':
                               html % fill_helpers})

    output_objects.append({'object_type': 'html_form', 'text':
                           '<div class="vertical-spacer"></div>'})
    return (output_objects, returnvalues.OK)
