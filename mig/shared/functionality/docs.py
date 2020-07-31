#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# docs - online documentation generator
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

# See all_docs dictionary below for information about adding
# documentation topics.

"""On-demand documentation generator"""
from __future__ import absolute_import

import fnmatch
import os

from mig.shared import mrslkeywords
from mig.shared import resconfkeywords
from mig.shared import returnvalues
from mig.shared.functional import validate_input
from mig.shared.init import initialize_main_variables
from mig.shared.output import get_valid_outputformats


def signature():
    """Signature of the main function"""

    defaults = {'show': [''], 'search': ['']}
    return ['text', defaults]


def display_topic(output_objects, subject, all_docs):
    """Display specified subject"""
    if subject in all_docs.keys():
        topic = all_docs[subject]['title']
        output_objects.append({'object_type': 'link',
                               'destination': './docs.py?show=%s' % subject,
                               'class': 'urllink iconspace',
                               'title': '%s Documentation' % topic,
                               'text': topic,
                               'plain_text': topic,
                               })
    else:
        output_objects.append({'object_type': 'text', 'text':
                               "No documentation found matching '%s'" % subject
                               })
    output_objects.append({'object_type': 'html_form', 'text': '<br />'})


def show_subject(subject, doc_function, doc_args):
    """Show documentation for specified subject"""
    doc_function(*doc_args)


def display_doc(output_objects, subject, all_docs):
    """Show doc"""
    if subject in all_docs.keys():
        generator = all_docs[subject]['generator']
        args = all_docs[subject]['args']
        show_subject(subject, generator, args)
    else:
        output_objects.append({'object_type': 'text', 'text':
                               "No documentation found matching '%s'" % subject
                               })


def mrsl_keywords(configuration, output_objects):
    """All job description keywords"""
    keywords_dict = mrslkeywords.get_keywords_dict(configuration)
    output_objects.append(
        {'object_type': 'header', 'text': 'Job description: mRSL'})
    sorted_keys = keywords_dict.keys()
    sorted_keys.sort()
    for keyword in sorted_keys:
        info = keywords_dict[keyword]
        output_objects.append(
            {'object_type': 'html_form', 'text': "<div id='%s'></div>" % keyword})
        output_objects.append(
            {'object_type': 'sectionheader', 'text': keyword})
        entries = []
        for (field, val) in info.items():
            entries.append(field + ': ' + str(val))
        output_objects.append({'object_type': 'list', 'list': entries})


def resconf_keywords(configuration, output_objects):
    """All resource configuration keywords"""
    resource_keywords = \
        resconfkeywords.get_resource_keywords(configuration)
    exenode_keywords = \
        resconfkeywords.get_exenode_keywords(configuration)
    storenode_keywords = \
        resconfkeywords.get_storenode_keywords(configuration)
    topics = [('Resource configuration', resource_keywords),
              ('Execution node configuration', exenode_keywords),
              ('Storage node configuration', storenode_keywords)]
    for (title, keywords_dict) in topics:
        output_objects.append({'object_type': 'header', 'text': title})
        sorted_keys = keywords_dict.keys()
        sorted_keys.sort()
        for keyword in sorted_keys:
            info = keywords_dict[keyword]
            output_objects.append(
                {'object_type': 'sectionheader', 'text': keyword})
            entries = []
            for (field, val) in info.items():
                entries.append(field + ': ' + str(val))
            output_objects.append({'object_type': 'list', 'list': entries})


def valid_outputformats(configuration, output_objects):
    """All valid output formats"""
    output_objects.append(
        {'object_type': 'header', 'text': 'Valid outputformats'})
    output_objects.append(
        {'object_type': 'text', 'text':
         'The outputformat is specified with the output_format parameter.'
         })
    output_objects.append({'object_type': 'text', 'text':
                           'Example: SERVER_URL/ls.py?output_format=txt'
                           })
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Valid formats'})
    entries = []
    for outputformat in get_valid_outputformats():
        entries.append(outputformat)
    output_objects.append({'object_type': 'list', 'list': entries})


def runtime_environments(configuration, output_objects):
    """All runtime environment keywords"""
    output_objects.append(
        {'object_type': 'header', 'text': 'Runtime Environments'})
    output_objects.append({'object_type': 'text', 'text':
                           """Runtime environments work as a kind of contract
between users and resources. The user can not as such expect a given resource
to provide any particular software or execution environment. However, jobs can
request one or more runtime environments listed here in order to only get
scheduled to resources advertising that environment."""})
    output_objects.append({'object_type': 'text', 'text':
                           """Anyone can create new runtime environments but
it is up to the resource owners to actually advertise the environments that
their resources provide.
For example a resource with the Python interpreter installed could advertise a
corresponding python runtime environment, so that all jobs that depend on
python to run can request that runtime environment and only end up on resources
with python."""})
    output_objects.append({'object_type': 'text', 'text':
                           """Runtime environments can be quite flexible in
order to support many kinds of software or hardware environments."""})


def license_information(configuration, output_objects):
    """Credits and license information for all MiG software dependencies"""
    output_objects.append({'object_type': 'header', 'text': 'License'})
    output_objects.append({'object_type': 'html_form', 'text': """
%s is based on the Minimum intrusion Grid (MiG) middleware. You can read about
MiG at the
<a class='urllink iconspace' href='https://sourceforge.net/projects/migrid/'>
project web site</a>.<br />
The MiG software license follows below:<br />
""" % configuration.site_title})
    try:
        # NOTE: occasionally __file__ points to .pyc file rather than .py
        #       we just strip the trailing c to always have access to license
        file_path = __file__
        file_path = file_path.replace('.pyc', '.py')
        module_fd = open(os.path.abspath(file_path))
        in_license, lic_lines = False, []
        for line in module_fd:
            if line.find('BEGIN_HEADER') != -1:
                in_license = True
            elif line.find('END_HEADER') != -1:
                in_license = False
                break
            elif line.find('This file is part of') != -1:
                # skip two lines
                next(module_fd)
                continue
            elif in_license:
                lic_lines.append(line.strip('#'))
        module_fd.close()
    except Exception as exc:
        configuration.logger.error("could not extract license info: %s" % exc)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "failed to extract license information!"})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Skip module info and leading/trailing blank lines

    lic_text = ''.join(lic_lines[2:-1])
    output_objects.append({'object_type': 'html_form', 'text':
                           '<code>%s</code><br />' %
                           lic_text.replace('\n', '<br \>')})

    output_objects.append(
        {'object_type': 'header', 'text': 'Acknowledgements'})

    output_objects.append({'object_type': 'text', 'text': """
This software is mainly implemented in Python and extension modules:"""})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://www.python.org/',
                           'class': 'urllink iconspace',
                           'title': 'Python Home Page',
                           'text': 'Python (PSF license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://pypi.python.org/pypi/watchdog',
                           'class': 'urllink iconspace',
                           'title': 'Python Watchdog Module at Python Package Index',
                           'text': 'Python Watchdog Module (Apache 2.0 license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://pypi.python.org/pypi/scandir',
                           'class': 'urllink iconspace',
                           'title': 'Python scandir Module at Python Package Index',
                           'text': 'Python scandir Module (New BSD license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://pypi.python.org/pypi/pyenchant',
                           'class': 'urllink iconspace',
                           'title': 'Python Enchant Module at Python Package Index',
                           'text': 'Python Enchant Module (LGPL license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'text', 'text': """
Web interfaces are served with the Apache HTTP Server:"""})
    output_objects.append({'object_type': 'link',
                           'destination': 'http://httpd.apache.org/',
                           'class': 'urllink iconspace',
                           'title': 'Apache HTTP Server Home Page',
                           'text': 'Apache HTTP Server with included modules '
                           '(Apache 2.0 license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://code.google.com/p/modwsgi/',
                           'class': 'urllink iconspace',
                           'title': 'Apache WSGI Module Home Page',
                           'text': 'Apache WSGI Module (Apache 2.0 license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'text', 'text':
                           "relying on JavaScript, styling and artwork from:"})
    output_objects.append({'object_type': 'link',
                           'destination': 'http://jquery.com/',
                           'class': 'urllink iconspace',
                           'title': 'JQuery Home Page',
                           'text': 'JQuery and extension modules (GPL/MIT and '
                           'Creative Commons 3.0 licenses)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://getbootstrap.com',
                           'class': 'urllink iconspace',
                           'title': 'Bootstrap Home Page',
                           'text': 'Bootstrap (MIT license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://fontawesome.com',
                           'class': 'urllink iconspace',
                           'title': 'Font Awesome Home Page',
                           'text': 'Font Awesome (Font Awesome Free license '
                           'with icons under CC BY 4.0 license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination':
                           'http://codemirror.net/',
                           'class': 'urllink iconspace',
                           'title': 'CodeMirror Home Page',
                           'text': 'CodeMirror web code editor (BSD '
                           'compatible license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination': 'http://markitup.jaysalvat.com/',
                           'class': 'urllink iconspace',
                           'title': 'markItUp! Home Page',
                           'text': 'markItUp! web markup editor (GPL/MIT '
                           'license)'})
    output_objects.append({'object_type': 'text', 'text':
                           "and icons from the following sources:"})

    output_objects.append({'object_type': 'link',
                           'destination': 'http://www.iconarchive.com/artist/pixelmixer.html',
                           'class': 'urllink iconspace',
                           'title': 'PixelMixer Home Page',
                           'text': 'pixel-mixer.com icons (free to use, '
                           'acknowledgement required)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination':
                           'http://www.famfamfam.com/lab/icons/silk/',
                           'class': 'urllink iconspace',
                           'title': 'FamFamFam Icons Home Page',
                           'text': 'famfamfam.com silk icons (Creative '
                           'Commons 2.5 license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination':
                           'http://www.kde-look.org/content/show.php/'
                           'Crystal+SVG?content=8341',
                           'class': 'urllink iconspace',
                           'title': 'KDE Crystal Icons HomePage',
                           'text': 'KDE Crystal Icons, LGPL'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'link',
                           'destination':
                           'https://www.svgrepo.com/',
                           'class': 'urllink iconspace',
                           'title': 'SVG Repo Home Page',
                           'text': 'SVG Repo Icons and Vectors (Creative '
                           'Commons CC0 / Public Domain license)'})
    output_objects.append({'object_type': 'text', 'text': ''})
    output_objects.append({'object_type': 'text', 'text':
                           "Core communication with dedicated resources use "
                           "OpenSSH client utilities:"})
    output_objects.append({'object_type': 'link',
                           'destination': 'http://www.openssh.com/',
                           'class': 'urllink iconspace',
                           'title': 'OpenSSH HomePage',
                           'text': 'OpenSSH secure remote shell and file '
                           'transfer (BSD license)'})
    output_objects.append({'object_type': 'text', 'text': ''})

    password_dep = False
    openssl_dep = False
    if configuration.site_enable_vmachines:
        openssl_dep = True
    if configuration.site_enable_sftp or configuration.site_enable_sftp_subsys:
        password_dep = True
        if configuration.site_enable_sftp_subsys:
            sftp_provider = "OpenSSH and Paramiko"
        else:
            sftp_provider = "Paramiko"
        output_objects.append({'object_type': 'text', 'text':
                               "SFTP access is delivered using %s:" %
                               sftp_provider})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://pypi.python.org/pypi/paramiko',
                               'class': 'urllink iconspace',
                               'title': 'Paramiko at Python Package Index',
                               'text': 'Paramiko SSH2 Module (LGPL license)'})
    if configuration.site_enable_davs:
        password_dep = True
        output_objects.append({'object_type': 'text', 'text':
                               "WebDAVS access is delivered using wsgidav:"})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://github.com/mar10/wsgidav',
                               'class': 'urllink iconspace',
                               'title': 'WsgiDAV Home Page',
                               'text': 'WsgiDAV Server Module (MIT license)'})
    if configuration.site_enable_ftps:
        password_dep = True
        openssl_dep = True
        output_objects.append({'object_type': 'text', 'text':
                               "FTPS access is delivered using pyftpdlib:"})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://code.google.com/p/pyftpdlib/',
                               'class': 'urllink iconspace',
                               'title': 'pyftpdlib Home Page',
                               'text': 'pyftpdlib FTP(S) Server Module (MIT license)'})
    if configuration.site_enable_seafile:
        password_dep = True
        output_objects.append({'object_type': 'text', 'text':
                               "File synchronization is delivered with Seafile:"})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://www.seafile.com',
                               'class': 'urllink iconspace',
                               'title': 'Seafile Home Page',
                               'text': 'Seafile Community Edition (various open source licenses)'})
        output_objects.append({'object_type': 'text', 'text':
                               "Seafile web pages are exposed with:"})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://github.com/ceph/mod-proxy-fcgi',
                               'class': 'urllink iconspace',
                               'title': 'Apache FCGI Proxy Module Home Page',
                               'text': 'Apache FCGI Proxy Module (Apache 2.0 license)'})
    if configuration.site_enable_transfers:
        output_objects.append({'object_type': 'text', 'text':
                               "Background data transfers use LFTP / RSync:"})
        output_objects.append({'object_type': 'link',
                               'destination': 'http://lftp.yar.ru/',
                               'class': 'urllink iconspace',
                               'title': 'LFTP Home Page',
                               'text': 'LFTP file transfer program (GPL license)'})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://rsync.samba.org/',
                               'class': 'urllink iconspace',
                               'title': 'RSync Home Page',
                               'text':
                               'RSync incremental file transfer client (GPL license)'})
    if password_dep:
        output_objects.append({'object_type': 'text', 'text': """
The optional password authentication support in SFTP/DAVS/FTPS servers relies
on the PBKDF2 module (embedded) from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.python.org/pypi/pbkdf2',
                               'class': 'urllink iconspace',
                               'title': 'pbkdf2 at Python Package Index',
                               'text': 'PBKDF2 Module (MIT license)'})
    if configuration.site_password_cracklib:
        output_objects.append({'object_type': 'text', 'text': """
The optional password strength testing for SFTP/DAVS/FTPS servers relies
on the Cracklib module from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.python.org/pypi/cracklib',
                               'class': 'urllink iconspace',
                               'title': 'cracklib at Python Package Index',
                               'text': 'Cracklib Module (LGPL license)'})
    if openssl_dep:
        output_objects.append({'object_type': 'text', 'text': """
The OpenSSL crypto helpers in the optional FTPS/VMachines proxy servers rely
on the PyOpenSSL module from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.python.org/pypi/pyOpenSSL',
                               'class': 'urllink iconspace',
                               'title': 'PyOpenSSL at Python Package Index',
                               'text': 'PyOpenSSL Module (Apache 2.0 license)'})
    if [i for i in configuration.notify_protocols if not i == 'email']:
        output_objects.append({'object_type': 'text', 'text': """
The optional instant messaging support in the imnotify server relies
on the irclib module from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.python.org/pypi/python-irclib',
                               'class': 'urllink iconspace',
                               'title': 'Python irclib at Python Package Index',
                               'text': 'Python irclib Module (LGPL license)'})
    if configuration.site_enable_twofactor:
        output_objects.append({'object_type': 'text', 'text': """
The optional 2-factor authentication in logins relies on the PyOTP module
from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.org/project/pyotp/',
                               'class': 'urllink iconspace',
                               'title': 'pyotp at Python Package Index',
                               'text': 'PyOTP Module (BSD license)'})
        output_objects.append({'object_type': 'text', 'text': """
The associated QR codes are rendered locally in the browser with the QRious
JavaScript library from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://neocotic.com/qrious/',
                               'class': 'urllink iconspace',
                               'title': 'QRious library home page',
                               'text': 'QRious JavaScript Library (GPLv3 license)'})
    if configuration.hg_path and configuration.hgweb_scripts:
        output_objects.append({'object_type': 'text', 'text':
                               "SCM repositories are delivered with Mercurial:"
                               })
        output_objects.append({'object_type': 'link',
                               'destination': 'http://mercurial.selenic.com/',
                               'class': 'urllink iconspace',
                               'title': 'Mercurial SCM Home Page',
                               'text': 'Mercurial SCM (GPLv2 license)'})
    if configuration.trac_admin_path:
        output_objects.append({'object_type': 'text', 'text':
                               """Trackers are delivered using Trac:"""})
        output_objects.append({'object_type': 'link',
                               'destination': 'http://trac.edgewall.org/',
                               'class': 'urllink iconspace',
                               'title': 'Trac Project Tracker Home Page',
                               'text': 'Trac Project Tracker (BSD license)'})
    if configuration.user_openid_address or configuration.user_openid_providers:
        output_objects.append({'object_type': 'text', 'text':
                               """OpenID login/support is delivered with:"""})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://github.com/openid/python-openid',
                               'class': 'urllink iconspace',
                               'title': 'Python OpenID Module at GitHub',
                               'text': 'Python OpenID Module (Apache 2.0 license)'})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'link',
                               'destination': 'http://findingscience.com/mod_auth_openid/',
                               'class': 'urllink iconspace',
                               'title': 'Apache OpenID Module Home Page',
                               'text': 'Apache OpenID Module (MIT license)'})
    if configuration.site_enable_jupyter:
        output_objects.append({'object_type': 'text', 'text': """
The optional interactive computing integration through Jupyter relies on the
Requests module from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.python.org/pypi/requests',
                               'class': 'urllink iconspace',
                               'title': 'Requests Module at Python Package Index',
                               'text': 'Python Requests Module (Apache 2.0 license)'})

    if configuration.site_enable_cloud:
        output_objects.append({'object_type': 'text', 'text': """
The optional interactive cloud computing integration through openstack relies on the
openstack client module from:"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.org/project/python-openstackclient/',
                               'class': 'urllink iconspace',
                               'title': 'OpenStack Client at Python Package Index',
                               'text': 'Python OpenStack Client (Apache 2.0 license)'})

    output_objects.append({'object_type': 'text', 'text': """The optional
JSONRPC interface is delivered with the jsonrpclib module:"""})
    output_objects.append({'object_type': 'link',
                           'destination': 'https://pypi.python.org/pypi/jsonrpclib',
                           'class': 'urllink iconspace',
                           'title': 'Python JSONRPC Module at Python Package Index',
                           'text': 'Python JSONRPClib Module (Apache 2.0 license)'})

    output_objects.append({'object_type': 'text', 'text': """
The optional country code validation support in certificate and OpenID account
creation relies on the iso3166 module from:"""})
    output_objects.append({'object_type': 'link',
                           'destination':
                           'https://pypi.org/project/iso3166/',
                           'class': 'urllink iconspace',
                           'title': 'iso3166 at Python Package Index',
                           'text': 'iso3166 Module (MIT license)'})

    if configuration.site_enable_workflows:
        output_objects.append({'object_type': 'text', 'text': """
The optional workflows overlay framework relies on:"""})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://pypi.org/project/nbformat',
                               'class': 'urllink iconspace',
                               'title': 'Python nbformat Module at Python Package Index',
                               'text': 'nbformat Module (BSD License)'})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://pypi.org/project/nbconvert',
                               'class': 'urllink iconspace',
                               'title': 'Python nbconvert Module at Python Package Index',
                               'text': 'nbconvert Module (BSD License)'})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://pypi.org/project/PyYAML/',
                               'class': 'urllink iconspace',
                               'title': 'Python PyYAML Module at Python Package Index',
                               'text': 'PyYAML Module (MIT License)'})
        output_objects.append({'object_type': 'text', 'text': """
In addition to the specified pypi packages, the workflows setup relies on the
executing resources to have the following packages provided as runtime environments"""})
        output_objects.append({'object_type': 'text', 'text': """
The papermill Module should be configured as a PAPERMILL runtime environment on the executing resources"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.org/project/papermill/',
                               'class': 'urllink iconspace',
                               'title': 'Python papermill Module at Python Package Index',
                               'text': 'papermill Module (BSD License)'})
        output_objects.append({'object_type': 'text', 'text': """
The notebook_parameterizer module enables the generation of notebooks that have been parameterized before runtime"""})
        output_objects.append({'object_type': 'link',
                               'destination':
                               'https://pypi.org/project/notebook-parameterizer/',
                               'class': 'urllink iconspace',
                               'title': 'Python notebook_parameterize Module at Python Package Index',
                               'text': 'notebook_parameterize Module (MIT License)'})

        output_objects.append({'object_type': 'text', 'text': """
The workflows also requires that the resources provide the SSHFS_MOUNT runtime environment"""})
        output_objects.append({'object_type': 'link',
                               'destination': 'https://github.com/libfuse/sshfs',
                               'class': 'urllink iconspace',
                               'title': 'The sshfs client available from GitHub used to network mount a user home',
                               'text': 'sshfs client (GNU v2.0)'})


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    show = accepted['show'][-1].lower()
    search = accepted['search'][-1].lower()

    # Topic to generator-function mapping - add new topics here by adding an
    # anchor_name -> {'title': topic, 'generator': generator_function,
    #                 'arg': generator_args}
    # entry.

    default_args = (configuration, output_objects)
    all_docs = {
        'mrsl': {'title': 'Job description: mRSL', 'generator': mrsl_keywords,
                 'args': default_args},
        'resconf': {'title': 'Resource configuration', 'generator':
                    resconf_keywords, 'args': default_args},
        'outformats': {'title': 'Valid outputformats', 'generator':
                       valid_outputformats, 'args': default_args},
        'runtimeenv': {'title': 'Runtime Environments', 'generator':
                       runtime_environments, 'args': default_args},
        'credits': {'title': 'License and Acknowledgements', 'generator':
                    license_information, 'args': default_args},
    }

    output_objects.append({'object_type': 'header', 'text':
                           '%s On-demand Documentation' %
                           configuration.short_title})
    if not show:
        output_objects.append({'object_type': 'text',
                               'text': '''
This is the integrated help system for %s.
You can search for a documentation topic or select the particular
section directly.
Please note that the integrated help is rather limited to short overviews and
technical specifications.''' % configuration.short_title})

        output_objects.append({'object_type': 'text',
                               'text': '''
You can find more user friendly tutorials and examples on the
official site support pages:'''})
        output_objects.append({'object_type': 'link', 'destination':
                               configuration.site_external_doc,
                               'class': 'urllink iconspace', 'title':
                               'external documentation',
                               'text': 'external %s documentation' %
                               configuration.site_title,
                               'plain_text': configuration.site_external_doc})

    html = '<br />Filter (using *,? etc.)'
    html += "<form method='get' action='docs.py'>"
    html += "<input type='hidden' name='show' value='' />"
    html += "<input type='text' name='search' value='' />"
    html += "<input type='submit' value='Filter' />"
    html += '</form><br />'
    output_objects.append({'object_type': 'html_form', 'text': html})

    # Fall back to show all topics

    if not search and not show:
        search = '*'

    if search:

        # Pattern matching: select all topics that _contain_ search pattern
        # i.e. like re.search rather than re.match

        search_keys = []
        for (key, val) in all_docs.items():

            # Match any prefix and suffix.
            # No problem with extra '*'s since'***' also matches 'a')

            topic = val['title']
            if fnmatch.fnmatch(topic.lower(), '*' + search + '*'):
                search_keys.append(key)

        output_objects.append(
            {'object_type': 'header', 'text': 'Documentation topics:'})
        for key in search_keys:
            display_topic(output_objects, key, all_docs)
        if not search_keys:
            output_objects.append(
                {'object_type': 'text', 'text': 'No topics matching %s' % search})

    if show:

        # Pattern matching: select all topics that _contain_ search pattern
        # i.e. like re.search rather than re.match

        show_keys = []
        for (key, val) in all_docs.items():

            # Match any prefix and suffix.
            # No problem with extra '*'s since'***' also matches 'a')

            topic = val['title']
            logger.info("match show %s vs %s or %s" % (show, topic, key))
            if fnmatch.fnmatch(topic.lower(), '*' + show + '*') or \
                    show == key:
                logger.info("found show match for %s" % show)
                show_keys.append(key)

        for key in show_keys:
            logger.info("show doc for %s" % key)
            display_doc(output_objects, key, all_docs)
        if not show_keys:
            output_objects.append(
                {'object_type': 'text', 'text': 'No topics matching %s' % show})

    return (output_objects, returnvalues.OK)
