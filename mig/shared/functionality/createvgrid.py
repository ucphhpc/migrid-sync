#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createvgrid - create a vgrid with all the collaboration components
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

"""Create a new VGrid"""

import os
import traceback
import ConfigParser
from email.utils import parseaddr
from tempfile import NamedTemporaryFile

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, generate_https_urls, valid_dir_input
from shared.defaults import default_vgrid, all_vgrids, any_vgrid, \
     keyword_owners, keyword_members, default_vgrid_settings_limit
from shared.fileio import write_file, make_symlink, delete_file
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.safeeval import subprocess_call, subprocess_popen, \
     subprocess_stdout, subprocess_pipe
from shared.useradm import distinguished_name_to_user, get_full_user_map
from shared.vgrid import vgrid_is_owner, vgrid_set_owners, vgrid_set_members, \
     vgrid_set_resources, vgrid_set_triggers, vgrid_set_settings, \
     vgrid_create_allowed, vgrid_restrict_write_support, vgrid_flat_name, \
     vgrid_settings
from shared.vgridkeywords import get_settings_keywords_dict


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['text', defaults]

def create_scm(
    configuration,
    client_id,
    vgrid_name,
    scm_dir,
    output_objects,
    repair=False
    ):
    """Create new Mercurial SCM repository"""

    logger = configuration.logger
    kind = 'member'
    scm_alias = 'vgridscm'
    # TODO: we only really support scm cert access for now
    # NOTE: we default to MiG cert and fallback to ext cert
    server_url = configuration.migserver_https_mig_cert_url
    if not server_url:
        server_url = configuration.migserver_https_ext_cert_url
    if scm_dir.find('private') > -1:
        kind = 'owner'
        scm_alias = 'vgridownerscm'
    elif scm_dir.find('public') > -1:
        kind = 'public'
        scm_alias = 'vgridpublicscm'
        server_url = configuration.migserver_http_url
    server_url_optional_port = ':'.join(server_url.split(':')[:2])
    cgi_template_script = os.path.join(configuration.hgweb_scripts,
                                       'hgweb.cgi')
    wsgi_template_script = os.path.join(configuration.hgweb_scripts,
                                        'hgweb.wsgi')

    # Depending on the Mercurial installation some of the
    # configuration strings may vary slightly.
    # We try to catch common variations with multiple targets

    script_template_name = 'repository name'
    script_template_repo = '/path/to/repo'
    script_template_repo_alt = '/path/to/repo/or/config'
    script_scm_name = '%s %s SCM repository' % (vgrid_name, kind)
    repo_base = 'repo'
    target_scm_repo = os.path.join(scm_dir, repo_base)
    repo_rc = os.path.join(target_scm_repo, '.hg', 'hgrc')
    repo_readme = os.path.join(target_scm_repo, 'readme')
    rc_text = '''
[web]
allow_push = *
allow_archive = gz, zip
description = The %s repository for %s participants
''' % (kind, vgrid_name)
    readme_text = '''This is the %(kind)s SCM repository for %(vgrid_name)s.

A web view of the repository is available on
%(server_url)s/%(scm_alias)s/%(vgrid_name)s
in any browser.
Access to non-public repositories is only granted if your user certificate
is imported in the browser.

For full access the repository you need a Mercurial client and the unpacked
user certificate files, that you received upon your certificate request.
Once again for non-public repositories you need client certificate support
in the client. Mercurial 1.3 and later is known to work with certificates,
but please refer to the documentation provided with your installation if you
have an older version. Installation of a newer version in user space should
be possible if case you do not have administrator privileges.

On the client a ~/.hgrc with something like:
[auth]
migserver.prefix = %(server_url_optional_port)s
migserver.key = /path/to/mig/key.pem
migserver.cert = /path/to/mig/cert.pem

# Disabled: we no longer rely on MiG CA signed server certificates
#[web]
#cacerts = /path/to/mig/cacert.pem

should allow access with your certificate.
In the above /path/to/mig is typically /home/USER/.mig where USER is
replaced by your login.

You can check out your own copy of the repository with:
hg clone %(server_url)s/%(scm_alias)s/%(vgrid_name)s [DESTINATION]

Please refer to the Mercurial documentation for further information about
the commands and work flows of this distributed SCM.
''' % {'vgrid_name': vgrid_name, 'kind': kind, 'scm_alias': scm_alias,
       'server_url': server_url,
       'server_url_optional_port': server_url_optional_port}

    cgi_scm_script = os.path.join(scm_dir, 'cgi-bin', 'hgweb.cgi')
    wsgi_scm_script = os.path.join(scm_dir, 'wsgi-bin', 'hgweb.wsgi')
    try:

        # Create scm directory

        if not repair or not os.path.isdir(scm_dir):
            os.mkdir(scm_dir)
        else:
            os.chmod(scm_dir, 0755)

        # Create modified Mercurial Xgi scripts that use local scm repo.
        # In this way modification to one vgrid scm will not affect others.
        # WSGI script may or may not be included in hg installation.
        
        script_pairs = [(cgi_template_script, cgi_scm_script)]
        
        if os.path.exists(wsgi_template_script):
            script_pairs.append((wsgi_template_script, wsgi_scm_script))
        for (template_path, target_path) in script_pairs:
            if repair and os.path.isfile(target_path):
                continue
            target_dir = os.path.dirname(target_path)
            os.mkdir(target_dir)
            template_fd = open(template_path, 'r')
            template_script = template_fd.readlines()
            template_fd.close()
            script_lines = []

            for line in template_script:
                line = line.replace(script_template_name,
                                    script_scm_name)
                line = line.replace(script_template_repo_alt, target_scm_repo)
                line = line.replace(script_template_repo, target_scm_repo)
                script_lines.append(line)
            target_fd = open(target_path, 'w')
            target_fd.writelines(script_lines)
            target_fd.close()

            # IMPORTANT NOTE:
            # prevent users writing in Xgi-bin dirs to avoid remote execution
            # exploits

            os.chmod(target_path, 0555)
            os.chmod(target_dir, 0555)

        if not repair or not os.path.isdir(target_scm_repo):
            os.mkdir(target_scm_repo)
            os.chmod(target_scm_repo, 0755)
            readme_fd = open(repo_readme, 'w')
            readme_fd.write(readme_text)
            readme_fd.close()
            # NOTE: we use command list here to avoid shell requirement
            subprocess_call([configuration.hg_path, 'init', target_scm_repo])
            subprocess_call([configuration.hg_path, 'add', repo_readme])
            subprocess_call([configuration.hg_path, 'commit', '-m"init"',
                             repo_readme])
        if not os.path.exists(repo_rc):
            open(repo_rc, 'w').close()
        os.chmod(repo_rc, 0644)
        rc_fd = open(repo_rc, 'r+')
        rc_fd.seek(0, 2)
        rc_fd.write(rc_text)
        rc_fd.close()
        os.chmod(repo_rc, 0444)

        os.chmod(scm_dir, 0555)
        return True
    except Exception, exc:
        logger.error('Could not create vgrid public_base directory: %s' % exc)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create %s scm: %s' % \
                               (configuration.site_vgrid_label, exc)})
        return False


def create_tracker(
    configuration,
    client_id,
    vgrid_name,
    tracker_dir,
    scm_dir,
    output_objects,
    repair=False
    ):
    """Create new Trac issue tracker bound to SCM repository if given"""

    logger = configuration.logger
    label = "%s" % configuration.site_vgrid_label
    kind = 'member'
    tracker_alias = 'vgridtracker'
    admin_user = distinguished_name_to_user(client_id)
    admin_email = admin_user.get('email', 'unknown@migrid.org')
    admin_id = admin_user.get(configuration.trac_id_field, 'unknown_id')
    # TODO: we only really support tracker cert access for now
    # NOTE: we default to MiG cert and fallback to ext cert
    server_url = configuration.migserver_https_mig_cert_url
    if not server_url:
        server_url = configuration.migserver_https_ext_cert_url
    if tracker_dir.find('private') > -1:
        kind = 'owner'
        tracker_alias = 'vgridownertracker'
    elif tracker_dir.find('public') > -1:
        kind = 'public'
        tracker_alias = 'vgridpublictracker'
        server_url = configuration.migserver_http_url
    tracker_url = os.path.join(server_url, tracker_alias, vgrid_name)

    # Trac init is documented at http://trac.edgewall.org/wiki/TracAdmin
    target_tracker_var = os.path.join(tracker_dir, 'var')
    target_tracker_conf = os.path.join(target_tracker_var, 'conf')
    target_tracker_conf_file = os.path.join(target_tracker_conf, 'trac.ini')
    tracker_db = 'sqlite:db/trac.db'
    # NB: deploy command requires an empty directory target
    # We create a lib dir where it creates cgi-bin and htdocs subdirs
    # and we then symlink both a parent cgi-bin and wsgi-bin to it
    target_tracker_deploy = os.path.join(tracker_dir, 'lib')
    target_tracker_bin = os.path.join(target_tracker_deploy, 'cgi-bin')
    target_tracker_cgi_link = os.path.join(tracker_dir, 'cgi-bin')
    target_tracker_wsgi_link = os.path.join(tracker_dir, 'wsgi-bin')
    target_tracker_gvcache = os.path.join(target_tracker_var, 'gvcache')
    target_tracker_downloads = os.path.join(target_tracker_var, 'downloads')
    target_tracker_files = os.path.join(target_tracker_var, 'files')
    target_tracker_attachments = os.path.join(target_tracker_var,
                                              'files/attachments')
    target_tracker_log = os.path.join(target_tracker_var, 'log')
    target_tracker_log_file = os.path.join(target_tracker_log, 'trac.log')
    repo_base = 'repo'
    target_scm_repo = os.path.join(scm_dir, repo_base)
    project_name = '%s %s project tracker' % (vgrid_name, kind)
    create_cmd = None
    create_status = True
    # Trac requires tweaking for certain versions of setuptools
    # http://trac.edgewall.org/wiki/setuptools
    admin_env = {}
    # strip non-string args from env to avoid wsgi execv errors like
    # http://stackoverflow.com/questions/13213676
    for (key, val) in os.environ.items():
        if isinstance(val, basestring):
            admin_env[key] = val
    admin_env["PKG_RESOURCES_CACHE_ZIP_MANIFESTS"] = "1"
    
    try:

        # Create tracker directory

        if not repair or not os.path.isdir(tracker_dir):
            logger.info('create tracker dir: %s' % tracker_dir)
            os.mkdir(tracker_dir)
        else:
            logger.info('write enable tracker dir: %s' % tracker_dir)
            os.chmod(tracker_dir, 0755)
            
        # Create Trac project that uses local storage.
        # In this way modification to one vgrid tracker will not affect others.

        if not repair or not os.path.isdir(target_tracker_var):
            # Init tracker with trac-admin command:
            # trac-admin tracker_dir initenv projectname db respostype repospath
            create_cmd = [configuration.trac_admin_path, target_tracker_var,
                          'initenv', vgrid_name, tracker_db, 'hg',
                          target_scm_repo]
            # Trac may fail silently if ini file is missing
            if configuration.trac_ini_path and \
                   os.path.exists(configuration.trac_ini_path):
                create_cmd.append('--inherit=%s' % configuration.trac_ini_path)

            # IMPORTANT: trac commands are quite verbose and will cause trouble
            # if the stdout/err is not handled (Popen vs call)
            logger.info('create tracker project: %s' % create_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(create_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker creation %s failed: %s (%d)" % \
                                (create_cmd, proc.stdout.read(), retval))

            # We want to customize generated project trac.ini with project info
        
            conf = ConfigParser.SafeConfigParser()
            conf.read(target_tracker_conf_file)

            conf_overrides = {
                'trac': {
                    'base_url': tracker_url,
                    },
                'project': {
                    'admin': admin_email,
                    'descr': project_name,
                    'footer': "",
                    'url': tracker_url,
                    },
                'header_logo': {
                    'height': -1,
                    'width': -1,
                    'src': os.path.join(server_url, 'images', 'site-logo.png'),
                    'link': '',
                    },
                }
            if configuration.smtp_server:
                (from_name, from_addr) = parseaddr(configuration.smtp_sender)
                from_name += ": %s %s project tracker" % (vgrid_name, kind)
                conf_overrides['notification'] = {
                    'smtp_from': from_addr,
                    'smtp_from_name': from_name,
                    'smtp_server': configuration.smtp_server,
                    'smtp_enabled': True,
                    }

            for (section, options) in conf_overrides.items():
                if not conf.has_section(section):
                    conf.add_section(section)
                for (key, val) in options.items():
                    conf.set(section, key, str(val))

            project_conf = open(target_tracker_conf_file, "w")
            project_conf.write("# -*- coding: utf-8 -*-\n")
            # dump entire conf file
            for section in conf.sections():
                project_conf.write("\n[%s]\n" % section)
                for option in conf.options(section):
                    project_conf.write("%s = %s\n" %
                                       (option, conf.get(section, option)))
            project_conf.close()

        if not repair or not os.path.isdir(target_tracker_deploy):
            # Some plugins require DB changes so we always force DB update here
            # Upgrade environment using trac-admin command:
            # trac-admin tracker_dir upgrade
            upgrade_cmd = [configuration.trac_admin_path, target_tracker_var,
                           'upgrade']
            logger.info('upgrade project tracker database: %s' % upgrade_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(upgrade_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker 1st upgrade db %s failed: %s (%d)" % \
                                (upgrade_cmd, proc.stdout.read(), retval))

            # Create cgi-bin with scripts using trac-admin command:
            # trac-admin tracker_dir deploy target_tracker_bin
            deploy_cmd = [configuration.trac_admin_path, target_tracker_var,
                          'deploy', target_tracker_deploy]
            logger.info('deploy tracker project: %s' % deploy_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(deploy_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker deployment %s failed: %s (%d)" % \
                                (deploy_cmd, proc.stdout.read(), retval))

        if not repair or not os.path.isdir(target_tracker_cgi_link):
            os.chmod(target_tracker_var, 0755)
            os.symlink(target_tracker_bin, target_tracker_cgi_link)
        if not repair or not os.path.isdir(target_tracker_wsgi_link):
            os.chmod(target_tracker_var, 0755)
            os.symlink(target_tracker_bin, target_tracker_wsgi_link)
        if not repair or not os.path.isdir(target_tracker_gvcache):
            os.chmod(target_tracker_var, 0755)
            os.mkdir(target_tracker_gvcache)
        if not repair or not os.path.isdir(target_tracker_downloads):
            os.chmod(target_tracker_var, 0755)
            os.mkdir(target_tracker_downloads)
        if not repair or not os.path.isdir(target_tracker_files):
            os.chmod(target_tracker_var, 0755)
            os.mkdir(target_tracker_files)
        if not repair or not os.path.isdir(target_tracker_attachments):
            os.chmod(target_tracker_var, 0755)
            os.mkdir(target_tracker_attachments)
        if not repair or not os.path.isfile(target_tracker_log_file):
            os.chmod(target_tracker_log, 0755)
            open(target_tracker_log_file, 'w').close()

        if not repair or create_cmd:
            # Give admin rights to creator using trac-admin command:
            # trac-admin tracker_dir permission add ADMIN_ID PERMISSION
            perms_cmd = [configuration.trac_admin_path, target_tracker_var,
                         'permission', 'add', admin_id, 'TRAC_ADMIN']
            logger.info('provide admin rights to creator: %s' % perms_cmd)
            # NOTE: we use command list here to avoid shell requirement
            proc = subprocess_popen(perms_cmd, stdout=subprocess_pipe,
                                    stderr=subprocess_stdout, env=admin_env)
            retval = proc.wait()
            if retval != 0:
                raise Exception("tracker permissions %s failed: %s (%d)" % \
                                (perms_cmd, proc.stdout.read(), retval))

            # Customize Wiki front page using trac-admin commands:
            # trac-admin tracker_dir wiki export WikiStart tracinfo.txt
            # trac-admin tracker_dir wiki import AboutTrac tracinfo.txt
            # trac-admin tracker_dir wiki import WikiStart welcome.txt
            # trac-admin tracker_dir wiki import SiteStyle style.txt

            settings = {'vgrid_name': vgrid_name, 'kind': kind, 'cap_kind':
                        kind.capitalize(), 'server_url':  server_url,
                        'css_wikipage': 'SiteStyle', '_label': label}
            if kind == 'public':
                settings['access_limit'] = "public"
                settings['login_info'] = """
This %(access_limit)s page requires you to register to get a login. The owners
of the %(_label)s will then need to give you access as they see fit.
""" % settings
            else:
                settings['access_limit'] = "private"
                settings['login_info'] = """
These %(access_limit)s pages use your certificate for login. This means that
you just need to click [/login login] to ''automatically'' sign in with your
certificate ID.

Owners of a %(_label)s can login and access the [/admin Admin] menu where they
can configure fine grained access permissions for all other users with access
to the tracker.

Please contact the owners of this %(_label)s if you require greater tracker
access.
""" % settings
            intro_text = \
                       """= %(cap_kind)s %(vgrid_name)s Project Tracker =
Welcome to the ''%(access_limit)s'' %(kind)s project management site for the
'''%(vgrid_name)s''' %(_label)s. It interfaces with the corresponding code
repository for the %(_label)s and provides a number of tools to help software
development and project management.

== Quick Intro ==
This particular page is a Wiki page which means that all ''authorized''
%(vgrid_name)s users can edit it.

Generally wou need to [/login login] at the top of the page to get access to
most of the features here. The navigation menu provides buttons to access
 * this [/wiki Wiki] with customizable contents
 * a [/roadmap Project Roadmap] with goals and progress
 * the [/browser Code Browser] with access to the %(kind)s SCM repository
 * the [/report Ticket Overview] page with pending tasks or issues
 * ... and so on.
%(login_info)s

== Look and Feel ==
The look and feel of this project tracker can be customized with ordinary CSS
through the %(css_wikipage)s Wiki page. Simply create that page and go
ahead with style changes as you see fit.

== Limitations ==
For security reasons all project trackers are quite locked down to avoid abuse.
This implies a number of restrictions on the freedom to fully tweak them e.g.
by installing additional plugins or modifying the core configuration.  

== Further Information ==
Please see TitleIndex for a complete list of local wiki pages or refer to
TracIntro for additional information and help on using Trac.
""" % settings
            style_text = """/*
CSS settings for %(cap_kind)s %(vgrid_name)s project tracker.
Uncomment or add your style rules below to modify the look and feel of all the
tracker pages. The example rules target the major page sections, but you can
view the full page source to find additional style targets.
*/

/*
body {
  background: #ccc;
  background: transparent url('/images/pattern.png');
  color: #000;
  margin: 0;
  padding: 0;
}

#banner,#main,#footer {
  background: white;
  border: 1px solid black;
  border-radius: 4px;
  -moz-border-radius: 4px;
  padding: 8px;
  margin: 4px;
}

#main {
  /* Prevent footer overlap with menu */
  min-height: 500px;
}

#ctxnav,#mainnav {
  margin: 4px;
}

#header {
}

#logo img {
}
*/
""" % settings
            trac_fd, wiki_fd = NamedTemporaryFile(), NamedTemporaryFile()
            style_fd = NamedTemporaryFile()
            trac_tmp, wiki_tmp = trac_fd.name, wiki_fd.name
            style_tmp = style_fd.name
            trac_fd.close()
            wiki_fd.write(intro_text)
            wiki_fd.flush()
            style_fd.write(style_text)
            style_fd.flush()

            for (act, page, path) in [('export', 'WikiStart', trac_tmp),
                                      ('import', 'TracIntro', trac_tmp),
                                      ('import', 'WikiStart', wiki_tmp),
                                      ('import', 'SiteStyle', style_tmp)]:
                wiki_cmd = [configuration.trac_admin_path, target_tracker_var,
                            'wiki', act, page, path]
                logger.info('wiki %s %s: %s' % (act, page, wiki_cmd))
                # NOTE: we use command list here to avoid shell requirement
                proc = subprocess_popen(wiki_cmd, stdout=subprocess_pipe,
                                        stderr=subprocess_stdout,
                                        env=admin_env)
                retval = proc.wait()
                if retval != 0:
                    raise Exception("tracker wiki %s failed: %s (%d)" % \
                                    (perms_cmd, proc.stdout.read(), retval))

            wiki_fd.close()

        # Some plugins require DB changes so we always force DB update here
        # Upgrade environment using trac-admin command:
        # trac-admin tracker_dir upgrade
        upgrade_cmd = [configuration.trac_admin_path, target_tracker_var,
                       'upgrade']
        logger.info('upgrade project tracker database: %s' % upgrade_cmd)
        # NOTE: we use command list here to avoid shell requirement
        proc = subprocess_popen(upgrade_cmd, stdout=subprocess_pipe,
                                stderr=subprocess_stdout, env=admin_env)
        retval = proc.wait()
        if retval != 0:
            raise Exception("tracker 2nd upgrade db %s failed: %s (%d)" % \
                            (upgrade_cmd, proc.stdout.read(), retval))

        if repair:
            # Touch WSGI scripts to force reload of running instances
            for name in os.listdir(target_tracker_wsgi_link):
                os.utime(os.path.join(target_tracker_wsgi_link, name), None)
    except Exception, exc:
        create_status = False
        logger.error('create %s tracker failed: %s' % (label, exc))
        logger.error("creation env:\n%s" % admin_env)
        logger.error("creation trace:\n%s" % traceback.format_exc())
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not create %s tracker: %s' % (label, exc)
                               })

    try:
        # IMPORTANT NOTE:
        # prevent users writing in cgi-bin, plugins and conf dirs to avoid
        # remote code execution exploits!
        #
        # We keep permissions at a minimum for the rest, but need to allow
        # writes to DB, attachments and log.

        logger.info('fix permissions on %s' % project_name)
        perms = {}
        for real_path in [os.path.join(target_tracker_var, i) for i in \
                          ['db', 'attachments', 'files/attachments', 'log',
                           'gvcache', 'downloads']]:
            perms[real_path] = 0755
        for real_path in [os.path.join(target_tracker_var, 'db', 'trac.db'),
                          target_tracker_log_file]:
            perms[real_path] = 0644
        for real_path in [os.path.join(target_tracker_bin, i) for i in \
                          ['trac.cgi', 'trac.wsgi']]:
            perms[real_path] = 0555
        for (root, dirs, files) in os.walk(tracker_dir):
            for name in dirs + files:
                real_path = os.path.join(root, name)
                if perms.has_key(real_path):
                    logger.info('loosen permissions on %s' % real_path)
                    os.chmod(real_path, perms[real_path])
                elif name in dirs:
                    os.chmod(real_path, 0555)
                else:
                    os.chmod(real_path, 0444)
        os.chmod(tracker_dir, 0555)
    except Exception, exc:
        create_status = False
        logger.error('fix permissions on %s tracker failed: %s' % (label, exc))
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not finish %s tracker: %s' % (label, exc)
                               })
        os.chmod(tracker_dir, 0000)
    return create_status


def create_forum(
    configuration,
    client_id,
    vgrid_name,
    forum_dir,
    output_objects,
    repair=False
    ):
    """Create new forum - just the base dir"""
    logger = configuration.logger
    try:
        if not repair or not os.path.isdir(forum_dir):
            os.mkdir(forum_dir)
        return True
    except Exception, exc:
        logger.error('Could not create forum directory: %s' % exc)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create %s forum: %s'
                               % (configuration.site_vgrid_label, exc)})
        return False


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Create %s" % label
    output_objects.append({'object_type': 'header', 'text'
                          : 'Create %s' % label})
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

    vgrid_name = accepted['vgrid_name'][-1].strip().strip('/')

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # No owner check here so we need to specifically check for illegal
    # directory access

    reserved_names = (default_vgrid, any_vgrid, all_vgrids)
    if vgrid_name in reserved_names or \
           not valid_dir_input(configuration.vgrid_home, vgrid_name):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Illegal vgrid_name: %s' % vgrid_name})
        logger.warning("""createvgrid possible illegal directory access
attempt by '%s': vgrid_name '%s'""" % (client_id, vgrid_name))
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional limitation of create vgrid permission
    if not user_dict or \
           not vgrid_create_allowed(configuration, user_dict):
        logger.warning("user %s is not allowed to create vgrids!" % client_id)
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only privileged users can create %ss' % label})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    vgrid_home_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                               vgrid_name)) + os.sep
    public_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name)) + os.sep
    public_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridscm')) + os.sep
    public_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridtracker')) + os.sep
    private_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name)) + os.sep
    private_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridscm')) + os.sep
    private_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridtracker')) + os.sep
    private_forum_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridforum')) + os.sep
    vgrid_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name)) + os.sep
    vgrid_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridscm')) + os.sep
    vgrid_tracker_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridtracker')) + os.sep
    vgrid_files_link = os.path.join(configuration.user_home, client_dir,
                                    vgrid_name)

    if vgrid_restrict_write_support(configuration):
        flat_vgrid = vgrid_flat_name(vgrid_name, configuration)
        vgrid_writable_dir = os.path.abspath(os.path.join(
            configuration.vgrid_files_writable, flat_vgrid)) + os.sep
        vgrid_readonly_dir = os.path.abspath(os.path.join(
            configuration.vgrid_files_readonly, flat_vgrid)) + os.sep
    else:
        vgrid_writable_dir = None
        vgrid_readonly_dir = None

    # does vgrid exist?

    if os.path.exists(vgrid_home_dir):
        logger.warning("user %s can't create vgrid %s - it exists!" % \
                       (client_id, vgrid_name))
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '%s %s cannot be created because it already exists!'
             % (label, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # does a matching directory for vgrid share already exist?

    if os.path.exists(vgrid_files_link):
        logger.warning("user %s can't create vgrid %s - a folder shadows!" % \
                       (client_id, vgrid_name))
        output_objects.append(
            {'object_type': 'error_text', 'text': '''
%s %s cannot be created because a folder with the same name already exists!
Please rename your %s folder to something else before creating a %s with that
name.''' % (label, vgrid_name, vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # verify that client is owner of imada or imada/topology if trying to
    # create imada/topology/test

    vgrid_name_list = vgrid_name.split('/')
    vgrid_name_parts = len(vgrid_name_list)
    if vgrid_name_parts <= 0:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'vgrid_name not specified?'})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    elif vgrid_name_parts == 1:

        # anyone can create base vgrid

        new_base_vgrid = True
    else:
        new_base_vgrid = False
        logger.debug("user %s attempts to create sub vgrid %s" % \
                     (client_id, vgrid_name))
        parent_vgrid_name = '/'.join(vgrid_name_list[0:vgrid_name_parts - 1])
        parent_files_base = os.path.dirname(vgrid_home_dir.rstrip(os.sep))
        if not os.path.isdir(parent_files_base):
            logger.warning("user %s can't create vgrid %s - no parent!" % \
                           (client_id, vgrid_name))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Parent %s %s does not exist!' % (label, parent_vgrid_name)})
            return (output_objects, returnvalues.CLIENT_ERROR)
        if not vgrid_is_owner(parent_vgrid_name,
                              client_id, configuration):
            logger.warning("user %s can't create vgrid %s - not owner!" % \
                           (client_id, vgrid_name))
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'You must own parent - to create a sub %s' % label})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # Creating VGrid beneath a write restricted parent is not allowed

        (load_parent, parent_settings) = vgrid_settings(parent_vgrid_name,
                                                        configuration,
                                                        as_dict=True)
        if not load_parent:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'failed to load saved %s settings' % parent_vgrid_name})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # TODO: change this to support keyword_owners as well?
        #       at least then same write_shared_files MUST be forced on it
        if parent_settings.get('write_shared_files', keyword_members) != \
               keyword_members:
            logger.warning("%s can't create vgrid %s - write limited parent!" \
                           % (client_id, vgrid_name))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You cannot create new %ss under write-restricted ones' % \
                 label})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # make sure all dirs can be created (that a file or directory with the same
    # name do not exist prior to the vgrid creation)

    try_again_string = \
        """%s cannot be created, a file or directory exists with the same
name, please try again with a new name!""" % label
    if os.path.exists(public_files_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(private_files_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(vgrid_files_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid files

    try:
        os.mkdir(vgrid_home_dir)
    except Exception, exc:
        logger.error('Could not create vgrid base directory: %s' % exc)
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : """Could not create %(vgrid_label)s directory, remember to create
parent %(vgrid_label)s before creating a sub-%(vgrid_label)s.""" % \
             {'vgrid_label': label}
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid public_base files

    try:
        os.mkdir(public_files_dir)
        pub_readme = os.path.join(public_files_dir, 'README')
        if not os.path.exists(pub_readme):
            https_links = generate_https_urls(
                configuration,
                '%(auto_base)s/vgrid/%(vgrid_name)s/',
                {'vgrid_name': vgrid_name})
            write_file("""= Public Web Page =
This directory is used for hosting the public web page for the %s %s.
It is accessible by the public from the %ss page or directly using the URL
%s

Just update the index.html file to suit your wishes for an entry page. It can
link to any other material in this folder or subfolders with relative
addresses. So it is possible to create a full web site with multiple pages and
rich content like on other web hosting services. However, there's no support
for server side scripting with Python, ASP or PHP for security reasons.
""" % (vgrid_name, label, label, https_links),
                       pub_readme, logger)
        pub_entry_page = os.path.join(public_files_dir, 'index.html')
        if not os.path.exists(pub_entry_page):
            write_file("""<!DOCTYPE html>
<html>
<head>
<meta http-equiv='Content-Type' content='text/html;charset=utf-8'/>
<title>Public entry page not created yet..</title>
</head>
<body>
No public entrypage created yet! (If you are owner of the %s, overwrite
public_base/%s/index.html to place it here)
</body>
</html>""" % (vgrid_name, label),
                       pub_entry_page, logger)
    except Exception, exc:
        logger.error('Could not create vgrid public_base directory: %s' % exc)
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : """Could not create %(vgrid_label)s public_base directory,
remember to create parent %(vgrid_label)s before creating a
sub-%(vgrid_label)s.""" % {'vgrid_label': label}
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid private_base files

    try:
        os.mkdir(private_files_dir)
        priv_readme = os.path.join(private_files_dir, 'README')
        if not os.path.exists(priv_readme):
            https_links = generate_https_urls(
                configuration,
                '%(auto_base)s/vgrid/%(vgrid_name)s/path/index.html',
                {'vgrid_name': vgrid_name})
            write_file("""= Private Web Page =
This directory is used for hosting the private web page for the %s %s.
It is only accessible for members and owners either from the %ss page or
directly using the URL
%s

Just update the index.html file to suit your wishes for an entry page. It can
link to any other material in this folder or subfolders with relative
addresses. So it is possible to create a full web site with multiple pages and
rich content like on other web hosting services. However, there's no support
for server side scripting with Python, ASP or PHP for security reasons.
""" % (vgrid_name, label, label, https_links),
                       priv_readme, logger)
        priv_entry_page = os.path.join(private_files_dir, 'index.html')
        if not os.path.exists(priv_entry_page):
            write_file("""<!DOCTYPE html>
<html>
<head>
<meta http-equiv='Content-Type' content='text/html;charset=utf-8'/>
<title>Private entry page not created yet..</title>
</head>
<body>
No private entrypage created yet! (If you are owner of the %s, overwrite
private_base/%s/index.html to place it here)<br>
</body>
</html>""" % (vgrid_name, label),
                       priv_entry_page, logger)
    except Exception, exc:
        logger.error('Could not create vgrid private_base directory: %s' % exc)
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : """Could not create %(vgrid_label)s private_base directory,
remember to create parent %(vgrid_label)s before creating a
sub-%(vgrid_label)s.""" % {'vgrid_label': label}
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory in vgrid_files_home or vgrid_files_writable to contain
    # shared files for the new vgrid.

    try:
        if vgrid_writable_dir:
            os.mkdir(vgrid_writable_dir)
            make_symlink(vgrid_writable_dir.rstrip('/'),
                         vgrid_files_dir.rstrip('/'),
                         logger)
        else:
            os.mkdir(vgrid_files_dir)
        share_readme = os.path.join(vgrid_files_dir, 'README')
        if not os.path.exists(share_readme):
            write_file("""= Private Share =
This directory is used for hosting private files for the %s %s.
It is accessible for all members and owners as a virtual %s directory in the
user home directory. Therefore it is also usable as source and destination
for job input and output.
""" % (vgrid_name, label, vgrid_name),
                       share_readme, logger, make_parent=False)
    except Exception, exc:
        logger.error('Could not create vgrid files directory: %s' % exc)
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create %s files directory.' % \
                               label
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    all_scm_dirs = ['', '', '']
    if configuration.hg_path and configuration.hgweb_scripts:

        # create participant scm repo in the vgrid shared dir
        # TODO: split further to save outside vgrid_files_dir?

        all_scm_dirs = [public_scm_dir, private_scm_dir, vgrid_scm_dir]
        for scm_dir in all_scm_dirs:
            if not create_scm(configuration, client_id, vgrid_name, scm_dir,
                               output_objects):
                return (output_objects, returnvalues.SYSTEM_ERROR)

    all_tracker_dirs = ['', '', '']
    if configuration.trac_admin_path:

        # create participant tracker in the vgrid shared dir
        # TODO: split further to save outside vgrid_files_dir?

        all_tracker_dirs = [public_tracker_dir, private_tracker_dir,
                            vgrid_tracker_dir]
        for (tracker_dir, scm_dir) in zip(all_tracker_dirs, all_scm_dirs):
            if not create_tracker(configuration, client_id, vgrid_name,
                                  tracker_dir, scm_dir, output_objects):
                return (output_objects, returnvalues.SYSTEM_ERROR)

    for forum_dir in [private_forum_dir]:
        if not create_forum(configuration, client_id, vgrid_name, forum_dir,
                            output_objects):
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # Create owners list with client_id as owner only add user in owners list
    # if new vgrid is a base vgrid (because symlinks to subdirs are not
    # necessary, and an owner is per definition owner of sub vgrids).

    owner_list = []
    if new_base_vgrid == True:
        owner_list.append(client_id)
    else:
        owner_list.append('')

    (owner_status, owner_msg) = vgrid_set_owners(configuration, vgrid_name,
                                                 owner_list)
    if not owner_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save owner list: %s' % owner_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create empty pickled members list

    (member_status, member_msg) = vgrid_set_members(configuration, vgrid_name,
                                                    [])
    if not member_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save member list: %s' % member_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create empty pickled resources list

    (resource_status, resource_msg) = vgrid_set_resources(configuration,
                                                          vgrid_name, [])
    if not resource_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save resource list: %s' % \
                               resource_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create empty pickled triggers list

    (trigger_status, trigger_msg) = vgrid_set_triggers(configuration,
                                                          vgrid_name, [])
    if not trigger_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save trigger list: %s' % \
                               trigger_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create default pickled settings list with only required values set to
    # leave all other fields for inheritance by default.

    init_settings = {}
    settings_specs = get_settings_keywords_dict(configuration)
    for (key, spec) in settings_specs.items():
        if spec['Required']:
            init_settings[key] = spec['Value']
    init_settings['vgrid_name'] = vgrid_name
    (settings_status, settings_msg) = vgrid_set_settings(configuration,
                                                         vgrid_name,
                                                         init_settings.items())
    if not settings_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save settings list: %s' % \
                               settings_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if new_base_vgrid:

        # create sym link from creators (client_id) home directory to directory
        # containing the vgrid files

        src = vgrid_files_dir
        if not make_symlink(src, vgrid_files_link, logger):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create link to %s files!' % \
                                   label
                                  })
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # make sure public_base dir exists in users home dir

        user_public_base = os.path.join(configuration.user_home,
                client_dir, 'public_base')
        try:
            os.mkdir(user_public_base)
        except:
            logger.warning("could not create %s. Probably already exists." % \
                   user_public_base)

        public_base_dst = os.path.join(user_public_base, vgrid_name)

        # create sym link for public_base

        if not make_symlink(public_files_dir, public_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Could not create link to public_base dir!'
                                  })
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # make sure private_base dir exists in users home dir

        user_private_base = os.path.join(configuration.user_home,
                client_dir, 'private_base')
        try:
            os.mkdir(user_private_base)
        except:
            logger.warning("could not create %s. Probably already exists." % \
                           user_private_base)

        private_base_dst = os.path.join(user_private_base, vgrid_name)

        # create sym link for private_base

        if not make_symlink(private_files_dir, private_base_dst, logger):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Could not create link to private_base dir!'
                 })
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # create sym link to make public_base public by linking it to
        # wwwpublic/vgrid

        try:

            # make sure root dir exists

            os.mkdir(os.path.join(configuration.wwwpublic, 'vgrid'))
        except:

            # dir probably exists

            pass

        if not make_symlink(public_files_dir,
                            os.path.join(configuration.wwwpublic,
                            'vgrid', vgrid_name), logger, force=True):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Could not create link in wwwpublic/vgrid/%s'
                 % vgrid_name})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '%s %s created!' % (label, vgrid_name)})
    output_objects.append(
        {'object_type': 'link',
         'destination': 'adminvgrid.py?vgrid_name=%s' % vgrid_name,
         'class': 'adminlink iconspace',
         'title': 'Administrate your new %s' % label,
         'text': 'Administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


